# Roadmap — Hive Mind

Atualizado em 26/10/2026. **Tudo que está em "Próximo" e "Depois" é planejado e
não existe no código.** O que existe hoje está descrito em `README.md`,
`backend.md`, `adaptadores.md` e `frontend.md` desta pasta. Os registros de
processo de cada tarefa ficam em `docs/planos/` (ver "Tarefas").

## Agora

Frontend (ciclo 7) e backend (C4) concluídos: missões reais com Claude e Codex
rodam do pedido à entrega aplicada na origem, validadas com turnos reais em
20/10/2026.

Concluída em 21/10/2026: `docs/planos/2026-10-21_hivemind-correcoes-pre-teste.md`
("Encerrar missão", motivo real das falhas, mensagens em português, mostrador do
Hub). A seguir: teste no Chrome do usuário (sem IA e com uma missão real pequena,
autorizada).

Teste no Chrome concluído em 25/10/2026: fase 1 aprovada e fase 2 completa pela
interface, do pedido à entrega aplicada na origem de teste, com Rainha e verificador
Codex e operária Claude, depois das correções de 24–25/10/2026 (sessões sob `pythonw`,
encerramento de processos, resposta final do Codex, checks com Python, escopo
verificável e avisos da gaveta Missão).

**Modo real com o visual do protótipo** (26/10/2026,
`docs/planos/2026-10-25_hivemind-visual-real/`, implementado inicialmente no ciclo 1 de 3, com correções e verificação final no ciclo 3/3): gavetas Agentes, Missão e Conversa, abas puxadoras, HUD com sete etapas,
colmeia com estados e rotas vindos do backend e popup de entrega, tudo com as mesmas classes
do protótipo; cadastro rico de abelha (descrição, skills declarativas, ferramentas),
ferramentas por abelha no broker, operação `progress` e `bees_summary`; comparador visual do
modo real e teste de estouro (`testes.md`). Esta tarefa veio **antes** da escala e absorveu parte dela (abaixo).

## Próximo — escala da equipe e navegação da colmeia

Tarefa `docs/planos/2026-10-20_hivemind-escala-equipe/` · PRD pronto · **suspensa,
ciclo 0/3**, aguardando o usuário mandar iniciar. Em 26/10/2026 ela perdeu o que foi
entregue pela tarefa do visual real: **EQ-04** (cadastro rico e ferramentas por abelha,
E06 e E07) e **EQ-12** inteiro (achados de interface F1, F3, F4 e F7) foram transferidos e
implementados, e a parte de cadastro de **EQ-07** (E08, formulário de abelhas na gaveta
Agentes) também. Continuam aqui os limites, o paralelismo, o encerramento das temporárias, os
anéis, o zoom e o histórico das temporárias na interface (E05).

- A Rainha decide o paralelismo: arquivos e recursos compartilhados (`resources`)
  serializam, o resto roda em paralelo.
- Limite padrão de 4 trabalhos simultâneos, ajustável de 1 a 8 (hoje o padrão é
  2), com guarda de 1,5 GB de RAM livre.
- Plano com no máximo 12 abelhas, 8 temporárias e 40 tarefas (`plan_too_large`).
- Temporárias somem da colmeia ao fim da missão e ficam no histórico.
- Colmeia em anéis para qualquer número de abelhas (hoje: slots fixos), zoom
  (`+`, `−`, `Ajustar`, roda do mouse), arrasto e teclado.
- Ressalvas do C3 (EQ-09) e endurecimento dos adaptadores do C4 (EQ-11).
- Regressão e documentação da escala (EQ-08), que agora conta com os testes de navegador
  do modo real (`testes.md`).

## Depois — agentes pessoais (somente ideia)

`ideias/agentes-pessoais.md`: segunda página dentro da aba Hive Mind com as mesmas
abelhas permanentes como assistentes pessoais proativos, inspirados em OpenAI
Dots, Meta Muse e xAI Grok Bot. Exige esclarecimento, PRD e decisões de
arquitetura (funcionamento com o Hub fechado, conectores).

## Tarefas

| Tarefa | Status | Registro |
|---|---|---|
| Animação das abelhas | Concluída (ciclo 1, 10/10/2026) | `docs/planos/2026-10-10_animacao-abelhas.md` |
| Frontend 2D no Hub | Concluída (ciclo 7, 13/10/2026) | `docs/planos/2026-10-10_hivemind-frontend-hub/` |
| Backend real | Concluída (C4, 20/10/2026) | `docs/planos/2026-10-19_hivemind-backend/` |
| Correções antes do teste no navegador | Concluída (ciclo 2, 21/10/2026) | `docs/planos/2026-10-21_hivemind-correcoes-pre-teste.md` |
| Teste no navegador real | Concluído (25/10/2026): fase 2 até a entrega aplicada | `docs/planos/2026-10-24_hivemind-teste-navegador.md` |
| Correções do teste no navegador | Concluída (B1, B2, B3, F2, F5, F6), 25/10/2026 | `docs/planos/2026-10-24_hivemind-correcoes-teste.md` |
| Checks com Python, escopo verificável e acabamentos | Concluída (ciclo 3, 25/10/2026) | `docs/planos/2026-10-25_hivemind-entrega-real.md` |
| Modo real com o visual do protótipo | Implementada, correções e verificação final no ciclo 3/3 (26/10/2026) | `docs/planos/2026-10-25_hivemind-visual-real/` |
| Escala da equipe e navegação | Suspensa, 0/3 (sem EQ-04 e EQ-12, e com E08 transferido) | `docs/planos/2026-10-20_hivemind-escala-equipe/` |
| Agentes pessoais | Ideia | `ideias/agentes-pessoais.md` |

Capturas de QA do frontend: `.qa-arquivo/2026-10-10_hivemind-frontend-hub/`
(fora de `docs/` desde 21/10/2026).
