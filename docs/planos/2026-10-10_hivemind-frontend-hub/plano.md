# Plano — integração Hive Mind ao Hub

> **Status em 21/10/2026: CONCLUÍDA** — aprovada na verificação independente do ciclo 7 (13/10/2026). Este arquivo é registro histórico do processo e pode descrever intenções já superadas; a referência do código atual está em `docs/hivemind/README.md`. As capturas de QA foram movidas para `.qa-arquivo/2026-10-10_hivemind-frontend-hub/`; caminhos `qa*/` citados abaixo são relativos a essa pasta.

Data inicial: 10/10/2026. Faixa completa. Ciclo final: **7 — sétima rodada expressamente autorizada pelo usuário**.
Status: **APROVADO na verificação independente final do ciclo 7**, GPT-6.1 Sol high. F07 encerrada com delta exclusivo emCSS; testes235/Node/browserC6 reutilizados por autorização expressa. Sete ciclos totais: três originais e quatro adicionais autorizados. Contador e histórico preservados; sem C8 automática.
Não reiniciar contador ao trocar agente/fase/sessão. Ciclos 2/3 somente após reprovação; sem ciclo 4 automático.

## Papéis, autorização e disponibilidade

Estado atual em 12/10/2026: a seleção direta de `gpt-5.6-terra` funcionou e o agente executou o candidato do ciclo 1. A conclusão anterior de indisponibilidade, baseada na lista anunciada de modelos, estava incorreta. Implementação e correções passam ao Terra high; planejamento e verificação permanecem Sol6.1 high. As linhas abaixo preservam o histórico da exceção inicial, sem definir o modelo atual.

- Planejamento: GPT-6.1 Sol (gpt-6.1-sol), high, agente exclusivo de planejamento; não altera código/testes.
- Implementação: GPT-5.6 Sol (gpt-5.6-sol), high, um agente responsável por toda a cadeia. Usuário autorizou expressamente somente nesta implementação, pois GPT-5.6 Terra não está oferecido no mecanismo atual. Regra permanente Terra intacta.
- Verificação: outro agente GPT-6.1 Sol, high, não participante da implementação/correções; somente leitura em código/testes, podendo escrever relatório/Issues.
- Sessão principal controla perguntas/liberação/status. Subagentes não criam agentes/chats.

Roteiro de três etapas e integração frontend primeiro já aprovados. Nova instrução explícita: toda a parte Hive, inclusive protótipo e backend futuro, deve ficar na pasta raiz **HiveMind/**. Movimentar protótipo para HiveMind/prototipo/ está autorizado; documentação processual permanece em docs/planos e testes em tests. Autorização específica recebida para os seis ganchos abaixo: “Autorizar os seis ganchos”. Exigência §5.5 atendida, sem alterar a regra permanente.

## Viabilidade e menor integração

O protótipo é um export de editor: x-dc/sc-for/sc-if, Component extends DCLogic e React.createElement/createRef, carregado por support.js. Não é HTML estático copiável para produção. Sua máquina de estados/fixtures, geometria axial, roteamento de conexões e projeções de gavetas são transportáveis para JS nativo. Extrair comportamento e estrutura visual para DOM/SVG, sem React/runtime do editor e sem iframe transitório.

A página Hive não é um novo provider. Em codex_frontend/static/providers.js, separar **selectedPage** (claude/codex/hive) do **selected provider** (claude/codex). current(), accepts(tab), selection(provider), drafts e lastSession continuam contratos de provider. Hive não recebe sid, modelo IA, histórico do Hub ou registros de sessão. Entrar Hive não chama createSession/selectSession nem muda provider; permite acesso no teto de seis. Sair para Claude/Codex usa select existente e só sai Hive quando essa seleção for válida.

Integrar uma pequena API de página no módulo de navegação existente, por exemplo canUseAssistantUI(), registerPage(id, lifecycle), selectPage(id), mantendo allowAction(tab) exclusivamente por provider. API está somente no frontend. A Hive registra mount/activate/deactivate, e a navegação monta a terceira opção com logo. Não duplicar navegações independentes nem criar ramificações provider==='hive'.

body.dataset.page distingue Hive; body.dataset.assistant continua claude/codex. CSS Hive escopado pela raiz da página e data-page, escondendo/inertizando palco/gavetas/modais Claude/Codex enquanto Hive está ativa, sem destruir/mover os painéis reais nem perder suas preferências. Considerar todos elementos fora do grid (dockL/dockR/minimalToggle, modal/relatório e chrome Codex). O seletor comum permanece acessível. stateChanged/setAudioLevel de Claude não mudam estado/abelhas Hive.

Painel completo: continua Claude original. beforeModeChange sai da página e seleciona Claude como hoje; afterModeChange restaura página preferida no minimalista. Separar preferência de página (por exemplo core.page) da preferência de provider já existente core.assistant. Sem persistir agentes/missões/sessões. Registrar explicitamente boot e ordem dos módulos: import estático do módulo providers no app Hive garante inicialização única; registro posterior aplica restauração Hive se preferida. Falha de carregar Hive deve conservar Claude/Codex operáveis.

## Organização da nova pasta

Estrutura prevista (responsabilidades podem ser refinadas dentro destes limites):

- HiveMind/__init__.py: exportar blueprint frontend.
- HiveMind/frontend/__init__.py e routes.py: blueprint que serve somente assets em /hive-ui/static; sem endpoint IA/dados pessoais.
- HiveMind/frontend/static/app.js: montagem e lifecycle, registro na navegação, CSS e conexão entre peças.
- HiveMind/frontend/static/demo-data.js: AGENTS/STEPS/PHASES/DIV/LINK_INFO/STATE_INFO e indicação inequívoca de dados simulados.
- HiveMind/frontend/static/simulation.js: estado, ações e clock injetável da demonstração (start/pause/resume/retry/approve/adjust/restart/scenario/CRUD).
- HiveMind/frontend/static/geometry.js: coordenadas hexagonais, malha e roteamento; sem DOM/estado de Hub.
- HiveMind/frontend/static/hive.js: células, estados/efeitos e conexões SVG clicáveis.
- HiveMind/frontend/static/drawers.js: três gavetas, agente/relações/skills/ferramentas, missão/aprovação/conversa/entrega.
- HiveMind/frontend/static/hive.css: visual nativo portado e regras scoped.
- HiveMind/frontend/static/bee-animation/bee.js e bee.css: rig portado do módulo recém-criado. Usar URL relativa ao módulo (import.meta.url), export DOM; manter alinhamento/pivôs/cadências/estados. Não carregar createReact se não usado; a cópia runtime não necessita esse adaptador.
- HiveMind/frontend/static/assets/: logo e as seis PNG em operaria-animacao/rainha-animacao; copiar sem redimensionar/recortar/recomprimir.
- HiveMind/prototipo/: conteúdo integral do diretório atual Protótipo Hive Mind Desktop, incluindo versões, support.js, uploads, arte e prévia. support.js continua aqui como referência exportada, **não carregado pelo Hub**.
- Backend futuro nascerá dentro de HiveMind/backend/ quando implementado. Não criar serviço, modelo, endpoints vazios ou arquitetura speculative agora.

Frontend/blueprint/runtime pertencem a HiveMind; somente encaixes mínimos no Hub, processo/docs e testes ficam fora. A separação prototipo versus frontend impede carregar acidentalmente export do editor, e preserva referência integral para comparar.

## Lotes e dependências

Tudo em sequência por **um implementador Sol 5.6 high**. Não há vantagem em paralelizar estas peças: render, estado e navegação dependem entre si; providers/index são compartilhados. O contador é único.

### L0 — movimentação autorizada e baseline

Antes de mover, registrar inventário e SHA256 de **todos** arquivos do protótipo, inclusive .thumbnail/ZIP/PNGs. Resolver origem/destino absolutos; verificar que ambos estão dentro da raiz exata do workspace, origem é diretório esperado e destino HiveMind/prototipo não existe. Criar apenas HiveMind, mover com Move-Item -LiteralPath em um único PowerShell, sem comandos de outra shell e sem sobrescrita. Conferir caminhos e hashes relativos após movimento, corrigir referências vivas do projeto/planos para o novo caminho. Se destino existir, inspecionar/reportar em vez de substituir.

Ler arquivos atuais antes de editar; comparar baseline e executar suíte inicial para distinguir falha prévia. Não mexer no conteúdo visual da referência. Origem deixa de existir após a movimentação, sem cópia antiga redundante.

Baseline informado pela coordenação antes desta tarefa:
index.html SHA256 A3EE776B32621E4FE238F70C588EC9E75D030DD181079ABC995FBC0DEEE99444;
server.py SHA256 A8D3633BD1A6E631B806757FB07071DA5B5A24FE159CD88E52FC005545B0A3AD;
CLAUDE.md SHA256 4142D0D0996D4C5E55266A94361A7CFADD39EC174D743EA2A678BAE99B2C2430.
Hashes são referência fornecida; planejador não recalculou. Checkout não apresentou .git no levantamento; confirmar antes de tentar commits.

### L1 — peças Hive e demonstração nativa

Criar blueprint/rig/dados/estado/geometria/render/gavetas. Portar **todas** informações e ações listadas R03–R10, não substituir gavetas por resumos. Manter fonte confiável para estado explícito (texto+símbolos); animar segundo estado simulado, nunca volume/atividade de agente real. Nomes/inputs com textContent ou criação segura de DOM, sem inserir HTML de usuário.

Clock suspende na invisibilidade e na troca de página; preservar pausa manual. Um controller possui timer/observer/listeners, sem remontagens repetidas. Respeitar prefers-reduced-motion em todas transições/fluxos, além do rig. Não avançar aprovação sem clique.

### L2 — encaixe no Hub

Depois de L1 (autorização específica §5.5 já recebida): import/registro blueprint em server.py; script module no index; integração de navegação em providers.js/CSS Codex e os seis ganchos mínimos abaixo. Não alterar models.js/galaxy.js além de necessidade fundamentada reportada; galaxy.setActive passa a considerar página visível no chamador. current/accepts/selection/provider continuam somente Claude/Codex.

### L3 — testes, documentação e QA

Depois de L2: testes de rotas/isolamento, comportamentais reais de navegação e estado, regressão voz/sid/mobile; documentação Hive e menções recentes do Hub. Rodar testes focados e suíte completa. Servidor QA isolado com serviços stubados, sem processos/voz/IA reais; comparar protótipo movido/runtime com screenshots. Registrar arquivos/resultado/limitações e entregar ao verificador.

### L4 — verificação independente do ciclo 1

Outro agente Sol 6.1 high lê PRD/plano/Issues/diff completo e executa validações pertinentes/suíte/QA. Não corrige código/testes. Emite passou/falhou/não verificável por requisito e aprovado/reprovado/pendente global. Reprovação vira Issue com reprodução/evidência; correções passam ao implementador no ciclo 2 ou 3. Aprovação anterior não valida alterações posteriores.

## Superfície autorizada e restrições

Permitidos: HiveMind/**; mover integralmente Protótipo Hive Mind Desktop para HiveMind/prototipo; server.py somente import/register blueprint; index.html somente loader e ganchos abaixo já autorizados; codex_frontend/static/providers.js (página/navegação/lifecycle) e codex.css (somente interação entre página/nav); tests/test_hivemind_frontend.py e tests/hivemind_frontend_behavior.mjs; testes Codex existentes somente adaptar mocks/asserções afetados sem reduzir cobertura; docs/hivemind-frontend.md, docs/frontend.md, docs/codex-frontend.md, docs/arquitetura.md e menções vivas ao caminho do protótipo; registros desta pasta.

Fora: CLAUDE.md, AGENTS.md, docs/desenvolvimento.md, runtime/voz/mobile, payloads/session lifecycle backend, limites, dependências, remodelagem do HUD. Não modificar protótipo além de sua localização/referências internas que realmente quebrem pelo movimento (se necessária, registrar). Não remover imagens/ZIP/previews/support.js da referência; não trazer runtime de editor para produção. Remover apenas resíduos substituídos nesta integração após conferir uso, sem limpeza de legado.

## Ganchos concretos — autorização específica recebida (§5.5)

A regra literal docs/desenvolvimento.md §5.5 diz: “Se a funcionalidade nova precisar tocar server.py ou index.html, o toque é mínimo (registrar o blueprint, carregar o script) e volta a valer §4.1. Qualquer coisa além disso: pare e pergunte.”

A integração modular já está autorizada. Os ganchos adicionais protegem a página de iniciar Claude invisível e preservam o turno já enviado; o usuário respondeu “Autorizar os seis ganchos”; a coordenação registrou a autorização específica antes de L2. Não mudar regra permanente.

Contrato proposto no módulo de navegação:
~~~js
canUseAssistantUI() { return selectedPage !== 'hive'; }
~~~
Usar hook opcional para preservar execução sem módulo/mocks antigos.

1. startListening (index atual ~2049), antes de getMic:
~~~js
if (window.hubProviders?.canUseAssistantUI?.() === false) return;
~~~
2. runSkill (~2285), antes de recordTurn, mesma linha acima.
3. sendTextPrompt (~2601), antes de recordTurn, mesma linha acima.
4. Rechecagem após await getMic (~2057), condição existente:
~~~js
if (tab!==activeTab() || tab.ui!=='idle' || !tabs.includes(tab)
    || window.hubProviders?.canUseAssistantUI?.() === false) {
  acquired.getTracks().forEach(track=>track.stop());
  return;
}
~~~
5. Handler global document.keydown (~2377), primeira guarda:
~~~js
if (window.hubProviders?.canUseAssistantUI?.() === false) return;
~~~
6. Autoativação mobileTurnStart (~3236), adicionar guarda à condição atual:
~~~js
if (at && at !== tab && at.ui === 'idle'
    && window.hubProviders?.current() !== 'codex'
    && window.hubProviders?.canUseAssistantUI?.() !== false)
  activateTab(tabs.indexOf(tab));
~~~

Manter allowAction(tab) por provider e **não** adicionar guarda de página em askAndSpeak/streamAsk/onRecStop. askAndSpeak (~2232) é continuação de STT já autorizado; bloquear por página quebraria o turno. Somente entradas UI e captura obsoleta são bloqueadas. Parar/limpar/criar sessões continua inacessível pela UI oculta/inert; não alterar seus contratos por efeito colateral.

## Riscos fundamentados e mitigação

- index2057 descarta mic pela mudança de tab, mas Hive não troca tab: adicionar rechecagem de página.
- askAndSpeak2232 usa allowAction depois da transcrição: separar continuação provider de entrada UI.
- keydown2377 chama onMain/onPause/onStop independentemente de alvo Hive: guarda de página evita comandos invisíveis.
- mobileTurnStart3236 guarda somente Codex: manter espelho atualizando, proibir foco Hive.
- providers.select aceita somente dois providers e cria sessão quando ausente: página separada evita sid Hive, consumo do teto e opções IA falsas.
- Documentos Codex/painel completo têm preferências/rascunhos próprios: testar retorno/reload/composição e carga tardia, sem guardar Hive em core.assistant.
- Protótipo assume mínimo1200×760 e gavetas392×300: QA em1280×800/1440×900/1920×1080, rolagem interna e ajustar fit para conteúdo acessível.
- bee.js atual usa document.currentScript.src e createReact: adaptar URL ao ES module em cópia runtime; preservar integralmente referência.
- Protótipo atualiza a cada100ms e usa Date.now: portar clock com suspensão explícita; testes com relógio controlado.
- Estilos body/html/a/input exportados poderiam vazar: escopar CSS e não sobrescrever variáveis/acento do Hub.
- Capturas de UI são necessárias; teste estático não prova gavetas/legibilidade. Sem QA/verificador aprovação fica pendente.

## Pendências/decisões

A autorização específica dos seis ganchos §5.5 foi recebida: “Autorizar os seis ganchos”. Não há decisão humana relevante pendente para executar o escopo planejado. Roteiro, frontend primeiro, demonstração explícita, Sol5.6 excepcional e localização/movimentação HiveMind já autorizados. Choices internos de módulos/rolagem/lifecycle são propostas concretas dentro desse escopo; se execução descobrir alteração significativa de UX/contrato/backend, reportar antes de ampliar.

## Fontes localizadas

providers.js: current/accepts/allowAction/select/decorate/beforeModeChange/afterModeChange e keys core.assistant/drafts/lastSession.
index.html: MAX_TABS1591, newTab1621, addTab1695, guards2050/2232/2286/2602, mic2057, keyboard2377, minimal2418, beforeunload3188, mobile3236 e hubFrontend3324 (linhas baseline, revalidar).
server.py: import56/register107, MAX_SESS500, binding1423.
tests/test_codex_frontend.py e codex_frontend_behavior.mjs: testes de catálogos/guardas/sessões, STT diferido/mic e geometria.
Protótipo e bee-animation no PRD; após L0 fonte viva HiveMind/prototipo. Nenhuma pesquisa externa necessária para esta decisão baseada em código local.

## Atualização de referência — 10/10/2026, 17:15:26 BRT (prioridade sobre inventário anterior)

O usuário substituiu o protótipo dentro de HiveMind pela versão mais recente e pediu frontend **exatamente fiel** ao novo desenho, com sombra, degradê e profundidade em 2D, cores de gavetas e menor mudança necessária no código existente, sem sobras. Não se trata de reprovação: permanece ciclo **1 de 3**, em andamento. Não refazer movimentação L0 nem restaurar a versão antiga sobre os arquivos atualizados.

Referência vigente: **HiveMind/prototipo/Hive Mind.dc.html**, 134879 bytes, mtime UTC 2026-10-10T20:15:26.774Z, SHA256 **03B05ACDDD71DA6C6C2E81D3AE14ADC6B08D4EBB340E44C1CE3D41A92CF8DAD6**. Hive Mind v1.dc.html não é a versão escolhida. Capturas qa/reference-1440x900.png e runtime-* têm mtime anterior (~20:13 UTC): são evidência histórica, não baseline visual nova.

### Inventário vigente de referência (6 arquivos)

| Arquivo relativo a HiveMind/prototipo | Bytes | SHA256 |
|---|---:|---|
| .thumbnail | 27432 | 2DBD762F0EA4E45D3B2BBB8FEBC2788E5A8C39DF798E1AF39DEADB87871D3ACC |
| assets/hive-mind-logo.png | 468642 | 6A5399F3055504ADFA2E416D8F88C35EB481FA579BACD6377FAAB6D1A44BFBA4 |
| Hive Mind v1.dc.html | 43589 | EB983AE65F4AB649BA078374B3C0A10DDA79BCEE87B8615FB1D70E781E62E7D0 |
| Hive Mind.dc.html | 134879 | 03B05ACDDD71DA6C6C2E81D3AE14ADC6B08D4EBB340E44C1CE3D41A92CF8DAD6 |
| support.js | 69150 | 8FE7DF74405F3C55F49B7249C74EA1397E65D07DEA2B1BD3B4A489BEC2E28CBE |
| uploads/Hive Mind Logo.webp | 108810 | 7BAAC77F807A8C572D35D99AF339E73C299ACE75CDE75A9615BD249764AEB22E |

Todos esses mtimes estão entre20:15:26.759–20:15:26.805 UTC, consistente com a substituição humana comunicada. O inventário **21/21 anterior pertence à referência anterior**, não diagnostica perda/falha desta implementação após a atualização do usuário. Não recriar bee-animation/assets/ZIP antigos dentro de prototipo. As seis PNG e o rig sobrevivem em frontend/static, preservados enquanto se decide preferência de abelhas.

### Limite explícito de abelhas

O novo HTML usa desenho SVG nativo em bee(o), linhas1078–1116, e não importa bee-animation. Personagens/poses/tamanhos diferem: operária40×40, sub28×28, Rainha50×56, ícone de lista22 (Rainha22×24.75), contra PNG64/56/40/26 da etapa anterior. A coordenação apresentou escolha opcional PNG versus SVG; preservar PNG previamente autorizadas como preferência se não houver nova resposta após a janela razoável. Até decisão, não trocar/retocar/destruir o rig ou as PNG. A diferença escolhida deve ser declarada no aceite visual; não alegar identidade dos pixels das abelhas caso se conservem PNG. Todo restante segue exatamente a nova referência, sem redesenho próprio.

### Inventário concreto CSS/DOM/efeitos — fonte atual → ajuste nativo

Linhas abaixo são do novo HTML e precisam ser conferidas imediatamente antes de editar. Portar valores/estrutura, não imitar aproximadamente por regras novas de precedência.

| Superfície | Referência vigente | Diferença nativa atual / destino focal |
|---|---|---|
| Tipografia/header | Space Grotesk400/500/600/700 display; Source Sans3 400/500/600/700 corpo; header52px papel, border-bottom1.5px, padding0 20px 0 6px; nav texto14px padding0 16px/linha inferior3px, logo24px. Toggle switch28×16 e knob9×9. | hive.css usa SegoeUI, nav herdada Codex é moldura e uppercase espaçada; checkbox comum e duas faixas de aviso cobrem HUD. Corrigir hive.css/app.js e somente CSS data-page=hive em codex.css. Aviso simulado/backend necessário deve integrar badge/legenda sem deslocar composição. |
| Mundo único | renderVals1158–1164: DW392/BH300; visW=hw−gavetas laterais; visH=hh−bottom; ws=max(.5,min(1,(visW−60)/820,(visH−40)/740)); wx=leftDrawerOffset+visW/2; wy=visH/2+((showSubs?54:24)+(alert?22:0))*ws. Mesmo container transform para mesh/cells/links. | Nativo SVG esticado em viewBox −850−5501700×1100 e cells pixels fixos em50%/50%, sem reserva drawers; causam desalinhamento/oclusão. Substituir composição de scene em hive.js/geometria; ResizeObserver único. |
| Malha iluminada 2D | meshLayer925–945, viewBox−1800−1150 3600×2300, radius72/W124.7077, hex topo vertical. Cinco tons #C2920F/#BD8C0D/#B8860B/#B3820A/#AD7E09; por tile gradiente x1.3/y1=0/x2.7/y2=1, mix branco7%/preto6%; distribuição v=−(x*.00045+y*.0006)+.45*sin(q*.85+r*.35)*cos(r*.6−q*.25), lvl=clamp(round(2−v*1.6),0,4); patterns W×3R; malha stroke rgba(0,0,0,.13)1px. | geometry.meshPath atual gira hex−30 e só desenha traço uniforme; trocar por funções geométricas/mesh e defs SVG portadas. Sem textura raster inventada/3D/gradiente único sobre toda tela. |
| Preenchimento células | hm-occ stops0 #CB9C25/.55 #B8860B/1 #A27408; hm-occ-sel0 #FBF8F2/.55 #F1EDE4/1 #E0D7C6; hm-queen0 #3B352E/.5 #17140F/1 #000000, mesma direção dos gradientes de mesh. | button clip-path com background papel/mostarda/preto e outline não reproduz borda/relevo. Substituir representação visual por SVG polygon mantendo wrapper/keyboard/hits acessíveis; remover clip-path/outline/backgrounds antigos que foram substituídos. |
| Bisel/sombra | Operária/Rainha124.71×144; sub100.46×116. Filtro operária drop-shadow(0 3px 3px rgba(0,0,0,.3)); Rainha0 4px4px rgba(.34); sub0 2px2.5px rgba(.28). Polyline superior operária/Rainha3.46,38 62.35,4 121.24,38 width2; inferior121.24,106 62.35,140 3.46,106 rgba(0,0,0,.26). Sub superior3.03,30.75 50.23,3.5 97.43,30.75 width1.6 e inferior97.43,85.25 50.23,112.5 3.03,85.25. Highlights branco95% quando selected/rgba(255,238,190,.6) normal/Rainhaescura rgba(241,237,228,.32). | CSS box-shadow dentro clip-path não demonstra relevo; usar filhos SVG reais e filtro no SVG externo como fonte. Texto e hits sem filtro; preservar pointer-events do protótipo. |
| Estado visual | cellFx1118–1127 e queenFx1129–1135: trilho interno march em trabalho; progresso no perímetro5px; aprovação anel fino; falha tracejado; Rainha coord anel segmentado, done hm-draw, seleção contorno claro; queen sweep/ripple em linksLayer. | Native tem brilho/outline/background negro por status, sem sourceFx; substituir efeitos, não manter estilo antigo em paralelo. Símbolos do status e shortOf são parte da informação/texto. |
| Rotas/fluxos | buildGraph/route/getRoutes948+ segue vértices da malha, penaliza células ocupadas8 e aresta já usada2.5. linksLayer distingue ida/in/ret reversos, pulsos out12 60 versus resultado6 4 6 56, duração.62s padrão, path violeta9px+papel3px, base/arrow/endpoints/hit transparente18px. Idle dotted1.5 5, del3.5px preto, wait6 5, done/ret2px preto; failX. | routeBetween atual L ortogonal simplificado; marker duplo não reverte trajeto; cor done violeta diverge. Portar geometria/stack SVG diretamente, sem mudar seleção/contrato simulação. Popup Conexão flutua no mundoHUD, não apenas texto em gaveta. |
| HUD e z-order | HUD top16px/h44 em wx; missãosimulada+sete pequenos hex+texto+ação; alerta abaixo em approval/fail. Z ordem: header30, links/células/malha no mundo, popup7/HUD6, bottom10, side12, entrega20. | Native só aviso superior e controls gaveta; criar HUD no hive.js/app.js, reaproveitar ações/status existentes. Não cobrir HUD com avisos redundantes. |
| Alças/gavetas | Side392px, alça38×152 top50%−76. Alça inferior36px acima bottom300px; side labels vertical e ícone+count/badge; alça aberta mostarda/fechada papel. Sombras alça esquerda4px2px10px rgba(.18), direita−4px2px10px(.18), bottom0−4px10px(.16). Sombras drawer abertos8px0 26px(.28)/−8px0 26px(.28)/0−8px26px(.24), fechados none. Bottom left/right deslocam392 conforme side. | Native tabs independentes sempre borda viewport, bottom largura inteira e sem badge; portar wrappers/transforms/alças em drawers.js/hive.css, preservar aria-expanded/teclado. |
| Cabeçalhos/painéis | Side heads240/478: padding18px20px16px, bg#2A2622/fg#F1EDE4, ícone mustard13×15, border-bottom3px#B8860B; title22px600. Subtexto#D8D0C0; badge#D9AC3C. Bottom head182+: padding12px22px11px/title17; botão fechar claro/contorno rgba(241,237,228,.4). Andamento right490 bg#E9E2D3 padding14px20px16px. | Native heads monocromáticos/titleline e right progress/text separados; reorganizar subárvores em drawers.js em vez de apenas backgroundpaint. Manter rolagem única rightbody e fixar heads/foot como fonte. |
| Agentes/detalhes | row wrapper270 bg selected#E7DFCE/inset4px0 0#B8860B; margemtop4; indent sub22px; grid34px minmax(0,1fr) auto, icon/progresso/símbolo. Details dentro da linha com padding0 14px16px18px, tabs/infos sem card borda2. Counters no cabeçalho. | Native lista sem ícones/contadores e card separado com borda; substituir DOM visual diretamente, conservar tabs/actions/inputs seguros. |
| Criar operária | Footer437+: botões Criar operária/Excluir agente+nota; form oculto até abrir, destino explícito e célula livre **somente ao criar**; nome/spec lado a lado, botãoCancelar, especialidade opcional como protótipo. Sem três células livres permanentes. | Native form sempre aberto, spec required e slots permanentemente visíveis. Portar form UI/estado mínimo em drawers.js/simulation.js; dados/IDs/cap máximo3 preservados; sem um CRUD paralelo. |
| Conversa/entrega | Bottom log autor/contexto+símbolo/actions de approve/adjust/retry/restart onde aplicável; label O que você quer...; input44px. Entrega sem máscara escura inventada, centro entre side drawers, max700/padding22px26; tabela4 colunas/header e cards stats numéricos. | Native p tags simplificados/placeholder diferente, overlay dark/max760 e sem table headings; substituir markup visual em drawers.js. Não conectar sistemas/relatórios reais. |

### Menor cadeia de alteração — mesmas peças, sem refatoração do Hub

1. Registrar baseline acima e preservar prototipo como somente leitura. A execução inicial já criou HiveMind e ganchos/navegação; **não repetir L0–L2 nem reescrever providers/index/server**.
2. Ajustar geometry.js e hive.js em conjunto: malha/defs, roteamento, container único, células e efeitos, HUD/popup. Trocar a representação simplificada pelo port nativo da referência. Não duplicar render antigo em modo alternativo.
3. Ajustar drawers.js e hive.css diretamente: hierarquia/cores/tipografia/badges/ações/rolagem/layout. app.js somente carga font/final CSS e mudanças necessárias no shell/invalidação de layout. simulation.js somente estado UI/derivações indispensáveis a form/HUD/progresso e preservação de ações do PRD; conservar relógio/lifecycle/guardas já implementados.
4. Consolidar os cinco overrides de layout.css no seletor correto de hive.css e remover folha+import em app.js quando redundantes. Não criar patch2.css/mais overrides. Se necessário dividir CSS, justificar responsabilidade real, não precedência.
5. codex_frontend/static/codex.css: editar somente bloco body.minimal[data-page=hive] para navigation14px/underline e fonte/padding da referência. providers.js/index/server permanecem intactos por padrão. Reportar necessidade funcional nova antes de alterar.
6. Atualizar testes Hive necessários e documentação final; não enfraquecer isolamento/voz/session assertions. Remover asserts que impõem presença de arquivos do protótipo anterior substituído pelo usuário, substituindo pelo inventário atual verdadeiro. Rodar toda suíte e QA pareado; novo verificador independente final ainda exigido.

Arquivos focais: HiveMind/frontend/static/{geometry.js,hive.js,drawers.js,hive.css,app.js,layout.css}; simulation.js apenas UI mínima; codex_frontend/static/codex.css somente regras Hive; tests/{test_hivemind_frontend.py,hivemind_frontend_behavior.mjs,hivemind_browser_qa.mjs}; docs/hivemind-frontend.md e quatro registros. Referência, assets/rig escolhidos, backend, limites, payloads, index e server protegidos do redesenho visual.

### Aceite de fidelidade V01–V08 (adicionais a R01–R14)

- **V01 Referência**: seis arquivos/hashs atuais preservados, novo HTML SHA corresponde; capturas da nova referência geradas, anteriores mantidas como histórico em diretório distinto. Não usar screenshot anterior/thumbnail reduzida como único aceite.
- **V02 Tipografia/composição**: mesma viewport/DPR/fonts loaded/fase/progresso/drawers/selection. Cabeçalho/nav/HUD/células/alças/gavetas/popup/entrega com mesmas bounds e tipografia/lineheight/paddings (diferença de arredondamento até1px), nenhuma diferença estrutural explicada como “estilização”.
- **V03 Profundidade2D**: stops/direção/distribuição de todos gradientes, biséis e sombras correspondem aos valores da fonte; aprovar só com comparação visual, não tokens CSS presentes.
- **V04 Mundo/fluxos**: mesh/cells/links usam um transform e mantém alinhamento em drawerstates/resize; routes/arrowdirections/pulsos/estado usados na referência, sem ortogonal simplificado.
- **V05 Gavetas**: headers escuros/faixa mostarda/rows selecionados/Andamento bege/badges/alças/counters e todos campos/actions/layout igual referência; forms/chat/entrega sem controles omitidos ou alterações arbitrárias.
- **V06 Estados**: comparar idle/p2b/approval/fail/done, seleção de agente/sub/link, form aberto e três drawers; reduced motion em ambas. Frames de animação congelados/progresso controlado para comparação, sem comparar screenshots fases distintas.
- **V07 Exceções explícitas**: única diferença visual de personagem caso PNG mantida + aviso backend/simulação exigido; documentar decisão/tamanhos. Identificação não autoriza outros desvios de composição. Se SVG escolhida, renderSVG referência e remover caminho runtime PNG substituído após conferir usos, preservando arte do usuário.
- **V08 Sem sobras/regressões**: render/rotas/estilos antigos diretamente substituídos removidos, layout.css redundante removida/import conferido; todos testes/regressões/QA e verificação independente do estado final; guardar evidências de cada diferença corrigida.

QA precisa usar novas capturas pareadas em1440×900,1920×1080,1280×800, fonts pronto/DPR igual. Harness atual aborta HTTPS/fontes e espera .hm-bee-asset no protótipo novo, que não existe: corrigir preparação/asserts conforme referência atual sem restaurar HTML antigo. Teste de presença de tokens/abas não prova fiel. Usar diff/overlay por região e conferência de bounds/computedstyles; não esconder desvios grandes sob limiar global de pixels. CasoPNG, excluir apenas região exata das abelhas na comparação automática, e inspecionar manualmente dimensão/posição delas. Todo desvio restante necessário deve ser reportado, não aprovado silenciosamente.

## Execução do ciclo 1 — 12/10/2026

Implementador: GPT-5.6 Terra, high. A implementação existente foi preservada e
ajustada nos módulos Hive, sem reescrever provider, index ou servidor. Ajustes
finais incluíram fallback dos subagentes após a coleta, ordem de definições de
links igual à fonte para o roteador, sombras CSS no SVG externo, HUD e alerta
de aprovação completos, slots estáveis de CRUD e preservação de rascunhos/foco.

O comparador `tests/hivemind_visual_compare.mjs` serve o protótipo sem o seu
bootstrap duplicado, injeta React somente no harness, congela estados/reduced
motion e grava pares e diffs por região. Ele cobre idle nos viewports
1280×800, 1440×900 e 1920×1080 e seis pares 1440×900: p2b-subagent,
approval, failure, done, selected-link e worker-form. Artefatos atuais:
`qa-atual/metrics.json` e `qa-atual/states/`. O rig PNG é a exceção visual
autorizada; não houve edição de assets.

## Liberação do ciclo 2 — 12/10/2026

Ciclo 1 formalmente REPROVADO; relatório e oito Issues gravados pelo verificador independente. Ciclo 2 registrado antes das correções. Responsável único: agente implementacao_hivemind_terra, GPT-5.6 Terra high. Cadeia sequencial limitada a HM-F01–HM-F08, preservando o protótipo, assets PNG e os passes de integração/voz/mobile/lifecycle. Não ampliar os encaixes em server/index/providers nem criar backend. Atualizar testes de regressão e confronto pareado de conteúdo/subárvores sem enfraquecer critérios. Após os checks, congelar candidato e encaminhar ao mesmo verificador independente Sol6.1 high. Ciclo 3 permanece disponível somente após nova reprovação; sem ciclo 4 automático.

## Liberação do ciclo 3 — 12/10/2026

Verificador independente Sol6.1 high emitiu REPROVADO no ciclo 2 com evidências: F01 e F06 corrigidas; F02/F03/F04/F05/F07/F08 parcialmente pendentes, incluindo animação Queen coord ainda ativa durante pausa. Ciclo 3 registrado antes de nova implementação. Responsável único permanece GPT-5.6 Terra high, limitado às pendências e referências exatas do handoff independente. Relatório do ciclo 2 será preservado em Issues/verificação. Fonte read-only, rig PNG e integração aprovada intactos. Toda seção omitida e comportamento derivado deve ser confrontado diretamente com a fonte, não aproximado. Não declarar fidelidade por containers. Após checks e congelamento, verificador independente Sol6.1 high avalia o estado final. Último ciclo total; se reprovado ou não verificável, parar e relatar diagnóstico.

### Handoff de contexto no ciclo 3

Agente correcoes_hivemind_terra_c2 encerrou escritas/processos e informou entrega parcial, sem bloqueio externo e sem congelamento. Cadeia restante transferida sequencialmente ao agente hivemind_terra_final, também GPT-5.6 Terra high, em contexto novo menor. Nenhum escritor concorrente e nenhum novo ciclo. Pendências F04 integral, F05 integral, F07 estrutural/estilos e F08 final; alterações parciais F02/F03/F09 precisam reteste real. Ciclo permanece3/3; verificação independente posterior avaliará o estado final.

## Registro do ciclo 3 — 12/10/2026

Correções sequenciais executadas por GPT-5.6 Terra high. O candidato segue para verificação independente Sol, sem criar ciclo adicional. Referência e rig autorizados foram preservados; a evidência local de pares está em `qa-ciclo3-comparator/`.

## Encerramento pelo teto — ciclo 3

Verificador independente confirmou REPROVADO no ciclo 3. Suíte235, Node, QAChrome e comparador passaram, mas verificação por38combinações/27pares/3viewports confirma pendências reais: detalhes não acompanham ticks, aprovação é sobrescrita pelo updater, sweeps recriados a cada tick, composição vazia deslocada e popup/subárvores/estilos inexatos. F09 (pausaQueen e delay oculto da entrega) passou; invariantesHub preservados. Não declarar implementação concluída nem iniciar backend/rodada4 automaticamente. Código mantido no candidato final, sem rollback ou novas correções. Relatório e Issues contêm diagnóstico para uma decisão explícita de continuação.

## Rodada adicional autorizada — ciclo 4

Após o diagnóstico independente e a interrupção pelo teto, o usuário respondeu expressamente “Autorizo” à pergunta sobre uma rodada adicional focada nas pendências. Liberação concreta: F02 composição vazia dentro do mundo/fit e conteúdo das gavetas; F03 popup/amostras/legenda; F04 detalhe por tick, approval/fail e textos integrais; F05 continuidade dos nós animados e valores/estados da fonte; F07 wrappers/medidas/ícones/fontes; F08 remoção de código diretamente substituído e testes que detectem as falhas reais. Manter F01/F06/F09 e todos os passes do Hub. Um único implementador Terra high, cadeia sequencial com arquivos compartilhados. Fonte/PNGs e monolitos protegidos; sem backend ou restart. Conferir critérios antes de congelar; Sol high independente verifica o candidato final. Se reprovado ou pendente nesta rodada, interromper e apresentar diagnóstico; nenhuma quinta rodada automática.
