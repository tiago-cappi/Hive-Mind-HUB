# PRD — Hive Mind: escala da equipe e navegação da colmeia

> **Status em 21/10/2026: SUSPENSA, ciclo 0/3** — aguardando o usuário mandar iniciar; nada desta tarefa existe no código ainda. A referência do código atual está em `docs/hivemind/README.md`.

20/10/2026 · faixa completa · escopo aprovado pelo usuário por voz em 20/10/2026
("10 a 14 como tarefa nova com PRD próprio"), com os valores de limite delegados
à sessão principal. **Começa somente depois de encerrado o C3** da tarefa
`2026-10-19_hivemind-backend`. Ciclo **0/3** (não iniciado; suspenso em 20/10/2026; Claude e Codex destravados no C4 do backend no mesmo dia, início depende só do usuário).

Fluxo de modelos autorizado pelo usuário em 20/10/2026: implementação por
subagentes Sonnet 5.5 em lotes disjuntos, coordenação pela sessão principal
Opus 5.5, verificação por subagente Opus 5.5 limpo e somente leitura.

## Objetivo

1. A Rainha decide o que roda em paralelo e o que roda em sequência, sem o teto
   fixo de duas operárias, protegido por limites de segurança de franquia e RAM
   adequados a PCs modestos.
2. Abelhas temporárias pertencem à missão e somem da colmeia ao final; abelhas
   permanentes são cadastradas pelo usuário com descrição, skills e ferramentas.
3. A colmeia mostra qualquer quantidade de abelhas, com zoom e arrasto.

## Decisões tomadas pela sessão principal (delegadas pelo usuário)

| ID | Decisão | Motivo |
|---|---|---|
| D1 | Limite global de trabalhos simultâneos (operárias + subagentes + verificador) **padrão 4**, ajustável pelo usuário de **1 a 8**; teto 8 fixo em código. A Rainha continua em slot próprio de coordenação. Substitui o padrão 2 de R05 do PRD do backend. | Cada CLI real consome de ~0,3 a 0,6 GB de RAM e franquia por turno; 4 cabe em PC de 8 GB com o Hub e o navegador; 8 evita que um erro da Rainha dispare dezenas de agentes. |
| D2 | **Guarda de memória:** antes de cada despacho, ler a memória física disponível (Windows `GlobalMemoryStatusEx`, sem dependência nova). Abaixo de **1,5 GB** livres, o trabalho espera na fila com motivo visível `memory_low`; leitura indisponível bloqueia com `memory_unverified`. Esperar não falha, não pausa e não consome ciclo. | Proteção determinística em código, não em prompt (§6.2). |
| D3 | **Limites do plano:** no máximo **12 abelhas** por plano (incluindo Rainha e verificador), das quais no máximo **8 temporárias**, e no máximo **40 tarefas**. Excesso → erro explícito `plan_too_large`. | Barreira contra a Rainha errar e invocar agentes demais. |
| D4 | **Paralelismo decidido pela Rainha:** tarefas com arquivos sobrepostos já exigem dependência explícita. Novo campo opcional `resources` por tarefa (rótulos como `deps`, `db`, `build`): tarefas que compartilham um rótulo nunca rodam ao mesmo tempo (exclusão mútua no scheduler, `resources_busy`), mesmo com arquivos diferentes. Tudo o que não depende nem compartilha arquivo ou recurso pode rodar em paralelo até o limite D1/D2. | Cobre os "outros casos" além de arquivos diferentes (instalação de dependências, banco, build, testes globais). |
| D5 | **Abelhas temporárias:** saem da colmeia e da equipe ativa em qualquer encerramento da missão (concluída, falha terminal, plano substituído). O registro histórico (eventos, jobs, planos, resultados e uso conhecido) permanece na missão. A Rainha deve preferir abelhas permanentes cuja descrição, skills e ferramentas se encaixem e criar temporárias só quando nenhuma servir. | Pedido do usuário; histórico preservado conforme R04. |
| D6 | **Skills nesta tarefa são declarativas:** tags e instruções que a Rainha usa para escolher abelhas e que entram no prompt da abelha. **Não** habilitam skills, MCP ou plugins dos CLIs, que continuam desligados pela política comprovada no P0. Skills executáveis e conectores pertencem ao plano de agentes pessoais. | Preserva o enforcement de R06/R15 sem nova prova de segurança. |
| D7 | **Ferramentas por abelha:** subconjunto do catálogo de capacidades existente (`read`, `patch`, `checks`). O broker recusa ferramenta fora da lista da abelha. O verificador nunca recebe `patch`. | Restrição real em código, já suportada pelo broker. |

## Requisitos e critérios de aceite

| ID | Requisito | Critério verificável |
|---|---|---|
| E01 | Limite global D1 | Padrão 4 em banco novo; banco existente que ainda tem o padrão antigo 2 nunca alterado pelo usuário (revisão 0) passa a 4 uma única vez; valores fora de 1–8 são rejeitados na API e na UI. Teste conta jobs reais simultâneos ≤ limite, inclusive com falha e reconexão. |
| E02 | Guarda de memória D2 | Com leitura simulada < 1,5 GB, nenhum job novo é reservado e o motivo `memory_low` aparece no estado/evento, uma vez por transição; ao liberar memória, o despacho continua sem ação do usuário e sem consumir ciclo. Leitura que falha → `memory_unverified`, sem despacho. |
| E03 | Limites do plano D3 | Plano com 13 abelhas, 9 temporárias ou 41 tarefas → `plan_too_large`, sem mudar estado. Limites exatos aceitos. |
| E04 | Paralelismo D4 | Tarefas independentes com arquivos e recursos disjuntos rodam em paralelo até o limite; tarefas com o mesmo `resources` nunca ficam ativas juntas (teste com barreira); `resources` inválido → erro de plano. O prompt da Rainha descreve como declarar dependências e recursos. |
| E05 | Temporárias D5 | Ao concluir, falhar de forma terminal ou substituir o plano, as temporárias ficam inativas, não aparecem na colmeia nem na equipe, e continuam no histórico da missão (consultável na gaveta da missão). Teste por estado terminal. |
| E06 | Cadastro de permanentes D6/D7 | Abelha permanente tem `id`, `name`, `role`, `description` (obrigatória, ≤ 2000), `skills` (≤ 20 tags de até 60 caracteres), `tools` (subconjunto válido; verificador sem `patch`), `provider`, `model`, `effort`. Cadastro antigo sem os campos novos é carregado como **incompleto**; planejamento com equipe incompleta → `roster_incomplete` com a abelha indicada. Rainha recebe descrição/skills/tools da equipe no prompt. |
| E07 | Ferramentas por abelha | Job de abelha sem `checks` (ou `patch`) recebe recusa do broker para essa ferramenta; teste em fixture sem CLI real. |
| E08 | Gaveta Equipe | Formulário para criar/editar/remover permanentes com os campos de E06, validação na tela com mensagem clara por campo, e salvamento por revisão/idempotência existentes. Temporárias aparecem só durante a missão, marcadas como temporárias, sem edição. |
| E09 | Layout dinâmico | A colmeia posiciona qualquer número de abelhas (testado com 1, 8, 12 e 40 nós sintéticos) em anéis hexagonais ao redor da Rainha, sem sobreposição, com rotas válidas. As 8 primeiras posições de operárias e as 2 de subagentes ficam idênticas às atuais (visual aprovado no C7 preservado). |
| E10 | Zoom e arrasto | Botões `+`, `−` e `Ajustar`; roda do mouse com zoom centrado no cursor; arrastar com mouse ou toque em área vazia; teclado (`+`, `−`, `0`, setas) com a colmeia focada. Zoom de 0,25× a 2×. Clique em abelha ou rota continua funcionando (arrasto só a partir de 4 px). Ajuste automático quando a quantidade de abelhas muda, até o usuário mover manualmente; `Ajustar` volta ao automático. Sem transições animadas com "reduzir movimento". Funciona no modo real e no demo. |
| E11 | Regressão | Suíte completa verde; demo, gavetas, navegação entre Hive/Claude/Codex, minimizar sem pausar, `MAX_SESS`/`MAX_TABS`, `SPEAK_Q` e mobile intactos; nenhum toque em `server.py`/`index.html`. |
| E13 | Ressalvas P3 do C3 do backend (incluídas por decisão do usuário em 20/10/2026; ver `2026-10-19_hivemind-backend/verificacao-c3.md`) | (a) Repetir `reconcile_source` com a mesma chave e outra revisão → `idempotency_key_reused`, como os demais comandos. (b) Fechamento sem janela: `hub_exit_ready()`/`ready_to_exit()` que sinalizam saída marcam `_closing` antes de responder `True`, e `heartbeat()` só zera `_closing` sob `_reconcile_lock` e nunca durante uma drenagem em curso; teste com barreira prova que nenhuma reconciliação é admitida depois do sinal de saída nem durante a drenagem. (c) Em `recovery_required`, a gaveta Missão não oferece "Reconciliar origem" enquanto a recuperação não for feita; códigos `closing`, `reconciliation_in_progress`, `recovery_required` e `cycle_limit_reached` aparecem como mensagens claras. |
| E14 | Endurecimento dos adaptadores (ressalvas P2/P3 do C4 do backend, `2026-10-19_hivemind-backend/verificacao-c4.md`) | Item nativo inesperado no Codex interrompe o turno e encerra a árvore de processos do job; Claude com major ≥ 3 ou flag não declarada como opção → `version_unverified`; `functionCallOutput` fora do broker e item de outro thread → `native_tool_unexpected`; perfil ativo `:read-only` sem `extends` inesperado; testes cobrem cada caso. Smoke real só se o usuário autorizar. |
| E12 | Documentação | `HiveMind/backend/README.md` e a seção Hive de `docs/runtime.md` descrevem limites, guarda de memória, recursos, temporárias e cadastro; o frontend descreve zoom/arrasto onde a página é documentada. |

## Fora do escopo

Página de agentes pessoais e proatividade (ver
`docs/hivemind/ideias/agentes-pessoais.md`), conectores novos,
skills/MCP executáveis nos CLIs, mudança de providers do Hub, acesso remoto,
redesenho visual além de controles de zoom e novas posições na malha, e
qualquer validação real com IA além do que o usuário autorizar à parte.
