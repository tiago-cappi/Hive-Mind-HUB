"""Testes da rota de STT (`POST /stt`) — isolamento por sessao e guarda do modelo.

Contexto: um turno de voz de 4min42 deixou o HUD em PROCESSANDO por ~13min sem
transcript e sem resposta. O turno morreu DENTRO do /stt: a rota e sincrona, o
faster-whisper roda na CPU abaixo do tempo real e nada do lado do servidor
protegia o recurso compartilhado.

Cobre o que mudou aqui:
  - o audio vai para um arquivo POR SID (antes: um unico hub_stt_in.webm global,
    em que duas abas gravando juntas se sobrescreviam);
  - `sid` e opcional — quem chamava a rota sem ele continua funcionando;
  - o sid e sanitizado (nada de path traversal vindo do nome da aba);
  - a transcricao corre sob a guarda nomeada STT_LOCK (regra 5 do CLAUDE.md):
    o WMODEL e um so e o faster-whisper nao e thread-safe num Flask threaded;
  - o `join` do generator acontece DENTRO do lock (o trabalho do faster-whisper
    e na iteracao, nao na chamada de transcribe()).

Stuba faster_whisper (server.py carrega o modelo no import) — nenhum modelo real
e baixado e nenhum audio de verdade e transcrito.

Rodar:  python -m pytest tests/test_stt.py -q
"""
import io
import os
import sys
import glob
import types
import shutil
import tempfile
import threading
from unittest.mock import patch

# --- stub do faster_whisper: server.py faz WMODEL = WhisperModel(...) no import ---
_fw = types.ModuleType("faster_whisper")
_fw.WhisperModel = lambda *a, **k: object()
sys.modules.setdefault("faster_whisper", _fw)

import server  # noqa: E402


class _Seg:
    def __init__(self, text):
        self.text = text


class FakeWhisper:
    """Dubla o WMODEL. `transcribe` devolve um GENERATOR, como o de verdade —
    o trabalho so acontece na iteracao, e e isso que o lock precisa cobrir."""

    def __init__(self, texto="ola mundo", on_iter=None):
        self.texto = texto
        self.on_iter = on_iter
        self.paths = []

    def transcribe(self, path, **kw):
        self.paths.append(path)

        def gen():
            if self.on_iter:
                self.on_iter()
            yield _Seg(self.texto)

        return gen(), None


class TempSttDir:
    """STT_DIR temporario + limpeza garantida (nao suja o %TEMP% real)."""

    def __enter__(self):
        self.dir = tempfile.mkdtemp(prefix="hub_stt_test_")
        self.patcher = patch.object(server, "STT_DIR", self.dir)
        self.patcher.start()
        return self.dir

    def __exit__(self, *exc):
        self.patcher.stop()
        shutil.rmtree(self.dir, ignore_errors=True)
        return False


def _post(client, sid=None, blob=b"audio-falso"):
    data = {"audio": (io.BytesIO(blob), "a.webm")}
    if sid is not None:
        data["sid"] = sid
    return client.post("/stt", data=data, content_type="multipart/form-data")


# ----------------------------- caminho feliz ---------------------------------
def test_transcreve_e_devolve_o_texto():
    fake = FakeWhisper("bom dia")
    with TempSttDir(), patch.object(server, "WMODEL", fake):
        r = _post(server.app.test_client(), sid="aba1")
    assert r.status_code == 200
    assert r.get_json() == {"texto": "bom dia"}


def test_sem_audio_devolve_texto_vazio_sem_erro():
    with TempSttDir():
        r = server.app.test_client().post("/stt")
    assert r.status_code == 200
    assert r.get_json() == {"texto": ""}


# --------------------- 1 arquivo por sid (era 1 global) ----------------------
def test_cada_sid_grava_no_proprio_arquivo():
    fake = FakeWhisper()
    with TempSttDir() as d, patch.object(server, "WMODEL", fake):
        client = server.app.test_client()
        _post(client, sid="aba1", blob=b"primeiro")
        _post(client, sid="aba2", blob=b"segundo")
        nomes = sorted(os.path.basename(p) for p in glob.glob(os.path.join(d, "*.webm")))
        assert nomes == ["hub_stt_in_aba1.webm", "hub_stt_in_aba2.webm"]
        # o audio de uma aba NAO foi sobrescrito pelo da outra
        with open(os.path.join(d, "hub_stt_in_aba1.webm"), "rb") as fh:
            assert fh.read() == b"primeiro"
    # cada transcricao leu o arquivo da sua propria sessao
    assert fake.paths[0].endswith("hub_stt_in_aba1.webm")
    assert fake.paths[1].endswith("hub_stt_in_aba2.webm")


def test_sid_ausente_cai_no_default_sem_quebrar():
    fake = FakeWhisper()
    with TempSttDir(), patch.object(server, "WMODEL", fake):
        r = _post(server.app.test_client())          # sem campo `sid`
    assert r.status_code == 200
    assert fake.paths[0].endswith("hub_stt_in_%s.webm" % server.DEFAULT_SID)


def test_sid_hostil_e_sanitizado_e_nao_escapa_da_pasta():
    fake = FakeWhisper()
    with TempSttDir() as d, patch.object(server, "WMODEL", fake):
        _post(server.app.test_client(), sid="../../etc/passwd")
    destino = fake.paths[0]
    assert os.path.dirname(os.path.abspath(destino)) == os.path.abspath(d)
    assert ".." not in os.path.basename(destino)


def test_sid_muito_longo_nao_estoura_o_nome_do_arquivo():
    fake = FakeWhisper()
    with TempSttDir(), patch.object(server, "WMODEL", fake):
        _post(server.app.test_client(), sid="x" * 300)
    assert len(os.path.basename(fake.paths[0])) < 80


# ------------------- guarda nomeada do WMODEL (regra 5) ----------------------
def test_transcricoes_simultaneas_sao_serializadas_pelo_stt_lock():
    """Duas sessoes transcrevendo ao mesmo tempo nao podem entrar juntas no
    WMODEL: o faster-whisper nao e thread-safe e o Flask e threaded=True."""
    dentro = []
    pico = [0]
    trava = threading.Lock()

    def on_iter():
        with trava:
            dentro.append(1)
            pico[0] = max(pico[0], len(dentro))
        # janela larga o bastante para a outra thread tentar entrar
        import time
        time.sleep(0.05)
        with trava:
            dentro.pop()

    fake = FakeWhisper(on_iter=on_iter)
    with TempSttDir(), patch.object(server, "WMODEL", fake):
        client = server.app.test_client()
        erros = []

        def bate(sid):
            try:
                assert _post(client, sid=sid).status_code == 200
            except Exception as e:      # pragma: no cover - so aparece se quebrar
                erros.append(e)

        ts = [threading.Thread(target=bate, args=("aba%d" % i,)) for i in range(4)]
        for t in ts:
            t.start()
        for t in ts:
            t.join(timeout=15)

    assert not erros
    assert pico[0] == 1, "duas transcricoes entraram no WMODEL ao mesmo tempo"


def test_o_join_do_generator_acontece_dentro_do_lock():
    """O trabalho do faster-whisper e na ITERACAO. Se o lock cobrisse so a
    chamada de transcribe(), a serializacao seria fake."""
    estado = {"preso": False}

    def on_iter():
        estado["preso"] = not server.STT_LOCK.acquire(blocking=False)
        if not estado["preso"]:
            server.STT_LOCK.release()

    fake = FakeWhisper(on_iter=on_iter)
    with TempSttDir(), patch.object(server, "WMODEL", fake):
        _post(server.app.test_client(), sid="aba1")
    assert estado["preso"], "a iteracao do generator rodou fora do STT_LOCK"


# --------------------------- padrao do modelo --------------------------------
def test_modelo_padrao_e_base():
    """`small` roda a 0.37x o tempo real nesta maquina e transcreve pior que o
    `base` (0.72x). Trocar o padrao foi a correcao de menor custo."""
    assert os.environ.get("HUB_WHISPER") or server.WHISPER_MODEL == "base"
