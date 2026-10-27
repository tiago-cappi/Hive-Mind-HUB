# Hive Mind — correções antes do teste no navegador

> **Status em 21/10/2026: CONCLUÍDA no ciclo 2/3** — aprovada com ressalvas P3, todas corrigidas pela coordenação. Referência do código: `docs/hivemind/`.

21/10/2026 · faixa média · aprovada pelo usuário em 21/10/2026 ("concordo com tudo,
pode criar o PRD e começar"). Implementação por subagentes Sonnet 5.5 em dois lotes
disjuntos; coordenação pela sessão principal Opus 5.5; conferência final por um Opus
5.5 limpo e somente leitura (pedido do usuário, além do mínimo da faixa média).
Referência do código: `docs/hivemind/`.

Depois desta tarefa vem o teste no Chrome do usuário (extensão Claude in Chrome):
fase 1 sem IA e fase 2 com uma missão real pequena num projeto de teste
descartável, **autorizada pelo usuário em 21/10/2026**. A instalação de `playwright` e
`sharp` e a atualização dos scripts de QA ficam para a tarefa de escala.

## Objetivo

Tirar da frente do teste real os problemas que travariam uma missão ou esconderiam a
causa de um erro: missão sem saída em `recovery_required`, motivo de falha
genérico, códigos brutos na tela e o mostrador "BACKEND PENDENTE".

## Decisões

| ID | Decisão |
|---|---|
| D1 | Saída da recuperação travada = comando **`abandon`** ("Encerrar missão"), que leva a missão ao novo estado terminal **`abandoned`**. Histórico (eventos, jobs, plano, workspace) preservado; nenhum arquivo é tocado. Alternativa "refazer cópia e recomeçar" rejeitada pelo usuário. |
| D2 | `abandon` só vale em `recovery_required`. Se houver journal **pendente** para o `delivery_hash` atual (o evento mais recente entre `delivery_applying` e `delivery_recovered` é `delivery_applying` **e** `Delivery.journal_root / ("delivery-" + digest([mission_id, delivery_hash])) / "journal.json"` existe e é ilegível/JSON inválido/acima de 10 MiB ou tem algum item com `attempted: true`), a origem pode ter sido alterada: recusa com `delivery_recovery_required` (use "Recuperar entrega" primeiro). Diretório sem `journal.json`, ou journal legível com todos os `attempted: false` (a origem nunca foi tocada: `Delivery.apply` grava `attempted: true` antes de cada mudança), journal já recuperado (mais recente `delivery_recovered`) ou sem `delivery_applying` não bloqueia. |
| D3 | Motivos de falha: todo código fixo de `DiscoveryError` dos adaptadores passa a ser registrado como ele mesmo em `job_error.reason`; códigos com sufixo variável (`thread_controls_unverified:…`, `protocol_request_failed:…`) registram só o prefixo. Texto do provedor continua nunca registrado. |
| D4 | Confirmação de "Encerrar missão" na própria gaveta (botão vira "Confirmar encerramento" + "Cancelar"); **sem** `window.confirm`, que bloqueia a automação do navegador. |
| D5 | EQ-10 da tarefa de escala (botão de reconciliação em `recovery_required` e mensagens dos códigos) é absorvido aqui e marcado como transferido lá. |
| D6 | Fora do escopo: limpeza de workspaces, `checks` sem Codex, EQ-09, EQ-11, scripts de QA no navegador. |

## Requisitos e critérios de aceite

| ID | Requisito | Critério verificável |
|---|---|---|
| C01 | Comando `abandon` | `POST /hive-api/missions/<id>/command {action:"abandon", key, revision, owner}` sob lease. Em `recovery_required` sem journal de entrega: estado `abandoned`, `data.abandoned = {previous_state, at}` (ou equivalente documentado), evento `mission_abandoned`, revisão +1, nenhum arquivo da origem, workspace ou journal alterado. Repetir com a mesma chave e revisão devolve o mesmo resultado; mesma chave e revisão diferente → `idempotency_key_reused`. Fora de `recovery_required` → `invalid_state:<estado>`. Com journal pendente (ver D2: `journal.json` ilegível ou com `attempted: true`) → `delivery_recovery_required`; diretório vazio, journal só com `attempted: false` ou journal antigo já recuperado → aceito. Testes cobrem cada caso, incluindo missão vinda de `recover_interrupted` com jobs `unknown`. |
| C02 | `abandoned` é terminal | Todos os outros comandos (`ask`, `propose`, `approve_plan`, `start`, `pause`, `resume`, `cycle_limit`, `approve_delivery`, `apply`, `recover_delivery`, `reconcile_source`, `abandon`) são recusados numa missão `abandoned`; `active_missions`, `recover_interrupted` e o scheduler a ignoram; `hub_exit_ready` não espera por ela. Teste parametrizado. |
| C03 | Motivo de falha real | Para cada código fixo levantado como `DiscoveryError` em `HiveMind/backend/adapters/*.py` (lista extraída do código, ex.: `context_unverified`, `global_instructions_unknown`, `security_config_invalid`, `catalog_invalid`, `control_invalid`, `usage_invalid`, `status_invalid`, `mcp_roster_invalid`, `mcp_name_invalid`, `unexpected_server_request`, `method_not_allowed`, `command_failed`, `protocol_closed`, `catalog_pagination_*`), `_failure_reason` devolve o próprio código; prefixos com sufixo devolvem só o prefixo; mensagem arbitrária continua `job_failed`. Teste garante que nenhum texto fora da lista vaza. |
| C04 | Mensagens claras na tela | `live-drawers.js` traduz para frases em português: todos os códigos de erro/conflito da tabela "Códigos de erro e conflito" de `docs/hivemind/backend.md`, todos os motivos de `job_error`, e todos os estados da missão (incluindo `abandoned`), mostrando o código entre parênteses para diagnóstico. Código desconhecido aparece como "Erro inesperado (código)". "Última interrupção" usa a frase traduzida. |
| C05 | Gaveta Missão em `recovery_required` (EQ-10 c) | Não mostra "Reconciliar origem" nem outro botão de avanço; mostra "Recuperar entrega" quando houver `delivery_hash` e "Encerrar missão" com confirmação D4; a recusa `delivery_recovery_required` aparece como orientação clara. Missão `abandoned` mostra "Missão encerrada por você. O histórico foi preservado e a origem não foi alterada." e nenhum botão de comando. |
| C06 | Orientação após falha | Em `awaiting_user` com `job_error` recente, a gaveta explica: o trabalho parou, o motivo traduzido, e que o caminho é conversar com a Rainha (gaveta Conversa) ou pedir novo plano; "Retomar" só aparece em `paused`, como hoje. |
| C07 | Mostrador do Hub | Na página Hive, `providers.js:updateReadout` não diz mais "DEMONSTRAÇÃO FRONTEND · BACKEND PENDENTE"; passa a "HIVE MIND · MISSÕES COM CLAUDE E CODEX". Nenhuma outra mudança em `providers.js`. |
| C08 | Documentação | `docs/hivemind/backend.md` (comando, estado, evento, códigos, motivos), `docs/hivemind/frontend.md` (gaveta Missão, mensagens, mostrador) e `docs/hivemind/README.md` ("Limitações conhecidas" sem os itens resolvidos; "Recursos" com o encerramento) atualizados; EQ-10 marcado "transferido para 2026-10-21_hivemind-correcoes-pre-teste" em `docs/planos/2026-10-20_hivemind-escala-equipe/issues.md`. |
| C09 | Regressão | Suíte completa verde (`./.venv/Scripts/python.exe -m pytest tests -q --basetemp=.test-tmp/<nome>`) e `node tests/hivemind_frontend_behavior.mjs`; nenhuma mudança em `server.py`, `index.html`, `mobile/`; nenhum turno real de IA nem acesso à porta 8765 pelos implementadores. |

## Lotes

| Lote | Requisitos | Arquivos permitidos | Agente |
|---|---|---|---|
| **A backend** | C01, C02, C03, C08 (backend.md) | `HiveMind/backend/{service,missions,routes,store,delivery,lifecycle,scheduler}.py` (só o necessário), `tests/test_hivemind_{service,missions,api,delivery,lifecycle,scheduler}.py`, `docs/hivemind/backend.md` | Sonnet A |
| **B frontend** | C04, C05, C06, C07, C08 (frontend.md) | `HiveMind/frontend/static/live-drawers.js`, `HiveMind/frontend/static/messages.js` (novo), `HiveMind/frontend/static/hive.css` (só se precisar), `codex_frontend/static/providers.js` (só a linha do mostrador), `tests/test_hivemind_frontend.py`, `tests/hivemind_frontend_behavior.mjs`, `docs/hivemind/frontend.md` | Sonnet B |
| Coordenação | C08 (README, escala), C09 | `docs/hivemind/{README,roadmap,testes}.md`, `docs/planos/2026-10-20_hivemind-escala-equipe/issues.md`, este arquivo; no fechamento, a correção P3 em `HiveMind/backend/missions.py:_journal_touched` e seu teste | sessão principal |

Contrato entre A e B: ação `abandon` (sem parâmetros além de `key`, `revision`,
`owner`), estado `abandoned`, evento `mission_abandoned`, erro
`delivery_recovery_required`, e os códigos de C03.

## Ciclos

| Ciclo | Resultado |
|---|---|
| 1 | Lotes A e B entregues (desvio registrado: Lote B criou `HiveMind/frontend/static/messages.js`, autorizado na instrução do lote). D2 refinada pela coordenação para "journal pendente" após o Lote A apontar um beco sem saída. Suíte 387 passed; `hivemind_frontend_behavior.mjs` ok. Verificador Opus: **APROVADO COM RESSALVAS** — P2: diretório de journal sem `journal.json` (falha entre `mkdir` e o primeiro `_save_journal`) trava a missão, pois `abandon` e `recover` recusam; P3: entrega ambígua sem saída não documentada, frase de `delivery_recovery_required` presa ao encerramento, concordância de `invalid_state`, `Object.hasOwn` em `messages.js`, frase de `cycle_limit` em `backend.md`, EQ-10 no roadmap, tabela de lotes, teste de reinício no meio do `apply`. |
| 2 | P2 e os 8 P3 do ciclo 1 corrigidos (D2 final: journal pendente só se `journal.json` ilegível, inválido, > 10 MiB, `items` malformado ou algum `attempted` não `false`). Suíte 401 passed. Verificador Opus: **APROVADO COM RESSALVAS** — sem caminho em que a origem possa estar alterada e o `abandon` seja aceito; P3: `items` não-lista aceito, journal corrompido sem saída não documentado, status do PRD, descrições em `testes.md`. A coordenação corrigiu os quatro (`_journal_touched` recusa `items` não-lista, com teste; limitação documentada em `README.md` e `backend.md`; registros atualizados). Suíte final **403 passed**; `hivemind_frontend_behavior.mjs` ok. **Tarefa concluída.** |
