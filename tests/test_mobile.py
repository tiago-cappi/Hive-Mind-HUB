"""Testes do módulo `mobile/` — o acesso pelo celular na rede de casa.

O que importa provar aqui, em ordem de gravidade:

1. **O cadeado fecha.** O Hub roda sem autenticação e com permissões liberadas;
   este módulo é a única coisa entre a rede de casa e ele. Sem token, sem
   cookie ou fora da faixa privada, nada responde.
2. **O turno sobrevive à queda do celular.** Ele roda numa thread do servidor e
   é observado por polling — fechar a aba não cancela nem perde a resposta.
3. **O histórico persiste** e respeita o teto.

Não sobe o Hub nem o `server.py` (o import de `server` carrega o Whisper): o
`bridge` é stubado. Um turno real ponta a ponta é verificação manual.

Rodar:  python -m pytest tests/test_mobile.py -q
"""
import os
import time
import json
import types
import tempfile
import shutil

import pytest

from mobile import auth, bridge, config, history, session
from mobile.app import app

LAN = {"REMOTE_ADDR": "192.168.15.99"}
FORA = {"REMOTE_ADDR": "8.8.8.8"}


@pytest.fixture(autouse=True)
def isolado(tmp_path, monkeypatch):
    """Cada teste com seus arquivos, seu token e seu estado — nada vaza."""
    monkeypatch.setattr(config, "SECRET_FILE", str(tmp_path / ".secret"))
    monkeypatch.setattr(config, "HISTORY_FILE", str(tmp_path / "history.json"))
    monkeypatch.setattr(config, "ACCESS_LOG", str(tmp_path / "access.log"))
    monkeypatch.setattr(auth, "_TOKEN", None)
    monkeypatch.setattr(auth, "_fails", {})
    monkeypatch.setattr(history, "_CACHE", None)
    monkeypatch.setattr(session, "_ST", dict(session._ST, rev=0, seq=0, busy=False,
                                            q="", txt="", passos=[], erro=""))
    monkeypatch.setattr(bridge, "hub_alive", lambda: True)
    yield


@pytest.fixture
def cli():
    return app.test_client()


@pytest.fixture
def logado(cli):
    cli.get("/login?t=" + auth.token(), environ_overrides=LAN)
    return cli


# --- 1. o cadeado -----------------------------------------------------------

def test_api_sem_token_nega(cli):
    assert cli.get("/api/state", environ_overrides=LAN).status_code == 401


def test_pagina_sem_token_manda_pro_login(cli):
    r = cli.get("/", environ_overrides=LAN)
    assert r.status_code == 302 and "/login" in r.headers["Location"]


def test_token_errado_nega(cli):
    r = cli.get("/api/state?t=nao-e-o-token", environ_overrides=LAN)
    assert r.status_code == 403


def test_token_certo_entra_e_ganha_cookie(cli):
    r = cli.get("/login?t=" + auth.token(), environ_overrides=LAN)
    assert r.status_code == 302
    assert config.COOKIE in r.headers.get("Set-Cookie", "")
    assert "HttpOnly" in r.headers.get("Set-Cookie", "")
    assert cli.get("/", environ_overrides=LAN).status_code == 200


def test_header_com_token_serve(cli):
    r = cli.get("/api/state", environ_overrides=LAN,
                headers={"X-Core-Token": auth.token()})
    assert r.status_code == 200


def test_ip_fora_da_lan_nega_mesmo_com_cookie(logado):
    """A trava de faixa vem ANTES do token: cookie bom de IP público não passa."""
    r = logado.get("/api/state", environ_overrides=FORA)
    assert r.status_code == 403


@pytest.mark.parametrize("ip,ok", [
    ("192.168.0.10", True), ("10.1.2.3", True), ("172.16.0.1", True),
    ("172.31.255.254", True), ("127.0.0.1", True), ("::1", True),
    ("172.32.0.1", False), ("8.8.8.8", False), ("203.0.113.7", False),
    ("100.64.0.1", False), ("2001:db8::1", False), ("", False), ("lixo", False),
])
def test_faixas_de_rede(ip, ok):
    assert auth.is_lan(ip) is ok


def test_freio_bloqueia_forca_bruta(cli):
    for _ in range(config.FAIL_MAX):
        cli.get("/api/state?t=errado", environ_overrides=LAN)
    r = cli.get("/api/state?t=errado", environ_overrides=LAN)
    assert r.status_code == 429
    # e o token CERTO também é barrado enquanto o castigo dura
    assert cli.get("/api/state?t=" + auth.token(),
                   environ_overrides=LAN).status_code == 429


def test_token_persiste_no_disco(cli):
    t1 = auth.token()
    auth._TOKEN = None                      # simula reinício do servidor
    assert auth.token() == t1
    assert os.path.exists(config.SECRET_FILE)


def test_acesso_negado_vira_log(cli):
    cli.get("/api/state", environ_overrides=FORA)
    with open(config.ACCESS_LOG, encoding="utf-8") as fh:
        assert "FORA-DA-LAN" in fh.read()


# --- 2. o turno vive no servidor, não na aba do celular ---------------------

def _stub_ask(eventos, atraso=0.0, registrar=None):
    """Substitui bridge.ask por um roteiro de eventos NDJSON do Hub."""
    def falso(texto, mudo=True, **kw):
        if registrar is not None:
            registrar.append(dict(kw, texto=texto, mudo=mudo))
        for ev in eventos:
            if atraso:
                time.sleep(atraso)
            yield ev
    return falso


def _espera(cli, env=LAN, teto=5.0):
    fim = time.time() + teto
    while time.time() < fim:
        s = cli.get("/api/state", environ_overrides=env).get_json()
        if not s["busy"]:
            return s
        time.sleep(0.02)
    raise AssertionError("o turno não terminou a tempo")


def test_turno_completo_vai_para_a_tela_e_para_o_historico(logado, monkeypatch):
    monkeypatch.setattr(bridge, "ask", _stub_ask([
        {"t": "step", "msg": "Lendo server.py"},
        # `partial` traz DELTAS (assim o Hub emite), nao o texto acumulado
        {"t": "partial", "txt": "oi, "},
        {"t": "partial", "txt": "tudo bem"},
        {"t": "done", "reply": "oi, tudo bem"},
    ]))
    r = logado.post("/api/ask", json={"texto": "e aí?"}, environ_overrides=LAN)
    assert r.status_code == 200 and r.get_json()["busy"] is True

    s = _espera(logado)
    assert s["txt"] == "oi, tudo bem" and s["erro"] == ""
    assert "Lendo server.py" in s["passos"]
    assert history.all()[-1] == {"ts": history.all()[-1]["ts"],
                                 "q": "e aí?", "a": "oi, tudo bem"}


def test_partial_e_delta_e_a_tela_acumula(logado, monkeypatch):
    """O Hub emite DELTAS de texto; a tela mostra a resposta crescendo — se o
    estado substituisse em vez de acumular, sobraria so o ultimo pedaco."""
    monkeypatch.setattr(bridge, "ask", _stub_ask([
        {"t": "partial", "txt": "um "},
        {"t": "partial", "txt": "dois "},
        {"t": "partial", "txt": "tres"},
        {"t": "done", "reply": ""},          # sem reply: vale o acumulado
    ]))
    logado.post("/api/ask", json={"texto": "conte"}, environ_overrides=LAN)
    s = _espera(logado)
    assert s["txt"] == "um dois tres"


def test_celular_pede_silencio_por_padrao(logado, monkeypatch):
    """Longe do PC, a casa não deve falar sozinha: `mudo` sai True."""
    visto = []
    monkeypatch.setattr(bridge, "ask",
                        _stub_ask([{"t": "done", "reply": "ok"}], registrar=visto))
    logado.post("/api/ask", json={"texto": "oi"}, environ_overrides=LAN)
    _espera(logado)
    assert visto[0]["mudo"] is True


def test_falar_true_libera_a_voz_no_computador(logado, monkeypatch):
    visto = []
    monkeypatch.setattr(bridge, "ask",
                        _stub_ask([{"t": "done", "reply": "ok"}], registrar=visto))
    logado.post("/api/ask", json={"texto": "oi", "falar": True}, environ_overrides=LAN)
    _espera(logado)
    assert visto[0]["mudo"] is False


def test_modelo_escolhido_na_tela_chega_ao_hub(logado, monkeypatch):
    """A gaveta manda o alias; no Hub ele vira `--model` no spawn do sid."""
    visto = []
    monkeypatch.setattr(bridge, "ask",
                        _stub_ask([{"t": "done", "reply": "ok"}], registrar=visto))
    logado.post("/api/ask", json={"texto": "oi", "modelo": "opus"},
                environ_overrides=LAN)
    _espera(logado)
    assert visto[0]["modelo"] == "opus"
    # e segue valendo no turno seguinte, sem a tela repetir a escolha
    logado.post("/api/ask", json={"texto": "de novo"}, environ_overrides=LAN)
    _espera(logado)
    assert visto[1]["modelo"] == "opus"


def test_modelo_desconhecido_cai_no_default(logado, monkeypatch):
    """Nome fora da whitelist nao vira flag: o spawn do Hub sai sem --model."""
    visto = []
    monkeypatch.setattr(bridge, "ask",
                        _stub_ask([{"t": "done", "reply": "ok"}], registrar=visto))
    logado.post("/api/ask", json={"texto": "oi", "modelo": "gpt --dangerous"},
                environ_overrides=LAN)
    _espera(logado)
    assert visto[0]["modelo"] == ""


def test_esforco_escolhido_na_tela_chega_ao_hub(logado, monkeypatch):
    """Mesmo caminho do modelo: a gaveta manda o nivel, o Hub vira `--effort`."""
    visto = []
    monkeypatch.setattr(bridge, "ask",
                        _stub_ask([{"t": "done", "reply": "ok"}], registrar=visto))
    logado.post("/api/ask", json={"texto": "oi", "esforco": "high"},
                environ_overrides=LAN)
    _espera(logado)
    assert visto[0]["esforco"] == "high"
    # e segue valendo no turno seguinte, sem a tela repetir a escolha
    logado.post("/api/ask", json={"texto": "de novo"}, environ_overrides=LAN)
    _espera(logado)
    assert visto[1]["esforco"] == "high"


def test_esforco_desconhecido_cai_no_default(logado, monkeypatch):
    """Valor fora da whitelist nao vira flag: o spawn do Hub sai sem --effort."""
    visto = []
    monkeypatch.setattr(bridge, "ask",
                        _stub_ask([{"t": "done", "reply": "ok"}], registrar=visto))
    logado.post("/api/ask", json={"texto": "oi", "esforco": "turbo --yolo"},
                environ_overrides=LAN)
    _espera(logado)
    assert visto[0]["esforco"] == ""


def test_nova_conversa_leva_modelo_e_esforco(logado, monkeypatch):
    """NOVA CONVERSA resobe o claude do sid ja com as duas escolhas da tela."""
    visto = {}
    monkeypatch.setattr(bridge, "reset",
                        lambda **kw: visto.update(kw) or {"ok": True})
    logado.post("/api/reset", json={"modelo": "haiku", "esforco": "max"},
                environ_overrides=LAN)
    assert visto == {"modelo": "haiku", "esforco": "max"}


def test_um_turno_por_vez(logado, monkeypatch):
    monkeypatch.setattr(bridge, "ask", _stub_ask(
        [{"t": "done", "reply": "ok"}], atraso=0.4))
    logado.post("/api/ask", json={"texto": "primeira"}, environ_overrides=LAN)
    r = logado.post("/api/ask", json={"texto": "segunda"}, environ_overrides=LAN)
    assert r.status_code == 409 and "andamento" in r.get_json()["erro"]
    _espera(logado)


def test_pergunta_vazia_nao_abre_turno(logado):
    r = logado.post("/api/ask", json={"texto": "   "}, environ_overrides=LAN)
    assert r.status_code == 409


def test_desligar_o_celular_no_meio_nao_perde_a_resposta(logado, monkeypatch):
    """O turno roda em thread própria: ninguém precisa estar olhando."""
    monkeypatch.setattr(bridge, "ask", _stub_ask(
        [{"t": "partial", "txt": "meia"}, {"t": "done", "reply": "resposta inteira"}],
        atraso=0.15))
    logado.post("/api/ask", json={"texto": "pergunta longa"}, environ_overrides=LAN)
    del logado                                   # o "celular" some da rede
    time.sleep(0.8)
    novo = app.test_client()
    novo.get("/login?t=" + auth.token(), environ_overrides=LAN)
    s = novo.get("/api/state", environ_overrides=LAN).get_json()
    assert s["busy"] is False and s["txt"] == "resposta inteira"
    assert history.all()[-1]["a"] == "resposta inteira"


def test_hub_fora_do_ar_vira_erro_legivel(logado, monkeypatch):
    def morto(*a, **kw):
        raise bridge.HubOffline("conexão recusada")
        yield                                     # pragma: no cover
    monkeypatch.setattr(bridge, "ask", morto)
    logado.post("/api/ask", json={"texto": "oi"}, environ_overrides=LAN)
    s = _espera(logado)
    assert "Hub" in s["erro"] and s["busy"] is False
    assert history.all() == []                    # turno sem resposta não entra


def test_long_poll_devolve_quando_o_estado_muda(logado, monkeypatch):
    monkeypatch.setattr(bridge, "ask", _stub_ask([{"t": "done", "reply": "pronto"}]))
    rev0 = logado.get("/api/state", environ_overrides=LAN).get_json()["rev"]
    logado.post("/api/ask", json={"texto": "oi"}, environ_overrides=LAN)
    t0 = time.time()
    s = logado.get(f"/api/state?rev={rev0}", environ_overrides=LAN).get_json()
    assert s["rev"] > rev0 and time.time() - t0 < 5   # não esperou o timeout


def test_rev_sobe_a_cada_evento(logado, monkeypatch):
    monkeypatch.setattr(bridge, "ask", _stub_ask([
        {"t": "step", "msg": "Rodando comando"},
        {"t": "partial", "txt": "a"}, {"t": "done", "reply": "a"}]))
    r0 = logado.get("/api/state", environ_overrides=LAN).get_json()["rev"]
    logado.post("/api/ask", json={"texto": "oi"}, environ_overrides=LAN)
    s = _espera(logado)
    assert s["rev"] > r0 + 2


# --- 3. histórico -----------------------------------------------------------

def test_historico_persiste_entre_reinicios(monkeypatch):
    history.add("q1", "a1")
    history.add("q2", "a2")
    monkeypatch.setattr(history, "_CACHE", None)   # simula reinício do servidor
    assert [t["q"] for t in history.all()] == ["q1", "q2"]


def test_historico_respeita_o_teto(monkeypatch):
    monkeypatch.setattr(config, "HISTORY_MAX", 5)
    for i in range(9):
        history.add(f"q{i}", f"a{i}")
    got = history.all()
    assert len(got) == 5 and got[0]["q"] == "q4"


def test_historico_json_corrompido_nao_derruba(monkeypatch):
    with open(config.HISTORY_FILE, "w", encoding="utf-8") as fh:
        fh.write("{isto não é json")
    monkeypatch.setattr(history, "_CACHE", None)
    assert history.all() == []
    history.add("q", "a")
    assert len(history.all()) == 1


def test_rota_de_historico_e_a_limpeza(logado):
    history.add("pergunta", "resposta")
    r = logado.get("/api/history", environ_overrides=LAN).get_json()
    assert r["turnos"][-1]["q"] == "pergunta"
    logado.post("/api/history/clear", environ_overrides=LAN)
    assert logado.get("/api/history", environ_overrides=LAN).get_json()["turnos"] == []


def test_historico_exige_token(cli):
    assert cli.get("/api/history", environ_overrides=LAN).status_code == 401


# --- 4. relatórios ----------------------------------------------------------

def test_lista_de_relatorios_passa_pelo_hub(logado, monkeypatch):
    monkeypatch.setattr(bridge, "reports", lambda: [
        {"file": "2026-08-26_dolar.html", "title": "Dólar", "mtime": 1, "size": 9}])
    r = logado.get("/api/reports", environ_overrides=LAN).get_json()
    assert r["reports"][0]["title"] == "Dólar"


def test_relatorio_com_hub_fora_do_ar_da_503(logado, monkeypatch):
    def morto():
        raise bridge.HubOffline("sem ponte")
    monkeypatch.setattr(bridge, "reports", morto)
    assert logado.get("/api/reports", environ_overrides=LAN).status_code == 503


def test_nome_de_relatorio_perde_o_caminho(monkeypatch):
    """`../../server.py` chega ao Hub como `server.py` — o traversal morre aqui."""
    visto = {}

    class FakeResp:
        headers = {"Content-Type": "text/html"}
        def read(self):
            return b"<html>"
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    def fake_open(path, *a, **kw):
        visto["path"] = path
        return FakeResp()

    monkeypatch.setattr(bridge, "_open", fake_open)
    bridge.report_bytes("../../server.py")
    assert visto["path"] == "/reports/server.py"


# --- 5. superfície: o que o celular NÃO alcança -----------------------------

def test_bridge_so_conhece_as_rotas_da_whitelist():
    """Rota nova no Hub não vira rota nova no celular por acidente."""
    fonte = open(os.path.join(os.path.dirname(bridge.__file__), "bridge.py"),
                 encoding="utf-8").read()
    for proibida in ("/forestos/action", "/session_end", "/speak", "/stt"):
        assert f'_open("{proibida}"' not in fonte, f"{proibida} vazou para o celular"


def test_nao_ha_rota_de_shell_nem_de_arquivo():
    caminhos = {str(r.rule) for r in app.url_map.iter_rules()}
    assert caminhos == {
        "/", "/login", "/manifest.webmanifest", "/static/<path:filename>",
        "/api/state", "/api/ask", "/api/cancel", "/api/reset",
        "/api/history", "/api/history/clear",
        "/api/reports", "/api/reports/<path:fn>",
    }


def test_paginas_estaticas_existem():
    est = os.path.join(os.path.dirname(bridge.__file__), "static")
    for arq in ("index.html", "app.js", "style.css", "icon.svg"):
        assert os.path.getsize(os.path.join(est, arq)) > 0
    html = open(os.path.join(est, "index.html"), encoding="utf-8").read()
    assert "/static/app.js" in html and "/static/style.css" in html


def test_respostas_nao_sao_cacheadas(logado):
    r = logado.get("/api/state", environ_overrides=LAN)
    assert "no-store" in r.headers["Cache-Control"]
