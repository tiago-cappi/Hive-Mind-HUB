# Pipeline de voz e TTS (Kokoro residente)

> Estado do código em 20/08/2026. Fontes: server.py, speak_server.py, forestos.html, forestos/.

Este documento cobre tudo o que acontece entre "o Hub tem um texto para falar" e
"o áudio saiu na caixa de som": o árbitro de fala do `server.py`, o servidor
residente `speak_server.py` (Kokoro), o protocolo de arquivos-sentinela
`hub_say_*`, o modo streaming `__stream__`, earcon/anúncio de título, os eventos
NDJSON e os watchdogs. Para a visão geral do Hub veja `arquitetura.md`; para as
demais rotas HTTP, `servidor-api.md`; para o lado do navegador (medidor de
áudio, abas), `frontend.md`.

> **AVISO — protocolo de dois lados.** O protocolo `hub_say_*` (sentinelas) e o
> modo `__stream__`/`__quit__` são implementados em **dois processos
> diferentes**: `server.py` (neste repo) e `speak_server.py` (fora do repo, em
> `hub_runtime/voice/speak_server.py`).
> **Qualquer mudança no protocolo exige mexer nos DOIS arquivos.** Já houve bug
> real por causa disso: o `speak_server.py` antigo não conhecia
> `__stream__`/`__quit__` e o Hub "só falava Sessão N" (o anúncio) sem nunca
> falar a resposta. Se alterar nomes de arquivo, ordem de escrita, marcadores
> especiais ou o formato do `hub_say_meta.json`, atualize os dois lados e rode
> `python -m pytest tests/test_speak_stream.py -q`.

> Atualização de 08/10/2026: residente, venv e modelos agora ficam no projeto.
> `HUB_SPEAK_TEMP` compartilha entre os dois lados um canal por instalação,
> em `%TEMP%/core_hub_<hash-da-raiz>`; nomes e ordem dos sentinelas preservados.
> Configuração e recuperação: `runtime.md`.

## 1. Arquitetura em duas peças

| Peça | Onde vive | Papel |
|---|---|---|
| `server.py` (árbitro) | raiz deste repo | Recebe pedidos de fala (`POST /speak` ou fala em streaming do `/ask`), enfileira em `SPEAK_Q` e conversa com o Kokoro por arquivos em `%TEMP%` |
| `speak_server.py` (Kokoro residente) | `hub_runtime/voice/speak_server.py` (constante `SPEAK_SRV` do `server.py`) | Carrega o modelo Kokoro **uma única vez** e fica em loop lendo pedidos; sintetiza (kokoro-onnx, CPU, 100% local) e toca via `sounddevice` |

Detalhes do residente:

- É spawnado por `start_speak_server()` no boot da ponte, usando o Python do
  venv do Kokoro (`KPY = hub_runtime/voice/.venv/Scripts/python.exe`),
  com `CREATE_NO_WINDOW` e stdout/stderr em `DEVNULL` (sob `pythonw` o handle
  herdado é inválido; um `print` do kokoro_onnx quebraria a síntese em silêncio).
- Modelo: `kokoro-v1.0.onnx` + `voices-v1.0.bin` em
  `hub_runtime/voice/models/` (provisionados localmente). Voz
  padrão `pf_dora`, idioma `pt-br` (env `KOKORO_VOICE` / `KOKORO_LANG`).
- Ambiente recriável por `hub_runtime/voice/requirements-lock.txt`; saída do residente é redirecionada pela ponte.
- A flag `SPEAK_OWNED` garante que só o processo que **subiu** o Kokoro pode
  encerrá-lo no `atexit` (`_shutdown()`): como os arquivos `hub_say_*` moram no
  `%TEMP%` compartilhado, um processo que apenas importasse `server.py` (a suíte
  de testes, um script auxiliar) mandaria `__quit__` ao sair e mataria o Kokoro
  da ponte que está no ar. Coberto por
  `tests/test_speak_stream.py::test_shutdown_so_encerra_kokoro_de_quem_o_subiu`.

## 2. A fila SPEAK_Q — por que a fala é serializada

```python
SPEAK_Q = queue.Queue()          # itens: {"sid","reply","earcon_hz","announce","events":Queue}
SPEAK_BUSY = threading.Event()   # um job de fala em andamento
```

Um único `speak_worker()` (thread daemon) consome a fila e chama `_do_speak(job)`
job a job. Como a reprodução no `speak_server.py` bloqueia até o áudio terminar
(`sd.wait()`), o worker só pega o próximo job quando o atual acaba —
**serialização de graça**: é impossível duas sessões (abas) falarem ao mesmo
tempo, mesmo com vários processos `claude` respondendo em paralelo. Cada job
carrega sua própria `Queue` de eventos (`events`), por onde `_do_speak` devolve
`speak_start`/`speak_env`/`speak_done` para quem enfileirou (o `/speak` ou o
`SpeakStream` do `/ask`).

## 3. Protocolo de arquivos entre os dois processos

Todos em `tempfile.gettempdir()` (`%TEMP%`). Nomes exatos (constantes idênticas
nos dois arquivos):

| Arquivo | Constante | Quem escreve | Quem lê | Significado |
|---|---|---|---|---|
| `hub_say_req.txt` | `REQ` | server.py | speak_server.py | Texto a falar; `__stream__` = texto vem por STREAM; `__quit__` = encerrar o residente |
| `hub_say_meta.json` | `META` | server.py | speak_server.py | `{"earcon_hz": int\|null, "announce": "<título da sessão>"}` — gravado **antes** do REQ |
| `hub_say_stream.txt` | `STREAM` | server.py (append) | speak_server.py | Streaming: o texto da resposta nascendo |
| `hub_say_stream_end.txt` | `STREAM_END` | server.py | speak_server.py | Streaming: sentinela de fim do texto |
| `hub_say_ready.txt` | `READY` | speak_server.py (1x) | server.py | Modelo Kokoro carregado |
| `hub_say_envelope.json` | `ENVELOPE` | speak_server.py | server.py | `{"levels":[0..1], "step_ms":40}` — níveis RMS p/ o medidor do front; **reescrito a cada trecho** no streaming |
| `hub_say_started.txt` | `STARTED` | speak_server.py | server.py | O áudio de fato começou a tocar |
| `hub_say_done.txt` | `DONE` | speak_server.py | server.py | O áudio terminou |

Ordem de um turno de fala (caminho não-streaming), em `_do_speak`:

1. server.py apaga `STARTED`, `DONE`, `ENVELOPE`, `STREAM`, `STREAM_END`.
2. server.py grava `META` (earcon + anúncio) e **depois** `REQ` (o texto) — o
   residente lê o META assim que vê o REQ.
3. speak_server.py sintetiza o anúncio e o texto principal, grava o `ENVELOPE`,
   toca o earcon (`winsound.Beep(earcon_hz, 120)`), grava `STARTED`, toca
   anúncio + resposta.
4. Ao terminar, o residente remove `REQ`/`META` **antes** de gravar `DONE` — a
   ordem inversa apagava o pedido seguinte, porque o server.py já escreve o
   próximo `REQ` assim que vê o `DONE`.
5. server.py vê `DONE`, remove `STARTED`/`DONE` e emite `speak_done`.

## 4. Streaming `__stream__` (fala com a resposta ainda nascendo)

A síntese custa ~2x a duração do áudio nesta máquina; em resposta longa, esperar
o turno fechar dobraria a latência. Por isso o `/ask` pode começar a falar pela
primeira frase, junto com a escrita do Claude.

Lado server.py (classe `SpeakStream`):

- Habilitado por `SPEAK_STREAM` (env `HUB_SPEAK_STREAM`, default ligado) e
  acionado quando o turno já acumulou `SPEAK_MIN` chars de texto
  (env `HUB_SPEAK_MIN`, default **320**) **e** o árbitro está livre. Se outra
  sessão está falando, o turno cai no `/speak` clássico do fim, como antes.
- Esse "o árbitro está livre?" passa por **`try_speak_stream()`**, sob o
  **`SPEAK_GATE`**: a checagem (`SPEAK_Q.empty()` e `SPEAK_BUSY` desarmado) e o
  enfileiramento são um passo só. Escritos separados, viram um TOCTOU — N abas
  que cruzam o `SPEAK_MIN` no mesmo instante veem a fila vazia *antes* de
  qualquer uma enfileirar e abrem vários streamings sobre o **mesmo** canal de
  texto. Medido com `sys.setswitchinterval(1e-6)` e 8 abas: 4 a 6 passavam ao
  mesmo tempo sem o gate. Ver `tests/test_concorrencia.py`.
- `SpeakStream` enfileira na **mesma** `SPEAK_Q` um job com `"stream": True` e
  um `threading.Event` `go`. Quando o worker chega nesse job, `_do_speak` zera o
  `STREAM`, escreve `REQ = "__stream__"` e arma o `go`; só então o `feed(txt)`
  passa a fazer **append** do texto em `STREAM` (antes disso o texto fica retido
  em `self.buf`).
- `close()` espera o `go` (timeout 120 s), descarrega o buffer e grava
  `STREAM_END` — sempre **depois** do último append, para o residente saber que
  a última leitura já traz o texto completo.
- **Só o dono do canal marca o fim.** `STREAM` e `STREAM_END` são arquivos
  únicos, compartilhados por todas as sessões. Um job que ainda espera a vez
  (sem `go`) nunca escreveu no `STREAM`: o `STREAM_END` dele fecharia o texto de
  **outra** sessão, cortando a fala dela no meio da frase. Por isso `_mark_end()`
  só grava se `go` estiver armado; sem ele, apenas registra `want_end`, e o
  `_watchdog` — que também espera o `go` — cumpre o fechamento quando a vez
  chegar. O watchdog nunca fecha com `buf` cheio, exceto no caso de fome (45 s),
  em que descarrega (`_flush()`) antes de marcar. O `buf` é compartilhado entre
  `feed()` e o watchdog, daí o `buf_lock`.
- Os eventos de fala saem pelo NDJSON do **próprio `/ask`** (não do `/speak`),
  e o evento `done` do `/ask` leva `"spoken": true` para o front não chamar o
  `/speak` de novo.

Lado speak_server.py (`_stream_turn`):

- Um thread produtor relê `STREAM` a partir da posição anterior (decoder UTF-8
  incremental) e fatia o buffer com `_take_chunk`: corta na última fronteira de
  frase (`_SENT_BOUND = [.!?…;:]` + fecha-aspas + espaço) desde que o trecho
  tenha ao menos `STREAM_MIN = 60` chars; sem fronteira até `STREAM_MAX = 400`
  chars, corta no último espaço. Cada trecho é sintetizado e vai para uma fila
  de áudio (`maxsize=8`); o `ENVELOPE` cresce a cada trecho (o server.py o relê
  durante a fala e repassa os níveis novos ao front como `speak_env`).
- **Regra de largada:** earcon + anúncio + `STARTED` só saem quando o primeiro
  trecho já tem áudio pronto, para a fala não abrir e gaguejar esperando síntese.
- Ao ver `STREAM_END` (e esvaziar o buffer), o produtor encerra; o principal
  toca tudo na ordem e remove `STREAM`/`STREAM_END`.

O `__quit__` funciona no mesmo canal `REQ`: `stop_speak_server()` escreve
`__quit__` e o loop principal do residente remove `REQ`/`META` e sai. É assim
que a ponte encerra o Kokoro no `atexit` (e só a ponte dona — ver seção 1).

## 5. Earcon e anúncio de título por sessão

Cada aba do front tem um bip próprio: `EARCON_HZ = [392,440,494,523,587,659,698,784]`
no `index.html` (escala G4→G5, indexada pela ordem de criação da aba). O front
manda `earcon_hz` e `titulo` em todo `/ask` e `/speak`; o server.py os grava no
`hub_say_meta.json` (`earcon_hz` + `announce`) e o residente toca
`winsound.Beep(hz, 120)` seguido do título sintetizado ("Sessão 2", etc.)
**antes** da resposta — identificação sonora de quem está respondendo sem olhar
a tela. O alarme de lembretes do ForestOS também usa esse canal (POST `/speak`
sem `earcon_hz`; ver `forestos.md`).

## 6. Eventos NDJSON do /speak

`POST /speak` (`{reply, sid, titulo, earcon_hz}`) responde
`application/x-ndjson` em streaming:

| Evento | Campos | Quando |
|---|---|---|
| `speak_queued` | `pos` (posição na fila do árbitro) | Imediatamente ao enfileirar |
| `speak_start` | `start_ms` (ms desde o início do job), `ready` (READY existe), `envelope` (níveis 0..1), `step_ms` | Quando o residente grava `STARTED` — o áudio **começou a tocar de fato** |
| `speak_env` | `levels` (só os níveis novos desde o último envio) | Durante a fala em streaming, conforme o `ENVELOPE` cresce |
| `speak_done` | `ok`, `ready`, `started`, `spoke_ms`, `chars`, `timeout` | Quando o residente grava `DONE` (ou estoura o watchdog: `ok:false, timeout:true`) |

Exceção dentro do worker vira `{"t":"speak_done","ok":false,"error":...}`. Na
fala em streaming, esses mesmos eventos saem pelo NDJSON do `/ask` (mais o
`done` com `spoken:true`).

## 7. Timeouts e watchdogs (valores reais)

| Watchdog | Valor | Onde | O que cobre |
|---|---|---|---|
| Espera pelo `STARTED` | 12000 × 0,05 s = **600 s** | `_do_speak` (laço 1) | O residente só larga quando tem colchão de áudio; resposta longa pode demorar a ordem de grandeza da própria fala |
| Espera pelo `DONE` | 12000 × 0,05 s = **600 s** | `_do_speak` (laço 2) | Fala completa; a cada 0,5 s relê o `ENVELOPE` e emite `speak_env` |
| Fome de texto no streaming | **45 s** sem sinal de vida | `SpeakStream._watchdog` | Turno morto no meio (ESC, aba fechada): grava `STREAM_END` sozinho para não prender o árbitro e emudecer o turno seguinte. **Sinal de vida ≠ texto novo:** o `/ask` chama `SpeakStream.alive()` a cada evento do processo e a cada heartbeat, então uma ferramenta longa (Bash, subagente, build) no meio da resposta **não** fecha mais o canal. Antes fechava: o Kokoro falava só o texto anterior à ferramenta e a resposta de verdade saía na tela sem nunca ser falada — com o turno ainda devolvendo `spoken: true`, o que tirava até o `/speak` do fim do caminho. Coberto por `tests/test_speak_stream.py::test_watchdog_fecha_o_texto_se_o_turno_morrer` e `::test_alive_segura_o_watchdog_enquanto_o_turno_pensa` |
| Espera pelo `go` no `close()` | **120 s** | `SpeakStream.close` | Sem isso o fim do texto seria marcado antes de o job virar o atual |

Correlatos fora da fala (documentados em `servidor-api.md`, testados em
`tests/test_watchdog.py`): o watchdog de ociosidade do `/ask` usa
`INACT_BOOT = 90 s` / `INACT_IDLE = 300 s` / `INACT_TOOL = 1200 s` conforme o
que o processo `claude` estava fazendo quando calou.

### O outro lado do pipeline: o STT também tem teto

Esses watchdogs cobrem da pergunta para frente. **Antes** deles existe a captura,
que é o outro trecho lento do turno — e era o único sem proteção nenhuma. O
`/stt` é síncrono e o faster-whisper roda na CPU a ~0,7× o tempo real (`base`)
ou ~0,37× (`small`), medido nesta máquina: 3 minutos de fala custam ~4 minutos de
transcrição. Um caso real de 4 min 42 s deixou o HUD em PROCESSANDO por ~13 min,
sem transcript e sem resposta — o `/ask` nunca chegou a ser chamado.

| Teto | Valor | Onde | O que cobre |
|---|---|---|---|
| Gravação | `REC_MAX_S = 180 s` | `armRecCap()` (`index.html`) | Avisa em banner e **envia** o que já foi falado, em vez de deixar a fala crescer sem limite |
| Transcrição | `STT_MAX_MS = 420000` (7 min) | `onRecStop()` (`index.html`) | `tab.sttCtrl.abort()` → banner + `finishIdle`; o ENCERRAR usa o mesmo `sttCtrl` |
| Concorrência | `STT_LOCK` | `/stt` (`server.py`) | Guarda nomeada do `WMODEL` (regra 5): faster-whisper não é thread-safe e o Flask é `threaded=True` |

**A montante do teto está a captura.** `getMic()` desliga `echoCancellation`,
`noiseSuppression` e `autoGainControl` (`MIC_CONSTRAINTS`): com os defaults do
Chrome o áudio chegava ao whisper com 4,3% da energia na banda de
inteligibilidade (1–3,4 kHz) e 41% abaixo de 300 Hz, e a transcrição voltava
repetida. Modelo maior não conserta áudio abafado — detalhe em `frontend.md` §6.

Durante a transcrição o HUD mostra `TRANSCREVENDO` com cronômetro (`setStep` a
cada 200 ms): a diferença entre "lento" e "travado" tem de ser visível. Detalhes
do front em `frontend.md` §6; da rota em `servidor-api.md` §2.

## 8. Caso-limite conhecido: sentinela tardio

Se uma síntese individual travar por minutos (sintoma de o `speak_server.py` já
estar com problema), `_do_speak` desiste de esperar o `DONE` após os 600 s e
emite `speak_done` com `timeout:true`. O job **seguinte** então escreve seu
`REQ` — mas o residente ainda está preso no job abandonado. Quando ele enfim
termina, o `finally` dele faz `_rm(REQ, META)` (apagando o pedido novo!) e grava
`DONE`, que o job seguinte pode ler como se fosse o próprio término. Resultado:
um turno "falado" instantaneamente sem áudio. Não acontece no dia a dia normal —
exige uma síntese estourar a janela de 600 s — e a recuperação é reiniciar o Hub
(ou só o residente); ver `operacao.md`.

## 9. Testes

```
python -m pytest tests/test_speak_stream.py -q   # streaming ponta a ponta (com dublê do Kokoro), watchdog de texto, posse do __quit__
python -m pytest tests/test_concorrencia.py -q   # N sessões: fala serializada, SPEAK_GATE, posse do canal de texto
python -m pytest tests/test_watchdog.py -q       # watchdog do /ask, /abort, kill em árvore
```

`test_speak_stream.py` redireciona as constantes do protocolo (`REQ`, `STREAM`,
`STREAM_END`, `STARTED`, `DONE`, `ENVELOPE`, `META`, `READY`) para arquivos
`tspk_*` de teste — nada de Kokoro nem áudio real, e sem colidir com um
residente em execução.
