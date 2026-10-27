"""As rotas do modulo mobile.

Superficie inteira, e ela e pequena de proposito:

  GET  /                     a pagina (exige cookie; senao manda pro /login)
  GET  /login[?t=TOKEN]      entrada — com o token na URL ja grava o cookie
  POST /login                entrada pelo formulario
  GET  /api/state[?rev=N]    estado do turno (long-poll: espera N avancar)
  POST /api/ask              dispara um turno ({texto,falar,modelo,esforco})
  POST /api/cancel           cancela o turno em curso
  POST /api/reset            NOVA CONVERSA
  GET  /api/history          os turnos guardados
  POST /api/history/clear    esvazia o historico do celular
  GET  /api/reports          lista os relatorios visuais do vault
  GET  /api/reports/<fn>     abre um relatorio

Nao ha rota de escrita em arquivo, de shell nem de proxy generico: o que o
celular alcanca no Hub esta congelado na whitelist do `bridge`.
"""
import json

from flask import Flask, request, jsonify, redirect, make_response, Response

from . import auth, bridge, config, history, session

app = Flask(__name__, static_folder="static", static_url_path="/static")


@app.after_request
def no_cache(resp):
    resp.headers["Cache-Control"] = "no-store, max-age=0"
    return resp


# --- entrada ----------------------------------------------------------------

_LOGIN_HTML = """<!doctype html><html lang=pt-BR><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>C.O.R.E. — entrar</title>
<style>
 body{background:#0a0f12;color:#e8eef2;font:16px system-ui,sans-serif;
      display:flex;min-height:100vh;align-items:center;justify-content:center;margin:0}
 form{width:min(92vw,340px);text-align:center}
 h1{font:600 20px/1.3 system-ui;color:#B88A3F;letter-spacing:.18em;margin:0 0 6px}
 p{color:#7d8b93;font-size:13px;margin:0 0 22px}
 input{width:100%%;padding:14px;border-radius:10px;border:1px solid #223038;
       background:#0f171c;color:#e8eef2;font:15px ui-monospace,monospace;box-sizing:border-box}
 button{width:100%%;margin-top:12px;padding:14px;border:0;border-radius:10px;
        background:#B88A3F;color:#0a0f12;font:600 15px system-ui}
 .err{color:#e0776b;font-size:13px;margin-top:14px}
</style>
<form method=post>
 <h1>C.O.R.E.</h1>
 <p>cole o token que apareceu no computador</p>
 <input name=t autocomplete=off autocapitalize=off autocorrect=off
        spellcheck=false placeholder="token" autofocus>
 <button>entrar</button>
 %s
</form>"""


@app.route("/login", methods=["GET", "POST"])
def login():
    ip = auth.client_ip()
    if not auth.is_lan(ip):
        return "Fora da rede local.", 403
    dado = (request.form.get("t") or request.args.get("t") or "").strip()
    if dado:
        ok, motivo, status = auth.check()
        if ok:
            return auth.grant(make_response(redirect("/")))
        return _LOGIN_HTML % f'<div class=err>{motivo}</div>', status
    return _LOGIN_HTML % ""


@app.route("/")
@auth.require_page
def index():
    return app.send_static_file("index.html")


@app.route("/manifest.webmanifest")
def manifest():
    return jsonify({
        "name": "C.O.R.E.", "short_name": "C.O.R.E.",
        "start_url": "/", "display": "standalone",
        "background_color": "#0a0f12", "theme_color": "#0a0f12",
        "icons": [{"src": "/static/icon.svg", "sizes": "any",
                   "type": "image/svg+xml", "purpose": "any"}],
    })


# --- conversa ---------------------------------------------------------------

@app.route("/api/state")
@auth.require
def state():
    """Snapshot do turno. Com `?rev=N`, segura ate `rev` passar de N (long-poll)
    — e assim que o celular ve o texto nascer sem ficar martelando a rede."""
    try:
        rev = int(request.args.get("rev", "-1"))
    except ValueError:
        rev = -1
    s = session.wait_change(rev) if rev >= 0 else session.snapshot()
    s["hub"] = bridge.hub_alive()
    return jsonify(s)


@app.route("/api/ask", methods=["POST"])
@auth.require
def ask():
    body = request.get_json(silent=True) or {}
    # `falar` = eu estou em casa e quero ouvir a resposta no PC. Default: nao.
    mudo = not bool(body.get("falar"))
    # `modelo`/`esforco` = o que esta escolhido na gaveta de opcoes; ausente
    # mantem o que ja estava. Valor desconhecido cai no default do CLI
    # (session._limpa_modelo / _limpa_esforco).
    ok, motivo = session.start(body.get("texto", ""), mudo=mudo,
                               modelo=body.get("modelo"),
                               esforco=body.get("esforco"))
    if not ok:
        return jsonify({"erro": motivo}), 409
    return jsonify(session.snapshot())


@app.route("/api/cancel", methods=["POST"])
@auth.require
def cancel():
    session.cancel()
    return jsonify({"ok": True})


@app.route("/api/reset", methods=["POST"])
@auth.require
def reset():
    body = request.get_json(silent=True) or {}
    try:
        out = session.reset(modelo=body.get("modelo"),
                            esforco=body.get("esforco"))
    except bridge.HubOffline as e:
        return jsonify({"erro": "o Hub nao respondeu · " + str(e)}), 503
    return jsonify(out)


# --- historico --------------------------------------------------------------

@app.route("/api/history")
@auth.require
def hist():
    try:
        limit = int(request.args.get("limit", "60"))
    except ValueError:
        limit = 60
    return jsonify({"turnos": history.all(max(1, min(limit, config.HISTORY_MAX)))})


@app.route("/api/history/clear", methods=["POST"])
@auth.require
def hist_clear():
    history.clear()
    return jsonify({"ok": True})


# --- relatorios -------------------------------------------------------------

@app.route("/api/reports")
@auth.require
def reports():
    try:
        return jsonify({"reports": bridge.reports()})
    except bridge.HubOffline as e:
        return jsonify({"erro": str(e)}), 503


@app.route("/api/reports/<path:fn>")
@auth.require
def report(fn):
    try:
        blob, ctype = bridge.report_bytes(fn)
    except bridge.HubOffline as e:
        return jsonify({"erro": str(e)}), 503
    except Exception:                                     # noqa: BLE001
        return jsonify({"erro": "relatorio nao encontrado"}), 404
    return Response(blob, content_type=ctype)
