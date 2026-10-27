# Verificação — Hive Mind no Hub

> **Status em 21/10/2026: CONCLUÍDA** — aprovada na verificação independente do ciclo 7 (13/10/2026). Este arquivo é registro histórico do processo e pode descrever intenções já superadas; a referência do código atual está em `docs/hivemind/README.md`. As capturas de QA foram movidas para `.qa-arquivo/2026-10-10_hivemind-frontend-hub/`; caminhos `qa*/` citados abaixo são relativos a essa pasta.

Data inicial: 10/10/2026. Verificação independente final: 13/10/2026. Faixa completa. Ciclos utilizados: **7 totais — três originais e quatro adicionais autorizados**.
Veredito global atual: **APROVADO na revisão independente final do ciclo 7**. F07 encerrada; critérios necessários atendidos com evidências reaproveitadas autorizadamente. Histórico preservado; sem C8 automática.
Planejador GPT-6.1 Sol high não é o verificador independente desta tarefa.

## Evidências do planejamento

Leitura do AGENTS.md, docs/desenvolvimento.md, CLAUDE.md, docs/frontend.md, docs/codex-frontend.md, docs/arquitetura.md e trechos de docs/servidor-api.md. Inspecionados index.html, server.py, codex_frontend/static/providers.js, routes.py, tests/test_codex_frontend.py, tests/codex_frontend_behavior.mjs, protótipo Hive Mind.dc.html e bee-animation/README.md/bee.js/bee.css.

Confirmados por código:
- providers seleciona somente claude/codex e associa seleção à sessão. Hive requer página separada.
- MAX_TABS e MAX_SESS são seis; entrar Hive não pode chamar addTab.
- Guarda mic atual depende da troca de aba; Hive conserva aba e exige rechecagem da página.
- askAndSpeak guarda pelo provider após STT; bloqueio global Hive interromperia turno legítimo.
- Handler global Enter/Espaço/Esc e foco automático mobile não conhecem Hive.
- Referência usa runtime DCLogic/React/support.js; rig dispõe de montagem DOM e três PNG alinhadas.
- Protótipo contém sete etapas, revisão/ajuste/aprovação, falha/retry, três gavetas, relações e entrega simulados.

Nenhum código/teste foi alterado pelo planejador. Nenhuma suíte/teste comportamental/QA foi executado nesta etapa. Visual final não foi verificado por leitura de código. A movimentação para HiveMind/prototipo será feita na implementação autorizada, não pelo planejamento.

## Execução exigida

1. Baseline: ./.venv/Scripts/python.exe -m pytest tests -q; registrar resultados anteriores/falhas de ambiente.
2. Focado: ./.venv/Scripts/python.exe -m pytest tests/test_hivemind_frontend.py tests/test_codex_frontend.py tests/test_frontend_static.py tests/test_dock_redesign.py -q.
3. Comportamental: node tests/hivemind_frontend_behavior.mjs e node tests/codex_frontend_behavior.mjs. Se Node não estiver no PATH, localizar runtime disponível sem instalar dependência desnecessária; registrar caminho/resultado. Testes usam módulos/caminhos reais, não cópia da implementação.
4. Suíte final: ./.venv/Scripts/python.exe -m pytest tests -q.
5. QA navegador: servidor isolado e endpoints/serviços de voz/IA stubados. Sem iniciar processos Claude, mic real ou alterar Hub ativo do usuário. Conferir erros console/rede e capturas. Testes não baixam modelos nem acessam IA real.
6. Revisão independente final: novo agente Sol6.1 high; leitura de diff/inventário/PRD/plano; executar checks e conferir cada requisito; relatório com veredito explícito.

## Cenários comportamentais mínimos

- Entrar Hive a partir de Claude e Codex e voltar; sessão/sid/modelo/esforço/rascunho/gavetas preservados. Entrar com seis sessões. Nenhum tab.provider Hive.
- Navegação real executando guards e lifecycle de providers/app, não apenas mock com canUseAssistantUI=false. Separar página/provider, inicialização tardia, preferência persistida e transição para painel completo.
- Enter/Espaço/Esc em campo, botão, superfície Hive e dialog entrega: somente Hive/navegador; controles Hub hidden/inert não recebem foco. Mic/IA/endpoints não chamados por ações Hive.
- Mic deferred: iniciar em Claude idle, selecionar Hive antes de aquisição, resolver promise; todas tracks stopped, nenhum MediaRecorder/meter.
- Voice deferred: enviar áudio Claude, /stt pendente, selecionar Hive, mudar preferências visíveis, resolver STT; /ask conserva sid/modelo/esforço do turno e continua, sem callbacks mudarem a página. Claude /ask e fala existentes também continuam.
- Mobile ask/step/done em Hive: espelho atualiza; active sid e selectedPage não mudam. Regressão Codex permanece coberta.
- Missão→approval→approve→done; approval→adjust→approval→approve→done (três divergências); fail→retry→aprovação; vazio→missão.
- Clock pausado, retomar, nextStep, reiniciar; esconder/restaurar página e document.hidden; nenhuma fase avançada enquanto oculto, pausa manual não retomada por visibilitychange.
- Seleção de todas categorias, mostrar subagentes, todas abas de gavetas e conexões/popup/sentidos; criar três/remover/recriar operárias; nome obrigatório/limites; nenhum dado do simulador aparece no transcript Claude/Codex.
- String com markup em nome/chat é exibida como texto, sem eventos/script.
- Reduced-motion sistema/toggle: todas asas/fluxos/transições estáticos sem remover informação; loops/observers/listeners não duplicados em entradas repetidas; galáxia Codex não roda sob Hive.
- Rotas static e assets respondem corretamente; inexistem Hive /ask,/stt,/session_start,/session_reset,/abort,/speak; traversal bloqueado; nenhum importruntime/backends pessoais.
- Inventário/hashes antes/depois da movimentação, seis PNG e demais arquivos de referência preservados; protótipo e prévia ainda abrem seus assets relativos.

## QA visual requerida

Comparar HiveMind/prototipo/Hive Mind.dc.html com runtime servido, registrando páginas/larguras:
1440×900 e 1920×1080: Missão idle/working/approval/done, Colmeia vazia, falha, subagentes, conexão selecionada, cada gaveta e entrega.
1280×800: três gavetas abertas/fechadas e alcance de textos/ações. Identificar restrições do protótipo sem chamar recorte irrecuperável de aprovado.
Revisitar Claude/Codex para confirmar telas/gavetas reais. Registrar screenshots locais e diferenças intencionais (aviso explícito, navegação Hub, acessibilidade). Não exigir igualdade pixel a pixel das informações de integração, mas preservar composição e conteúdo completo.

## Matriz do ciclo 1

| Critério | Resultado | Evidência |
|---|---|---|
| R01–R14 (cada um deve receber linha própria na verificação) | Não executado | Planejamento apenas |

O verificador deverá substituir esta linha agregada por resultados individuais, sem apagar histórico do planejamento, e indicar: passou/falhou/não verificável; comando/reprodução/captura; risco pendente.
Aprovar somente quando nenhuma verificação necessária estiver ausente. Suite passing não substitui QA/interação real.

## Histórico de ciclos

- Ciclo 1: reservado; implementação liberada; seis ganchos index autorizados explicitamente (“Autorizar os seis ganchos”); modelo Sol5.6 high autorizado excepcionalmente.
- Ciclos 2/3: não iniciados, somente após reprovação. Contador não reinicia.

## Evidência complementar — nova referência após substituição humana

Planejamento retomado somente leitura. Referência vigente em HiveMind/prototipo/Hive Mind.dc.html identificada por mtime20:15:26.774UTC/134879bytes e SHA25603B05ACDDD71DA6C6C2E81D3AE14ADC6B08D4EBB340E44C1CE3D41A92CF8DAD6. Hashs dos seis arquivos atuais registrados no plano. Não restaurar antigo nem comparar inventário21/21 como falha após atualização expressa do usuário.

Inspeção visual das imagens históricas qa/reference-1440x900.png, runtime-1440x900-working.png e runtime-1280x800-drawers.png: nativo anterior já simplificava fonte/nav/HUD/contornos/rotas/form/gavetas. Elas são anteriores ao novo protótipo e não validam V01–V08. .thumbnail atual também visualizada: mostra gradientes, relevo e abelhasSVG, mas sua resolução640px/corte não substitui captura integral nova.

Leitura dos arquivos nativos app.js,hive.js,geometry.js,hive.css,layout.css,drawers.js,simulation.js e regrasHive do codex.css confirma divergências estruturais/dimensões/efeitos específicas inventariadas no adendo. Layout.css contém cinco overrides; substituir diretamente estilosbase e remover folha/import redundantes.

Leitura dos testes:
- test_hivemind_frontend.py exige arquivos bee-animation/ZIP do protótipo anterior que usuário substituiu; atualizar assert do inventário conforme seis arquivos atuais, sem alegar regressão da movimentação.
- hivemind_browser_qa.mjs aborta URLsHTTPS incluindo fonts, injetaReact para referência, aguarda .hm-bee-asset ausente no HTML vigente e captura fases distintas (referenceidle/runtimeworking). Harness precisa preparar fonte/estado da referência atual e comparar capturas pareadas antes de alegar fidelidade.
- Testes de estado/isolamento continuam necessários. Presença de stringsCSS/abas não valida V02–V06.

Nenhum teste ou captura nova executado pelo planejador. Nenhum código/teste/protótipo alterado pelo planejamento. Mudança de requisito permanece no ciclo1/3; sem reprovação independente inventada.

### Matriz adicional obrigatória

| Critério | Estado atual | Evidência exigida para liberar |
|---|---|---|
| V01 | Baseline por leitura/hashes registrada; QA nova pendente | Hashs atuais preservados e capturas recentes completas |
| V02 | Pendente | Bounds/fonte/lineheight/padding source × runtime, diferenças até1px de arredondamento |
| V03 | Pendente | Stops/direção/distribuição de gradientes, biséis/sombras e visual pareado |
| V04 | Pendente | Um mundo/transform; mesh/célula/link alinhados; routes/source e direção/pulsos reais |
| V05 | Pendente | Todas gavetas/detalhes/badges/forms/chat/entrega com hierarquia e dimensões exatas |
| V06 | Pendente | Idle/p2b/approval/fail/done/selected/sub/link/form/drawers, estado/progresso pareados |
| V07 | Decisão opcional apresentada pela coordenação | PreferênciaPNGvsSVG registrada, exceção limitada/documentada casoPNG |
| V08 | Pendente | Sem sobras, fontes/JS preparados, testes/suíte/QA/verificador independentes passing |

Gerar capturas novas em diretórioQA distinto (exemplo qa/referencia-atualizada/), preservando qa anterior como histórico. Comparar por região/overlay e métricas locais, sem limiarglobal esconder alterações de layout. Fonts efetivamente carregadas/DPRigual/sameviewport e freeze de animações para snapshots. PNGexceção só região exata de personagens, com dimensão/posição conferidas manualmente. Não aprovar sem capturas referência nova × runtime na mesma fase/configuração e veredito independente do estado final.

## Evidência do implementador — 12/10/2026 (antes da revisão independente)

Executada por GPT-5.6 Terra, high. Estes resultados não substituem o veredito
do verificador independente.

| Critério | Resultado do implementador | Evidência |
|---|---|---|
| R01 | Passou | Chrome isolado: Hive entra com seis abas e retorna a Claude/Codex sem trocar provider/sid. |
| R02 | Passou | Aviso backend pendente, simulação local e endpoints stubados no QA. |
| R03 | Passou na comparação implementador | `qa-atual/metrics.json`; bounds principais até 1 px; pares regionais e inspeção manual. |
| R04 | Passou | Gaveta de agentes, detalhes, subagentes e contadores nos pares e QA. |
| R05 | Passou | Andamento, HUD, aprovação/ajuste/retry, tabs e conexões cobertos. |
| R06 | Passou | Conversa local, entrega, quatro/três divergências e modal cobertos. |
| R07 | Passou | p2b/subagente, rota selecionada, sentidos e popup pareados. |
| R08 | Passou | Cenários e CRUD; limites 16/40, XSS como texto e remoção/reuso de slots verificados no Chrome. |
| R09 | Passou com exceção autorizada | Rig PNG preservado em 64/56/40/26; comparação não declara igualdade de pixels dos personagens. |
| R10 | Passou | Pausa manual/documento e reduced motion verificam pulsos, contornos e rig. |
| R11 | Passou | QA verifica ações Hive sem endpoints de assistente e entrada tratada como texto. |
| R12 | Passou | QA cobre mic diferido, continuidade STT, mobile sem foco e retorno. |
| R13 | Passou | Módulos ES nativos/blueprint estático; React/support apenas no harness. |
| R14 | Pendente de verificador | Regressões passaram, mas aprovação independente ainda é requisito da faixa completa. |
| V01 | Passou | Referência/hash preservados; capturas novas em `qa-atual/`. |
| V02–V06 | Passou no escopo implementador | Três viewports idle e seis pares congelados por estado, com diffs header/left/world/right/bottom. |
| V07 | Passou com exceção limitada | PNG autorizado e documentado; aviso/backend obrigatório mantido. |
| V08 | Pendente de verificador | Sem sobras conhecidas; ainda requer leitura independente final. |

Comandos finais: `./.venv/Scripts/python.exe -m pytest tests -q` → **235
passed**; `node tests/hivemind_frontend_behavior.mjs` e `node
tests/codex_frontend_behavior.mjs` → passaram; `node
tests/hivemind_browser_qa.mjs .../qa-atual-functional` → passou; `node
tests/hivemind_visual_compare.mjs .../qa-atual` → passou e gravou 3 pares idle
e 6 pares de estado. Nenhum processo Hub, Claude, microfone real ou serviço IA
foi iniciado por esses testes.

Estado de entrega: **candidato congelado, aguardando revisão independente
GPT-6.1 Sol high**. Não declarar conclusão nem iniciar ciclo 2 sem o veredito.

## Verificação independente formal — ciclo 1, 12/10/2026

Verificador **GPT-6.1 Sol, high**, independente, sem participação no código.
Preparação anterior foi exclusivamente referência. Não alterou produção,
testes, assets ou protótipo; somente instrumentos temporários/evidências e
estes registros. Histórico Sol5.6 autorizado → handoff → Terra high preservado;
a lista exposta não provou indisponibilidade do Terra.

**Veredito global: REPROVADO sobre o candidato congelado recebido.** Testes
passing não substituem os comportamentos/conteúdo/fidelidade que falharam.
HM-F01–HM-F08 em `issues.md` exigem correção no ciclo 2 e novo congelamento.
Nenhuma reprovação formal anterior; ciclo 1 consumido, ciclos 2/3 não executados.

### Integridade e superfície

- `qa-verificador/fingerprint-start.json` e `fingerprint-end.json` confirmam
  candidato inalterado durante a revisão. HTML referência SHA
  `03B05ACDDD71DA6C6C2E81D3AE14ADC6B08D4EBB340E44C1CE3D41A92CF8DAD6`;
  seis arquivos/hashes verificados, sem restaurar inventário histórico 21/21.
- `baseline-check.json`: reconstrução em bytes de server.py e index.html,
  retirando apenas import/registro, loader e seis ganchos autorizados, coincide
  **exatamente** com ambos baselines. Finais de linha mistos foram preservados.
  CLAUDE.md SHA continua `4142D0D0996D4C5E55266A94361A7CFADD39EC174D743EA2A678BAE99B2C2430`.
- MAX_SESS/MAX_TABS=6; binding 127.0.0.1, SPEAK_Q, payloads e guardas mantidos.
  Runtime/blueprint/protótipo Hive dentro HiveMind, sem backend novo.
- Seis camadas PNG 1254×1254, ordem esquerda/direita/corpo, pivôs, sete estados,
  cadências .18/.26 s e tamanhos 64/56/40/26 conferidos. Decisão explícita PNG
  animadas e aviso backend são exceções; não justificam outros desvios.

### Testes e evidência independente

Python `.venv`, Node local, Playwright/Chrome; servidores efêmeros somente
127.0.0.1. Sem Hub vivo/restart, mic/voz/IA reais ou vault pessoal. TEMP/TMP em
`.test-tmp/verificador-hive-final`. Navegadores/servidores de teste encerrados.

| Execução | Resultado |
|---|---|
| `.venv/Scripts/python.exe -m pytest tests -q --basetemp .test-tmp/verificador-hive-final/pytest` | **235 passed em 13,41 s**, sem skips; inclui testes pertinentes Hive/Codex/frontend/dock. Falha Windows histórica não reproduziu; causa não presumida. |
| `node tests/hivemind_frontend_behavior.mjs` | Passou. |
| `node tests/codex_frontend_behavior.mjs` | Passou, inclusive STT/mic diferidos e loop galáxia. |
| `node tests/hivemind_browser_qa.mjs .../qa-verificador/functional` | Passou no escopo exercitado: seis sessões, mic, isolamento, drafts/foco, slots, movimento, retorno/fullmode/mobile. |
| `node tests/hivemind_visual_compare.mjs .../qa-verificador/comparator` | Asserções passaram: 3 pares idle e 6 pares de estado. **Não aprova fidelidade**: gate não verifica subárvores/diffs, HM-F08. |
| `.test-tmp/verificador-hive-final/independent.mjs` | Concluído sem erros de página: inventário de 38 combinações agente/aba, 10 pares, cliques reais, lifecycle e STT/ask/speak mockados. |

Instrumento próprio: `qa-verificador/independent/report.json` e pares
`native-*.png`/`reference-*.png`: idle-all-drawers, documentos-relacoes,
documentos-tools, mission-conex, p2b-subprogress, empty, approval, fail,
done-delivery, worker-form. Mesmo viewport1440×900/DPR1/fase/progresso/drawers,
fontes Space Grotesk e Source Sans3 **carregadas efetivamente** em pesos
400/500/600/700, reduced motion. Comparador reexecutado fornece também
1280×800 e1920×1080, selected-link e diffs regionais. Inspeção visual direta
dos pares idle/Conexões/vazio/subprogresso/entrega além da fonte/DOM.

Uma chamada mobile no instrumento temporário foi corrigida: mobileTurnStart
não retorna tab, então mobileTurnEnd usa ensureMobileTab(). Era erro do
instrumento, não regressão do candidato. Não houve alteração de testes reais.

### Matriz independente R01–R14

| ID | Resultado | Evidência/limite |
|---|---|---|
| R01 | **Passou** | Navegação real com seis abas; Hive não muda provider/sid/quantidade; retorno Claude/Codex, fullmode e preferência Hive no QA. |
| R02 | **Passou** | Aviso persistente/local; Hive não chama IA. Requests STT/ask/speak do instrumento pertencem ao turno Claude anterior mockado. |
| R03 | **Falhou** | Containers coincidem, mas quadros, subárvores, tipografia, controls/alças/HUD/entrega divergem além das exceções. F02/F05/F07. |
| R04 | **Falhou** | Relações omite conexões; subagentes sem progresso/detalhes; seleção não mostra subs e alça conta6 versus8. F03/F04/F06. |
| R05 | **Falhou** | Legenda/amostras omitidas, andamento/pausa/estado inexatos, vazio mantém ações/textos de missão. F02/F03/F04/F07. |
| R06 | **Falhou** | Clique de envio não envia; entrega conserva estado após troca de cenário e layout diverge. Manual entrega23/4 e23/3 correto. F01/F02/F07. |
| R07 | **Falhou** | Routes/sentidos base portados, mas seleção muda gaveta/tab; popup/legenda resumidos e efeitos Queen/subseleção divergentes. F03/F05/F06. |
| R08 | **Falhou** | Limites16/40, três slots/reuso/XSS passam; vazio permite criar e cenário conserva delivery/adjusted/showSubs. F02. |
| R09 | **Passou com exceção autorizada** | Rig PNG, seis dimensões/camadas/estados/cadências/tamanhos conferidos. Não declara igualdade de pixels com SVG. |
| R10 | **Passou no lifecycle/movimento** | Asas/pulsos ativos; ocultação congela fase/elapsed, timer100ms=0; volta retoma; pausa manual persiste após visibilitychange/4 reentradas; sem timer duplicado. CSS reduz motion; galaxy somente Codex visível. Estado visual toggle pendente F07. |
| R11 | **Passou** | Enter/Espaço/Esc sem mic/IA; controles Hub inert/ocultos; DOM/textContent e XSS seguro no QA. |
| R12 | **Passou** | Entrada recusada listen; mic stops1/recorders0; STT anterior continua ask/speak no sid/model/effort originais sob Hive; mobile ask/done sem foco; drafts/retorno no QA. |
| R13 | **Passou** | Blueprint apenas static/traversal bloqueado; ES modules; sem React/support/CDN JS/bundler/dependência/backend produção; docs/frontend e Codex documentam extensão. |
| R14 | **Falhou no aceite global** | Suíte/invariantes passam, mas QA/conteúdo/ações exigidos falham e não há aprovação final. F01–F08. |

### Matriz independente V01–V08

| ID | Resultado | Evidência/limite |
|---|---|---|
| V01 | **Passou** | Seis hashes atuais preservados; novas capturas/3viewports; histórico separado. |
| V02 | **Falhou** | Subárvores: Nova operária Source Sans3 16/700 versus Space Grotesk15/600; especialidade14 versus14,5; Simular de Andamento13,5 versus13; entrega stats22/700 versus26/600, buttons/gaps/bounds diferentes. F07. |
| V03 | **Passou na composição estática observada** | Stops/distribuição mesh/células, highlights/lowlights/drop-shadow conferem por fonte/pares idle3viewports. Composição dinâmica por estado falha V06/F05. |
| V04 | **Falhou** | Mundo/axial/roteador/resizing portados; clique de trilha muda enquadramento e popup/legenda não preservam todo sentido/estado. F03/F06. |
| V05 | **Falhou** | Gavetas omitidas/Relações/legenda/vazio; form/chat/entrega/alças/badges/controls inexatos. F01/F02/F03/F07. |
| V06 | **Falhou** | Pares mostram12/23 versus11/23, subprogresso ausente, andamento impreciso, efeitos Queen substituídos e switch não acompanha reduced. F04/F05/F07. |
| V07 | **Passou quanto à decisão/exceção** | PNG animadas+aviso preservados; desvios restantes não aprovados como exceção. |
| V08 | **Falhou** | Layout.css/import removidos/fingerprint estável, porém caminhos simplificados/omissões e gateQA incompleto persistem. F03–F08. |

Sem bloqueio real de renderer/fontes/ambiente. Correção apenas das Issues no
escopo aprovado, preservando passes de navegação/sid/voz/mobile/isolamento/rig
e baselines dos monolitos. Depois, novo congelamento, suíte completa e reteste
R01–R14/V01–V08 com conteúdo/estados/subárvores reais. Não concluir nem alegar
aprovação de código alterado posteriormente. Coordenação registra ciclo2 antes
das correções; teto total permanece3.

## Candidato do ciclo 2 — aguardando verificação independente

Implementação executada por **GPT-5.6 Terra, high**. O candidato corrige
HM-F01–HM-F08 e está congelado; este é um registro de execução, não um novo
veredito. Evidências do implementador: suíte Python completa com **235 passed**,
regressões Node Codex/Hive passantes, QA Chrome isolado com envio por clique,
reset de cenário vazio, seis sessões, voz/mic obsoleto, mobile e retorno entre
páginas. O confronto de três viewports e seis pares de estados está em
`qa-ciclo2/`, com animação reduzida e fontes carregadas. A nova matriz
R01–R14/V01–V08 e a decisão global pertencem exclusivamente ao verificador
GPT-6.1 Sol high que não participou desta implementação.

Limite registrado: o comparador visual mantém capturas e diffs dos pares, mas
não emite aprovação por contêineres nem por limiar global de pixels. O gate de
regressão de navegador reprova explicitamente envio, cenário vazio/CRUD,
progresso p2b, subagentes, preservação de gavetas ao selecionar conexões,
inventário de conexões e alerta HUD oculto. A confirmação independente ainda
deve avaliar integralmente pixels e subárvores contra a fonte.


## Verificação independente formal — ciclo 2, 12/10/2026

Verificador **GPT-6.1 Sol high**, sem participação na implementação. **REPROVADO** sobre o candidato congelado do ciclo **2/3**. HM-F01 e HM-F06 corrigidas; demais Issues continuam parciais. HM-F09 registra regressão de lifecycle introduzida pelas correções. Somente o ciclo 3 permanece disponível; nenhuma conclusão/quarta rodada automática.

Evidências independentes: `qa-verificador-ciclo2/`. Fingerprints início/fim confirmam **zero alteração do candidato**; `protected-check.json` confirma server/index/CLAUDE/providers/geometry/rig/seis PNG iguais ao ciclo 1. A reconstrução dos monolitos do ciclo 1 continua aplicável. Seis hashes da referência conferem, incluindo HTML `03B05ACDDD71DA6C6C2E81D3AE14ADC6B08D4EBB340E44C1CE3D41A92CF8DAD6`. PNGs 1254×1254, camadas/pivôs/cadências/64-56-40-26 preservados. Backend/invariantes intactos.

| Check independente | Resultado |
|---|---|
| pytest completo com `.venv`, TEMP/TMP e basetemp `.test-tmp/verificacao-c2` | **235 passed em 16,96 s**, sem skips |
| Node Hive/Codex behavior | Passaram; mic/STT diferidos e loop Codex preservados |
| Gate real `tests/hivemind_browser_qa.mjs` | **Falhou**: timeout linha 72, entrega reaberta por timer cobre alça inferior |
| Cópia temporária do mesmo QA | Espera autoabertura normal 1700 ms antes de fechar; restante passou, incluindo seis sessões, mic stops=1/recorders=0, drafts, slots/XSS, retorno/fullmode/mobile. **Não altera nem aprova o gate real** |
| Comparador real | Passou gate restrito: 3 pares idle e 6 estados; diffs arquivados, sem provar fidelidade |
| Instrumento independente temporário | **38 combinações agente/aba**, 22 pares congelados + popup/operária criada, 3 viewports, ações reais, fases/fixtures, lifecycle e STT/ask/speak stubados; sem erros de página |

`independent/report.json` e `analysis.json` preservam texto, botões, leaves, medidas, estilos, progresso, fontes e observações; pares `native-*`/`reference-*` em 1280×800/1440×900/1920×1080. Fontes Space Grotesk/Source Sans 3 realmente loaded nos pesos 400/500/600/700, DPR1, mesmo estado/progresso/gavetas/reduced. Timer decorativo de autoentrega foi cancelado **só no setup temporário dos snapshots**, em ambas páginas, para respeitar o estado congelado; timer real foi exercitado separadamente. Ajustes de seletor React child único e Fechar ambíguo foram exclusivamente do instrumento. Houve inspeção visual direta de Conexões/form/entrega, além da comparação DOM/fonte. Sem Hub vivo/restart/mic/IA/vault reais; navegadores/servidores encerrados.

| ID | Resultado | Evidência |
|---|---|---|
| R01 | Passou | Navegação real, seis abas, provider/sid e retorno/fullmode preservados |
| R02 | Passou | Aviso persistente e demonstração local; IA somente turno Claude anterior stubado |
| R03 | Falhou | Subárvores, vazio, form/tools/entrega/switch/efeitos fora das exceções: F02/F03/F05/F07 |
| R04 | Falhou | Todas 8 Relações sem Conexões na colmeia; detalhes dinâmicos ausentes, alça6/8: F03/F04 |
| R05 | Falhou | Legenda, pausa/falha/approval/faixas/plano/vazio inexatos: F02/F03/F04 |
| R06 | Falhou | Clique/Enter únicos corrigidos e entrega23/4→23/3 funcional; layout/conteúdo entrega/chat inexatos: F07 |
| R07 | Falhou | Fluxos base preservados; links de fases de ajuste omitidos, samples/popup/Queen incompletos: F03/F04/F05 |
| R08 | Passou no comportamento | Cenários/reset/guard vazio, ajuste até novo approval e três divergências; limites/slots/XSS/removíveis preservados. Composição/dados de exibição falham nos requisitos acima |
| R09 | Passou com exceção autorizada | Rig PNG preservado; sem alegação de igualdade com SVG |
| R10 | Falhou | Timer de fase/wing/pulse/pausa/reentrada funcionam, mas Queen continua running na pausa e autoentrega muda estado oculta: F09 |
| R11 | Passou | Guardas/teclado/inert/texto seguro, zero IA por entrada Hive |
| R12 | Passou | Listen bloqueado, mic descartado, STT→ask→speak sid/model/effort originais, mobile sem foco e preferências |
| R13 | Passou | Blueprint estático/ES modules/traversal, sem backend/runtime editor/dependência nova; encaixes protegidos |
| R14 | Falhou | Invariantes/suíte passam; gate real, conteúdo/fidelidade/lifecycle e aprovação final falham |
| V01 | Passou | Referência íntegra, pares novos/histórico separado |
| V02 | Falhou | Form Nova operária16/700 Source Sans versus15/600 Space; ferramentas e medidas locais >1px: F07 |
| V03 | Passou na composição estática base | Gradientes/mesh/bisel/sombras portados e geometry intacta; efeitos/seleção dinâmicos falham V06/F05 |
| V04 | Falhou | Mundo/rotas base alinhados; estados omitidos e samples/sentidos em listas/popup inexatos: F03/F04 |
| V05 | Falhou | Gavetas/vazio/legenda/relações/form/tools/chat/entrega/alças incompletos: F02/F03/F07 |
| V06 | Falhou | Detail/progresso/pausa/falha/approval/Queen/switch divergem: F04/F05/F07/F09 |
| V07 | Passou quanto à exceção | Somente PNG e aviso backend autorizados; demais desvios reprovados |
| V08 | Falhou | Sobras genéricas/port incompleto e gate real falho: F03–F05/F07–F09 |

Veredito não depende de limiar global. Nenhuma limitação de ambiente impede confirmar as falhas. Reteste final precisa preservar todos os passes e resolver integralmente as seções/estados da fonte descritos nas Issues, sem redesign, alterações de fonte/assets ou flexibilização de aceite.

## Reteste do implementador — ciclo 3, 12/10/2026

- `pytest tests -q`: **235 passed**.
- Node: `hivemind_frontend_behavior.mjs`, `codex_frontend_behavior.mjs` e `--check` de `hive.js`, `drawers.js`, `demo-data.js` e `simulation.js` passaram.
- Chrome real: `hivemind_browser_qa.mjs` passou, incluindo autoentrega 400/1600 ms, pausa/retomada e isolamento de sessão/microfone.
- Comparador: `qa-ciclo3-comparator/metrics.json` registra DPR 1, 3 pares de viewport e 6 pares congelados de estado.

Os testes do implementador não substituem a verificação independente final exigida para esta faixa completa.


## Verificação independente FINAL — ciclo 3/3, 12/10/2026

**REPROVADO**, verificador **GPT-6.1 Sol high**, independente, código/testes/protótipo/assets somente leitura. O candidato melhorou, mas não atende fidelidade integral, conteúdo dinâmico e efeitos exigidos. **Teto de três ciclos esgotado: parar e apresentar diagnóstico; sem implementação de ciclo4 automática.**

Evidência nova: `qa-verificador-ciclo3/`. Fingerprints início/fim: **zero alterações do candidato**. `protected-check.json`: server/index/CLAUDE/providers/geometry/rig/seis PNG/seis arquivos da fonte iguais ao ciclo1; baseline dos monolitos continua válido. HTML SHA `03B05ACDDD71DA6C6C2E81D3AE14ADC6B08D4EBB340E44C1CE3D41A92CF8DAD6`. Camadas, tamanhos, pivôs e cadências PNG preservados; aviso backend mantido. Invariantes intactos.

| Execução independente | Resultado |
|---|---|
| Pytest completo, `.venv`, TEMP/TMP/basetemp exclusivos `.test-tmp/verificacao-c3` | **235 passed em15,47s**, sem skips |
| Node Hive e Codex behavior | Passaram |
| Gate real Chrome/browserQA | Passou, inclusive delays400/1600, seis abas, mic obsoleto, retorno/fullmode/mobile |
| Comparador real | Passou gate restrito, 3 viewports/6 estados; diffs arquivados |
| Instrumento próprio | **38 combinações agente/aba,27 pares + popup/operária criada**,3 viewports e lifecycle/ticks/STT-ask-speak reais com endpoints stubados; sem erros de página |

`independent/report.json` e `analysis.json` registram fontes **realmente loaded** Space Grotesk/Source Sans3 em400/500/600/700, DPR1, mesmos estados/progressos/gavetas/reduced. Capturas1280×800/1440×900/1920×1080; inspecionados visualmente Relações, form, vazio e entrega. Animação/timer foram congelados somente no setup temporário dos snapshots, em ambas páginas. Normal/reduced/pausa/ocultação foram exercitados separadamente na produção real. Um erro do instrumento (sweep ausente sob reduced=true) foi resolvido exclusivamente na cópia temporária; não é falha do candidato. Não se usaram medidas de leaf versus wrapper como prova; controles/títulos correspondentes e fontes/estrutura real sustentam desvios. Sem Hub vivo/restart/mic/IA/voz/vault reais; browsers/servidores encerrados.

| Critério | Resultado | Evidência/limite |
|---|---|---|
| R01 | Passou | Hive no teto6, provider/sid e retorno/fullmode preservados |
| R02 | Passou | Aviso explícito e simulação sem IA real |
| R03 | Falhou | Vazio fora do mundo/fit e subárvores/estilos fora da exceçãoPNG/aviso, F02/F03/F07 |
| R04 | Falhou | Relações e contagem8 adicionadas; detail congela0/23 durante ticks, informações de subagentes/adições resumidas, F04 |
| R05 | Falhou | Legenda adicionada; approval/fail sobrescritos, pausa em posição incorreta e composição vazia inexata, F02/F04 |
| R06 | Falhou na fidelidade | Clique/Enter únicos, log e23/4→23/3 funcionam; entrega/tipografia/estrutura diferem, F07 |
| R07 | Falhou | Routes/sentidos/listas adicionados; popup sem sample e efeitos reiniciados/inexatos, F03/F05 |
| R08 | Passou no comportamento | Cenários/reset/guards/CRUD/limites/slots/ajuste/retry preservados; conteúdo de detalhes falha R04 |
| R09 | Passou com exceção autorizada | RigPNG intacto64/56/40/26, sem alegação de pixeligualSVG |
| R10 | Passou no lifecycle | Queen/wing/pulse pausam, fase congela, manual persiste, timers únicos; autoentrega preserva1586,2ms ocultos e retoma; F09 corrigida |
| R11 | Passou | EntradasHive sem IA/mic/abort; controlesHub inert e strings seguras |
| R12 | Passou | Listen bloqueado, mic tracks liberadas, STT→ask→speak conserva sid/model/effort, mobile não focaHive |
| R13 | Passou | Blueprint estático/ES modules, sem backend/runtimeeditor/dependência; encaixes protegidos |
| R14 | Falhou no aceite global | Gates/invariantes passam, mas fidelidade/conteúdo/efeitos não; não há aprovação final |
| V01 | Passou | Fonte íntegra, pares novos e histórico preservado |
| V02 | Falhou | BotãoSubs desloca192,813px/h+10; títuloformY−9,016; skills10.5/600 Space versus13.5/400 Source; entrega700 versus600, F07 |
| V03 | Passou na base estática | Mesh/gradientes/bisel/sombras base preservados; estados/efeitos falhamV06 |
| V04 | Falhou | Mundo/rotas base alinhados; cartão vazio fora do transform e popup/sample/effects incompletos, F02/F03/F05 |
| V05 | Falhou | Seções adicionadas, mas wrappers/ícones/carets/skills/relations/popup/entrega não são o port exato, F02/F03/F07 |
| V06 | Falhou | Progress real desatualizado, approval preenchido por ticks, efeitos/color/keyframes diferentes, F04/F05 |
| V07 | Passou quanto à exceção | Apenas personagensPNG e aviso autorizados; outros desvios não aceitos |
| V08 | Falhou | Regras substituídas/overrides persistem e gates passing não detectam falhas restantes, F08 |

Não houve bloqueio de ambiente. F01/F06/F09 efetivamente corrigidas; F02/F03/F04/F05/F07/F08 continuam parciais. Diagnóstico final e reproduções exatas no append de Issues; nenhum código foi corrigido pelo verificador. Nova implementação depende de decisão explícita do usuário após os três ciclos.

## Candidato da rodada adicional — ciclo 4 autorizado, 12/10/2026

Implementação por GPT-5.6 Terra high, após autorização explícita do usuário
para a rodada adicional focada. Este registro **não** é aprovação independente
nem encerra a faixa completa. A fonte `Hive Mind.dc.html` e os PNGs do rig não
foram alterados; Hub, backend, voz, runtime, providers, index e servidor não
foram modificados nesta rodada.

- F04: os detalhes de progresso usam o mesmo tick da célula; p2b conserva
  “Depende das entregas de Documentos e Cadastros.”, subagente idle usa
  “Acionado por Documentos quando houver leitura.” e operária adicionada usa
  os valores completos da fonte, inclusive “Especialidade a definir” quando
  omitida.
- F05: marcha usa os offsets da fonte (Rainha −62, operária −31,5, sub −24,5),
  sweep sem escala, ripple inicia em escala 1, e a Rainha concluída usa anel
  mostarda de 3 px. O anel de seleção continua separado.
- F07/F08: relações, skills, form e entrega foram confrontados com a fonte;
  ícones das gavetas passaram a SVGs equivalentes (inclui ampulheta), e as
  regras de popup/trilha foram consolidadas na base, removendo as regras
  diretamente substituídas de borda/override.
- Gates acrescentados: `hivemind_frontend_behavior.mjs` agora cobre textos de
  p2b/sub idle/operária adicionada; o QA Chrome confere a ausência de escala
  no sweep e o traço mostarda de 3 px no estado concluído.

| Execução | Resultado |
|---|---|
| `node tests/hivemind_frontend_behavior.mjs` | Passou |
| `pytest tests/test_hivemind_frontend.py -q` | 6 passed |
| QA Chrome isolado `hivemind_browser_qa.mjs` | Passou; fontes loaded, ticks/effects/drafts/pausa/ocultação e 3 viewports exercitados |
| Comparador Chrome `hivemind_visual_compare.mjs` | Passou; `qa-ciclo4-comparator/`, DPR 1, 3 viewports e 6 pares congelados |
| `pytest tests -q` | **235 passed em 12,96 s** fora da sandbox; a sandbox bloqueia `TEMP` dos fixtures de reports/STT e não representa falha do candidato |

Artefatos de QA: `qa-ciclo4-browser/` e `qa-ciclo4-comparator/`. O candidato
está congelado para teste real do Hub e verificação independente Sol high.
Não foram feitas mais escritas após este registro.

### Revisão mínima do candidato C4, 12/10/2026

Após a revisão do candidato congelado, foram corrigidos dois desvios restantes
apontados contra a fonte, ainda dentro da rodada C4 autorizada: `hm-flow` passa
a usar `var(--cyc)`, com rotas em `-72px` e amostras da legenda em `-18px`; e o
rótulo de cada item da legenda voltou a usar `strong` para o nome antes de
` · descrição`. O espaçamento de 12 px da legenda foi preservado.

O QA Chrome isolado foi ampliado para ler esses valores computados e as sete
linhas de legenda no DOM. Nesta revisão, `node --check` para `drawers.js` e o
QA, `node tests/hivemind_frontend_behavior.mjs`, `pytest
tests/test_hivemind_frontend.py -q` (**6 passed**) e o QA Chrome passaram. A
fonte e os PNGs permanecem intactos. O candidato foi congelado novamente;
estes resultados não substituem teste real do Hub nem verificação independente
Sol high.

## Candidato C5 — revisão mínima autorizada, 13/10/2026

Implementação por **GPT-5.6 Terra, high**. Foram alterados apenas
`demo-data.js`, `simulation.js`, `drawers.js`, `hive.css` e o gate Chrome:
LINK_INFO agora porta literalmente as dez descrições da fonte; a Missão vazia
preserva objetivo e Limites; pausa permanece no `strong`; ajustes usam fill de
50%; e Conexões, alças, responsabilidades e entrega receberam a estrutura e os
valores documentados no diagnóstico C4. Regras de popup diretamente substituídas
foram incorporadas à regra-base e removidas do override.

O gate Chrome troca a asserção temporal fixa por igualdade entre célula,
detalhe e valor calculado do elapsed atual, preservando os checks de clock,
sweep e bordas. Passaram `node --check`, `node
tests/hivemind_frontend_behavior.mjs`, `pytest
tests/test_hivemind_frontend.py -q` (**6 passed**) e QA Chrome isolado em
`qa-ciclo5-browser/`. A fonte permanece SHA
`03B05ACDDD71DA6C6C2E81D3AE14ADC6B08D4EBB340E44C1CE3D41A92CF8DAD6`.
O candidato C5 está congelado para a suíte completa e verificação Sol; este
registro não constitui aprovação independente.


## Verificação independente FINAL — ciclo 4 adicional autorizado, 12/10/2026

**REPROVADO — GPT-6.1 Sol, high, independente e somente leitura no candidato.**
O usuário autorizou expressamente esta quarta rodada; os três ciclos anteriores
continuam contabilizados. Não há quinta rodada automática. Testes e comportamento
básico melhoraram, mas fidelidade integral e informação completa ainda falham.

Evidências: `qa-verificador-ciclo4/independent/{report,analysis}.json`, 27 pares
de capturas, 38 combinações de agente/aba e inventário de todas as **24 fases**.
Fontes Space Grotesk/Source Sans 3 realmente loaded em 400/500/600/700, DPR 1,
1280×800, 1440×900 e 1920×1080; estados, seleção, gavetas e progresso iguais
nos pares, com movimento congelado apenas no setup temporário. A revisão visual
direta incluiu Conexões, vazio e entrega. Medidas citadas abaixo correspondem a
controles ou títulos semanticamente equivalentes, sem confundir folha e wrapper.
Não se usa limiar global de pixels como aprovação.

`fingerprints-start.json` preserva a preparação anterior. Após a revisão mínima
autorizada e antes do QA formal, `fingerprints-formal-start.json` registra o
candidato congelado: somente drawers.js, hive.css e o gate browser mudaram nesse
intervalo. `fingerprints-end.json`/`fingerprint-differences.json` confirmam **zero
alterações nos 70 arquivos durante a revisão formal**. `protected-check.json`
confirma 19 arquivos protegidos iguais aos ciclos 3/1: server/index/CLAUDE,
providers, geometry, rig, seis PNG e seis arquivos de referência. Continua
aplicável a reconstrução dos monolitos do ciclo 1. HTML fonte: 134879 bytes,
SHA256 `03B05ACDDD71DA6C6C2E81D3AE14ADC6B08D4EBB340E44C1CE3D41A92CF8DAD6`.
Somente PNG autorizadas e aviso de simulação/backend constituem exceções.

| Execução independente | Resultado |
|---|---|
| Pytest completo direto, .venv, TEMP/TMP/basetemp exclusivos | **235 passed em 44,59 s**, sem skips |
| Node Hive/Codex behavior | Ambos passaram |
| Gate real browser QA | **Falhou duas vezes** no contador literal 12 após 1950 ms; observou 13, enquanto sweep permaneceu conectado e avançou 1894/1908 ms, detalhe atualizado e approval papel/borda sólida |
| Cópia instrumental temporária do browser QA | Passou restante, comparando detalhe e célula no mesmo tick: seis sessões, mic stops=1/recorders=0, drafts, slots/XSS, mobile, painel completo, retorno e delays 400/1600/ocultação. Não modifica nem aprova o gate real |
| Comparador real | Passou gate restrito: três viewports e seis estados; diferenças guardadas |
| Instrumento independente | 38 combinações + 27 pares + 24 fases + 58 observações, zero erros de página; fases/agents/links normalizados, STEPS e STATE_INFO iguais à fonte |

A execução intermediada da suíte apresentou duas falhas dos fixtures Windows;
a execução direta elevada resolveu ambas e aprovou os 235 testes. O primeiro
Chrome foi bloqueado pela sandbox em localhost; foi repetido fora dela. Um erro
do setup temporário (sweep procurado com reduced=true) foi corrigido somente no
instrumento e o QA foi concluído. Não são falhas atribuídas ao candidato.
O gate temporal real continua falho e não foi enfraquecido nem editado durante
a revisão. Seus logs e os do instrumento temporário permanecem separados.

### Diagnóstico concreto do candidato final

- **F02 parcial:** card vazio agora está dentro do mundo e alinhado à fonte;
  grid educativo e Plano de sete etapas existem. A gaveta Missão vazia ainda
  troca o objetivo do cabeçalho por “Este exemplo não tem agentes...” e omite
  Limites, enquanto a fonte preserva ambos. A lateral educativa usa título
  Source Sans 18,72/700 em vez de Space Grotesk 18/600, x=12 em vez de 20;
  label Uma colmeia reúne 11 em vez de 11,5. CTA lateral usa 13,5/padding14/
  altura38 em vez de 14/padding16/altura36. Pares empty nos três viewports.
- **F03 parcial:** rótulos fortes da legenda e samples -18 estão corrigidos,
  keyframes reais conferidos. Ainda há descrições resumidas: popup q-doc diz
  “A Rainha delega a extração...” e a fonte “A Rainha delega a Documentos a
  extração...”; doc-s1 omite o repasse por Documentos e descreve apenas Anexos.
  O inventário LINK_INFO demonstra diferenças em nove das dez descrições.
  O popup deve conservar a informação literal completa, inclusive agente e
  dependência. A estrutura geral melhorou; não equivale a completude.
- **F04 parcial:** detalhes acompanham célula durante ticks, bordas approval/fail
  persistem, todas as 24 fixtures PH normalizadas coincidem. Porém Pausada muda
  do strong para o fim de phaseText após Claude→Hive: strong antes “Etapa 2 de
  7. Pausada.”, depois “Etapa 2 de 7.”; elapsed=2080,4 ms fica igual. A fonte
  mantém Pausada no stepTag. updateProgress reintroduz a posição antiga.
  Nas fases adj1–adj5, stepProgress nativo começa em 0 e cresce com o clock;
  fonte renderVals usa fill=50% quando não há STEP_PH para etapa 5. Não é a
  sequência textual PH que falha, é a projeção de progresso e pausa.
- **F07 parcial:** intro Conexões usa p sem estilo, efetivamente **16px/normal**,
  versus fonte **13,5px/18,9px**; altura66 versus37,78125. As oito linhas ficam
  **Y+30,84375px**, Conexões agora **Y+34,84375px**. Controles Avançar/Reiniciar
  usam 13,5/padding14 versus fonte13/padding12; Avançar **W+7,484375px**.
  Tabs inativas usam weight400 versus500. Alça inferior Source Sans versus
  Space Grotesk, **W−35,390625px**, e carets estão omitidos. Nova operária
  mantém fonte correta, mas título **Y+2px**. Entrega mantém h2/label corrigidos,
  mas labels dos números **16px versus13px**, pedido4817 Source Sans400 versus
  Space Grotesk600; botão Fechar **Y−7,421875px**. A diferença não está nas PNG.
  Responsabilidades ainda usa nome/duty/status em itens planos em vez da
  estrutura/símbolos/short source. Esses desvios foram vistos e medidos nos
  pares e nas 38 combinações, inclusive em viewports alternativas.
- **F08 parcial:** permanecem regras diretamente substituídas: hive.css:98
  popup-state gap7/weight600, sobrescrita na linha289 por gap10/weight700;
  popup-head strong:95 e popup p:97 não correspondem mais à árvore div atual.
  Novos gates não detectam intro/layout/conteúdo/projeção da pausa acima.
  O browser real tem ainda assert temporal literal frágil. Nenhum gate passing
  substitui o aceite exato do protótipo.

F01 e F06 continuam corrigidas. F05 passou nos aspectos reprovidos anteriormente:
nós de sweep preservados entre ticks, keyframes/offsets/mustard/seleção separados,
ondas de ajuste presentes e pausa de efeitos. F09 continua corrigida: autoentrega
oculta conservou 1552,1 ms durante 1750 ms ocultos e abriu após retorno; pausa
manual e quatro reentradas mantêm tempo/zero intervalos enquanto pausadas.

| Critério | Resultado | Evidência |
|---|---|---|
| R01 | Passou | Seis sessões, provider/sid e retorno preservados |
| R02 | Passou | Aviso persistente, demonstração local sem IA real |
| R03 | Falhou | F02/F07: composição/tipografia fora das exceções |
| R04 | Falhou na fidelidade | 38 combinações, conteúdo base/progresso passam; tabs, hierarquia e projeções de gavetas ainda F07 |
| R05 | Falhou | F02/F04/F07: cabeçalho vazio, pausa, fill ajustes e Conexões |
| R06 | Falhou na fidelidade | Envio único e 23/4→23/3 passam; entrega/chat/alças inexatos F07 |
| R07 | Falhou | F03: descrições incompletas; links, direção, seleção e samples corrigidos |
| R08 | Passou no comportamento | Cenários/guard vazio/CRUD3/limites/slots/XSS/ajuste/retry |
| R09 | Passou com exceção autorizada | Rig/PNGs/hashs/1254²/64-56-40-26 preservados |
| R10 | Passou no lifecycle | F09, normal/reduced, ocultação, pausa e reentradas sem duplicação |
| R11 | Passou | Teclado/inert/texto seguro, zero IA/mic por entrada Hive |
| R12 | Passou | Listen bloqueado, mic descartado, STT anterior stubado conserva sid/model/effort; mobile sem foco |
| R13 | Passou | Blueprint estático/ES modules, encaixes mínimos e sem backend Hive |
| R14 | Falhou | Invariantes e 235 testes passam; fidelidade/conteúdo/gate real falham |
| V01 | Passou | Fonte/hashs íntegros, capturas atuais novas e histórico preservado |
| V02 | Falhou | Controles/títulos correspondentes e fontes loaded: F02/F07 |
| V03 | Passou na composição base | Mundo/malha/gradientes/bisel/sombras preservados; PNG explícitas |
| V04 | Passou no mundo/fluxos geométricos | Transform/rotas/sentidos/samples atuais; texto incompleto tratado em R07/F03 |
| V05 | Falhou | Gavetas/empty/popup/chat/entrega/controls ainda F02/F03/F07 |
| V06 | Falhou | F04/F07: pausa pósnav e projeção de ajustes; estados/efeitos básicos corrigidos |
| V07 | Passou quanto às exceções | Somente PNG e identificação autorizadas; demais desvios reprovados |
| V08 | Falhou | Sobras diretamente substituídas/gate real/fidelidade: F08 |

A coordenação realizou separadamente QA do Hub real com CUA integrado: reload,
envio, aprovação, entrega23/19/4, navegação com pausa, CRUD e cenários; sem erros
de página. Essa evidência funcional complementar não substitui esta comparação
independente com a fonte. O verificador não interagiu com a porta8765 nem com
o navegador integrado, não reiniciou serviços e não usou mic/IA/voz/vault reais.
Servidores efêmeros e Chrome isolados foram encerrados pelo próprio harness.

Prévia nativa atual disponível: `qa-verificador-ciclo4/independent/native-mission-conex.png`.
**Encerrar a quarta rodada com diagnóstico e aguardar decisão do usuário.**


## Verificação independente FINAL — ciclo 5 autorizado, 13/10/2026

**REPROVADO — GPT-6.1 Sol high, independente, revisão somente leitura.**
Cinco ciclos totais: três originais e dois adicionais autorizados. Nenhuma sexta
rodada automática. Revisão limitada ao delta C4→C5 e às reproduções pendentes.

Delta: demo-data.js, drawers.js, hive.css, simulation.js e browser QA.
Os outros 65 arquivos do mapa C4 estão intactos; fonte mantém 134879 bytes/SHA
`03B05ACDDD71DA6C6C2E81D3AE14ADC6B08D4EBB340E44C1CE3D41A92CF8DAD6`.
Fingerprint início/fim confirma zero alteração durante o QA formal. Reutilizados
C4/C1 para monolitos, providers, geometria, rig/PNGs, encaixe e F01/F05/F06/F09.
Não foram refeitos os 38 combos, 24 fases ou 27 pares anteriores.

Checks: **235 pytest passed em16,21s**, única execução completa direta elevada
com TEMP próprio; Node Hive/Codex passaram. Browser QA atualizado passou o novo
check de ticks, porém **falhou na linha58**: setup elapsed1800 com clock ativo
produziu fill51% durante seleção/render/pausa, enquanto o assert exige50%;
detail11/23, strong Pausada, fail e approval estavam corretos. Não foi repetido,
editado nem enfraquecido. Essa falha temporal do teste não é atribuída, por si,
a regressão semântica do progresso; ainda impede considerar o gate aprovado.

Comparação direcionada: **15 pares** (vazio/Conexões/form/entrega/responsabilidades
×1280×800/1440×900/1920×1080), fontes realmente loaded400/500/600/700, DPR1,
mesmos estados/seleção/gavetas/progresso congelado; zero erros de página.
Evidências `qa-verificador-ciclo5/independent/{report,analysis}.json` e capturas.

| Aceites reabertos | Resultado e evidência C5 |
|---|---|
| F02; R03/R05/V02/V05 | Parcial: objetivo/Limites e fonte/tamanho do título vazio corrigidos. Título lateralY−10,8125px; label Uma colmeia reúne11 versus11,5 e CTA Y+1,1875px. Persistem composição/margens acima do aceite1px |
| F03; R07/V05 | Parcial:8 descrições coincidem; doc-ana/cad-ana ainda omitem o prefixo literal “Dependência:”. description-differences.json contém esperado/observado |
| F04; V06 | **Corrigida**: Pausada permanece no strong após Claude→Hive; elapsed880,8ms conservado. adj1–adj5 usam50% como a fonte |
| F07; R03/R04/R05/R06/V02/V05 | Parcial: intro13,5/18,9, tabs500, dimensões dos controles, SVG carets, labels13 e pedidosSpace600 corrigidos. Alça inferior ainda Source Sans versusSpace Grotesk/W−15,390625px; Conexões agoraY−15,375px; Nova operáriaY+2px. Rainha→Relações usa Extraindo informações/Consultando registros/Aguardando informação onde a fonte usaTrabalhando/Trabalhando/Aguardando. Missão→Responsabilidades tem rows mais baixas/contíguas que a fonte. Fechar entregaY−5,421875px medido; labels/IDs passaram, não se usa folha versus wrapper como prova |
| F08; R14/V08 | Parcial: popup CSS consolidado e regras obsoletas citadas emC4 removidas. Gate real continua falho e não cobre as divergências acima |

Os restantes R01/R02/R08–R13/V01/V03/V04/V07 conservam as evidências C4 sobre
arquivos intactos e as regressões Node; não há novo backend Hive, acesso pessoal
ou alteração de invariantes. R03–R07/R14/V02/V05/V08 continuam **falhando** pelos
motivos da tabela. V06 passa no reteste dinâmico reaberto. Aceite global exige
fidelidade e checks necessários passando, portanto permanece **REPROVADO**.

Inspeção visual direta dos pares Conexões e responsabilidades confirma as
diferenças de alças, layout e short statuses. O relatório não depende de limiar
global de pixels. Não houve Hub real/IAB/porta8765/mic/IA/voz/vault nem agentes
novos. Chrome e servidores efêmeros encerrados pelo harness. Prévia atual:
`qa-verificador-ciclo5/independent/native-connections-1440.png`.
Encerrar C5 com diagnóstico; qualquer sexta correção requer decisão do usuário.

## C6 — 13/10/2026 — candidato congelado (GPT-5.6 Terra, esforço high)

Aplicados somente os resíduos C5: descrições `Dependência:`; alça em Space;
estrutura/fonte do vazio, formulário, conexões, responsabilidades e entrega;
status curtos; e relógio congelado no gate de progresso. O cabeçalho vazio
mantém seu wrapper fonte e o formulário usa inputs de 38px; a legenda aplica
13,5px somente ao span de texto, como a fonte. A entrega removeu a altura
herdada do cabeçalho de tabela, deixando diálogo e botão Fechar idênticos à
fonte (700×541,234; botão Y229,375, 68,6875×30, Space).

Checks focados passaram: `node --check`, `hivemind_frontend_behavior.mjs`,
`hivemind_browser_qa.mjs` e comparador DPR1 em 1280×800/1440×900/1920×1080
(três viewports, seis estados, fontes loaded). Medição DOM C6 em
`qa-ciclo6-dom-pairs.json` confirmou vazio título/label ≤0,813px, alça e Nova
operária/entrega correspondentes. Fonte e PNGs permanecem intactos (SHA-256 da
fonte `03B05ACDDD71DA6C6C2E81D3AE14ADC6B08D4EBB340E44C1CE3D41A92CF8DAD6`).

Não houve Hub real, IAB, porta 8765, mic, IA, voz ou alterações fora do
frontend/demo. A sonda focal C6 confirmou cabeçalho fonte=nativo em 158,25px e
progresso fonte=nativo em 156,1875px, removendo o delta acumulado de Conexões
agora (0px no estado pareado). Responsabilidades teve conferência estrutural e
de estilos do button do painel direito; os bounds das rows não foram
reexportados pela sonda. Este é um candidato C6 congelado; não constitui
aprovação independente Sol nem autoriza C7.

### Revisão de candidato C6 pré-FULL

Pré-checagem com `qa-ciclo6-root-diagnostic/responsibilities.json` confirmou as
cinco rows de Missão/Responsabilidades fonte=nativo (Y 509,625/563,625/617,625/
671,625/725,625; 351×54; padding 8px e borda inferior). Restaurado somente o
texto detalhado da missão via `agentStatus()[1]` — Documentos “Extraindo
informações”, Cadastros “Consultando registros” e Análise “Aguardando
informação”. Rainha/Relações preserva os textos curtos. `node --check`,
`hivemind_frontend_behavior.mjs` e `hivemind_browser_qa.mjs` passaram. O
candidate C6 permanece congelado para FULL/solução independente; não há C7.


## Verificação independente FINAL — ciclo 6 autorizado, 13/10/2026

**REPROVADO — GPT-6.1 Sol high, independente, candidato somente leitura.**
Seis ciclos totais: três originais e três adicionais expressamente autorizados.
Não iniciar C7 automaticamente. Revisão limitada ao delta e às reproduções C5;
sem repetir os inventários completos de 38 combinações/24 fases/27 pares.

- **235 pytest passed em14,30s**, única execução completa direta elevada com
  TEMP próprio. Node Hive/Codex passaram. **Browser QA real passou**, incluindo
  gate58 congelado, tick57 real, seis sessões, mic obsoleto, mobile, retorno,
  painel completo, drafts/CRUD e autoentrega400/1600 com suspensão.
- Comparação independente:15 pares de cinco composições em1280×800/1440×900/
  1920×1080, DPR1, fontes efetivamente loaded400/500/600/700, estado/progresso/
  seleção/gavetas iguais; zero erros. Evidências `qa-verificador-ciclo6/`.
- DeltaC5→C6: demo-data.js, drawers.js, hive.css e browserQA. Os demais66 arquivos
  do mapa estão intactos, inclusive simulation e protegidos. Fingerprints
  formal início/fim: **zero alterações**. Fonte134879bytes/SHA256
  `03B05ACDDD71DA6C6C2E81D3AE14ADC6B08D4EBB340E44C1CE3D41A92CF8DAD6`.
  Reutilizados C4/C5 para invariantes, rig/PNGs e F01/F05/F06/F09.

| Aceite reaberto | Resultado |
|---|---|
| F02 | Corrigida: objetivo/Limites, título/label/CTA vazio correspondem; títulosY−0,8125px dentro do aceite |
| F03/R07 | Corrigida: dez descrições literais, incluindo os dois prefixos Dependência |
| F04/V06 | Corrigida/preservada: pausa pósnav mantém strong/texto/elapsed863,1ms; adj1–adj5fill50% |
| F07/R03/R05/V02/V05 | **Parcial/Falhou:** alçaSpace/dimensões, Conexões agora, formtitle, Fechar, labels/IDs e responsabilidades foram corrigidos; permanece padding dos botões primários abaixo |
| F08 | Corrigida nas pendências citadas: CSSpopup consolidado e gate58 estabilizado sem relaxar asserts |
| R14 | **Falhou no aceite global:** testes passaram, mas diferença confirmada4px excede o teto1px |

**Pendência concreta única: F07, controles primários da Missão.** Em Missãoidle
(Simular missão), Coleta pausada (Continuar) e conclusão (Simular novamente),
`hive.css:205 .hm-controls button` aplica `padding:0 12px` também ao botão preto.
A fonte exige **0 14px nos primários**, mantendo0 12px em Avançar/Reiniciar.
Nos três viewports, controles equivalentes têm **largura−4px**; Avançar etapa/
Reiniciar seguintes ficam **X−4px**, com font/height/Y idênticos. São medidas de
botão contra botão, não folha versus wrapper; `independent/analysis.json` e
pares connections/form/delivery/responsibilities preservam esperado/observado.
A inspeção visual direta confirmou a diferença. Não pertence às exceções PNG
ou aviso de demonstração. Critério de composição permite apenas até1px.

Responsabilidades foram interpretadas por contexto: Rainha→Relações usa status
curtos; Missão→Responsabilidades usa detalhados. Ambos agora coincidem com a
fonte; não exigir labels curtos na gaveta Missão. Não houve alteração de aceites.

R01/R02/R04/R06–R13/V01/V03/V04/V06/V07 mantêm os passes e evidências anteriores,
com regressões atuais; R03/R05/V02/V05/R14 continuam falhando exclusivamente pela
pendência concreta acima. Sem Hub real/IAB/8765/mic/IA/voz/vault ou novos agentes.
Chrome/servidores efêmeros encerrados. Código e testes não foram corrigidos pelo
verificador. Captura atual: `independent/native-connections-1440.png`.
EncerrarC6 e apresentar diagnóstico; nenhumaC7 sem decisão do usuário.


## Verificação independente FINAL — ciclo 7 autorizado, 13/10/2026

**APROVADO — GPT-6.1 Sol high, independente.** Sete ciclos totais: três originais
e quatro adicionais expressamente autorizados. Não iniciar C8 automaticamente.

Único deltaC6→C7: `hive.css:206 .hm-controls .hm-dark{padding:0 14px}`.
Remover essa linha em memória reconstrói exatamente o SHA do CSSC6; os demais
69 arquivos do mapa, fonte/protegidos/rig/PNGs e testes estão intactos.
Fingerprint início/fim: zero alterações durante a revisão.

Conferência focada independente em1440×900/DPR1, fontes efetivamente loaded:
Simular missão, Continuar e Simular novamente têm padding14; Avançar/Reiniciar
mantêm12. Nos três estados, os nove controles correspondem à fonte em
**X/Y/largura/altura, com todos os deltas0px**; tipografia/padding idênticos.
F07 encerrada; R03/R05/V02/V05/R14 agora passam. Demais aceites e evidências
C6/C5/C4 preservados. Reaproveitados, por autorização expressa, **235pytest,
Node Hive/Codex e browser QA real aprovados noC6**, sem execução redundante.

Evidência `qa-verificador-ciclo7/independent/report.json`, log e par de capturas.
Código/testes/referência somente leitura; não houve Hub real/IAB/8765/IA/mic/voz
ou agentes novos. Chrome/servidor efêmero encerrados. **Tarefa original aprovada
no estado final C7, com exceções autorizadas PNG/aviso de backend e sem backend
Hive implementado.** Histórico anterior preservado.
