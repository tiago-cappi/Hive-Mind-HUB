#!/usr/bin/env python
"""Servidor de fala persistente para o Voice Hub.

Carrega o modelo Kokoro UMA vez e fica residente, falando textos sob demanda.
Elimina o atraso de carregar o modelo a cada resposta (era o gargalo do delay).

Protocolo por arquivos em TEMP:
  hub_say_req.txt       -> texto a falar (ou "__quit__" para encerrar o servidor,
                            ou "__stream__" para ler o texto de hub_say_stream.txt
                            conforme ele nasce, sem esperar a resposta fechar)
  hub_say_stream.txt    -> modo streaming: texto em append pelo Hub (deltas do turno)
  hub_say_stream_end.txt-> modo streaming: marca que nao vem mais texto
  hub_say_started.txt   -> criado quando o audio comeca a tocar (fala iniciou)
  hub_say_done.txt      -> criado quando termina de falar (sinal para o Hub)
  hub_say_ready.txt     -> criado quando o modelo terminou de carregar
  hub_say_envelope.json -> {"step_ms":N,"levels":[0..1,...]} amplitude da fala,
                            usado pelo Hub p/ animar o grafo em sincronia com o audio
  hub_say_meta.json     -> {"earcon_hz":N,"announce":"txt"} identificacao sonora
                            da sessao (Fase 3): bip curto + anuncio falado do
                            titulo, escritos pelo server.py ANTES do REQ do turno
"""
import os
import re
import json
import time
import queue
import threading
import tempfile
import winsound
import platform

# Blindagem WMI (Python 3.13 trava em queries Win32_*); idem say.py/speak.py.
try:
    platform._uname_cache = platform.uname_result(
        "Windows", os.environ.get("COMPUTERNAME", "pc"), "11", "10.0.26200",
        os.environ.get("PROCESSOR_ARCHITECTURE", "AMD64"))
except Exception:
    pass
platform.win32_ver = lambda *a, **k: ("10", "10.0.26200", "", "")
platform._wmi_query = lambda *a, **k: (_ for _ in ()).throw(OSError("wmi off"))

KDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")
MODEL = os.path.join(KDIR, "kokoro-v1.0.onnx")
VOICES = os.path.join(KDIR, "voices-v1.0.bin")
VOICE = os.environ.get("KOKORO_VOICE", "pf_dora")
LANG = os.environ.get("KOKORO_LANG", "pt-br")
SPEED = float(os.environ.get("KOKORO_SPEED", "1.0"))
CHUNK_CHARS = 140  # bloco de sintese; menor = colchao medido em passos mais finos
FIRST_CHARS = 90   # 1o bloco menor ainda: primeiro audio pronto mais cedo
ENV_STEP_MS = 60   # resolucao do envelope de amplitude usado p/ animar o grafo
# onnxruntime sem SessionOptions usa o default do ORT, que nesta CPU hibrida
# (i5-1235U: 2 P-cores + 8 E-cores) espalha threads nos nucleos lentos. Medido:
# rtf 2.86 no default vs 2.02 com 6 threads intra-op -> 30% de sintese de graca.
THREADS = int(os.environ.get("KOKORO_THREADS", "6"))
HEADROOM_S = float(os.environ.get("KOKORO_HEADROOM", "2.0"))  # colchao minimo de audio
SAFETY = float(os.environ.get("KOKORO_SAFETY", "1.15"))       # folga na regra de largada

TMP = os.environ["HUB_SPEAK_TEMP"]
REQ = os.path.join(TMP, "hub_say_req.txt")
STREAM = os.path.join(TMP, "hub_say_stream.txt")
STREAM_END = os.path.join(TMP, "hub_say_stream_end.txt")
STARTED = os.path.join(TMP, "hub_say_started.txt")
DONE = os.path.join(TMP, "hub_say_done.txt")
READY = os.path.join(TMP, "hub_say_ready.txt")
ENVELOPE = os.path.join(TMP, "hub_say_envelope.json")
META = os.path.join(TMP, "hub_say_meta.json")
WAV = os.path.join(TMP, "claude_hub_say.wav")


def clean(text):
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    text = re.sub(r"`[^`]*`", " ", text)
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"\[\[([^\]]*)\]\]", r"\1", text)
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"[\U0001F000-\U0001FFFF]", " ", text)
    text = re.sub(r"[\U00002600-\U000027BF]", " ", text)
    text = re.sub(r"\s*[—–]\s*", ", ", text)
    text = re.sub(r"[#>*_~|\\]{1,}", " ", text)
    text = re.sub(r"[\[\]{}<>]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text.encode("utf-8", errors="ignore").decode("utf-8")


def build_levels(samples, sr, step_ms):
    # RMS cru por janela; a normalizacao fica no write_envelope, porque em
    # streaming o pico da fala so e conhecido conforme o audio vai nascendo.
    win = max(1, int(sr * step_ms / 1000))
    out = []
    for i in range(0, len(samples), win):
        seg = samples[i:i + win]
        if len(seg):
            out.append(float((seg.astype("float64") ** 2).mean()) ** 0.5)
    return out


def write_envelope(raw):
    # Serie 0..1 que o frontend usa pra animar o grafo em sincronia com o audio.
    # Reescrita a cada bloco (o Hub le de novo e manda os niveis novos ao front);
    # os.replace mantem a leitura atomica.
    peak = max(raw) if raw else 0.0
    if peak <= 0:
        return
    try:
        with open(ENVELOPE + ".tmp", "w", encoding="utf-8") as f:
            json.dump({"step_ms": ENV_STEP_MS,
                       "levels": [round(min(1.0, lv / peak), 3) for lv in raw]}, f)
        os.replace(ENVELOPE + ".tmp", ENVELOPE)
    except OSError:
        pass


def mark_started():
    try:  # sinaliza ao Hub que a fala comecou de fato (item 2)
        open(STARTED, "w").close()
    except Exception:
        pass


SENT = re.compile(r"(?<=[.!?…:;])\s+")


def take_units(buf, force, limit, first_limit=None):
    """Corta o buffer em unidades falaveis completas -> (unidades, resto).

    So corta em fim de frase: cortar no meio deixa a prosodia do Kokoro errada.
    Sem `force`, a ultima frase (possivelmente incompleta) volta como resto.
    """
    if not force and buf.count("```") % 2:
        return [], buf                     # bloco de codigo aberto: espera fechar
    parts = SENT.split(buf)
    tail = "" if force else parts.pop()
    if tail and len(tail) > 2 * limit:     # frase interminavel: corta no espaco
        cut = tail.rfind(" ")
        if cut > 0:
            parts.append(tail[:cut])
            tail = tail[cut + 1:]
    units, cur, lim = [], "", first_limit or limit
    for p in parts:
        if cur and len(cur) + len(p) + 1 > lim:
            units.append(cur)
            cur, lim = p, limit
        else:
            cur = (cur + " " + p).strip()
    if cur:
        units.append(cur)
    return units, tail


class TextSource:
    """Texto a falar: pronto de uma vez, ou nascendo em STREAM (append do Hub)."""

    def __init__(self, text=None, head=""):
        self.buf = head + (text or "")
        self.streaming = text is None
        self.closed = not self.streaming
        # chars de texto ja conhecidos (entregues ou nao). O que falta sintetizar
        # e `total - chars_sintetizados`: contar pelo buffer daria zero assim que
        # as unidades saem daqui, e a largada aconteceria cedo demais.
        self.total = len(self.buf)

    def units(self):
        pos, idle, first = 0, 0, True
        while True:
            if self.streaming:
                try:
                    with open(STREAM, "r", encoding="utf-8", errors="replace") as f:
                        f.seek(pos)
                        new = f.read()
                        pos = f.tell()
                except OSError:
                    new = ""
                if new:
                    self.buf += new
                    self.total += len(new)
                    idle = 0
                elif os.path.exists(STREAM_END):
                    self.closed = True
            got, self.buf = take_units(self.buf, self.closed, CHUNK_CHARS,
                                       FIRST_CHARS if first else None)
            for u in got:
                first = False
                yield u
            if got:
                continue
            if self.closed:
                return
            idle += 1
            if idle > 2400:               # 2min sem texto novo: o Hub sumiu
                return
            time.sleep(0.05)


def speak(kokoro, np, sf, src):
    """Sintetiza numa thread e toca num stream de audio unico e continuo.

    A REGRA DE LARGADA e o coracao disto. Medido nesta maquina: a sintese custa
    ~2x a duracao do audio (rtf~2), ou seja a fala consome mais rapido do que a
    sintese produz. Por isso o pipeline antigo gaguejava: largava no 1o trecho e
    era alcancado no meio. Aqui o consumidor so larga quando o colchao ja cobre
    tudo o que ainda falta produzir: B >= R*(rtf-1), com B = audio pronto e
    R = audio que falta sintetizar. Com rtf~2 isso e "metade pronta" -> corta um
    terco do tempo total e nao gagueja; numa maquina com rtf<1 a condicao fica
    trivial e a fala comeca no primeiro colchao, sem mudar nada aqui.
    """
    blocks = queue.Queue()
    st = {"audio": 0.0, "synth": 0.0, "chars": 0, "queued": 0.0, "sr": 24000,
          "eof": False}
    raw_levels = []
    lock = threading.Lock()

    def produce():
        try:
            for unit in src.units():
                raw = len(unit)          # chars brutos: mesma unidade de src.total
                unit = clean(unit)
                if not unit:
                    with lock:
                        st["chars"] += raw
                    continue
                t = time.time()
                s, sr = kokoro.create(unit, voice=VOICE, speed=SPEED, lang=LANG)
                el, dur = time.time() - t, len(s) / sr
                with lock:
                    st["sr"], st["audio"] = sr, st["audio"] + dur
                    st["synth"] += el
                    st["chars"] += raw
                    st["queued"] += dur
                blocks.put(s)
                raw_levels.extend(build_levels(s, sr, ENV_STEP_MS))
                write_envelope(raw_levels)
        finally:
            st["eof"] = True
            blocks.put(None)

    threading.Thread(target=produce, daemon=True).start()

    while not st["eof"]:
        with lock:
            audio, synth, chars, B = st["audio"], st["synth"], st["chars"], st["queued"]
        if audio > 0:
            rtf = synth / audio
            R = max(0.0, src.total - chars) * (audio / chars)   # audio que falta
            if rtf <= 1.0:
                if B >= HEADROOM_S:
                    break
            elif src.closed and B >= R * (rtf - 1) * SAFETY + HEADROOM_S:
                break
        time.sleep(0.1)

    try:
        import sounddevice as sd
    except Exception:
        sd = None
    if sd is None:                        # sem PortAudio: caminho antigo (WAV)
        pieces = []
        while True:
            blk = blocks.get()
            if blk is None:
                break
            pieces.append(blk)
        if not pieces:
            return
        sf.write(WAV, np.concatenate(pieces), st["sr"])
        mark_started()
        winsound.PlaySound(WAV, winsound.SND_FILENAME)
        return

    stream = None
    try:
        while True:
            blk = blocks.get()
            if blk is None:
                break
            with lock:
                st["queued"] -= len(blk) / st["sr"]
            if stream is None:
                # Um unico device aberto do inicio ao fim: sem o clique/gap que
                # o winsound dava ao reabrir o dispositivo a cada trecho.
                stream = sd.OutputStream(samplerate=st["sr"], channels=1,
                                         dtype="float32")
                stream.start()
                mark_started()
            stream.write(np.ascontiguousarray(blk, dtype="float32"))
    finally:
        if stream is not None:
            try:
                stream.stop()   # drena o que ja esta no buffer antes de fechar
                stream.close()
            except Exception:
                pass


def main():
    import numpy as np
    import soundfile as sf
    import onnxruntime as rt
    from kokoro_onnx import Kokoro
    # kokoro_onnx cria a InferenceSession sem SessionOptions; injetar a sessao
    # por from_session e o unico jeito de fixar os threads sem tocar na lib.
    try:
        so = rt.SessionOptions()
        so.intra_op_num_threads = THREADS
        so.inter_op_num_threads = 1
        so.graph_optimization_level = rt.GraphOptimizationLevel.ORT_ENABLE_ALL
        kokoro = Kokoro.from_session(
            rt.InferenceSession(MODEL, sess_options=so,
                                providers=["CPUExecutionProvider"]), VOICES)
    except Exception:
        kokoro = Kokoro(MODEL, VOICES)  # carga unica (uns segundos, so na abertura)
    try:
        open(READY, "w").close()
    except Exception:
        pass

    while True:
        if not os.path.exists(REQ):
            time.sleep(0.12)
            continue
        try:
            with open(REQ, "r", encoding="utf-8", errors="replace") as f:
                raw = f.read()
            os.remove(REQ)
        except Exception:
            time.sleep(0.05)
            continue
        if raw.strip() == "__quit__":
            break
        # Fase 3: le o meta (earcon + anuncio) deste turno, se o server.py
        # escreveu um antes do REQ. Meta e' por-turno: consome e apaga.
        earcon_hz, announce = None, ""
        if os.path.exists(META):
            try:
                with open(META, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                earcon_hz, announce = meta.get("earcon_hz"), (meta.get("announce") or "")
            except Exception:
                pass
            try:
                os.remove(META)
            except OSError:
                pass
        # limpa sentinelas do turno anterior: o produtor e a autoridade do
        # ciclo (evita o servidor ver um STARTED/DONE/ENVELOPE obsoleto -> race).
        for s in (STARTED, DONE, ENVELOPE):
            try:
                os.remove(s)
            except OSError:
                pass
        # "__stream__": o texto nao esta pronto ainda; nasce em STREAM enquanto o
        # Claude escreve, e a sintese ja comeca pela 1a frase (o clean passa a
        # ser aplicado por unidade, dentro do produtor).
        head = (announce + ". ") if announce else ""
        if raw.strip() == "__stream__":
            src = TextSource(head=head)   # pelo construtor: `total` conta o anuncio
        else:
            src = TextSource(clean(head + raw))
        if src.streaming or src.buf:
            try:
                if earcon_hz:  # 3A: bip curto de identidade da sessao, antes da fala
                    try:
                        winsound.Beep(int(earcon_hz), 200)
                    except (ValueError, RuntimeError):
                        pass
                speak(kokoro, np, sf, src)
            except Exception:
                pass
        try:
            open(DONE, "w").close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
