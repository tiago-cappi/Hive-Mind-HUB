# Issues — backend HiveMind

> **Status em 21/10/2026: CONCLUÍDA** — aprovada na verificação independente do C4 (20/10/2026, R01–R15). Este arquivo é registro histórico do processo e pode descrever intenções já superadas; a referência do código atual está em `docs/hivemind/README.md`. As ressalvas do C4 seguem como EQ-11 em `../2026-10-20_hivemind-escala-equipe/issues.md`.

19/10/2026 · ciclo **3/3** · C1 e C2 preservados; último ciclo autorizado
somente para HB-C2-01 a HB-C2-03 e o diagnóstico sanitizado de R15. Nenhum
quarto ciclo será iniciado. Histórico frontend C7 permanece separado.
Responsável de implementação: um agente GPT-5.6 Terra high para a cadeia,
modelo e esforço selecionados explicitamente;
coordenação libera fases; verificador futuro GPT-6.1 Sol high independente.

| ID/fase | Requisitos e arquivos | Dependência | Aceite de conclusão |
|---|---|---|---|
| HB-00 / P0 | R01–02, R06–07, R10–11, R15; HiveMind/backend/adapters/{base,codex,claude}.py, capabilities.py, testes adapters/fixtures. | Aprovação plano e exceções. | Schema/conta/catalog sanitizados; distinguir entitlement/billing; enforcement de ferramentas e pausa comprovados ou gate explicitamente bloqueado. Sem inferência de descoberta. |
| HB-01 / P1 | R03–04, R08, R12; store.py, missions.py, capabilities.py e testes store/missions. | HB-00. | Estado durável, eventos e idempotência; aprovações versionadas; ciclos não reiniciam; roster temporário arquivado e histórico preservado. |
| HB-02 / P2 | R06–07, R09; workspaces.py, tools.py, delivery.py e testes workspaces/delivery. | HB-01 e política P0. | Git/snapshot sem Git; origem protegida; exclusões/links; geração imutável sem recursão; stale invalida pacote; aplicação e rollback recuperam journal. |
| HB-03 / P3 | R01–02, R04–05, R07–08, R10–12; adapters, scheduler.py, lifecycle.py, service.py, hub_runtime/assistant.py opt-in, server.py watchdog e testes correspondentes. | HB-02 e aprovação explícita §5.5. | Sessões reais por papel; dois slots totais; sem bypass nativo; pausa drena escrita; último HUD e perda incerta distintos; boot/reload não retoma; quota/ciclo teto param com diagnóstico. |
| HB-04 / P4 | R03–04, R08–14; routes.py, backend/__init__.py, frontend/static/{api,mission-state,app,hive,drawers}.js, server.py import/register e testes API/browser. | HB-03. | Missão ponta a ponta ligada ao backend; controles reais; dados desconhecidos honestos; layout/PNG preservados; navegação/minimização sem pausa e sem novo provider. |
| HB-05 / P5 | R01–15; tests/test_hivemind_*.py, tests/hivemind_backend_behavior.mjs, HiveMind/backend/README.md, docs/runtime.md e registros. | HB-04; P0/quota aptos e aprovação deste plano. | Um smoke curto por CLI habilitado e uma missão mínima ponta a ponta em fixture, incluídos na aprovação do plano, consumindo franquia de assinatura sem APIs/créditos extras; sem inferência se P0/quota falhar nem repetir livechecks válidos com hash/protocolo estáveis; testes focados+suíte completa; evidências por aceite; manifesto final congelado e pacote revisável, sem aprovação fictícia. |
| HB-06 / P6 | R01–15; relatório nesta pasta, código/testes somente leitura. | HB-05; agente independente. | Sol6.1 high emite veredito por critério e global; aprovados só os verificáveis; nada necessário pendente. |

## Decisões de liberação

- Usuário aprovou em 19/10/2026 o plano, os três encaixes listados em plano.md
  e validação real mínima em fixture com consumo da franquia das assinaturas.
  P0 não realiza inferência; encaixes externos dependem das fases posteriores.
- P0 concluído com 11 testes focados e sessões sem turno dos dois CLIs; entitlement individual segue não testado até P5. P1–P5 liberados pela coordenação no ciclo 1.
- P0 resolve compatibilidade/enforcement/cobrança incluída. Se não puder comprovar,
  não liberar execução gravável nem escolher alternativa que reduza o requisito.
- P1–P4 foram implementados e validados por testes focados. P5 registrou um
  smoke Claude aprovado, um smoke Codex falho sem causa sanitizada disponível na
  execução histórica e uma missão Claude que parou após a Queen em `awaiting_user`.
  Não houve repetição de inferência. A entrega real, os três papéis e R15 Codex
  continuam pendentes para avaliação independente e eventual nova liberação.
- O candidato C1 está congelado em `manifesto-c1.sha256`. A única tentativa de
  suíte completa encerrou sem resultado terminal disponível, depois de publicar
  progresso parcial; ela não deve ser tratada como aprovação nem repetida pelo
  implementador sem uma nova decisão de verificação.

## Registro de reprovações/correções

### C4 — 20/10/2026 — continuação autorizada pelo usuário (escopo R15)

Decisão explícita do usuário depois do teto: "corrija os problemas que impedem
o Claude e o Codex rodarem no HUB da Hive Mind". Ele também autorizou dar
permissão completa aos CLIs, se necessário (não foi necessário) e mandou
excluir o Fable, deixando só os modelos Claude mais recentes. A implementação é
da sessão principal Opus 5.5, por depender do diagnóstico real feito nela. A
verificação é de um Opus limpo, somente leitura.

Diagnóstico real (`.test-tmp/hivemind-c3-r15/`, anexo em `verificacao-c3.md`):

- **Codex 0.160.0:** qualquer perfil de permissões **customizado** em
  `thread/start` faz o turno falhar com `failed to load workspace requirements`
  (5 reconexões, antes do modelo). Com o perfil embutido `:read-only` ou
  `sandbox: read-only`, o mesmo turno responde `OK`. O `command/exec` dos checks
  com perfil customizado funciona.
- **Claude:** o CLI se atualizou para 2.1.305 e o pin exato 2.1.289 bloqueia
  tudo. Com o pin contornado só no diagnóstico, a sessão Hive responde `OK`
  (`sonnet`/`low`). A falha do C2 foi do modelo `claude-fable-5`:
  `api_error_429`, que exige créditos de uso fora da assinatura.

| ID | Correção | Status |
|---|---|---|
| HB-C4-01 | Codex: sessão com perfil embutido `:read-only` (sem perfil customizado) e checagem `activePermissionProfile.id == ":read-only"`; remoção do conflito de nome de perfil que ficou obsoleto; recusa de qualquer item nativo de ferramenta no turno (lista fechada de tipos permitidos) | implementado, aprovado |
| HB-C4-02 | Claude: versão ≥ 2.1.289 compatível somente se `--help` da versão instalada expõe todas as flags de isolamento (sem inferência, cache por versão); evidência atrelada à versão descoberta no início da sessão | implementado, aprovado |
| HB-C4-03 | Claude: catálogo restrito a `opus`, `sonnet`, `haiku` (apelidos dos modelos mais recentes); Fable e versões antigas fora | implementado, aprovado |
| HB-C4-04 | Validação real R15: um teste curto por CLI e uma missão mínima ponta a ponta | executado, passou |
| HB-C4-05 | Achado durante a validação: a Rainha Codex devolvia plano fora do formato (`project` como string, depois JSON malformado), que virava `job_failed`. Correção: prompt com o formato exato; saída estruturada `outputSchema` para plano e veredito (o Claude recebe o esquema no texto); `ValueError` ou JSON inválido → `planning_result_invalid`/`verdict_invalid` | implementado |


Evidência real C4 (`.test-tmp/hivemind-c4-r15/`, sem nenhum contorno do gate):

- `smoke-claude`: Claude 2.1.305, `sonnet`/`low`, gate apto, resposta `OK` (18,2 s).
- `smoke-codex`: Codex 0.160.0, `gpt-5.6-luna`/`low`, gate apto, resposta `OK` (9,2 s).
- `mission4`: missão `note.txt` com equipe mista e 3 turnos reais: Rainha Codex
  `gpt-5.6-luna`/`medium`, operária Claude `sonnet`/`low`, verificador Codex.
  Passou do plano à aprovação, workspace, operária, verificação, pacote,
  aprovação e aplicação. A origem terminou com `greeting=hello hive`, e a missão
  ficou `completed`.
- `mission`, `mission2` e `mission3`: tentativas anteriores, que falharam por
  plano inválido (motivo do HB-C4-05) e por assinatura do wrapper do harness.
- Turnos de diagnóstico gastos: Codex 7, Claude 2 (contagem conferida pelo verificador C4).

Suíte completa: `346 passed in 37.63s`. Manifesto: `manifesto-c4.sha256`.
**Veredito C4 (verificador Opus independente, `verificacao-c4.md`): APROVADO.**

- R01–R15 atendidos.
- Suíte `346 passed in 48.30s`.
- Manifesto 64/64 hashes no início e no fim.
- **A tarefa do backend HiveMind está concluída.**

Ressalvas não bloqueantes, levadas para a tarefa `2026-10-20_hivemind-escala-equipe` (EQ-11):

- **P2-a:** o perfil `:read-only` amplia a leitura caso exista alguma ferramenta
  nativa. A detecção de item nativo só acontece depois do efeito: não envia
  `turn/interrupt` e não encerra a árvore de processos.
- **P2-b:** a política `>= 2.1.289` do Claude não tem teto de major, e a
  presença das flags no `--help` não prova o comportamento de `--tools ""`.
- **P3-a:** o tipo `functionCallOutput` passa com qualquer nome; itens de outro
  `threadId` são ignorados; o perfil é conferido só pelo `id`.
- **P3-b:** a regex das flags aceita menção dentro da descrição de outra opção.
- **P3-c:** faltam testes de regressão para o vínculo de versão do Claude, a
  normalização de nulos, `verdict_invalid` e `functionCallOutput`.
- **P3-d:** `tests/fixtures/hivemind/fake_cli.py` está fora dos manifestos.
- **P3-e:** registros. O audit do harness marca `provider` errado; a contagem de
  turnos e o status da tabela foram corrigidos aqui.

### C3 — 20/10/2026 — veredito: PENDENTE DE VERIFICAÇÃO (teto atingido)

Verificador independente Opus 5.5, somente leitura (`verificacao-c3.md`).

- **Integridade:** manifesto C3 com 62/62 hashes conferidos no início e no fim.
- **Suíte:** `337 passed in 40.64s`.
- **Achados do C2:** HB-C2-01, HB-C2-02 e HB-C2-03 **corrigidos**, reproduzidos
  de forma independente. O escopo adicional de frontend foi atendido.
- **R01–R14:** nenhum falhou. As correções locais do C3 estariam aprovadas.
- **Bloqueio:** R15 (validação real com IA) segue **pendente necessário**, sem
  evidência real nova, e impede a aprovação global.
- **Ressalvas não bloqueantes (P3), detalhadas no relatório:**
  - Replay da reconciliação com revisão diferente não recusa com
    `idempotency_key_reused`.
  - Janela residual na barreira de fechamento: `hub_exit_ready` sem missões não
    marca `_closing`, e `heartbeat()` zera `_closing` sem lock.
  - O botão "Reconciliar origem" aparece em `recovery_required` e devolve um
    erro cru.
- **Doc:** `docs/frontend.md` (P3-c) foi corrigido pela sessão principal depois
  do veredito; é só texto, fora do manifesto.

**Ciclo 3/3 encerrado.** Pela §3.F não há quarto ciclo automático. Corrigir as
ressalvas P3 ou executar a validação real do R15 exige decisão explícita do
usuário. A tarefa não está concluída.

### C3 — 20/10/2026 — retomada no Claude Code (decisões do usuário)

A implementação C3 de 19/10 foi interrompida no meio: `missions.py`,
`scheduler.py` e `service.py` divergem do manifesto C2 sem testes novos, e
`service.py:451/468` chama assinaturas antigas de `missions.py` (TypeError;
5 testes Hive falham). O contador **não** é reiniciado: continua C3/3.

Decisões explícitas do usuário em 20/10/2026:

- **Modelos (substituição autorizada):** GPT Terra/Sol indisponíveis no Claude
  Code. Implementação por subagentes Sonnet 5.5 em lotes disjuntos, coordenados
  pela sessão principal Opus 5.5; verificação por subagente Opus 5.5 novo,
  contexto limpo, somente leitura, sem participação na implementação.
- **HB-C2-01 / regra de ciclos:** reautorizar um plano (idêntico ou novo) depois
  de reprovação no teto **consome um ciclo novo**; exige elevar o teto antes e é
  recusada antes de qualquer snapshot quando não houver ciclo disponível. Os
  testes C2 que esperavam ciclo preservado com hash novo passam a refletir esta
  decisão.
- **Escopo adicional aprovado no C3 (frontend):** cursor de eventos (`?after=`)
  além de 200; mensagem clara ao salvar equipe com modelo/esforço vazio; saída
  para `queen_configuration_changed` no chat; conferir o beacon de saída; textos
  obsoletos “backend pendente/ausente”.
- **Fora do C3:** paralelismo sem limite fixo, abelhas permanentes ricas, zoom e
  arrasto (tarefa nova com PRD próprio) e agentes pessoais (plano posterior).

| ID | Correção | Responsável | Status |
|---|---|---|---|
| HB-C3-01 | Reconciliação: chamadas com `operation_key`; intenção durável (`begin_reconciliation`) antes de qualquer cópia; replay devolve o resultado salvo; interrupção → recuperação explícita; boot com operação pendente → `recovery_required` | Sonnet backend | implementado, aguardando verificação |
| HB-C3-02 | Fechamento: reconciliação admitida conta como ativa; `_closing` bloqueia novas admissões; drenagem antes de `ready_to_exit` | Sonnet backend | implementado, aguardando verificação |
| HB-C3-03 | Reautorização no teto recusada antes do snapshot, sem `recovery_required` falso; nova tentativa consome ciclo | Sonnet backend | implementado, aguardando verificação |
| HB-C3-04 | Códigos sanitizados de falha de turno Claude; categorias de rede Codex com status preservadas | Sonnet backend | implementado, aguardando verificação |
| HB-C3-05 | Bugs de frontend listados acima | Sonnet frontend + sessão principal (`drawers.js:101`) | implementado, aguardando verificação |

Implementação C3 em 20/10/2026, sem nenhum CLI, login ou turno real de IA.

- **Backend:** `service.py`, `missions.py`, `store.py` (`command_result`, boot com
  reconciliação pendente), `adapters/claude.py` (`turn_error_code` com whitelist
  de subtypes e `api_error_<status>`) e `README.md`.
  - `_reconciling` foi removido.
  - `_closing` passa a ser zerado por `heartbeat()`: um HUD vivo depois de uma
    pausa por presença volta a admitir reconciliação, sem retomar nada.
  - A reconciliação interrompida se recupera em dois passos: `recover_delivery`
    e depois uma nova reconciliação com outra chave.
- **Frontend:**
  - `mission-state.js`: cursor `?after=`, até 500 eventos.
  - `live-drawers.js`: `validateTeam`, `chatQueen` e mensagens claras.
  - Textos obsoletos em `demo-data.js`, `drawers.js` e `HiveMind/__init__.py`.
  - Beacon comprovado em Chrome real num servidor temporário na porta 18791, sem
    alteração de código.
  - `tests/hivemind_browser_qa.mjs:50-51` ajustado ao novo aviso (harness fora do
    pytest, não executado).
- **Testes:**
  - Os 2 testes C2 de reautorização foram adaptados à decisão de ciclos.
  - Regressões novas cobrem replay limpo e com conflito, interrupção, boot,
    barreira de fechamento, recusa no teto antes do snapshot, códigos Claude e
    Codex, cursor de eventos, validação de equipe e beacon.
- **Suíte completa no estado integrado:** `337 passed in 40.44s`
  (`--basetemp=.test-tmp/hivemind-c3-integrado`).
- **Manifesto congelado:** `manifesto-c3.sha256`.
- **R15** continua pendente necessário; nada nesta implementação o cobre.

### C3 — 19/10/2026 — em implementação (último ciclo), interrompida

O verificador independente GPT-6.1 Sol high reprovou C2. Este ciclo corrige
somente: identidade durável de tentativa para reautorização do mesmo plano;
intenção, replay e recuperação explícita da reconciliação; admissão/drenagem
da reconciliação no fechamento; e códigos oficiais sanitizados para falhas de
turno Claude. C1/C2, seus históricos e R15 real permanecem preservados. Não há
inferência, login, descoberta ou leitura de históricos nesta correção.

### C2 — 19/10/2026 — aberto

O verificador independente GPT-6.1 Sol high reprovou C1 após uma suíte completa
verde (292 testes em 30,03 s). O relatório e os achados imutáveis estão em
`verificacao-c1.md` e `issues-c1.md`; C1 não foi apagado nem reclassificado.
O implementador C2 é GPT-5.6 Terra, esforço `high`. Estão abertas as correções
HB-C1-01 (identidade da geração), HB-C1-02 (reconciliação stale), HB-C1-03
(coordenação da Queen) e HB-C1-04 (limite por missão na UI). R15 continua
pendente e não autoriza novos smokes ou missões reais.

### C2 — correções implementadas, aguardando suíte completa

- **HB-C1-01:** jobs, dependências concluídas, tentativas, chaves pendentes e
  verificação agora carregam `plan_hash`. Um plano aprovado novo cria workspace
  novo, preserva o anterior em histórico e não reutiliza sucesso nem falha de
  tarefa de geração diferente. Job `unknown` impede novo plano até recuperação
  explícita; ciclo e histórico não são reiniciados.
- **HB-C1-02:** `reconcile_source` é um comando controlado e visível na missão.
  Ele cria snapshot/base/candidato separados, preserva o workspace e pacote
  antigos, reaplica apenas arquivos cuja origem ainda coincide com a base
  anterior e inicia verificação nova. Conflitos preservam ambos candidatos,
  listam os arquivos e mantêm `awaiting_user` com instrução para replanejar de
  modo consciente; a origem nunca é alterada por reconciliação.
- **HB-C1-03:** verdict guarda evidence. Em `correcting`, a Queen recebe o
  verdict completo, coordena sem editar e persiste feedback antes de qualquer
  worker poder reservar tarefa. Os workers recebem esse feedback, mas os paths,
  escopo e aprovações não mudam.
- **HB-C1-04:** o drawer da missão selecionada mostra e salva seu próprio teto
  de ciclos por `cycle_limit`; o comando existente mantém revisão, evento,
  limite mínimo do ciclo atual e não retoma trabalho.
- Testes concluídos durante C2: conjunto focado anterior 40 passou em 10,45 s;
  duas regressões finais de geração/Queen passaram em 0,94 s; reconciliação
  limpa, conflito preservador e controle de UI passaram em 0,86 s. Nenhuma IA
  foi chamada. A suíte completa controlada registrou 300 testes, 0 falhas e 0
  erros em 43,416 s no JUnit `.test-tmp/hivemind-c2-full.xml`. O manifesto C2
  está congelado em `manifesto-c2.sha256`; R15 permanece pendente e não é
  coberto por esse resultado.
