# PRD — Hive Mind: modo real com o visual do protótipo

> **Status em 26/10/2026: CICLO 3 EM ANDAMENTO** · faixa completa · plano aprovado pelo usuário em 26/10/2026, com autorização de uma missão real pela interface para a validação final.

## Contexto

O protótipo aprovado (`HiveMind/prototipo/Hive Mind.dc.html`) foi trazido em 10–13/10/2026
só para o **modo demonstração** (`drawers.js`, `simulation.js`). O **modo real**, padrão
desde 21/10/2026, foi construído depois só para funcionar (`live-drawers.js`): formulários
crus, JSON bruto, abas puxadoras sem estilo e nenhum dos componentes do protótipo. O
usuário esperava o modo real idêntico ao protótipo (pergunta de 25/10/2026).

Prints de 25/10/2026 (janela 1396×612):
- a demonstração reproduz o protótipo, com a única diferença do rig PNG das abelhas;
- o modo real não usa nenhum componente do protótipo, embora todas as classes já existam
  em `hive.css`;
- estouros: abas puxadoras "Equipe"/"Missão" com 38 px e texto horizontal cortado,
  sobrepostas à gaveta Conversa; hash e JSON cru na gaveta Missão; mensagem da Conversa
  com 683 px de conteúdo em 559 px;
- os campos Modelo e Esforço ficam vazios com a equipe salva até "Consultar modelos";
- `.hm-page` tem `min-height:760px`, então a Conversa fica cortada em janelas baixas;
- na colmeia real só existem os estados "Disponível" e "Trabalhando"; não há etapas no
  HUD, banner de aprovação, progresso nem rotas com estado.

## Objetivo

O modo real fica **visualmente idêntico ao protótipo**: mesmos componentes, sombras,
animações e comportamento das gavetas, HUD, colmeia e painel de entrega. Ele mostra só
dados reais e ganha no backend os dados que o protótipo exibe e que hoje não existem.

## Decisões do usuário (25/10/2026)

| ID | Decisão |
|---|---|
| D1 | Funções reais sem tela no protótipo usam o **vocabulário do protótipo**. Equipe: lista Agentes + detalhe com abas + formulário no estilo "Criar operária". Criar missão: cartão na gaveta Missão. Aprovações: cartão "Aprovações" + banner no mapa. Entrega: popup de entrega. |
| D2 | **Colmeia:** cada abelha da missão ganha sua célula: as permanentes que o usuário criou e as temporárias que a Rainha criou no plano. A Rainha fica no centro, em destaque, com todas as animações do protótipo: borda tracejada girando, rotas com setas e pulsos, varredura e ondas da Rainha, anel de progresso. O **HUD** mostra 7 hexágonos com as etapas reais da missão. |
| D3 | **Criar dados novos no backend:** descrição, skills e ferramentas por abelha (antes no EQ-04 da escala) e progresso fino informado pela própria abelha. |
| D4 | **Rig PNG das abelhas mantido**, a única exceção ao "idêntico" (decisão de 10/10/2026). |
| D5 | **Esta tarefa vem antes da escala.** Ela absorve o EQ-12 inteiro (F1, F3, F4, F7), o EQ-04 (E06, E07) e a parte de cadastro do EQ-07 (E08). A escala continua com limites, paralelismo, encerramento das temporárias, anéis e zoom. |
| D6 | Skills são **declarativas** (como D6 da escala): tags e instruções que a Rainha usa para escolher abelhas e que entram no prompt da abelha. Não habilitam skills, MCP ou plugins dos CLIs. |

## Requisitos e critérios de aceite

### Frontend — modo real

| ID | Requisito | Critério de aceite verificável |
|---|---|---|
| V01 | **Gaveta Equipe = gaveta "Agentes" do protótipo** | Usa o mesmo cabeçalho escuro com contadores de trabalhando, aguardando, disponíveis e entregues. As linhas têm ícone da abelha, papel, estado, progresso `x/y` e ícone de estado; temporárias levam a marca "TEMPORÁRIA". O detalhe tem as abas Visão geral, Tarefas, Skills, Ferramentas e Relações, com as mesmas classes `hm-agent-*`, `hm-tabs`, `hm-detail-*` e `hm-tool*` da demonstração. A Rainha tem as abas do protótipo para ela. Provedor, modelo e esforço ficam editáveis em Visão geral só nas permanentes; temporárias são somente leitura. O formulário de criar e editar segue o estilo "Criar operária" e cobre os campos de B01, com erro por campo. "Excluir agente" existe só para operária permanente. Modelo e esforço salvos aparecem mesmo antes de consultar o catálogo. "Consultar modelos" mostra carregamento (F1). |
| V02 | **Gaveta Missão = gaveta "Missão" do protótipo** | **Cabeçalho escuro:** título; objetivo; linha de limites com projeto e máximo de ciclos; selo de estado no lugar de "Execução simulada". **"Andamento":** 7 segmentos das etapas reais (V05), frase do estado e botões de ação no estilo do protótipo (`hm-dark`/`hm-outline`). **Cartão "Aprovações":** plano ou entrega pendente com "Aprovar" e "Solicitar ajuste"; o ajuste abre a Conversa. **Abas:** Plano (tarefas com ✓, ● e ☐ e a abelha dona), Responsabilidades (tarefas por abelha), Conexões (rotas e legenda) e Entrega (veredito por critério, arquivos alterados e fora do plano, "Incorporar"). **Nenhum JSON cru**; hashes abreviados (8 caracteres) com cópia completa no `title`. **Criar missão:** cartão no estilo do protótipo quando não há missão ou por "Nova missão"; os campos limpam após criar (F7). **Avisos especiais** (recuperação, encerrar com confirmação, reconciliar, interrupção, limite de ciclos) no estilo `hm-approval`, preservando os comportamentos atuais (`frontend.md` §4). |
| V03 | **Conversa = gaveta "Conversa" do protótipo** | Usa `hm-chat-head`, `hm-chat-log` (balões `hm-chat-user` e `hm-chat-event`) e `hm-chat-form` com "Enviar para a Rainha". Textos longos quebram dentro do balão. As regras de habilitação atuais são mantidas. |
| V04 | **Abas puxadoras e botões** | As abas são idênticas às da demonstração: ícone, contador (`n` agentes; `etapa/7` na Missão) e seta (F3). Botões só com `hm-dark` e `hm-outline` (F4). Nenhuma aba fica sobre outra gaveta aberta. |
| V05 | **HUD com etapas reais** | Formato "MISSÃO REAL ⬢⬢⬡⬡⬡⬡⬡ Etapa n de 7 · Nome [ação]", com as mesmas classes e animação de preenchimento dos passos do protótipo. Etapas: 1 Planejamento (`clarifying`, `planning`), 2 Aprovação do plano (`awaiting_plan_approval`, `ready`), 3 Execução (`running`, `correcting`), 4 Verificação (`verifying`), 5 Aprovação da entrega (`awaiting_delivery_approval`), 6 Incorporação (`delivery_approved`, aplicação, `recovery_required`), 7 Concluída (`completed`). `paused`, `awaiting_user` e falha mostram a etapa onde pararam, com o estilo de espera ou falha do protótipo. O botão do HUD segue o estado: Aprovar plano, Iniciar, Pausar, Retomar, Ver entrega ou Ver aprovação. Com aprovação pendente aparece o banner do mapa (`hm-hud-alert`) com "Ver aprovação". |
| V06 | **Colmeia real animada** | **Células:** uma por abelha ativa da missão (plano; sem plano, equipe salva), Rainha no centro com polígono preto, varredura e ondas. **Estados** derivados do backend: `coord` (Rainha com job), `working` (job rodando), `waiting` (tarefa com dependência pendente), `approval` (Rainha em aprovação pendente), `done` (tarefas da abelha concluídas), `failed` (último job da abelha falhou). Mostra o anel de progresso e o texto "x de y" da abelha (B03/B04). **Rotas** Rainha→abelha e entre tarefas dependentes, com os estados do protótipo (`out`, `del`, `wait`, `in`, `done`, `fail`, `idle`) derivados de jobs e tarefas. **Temporárias** com a marca do protótipo para célula adicionada. Teto atual: Rainha + 8 (anéis ficam na escala). Movimento reduzido continua desligando tudo. |
| V07 | **Painel de entrega** | O popup `hm-delivery` do protótipo abre em "Ver entrega" com dados reais: resumo, veredito, critérios e arquivos alterados. Aprovar e incorporar ficam ali e na gaveta. `Esc` fecha. |
| V08 | **Sem estouro** | Em 1280×720 e 1920×1080, nenhum elemento das gavetas, HUD ou popup tem conteúdo maior que a caixa sem rolagem própria. Teste automatizado com `scrollWidth`/`getBoundingClientRect` e textos longos de fixture. Com altura ≥ 600 px, a Conversa aberta fica inteira visível. |
| V09 | **Fidelidade visual medida** | `tests/hivemind_visual_compare.mjs` ganha casos do modo real com `/hive-api` falso (fixture) comparados com o protótipo nos componentes equivalentes: gavetas, HUD, abas puxadoras, células e popup. A tolerância de pixel é a mesma do ciclo 7, com animações congeladas e o rig PNG mascarado. A demonstração continua passando no comparador atual, sem regressão. |

### Backend — dados novos

| ID | Requisito | Critério de aceite verificável |
|---|---|---|
| B01 | **Cadastro rico de abelha** (E06 da escala) | Abelha permanente tem `id`, `role`, `description` (obrigatória, ≤ 2000), `skills` (≤ 20 tags de até 60 caracteres, mais `instructions` opcional ≤ 4000), `tools` (subconjunto de `read`, `patch`, `checks`; verificador sem `patch`), `provider`, `model`, `effort`, `temporary`. Cadastro antigo sem os campos carrega como **incompleto**. Planejar com equipe incompleta dá `roster_incomplete` indicando a abelha. Temporárias do plano têm os mesmos campos, validados no plano. Testes de store, rotas e plano. |
| B02 | **Ferramentas por abelha** (E07) | O broker de cada job recebe só as ferramentas da abelha; ferramenta fora da lista dá recusa `tool_not_allowed`. Teste com fixture, sem CLI real. |
| B03 | **Progresso fino** | Nova operação do broker `progress {done, total, note}`, disponível a operárias, subagentes e verificador. `done` e `total` são inteiros com `0 ≤ done ≤ total ≤ 100000`; `note` tem até 200 caracteres e é texto puro. Cada chamada grava o evento `bee_progress` com job, abelha e valores e não altera arquivos. O prompt das abelhas explica quando usar. Argumento inválido é recusado sem derrubar o job. Testes de broker e de serviço. |
| B04 | **Resumo por abelha na API** | `GET /missions/<id>` devolve `bees_summary` com uma entrada por abelha ativa: `id`, `role`, `temporary`, `description`, `skills`, `tools`, tarefas (`total`, `done`, `current`), último `progress`, contagem de ferramentas usadas por nome, último estado de job e ciclo. O resumo é calculado no backend a partir de plano, jobs e eventos, sem depender do limite de 500 eventos do front. Teste de rota. |
| B05 | **Rainha e abelhas recebem o cadastro** | O prompt de planejamento leva descrição, skills e ferramentas da equipe e instrui a Rainha a preferir permanentes adequadas e a criar temporárias completas. O prompt de cada abelha leva sua descrição e as instruções das skills. Testes de prompt com fake. |
| B06 | **Compatibilidade e documentação** | `docs/hivemind/{backend,frontend,testes,roadmap,README}.md` atualizados. Os códigos novos têm frase em `messages.js`, exigida pelo teste existente. A suíte completa passa. Missões antigas, sem `bees_summary` de origem, abrem sem erro. |

## Fora de escopo

- Itens da escala que ficam lá: limites 1–8 e memória (E01, E02), limites do plano e
  `resources` (E03, E04), encerramento das temporárias (E05), anéis, zoom e arrasto
  (E09, E10).
- Trocar o rig PNG por ícone vetorial (D4).
- Mudar `server.py`, `index.html` ou `providers.js` além dos encaixes atuais.
- Skills ou MCP executáveis nos CLIs (D6).
- Turnos reais de IA sem autorização expressa do usuário. A validação usa fixtures e
  fakes; uma missão real pela interface só com autorização à parte.
- Mudar a demonstração, exceto para extrair componentes compartilhados sem mudar o
  visual, conferido pelo comparador.

## Esclarecimento de aceite V02 — 26/10/2026 (retomada Codex)

O usuário confirmou explicitamente nesta conversa: **manter Solicitar ajuste apenas na aprovação do plano; na entrega, permitir aprovar e incorporar**. Assim, a menção genérica a Solicitar ajuste em V02 aplica-se ao cartão do plano. A entrega preserva o fluxo já implementado e documentado em VR-06; não é necessário ampliar a máquina de estados do backend para concluir esta tarefa.
