# Issues — Hive Mind: modo real com o visual do protótipo

> **Status em 26/10/2026: CICLO 3 EM ANDAMENTO** · faixa completa · plano aprovado pelo usuário em 26/10/2026, com autorização de uma missão real pela interface para a validação final.

| ID | Requisitos | Lote | Dependência | Responsável | Status |
|---|---|---|---|---|---|
| VR-01 | B01 — cadastro rico, incompleto, `roster_incomplete`, temporárias completas no plano | L1 | aprovação | Implementador A | implementado no C1 (26/10/2026), aguardando verificação. Decisão: Rainha e verificador nunca têm `patch` |
| VR-02 | B02, B03 — ferramentas por abelha no broker, operação `progress` e evento `bee_progress` | L1 | VR-01 | Implementador A | implementado no C1 (26/10/2026), aguardando verificação |
| VR-03 | B04, B05 — `bees_summary` na rota da missão e prompts da Rainha e das abelhas com o cadastro | L1 | VR-01, VR-02 | Implementador A | implementado no C1 (26/10/2026), aguardando verificação. Pendência para L4: `docs/hivemind/adaptadores.md` (ferramentas filtradas pelo broker e `progress`) |
| VR-04 | V05, V06 — snapshot real (etapas, estados, rotas, progresso, temporárias), HUD com etapas e banner, colmeia animada | L2 | contrato do plano | Implementador B | implementado no C1 (26/10/2026), aguardando verificação. Decisões do orquestrador: Rainha em `coord` enquanto qualquer abelha executa; HUD não aprova direto ("Ver aprovação" abre o cartão da gaveta) |
| VR-05 | V01, V04 — gaveta Equipe no estilo "Agentes", abas puxadoras e botões (F1, F3, F4) | L3 | VR-04 | Implementador B | implementado no C1 (26/10/2026), aguardando verificação. A gaveta passou a se chamar "Agentes", como no protótipo; equipe vazia ganha rascunho com seletor de papel |
| VR-06 | V02, V07 — gaveta Missão no estilo do protótipo, criação de missão (F7), avisos especiais, painel de entrega | L3 | VR-04 | Implementador B | implementado no C1 (26/10/2026), aguardando verificação. Desvio justificado: o cartão de entrega não tem "Solicitar ajuste", porque o backend não aceita mensagem à Rainha em `awaiting_delivery_approval` |
| VR-07 | V03, V08 — Conversa no estilo do protótipo e nenhum estouro | L3 | VR-04 | Implementador B | implementado no C1 (26/10/2026), aguardando verificação. Revisão do orquestrador nos prints achou estouro no título do popup, aba Plano vazia (fixture) e rótulo "x de y" encostando no anel; os dois primeiros foram corrigidos e o terceiro é igual ao protótipo e à demonstração (rig PNG, D4) |
| VR-08 | V08, V09, B06 — testes de estouro, comparador visual do modo real, behavior, documentação | L4 | VR-01 a VR-07 | Implementador C | implementado no C1 (26/10/2026), aguardando verificação. O teste de estouro achou o popup de entrega com a coluna Arquivo em 0 px a 1280 px; o comparador achou o mapa 20,6 px abaixo (`showSubs` fixo) e o botão "Ver entrega" com 38 px. Os três foram corrigidos pelo Implementador B no mesmo ciclo (`KNOWN` vazio). `hivemind_browser_qa.mjs` foi adaptado ao modo real como padrão |

## Transferências (efetivadas em 26/10/2026)

- Da escala (`../2026-10-20_hivemind-escala-equipe/issues.md`):
  - **EQ-12 inteiro** (F1, F3, F4, F7) vai para VR-05 e VR-06.
  - **EQ-04** (E06, E07) vai para VR-01 e VR-02.
  - A parte de cadastro de **EQ-07** (E08) vai para VR-05. O histórico das temporárias
    (E05 da UI) fica na escala.

## Reprovações e correções

Ciclo 1 reprovado pelo verificador independente GPT-6.1 Sol high (`verificacao-c1-codex.md`).

| ID | Critério | Correção exigida | Responsável | Estado |
|---|---|---|---|---|
| C1-01 | B06 | Resolver executável válido no PATH mesmo havendo homônimo no cwd, sem conceder acesso ao cwd | GPT-6.1 Terra high | correção C2 autorizada |
| C1-02 | B02 | Filtrar ferramentas da Rainha no planejamento e recusar ferramenta não autorizada antes do handler; origem somente leitura | GPT-6.1 Terra high | correção C2 autorizada |
| C1-03 | V01/F1 | Botão Consultar modelos do formulário mostra carregamento e bloqueia duplicação, preservando campos e foco | GPT-6.1 Terra high | correção C2 autorizada |

Dois testes de ciclo de vida fora da Hive ainda exigem contraprova fora do sandbox (CIM/taskkill); não foram classificados como falha do produto. A missão real pela interface e a validação visual serão feitas sobre o candidato corrigido.

V02/VR-06: desvio esclarecido e aceito explicitamente pelo usuário em 26/10/2026: Solicitar ajuste apenas no plano; entrega com aprovação e incorporação. Não há escopo adicional de backend.

## Reprovações C2 e correções C3

C1-01, C1-02 e C1-03 corrigidos e confirmados independentemente em C2.

| ID | Critério | Correção comprovadamente necessária | Estado |
|---|---|---|---|
| C2-01 | V06/V09 | IDs de gradiente/padrão por colmeia, pintura preta da Rainha e papel da selecionada, teste da pintura efetiva com demo oculta | correção C3 autorizada |
| C2-02 | B06/fluxo real | Distinguir requests do servidor e resposta inicial RPC; reproduzir colisão no nono progress sem iniciar IA | correção C3 autorizada |
| C2-03 | V05/interação | Preservar botão/foco do alerta entre renders, mantendo ações e estilo; BrowserQA não deve exigir clique em nó recriado | correção C3 autorizada |

Evidências completas: `verificacao-c2-codex.md`, `.test-tmp/vrc2/{rpc-collision,alert-identity}.log` e capturas `codex-c2-real/`. Resta somente o ciclo 3/3.
