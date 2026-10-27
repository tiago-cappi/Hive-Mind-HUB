"""Testes do watchdog de ociosidade do /ask e do cancelamento manual.

Contexto: o teto unico de 90s de silencio matava o processo persistente no meio
de trabalho legitimo (um subagente Sonnet passa minutos sem emitir evento). O
teto agora depende do que o turno estava fazendo quando calou, e o CANCELAR do
front derruba o turno no servidor em vez de so' fechar a escuta do fetch.

Cobre: inact_limit (as tres faixas), /abort (mata o processo mas mantem o sid
no registro, ao contrario de /session_end) e os pontos do front que consomem o
`limit_s` do heartbeat.

Rodar:  python -m pytest tests/test_watchdog.py -q
"""
import re
import sys
import types
from pathlib import Path
from unittest.mock import patch

_fw = types.ModuleType("faster_whisper")
_fw.WhisperModel = lambda *a, **k: object()
sys.modules.setdefault("faster_whisper", _fw)

import server  # noqa: E402

INDEX = (Path(__file__).resolve().parent.parent / "index.html").read_text(encoding="utf-8")


class FakeProc:
    def __init__(self):
        self._alive = True
        self.stdin, self.stdout, self.stderr = None, iter([]), iter([])

    def poll(self):
        return None if self._alive else 0

    def kill(self):
        self._alive = False


def _clear_sess():
    with server.REG_LOCK:
        server.SESS.clear()


# ------------------------------- inact_limit ---------------------------------
def test_ferramenta_aberta_ganha_o_teto_longo():
    limit, why = server.inact_limit("Agent", 12)
    assert limit == server.INACT_TOOL
    assert "Agent" in why


def test_sem_nenhum_evento_usa_o_teto_curto():
    limit, why = server.inact_limit("", 0)
    assert limit == server.INACT_BOOT
    assert "nenhum evento" in why


def test_ocioso_com_eventos_e_sem_ferramenta_fica_no_meio():
    limit, _ = server.inact_limit("", 5)
    assert limit == server.INACT_IDLE
    assert server.INACT_BOOT < server.INACT_IDLE < server.INACT_TOOL


def test_teto_longo_cobre_um_subagente_demorado():
    # a regressao que originou tudo isto: 90s nao cobria um Agent de minutos.
    limit, _ = server.inact_limit("Agent", 3)
    assert limit >= 600


# ---------------------------------- /abort -----------------------------------
def test_abort_mata_o_processo_e_mantem_a_sessao_registrada():
    _clear_sess()
    with patch.object(server.subprocess, "Popen", side_effect=lambda *a, **k: FakeProc()):
        server.spawn_claude("sid-x", "", "")
    assert server.claude_alive("sid-x")

    r = server.app.test_client().post("/abort", json={"sid": "sid-x"})
    assert r.status_code == 200
    assert r.get_json()["alive"] is False
    assert not server.claude_alive("sid-x")
    # ao contrario do /session_end, o registro do sid continua (a aba segue viva)
    assert "sid-x" in server.SESS


def test_abort_de_sid_desconhecido_nao_explode():
    _clear_sess()
    r = server.app.test_client().post("/abort", json={"sid": "nao-existe"})
    assert r.status_code == 200
    assert r.get_json()["ok"] is True


def test_session_end_continua_removendo_o_registro():
    _clear_sess()
    with patch.object(server.subprocess, "Popen", side_effect=lambda *a, **k: FakeProc()):
        server.spawn_claude("sid-y", "", "")
    server.app.test_client().post("/session_end", json={"sid": "sid-y"})
    assert "sid-y" not in server.SESS


# ------------------------------- kill em arvore -------------------------------
def test_kill_claude_derruba_a_arvore_no_windows():
    # spawn_claude usa shell=True: o Popen e' o cmd.exe e o `claude` e' filho.
    # matar so o Popen deixava o claude orfao editando arquivos.
    _clear_sess()
    with patch.object(server.subprocess, "Popen", side_effect=lambda *a, **k: FakeProc()):
        server.spawn_claude("sid-t", "", "")
    proc = server.SESS["sid-t"]["proc"]
    proc.pid = 4242
    with patch.object(server.os, "name", "nt"),          patch.object(server.subprocess, "run") as run:
        server.kill_claude("sid-t")
    assert run.called, "nao chamou taskkill"
    argv = run.call_args[0][0]
    assert argv[:2] == ["taskkill", "/PID"] and "/T" in argv and "/F" in argv
    assert "4242" in argv
    assert proc.poll() is not None, "o proprio Popen tambem tem de morrer"


def test_kill_claude_fora_do_windows_so_mata_o_processo():
    _clear_sess()
    with patch.object(server.subprocess, "Popen", side_effect=lambda *a, **k: FakeProc()):
        server.spawn_claude("sid-u", "", "")
    proc = server.SESS["sid-u"]["proc"]
    with patch.object(server.os, "name", "posix"),          patch.object(server.subprocess, "run") as run:
        server.kill_claude("sid-u")
    assert not run.called
    assert proc.poll() is not None


# ------------------------------- front (estatico) -----------------------------
def test_heartbeat_do_servidor_carrega_teto_e_ferramenta():
    src = (Path(__file__).resolve().parent.parent / "server.py").read_text(encoding="utf-8")
    assert '"limit_s": limit, "tool": open_tool' in src


def test_front_pinta_o_watchdog_em_fracao_do_teto():
    assert "tab.idleLimit = ev.limit_s||90" in INDEX
    assert re.search(r"const limit = tab\.idleLimit \|\| 90;", INDEX)
    assert "idle >= limit*0.75" in INDEX


def test_cancelar_derruba_o_turno_no_servidor():
    assert "fetch('/abort'" in INDEX
