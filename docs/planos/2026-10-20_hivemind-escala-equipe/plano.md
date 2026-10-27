# Plano — Hive Mind: escala da equipe e navegação da colmeia

> **Status em 21/10/2026: SUSPENSA, ciclo 0/3** — aguardando o usuário mandar iniciar; nada desta tarefa existe no código ainda. A referência do código atual está em `docs/hivemind/README.md`.

20/10/2026 · faixa completa · ciclo **0/3** (suspenso; Claude e Codex destravados no C4 do backend em 20/10/2026), após o encerramento do C3
de `2026-10-19_hivemind-backend`. Coordenação: sessão principal Opus 5.5.
Implementação: Sonnet 5.5. Verificação: Opus 5.5 limpo, somente leitura.

## Lotes

| Lote | Requisitos | Arquivos permitidos | Dependência | Agente |
|---|---|---|---|---|
| **L1 backend** | E01–E07, E12 (backend), E13 (a, b), E14 | `HiveMind/backend/{store,missions,scheduler,service,capabilities,tools,delivery,routes}.py`, `HiveMind/backend/adapters/{codex,claude}.py`, `tests/test_hivemind_adapter_turns.py`, `HiveMind/backend/README.md`, `docs/runtime.md` (seção Hive), `tests/test_hivemind_{store,missions,scheduler,service,delivery,api,adapters}.py`, `tests/fixtures/hivemind/` | C3 encerrado | Sonnet A |
| **L2 colmeia** | E09, E10 | `HiveMind/frontend/static/{geometry,hive,app}.js`, `hive.css` (seção da malha e controles de zoom), `tests/test_hivemind_frontend.py`, `tests/hivemind_frontend_behavior.mjs`, `tests/hivemind_browser_qa.mjs` | C3 encerrado | Sonnet B |
| **L3 gaveta Equipe** | E05 (UI), E08, E12 (frontend), E13 (c) | `HiveMind/frontend/static/{live-drawers,mission-state,api}.js`, `hive.css` (seção das gavetas), testes frontend | L1 (contrato do cadastro) **e** L2 (compartilha `hive.css` e testes) | Sonnet B, em sequência |

L1 e L2 são disjuntos e rodam em paralelo. L3 roda depois dos dois, com o
mesmo agente de L2 para não haver dois escritores em `hive.css`.

## Contrato do cadastro (fixado antes de L1/L3)

`POST /hive-api/settings {kind:"roster", bees:[bee...], key, revision}` (o campo `bees` já é o
usado pelo código atual; os campos novos de cada abelha são a mudança), com
`bee = {id, name, role, description, skills:[str], tools:["read"|"patch"|"checks"],
provider, model, effort, temporary:false}`. `GET /hive-api/status` devolve
`roster.bees` com `incomplete:true` e `missing:[campo]` nas entradas antigas,
além de `settings.worker_limit` (1–8) e `dispatch.memory` (`ok`, `memory_low`
ou `memory_unverified`). Plano proposto pela Rainha: tarefas aceitam
`resources:[safe_name]` opcional; abelhas do plano carregam os mesmos campos.

## Notas técnicas

- Guarda de memória num helper próprio do backend, chamado pelo scheduler antes
  de reservar; a função de leitura é injetável para os testes.
- Migração SQLite idempotente (colunas/JSON novos com valores padrão), sem
  apagar dados; limite 2→4 só quando a revisão das configurações é 0.
- Limpeza de temporárias concentrada num único ponto de transição terminal;
  remover a atualização isolada em `delivery.py` se ela for substituída (§4.1).
- Layout: gerador de anéis axiais em `geometry.js` que preserva `AXIAL_SLOTS`
  atuais como primeiras posições; malha SVG cresce conforme o raio ocupado.
- Zoom/arrasto: transformação da camada `hm-world` (escala + translação) com
  limites; o cálculo automático atual de `resize()` vira o modo "Ajustar".

## Validação e ciclos

Cada lote roda os testes Hive; ao fim, suíte completa, manifesto
`manifesto-c1.sha256` e verificação independente registrada em `verificacao.md`.
Reprovação → `issues.md` e ciclo seguinte, teto 3, sem quarto ciclo automático.
Sem Git neste checkout: manifesto por ciclo no lugar de commits.
