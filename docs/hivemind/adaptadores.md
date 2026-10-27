# Hive Mind — adaptadores Claude e Codex
Atualizado em 26/10/2026 · descreve o código atual; o que é planejado fica em `roadmap.md`.

Fonte: `HiveMind/backend/adapters/{base,launcher,codex,claude}.py` e o gate em
`HiveMind/backend/capabilities.py`. Este é o ponto mais sensível do backend: depende do
comportamento dos CLIs e muda a cada versão deles. O resto do backend está em
`backend.md`.

## Arquitetura comum

Cada provedor tem um **adaptador** (descoberta sem inferência) e uma **sessão**
(`CodexProofSession`, `ClaudeProofSession`) que roda uma conversa só com modelo, sem
ferramentas nativas. Toda ação do modelo passa pelo `ToolBroker` do backend, que recebe
**só as ferramentas do job** (o subconjunto de `read`, `patch` e `checks` do cadastro da
abelha, mais `progress` para operária, subagente e verificador; a Rainha não tem
`progress`). Os dois adaptadores anunciam ao provedor exatamente `broker.names`, e
nenhuma outra ferramenta é oferecida. Uma ferramenta do catálogo que o job não recebeu e
que o modelo pede mesmo assim é recusada pelo broker com `{"error": "tool_not_allowed"}`,
sem derrubar o job (`backend.md`, "Broker de ferramentas").

### `adapters/base.py`

| Símbolo | Papel |
|---|---|
| `Model(name, efforts)` | Modelo do catálogo e esforços aceitos |
| `Discovery` | Fatos verificados de um provedor: `provider`, `version`, `installed`, `authenticated`, `compatible`, `account_kind`, `models` (ou `None`), `ordinary_usage_allowed`, `has_credits` (Codex), `extra_usage_enabled` (Claude), `policy_customizations_absent` (Claude), `errors` |
| `DiscoveryError` | Código fixo de diagnóstico, nunca texto cru do CLI |
| `safe_name` | Devolve o valor se casar `^[A-Za-z0-9_.-]{1,100}$`, senão `None` |
| `run_status(command, args, timeout)` | Executa o CLI com saída capturada; falha de execução ou tempo: `process_unavailable`; código de saída diferente de zero: `command_failed` |
| `discovery_environment()` | Ambiente herdado sem as variáveis `OPENAI_API_KEY`, `CODEX_API_KEY`, `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, `CLAUDE_CODE_OAUTH_TOKEN`, `OPENAI_BASE_URL`, `ANTHROPIC_BASE_URL`, `CLAUDE_CODE_USE_BEDROCK`, `CLAUDE_CODE_USE_VERTEX`, `CLAUDE_CODE_USE_FOUNDRY`, `HUB_VAULT`, `VOICE_HUB`, `HUB_GUARD_STATE`, `HUB_GUARD_OWNER`, `HUB_GUARD_PID`. Mantém o login nativo do fornecedor |
| `DiscoveryRpc` | JSON-RPC por linha sobre `<cli> app-server --stdio`, com lista fechada de métodos: `initialize`, `account/read`, `model/list`, `account/rateLimits/read`, `config/read`. Timeout padrão de 20 s por requisição |

Erros do `DiscoveryRpc`: `process_unavailable`, `protocol_closed`, `method_not_allowed`,
`protocol_timeout`, `protocol_invalid_or_closed`, `unexpected_server_request` e
`protocol_request_failed:<método>:<código numérico ou unknown>:<categoria>`, com
categoria `reload_config`, `read_mcp` ou `other`. O stderr do CLI é descartado.

Ao abrir, `_track()` põe o processo lançado num **Job Object** do Windows com
`JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE` (os descendentes entram no mesmo job) e inicia a
thread leitora. `close()` fecha o stdin e espera 5 s; se o processo não sair, mata a
**árvore inteira** (`taskkill /T /F`, depois `kill`). Depois fecha o job, o que encerra
qualquer descendente que tenha sobrado (em `finally`, mesmo se o fechamento falhar),
inclusive quando o lançador saiu sozinho e
deixou o CLI segurando o pipe. Por fim espera até 5 s a leitora e só fecha o stdout se
ela terminou; fechar o stdout sob uma leitura bloqueada travava o `close()` para sempre
(B2 do teste no navegador de 24/10/2026). Se o job não puder ser criado, sobra o
`taskkill`.

### `adapters/launcher.py`

- `provider_command(provider)` resolve o executável em
  `%APPDATA%\npm\node_modules`: Codex como `(node, @openai/codex/bin/codex.js)`,
  Claude como `(@anthropic-ai/claude-code/bin/claude.exe,)`. Sem o arquivo (ou sem
  `node`, no Codex): `ValueError("provider_unavailable")`.
- `adapters(generation)` monta `{"codex": CodexAdapter, "claude": ClaudeAdapter}`. Um
  provedor sem CLI instalada simplesmente não entra no dicionário (aparece como ausente
  em `GET /status` e leva a `provider_unavailable`). Cada adaptador recebe o comando
  direto (descoberta) e um `session_command` que aponta para o `assistant.py` **da
  geração de runtime**: `python -B <geração>/hub_runtime/assistant.py --hivemind <provedor>`.
- `main(argv)` é o ponto `--hivemind` de `hub_runtime/assistant.py`. Só executa duas
  formas, qualquer outra devolve código 2:
  - `codex app-server --stdio`;
  - `claude` com exatamente os argumentos de `model_only_arguments()` seguidos de
    `--model <nome seguro> --effort <nome seguro>`.
  Depois dispara o CLI real com `discovery_environment()`, entregando **explicitamente**
  o stdin e o stdout do lançador (`stdin=0, stdout=1`), stderr descartado e
  `CREATE_NO_WINDOW`. Sem isso, com o Hub em `pythonw.exe` (sem console, o modo normal
  do `launch_hub.vbs`), o CLI não recebia os pipes e toda sessão expirava com
  `protocol_timeout` (B1 de 24/10/2026; teste
  `test_launcher_hands_pipes_to_cli_when_started_without_console`).

## Gate e evidência de enforcement

`capabilities.evaluate(discovery, model, effort, evidence)` devolve `GateResult`
(`catalog`, `entitlement`, `included_billing`, `execution_allowed`, `reasons`).
`entitlement` fica sempre `not_tested`: estar no catálogo não prova direito de uso.
Cada motivo abaixo bloqueia o despacho; o gate só libera com a lista de motivos vazia.

| Motivo (nesta ordem) | Quando |
|---|---|
| `cli_unavailable` | `installed` falso |
| `version_unverified` | `compatible` falso |
| `subscription_unverified` | `authenticated` falso |
| `discovery_incomplete` | `discovery.errors` não vazio |
| `selection_unknown` | catálogo ausente (`models is None`) |
| `selection_model_unlisted` | modelo fora do catálogo |
| `selection_effort_unlisted` | esforço fora dos esforços do modelo |
| `ordinary_quota_unavailable` | `ordinary_usage_allowed` é `False` |
| `billing_path_unverified` | caminho de cobrança não é o incluído (abaixo) |
| `managed_policy_unverified` | só Claude: `policy_customizations_absent` diferente de `True` |
| `enforcement_evidence_unverified` | sem evidência válida da sessão, ou com versão, modelo ou esforço diferentes, ou a validação falhou ou lançou exceção |

Caminho de cobrança incluído (`ordinary_available`):

- Codex: autenticado, `ordinaryUsageAllowed` verdadeiro e `has_credits` falso.
- Claude: autenticado, `ordinary_usage_allowed` verdadeiro e `extra_usage_enabled`
  falso.

Em qualquer outro caso é `unknown` e o despacho é bloqueado. A exceção do turno traz
só o primeiro motivo (`gate:<motivo>`).

**Evidência** (`capabilities._issue_evidence`): objeto interno, selado, emitido pela
sessão para `(provedor, versão, modelo, esforço, função de validação)`. Nunca vem de HTTP
nem da tela. O gate o aceita só se `provider`, `version`, `model` e `effort` forem
exatamente os da descoberta atual **e** a função de validação devolver `True`
naquele instante. A evidência morre junto com a sessão ou com uma mudança de controle.

Fluxo de cada turno (Codex) ou de cada ida ao broker (Claude): `adapter.discover()`
novo, `evaluate(..., session.evidence())`, e só então a mensagem segue ao provedor.
O gate roda **antes** de cada despacho; nenhuma decisão é reaproveitada.

## Codex

| Item | Valor no código |
|---|---|
| Versão aceita | exatamente `0.160.0` (`compatible = version == "0.160.0"`); a evidência também carrega `"0.160.0"` fixo |
| Saída de `--version` | precisa casar `codex-cli X.Y.Z`; senão `version_unrecognized` |
| Conta aceita | `account/read` com `type == "chatgpt"` (`apiKey` e `amazonBedrock` ficam não autenticados) |
| Protocolo | `codex app-server --stdio` (via launcher), JSON-RPC por linha, `experimentalApi` ligado nas sessões |
| Catálogo | `model/list` paginado (limite 100, sem ocultos, até 100 páginas); modelo = `model`, esforços = `supportedReasoningEfforts[].reasoningEffort`. Sem lista fixa no código; validado com `gpt-5.6-luna` |
| Cobrança | `account/rateLimits/read`: `ordinaryUsageAllowed` e `rateLimits.credits.hasCredits` |

Erros de descoberta específicos: `catalog_invalid`, `catalog_pagination_invalid`,
`catalog_pagination_limit`.

### Inventário de segurança (`security_inventory`)

Antes de iniciar a thread, a sessão lê `config/read` e reduz a poucos fatos
(`SecurityInventory`: nomes dos servidores MCP, fingerprint e motivos). Qualquer motivo
aborta com `context_unverified`:

| Motivo | Quando |
|---|---|
| `global_instructions_present` | existe `AGENTS.md` ou `AGENTS.override.md` em `CODEX_HOME` (padrão `~/.codex`) |
| `custom_instructions_present` | `instructions`, `developer_instructions`, `model_instructions_file` ou `compact_prompt` configurados |
| `custom_provider_configuration` | `model_catalog_json` ou `openai_base_url` definidos, ou `chatgpt_base_url` diferente do padrão |

Erros de inventário: `security_config_invalid`, `mcp_name_invalid`,
`global_instructions_unknown`. Na prática, um `AGENTS.md` global em `CODEX_HOME`
impede qualquer abelha Codex de rodar.

### `thread/start` (`session_params`)

| Parâmetro | Valor |
|---|---|
| `model`, `modelProvider` | modelo escolhido, `openai` |
| `serviceTier` | `default` |
| `cwd`, `runtimeWorkspaceRoots` | o workspace da missão (lista com um item) |
| `permissions` | `":read-only"` (perfil embutido) |
| `approvalPolicy` | `never` |
| `allowProviderModelFallback` | `false` |
| `ephemeral` | `true` |
| `environments` | `[]` |
| `dynamicTools` | **só as ferramentas do broker do job** (`session_params(..., tool_names=broker.names)`, na ordem `read`, `patch`, `checks`, `progress`): `read` (`path`), `patch` (`path`, `content` texto ou nulo, `expected_sha256` texto ou nulo), `checks` (`argv` lista de textos) e `progress` (`done` e `total` inteiros, `note` texto); todos com todos os campos obrigatórios e `additionalProperties: false`; descrição `HiveMind broker operation: <nome>`. Sem `tool_names`, o padrão anuncia as quatro. Uma operária sem `checks` no cadastro não vê `checks`; a Rainha só vê as do cadastro dela e nunca `progress` |
| `config.agents.enabled` | `false` |
| `config.features` | `multi_agent_v2`, `multi_agent`, `plugins`, `apps`, `shell_tool`, `memories`, `hooks`, `code_mode`, `deferred_executor` desligados; `prefer_mxc` ligado |
| `config.windows.sandbox` | `unelevated` |
| `config.mcp_servers` | cada servidor MCP descoberto com `enabled: false` |
| `config.memories` | `use_memories` e `generate_memories` falsos |
| `config.skills.include_instructions` | `false` |
| `config.project_doc_max_bytes` | `0` |
| `config.web_search` | `disabled` |

Toda escrita passa pelo broker; o Codex nunca escreve por conta própria.

Depois da resposta, a sessão confere (`thread_controls_unverified:<campos>:roots_<forma>`
se algum falhar): id da thread, `instructionSources == []`, `environments == []`,
`ephemeral`, modelo igual, `modelProvider == "openai"`, `approvalPolicy == "never"`,
`activePermissionProfile.id == ":read-only"`, no máximo uma raiz igual ao workspace e
`cwd` igual ao workspace. Em seguida `_validate` precisa dar verdadeiro, senão
`session_controls_unverified`.

`CodexProofSession._validate` confere: processo vivo, thread aberta, broker aceitando
chamadas, `CODEX_HOME` inalterado, inventário igual ao inicial e sem motivos, roster de
MCP inteiro `disabled` (`mcpServerStatus/list` paginado) e o gate com exatamente o motivo
`enforcement_evidence_unverified` (ou seja, nada além da evidência faltando).

### `turn/start` e itens do turno

- Parâmetros: `threadId`, `input` (um texto), `model`, `effort`, `serviceTierForTurn:
  "default"` e, quando há esquema, `outputSchema` (a Rainha e o verificador recebem
  esquema; operária e Rainha de correção não). Prompt acima de 100000 caracteres ou
  vazio: `ValueError`.
- Chamadas de ferramenta (`item/tool/call`): conferem `threadId`, `turnId` e o limite
  de 100 chamadas por turno; senão a resposta é `tool_request_invalid`. O resultado
  volta como `inputText` com o JSON e `success`. Ferramenta do catálogo que o job não
  recebeu: resposta `{"error": "tool_not_allowed"}` (o turno continua). Nome fora do
  catálogo ou pausa pendente: resposta `tool_not_available`.
- Qualquer outra requisição do servidor recebe erro JSON-RPC `-32601`.
- O texto de saída são os itens `agentMessage` concluídos no turno com
  `phase: "final_answer"`. Mensagens de comentário (`phase: "commentary"`, que o Codex
  manda antes de usar ferramentas) ficam de fora; sem nenhuma `final_answer`, vale a
  concatenação (quebra de linha) das que não são `commentary`. Antes de 25/10/2026 tudo era concatenado e
  o JSON da Rainha ou do verificador quebrava (B3).
- `turn/completed` com status diferente de `completed`: `turn_failed:<código>`,
  `turn_interrupted` ou `turn_invalid`; status `completed` devolve o texto.

**Itens permitidos** (`_TURN_ITEM_TYPES`): `userMessage`, `agentMessage`, `reasoning`,
`plan`, `dynamicToolCall`, `functionCallOutput`, `contextCompaction`. Um
`item/started` ou `item/completed` da thread com outro tipo (comando, edição de
arquivo, MCP, busca na web, imagem, etc.) levanta `native_tool_unexpected`.

**`turn_error_code`** reduz o erro do turno a uma categoria fechada, sem mensagem do
provedor:

| Origem | Categorias |
|---|---|
| Texto em `codexErrorInfo` | `contextWindowExceeded`, `sessionBudgetExceeded`, `usageLimitExceeded`, `rateLimitExceeded`, `flexUnavailable`, `serverOverloaded`, `cyberPolicy`, `misalignmentPolicyViolation`, `tooManyDenials`, `internalServerError`, `unauthorized`, `badRequest`, `threadRollbackFailed`, `sandboxError`, `other` |
| Objeto com um nome | `httpConnectionFailed`, `responseStreamConnectionFailed`, `responseStreamDisconnected`, `responseTooManyFailedAttempts`, seguidos de `:<status http>` quando houver (100 a 599) |
| Qualquer outro formato | `unknown` |

### Interrupção

`interrupt()` só atua depois de o broker estar drenado (`tool_not_drained` senão).
Marca pausa pendente e, se já há turno, envia `turn/interrupt`; se o turno ainda está
começando, o `turn/interrupt` vai assim que o id do turno chega. Novo turno com pausa
pendente: `turn_not_available`.

## Claude

| Item | Valor no código |
|---|---|
| Versão aceita | `_MIN_VERSION = (2, 1, 289)` ou mais nova, **e** `flags_supported` verdadeiro. Sem teto de versão |
| Saída de `--version` | precisa casar `X.Y.Z (Claude Code)`; senão `version_unrecognized` |
| Conta aceita | `claude auth status --json` com `loggedIn` verdadeiro, `authMethod == "claude.ai"` e `apiProvider == "firstParty"` |
| Catálogo | `_MODELS = ("opus", "sonnet", "haiku")`: só esses apelidos, que apontam para o modelo mais recente da família, e só se vierem no `initialize` do CLI. Esforços = `supportedEffortLevels` (ausente vira lista vazia, e então nenhum esforço é aceito) |
| Cobrança e cota | `get_usage`: exige `rate_limits_available`, `subscription_type` em `pro`, `max`, `team` ou `enterprise`, e `five_hour.utilization` e `seven_day.utilization` numéricos de 0 a 100; ordinário liberado se ambos `< 100`; `extra_usage.is_enabled` define `extra_usage_enabled` |
| Política | `get_settings.effective` sem `hooks`, `statusLine`, `fileSuggestion` nem `fallbackModel` |
| Protocolo | `stream-json` de entrada e saída, com `control_request` |

### `flags_supported` (prova das flags)

Roda `<claude> --help` (sem inferência) e exige que **todas** as flags da sessão
apareçam, casando `(^|[\s,])--flag([\s,=]|$)` em alguma linha. O resultado é guardado em
cache por string de versão (`_flag_proofs`); falha ao executar o `--help` não entra no
cache e é tentada de novo. As flags verificadas são 14: as 12 de
`model_only_arguments()` e `--model` e `--effort`. A checagem enxerga uma flag citada só
em texto de ajuda de outra (ressalva abaixo).

### `model_only_arguments()`

Argumentos do candidato sem ferramentas nativas (o launcher só aceita esta lista exata):

| Argumento | Efeito |
|---|---|
| `--print` | modo print (não interativo) |
| `--safe-mode` | modo seguro (`safe-mode`) do CLI |
| `--input-format stream-json` | entrada por mensagens JSON |
| `--output-format stream-json` | saída por mensagens JSON |
| `--verbose` | saída detalhada |
| `--tools ""` | lista vazia de ferramentas nativas |
| `--strict-mcp-config` | só a configuração MCP indicada |
| `--mcp-config '{"mcpServers":{}}'` | nenhum servidor MCP |
| `--setting-sources ""` | lista vazia de fontes de configuração |
| `--no-chrome` | integração com o Chrome desligada |
| `--disable-slash-commands` | slash commands desabilitados |
| `--no-session-persistence` | sessão efêmera |

A sessão acrescenta `--model <nome> --effort <esforço>` e roda com `cwd` no
workspace. `read_controls` (descoberta) usa os mesmos argumentos e envia por stdin as
três requisições de controle.

### Ambiente

`model_only_environment()` = `discovery_environment()` mais
`CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`.

### Controles e sessão

- `read_controls` e `_ControlRpc.controls` enviam `control_request` com `initialize`
  (no `_ControlRpc`, só na primeira chamada; depois reaproveita), `get_settings` e `get_usage` (`skip_behaviors: true`) e exigem resposta `success` para
  cada `request_id` (`control_invalid` senão; `catalog_invalid`, `usage_invalid` para
  respostas malformadas).
- Entrada na sessão (`ClaudeProofSession.__enter__`): guarda `self.version` com um
  `discover()` novo e lê os controles. Os controles só valem se a cota ordinária está
  livre, `extra_usage` está desligado, a política está limpa e o modelo e o esforço
  constam no catálogo (`session_controls_unverified` senão).
- **Evidência presa à versão**: `evidence()` usa `self.version`, a versão do início da
  sessão. Se o Claude for atualizado no meio, `discovery.version` deixa de coincidir e o
  gate bloqueia (`enforcement_evidence_unverified`); voltar à versão original libera de
  novo.
- `_validate`: processo vivo, broker aceitando, gate com exatamente
  `enforcement_evidence_unverified` e controles atuais ainda válidos.

### Turno e envelope `final` / `action`

A sessão do Claude define o próprio envelope. Cada turno acrescenta ao prompt a instrução de responder um objeto
JSON: `{"final": <texto>}` quando terminar, ou
`{"action": <uma das ferramentas do job>, "arguments": {...}}` para pedir o broker. O
texto lista **só as ferramentas do broker do job** (`broker.names`: por exemplo
`"read"|"patch"|"checks"|"progress"` numa operária completa, ou só `"read"|"checks"` na
Rainha de planejamento), explica o argumento de cada uma (`read` recebe `path`; `patch`
recebe `path`, `content` e `expected_sha256`; `checks` recebe `argv`; `progress` recebe
`done`, `total` e `note`) e termina com "No other tools are available.". Com esquema, o
texto de `final` precisa ser um JSON que obedeça a esse esquema (`output_schema` vai como
texto na mensagem).

Laço (até 100 iterações; depois, `tool_limit_reached`):

1. Gate completo (descoberta, evidência, `evaluate`).
2. Envia a mensagem de usuário em `stream-json`.
3. Lê até chegar `type: "result"`. Mensagem `assistant` com `tool_use` ou
   `parent_tool_use_id` preenchido: `native_tool_unexpected`.
4. `is_error` verdadeiro ou `subtype` diferente de `success`:
   `turn_failed:claude:<código>`. Resultado que não é JSON objeto: `turn_result_invalid`.
5. `{"final": texto}` devolve o texto. Só `{"action", "arguments"}` chama o broker
   (`dispatch_and_reply`) e a próxima mensagem leva `Broker result: <JSON>`. Ferramenta
   do catálogo que o job não recebeu: o resultado é `{"success": false, "result":
   {"error": "tool_not_allowed"}}` e o laço segue. Ação fora do catálogo ou pausa
   pendente: `tool_not_available`. Qualquer outra forma: `turn_result_invalid`.

**`turn_error_code`** (Claude): `error_max_turns`, `error_during_execution`,
`error_max_budget_usd`, `error_max_structured_output_retries`, `api_error_<status>`
(`api_error_status` inteiro de 100 a 599) ou `unknown`.

`interrupt()` só atua depois de o broker estar drenado (`tool_not_drained` senão) e
envia `control_request` `interrupt` se houver turno em andamento; novo turno com pausa pendente: `turn_not_available`.

## Validação real

Feita em 20/10/2026 (continuação C4, `docs/planos/2026-10-19_hivemind-backend/verificacao-c4.md`):

- Claude 2.1.305, modelo `sonnet`, e Codex 0.160.0, modelo `gpt-5.6-luna`: gate vazio e
  um smoke curto por CLI.
- Missão mista de ponta a ponta: Rainha e verificador no Codex (`gpt-5.6-luna`),
  operária no Claude (`sonnet`), com plano aprovado, três jobs `succeeded`, verificação,
  entrega aplicada na origem e missão `completed` em ciclo 1.
- Catálogo real do Claude reduzido a `opus`, `sonnet` e `haiku`; `fable` fica fora
  (`selection_model_unlisted`).
- Caminho de cobrança incluído nos dois (`has_credits` falso no Codex, `extra_usage`
  falso no Claude).
- O verificador independente (Opus) aprovou R01 a R15 com ressalvas não bloqueantes.
  Os resultados dependem das versões acima; outra versão de CLI exige nova validação
  real.

## Ressalvas conhecidas, ainda não corrigidas

Registradas como EQ-11 em `docs/planos/2026-10-20_hivemind-escala-equipe/issues.md`.
Valem hoje como limitações:

| Ressalva | Comportamento atual |
|---|---|
| Item nativo no Codex é detectado depois do efeito | `item/started` é só notificação: quando `native_tool_unexpected` é levantado, o comando ou a leitura já começou no app-server. O encerramento fecha o stdin, espera até 5 s e então mata só o processo pai; **não** envia `turn/interrupt` nem encerra a árvore de processos. O efeito fica limitado pelo sandbox somente leitura, e a lista é uma trava de integridade, não prevenção |
| Leitura nativa ampla sob `:read-only` | O perfil antigo negava `:root` e temporários; o `:read-only` permite ler o disco por uma ferramenta nativa, se existir alguma. A barreira primária é a configuração (shell, apps, plugins, multiagente, hooks, web e MCP desligados; `environments: []`) e o pin exato `0.160.0` |
| `functionCallOutput` sem checagem de nome | Aceito com qualquer `name`; só as chamadas do broker deveriam passar |
| Item de outra thread é ignorado | Itens com `threadId` diferente não passam pela lista de tipos |
| Perfil ativo conferido só pelo `id` | `extends` do perfil não é verificado |
| Claude sem teto de versão | `>= 2.1.289` mais prova das flags; uma versão nova só prova que as flags existem, não que `--tools ""` mantém a semântica. A detecção de `tool_use` também é posterior à execução |
| Regex das flags | Aceita uma flag citada só em prosa de outra linha do `--help`. O cache por versão não percebe mudança de ajuda com a mesma versão |
| `fake_cli.py` fora do manifesto | `tests/fixtures/hivemind/fake_cli.py` nunca entrou em um manifesto de verificação |
| Regressões sem teste automatizado | Faltam testes para: vínculo evidência × versão do Claude, normalização de nulos da Rainha, `verdict_invalid` e `functionCallOutput` |

## Diagnóstico quando um CLI atualiza e quebra

Nada abaixo exige rodar turno de IA. Comece por `GET /hive-api/catalog` (só descoberta
sem inferência, sobe os CLIs) e pelo `job_error.reason` nos eventos da missão.

| Sintoma ou código | Causa provável | Onde olhar |
|---|---|---|
| `cli_unavailable` ou provedor ausente em `GET /status` | CLI não está em `%APPDATA%\npm\node_modules` (ou falta `node` no Codex), ou `--version` falhou | `launcher.provider_command`, `base.run_status` |
| `discovery_incomplete` com `version_unrecognized` | A saída de `--version` mudou de formato (`codex-cli X.Y.Z`, `X.Y.Z (Claude Code)`) | `CodexAdapter.discover`, `ClaudeAdapter.discover` |
| `version_unverified` no Codex | Qualquer versão diferente de `0.160.0` | `codex.py` (`compatible`), `tools.py` (`check_cli_unverified`) e a versão da evidência |
| `version_unverified` no Claude | Versão abaixo de 2.1.289, ou o `--help` não lista mais uma das 14 flags (renomeada ou removida), ou `--help` falhou | `claude.py:flags_supported`, `model_only_arguments` |
| `selection_model_unlisted` ou `selection_effort_unlisted` | O catálogo do CLI mudou: modelo renomeado, esforço não listado ou, no Claude, `supportedEffortLevels` ausente | `GET /catalog`; `_MODELS` no Claude |
| `selection_unknown` | Catálogo não foi lido (`discovery.models` ausente) | `discovery.errors` do `GET /catalog` |
| `ordinary_quota_unavailable` | Cota ordinária esgotada (Codex: `ordinaryUsageAllowed` falso; Claude: janela de 5 h ou 7 dias em 100%) | `account/rateLimits/read`, `get_usage` |
| `billing_path_unverified` | Há créditos extras (`hasCredits` verdadeiro no Codex) ou `extra_usage` ligado no Claude, ou o `get_usage` mudou de formato | `Discovery.has_credits`, `extra_usage_enabled` |
| `subscription_unverified` | Conta fora de `chatgpt` no Codex; ou, no Claude, não logado, sem `claude.ai` ou `apiProvider` diferente de `firstParty` | `account/read`, `claude auth status --json` |
| `managed_policy_unverified` | O Claude passou a ter hooks, `statusLine`, `fileSuggestion` ou `fallbackModel` efetivos | `get_settings.effective` |
| `enforcement_evidence_unverified` | A validação da sessão falhou: processo morreu, controles ou inventário mudaram, MCP deixou de estar `disabled`, `CODEX_HOME` mudou, ou o Claude foi atualizado durante a sessão | `CodexProofSession._validate`, `ClaudeProofSession._validate` |
| `job_failed` sem detalhe, em Codex | Entre as causas possíveis: `context_unverified` (um `AGENTS.md` global, instruções ou provedor customizados em `CODEX_HOME`), `thread_controls_unverified:...` (a resposta do `thread/start` não bate com o esperado) ou `catalog_invalid`. Esses detalhes não chegam ao evento | `security_inventory`, `session_params`, `CodexProofSession.__enter__` |
| `native_tool_unexpected` no Codex | A nova versão emite um tipo de item que não está em `_TURN_ITEM_TYPES` | `_TURN_ITEM_TYPES` em `codex.py` |
| `native_tool_unexpected` no Claude | O CLI passou a emitir `tool_use` ou mensagens de sub-agente | laço de `ClaudeProofSession.turn` |
| `turn_result_invalid` | Claude respondeu fora do envelope `final`/`action`; no Codex, o `turn/completed` trouxe id de turno diferente do aberto (`turn_start_failed` é quando a resposta de `turn/start` não traz id) | envelope em `claude.py`, `turn/completed` em `codex.py` |
| `turn_failed:...` | Falha do provedor mapeada por `turn_error_code`: limite, rede, política | listas de categorias acima |
| `planning_result_invalid` | Saída da Rainha fora do formato: JSON inválido, os dois campos nulos ou presentes, `validate_plan` falhou. A regra violada não é registrada (o texto do provedor nunca é gravado) | `service.py:_plan_job`, `_QUEEN_OUTPUT` |
| `verdict_invalid` | Veredito fora do formato (`criteria`/`evidence`), critérios incompletos ou candidato alterado | `_verdict_output`, `run_job` |
| `process_identity_unverified` | O processo da sessão já saiu antes de gravar a identidade, ou não é Windows | `HiveService._session_started` |
| `protocol_timeout` ou `protocol_invalid_or_closed` | O app-server ou o stream do CLI não respondeu a tempo ou fechou | `DiscoveryRpc`, `turn()` |
| `check_cli_unverified`, `check_profile_unverified`, `restricted_check_failed` | O Codex dos checks mudou de versão ou a configuração efetiva do perfil `hive-verify` não bate | `tools.py:RestrictedCheckRunner` |
| `protocol_request_failed:<método>:<código>:<categoria>` | O app-server recusou um método permitido (`reload_config`, `read_mcp` ou `other`); aparece em `discovery.errors` | `GET /catalog` |

Ordem recomendada: (1) `GET /catalog` para ver `errors`, `compatible` e o catálogo; (2)
eventos `job_error` da missão; (3) rodar `./.venv/Scripts/python.exe -m pytest
tests/test_hivemind_adapters.py tests/test_hivemind_adapter_turns.py -q` com os fakes de
CLI para separar quebra de formato de quebra de ambiente; (4) só depois pedir nova
validação real com autorização do usuário.
