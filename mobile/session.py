"""O turno em curso — desacoplado da conexao do celular.

O problema que este modulo resolve: no celular a conexao cai o tempo todo. A
tela apaga, o Wi-Fi troca de canal, o navegador congela a aba em segundo plano.
Se a resposta viesse presa a um streaming HTTP, cada uma dessas coisas mataria
o turno no meio e perderia a resposta.

Entao o turno roda numa thread propria, alimentada pelo `bridge`, escrevendo num
estado global. O celular so olha esse estado (`snapshot`) quando pode. Fechar o
navegador nao cancela nada: o Claude termina, o turno vai para o historico e a
resposta esta la quando o aparelho voltar.

Um turno por vez, de proposito: e uma pessoa com um celular, e dois turnos
paralelos no mesmo sid disputariam o lock do sid la no Hub de qualquer jeito.
"""
import time
import threading

from . import bridge, config, history

MAX_PASSOS = 40          # so os ultimos passos interessam na tela do celular

_LOCK = threading.Lock()
_CHANGED = threading.Condition(_LOCK)

_ST = {
    "rev": 0,            # sobe a cada mudanca — o celular usa para long-poll
    "seq": 0,            # numero do turno (cresce sempre)
    "busy": False,
    "q": "",             # pergunta do turno atual
    "txt": "",           # resposta acumulada (vai crescendo)
    "passos": [],        # "Lendo server.py", "Rodando comando"...
    "pensando": 0,       # chars de raciocinio no turno
    "erro": "",
    "ts": 0.0,
    "modelo": config.MODELO,   # alias do CLI em vigor ("" = default do Hub)
    "esforco": config.ESFORCO, # --effort em vigor ("" = default do Hub)
}


def _limpa_modelo(m):
    """So alias conhecido vira flag la no Hub; o resto cai no default do CLI."""
    m = (m or "").strip().lower()
    return m if m in config.MODELOS else ""


def _limpa_esforco(e):
    """Idem para o --effort: fora da lista conhecida, cai no default do CLI."""
    e = (e or "").strip().lower()
    return e if e in config.ESFORCOS else ""


def _touch():
    """Marca mudanca e acorda quem espera. Chamar sempre com o lock tomado."""
    _ST["rev"] += 1
    _CHANGED.notify_all()


def snapshot():
    with _LOCK:
        s = dict(_ST)
        s["passos"] = list(_ST["passos"])
    return s


def wait_change(rev, timeout=25.0):
    """Long-poll: devolve o snapshot assim que `rev` avancar (ou no timeout)."""
    fim = time.time() + timeout
    with _LOCK:
        while _ST["rev"] == rev:
            restante = fim - time.time()
            if restante <= 0:
                break
            _CHANGED.wait(restante)
        s = dict(_ST)
        s["passos"] = list(_ST["passos"])
    return s


def busy():
    with _LOCK:
        return _ST["busy"]


def _run(texto, mudo, modelo, esforco):
    """Corpo da thread do turno. Nunca levanta: erro vira campo `erro`."""
    reply = ""
    erro = ""
    try:
        for ev in bridge.ask(texto, mudo=mudo, modelo=modelo, esforco=esforco):
            t = ev.get("t")
            with _LOCK:
                if t == "partial":
                    # o Hub manda DELTAS (o que nasceu desde o ultimo flush),
                    # nao o texto inteiro: acumula, senao a tela do celular
                    # mostraria so o ultimo pedaco enquanto a resposta cresce.
                    _ST["txt"] += ev.get("txt", "")
                    _touch()
                elif t == "step":
                    msg = (ev.get("msg") or "").strip()
                    if msg and (not _ST["passos"] or _ST["passos"][-1] != msg):
                        _ST["passos"].append(msg)
                        del _ST["passos"][:-MAX_PASSOS]
                        _touch()
                elif t == "thinking":
                    _ST["pensando"] = ev.get("chars", 0)
                    _touch()
                elif t == "done":
                    reply = ev.get("reply", "") or _ST["txt"]
                    _ST["txt"] = reply
                    _touch()
                elif t == "debug" and ev.get("lv") == "ERR":
                    erro = ev.get("msg", "")
    except bridge.HubOffline as e:
        erro = "o Hub nao respondeu (a ponte esta no ar?) · " + str(e)
    except Exception as e:                                # noqa: BLE001
        erro = f"{type(e).__name__}: {e}"

    if reply.strip():
        history.add(texto, reply)
        erro = ""            # respondeu: erro no meio do caminho e ruido
    elif not erro:
        erro = "o turno terminou sem resposta"

    with _LOCK:
        _ST["busy"] = False
        _ST["erro"] = erro
        _ST["txt"] = reply or _ST["txt"]
        _touch()


def start(texto, mudo=True, modelo=None, esforco=None):
    """Dispara o turno em segundo plano. (ok, motivo).

    `modelo` (alias do CLI) e `esforco` (--effort) ficam valendo para os
    proximos turnos tambem — a tela manda o que esta escolhido nela. Trocar
    qualquer um dos dois faz o Hub matar e resubir o `claude` deste sid, mas o
    processo novo sobe com `--resume`: a CONVERSA sobrevive a troca de modelo.
    Zerar o contexto e' so no `reset()`.
    """
    texto = (texto or "").strip()
    if not texto:
        return False, "pergunta vazia"
    with _LOCK:
        if _ST["busy"]:
            return False, "ja existe um turno em andamento"
        if modelo is not None:
            _ST["modelo"] = _limpa_modelo(modelo)
        if esforco is not None:
            _ST["esforco"] = _limpa_esforco(esforco)
        escolhido = _ST["modelo"]
        escolhido_esf = _ST["esforco"]
        _ST.update({
            "seq": _ST["seq"] + 1, "busy": True, "q": texto, "txt": "",
            "passos": [], "pensando": 0, "erro": "", "ts": time.time(),
        })
        _touch()
    threading.Thread(target=_run, args=(texto, mudo, escolhido, escolhido_esf),
                     daemon=True,
                     name="mobile-turn").start()
    return True, ""


def cancel():
    """Cancela o turno no Hub. A thread termina sozinha quando o stream fechar."""
    try:
        bridge.abort()
    except bridge.HubOffline:
        pass
    with _LOCK:
        if _ST["busy"]:
            _ST["erro"] = "cancelado"
            _touch()
    return True


def reset(modelo=None, esforco=None):
    """NOVA CONVERSA: limpa a tela do celular e resobe o processo no Hub."""
    with _LOCK:
        if modelo is not None:
            _ST["modelo"] = _limpa_modelo(modelo)
        if esforco is not None:
            _ST["esforco"] = _limpa_esforco(esforco)
        escolhido = _ST["modelo"]
        escolhido_esf = _ST["esforco"]
    out = bridge.reset(modelo=escolhido, esforco=escolhido_esf)
    with _LOCK:
        _ST.update({"q": "", "txt": "", "passos": [], "pensando": 0, "erro": ""})
        _touch()
    return out
