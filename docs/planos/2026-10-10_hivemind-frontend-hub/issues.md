# Issues — Hive Mind no Hub

> **Status em 21/10/2026: CONCLUÍDA** — aprovada na verificação independente do ciclo 7 (13/10/2026). Este arquivo é registro histórico do processo e pode descrever intenções já superadas; a referência do código atual está em `docs/hivemind/README.md`. As capturas de QA foram movidas para `.qa-arquivo/2026-10-10_hivemind-frontend-hub/`; caminhos `qa*/` citados abaixo são relativos a essa pasta.

Atualização final: 13/10/2026. Faixa completa. Ciclos utilizados: **7 totais — três originais e quatro adicionais autorizados; ciclo 7 APROVADO**. Todas as Issues encerradas no candidato final; histórico preservado abaixo. Sem C8 automática.
Planejamento GPT-6.1 Sol high; candidato atual implementado/corrigido por GPT-5.6 Terra high; verificação independente GPT-6.1 Sol high. Exceções anteriores permanecem somente como histórico.

| ID | Tarefa | Requisitos | Arquivos/superfície | Dependência | Responsável | Status |
|---|---|---|---|---|---|---|
| HM-00 | Autorizar seis ganchos mínimos index conforme docs/desenvolvimento.md §5.5 | R11/R12 | Trechos exatos no plano; autorização específica já recebida | Plano | Sessão principal/usuário | Concluída: “Autorizar os seis ganchos” |
| HM-01 | Mover protótipo inteiro e confirmar integridade/baseline | R03/R09/R13 | Protótipo Hive Mind Desktop → HiveMind/prototipo; referências vivas | Nenhuma, movimentação já autorizada | Implementador Sol5.6 high | Em andamento — inventário SHA-256 pré-movimento concluído; baseline local 228 passou/1 falhou em teste preexistente de árvore Windows |
| HM-02 | Blueprint estático, assets PNG e rig nativo | R09/R10/R13 | HiveMind/__init__.py, frontend/routes.py, static/bee-animation e assets | HM-01 | Mesmo implementador | Não iniciada |
| HM-03 | Dados simulados, clock e máquina de estados | R02/R05/R06/R08/R10 | frontend/static/demo-data.js, simulation.js | HM-02 | Mesmo implementador | Não iniciada |
| HM-04 | Colmeia e fluxos geométricos clicáveis | R03/R07/R09 | geometry.js, hive.js, hive.css | HM-03 | Mesmo implementador | Não iniciada |
| HM-05 | Três gavetas completas, conversa, agentes e entrega | R04/R05/R06/R08/R11 | drawers.js, hive.css, app.js | HM-04 | Mesmo implementador | Não iniciada |
| HM-06 | Navegação página/provider e guardas mínimas | R01/R10/R11/R12/R13 | providers.js/codex.css; index seis ganchos+loader; server import/register | HM-00, HM-05 | Mesmo implementador | Não iniciada |
| HM-07 | Testes reais/QA visual/documentação final | R01–R14 | tests/test_hivemind_frontend.py, hivemind_frontend_behavior.mjs; testes Codex afetados; docs atuais e registros | HM-06 | Mesmo implementador | Não iniciada |
| HM-08 | Revisão e verificação independente | R01–R14 | Leitura do estado final; issues/verificacao em disco | HM-07 | Novo verificador Sol6.1 high | Não iniciada |

## Aceite dos lotes

HM-00: usuário respondeu “Autorizar os seis ganchos”; autorização específica registrada pela coordenação, sem ampliar contratos/backend nem mudar regras permanentes.

HM-01: conferir caminhos absolutos dentro workspace antes do move; destino não existe; inventário/hashes de todos arquivos coincidem; fonte antiga não duplicada; links relativos da prévia preservados; suíte baseline registrada.

HM-02: Flask serve módulo/CSS/logo/seis PNG; tentativas de path traversal não abrem arquivos fora de static; nenhuma rota IA; rig mantém três camadas/pivôs/estados e não depende do runtime exportado.

HM-03: fase/tempo/contadores testáveis com clock controlado; aprovação nunca automática; ajuste→nova aprovação; retry→retomada; pausa/invisibilidade preservam tempo/estado; simulação explicitamente identificada.

HM-04: malha/ocupação e conexões/sentidos do protótipo; seleção e popup úteis; subagentes aparecem somente quando habilitados; sem overlays cobrindo hits incorretamente.

HM-05: inventário de TODAS abas/infos do PRD presentes; CRUD com slots/limites; input seguro; simulador explica alcance e não faz rede IA; entrega das quatro/três divergências correta.

HM-06: selectedPage distinto de selected provider; Hive acessível com seis sessões sem criar sid; retorno mantém provider/rascunhos/preferências; page guard só entradas UI e mic obsoleto; STT legítimo segue; mobile sem foco; painel completo Claude; galáxia suspensa; ordem de módulos e fallback conservam Hub.

HM-07: testes focados e suíte inteira passing com evidências; QA runtime versus protótipo movido (mínimo viewports PRD), capturas de cenários/gavetas e redução de movimento; docs descrevem ausência de backend e limites; nenhuma alteração fora da superfície. Skip de teste necessário é pendência, não aprovação.

HM-08: passou/falhou/não verificável por R01–R14; veredito explícito sobre estado final, com riscos/pendências identificados. Não editar código/testes.

## Reprovações e correções

Nenhuma verificação executada; nenhuma reprovação registrada. Falhas futuras recebem IDs HM-F01 etc. Registrar ciclo, requisito, local, reprodução, esperado/observado, evidência e correção requerida. Preservar histórico; correções somente ciclos 2/3. Não consumir um ciclo novo por etapa ou por falha de ambiente.

## Atualização de referência — mesmo ciclo1/3

Requisito visual ampliado explicitamente pelo usuário após atualização do protótipo em17:15:26BRT. Não registrar reprovação por substituição humana; histórico21/21 não é baseline nova. Código já criado está sob ajuste do ciclo1, ainda sem veredito independente. HM-00 continua autorizada; não pedir/repetir seis ganchos.

| ID | Trabalho focal adicional | Requisitos | Arquivos | Dependência/status |
|---|---|---|---|---|
| HM-09 | Fixar nova referência/inventário seis arquivos e capturas pareadas | R03/V01 | Somente registrosQA/planejamento; protótipo leitura | Planejamento concluído por leitura/hashes; capturas novas pendentes |
| HM-10 | Portar mundo único/malha gradiente/bisel/sombras/efeitos/routes/HUD | R03/R07/V02–V04/V06 | geometry.js,hive.js,hive.css; app.js somente shell necessário | A executar por mesmo Sol5.6high |
| HM-11 | Gavetas/layout/fonts exatos e remoção de sobras | R04–R06/R08/V02/V05/V08 | drawers.js,hive.css,app.js; simulation.js UI mínimo; remover layout.css se redundante/import; CSS Codex só blocoHive | DepoisHM-10, mesma cadeia |
| HM-12 | Resolver abelhas conforme preferência sem alterar referência | R09/V07 | Rig/representação runtime somente conforme decisão | Escolha opcional PNGvsSVG apresentada pela coordenação; preferênciaPNG enquanto pendente |
| HM-13 | Corrigir harness de referência, novaQA/testes/docs | R14/V01–V08 | três testesHive/documentaçãoQA | DepoisHM-10/11/12; preservar isolamento/voicechecks |
| HM-14 | Verificador independente do estado final atualizado | R01–R14/V01–V08 | Relatório/Issues; código/testes somente leitura | DepoisHM-13; novoSol6.1high |

Aceite detalhado/valores CSS/DOM/source no adendo do plano. Não é só “adicionar sombra”. Corrigir simplificações visuais diretamente; não reescrever provider/index/server, não restaurar referência antiga e não executar L0 novamente. Planejador apenas registra documentos, sem código/testes/protótipo alterados.

## Atualização de execução — 12/10/2026

Implementação: **GPT-5.6 Terra, high**. A indicação Sol5.6 nas linhas
históricas acima registra a exceção anterior, substituída para esta execução
pela escolha permanente do usuário. Ciclo permanece **1/3**.

| ID | Status verificado do implementador |
|---|---|
| HM-01 | Concluída: protótipo vigente preservado; SHA-256 de referência permanece `03B05ACDDD71DA6C6C2E81D3AE14ADC6B08D4EBB340E44C1CE3D41A92CF8DAD6`. |
| HM-02 | Concluída: blueprint estático, assets e rig PNG preservados; sem dependência de produção nova. |
| HM-03 | Concluída: fases, lifecycle, pausa, aprovação, ajuste, retry e slots estáveis de CRUD cobertos. |
| HM-04 | Concluída: mundo/rotas SVG, ordem de links da fonte, popup e sombras de célula conferidos em pares. |
| HM-05 | Concluída: gavetas, tabs, conversa, entrega, aprovação, formulário/destino e preservação de rascunhos implementados. |
| HM-06 | Concluída: integração existente preservada; QA isolado confirma seis sessões, mic/STT/mobile e retorno Claude/Codex. |
| HM-07 | Concluída pelo implementador: suíte, Node, Chrome e comparativo visual executados com evidência abaixo. |
| HM-08 / HM-14 | **Pendente**: verificador independente GPT-6.1 Sol high deve revisar o candidato congelado sem editar código ou testes. |

Evidência de execução: `pytest tests -q` = **235 passed**; testes Node Hive e
Codex passaram; `hivemind_browser_qa.mjs` passou com Chrome isolado; o
comparador visual passou com 3 pares idle e 6 pares de estado em
`qa-atual/`. Não houve reprovação de ciclo, nem alteração de referência ou
assets. O candidato deve permanecer sem novas escritas até a revisão HM-08.

## Reprovação independente formal — ciclo 1, 12/10/2026

Verificador **GPT-6.1 Sol high**, independente e somente leitura no candidato.
**REPROVADO**: 235 testes passam, mas comportamentos/conteúdo/fidelidade exigidos
falham. Matriz R01–R14/V01–V08 em verificacao.md; evidências exclusivas em
qa-verificador/independent/report.json e capturas pareadas. Esta é a primeira
reprovação formal. Ciclo 1 consumido; ciclo 2 ainda não iniciado, correções pelo
implementador Terra high conforme coordenação. Código/testes/protótipo intactos.

### HM-F01 — [P1] Botão de envio da conversa não envia

- Critérios: R06/V05. Local: HiveMind/frontend/static/drawers.js:82, renderBottom;
  helper button define type=button e Enviar para a Rainha não recebe submit/click.
- Reprodução: missão idle, abrir conversa, escrever Pedido de clique e clicar
  Enviar para a Rainha. Observado: phase=idle/log=[]/input intacto/type=button.
  Esperado/fonte: phase=p1a e log do usuário+evento após o mesmo clique.
- Evidência: report.json observação send-button-click.
- Correção/reteste: submeter uma vez por clique e Enter, limpar input somente no
  sucesso, registrar texto seguro durante missão, zero chamadas IA. Guardas Hub
  e continuidade de turno anterior permanecem inalteradas.

### HM-F02 — [P1] Cenários conservam estado inválido e vazio permite criação

- Critérios: R03/R05/R06/R08/V05/V06. Locais: simulation.js:128 setScenario,
  start/restart/freeSlot/setWorkerForm/addWorker; drawers.js renderLeft/Mission/
  Delivery; hive.js cenário vazio.
- Reprodução 1: done com entrega aberta, adjusted=true e showSubs=true, clicar
  Colmeia vazia. Observado: idle com delivery=true/adjusted=true/showSubs=true;
  dialog anterior permanece. Fonte limpa todos e remove dialog. Form também não
  é limpo por setScenario; restart não limpa link como a fonte.
- Reprodução 2: em vazio, Criar operária está habilitado e abre form; fonte
  desabilita. Painel direito nativo mantém Simular missão/Pronta/aprovação normal
  e badge0/7; fonte mostra Sem agentes/Sem missão/badge– e não simula. Ausentes
  quadro central com logo/explicação/CTA e Uma colmeia reúne no painel esquerdo.
- Evidências: scenario-reset-from-delivery/empty-create e par native-empty.png/
  reference-empty.png.
- Correção/reteste: restaurar resets, guards e composição da fonte; testar
  done→empty→mission, failed→mission, form aberto→cenário, restart com link e
  envio/CRUD inválidos em vazio. Preservar somente dados que a fonte preserva.

### HM-F03 — [P1] Gavetas e popup omitem informações e fluxos

- Critérios: R04/R05/R07/V04/V05/V08. Locais: drawers.js renderDetails (42–63),
  renderMission (76–78); hive.js popup (53); demo-data.js LINK_INFO.
- Reprodução: Documentos/Rainha→Relações e Missão→Conexões. Fonte apresenta
  Conexões na colmeia navegáveis nos detalhes, legenda de sete estados com
  setas/pulsos/amostras e Conexões agora. Nativo omite relações/legenda, usa
  traços simples/resumos, lista LINK_INFO inteiro mesmo com subs ocultos e não
  incorpora conexões de operárias criadas. Popup usa ↔/título fixo e omite
  explicação STATE_INFO/amostra; fonte calcula origem→destino em in/ret.
- Contador da alça continua6 com subs visíveis, fonte8; símbolos waiting/coord
  e badges diferem. Inventário de todas as 38 combinações agente/aba confirma.
- Evidências: report.json inventories; pares documentos-relacoes,documentos-tools,
  mission-conex; comparator/states selected-link; fonte renderVals/details/
  legend/connOf/rowIcon.
- Correção/reteste: preservar todas as informações/textos/símbolos/listas
  dinâmicas da referência, sem resumo substitutivo. Conferir todas as abas,
  subs ocultos/visíveis, agentes criados e out/in/ret/flow/wait/fail, relações
  navegáveis. Permissões continuam descritivas/simuladas.

### HM-F04 — [P1] Progresso, detalhes e estados derivados incorretamente

- Critérios: R04/R05/V06. Locais: hive.js agentStatus (10)/render (51),
  drawers.js renderDetails/renderLeft/updateProgress, demo-data.js fases,
  simulation.js adjust/go.
- Reprodução: p2b pausado a50%. Documentos/Cadastros nativos12/23 por Math.round,
  fonte11/23 por Math.floor. Detalhe vazio quando status[2]=null; fonte usa
  11 de 23 e-mails lidos. Anexos/Mensagens sem7/14 e4/9, segmentos/totais/detalhes;
  Processamento simulado em andamento substitui informação de progresso.
- Andamento atual inicia inteiro e depois usa frac da subfase; fonte combina
  STEP_PH/index+frac. Pausa/falha e bordas não derivadas como fonte, plano atual
  sem peso700. Textos de fases/LINK_INFO encurtados; adjusted ativa em adj1,
  fonte em adj4/retorno.
- Evidências: progress-and-detail-50-percent, p2b-subprogress e inventories;
  fonte status/steps/plan/buildPhases/go.
- Correção/reteste: derivar campos/totais14/9/floor/detalhes/fórmula STEP_PH e
  paused/approval/fail da fonte. Conferir ticks e todas fases, adj1–adj5/novo
  approval, sem perder drafts/foco. Não validar somente jump ao estado final.

### HM-F05 — [P1] Efeitos da Rainha e HUD não preservam os estados

- Critérios: R03/R07/V06, composição dinâmica relacionada a V03.
  Locais: hive.js cellVisual (38)/render/HUD; hive.css37/86.
- Reprodução: Rainha selecionada p2b. Fx genérico preto1,5px/dash7/7/radius63;
  fonte mostarda2,5px/dash17.36/13.64/radius62 + seleção branca3px/radius67.
  Sweep/ripple coord/retorno e hm-draw done ausentes; cadência genérica1,2s
  difere de queenFx1,8s. Efeitos não fazem parte da exceção de personagens PNG.
- Idle/vazio: hm-hud-alert[hidden] continua display:flex, formando retângulo
  preto abaixo do HUD. Alertas approval/fail/botões e step5 preenchido diferem.
- Evidências: queen-effects, pares idle/p2b/approval/fail/done; fonte queenFx/
  cellFx/linksLayer/renderVals.
- Correção/reteste: portar efeitos/estados da fonte e remover genérico substituído;
  manter rigPNG e pausa/hidden/reduced. Ver seleção/coord/retorno/approval/fail/
  done e ausência de alerta vazio, tanto animado quanto congelado.

### HM-F06 — [P2] Seleção altera comportamento e enquadramento

- Critérios: R04/R07/V04/V06. Local: simulation.js:140 selectAgent,141 selectLink;
  handlers das células/links/gavetas.
- Reprodução1: selecionar Anexos na lista com subs ocultos; nativo mantém
  showSubs=false, fonte true e célula selecionada visível.
- Reprodução2: fechar Missão/clicar trilha; nativo abre gaveta e missionTab=conex,
  mudando mundo; fonte apenas seleciona link/popup, preserva gaveta/tab.
- Evidência: subagent-row-click/link-click-layout.
- Correção/reteste: aplicar pickAgent/link da fonte, distinguindo célula/lista,
  mostrando subs quando necessário e limpando form/link quando a fonte limpa;
  popup close/toggle sem abrir painel. Conferir relações/duties/resize/ocultação
  sem perder drafts legítimos ou tocar provider/sid.

### HM-F07 — [P1] Subárvores de form/chat/entrega/controls divergem

- Critérios: R03–R06/V02/V05/V06. Locais: drawers.js,hive.css,app.js estado
  visual reduced; templates/renderVals da referência vigente.
- Mesma fonte/DPR/fase: Nova operária Source Sans3 16px/700 versus Space Grotesk
  15px/600; especialidade14 versus14,5px; body gap7 versus grupos12; Simular de
  Andamento13,5 versus13px; form submit38 versus36px; stats entrega22/700 versus
  26/600; Fechar entrega38 versus30px. Modal/tipografia/paddings/gaps/badges/
  skills/tools/rows/alças/carets/símbolos divergem além de1px/exceções.
- Tags de conversa viram uppercase11px; fonte Space Grotesk14px/600. Ações de
  approval/fail aparecem em todo evento correspondente, fonte somente último.
  Entrega usa rótulos/estilos diferentes e não abre automaticamente após done
  como go da fonte. Checkbox não acompanha state.reduced/preferência do sistema
  (pares fonte ligada/nativo desligado com reduced=true).
- Evidências: inventories/bounds/styles em report.json; pares worker-form,
  idle-all-drawers,done-delivery,approval/fail; leitura dos templates/CSS.
- Correção/reteste: preservar valores/hierarquia/conteúdo/controles exatamente,
  só PNG/aviso como exceções. Corrigir estilosbase, sem patch CSS em cascata ou
  redesign Hub. Comparar todas subárvores/tabs/form/chat/log/entrega/drawers nos
  três viewports/estados e em movimento reduzido/normal. Exemplos não esgotam
  divergências: revisar campos/ações completos da fonte.

### HM-F08 — [P2] Gate QA passa sem conferir fidelidade e conteúdo

- Critérios: R14/V08 e qualidade das evidências V01–V07. Locais:
  tests/hivemind_visual_compare.mjs:25/29/38, browser_qa:78, testes Hive.
- Reprodução: comparador retorna ok=true neste candidato reprovado. Assert
  apenas header/queen/left/right/bottom/hud; nativeDetails registrados sem gate,
  diffs gravados sem aceite/reprovação; pares verificam somente doc-s1 out e um
  close. running=false/reduced=true não sincroniza integralmente pausa/switch.
  browser_qa ainda aborta HTTPS da referência/fontes: sua reference screenshot
  não prova fidelidade; comparador separado e instrumento próprio carregaram.
- Evidências: comandos independentes passing apesar de HM-F01–F07 e código QA.
- Correção/reteste: regressões significativas para F01–F06 e confronto de
  conteúdo/subárvores/estados reais pareados. Excluir somente regiões exatas PNG/
  aviso autorizadas, inspecionar diffs locais e não usar limiar global/tokens
  CSS como prova. Não enfraquecer suíte nem adaptar produção/ref ao harness.
  Suíte inteira+QA+veredito independente sobre novo candidato são necessários.

### Handoff

Resolver HM-F01–HM-F08 dentro do escopo aprovado, preservando passes de navegação,
sid/voz/mobile/isolamento/rig e monolitos cujo baseline foi confirmado. Congelar
novo candidato; nova matriz R01–R14/V01–V08, suíte e QA necessários. Não concluir
pela aprovação anterior de containers. Teto total3, sem ciclo extra automático.
Não há aprovação humana nova pendente para correções do escopo autorizado.

## Execução do ciclo 2 — 12/10/2026

Implementação: **GPT-5.6 Terra, high**. A primeira reprovação permanece
preservada acima; este registro não substitui o veredito independente pendente.

| Issue | Correção e evidência do implementador | Status |
|---|---|---|
| HM-F01 | O envio da conversa passou a ser `submit`; clique e Enter submetem uma vez, limpam o campo só após sucesso e continuam locais. QA Chrome exercita o clique. | Corrigida — aguarda verificação independente |
| HM-F02 | Troca de cenário limpa formulário/rascunhos e estados transitórios; vazia bloqueia CRUD e apresenta composição sem missão. QA Chrome cobre reset/controle desabilitado. | Corrigida — aguarda verificação independente |
| HM-F03 | Relações, lista de conexões e popup são derivados das conexões ativas, incluindo subagentes e operárias de demonstração; o sentido acompanha retorno. | Corrigida — aguarda verificação independente |
| HM-F04 | Progresso usa `floor`, totais e detalhe derivados; a faixa da etapa usa `STEP_PH`, inclusive subagentes. | Corrigida — aguarda verificação independente |
| HM-F05 | HUD oculto não ocupa área; efeitos específicos da Rainha e pausa/redução são representados sem afetar o rig PNG autorizado. | Corrigida — aguarda verificação independente |
| HM-F06 | Retestado: selecionar subagente revela subárvores; link preserva gavetas/aba e apenas alterna popup. | Corrigida — aguarda verificação independente |
| HM-F07 | Ajustados estados de entrega/chat/form e valores internos divergentes; conteúdo dinâmico de relações, aprovação, entrega e controles foi exercitado nos pares. | Corrigida pelo implementador — aguarda verificação independente |
| HM-F08 | Regressões de estado e navegador agora cobrem envio, vazio/CRUD, slots, subagentes, progresso, links e preservação de isolamento. O comparador continua evidência, não aprovação por contêineres. | Corrigida — aguarda verificação independente |

Validação do implementador: `pytest tests -q` = **235 passed**;
`codex_frontend_behavior.mjs` e `hivemind_frontend_behavior.mjs` passaram;
`hivemind_browser_qa.mjs` passou em Chrome isolado com as regressões explícitas
de envio e cenário vazio. Pares em três viewports e seis estados foram gravados
em `qa-ciclo2/`; áreas PNG do rig e o aviso de backend continuam as únicas
exceções autorizadas. Candidato do ciclo 2 congelado para a nova verificação
independente, sem alegação de aprovação.

### Handoff congelado para HM-08/HM-14

Estado final para leitura independente: fonte imutável
`HiveMind/prototipo/Hive Mind.dc.html` (SHA-256 registrado), runtime em
`HiveMind/frontend/static/` e gate em `tests/hivemind_browser_qa.mjs`.
O inventário efetivamente exercitado inclui Rainha, operária, subagente e
operária criada; abas Visão geral/Tarefas/Skills/Ferramentas/Relações;
Missão Plano/Responsabilidades/Conexões/Entrega; vazio, p2b a 50%, aprovação,
falha, concluída, formulário e link selecionado; três viewports e movimento
reduzido. O gate funcional reprova F01–F06 por conteúdo/estado e preserva a
isolação Hub. O comparador visual arquiva pares e diffs, mas **não usa limiar
global de pixels nem declara aprovação por contêineres**. A lacuna restante é a
avaliação humana/independente de fidelidade integral das subárvores e pixels;
não há falha conhecida HM-F01–HM-F07 após os retestes. Não modificar este
candidato antes do veredito independente.


## Reprovação independente formal — ciclo 2, 12/10/2026

**REPROVADO, GPT-6.1 Sol high.** Evidências `qa-verificador-ciclo2/independent/report.json`, `analysis.json`, pares e fingerprints. Código/testes/assets/protótipo somente leitura. Estes registros atualizam o status da tabela do implementador sem apagar o histórico. Última correção possível: ciclo **3/3**.

| Issue | Reteste independente ciclo 2 |
|---|---|
| HM-F01 | **Corrigida**: clique/Enter geram exatamente um usuário + p1a, input limpo e zero IA |
| HM-F02 | **Parcial**: resets/guard/CRUD vazio corrigidos; composição vazia e nota de aprovação incompletas |
| HM-F03 | **Parcial**: conexões ativas/criadas listadas, mas Relações/legenda/samples/sentidos/textos/contador não portados integralmente |
| HM-F04 | **Parcial**: floor/totais/segmentos corrigidos; detalhes/faixas/pausa/falha/plano/fixtures continuam incorretos |
| HM-F05 | **Parcial**: HUD hidden e cor/dash coord corrigidos; geometrias/seleção/sweeps/ripple/done diferentes |
| HM-F06 | **Corrigida nas reproduções**: subagente revela; link preserva gaveta/tab e popup fecha |
| HM-F07 | **Parcial**: números entrega26/600/Fechar30 e ações último evento corrigidos; demais subárvores/estilos/switch divergem |
| HM-F08 | **Pendente**: gate real falhou; cobertura continua sem confrontar omissões/detalhes/efeitos/estilos completos |
| HM-F09 | **Nova [P1]**: Queen não pausa; timer de autoentrega continua oculto |

### Correções requeridas agrupadas — sem ampliar escopo

**F02 — vazio integral.** Fonte HTML vigente linhas 125–135: quadro central 380px, logo72px, título “Esta colmeia ainda não tem agentes”, explicação e CTA. Linhas 253–268: seção esquerda “Uma colmeia reúne”, descrição Rainha/Operárias e ícones. `approvalNote`1307 deve ser “Sem missão neste exemplo.”. Nativo `hive.js render` só cria células vazias, `drawers.js:81` só introdução/CTA, `:87` mantém nota de etapa5. Reprodução: Colmeia vazia com três gavetas. Pares empty/empty-1280/empty-1920 mostram ausências. Reteste também done→empty→mission, form→cenário e restart/link; resets atuais devem continuar passando.

**F03 — seções e samples completos.** Fonte418–428 e1270: cada Relações (Rainha, 5 operárias, 2 subs e adições) inclui “Conexões na colmeia”, filtered conns, títulos/estado, sample44×12 navegável e seleção branca. Nativo `drawers.js:51–73` termina sem conns. Fonte571–586/1302–1303: Missão→Conexões inclui legenda dos **7 estados** out/flow/del/wait/done/idle/fail com rótulo, explicação e amostra exata, depois “Conexões agora”. Nativo:88 só introdução/lista. Fonte `trailSample`1013–1025 usa seta, base, pulsos simples6/12 ou duplos3/2/3/10, widths7/2, fail-X; nativo:18 e CSS `.hm-trail-sample` são traço/border genéricos. Fonte `linkTitle/connOf`1199–1204 reverte origem→destino in/ret, usa nomes reais da operária criada e LINK_INFO completo; nativo connectionRow mantém ↔/título fixture fixo e fallback genérico. Fonte popup138–147 separa label11px, título16px, sample+estado14/700, explicação e descrição com border-top; nativo hive.js popup reúne título e troca sample por statusSymbol, resume LINK_INFO. Fonte1333 agentCount=visible.length; nativo drawers:85 exclui subs: **6 vs8**. Pares mission-conex/documentos-relacoes/documentos-tools e 38 inventories comprovam. Reteste todas tabs/adições, subs on/off e out/in/ret/flow/wait/fail, navegação das relações e popup close/toggle sem abrir gaveta.

**F04 — derivados, fixtures e ticks completos.** Fonte status880–898 usa detalhe do progresso quando r[2] nulo; nativo hive.progressOf calcula, mas drawers:58 renderiza r[2] vazio. p2b50%: células11/23 e segmentos14 passam; faltam **11 de23 e-mails lidos /11 de23 clientes consultados /7 de14 anexos lidos /4 de9 e-mails lidos** no detalhe. Fonte1220–1238: fill combinado STEP_PH, paused em stepTag, failed “Etapa2 de7 falhou.”, approval papel/borda sólida e fail papel/borda tracejada; nativo renderMission:86 recria current preto inteiro, e updateProgress:98 só atualiza no ramo posterior: **pausa real deixa fill100%, sem Pausada**, mesmo em50%. Approval/fail ficam preenchidos indevidamente. Fonte plan1259–1263 peso atual700/restante400; nativo planRow:89 não aplica. `analysis.json.fixturesDifferences` confronta todas fases (campos extras internos não são falhas por si): há textos encurtados e **links adj1–adj5/p6a… omitidos**, tornando done/ret em idle. Exemplos fonte adj1 preserva doc-ana/cad-ana=done e q-ana=ret; nativo não. Fonte p2c label Entrega enviada; nativo Entregue. Portar semanticamente todas PH/a/l/LINK_INFO/status da fonte, sem resumir. Ajuste real agora marca adjusted emadj4 e23/3 passa; não regredir. Reteste avanço por tick, pausa/retoma, retry/adj1–adj5/novoapproval e mudanças de tab com progresso, não só saltos finais.

**F05 — efeitos exatos, sem genéricos.** Fonte QueenFx1129–1135: coord radius**62**, pontos62.35,10… (C mustard2.5/dash17.36 13.64); selected radius**67**, branco papel3px separado; done radius62/width3 e **hm-draw1.1s ease-out both**, sem efeito approval inventado. Nativo hive.js cellVisual:38 raio63, seleção altera face exterior raio72, CSS267–269 mantém hm-queen-ripple infinito approval/done. Fonte linksLayer1029: **6 sweeps** nos vizinhos radius56/width2/cadência1.8s+offsets. Fonte1060–1064: ripple pequeno1.1s escala1.8 em p1a/retorno e grande3 ondas2.4s escala6.5/delays.4 emdone; nativo não os cria. Fonte cellFx1118 usa radius(R−9) e dash proporcional(6ri/24)*.5 (7.875/7.875 worker e6.125/6.125 sub), nativo generic7/7. Fonte HUD1233 currentapproval papel, nativo mustard. Pares Queen-coord/Queen-done/approval/fail e queen-effects comprovam. Remover efeitos substitutos diretamente e portar os estados/seleção/nonce/cadências reais. Retestar animado, pausa/hidden e reduced, além de snapshots coerentes.

**F07 — subárvores exatas, não só exemplos.** Fonte form445–465: gap9, título **Space Grotesk15/600**, explicação **13.5**, inputs36px e submit36px, label10.5; nativo CSS186–190 título **Source Sans16/700**, gap12, texto14, inputs38/submit38; título y662 versus696.359 (Δ34.359), submit h38 versus36. Fonte ferramenta362–372 badge Space10.5/600/letter.08em/padding3×7 nos dois tipos; nativo CSS172 badge SourceSans/700 e padding só escrita. Fonte skills346 tem hexagonmostarda/gap7/lineheight1.3; nativo tags sem ícone. Fonte gerais284–319 usa grupos/gap12 e margin4; nativo tabBody161 usa lista plana/gap7. Fonte relações/divduties mantém símbolos/short, nativo omite/troca label. Fonte controlesAndamento button13px; nativo13.5: botão124.609×32 versus121.031×32, y317.062 versus318.437. Fonte form célula livre96–103 tem ＋ separado, texto/destino; nativo só “＋ Célula livre”. Fonte alças176–179/236 caret e badge20px/700; nativo sem caret/badges diferentes; waiting fonte hourglass, nativo diamante. Fonte entrega611–642 usa título12, descrição14.5/margin4, stats margin16/padding10×14/labels13 (“pedidos conferidos”), pedidos Space/600, nota13/margin14/padding12. Nativo CSS/drawers herda p16/margens padrão, stats10/padding8×10/labels16, “conferidos”, pedidos sem displayfont e nota alterada além do aviso necessário. **Fechar**13/padding12/w68.687/y164.594 fonte versus13.5/padding14/w74.328/y139.656 nativo. Fonte548…/bottom autorVocê10.5 uppercase com margem2; nativo14 sem essas propriedades. Checkbox continua false com state.reduced=true/preferência sistema; app.subscribe59–68 não sincroniza input. Pares form/tools/entrega/idle3viewports e `analysis.json.specificMetrics` confirmam valores, sem comparação button-versus-span como métrica. Portar integralmente os wrappers/props/styles/status da fonte, preservar fontes carregadas e exceçãoPNG/aviso estrita; substituir estilos-base e apagar genéricos redundantes. Reteste38combos, forms/chat/log/entrega e medidas ≤1px.

**F08 — gate e timer real da fonte.** Execução independente do gate abortou `tests/hivemind_browser_qa.mjs:72`: autoentrega cobre toggle-bottom. Fonte `go`819–828 e runtime `go` simulation:86–108 fazem autoabertura **400ms reduced /1600ms normal**, inclusive se modal foi aberto/fechado manualmente antes: isto é comportamento da fonte, não remover timer para passar teste. QA real fecha antes de callback pendente e continuaCRUD até a autoabertura interceptar clique. Cópia temporária esperou1700 antes de Fechar e resto passou. Teste deve aguardar autoabertura real e fechá-la, conferir ambos delays e cancelamento por cenário/restart, preservando assert/cliques sem force; não adaptar produção à temporização do harness. BrowserQA ainda abortaHTTPS/fontes de referência na linha78; sua captura não prova visual. Comparador/testes atuais não detectam F02–F07/F09. Acrescentar regressões efetivas por campos/estados/subárvores/efeitos e confronto pareado local; tokens/containers não aprovam. Python235 e Node passaram, mas gate real permanece falho.

**F09 [P1] — lifecycle de peças novas.** R10/V06/V08. Reprodução1: p2b normal, Pausar. report `queen-motion-real-pause`: rootpaused=true, wingpaused, porém Queen **running/1.8s**. CSS256 pausa `.hm-cell-fx-coord`, mas novo `.hm-queen-fx-coord`267 não casa. Fonte animações respeitam paused. Reprodução2: sim.go(done,delivery:false) normal e imediatamente `hubProviders.selectPage('claude')`;1750ms oculto. `hidden-auto-delivery-synchronous`: delivery**false→true** com pageclaude, contrariando suspensão/tempo restante R10. simulation.setLifecycle33 só congela timer de fase e não deliveryTimer105. Preservar delay400/1600 e suspensão/retomada do tempo restante; pausa/hidden afetam todos efeitos novos. Reteste visibilidade/página durante delay, pausa manual, 4reentradas e reduced, sem timers/listeners duplicados nem fase/modal avançando ocultos.

Handoff final: corrigir as seções completas acima no **último ciclo3**, com port direto da fonte, removendo substitutos/sobras, sem refatorar Hub/backends/assets. Preservar seis sessões/sid/voz/mobile/guardas/rig/invariantes. Novo congelamento e aprovação independente explícita são necessários; testes passing ou afirmações do implementador não encerram a tarefa.

## Implementação e reteste do ciclo 3 — 12/10/2026

Implementador: GPT-5.6 Terra high, único escritor. F04 recebeu fixtures, progresso parcial, detalhes, pausa/falha/approval e plano; F05 recebeu overlays separados da Rainha, sweeps, ripples e dash proporcional; F07 portou a estrutura de célula livre, formulário, skills, badges de ferramentas, entrega, chat e alças; F08 passou no Chrome real com entrega automática normal/reduced e suspensão por página. A fonte permaneceu read-only com SHA256 `03B05ACDDD71DA6C6C2E81D3AE14ADC6B08D4EBB340E44C1CE3D41A92CF8DAD6`; rig PNG e aviso de backend foram preservados. Evidências estão em `qa-ciclo3-comparator/`. Isto é handoff para revisão independente, não aprovação final.


## Diagnóstico independente FINAL — ciclo 3/3, 12/10/2026

**REPROVADO, GPT-6.1 Sol high. Três ciclos utilizados; interromper, sem ciclo4 automático.** Código/testes/assets/fonte permaneceram inalterados durante revisão. Evidências `qa-verificador-ciclo3/independent/report.json`, `analysis.json`,27 pares e fingerprints. Gates pytest235/Node/Chrome/comparador passaram; não comprovam os critérios visuais/dinâmicos abaixo.

| Issue | Estado final |
|---|---|
| HM-F01 | Corrigida; clique/Enter únicos, input limpo, zeroIA |
| HM-F02 | Parcial; reset/guard/conteúdo básico passam; composição/fit/estado das gavetas vazio divergem |
| HM-F03 | Parcial; todas Relações/legenda/contador/listas/sentidos adicionados; popup e samples não preservados integralmente |
| HM-F04 | Parcial; snapshots50%/floor/fases/links/plano melhoraram; detail/ticks/approval/pausa/info restantes falham |
| HM-F05 | Parcial; overlays/cadências adicionados; animações reais/cores/keyframes/estados divergem |
| HM-F06 | Corrigida; subagente revela e links preservam gaveta/tab |
| HM-F07 | Parcial; formfont/badges/input/entrega melhoraram; subárvores/styles >1px persistem |
| HM-F08 | Parcial; gate real passa, mas não detecta as falhas demonstradas; código substituído emCSS não removido |
| HM-F09 | Corrigida; Queen pausa e autoentrega congela tempo restante, retoma;400/1600 preservados |

### Pendências necessárias confirmadas no último candidato

**F02 — composição vazia.** Fonte HTML125–135 mantém card380px **dentro do mundo único** emleft−190/top−150 e sob fit/world transform; runtime hive.js cria `emptyCard` emscene, CSS `.hm-empty-card` centraliza50%/50% sem escala/reserva de gavetas. Mesmas três gavetas1440×900: título equivalente tem **ΔY+112,4078px/ΔW+99,6973px**; CTA central é coberto pelo bottom. Pares empty nos3viewports comprovam. Fonte253–268 usa gridíconesSVG+textos14/1.4; nativo `.hm-empty-explain` substitui por caracteres Unicode/p13.5/1.35. Fonte vazia conserva head/badge deMissão e Plano7etapas (snapshot referência); runtime renderMission troca head/removebadge/substitui tabs por mensagem genérica. Conteúdo aparecer não satisfaz igualdade de composição/estados. Esperado: exatamente source transform/wrappers/tabs, salvoPNG/aviso; observado conforme pares.

**F03 — popup e amostras.** Fonte138–147 separa labelConexão11px, título16px, **trailSample44×12+estado14/700**, explicação e descrição com border-top/padding8. Runtime `hive.js` ainda usa “Conexão · título” único14px, statusSymbol em vez da amostra, psemhierarquia/border. Reprodução: clicarq-ana emp3b(in) oudoc-s1/subvisível; popup seleciona/fecha sem abrirdrawer, mas conteúdo/estrutura visual divergem. Fonte `trailSample`1013 usa strokes/flowvar `--cyc:-18px`; nativo `.hm-sample-pulse` reutiliza hm-flowfixo−72px: pulsos de legenda/lista têm percurso/cadência incorretos. Fonte Conexões571–586 rótulos emstrong e gap10; runtimelegend agrega texto simples e gap12. Listas retornam nomes corretos e contador8 passou; manter esses passes. Pares mission-conex/relations-return/return-popup e inventory38.

**F04 — detalhe e bordas durante ticks reais.** Reproduzir p2b comDocumentos selecionado **em execução**, aguardar1950ms. Observação `real-tick-progress-and-effects`: progress0,549194, célula**12de23**, detalhe ainda **0de23 e-mails lidos**. `drawers.updateProgress` atualiza segmentos/contador e não o texto deprogress.detail; pause reconstrói e então corrige para12. Fonte status880–898/forceUpdate805 atualiza texto a cada tick. Reproduzir approval ativa,220ms: currentbackground **gradient100%preto, border0**, apesar de render classpaper; fonte1220–1226 pede papel/borda1.5sólida/fill0 (failtracejada). updateProgress sobrescreve estes estados e CSS não definepaper/border adequadamente. Pausa foi acrescentada **depois da phaseCopy**; fonte1236–1238 acrescenta no **stepTag strong**, antes dephaseText, alterando informação/bold/layout. Uma fixture ainda resumida: p2b.Análise “Depende das duas entregas.” versus “Depende das entregas de Documentos e Cadastros.” (analysis.fixtureDiffs). Subagenteidle fonte“Acionado por Documentos quando houver leitura.”, nativo“Sem tarefa no momento.”; adições fonteSpecdefault“Especialidade a definir”/missão“Operária criada por você nesta demonstração. A missão ainda não foi definida.”/estado“Sem tarefa nesta missão.”, nativo textos alternativos. Inventários38+added-worker confirmam. Todas informações integrais são obrigatórias; snapshotsgo finais não provam ticks.

**F05 — efeitos reiniciados e valores diferentes.** `hive.render` usa **effects.replaceChildren() em todo emit100ms**, recriando sweeps/ripples. Probe1950ms: referência guardada perdeu conexãoDOM e seis animações novas currentTime0/opacity0; delays.3–1.5s não conseguem progredir. Fonte linksLayer1029/1060–1064 usa keys/nonce e preserva os nós entre ticks. Fontekeyframes24–25: sweepopacity0→1em8%→0em36%, semscale; nativehm-sweep cresceparaopacity.8/scale1.12. Fonte ripplecomeçascale1/opacity1; nativo.82/.8. Fonte pequenaonda também emadj1/adj4 (q-* in); runtime hardcodesp1a/p3b/p7a/done e omiteajustes. Fonte QueenDone1129–1135 usa **mustard#B8860B** emraio62/width3; runtime `.hm-queen-fx-done` usa**preto**. Source marchusa`--off` específico (Queen−62px, worker−31.5, sub−24.5); nativo keyframefixo−28. SeleçãoQueen ainda altera stroke daface exterior3px, sourceface2px+ring67separado. Dash proporcional/raios/pausa novos passaram, mas valores/continuidade/sourceestados restantes falham. Critérios exigem animaçãoreal e snapshot, sem genéricos substitutos.

**F07 — subárvores/medidas acima de1px.** Pares com fontesloaded eDPR1: Documentos→Relações botãoMostrarSubs nativo fica emlinhaseparada àesquerda **ΔX−192,8125px/ΔH+10px**,fontsize13.5/padding14 versus fonte12.5/padding10/h28. Fonte397–401 põe label ebotão namesmalinhaflex; nativo `.hm-subs-detail` segueflatappend. LabelsRecebe/Entrega11 versus10.5; símbolos/short dasduties e carret/alças ainda substituídos/omitidos; waitingpermanece diamante versusSVGhourglass. Skills **Space10.5/600** e chips3×7 nativos versus fonte346 **SourceSans13.5/400/line17.55** comSVG8×9/padding5×10×5×8. Form títuloAgoraSpace15/600 passou, mas **Y−9,0156px** persiste: nativo renderiza form-errorvazio permanentemente comoitemflex, enquanto fontehasFormError sóinsereseerro, além dewrappers. Geral usa lista plana label/p/gap12 versus gruposlabel+texto/margem4 dafonte284–319; “Estado”Y+8,2188px. Entrega title **weight700 versus600**,label11 versus12, pedidos semSpace600, h2margens/letterspacing diferentes; Fecharcontrole corresponde, masY−7,4219px. BadgesdeFerramentas agora têmfont/tag corretos, porém rows são itensflatgap12 ao invésdewrapperrowscontíguas, alongando listagem. Vazio/card/cabeçalhos são F02. Não computar largura/padding rawleaf-versus-wrapper como prova; deltas citados são controles/títulos semanticamente correspondentes, os demais têmcontrasteCSS/DOM/fonte explícito. Comparar todas38tabs e estados necessários, não só exemplos citados.

**F08 — sobras e cobertura.** `hive.css` conserva `.hm-worker-form>strong` Source16/700 e adiciona novoSpace15/600 emoverride; input38 repetido depois36; tags13.5 depois10.5; `.hm-tool strong` já não corresponde ao span.hm-tool-access; `.hm-trail-sample` bordergenérico antigo depoisoverrideborder0; `.hm-tab-body` gap7 depois12. São trechos diretamente substituídos nesta mudança, contrários à remoção/minimalidade e semport estruturalexato. GatebrowserQA agoraespera autoentrega e passa400/1600/hidden; F09 foi validada independentemente (remaining1586.2ms constanteoculta,deliveryfalse→truesóapósretorno). Porém gatesnãoverificam detalhe avançandoporms, bordas após ticks, continuidade deefeitos ou popup/subárvore/font/layout exact. Captura browserQA aindaabortaHTTPSfonte; fontloaded foi comprovado pelo instrumento/comparador separados. GatespassingnãoaprovaF02–F07. Nenhum teste necessário ficouskipado, nenhuma falhaambiente impede diagnóstico.

Encerramento do verificador: fonte/assets/protectedchecks íntegros; revisão somenteleitura, relatório/issues append e artefatostemporários apenas. Não implementar correções apósterceirareprovação. Sessãoprincipal deveapresentar o diagnóstico ao usuário e aguardar decisão explícita paraqualquer continuação.


## Diagnóstico independente FINAL — ciclo 4 adicional autorizado, 12/10/2026

**REPROVADO**, GPT-6.1 Sol high, candidato congelado somente leitura.
Quatro ciclos contabilizados; nenhum quinto automático. Relatório completo e
matriz R01–R14/V01–V08 em verificacao.md; evidências `qa-verificador-ciclo4/`.
235 pytest passaram na execução direta; Node Hive/Codex e comparador passaram.
O gate browser real falhou duas vezes no literal12 após1950ms (observou13);
instrumento temporário com igualdade célula/detalhe passou restante. Não se
atribui esse literal temporal a regressão semântica do progresso corrigido.

| Issue | Estado C4 |
|---|---|
| HM-F01 | Corrigida, clique/Enter únicos e input limpo |
| HM-F02 | Parcial: card/world e Plano corrigidos; cabeçalho vazio/educação inexatos |
| HM-F03 | Parcial: sample -18 e legend strong corrigidos; nove descrições ainda resumidas |
| HM-F04 | Parcial: PH24/detalhe/ticks/bordas corrigidos; Pausada pósnav e fill ajuste divergentes |
| HM-F05 | Corrigida nas pendências anteriores; efeitos preservam nós/clock, valores e pausa |
| HM-F06 | Corrigida, subagente/seleção de link preservam contexto |
| HM-F07 | Parcial: várias fontes/wrappers corrigidas; controles/intro/entrega/alças ainda diferem |
| HM-F08 | Parcial: sobras popup e gate temporal/cobertura incompleta |
| HM-F09 | Corrigida, tempo restante autoentrega/pausa/ocultação/reentradas |

### Pendências necessárias e reproduções

**HM-F02 — R03/R05/V02/V05.** Abrir três gavetas e Colmeia vazia. Esperado:
header Missão/objetivo/Limites e lateral source253–268. Observado: header troca
objetivo e omite Limites; título lateral18,72/700 Source Sans versus18/600 Space,
x12 versus20; CTA38/13,5/pad14 versus36/14/pad16. Locais drawers.js renderLeft/
renderMission:93 e estilos educativos. Pares `native/reference-empty*.png`.
Card central/world agora coincidem; não repetir diagnóstico antigo do card.

**HM-F03 — R07/V05.** Selecionar q-doc e doc-s1, inclusive estados de retorno.
Esperado: descrição inteira de LINK_INFO source. Observado: q-doc omite “a
Documentos”; doc-s1 omite “Documentos repassa os anexos em PDF ao subagente...”.
Nove de dez descrições diferem; fonte/info completas em report.json observação
fixtures-source-runtime/return-popup. Local demo-data.js LINK_INFO e hive.js
popup. Samples/keyframes -18 e strong de legenda estão corrigidos.

**HM-F04 — R05/V06.** Coleta p2b, Pausar, Claude→Hive. Esperado strong
“Etapa 2 de 7. Pausada.” antes da descrição como source1236–1239. Observado
strong perde Pausada, texto final recebe sufixo, elapsed2080,4 inalterado.
Local drawers.js updateProgress:101–108, observação pause-copy-after-navigation.
Em approval→Solicitar ajuste, barra current começa0/cresce, enquanto fonte
renderVals1226 retorna50 quando STEP_PH[5] não existe. Local simulation.js
stepProgress. PH24 e detail real agora passam; não restaurar textos antigos.

**HM-F07 — R03–R06/V02/V05/V06.** Abrir Conexões com três gavetas em1440×900,
fontes loaded. Intro nativa16/normal/altura66 contra13,5/18,9/37,78125;
linhas correspondentes Y+30,84375 e label Conexões agora Y+34,84375. Local
drawers.js:95 p sem estilo/hive.css:219. Avançar etapa13,5/pad14 versus13/pad12,
W+7,484375; tabs inativas400 versus500; alça inferior Source Sans em vez de
Space/W−35,390625/carets ausentes. Entrega labels16 versus13, pedidos Source400
versusSpace600, FecharY−7,421875. Form títuloY+2. Responsabilidades permanece
plana sem símbolos/short source. Pares e controles medidos em analysis.json;
não comparar folha e wrapper como se fossem controles equivalentes.

**HM-F08 — R14/V08.** hive.css:98 popup-state gap7/600 substituído pelo
override:289 gap10/700; popup-head strong:95 e popup p:97 já sem correspondência
na árvore atual. Esperado remover estilos diretamente substituídos e validar
as projeções exatas. Gate real tests/hivemind_browser_qa.mjs:57 tem literal12
após1950ms e falhou duas vezes com13; instrumento temporário confirmou que
célula/detalhe concordam. Preservar testes/protótipo; revisão não os alterou.

Estado integrado não aprovado. A coordenação deve apresentar diagnóstico e
aguardar decisão explícita para qualquer continuidade após este ciclo4.


## Diagnóstico independente FINAL — ciclo 5 autorizado, 13/10/2026

**REPROVADO**, Sol6.1 high, cinco ciclos totais, sem sexta rodada automática.
Relatório curto/matriz reaberta em verificacao.md; evidências qa-verificador-ciclo5.
235pytest/16,21s e Node2 passaram; browser real falhou linha58 em fill51 versus
assert50 com clock ativo. Não alterar candidato/testes na revisão.

- **F02 parcial — R03/R05/V02/V05:** três gavetas→Colmeia vazia. Objetivo/Limites
  e título18/600 Space corrigidos, mas títuloY−10,8125px, label11 versus11,5,
  CTAY+1,1875px. Esperado composição source; observado nos15pares/3viewports.
- **F03 parcial — R07/V05:** selecionar doc-ana/cad-ana. Esperado descrição
  começa “Dependência: Análise só começa...”; observado começa “Análise só
  começa...”. Local demo-data.js LINK_INFO. Oito outras descrições passaram.
- **F04 corrigida:** pausa pósnav preserva strong/texto/elapsed; cinco ajustes50%.
- **F07 parcial — R03–R06/V02/V05:** alça conversa ainda Source Sans em vez de
  Space/W−15,390625px; fonte `.hm-page button` prevalece sobre `.hm-pull`.
  Conexões agoraY−15,375; formtitleY+2. Rainha→Relações em p2b mostra os status
  longos onde source usaTrabalhando/Aguardando (drawers.js renderDetails).
  Missão→Responsabilidades usa rows sem wrapper/margem source; diferenças
  acumulam. EntregaFecharY−5,421875; labels/IDs fonte correta agora passaram.
  Esperado controles/títulos/shorts source, tolerância1px. Observado em
  independent/report.json e analysis.json; fonte/fonts loaded/DPR1 e frames iguais.
- **F08 parcial — R14/V08:** CSSpopup obsoleto citadoC4 removido; gate real ainda
  exige literal50 em setupclockativo (tests/hivemind_browser_qa.mjs:58).
  Atualizador/progresso não foi reprovado apenas por esse assert temporal.

F01/F05/F06/F09 e protegidos permanecem conforme hashes/evidênciasC4. Código,
testes, assets e referência intactos durante revisão. Não iniciar sexta rodada.


## Diagnóstico independente FINAL — ciclo 6 autorizado, 13/10/2026

**REPROVADO**, Sol6.1 high independente; seis ciclos totais, sem C7 automática.
235pytest/14,30s, Node2 e browserQA real passaram. Fonte/PNGs/protegidos intactos;
fingerprint formal zero alterações. Relatório e15pares em qa-verificador-ciclo6.
F02/F03/F04/F08 corrigidas; passes F01/F05/F06/F09 preservados. F07 permanece
parcial por uma única pendência concreta nos controles da Missão:

- **R03/R05/V02/V05/R14:** abrir Missãoidle/Coleta pausada/conclusão. Fonte pede
  padding0 14px em Simular missão/Continuar/Simular novamente, e0 12px nos outlines.
  Observado: hive.css:205 `.hm-controls button` usa12 em todos. Botão primário
  W−4px; Avançar/Reiniciar seguintesX−4px nos três viewports, fonte/altura/Y iguais.
  Evidência: independent/analysis.json e pares connections/form/delivery/
  responsibilities. Controles semanticamente equivalentes, fontes loaded/DPR1;
  limite autorizado1px. Preservar os demais controles e correções aprovadas.

Alça/Conexões/form/entrega/educação e responsabilidades alvo foram corrigidos.
Rainha→Relações mantém labels curtos; Missão→Responsabilidades mantém detalhados,
como source568. Não aplicar a regra de short labels ao contexto errado.
Sem alterações do candidato ou novos testes/QA depois do diagnóstico. Não C7.


## Encerramento independente — ciclo 7 autorizado, 13/10/2026

**APROVADO**, Sol6.1 high independente. F07 encerrada: regra exclusiva dos
primários restaura padding14, secundários12; nove controles/3estados com
deltasX/Y/W/H0px em1440×900, fontes loaded. Fonte/69outrosarquivos/testes intactos;
CSS reconstruído em memória confirma somente uma linha adicionada.
Reutilizados235pytest/Node/browserQA aprovadosC6 por autorização expressa.
Todas as Issues e critérios necessários atendidos no candidato finalC7.
Sete ciclos contabilizados; nenhumC8automático. Evidências qa-verificador-ciclo7.
