# Verificação independente Codex — ciclo 2/3

Data: 26/10/2026. Verificador: **GPT-6.1 Sol (`gpt-6.1-sol`), high**,
independente da implementação e das correções. Implementador C2: agente distinto
GPT-6.1 Terra high, substituição explicitamente autorizada pelo usuário e registrada
no plano. Nenhum código ou teste foi modificado pelo verificador.

**Veredito: REPROVADO.** As três correções de C1 foram confirmadas, mas a revisão
das capturas e a missão real revelaram as causas C2-01, C2-02 e C2-03 abaixo.
Não repetir turnos reais nem iniciar nova rodada de implementação fora do contador:
resta **somente C3** para corrigir e verificar o estado integrado final.

## Integridade e escopo

- Manifestos: `.test-tmp/vrc2/hash-start.json`, `hash-interim.json`,
  `hash-interim2.json`, `hash-interim3.json` e `hash-final.json`.
- **65/65 arquivos intactos do início ao fim.** São os 59 arquivos de código,
  testes, fixtures e encaixes congelados em C1, mais os seis documentos vivos de
  `docs/hivemind/`. Logs de integridade ficam na mesma pasta.
- Comparação contra C1: exatamente oito arquivos de código/testes mudaram:
  `HiveMind/backend/{tools,service}.py`,
  `HiveMind/frontend/static/{live-team,messages}.js`,
  `tests/test_hivemind_{workspaces,bees,service}.py` e
  `tests/hivemind_frontend_behavior.mjs`.
- `ToolBroker`, adaptadores, `hive.js`, CSS, encaixes do Hub e demais arquivos do
  candidato permaneceram iguais aos de C1. A correção deve alcançar agora causas
  existentes no estado integrado, não uma alteração de arquitetura.
- PRD/plano/Issues podem receber a consolidação da sessão principal; ficam fora do
  congelamento técnico. O aceite de V02 pelo usuário foi informado pela sessão
  principal: **“Manter ajuste apenas no plano; entrega permite aprovar e incorporar”**.

Este agente não abriu navegador, não operou a interface, não acessou a porta 8765
e não executou IA real. Inspecionou arquivos, métricas e capturas produzidos pela
sessão principal; reproduções próprias usaram somente fakes/DOM descartável.

## Correções de C1 confirmadas

| Achado anterior | Resultado C2 | Evidência |
|---|---|---|
| C1-01 — resolução de executável | **Corrigido** | `program_path` percorre entradas do PATH, ignora cwd e passa candidato qualificado ao `which`. O teste original mantém todas as recusas e o caso `home` inexistente; passou na suíte. Foi adicionada a asserção explícita de homônimo no cwd. As guardas de concessão de leitura não foram relaxadas. |
| C1-02 — ferramentas da Rainha | **Corrigido** | `_plan_job` anuncia somente `read` autorizado. Sem `read`, falha com `planning_read_required` antes de construir a sessão. Seis casos fake cobrem Codex/Claude × read/checks/legado; ferramentas patch/checks/progress recusadas com `tool_not_allowed`, origem intacta. Código estável e mensagem em português presentes. |
| C1-03 — carregamento no formulário | **Corrigido** | `form.syncLoading` atualiza texto/disabled durante render sem substituir o formulário. Behavior testa criar/editar, foco, valores e retorno do carregamento. `hivemind behavior ok`. |

O ajuste do teste antigo de planejamento de `PermissionError` para
`ToolNotAllowed` corresponde à remoção do handler antigo `denied`; não enfraquece a
proibição de patch. Nenhum teste foi reduzido para obter aprovação.

## Reprovações reais do estado integrado

### C2-01 — P2: preenchimentos SVG do modo real não são pintados como especificado

Critérios afetados: **V06 e V09**.

Evidência visual direta:

- `.qa-arquivo/2026-10-25_hivemind-visual-real/codex-c2-comparador/real/real-execucao-1440x900.png`:
  Rainha dourada/transparente como o fundo, em vez do polígono preto; operária
  selecionada também dourada, em vez do preenchimento claro.
- `reference-execucao-1440x900.png`, na mesma pasta: Rainha preta e operária
  selecionada clara no protótipo.
- `.qa-arquivo/2026-10-25_hivemind-visual-real/codex-c2-real/02-plano-pendente.png`:
  confirma a Rainha dourada na interface real, não apenas na fixture.

A fonte de colisão foi identificada: `app.js:22-24` cria a colmeia de demonstração
primeiro e a real depois; `hive.js:37-43` cria os mesmos IDs globais de gradientes
e padrões em ambas (`hm-queen`, `hm-occ`, `hm-occ-sel`, `hm-t*`, `hm-pt*`). O modo
demonstração está oculto quando o real é exibido. As faces usam `url(#...)`
(`hive.js:64`), sem distinguir as instâncias.

O comparador terminou verde, mas mede propriedades/estrutura e trata o mapa como
informação. Neste candidato, a métrica de pixels do mapa real é **10,90%**, contra
**6,57%** da demonstração; isso não falha o script. A presença de um `fill` que
referencia URL não demonstra que a tinta foi efetivamente renderizada.

Correção necessária: IDs SVG únicos por instância e referências coerentes,
preservando demonstração e real. A prova deve detectar pintura efetiva da Rainha
preta e da célula selecionada clara com a demonstração oculta, além de IDs
duplicados, sem relaxar tolerâncias nem mascarar o preenchimento junto com o rig.

### C2-02 — P1: colisão entre IDs JSON-RPC de cliente e servidor interrompe turno válido

Critérios afetados: **B06 / integração real da missão**.

Local: `HiveMind/backend/adapters/codex.py:358-370`, antes do despacho de
`item/tool/call` nas linhas 371-386.

Prova independente, sem IA: `.test-tmp/vrc2/rpc_collision.py` reutiliza o
`FakeRpc` existente sem modificar código/testes. Executa `turn/start` com ID 9,
resposta inicial válida, depois nove requisições de ferramenta do servidor com
IDs de 1 a 9. Saída em `rpc-collision.log`:

```text
ERROR: turn_start_failed
START REQUEST ID: 9
HANDLER COUNT: 8
TOOLS EXECUTED: ['progress', 'read', 'read', 'progress', 'patch', 'patch', 'progress', 'checks']
FINAL PROGRESS EXECUTED: False
REPLY IDS: [1, 2, 3, 4, 5, 6, 7, 8]
```

Causa demonstrada: `if item.get('id') == request_id` não diferencia resposta de
requisição/notification do servidor. A nona chamada válida, com `method` e `params`,
é lida como nova resposta a `turn/start`; como não contém `result.turn.id`, causa
`turn_start_failed`. IDs dos dois sentidos podem coincidir.

Isso reproduz o padrão da missão real C2: a operária realizou progress/read/read/
progress/patch/patch/progress/checks e falhou antes do próximo progresso. A cadeia
de eventos prova oito operações; o diagnóstico JSON da missão não captura os IDs
RPC brutos, portanto a associação à colisão é sustentada pelo padrão, pelo código
e pela reprodução determinística, sem alegar que o ID foi observado no tráfego real.

Correção necessária: distinguir envelopes JSON-RPC antes de correlacionar
respostas; preservar gate, checagens de thread/turn, ferramentas permitidas,
limites e pausa. Cobrir colisão antes e depois da resposta inicial, resposta
inválida genuína e chamadas normais, sem consumir mais quota para o diagnóstico.

### C2-03 — P2: alerta reconstrói o botão a cada render e perde identidade/foco

Critérios afetados: **V05 e regressão do QA de interação**.

Local: `hive.js:51` (`fillAlert`) e `renderHud`, linha 62. O alerta usa
`replaceChildren` em todo render, mesmo sem mudança no conteúdo. A demonstração
tem ticks frequentes e o modo real tem polling.

Prova independente sem navegador: `.test-tmp/vrc2/alert_identity.mjs` lê a função
real `fillAlert` e a executa em DOM falso, duas vezes com os mesmos argumentos.
Depois de focar o botão original, a segunda renderização registra em
`alert-identity.log`:

```json
{"sameContent":true,"sameButton":false,"focusedNodeStillMounted":false}
```

A sessão principal também reportou falha do
`tests/hivemind_browser_qa.mjs:72`: durante 30 segundos o locator de “Ver aprovação”
era destacado/removido antes de concluir o clique. A reprodução acima confirma
a causa de identidade, independentemente da latência ou da automação.

Correção necessária: preservar nós e foco quando o conteúdo do alerta não muda;
atualizar texto/handler quando o estado muda. Validar rerender idêntico e troca de
estado, além do Browser QA existente. Não resolver com `force` no clique,
timeouts maiores ou enfraquecimento do teste.

## Testes e evidências recebidas

| Verificação | Resultado |
|---|---|
| Suíte completa fora do sandbox, TEMP/TMP próprios e wrapper com guarda `__main__` | **467 passaram, 1 falhou, nenhum skip; 429,55 s**. `suite.log` e `results.xml` em `.test-tmp/vrc2/`. |
| Única falha da suíte | `test_gate_requires_live_verified_session_and_current_billing`, linha 97: sessão falsa Claude devolveu `enforcement_evidence_unverified`. Adaptador e teste não mudaram C1→C2. |
| Repetição isolada exata fora do sandbox, sem mudar código/teste/timeout | **1 passou; 8,82 s**, `gate1.log` e `gate1.xml`. Há instabilidade não explicada dessa execução completa; não se declara a suíte inteira verde a partir da repetição isolada. |
| Hardlinks e testes de ciclo de vida | **Passaram** na suíte fora do sandbox; a limitação/skip de C1 não se repetiu. |
| `node tests/hivemind_frontend_behavior.mjs` | **Passou**, `behavior.log`. |
| Comparador executado pela sessão principal, métricas inspecionadas pelo verificador | DPR 1, 3 viewports de demonstração, 6 estados; modo real 13 casos e 268 pares; `real.failures=[]`, `real.known=[]`, `errors=[]`. Os PNGs revelam C2-01 apesar desse resultado. |
| Estouro executado pela sessão principal, JSON inspecionado | **237 checks, zero failures, errors/problemas vazios**; 194 avisos de HUD/células sob gavetas, já conhecidos. `codex-c2-estouro/estouro.json`. |
| Browser QA executado pela sessão principal | **Falhou** no clique do alerta; C2-03 confirma causa. Não foi repetido pelo verificador. |

A sessão principal pediu não repetir a suíte completa no estado já reprovado;
o candidato de C3 deve receber uma execução completa limpa, sem concorrência com
QA ou missão real. A falha isolada do gate Claude não foi transformada em uma
quarta correção especulativa nem atribuída ao sandbox — a suíte rodou fora dele.

## Missão real conduzida pela sessão principal

Fonte lida: `.test-tmp/hive-visual-codex/missao-real.json`, missão
`bbfa9d4feda8417bb2221f0e3c726fc2`, eventos 150–174. Capturas em
`codex-c2-real/` (planejamento, plano pendente e falha). Equipe de três abelhas
Codex `gpt-5.6-luna/medium`, limite 1/1. Plano `fff6db85…`, uma tarefa e dois
arquivos; aprovação e início pela interface, conforme relato da sessão principal.

O JSON confirma planejamento sucedido, aprovação do plano por hash, workspace,
operária com sessão/processo próprio e último progresso 65/100. Contagens:
2 read, 2 patch, 1 checks com sucesso e 3 progress. Depois, `job_error` com
`turn_start_failed`; a missão terminou em `awaiting_user`, job da operária
`failed`, sem verificação e sem entrega. A sessão principal confirmou que os
dois hashes da origem de teste permanecem os iniciais. O teste **não** comprovou
verificação/entrega/incorporação do novo candidato e não é aprovado ponta a ponta.

A suspeita de abas do detalhe não foi confirmada: a sessão principal abriu
Ferramentas usando Enter e observou as contagens corretas. Não há reprovação de
abas nem pedido para alterá-las.

## Critérios, um a um

| Critério | Resultado C2 | Evidência |
|---|---|---|
| B01 | **Passou** | Validação de cadastro, limites, antigas incompletas, temporárias e `roster_incomplete`; testes passaram. Cadastro também completado pela interface pela sessão principal. |
| B02 | **Passou** | C1-02 corrigido; planejamento read-only autorizado e recusas comprovadas nos dois provedores fake. Execução/verificação continuam com ferramentas por abelha e sem patch no verificador. |
| B03 | **Passou no broker/serviço** | Validação e eventos passaram; missão real registrou 0, 25 e 65/100 sem tocar arquivos por progress. A chamada final é impedida pela falha de transporte C2-02, não por erro da validação dos argumentos. |
| B04 | **Passou** | Resumos de tarefas/progresso/ferramentas/último job/ciclo, teste com 700 eventos e rota antiga passaram; JSON real exibiu os valores correspondentes. |
| B05 | **Passou** | Cadastros e skills declarativas nos prompts; identidade do elenco preservada no plano e testes fake passaram. |
| B06 | **Falhou** | Integração real interrompida por C2-02; suíte completa teve uma falha não reproduzida isoladamente. Compatibilidade e mensagens testadas passaram. |
| V01 | **Passou nas evidências disponíveis** | C1-03 resolvido e behavior cobre criar/editar sem perder foco/valores. Capturas mostram componentes esperados; seleção de Ferramentas confirmada pela sessão principal. |
| V02 | **Passou nas fixtures e estados exercitados** | Plano, aprovação e início reais conferidos; cartões/avisos/abas cobertos por behavior. Usuário esclareceu que ajuste existe somente no plano. Entrega real ainda não alcançada. |
| V03 | **Passou nas fixtures** | Classes e regras de habilitação, texto seguro e teste de estouro; capturas e behavior. |
| V04 | **Passou nas fixtures** | Abas com contadores/ícones/setas, ações e teste de sobreposição sem falhas. |
| V05 | **Falhou** | Etapas, banner, estado e ações mapeados corretamente; C2-03 torna botão de alerta instável e remove foco a cada render. |
| V06 | **Falhou** | C2-01: Rainha não está preta e selecionada não recebe preenchimento claro. Estados/progresso/rotas backend foram observados; isso não elimina a falha visual explícita. |
| V07 | **Passou nas fixtures; ponta a ponta pendente** | Popup com critérios/arquivos e ações no behavior/comparador, screenshot de entrega inspecionado. Missão real não chegou à entrega por C2-02. |
| V08 | **Passou nos casos automatizados** | JSON com 237 checks e zero falhas, cobrindo os tamanhos previstos e textos longos; avisos conhecidos preservados. |
| V09 | **Falhou na prova integrada de fidelidade** | Script passou, mas as capturas evidenciam C2-01; medição atual não detecta a tinta SVG ausente. Exigir prova de pintura efetiva e regressão da demonstração em C3. |

## Lote mínimo para o último ciclo

1. `HiveMind/backend/adapters/codex.py`: correlacionar corretamente mensagens
   JSON-RPC, com regressão fake da colisão, sem mexer nos controles de isolamento.
2. `HiveMind/frontend/static/hive.js`: IDs SVG por instância e referências
   correspondentes; identidade estável do alerta sem alterar layout/animações.
3. Testes diretamente ligados às três causas, incluindo pintura com instância de
   demonstração oculta e identidade/foco do alerta; documentação viva correspondente.

Nenhuma mudança nas abas, encaixes do Hub, ferramentas permitidas, fila de voz,
arquitetura de execução ou política de aprovação foi solicitada. Este relatório
congela C2; a sessão principal controla a liberação do terceiro e último ciclo.
