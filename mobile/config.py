"""Configuracao do modulo mobile.

Unico arquivo do modulo que le `os.environ`. Tudo tem default util: dando
`python mobile/run.py` sem configurar nada, funciona.

Variaveis de ambiente reconhecidas (todas opcionais):
  HUB_MOBILE_PORT      porta deste servidor            (default 8766)
  HUB_MOBILE_BIND      interface de escuta             (default 0.0.0.0 = LAN)
  HUB_MOBILE_URL       onde esta o Hub                 (default 127.0.0.1:8765)
  HUB_MOBILE_SID       sid da sessao do celular        (default "mobile")
  HUB_MOBILE_LAN_ONLY  "0" desliga a trava de faixa privada (NAO recomendado)
  HUB_MOBILE_HISTORY   quantos turnos guardar          (default 200)
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))

# --- rede -------------------------------------------------------------------
PORT = int(os.environ.get("HUB_MOBILE_PORT", "8766"))
BIND = os.environ.get("HUB_MOBILE_BIND", "0.0.0.0")   # 0.0.0.0 = visivel na LAN
HUB = os.environ.get("HUB_MOBILE_URL", "http://127.0.0.1:8765").rstrip("/")

# Trava de faixa: so responde a IP privado (192.168.x, 10.x, 172.16-31.x, ::1,
# 127.x). Se um tunel/port-forward jogar a porta na internet, o pedido morre
# aqui mesmo, antes do token. Cinto e suspensorio.
LAN_ONLY = os.environ.get("HUB_MOBILE_LAN_ONLY", "1") != "0"

# --- sessao do celular ------------------------------------------------------
# sid proprio: o celular nao divide contexto com nenhuma aba do computador.
# Consome 1 dos 6 slots de MAX_SESS do server.py enquanto estiver ativo.
SID = os.environ.get("HUB_MOBILE_SID", "mobile")
TITULO = "Celular"          # prefixo no transcript do vault e no anuncio falado
MODELO = ""                 # "" = default do CLI; ou fable|opus|sonnet|haiku
ESFORCO = ""                # "" = default do CLI; ou low|medium|high|xhigh|max

# Os modelos que a tela do celular pode escolher; MODELO acima e so o inicial.
# Espelha ALLOWED_MODELS do server.py — nome fora desta lista vira "" (default
# do CLI), entao a tela nunca consegue injetar uma flag inventada no spawn.
MODELOS = ("", "fable", "opus", "sonnet", "haiku")

# Idem para o esforco de raciocinio; espelha ALLOWED_EFFORTS do server.py.
# ESFORCO acima e so o inicial; valor fora desta lista vira "" (default).
ESFORCOS = ("", "low", "medium", "high", "xhigh", "max")

# --- arquivos locais (todos ignorados pelo git) -----------------------------
SECRET_FILE = os.path.join(HERE, ".secret")
from hub_runtime.paths import vault_root
HISTORY_FILE = os.environ.get("HUB_MOBILE_HISTORY_FILE", str(vault_root() / "_agentes" / "historico-mobile.json"))
ACCESS_LOG = os.path.join(HERE, "access.log")

# --- cookie -----------------------------------------------------------------
COOKIE = "core_mobile"
COOKIE_DAYS = 60            # entrar uma vez pelo link com token basta por 2 meses

# --- limites ----------------------------------------------------------------
HISTORY_MAX = int(os.environ.get("HUB_MOBILE_HISTORY", "200"))
FAIL_MAX = 8                # tokens errados tolerados por IP
FAIL_WINDOW = 600           # segundos de castigo depois de estourar
ASK_TIMEOUT = 900           # teto do turno (o watchdog do Hub corta bem antes)
HUB_PING_TIMEOUT = 1.5      # teto do "o Hub esta no ar?"
