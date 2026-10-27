# Hive Mind — front-end
Atualizado em 26/10/2026 · descreve o código atual; o que é planejado fica em `roadmap.md`.

A tela do Hive Mind é um conjunto de módulos ES nativos (sem build, sem framework)
em `HiveMind/frontend/`. Ela tem **dois modos**: o **modo real** (padrão), que fala
com o backend pela API `/hive-api` e controla missões de verdade, e o **modo
demonstração**, uma simulação local sem nenhuma chamada ao backend. Desde 26/10/2026 o
modo real usa os mesmos componentes visuais do protótipo e da demonstração (gavetas
Agentes, Missão e Conversa, HUD com sete etapas, colmeia animada, popup de entrega),
com dados reais. O texto antigo
que dizia "a página é só demonstração e não usa modelos nem IA" é falso: os modelos
são usados pelo backend (`HiveMind/backend/`), a pedido da tela real. O que a
*página* não faz é chamar voz, STT, TTS ou as rotas de assistente do Hub (`/ask`,
`/stt`, `/speak`, `/session_*`, `/abort`).

## 1. Como a página é montada

A página **não tem URL própria**. Ela é injetada na própria `/` (a tela do Hub):

| Peça | Onde | O que faz |
|---|---|---|
| Tag de script | `index.html`: `<script type="module" src="/hive-ui/static/app.js">` | Único encaixe no HTML do Hub. |
| Blueprint estático | `HiveMind/frontend/routes.py:blueprint` (`hivemind_frontend`) | Serve só `static/` em `/hive-ui/static/...`. Nenhuma rota de assistente ou de API. Registrado em `server.py` via `from HiveMind import blueprint`. |
| Botão da aba | `codex_frontend/static/providers.js` (`#assistantNavigation`, `<button data-page="hive">`) | A aba "HIVE MIND" não está no `index.html`; nasce no chrome criado por `providers.js`. |
| Registro | `app.js` → `window.hubProviders.registerPage('hive', lifecycle)` | `providers.js:registerPage` só aceita o id `hive`. Guarda `{activate, deactivate}` e chama o que for preciso. |
| Raiz da página | `app.js`: `<main id="hmPage" class="hm-page">` anexado ao `body` | `position:fixed; inset:0; z-index:70`, `min-width:1200px; min-height:560px` (`hive.css`; era 760 px até 25/10/2026 e cortava a Conversa em janelas baixas). Nasce `hidden`, `inert` e `aria-hidden="true"`. |

`app.js` começa importando `/codex-ui/static/providers.js`, então a dependência de
`providers.js` é estrutural: o import é estático, então se o arquivo faltar o
`app.js` inteiro falha ao carregar e a página não existe (o `?.` em `registerPage`
não evita isso).

**Quando a página fica ativa.** `providers.js:selectPage('hive')` só ativa a página no
modo minimalista (`hub.isMinimal`) e exige que o registro já tenha ocorrido. A
preferência fica em `localStorage['core.page']` (`claude` | `codex` | `hive`).
Voltar ao painel completo chama `deactivate` (via `beforeModeChange`). Trocar de
página nunca cria nem troca a sessão do Hub: a aba Hive não é um provider
(`MAX_TABS`/`MAX_SESS` continuam em 6).

**Isolamento do resto do Hub** (`app.js:setHubIsolated`). Ao ativar, todo filho
direto do `body` que não seja `<script>`, a raiz `#hmPage` ou `#assistantChrome` recebe
`inert = true` e `aria-hidden="true"`; o estado anterior de cada nó é guardado num
`Map` e restaurado ao desativar. O `#assistantChrome` fica de fora para a navegação
continuar utilizável. Enquanto a página está ativa, `providers.js:canUseAssistantUI()`
devolve `false`, e os atalhos globais do Hub (Enter/Espaço/Esc, microfone, skills,
envio de texto, foco automático do mobile) respeitam isso.

**Rótulos da navegação** (`app.js:setHiveNavigationLabels`). Com a página ativa, os três
botões de `#assistantNavigation` passam a dizer `Claude Code`, `Codex`, `Hive Mind` (em
vez de `CLAUDE CODE`, `CODEX`, `HIVE MIND`); o texto original de cada botão é guardado
e restaurado ao desativar.

**Fontes e CSS carregados** (`app.js:addStylesheet`, uma vez cada): Google Fonts
(Space Grotesk 400–700 e Source Sans 3 400–700), `/hive-ui/static/bee-animation/bee.css`
e `/hive-ui/static/hive.css`. Sem a fonte remota, a página cai nas fontes genéricas e o
comparador visual deixa de ser válido (ver `testes.md`).

## 2. Mapa de módulos

Todos em `HiveMind/frontend/static/`.

| Arquivo | Responsabilidade |
|---|---|
| `app.js` | Monta `#hmPage`, instancia simulação e estado real, alterna modo, isolamento, rótulos da navegação, "Reduzir movimento", visibilidade do documento, lifecycle `activate/deactivate`, registro no `hubProviders`, globais `hiveMindDemo` e `hiveMindLive`. |
| `api.js` | `hiveApi.get/post` sobre `fetch('/hive-api' + caminho)`; normaliza o erro e guarda o corpo da resposta em `error.detail` (seção 4). |
| `mission-state.js` | `HiveMissionState`: estado do modo real (presença, polling, cursor de eventos, comandos, `hudAction`, `requestUi`/`onUiRequest`, `snapshot()` no mesmo formato da simulação). Exporta também funções puras: `STEP_NAMES`, `missionStep`, `missionFailure` e `deriveRealView` (células, estados, rotas e HUD derivados de missão, jobs, eventos e `bees_summary`). |
| `live-drawers.js` | `createLiveDrawers`: só o **compositor** das gavetas do modo real (monta as três gavetas, as abas puxadoras e o popup de entrega e repassa o estado a cada módulo abaixo). Reexporta `validateTeam` e `chatQueen`. |
| `live-ui.js` | Peças compartilhadas pelas gavetas reais: reexporta de `drawers.js` os componentes da demonstração (`el`, `svg`, `label`, `hex`, `caret`, `statusIcon`, `trailSample`, `statusShort`) e define `btn`, `shortHash`/`hashNode` (hash de 8 caracteres com o completo no `title`), `taskKind`, `drawerHead`, `tabs`, `pullTab` e `segmentBar`. |
| `live-team.js` | Gaveta **Agentes** do modo real: lista, detalhe com abas, formulário de criar/editar abelha, limite de execução. Exporta `createLiveTeam`, `validateTeam`, `validateBeeForm` e `parseTags`. |
| `live-mission.js` | Gaveta **Missão**: cabeçalho, seletor, criação de missão, Andamento, Aprovações, abas Plano/Responsabilidades/Conexões/Entrega. Exporta `createLiveMission`, `interruption`, `cycleLimitNotice`, `reconcileText` e `planSummary`. |
| `live-chat.js` | Gaveta **Conversa**. Exporta `createLiveChat`, `chatQueen`, `chatBlockedReason`, `teamChangeNotice` e `CHAT_STATES`. |
| `live-delivery.js` | Popup de entrega do modo real. Exporta `createLiveDelivery`, `deliveryView`, `criteriaList`, `deliveryStats`, `criterionText` e `CRITERION`. |
| `messages.js` | `describeCode(código)`, `describeError(código, detalhe)`, `stateLabel`, `stateBadge`, `stateSentence` e `fieldName`: mapa código → frase em português (erros, conflitos, motivos de `job_error`), rótulos curtos e frases de cada estado da missão. Usado pelos módulos `live-*.js` e por `mission-state.js`. |
| `hive.js` | `createHiveView`: renderiza colmeia, células, rotas, HUD, popup de conexão; usado pelos dois modos (o HUD tem um ramo para `state.real`). Exporta `agentStatus`, `linkStatus`, `progressOf`. |
| `geometry.js` | `AXIAL_SLOTS`, malha hexagonal (`meshGeometry`), `HoneycombRouter`, `slotPoint`, `hexPoints`, `pathFromPoints`, `pointAlong`. |
| `bee-animation/bee.js` + `bee.css` | Abelha em SVG com três PNG (`createBee`, `updateBee`) e animações por estado. |
| `assets/` | `hive-mind-logo.png`, `operaria-animacao/` e `rainha-animacao/` (`asa-esquerda`, `asa-direita`, `corpo-sem-asas`, todos PNG). |
| `hive.css` | Todo o estilo da página (classes `hm-*`). |
| `simulation.js` | `HiveSimulation`: máquina de estados da demonstração (relógio, fases, pausa, entrega, cenários, CRUD simulado). |
| `demo-data.js` | Dados da demonstração: `DEMO_NOTICE`, `MISSION`, `STEPS`, `DIVERGENCES`, `STATE_INFO`, `LINK_INFO`, `AGENTS`, `PHASES`, `CONNECTIONS`. |
| `drawers.js` | `createDrawers`: gavetas Agentes, Missão e Conversa da demonstração, popup de entrega. Também **exporta** os componentes puros que o modo real reutiliza (`el`, `svg`, `label`, `hex`, `caret`, `statusIcon`, `trailSample`, `statusShort`); o comportamento da demonstração não mudou. |

`HiveMind/frontend/__init__.py` apenas reexporta o blueprint; `HiveMind/__init__.py`
reexporta o mesmo blueprint para o `server.py`.

## 3. Modo real × demonstração

O modo inicial é `real`. O botão do cabeçalho (`.hm-mode`) alterna: no real ele diz
"Abrir demonstração"; na demonstração, "Voltar à missão real". Também há o evento
`hivemind-demo-request` na `window` (disparado por `HiveMissionState.setScenario`,
usado pelo botão "Ver colmeia de exemplo" do cartão de colmeia vazia do modo real).

| | Modo real | Demonstração |
|---|---|---|
| Container | `.hm-live-workspace` | `.hm-demo-workspace` |
| Estado | `HiveMissionState` | `HiveSimulation` |
| Gavetas | `createLiveDrawers` | `createDrawers` |
| Dados | `/hive-api` (backend) | `demo-data.js`, tudo local |
| Polling/relógio | `live.setLifecycle(pageActive && !demo)` | `simulation.setLifecycle(pageActive && demo, visível)` |
| Cabeçalho | projeto "Hive Mind"; sem cenários nem aviso | projeto "Operação de pedidos"; botões de cenário e aviso |

`app.js:setMode` mostra um workspace, esconde o outro e liga o ciclo de vida de apenas
um deles; o relógio da simulação para fora da demonstração e o polling do real para
fora do modo real.

**A demonstração nunca controla missão real.** `simulation.js` e `drawers.js` não
importam `api.js` e não chamam o backend. O aviso fica visível (`.hm-demo-notice`,
texto "DEMONSTRAÇÃO" + "DADOS SIMULADOS") e leva a frase `DEMO_NOTICE` em
`aria-label` e `title`: "Demonstração simulada · separada do backend real; não
controla missões reais". Essa frase é exigida por testes (`testes.md`). O cabeçalho
mantém o mesmo botão de "Reduzir movimento" nos dois modos, e a preferência do
sistema `prefers-reduced-motion` também vale para ambos.

**Globais de depuração** (usadas pelos testes de navegador):

| Global | Conteúdo |
|---|---|
| `window.hiveMindDemo` | `{simulation, getState()}` — a instância de `HiveSimulation` e `snapshot()`. |
| `window.hiveMindLive` | `{getState()}` — `snapshot()` do `HiveMissionState`. |

Observação sobre a presença: `HiveMissionState` é criado quando o módulo carrega, e o
heartbeat de presença roda desde então, **mesmo com a página Hive fechada ou em modo
demonstração** (a presença é "HUD aberto", não "aba Hive visível").

## 4. Modo real

### `api.js`

`hiveApi.get(path)` e `hiveApi.post(path, data)` chamam `/hive-api<path>` (POST com
`Content-Type: application/json`). Se o corpo não for JSON, os dados viram
`{error:'resposta_inválida'}`: com status de erro isso é lançado; com 2xx é devolvido
sem lançar. Se `response.ok` for falso, lança `Error(data.error ||
'falha_na_solicitação')` com `error.detail = data` (o corpo inteiro da resposta). Ou seja,
o front **vê o código curto do backend** (por exemplo `local_origin_required`,
`not_found`, `invalid_request`, `internal_error`, ou o código de um 409 como
`queen_configuration_changed`) e os campos extras que ele manda, como `bee`, `field` e
`missing` do cadastro de abelha; nunca um texto longo. A tela traduz com `messages.js`
(ver "Mensagens de erro"). Falha de rede propaga a mensagem do próprio `fetch`.

### `mission-state.js:HiveMissionState`

| Tema | Comportamento |
|---|---|
| Identidade | `hud` e `owner` são UUIDs sem hífen, gerados no construtor. `hud` identifica a tela na presença; `owner` identifica quem controla a missão (lease). |
| Presença | `POST /presence {hud, present:true}` na criação e a cada **15 s** (`heartbeat`). No `pagehide` com `event.persisted` falso, `navigator.sendBeacon('/hive-api/presence', {hud, present:false})`. Erros de ping são ignorados. |
| Polling | Com a página ativa em modo real, `refresh()` a cada **2,5 s** (e uma vez ao ativar). Uma chamada em andamento é aguardada antes da próxima. |
| Cada `refresh` | `GET /status`, `GET /missions`, e, se há missão selecionada, `GET /missions/<id>?after=<seq>`. Sem seleção, escolhe a primeira da lista. |
| Cursor de eventos | `?after=` usa o último `seq` visto (`eventSeq`). Se a página vier com 200 eventos, busca mais, até 9 páginas extras por refresh. A lista local é `slice(-500)`: **no máximo 500 eventos** no front. Trocar de missão zera `events` e o cursor. |
| Resumo por abelha | `refresh()` guarda `bees_summary` da resposta (`null` se o backend não mandar, como numa versão antiga); `selectMission` e `create` o zeram. O front **não recalcula** status de tarefa, progresso nem ferramentas usadas dos eventos: usa o resumo (ver `backend.md`). Sem o resumo, só o status das tarefas é calculado dos jobs (`localTasks`). |
| Missão selecionada | Guardada em `sessionStorage['hivemind-mission']`; criar ou selecionar missão atualiza a chave. |
| Revisão/chave | Todo comando e toda configuração enviam `key` (UUID novo, idempotência) e `revision` (`mission.revision`, `status.roster.revision` ou `status.settings.revision`). |
| Lease | `command()` faz `POST /missions/<id>/lease {owner}` e só então `POST /missions/<id>/command {owner, action, key, revision, ...extra}`; em seguida `refresh()`. |
| Erro | `this.error` guarda o código da última falha e `this.errorDetail` o corpo da resposta. Comando, configuração e catálogo bem-sucedidos limpam o erro; o `refresh` não o limpa. |
| `create(title, source, message, limit)` | Exige Rainha configurada (`configure_a_equipe`); `POST /missions {id, key, title, cycle_limit}`; carrega a missão (`missão_não_carregada` se falhar) e envia o comando `ask`. |
| Gavetas e seleção | `drawers` começa `{left:true, right:true, bottom:false}`. `selectAgent(id)` alterna a seleção e abre a gaveta esquerda quando há seleção (fecha-a ao desmarcar); `selectLink(id)` alterna a conexão selecionada; `toggleDrawer(nome)`. |
| `hudAction(id)` | `start`, `pause` e `resume` viram comandos do backend; `view_delivery` pede o popup (`requestUi('delivery')`), `view_approval` a aprovação (`requestUi('approval')`) e qualquer outro id os detalhes (`requestUi('details')`). O HUD **não aprova direto**: "Ver aprovação" só abre a gaveta Missão, onde fica o cartão de aprovação. |
| `requestUi(target)` / `onUiRequest(fn)` | Canal do HUD e das gavetas até os módulos: `requestUi` abre a gaveta de destino (Conversa para `chat`, Missão para os demais), chama os ouvintes e emite o estado. `live-delivery.js` abre o popup em `delivery`; `live-chat.js` foca o campo em `chat`. `onUiRequest` devolve a função que remove o ouvinte. |
| Redução de movimento | `setReduced`; `animationsPaused = !active || document.hidden || reduced`. |

#### `snapshot()` e `deriveRealView`

`snapshot()` produz o mesmo formato que a simulação, para `hive.js` renderizar sem saber
o modo, e acrescenta `real: true`. Campos: `mission`, `jobs`, `events`, `roster`, `team`,
`beesSummary`, `messages` (as do planejamento), `missions`, `status`, `catalog`,
`catalogLoading`, `error`, `errorDetail`, `tasks`, `agents`, `added`, `phase`
(`{agents, links, step, failed}`), `connections`, `linkInfo`, `hud`, `phaseId`
(`done` com a missão concluída, senão `real`), `scenario` (`real`, ou `empty` sem
agentes), `selected`, `selectedLink`, `drawers`, `reduced`, `manualPaused`,
`animationsPaused`, mais `progress: 0`, `adjusted: false`, `showSubs` (verdadeiro só se há subagente visível) e `form: false`
(constantes que só a demonstração varia). O que a colmeia e o HUD desenham vem de
`deriveRealView({mission, jobs, events, team, summary})`, uma função pura (testada no
Node sem DOM).

**Etapas** (`missionStep`, `STEP_NAMES`): a missão está numa de sete etapas; sem missão é a 0.

| Etapa | Nome | Estados da missão |
|---|---|---|
| 1 | Planejamento | `draft`, `clarifying`, `planning` |
| 2 | Aprovação do plano | `awaiting_plan_approval`, `ready`, `preparing` |
| 3 | Execução | `running`, `correcting` |
| 4 | Verificação | `verifying` |
| 5 | Aprovação da entrega | `awaiting_delivery_approval` |
| 6 | Incorporação | `delivery_approved`, `applying`, `recovery_required` |
| 7 | Concluída | `completed` |

`paused`, `pausing` e `awaiting_user` mostram a etapa onde pararam (`data.pause.from`);
`abandoned` usa `data.abandoned.previous_state`; `awaiting_user` por limite de ciclos do
plano atual fica na 4. Sem estado conhecido, a etapa vem dos dados (entrega: 5; área
isolada: 3; plano: 2; senão 1).

**Células.** A equipe é a do `bees_summary` (só as `active`); sem resumo, `plan.bees`,
depois `planning.team`, depois `status.roster.bees`. Rainha primeiro, **no máximo 9
integrantes**; o id da célula é `rainha` ou `bee-<id>`, o nome é o `id` da abelha e a
especificação `provedor · modelo · esforço`. Abelha temporária (a Rainha a criou no plano)
leva a marca "Temporária" (`.hm-cell-tag`); papel `subagent` mantém a célula pequena. O
estado vem do backend, nunca dos eventos:

| Estado | Quando |
|---|---|
| `coord` | Rainha com job rodando (planejamento ou correção) e, em `running`, `verifying` ou `correcting`, enquanto qualquer operária ou o verificador trabalha ("Acompanhando o andamento") |
| `working` | job da abelha rodando: "Iniciando" até haver processo, "Executando" depois; o texto é a nota do último `progress` ou a descrição da tarefa; o anel e o "x de y" mostram os passos do `progress` (`done`/`total`) ou, sem ele, as tarefas concluídas |
| `waiting` | tarefa com dependência pendente ("Aguardando informação", com a abelha de que depende), tarefa na fila ("Tarefa na fila", "Em pausa" se pausada) ou verificador com a missão em `verifying` |
| `approval` | Rainha com aprovação pendente ("Aguardando sua decisão"), esclarecimento ou `awaiting_user` ("Aguardando você") ou falha da missão ("Impedimento") |
| `done` | todas as tarefas da abelha concluídas ("Entregue"), verificador que entregou o veredito, Rainha com a missão `completed` |
| `failed` | o último job da abelha falhou |
| `idle` | o resto ("Disponível", com a contagem de tarefas do plano) |

**Rotas.** Há uma rota Rainha→abelha (`q-<id da célula>`) para cada abelha e uma rota
`dep-<de>-<para>` entre abelhas cujas tarefas dependem uma da outra. Estados da Rainha→abelha:
`del` (job rodando), `fail` (job falhou), `in` (resultado entregue há menos de 6 s, pelo
evento `job_finished`) e depois `ret`, `wait` (tarefa à espera de dependência), `out`
(delegada e na fila; também o verificador em `verifying`) e `idle`. Rota de dependência:
`fail` se a tarefa anterior falhou, `idle` fora da execução, `wait` enquanto a anterior não
terminou, `flow` quando terminou e a seguinte ainda não começou, `done` depois.

**HUD** (`hud` do snapshot, desenhado por `hive.js:renderHud`): "MISSÃO REAL", sete
hexágonos com a etapa (preenchidos até a atual; atual em estilo de espera `paper` nas
aprovações e na pausa, ou de falha), o texto "Etapa n de 7 · Nome" com sufixo ("· Pausada",
"· Pausando", "· Recuperação necessária", "· Encerrada", "· Aguardando você" ou "· falhou";
o `title` guarda título, estado e ciclo) e **um botão que segue o estado**:

| Botão | Estado da missão | Efeito (`hudAction`) |
|---|---|---|
| Ver aprovação | `awaiting_plan_approval` com plano | `view_approval`: abre a gaveta Missão, onde fica o cartão de aprovação |
| Iniciar | `ready` | comando `start` |
| Pausar | `planning`, `running`, `verifying`, `correcting` | comando `pause` |
| Retomar | `paused` | comando `resume` |
| Ver entrega | entrega presente em `awaiting_delivery_approval`, `delivery_approved` ou `completed` | `view_delivery`: abre o popup de entrega |

Com aprovação pendente ou falha aparece o **banner do mapa** (`.hm-hud-alert`):
"Aprovação pendente." com "Ver aprovação", ou "Falha na etapa <nome>." com o motivo e "Ver
detalhes" (`requestUi('approval' | 'details')`). A falha mostrada é a de `recovery_required`,
a do limite de ciclos ou a do último `job_error` ainda não superado (`missionFailure`).

### Gavetas do modo real

`live-drawers.js:createLiveDrawers` monta as três gavetas no mesmo molde da demonstração
(`.hm-side-left`, `.hm-side-right`, `.hm-bottom`, cada uma com a gaveta e a aba puxadora)
e entrega o estado a `live-team.js`, `live-mission.js`, `live-chat.js` e
`live-delivery.js`. Larguras e posições vêm de `hive.css` (laterais de 392 px, inferior de
300 px). Gaveta fechada fica `inert` (sem foco nem clique) e a área do modo real
(`.hm-live-workspace`) usa `overflow:clip`: antes, foco ou digitação numa gaveta fechada
rolava a colmeia e fazia a Conversa aparecer (F2 de 24/10/2026). A aba puxadora fica fora
do `inert` e continua clicável.

**Abas puxadoras** (`live-ui.js:pullTab`, iguais às da demonstração): ícone, nome,
contador e seta. Agentes mostra o número de agentes, Missão `etapa/7` e Conversa o número
de mensagens. Com altura de até 820 px e a Conversa aberta, as duas abas laterais sobem 150
px (`hive.css`) para não ficarem sobre ela.

**Agentes (esquerda, `live-team.js`).** Cabeçalho escuro com o resumo ("1 rainha, 4
operárias, 1 verificador, 1 temporárias") e contadores de trabalhando, aguardando,
disponíveis e entregues (mais "com falha" e "incompletas" só quando houver). Lista de
linhas (`.hm-agent-row`): ícone da abelha, nome, marcas "Temporária", "Subagente" e
"Incompleta", estado, progresso `x/y` e ícone de estado. A linha selecionada abre o
detalhe com abas:

| Aba | Conteúdo |
|---|---|
| Visão geral | papel e especificação; **provedor, modelo e esforço editáveis só em abelha permanente** (as temporárias são somente leitura), com o valor salvo visível mesmo antes de consultar o catálogo; estado (com a barra de segmentos quando há progresso); descrição; na Rainha, o objetivo do plano e "Ver entrega" |
| Tarefas | tarefa atual e lista das tarefas da abelha (a Rainha vê o plano inteiro) |
| Skills | tags e instruções declarativas do cadastro (todas, menos a Rainha) |
| Ferramentas | uma linha por ferramenta do cadastro, mais "Informar progresso" (automática), com a contagem de usos (`tools_used`) |
| Relações | de quem recebe e para quem entrega; a Rainha vê as responsabilidades distribuídas; mais as conexões da abelha na colmeia (clicar seleciona a rota) |

A Rainha só tem as abas Visão geral, Tarefas e Relações. Abaixo da lista: "Consultar
modelos" (mostra "Consultando modelos…" e fica desabilitado enquanto carrega: F1), o aviso
de disponibilidade dos provedores, o aviso de cadastros incompletos e o limite global de
execução (`worker_limit` de 1 a 20, "Salvar limite"). O rodapé tem "＋ Criar operária",
"Editar agente" e "Excluir agente"; o último só vale para operária ou subagente
**permanente** (a Rainha e o verificador não saem do cadastro) e se a equipe continuar
válida. Abelha temporária é somente leitura: só a Rainha as cria e elas saem com a missão.

O **formulário de abelha** (criar e editar, no estilo "Criar operária") fica na própria
gaveta e **não é reconstruído pelo polling**, para não perder o que foi digitado. Campos:
papel (só quando há mais de uma opção), identificador (somente leitura ao editar),
descrição (até 2000 caracteres), skills (tags separadas por vírgula, com pré-visualização),
instruções das skills (até 4000), ferramentas (`read`, `patch`, `checks`; `patch` bloqueado
para Rainha e verificador; "Informar progresso é automático"), provedor, modelo e esforço
e "Consultar modelos". Durante a consulta, o botão do formulário fica desabilitado e mostra
"Consultando modelos…"; o formulário, seus valores e o foco são preservados. `validateBeeForm` valida por campo e `validateTeam(rows)` valida a
equipe (identificador com `[A-Za-z0-9_.-]{1,100}`, sem repetição, modelo e esforço
obrigatórios, exatamente uma Rainha e um Verificador, ao menos uma Operária). O erro do
backend com `{bee, field}` aparece no campo certo (`describeError`). "Salvar" envia
`POST /settings {kind:'roster', bees, key, revision}`. Sem equipe salva, as abelhas ficam
num rascunho local e o rodapé oferece "＋ Adicionar abelha", "Salvar equipe" e "Descartar".
Cadastro **incompleto** (abelha salva antes do cadastro rico) aparece com a marca
"Incompleta", o que falta e o bloqueio de planejar (`roster_incomplete`).

**Missão (direita, `live-mission.js`).**

- *Cabeçalho escuro*: título "Missão", selo do estado (`stateBadge`, no lugar de "Execução
  simulada"), nome da missão (uma linha com reticências), objetivo (até duas linhas, texto
  inteiro no `title`), linha "Projeto: caminho · Ciclo n de limite" (uma linha) e o
  campo "Máximo de ciclos" com "Salvar" (`cycle_limit`; escondido em `abandoned`).
- *Seletor* de missão com "Nova missão". O cartão **Criar missão** (nome, projeto
  autorizado, objetivo, máximo de ciclos de 1 a 20, erro por campo) aparece sem missão ou
  por "Nova missão", é persistente (o polling não apaga os campos) e limpa os campos depois de criar
  (F7). "Planejar com a Rainha" fica desabilitado sem equipe ou com abelha incompleta.
- *Andamento*: sete segmentos (feitos, atual, futuros; o atual em estilo de espera nas
  aprovações e na pausa, ou de falha; na execução preenche pela proporção de tarefas
  concluídas), a frase "Etapa n de 7 · Nome." mais a frase do estado e os botões
  (estilos `hm-dark` e `hm-outline`):

| Botão | Aparece quando | Comando (`action`) e extras |
|---|---|---|
| "Iniciar" | `ready` | `start` |
| "Pausar" | `planning`, `running`, `verifying`, `correcting` | `pause` |
| "Retomar" | `paused` | `resume` |
| "Ver entrega" | há entrega | abre o popup (`requestUi('delivery')`) |

- *Aprovações* (cartões `hm-approval`; sem pendência, "Nenhuma aprovação pendente." ou, com a missão concluída, "Tudo aprovado e incorporado."):

| Cartão e botão | Aparece quando | Comando (`action`) e extras |
|---|---|---|
| "O plano da Rainha aguarda você": "Aprovar" | `awaiting_plan_approval` e há plano | `approve_plan {plan_hash}` |
| mesmo cartão: "Solicitar ajuste" | idem | abre a Conversa (`requestUi('chat')`) |
| "A entrega verificada aguarda você": "Aprovar" | `awaiting_delivery_approval` | `approve_delivery {candidate_hash, delivery_hash}` |
| mesmo cartão: "Ver entrega" | idem | abre o popup. **Não há "Solicitar ajuste" na entrega**: o backend não aceita mensagem à Rainha nesse estado |
| "Recuperação necessária": "Recuperar entrega" | `recovery_required` e há `delivery_hash` | `recover_delivery` |
| mesmo cartão: "Encerrar missão" | `recovery_required` | primeiro clique só pede confirmação (abaixo); "Confirmar encerramento" envia `abandon` |
| "A origem mudou": "Reconciliar origem em área isolada" | `data.reconciliation_required` e estado diferente de `recovery_required` e `abandoned` | `reconcile_source` |
| "Trabalho interrompido" e "Limite de ciclos" | ver estados especiais | só aviso |

- *Abas* (`hm-tabs`): **Plano** (tarefas com ✓, ● e ☐ conforme o status do backend e a
  abelha dona; critérios de aceite com o veredito; "Versão do plano" com hash curto),
  **Responsabilidades** (uma linha por abelha, que seleciona o agente), **Conexões** (a
  legenda dos sete estados de rota e a lista das conexões; clicar numa seleciona a rota e
  abre o popup do mapa) e **Entrega** (veredito por critério, evidência, arquivos
  alterados e fora do plano, "Ver entrega" e, em `delivery_approved`, "Incorporar entrega
  aprovada" com o aviso de que origem e journal precisam estar no mesmo volume; comando
  `apply {delivery_hash}`).
- Nenhuma tela mostra JSON cru. Hashes aparecem com 8 caracteres e o valor completo no `title`.
- A ação `propose` do backend não tem botão; quem propõe o plano é a Rainha. O "Pausar" e o
  "Retomar" também existem no HUD do mapa.

**Estados especiais da gaveta Missão** (cartões `hm-approval`).

- `recovery_required`: aviso de que a missão exige recuperação explícita. Nenhum botão de
  avanço (nem "Reconciliar origem"). "Recuperar entrega" só com `data.delivery_hash`.
  "Encerrar missão" pede confirmação **na própria gaveta** (nunca `window.confirm`):
  o botão é trocado por "Confirmar encerramento" + "Cancelar". A confirmação é um estado
  local (`confirmAbandon`, guarda o id da missão) que sobrevive às renderizações do
  polling de 2,5 s enquanto a missão for a mesma e continuar em `recovery_required`;
  sai ao cancelar, confirmar, trocar de missão ou mudar de estado. Se o backend recusar
  com `delivery_recovery_required` (há aplicação pendente de recuperação), o cartão mostra
  a frase neutra do código ("Há uma aplicação na origem pendente de recuperação: use
  “Recuperar entrega” antes de continuar.").
- `abandoned` (terminal): aviso "Missão encerrada por você. O histórico foi preservado e a
  origem não foi alterada." e **nenhum botão de comando**, nem o do limite de ciclos.
- `job_error` mais recente que o último `plan_proposed`, `resumed` ou
  `planning_requested`: em `awaiting_user`, o aviso diz que o trabalho parou, o motivo
  traduzido e que o caminho é conversar com a Rainha na gaveta Conversa ou pedir novo
  plano; nos outros estados, "Última interrupção: <motivo>". Falha anterior a um novo
  plano ou a uma retomada não aparece mais (F9 de 24/10/2026). "Retomar" continua só em
  `paused`.
- `awaiting_user` com `attempt_outcome.status == "cycle_limit"` do plano atual: o aviso
  diz que os N ciclos permitidos acabaram sem passar na verificação e que o caminho é
  aumentar o máximo de ciclos e conversar com a Rainha para um plano ajustado (F8).
- Verificação independente: em vez do JSON, "Aprovada"/"Não aprovada no ciclo N", uma
  lista com cada critério ("aprovado", "reprovado" ou "não verificável", descrição e id)
  e a evidência do verificador (aba Entrega).

**Conversa (inferior, `live-chat.js`).** Usa as classes da demonstração: cabeçalho escuro com
o nome da missão, histórico (`hm-chat-user` "Você" e `hm-chat-event` "Rainha · texto", com
ícone de estado; o aviso de troca de equipe aparece como um evento "Equipe ·") e o formulário
"Sua mensagem para a Rainha" com "Enviar para a Rainha". O envio manda `ask {source, queen,
message}` e só fica habilitado nos estados `clarifying`, `awaiting_plan_approval` e
`awaiting_user` (`CHAT_STATES`); fora deles o campo explica o motivo
(`chatBlockedReason`). Textos longos quebram dentro do balão. `chatQueen(status, planning)`
usa a Rainha **atual** do elenco salvo, com a do planejamento só como reserva; se ela difere
da Rainha do início da missão, a gaveta avisa qual vale para as próximas mensagens.
"Solicitar ajuste" do cartão do plano abre a gaveta e foca o campo.

**Popup de entrega (`live-delivery.js`).** O `div.hm-delivery` fica no workspace do modo
real (mesmas classes `hm-delivery-*` da demonstração) e abre em `requestUi('delivery')`:
"Entrega · missão real" e "Fechar", o nome da missão (até duas linhas), a frase do
veredito (Aprovada ou Não aprovada pela verificação independente no ciclo N), os três
números (arquivos alterados, critérios aprovados, fora do plano), a tabela Tarefa, Abelha,
Arquivo e Situação (a tarefa dona vem dos arquivos do plano; sem dona, "Fora do plano"),
os critérios de aceite e a evidência, a "Versão da entrega" e, em `delivery_approved`, o
aviso do volume. "Aprovar entrega" (`awaiting_delivery_approval`) e "Incorporar entrega
aprovada" (`delivery_approved`) ficam aqui e na gaveta. `Esc` fecha. O popup só é
reconstruído quando muda o estado, a revisão ou o erro, para o polling não roubar o foco.

**Mensagens de erro.** `messages.js:describeCode` devolve "frase (código)" para todos os
códigos de erro e conflito de `backend.md` (incluindo os de `WorkspaceError`, `roster_incomplete`
e `tool_not_allowed`), todos os motivos de `job_error` (gate, turno, adaptadores, planejamento
e `job_failed`) e os erros do próprio front (`missão_ausente`, `configure_a_equipe`, ...).
`invalid_state:<estado>` vira "Ação indisponível no estado “<rótulo>”." (vale para todos os
estados); `turn_failed:...` e `api_error_<status>` viram uma frase genérica de falha do
provedor; código desconhecido vira "Erro inesperado (código)" (a busca usa `Object.hasOwn`,
então `toString` ou `constructor` também caem aí). `describeError(código, detalhe)` acrescenta
a abelha e o campo quando o erro os traz ("Abelha “x”: falta descrição, skills."). `stateLabel`
traduz os estados da missão (incluindo `abandoned`), `stateBadge` dá o selo curto do
cabeçalho da Missão e `stateSentence` a frase do Andamento. Usos: os avisos "Não foi
possível concluir: <frase>" das gavetas, o selo e as frases da Missão, a linha de
interrupção. O teste `test_every_documented_code_and_adapter_reason_has_a_portuguese_message`
lê `docs/hivemind/backend.md` e os adaptadores e falha se um código novo ficar sem frase.

### Cartão de colmeia vazia e popup de conexão (modo real)

Sem elenco, o cartão de colmeia vazia diz "Configure a Rainha, operárias e o verificador na
equipe." O popup de uma conexão selecionada diz "Conexão da equipe nesta missão." quando a
rota não tem descrição própria; as rotas do modo real trazem o texto de `linkInfo`
("A Rainha delega tarefas a <abelha> e recebe o resultado." e "Dependência: <abelha> só avança
com o que <outra> entregar.").

## 5. Colmeia

### `geometry.js`

Grade hexagonal em coordenadas axiais; `RADIUS = 72`, `HEX_WIDTH = 124.7077`;
`axialPoint([q,r]) = [HEX_WIDTH·(q + r/2), 1.5·RADIUS·r]`.

**Posições fixas hoje** (`AXIAL_SLOTS`, nada é calculado dinamicamente):

| Slot | `[q, r]` | Uso |
|---|---|---|
| `Q` | `[0,0]` | Rainha |
| `NW` `NE` `E` `SE` `SW` `W` | `[0,-2]` `[2,-2]` `[2,0]` `[0,2]` `[-2,2]` `[-2,0]` | 6 operárias do primeiro anel |
| `X1` `X2` | `[3,-3]` `[1,2]` | 2 posições extras de operárias |
| `S1` `S2` | `[-1,-3]` `[-2,-1]` | subagentes (só a demonstração usa) |

No modo real, as posições são preenchidas na ordem `NW, NE, E, SE, SW, W, X1, X2`
com os integrantes que não são Rainha, na ordem do elenco; `S1` e `S2` nunca recebem
integrantes reais. Como `deriveRealView` limita a 9 integrantes visíveis, **o teto atual da
colmeia é Rainha + 8**; quem passa disso não aparece, mesmo que o limite de execução do
backend (1–20) seja maior. Um integrante com papel `subagent` mantém o formato de célula
pequena de subagente, mas ocupa uma das posições de operária. Anéis adicionais, zoom e
navegação da colmeia são **planejados**, não existem no código: ver `roadmap.md`.

`meshGeometry()` desenha o favo de fundo (`r` de -11 a 11, `q` de -24 a 24, cortado em
|x|≤1800 e |y|≤1150), em cinco tons de mostarda escolhidos por uma função suave. O
`<svg class="hm-mesh">` tem 3600×2300.

`HoneycombRouter` roteia as conexões **pelas arestas do favo**, não em linha reta:
constrói o grafo de vértices (`q` -10..10, `r` -6..6, |x|≤900), e para cada conexão
roda Dijkstra do vértice de uma célula até o da outra. Custo: 1 por aresta, +8 para
vértices de células ocupadas (exceto origem e destino) e +2,5 para arestas já usadas por
outra rota. O resultado é cacheado por (conexões, posições ocupadas).

### `hive.js:createHiveView`

Cria `.hm-scene > .hm-world` (malha, `svg.hm-links`, `.hm-cells`), o HUD, o popup de
conexão e o cartão de colmeia vazia. `render(state)`:

- Escala do mundo: `max(.5, min(1, (largura útil − 60)/820, (altura útil − 40)/740))`,
  descontando as gavetas abertas (392 px cada lateral, 300 px a inferior). O mundo desce
  `(showSubs ? 54 : 24) × escala` px e mais `22 × escala` px quando há banner no HUD. No
  modo real, `showSubs` só é verdadeiro com subagente visível, então sem subagentes o mapa
  fica na mesma altura do protótipo. Com as três gavetas abertas, o teste de estouro avisa (sem
  falhar) que em 1396×612 a Conversa cobre as células de baixo e que em 1280×720 o HUD, mais
  largo que o mapa de 496 px, passa por baixo das gavetas laterais.
- Células por `ensureCell`: botão `.hm-cell` com polígono, realces, anel de progresso e
  uma abelha (`createBee`) de **64 px (Rainha), 56 px (operária), 40 px (subagente)**;
  nas linhas da lista de agentes da demonstração (`drawers.js:createRowIcon`) a abelha
  tem **26 px**. A Rainha tem polígono preto e efeitos próprios: varredura enquanto
  coordena, onda pequena no ajuste e três ondas grandes ao concluir (no modo real, a
  missão `completed` tem `phaseId: 'done'`). Abelha temporária ganha a etiqueta
  "Temporária" (`.hm-cell-tag`, também no modo real) e toda célula com progresso mostra o
  anel e o texto "x de y".
- Rotas por `renderLink`: base, pulsos e seta. Estados da conexão (`STATE_INFO`): `idle`,
  `out` (tarefa delegada), `del` (em execução), `wait`, `flow`, `in`, `done`, `ret`,
  `fail`. Rotas **ativas** (`out`, `in`, `flow`) são violeta `#6500C9` com pulsos
  (simples em `out`, duplos em `in`/`flow`); `in` e `ret` invertem o sentido do desenho;
  `fail` mostra um quadrado com "X" no meio; `wait` é tracejada e `idle` pontilhada. Clique ou Enter/Espaço
  na rota abre o popup "Conexão".
- Estado da célula: `idle`, `working`, `coord`, `waiting`, `approval`, `done`, `failed`
  (texto curto: "Disponível", "Trabalhando", "Coordenando", "Aguardando", "Aguarda você",
  "Entregue", "Falhou"). O estado é copiado para o `data-state` da abelha. No modo real
  os estados e as rotas vêm de `deriveRealView` (seção 4), a partir do backend.
- HUD: ramo da demonstração ("Missão simulada") e ramo real (`state.real`: "Missão real",
  sete hexágonos, texto da etapa, botão `hudAction` e banner `requestUi`; seção 4).
- Entrada de texto é sempre colocada por `textContent`, nunca como HTML.

## 6. Animação das abelhas

`bee-animation/bee.js:createBee({queen, state, size, paused, reduced})` devolve um
`<svg viewBox="0 0 1254 1254">` com `g.hm-bee-rig` contendo três `<image>` alinhadas:
`asa-esquerda`, `asa-direita` e `corpo-sem-asas` (pasta `rainha-animacao/` ou
`operaria-animacao/`). `updateBee(svg, {state, paused, reduced})` só altera `data-*`.
O rig de três PNG foi mantido por decisão expressa (tamanhos 64/56/40/26 px); é a única
exceção visual deliberada em relação ao protótipo.

`bee.css` anima por `data-state`:

| Estado | Animação |
|---|---|
| `working`, `coord` | asas batendo (`.18 s`; Rainha `.26 s`) e flutuação vertical do rig |
| `waiting`, `approval` | asas oscilando devagar (`2,8 s`) |
| `idle`, `done` | leve subida e descida do rig (`3,5 s`) |
| `failed` | sem animação própria |

Pausa e redução de movimento:

- `data-paused="true"` e qualquer abelha dentro de `.hm-page[aria-hidden="true"]` ficam
  com `animation-play-state: paused`.
- `data-reduced="true"` ou `@media (prefers-reduced-motion: reduce)` desligam
  animações e transições (`animation:none`). O `hive.css` repete a regra para toda a
  página.
- `hive.js` copia `state.animationsPaused` e `state.reduced` para cada abelha. A
  demonstração pausa quando a página não está ativa, a aba do navegador está oculta
  (`visibilitychange`) ou o usuário pausou; o modo real pausa quando inativo, oculto ou
  com movimento reduzido.

## 7. Demonstração

Ficção local sobre "conferir pedidos recebidos por e-mail e preparar um relatório de
divergências", em sete etapas (`STEPS`: Plano, Coleta, Análise, Revisão, Aprovação,
Relatório, Entrega). Nada sai da página.

- **`simulation.js:HiveSimulation`**: relógio por fase (`PHASES` em `demo-data.js`, cada
  fase com `dur`, `agents`, `links`, `next`), pausa manual e por visibilidade,
  `go/start/pause/resume/nextStep/restart`, aprovação (`approve`), ajuste (`adjust`, que
  passa de 4 para 3 divergências), falha e nova tentativa (`retry`), entrega
  (`setDelivery`; abre sozinha depois de 1,6 s na fase final, 0,4 s com movimento
  reduzido), conversa (`sendMessage`; a mensagem durante uma missão em andamento só
  enfileira o aviso "A Rainha recebe um novo pedido quando a missão atual terminar.") e o
  CRUD simulado. Os relógios e timers são injetáveis (`now`, `schedule`, ...), o que
  permite testar sem navegador.
- **Cenários** (botões do cabeçalho, `setScenario`): `mission` ("Missão"), `empty`
  ("Colmeia vazia", sem agentes e com cartão convidando a ver o exemplo) e `failed`
  ("Etapa com falha": entra direto na fase `fail`, com Cadastros falhando e o botão
  "Tentar novamente").
- **CRUD simulado** (`addWorker`, `removeSelected`): até **3 operárias** de demonstração,
  nos slots livres `W`, `X1`, `X2`; **nome obrigatório com até 16 caracteres** e
  **especialidade com até 40**; remover uma operária preserva o slot das demais e o
  próximo cadastro reutiliza só a célula livre. Cada uma começa sem tarefa ("Sem tarefa
  nesta missão.") e o texto digitado é exibido como texto puro.
- **`drawers.js:createDrawers`**: gaveta **Agentes** (lista, detalhes com abas "Visão
  geral", "Tarefas", "Skills", "Ferramentas", "Relações"; a Rainha só tem três abas;
  mostrar/ocultar subagentes; formulário de nova operária), gaveta **Missão** (abas
  "Plano", "Responsabilidades", "Conexões", "Entrega"; aprovar/ajustar), gaveta
  **Conversa** ("Conversa com a Rainha", envio "Enviar para a Rainha") e o painel
  de entrega com as divergências. `Esc` fecha a entrega (`app.js`).
- Ações do HUD/gavetas: "Simular missão", "Pausar/Continuar", "Avançar etapa",
  "Reiniciar", "Solicitar ajuste", "Tentar novamente", "Simular novamente".
- Os subagentes `Anexos` (`S1`) e `Mensagens` (`S2`) só existem aqui; aparecem quando
  `showSubs` é verdadeiro (ao selecionar um subagente ou pelo botão da gaveta).

## 8. Paleta e CSS (essencial)

Tokens declarados em `.hm-page` (`hive.css`): `--hm-mustard:#B8860B` (fundo da página),
`--hm-paper:#F1EDE4` (cabeçalho e cartões), `--hm-violet:#6500C9` (rotas ativas),
`--hm-dark:#2A2622` (botões escuros); texto `#000`; fonte do corpo `Source Sans 3`,
títulos `Space Grotesk`. Gradientes de célula em `hive.js:createMesh` (mostarda) e
`#17140F`/`#000` para a Rainha.

**Classes.** O modo real usa as **mesmas classes da demonstração** (`hm-drawer`, `hm-agents`,
`hm-agent-row`, `hm-tabs`, `hm-agent-detail`, `hm-tool`, `hm-approval`, `hm-plan-row`, `hm-duty`,
`hm-connection-row`, `hm-chat-*`, `hm-delivery-*`, `hm-hud-*`, `hm-pull-*`, `hm-cell-*`, ...); só o
contêiner se chama `.hm-live-workspace`. As classes `hm-live-*` do primeiro modo real
(`hm-live-body`, `hm-live-field`, `hm-live-bee`, `hm-live-details`, `hm-live-verdict`,
`hm-live-chat`, `hm-live-notice`) **foram apagadas** em 26/10/2026 (um teste confere que não
voltam). O que só existe com dados reais fica no fim de `hive.css`, no bloco "Gavetas do modo
real": `hm-quick-edit`, `hm-catalog-row`, `hm-worker-form` (campos empilhados),
`hm-limit-edit`, `hm-mission-picker`, `hm-select`, `hm-hash`, `hm-create-card`,
`hm-row-incomplete` e as regras `.hm-live-workspace ...` abaixo.

**Regras contra estouro** (V08): gavetas e popup de entrega quebram qualquer texto
(`overflow-wrap:anywhere`); selo do estado com no máximo 190 px e reticências; nome da
missão em uma linha, objetivo em duas e caminho do projeto em uma (`-webkit-line-clamp`, texto
inteiro no `title`); nome da missão no popup de entrega em duas linhas; células da tabela da
entrega com `min-width:0`. Reticências e `line-clamp` são truncamentos de projeto: o teste de
estouro (`testes.md`) os aceita.

**Altura mínima.** `.hm-page` tem `min-height:560px` (era 760 px): com altura de 600 px ou
mais a Conversa aberta fica inteira visível, e abaixo de 820 px as abas laterais sobem 150 px
quando a Conversa está aberta.

Atenção: a "Paleta Hive Mind" citada em `docs/frontend.md` (`--bg:#14120c`,
`--ink:#ECE4D4`) é a do `index.html` do Hub, não a desta página.

## 9. O que não alterar

- `server.py` e `index.html` só têm os encaixes existentes (import e
  `register_blueprint` no servidor; a tag de script no HTML). Nada novo vai ali.
- `codex_frontend/static/providers.js` é a dependência de navegação: não renomear
  `registerPage`, `selectPage`, `canUseAssistantUI`, `#assistantNavigation` ou
  `data-page="hive"`, nem o id `hive`.
- O blueprint estático não deve ganhar rota de assistente (`/hive-ui/ask` etc. devolvem
  404 por teste).
- `HiveMind/prototipo/` é a referência visual (ver abaixo) e tem hashes conferidos por
  teste; não editar.
- O rig PNG e os tamanhos 64/56/40/26 px são decisão expressa.

`HiveMind/prototipo/` guarda o protótipo aprovado (`Hive Mind.dc.html`,
`Hive Mind v1.dc.html`, `support.js`, `assets/`, `uploads/`, `.thumbnail`). Serve só de
comparação visual (o `hivemind_visual_compare.mjs` o carrega com React); o runtime
nunca importa `support.js` nem o editor do protótipo.

## 10. Armadilhas

- **"A página é só demonstração"** é texto antigo e falso. O padrão é o modo real;
  registros anteriores a 21/10/2026 ainda podem dizer o contrário.
- O visual aprovado no ciclo 7 deve ser preservado; qualquer mudança em `hive.css`,
  `hive.js`, `geometry.js`, `drawers.js` ou nos módulos `live-*.js` deve ser conferida com
  `tests/hivemind_visual_compare.mjs` (demonstração e modo real contra o protótipo; fontes
  carregadas, DPR 1, animações congeladas) e `tests/hivemind_overflow.mjs` (estouro). Os dois
  precisam do `NODE_PATH` com `playwright` e `sharp` (`testes.md`).
- **Componentes compartilhados:** as peças de `drawers.js` que os módulos `live-*.js`
  importam (`el`, `svg`, `label`, `hex`, `caret`, `statusIcon`, `trailSample`, `statusShort`)
  são exportadas de propósito. Mudar uma delas muda a demonstração **e** o modo real.
- **O front não recalcula o que o backend entrega.** Status de tarefa, progresso, ferramentas
  usadas e ciclo do job vêm do `bees_summary`; mexer na regra é mexer em `summary.py`, não
  em `mission-state.js`. Só o status das tarefas tem um cálculo de reserva a partir dos jobs
  (missão sem resumo).
- **Aprovar só pelos cartões e pelo popup.** O HUD nunca aprova (`hudAction` só abre a
  gaveta ou o popup, ou envia `start`, `pause` e `resume`). "Solicitar ajuste" só existe no
  cartão do plano: em `awaiting_delivery_approval` o backend recusa mensagem à Rainha.
- **Formulários persistentes.** O formulário de abelha, o de missão, o campo de limite e o
  popup de entrega não são reconstruídos pelo polling de 2,5 s; ao mexer neles, preserve
  isso ou o usuário perde o que digitou.
- **Popup de entrega estreito.** Com janela de 1280 px e gavetas laterais abertas o popup tem
  376 px úteis; no modo real a grade `.hm-delivery-row` usa `56px min(140px,22%) minmax(0,1fr)
  min(170px,27%)` para a coluna Arquivo não zerar (defeito achado e corrigido em 26/10/2026).
  Não volte às colunas fixas da demonstração no modo real.
- O leitor de modelo da navegação (`providers.js:updateReadout`, ativo quando a página é
  `hive`) diz "HIVE MIND · MISSÕES COM CLAUDE E CODEX". O arquivo fica fora de `HiveMind/`;
  só mexer com autorização.
- Código novo de erro, conflito ou motivo no backend precisa de frase em `messages.js`
  (o teste acima avisa); sem ela a tela mostra "Erro inesperado (código)".
- Mexer na ordem dos slots (`AXIAL_SLOTS`) muda a posição de todo mundo e o roteamento,
  que é cacheado por slot.
- Subagente real ocupa slot de operária; subagentes `S1`/`S2` são só da demonstração.
- Acesso `/hive-api` exige origem local; fora do Hub (outro host/porta) toda chamada
  falha com `local_origin_required`.
- Só o modo real chama o backend; confira em qual modo está antes de diagnosticar "nada
  acontece" (a demonstração não grava nada).
- `window.hiveMindDemo` e `window.hiveMindLive` existem desde o carregamento, mesmo com
  a página oculta.
