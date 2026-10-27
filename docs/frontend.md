# Front-end do Hub C.O.R.E. — `index.html`

> Extensão de 08/10/2026: o minimalista inclui o seletor Claude Code/Codex e
> o tema/galáxia do protótipo aprovado. Os painéis continuam compartilhados,
> com sessões separadas. O backend Codex está pendente. Ver
> [codex-frontend.md](codex-frontend.md) para módulos, contratos e limites.

> Estado do código em 20/08/2026. Fonte: index.html.

## Hive Mind (atualizado em 21/10/2026)

No modo minimalista há uma terceira página, **Hive Mind**, montada dentro de `/`
pela tag `<script type="module" src="/hive-ui/static/app.js">`; o `index.html`
não ganha mais nada. Ela não é um provedor de chat e não usa voz, STT ou TTS,
mas o modo real (padrão) roda missões com Claude e Codex pelo backend
`/hive-api`; a demonstração é separada e nunca controla missão real. A troca
preserva provider, sid, rascunhos e gavetas do Hub. Referência completa:
[hivemind/README.md](hivemind/README.md) e [hivemind/frontend.md](hivemind/frontend.md).

O front inteiro é um único arquivo (`index.html`, ~3050 linhas): CSS, markup e JS
vanilla, sem build step, servido pelo Flask local (`GET /` na porta 8765 — ver
`servidor-api.md`). Fontes: Space Grotesk (display) + JetBrains Mono (telemetria).
Paleta "Hive Mind": fundo preto-quente (`--bg:#14120c`), texto papel
(`--ink:#ECE4D4`), acento dinâmico `--accent` / `--accent-rgb` trocado por JS
conforme o estado. O CSS e o JS são divididos em seções comentadas e numeradas
(CSS 0–9d, JS 1–9); este documento segue essa numeração quando útil.

## 1. Estrutura geral da página

Layout em grid de tela cheia (`.grid`, `100vh`):

| Linha | Altura | Conteúdo |
|---|---|---|
| 1 | `54px` | `.topbar` — marca, fila de status, relógio, seletores de modelo/esforço |
| 2 | `1fr` | `.stage` — palco em 3 colunas |
| 3 | `224px` | `.console` — transcript (abas) + controles |

O palco `.stage` tem 3 colunas: `288px 1fr 288px`:

- **`.col.left`** — painéis *placeholder* (dados mockados): SYSTEM VITALS
  (métricas com sparklines SVG geradas em `spark()`; `#ctxNum` "JANELA CLAUDE" é
  uma métrica fictícia que deriva a cada 3,5 s), DIRECTIVES (checklist estática)
  e VAULT (lista estática de notas recentes).
- **`.core`** (centro) — o núcleo: `#core-canvas` dentro de `.canvas-wrap`, com
  brackets decorativos (`.bracket.tl/.tr/.bl/.br`), rótulos `.corelabel`,
  o rótulo de etapa `#step`, e os overlays de progresso `#errBanner` (F2),
  `#planPanel` (F4), `#liveResp` (F3), `#caption` (legenda do minimalista) e
  `#cancelBtn` (F2). Abaixo, o `.readout`: `#state` (status grande), a barra
  `#meter` (nível de microfone/fala) e a legenda `.meter-cap`.
- **`.col.right`** — COMMAND DECK (`#skills`, 8 botões `.skill` gerados do array
  `SKILLS`) e o painel AUDIO I/O (`#ioBlock`): LED `#ttsLed`, rótulo `#tts`
  (`TTS · STANDBY` / `TTS · SPEAKING`), lembrete de atalhos, `#speakStatus`
  (fila de fala entre abas) e `#soundToggle` (F5).

O rodapé `.console` tem 2 colunas (`1fr 250px`):

- **`#txPanel`** (`.panel.transcript`) — as abas de visão `h3.tabs` (com o tag
  `#tabTag`), o cabeçalho de gaveta `#dockHead` (só visível no minimalista), a
  barra de sessões `#sessiontabs`, as cinco caixas de conteúdo (`#log`, `#chg`,
  `#debug`, `#convs`, `#reps` — só uma visível por vez via `[hidden]`), os
  seletores espelhados `.dock-selects` (`#dockModel`/`#dockEffort`, só no
  minimalista) e a alça de largura `#dockGrip`.
- **`.controls`** — `#modeToggle` (MODO TEXTO), `#textForm`
  (`#textInput` + `#textSend`, oculto no modo voz), `#main` (INICIAR/ENVIAR),
  `#pause`, `#newconv` (NOVA CONVERSA), `#stop` (ENCERRAR) e a dica de atalhos.

Fora do grid ficam: o fundo HUD (`.floor` chão em grade com perspectiva, `.scan`
scanlines, `.vign` vinheta), o botão `#minimalToggle`, as alças de gaveta
`#dockL`/`#dockR`, o modal de composição `#textModalOverlay` e o visor de
relatórios `#repOverlay` (ver `relatorios.md`).

Os painéis usam cantos chanfrados via `clip-path` (`--chamf:11px`) e moldura de
1px desenhada com `mask-composite`. Abaixo de 1100 px o layout empilha
(`@media (max-width:1100px)`), com o núcleo no topo.

## 2. Máquina de estados (idle / listen / think / speak)

O objeto `STATES` define cor de acento e textos de cada estado:

| Estado | `--accent` | `#state` (label) | `#liveStat` | Grafo |
|---|---|---|---|---|
| `idle` | `#B88A3F` (honey-deep) | `ONLINE` | `IDLE` | rotação lenta, respiração |
| `listen` | `#6FA89C` (sage) | `OUVINDO… FALE AGORA` | `LISTEN` | expande com o nível do mic (`audioSm*0.32`) |
| `think` | `#E8B658` (honey) | `PROCESSANDO…` | `THINK` | agitação alta (`jitter:.115`), rotação rápida |
| `speak` | `#7FC4A6` (sage-verde) | `FALANDO…` | `SPEAK` | anéis concêntricos + onda radial de brilho |

`window.setState(s)` (contrato de integração, seção 4 do JS — **não renomear**)
pinta a UI inteira: troca `--accent`/`--accent-rgb` no `:root`, escreve
`document.body.dataset.state`, atualiza `#state` e `#liveStat`, chama
`graph.setMode(s)`, esconde `#step` fora de `think` e zera o nível de áudio fora
de `listen`/`speak`. Os demais contratos globais: `setMeter(pct)` (barra
`#meter` + áudio do grafo), `setStep(texto, segundos)` (rótulo de etapa com
cronômetro), `addLine(quem, texto)`, `setSpeaking(bool)` (pulso do grafo + LED
TTS) e `dbg(nivel, msg)`.

Importante: cada **aba de sessão** tem seu próprio `tab.ui`
(`idle|listen|think|speak`); `applyUiIfActive(tab)` só sincroniza os widgets
singulares (grafo, medidor, `#state`, botões) se a aba for a ativa. O ciclo
completo é `idle → listen → think → speak → idle`; o estado `speak` só acende
quando o evento `speak_start` chega do servidor (o áudio começou de fato a
tocar — ver `voz-tts.md`).

## 3. O grafo 3D do núcleo (`CoreGraph`, seção 3 do JS)

Canvas 2D (não WebGL): uma esfera de Fibonacci com 150 nós (`build(150)`) +
16 nós internos, projetada em 2D com rotação contínua nos eixos Y e X
(`focal=3.3`, `dpr` limitado a 2, `scale = min(w,h)*0.255`). Arestas ligam cada
nó aos 2–3 vizinhos mais próximos (topologia fixa, dedupe via `Set`). O desenho
usa blend aditivo (`globalCompositeOperation='lighter'`): brilho central
radial, retícula HUD de 72 traços girando devagar, arestas, anéis de fala e nós
pintados de trás para frente.

Cada estado define alvos (`setMode`) de `expand/jitter/rot/bright/edge/col` que
os valores correntes perseguem com suavização independente de FPS
(`1 - exp(-dt/170)`), então as transições são contínuas. Contratos do grafo:
`setAudioLevel(v)` (0..1, usado em `listen`/`speak`) e `setSpeaking(b)` — em
`speak`, um anel novo nasce a cada 520 ms e os nós recebem uma onda radial de
brilho. O loop roda em `requestAnimationFrame`; um `setInterval` de 33 ms serve
de reserva **apenas** com a aba oculta (`document.hidden`) para o núcleo não
congelar. `graph.resize()` é chamado ao recolher painéis e ao alternar o
minimalista; um `ResizeObserver` no pai do canvas cuida do resto.

## 4. Barra de abas de sessão (`.sessiontabs`, seções 5 e 9d)

Sessões **paralelas**: 1 aba = 1 `sid` (`makeSid()` → `'s-' + uuid.slice(0,8)`)
= 1 processo `claude` isolado no servidor. As abas ficam em `#sessiontabs`,
renderizadas por `renderTabBar()` como botões `.stab` (classe distinta de `.tab`
de propósito — `.tab` são as abas de **visão**, seção 5 abaixo). Constantes:

- `MAX_TABS = 6` — teto de abas vivas (sincronizado com `MAX_SESS` do servidor);
  o botão `+` (`.stab.splus`) fica `disabled` no teto.
- `EARCON_HZ = [392,440,494,523,587,659,698,784]` — escala G4→G5; cada aba
  recebe um bip próprio (`tab.earconHz`) usado nos blips de progresso e no
  anúncio de fala do servidor.

Anatomia de `.stab`: bolinha de estado `.sdot` (cinza em idle, teal em
`listen`, âmbar em `think`, verde pulsando em `speak`), título ("Sessão N", via
contador `tabSeq`), e o `×` (`.sclose`) de fechar. Aba com resposta pronta em
segundo plano ganha `.unread` (ponto âmbar).

Regras:

### A aba CELULAR (espelho, seção 10 do JS)

Além das abas normais existe uma aba **especial "CELULAR"** (`tab.mirror = true`,
sid fixo `mobile`, ícone 📱): o espelho **somente leitura** da sessão do celular
(`mobile/`, ver `mobile.md`). Ela não nasce no boot — `mobileWatchLoop()` faz
long-poll em `GET /session_watch/mobile` (começando com `rev=-1`, que só
sincroniza o rev atual, sem replay de turnos velhos) e cria a aba na primeira
atividade. Cada linha espelhada passa por `mobileWatchLine(ev)`, que reproduz o
turno com os mesmos widgets das abas normais: o evento `ask` vira a linha `EU`
(a pergunta digitada no celular) e liga `think`; `step`/`hb`/`partial`/
`thinking`/`plan`/`change`/`debug`/`done`/`speak_*` seguem os mesmos handlers do
`streamAsk`. Se a aba ativa estiver ociosa, o espelho **assume o foco** quando
um turno começa no celular; se você estiver no meio de algo, ele fica em segundo
plano e marca `unread` como qualquer aba.

Regras da aba-espelho: nunca chama `/session_start`, `/session_end` nem `/ask`
(o processo `claude` do sid `mobile` pertence ao celular); fechá-la só a tira da
tela (renasce na próxima atividade); o `beforeunload` a pula; e `onMain`/
`onStop`/`onNewConv`/`sendTextPrompt`/`runSkill` são bloqueados nela com um
aviso no DEBUG — para conversar, use o celular ou troque de aba.

- **`addTab()`** — cria a aba, ativa, e chama `POST /session_start` com
  `{modelo, esforco, sid}` para aquecer o processo.
- **`activateTab(i)`** — troca o foco, zera `unread`, repinta transcript,
  overlays e alterações (`renderActiveTranscript()`). **Bloqueada enquanto a
  aba ativa está em `listen`**: trocar de aba no meio da gravação orfanaria o
  `MediaRecorder` (o mic é um só).
- **`closeTab(i)`** — bloqueada se for a última aba ou se `tab.ui !== 'idle'`
  (não mata um `/ask` em curso); remove a aba e chama `POST /session_end`.
- Só a aba **ativa** controla grafo/medidor/estado; abas em segundo plano
  continuam em `think`/`speak` e marcam `unread` ao terminar (`finishIdle`).
- `beforeunload` dispara `navigator.sendBeacon('/session_end', …)` para cada
  aba viva — fechar o HUB encerra todos os processos.
- **NOVA CONVERSA** (`onNewConv`, botão `#newconv`) não fecha a aba: arquiva
  `turns` + `changes` no array `history` (aba CONVERSAS), zera ambos e chama
  `POST /session_reset` no mesmo `sid`. Bloqueado fora de `idle`.

## 5. Abas de visão (TRANSCRIPT / ALTERAÇÕES / DEBUG / CONVERSAS / RELATÓRIOS)

Cinco botões `.tab` em `h3.tabs` do `#txPanel`, com `data-tab` =
`log | chg | debug | convs | reps`. O handler alterna o `[hidden]` das cinco
caixas (a regra `#log[hidden],#debug[hidden],#convs[hidden],#chg[hidden],#reps[hidden]{ display:none !important; }`
garante que só uma aparece) e troca o `#tabTag`:
`LIVE` (transcript), `DIFF` (alterações), `DEBUG`, `HISTÓRICO` (conversas),
`VISUAIS` (relatórios).

- **TRANSCRIPT (`#log`)** — a conversa da aba de sessão ativa: linhas `.line`
  com rótulo `EU` (teal), `CLAUDE` (verde) ou `SISTEMA` (vermelho), teto de 200
  linhas no DOM. Durante um turno, a timeline de atividade (F1,
  `showActivity`) empilha as etapas do servidor ("· lendo x…"); ao concluir,
  cada etapa anterior é fechada com `✓` e duração, e no `done` tudo colapsa
  (`clearActivity`) restando só a resposta final (`finalizeResp` →
  `recordTurn`).
- **ALTERAÇÕES (`#chg`)** — F6: o que o Claude **mudou** na conversa corrente
  da aba. Cada evento NDJSON `{"t":"change","ch":{…}}` vira, via
  `noteChange(tab, ch)`, uma linha `.chg-row`: `EDIT`/`NOVO` + arquivo +
  `+adições −remoções` (clicar expande o diff colorido `.chg-diff`, com aviso
  `… DIFF TRUNCADO` quando `truncated`), ou `CMD`/`FALHOU` + `$ comando` para
  Bash/PowerShell. No topo, `chgSummary` resume: arquivos distintos, `+`/`−`
  somados e comandos. Teto `CHG_MAX = 400` itens por conversa. Badge de não
  vistos no rótulo da aba (`ALTERAÇÕES (n)`). É por **conversa**: NOVA CONVERSA
  arquiva junto com o transcript e zera.
- **DEBUG (`#debug`)** — console estruturado alimentado por
  `window.dbg(level, msg)`: timestamp com milissegundos, nível colorido
  (`INFO/OK/WARN/ERR/NET/STEP`; os rótulos `STT/ASK/SPEAK` reusam a cor de
  info), teto `DEBUG_MAX = 600` linhas, espelho em `console.log('[core]', …)`.
  Recebe eventos de **todas** as abas, prefixados pelo título da sessão. Badge
  `DEBUG (n)` de não lidas quando a aba não está visível.
- **CONVERSAS (`#convs`)** — histórico **arquivado** da janela (array
  `history`, em memória — zera ao fechar o HUB): só ganha entrada quando NOVA
  CONVERSA reseta uma aba. Cada item mostra título, primeiro turno do usuário,
  hora, nº de mensagens e resumo de alterações; clicar abre os turnos em modo
  leitura (`renderConvDetail`, com botão `‹ VOLTAR ÀS CONVERSAS`). Sessões ao
  vivo **não** aparecem aqui — ficam na barra de abas.
- **RELATÓRIOS (`#reps`)** — acervo dos relatórios visuais (global, não por
  sessão). Lista `.rep-item` com título e data (`fmtRepTime` → `DD/MM HH:MM`);
  clicar abre o visor. Badge `RELATÓRIOS (n)`. Detalhes completos em
  `relatorios.md`.

## 6. Fluxo de voz

```
INICIAR (#main / Enter / clique no palco no minimalista)
  └─ startListening(): getMic() → MediaRecorder(rec.start(250)) → estado listen
       getMic tenta o default e cai para enumerateDevices por deviceId
       falhou tudo → lança o erro REAL do default via micErrText (nome +
         mensagem + dica: NotAllowedError = permissão; NotReadableError =
         dispositivo não abriu — em uso, driver ou antivírus) + nº de devices
       MIC_CONSTRAINTS desliga aec/ns/agc nos DOIS caminhos (ver abaixo)
       pickMime escolhe o primeiro mimeType suportado (webm/opus → webm → ogg → mp4)
       startMeter(): AnalyserNode (fftSize 512) → setMeter() → grafo reage
       armRecCap(): teto de REC_MAX_S (180 s) — ao bater, avisa e envia
ENVIAR (#main de novo / Enter / teto de 180 s)
  └─ sendTurn(): clearRecCap() → rec.stop() → onRecStop(tab)
       estado think + setStep('TRANSCREVENDO', s) com cronômetro de 200 ms
       Blob dos chunks → POST /stt (FormData "audio" + "sid") → {texto}
       tab.sttCtrl (AbortController) + teto STT_MAX_MS (420 s)
       texto vazio → aborta com WARN; senão recordTurn(tab,'EU',texto)
  └─ askAndSpeak(tab, texto): estado think
       streamAsk(): POST /ask {texto, modelo, esforco, sid, titulo, earcon_hz}
         resposta NDJSON, lida por reader/getReader linha a linha:
         · step      → etapa amigável: setStep + timeline F1 + blip F5
         · hb        → watchdog F2: tab.idleS/idleLimit/idleTool → applyWatchdog
         · partial   → resposta nascendo (F3, #liveResp, últimos 600 chars)
         · thinking  → volume de raciocínio (F3, "RACIOCINANDO · n chars")
         · change    → F6 → noteChange (aba ALTERAÇÕES)
         · plan      → F4 → renderPlan (#planPanel, checklist do TodoWrite)
         · debug     → dbg(); ERR também vira banner (#errBanner)
         · done      → {reply, spoken}; spoken=true = a voz correu em streaming
                        dentro do próprio /ask (finalizeResp imediato)
         · error     → banner + dbg ERR
         · speak_*   → handleSpeakEvent (fala em streaming)
       se !spoken → POST /speak {reply, sid, titulo, earcon_hz} (NDJSON):
         speak_queued {pos} → fila global renderSpeakStatus (#speakStatus)
         speak_start {envelope, step_ms} → estado speak + setSpeaking(true)
                     + startSpeakMeter (medidor caminha pelo envelope real)
         speak_env {levels} → mais níveis (o áudio nasce em streaming)
         speak_done → medidor zera
  └─ finishIdle(tab): volta ao idle; aba em 2º plano marca unread
```

Watchdog visual (F2): `applyWatchdog` pinta `#step` com `.warn` a partir de 34%
do teto de ociosidade (`hb.limit_s`, default 90 s) e `.crit` + botão
`#cancelBtn` a partir de 75%. `announceProgress` (F5) enfileira um "ainda
trabalhando: …" falado a cada 45 s de silêncio (`tab.nextAnnounce`), só com o
som ligado e a aba em `think`. O toggle `#soundToggle` persiste em
`localStorage` `hub_sound_progress` (padrão **ligado**); os blips usam WebAudio
(`blip(hz)` na frequência da aba), destravado no primeiro gesto do usuário.

**ENCERRAR** (`onStop`, botão `#stop` ou Esc): aborta o fetch do `/ask`
(`tab.askCtrl.abort()`) **e** chama `POST /abort {sid}` — abortar só o fetch
deixaria o processo produzindo e a sobra vazaria no turno seguinte. Aborta
também o fetch do `/stt` (`tab.sttCtrl.abort()`) e desarma o teto de gravação
(`clearRecCap()`): sem isso o ENCERRAR não alcançava a transcrição, que ao
voltar ainda disparava o `/ask` numa aba já em repouso — por isso `onRecStop`
checa `tab.ui==='idle'` depois do `await` e descarta o turno. **PAUSAR**
(`onPause`, Espaço) pausa/retoma o `MediaRecorder` durante a escuta; o teto de
gravação é relógio de parede e **não** para na pausa (o custo do STT é o mesmo).

### Captura: o DSP do Chrome fica desligado

`getMic()` pede `{audio: MIC_CONSTRAINTS}` com `echoCancellation`,
`noiseSuppression` e `autoGainControl` em **`false`** — nos dois caminhos (mic
default e o fallback por `deviceId`). Com o `{audio:true}` anterior o Chrome
ligava os três por padrão, e o AEC3 come justamente a banda que o whisper usa:
medido no áudio de um turno real, sobrava **4,3%** da energia entre 1–3,4 kHz
(o normal é 15–30%) contra **41%** abaixo de 300 Hz — som abafado, e a
transcrição voltava repetida e incoerente ("...a dor, dor, dor... o cache o
cache o cache..."). Aqui não há eco a cancelar: a fala é em turno e o mic é
próximo. `startListening` registra em DEBUG o que o navegador de fato aceitou
(`tk.getSettings()` → `mic dsp: aec=… ns=… agc=…`), porque uma constraint pode
ser ignorada em silêncio.

### Tetos da fase de voz

| Constante | Valor | O que faz |
|---|---|---|
| `REC_MAX_S` | `180` (s) | teto da gravação: `showErrBanner` + `dbg WARN` e **envia** o que já foi falado (descartar custaria 3 min de fala) |
| `STT_MAX_MS` | `420000` (7 min) | teto da transcrição: `tab.sttCtrl.abort()` → banner + `finishIdle` |

O STT é local e roda na CPU a ~0,7× o tempo real (`servidor-api.md` §2): 180 s de
fala custam ~4 min de transcrição. Antes destes tetos o HUD entrava em
`think` **antes** do `fetch('/stt')`, que não tinha `signal`, timeout, cronômetro
nem watchdog — `tab.askTimer` só nasce em `streamAsk()`, então a fase STT era um
ponto cego: uma fala de 4 min 42 s deixou o HUD em PROCESSANDO por ~13 min, sem
transcript e sem resposta.

### Modo texto

`#modeToggle` alterna (`setTextMode`, só em `idle`): esconde `#main`/`#pause`,
mostra `#textForm`. Enter envia, Shift+Enter quebra linha. **Focar o campo
pequeno abre o modal** `#textModalOverlay` (composição em tela cheia, com
seletores `#modalModel`/`#modalEffort` espelhados; Enter envia, Esc fecha
sincronizando o texto de volta). `sendTextPrompt` valida (`trim`, vazio não
envia) e entra no mesmo `askAndSpeak` da voz — só pula o STT; a resposta ainda
é falada. Os botões do COMMAND DECK fazem o mesmo: `runSkill` envia o rótulo
como turno do usuário (aba ocupada → feedback `.queued` por 1,4 s, sem fila real).

## 6.1 Pulso do HUD — fechar a janela derruba a ponte

Cada janela gera um `HUD_ID` (`'hud-' + base36(Date.now()) + aleatório`), pulsa
em `POST /hud_ping {hud}` a cada `HUD_PING_MS` (15 s, mais um pulso imediato no
load) e manda `sendBeacon('/hud_bye', {hud})` no `beforeunload`, junto dos
`/session_end` de cada aba. Sem HUD pulsando, a ponte se encerra sozinha
(`servidor-api.md` §2.1). O id por janela é o que torna seguro ter duas abertas:
fechar uma não derruba a ponte da outra.

---

## 7. Modo minimalista e gavetas laterais (seções 7b do JS, 9b–9b-quinquies do CSS)

Botão `#minimalToggle` (fixo, fora do grid — sobrevive ao modo) alterna
`body.minimal` via `setMinimal(on)`; o rótulo vira `PAINEL COMPLETO`. No
minimalista somem topbar, coluna esquerda, AUDIO I/O e a maioria dos controles;
sobram o grafo centralizado, `#state` discreto, o medidor e o `#main`
(encolhido; **clicar em qualquer ponto vazio do palco** também dispara
`onMain()`). Nada é duplicado: as gavetas **são os painéis existentes**
reposicionados por `position:fixed`:

- **Gaveta esquerda · CONVERSA** = `#txPanel` inteiro (alça `#dockL`, classe
  `dock-l` no body).
- **Gaveta direita · SKILLS** = `.col.right` (alça `#dockR`, classe `dock-r`).

Comportamento (objeto `DOCKS`, `setDock`, `armDockHide`, `dockNotify`):

- **Persistência** — `localStorage` chave `MIN_KEY = 'core.minimal'` guarda
  `{on, l, r}` (modo + gavetas abertas); restaurado no boot. As classes
  `dock-*` só têm efeito sob `body.minimal`, então ir e voltar do painel
  completo preserva o estado.
- **Auto-recolhimento** — gaveta aberta fecha sozinha após
  `DOCK_HIDE_MS = 45000` (45 s) parada. O timer rearma a cada
  `pointerdown/pointermove/wheel/focusin/keydown` dentro dela e **nunca**
  dispara com mouse/foco dentro, texto selecionado na gaveta ou busca escrita
  (`dockBusy`).
- **Ponto de aviso** — `dockNotify('l')` acende um ponto âmbar pulsante
  (`.dock-tab.nu`) na alça recolhida quando chega: turno novo do Claude,
  alteração de arquivo, `dbg` WARN/ERR ou relatório novo. Abrir a gaveta apaga.
- **Legenda passageira** — `#caption` mostra a última frase (EU/CLAUDE/SISTEMA)
  sob o grafo por `CAPTION_MS = 7000` ms, cortada em `CAPTION_MAX = 220`
  caracteres. Cala enquanto `#liveResp` ocupa a faixa (seletor `~` no CSS) e
  **some com a gaveta esquerda aberta** (seria eco do transcript ao lado).

O redesenho da gaveta esquerda (contrato `docs/task-hud-gaveta.md`, coberto por
`tests/test_dock_redesign.py`) adicionou, **tudo escopado em `body.minimal`**:

1. **Largura ajustável** (`#dockGrip`) — arrasto muda só `--dock-w`
   (padrão `clamp(420px, 34vw, 760px)`; mínimo `DOCKW_MIN = 340`, máximo
   `min(1100, 92vw)`), sem `graph.resize()` (a gaveta flutua por cima).
   Persiste em `DOCKW_KEY = 'core.dockw'` ao soltar. Duplo clique alterna com
   uma largura ampla passageira (`min(1100, 80vw)`).
2. **Rail vertical de visões** — `#txPanel` vira grid `104px 1fr`: as 5 abas
   viram blocos com ícone (`▤ ± ⌗ ⟲ ◳` via `::before`) numa coluna à esquerda;
   `#dockHead` ganha o título da visão (`#dockTitle`, mapeado por
   `DOCK_VIEW_LABELS`) e o `#tabTag` **migra de pai** para dentro dele
   (`setMinimal` move o elemento; volta ao `h3.tabs` no painel completo).
3. **Tipografia e densidade** — corpo maior só na gaveta (`#log` 13,5 px etc.),
   piso de 10 px, cor intermediária `--ink-faint-2:#8A8069`; botão
   `#densToggle` alterna `body.dense` (COMPACTA/CONFORTO), persistido em
   `DENSE_KEY = 'core.dense'`.
4. **Busca e chips** — `#dockFind` filtra a visão ativa (case-insensitive, sem
   regex; seletores por visão em `FIND_SPEC`), esconde não-casados via classe
   `.nomatch` (que só tem efeito sob `body.minimal` — voltar ao painel completo
   com filtro escrito não some com nada), contador `#dockCount` ("N de M"), e
   um `MutationObserver` reaplica o filtro em linhas novas. Esc no campo limpa
   o filtro com `stopPropagation()` (não encerra a sessão). Os chips
   `#dbgLevels` ligam/desligam níveis do DEBUG (classes `hide-info` etc. no
   `#debug`); o estado guarda os **desligados** em `DBG_KEY = 'core.dbgLevels'`.
5. **Transcript em blocos** — cada turno vira bloco com faixa de 2 px por autor
   (teal/verde/vermelho) na borda esquerda; as etapas de progresso ficam
   indentadas, sem rótulo repetido.

Os seletores `#dockModel`/`#dockEffort` (`.dock-selects`) aparecem só no
minimalista (a topbar com os originais está oculta) e são **espelhos**: mudar
qualquer lado sincroniza o outro (`mirrorDockSelects`); `currentModel()` /
`currentEffort()` continuam lendo só `els.model`/`els.effort`.

## 8. Atalhos de teclado

Handler global de `keydown` (seção 7 do JS):

| Tecla | Ação |
|---|---|
| `Espaço` | pausar/retomar a gravação (`onPause`) |
| `Enter` | iniciar a escuta ou enviar o áudio (`onMain`) |
| `Esc` | encerrar o fluxo da aba ativa (`onStop`, inclui `/abort`) |

Exceções, na ordem em que o handler as testa: eventos vindos dos selects
(`#model`, `#effort`, `#dockModel`, `#dockEffort`) e do `#textInput` passam
direto; com o **modal de texto aberto** nada é interceptado (o modal tem seus
próprios: Enter envia, Shift+Enter quebra, Esc fecha); com o **visor de
relatórios aberto**, Esc fecha **o visor**, nunca a sessão. No campo de busca
da gaveta, Esc limpa o filtro (ou tira o foco) e para a propagação. Cabeçalhos
de painel recolhíveis também aceitam Enter/Espaço com foco (role `button`).

## 9. Seletores de modelo e esforço

Três pares espelhados do mesmo valor: topbar (`#model`/`#effort`), gaveta
CONVERSA (`#dockModel`/`#dockEffort`) e modal (`#modalModel`/`#modalEffort`).

- **Modelo** — opções `FABLE 5`, `OPUS 4.8`, `SONNET 5`, `HAIKU 4.5`;
  `currentModel()` normaliza para o alias do CLI (`fable|opus|sonnet|haiku`),
  vazio = padrão.
- **Esforço** — `PADRÃO` (valor vazio), `LOW`, `MEDIUM`, `HIGH`, `XHIGH`,
  `MAX`; `currentEffort()` restringe ao conjunto permitido. Enviado como
  `esforco` no corpo de `/ask`, `/session_start` e `/session_reset` (contrato
  verificado por `tests/test_frontend_static.py`).

## 10. Outros recursos visíveis no código

- **Painéis recolhíveis (8b)** — clicar no `h3` de qualquer painel (exceto
  `#txPanel`, cujas abas cuidam do clique) recolhe/expande (`.collapsed`,
  seta `.chev`); estado persistido em `PANEL_KEY = 'core.collapsed'` por chave
  derivada do título. Recolher o transcript liga `body.tx-collapsed`, que
  encolhe a faixa do rodapé para o núcleo crescer; `graph.resize()` acompanha.
- **Fila de fala visível** — `#speakStatus` mostra "🔊 falando: Sessão X · na
  fila: …" (a serialização é do servidor; ver `voz-tts.md`).
- **Relógio** — `tickClock()` a cada segundo: `HH:MM:SS` + data pt-BR
  (`SEG 20 AGO 2026`).
- **Link ForestOS** — `🌲 ForestOS` na fila de status aponta para `/forestos`
  (ver `forestos.md`).
- **Boot (seção 9)** — `setState('idle')`, cria a 1ª aba, restaura minimalista
  /gavetas/largura/densidade do `localStorage`, destrava o AudioContext no 1º
  gesto, aquece o claude da 1ª aba via `/session_start` e registra
  `dbg('OK','C.O.R.E. frontend carregado · contratos prontos')`.
- **Erros ao vivo** — `#errBanner` sobre o núcleo (fechável no `×`), além do
  DEBUG; `ev.t==='error'` e `debug` de nível ERR o acionam.
- **Placeholder assumido** — toda a coluna esquerda é mock; o Command Deck
  ainda envia o rótulo do botão como pergunta comum (mapeamento para skills
  dedicadas é pendência).

Para o lado servidor das rotas citadas (`/stt`, `/ask`, `/speak`, `/abort`,
`/session_*`, `/reports`), ver `servidor-api.md`; para a arquitetura geral,
`arquitetura.md`; para operação (subir/derrubar o Hub), `operacao.md`.
