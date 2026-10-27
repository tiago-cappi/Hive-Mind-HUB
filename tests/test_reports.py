"""Testes das rotas de RELATÓRIOS VISUAIS no Flask (base do visor do Hub).

Cobre: GET /reports lista só .html/.htm da pasta, mais recente primeiro, com
título vindo do <title> (fallback: nome do arquivo sem timestamp); GET
/reports/<fn> serve o arquivo e barra path traversal; pasta criada no 1º uso.

Aponta server.REPORTS_DIR para um diretório temporário — nada é escrito no
vault real. Stuba faster_whisper (server.py carrega o modelo no import).

Rodar:  python -m pytest tests/test_reports.py -q
"""
import os
import sys
import time
import types
import tempfile
import shutil
from unittest.mock import patch

# --- stub do faster_whisper: server.py faz WMODEL = WhisperModel(...) no import ---
_fw = types.ModuleType("faster_whisper")
_fw.WhisperModel = lambda *a, **k: object()
sys.modules.setdefault("faster_whisper", _fw)

import server  # noqa: E402


def _client():
    return server.app.test_client()


class TempReports:
    """Context manager: REPORTS_DIR temporário + limpeza garantida."""

    def __enter__(self):
        self.dir = tempfile.mkdtemp(prefix="hub_reports_test_")
        self.patcher = patch.object(server, "REPORTS_DIR", self.dir)
        self.patcher.start()
        return self.dir

    def __exit__(self, *exc):
        self.patcher.stop()
        shutil.rmtree(self.dir, ignore_errors=True)


def _write(dirpath, fn, body, mtime=None):
    p = os.path.join(dirpath, fn)
    with open(p, "w", encoding="utf-8") as f:
        f.write(body)
    if mtime is not None:
        os.utime(p, (mtime, mtime))
    return p


# ------------------------------ GET /reports ---------------------------------
def test_get_reports_pasta_vazia_devolve_lista_vazia():
    with TempReports():
        r = _client().get("/reports")
    assert r.status_code == 200
    assert r.get_json() == {"reports": []}


def test_get_reports_cria_a_pasta_no_primeiro_uso():
    with TempReports() as d:
        sub = os.path.join(d, "ainda-nao-existe")
        with patch.object(server, "REPORTS_DIR", sub):
            r = _client().get("/reports")
        assert r.status_code == 200
        assert os.path.isdir(sub)


def test_get_reports_lista_html_mais_recente_primeiro_com_titulo():
    now = time.time()
    with TempReports() as d:
        _write(d, "2026-08-18_100000_dolar.html",
               "<html><head><title>Dólar · 30 dias</title></head></html>", now - 100)
        _write(d, "2026-08-18_110000_clima.html",
               "<html><head><title>Clima da semana</title></head></html>", now)
        r = _client().get("/reports")
    body = r.get_json()
    assert [x["title"] for x in body["reports"]] == ["Clima da semana", "Dólar · 30 dias"]
    assert body["reports"][0]["file"] == "2026-08-18_110000_clima.html"
    assert body["reports"][0]["mtime"] >= body["reports"][1]["mtime"]


def test_get_reports_ignora_arquivos_que_nao_sao_html():
    with TempReports() as d:
        _write(d, "dados.csv", "a,b\n1,2")
        _write(d, "nota.md", "# oi")
        _write(d, "ok.html", "<title>Ok</title>")
        r = _client().get("/reports")
    files = [x["file"] for x in r.get_json()["reports"]]
    assert files == ["ok.html"]


def test_get_reports_titulo_sem_title_cai_no_nome_sem_timestamp():
    with TempReports() as d:
        _write(d, "2026-08-18_120000_vendas_do_mes.html", "<html><body>sem title</body></html>")
        r = _client().get("/reports")
    assert r.get_json()["reports"][0]["title"] == "vendas do mes"


# --------------------------- GET /reports/<fn> --------------------------------
def test_get_reports_arquivo_serve_o_conteudo():
    with TempReports() as d:
        _write(d, "rel.html", "<title>X</title><h1>conteúdo</h1>")
        r = _client().get("/reports/rel.html")
    assert r.status_code == 200
    assert "conteúdo".encode("utf-8") in r.data


def test_get_reports_arquivo_vizinho_nao_html_tambem_e_servido():
    # relatório pode referenciar um csv/imagem ao lado — a pasta inteira é servida
    with TempReports() as d:
        _write(d, "dados.csv", "a,b\n1,2")
        r = _client().get("/reports/dados.csv")
    assert r.status_code == 200


def test_get_reports_path_traversal_e_barrado():
    with TempReports():
        r = _client().get("/reports/..%2Fserver.py")
    assert r.status_code == 404


def test_get_reports_arquivo_inexistente_devolve_404():
    with TempReports():
        r = _client().get("/reports/nao-existe.html")
    assert r.status_code == 404


# ------------------------- DELETE /reports/<fn> --------------------------------
def test_delete_reports_remove_o_arquivo():
    with TempReports() as d:
        _write(d, "rel.html", "<title>X</title>")
        r = _client().delete("/reports/rel.html")
        assert r.status_code == 200
        assert r.get_json() == {"ok": True}
        assert not os.path.exists(os.path.join(d, "rel.html"))


def test_delete_reports_arquivo_inexistente_devolve_404():
    with TempReports():
        r = _client().delete("/reports/nao-existe.html")
    assert r.status_code == 404


def test_delete_reports_recusa_extensao_que_nao_e_relatorio():
    with TempReports() as d:
        _write(d, "dados.csv", "a,b\n1,2")
        r = _client().delete("/reports/dados.csv")
        assert r.status_code == 400
        assert os.path.exists(os.path.join(d, "dados.csv"))


def test_delete_reports_path_traversal_e_barrado():
    with TempReports():
        r = _client().delete("/reports/..%2Fserver.py")
    assert r.status_code == 400  # extensão não-.html já barra antes do safe_join


def test_delete_reports_path_traversal_com_extensao_html_tambem_e_barrado():
    with TempReports() as d:
        _write(os.path.dirname(d), "fora.html", "<title>fora</title>")
        r = _client().delete("/reports/..%2Ffora.html")
        assert r.status_code == 404
        assert os.path.exists(os.path.join(os.path.dirname(d), "fora.html"))


# --------------------- smoke test: rotas existentes intactas ------------------
def test_rotas_existentes_continuam_respondendo():
    client = _client()
    assert client.get("/").status_code == 200
    r = client.post("/stt")
    assert r.status_code == 200
    assert r.get_json() == {"texto": ""}
