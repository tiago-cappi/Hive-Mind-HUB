"""Testes do espelho de sessao (GET /session_watch/<sid>) — a fila de linhas
que o HUD usa para reproduzir a sessao do celular na aba CELULAR.

O espelho guarda TODAS as linhas recentes (nao so a ultima): um turno emite
rajadas (step + debug + partial no mesmo flush) e, se o long-poll perdesse
linhas entre duas idas, o texto espelhado sairia corrompido.

Rodar:  .venv/Scripts/python.exe -m pytest tests/test_session_watch.py -q
"""
import sys
import types
from pathlib import Path

# --- stub do faster_whisper: server.py faz WMODEL = WhisperModel(...) no import ---
_fw = types.ModuleType("faster_whisper")
_fw.WhisperModel = lambda *a, **k: object()
sys.modules.setdefault("faster_whisper", _fw)

import server  # noqa: E402


def _slot_limpo(sid):
    server.WATCH.pop(sid, None)


def test_watch_devolve_todas_as_linhas_desde_rev():
    sid = "t-watch-fila"
    _slot_limpo(sid)
    for i in range(5):
        server._watch_publish(sid, f"linha{i}\n")
    cli = server.app.test_client()
    j = cli.get(f"/session_watch/{sid}?rev=2").get_json()
    assert j["rev"] == 5
    assert j["lines"] == ["linha2\n", "linha3\n", "linha4\n"]
    assert j["line"] == "linha4\n"          # compat: a mais recente


def test_watch_rev_negativo_so_sincroniza_sem_replay():
    sid = "t-watch-sync"
    _slot_limpo(sid)
    server._watch_publish(sid, "turno velho\n")
    cli = server.app.test_client()
    j = cli.get(f"/session_watch/{sid}?rev=-1").get_json()
    assert j["rev"] == 1 and j["lines"] == [] and j["line"] is None


def test_watch_tem_teto_de_linhas():
    sid = "t-watch-teto"
    _slot_limpo(sid)
    for i in range(server.WATCH_KEEP + 50):
        server._watch_publish(sid, f"l{i}\n")
    w = server._watch_slot(sid)
    assert len(w["lines"]) == server.WATCH_KEEP
    assert w["lines"][-1][1] == f"l{server.WATCH_KEEP + 49}\n"


def test_watched_espelha_sem_mudar_o_stream_original():
    sid = "t-watch-espelho"
    _slot_limpo(sid)
    origem = ["a\n", "b\n"]
    saiu = list(server._watched(sid, iter(origem)))
    assert saiu == origem
    w = server._watch_slot(sid)
    assert [ln for _, ln in w["lines"]] == origem


# --- contratos estaticos (mesmo espirito de test_frontend_static.py) ---------

def test_ask_anuncia_a_pergunta_no_proprio_stream():
    """Sem o evento `ask`, o espelho nao teria como mostrar o que veio do celular."""
    src = Path(server.__file__).read_text(encoding="utf-8")
    assert '"t": "ask"' in src and '"q": texto' in src


def test_front_tem_a_aba_espelho_do_celular():
    src = (Path(server.__file__).parent / "index.html").read_text(encoding="utf-8")
    assert "/session_watch/mobile?rev=" in src
    assert "ensureMobileTab" in src and "mobileWatchLine" in src
    # fechar o HUD nunca encerra o processo do celular (ele pertence ao aparelho)
    assert "if (t.mirror) return;" in src
