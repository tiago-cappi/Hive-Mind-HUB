"""Historico de turnos do celular — sobrevive a reinicios do servidor.

Arquivo JSON proprio (`<vault>/_agentes/historico-mobile.json`), nao o transcript do vault: o
transcript e de todas as sessoes e cresce sem fim; aqui e so o fio da conversa
do celular, cortado em `config.HISTORY_MAX` turnos.

Escrita atomica (tmp + os.replace) sob lock: um turno interrompido no meio da
gravacao nao deixa um JSON quebrado que impede o celular de abrir.
"""
import os
import json
import time
import threading

from . import config

_LOCK = threading.Lock()
_CACHE = None            # lista de turnos, carregada uma vez


def _load():
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    try:
        with open(config.HISTORY_FILE, encoding="utf-8") as fh:
            got = json.load(fh)
        _CACHE = got if isinstance(got, list) else []
    except (OSError, ValueError):
        _CACHE = []
    return _CACHE


def _save():
    tmp = config.HISTORY_FILE + ".tmp"
    try:
        os.makedirs(os.path.dirname(config.HISTORY_FILE), exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(_CACHE, fh, ensure_ascii=False)
        os.replace(tmp, config.HISTORY_FILE)
    except OSError:
        pass


def add(pergunta, resposta, ts=None):
    """Anexa um turno e devolve o item gravado."""
    item = {"ts": ts or time.time(), "q": pergunta, "a": resposta}
    with _LOCK:
        _load().append(item)
        del _CACHE[:-config.HISTORY_MAX]
        _save()
    return item


def all(limit=None):
    """Os turnos, do mais antigo para o mais novo. `limit` pega os N ultimos."""
    with _LOCK:
        got = list(_load())
    return got[-limit:] if limit else got


def clear():
    """Apaga o historico do celular. Nao toca no transcript do vault."""
    global _CACHE
    with _LOCK:
        _CACHE = []
        _save()
