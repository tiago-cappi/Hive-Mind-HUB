"""Testes do AUTOQUIT — a ponte morre junto com o HUD.

Contexto: fechar a janela do Chrome nao derrubava nada. Um `pythonw server.py`
ficou 18h no ar segurando a porta 8765 com codigo VELHO em memoria — o usuario
editava o server.py e nada mudava, porque o processo no ar era o de ontem.

Contrato coberto aqui:
  - /hud_ping registra a janela POR ID e marca que um HUD ja apareceu;
  - /hud_bye da baixa na hora (sendBeacon do beforeunload);
  - pulso sem `hud` e ignorado — um HUD anonimo nao teria como dar baixa e
    prenderia a ponte viva para sempre;
  - HUD calado ha mais de HUD_TTL e recolhido por _huds_vivos();
  - com DUAS janelas abertas, fechar uma NAO derruba a ponte da outra;
  - antes do primeiro pulso a ponte nunca se encerra sozinha (suite de testes,
    cliente do celular e scripts auxiliares sobem o server sem HUD).

O laco _hud_watchdog() em si nao e chamado: ele termina em os._exit(0) e mataria
o processo do pytest. O que se testa e a decisao que ele consulta.

Rodar:  python -m pytest tests/test_autoquit.py -q
"""
import sys
import time
import types

# --- stub do faster_whisper: server.py faz WMODEL = WhisperModel(...) no import ---
_fw = types.ModuleType("faster_whisper")
_fw.WhisperModel = lambda *a, **k: object()
sys.modules.setdefault("faster_whisper", _fw)

import server  # noqa: E402


def _client():
    return server.app.test_client()


def _zera():
    with server.HUD_LOCK:
        server.HUDS.clear()
    server.HUD_EVER[0] = False


def _ping(client, hud):
    return client.post("/hud_ping", json={"hud": hud})


# ------------------------------- registro ------------------------------------
def test_ping_registra_a_janela_e_marca_que_houve_hud():
    _zera()
    try:
        r = _ping(_client(), "hud-a")
        assert r.status_code == 200
        j = r.get_json()
        assert j["ok"] is True and j["huds"] == 1
        assert server.HUD_EVER[0] is True
        assert "hud-a" in server.HUDS
    finally:
        _zera()


def test_ping_sem_id_nao_registra_hud_fantasma():
    """Um HUD sem id nunca receberia baixa: prenderia a ponte viva para sempre."""
    _zera()
    try:
        r = _client().post("/hud_ping", json={})
        assert r.status_code == 200
        assert r.get_json()["ok"] is False
        assert server.HUDS == {}
        assert server.HUD_EVER[0] is False
    finally:
        _zera()


def test_pings_repetidos_da_mesma_janela_nao_multiplicam_o_registro():
    _zera()
    try:
        client = _client()
        for _ in range(5):
            _ping(client, "hud-a")
        assert len(server.HUDS) == 1
    finally:
        _zera()


# --------------------------------- baixa -------------------------------------
def test_bye_da_baixa_na_hora():
    _zera()
    try:
        client = _client()
        _ping(client, "hud-a")
        r = client.post("/hud_bye", json={"hud": "hud-a"})
        assert r.status_code == 200 and r.get_json()["huds"] == 0
        assert server._huds_vivos() == 0
    finally:
        _zera()


def test_fechar_uma_janela_nao_derruba_a_ponte_da_outra():
    _zera()
    try:
        client = _client()
        _ping(client, "hud-a")
        _ping(client, "hud-b")
        client.post("/hud_bye", json={"hud": "hud-a"})
        assert server._huds_vivos() == 1, "a ponte cairia com a 2a janela aberta"
    finally:
        _zera()


def test_bye_de_janela_desconhecida_nao_quebra():
    _zera()
    try:
        r = _client().post("/hud_bye", json={"hud": "nunca-existiu"})
        assert r.status_code == 200
    finally:
        _zera()


# ------------------------------- expiracao -----------------------------------
def test_hud_calado_alem_do_ttl_e_recolhido():
    _zera()
    try:
        _ping(_client(), "hud-a")
        with server.HUD_LOCK:
            server.HUDS["hud-a"] = time.time() - server.HUD_TTL - 5
        assert server._huds_vivos() == 0
        assert "hud-a" not in server.HUDS
    finally:
        _zera()


def test_hud_dentro_do_ttl_continua_vivo():
    _zera()
    try:
        _ping(_client(), "hud-a")
        with server.HUD_LOCK:
            server.HUDS["hud-a"] = time.time() - (server.HUD_TTL / 2)
        assert server._huds_vivos() == 1
    finally:
        _zera()


def test_ttl_folgado_o_bastante_para_o_throttle_de_aba_em_segundo_plano():
    """O Chrome estrangula timers de janela em 2o plano ate ~1 pulso/minuto.
    TTL curto derrubaria a ponte com o HUD apenas minimizado."""
    assert server.HUD_TTL >= 90


# ------------------------------ porta de saida -------------------------------
def test_sem_nenhum_hud_a_ponte_nao_se_encerra_sozinha():
    """A suite, o cliente do celular e scripts auxiliares sobem o server sem HUD."""
    _zera()
    assert server.HUD_EVER[0] is False
    assert server._huds_vivos() == 0


def test_autoquit_ligado_por_padrao_e_desligavel_por_env():
    import os
    assert server.AUTOQUIT is (os.environ.get("HUB_AUTOQUIT", "1") != "0")
