"""O cadeado. Nega por padrao.

Por que existe: o Hub (8765) roda `claude --dangerously-skip-permissions` sem
autenticacao nenhuma. Quem alcanca aquela porta manda comandos nesta maquina.
Este modulo e a unica coisa entre a rede de casa e ela — entao ele e chato de
proposito: sem faixa privada, sem token e sem cookie, nada responde.

Tres camadas, nesta ordem:
  1. faixa de rede  — so IP privado (config.LAN_ONLY)
  2. freio          — 8 tokens errados por IP = 10 min de silencio
  3. token          — cookie assinado por comparacao constante, ou ?t= na URL
"""
import os
import time
import stat
import secrets
import ipaddress
import threading
import datetime
from functools import wraps

from flask import request, jsonify, redirect

from . import config

_TOKEN = None
_TOKEN_LOCK = threading.Lock()

# IP -> [n_falhas, timestamp_da_ultima]
_fails = {}
_FAIL_LOCK = threading.Lock()


# --- token ------------------------------------------------------------------

def token():
    """Le o token do disco; cria um na primeira vez. Cacheado em memoria."""
    global _TOKEN
    with _TOKEN_LOCK:
        if _TOKEN:
            return _TOKEN
        try:
            with open(config.SECRET_FILE, encoding="utf-8") as fh:
                got = fh.read().strip()
            if got:
                _TOKEN = got
                return _TOKEN
        except OSError:
            pass
        _TOKEN = secrets.token_urlsafe(24)
        with open(config.SECRET_FILE, "w", encoding="utf-8") as fh:
            fh.write(_TOKEN + "\n")
        try:                     # best-effort: so o dono le (no-op no Windows)
            os.chmod(config.SECRET_FILE, stat.S_IRUSR | stat.S_IWUSR)
        except OSError:
            pass
        return _TOKEN


def reset_token():
    """Descarta o token atual e gera outro. Derruba todos os celulares."""
    global _TOKEN
    with _TOKEN_LOCK:
        _TOKEN = None
        try:
            os.remove(config.SECRET_FILE)
        except OSError:
            pass
    return token()


# --- faixa de rede ----------------------------------------------------------

# Faixas de rede domestica, explicitas. Nao uso `addr.is_private`: ele tambem
# aceita os blocos de documentacao (192.0.2.0/24, 198.51.100.0/24,
# 203.0.113.0/24) e o CGNAT (100.64.0.0/10) — nada disso e a sua casa.
_FAIXAS = tuple(ipaddress.ip_network(x) for x in (
    "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16",   # RFC 1918
    "169.254.0.0/16", "127.0.0.0/8",                    # link-local, loopback
    "fc00::/7", "fe80::/10", "::1/128",                 # IPv6 equivalentes
))


def is_lan(ip):
    """True so para IP de rede domestica. String vazia ou lixo -> False."""
    if not config.LAN_ONLY:
        return True
    try:
        addr = ipaddress.ip_address((ip or "").split("%")[0])
    except ValueError:
        return False
    return any(addr in rede for rede in _FAIXAS if rede.version == addr.version)


def client_ip():
    """IP do cliente. Ignora X-Forwarded-* de proposito: aqui nao ha proxy, e
    confiar no cabecalho seria deixar o cliente escolher o proprio IP."""
    return request.remote_addr or ""


# --- freio de tentativas ----------------------------------------------------

def _blocked(ip):
    with _FAIL_LOCK:
        n, ts = _fails.get(ip, (0, 0.0))
        if n < config.FAIL_MAX:
            return 0
        left = config.FAIL_WINDOW - (time.time() - ts)
        if left <= 0:
            _fails.pop(ip, None)
            return 0
        return int(left)


def _note_fail(ip):
    with _FAIL_LOCK:
        n, _ = _fails.get(ip, (0, 0.0))
        _fails[ip] = (n + 1, time.time())


def _clear_fail(ip):
    with _FAIL_LOCK:
        _fails.pop(ip, None)


# --- log de acesso ----------------------------------------------------------

def log_access(ip, path, verdict):
    """Uma linha por pedido negado ou por entrada nova. Sucesso repetido nao
    entra: o interessante e quem tentou, nao quem ja mora aqui."""
    try:
        stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(config.ACCESS_LOG, "a", encoding="utf-8") as fh:
            fh.write(f"{stamp}\t{ip}\t{verdict}\t{path}\n")
    except OSError:
        pass


# --- porteiro ---------------------------------------------------------------

def check():
    """Devolve (ok, motivo, http_status). Nao levanta."""
    ip = client_ip()
    if not is_lan(ip):
        log_access(ip, request.path, "FORA-DA-LAN")
        return False, "fora da rede local", 403
    left = _blocked(ip)
    if left:
        return False, f"bloqueado por {left}s (tokens errados demais)", 429

    good = token()
    cookie = request.cookies.get(config.COOKIE, "")
    if cookie and secrets.compare_digest(cookie, good):
        return True, "", 200

    # `?t=` (link), campo do formulario do /login, ou cabecalho (fetch do app).
    given = (request.args.get("t") or request.form.get("t")
             or request.headers.get("X-Core-Token") or "")
    if given and secrets.compare_digest(given, good):
        _clear_fail(ip)
        log_access(ip, request.path, "ENTROU")
        return True, "", 200

    if given or cookie:
        _note_fail(ip)
        log_access(ip, request.path, "TOKEN-ERRADO")
        return False, "token invalido", 403
    log_access(ip, request.path, "SEM-TOKEN")
    return False, "token ausente", 401


def require(fn):
    """Decorator das rotas de API: 401/403/429 em JSON, sem vazar detalhe."""
    @wraps(fn)
    def guard(*a, **kw):
        ok, motivo, status = check()
        if not ok:
            return jsonify({"erro": motivo}), status
        return fn(*a, **kw)
    return guard


def require_page(fn):
    """Igual, para paginas: manda para /login em vez de devolver JSON."""
    @wraps(fn)
    def guard(*a, **kw):
        ok, _motivo, status = check()
        if not ok:
            if status == 429:
                return "Bloqueado por tentativas demais. Tente mais tarde.", 429
            if status == 403 and not is_lan(client_ip()):
                return "Fora da rede local.", 403
            return redirect("/login")
        return fn(*a, **kw)
    return guard


def grant(resp):
    """Gruda o cookie de sessao na resposta. Chamado so depois de token valido."""
    resp.set_cookie(
        config.COOKIE, token(),
        max_age=config.COOKIE_DAYS * 24 * 3600,
        httponly=True, samesite="Lax", secure=False,  # LAN em http, sem TLS
    )
    return resp
