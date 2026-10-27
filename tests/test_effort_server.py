"""Testes do eixo de esforco no servidor (F3 / ISS-002).

Cobre: spawn_claude monta --effort so quando o nivel e valido; /session_start
e /session_reset repassam esforco a spawn_claude; /ask honra esforco em sessao
nova, reinicia o processo quando SO o esforco muda (mantendo o modelo), tolera
payload antigo sem o campo e ignora nivel invalido; o fallback (claude -p sem
processo persistente) tambem inclui --effort quando aplicavel.

Mocka subprocess.Popen/subprocess.run — nenhum processo `claude` real e
lancado. Stuba faster_whisper (server.py carrega o modelo no import).

Rodar:  python -m pytest tests/test_effort_server.py -q
"""
import sys
import types
import queue as queue_mod
from unittest.mock import patch

# --- stub do faster_whisper: server.py faz WMODEL = WhisperModel(...) no import ---
_fw = types.ModuleType("faster_whisper")
_fw.WhisperModel = lambda *a, **k: object()
sys.modules.setdefault("faster_whisper", _fw)

import server  # noqa: E402


class FakeStdin:
    def __init__(self):
        self.written = []

    def write(self, s):
        self.written.append(s)

    def flush(self):
        pass


class FakeProc:
    """Processo persistente falso: stdout/stderr vazios -> o loop do /ask
    recebe o sentinela `_end` de imediato e nao bloqueia esperando saida real."""

    def __init__(self):
        self._alive = True
        self.returncode = 0
        self.stdin = FakeStdin()
        self.stdout = iter([])
        self.stderr = iter([])

    def poll(self):
        return None if self._alive else 0

    def kill(self):
        self._alive = False


    def communicate(self, input=None, timeout=None):
        self._alive = False
        return "resposta fallback", ""


class FakeCompleted:
    def __init__(self, stdout="resposta fallback", stderr="", returncode=0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode

    def communicate(self, input=None, timeout=None):
        return self.stdout, self.stderr

    def poll(self):
        return self.returncode


def _clear_sess():
    with server.REG_LOCK:
        server.SESS.clear()


def _consume(resp):
    # drena o generator NDJSON da rota de streaming (test client nao streama
    # de verdade sobre rede; iterar o response ja executa o generator inteiro).
    return b"".join(resp.response).decode("utf-8", "replace")


# ------------------------- spawn_claude (ISS-002.1) --------------------------
def test_spawn_claude_adiciona_effort_quando_valido():
    _clear_sess()
    captured = {}

    def fake_popen(cmd, **kw):
        captured["cmd"] = cmd
        return FakeProc()

    with patch.object(server.subprocess, "Popen", side_effect=fake_popen):
        server.spawn_claude("sid-a", "", "high")
    assert "--effort high" in captured["cmd"]
    assert server.SESS["sid-a"]["effort"] == "high"


def test_spawn_claude_omite_effort_quando_invalido_ou_vazio():
    _clear_sess()
    captured = {}

    def fake_popen(cmd, **kw):
        captured["cmd"] = cmd
        return FakeProc()

    with patch.object(server.subprocess, "Popen", side_effect=fake_popen):
        server.spawn_claude("sid-b", "", "ultra")
    assert "--effort" not in captured["cmd"]
    assert server.SESS["sid-b"]["effort"] == ""

    with patch.object(server.subprocess, "Popen", side_effect=fake_popen):
        server.spawn_claude("sid-b", "", "")
    assert "--effort" not in captured["cmd"]


# ------------------- /session_start e /session_reset (ISS-002) ---------------
def test_session_start_repassa_esforco_a_spawn_claude():
    _clear_sess()
    client = server.app.test_client()
    with patch.object(server, "spawn_claude", wraps=server.spawn_claude) as spy, \
         patch.object(server.subprocess, "Popen", return_value=FakeProc()):
        r = client.post("/session_start", json={"sid": "ss1", "modelo": "", "esforco": "medium"})
    assert r.status_code == 200
    spy.assert_called_once_with("ss1", "", "medium")
    assert server.SESS["ss1"]["effort"] == "medium"


def test_session_reset_repassa_esforco_a_spawn_claude():
    _clear_sess()
    client = server.app.test_client()
    with patch.object(server, "spawn_claude", wraps=server.spawn_claude) as spy, \
         patch.object(server.subprocess, "Popen", return_value=FakeProc()):
        r = client.post("/session_reset", json={"sid": "sr1", "modelo": "", "esforco": "xhigh"})
    assert r.status_code == 200
    spy.assert_called_once_with("sr1", "", "xhigh")
    assert server.SESS["sr1"]["effort"] == "xhigh"


# ------------------------------ /ask (ISS-002) --------------------------------
def test_ask_sessao_nova_sobe_processo_com_effort_pedido():
    _clear_sess()
    client = server.app.test_client()
    with patch.object(server.subprocess, "Popen", return_value=FakeProc()), \
         patch.object(server.subprocess, "run", return_value=FakeCompleted()):
        r = client.post("/ask", json={"texto": "oi", "modelo": "", "esforco": "high", "sid": "news1"})
        body = _consume(r)
    assert "claude persistente iniciado" in body
    assert server.SESS["news1"]["effort"] == "high"


def test_ask_troca_so_o_esforco_reinicia_processo_e_mantem_modelo():
    _clear_sess()
    sid = "swap1"
    s = server.get_sess(sid)
    s["proc"], s["model"], s["effort"], s["q"] = FakeProc(), "", "low", queue_mod.Queue()
    client = server.app.test_client()
    with patch.object(server.subprocess, "Popen", return_value=FakeProc()), \
         patch.object(server.subprocess, "run", return_value=FakeCompleted()):
        r = client.post("/ask", json={"texto": "oi", "modelo": "", "esforco": "high", "sid": sid})
        body = _consume(r)
    assert "reiniciando claude" in body
    assert "low" in body and "high" in body
    assert server.SESS[sid]["effort"] == "high"
    assert server.SESS[sid]["model"] == ""


def test_ask_payload_antigo_sem_esforco_nao_quebra():
    _clear_sess()
    client = server.app.test_client()
    with patch.object(server.subprocess, "Popen", return_value=FakeProc()), \
         patch.object(server.subprocess, "run", return_value=FakeCompleted()):
        r = client.post("/ask", json={"texto": "oi", "modelo": "", "sid": "old1"})
        body = _consume(r)
    assert r.status_code == 200
    assert '"t": "done"' in body or '"t":"done"' in body
    assert server.SESS["old1"]["effort"] == ""


def test_ask_esforco_invalido_e_ignorado_sem_erro():
    _clear_sess()
    client = server.app.test_client()
    with patch.object(server.subprocess, "Popen", return_value=FakeProc()), \
         patch.object(server.subprocess, "run", return_value=FakeCompleted()):
        r = client.post("/ask", json={"texto": "oi", "modelo": "", "esforco": "ultra", "sid": "inv1"})
        body = _consume(r)
    assert r.status_code == 200
    assert server.SESS["inv1"]["effort"] == ""


def test_ask_fallback_inclui_effort_quando_valido():
    _clear_sess()
    client = server.app.test_client()
    captured = {}

    def fake_run(cmd, **kw):
        captured["cmd"] = cmd
        return FakeCompleted()

    # forca o caminho de fallback: spawn_claude sempre falha -> nunca fica "alive"
    with patch.object(server, "spawn_claude", side_effect=RuntimeError("sem claude no ambiente de teste")), \
         patch.object(server.subprocess, "Popen", side_effect=fake_run):
        r = client.post("/ask", json={"texto": "oi", "modelo": "", "esforco": "max", "sid": "fb1"})
        body = _consume(r)
    assert "--effort max" in captured["cmd"]
    assert "resposta fallback" in body


def test_ask_fallback_omite_effort_quando_invalido():
    _clear_sess()
    client = server.app.test_client()
    captured = {}

    def fake_run(cmd, **kw):
        captured["cmd"] = cmd
        return FakeCompleted()

    with patch.object(server, "spawn_claude", side_effect=RuntimeError("sem claude no ambiente de teste")), \
         patch.object(server.subprocess, "Popen", side_effect=fake_run):
        r = client.post("/ask", json={"texto": "oi", "modelo": "", "esforco": "nope", "sid": "fb2"})
        _consume(r)
    assert "--effort" not in captured["cmd"]
