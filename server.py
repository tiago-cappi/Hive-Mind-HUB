#!/usr/bin/env python
"""Ponte local do Hub de voz (web app).

Serve a pagina, faz STT (faster-whisper local), chama o Claude com acesso explícito ao vault e
dispara o Kokoro residente (speak_server.py). Escuta SO em 127.0.0.1.

Sessoes paralelas: cada aba do front tem um `sid` proprio, com seu processo
`claude` isolado (registro SESS[sid]). A fala e serializada por um arbitro
unico (fila SPEAK_Q) para nunca duas sessoes falarem ao mesmo tempo.

Rotas:
  GET  /             -> index.html
  POST /hud_ping     -> {hud} -> pulso da janela do HUD (autoquit da ponte)
  POST /hud_bye      -> {hud} -> baixa da janela ao fechar (sendBeacon)
  POST /stt          -> {audio (webm), sid} -> faster-whisper (STT_LOCK) -> {texto}
  POST /ask          -> {texto,modelo,esforco,sid,titulo} -> claude (por sid) -> {reply} + log
  POST /speak        -> {reply,sid,titulo,earcon_hz} -> enfileira no arbitro -> fala (Kokoro)
  POST /session_start  -> {sid,modelo,esforco} -> garante o processo daquele sid vivo (warm)
  POST /session_reset  -> {sid,modelo,esforco} -> mata + resobe o processo daquele sid
  POST /session_end    -> {sid} -> mata e remove o registro daquele sid
  GET  /session_watch/<sid>?rev=N -> long-poll: espelha (sem consumir) as
                          linhas NDJSON que /ask ou /speak emitirem para
                          aquele sid desde N ({lines}); rev negativo = so
                          sincroniza o rev atual. Usado pelo HUD para
                          reproduzir a sessao do celular na aba CELULAR.
"""
import os
import re
from hub_runtime.instance_lock import hold as hold_instance
import shlex
import uuid
import json
import time
import queue
import threading
import subprocess
import tempfile
import datetime
import atexit
import platform

# Blindagem WMI (Python 3.13 trava em queries Win32_*); igual aos demais scripts.
try:
    platform._uname_cache = platform.uname_result(
        "Windows", os.environ.get("COMPUTERNAME", "pc"), "11", "10.0.26200",
        os.environ.get("PROCESSOR_ARCHITECTURE", "AMD64"))
except Exception:
    pass
platform.win32_ver = lambda *a, **k: ("10", "10.0.26200", "", "")
platform._wmi_query = lambda *a, **k: (_ for _ in ()).throw(OSError("wmi off"))

HERE = os.path.dirname(os.path.abspath(__file__))
from hub_runtime.paths import PROJECT_ROOT, RUNTIME_ROOT, vault_root, voice_python, speech_temp
from hub_runtime.assistant import bridge_command
from hub_runtime.instance import blueprint as instance_blueprint, record as record_instance
from codex_frontend import blueprint as codex_frontend_blueprint
from HiveMind import blueprint as hivemind_frontend_blueprint
from HiveMind.backend.routes import blueprint as hivemind_backend_blueprint

VAULT = str(vault_root())
LOG = os.path.join(VAULT, "_agentes", "voice-hub.md")
# Todo turno de TODA sessao da append neste mesmo arquivo, e o Flask e threaded:
# com N abas respondendo em paralelo, dois writes maiores que o buffer do modo
# texto (8 KB) viram varios os.write cada um e INTERCALAM — linha de uma sessao
# no meio da outra. Coberto por tests/test_concorrencia.py.
LOG_LOCK = threading.Lock()


def log_turn(stamp, tag, texto, reply):
    """Grava um turno no transcript do vault. Serializado entre sessoes."""
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with LOG_LOCK, open(LOG, "a", encoding="utf-8") as fh:
            fh.write(f"\n**[{stamp}] {tag}EU:** {texto}\n"
                     f"**[{stamp}] {tag}CLAUDE:** {reply}\n")
    except OSError:
        pass
KPY = str(voice_python())
SPEAK_SRV = str(RUNTIME_ROOT / "voice" / "speak_server.py")
PORT = 8765
# Medido nesta maquina (i5-1235U, CPU int8, vad_filter): `small` transcreve a
# 0.37x do tempo real -- 4min de audio viravam ~13min de STT, com o HUD parado
# em PROCESSANDO. `base` roda a 0.72x (2x mais rapido) e transcreveu MELHOR o
# mesmo audio. Por isso o padrao e base; HUB_WHISPER troca sem mexer no codigo.
WHISPER_MODEL = os.environ.get("HUB_WHISPER", "base")  # tiny | base (padrao) | small | medium
# Fala em streaming: a sintese custa ~2x a duracao do audio nesta maquina, entao
# ela comeca pela 1a frase, junto com a escrita do Claude, em vez de esperar o
# turno fechar. So vale a pena em resposta longa (curta sintetiza rapido).
SPEAK_STREAM = os.environ.get("HUB_SPEAK_STREAM", "1") != "0"
SPEAK_MIN = int(os.environ.get("HUB_SPEAK_MIN", "320"))  # chars de texto p/ acionar

TMP = str(speech_temp())
REQ = os.path.join(TMP, "hub_say_req.txt")
STREAM = os.path.join(TMP, "hub_say_stream.txt")        # fala em streaming: texto nascendo
STREAM_END = os.path.join(TMP, "hub_say_stream_end.txt")  # fala em streaming: fim do texto
STARTED = os.path.join(TMP, "hub_say_started.txt")
DONE = os.path.join(TMP, "hub_say_done.txt")
READY = os.path.join(TMP, "hub_say_ready.txt")
ENVELOPE = os.path.join(TMP, "hub_say_envelope.json")
META = os.path.join(TMP, "hub_say_meta.json")  # Fase 3: earcon_hz + anuncio do turno de fala atual
STT_DIR = TMP  # audio recebido pelo /stt: um arquivo POR SID (ver _stt_path)

from flask import Flask, request, jsonify, send_from_directory, Response, stream_with_context
from werkzeug.utils import safe_join
from faster_whisper import WhisperModel

app = Flask(__name__)
app.register_blueprint(instance_blueprint)
app.register_blueprint(codex_frontend_blueprint)
app.register_blueprint(hivemind_frontend_blueprint)
app.register_blueprint(hivemind_backend_blueprint)

print(f"[hub] carregando whisper '{WHISPER_MODEL}' (1a vez baixa o modelo)...", flush=True)
WMODEL = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
print("[hub] whisper pronto.", flush=True)

# Guarda nomeada do WMODEL (regra 5): o modelo e UM so e o faster-whisper nao e
# thread-safe -- o Flask e threaded, entao duas abas transcrevendo ao mesmo tempo
# entravam no mesmo objeto. Serializa o STT entre as sessoes.
STT_LOCK = threading.Lock()


def _stt_path(sid):
    """Arquivo de audio daquela sessao. Um unico hub_stt_in.webm global fazia
    duas abas gravando ao mesmo tempo sobrescreverem o audio uma da outra."""
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", sid or DEFAULT_SID)[:40] or DEFAULT_SID
    return os.path.join(STT_DIR, "hub_stt_in_" + safe + ".webm")


SPEAK_PROC = None
SHUTDOWN_LOCK = threading.Lock()
SPEAK_OWNED = False   # so a ponte que subiu o Kokoro pode encerra-lo (ver _shutdown)


def start_speak_server():
    # Sobe o Kokoro residente (carga unica do modelo = sem delay por turno).
    global SPEAK_OWNED, SPEAK_PROC
    os.makedirs(TMP, exist_ok=True)
    for p in (REQ, STREAM, STREAM_END, STARTED, DONE, READY, META):
        try:
            os.remove(p)
        except OSError:
            pass
    # stdout/stderr -> DEVNULL: sob pythonw o handle herdado e invalido; sem
    # isso, um print do kokoro_onnx (1a sintese/avisos) lanca excecao que o
    # producer engole -> sintese falha em silencio (sem audio). DEVNULL = sink ok.
    speech_proc = subprocess.Popen([KPY, SPEAK_SRV], creationflags=0x08000000,  # CREATE_NO_WINDOW
                     stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     env=dict(os.environ, HUB_SPEAK_TEMP=TMP))
    SPEAK_PROC = speech_proc
    SPEAK_OWNED = True
    record_instance(speech_proc.pid)


def stop_speak_server():
    try:
        with open(REQ, "w", encoding="utf-8") as f:
            f.write("__quit__")
    except OSError:
        pass


def _shutdown():
    # Mantém a posse até encerrar o residente próprio. Um lançamento seguinte
    # não pode limpar o __quit__ antes de o residente anterior recebê-lo.
    global SPEAK_OWNED, SPEAK_PROC
    with SHUTDOWN_LOCK:
        if not SPEAK_OWNED:
            return
        try:
            kill_all()
        except Exception:
            pass
        stop_speak_server()
        if SPEAK_PROC is not None:
            try:
                SPEAK_PROC.wait(timeout=5)
            except subprocess.TimeoutExpired:
                _kill_tree(SPEAK_PROC)
                SPEAK_PROC.wait(timeout=5)
        SPEAK_PROC = None
        SPEAK_OWNED = False


atexit.register(_shutdown)


# ----------------------------------------------------------------------------
# AUTOQUIT — a ponte morre junto com o HUD.
# A ponte era residente de proposito (reabrir o Hub reaproveitava a porta), mas
# fechar a janela do Chrome nao derrubava nada: um pythonw ficou 18h no ar
# segurando a 8765 com codigo VELHO em memoria, e o usuario editava o server.py
# sem efeito nenhum. Agora cada janela do HUD pulsa em /hud_ping com um id
# proprio e avisa em /hud_bye ao fechar; quando nao sobra HUD vivo, a ponte se
# encerra. O registro e por ID (nao um contador) para aguentar N janelas: fechar
# uma nao derruba a ponte da outra.
# So arma DEPOIS do primeiro pulso -- subir a ponte sem HUD (suite de testes,
# cliente do celular, script auxiliar) continua valendo. HUB_AUTOQUIT=0 desliga.
# ----------------------------------------------------------------------------
AUTOQUIT = os.environ.get("HUB_AUTOQUIT", "1") != "0"
HUD_TTL = int(os.environ.get("HUB_HUD_TTL", "90"))   # s sem pulso = HUD morto
HUDS = {}                      # hud_id -> instante do ultimo pulso
HUD_LOCK = threading.Lock()    # protege HUDS (pulsos chegam em threads do Flask)
HUD_EVER = [False]             # algum HUD ja se conectou nesta ponte?


def _huds_vivos(now=None):
    """Remove os HUDs calados ha mais de HUD_TTL e devolve quantos sobraram."""
    now = now or time.time()
    with HUD_LOCK:
        for hid in [h for h, t in HUDS.items() if now - t > HUD_TTL]:
            HUDS.pop(hid, None)
        return len(HUDS)


def _hud_watchdog():
    # TTL folgado de proposito: o Chrome estrangula timers de janela em segundo
    # plano (ate 1 pulso/minuto), e derrubar a ponte com o HUD minimizado seria
    # pior que o problema original.
    while True:
        time.sleep(2)
        if not HUD_EVER[0] or _huds_vivos():
            continue
        from HiveMind.backend.manager import hub_exit_ready
        if not hub_exit_ready():
            continue
        print("[hub] nenhum HUD vivo -> encerrando a ponte", flush=True)
        try:
            _shutdown()
        finally:
            os._exit(0)


@app.after_request
def no_cache(resp):
    resp.headers["Cache-Control"] = "no-store, max-age=0"
    return resp


@app.route("/")
def index():
    return send_from_directory(HERE, "index.html")


@app.route("/assets/<path:fn>")
def assets(fn):
    return send_from_directory(os.path.join(HERE, "assets"), fn)


# ----------------------------------------------------------------------------
# RELATÓRIOS VISUAIS — a IA grava um HTML no acervo explicitamente configurado
# auto-contido em REPORTS_DIR; o front sonda GET /reports e, quando aparece um
# arquivo novo, abre o visor sozinho (ver seção 8e do index.html). A pasta fica
# DENTRO do vault de propósito: o histórico de relatórios vira parte do acervo
# do Obsidian, consultável depois.
# ----------------------------------------------------------------------------
REPORTS_DIR = os.path.join(VAULT, "_agentes", "relatorios")
REPORT_EXTS = (".html", ".htm")


def _report_title(path):
    # Título legível: o <title> dos primeiros 4KB; sem ele, o nome do arquivo
    # sem timestamp/extensão. Nunca lança — listagem não pode cair por 1 arquivo.
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            head = f.read(4096)
        m = re.search(r"<title[^>]*>(.*?)</title>", head, re.I | re.S)
        if m and m.group(1).strip():
            return re.sub(r"\s+", " ", m.group(1)).strip()[:120]
    except OSError:
        pass
    base = os.path.splitext(os.path.basename(path))[0]
    base = re.sub(r"^\d{4}-\d{2}-\d{2}[_ ]?\d{0,6}[_ ]?", "", base)
    return (base.replace("_", " ").replace("-", " ").strip() or "relatório")[:120]


@app.route("/reports")
def reports_list():
    # Lista os relatórios (só REPORT_EXTS), mais recente primeiro. Cria a pasta
    # se não existir para o 1º uso não depender de ninguém.
    try:
        os.makedirs(REPORTS_DIR, exist_ok=True)
        items = []
        for fn in os.listdir(REPORTS_DIR):
            if not fn.lower().endswith(REPORT_EXTS):
                continue
            p = os.path.join(REPORTS_DIR, fn)
            try:
                st = os.stat(p)
            except OSError:
                continue
            items.append({"file": fn, "title": _report_title(p),
                          "mtime": int(st.st_mtime), "size": st.st_size})
        items.sort(key=lambda i: (i["mtime"], i["file"]), reverse=True)
        return jsonify({"reports": items})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/reports/<path:fn>")
def reports_file(fn):
    # send_from_directory barra path traversal; serve QUALQUER arquivo da pasta
    # (um relatório pode referenciar uma imagem/CSV vizinho), mas só ela.
    return send_from_directory(REPORTS_DIR, fn)


@app.route("/reports/<path:fn>", methods=["DELETE"])
def reports_delete(fn):
    # Só apaga relatórios (REPORT_EXTS) e só dentro de REPORTS_DIR; safe_join
    # barra path traversal do mesmo jeito que send_from_directory faz no GET.
    if not fn.lower().endswith(REPORT_EXTS):
        return jsonify({"error": "só é possível excluir arquivos de relatório"}), 400
    p = safe_join(REPORTS_DIR, fn)
    if not p or not os.path.isfile(p):
        return jsonify({"error": "relatório não encontrado"}), 404
    try:
        os.remove(p)
    except OSError as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({"ok": True})


@app.route("/hud_ping", methods=["POST"])
def hud_ping():
    # Pulso de uma janela do HUD. Sem `hud` o pulso e ignorado (nao registra um
    # HUD anonimo que ninguem consegue dar baixa depois, prendendo a ponte viva).
    body = request.get_json(silent=True) or {}
    hid = (body.get("hud") or "").strip()
    if hid:
        with HUD_LOCK:
            HUDS[hid] = time.time()
        HUD_EVER[0] = True
    return jsonify({"ok": bool(hid), "huds": len(HUDS), "ttl": HUD_TTL,
                    "autoquit": AUTOQUIT})


@app.route("/hud_bye", methods=["POST"])
def hud_bye():
    # sendBeacon do beforeunload: da baixa na hora, sem esperar o TTL vencer.
    body = request.get_json(silent=True) or {}
    hid = (body.get("hud") or "").strip()
    with HUD_LOCK:
        HUDS.pop(hid, None)
    return jsonify({"ok": True, "huds": len(HUDS)})


@app.route("/stt", methods=["POST"])
def stt():
    f = request.files.get("audio")
    if not f:
        return jsonify({"texto": ""})
    sid = (request.form.get("sid") or "").strip() or DEFAULT_SID
    path = _stt_path(sid)
    f.save(path)
    # o trabalho do faster-whisper acontece ao ITERAR o generator -- por isso o
    # join fica dentro do lock, nao so a chamada de transcribe().
    with STT_LOCK:
        segs, _ = WMODEL.transcribe(path, language="pt", vad_filter=True)
        texto = "".join(s.text for s in segs).strip()
    return jsonify({"texto": texto})


def _basename(p):
    if not p:
        return ""
    return os.path.basename(str(p).rstrip("/\\"))


def friendly_step(blk):
    # Converte um tool_use do stream-json em uma etapa legivel (item 2).
    name = blk.get("name", "") or ""
    inp = blk.get("input", {}) or {}
    if name == "Read":
        return "Lendo " + (_basename(inp.get("file_path")) or "arquivo")
    if name in ("Edit", "MultiEdit"):
        return "Editando " + (_basename(inp.get("file_path")) or "arquivo")
    if name == "Write":
        return "Escrevendo " + (_basename(inp.get("file_path")) or "arquivo")
    if name == "Grep":
        return "Procurando: " + str(inp.get("pattern", ""))[:40]
    if name == "Glob":
        return "Listando arquivos"
    if name == "Bash":
        return "Rodando comando"
    if name == "Skill":
        return "Skill: " + str(inp.get("command") or inp.get("name") or "")
    if name in ("Task", "Agent"):
        return "Delegando a subagente"
    if name == "TodoWrite":
        return "Planejando passos"
    if name in ("WebFetch", "WebSearch"):
        return "Buscando na web"
    if name.startswith("mcp__"):
        return "Ferramenta externa"
    return name or "Trabalhando"


def dbg(level, msg):
    # Evento de debug estruturado p/ a aba DEBUG do frontend.
    return json.dumps({"t": "debug", "lv": level, "msg": str(msg)}) + "\n"


def todos_to_plan(todos):
    # F4: converte o input.todos de um tool_use TodoWrite na lista de itens do
    # painel de plano ({"txt","status"}). Tolera formato ausente/variavel: se
    # nao for uma lista util, devolve [] (o /ask nao emite `plan`).
    if not isinstance(todos, list):
        return []
    items = []
    for td in todos:
        if not isinstance(td, dict):
            continue
        txt = td.get("content") or td.get("activeForm") or ""
        status = td.get("status") or "pending"
        if txt:
            items.append({"txt": str(txt), "status": str(status)})
    return items


# ----------------------------------------------------------------------------
# F6: REGISTRO DE ALTERACOES — o que o Claude de fato mudou no turno.
# O stream-json entrega, no evento `user` que fecha cada ferramenta, um campo
# `tool_use_result` com `structuredPatch` (hunks no formato unified diff) para
# Edit/MultiEdit/Write/NotebookEdit. Daqui saem: arquivo, linhas +/- e o diff.
# Write de arquivo NOVO vem com structuredPatch vazio e `type: create` — nesse
# caso o conteudo inteiro conta como adicao.
# ----------------------------------------------------------------------------
CHANGE_TOOLS = ("Edit", "MultiEdit", "Write", "NotebookEdit")
MAX_DIFF_LINES = 300   # teto de linhas de diff por alteracao (evita NDJSON gigante)
MAX_DIFF_COLS = 240    # teto de largura de cada linha do diff


def _diff_from_patch(patch):
    # structuredPatch -> (linhas formatadas, adicionadas, removidas).
    lines, add, rem = [], 0, 0
    if not isinstance(patch, list):
        return lines, add, rem
    for h in patch:
        if not isinstance(h, dict):
            continue
        lines.append("@@ -{},{} +{},{} @@".format(
            h.get("oldStart", 0), h.get("oldLines", 0),
            h.get("newStart", 0), h.get("newLines", 0)))
        for ln in h.get("lines") or []:
            ln = str(ln)
            if ln.startswith("+"):
                add += 1
            elif ln.startswith("-"):
                rem += 1
            lines.append(ln[:MAX_DIFF_COLS])
    return lines, add, rem


def change_from_tool(name, inp, res, is_error=False):
    # Converte um par tool_use/tool_result em um item do painel ALTERACOES.
    # Devolve None para ferramentas que nao mudam nada (Read, Grep, Glob...).
    inp = inp if isinstance(inp, dict) else {}
    res = res if isinstance(res, dict) else {}
    if name in ("Bash", "PowerShell"):
        cmd = str(inp.get("command", "") or "").strip()
        if not cmd:
            return None
        return {"kind": "cmd", "cmd": cmd[:400],
                "desc": str(inp.get("description", "") or "")[:80],
                "ok": not is_error}
    if name not in CHANGE_TOOLS:
        return None
    path = str(res.get("filePath") or inp.get("file_path")
               or inp.get("notebook_path") or "")
    diff, add, rem = _diff_from_patch(res.get("structuredPatch"))
    novo = res.get("type") == "create"
    if not diff and novo:
        corpo = str(res.get("content") or inp.get("content") or "")
        linhas = corpo.splitlines()
        add = len(linhas)
        diff = ["+" + l[:MAX_DIFF_COLS] for l in linhas]
    truncado = len(diff) > MAX_DIFF_LINES
    if truncado:
        diff = diff[:MAX_DIFF_LINES]
    return {"kind": "create" if novo else "edit",
            "file": _basename(path) or "arquivo", "path": path,
            "add": add, "del": rem, "diff": diff,
            "truncated": truncado, "ok": not is_error}


ALLOWED_MODELS = {"fable", "opus", "sonnet", "haiku"}  # aliases seguros do claude CLI
ALLOWED_EFFORTS = {"low", "medium", "high", "xhigh", "max"}  # --effort do claude CLI
# Nivel de permissao do claude headless. O usuario AUTORIZOU explicitamente
# rodar sem restricoes (edita o vault e roda comandos sem pedir aprovacao);
# necessario porque no modo -p/headless nao ha como aprovar prompts.
PERMISSION_FLAG = " --dangerously-skip-permissions"

# ----------------------------------------------------------------------------
# Processos claude PERSISTENTES (headless) — um por SESSAO (sid). Cada aba do
# front tem seu proprio processo, vivo enquanto a aba existir, lendo turnos
# pela stdin em stream-json e mantendo o contexto EM MEMORIA (sem reiniciar a
# cada mensagem). Duas sessoes diferentes rodam de verdade em paralelo; a
# MESMA sessao serializa turnos entre si (lock por sid).
#   - Nova conversa (contexto zerado) da sessao = matar e respawnar so ela.
#   - Fechar uma aba = matar so o processo daquela sessao.
# Se o persistente falhar, o fallback usa o ID explícito da conversa deste sid.
# ----------------------------------------------------------------------------
SESS = {}                      # sid -> {"proc","model","q","lock","fresh","last_used","cid"}
REG_LOCK = threading.Lock()    # protege criacao/remocao/ITERACAO de entradas em SESS
DEFAULT_SID = "default"        # usado se o front nao mandar nenhum sid (defensivo)
MAX_SESS = 6                   # teto de sessoes simultaneas vivas (Fase 1.5) — RAM (whisper+kokoro+N*claude)
REAP_IDLE_SECS = 6 * 3600      # sessao viva sem uso ha mais que isso -> zumbi, reaproveitada no proximo /session_start


def get_sess(sid):
    sid = (sid or "").strip() or DEFAULT_SID
    with REG_LOCK:
        s = SESS.get(sid)
        if s is None:
            s = {"proc": None, "model": "", "effort": "", "q": None, "lock": threading.Lock(),
                 "fresh": False, "last_used": time.time(), "cid": "", "cancel_rev": 0}
            SESS[sid] = s
        return s


def _alive_count():
    # iteracao protegida: outras threads podem inserir/remover chaves em SESS
    # (get_sess/session_end) enquanto isto roda -> RuntimeError sem o lock.
    with REG_LOCK:
        return sum(1 for s in SESS.values() if s["proc"] is not None and s["proc"].poll() is None)


def _reap_stale(exclude_sid):
    # Sessoes zumbi (o beforeunload/sendBeacon do front pode nao disparar num
    # fechamento abrupto do Chrome) ficam vivas pra sempre sem isso, inflando
    # _alive_count() e ocupando slots mesmo sem uma aba real em uso. Roda a cada /session_start (todo load de pagina).
    now = time.time()
    with REG_LOCK:
        stale = [sid for sid, s in SESS.items()
                 if sid != exclude_sid and s["proc"] is not None
                 and now - s.get("last_used", now) > REAP_IDLE_SECS]
    for sid in stale:
        kill_claude(sid)
        with REG_LOCK:
            SESS.pop(sid, None)


def _claude_reader(stream, tag, q):
    try:
        for ln in stream:
            q.put((tag, ln))
    except Exception as e:
        q.put(("rerr", tag + ": " + str(e)))
    finally:
        q.put((tag + "_end", None))


def spawn_claude(sid, model, effort="", resume=""):
    # Inicia o processo persistente daquele sid no modo stream-json (entrada e saida).
    # `resume` = id de conversa do CLI (s["cid"]): o processo e outro, mas a
    # CONVERSA e a mesma. E o que permite trocar de modelo sem perder o contexto.
    s = get_sess(sid)
    want = model if model in ALLOWED_MODELS else ""
    want_effort = effort if effort in ALLOWED_EFFORTS else ""
    model_flag = f" --model {want}" if want else ""
    effort_flag = f" --effort {want_effort}" if want_effort else ""
    resume_flag = f" --resume {resume}" if resume else ""
    # --include-partial-messages: deltas token a token (texto + thinking) para o
    # streaming ao vivo (F3). E so observabilidade — nao muda o comportamento do
    # Claude. Se uma versao futura do CLI nao aceitar a flag, o processo morre no
    # start -> claude_alive() falso -> /ask cai no fallback `claude -p` (que segue
    # funcionando). Degrada sem quebrar.
    cmd = ("-p --input-format stream-json --output-format stream-json"
           " --verbose --include-partial-messages" + PERMISSION_FLAG + model_flag
           + effort_flag + resume_flag)
    env = dict(os.environ, VOICE_HUB="1")
    with REG_LOCK:
        if sum(1 for item in SESS.values() if item["proc"] is not None and item["proc"].poll() is None) >= MAX_SESS:
            raise RuntimeError(f"limite de {MAX_SESS} sessoes simultaneas")
        p = subprocess.Popen(
            bridge_command(shlex.split(cmd)), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, cwd=str(PROJECT_ROOT), shell=True,
            env=env, text=True, encoding="utf-8", bufsize=1)
        s["proc"], s["model"], s["effort"] = p, want, want_effort
    q = queue.Queue()
    threading.Thread(target=_claude_reader, args=(p.stdout, "out", q), daemon=True).start()
    threading.Thread(target=_claude_reader, args=(p.stderr, "err", q), daemon=True).start()
    s["q"] = q
    s["last_used"] = time.time()
    return p


def claude_alive(sid):
    s = SESS.get(sid)
    return s is not None and s["proc"] is not None and s["proc"].poll() is None


# --- watchdog de ociosidade do /ask -------------------------------------------
# Silencio NAO e' sinal de travamento: um subagente, um build ou uma suite de
# testes passam minutos sem emitir um unico evento. Um teto unico e curto matava
# trabalho legitimo no meio -- pior, no meio de uma escrita de arquivo. Por isso o
# teto depende do que o processo estava fazendo quando calou. Processo morto de
# verdade nao depende disto: o stream fechado chega como tag `_end` e quebra o
# laco na hora.
FALLBACK_TIMEOUT = 300
INACT_BOOT = 90      # turno enviado e nem o system/init voltou -> nao engatou
INACT_IDLE = 300     # ja produziu eventos, nada em aberto -> raciocinio ou rede
INACT_TOOL = 1200    # ferramenta em aberto (Agent, Bash, build) -> ocupado la dentro


def inact_limit(open_tool, events):
    """Teto de silencio (s) e o motivo, dado o que o turno estava fazendo."""
    if open_tool:
        return INACT_TOOL, "ferramenta aberta: " + open_tool
    if not events:
        return INACT_BOOT, "nenhum evento desde o envio do turno"
    return INACT_IDLE, "ocioso sem ferramenta aberta"


def _kill_tree(p):
    """Mata o processo E a arvore abaixo dele.

    spawn_claude sobe com shell=True: o Popen e' o cmd.exe e o `claude` de
    verdade e' filho dele. p.kill() sozinho derrubava so o cmd.exe -- o claude
    ficava orfao, vivo e ainda escrevendo nos arquivos do projeto. Foi assim que
    um turno morto pelo watchdog continuou editando o index.html por baixo do
    turno seguinte.
    """
    if os.name == "nt":
        try:
            subprocess.run(["taskkill", "/PID", str(p.pid), "/T", "/F"],
                           capture_output=True, timeout=10)
        except Exception:
            pass
    try:
        p.kill()
    except Exception:
        pass


def kill_claude(sid):
    s = SESS.get(sid)
    if s is None:
        return
    p = s["proc"]
    if p is not None:
        _kill_tree(p)
    s["proc"], s["q"] = None, None


def cancel_turn(sid):
    s = SESS.get(sid)
    if s is not None:
        with REG_LOCK:
            s["cancel_rev"] = s.get("cancel_rev", 0) + 1
        kill_claude(sid)


def kill_all():
    with REG_LOCK:
        sids = list(SESS.keys())
    for sid in sids:
        try:
            cancel_turn(sid)
        except Exception:
            pass


# ----------------------------------------------------------------------------
# ESPELHO PARA SESSAO SEM ABA (ex.: o cliente do celular, sid="mobile") — copia
# cada linha NDJSON que /ask e /speak ja emitem para um buffer por sid, sem
# alterar o que essas rotas devolvem ao chamador original. Serve so para um
# consumidor via long-poll (GET /session_watch/<sid>) acompanhar processando/
# falando de uma sessao que nao tem aba propria no navegador.
# ----------------------------------------------------------------------------
WATCH = {}          # sid -> {"rev": int, "lines": [(rev, str)], "cond": Condition}
WATCH_LOCK = threading.Lock()
WATCH_KEEP = 400    # linhas guardadas por sid — um turno tipico cabe inteiro


def _watch_slot(sid):
    with WATCH_LOCK:
        w = WATCH.get(sid)
        if w is None:
            w = {"rev": 0, "lines": [], "cond": threading.Condition()}
            WATCH[sid] = w
        return w


def _watch_publish(sid, line):
    w = _watch_slot(sid)
    with w["cond"]:
        w["rev"] += 1
        w["lines"].append((w["rev"], line))
        del w["lines"][:-WATCH_KEEP]
        w["cond"].notify_all()


def _watched(sid, gen):
    """Espelha cada linha do generator NDJSON no buffer de watch daquele sid,
    sem mudar o que e devolvido ao chamador original (so observa, nunca filtra)."""
    for line in gen:
        try:
            _watch_publish(sid, line)
        except Exception:
            pass
        yield line


@app.route("/session_watch/<sid>")
def session_watch(sid):
    # Long-poll: devolve TODAS as linhas NDJSON publicadas para aquele sid desde
    # `rev` (campo `lines`; `line` = a mais recente, mantido por compatibilidade).
    # `rev` negativo = sincronizacao: so o rev atual, sem replay do passado (e o
    # que o HUD usa ao abrir, para nao reencenar turnos antigos do buffer).
    # Nao consome nada de /ask ou /speak -- e so leitura do espelho.
    try:
        since = int(request.args.get("rev", "0"))
    except ValueError:
        since = 0
    w = _watch_slot(sid)
    with w["cond"]:
        if since < 0:
            return jsonify({"rev": w["rev"], "lines": [], "line": None})
        if w["rev"] <= since:
            w["cond"].wait(timeout=25)
        lines = [ln for rv, ln in w["lines"] if rv > since]
        return jsonify({"rev": w["rev"], "lines": lines,
                        "line": lines[-1] if lines else None})


@app.route("/session_start", methods=["POST"])
def session_start():
    # Chamado ao abrir uma aba: deixa o claude daquele sid pronto (warm) em segundo plano.
    body = request.get_json(silent=True) or {}
    sid = (body.get("sid") or "").strip() or DEFAULT_SID
    modelo = (body.get("modelo", "") or "").strip().lower()
    esforco = (body.get("esforco", "") or "").strip().lower()
    _reap_stale(sid)   # limpa sessoes zumbi de fechamentos abruptos antes de contar
    s = get_sess(sid)
    with s["lock"]:
        spawned = False
        if not claude_alive(sid):
            if _alive_count() >= MAX_SESS:
                return jsonify({"ok": False, "err": f"limite de {MAX_SESS} sessoes simultaneas"})
            try:
                spawn_claude(sid, modelo, esforco)
                spawned = True
            except Exception as e:
                return jsonify({"ok": False, "err": str(e)})
    return jsonify({"ok": True, "alive": claude_alive(sid), "spawned": spawned, "model": s["model"], "sid": sid})


@app.route("/session_reset", methods=["POST"])
def session_reset():
    # Nova conversa NAQUELA aba: mata o processo do sid e sobe outro do zero.
    body = request.get_json(silent=True) or {}
    sid = (body.get("sid") or "").strip() or DEFAULT_SID
    modelo = (body.get("modelo", "") or "").strip().lower()
    esforco = (body.get("esforco", "") or "").strip().lower()
    s = get_sess(sid)
    cancel_turn(sid)
    with s["lock"]:
        s["fresh"] = True          # garante limpeza tambem no caminho de fallback
        s["cid"] = ""              # NOVA conversa: nao ha o que retomar no spawn
        ok = True
        try:
            spawn_claude(sid, modelo, esforco)
        except Exception:
            ok = False
    return jsonify({"ok": ok, "alive": claude_alive(sid)})


@app.route("/session_end", methods=["POST"])
def session_end():
    # Chamado ao fechar uma aba/o HUB (sendBeacon, 1x por sid vivo): encerra e remove o registro.
    body = request.get_json(silent=True) or {}
    sid = (body.get("sid") or "").strip() or DEFAULT_SID
    s = SESS.get(sid)
    if s is not None:
        cancel_turn(sid)
        with s["lock"]:
            pass
        with REG_LOCK:
            SESS.pop(sid, None)
    return jsonify({"ok": True})


@app.route("/abort", methods=["POST"])
def abort_turn():
    # CANCELAR do front: derruba o turno em curso daquele sid sem esquecer a sessao.
    # Abortar so o fetch nao bastava -- o processo seguia produzindo e a fila ficava
    # com sobras do turno morto, que contaminavam a proxima pergunta. Aqui o processo
    # some junto com a fila; o próximo /ask retoma pelo ID explícito da sessão.
    body = request.get_json(silent=True) or {}
    sid = (body.get("sid") or "").strip() or DEFAULT_SID
    s = SESS.get(sid)
    if s is None:
        return jsonify({"ok": True, "alive": False})
    # sem o lock: o /ask em curso o segura ate o fim do turno, e o que se quer aqui
    # e' justamente interromper esse turno.
    cancel_turn(sid)
    return jsonify({"ok": True, "alive": claude_alive(sid)})


@app.route("/ask", methods=["POST"])
def ask():
    body = request.get_json(silent=True) or {}
    texto = (body.get("texto", "") or "").strip()
    modelo = (body.get("modelo", "") or "").strip().lower()
    esforco = (body.get("esforco", "") or "").strip().lower()
    sid = (body.get("sid") or "").strip() or DEFAULT_SID
    titulo = (body.get("titulo", "") or "").strip()
    # `mudo`: nao falar em voz alta NESTA maquina neste turno. Quem pede e o
    # cliente do celular (mobile/), que esta longe do PC — a resposta vai pela
    # tela dele. Ausente/False = comportamento de sempre.
    mudo = bool(body.get("mudo"))
    # `mudo` presente e falso = o cliente PEDIU a fala nesta maquina (celular
    # com "falar no PC" ligado) e nao tem como chamar /speak depois — a rota nem
    # esta na whitelist do bridge. Se a fala em streaming nao engatar (resposta
    # < SPEAK_MIN, arbitro ocupado), o proprio /ask fala no fim do turno. O HUD
    # do computador nao manda o campo, entao segue com o fallback /speak dele.
    quer_falar = ("mudo" in body) and not mudo
    if not texto:
        return jsonify({"reply": "(sem pergunta)"})
    want = modelo if modelo in ALLOWED_MODELS else ""
    want_effort = esforco if esforco in ALLOWED_EFFORTS else ""
    s = get_sess(sid)
    turn_rev = s.get("cancel_rev", 0)

    def generate():
        # Instruções do runtime no projeto; vault é somente acervo explícito.
        yield dbg("ASK", "cwd: " + str(PROJECT_ROOT) + " · acervo: " + VAULT + " · sid=" + sid)
        # anuncia a PERGUNTA no proprio stream: quem consome o /ask ja a conhece
        # (e ignora), mas o espelho /session_watch so ve o que passa por aqui —
        # e sem isso o HUD nao teria como mostrar o que chegou do celular.
        yield json.dumps({"t": "ask", "q": texto, "titulo": titulo or sid}) + "\n"
        reply = None
        spk = None            # fala em streaming deste turno (None = fala no /speak)
        with s["lock"]:
            if s.get("cancel_rev", 0) != turn_rev:
                return
            # 1) garante o processo persistente daquele sid vivo no modelo/esforco pedidos
            s["last_used"] = time.time()
            resume_cid = (s.get("cid") or "") if not s["fresh"] else ""
            if claude_alive(sid) and (s["model"] != want or s["effort"] != want_effort):
                yield dbg("ASK", f"modelo/esforco mudou ({s['model'] or 'default'}/{s['effort'] or 'default'} -> {want or 'default'}/{want_effort or 'default'}) -> reiniciando claude")
                kill_claude(sid)
                # o processo morre, a conversa nao: --resume devolve o historico
                # ao processo novo. Sem isso, trocar de modelo zerava o contexto.
                resume_cid = s.get("cid") or ""
            if not claude_alive(sid):
                if _alive_count() >= MAX_SESS:
                    # respeita o mesmo teto do /session_start — nao spawna um Nº+1
                    # processo por baixo dos panos; o fallback também confere o teto.
                    yield dbg("WARN", f"limite de {MAX_SESS} sessoes atingido -> sem processo persistente pra este turno")
                else:
                    try:
                        spawn_claude(sid, want, want_effort, resume=resume_cid)
                        s["fresh"] = False
                        yield dbg("ASK", "claude persistente iniciado · modelo=" + (s["model"] or "default")
                                  + (" · retomando " + resume_cid[:8] if resume_cid else ""))
                    except Exception as e:
                        yield dbg("ERR", "falha ao iniciar persistente: " + str(e))

            if s.get("cancel_rev", 0) != turn_rev:
                kill_claude(sid)
                yield dbg("WARN", "turno cancelado")
                return

            # 2) caminho persistente: envia o turno e drena ate o `result`
            if claude_alive(sid):
                t0 = time.time()
                reply_parts = []
                events = 0
                pend_tools = {}   # F6: tool_use_id -> {name,input}, casado no tool_result
                q = s["q"]
                proc = s["proc"]
                try:
                    msg = {"type": "user", "message": {"role": "user",
                           "content": [{"type": "text", "text": texto}]}}
                    proc.stdin.write(json.dumps(msg) + "\n")
                    proc.stdin.flush()
                    yield dbg("ASK", "turno enviado ao processo persistente")
                    # --- estado do heartbeat (F2) e do streaming parcial (F3) ---
                    HB = 5                     # cadencia do heartbeat de ociosidade (s)
                    THROTTLE = 0.3             # agrupamento de deltas parciais (s)
                    last_real = time.time()    # ultimo item recebido da fila (p/ idle_s)
                    part_buf = []              # deltas de texto acumulados desde o ultimo flush
                    spk_buf = []               # idem, mas para a fala em streaming
                    think_chars = 0            # total de chars de raciocinio neste turno
                    think_sent = -1            # ultimo think_chars ja enviado ao front
                    last_flush = time.time()   # ultimo flush de partial/thinking
                    while True:
                        try:
                            tag, ln = q.get(timeout=HB)
                        except queue.Empty:
                            if spk is not None:
                                spk.alive()   # turno vivo: o canal de fala nao fecha
                            idle = time.time() - last_real
                            # de que silencio se trata: com ferramenta em aberto o
                            # processo esta ocupado por dentro dela, nao parado.
                            open_tool = ""
                            for _pend in pend_tools.values():
                                open_tool = _pend.get("name", "") or ""
                                break
                            limit, why = inact_limit(open_tool, events)
                            if idle >= limit:
                                yield dbg("ERR", f"sem saida ha {int(idle)}s (teto {limit}s, {why}) -> matando")
                                kill_claude(sid)
                                break
                            # F2: expoe o ocioso e o teto vigente (NAO encurta o watchdog;
                            # so informa o front antes dele). Nao emitir apos o result
                            # (o loop ja tera dado break).
                            yield json.dumps({"t": "hb", "idle_s": int(idle),
                                              "limit_s": limit, "tool": open_tool}) + "\n"
                            continue
                        # qualquer item da fila = o processo produziu algo -> zera o ocioso
                        last_real = time.time()
                        if spk is not None:
                            spk.alive()
                        if tag.endswith("_end"):
                            yield dbg("ERR", "processo persistente encerrou o stream")
                            kill_claude(sid)
                            break
                        if tag == "err":
                            s_err = (ln or "").rstrip()
                            if s_err:
                                yield dbg("ERR", "stderr: " + s_err[:300])
                            continue
                        if tag == "rerr":
                            yield dbg("ERR", str(ln))
                            continue
                        line = (ln or "").strip()
                        if not line:
                            continue
                        try:
                            ev = json.loads(line)
                        except ValueError:
                            yield dbg("WARN", "linha nao-JSON: " + line[:160])
                            continue
                        events += 1
                        # id da conversa no CLI: guardado para poder retoma-la
                        # (--resume) quando o processo precisar ser trocado.
                        if ev.get("session_id"):
                            s["cid"] = ev["session_id"]
                        typ = ev.get("type")
                        if typ == "system":
                            yield dbg("ASK", f"system/{ev.get('subtype','')}")
                        elif typ == "assistant":
                            for blk in (ev.get("message", {}) or {}).get("content", []) or []:
                                bt = blk.get("type")
                                if bt == "text":
                                    txt = blk.get("text", "")
                                    reply_parts.append(txt)
                                    yield dbg("ASK", f"texto +{len(txt)} chars")
                                elif bt == "tool_use":
                                    # texto antes de uma ferramenta e narracao de
                                    # progresso, nao a resposta: nao vale falar.
                                    if spk is None:
                                        spk_buf = []
                                    step = friendly_step(blk)
                                    yield json.dumps({"t": "step", "msg": step}) + "\n"
                                    yield dbg("STEP", f"{blk.get('name','')} -> {step}")
                                    # F6: guarda a chamada p/ casar com o resultado (diff)
                                    if blk.get("id"):
                                        pend_tools[blk["id"]] = {"name": blk.get("name", ""),
                                                                 "input": blk.get("input", {}) or {}}
                                    # F4: TodoWrite carrega o plano completo em input.todos
                                    if blk.get("name") == "TodoWrite":
                                        items = todos_to_plan((blk.get("input", {}) or {}).get("todos"))
                                        if items:
                                            yield json.dumps({"t": "plan", "items": items}) + "\n"
                        elif typ == "stream_event":
                            # F3: deltas token a token. ev.event.type=='content_block_delta'
                            # com delta.type em {text_delta(.text), thinking_delta(.thinking),
                            # signature_delta(ignorar)}. Acumula e emite com throttle p/ nao
                            # engasgar o NDJSON (nunca 1 evento por token).
                            se = ev.get("event", {}) or {}
                            if se.get("type") == "content_block_delta":
                                d = se.get("delta", {}) or {}
                                dt = d.get("type")
                                if dt == "text_delta":
                                    part_buf.append(d.get("text", ""))
                                    spk_buf.append(d.get("text", ""))
                                elif dt == "thinking_delta":
                                    think_chars += len(d.get("thinking", "") or "")
                            now = time.time()
                            if now - last_flush >= THROTTLE:
                                if part_buf:
                                    yield json.dumps({"t": "partial", "txt": "".join(part_buf)}) + "\n"
                                    part_buf = []
                                if think_chars != think_sent:
                                    yield json.dumps({"t": "thinking", "chars": think_chars}) + "\n"
                                    think_sent = think_chars
                                last_flush = now
                                # aciona a fala com a resposta ainda nascendo. Exige
                                # arbitro livre: se outra sessao fala, este turno cai
                                # no /speak do fim, como antes.
                                if (spk is None and SPEAK_STREAM and not mudo
                                        and sum(len(x) for x in spk_buf) >= SPEAK_MIN):
                                    spk = try_speak_stream(sid, titulo, body.get("earcon_hz"))
                                    if spk is not None:
                                        yield dbg("SPEAK", "fala em streaming acionada")
                                if spk is not None and spk_buf:
                                    for e in spk.feed("".join(spk_buf)):
                                        yield json.dumps(e) + "\n"
                                    spk_buf = []
                        elif typ == "user":
                            yield dbg("ASK", "tool_result recebido")
                            # F6: fecha a ferramenta -> emite a alteracao (arquivo+diff
                            # ou comando). tool_use_result e' irmao de `message`.
                            tur = ev.get("tool_use_result")
                            for blk in (ev.get("message", {}) or {}).get("content", []) or []:
                                if blk.get("type") != "tool_result":
                                    continue
                                p = pend_tools.pop(blk.get("tool_use_id"), None)
                                if not p:
                                    continue
                                try:
                                    ch = change_from_tool(p["name"], p["input"], tur,
                                                          bool(blk.get("is_error")))
                                except Exception as e:
                                    yield dbg("WARN", "change_from_tool: " + str(e))
                                    continue
                                if ch:
                                    yield json.dumps({"t": "change", "ch": ch}) + "\n"
                                    yield dbg("STEP", "alteracao: " + (
                                        ch.get("cmd", "")[:60] if ch["kind"] == "cmd"
                                        else f"{ch['file']} +{ch['add']} -{ch['del']}"))
                        elif typ == "result":
                            # descarrega qualquer resto de delta antes de fechar
                            if part_buf:
                                yield json.dumps({"t": "partial", "txt": "".join(part_buf)}) + "\n"
                                part_buf = []
                            if spk is not None and spk_buf:
                                for e in spk.feed("".join(spk_buf)):
                                    yield json.dumps(e) + "\n"
                                spk_buf = []
                            reply = (ev.get("result") or "").strip()
                            yield dbg("ASK", f"result subtype={ev.get('subtype','')} dur={ev.get('duration_ms','?')}ms reply={len(reply)} chars")
                            break
                    if reply is None and reply_parts:
                        reply = "".join(reply_parts).strip()
                    yield dbg("ASK", f"persistente eventos={events} elapsed={time.time()-t0:.1f}s")
                except Exception as e:
                    yield dbg("ERR", "excecao no persistente: " + str(e))
                    kill_claude(sid)
                    reply = None

            if s.get("cancel_rev", 0) != turn_rev:
                if spk is not None:
                    spk.cancel()
                yield dbg("WARN", "turno cancelado")
                return

            # 3) fallback: conversa explícita por sid, nunca --continue global ao diretório
            if not reply:
                yield dbg("WARN", "fallback claude -p (persistente indisponivel)")
                yield json.dumps({"t": "step", "msg": "processando"}) + "\n"
                env = dict(os.environ, VOICE_HUB="1")
                resume = (s.get("cid") or "") if not s["fresh"] else ""
                fallback_cid = resume or str(uuid.uuid4())
                cont = (" --resume " + resume) if resume else (" --session-id " + fallback_cid)
                model_flag = f" --model {want}" if want else ""
                effort_flag = f" --effort {want_effort}" if want_effort else ""
                fb = "-p" + cont + PERMISSION_FLAG + model_flag + effort_flag
                p = None
                try:
                    with REG_LOCK:
                        if sum(1 for item in SESS.values() if item["proc"] is not None and item["proc"].poll() is None) >= MAX_SESS:
                            raise RuntimeError(f"limite de {MAX_SESS} sessoes simultaneas")
                        p = subprocess.Popen(bridge_command(shlex.split(fb)), stdin=subprocess.PIPE,
                                             stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                             cwd=str(PROJECT_ROOT), encoding="utf-8",
                                             shell=True, env=env)
                        s["proc"] = p
                    if s.get("cancel_rev", 0) != turn_rev:
                        _kill_tree(p)
                        return
                    try:
                        stdout, stderr = p.communicate(input=texto, timeout=FALLBACK_TIMEOUT)
                    except subprocess.TimeoutExpired:
                        _kill_tree(p)
                        p.communicate(timeout=10)
                        raise
                    if s.get("cancel_rev", 0) != turn_rev:
                        return
                    reply = (stdout or "").strip()
                    s["fresh"] = False
                    if p.returncode == 0:
                        s["cid"] = fallback_cid
                    if stderr:
                        yield dbg("ERR", "fallback stderr: " + stderr.strip()[:300])
                    yield dbg("ASK", f"fallback exit={p.returncode} reply_len={len(reply)}")
                except Exception as e:
                    reply = f"(erro ao chamar claude: {e})"
                    yield dbg("ERR", "fallback excecao: " + str(e))
                finally:
                    if p is not None:
                        if p.poll() is None:
                            _kill_tree(p)
                        if s.get("proc") is p:
                            s["proc"], s["q"] = None, None
                    if s.get("cancel_rev", 0) != turn_rev and spk is not None:
                        spk.cancel()


        if s.get("cancel_rev", 0) != turn_rev:
            if spk is not None:
                spk.cancel()
            return
        if not reply:
            reply = "(sem resposta)"
        stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        tag = f"[{titulo or sid}] "
        log_turn(stamp, tag, texto, reply)
        yield dbg("OK", "done enviado ao frontend")
        # `spoken`: a fala ja esta correndo por aqui -> o front nao chama /speak.
        # O done sai ANTES de esperar o fim da fala, senao a resposta so apareceria
        # na tela quando a voz terminasse.
        yield json.dumps({"t": "done", "reply": reply, "spoken": spk is not None}) + "\n"
        if spk is not None:
            for e in spk.close():
                yield json.dumps(e) + "\n"
        elif quer_falar:
            # fala classica no lugar do fallback /speak que o cliente nao tem;
            # os eventos saem por aqui e o espelho os leva a aba CELULAR.
            ev_q = queue.Queue()
            SPEAK_Q.put({"sid": sid, "reply": reply, "earcon_hz": body.get("earcon_hz"),
                         "announce": titulo, "events": ev_q})
            yield json.dumps({"t": "speak_queued", "pos": SPEAK_Q.qsize()}) + "\n"
            while True:
                e = ev_q.get()
                if e is None:
                    break
                yield json.dumps(e) + "\n"

    resp = Response(stream_with_context(_watched(sid, generate())), mimetype="application/x-ndjson")
    resp.headers["X-Accel-Buffering"] = "no"
    return resp


# ----------------------------------------------------------------------------
# Arbitro de fala (Fase 2) — fila UNICA + 1 worker. Como winsound.PlaySound
# (no speak_server.py) bloqueia ate tocar por inteiro, o worker so pega o
# proximo job quando o atual termina -> serializacao de graca, impossivel
# duas sessoes falarem ao mesmo tempo.
# ----------------------------------------------------------------------------
SPEAK_Q = queue.Queue()   # itens: {"sid","reply","earcon_hz","announce","events":Queue}
SPEAK_BUSY = threading.Event()   # um job de fala em andamento (segurado pelo worker)
# Torna atomico o "arbitro esta livre? entao abro streaming". Sem ele, N abas que
# passam do SPEAK_MIN no mesmo instante checam a fila vazia ANTES de qualquer uma
# enfileirar e abrem varios streamings de uma vez — e o canal de texto do Kokoro
# (STREAM/STREAM_END) e UNICO: o STREAM_END do job que ficou na fila corta a fala
# de quem esta no ar. Coberto por tests/test_concorrencia.py.
SPEAK_GATE = threading.Lock()


def _read_env():
    # O speak_server reescreve o envelope a cada trecho sintetizado (o audio nasce
    # em streaming), por isso ele e relido durante a fala, nao so no inicio.
    try:
        with open(ENVELOPE, "r", encoding="utf-8") as f:
            return json.load(f) or {}
    except Exception:
        return {}


def _do_speak(job):
    reply = job["reply"]
    events = job["events"]
    streaming = bool(job.get("stream"))
    t0 = time.time()
    for p in (STARTED, DONE, ENVELOPE, STREAM, STREAM_END):
        try:
            os.remove(p)
        except OSError:
            pass
    # Fase 3: grava o meta (earcon + anuncio) ANTES do REQ — o speak_server le
    # este arquivo assim que pega o pedido de fala.
    try:
        with open(META, "w", encoding="utf-8") as f:
            json.dump({"earcon_hz": job.get("earcon_hz"), "announce": job.get("announce") or ""}, f)
    except OSError:
        pass
    if streaming:
        # canal de texto zerado antes do pedido; o produtor (o /ask) faz append
        # nele conforme o Claude escreve, e so pode escrever depois do `go`.
        try:
            open(STREAM, "w", encoding="utf-8").close()
        except OSError:
            pass
    with open(REQ, "w", encoding="utf-8") as f:
        f.write("__stream__" if streaming else reply)
    if streaming:
        job["go"].set()
    # 1) espera a fala comecar. O speak_server so larga quando tem colchao de
    # audio para nao gaguejar (regra de largada), o que em resposta longa leva
    # a ordem de grandeza da propria fala — dai a janela larga aqui.
    waited = 0
    started = False
    while waited < 12000:
        if os.path.exists(STARTED):
            started = True
            break
        if os.path.exists(DONE):     # texto vazio/curto: terminou sem START
            break
        time.sleep(0.05)
        waited += 1
    env_sent = 0
    if started:
        env = _read_env()
        envelope, step_ms = env.get("levels"), env.get("step_ms")
        env_sent = len(envelope or [])
        events.put({"t": "speak_start", "start_ms": int((time.time() - t0) * 1000),
                    "ready": os.path.exists(READY), "envelope": envelope, "step_ms": step_ms})
    # 2) espera terminar de falar, repassando os niveis novos do envelope (o
    # audio segue sendo sintetizado enquanto a fala corre).
    waited = 0
    while not os.path.exists(DONE) and waited < 12000:
        time.sleep(0.05)
        waited += 1
        if started and waited % 10 == 0:
            lv = _read_env().get("levels") or []
            if len(lv) > env_sent:
                events.put({"t": "speak_env", "levels": lv[env_sent:]})
                env_sent = len(lv)
    done = os.path.exists(DONE)
    for p in (STARTED, DONE):
        try:
            os.remove(p)
        except OSError:
            pass
    events.put({
        "t": "speak_done",
        "ok": done,
        "ready": os.path.exists(READY),
        "started": started,
        "spoke_ms": int((time.time() - t0) * 1000),
        "chars": len(reply or ""),
        "timeout": (not done),
    })
    events.put(None)  # sentinela: fim do job


def speak_worker():
    while True:
        job = SPEAK_Q.get()
        SPEAK_BUSY.set()
        try:
            _do_speak(job)
        except Exception as e:
            job["events"].put({"t": "speak_done", "ok": False, "error": str(e)})
            job["events"].put(None)
        finally:
            SPEAK_BUSY.clear()


threading.Thread(target=speak_worker, daemon=True).start()


class SpeakStream:
    """Fala do turno alimentada em streaming, enquanto o Claude ainda escreve.

    Enfileira um job no MESMO arbitro das outras falas (nada de duas sessoes
    falando juntas) e, quando chega a vez dele, passa a escrever o texto em
    STREAM. Os eventos de fala saem pelo NDJSON do proprio /ask, porque aqui a
    fala comeca antes de o turno fechar.
    """

    def __init__(self, sid, titulo, earcon_hz):
        self.events = queue.Queue()
        self.go = threading.Event()   # o worker libera quando o job vira o atual
        self.buf = ""                 # texto retido enquanto o job aguarda a vez
        self.buf_lock = threading.Lock()   # feed() e watchdog descarregam o buf
        self.ended = False
        self.text_closed = False
        self.want_end = False         # quis fechar antes de ser dono do canal
        self.last = time.time()
        SPEAK_Q.put({"sid": sid, "reply": "", "earcon_hz": earcon_hz,
                     "announce": titulo, "events": self.events,
                     "stream": True, "go": self.go})
        threading.Thread(target=self._watchdog, daemon=True).start()

    def _mark_end(self):
        # STREAM_END e um arquivo UNICO, compartilhado por todas as sessoes. Um
        # job que ainda espera a vez (sem `go`) nunca escreveu no STREAM: o
        # STREAM_END dele fecharia o texto de OUTRA sessao, cortando a fala dela
        # no meio da frase. Quem ainda nao e dono do canal so registra a vontade
        # de fechar; o watchdog cumpre assim que o `go` chegar.
        if self.text_closed:
            return
        self.want_end = True
        if not self.go.is_set():
            return
        self.text_closed = True
        try:
            open(STREAM_END, "w").close()
        except OSError:
            pass

    def cancel(self):
        with self.buf_lock:
            self.buf = ""
        self._mark_end()

    def alive(self):
        """O turno segue vivo, mesmo sem texto novo (ferramenta longa, raciocinio).

        Adia a fome do watchdog. Sem isto, uma pausa de 45s no meio da resposta
        — um Bash demorado, um subagente — fechava o canal de texto: o Kokoro
        falava so o que tinha vindo ANTES da ferramenta e o resto, que costuma
        ser A RESPOSTA, saia na tela e nunca era falado (com o turno ainda se
        declarando `spoken`, entao nem o /speak do fim entrava no lugar).
        """
        self.last = time.time()

    def _watchdog(self):
        # Se o turno morre no meio (ESC, aba fechada), ninguem chama close() nem
        # alive() e o Kokoro ficaria esperando texto que nao vem — prendendo o
        # arbitro e emudecendo o turno seguinte. Turno vivo chama alive().
        self.go.wait()          # antes da vez dele, este job nao pode fechar nada
        while not self.text_closed:
            if time.time() - self.last > 45:
                # fome: o turno morreu. Descarrega o que ficou retido e fecha.
                self._flush()
                self._mark_end()
                return
            if self.want_end and not self.buf:
                # o close() quis fechar antes de este job ser dono do canal, e o
                # texto retido ja saiu: agora o fim pode ser marcado. Enquanto o
                # `buf` tiver texto, fechar marcaria o fim ANTES do texto sair.
                self._mark_end()
                return
            time.sleep(0.2)

    def _flush(self):
        """Escreve no canal o texto retido, se este job ja for o dono dele.

        Sob lock: o watchdog tambem descarrega o buffer (turno morto), e um
        `buf` lido por um lado e zerado pelo outro perderia texto.
        """
        with self.buf_lock:
            if self.buf and self.go.is_set():
                try:
                    with open(STREAM, "a", encoding="utf-8") as f:
                        f.write(self.buf)
                    self.buf = ""
                except OSError:
                    pass

    def feed(self, txt):
        """Entrega texto novo ao Kokoro; devolve os eventos de fala pendentes."""
        if txt:
            self.last = time.time()
        with self.buf_lock:
            self.buf += txt or ""
        self._flush()
        out = []
        while True:
            try:
                ev = self.events.get_nowait()
            except queue.Empty:
                break
            if ev is None:
                self.ended = True
                break
            out.append(ev)
        return out

    def close(self):
        """Fecha o texto e cede os eventos ate a fala terminar."""
        self.go.wait(timeout=120)     # sem isso o fim marcaria antes do texto sair
        for ev in self.feed(""):
            yield ev
        self._mark_end()
        while not self.ended:
            ev = self.events.get()
            if ev is None:
                break
            yield ev


def try_speak_stream(sid, titulo, earcon_hz):
    """Abre a fala em streaming SE o arbitro estiver livre. None = ocupado.

    A checagem e o enfileiramento andam juntos sob o SPEAK_GATE: sao um passo
    so, ou N abas que passam do SPEAK_MIN ao mesmo tempo veem a fila vazia antes
    de qualquer uma enfileirar e abrem varios streamings sobre o mesmo canal de
    texto. Quem nao entra aqui cai no /speak classico do fim do turno.
    """
    with SPEAK_GATE:
        if not SPEAK_Q.empty() or SPEAK_BUSY.is_set():
            return None
        return SpeakStream(sid, titulo, earcon_hz)


@app.route("/speak", methods=["POST"])
def speak():
    # Resposta NDJSON em streaming: `speak_queued` (posicao na fila do arbitro),
    # `speak_start` quando o audio COMECA de fato (sentinela STARTED do
    # speak_server) e `speak_done` ao terminar. O frontend so acende "FALANDO"
    # quando a voz inicia de fato.
    body = request.get_json(silent=True) or {}
    reply = body.get("reply", "")
    sid = (body.get("sid") or "").strip() or DEFAULT_SID
    titulo = (body.get("titulo", "") or "").strip()
    earcon_hz = body.get("earcon_hz")
    events = queue.Queue()
    job = {"sid": sid, "reply": reply, "earcon_hz": earcon_hz, "announce": titulo, "events": events}
    SPEAK_Q.put(job)
    pos = SPEAK_Q.qsize()

    def generate():
        yield json.dumps({"t": "speak_queued", "pos": pos}) + "\n"
        while True:
            ev = events.get()
            if ev is None:
                break
            yield json.dumps(ev) + "\n"

    resp = Response(stream_with_context(_watched(sid, generate())), mimetype="application/x-ndjson")
    resp.headers["X-Accel-Buffering"] = "no"
    return resp


if __name__ == "__main__":
    with hold_instance("bridge", timeout=0):
        start_speak_server()
        try:
            if AUTOQUIT:
                threading.Thread(target=_hud_watchdog, daemon=True).start()
            app.run(host="127.0.0.1", port=PORT, threaded=True)
        finally:
            _shutdown()
