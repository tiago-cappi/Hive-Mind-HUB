# Hive Mind — testes
Atualizado em 26/10/2026 · descreve o código atual; o que é planejado fica em `roadmap.md`.

A suíte do Hive Mind roda junto com a do Hub (pytest) e não precisa de conta, modelo,
rede nem da porta 8765: os adaptadores são testados com um CLI falso e com
dublês de protocolo. Há ainda quatro scripts Node (um de comportamento e três de
navegador: QA do Hub, comparador visual e teste de estouro) e um **harness de validação
real** com IA, que só roda com autorização explícita do usuário. Em 26/10/2026 o pytest
coleta 462 testes no total, 232 deles do Hive (`-k hivemind`); as bases anteriores foram
459 e 229 (fim do lote de backend da tarefa do visual real, 26/10/2026) e 413 e 183
(25/10/2026).

## 1. O que cada teste cobre

### pytest (`tests/`)

| Arquivo | Cobre |
|---|---|
| `test_hivemind_frontend.py` (19) | Blueprint estático serve todos os assets nativos e **não** responde `/hive-ui/ask`, `stt`, `session_start`, `session_reset`, `abort`, `speak` nem `../routes.py`; protótipo movido por inteiro com hashes SHA-256 conferidos e runtime sem `support.js`/React/iframe; aba Hive separada do provider (nunca cria sessão); os seis guardas `canUseAssistantUI` do `index.html` (e ausência deles no `askAndSpeak`/`onRecStop`); textos e contrato de acessibilidade da demonstração; roda `hivemind_frontend_behavior.mjs` (pula se não houver Node); controles de limite de ciclos e reconciliação; cursor `?after=` e teto de 500 eventos; `validateTeam` e `chatQueen`; textos que dizem que o backend existe e que a demonstração é separada; HUD do modo real com estado traduzido; **modo real com o visual do protótipo** (26/10/2026): HUD e colmeia usam o snapshot real sem chamar a API (`hudAction`, `requestUi`, `onUiRequest`, `deriveRealView`, `missionStep`, os sete nomes de etapa, `bees_summary` e a etiqueta `.hm-cell-tag`); gavetas divididas por finalidade (compositor com menos de 40 linhas e módulos `live-*.js`), componentes `hm-*` da demonstração reutilizados, classes `hm-live-*` antigas, `window.confirm` e `<pre>` ausentes e `min-height:760px` removido; os módulos `live-*.js` são servidos e nunca chamam a API; erros da API guardam `detail` e `describeError` existe. |
| `test_hivemind_api.py` (17) | Rotas `/hive-api`: origem local, lease e aprovação preservada; o formato do beacon de saída é aceito pela rota de presença; comando `abandon` (replay, recusas) e missão `abandoned` recusando todos os comandos. |
| `test_hivemind_bees.py` (45) | Cadastro rico (VR-01 a VR-03): limites de `description`, `skills` e `tools` (verificador e Rainha sem `patch`); gravação que preenche `instructions`, recusa abelha nova incompleta com `{bee, field}` e tolera a antiga idêntica; `/status` com `roster.incomplete`; `roster_incomplete` no `ask` (serviço e rota, com e sem cadastro); `validate_plan` exigindo os campos em toda abelha; esquema e prompt da Rainha com o cadastro e plano guardado com a abelha exata do cadastro; **broker por abelha** (construção com subconjunto, `tool_not_allowed` sem chamar o handler e sem derrubar o job nos dois adaptadores, recusa antiga para nome fora do catálogo, pausa); `session_params` só com as ferramentas pedidas e esquema de `progress`; jobs com as ferramentas do cadastro, plano antigo com o padrão do papel; `progress` (evento `bee_progress`, 12 argumentos inválidos recusados sem derrubar o job, nenhum arquivo tocado, Rainha de correção sem `progress`); perfil e explicação de `progress` na primeira linha de cada prompt; `bees_summary` (status de tarefa, progresso do último job, `tools_used`, 700 eventos além dos 500 do front, missão sem plano, com planejamento antigo e vazia) e a rota `GET /missions/<id>`. |
| `test_hivemind_service.py` (42) | Presença (todas as telas, carência, heartbeat expirado, saída do Hub nunca retoma sozinha); job com broker escopado e verificador em sessão distinta, que recebe do backend `changed_files` e `files_outside_plan` (com um arquivo fora do plano); planejamento da Rainha só com leitura antes da aprovação; resultado de planejamento estrito; motivos de falha nunca expõem texto do provedor; despachante respeita o limite global; Rainha coordena veredito reprovado; recusa de iniciar no teto de ciclos antes de qualquer snapshot; schemas estruturados fechados; missão `abandoned` ignorada por saída, recuperação e despacho; motivos de falha cobrem todos os códigos fixos dos adaptadores. |
| `test_hivemind_missions.py` (19) | Encerramento (`abandon`) só em `recovery_required` e regra do journal pendente; `abandoned` terminal; aprovação versionada e idempotente que precede o trabalho; ciclos e veredito independente não reiniciam; revisão concorrente e recuperação de falha; plano que escapa da raiz, dependências inválidas, Rainha como operária. |
| `test_hivemind_scheduler.py` (11) | Reservas (tarefa uma vez, estado de pausa); operária e subagentes dividem os slots, Rainha separada; identidade do processo registrada; geração de plano reaprovado; efeito desconhecido exige recuperação; plano igual após o teto exige limite maior; missão `abandoned` não recebe job. |
| `test_hivemind_lifecycle.py` (3) | Pausa nega novas ferramentas, espera o que foi admitido e só então interrompe, e exige retomada; lease de controle exclui outra aba até expirar; missão `abandoned` não pausa nem retoma. |
| `test_hivemind_workspaces.py` (14) | Snapshot exclui privado e estado e detecta mudança; broker restringe `read`/`patch` e escrita do verificador; links e arquivos compartilhados não são seguidos; aliases e dispositivos do Windows rejeitados; geração do runtime endereçada por hash; projeto Git usa worktree e preserva arquivos sujos; leitura extra dos checks só para nome puro numa pasta do `PATH` (nunca a atual), pasta do programa e venv concedível (com `home` absoluta, com `python.exe` e concedível), nunca raiz, pasta do usuário e filhos diretos, raízes do `AppData`, `OneDrive*`, outros perfis, candidato ou scratch; perfil `hive-verify` conferido com exatamente essas leituras; com RPC falso, o check envia `timeoutMs`, espera o teto mais 60 s, inclui as leituras no perfil, executa o caminho resolvido e põe o cache do pytest no scratch. |
| `test_hivemind_delivery.py` (26) | Entrega exige aprovação exata e preserva histórico; mudança na origem ou no candidato invalida; volumes diferentes recusados antes de mutar; rollback parcial; escritas concorrentes retidas; adições/remoções limitadas ao pacote aprovado (remoção vai para quarentena); reconciliação de origem desatualizada (nova base e candidato, conflito preserva versões, replay, interrupção, boot, barreira de fechamento); encerramento após apply falho, journal vazio ou ilegível e reinício no meio do apply. |
| `test_hivemind_adapters.py` (17) | Descoberta Codex/Claude sanitizada, sem expor identidade ou chave de API e sem iniciar turno; gate não confunde catálogo com permissão; exige sessão verificada e cobrança vigente; sessão Codex rejeita ambiente nativo e MCP ligado; pedido inesperado do servidor falha fechado; pausa do broker; sessões de candidato sem superfícies nativas; versão mais nova do Claude só com todas as flags de isolamento; catálogo só com as famílias mais novas; lançador sob `pythonw` entrega os pipes ao CLI; `close()` mata o CLI órfão e não trava, inclusive quando o lançador saiu sozinho (Job Object) (só no Windows, com processos reais e sem IA); o job é liberado mesmo se o fechamento falhar e criá-lo nunca levanta. |
| `test_hivemind_adapter_turns.py` (19) | Turnos com dublê de RPC (`FakeRpc`): Codex usa thread fixada e broker; Claude só com laço de modelo, sem ferramentas nativas; falhas guardam só categoria segura; resposta de ferramenta dentro do dreno da pausa; lançador opt-in valida comandos e ignora perfil pessoal; ambiente do Hive exclui vault e guarda pessoal; item de ferramenta nativa do Codex falha fechado; `output_schema` só quando dado; só a mensagem `final_answer` vira a saída quando há comentário antes. |

### Node (`tests/*.mjs`)

| Arquivo | Cobre |
|---|---|
| `hivemind_frontend_behavior.mjs` | Roda sem navegador, importando os módulos reais. Máquina de estados de `HiveSimulation` (fases, pausa, visibilidade, entrega com timers injetados e movimento reduzido, cenários, limite de 3 operárias, CRUD); entrada tratada como texto; `HiveMissionState` com `fetch` simulado (paginação de 200, teto de 500 eventos, troca de missão e de cursor, `bees_summary` guardado e zerado, ações do HUD); `validateTeam` e `chatQueen`; **gavetas do modo real com DOM mínimo** (VR-04 a VR-07): abas puxadoras com contador e gavetas fechadas `inert`, recuperação sem botão de avanço e encerramento confirmado na própria gaveta, interrupções (F9) e limite de ciclos (F8) legíveis, aprovações do plano e da entrega com hash curto e sem JSON, popup de entrega (abre por `onUiRequest`, fecha com Esc), criar missão com erro por campo e campos limpos (F7), equipe incompleta bloqueando o planejamento, Conversa (balões e habilitação), Agentes (linhas, marcas, contadores, abas, skills e ferramentas, "Consultar modelos" com carregamento, excluir só operária permanente, formulário completo com erro no campo certo); **snapshot real** com etapas, estados, rotas, progresso fino, temporárias, ordem e teto Rainha + 8. Imprime `hivemind behavior ok`. |

| `hivemind_visual_compare.mjs` | Navegador. Duas partes: (1) a **demonstração** contra o protótipo (`HiveMind/prototipo/`), por região, em 3 viewports e 6 estados congelados, com imagens, diffs e geometria dentro de 1,01 px; (2) o **modo real** contra o protótipo, em 13 casos com `/hive-api` falso (critério na seção 3). Grava imagens, diffs, `real/` e `metrics.json`. |
| `hivemind_overflow.mjs` | Navegador. Teste de estouro (V08) do modo real, com os textos longos da fixture `hivemind_real_longo.json`, em 1280×720, 1920×1080 e 1396×612, seis estados da missão e todas as telas das gavetas, do HUD e dos popups (critérios na seção 3). Falha listando elemento, medida e contexto. |
| `hivemind_browser_qa.mjs` | QA em Chrome real (Playwright) sobre o `index.html`: entra e sai da aba Hive com seis sessões, microfone adiado descartado, nenhum endpoint de assistente chamado, rascunhos, entrega, CRUD e XSS como texto, cenários, tamanhos 1280×800/1440×900/1920×1080, volta a Claude/Codex, painel completo, mobile. Captura imagens e falha em qualquer erro de console. Desde 26/10/2026 ele abre a demonstração pelo botão `.hm-mode` antes dos passos dela, responde um `/hive-api` mínimo (para o modo real não gerar 404) e escopa os seletores em `.hm-demo-workspace`. |

As regressões C2 também verificam o executável do PATH quando há homônimo no diretório
atual, o broker de planejamento com os dois provedores e cadastro legado ou sem leitura,
e o carregamento da consulta de modelos nos formulários de criação e edição com foco preservado.

### Fixtures

**`tests/fixtures/hivemind_real_*.json`** alimentam o `/hive-api` falso dos dois scripts de
navegador do modo real. Formato (o mesmo das respostas do backend):

```json
{"about":"...",
 "status":{"settings":{"worker_limit":2,"revision":1},"roster":{"bees":[...],"revision":1,"incomplete":[]},"providers":["claude","codex"]},
 "catalog":{"codex":{"authenticated":true,"compatible":true,"errors":[],"models":[{"name":"gpt-x","efforts":["low","high"]}]},"claude":{...}},
 "scenarios":{"running":{"mission":{...},"jobs":[...],"events":[...],"roster":[...],"bees_summary":[...]}, "...":{}}}
```

Cada cenário é o corpo de `GET /missions/m1` (`mission`, `jobs`, `events`, `roster`,
`bees_summary`) e tem o estado da missão como nome: `running`, `awaiting_plan_approval`,
`awaiting_delivery_approval`, `recovery_required`, `awaiting_user` (limite de ciclos e
`job_error`) e `completed`. O servidor falso monta `/status`, `/catalog`, `/missions` (a lista
com a missão do cenário atual) e `/missions/m1?after=` (só os eventos com `seq` maior).

| Arquivo | Conteúdo |
|---|---|
| `hivemind_real_paridade.json` | Equipe do protótipo (Rainha, Documentos, Cadastros, Análise, Relatórios e o verificador Revisão, nos mesmos encaixes da colmeia) com textos curtos: serve à comparação com o protótipo (V09). |
| `hivemind_real_longo.json` | Mesmos cenários com textos longos e sem espaço (descrição, tarefas, objetivo, caminho do projeto, evidência, arquivo fora do plano) e uma abelha temporária: serve ao teste de estouro (V08). |

Os arquivos são gerados uma vez e versionados; edite-os à mão (ou regenere) mantendo o
formato do backend. Eles não têm dados pessoais.

**`tests/fixtures/hivemind/fake_cli.py`** é um CLI finito que imita `claude` e `codex` sem
conta nem modelo (primeiro argumento: o provedor). É usado por `test_hivemind_adapters.py`
como comando dos adaptadores. Simula:

- `--version`: `codex-cli 0.160.0` e `2.1.289 (Claude Code)`;
- Claude: `--help` com as flags de isolamento, `auth status --json` e o modo `--print`
  com `initialize`, `get_settings` e `get_usage` (modelos `sonnet` e `fable`, cota
  ordinária disponível, `extra_usage` desligado);
- Codex: `app-server --stdio` com `initialize`, `account/read`, `model/list`
  (duas páginas), `account/rateLimits/read`, `config/read` (MCP), `thread/start`
  (perfil `:read-only`, ambiente vazio) e `mcpServerStatus/list`.

Variáveis de ambiente mudam o comportamento: `HIVEMIND_FIXTURE_LOG` (arquivo onde cada
requisição é registrada), `HIVEMIND_FIXTURE_CHANGED` (arquivo marcador que, ao existir,
faz a configuração MCP mudar), `HIVEMIND_FIXTURE_BAD_THREAD` (thread com ambiente
externo), `HIVEMIND_FIXTURE_BAD_MCP` (MCP "conectado") e
`HIVEMIND_FIXTURE_SERVER_REQUEST` (pedido inesperado do servidor). Dados de identidade
do fixture são fictícios (`private-fixture@example.invalid`).

`tests/conftest.py` só põe a raiz do repositório no `sys.path` (os testes fazem
`import server`/`import HiveMind`). Não há `pytest.ini`.

## 2. Comandos

Sempre a partir da raiz do projeto (PowerShell):

```powershell
# suíte do Hive Mind (232 testes)
./.venv/Scripts/python.exe -m pytest tests -q -k hivemind

# só o front-end (19 testes; inclui o behavior.mjs se houver Node)
./.venv/Scripts/python.exe -m pytest tests/test_hivemind_frontend.py -q

# suíte completa do Hub (462 testes)
./.venv/Scripts/python.exe -m pytest tests -q

# comportamento do front-end, direto no Node
node tests/hivemind_frontend_behavior.mjs
```

Os scripts de navegador (comparador e estouro) precisam do `NODE_PATH`; os comandos estão
na seção 3.

Nas verificações independentes foram usados também `PYTHONDONTWRITEBYTECODE=1`,
`-p no:cacheprovider` e `--basetemp=.test-tmp/<nome>` (por exemplo
`.test-tmp/hive-independent-c4/pytest`), para não deixar sobras fora de `.test-tmp/`.

**Observação de ambiente.** Em sandboxes em que `TEMP`/`TMP` não são graváveis ou ficam
fora do projeto, `test_git_project_uses_worktree_and_preserves_dirty_files`
(`test_hivemind_workspaces.py`) é o candidato natural a falhar, porque cria um
repositório Git e um `git worktree` dentro de `tmp_path`. Nesse caso, use
`--basetemp=.test-tmp/<nome>` (dentro do projeto), como já recomenda `docs/operacao.md`
para o temporário do sandbox, e **não enfraqueça o teste**. Em 21/10/2026, com o temporário
padrão do usuário, os 11 testes de `test_hivemind_workspaces.py` (na época) passaram; a falha em
sandbox não foi reproduzida aqui. O teste pula sozinho se `git` não existir.

## 3. QA no navegador

Os três scripts `.mjs` de navegador (`hivemind_browser_qa.mjs`, `hivemind_visual_compare.mjs` e
`hivemind_overflow.mjs`) **não rodam no pytest** e não fazem parte da suíte automática.
Pré-requisitos (nenhum está no repositório, que não tem `package.json` nem `node_modules`;
**não instale pacotes no projeto**):

- Node (v22 no ambiente atual) e os pacotes `playwright` (todos) e `sharp` (só o comparador),
  resolvíveis pelo Node via `NODE_PATH`. Nesta máquina (verificado em 26/10/2026, Playwright
  1.60 e sharp 0.34):

  ```powershell
  $env:NODE_PATH = "C:/Users/m.rafael/Desktop/projetos/CRM Clean Environment Brasil/frontend/node_modules;C:/Users/m.rafael/Desktop/Projetos Pessoais/forest-os-web-master/forest-os-web-master/node_modules"
  ```

  (a primeira pasta tem o `playwright`, a segunda o `sharp`; no Git Bash use o mesmo valor com
  `export NODE_PATH=...`). Em outra máquina, aponte para qualquer `node_modules` que tenha os dois.
- Chrome em `C:/Program Files/Google/Chrome/Application/chrome.exe` (caminho fixo no código).
- Fontes do Google carregadas (rede): sem elas o comparador deixa de ser válido (ele confere
  `document.fonts.status`).
- Só o comparador e o QA: React e ReactDOM vendorizados em `.test-tmp/hivemind-bees/react.js` e
  `react-dom.js` (há `download-react.cjs` na pasta) e o protótipo em `HiveMind/prototipo/`, para a
  página de referência; o comparador também lê o `support.js` do protótipo.

Como rodam: cada script sobe um servidor HTTP próprio em `127.0.0.1` numa porta
aleatória, serve `index.html`, `codex_frontend/static`, `HiveMind/frontend/static`, `assets/` (e o
protótipo, nos dois primeiros) e **simula** os endpoints do Hub (`/ask`, `/stt`, `/speak`,
`/session_*`, `/hud_ping`, etc.) e, no comparador e no estouro, o `/hive-api` com as fixtures
`hivemind_real_*.json`. Não tocam a porta 8765, não iniciam processos `claude`/`codex`, não
abrem microfone real e nunca fazem turno de IA.

```powershell
node tests/hivemind_visual_compare.mjs [pasta-de-saída]   # ~1 min
node tests/hivemind_overflow.mjs [pasta-de-saída]         # ~1 min
node tests/hivemind_browser_qa.mjs [pasta-de-saída]       # ~30 s
```

Saídas padrão (o argumento opcional troca a pasta):

| Script | Pasta padrão | Conteúdo |
|---|---|---|
| `hivemind_browser_qa.mjs` | `.qa-arquivo/2026-10-10_hivemind-frontend-hub/qa` | capturas `runtime-1440x900-working.png`, `runtime-1280x800-drawers.png`, `runtime-1920x1080-failure.png` e demais; JSON final no console |
| `hivemind_visual_compare.mjs` | `.qa-arquivo/2026-10-10_hivemind-frontend-hub/qa-atual` | demonstração: pares nativo × referência (1280×800, 1440×900, 1920×1080; `states/` com 6 estados: p2b-subagent, approval, failure, done, selected-link, worker-form) e diffs por região; modo real: `real/real-<caso>-1440x900.png`, `real/reference-<caso>-1440x900.png` e `real/recortes/`; `metrics.json` |
| `hivemind_overflow.mjs` | `.qa-arquivo/2026-10-25_hivemind-visual-real/qa-estouro` | `estouro.json` (verificações, problemas e avisos) e, em caso de falha, capturas dos casos ruins |

`.qa-arquivo/` é uma pasta oculta na raiz, fora de `docs/` (as capturas históricas do
ciclo de 10/2026 foram movidas para lá).

### Comparador do modo real (V09)

A demonstração continua sendo comparada como no ciclo 7: o script a abre pelo botão
`.hm-mode` e confere a geometria (≤ 1,01 px) em 3 viewports parados e 6 estados.

O **modo real** é comparado com o protótipo (React do `Hive Mind.dc.html`, fixado por hash;
cada elemento tem um `data-dc-tpl` estável) em 13 casos, sempre com fontes carregadas, DPR 1,
movimento reduzido nos dois lados e animações/transições desligadas por CSS. A fixture é a
`hivemind_real_paridade.json`:

| Caso | Modo real (fixture) | Protótipo |
|---|---|---|
| `execucao` | `running`, agente `documentos` selecionado, três gavetas abertas | `p2b` com Documentos selecionado |
| `aprovacao` | `awaiting_delivery_approval` (etapa 5) | `approval` (etapa 5) |
| `falha` | `awaiting_user` com limite de ciclos | `fail` |
| `entrega` | `completed`, popup aberto pelo botão "Ver entrega" do HUD | `done` com o popup |
| `aba-tarefas`, `aba-skills`, `aba-ferramentas`, `aba-relacoes` | `running`, agente `documentos`, a aba correspondente do detalhe | `p2b` com Documentos e a mesma aba |
| `aba-rainha` | `running`, Rainha, aba Relações (responsabilidades distribuídas) | `p2b` com a Rainha |
| `missao-resp`, `missao-conex` | `running`, aba Responsabilidades ou Conexões da Missão | `p2b` com a mesma aba |
| `missao-entrega` | `completed`, aba Entrega da Missão | `done` com a aba Entrega |
| `conexao` | `running`, rota selecionada | `p2b` com a rota `doc-ana` |

Como os textos do modo real são dados reais e diferem dos do protótipo, **o texto não é
comparado**; compara-se a estrutura e o estilo dos 268 pares de componentes equivalentes
(abas puxadoras, células da Rainha e da operária, HUD e banner, cabeçalhos, contadores,
linhas e detalhe dos agentes com as abas Tarefas, Skills, Ferramentas e Relações, rodapé,
cabeçalho da Missão, Andamento, tira de etapas, cartões de aprovação e de falha, abas
Plano, Responsabilidades, Conexões e Entrega, Conversa, balões e formulário, popup de
entrega, popup da conexão):

- **Estilo computado**: fonte, tamanho, peso, entrelinha, espaçamento de letras, caixa do
  texto, cor, fundo, bordas, raio, sombra, espaçamento interno e opacidade, com tolerância de
  0,51 px nos números. As chaves de texto só valem quando os dois elementos têm texto próprio.
- **Dimensões e posição** (`w`, `h`, `x`/`y`) só onde o conteúdo não decide a medida, com a
  mesma tolerância de 1,01 px do ciclo 7 (gavetas, cabeçalhos, abas puxadoras, célula da
  Rainha e da operária, popup de entrega e de conexão, tira de etapas).
- **Pixels** em recortes sem texto (abas puxadoras): no máximo 0,5 % dos pixels com diferença
  maior que 32 em algum canal. A região do mapa entre as gavetas é comparada por pixel com o
  rig PNG das abelhas **mascarado** (D4) e o resultado só é **informado** em `metrics.json`
  (13,2 % no modo real contra 6,6 % na demonstração, porque o mapa real fica 20,6 px abaixo).
- **Linha de base**: os mesmos pares são medidos na demonstração, aprovada no ciclo 7. Uma
  diferença só **falha** se o modo real difere do protótipo **e** da demonstração. Se for igual
  à da demonstração (142 casos em 26/10/2026, quase todos de acabamento: peso 700 contra 600
  nos títulos, espaçamento de letras, preenchimento interno dos botões de ícone, cor das
  etapas futuras do HUD), ela é herdada e fica listada em `metrics.json` (`real.inherited`).
- **Diferenças conhecidas** (`KNOWN` no script, com o motivo; ficam em `real.known`): a lista
  está vazia desde 26/10/2026. As duas que existiam (mapa 20,6 px abaixo por `showSubs` fixo e
  botão "Ver entrega" com 38 px) foram corrigidas no ciclo 1.

Resultado em 26/10/2026: demonstração 3 pares parados e 6 de estado; modo real 268 pares e 2
recortes comparados nos 13 casos (execução 90, aprovação 74, falha 22, entrega 18, abas do
agente 35, abas da Missão 21, conexão 8), 0 falhas; depois das correções do ciclo 1, nenhuma diferença conhecida. Substituir um estilo no modo real (por exemplo o tamanho da fonte do
nome na lista, a cor do cartão de aprovação ou a largura da aba) faz o teste falhar listando
o par, a chave e os três valores (conferido em 26/10/2026 com CSS injetado).

### Teste de estouro (V08)

`hivemind_overflow.mjs` usa a fixture `hivemind_real_longo.json` e, para cada um dos seis
estados da missão e cada tamanho de janela (1280×720, 1920×1080 e 1396×612, que deve exibir a
Conversa inteira), com as três gavetas abertas, confere a tela padrão, as quatro abas da Missão,
o detalhe de cada agente com todas as abas (Rainha, operária, temporária e verificador, nos
estados em execução e aguardando você), os formulários de abelha (criar, editar, com catálogo
e com erros), a criação de missão com erros, o popup de conexão e o popup de entrega. Falha
quando encontra:

1. elemento de bloco com `scrollWidth > clientWidth` sem rolagem própria (`overflow` visível ou
   cortado sem reticências) ou com rolagem horizontal;
2. descendente que passa da borda da gaveta, do HUD, do banner ou dos popups;
3. bloco de altura fixa com conteúdo maior e sem rolagem vertical;
4. aba puxadora sobre outra gaveta aberta (V04);
5. Conversa cortada em janela de 600 px ou mais, ou a página com rolagem do documento.

Reticências e `line-clamp` são truncamentos de projeto e passam. Também junta **avisos** (não
falham): células cobertas por gavetas e HUD sob as gavetas. Em 26/10/2026 o script fez 237
verificações e achou um defeito do produto: o popup de entrega em 1280×720 (e em qualquer janela
de 1280 px com as gavetas laterais abertas) tinha a tabela com 402 px dentro de 376 px úteis, e
a coluna Arquivo ficava com 0 px. Foi corrigido no mesmo ciclo (colunas laterais encolhem no
modo real, `frontend.md` seção 8) e o script passa. Os avisos que restam: HUD sob as gavetas em
1280×720 e as duas células de baixo cobertas pela Conversa em 1396×612, como na demonstração. Com CSS injetado que alarga uma linha da lista, o
nome da missão e a Conversa, o script falha apontando cada elemento (conferido em 26/10/2026).

### Estado dos scripts

- `hivemind_visual_compare.mjs` e `hivemind_overflow.mjs` foram executados em 26/10/2026 com o
  `NODE_PATH` acima: os dois passam.
- `hivemind_browser_qa.mjs` passa de novo (26/10/2026, ~30 s, duas execuções seguidas): foi
  adaptado ao modo real como padrão (clica em `.hm-mode` antes dos passos da demonstração,
  `/hive-api` falso mínimo, seletores dentro de `.hm-demo-workspace`) e a conferência do
  progresso da célula aceita um passo de atraso em relação ao relógio (a tela desenha no
  último tick). Ele continua testando só a demonstração e o isolamento da aba Hive.
- Para uma comparação limpa, use fontes carregadas, DPR 1 e animações congeladas, como na
  aprovação do ciclo 7 (`docs/planos/2026-10-10_hivemind-frontend-hub/verificacao.md`).

## 4. Validação real com IA

Consome franquia dos provedores. **Só rodar com autorização explícita do usuário**,
uma execução por pedido, e repetir apenas depois de uma falha seguida de mudança de
código ou do harness.

O harness do ciclo C4 está em `.test-tmp/hivemind-c4-r15/` (somente leitura aqui; não
executar sem autorização):

| Item | O que é |
|---|---|
| `smoke.py <provedor> <modelo> <esforço>` | Um turno real ("Responda apenas: OK") por CLI, usando a geração de runtime, o adaptador e a sessão-prova reais; avalia o gate antes e depois da sessão. Grava `smoke-<provedor>/terminal.json`; se esse arquivo existir, não repete ("duplicate fixture; no turn"). |
| `mission.py`, `mission2.py`, `mission3.py` | Tentativas anteriores de missão mínima (terminaram em `failed`: `job_failed`, `planning_result_invalid`, `job_failed`). |
| `mission4.py` | Missão mínima ponta a ponta com equipe mista: edita só `note.txt` (`greeting=hello` para `greeting=hello hive`) e termina com origem e workspace conferidos. Envolve `turn()` com checagem extra de gate e teto de 8 turnos; só registra códigos de falha de uma lista fechada; recusa rodar de novo se houver `terminal.json`. Registra `audit.jsonl` e `terminal.json`. |
| `planning_diag.py`, `planning_diag2.py` | Diagnóstico do planejamento (saída do modelo e falhas locais no terminal), fora do produto, sem contornar o gate. |

O que foi validado em 20/10/2026 (verificação independente do C4, aprovada, R15):

- **Smoke Claude:** 2.1.305, `sonnet/low`, gate `[]`, resposta `OK` em 18,2 s.
- **Smoke Codex:** 0.160.0, `gpt-5.6-luna/low`, gate `[]`, resposta `OK` em 9,2 s.
- **`mission4`:** missão `completed` no ciclo 1/1, com Rainha Codex
  (`gpt-5.6-luna/medium`), operária Claude (`sonnet/low`) e verificador Codex, três
  jobs com sessão e processo próprios, entrega preparada, aprovada, aplicada e origem
  alterada. A aprovação do plano e do pacote foi feita pelo harness, pela API real, com
  hash; o caminho humano pela interface não foi exercitado nesse ensaio.
- Caminho de cobrança comum nos dois provedores (Codex sem créditos extras, Claude com
  `extra_usage` desligado). O Codex ficou fixado em `0.160.0`.

Registro completo: `docs/planos/2026-10-19_hivemind-backend/verificacao-c4.md` (seção 4).
Limitações do ensaio e riscos residuais estão no mesmo arquivo.

## 5. Regras para agentes

- Subagentes e verificadores **não rodam turnos reais de IA, não chamam os CLIs
  `claude`/`codex` para turno e não tocam a porta 8765** sem autorização do usuário.
  Comandos reais permitidos sem pedido: `--version`, `--help` e a descoberta
  (`discover()`) dos adaptadores, que não enviam prompt. O QA de navegador usa
  endpoints simulados e servidor próprio.
- Não ler tokens, credenciais nem históricos pessoais. Usar `.test-tmp/` para
  temporários e harnesses; é descartável e não entra na documentação.
- Sem Git neste checkout: cada ciclo congela um **manifesto sha256** do candidato e o
  verificador confere o início e o fim.
- Verificador é independente (contexto limpo, sem participar da implementação) e não
  edita código, testes nem manifesto.
- Testes de cancelamento e timeout usam processos descartáveis reais; se o sandbox
  impedir encerrar a árvore deles, rodar no ambiente do usuário
  (`docs/operacao.md`).

### Manifesto sha256 por ciclo

Exemplo: `docs/planos/2026-10-19_hivemind-backend/manifesto-c4.sha256` (também
`manifesto-c1`, `c2`, `c3`).

- Formato compatível com `sha256sum`: linhas de comentário iniciadas por `#` (título,
  data, estado integrado, quem implementou) e, depois, uma linha por arquivo: o hash
  SHA-256 em minúsculas, **dois espaços** e o caminho **relativo à raiz do projeto**, com
  barras `/`.
- Cobre o candidato do ciclo: `HiveMind/` (backend, adaptadores, front-end estático,
  três arquivos do protótipo), `server.py`, o lançador compartilhado em `hub_runtime/`,
  os testes (`tests/test_hivemind_*.py`, `hivemind_*.mjs`) e os documentos do plano.
  O `tests/fixtures/hivemind/fake_cli.py` ficou **fora** de todos os manifestos (P3-d do
  C4).
- Conferência (a partir da raiz): `grep -v '^#' <manifesto> | sha256sum -c -`. Arquivos
  alterados depois do congelamento aparecem como `FAILED`; em 21/10/2026 isso acontece
  com documentos do plano que mudaram ou foram movidos (o manifesto é histórico, não
  vale como estado atual).
- Os resultados das conferências ficam em `.test-tmp/<pasta-do-verificador>/`
  (por exemplo `integrity-final.txt` no C4, "64/64 OK" no início e no fim).
- Cada manifesto é novo a cada ciclo; o verificador compara com o do ciclo anterior para
  confirmar que o escopo alterado é o declarado.
