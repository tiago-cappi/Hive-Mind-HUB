"""A unica peca do modulo que fala com o Hub (127.0.0.1:8765).

Whitelist explicita, e curta de proposito. O celular alcanca:
    POST /ask            conversar
    POST /session_reset  nova conversa
    POST /abort          cancelar o turno
    GET  /reports        listar relatorios
    GET  /reports/<fn>   abrir um relatorio

Nao ha caminho daqui para /forestos/action, /speak, /session_end ou /stt. Rota
nova no Hub nao vira rota nova no celular sozinha — tem que ser escrita aqui.

Usa so a biblioteca padrao (urllib): o venv do Hub nao tem `requests`, e o
modulo nao vale uma dependencia nova.
"""
import json
import socket
import urllib.error
import urllib.parse
import urllib.request

from . import config


class HubOffline(RuntimeError):
    """O Hub nao respondeu — quase sempre a ponte esta fora do ar."""


def _req(path, payload=None, method=None, timeout=30):
    url = config.HUB + path
    data = None
    headers = {"Accept": "application/x-ndjson, application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    return urllib.request.Request(
        url, data=data, headers=headers, method=method or ("POST" if data else "GET")
    ), timeout


def _open(path, payload=None, method=None, timeout=30):
    req, tmo = _req(path, payload, method, timeout)
    try:
        return urllib.request.urlopen(req, timeout=tmo)
    except urllib.error.HTTPError:
        raise
    except (urllib.error.URLError, socket.timeout, ConnectionError) as e:
        raise HubOffline(str(e)) from e


def hub_alive():
    """O Hub esta no ar? Barato: abre a porta e desiste rapido."""
    host = urllib.parse.urlparse(config.HUB)
    try:
        with socket.create_connection(
            (host.hostname or "127.0.0.1", host.port or 80), config.HUB_PING_TIMEOUT
        ):
            return True
    except OSError:
        return False


def ask(texto, mudo=True, modelo=None, esforco=None, sid=None, titulo=None):
    """Manda o turno e devolve um gerador dos eventos NDJSON do Hub.

    `mudo=True` (default do celular) pede ao Hub que NAO fale em voz alta no
    computador — voce esta longe dele. O campo e ignorado por um server.py
    antigo, entao no pior caso a casa fala; nada quebra.
    """
    payload = {
        "texto": texto,
        "sid": sid or config.SID,
        "titulo": titulo or config.TITULO,
        "modelo": config.MODELO if modelo is None else modelo,
        "esforco": config.ESFORCO if esforco is None else esforco,
        "mudo": bool(mudo),
    }
    resp = _open("/ask", payload, timeout=config.ASK_TIMEOUT)
    ctype = (resp.headers.get("Content-Type") or "").lower()
    if "ndjson" not in ctype:
        # texto vazio -> o Hub responde JSON simples; normaliza para 1 evento.
        try:
            body = json.loads(resp.read().decode("utf-8", "replace"))
        except (ValueError, OSError):
            body = {"reply": ""}
        yield {"t": "done", "reply": body.get("reply", ""), "spoken": False}
        return
    with resp:
        for raw in resp:
            line = raw.decode("utf-8", "replace").strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except ValueError:
                continue          # linha partida no meio: descarta, segue o turno


def reset(sid=None, modelo=None, esforco=None):
    """NOVA CONVERSA: mata e resobe o processo `claude` da sessao do celular."""
    with _open("/session_reset", {
        "sid": sid or config.SID,
        "modelo": config.MODELO if modelo is None else modelo,
        "esforco": config.ESFORCO if esforco is None else esforco,
    }, timeout=60) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def abort(sid=None):
    """CANCELAR: mata o processo do turno em curso, mantendo a sessao."""
    with _open("/abort", {"sid": sid or config.SID}, timeout=30) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def reports():
    """Lista os relatorios visuais do vault (mais recente primeiro)."""
    with _open("/reports", timeout=15) as r:
        return json.loads(r.read().decode("utf-8", "replace")).get("reports", [])


def report_bytes(fn):
    """Conteudo de um relatorio. Devolve (bytes, content_type).

    O nome vai quoted e sem barras: quem barra path traversal de verdade e o
    `send_from_directory` do Hub, mas nao custa nao ajudar o atacante.
    """
    safe = urllib.parse.quote(fn.replace("\\", "/").split("/")[-1])
    with _open("/reports/" + safe, timeout=30) as r:
        return r.read(), r.headers.get("Content-Type", "application/octet-stream")
