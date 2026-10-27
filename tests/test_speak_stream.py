"""Testes da fala em streaming (SpeakStream + arbitro + protocolo de arquivos).

A fala do turno passou a comecar com a resposta ainda nascendo: o /ask enfileira
um job no arbitro e vai escrevendo o texto em STREAM, e o speak_server sintetiza
pela 1a frase em vez de esperar o turno fechar.

Aqui o speak_server e substituido por um duble (nada de Kokoro, nada de audio) e
os caminhos do protocolo apontam para arquivos de teste, para nao colidir com o
servidor de fala residente. Rodar: python -m pytest tests/test_speak_stream.py -q
"""
import json
import os
import tempfile
import threading
import time

import server as S

TMP = tempfile.gettempdir()
PATHS = ("REQ", "STREAM", "STREAM_END", "STARTED", "DONE", "ENVELOPE", "META", "READY")


def _redirect():
    """Aponta o protocolo para arquivos de teste; devolve os valores originais."""
    orig = {n: getattr(S, n) for n in PATHS}
    for n in orig:
        setattr(S, n, os.path.join(TMP, "tspk_" + n.lower() + ".txt"))
    for n in orig:
        try:
            os.remove(getattr(S, n))
        except OSError:
            pass
    open(S.READY, "w").close()
    return orig


def _fake_speak_server(got):
    """Duble: le o pedido, consome o texto em streaming, sinaliza o ciclo."""
    while not os.path.exists(S.REQ):
        time.sleep(0.02)
    with open(S.REQ, "r", encoding="utf-8") as f:
        got["req"] = f.read().strip()
    os.remove(S.REQ)
    pos, levels, started = 0, [], False
    while True:
        try:
            with open(S.STREAM, "r", encoding="utf-8") as f:
                f.seek(pos)
                new = f.read()
                pos = f.tell()
        except OSError:
            new = ""
        if new:
            got["text"] += new
        if not started and len(got["text"]) > 40:   # colchao pronto -> larga
            started = True
            levels += [0.5] * 10
            with open(S.ENVELOPE, "w", encoding="utf-8") as f:
                json.dump({"step_ms": 60, "levels": levels}, f)
            open(S.STARTED, "w").close()
        elif started and new:                       # envelope cresce com o audio
            levels += [0.6] * 8
            with open(S.ENVELOPE, "w", encoding="utf-8") as f:
                json.dump({"step_ms": 60, "levels": levels}, f)
        if os.path.exists(S.STREAM_END):
            if got["end_at"] is None:
                got["end_at"] = time.time()
            if not new:
                break
        time.sleep(0.05)
    time.sleep(0.5)
    open(S.DONE, "w").close()


PARTES = ["Primeira frase da resposta, com um tamanho razoavel. ",
          "Segunda frase, ainda escrevendo. ",
          "Terceira e ultima frase do turno."]


def _run_turn():
    got = {"req": None, "text": "", "end_at": None, "fed_at": None}
    threading.Thread(target=_fake_speak_server, args=(got,), daemon=True).start()
    evs = []
    spk = S.SpeakStream("sid-teste", "Aba Teste", 440)
    for p in PARTES:
        time.sleep(0.3)
        evs += spk.feed(p)
    got["fed_at"] = time.time()
    evs += list(spk.close())
    return got, evs


def test_fala_em_streaming_ponta_a_ponta():
    orig = _redirect()
    try:
        got, evs = _run_turn()
        tipos = [e["t"] for e in evs]
        # o pedido avisa o Kokoro que o texto vem pelo canal de streaming
        assert got["req"] == "__stream__", got["req"]
        # todo o texto do turno chega, na ordem, e sem o anuncio (que vai no META)
        assert got["text"].strip() == "".join(PARTES).strip(), got["text"]
        # o fim so e marcado depois de o texto sair todo
        assert got["end_at"] >= got["fed_at"] - 0.01
        # o ciclo de eventos que o front espera
        assert "speak_start" in tipos, tipos
        assert "speak_env" in tipos, tipos          # envelope incremental
        assert tipos[-1] == "speak_done", tipos
        done = evs[-1]
        assert done["ok"] and done["started"], done
        start = [e for e in evs if e["t"] == "speak_start"][0]
        assert start["envelope"], start             # niveis iniciais p/ o medidor
        # o arbitro fica livre para o proximo turno
        assert not S.SPEAK_BUSY.is_set()
    finally:
        for n, v in orig.items():
            setattr(S, n, v)


def test_watchdog_fecha_o_texto_se_o_turno_morrer():
    """ESC/aba fechada: ninguem chama close() -> o canal nao pode ficar aberto."""
    orig = _redirect()
    try:
        spk = S.SpeakStream("sid-morto", "", None)
        spk.last = time.time() - 60          # simula 60s sem texto novo
        for _ in range(40):
            if spk.text_closed:
                break
            time.sleep(0.05)
        assert spk.text_closed, "watchdog nao fechou o canal de texto"
        assert os.path.exists(S.STREAM_END)
    finally:
        for n, v in orig.items():
            setattr(S, n, v)


def test_alive_segura_o_watchdog_enquanto_o_turno_pensa():
    """Ferramenta longa no meio da resposta NAO pode fechar o canal de texto.

    Regressao do bug em que um Bash/subagente de mais de 45s durante um turno
    fazia o watchdog marcar STREAM_END: o Kokoro falava so o texto anterior a
    ferramenta e a resposta de verdade, escrita depois, saia na tela sem nunca
    ser falada — com o turno ainda se declarando `spoken`, o que tirava ate o
    /speak do fim do caminho. O /ask agora chama alive() a cada evento e a cada
    heartbeat; so um turno REALMENTE morto para de chamar.
    """
    orig = _redirect()
    try:
        spk = S.SpeakStream("sid-pensando", "", None)
        spk.go.set()                         # este job ja e o dono do canal
        spk.last = time.time() - 60          # ja passou da fome...
        for _ in range(12):                  # ...mas o turno segue vivo
            spk.alive()
            time.sleep(0.05)
            assert not spk.text_closed, "watchdog fechou o canal com o turno vivo"
        spk.last = time.time() - 60          # agora o turno morre de verdade
        for _ in range(40):
            if spk.text_closed:
                break
            time.sleep(0.05)
        assert spk.text_closed, "watchdog nao fechou o canal do turno morto"
    finally:
        for n, v in orig.items():
            setattr(S, n, v)


# ---------------------------------------------------------------------------
# Regressao: importar o server nao pode encerrar o Kokoro da ponte no ar
# ---------------------------------------------------------------------------

def test_shutdown_so_encerra_kokoro_de_quem_o_subiu():
    """Os arquivos hub_say_* moram no %TEMP% compartilhado: se o _shutdown de
    um processo que apenas importou o modulo (esta suite, um script auxiliar)
    escrever "__quit__", ele mata o speak_server da ponte que esta rodando — e
    a proxima resposta fica "processando" ate o timeout, sem falar nada."""
    assert S.SPEAK_OWNED is False, "importar o server nao pode marcar posse do Kokoro"

    orig = _redirect()
    orig_kill = S.kill_all
    S.kill_all = lambda: None
    try:
        S._shutdown()
        assert not os.path.exists(S.REQ), "_shutdown sem posse nao pode escrever no REQ"

        S.SPEAK_OWNED = True   # agora sim: a ponte dona encerra o seu Kokoro
        try:
            S._shutdown()
            with open(S.REQ, encoding="utf-8") as f:
                assert f.read().strip() == "__quit__"
        finally:
            S.SPEAK_OWNED = False
    finally:
        S.kill_all = orig_kill
        for n, v in orig.items():
            setattr(S, n, v)
