# Hive Mind — backend
Atualizado em 26/10/2026 · descreve o código atual; o que é planejado fica em `roadmap.md`.

Fonte: `HiveMind/backend/*.py` (a parte de Claude e Codex está em `adaptadores.md`).
Este arquivo substitui o conteúdo do antigo `HiveMind/backend/README.md` e da seção
"HiveMind opt-in" de `docs/runtime.md`, que viraram ponteiros para cá.

## Visão geral

O backend mantém missões, comandos idempotentes, aprovações por hash e eventos
duráveis em um SQLite próprio (`HiveMind/state/hive.sqlite3`). A rota Flask
(`/hive-api`) é uma API local de controle: a tela lê o estado e executa comandos
usando lease, revisão e chave de idempotência. O backend não inicia provedor
nenhum sozinho; cada sessão de IA nasce de um comando explícito da tela (`ask`,
`start`, `resume`) e depois o scheduler despacha somente trabalho já aprovado.

Fluxo de uma missão, do pedido à aplicação na origem:

1. `POST /missions` cria a missão em `draft`.
2. A tela obtém o lease (`/lease`) e envia `ask`. A Rainha, numa sessão
   somente leitura sobre a **origem**, devolve uma pergunta (`clarifying`) ou um
   plano (`awaiting_plan_approval`). Um plano também pode entrar manualmente por
   `propose`.
3. `approve_plan` com o `plan_hash` exato leva a missão a `ready`.
4. `start` copia a origem para um workspace isolado (snapshot ou worktree Git
   sem checkout) e leva a missão a `running`.
5. O scheduler despacha as operárias tarefa a tarefa, cada uma numa sessão
   própria que só enxerga o broker (`read`, `patch`, `checks`) do workspace.
6. Quando todas as tarefas do ciclo terminam, a missão vai a `verifying` e um
   verificador independente, em outra sessão, devolve o veredito por critério.
7. Veredito aprovado: o backend monta o pacote de entrega (`awaiting_delivery_approval`).
   Reprovado: nova rodada (`correcting`, ciclo + 1) até `cycle_limit`, depois
   `awaiting_user`.
8. `approve_delivery` (com `candidate_hash` e `delivery_hash`) e `apply` aplicam o
   pacote na origem com journal, backup e rollback; a missão termina em `completed`.

Tudo acima só roda no Windows: a identidade do processo da sessão
(`HiveService._session_started`) e a entrega (`Delivery`) usam a API do Windows;
fora dele devolvem `process_identity_unverified` e `delivery_platform_unsupported`.

## Mapa de arquivos

| Módulo | Responsabilidade |
|---|---|
| `store.py` | SQLite (missões, eventos, comandos, abelhas, jobs, leases, configurações), `Store.mutate`, idempotência, `recover_interrupted`, validação do limite e do cadastro, `bee_events` (eventos de ferramenta e progresso sem o limite de paginação) |
| `bees.py` | Cadastro de abelha: regras de `description`, `skills` e `tools` (`profile_gaps`, `require_profile`, `InvalidProfile`), abelhas incompletas, `same_bee`, ferramentas do job (`job_tools`), linha de perfil do prompt (`prompt_profile`) e validação de `progress` (`validate_progress`) |
| `summary.py` | `bees_summary`: resumo por abelha de uma missão, calculado do plano, dos jobs e dos eventos |
| `missions.py` | Transições da missão, `validate_plan`, aprovações por hash, ciclos, reconciliação (lado do estado) |
| `service.py` | `HiveService`: planejamento pela Rainha, `run_job`, despacho (`advance`), presença, watchdog, `start_mission`, `reconcile_source`, `resume`, códigos estáveis de falha |
| `scheduler.py` | Reserva transacional de jobs (limite, abelha ocupada, arquivos, dependências) e encerramento de jobs |
| `lifecycle.py` | Lease de controle, registro de sessões, pausa com drenagem, retomada |
| `capabilities.py` | `evaluate` (gate), evidência de enforcement, `ToolAdmission` e `ToolBroker` (conjunto de ferramentas do job) |
| `tools.py` | `WorkspaceTools` (`read`, `patch`, `checks`) e `RestrictedCheckRunner`; `progress` fica em `service.py` |
| `workspaces.py` | Exclusões, validação de caminhos, `manifest`, `snapshot`, geração de runtime |
| `delivery.py` | Pacote de entrega, aplicação journalada, rollback, recuperação |
| `routes.py` | Blueprint `/hive-api`, proteção de origem local, mapeamento de erros |
| `manager.py` | Dono único e preguiçoso do serviço; `hub_exit_ready` |
| `adapters/base.py` | `Discovery`, `Model`, `DiscoveryRpc`, `safe_name`, `run_status`, `discovery_environment` |
| `adapters/codex.py` | Adaptador e sessão do Codex (app-server JSON-RPC) |
| `adapters/claude.py` | Adaptador e sessão do Claude (stream-json) |
| `adapters/launcher.py` | Lançador `--hivemind` e construção dos adaptadores |

Importar o pacote (`HiveMind/backend/__init__.py`) não inicia serviço nem processo.

Testes: `tests/test_hivemind_{adapters,adapter_turns,api,bees,delivery,frontend,lifecycle,missions,scheduler,service,workspaces}.py`
(229 testes do Hive, 213 fora de `test_hivemind_frontend.py`, em 26/10/2026 com `./.venv/Scripts/python.exe -m pytest tests -q -k hivemind`; no PowerShell o glob `test_hivemind_*.py` não é expandido).

## Encaixes no Hub

| Onde | O que o Hub tem |
|---|---|
| `server.py`, import | `from HiveMind.backend.routes import blueprint as hivemind_backend_blueprint` (par do blueprint do frontend, `from HiveMind import blueprint`) |
| `server.py`, registro | `app.register_blueprint(hivemind_backend_blueprint)` |
| `server.py:_hud_watchdog` | Depois de não restar HUD do Hub vivo, chama `HiveMind.backend.manager.hub_exit_ready()`; só encerra a ponte se ele devolver verdadeiro |
| `index.html` | Só a tag `<script type="module" src="/hive-ui/static/app.js">` (frontend da colmeia) |
| `hub_runtime/assistant.py:main` | `--hivemind <codex\|claude> ...` delega a `HiveMind.backend.adapters.launcher.main`; quando roda como script de uma geração de runtime, carrega o launcher como `_hivemind_launcher` a partir de `<geração>/HiveMind/backend`; não passa pelo perfil do assistente pessoal |

Regras que valem para esses encaixes (CLAUDE.md, regras 7, 10 e 11):

- `server.py` e `index.html` só ganham import, `register_blueprint` e tag de script
  para o Hive; nenhuma lógica nova entra neles.
- A ponte fica em `127.0.0.1`. A API do Hive é local e recusa qualquer outra origem
  (seção seguinte). O `mobile/` não expõe `/hive-api` (whitelist de 5 rotas do Hub).
- `hub_runtime.assistant --hivemind` é um lançador separado, só para as sessões
  efêmeras do Hive. Preserva a autenticação nativa do fornecedor mas remove
  chaves de API e variáveis do vault do ambiente (`discovery_environment`); não
  inclui vault, instruções pessoais, memória, plugins, MCP nem ferramentas nativas.
  Não usar para o assistente cotidiano, nem usar `--safe-mode` como substituto
  geral de runtime: o modo Hive é validado pelo adaptador e por seus controles.

## Geração de runtime

`manager.get_service()` cria o serviço na primeira chamada de rota e o mantém em
memória. Ele não roda o código direto da árvore do projeto:
`workspaces.load_runtime_generation` copia `HiveMind/backend` (arquivos `.py`,
`.md` e `.json`) mais `HiveMind/__init__.py`, `hub_runtime/__init__.py`,
`hub_runtime/assistant.py` e `hub_runtime/paths.py` para
`HiveMind/state/runtime/<hash>/`, onde `<hash>` é o `digest` do manifesto, e importa
o serviço desse pacote privado (`_hivemind_runtime_<hash>`).

- Alterar qualquer um desses arquivos (inclusive `.md`) cria outra geração, mas só
  vale depois de reiniciar o Hub (o serviço fica em cache).
- Antes de `ask`, `start`, `resume`, de cada job e de cada chamada de ferramenta o
  serviço revalida a geração (`validate_runtime_generation`); qualquer divergência
  vira `runtime_generation_changed`.
- O comando de sessão dos provedores aponta para o `assistant.py` da geração
  (`sys.executable -B <geração>/hub_runtime/assistant.py --hivemind <provedor>`).
- Nenhuma rotina remove gerações antigas.
- Consequência: as classes de exceção do serviço não são as importadas por
  `routes.py`; por isso `routes.error_response` compara `type(error).__name__`.

## API `/hive-api`

Implementada em `routes.py`. Prefixo `/hive-api`; respostas JSON.

### Proteção de origem local

`routes.local_origin` roda em `before_request` e recusa com `403 {"error": "local_origin_required"}`:

- host da requisição diferente de `127.0.0.1` ou `localhost`, ou cliente
  (`remote_addr`) diferente de `127.0.0.1` ou `::1`;
- `Sec-Fetch-Site` presente e diferente de `same-origin` ou `none`;
- em métodos diferentes de GET: `Origin` ausente ou diferente de `host_url`, ou corpo
  que não é JSON.

Em métodos diferentes de GET, `Content-Length` acima de 1 MiB devolve
`413 {"error": "request_too_large"}`. Corpo que não é um objeto JSON vira
`ValueError` (400).

### Rotas

| Método e rota | Payload | Resposta |
|---|---|---|
| `GET /status` | — | `{settings: {worker_limit, revision}, roster: {bees, revision, incomplete}, providers: [nomes]}`. `roster.incomplete` lista as abelhas salvas sem o cadastro completo: `[{id, missing: ["description"\|"skills"\|"tools", ...]}]` (vazia quando tudo está completo). `providers` lista só os adaptadores que o launcher conseguiu montar (CLI instalada em `%APPDATA%\npm`) |
| `GET /catalog` | — | `{provedor: Discovery}` por adaptador (`asdict`). Executa `discover()` na hora (sobe processos dos CLIs, sem inferência) |
| `POST /settings` | `{kind:"worker_limit", value, key, revision}` ou `{kind:"roster", bees, key, revision}` | `{worker_limit, revision}` ou `{bees, revision, incomplete}` (revisão nova; `bees` já normalizadas). Outro `kind` dá 400; abelha inválida dá 400 com `bee` e `field` (ver "Cadastro de abelhas") |
| `POST /presence` | `{hud, present: true\|false}` | `{ok: true}`; `hud` precisa passar em `safe_name`; outro valor de `present` dá 400 |
| `GET /missions` | — | até 100 missões, mais recentemente atualizadas primeiro |
| `POST /missions` | `{key, title, id?, cycle_limit?}` | registro da missão. `id` opcional (alfanumérico, até 64; senão `uuid4().hex`); `cycle_limit` padrão 3, inteiro de 1 a 20 |
| `GET /missions/<id>` | `?after=<seq>` (decimal, padrão 0) | `{mission, events, roster, jobs, bees_summary}`; no máximo 200 eventos por chamada, em ordem de `seq`; `roster` são as abelhas da missão; `jobs` em ordem de criação; `bees_summary` é o resumo por abelha (ver abaixo) |
| `POST /missions/<id>/lease` | `{owner}` | `{expires_at}`; renova o lease do mesmo dono |
| `POST /missions/<id>/command` | `{action, key, revision, owner, ...}` | resultado da ação (em geral o registro da missão com `revision` nova) |

O registro da missão tem `id`, `state`, `revision`, `cycle`, `cycle_limit`, `data`
(JSON da missão), `created_at`, `updated_at`. Chaves ausentes no corpo viram
`KeyError` (400).

### Resumo por abelha (`bees_summary`)

`GET /missions/<id>` devolve `bees_summary`, calculado no backend (`summary.py`) a partir
do plano, dos jobs e **de todos os eventos** `tool_completed` e `bee_progress` da missão
(`Store.bee_events`, sem o limite de 200 por chamada nem o de 500 do `events`). Há uma
entrada por abelha ativa, na ordem do plano; missão sem plano usa a equipe do
planejamento (`data.planning.team`, cadastro antigo incluído); sem nenhum dos dois, a
lista é vazia. Missão antiga nunca quebra a rota: campos que o cadastro antigo não tem
saem com valores padrão.

```json
{"id":"worker1","role":"worker","temporary":false,"active":true,
 "description":"...","skills":{"tags":["python"],"instructions":"..."},"tools":["read","patch","checks"],
 "provider":"codex","model":"...","effort":"...",
 "tasks":{"total":3,"done":1,"current":"t2","items":[{"id":"t1","description":"...","status":"done","depends_on":[],"files":["a.py"]}]},
 "progress":{"done":3,"total":23,"note":"...","seq":812},
 "tools_used":{"read":4,"patch":2,"checks":1,"progress":5},
 "job":{"state":"running","cycle":1,"started":true}}
```

| Campo | Regra |
|---|---|
| `description`, `skills`, `tools` | do cadastro; abelha salva antes do cadastro rico sai com `""`, `{"tags": [], "instructions": ""}` e as ferramentas que o job dela teria (`read`/`checks` para Rainha e verificador, as três para operárias). `tools` nunca traz `progress` |
| `temporary`, `active` | `active` é sempre `true`: só entram as abelhas do plano (ou do planejamento) em vigor |
| `tasks.items[].status` | `done`: job `succeeded` da tarefa no **ciclo atual** e na geração atual do plano; `running`: job ativo; `failed`: último job da tarefa neste ciclo falhou (`failed` ou `unknown`); `waiting`: alguma dependência ainda não está `done`; `pending`: o resto. Job pausado não conta como feito nem como falha |
| `tasks.total` / `done` / `current` | contagens das tarefas da abelha; `current` é a tarefa `running`, senão a primeira ainda não `done`, senão `null`. Rainha e verificador têm `total` 0 |
| `progress` | último evento `bee_progress` do **último job** da abelha (`seq` é o do evento); `null` se esse job ainda não informou progresso ou a abelha não tem job |
| `tools_used` | contagem de `tool_completed` com `success: true` por ferramenta (`read`, `patch`, `checks`) e de `bee_progress` (`progress`), em toda a missão; sempre as quatro chaves |
| `job` | último job da abelha na geração atual do plano (o job de planejamento da Rainha conta): `state` em `running` (`running`, `tool_active`, `draining`), `completed` (`succeeded`), `failed` (`failed`, `unknown`) ou `null` (sem job ou `paused`); `cycle` é o do job; `started` diz se há algum job (`{"state": null, "cycle": null, "started": false}` sem job) |

### Comandos de `POST /missions/<id>/command`

Todo comando exige `owner` com lease válido (`lease_required` se não houver) e roda
serializado dentro de `Lifecycle.controlled`.

| `action` | Parâmetros extras | Função chamada |
|---|---|---|
| `ask` | `source`, `queen`, `message` | `HiveService.ask_queen` |
| `propose` | `plan` | `Missions.propose` |
| `approve_plan` | `plan_hash` | `Missions.approve_plan` |
| `start` | — | `HiveService.start_mission` |
| `pause` | — | `Lifecycle.request_pause(..., "user")` e em seguida `Lifecycle.progress` |
| `resume` | — | `HiveService.resume` |
| `cycle_limit` | `limit` | `Missions.set_cycle_limit` |
| `approve_delivery` | `candidate_hash`, `delivery_hash` | `Missions.approve_delivery` |
| `apply` | `delivery_hash` | `Delivery.apply` |
| `recover_delivery` | — | `Delivery.recover` |
| `reconcile_source` | — | `HiveService.reconcile_source` |
| `abandon` | — | `Missions.abandon` (recebe `Delivery.journal_root`) |

Outra `action` dá 400 (`invalid_request`) depois da checagem do lease.
`/settings`, `/presence`, `POST /missions` e `/lease` não exigem lease.

### Lease, revisão, chave e idempotência

- **Lease** (`Lifecycle.acquire_control`): um dono por missão, TTL padrão de 30 s
  (aceita 1 a 120 s internamente; a rota usa o padrão). Outro dono só assume depois de
  expirar (`lease_held`). `owner` passa por `safe_name`.
- **Revisão**: toda mutação de missão exige `revision` igual à atual
  (`stale_revision`) e a incrementa em 1.
- **Chave**: string de 1 a 128 caracteres. `Store.mutate` grava em `commands`
  `(mission_id, key) -> fingerprint, result`. O fingerprint é o `digest` de
  `[kind, revision, request]`. Mesma chave com o mesmo fingerprint devolve o resultado
  salvo sem mutar nem gerar evento; mesma chave com outro fingerprint (inclusive outra
  revisão) dá `idempotency_key_reused`.
- Configurações (`worker_limit`, roster) usam as mesmas regras, com os pseudo-ids
  `__settings__` e `__roster__` na tabela `commands` e a revisão da própria
  configuração.
- Comandos internos usam chaves derivadas (`bind:`, `start:`, `verify:`, `verdict:`,
  `prepare:`, `pause-complete:` etc.), que dividem o mesmo espaço de chaves da missão.
- `HiveService.reconcile_source` consulta `Store.command_result` antes de tudo: repetir
  a mesma chave devolve o resultado salvo.

### Erros HTTP

`routes.error_response` converte a exceção pelo **nome da classe**:

| HTTP | Corpo | Quando |
|---|---|---|
| 400 | `{"error": "invalid_request"}` | `ValueError`, `KeyError`, `TypeError` (corpo, chave, revisão ou campo inválido) |
| 403 | `{"error": "local_origin_required"}` | proteção de origem |
| 404 | `{"error": "not_found"}` | `NotFound` (missão inexistente) |
| 409 | `{"error": "<código>"}` | `Conflict`, `InvalidTransition`, `WorkspaceError`; o código é o texto da exceção se tiver até 100 caracteres de letras, dígitos, `_`, `:`, `.`, `-`; senão `conflict` |
| 413 | `{"error": "request_too_large"}` | corpo acima de 1 MiB |
| 500 | `{"error": "internal_error"}` | qualquer outra exceção |

Algumas exceções carregam `detail` (dicionário) que vira campos extras do corpo:
`roster_incomplete` (409) traz `bee` e `missing`; abelha inválida em `POST /settings` ou em
`propose` (400, `invalid_request`) traz `bee` e `field`.

Os códigos de 409 estão em "Códigos de erro e conflito".

## Configurações

### `worker_limit`

- Valor padrão no código: **2** (`INSERT OR IGNORE INTO settings VALUES(1,2,0)` em
  `Store`).
- `Store.set_worker_limit` aceita inteiro de **1 a 20**; fora disso, `ValueError` (400).
- Conta jobs de operária, subagente e verificador de **todas as missões juntas**
  (qualquer papel diferente de `queen` em estado `running`, `tool_active` ou
  `draining`). A Rainha (planejamento e coordenação de correção) não conta.
- O limite é lido em `Scheduler.reserve` (barreira transacional,
  `worker_slots_full`) e em `HiveService.advance` (para não disparar jobs além das
  vagas).

### Cadastro de abelhas (`kind: "roster"`, campo `bees`)

`Store.set_configured_bees` grava a equipe permanente em `roster_settings`.
`GET /status` devolve `roster: {bees, revision, incomplete}`. Cada abelha aceita:

| Campo | Regra |
|---|---|
| `id` | `safe_name`: `[A-Za-z0-9_.-]`, 1 a 100 caracteres; único na lista |
| `role` | `queen`, `worker`, `subagent` ou `verifier` |
| `provider` | `codex` ou `claude` |
| `model` | `safe_name` |
| `effort` | `safe_name` |
| `temporary` | exatamente `false` |
| `description` | texto não vazio de até 2000 caracteres (obrigatória) |
| `skills` | objeto `{tags, instructions?}`: `tags` é lista de até 20 textos não vazios de até 60 caracteres (pode ser vazia); `instructions` é texto opcional de até 4000 caracteres (a gravação o preenche com `""`). Nenhuma outra chave |
| `tools` | lista sem repetição, subconjunto de `read`, `patch`, `checks`. **Rainha e verificador nunca recebem `patch`** (só `read` e `checks`): na Rainha o motivo é que o planejamento é só leitura e a coordenação de correção não tem arquivos editáveis, como no verificador. `progress` não entra no cadastro: todo job de operária, subagente e verificador o recebe automaticamente |

Skills são **declarativas** (D6): tags e instruções que a Rainha usa para escolher abelhas e
que entram no prompt da própria abelha. Não habilitam skills, MCP nem plugins dos CLIs.

A lista inteira precisa ter **exatamente uma** `queen`, **exatamente um** `verifier` e
**ao menos uma** `worker`; senão `ValueError("invalid roster")` (400). Uma lista vazia
também é recusada, então o cadastro não volta a `[]` pela API. O backend não confere
modelo e esforço contra o catálogo ao gravar; isso acontece no gate, a cada turno.

**Cadastro antigo e abelha incompleta.** Cadastro salvo sem `description`, `skills` ou
`tools` carrega normalmente e aparece em `roster.incomplete` com o que falta
(`missing`, na ordem `description`, `skills`, `tools`; campo presente mas inválido também
conta como faltando). Na gravação, toda abelha **nova ou alterada** precisa vir completa:
senão `InvalidProfile` (`ValueError`, 400 `invalid_request` com `{bee, field}` do primeiro
campo inválido). Uma abelha incompleta **idêntica à já salva** pode ficar como está, para
a equipe ser completada em mais de um salvamento. Enquanto houver abelha incompleta, o
planejamento é recusado (`roster_incomplete`, abaixo).

O cadastro só vale se houver abelhas gravadas (padrão: `[]`):

- `ask_queen` exige que a `queen` enviada seja igual (dicionário idêntico) a uma abelha
  do cadastro (`queen_configuration_changed`); com cadastro vazio, a equipe permanente
  é só a Rainha enviada. Em qualquer dos dois casos, abelha incompleta na equipe dá
  `Conflict("roster_incomplete")` com `detail {bee, missing}` (corpo 409
  `{"error": "roster_incomplete", "bee": "<id>", "missing": [...]}`), antes de qualquer
  job de planejamento.
- O plano da Rainha precisa conter cada abelha permanente igual ao cadastro, e toda
  abelha não temporária do plano precisa estar no cadastro (`planning_scope_mismatch`). A
  igualdade (`bees.same_bee`) compara só os campos do cadastro e ignora a ordem de
  `tags` e `tools`; o plano guardado usa a abelha exatamente como está no cadastro.

## Máquina de estados da missão

Estados que o código atribui: `draft`, `clarifying`, `planning`,
`awaiting_plan_approval`, `ready`, `preparing`, `running`, `verifying`, `correcting`,
`awaiting_delivery_approval`, `delivery_approved`, `applying`, `completed`, `pausing`,
`paused`, `awaiting_user`, `recovery_required`, `abandoned`.

Ação fora do estado permitido lança `InvalidTransition("invalid_state:<estado>")`
(409).

| De | Evento | Para |
|---|---|---|
| `draft`, `clarifying`, `awaiting_plan_approval`, `awaiting_user` | `ask` (`request_planning`) | `planning` |
| `planning` | Rainha devolve pergunta (`queen_replied`) | `clarifying` |
| `planning` | Rainha devolve plano válido, depois `propose` automático | `awaiting_plan_approval` |
| `draft`, `clarifying`, `planning`, `awaiting_plan_approval`, `ready`, `awaiting_user` | `propose` | `awaiting_plan_approval` |
| `awaiting_plan_approval` | `approve_plan` | `ready` |
| `ready` | `start` | `preparing`, depois `running` (snapshot feito e ligado) |
| `preparing` | falha ou interrupção na preparação | `recovery_required` |
| `running`, `correcting` | todas as tarefas do ciclo concluídas (`begin_verification`) | `verifying` |
| `verifying` | veredito aprovado | `awaiting_delivery_approval` |
| `verifying` | veredito reprovado, `cycle < cycle_limit` | `correcting` (ciclo + 1) |
| `verifying` | veredito reprovado, `cycle >= cycle_limit` | `awaiting_user` |
| `awaiting_delivery_approval` | `approve_delivery` | `delivery_approved` |
| `delivery_approved` | `apply` | `applying`, depois `completed` ou `recovery_required` |
| `planning`, `running`, `verifying`, `correcting` | pausa solicitada | `pausing` |
| `pausing` | sessões drenadas e jobs encerrados | `paused`, ou `awaiting_user` se o motivo foi `job_failed` |
| `paused` | `resume` | o estado de origem da pausa (`data.pause.from`) |
| `recovery_required` | `recover_delivery` | `awaiting_user` |
| `recovery_required` | `abandon` (sem journal pendente que possa ter tocado a origem) | `abandoned` (terminal) |
| `awaiting_user` | `reconcile_source` | `verifying` (reconciliou), permanece (conflito) ou `recovery_required` (interrompida) |
| qualquer estado ativo | reinício do serviço | `recovery_required` (ver "Reinício") |

`cycle_limit` vale em qualquer estado exceto `abandoned` (`invalid_state:abandoned`):
`Missions.set_cycle_limit` aceita inteiro de 1 a 20 e recusa valor abaixo do ciclo
atual (`limit_below_current_cycle`).

Observações do código:

- `resume` só vale em `paused`. Depois de `job_failed` a missão fica em
  `awaiting_user` e o caminho de volta é `ask` ou `propose` (novo plano).
- `recovery_required` tem duas saídas: `recover_delivery`, que exige um pacote de
  entrega com journal verificável (numa missão interrompida antes de existir pacote,
  devolve `delivery_journal_unverified`), e `abandon` ("Encerrar missão").
- `abandon` só vale em `recovery_required`. Recusa com `delivery_recovery_required`
  quando há **journal pendente**: a missão tem `delivery_hash`, o evento mais recente
  entre `delivery_applying` e `delivery_recovered` é `delivery_applying` (houve
  aplicação sem recuperação depois) **e** existe
  `deliveries/delivery-<digest(missão, delivery_hash)>/journal.json` que não é legível
  (JSON inválido, `items` ausente ou mal formado, ou arquivo acima de 10 MiB, o mesmo
  limite de `Delivery.recover`) ou tem algum item com `attempted` diferente de `false`. Use
  `recover_delivery` antes. Diretório sem `journal.json` (falha entre o `mkdir` e a
  primeira gravação do journal) ou journal legível com todos os `attempted: false`
  significa que a origem nunca foi tocada (`Delivery.apply` grava `attempted: true`
  de forma atômica antes de cada mudança na origem): `abandon` é aceito. Se o evento
  mais recente é `delivery_recovered`, ou nunca houve `delivery_applying`, o journal é
  antigo e `abandon` também é aceito. A consulta roda na mesma transação do
  `Store.mutate`.
  Grava `data.abandoned = {previous_state, at}` e o evento `mission_abandoned`; não toca
  em origem, workspace, journal nem jobs (o histórico, inclusive jobs `unknown`, fica).
- `completed` e `abandoned` são terminais: todo comando em missão `abandoned` é
  recusado (409), e ela não conta como ativa para `hub_exit_ready`, `recover_interrupted`
  nem para o despacho. `cycle_limit` também recusa (`invalid_state:abandoned`).

### Ciclos e `cycle_limit`

- A missão nasce com `cycle = 1` e `cycle_limit` padrão 3 (1 a 20).
- Veredito reprovado com ciclo abaixo do teto: `cycle + 1`, estado `correcting` e
  `data.correction = {status: "pending", ...}`. A Rainha coordena a correção (job
  `queen`, sem esquema de saída); o texto dela vira `correction.feedback` e o
  estado de `correction` passa a `coordinated`. Só então as operárias reexecutam
  **todas** as tarefas no novo ciclo (a conclusão é contada por ciclo) e o
  verificador volta a rodar.
- Veredito reprovado no teto: `awaiting_user` com
  `data.attempt_outcome = {status: "cycle_limit", ...}`.
- **Reautorização consome ciclo.** `propose` (plano igual ou novo) depois de um
  `attempt_outcome` grava `data.pending_reauthorization`. Enquanto
  `cycle >= cycle_limit`, `approve_plan` e `start_mission` devolvem
  `cycle_limit_reached`, antes de qualquer snapshot; é preciso elevar o teto antes.
  `Missions.start` move o resultado para `attempt_history` e faz `cycle + 1`.

### `plan_hash` e `plan_attempt`

- `plan_hash` é o `digest` do plano (SHA-256 do JSON canônico: chaves ordenadas, sem
  espaços). `approve_plan` exige o hash exato (`stale_plan`).
- `plan_attempt` sobe 1 a cada `propose`, mesmo com plano idêntico. Aprovação,
  workspace, jobs, veredito e correção carregam `(plan_hash, plan_attempt)`; qualquer
  divergência impede o uso (`plan_not_approved`, `workspace_required`,
  `workspace_generation_mismatch`, `stale_candidate`).
- Um novo `propose` zera aprovação, candidato, veredito, entrega e correção,
  arquiva o workspace anterior em `data.workspace_history` (sem apagá-lo do disco) e
  marca todas as abelhas da missão como inativas até a próxima aprovação.
- `propose` recusa com `recovery_required` se existir job em estado `unknown`.

## Planejamento pela Rainha

`HiveService.ask_queen` valida a presença, a geração de runtime e a equipe, grava a
solicitação (`Missions.request_planning`) e dispara a thread `hivemind-queen`
(`_plan_job`). Pré-condições e validações:

- `queen` precisa ser um objeto com `role: "queen"`, `id`, `provider`, `model`,
  `effort` e `temporary` booleano válidos; `message` é texto não vazio de até 50000
  caracteres; `source` passa por `project_root` (recusa o vault configurado, suas
  subpastas e seus ancestrais: `vault_project_forbidden`; sem `HUB_VAULT`, o vault é
  `~/Documents/Obsidian Vault`).
- Dentro da mesma missão, a origem não muda (`project_mismatch`).
- Provedor ausente em `adapters`: `provider_unavailable`. Sem tela do Hive viva:
  `presence_uncertain`. Equipe com abelha incompleta: `roster_incomplete`.
- A chave deduplica: o `job_id` é `planning-<digest(missão, chave)>`; repetir devolve a
  missão sem outra sessão.

A sessão da Rainha anuncia somente `read`, quando autorizado no cadastro: lê a **origem**
(um `WorkspaceTools` sem arquivos editáveis, revalidando a geração a cada leitura).
`patch`, `checks` e `progress` são recusados com `tool_not_allowed`. Cadastros legados
usam o padrão do papel; sem `read`, o job falha antes da sessão com `planning_read_required`.
Mais de 5000 arquivos no manifesto da
origem: `project_too_large_to_plan`. O prompt inclui origem, lista de arquivos, equipe
(cada abelha com descrição, skills e ferramentas) e mensagens (`canonical(...)`); o
adaptador recusa prompt acima de 100000 caracteres com `ValueError`, que vira
`job_failed`. O texto do prompt manda **preferir as abelhas permanentes cuja descrição,
skills e ferramentas servem à tarefa** e criar uma temporária só quando nenhuma serve,
**preenchendo todos os campos** (`description`, `skills.tags`, `skills.instructions`,
`tools`, sem `patch` para Rainha e verificador).

Saída estruturada (`service.py:_QUEEN_OUTPUT`): objeto fechado com `clarification`
(texto ou nulo) e `plan` (nulo ou o plano). Tudo é `required` e
`additionalProperties: false`; o plano tem `objective`, `project{path}`, `bees[]`
(`id`, `role`, `provider`, `model`, `effort`, `temporary`, `description`,
`skills{tags, instructions}`, `tools`), `tasks[]` (`id`,
`description`, `bee_id`, `files`, `depends_on`), `acceptance[]` (`id`, `description`) e
`checks` (lista de listas de texto). O Codex recebe o esquema em `outputSchema`; o
Claude, dentro do envelope `final` (ver `adaptadores.md`).

Tratamento da resposta em `_plan_job`:

1. Texto que não é JSON, ou que não vira objeto: `planning_result_invalid`.
2. Chaves com valor nulo são descartadas; o conjunto restante precisa ser exatamente
   `{clarification}` ou `{plan}`; os dois ou nenhum: `planning_result_invalid`.
3. `clarification`: texto não vazio de até 50000 caracteres; a missão vai a
   `clarifying`.
4. `plan`: `validate_plan` (`ValueError` vira `planning_result_invalid`); o caminho do
   projeto precisa resolver para a origem e a equipe precisa casar com o cadastro
   (`planning_scope_mismatch`, comparação por `same_bee`); as abelhas permanentes são
   trocadas pela versão do cadastro; depois `Missions.propose` registra o plano.
5. O evento `queen_replied` registra `kind: "clarification" | "plan"`; o texto da
   resposta fica em `data.planning.messages`, não no evento.

### `validate_plan` (`missions.py`)

Devolve o `plan_hash` ou lança `ValueError`. As regras são:

| Regra | Mensagem de erro |
|---|---|
| `plan` é objeto com `project` objeto | `invalid plan project` |
| `objective` é texto não vazio | `plan objective required` |
| `project.path` é texto não vazio | `project path required` |
| `bees` e `tasks` são listas não vazias | `plan needs bees and tasks` |
| cada abelha tem `id` com `safe_name`, único | `invalid bee` |
| `role` em quatro valores, `provider` em `codex`/`claude`, `model` e `effort` com `safe_name`, `temporary` booleano | `invalid bee configuration` |
| `description`, `skills` e `tools` válidos em **toda** abelha do plano, temporárias incluídas (mesmas regras do cadastro; verificador e Rainha sem `patch`) | `InvalidProfile` (`ValueError`, com `detail {bee, field}`) |
| exatamente uma `queen` e exatamente um `verifier` | `exactly one queen and independent verifier required` |
| cada tarefa: `id` com `safe_name` único | `invalid task` |
| `description` não vazia | `task description required` |
| `bee_id` de uma abelha `worker` ou `subagent` | `task must use a worker` |
| `files`: lista não vazia de caminhos relativos válidos (`path_key`) | `invalid task files` |
| sem caminhos repetidos na tarefa (comparação sem diferenciar maiúsculas) | `duplicate task files` |
| `depends_on`: lista de ids com `safe_name` | `invalid dependencies` |
| dependência existente / sem ciclo | `unknown dependency` / `dependency cycle` |
| tarefas que compartilham arquivo precisam ter relação de dependência (direta ou transitiva) | `overlapping tasks require dependency` |
| `acceptance`: lista não vazia de `{id, description}` com id válido e descrição não vazia | `invalid acceptance criteria` |
| ids de critério únicos | `duplicate acceptance criterion` |
| `checks` (opcional): lista de listas não vazias de textos não vazios | `invalid checks` |

O backend não limita o número de abelhas ou tarefas do plano.
Caminhos de arquivo seguem `workspaces.relative_path`: sem absoluto, sem `..`, sem
nomes de dispositivo do Windows, sem caracteres de controle ou `<>:"|?*`, sem ponto ou
espaço no fim, e fora da lista de exclusões (`.git`, `.agents`, `.codex`, `.aws`,
`.venv`, `venv`, `node_modules`, `__pycache__`, `.pytest_cache`, `.test-tmp`, `vault`,
`logs`, `.env`, `.env.*`, `auth.json`, `credentials.json`, sufixos `.pyc`, `.log`,
`.pem`, `.key`, `.p12`, `.pfx` e `HiveMind/state`).

## Scheduler e despacho

`HiveService.advance` roda a cada 2 s, na thread `hivemind-presence` (é o único
chamador). Só age se houver adaptadores e ao menos uma tela do Hive com
heartbeat válido (`_can_dispatch`); sem tela, nada novo é iniciado.

Por missão em `running`, `correcting`, `verifying` ou `awaiting_delivery_approval`
(ordem de criação), sob `_drive_lock`:

- **Vagas** = `worker_limit` − jobs ativos que não são da Rainha − lançamentos
  pendentes ainda sem job gravado.
- `awaiting_delivery_approval` sem `delivery_hash`: chama `Delivery.prepare` com a
  chave `prepare:<candidate_hash>`.
- `running` e `correcting`: em `correcting`, primeiro a coordenação da Rainha
  (`correction.status` `pending`, depois `coordinated`). Uma tarefa é lançada se
  não estiver concluída no ciclo, não houver lançamento pendente, a abelha não
  estiver ocupada na missão, as dependências estiverem concluídas e restarem vagas.
  Quando todas as tarefas do ciclo estão concluídas e não há job ativo ou pendente
  da missão, calcula o `candidate_hash` (`digest(manifest(workspace))`) e chama
  `Missions.begin_verification`.
- `verifying`: lança o verificador se houver vaga e ele não estiver ocupado.

`_launch` cria o job numa thread `hivemind-job` que chama `run_job`. Conflitos
transitórios (`worker_slots_full`, `bee_busy`, `files_busy`, `dependencies_incomplete`,
`dispatch_not_allowed`) são ignorados e o próximo ciclo tenta de novo; qualquer outra
falha chama `_fail_job`.

`Scheduler.reserve` (uma transação `BEGIN IMMEDIATE`) reconfere, nesta ordem: plano
aprovado e do mesmo `plan_attempt` (`plan_not_approved`), workspace existente
(`workspace_required`), abelha no plano (`unknown_bee`), estado compatível com o
papel (`dispatch_not_allowed`), correção coordenada para operárias
(`correction_not_ready`), job novo (`job_exists`), uma Rainha por missão
(`queen_busy`), limite global (`worker_slots_full`), abelha livre na missão
(`bee_busy`), e para operárias e subagentes: tarefa atribuída à abelha
(`task_not_assigned`), dependências concluídas no ciclo (`dependencies_incomplete`),
arquivos livres entre jobs ativos da missão (`files_busy`) e tarefa não tentada antes no
mesmo ciclo e plano, exceto se o job anterior foi `paused`
(`task_already_attempted`). O verificador só em `verifying`; operária, subagente e
Rainha de correção em `running` ou `correcting`.

Estados de job gravados: `running`, `succeeded`, `failed`, `paused` e `unknown`
(este só na recuperação após reinício). `tool_active` e `draining` aparecem nas
consultas, mas nenhum código os atribui hoje.

`Scheduler.reserve_planning` reserva o job da Rainha antes da aprovação, só com a
missão em `planning` (`dispatch_not_allowed`), sem outra Rainha ativa na missão
(`queen_busy`); não consome vaga do limite.

### Gate reavaliado a cada despacho

O gate é `capabilities.evaluate` (detalhes em `adaptadores.md`). Em cada `turn()` a
sessão refaz o `discover()` do CLI e executa `evaluate` com a evidência da própria
sessão; se `execution_allowed` for falso, o turno nem começa e o job falha com
`gate:<primeiro motivo>`. No Claude, o gate roda de novo a cada ida ao broker dentro
do mesmo turno (até 100). Não há fallback silencioso de modelo ou provedor.

### Execução de um job (`run_job`)

1. Revalida a geração, localiza a abelha e o provedor (`unknown_bee`). O verificador
   exige que o workspace ainda tenha o `candidate_hash` (`stale_candidate`).
2. `Scheduler.reserve`; cria o diretório de scratch
   `HiveMind/state/verification/<sha256(job_id)>`.
3. Monta `WorkspaceTools` (arquivos editáveis só os da tarefa; verificador e Rainha de
   correção ficam sem nenhum), `RestrictedCheckRunner` (só se houver adaptador
   `codex`) e o `ToolBroker` **só com as ferramentas da abelha** (`bees.job_tools`: as do
   cadastro mais `progress` para operária, subagente e verificador; a Rainha não recebe
   `progress`). Abelha de plano gravado antes do cadastro rico usa o padrão do papel
   (`read` e `checks` para Rainha e verificador, as três para operárias). Cada chamada de
   `read`, `patch` ou `checks` revalida a geração e grava o evento `tool_completed`;
   `progress` grava `bee_progress` (ver "Broker de ferramentas").
4. Cria a sessão (`CodexProofSession` ou `ClaudeProofSession`), registra no
   `Lifecycle`, grava a identidade do processo e dispara o evento
   `provider_session_started`.
5. Todo prompt leva, na primeira linha, o perfil da própria abelha (`bees.prompt_profile`:
   `id`, papel, descrição e skills com as instruções, em JSON de uma linha, declarado como
   orientação que não concede ferramenta) e, quando o job tem `progress`, a explicação de
   quando e como usá-lo. Prompt por papel: operária (tarefa, critérios, checks, veredito e correção
   anteriores), verificador (objetivo, tarefas, critérios, checks, `changed_files` e
   `files_outside_plan`; esquema de saída `_verdict_output`) ou Rainha de correção
   (plano e correção; sem esquema). `changed_files` é calculado pelo backend com a mesma
   regra do `Delivery.prepare` (manifesto-base do snapshot × manifesto do candidato) e
   `files_outside_plan` são as mudanças fora dos arquivos das tarefas; o prompt diz que as
   duas listas são evidência confiável para critérios de escopo, que o verificador não
   teria como observar só com `read`.
6. Resultado maior que 200000 caracteres: `job_result_invalid`. Para o verificador, o
   JSON precisa ter exatamente `criteria` e `evidence`; `evidence` texto não vazio;
   `criteria` com todos os ids de aceite e valores `passed`, `failed` ou
   `unverifiable`; e o workspace não pode ter mudado desde o `candidate_hash`; senão
   `verdict_invalid`.
7. Conforme o papel: coordenação da Rainha grava `record_correction_coordination` e
   depois chama `Scheduler.finish`; verificador chama `Scheduler.finish` e depois
   `record_verdict` (`Missions.record_verdict` revalida candidato, geração, verificador
   independente `independent_verifier_required` e critérios completos
   `verification_criteria_incomplete`).

`_verdict_output(acceptance)` é um objeto fechado: `criteria` (um campo por id de
aceite, enum `passed|failed|unverifiable`) e `evidence` (texto).
O sucesso de uma operária é o turno terminar; o backend não confere se ela alterou arquivos.

Falha de job (`_fail_job`): grava `job_error {job_id, reason}`, pede pausa com motivo
`job_failed` e a missão termina em `awaiting_user`. O `reason` é um código estável
(`_failure_reason`), nunca texto do provedor: gate (11 códigos), falhas de turno e dos
adaptadores, falhas de planejamento, `turn_failed:...` filtrado por `turn_error_code` ou
`job_failed` para tudo o mais.

## Broker de ferramentas

`capabilities.ToolBroker` recebe os handlers **do job**: um conjunto não vazio entre
`read`, `patch`, `checks` e `progress` (`ToolBroker.names` os lista). Despacha por
`ToolAdmission` (admissão com contagem, usada na pausa). Se o handler lançar exceção, o
provedor recebe só `{"error": "tool_failed"}`; o código do erro não chega ao modelo. O
broker não autoriza arquivos: isso é do handler.

**Ferramenta fora da lista da abelha.** Uma ferramenta real do catálogo que o job não
recebeu é recusada com `reply(False, {"error": "tool_not_allowed"})`, **sem derrubar o
job** (o modelo pode seguir com outra chamada), nos dois adaptadores e dentro da mesma
admissão da pausa; o handler não roda e nada é gravado. `dispatch` direto levanta
`ToolNotAllowed`. Nome fora do catálogo (`shell`, por exemplo) mantém a recusa antiga:
`ToolNotAllowed`, que o Codex responde com `tool_not_available` e o Claude transforma na
falha de job `tool_not_available`. O Codex só anuncia (`dynamicTools`) as ferramentas do
broker do job, e o texto do Claude lista só essas.

**`progress`** `{done, total, note}`: `done` e `total` inteiros (booleano e decimal não
valem) com `0 <= done <= total <= 100000`; `note` texto puro de até 200 caracteres, sem
caracteres de controle (opcional, padrão vazio); nenhuma outra chave. Argumento inválido
vira `tool_failed` para o modelo e **não derruba o job**. Uma chamada válida grava o evento
`bee_progress` `{job_id, bee_id, done, total, note}`, devolve `{"recorded": true}` e não
toca arquivos. Não gera `tool_completed`. Os handlers de `progress` são de `service.py`
(`run_job`), porque dependem do job e da missão.

`tools.WorkspaceTools` opera sobre o workspace isolado, com um `RLock` por raiz:

| Ferramenta | Argumentos | Regras |
|---|---|---|
| `read` | `{path}` | caminho validado e dentro da raiz, sem link; arquivo comum de até 1 MiB, UTF-8; devolve `{content, sha256}` |
| `patch` | `{path, content, expected_sha256}` | `content` texto (até 1 MiB) ou `null` para remover; o caminho precisa estar na lista de arquivos da tarefa (`write_not_approved`); pasta pai precisa existir (`missing_parent`); `expected_sha256` precisa igualar o hash atual, `null` só para arquivo novo (`stale_patch`); escrita atômica por arquivo temporário e `os.replace`; devolve `{written}` ou `{removed}` |
| `checks` | `{argv}` | `argv` precisa ser idêntico a um item de `plan.checks` (`check_not_approved`); sem runner: `restricted_runner_unavailable` |

Erros de ferramenta: `invalid_read`, `invalid_read_target`, `invalid_patch`,
`missing_path`, `invalid_check` e os de caminho de `workspaces` (`invalid_path`,
`excluded_path`, `link_or_shared_file`, `outside_root`).

### `RestrictedCheckRunner`

Roda o `argv` aprovado pelo `command/exec` do app-server do Codex, com perfil próprio
`hive-verify` (nome interno dos checks, diferente do perfil da sessão): estende
`:read-only`, nega `:root`, `:tmpdir` e `/tmp`, lê `:minimal` e a raiz do candidato e só
escreve no scratch, rede desligada, MXC e sandbox `unelevated` do Windows. Sem
fallback: falha de preparação é falha do check.

- Exige Codex `codex-cli 0.160.0` exato (`check_cli_unverified`) e launcher `node.exe`
  (`check_launcher_unverified`).
- Lê a configuração efetiva e confere o perfil inteiro antes de executar
  (`check_profile_unverified`).
- Leitura extra do programa (`tools.program_read_roots`): só para `argv[0]` que seja
  nome puro (sem `/`, `\` nem `:`), encontrado numa pasta do `PATH` do Hub (nunca na
  pasta atual; `tools.program_path`). O perfil ganha leitura da pasta do executável e,
  se houver `pyvenv.cfg` no pai e o próprio venv for concedível, do venv e da `home`
  dele (só se absoluta e com `python.exe`). Nunca concede: raiz de unidade; a pasta do
  usuário, os ancestrais e os filhos diretos dela; `AppData\Local`, `AppData\Roaming`,
  `AppData\LocalLow` e `AppData\Local\Programs`; pastas `OneDrive*` do usuário; outros
  perfis e `Public` dentro da pasta de usuários; pasta que contenha ou esteja dentro do
  candidato ou do scratch. A barreira é por posição, não por conteúdo: uma pasta mais
  funda da pasta do usuário (ex.: `Documents\Ferramentas`) é concedível se o próprio
  usuário puser um programa dela no `PATH`. Se a pasta do executável for barrada, nada
  é concedido. A conferência do perfil exige exatamente essas entradas. O check executa
  o **mesmo arquivo** resolvido (caminho absoluto no lugar do nome), e não um homônimo na
  raiz do candidato. Sem isso, Python instalado por usuário (fora de `:minimal`) nunca
  rodava (B4 do teste de 24–25/10/2026). O alias da Microsoft Store
  (`WindowsApps\python.exe`) só concede a pasta de atalhos e continua sem iniciar.
- Executa por um wrapper `node` que recria o ambiente com lista de variáveis
  permitidas, `TEMP`, `TMP` e `HOME` no scratch e `PYTEST_ADDOPTS` apontando o
  `cache_dir` do pytest para o scratch (no candidato somente leitura, o
  `tempfile.mkdtemp` do Python no Windows repetia `PermissionError` sem fim); saída
  limitada a 262144 bytes. Ressalva: projeto que desliga o `cacheprovider` e usa
  `--strict-config` recusa a opção `cache_dir` e o check falha.
- Teto de tempo: `timeoutMs` de 600 s por check (`RestrictedCheckRunner(timeout=...)`);
  a espera do RPC é o teto mais 60 s. Check que estoura volta com código 124. Como o
  check só escreve no scratch, encerrá-lo não toca o candidato.
- Resultado: `{exit_code, stdout, stderr}`; erro de protocolo vira
  `restricted_check_failed`; `exitCode` não inteiro vira `check_result_invalid`;
  scratch dentro ou contendo o candidato: `scratch_not_separate`.
- O runner é criado sempre que existe o adaptador `codex`, seja qual for a equipe. Em
  instalação sem Codex, `checks` falha com `restricted_runner_unavailable` mesmo para
  equipes só Claude.

### Workspace isolado

`workspaces.snapshot` cria o candidato em `HiveMind/state/workspaces/<id>`
(`<id>` = `digest(missão, plan_hash, plan_attempt, chave)`):

- Origem sem `.git`: cópia dos arquivos do `manifest` para uma pasta temporária
  (`.hive-snapshot-*`) e `os.replace`; `kind: "snapshot"`.
- Origem com `.git`: o topo do repositório precisa ser a própria origem
  (`git_root_required`), `HEAD` válido (`git_head_invalid`); cria
  `git worktree add --detach --no-checkout`, `read-tree` e copia os arquivos do
  manifesto (ambiente Git sem config global, hooks e prompt); `kind: "git"` com o
  `head`. Em falha, remove o worktree.
- Nos dois casos calcula a base antes da cópia e, depois dela, confere
  `manifest(origem) == manifest(candidato) == base` (`source_changed_during_snapshot`).
- `manifest` hasheia (SHA-256) cada arquivo fora das exclusões e recusa links
  simbólicos, pontos de reparse, arquivos com mais de um hard link e aliases de
  caminho (`link_or_shared_file`, `path_alias`, `unsupported_file`).
- `Missions.bind_workspace` recusa candidato dentro ou igual à origem
  (`invalid_workspace_location`) e base divergente (`source_changed`,
  `invalid_workspace_base`).

## Reconciliação da origem

Acontece quando a origem mudou depois do candidato e a entrega não pôde ser aplicada.
A marca `data.reconciliation_required` é gravada por `Delivery.recover` quando, após o
rollback, o manifesto da origem difere da base do pacote. Em `awaiting_user`:

1. `HiveService.reconcile_source` repete o resultado salvo se a chave já foi usada;
   com o serviço fechando devolve `closing`.
2. `Missions.begin_reconciliation` grava a intenção durável
   (`reconciliation_operation` com `status: "pending"`), **antes** de copiar qualquer
   coisa (`reconciliation_not_available`, `reconciliation_in_progress`).
3. Cria um snapshot novo da origem atual e calcula os arquivos que o candidato antigo
   alterou. Se algum estiver fora dos arquivos das tarefas:
   `reconciliation_scope_invalid`. Arquivo alterado também na origem desde a base:
   conflito, registrado por `record_reconciliation_conflict` (status `conflict`, lista
   ordenada em `reconciliation_required.conflicts`, a missão fica em `awaiting_user`,
   resposta 200).
4. Sem conflito, copia as alterações para o candidato novo, confere hashes e
   `Missions.reconcile_workspace` liga o candidato novo, arquiva o antigo em
   `workspace_history` e o pacote em `delivery_history`, e leva a missão a
   `verifying` para nova verificação independente (`reconciliation_stale` se algo
   mudou no meio).
5. Falha ou reinício no meio: `reconciliation_interrupted` leva a missão a
   `recovery_required`, com workspace e origem intactos. Depois de
   `recover_delivery`, reconciliar de novo exige chave nova.

Uma reconciliação pendente conta como missão ativa: o fechamento do Hub espera.

## Entrega

`Delivery.prepare` (chamada pelo despacho) monta o pacote: `source`, `candidate`,
`base`, `candidate_manifest`, `candidate_hash`, `changes` (arquivos diferentes da
base), `plan_hash`. O `delivery_hash` é o `digest` do pacote. Recusa
`workspace_mismatch`, `stale_candidate`, `changes_outside_plan` (qualquer mudança fora
dos arquivos das tarefas) e `project_mismatch`.

`Delivery.apply` (estado `delivery_approved`; repetir após `completed` devolve a
missão):

1. Confere aprovação e hash (`delivery_not_approved`) e que origem e raiz do journal
   estão no **mesmo volume** (`delivery_same_volume_required`; fora do Windows,
   `delivery_platform_unsupported`), antes de mutar.
2. Marca `applying`. Cria `HiveMind/state/deliveries/delivery-<digest>/` (se já existir:
   `delivery_recovery_required`) e grava `journal.json` com um item por arquivo
   (`attempted`, `rollback_attempted`).
3. Confere `manifest(origem) == base` (`source_changed`) e
   `manifest(candidato) == candidate_manifest` (`candidate_changed`); copia cada
   original para `<n>.original` e cada novo para `<n>.new`, de forma exclusiva
   (`delivery_artifact_changed`).
4. Aplica item a item gravando `attempted` no journal antes:
   - **substituição**: `ReplaceFileW` captura o arquivo realmente substituído como
     `<n>.captured` (backup);
   - **adição**: `MoveFileEx` sem permitir substituir (não sobrescreve destino criado
     em paralelo);
   - **remoção**: o arquivo vai para `<n>.captured` (quarentena).
   Depois de cada item confere o backup (`source_changed_during_apply`); no fim,
   `manifest(origem)` precisa ser o esperado.
5. Marca o journal completo, a missão vai a `completed` e as abelhas temporárias
   ficam inativas.

Qualquer falha dispara `_rollback` (restaura pelos backups, em ordem inversa, só se o
estado atual de cada arquivo for exatamente o esperado); a missão fica em
`recovery_required` com `approved_delivery_hash` zerado e o evento
`delivery_interrupted {rollback_complete}`. Divergência ou falha parcial mantém os
artefatos do journal para recuperação. Não é uma transação global entre arquivos.

`Delivery.recover` (`recover_delivery`, só em `recovery_required`) valida o journal
contra o pacote (`delivery_journal_unverified`), roda o rollback (`delivery_recovery_ambiguous`
se um arquivo não puder ser restaurado com segurança, mantendo tudo no lugar) e leva a
missão a `awaiting_user`, com a marca de reconciliação se a origem mudou.

Limitações da recuperação (sem tratamento automático):

- `delivery_recovery_ambiguous` **exige intervenção manual**: a origem pode estar
  alterada e os artefatos (`.original`, `.captured`, `.rollback`) ficam preservados no
  diretório do journal. Nem `recover_delivery` repetido nem `abandon` (recusado com
  `delivery_recovery_required`, pois o journal tem `attempted: true`) resolvem; só
  conferir e restaurar os arquivos à mão.
- Journal ilegível, corrompido ou acima de 10 MiB com `delivery_applying` como evento
  mais recente: `recover_delivery` devolve `delivery_journal_unverified` e `abandon` é
  recusado (o journal conta como pendente); **exige intervenção manual**.
- Depois de `recover_delivery`, aplicar de novo a **mesma** entrega (mesmo
  `delivery_hash`) é recusado com `delivery_recovery_required`, porque o diretório do
  journal já existe (`Delivery.apply`); a missão volta a `recovery_required` e o caminho
  é gerar outra entrega (novo candidato e nova verificação).

## Ciclo de vida

### Presença e heartbeat

- A tela envia `POST /presence {hud, present:true}` (a cada 15 s no frontend atual); `heartbeat`
  registra o instante e limpa o estado de fechamento. `present:false` (`bye`) remove
  a tela.
- TTL de 120 s por tela e carência (`presence_grace`) de 10 s, ambos no código de
  `HiveService`.
- `check_presence` (a cada 2 s): sem tela viva e com histórico de tela, marca o
  início da ausência com motivo `last_viewer_closed` (nenhuma tela registrada) ou
  `presence_uncertain` (telas registradas mas expiradas); passada a carência pede
  pausa de todas as missões ativas.
- Sem tela viva, `ask`, `start` e `resume` devolvem `presence_uncertain` e o despacho
  não inicia jobs.

### Pausa, drenagem e retomada

- Motivos válidos de pausa: `user`, `last_viewer_closed`, `presence_uncertain`,
  `shutdown`, `job_failed`. Só estados `planning`, `running`, `verifying`, `correcting`
  podem pausar (`pause_not_allowed`).
- `Lifecycle.request_pause` põe a missão em `pausing` (com `fence` único) e fecha a
  admissão do broker de cada sessão registrada; novas ferramentas recebem
  `tool_not_available`.
- `Lifecycle.progress` espera todos os brokers drenarem, só então chama o
  `interrupt` das sessões e declara `paused` (ou `awaiting_user` para `job_failed`)
  quando nenhum job continua `running`. A watchdog e o fim de cada job chamam
  `progress`.
- `resume` só em `paused`, só por pedido explícito, e bloqueia se houver job
  `unknown` (`recovery_required`). Retomar `planning` cria uma sessão nova da
  Rainha (`resume-planning-...`); as demais voltam ao despacho normal.
- `preparing` e `applying` não pausam; contam como ativas até terminar.
- Fechar a última tela também pausa; reabrir ou recarregar nunca retoma sozinho.

### `hub_exit_ready` e watchdog

- A thread `hivemind-presence` (daemon, iniciada por `get_service`) roda
  `check_presence`, `progress_pauses` e `advance` a cada 2 s; exceção num tick não
  derruba a thread e nunca retoma nada.
- `manager.hub_exit_ready()` devolve verdadeiro se o serviço nunca foi criado.
  Senão chama `HiveService.hub_exit_ready`: sem missão ativa, verdadeiro; com tela do
  Hive viva, falso; sem tela, abre a carência (falso) e, vencida, pede pausa de todas
  (`request_pause_all`) e devolve verdadeiro só quando nenhuma missão continua ativa.
- Missão ativa = `planning`, `preparing`, `running`, `verifying`, `correcting`,
  `pausing`, `applying`, ou `awaiting_user` com reconciliação pendente.
- `request_pause_all` também fecha novas reconciliações (`closing`) até o próximo
  heartbeat.
- `HiveService.close` pede pausa e só encerra se nada estiver ativo
  (`pause_draining`); o `server.py` atual não o chama.

### Reinício

`Store.recover_interrupted` roda quando o serviço é criado. Missões em `planning`,
`preparing`, `running`, `verifying`, `correcting`, `pausing` ou `applying` viram
`recovery_required` (jobs `running`, `tool_active`, `draining` viram `unknown`, com
evento `recovery_required {previous_state}`); uma reconciliação pendente em
`awaiting_user` também. O código nunca repete um efeito externo possivelmente
executado. Missões `paused` continuam `paused`.

`service.lock` (bloqueio exclusivo de 1 byte na pasta de estado) impede dois serviços
no mesmo estado (`service_already_owned`).

## Estado em disco

Raiz: `HiveMind/state/` (criada na primeira chamada de rota; fora do manifesto dos
workspaces).

| Caminho | Conteúdo |
|---|---|
| `hive.sqlite3` | Banco do serviço (esquema abaixo) |
| `service.lock` | Posse exclusiva do estado |
| `runtime/<hash>/` | Geração de runtime copiada |
| `workspaces/<id>/` | Candidatos isolados (snapshot ou worktree Git) |
| `verification/<sha256 do job>/` | Scratch de escrita dos checks |
| `deliveries/delivery-<digest>/` | `journal.json` e `<n>.original`, `.new`, `.captured`, `.restore`, `.rollback` |

Tabelas do SQLite (conexão com `timeout=10`, chaves estrangeiras ligadas, transações
`BEGIN IMMEDIATE`):

| Tabela | Conteúdo |
|---|---|
| `missions` | `id`, `state`, `revision`, `cycle`, `cycle_limit`, `data` (JSON), datas |
| `events` | `seq` autoincremental, `mission_id`, `kind`, `data`, `created_at` |
| `commands` | `(mission_id, key)`, `fingerprint`, `result` (idempotência) |
| `bees` | abelhas da missão: `id`, `role`, `temporary`, `active`, `data` |
| `jobs` | `id`, `mission_id`, `bee_id`, `role`, `state`, `data` (tarefa, arquivos, ciclo, plano, identidade do processo, resultado) |
| `leases` | `mission_id`, `owner`, `expires_at` |
| `settings` | `worker_limit` e `revision` (linha única) |
| `roster_settings` | equipe permanente (JSON) e `revision` (linha única) |

Nenhum código remove workspaces, scratch, journals ou gerações depois de usados. Em
projetos Git, o candidato é um worktree registrado no `.git` da origem e só é removido
se o snapshot falhar.

## Eventos

`GET /missions/<id>` devolve `events` com `seq`, `kind`, `data`, `created_at`. Os
dados nunca trazem texto de provedor nem do modelo.

| `kind` | Quando |
|---|---|
| `mission_created` | criação (`cycle`, `cycle_limit`) |
| `planning_requested` | `ask` aceito (`queen_id`) |
| `queen_replied` | Rainha respondeu (`job_id`, `kind`) |
| `plan_proposed` / `plan_approved` | plano registrado / aprovado (`plan_hash`, `plan_attempt`) |
| `workspace_requested` | `start` aceito, snapshot a caminho |
| `workspace_bound` | candidato ligado à missão (`base_hash`, `kind`) |
| `mission_started` | `running` (`plan_hash`, `plan_attempt`, `cycle`) |
| `job_started` / `job_finished` | job reservado / encerrado (`state`: `succeeded`, `failed`, `paused`) |
| `provider_session_started` | sessão do provedor criada, identidade do processo gravada |
| `tool_completed` | chamada a `read`, `patch` ou `checks` (`job_id`, `bee_id`, `tool`, `success`); só jobs de execução |
| `bee_progress` | `progress` válido de uma abelha (`job_id`, `bee_id`, `done`, `total`, `note`); jobs de execução, não o planejamento |
| `job_error` | job falhou (`reason`: código estável) |
| `verification_started` / `verification_recorded` | verificação iniciada (`candidate_hash`) / veredito (`passed`, `cycle`) |
| `correction_coordinated` | Rainha entregou a coordenação da correção |
| `cycle_limit_changed` | teto alterado |
| `pause_requested` / `paused` / `resumed` | pausa pedida (`reason`, `fence`) / concluída / retomada (`resumed_to`) |
| `delivery_prepared` | pacote montado (`delivery_hash`, `changes`) |
| `delivery_approved` | entrega aprovada |
| `delivery_applying` / `delivery_completed` | aplicação iniciada / concluída |
| `delivery_interrupted` | falha na aplicação (`rollback_complete`) |
| `delivery_recovered` | `recover_delivery` concluído |
| `mission_abandoned` | `abandon` aceito (`previous_state`) |
| `source_reconciliation_requested` | intenção de reconciliar gravada |
| `source_reconciliation_conflict` | conflitos encontrados (`conflicts`, `candidate`) |
| `source_reconciled` | candidato novo ligado (`preserved_workspace`) |
| `source_reconciliation_interrupted` | reconciliação interrompida |
| `recovery_required` | reinício (`previous_state`), preparação interrompida (`reason`) |

## Códigos de erro e conflito

Códigos de `409` devolvidos pela API (e usados internamente como motivo de falha de
job quando listados em `service.py`):

| Código | Significado |
|---|---|
| `invalid_state:<estado>` | ação não vale no estado atual |
| `stale_revision` | `revision` diferente da atual |
| `idempotency_key_reused` | mesma chave com outro payload ou outra revisão |
| `mission_exists` | `id` já existe (com chave nova) |
| `lease_held` / `lease_required` | outro dono tem o lease / falta lease válido para o dono |
| `presence_uncertain` | nenhuma tela do Hive viva |
| `closing` | serviço fechando; nova reconciliação recusada |
| `runtime_generation_changed` | a geração copiada foi alterada ou ficou inválida |
| `service_already_owned` | outro processo já possui o estado |
| `provider_unavailable` | provedor sem adaptador (CLI não encontrada) |
| `queen_configuration_changed` | Rainha enviada não está no cadastro |
| `roster_incomplete` | alguma abelha da equipe não tem descrição, skills ou ferramentas válidas; o corpo traz `bee` e `missing` |
| `tool_not_allowed` | **não é HTTP**: resposta do broker ao modelo quando a ferramenta existe mas não está na lista da abelha; o job continua |
| `project_mismatch` | projeto difere do planejado, aprovado ou entregue |
| `stale_plan` / `plan_not_approved` | hash do plano divergente / plano sem aprovação do mesmo `plan_attempt` |
| `workspace_required` / `workspace_generation_mismatch` | sem workspace do plano / workspace de outro plano |
| `cycle_limit_reached` | reautorização exige elevar o teto antes |
| `limit_below_current_cycle` | teto menor que o ciclo atual |
| `recovery_required` | há job `unknown` (propose ou resume) |
| `attempt_unverified` | contador de tentativas do plano inválido |
| `jobs_still_running` | verificação pedida com job ativo |
| `stale_candidate` | candidato mudou desde a verificação ou o veredito |
| `independent_verifier_required` | veredito de quem não é o verificador do plano |
| `verification_criteria_incomplete` | critérios do veredito diferem dos de aceite |
| `stale_delivery` | `candidate_hash` ou `delivery_hash` divergente, ou veredito não aprovado |
| `correction_not_pending` / `correction_not_ready` | sem correção pendente / operária antes da coordenação |
| `dispatch_not_allowed` | estado ou pausa não permitem despachar |
| `job_exists` / `job_not_running` | job duplicado / job não está em execução |
| `queen_busy` / `bee_busy` / `worker_slots_full` / `files_busy` | Rainha, abelha, limite global ou arquivos ocupados |
| `unknown_bee` / `task_not_assigned` | abelha fora do plano / tarefa de outra abelha |
| `dependencies_incomplete` / `task_already_attempted` | dependência pendente / tarefa já tentada no ciclo |
| `pause_not_allowed` / `resume_not_allowed` / `pause_draining` | estado não pausa / só `paused` retoma / ainda drenando |
| `planning_result_invalid` | resposta da Rainha fora do formato ou plano inválido |
| `planning_scope_mismatch` | plano muda projeto ou equipe permanente |
| `project_too_large_to_plan` | origem com mais de 5000 arquivos |
| `job_result_invalid` | resultado do job acima de 200000 caracteres |
| `verdict_invalid` | veredito fora do formato, incompleto ou com candidato alterado |
| `process_identity_unverified` | não foi possível gravar a identidade do processo da sessão |
| `invalid_workspace_location` / `invalid_workspace_base` | candidato em local proibido / base inconsistente |
| `source_changed` | origem difere da base |
| `reconciliation_not_available` / `reconciliation_in_progress` | sem marca de reconciliação / já há uma pendente |
| `reconciliation_stale` / `reconciliation_scope_invalid` | origem ou arquivos mudaram durante a reconciliação / alteração fora das tarefas |
| `workspace_mismatch` / `changes_outside_plan` | pacote não bate com o workspace / mudança fora das tarefas |
| `delivery_not_approved` | hash aprovado diferente ou veredito não aprovado |
| `delivery_same_volume_required` / `delivery_platform_unsupported` | origem e journal em volumes diferentes / fora do Windows |
| `delivery_recovery_required` | diretório do journal já existe (em `apply`) / há journal pendente da entrega atual (em `abandon`: recuperar a entrega antes) |
| `candidate_changed` / `source_changed_during_apply` / `delivery_artifact_changed` | candidato, origem ou artefato do journal mudou |
| `delivery_journal_unverified` / `delivery_recovery_ambiguous` | journal ausente ou inconsistente / rollback não confirmou todos os arquivos |

Códigos de `WorkspaceError` (também 409): `invalid_root`, `vault_configuration_invalid`,
`vault_project_forbidden`, `invalid_path`, `excluded_path`, `link_or_shared_file`,
`missing_path`, `outside_root`, `path_alias`, `unsupported_file`, `git_unavailable`,
`git_command_failed`, `invalid_workspace_id`, `recursive_state_root`,
`workspace_exists`, `git_root_required`, `git_head_invalid`,
`source_changed_during_snapshot`, `runtime_unavailable`,
`runtime_changed_during_generation`, `invalid_base_manifest`, `missing_delivery_parent`,
`invalid_read`, `invalid_read_target`, `invalid_patch`, `write_not_approved`,
`missing_parent`, `stale_patch`, `invalid_check`, `check_not_approved`,
`restricted_runner_unavailable`, `scratch_not_separate`, `check_cli_unverified`,
`check_launcher_unverified`, `check_profile_unverified`, `restricted_check_failed`,
`check_result_invalid`. Os de ferramenta chegam ao modelo apenas como `tool_failed`.

Códigos de motivo em `job_error.reason` (`HiveService._failure_reason`):

| Grupo | Códigos |
|---|---|
| Gate (`gate:<código>` na exceção, só o código no evento) | `cli_unavailable`, `version_unverified`, `subscription_unverified`, `discovery_incomplete`, `selection_unknown`, `selection_model_unlisted`, `selection_effort_unlisted`, `ordinary_quota_unavailable`, `billing_path_unverified`, `managed_policy_unverified`, `enforcement_evidence_unverified` |
| Turno | `native_tool_unexpected`, `process_unavailable`, `protocol_invalid_or_closed`, `protocol_timeout`, `session_controls_unverified`, `tool_limit_reached`, `tool_not_available`, `tool_not_drained`, `turn_not_available`, `turn_result_invalid`, `turn_start_failed` |
| Adaptadores (código fixo) | `command_failed`, `protocol_closed`, `method_not_allowed`, `unexpected_server_request`, `control_invalid`, `catalog_invalid`, `usage_invalid`, `status_invalid`, `security_config_invalid`, `mcp_name_invalid`, `mcp_roster_invalid`, `global_instructions_unknown`, `catalog_pagination_invalid`, `catalog_pagination_limit`, `context_unverified` |
| Adaptadores (a exceção traz sufixo variável; só o prefixo é gravado) | `thread_controls_unverified`, `protocol_request_failed` |
| Planejamento e resultado | `planning_result_invalid`, `planning_scope_mismatch`, `project_too_large_to_plan`, `runtime_generation_changed`, `process_identity_unverified`, `job_result_invalid`, `verdict_invalid` |
| Falha do provedor | `turn_failed:claude:<código>` ou `turn_failed:<categoria do Codex>[:<status http>]` (listas em `adaptadores.md`) |
| Resto | `job_failed` (genérico: texto do provedor, `turn_interrupted`, `turn_invalid` e qualquer outro texto) |

As listas ficam em `service.py` (`_GATE_FAILURES`, `_TURN_FAILURES`, `_ADAPTER_FAILURES`, `_PREFIXED_FAILURES`);
`tests/test_hivemind_service.py` lê `adapters/{base,claude,codex}.py` e quebra se um `DiscoveryError("<código>")`
novo não entrar nelas.
## Armadilhas e o que não existe mais

| Tema | Situação atual no código |
|---|---|
| Perfil de permissões do Codex | O perfil customizado `hivemind-isolated` foi removido. A sessão usa o perfil embutido `:read-only` (um perfil customizado fazia o Codex 0.160.0 falhar todo turno). Não restam referências a `hivemind-isolated` nem a `profile_name_conflict`. Só os checks usam um perfil próprio, `hive-verify` |
| Versão do Claude | O pin exato foi substituído por mínimo `2.1.289` mais prova das flags no `--help`. Não há teto de versão |
| Versão do Codex | Continua exata: `0.160.0` |
| Modelo Fable | Fora do catálogo do Claude; o catálogo só mostra `opus`, `sonnet` e `haiku`. Fable exigiria créditos fora da assinatura |
| Limite padrão de operárias | O código hoje usa **2** (máximo 20). O padrão 4 (máximo 8) está planejado em `roadmap.md` |
| Limites do plano | Não há limite de abelhas ou tarefas; só o teto de 5000 arquivos na origem e 100000 caracteres de prompt |
| Temporárias | Ficam inativas ao concluir a entrega ou ao registrar novo plano; não há ainda limpeza em todo encerramento |
| Reutilizar chave com outra revisão | O fingerprint inclui a revisão, então repetir o mesmo comando com revisão nova devolve `idempotency_key_reused` (ressalva conhecida) |
| Provedor que diz "não" em silêncio | Os motivos de falha de job são códigos fechados; só o texto livre do provedor vira `job_failed`; `thread_controls_unverified:*` e `protocol_request_failed:*` registram só o prefixo |
| Sessões do Hive e vault | O ambiente das sessões remove `HUB_VAULT`, `VOICE_HUB` e as variáveis `HUB_GUARD_*` |
| Estado `tool_active` e `draining` | Consultados, nunca gravados |
| Limpeza de disco | Nada remove workspaces, scratch, journals, gerações ou worktrees Git concluídos |
