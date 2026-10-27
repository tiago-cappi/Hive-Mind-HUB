"""Testes de N sessoes simultaneas disputando os recursos unicos do Hub.

O Hub deixa ate MAX_SESS abas pensando em paralelo, cada uma com seu processo
`claude`. Tres recursos sao UNICOS e precisam sobreviver a isso:

  1. O ARBITRO DE FALA (`SPEAK_Q` + 1 worker) — duas abas nao podem falar por
     cima uma da outra. Cinco sessoes pedem fala juntas; o teste verifica que as
     janelas [start, done] nao se sobrepoem e que nenhum anuncio se perde.
  2. O CANAL DE TEXTO do Kokoro (`STREAM`/`STREAM_END`) — tambem e um so. Duas
     sessoes que abrem streaming juntas (TOCTOU no gate) disputam o mesmo canal,
     e o `STREAM_END` da que ficou na fila CORTA a fala da que esta no ar. Dai o
     `SPEAK_GATE` e a regra de que so o dono do canal marca o fim.
  3. O TRANSCRIPT `_agentes/voice-hub.md` — todo turno de toda sessao da append
     no MESMO arquivo. Sem `LOG_LOCK`, o append do CRT no Windows (seek + write
     em duas etapas) faz uma sessao sobrescrever a outra e o turno some.

O quarto recurso disputado sao os ARQUIVOS DO VAULT, e esse nao da para testar
daqui: quem escreve sao os processos `claude`. A guarda dele vive no vault
(`<vault>/.claude/hooks/file_guard.py`), com teste proprio
(`python .claude/hooks/test_file_guard.py`). Ver `docs/servidor-api.md` §3.4.

Nada de Kokoro nem de audio: o speak_server e substituido por um duble e as
constantes do protocolo apontam para arquivos tconc_* em %TEMP%.
Rodar: python -m pytest tests/test_concorrencia.py -q
"""
import json
import os
import sys
import tempfile
import threading
import time

import pytest

import server as S

TMP = tempfile.gettempdir()
PATHS = ("REQ", "STREAM", "STREAM_END", "STARTED", "DONE", "ENVELOPE", "META", "READY")


def _rm(*ps):
    for p in ps:
        try:
            os.remove(p)
        except OSError:
            pass


@pytest.fixture
def protocolo():
    """Redireciona o protocolo de fala para arquivos de teste e restaura no fim."""
    orig = {n: getattr(S, n) for n in PATHS}
    for n in orig:
        setattr(S, n, os.path.join(TMP, "tconc_" + n.lower() + ".txt"))
    _rm(*[getattr(S, n) for n in PATHS])
    open(S.READY, "w").close()
    yield
    _rm(*[getattr(S, n) for n in PATHS])
    for n, v in orig.items():
        setattr(S, n, v)


def _fake_kokoro(n_jobs, log, stop, sintese=0.08, audio=0.20):
    """Duble do speak_server: atende n_jobs pedidos, um por vez, e cronometra."""
    atendidos = 0
    while atendidos < n_jobs and not stop.is_set():
        if not os.path.exists(S.REQ):
            time.sleep(0.01)
            continue
        try:
            with open(S.META, "r", encoding="utf-8") as f:
                who = (json.load(f) or {}).get("announce") or "?"
        except Exception:
            who = "?"
        time.sleep(sintese)                      # sintetizando
        with open(S.ENVELOPE, "w", encoding="utf-8") as f:
            json.dump({"step_ms": 40, "levels": [0.5] * 8}, f)
        open(S.STARTED, "w").close()
        log.append(("start", who, time.time()))
        time.sleep(audio)                        # tocando (sd.wait() bloqueia)
        log.append(("done", who, time.time()))
        _rm(S.REQ, S.META)                       # ordem do protocolo: REQ/META antes do DONE
        open(S.DONE, "w").close()
        atendidos += 1
        while os.path.exists(S.DONE) and not stop.is_set():
            time.sleep(0.01)                     # espera o server consumir o DONE


def test_cinco_sessoes_nao_falam_por_cima_uma_da_outra(protocolo):
    n = 5
    log, stop = [], threading.Event()
    duble = threading.Thread(target=_fake_kokoro, args=(n, log, stop), daemon=True)
    duble.start()

    filas = []
    for i in range(1, n + 1):
        ev = __import__("queue").Queue()
        filas.append((f"Sessao {i}", ev))

    # as 5 abas pedem fala PRATICAMENTE ao mesmo tempo
    def pedir(titulo, ev):
        S.SPEAK_Q.put({"sid": titulo, "reply": f"resposta da {titulo}",
                       "earcon_hz": 440, "announce": titulo, "events": ev})

    ths = [threading.Thread(target=pedir, args=(t, e)) for t, e in filas]
    for t in ths:
        t.start()
    for t in ths:
        t.join()

    # coleta os eventos de cada pedido
    resultados = {}
    for titulo, ev in filas:
        evs = []
        while True:
            item = ev.get(timeout=30)
            if item is None:
                break
            evs.append(item)
        resultados[titulo] = evs
    stop.set()

    # todo mundo falou, e falou de verdade (STARTED chegou)
    for titulo, evs in resultados.items():
        done = [e for e in evs if e["t"] == "speak_done"]
        assert done, f"{titulo} nunca recebeu speak_done"
        assert done[0]["ok"] is True, f"{titulo}: speak_done ok=False -> {done[0]}"
        assert done[0]["started"] is True, f"{titulo}: falou sem STARTED (audio mudo)"
        assert any(e["t"] == "speak_start" for e in evs), f"{titulo} sem speak_start"

    # nenhum anuncio se perdeu nem foi duplicado
    anunciados = [w for (k, w, _) in log if k == "start"]
    assert sorted(anunciados) == sorted(t for t, _ in filas), f"anuncios: {anunciados}"

    # e o essencial: as janelas de audio NAO se sobrepoem
    janelas = {}
    for kind, who, ts in log:
        janelas.setdefault(who, {})[kind] = ts
    ordenadas = sorted(((v["start"], v["done"], w) for w, v in janelas.items()))
    for (s1, d1, w1), (s2, d2, w2) in zip(ordenadas, ordenadas[1:]):
        assert s2 >= d1, f"{w2} comecou a falar antes de {w1} terminar (sobreposicao)"


def test_so_uma_sessao_abre_fala_em_streaming(protocolo, monkeypatch):
    """N abas passam do SPEAK_MIN no mesmo instante: so UMA pode abrir streaming.

    O canal de texto do Kokoro (STREAM/STREAM_END) e unico. Se duas sessoes
    abrem streaming juntas, a que ficou na fila fecha o canal (watchdog de fome
    ou close()) e CORTA a fala da que esta no ar. `try_speak_stream` faz a
    checagem e o enfileiramento sob o SPEAK_GATE, num passo so.

    `setswitchinterval` bem baixo expoe a janela: sem o gate, o mesmo teste
    deixa 4 a 6 sessoes passarem.
    """
    import queue as Q
    monkeypatch.setattr(S, "SPEAK_Q", Q.Queue())      # worker fora do caminho: os jobs ficam na fila
    orig_switch = sys.getswitchinterval()
    sys.setswitchinterval(1e-6)
    try:
        n, pior = 8, 0
        for _ in range(10):
            monkeypatch.setattr(S, "SPEAK_Q", Q.Queue())
            S.SPEAK_BUSY.clear()
            abertos, trava = [], threading.Lock()
            barreira = threading.Barrier(n)

            def tenta(i):
                barreira.wait()
                spk = S.try_speak_stream(f"s{i}", f"Sessao {i}", 440)
                if spk is not None:
                    with trava:
                        abertos.append(i)

            ths = [threading.Thread(target=tenta, args=(i,)) for i in range(n)]
            for t in ths:
                t.start()
            for t in ths:
                t.join()
            pior = max(pior, len(abertos))
            assert len(abertos) == 1, (
                f"{len(abertos)} sessoes abriram streaming sobre o mesmo canal "
                f"de texto: {abertos}")
        assert pior == 1
    finally:
        sys.setswitchinterval(orig_switch)


def test_job_na_fila_nao_corta_a_fala_de_quem_esta_no_ar(protocolo, monkeypatch):
    """O STREAM_END de um job que ainda espera a vez nao pode fechar o canal.

    Cenario: a sessao A esta falando; a B enfileirou um streaming e seu turno
    morre (ESC, aba fechada) — o watchdog de fome de B dispara. Se B gravasse o
    STREAM_END, o Kokoro pararia de ler o texto de A no meio da frase.
    """
    import queue as Q
    monkeypatch.setattr(S, "SPEAK_Q", Q.Queue())

    b = S.SpeakStream("sB", "Sessao B", 440)   # B entra na fila e NAO recebe o `go`
    assert not b.go.is_set()

    b.last = 0                                 # simula 45 s sem texto novo
    b._mark_end()                              # o que o watchdog faria

    assert not os.path.exists(S.STREAM_END), (
        "um job que ainda espera a vez fechou o canal de texto -> cortaria a "
        "fala da sessao que esta no ar")
    assert b.want_end is True                  # a vontade de fechar fica registrada
    assert b.text_closed is False

    # quando enfim vira o job atual, o fim pendente e cumprido
    b.go.set()
    b._mark_end()
    assert os.path.exists(S.STREAM_END)
    assert b.text_closed is True


def test_texto_retido_sai_antes_do_fim_do_canal(protocolo, monkeypatch):
    """B espera a vez com texto no buffer: o fim so pode vir DEPOIS do texto.

    Se o STREAM_END fosse marcado antes do `_flush`, o Kokoro leria o canal
    achando que a resposta terminou e falaria um pedaco da frase — ou nada.
    """
    import queue as Q
    monkeypatch.setattr(S, "SPEAK_Q", Q.Queue())

    b = S.SpeakStream("sB", "Sessao B", 440)
    b.feed("Texto que chegou enquanto a outra sessao ainda falava. ")
    assert b.buf, "sem o `go`, o texto tem de ficar retido, nao ir para o canal"
    assert not os.path.exists(S.STREAM), "escreveu no canal antes da vez"

    b.want_end = True          # o close() ja quis fechar, mas B nao era dono
    b.go.set()                 # chegou a vez de B
    open(S.STREAM, "w").close()

    b._flush()                 # o que o watchdog/close fazem ao assumir o canal
    b._mark_end()

    with open(S.STREAM, encoding="utf-8") as f:
        assert "Texto que chegou" in f.read(), "o texto retido nao chegou ao canal"
    assert os.path.exists(S.STREAM_END)
    assert not b.buf


def test_transcript_nao_corrompe_com_sessoes_simultaneas(tmp_path, monkeypatch):
    """Cinco sessoes gravando turnos longos no MESMO voice-hub.md ao mesmo tempo.

    Chama o mesmo S.log_turn() que o /ask usa. Cada
    sessao escreve linhas feitas de UM unico caractere; se duas escritas
    intercalarem, uma linha sai com caracteres de duas sessoes.
    """
    log = tmp_path / "voice-hub.md"
    monkeypatch.setattr(S, "LOG", str(log))

    # marcas fora do texto fixo do cabecalho ("Sessao", "EU", "CLAUDE", stamp),
    # senao a busca acusa corrupcao onde so ha as proprias palavras da linha.
    marcas = "qwxyz"
    turnos = 12
    reply_len = 60000        # resposta longa: estoura o buffer de 8 KB do modo texto

    def sessao(marca):
        for _ in range(turnos):
            S.log_turn("2026-08-26 12:00:00", f"[Sessao {marca}] ",
                       marca * 200, marca * reply_len)

    ths = [threading.Thread(target=sessao, args=(m,)) for m in marcas]
    for t in ths:
        t.start()
    for t in ths:
        t.join()

    conteudo = log.read_text(encoding="utf-8")
    esperado = turnos * len(marcas)

    # 1) NENHUM turno pode sumir. Este e o modo de falha real no Windows: o
    # modo append do CRT faz seek-para-o-fim + write em duas etapas, entao duas
    # sessoes que abrem o arquivo juntas apontam para o MESMO offset e a segunda
    # escreve por cima da primeira. Sem o LOG_LOCK isto da 58/60, 59/60...
    assert conteudo.count("CLAUDE:**") == esperado, (
        f"turnos perdidos no transcript: {conteudo.count('CLAUDE:**')}/{esperado} "
        f"(sessao sobrescrita por outra)")
    assert conteudo.count("EU:**") == esperado

    # 2) e nenhuma linha pode misturar duas sessoes (intercalacao de buffers)
    corrompidas = []
    for i, linha in enumerate(conteudo.splitlines()):
        if not linha.strip():
            continue
        presentes = {m for m in marcas if m in linha}
        if len(presentes) > 1:
            corrompidas.append((i, sorted(presentes), len(linha)))
    assert not corrompidas, (
        f"{len(corrompidas)} linhas do transcript misturam sessoes; "
        f"primeiras: {corrompidas[:3]}")
