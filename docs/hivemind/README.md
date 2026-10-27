# Hive Mind — índice

Atualizado em 26/10/2026 · descreve o código atual; o que é planejado fica em
[roadmap.md](roadmap.md).

A Hive Mind é a terceira página do Hub (ao lado de Claude Code e Codex): uma
equipe de abelhas de IA que executa missões de software em projetos locais. A
**Rainha** conversa com você e propõe plano e equipe; você aprova; **operárias**
e **subagentes** trabalham numa cópia isolada do projeto; um **verificador
independente** avalia; você aprova o pacote final, que é aplicado na origem com
backup e rollback. Cada abelha roda num CLI real, Claude Code ou Codex, com
modelo e esforço escolhidos por você.

## Comece por aqui

1. Este índice (recursos, encaixes, regras).
2. O documento da parte que você vai mexer: [backend.md](backend.md),
   [adaptadores.md](adaptadores.md) ou [frontend.md](frontend.md).
3. [testes.md](testes.md) antes de validar.
4. [roadmap.md](roadmap.md) para saber o que ainda **não** existe.
5. Processo de desenvolvimento do Hub: `docs/desenvolvimento.md`.

## Recursos que existem hoje

| Recurso | Resumo | Detalhe |
|---|---|---|
| Página no Hub | Aba HIVE MIND no modo minimalista, montada dentro de `/` (sem URL própria) | [frontend.md](frontend.md) |
| Modo real × demonstração | Real é o padrão e controla missões, com o mesmo visual do protótipo e da demonstração; a demonstração é simulada e nunca toca o backend de missões | [frontend.md](frontend.md) |
| Colmeia 2D | Rainha no centro e 8 posições fixas para os demais integrantes no modo real (a demonstração tem mais 2 de subagentes); uma célula por abelha da missão, inclusive as temporárias que a Rainha criou; estados (`coord`, `working`, `waiting`, `approval`, `done`, `failed`), anel de progresso e rotas com estado vindos do backend; abelhas animadas | [frontend.md](frontend.md) |
| HUD | "Missão real" com sete hexágonos (Planejamento, Aprovação do plano, Execução, Verificação, Aprovação da entrega, Incorporação, Concluída), botão que segue o estado (Ver aprovação, Iniciar, Pausar, Retomar, Ver entrega) e banner de aprovação ou falha | [frontend.md](frontend.md) |
| Gavetas | **Agentes** (lista com estado e progresso, detalhe com abas Visão geral, Tarefas, Skills, Ferramentas e Relações, cadastro rico de abelha), **Missão** (Andamento, Aprovações, abas Plano, Responsabilidades, Conexões e Entrega, criar missão, ciclos) e **Conversa** (chat com a Rainha); abas puxadoras com contador; popup de entrega | [frontend.md](frontend.md) |
| Cadastro de abelha | Descrição, skills declarativas (tags e instruções), ferramentas (`read`, `patch`, `checks`; Rainha e verificador sem `patch`), provedor, modelo e esforço; cadastro antigo vira "incompleto" e bloqueia o planejamento (`roster_incomplete`) | [backend.md](backend.md) |
| Progresso e resumo por abelha | Operação `progress {done, total, note}` do broker (evento `bee_progress`) e `bees_summary` em `GET /missions/<id>` (tarefas, progresso, ferramentas usadas, último job) | [backend.md](backend.md) |
| API local `/hive-api` | Status, catálogo, configurações, presença, missões, lease e comandos; só aceita origem local | [backend.md](backend.md) |
| Missões | Máquina de estados do pedido à entrega, comandos idempotentes (chave + revisão), eventos duráveis em SQLite | [backend.md](backend.md) |
| Plano da Rainha | Saída estruturada validada por `validate_plan`; aprovação presa ao hash do plano | [backend.md](backend.md) |
| Ciclos | Verificador reprova → correção, até o teto (padrão 3); reautorizar consome ciclo | [backend.md](backend.md) |
| Encerrar missão | Missão travada em `recovery_required` pode ser encerrada (`abandon` → `abandoned`), com histórico preservado e origem intocada | [backend.md](backend.md) |
| Mensagens | Erros, motivos de falha e estados aparecem em português com o código entre parênteses (`messages.js`) | [frontend.md](frontend.md) |
| Isolamento | Snapshot do projeto; abelhas só usam as ferramentas do broker do job (as do cadastro dela entre `read`, `patch`, `checks`, mais `progress`); o resto é recusado com `tool_not_allowed` | [backend.md](backend.md), [adaptadores.md](adaptadores.md) |
| Entrega | Journal, backup no mesmo volume, quarentena, rollback, `recovery_required` | [backend.md](backend.md) |
| Reconciliação | Origem alterada durante a missão → nova cópia com reaplicação das mudanças | [backend.md](backend.md) |
| Ciclo de vida | Presença da tela, pausa com drenagem, Hub só fecha quando a Hive libera | [backend.md](backend.md) |
| Limite de simultâneos | Padrão 2 trabalhos ao mesmo tempo (operárias + subagentes + verificador); Rainha à parte | [backend.md](backend.md) |
| Claude e Codex | Sessões só-modelo com isolamento comprovado, gate antes de cada despacho, sem fallback silencioso | [adaptadores.md](adaptadores.md) |

## Mapa de pastas

| Caminho | Conteúdo |
|---|---|
| `HiveMind/backend/` | Backend Python (blueprint `/hive-api`, serviço, missões, adaptadores) |
| `HiveMind/frontend/` | Blueprint estático `/hive-ui/static` e módulos JS/CSS da página |
| `HiveMind/prototipo/` | Protótipo HTML de referência visual (não é servido pelo Hub) |
| `HiveMind/state/` | Estado em execução (SQLite, workspaces, journal); criado sob demanda, não versionar |
| `tests/test_hivemind_*.py`, `tests/hivemind_*.mjs`, `tests/fixtures/hivemind/`, `tests/fixtures/hivemind_real_*.json` | Testes ([testes.md](testes.md)); os JSON são as respostas falsas do `/hive-api` usadas pelo comparador visual e pelo teste de estouro |
| `docs/hivemind/` | Esta referência viva |
| `docs/hivemind/ideias/` | Ideias registradas que ainda não são tarefa |
| `docs/planos/*hivemind*` | Registros de processo (PRD, plano, issues, verificação) de cada tarefa |
| `.qa-arquivo/` | Capturas antigas de QA visual (fora de `docs/`) |

## Encaixes no Hub (não mexer além disto)

| Arquivo | Encaixe |
|---|---|
| `server.py` | import dos dois blueprints, `app.register_blueprint` de ambos e a chamada a `HiveMind.backend.manager.hub_exit_ready()` no watchdog de saída |
| `index.html` | só a tag `<script type="module" src="/hive-ui/static/app.js">` |
| `codex_frontend/static/providers.js` | botão `data-page="hive"` na navegação e `hubProviders.registerPage` (a página Hive depende disso) |
| `hub_runtime/assistant.py` | desvio `--hivemind` para o launcher (`HiveMind/backend/adapters/launcher.py`), carregado como `_hivemind_launcher` a partir da geração de runtime quando a sessão roda numa cópia da geração |

`server.py` e `index.html` não são refatorados (regra 11 do `CLAUDE.md`). A ponte
fica em `127.0.0.1` e o `/hive-api` recusa qualquer origem que não seja local. O
celular (`mobile/`) não expõe a Hive Mind.

## Regras para quem desenvolve

- **Esta pasta descreve só o que está no código.** Recurso planejado aparece
  apenas no [roadmap.md](roadmap.md) ou no PRD da tarefa, marcado como planejado.
- **Mudou o código, atualize o documento correspondente no mesmo lote.** O
  verificador confere a documentação contra o código.
- **`docs/planos/` é histórico.** PRDs, planos e verificações registram intenções
  e ciclos daquele momento; o status no topo de cada arquivo diz se a tarefa está
  concluída, ativa ou suspensa. Em conflito, vale o código e esta pasta.
- **Turnos reais de IA só com autorização do usuário** (consomem franquia).
  Subagentes e verificadores não rodam turnos reais nem tocam a porta 8765 sem
  essa autorização.
- Sem chaves de API, login, instalação ou atualização de CLIs pelo Hive; nunca
  ler ou copiar tokens ou credenciais.

## Limitações conhecidas do código atual

Encontradas na auditoria de 21/10/2026; as que ainda valem estão abaixo (a tarefa
de escala trata as marcadas no [roadmap.md](roadmap.md)).

- `resume` só vale em `paused`; após uma falha de trabalho a missão vai a
  `awaiting_user` e segue por conversa com a Rainha ou novo plano (a gaveta Missão
  orienta isso).
- `delivery_recovery_ambiguous` (a reversão não confirmou todos os arquivos) não tem
  saída pela interface: exige intervenção manual, pois a origem pode estar alterada
  (os artefatos ficam preservados no journal) e `abandon` é recusado enquanto o
  journal tiver `attempted: true`.
- Journal de entrega ilegível, corrompido ou acima de 10 MiB após uma aplicação:
  `recover_delivery` devolve `delivery_journal_unverified` e `abandon` é recusado;
  exige intervenção manual (só ocorre com corrupção externa ou entregas enormes).
- Depois de `recover_delivery`, aplicar de novo a mesma entrega (mesmo `delivery_hash`)
  é recusado com `delivery_recovery_required`, porque o diretório do journal já existe;
  é preciso gerar outra entrega (novo candidato e nova verificação).
- `checks` depende do runner restrito do Codex: sem o Codex instalado, `checks`
  falha com `restricted_runner_unavailable`, mesmo em equipe só com Claude.
- `checks` só lê, além de `:minimal`, do candidato e do scratch, a pasta do programa
  (nome puro, encontrado no `PATH`) e o ambiente virtual dele. Um programa fora de
  `:minimal` chamado por caminho ou instalado em pasta barrada (ex.: direto em
  `AppData\Local`) não inicia (código 127), nem um venv de dentro do candidato; o
  Python da Microsoft Store também não. Cada check tem teto de 600 s (código 124).
- Um `AGENTS.md` global em `CODEX_HOME` (ou instruções/provedor customizados)
  aborta toda sessão Codex com `context_unverified` (motivo mostrado na gaveta Missão).
- Nada apaga workspaces, journals, gerações de runtime ou worktrees usados.
- O plano não tem teto de abelhas ou tarefas (planejado em [roadmap.md](roadmap.md)).
- `playwright` e `sharp` não estão instalados no projeto: os testes de navegador exigem
  um `NODE_PATH` apontando para outra pasta que os tenha ([testes.md](testes.md)).
  `tests/hivemind_visual_compare.mjs` (demonstração e modo real contra o protótipo) e
  `tests/hivemind_overflow.mjs` (estouro) e `tests/hivemind_browser_qa.mjs` (QA da aba no
  Hub, abre a demonstração por `.hm-mode`) funcionam.

Detalhes em [backend.md](backend.md), [adaptadores.md](adaptadores.md) e [frontend.md](frontend.md).

## Não existe mais (não confie em textos antigos)

- "A página Hive é só demonstração e não usa IA": falso desde o backend; o modo
  real é o padrão.
- A gaveta "Equipe" com formulário cru, JSON cru na gaveta Missão, abas puxadoras sem estilo
  e as classes `hm-live-*` do primeiro modo real: substituídas em 26/10/2026 pelas gavetas
  "Agentes", "Missão" e "Conversa" no estilo do protótipo.
- A altura mínima de 760 px da página e o limite fixo `read`, `patch`, `checks` do broker
  para todas as abelhas: hoje são 560 px e as ferramentas do cadastro de cada abelha.
- Perfil customizado de permissões do Codex (`hivemind-isolated`): removido; o
  Codex usa o perfil embutido `:read-only`.
- Versão exata fixa do Claude: substituída por versão mínima e prova das flags
  no `--help`.
- Modelo Fable e nomes completos de modelos Claude no catálogo: só `opus`,
  `sonnet` e `haiku`.
- `HiveMind/backend/README.md` como referência: virou ponteiro para esta pasta.
- `docs/planos/roadmap-hivemind.md` e `docs/planos/2026-10-20_hivemind-agentes-pessoais/`:
  movidos para [roadmap.md](roadmap.md) e [ideias/](ideias/agentes-pessoais.md).
- Capturas de QA em `docs/planos/2026-10-10_hivemind-frontend-hub/qa*`: movidas
  para `.qa-arquivo/2026-10-10_hivemind-frontend-hub/`.
