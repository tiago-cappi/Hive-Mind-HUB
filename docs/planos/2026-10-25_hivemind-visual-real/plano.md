# Plano — Hive Mind: modo real com o visual do protótipo

> **Status em 26/10/2026: CICLO 3 EM ANDAMENTO** · faixa completa · plano aprovado pelo usuário em 26/10/2026, com autorização de uma missão real pela interface para a validação final.
> PRD: `prd.md` · Issues: `issues.md` · Verificação: `verificacao.md`.

## Agentes

| Papel | Modelo | Observação |
|---|---|---|
| Orquestrador | sessão principal (Opus 5.5) | Esclarece, planeja, libera lotes, consolida registros e conversa com o usuário. |
| Implementador A | Sonnet, esforço alto | Lote L1 (backend). |
| Implementador B | Sonnet, esforço alto | Cadeia L2 → L3 (front), sempre em sequência porque L3 usa o snapshot de L2. |
| Implementador C | Sonnet, esforço médio | Lote L4 (testes de navegador e documentação), depois de L1–L3. |
| Verificador | Opus limpo, somente leitura | Preferência registrada do usuário. Sem turno real de IA e sem tocar a porta 8765 sem autorização. |

O `docs/desenvolvimento.md` cita modelos do fluxo Codex. Este fluxo é o do Claude Code,
igual às tarefas Hive anteriores (Sonnet implementa, Opus limpo verifica).

## Contrato entre lotes (fixado aqui para L1 ∥ L2)

`GET /missions/<id>` ganha `bees_summary` (lista, mesma ordem do plano; sem plano, a
equipe do planejamento):

```json
{"id":"worker1","role":"worker","temporary":false,"active":true,
 "description":"...","skills":{"tags":["python"],"instructions":"..."},"tools":["read","patch","checks"],
 "provider":"codex","model":"...","effort":"...",
 "tasks":{"total":3,"done":1,"current":"t2","items":[{"id":"t1","description":"...","status":"done|running|waiting|pending|failed","depends_on":[],"files":["a.py"]}]},
 "progress":{"done":3,"total":23,"note":"...","seq":812}|null,
 "tools_used":{"read":4,"patch":2,"checks":1,"progress":5},
 "job":{"state":"running|completed|failed|null","cycle":1,"started":true}}
```

Status de tarefa: `done` (job concluído no ciclo atual), `running` (job rodando),
`failed` (último job falhou), `waiting` (dependência ainda não concluída) e `pending`.
O front nunca recalcula isso dos eventos.

## Fases e lotes

| Lote | Responsável | Depende de | Arquivos permitidos | Entrega |
|---|---|---|---|---|
| **L1 — backend** | A | aprovação | `HiveMind/backend/{store,service,missions,capabilities,tools,routes}.py`, `adapters/*.py` só para levar a ferramenta `progress` ao provedor, `tests/test_hivemind_*.py` (exceto o do front) | B01–B05. `ToolBroker` passa a aceitar o conjunto do job (`read`, `patch`, `checks`, `progress`) e recusa o resto. A mudança é sensível: a recusa precisa de teste próprio. |
| **L2 — estado e colmeia** | B | aprovação (contrato acima) | `HiveMind/frontend/static/{mission-state,hive,messages}.js`, parte "colmeia/HUD" de `hive.css` | V05, V06 e a parte de dados de V01/V02: o snapshot real passa a ter etapas, estados, rotas, progresso e temporárias. |
| **L3 — gavetas** | B | L2 | `live-drawers.js` (vira só o compositor) e os novos `live-team.js`, `live-mission.js`, `live-chat.js` e `live-delivery.js`; `drawers.js` só para **exportar** auxiliares puros (`tabs`, `statusIcon`, `createRowIcon`, `hex`) sem mudar o comportamento; a parte `hm-live-*` de `hive.css` | V01–V04, V07, V08. As classes `hm-live-*` que ficarem sem uso são apagadas. |
| **L4 — prova e docs** | C | L1, L2, L3 | `tests/hivemind_visual_compare.mjs`, `tests/hivemind_frontend_behavior.mjs`, `tests/test_hivemind_frontend.py`, fixture `tests/fixtures/hivemind_real_*.json`, `docs/hivemind/*.md` | V08 automatizado, V09 e B06. |

Arquivos novos em `static/` seguem a regra 11: um arquivo por gaveta, mesma pasta,
nenhum encaixe novo em `server.py` ou `index.html`. Se algum passar de ~600 linhas, o
implementador avisa em vez de dividir sozinho.

## Riscos

- **Mudança de segurança:** o `ToolBroker` deixa de ter o conjunto fixo
  `read`/`patch`/`checks`. A recusa por abelha e a validação de `progress` precisam de
  teste próprio, e o verificador olha isso primeiro.
- **Regressão da demonstração:** o comparador do ciclo 7 roda antes e depois de L3.
- **Fidelidade:** o protótipo não tem tela para algumas funções reais. O encaixe segue D1
  e o resultado é comparado com o componente equivalente, não com uma tela inexistente.
- **Elenco antigo:** o cadastro salvo hoje (`queen`, `worker1`, `verifier`) vira
  incompleto. A gaveta Equipe precisa mostrar com clareza o que falta.
- **Missões antigas** (1–3 em `awaiting_user`, a 4 concluída) precisam abrir sem erro.

## Validação de cada ciclo

1. `./.venv/Scripts/python.exe -m pytest tests -q` com a suíte completa.
2. `node tests/hivemind_frontend_behavior.mjs` e `node tests/hivemind_visual_compare.mjs`
   para o modo real (novo) e a demonstração (sem regressão).
3. Prints do modo real no Hub, com a missão concluída "Teste real despedida 4" e as
   fixtures, lado a lado com o protótipo, anexados à `verificacao.md`.
4. Uma missão real pela interface **só com autorização do usuário**.

## Contador

| Ciclo | Estado |
|---|---|
| 1 | implementação inicial concluída; verificação independente Codex reprovada em 26/10/2026 (C1-01, C1-02 e C1-03) |
| 2 | três correções C1 confirmadas; reprovado por C2-01 (pintura SVG), C2-02 (colisão RPC real/fake) e C2-03 (foco do alerta) |
| 3 | iniciado em 26/10/2026: último ciclo, lote único codex.py + hive.js, regressões/testes de pintura e validação integrada final |

## Retomada pelo Codex — 26/10/2026

O usuário autorizou continuar a verificação e executar uma missão real diretamente pela página Hive Mind, preferindo navegador integrado e permitindo o Chrome local. O navegador integrado não alcançou o serviço local; a sessão principal recuperou uma instância de teste restrita que ocupava a porta sem responder e reabriu pelo lançador normal. Identidade da instalação e HTTP 200 confirmados. Sem mudança nos encaixes do Hub.

Fluxo desta retomada: sessão principal coordena; verificador independente **GPT-6.1 Sol, high**; correções **GPT-6.1 Terra, high**, substituição explicitamente autorizada pelo usuário nesta conversa porque GPT-5.6 Terra não está disponível nos subagentes. A autorização original de escopo permanece válida. O contador continua 2/3, sem reinício. Relatório C1: `verificacao-c1-codex.md`; candidato C1 permaneceu 59/59 arquivos idênticos.

Lote C2 único e sequencial: corrigir resolução de programas apenas no PATH sem seleção do cwd (C1-01); aplicar ferramentas da Rainha também no planejamento, preservando somente leitura da origem e recusa por broker (C1-02); sincronizar carregamento do catálogo nos formulários de criar/editar sem perder valores ou foco (C1-03). Arquivos: `HiveMind/backend/{tools,service}.py`, `HiveMind/frontend/static/live-team.js`, testes diretamente correspondentes e documentação viva do assunto. Não refatorar os encaixes nem implementar a escala.

Esclarecimento V02 confirmado pelo usuário na retomada: ajuste apenas no plano; entrega permite aprovar e incorporar. Registrado no PRD, sem alteração da máquina de estados.

## Ciclo 3 — último lote autorizado

C2 reprovado pelo verificador independente (`verificacao-c2-codex.md`), candidato intacto 65/65. A missão real pela página integrada (`bbfa9d4feda8417bb2221f0e3c726fc2`) realizou leitura, patches e check no candidato, mas falhou na nona chamada de ferramenta por colisão de IDs RPC; origem preservada por hash. Comparador e estouro passaram, porém a inspeção das capturas revelou preenchimentos incorretos que a medição anterior não detectava. BrowserQA também expôs recriação contínua do botão do alerta, confirmada por fake.

Implementação GPT-6.1 Terra high (autorização de substituição mantida), cadeia única: distinguir respostas RPC das requisições do servidor e consumir a resposta inicial uma vez, sem relaxar thread/turn/gates/pausa; dar identificadores SVG exclusivos a cada colmeia e referências corretas; preservar nós e foco do alerta entre renders equivalentes. Arquivos de produto permitidos: `HiveMind/backend/adapters/codex.py` e `HiveMind/frontend/static/hive.js`. Testes diretos: adapter_turns, behavior, comparador e BrowserQA se necessário para verificar identidade/pintura, mantendo tolerâncias e ações reais. Atualizar somente docs vivos pertinentes.

A validação final exige nova verificação independente, suíte completa fora do sandbox sem carga de navegador concorrente, comparador com prova de pintura real e regressão da demonstração, estouro, BrowserQA e nova missão real pela página após a correção. Não iniciar quarto ciclo; se C3 reprovar ou ficar pendente, parar e apresentar diagnóstico.
