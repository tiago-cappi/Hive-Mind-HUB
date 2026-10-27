// Comparador visual do Hive Mind: demonstração x protótipo (ciclo 7) e modo real x protótipo (V09).
//
// Como rodar (a partir da raiz do projeto; não há package.json nem node_modules no repositório):
//   $env:NODE_PATH = "<pasta com node_modules que tenha playwright e sharp>"     # PowerShell
//   node tests/hivemind_visual_compare.mjs [pasta-de-saída]
// Nesta máquina: NODE_PATH="C:/Users/m.rafael/Desktop/projetos/CRM Clean Environment Brasil/frontend/node_modules;C:/Users/m.rafael/Desktop/Projetos Pessoais/forest-os-web-master/forest-os-web-master/node_modules"
// Pré-requisitos: Chrome em C:/Program Files/Google/Chrome/Application/chrome.exe, React/ReactDOM em
// .test-tmp/hivemind-bees/ e o protótipo em HiveMind/prototipo/. Não toca a porta 8765: sobe o próprio servidor.
// Saída (padrão .qa-arquivo/2026-10-10_hivemind-frontend-hub/qa-atual): pares idle, `states/` (demonstração, com
// diffs por região), `real/` (modo real x protótipo) e `metrics.json`. Sai com erro se algo diferir.
//
// 1) Demonstração (abre pelo botão `.hm-mode`): 3 viewports idle e 6 estados congelados, geometria dentro de 1,01 px.
// 2) Modo real: `/hive-api` falso servido de tests/fixtures/hivemind_real_paridade.json, 13 casos (execução, aprovação,
//    falha, entrega, abas do agente e da Missão, conexão) e o critério descrito no bloco "Modo real (V09)" abaixo.
// O teste de estouro (V08) está em tests/hivemind_overflow.mjs.
import {createRequire} from 'node:module';
import {createServer} from 'node:http';
import {readFile,mkdir,writeFile} from 'node:fs/promises';
import {extname,join,normalize} from 'node:path';
import process from 'node:process';

const require=createRequire(import.meta.url),{chromium}=require('playwright'),sharp=require('sharp'),root=process.cwd(),output=process.argv[2]||join(root,'.qa-arquivo','2026-10-10_hivemind-frontend-hub','qa-atual');
await mkdir(output,{recursive:true});
const mime={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.png':'image/png','.webp':'image/webp'};
const fileFor=url=>{const path=decodeURIComponent(new URL(url,'http://local').pathname);if(path==='/')return join(root,'index.html');if(path.startsWith('/codex-ui/static/'))return join(root,'codex_frontend','static',path.slice(17));if(path.startsWith('/hive-ui/static/'))return join(root,'HiveMind','frontend','static',path.slice(16));if(path.startsWith('/assets/'))return join(root,'assets',path.slice(8));if(path.startsWith('/prototype/'))return join(root,'HiveMind','prototipo',path.slice(11));return null;};
const server=createServer(async(req,res)=>{const path=new URL(req.url,'http://local').pathname;if(path.startsWith('/hive-api/')){res.writeHead(200,{'content-type':'application/json'});res.end(JSON.stringify(hiveApi(path.slice(9),new URL(req.url,'http://local').searchParams)));return;}if(path==='/codex-ui/models'){res.writeHead(200,{'content-type':'application/json'});res.end('{"source":"snapshot","backendReady":false,"models":[]}');return;}if(path==='/reports'){res.writeHead(200,{'content-type':'application/json'});res.end('[]');return;}if(path.startsWith('/session_watch/')){res.writeHead(200,{'content-type':'application/json'});res.end('{"rev":0,"lines":[]}');return;}if(['/session_start','/hud_ping','/hud_bye'].includes(path)){res.writeHead(200,{'content-type':'application/json'});res.end('{"ok":true}');return;}const file=fileFor(req.url);if(!file||!normalize(file).startsWith(root)){res.writeHead(404);res.end();return;}try{let body=await readFile(file);if(file.endsWith('Hive Mind.dc.html'))body=Buffer.from(body.toString().replace('<script src="./support.js"></script>',''));res.writeHead(200,{'content-type':mime[extname(file)]||'application/octet-stream'});res.end(body);}catch{res.writeHead(404);res.end();}});
// ---------------------------------------------------------------------------------------------
// Modo real (V09). O servidor falso devolve a fixture `hivemind_real_paridade.json` em `/hive-api/`.
// Em cada caso o modo real e o protótipo ficam no mesmo estado visual e os componentes equivalentes
// são comparados assim (o protótipo é inline-style com `data-dc-tpl` estável: o arquivo é fixado por hash):
//   - estilo computado (fonte, tamanho, peso, espaçamento de letras, cores, bordas, raio, sombra,
//     espaçamentos internos) com tolerância de 0,51 px nos números;
//   - dimensões (`w`, `h`) e posição (`p`, `y`) só onde o conteúdo não decide a medida, com a mesma
//     tolerância de 1,01 px do ciclo 7;
//   - recortes (`crops`) comparados por pixel (até 0,5 % dos pixels com diferença > 32) onde o desenho não
//     tem texto (abas puxadoras; hexágonos do HUD e segmentos da tira de etapas saem por estilo SVG/CSS,
//     porque o recorte de formas pequenas varia com a posição fracionária);
//   - região do mapa por pixel com o rig PNG das abelhas mascarado (D4), só informativa em metrics.json.
// Onde o modo real mostra dado diferente do protótipo (textos, contagens) o texto não é comparado: vale a estrutura
// e o estilo. `skip`/`only` restringem as chaves de estilo de um par, sempre com o motivo ao lado.
// Linha de base: os mesmos pares são medidos na demonstração, aprovada no ciclo 7 contra o protótipo. Uma diferença só
// FALHA se o modo real difere do protótipo E da demonstração. Se for igual à da demonstração, é "herdada" e vai para
// metrics.json (real.inherited). `KNOWN` lista diferenças do modo real já conhecidas, com o motivo (real.known).
// ---------------------------------------------------------------------------------------------
const hive={fixture:await readFile(join(root,'tests','fixtures','hivemind_real_paridade.json'),'utf8').then(JSON.parse),scenario:'running'};
const hiveApi=(api,query)=>{const sc=hive.fixture.scenarios[hive.scenario];if(api==='/status')return hive.fixture.status;if(api==='/catalog')return hive.fixture.catalog;if(api==='/missions')return [sc.mission];if(api.startsWith('/missions/m1')){const after=Number(query.get('after')||0);return {...sc,events:sc.events.filter(event=>event.seq>after)};}return {ok:true};};
const FREEZE='*,*::before,*::after{animation:none!important;transition:none!important;caret-color:transparent!important}';
const LOG=[{type:'user',text:'Quero conferir os pedidos recebidos esta semana.'},{type:'event',tag:'Rainha',text:'Entendi. Aqui está o plano proposto para a sua aprovação.',kind:'coord'}];
const STYLE_KEYS=['font-family','font-size','font-weight','font-style','line-height','letter-spacing','text-transform','text-align','color','background-color','background-image','border-top-left-radius','box-shadow','padding-top','padding-right','padding-bottom','padding-left','opacity','text-decoration-line'];
const SVG_KEYS=['fill','stroke','stroke-width'];
const FONT_KEYS=['font-family','font-size','font-weight','color'];
const TEXT_KEYS=['font-family','font-size','font-weight','font-style','line-height','letter-spacing','text-transform','text-align','color','text-decoration-line'];

// [nome, seletor no modo real, id `data-dc-tpl` no protótipo, medidas ('w' largura, 'h' altura, 'p' posição, 'y' topo), opções]
const STEPS=idx=>[...idx].map(([kind,real,proto])=>[`hud-step-${kind}`,'.hm-hud-steps polygon',99,'',{only:SVG_KEYS,pchild:'polygon',ridx:real,pchildIdx:proto}]); // hexágono feito, atual ou futuro do HUD
// segmentos da tira de etapas: feito (a cor está no preenchimento interno do protótipo), atual de espera e futuro
const SEGMENTS=[['segment-done','.hm-step-strip i',374,'',{only:['background-color'],ridx:0}],['segment-current','.hm-step-strip i',373,'',{only:['background-color','border-top','border-right','border-bottom','border-left'],ridx:4,pidx:4}],['segment-future','.hm-step-strip i',373,'',{only:['background-color','border-top'],ridx:6,pidx:6}]];
const HUD=[['hud','.hm-hud-main',97,'hy'],['hud-label','.hm-hud-main > strong',98],['hud-text','.hm-hud-text',103]];
const PULLS=[['pull-left','.hm-pull-left',163,'whp'],['pull-left-label','.hm-pull-left > span:nth-of-type(2)',166,'',{only:FONT_KEYS}],['pull-right','.hm-pull-right',350,'whp'],['pull-right-label','.hm-pull-right > span:nth-of-type(2)',353,'',{only:FONT_KEYS}],['pull-bottom','.hm-pull-bottom',117,'hy'],['pull-bottom-label','.hm-pull-bottom > span:nth-of-type(2)',120,'',{only:FONT_KEYS}]];
const CELLS=[['cell-queen','.hm-cell-queen',66,'whp'],['cell-queen-name','.hm-cell-queen strong',75],['cell-queen-state','.hm-cell-queen .hm-cell-state',76],
  ['cell-worker','.hm-cell[data-agent="bee-documentos"]',44,'whp',{pidx:0}],['cell-worker-name','.hm-cell[data-agent="bee-documentos"] strong',50,'',{pidx:0}],['cell-worker-state','.hm-cell[data-agent="bee-documentos"] .hm-cell-state',51,'',{pidx:0}]];
const LEFT=[['left-side','.hm-side-left',162,'whp'],['left-panel','.hm-agents',168,'wh'],['left-head','.hm-agents .hm-drawer-head',169,'wh'],['left-head-line','.hm-agents .hm-head-line',170,'wh'],['left-title','.hm-agents .hm-head-title strong',174],['left-close','.hm-agents .hm-close',175,'wh'],['left-sub','.hm-agents .hm-head-sub',178],
  ['left-counters','.hm-agents .hm-counters',179],['left-counter','.hm-agents .hm-counters > span',181],['left-scroll','.hm-agents .hm-drawer-scroll',183,'w'],
  ['row-wrap','.hm-agents .hm-agent-row-wrap',201],['row','.hm-agents .hm-agent-row',202,'wh'],['row-icon','.hm-agents .hm-row-icon',203,'wh'],['row-copy','.hm-agents .hm-row-copy',204],['row-title','.hm-agents .hm-row-title',205],['row-name','.hm-agents .hm-row-title strong',206],['row-state','.hm-agents .hm-row-copy > span:last-child',208],['row-ending','.hm-agents .hm-row-ending',209],
  ['foot','.hm-agents .hm-drawer-foot',321,'w'],['foot-actions','.hm-agents .hm-drawer-foot .hm-foot-actions',323],['foot-create','.hm-agents .hm-drawer-foot .hm-foot-actions button:first-child',324,'h'],['foot-note','.hm-agents .hm-drawer-foot .hm-foot-note',329]];
const DETAIL=[['detail','.hm-agent-detail',211,'w'],['detail-tabs','.hm-agent-detail .hm-tabs',212,'wh'],['detail-tab-active','.hm-agent-detail .hm-tabs .active',214,'h'],['detail-body','.hm-tab-body',216],['detail-group','.hm-tab-body .hm-detail-group',218],['detail-label','.hm-tab-body .hm-detail-group .hm-label',219],['detail-text','.hm-tab-body .hm-detail-group p',220],
  ['state-group','.hm-tab-body .hm-detail-group',221,'',{filter:'Estado'}],['state-label','.hm-tab-body .hm-detail-group .hm-label',222,'',{filter:'Estado'}],['state-line','.hm-detail-state',223],['state-name','.hm-detail-state strong',224],['state-copy','.hm-detail-copy',225],['state-bar','.hm-segment-progress',227,'wh'],
  ['desc-group','.hm-tab-body .hm-detail-group',231,'',{filter:'Descrição'}],['desc-label','.hm-tab-body .hm-detail-group .hm-label',232,'',{filter:'Descrição'}],['desc-text','.hm-tab-body .hm-detail-group',233,'',{filter:'Descrição',child:'p'}]];
const RIGHT=[['right-side','.hm-side-right',349,'whp'],['right-panel','.hm-mission',355,'wh'],['right-head','.hm-mission .hm-drawer-head',356,'w'],['right-head-line','.hm-mission .hm-head-line',357,'wh'],['right-title','.hm-mission .hm-head-title strong',361],['right-badge','.hm-mission .hm-head-badge',362],['right-close','.hm-mission .hm-close',363,'wh'],
  ['right-headline','.hm-mission .hm-head-sub',366],['right-objective','.hm-mission .hm-head-limit:not(.hm-head-path)',367],['right-limits','.hm-mission .hm-head-path',367],
  ['progress','.hm-mission-progress',369,'w'],['progress-label','.hm-mission-progress .hm-label',370],['strip','.hm-step-strip',371,'wh'],['phase','.hm-phase',375],['phase-step','.hm-phase strong',376],['controls','.hm-controls',377],
  ['approvals','.hm-approvals:not(.hm-create-card)',387,'w'],['approvals-label','.hm-approvals:not(.hm-create-card) .hm-label',388],
  ['tabs-wrap','.hm-mission-tabs',415,'w'],['tabs','.hm-mission-tabs > .hm-tabs',416,'wh'],['tab-active','.hm-mission-tabs > .hm-tabs .active',418,'h'],['tab-body','.hm-mission-body',419],['plan-row','.hm-mission-body .hm-plan-row',422,'h'],['plan-no','.hm-mission-body .hm-plan-row strong',423],['plan-bee','.hm-mission-body .hm-plan-row small',425]];
const APPROVAL=[['approval','.hm-approval',390,'w'],['approval-title','.hm-approval-title',391],['approval-title-text','.hm-approval-title > span:not(.hm-state-icon):not(.hm-approval-badge)',394],['approval-badge','.hm-approval-badge',395],['approval-p','.hm-approval > p',396],['approval-actions','.hm-approval .hm-foot-actions',397],['approval-approve','.hm-approval .hm-foot-actions button:first-child',398,'h'],['approval-adjust','.hm-approval .hm-foot-actions button:nth-child(2)',399,'h'],
  ['approval-wait','.hm-approval-wait',381,'h']];
const ALERT=[['hud-alert','.hm-hud-alert',112,'h'],['hud-alert-strong','.hm-hud-alert strong',114],['hud-alert-btn','.hm-hud-alert button',115,'h']];
const FAIL=[['fail-card','.hm-approval',401,'w'],['fail-title','.hm-approval-title',402],['fail-title-text','.hm-approval-title > span:not(.hm-state-icon):not(.hm-approval-badge)',406],['fail-p','.hm-approval > p',408]];
const CHAT=[['chat','.hm-chat',125,'wh'],['chat-head','.hm-chat-head',126,'wh'],['chat-title','.hm-chat-head .hm-head-title strong',130],['chat-sub','.hm-chat-head .hm-head-sub',131],['chat-close','.hm-chat .hm-close',132,'wh'],['chat-log','.hm-chat-log',135,'w'],
  ['chat-form','.hm-chat-form',157,'w'],['chat-form-label','.hm-chat-form label > strong',158],['chat-line','.hm-chat-form label > div',159,'h'],['chat-input','.hm-chat-form input',160,'h']];
const SEND_OFF=['chat-send','.hm-chat-form button',161,'wh',{skip:['color']}]; // desabilitado enquanto a Rainha não aceita mensagem (cor de desabilitado); o habilitado vale no caso falha
const SEND_ON=['chat-send','.hm-chat-form button',161,'wh'];
const BUBBLES=[['chat-user','.hm-chat-user',141],['chat-user-label','.hm-chat-user strong',142],['chat-event','.hm-chat-event',144],['chat-event-name','.hm-chat-event strong',148]];
const TAB_TASKS=[['tarefas-body','.hm-tab-body',242],['tarefas-label','.hm-tab-body .hm-label',244],['tarefas-text','.hm-tab-body .hm-detail-group p',245]];
const TAB_SKILLS=[['skills-body','.hm-tab-body',258],['skills-label','.hm-tab-body .hm-label',259],['skills-tags','.hm-tags',261],['skills-tag','.hm-tags span',263]];
const TAB_TOOLS=[['tools-body','.hm-tab-body',269],['tools-label','.hm-tab-body .hm-label',270],['tools-list','.hm-tools',272],['tool-row','.hm-tools .hm-tool',274],['tool-icon','.hm-tools .hm-tool-icon',275,'wh'],['tool-access','.hm-tools .hm-tool-access',279]];
const TAB_REL=[['rel-body','.hm-tab-body',283],['rel-grid','.hm-rel-grid',285],['rel-from','.hm-rel-grid > button:first-child',286],['rel-from-label','.hm-rel-grid > button:first-child .hm-label',287],['rel-from-name','.hm-rel-grid > button:first-child strong',288],['rel-to','.hm-rel-grid > button:last-child',292],['rel-to-label','.hm-rel-grid > button:last-child .hm-label',293],['rel-to-name','.hm-rel-grid > button:last-child strong',294],
  ['conn-group','.hm-tab-body .hm-detail-group',313,'',{filter:'Conexões na colmeia'}],['conn-label','.hm-tab-body .hm-detail-group .hm-label',314,'',{filter:'Conexões na colmeia'}],['conn-list','.hm-tab-body .hm-connection-list',315],['conn-row','.hm-tab-body .hm-connection-row',317,'h'],['conn-name','.hm-tab-body .hm-connection-row strong',319],['conn-sub','.hm-tab-body .hm-connection-row small',320]];
const TAB_QUEEN=[['duty-group','.hm-tab-body .hm-detail-group',302,'',{filter:'Responsabilidades distribuídas'}],['duty-label','.hm-tab-body .hm-label',303,'',{filter:'Responsabilidades'}],['duty-list','.hm-duty-list',304],['duty','.hm-duty-list .hm-duty',306,'h'],['duty-copy','.hm-duty-list .hm-duty-copy',307],['duty-name','.hm-duty-list .hm-duty-name',308],['duty-text','.hm-duty-list .hm-duty-text',309],['duty-status','.hm-duty-list .hm-duty-status',310]];
const MISSION_RESP=[['mresp-row','.hm-mission-body .hm-duty',428,'h'],['mresp-copy','.hm-mission-body .hm-duty-copy',429],['mresp-name','.hm-mission-body .hm-duty-name',430],['mresp-text','.hm-mission-body .hm-duty-text',431],['mresp-status','.hm-mission-body .hm-duty-status',432]];
const MISSION_CONEX=[['mconex-intro','.hm-connections-intro',435],['mconex-legend','.hm-connection-legend',436],['mconex-legend-row','.hm-legend-row',438,'h'],['mconex-legend-text','.hm-legend-row > span',439],['mconex-current','.hm-connections-current',441],['mconex-list','.hm-mission-body .hm-connection-list',442],['mconex-row','.hm-mission-body .hm-connection-row',444,'h'],['mconex-name','.hm-mission-body .hm-connection-row strong',446],['mconex-sub','.hm-mission-body .hm-connection-row small',447]];
const MISSION_DELIVERY=[['mentrega-title','.hm-mission-body h3',450],['mentrega-stats','.hm-mission-body .hm-delivery-stats',452,'w'],['mentrega-card','.hm-mission-body .hm-delivery-stats > div:first-child',453,'h'],['mentrega-n','.hm-mission-body .hm-delivery-stats > div:first-child strong',454],['mentrega-t','.hm-mission-body .hm-delivery-stats > div:first-child span',455],['mentrega-dark','.hm-mission-body .hm-delivery-stats .dark',459,'h'],['mentrega-btn','.hm-mission-body .hm-foot-actions button',462,'h']];
const POPUP=[['delivery','.hm-delivery',466,'wh'],['delivery-dialog','.hm-delivery-dialog',467,'w'],['dl-top','.hm-delivery-top',468,'wh'],['dl-label','.hm-delivery-top .hm-label',469],['dl-close','.hm-delivery-top button',470,'wh'],['dl-title','.hm-delivery-title',471],['dl-p','.hm-delivery-dialog > p',472],['dl-stats','.hm-delivery-stats',473,'wh'],['dl-card','.hm-delivery-stats > div:first-child',474,'wh'],['dl-card-n','.hm-delivery-stats > div:first-child strong',475],['dl-card-t','.hm-delivery-stats > div:first-child span',476],['dl-dark','.hm-delivery-stats .dark',480,'wh'],['dl-table','.hm-delivery-table',483,'w'],['dl-header','.hm-delivery-row.header',484,'wh'],['dl-row','.hm-delivery-row:not(.header)',490],['dl-note','.hm-delivery-note',497]];
const WORLD_POPUP=[['wpop','.hm-world-popup',85,'wp'],['wpop-head','.hm-world-popup-head',86,'wh'],['wpop-label','.hm-world-popup-head > span',87],['wpop-close','.hm-world-popup-head button',88,'wh'],['wpop-title','.hm-world-popup-title',91],['wpop-state','.hm-world-popup-state',93,'',{only:FONT_KEYS}],['wpop-copy','.hm-world-popup-copy',94],['wpop-desc','.hm-world-popup-description',95]];
// recortes por pixel: [nome, seletor real, id do protótipo]
const PIXEL_CASES=[
  {name:'execucao',scenario:'running',proto:{phase:'p2b',selected:'documentos'},agent:'bee-documentos',bottom:true,pairs:[...HUD,['hud-action','.hm-hud-action',105,'hy'],...PULLS,...CELLS,...LEFT,...DETAIL,...RIGHT,...CHAT,SEND_OFF],crops:[]},
  {name:'aprovacao',scenario:'awaiting_delivery_approval',proto:{phase:'approval',log:LOG},agent:null,bottom:true,pairs:[...HUD,...STEPS([['done',0,0],['current',4,4],['future',6,6]]),...SEGMENTS,...ALERT,...APPROVAL,...PULLS,...LEFT,...RIGHT.filter(pair=>!['approvals','approvals-label'].includes(pair[0])),['approvals','.hm-approvals:not(.hm-create-card)',387,'w'],['approvals-label','.hm-approvals:not(.hm-create-card) .hm-label',388]],
    crops:[['pull-left','.hm-pull-left',163],['pull-right','.hm-pull-right',350]],world:true},
  {name:'falha',scenario:'awaiting_user',proto:{phase:'fail',log:LOG},agent:null,bottom:true,pairs:[...ALERT,...FAIL,...CHAT,SEND_ON,...BUBBLES],crops:[]},
  {name:'entrega',scenario:'completed',proto:{phase:'done',delivery:true},agent:null,bottom:true,delivery:true,pairs:[...POPUP,...STEPS([['done',0,0],['all',6,6]])],crops:[]},
  // abas do detalhe do agente e da Missão (ficam por último: a aba escolhida persiste na tela real)
  {name:'aba-tarefas',scenario:'running',proto:{phase:'p2b',selected:'documentos',agentTab:'tarefas'},agent:'bee-documentos',agentTab:'Tarefas',pairs:TAB_TASKS,crops:[]},
  {name:'aba-skills',scenario:'running',proto:{phase:'p2b',selected:'documentos',agentTab:'skills'},agent:'bee-documentos',agentTab:'Skills',pairs:TAB_SKILLS,crops:[]},
  {name:'aba-ferramentas',scenario:'running',proto:{phase:'p2b',selected:'documentos',agentTab:'ferramentas'},agent:'bee-documentos',agentTab:'Ferramentas',pairs:TAB_TOOLS,crops:[]},
  {name:'aba-relacoes',scenario:'running',proto:{phase:'p2b',selected:'documentos',agentTab:'relacoes'},agent:'bee-documentos',agentTab:'Relações',pairs:TAB_REL,crops:[]},
  {name:'aba-rainha',scenario:'running',proto:{phase:'p2b',selected:'rainha',agentTab:'relacoes'},agent:'rainha',agentTab:'Relações',pairs:TAB_QUEEN,crops:[]},
  {name:'missao-resp',scenario:'running',proto:{phase:'p2b',missionTab:'resp'},agent:null,missionTab:'Responsabilidades',pairs:MISSION_RESP,crops:[]},
  {name:'missao-conex',scenario:'running',proto:{phase:'p2b',missionTab:'conex'},agent:null,missionTab:'Conexões',pairs:MISSION_CONEX,crops:[]},
  {name:'missao-entrega',scenario:'completed',proto:{phase:'done',missionTab:'entrega'},agent:null,missionTab:'Entrega',pairs:MISSION_DELIVERY,crops:[]},
  {name:'conexao',scenario:'running',proto:{phase:'p2b',link:'doc-ana'},agent:null,bottom:true,link:'q-bee-documentos',pairs:WORLD_POPUP,crops:[]},
];
// Diferenças do modo real já conhecidas e aceitas, sempre com o motivo. Qualquer outra derruba o teste.
const KNOWN=[];
const sameValue=(a,b)=>{
  const clean=value=>String(value).replaceAll('"','').replaceAll("'",'').replace(/\s+/g,' ').trim();
  a=clean(a);b=clean(b);if(a===b)return true;
  const number=/-?\d*\.?\d+/g,x=a.match(number),y=b.match(number);
  return !!x&&!!y&&x.length===y.length&&a.replace(number,'#')===b.replace(number,'#')&&x.every((value,index)=>Math.abs(value-y[index])<=0.51);
};
// Roda dentro de cada página: devolve estilo e retângulo de cada item (ou null se ausente/invisível).
const measureItems=({items,keys,realRoot})=>{
  const norm=node=>node.textContent.replace(/\s+/g,' ').trim(),visible=node=>node.getClientRects().length>0;
  // Compare o conteúdo da definição, não o identificador exclusivo de cada instância.
  const paint=value=>value.replace(/url\(["']?#([^"')]+)["']?\)/g,(match,id)=>{
    const definition=document.getElementById(id);if(!definition)return `missing-paint(${id})`;
    const serialize=node=>[node.localName,[...node.attributes].filter(attr=>attr.name!=='id').map(attr=>[attr.name,attr.value]).sort(([a],[b])=>a.localeCompare(b)),[...node.children].map(serialize)];
    return `paint(${JSON.stringify(serialize(definition))})`;
  });
  const screen=document.querySelector('[data-screen-label="Hive Mind"]');
  return items.map(item=>{
    let node;
    if(item.tpl!==undefined){node=[...screen.querySelectorAll(`[data-dc-tpl="${item.tpl}"]`)].filter(visible)[item.pidx||0];if(node&&item.pchild)node=node.querySelectorAll(item.pchild)[item.pchildIdx||0];}
    else{node=[...document.querySelectorAll(`${realRoot} ${item.css}`)].filter(candidate=>visible(candidate)&&(!item.filter||norm(candidate).startsWith(item.filter)))[item.ridx||0];if(node&&item.child)node=node.querySelector(item.child);}
    if(!node)return {name:item.name,missing:true};
    const style=getComputedStyle(node),rect=node.getBoundingClientRect(),sig={},own=!!node.textContent.trim()&&[...node.children].every(child=>['svg','img'].includes(child.tagName.toLowerCase())||getComputedStyle(child).display==='inline'); // tem texto próprio (o protótipo envolve o texto em span inline)
    keys.concat(['fill','stroke','stroke-width']).forEach(key=>{sig[key]=key==='fill'?paint(style.getPropertyValue(key)):style.getPropertyValue(key);});
    ['top','right','bottom','left'].forEach(side=>{const width=style.getPropertyValue(`border-${side}-width`),kind=style.getPropertyValue(`border-${side}-style`);sig[`border-${side}`]=kind==='none'||parseFloat(width)===0?'none':`${width} ${kind} ${style.getPropertyValue(`border-${side}-color`)}`;});
    return {name:item.name,sig,own,rect:{x:rect.x,y:rect.y,w:rect.width,h:rect.height}};
  });
};
async function compareReal({context,runtime,reference,errors,report}){
  const real=await context.newPage();
  real.on('pageerror',error=>errors.push('real: '+(error.stack||error.message)));
  real.on('console',message=>{if(message.type()==='error'&&!/404|fonts\.g/.test(message.text()))errors.push('real console: '+message.text());});
  await real.addInitScript(()=>{localStorage.setItem('core.minimal',JSON.stringify({on:true,l:false,r:false}));localStorage.setItem('core.assistant','claude');localStorage.setItem('core.page','hive');sessionStorage.setItem('hivemind-mission','m1');});
  await real.setViewportSize({width:1440,height:900});await reference.setViewportSize({width:1440,height:900});
  await real.goto(base+'/',{waitUntil:'domcontentloaded'});await real.locator('#hmPage').waitFor({state:'visible'});await real.evaluate(()=>document.fonts.ready);
  await real.locator('.hm-reduced').click();
  await real.addStyleTag({content:FREEZE});await reference.addStyleTag({content:FREEZE});
  const setProto=async config=>{
    const result=await reference.evaluate(async config=>{
      const screen=document.querySelector('[data-screen-label="Hive Mind"]');let component=null;
      for(const node of [screen,...screen.querySelectorAll('*')]){const key=Object.keys(node).find(name=>name.startsWith('__reactFiber$'));let fiber=key?node[key]:null;while(fiber){const logic=fiber.stateNode?.logic||fiber.stateNode;if(logic&&typeof logic.go==='function'){component=logic;break;}fiber=fiber.return;}if(component)break;}
      if(!component)return false;
      await new Promise(resolve=>component.go(config.phase,{running:false,showDelivery:false,log:[]})||setTimeout(resolve,0));if(component.dt)clearTimeout(component.dt);
      await new Promise(resolve=>component.setState({adjusted:false,reduced:true,showSubs:false,sel:config.selected||null,link:config.link||null,form:false,running:false,showDelivery:!!config.delivery,log:config.log||[],agentTab:config.agentTab||'geral',missionTab:config.missionTab||'plano',lo:true,ro:true,bo:true},resolve));return true;
    },config);
    if(!result)throw new Error('Componente React do protótipo não encontrado');
  };
  const setDemo=async config=>runtime.evaluate(config=>{const sim=window.hiveMindDemo.simulation;sim.go(config.phase,{running:false,delivery:false,log:[]});sim.freezeClock();Object.assign(sim.state,{adjusted:false,log:config.log||[],showSubs:false,selected:config.selected||null,selectedLink:config.link||null,form:false,running:false,delivery:!!config.delivery,agentTab:config.agentTab||'geral',missionTab:config.missionTab||'plano',drawers:{left:true,right:true,bottom:true}});sim.emit();},config);
  await runtime.addStyleTag({content:FREEZE});
  const failures=[],summary=[];
  const inherited=[];
  // Falha só o que difere do protótipo E da demonstração (a demonstração foi aprovada no ciclo 7 contra o protótipo):
  // diferença igual à da demonstração é herdada e fica registrada em metrics.json, não derruba o teste.
  const compare=(label,pairs,realMeasured,protoMeasured,demoMeasured)=>{
    let compared=0;
    pairs.forEach((pair,index)=>{
      const [name,,,flags='',options={}]=pair,a=realMeasured[index],b=protoMeasured[index],c=demoMeasured[index];
      if(a.missing||b.missing){failures.push(`[${label}] ${name}: ausente ${a.missing?'no modo real':''}${a.missing&&b.missing?' e ':''}${b.missing?'no protótipo':''}`);return;}
      compared++;
      const textual=a.own&&b.own,keys=options.only||[...STYLE_KEYS,'border-top','border-right','border-bottom','border-left'].filter(key=>!(options.skip||[]).includes(key)&&(textual||!TEXT_KEYS.includes(key)));
      const judge=(key,realValue,protoValue,demoValue)=>{
        if(sameValue(realValue,protoValue))return;
        const text=`[${label}] ${name}: ${key} real=${realValue} | protótipo=${protoValue} | demonstração=${demoValue??'—'}`;
        if(demoValue!==undefined&&sameValue(realValue,demoValue))inherited.push(text);else failures.push(text);
      };
      keys.forEach(key=>judge(key,a.sig[key],b.sig[key],c&&!c.missing?c.sig[key]:undefined));
      const dims=[];if(flags.includes('w'))dims.push('w');if(flags.includes('h'))dims.push('h');if(flags.includes('p'))dims.push('x','y');if(flags.includes('y')&&!flags.includes('p'))dims.push('y');
      dims.forEach(key=>{
        if(Math.abs(a.rect[key]-b.rect[key])<=1.01)return;
        const text=`[${label}] ${name}: ${key} real=${a.rect[key].toFixed(2)} | protótipo=${b.rect[key].toFixed(2)} | demonstração=${c&&!c.missing?c.rect[key].toFixed(2):'—'}`;
        if(c&&!c.missing&&Math.abs(a.rect[key]-c.rect[key])<=1.01)inherited.push(text);else failures.push(text);
      });
    });
    return compared;
  };
  const crop=async(locator)=>sharp(await locator.first().screenshot()).ensureAlpha().raw().toBuffer({resolveWithObject:true});
  // Devolve a taxa de pixels diferentes (> 32 em algum canal) entre dois recortes, ou o par de tamanhos se não couberem.
  const pixelRatio=async(realLocator,protoLocator,save)=>{
    const [a,b]=await Promise.all([crop(realLocator),crop(protoLocator)]);
    if(a.info.width!==b.info.width||a.info.height!==b.info.height)return {size:`${a.info.width}x${a.info.height} | protótipo=${b.info.width}x${b.info.height}`,own:`${a.info.width}x${a.info.height}`};
    if(save){await mkdir(join(statesDir,'recortes'),{recursive:true});for(const [side,item] of [['real',a],['reference',b]])await sharp(item.data,{raw:{width:item.info.width,height:item.info.height,channels:4}}).png().toFile(join(statesDir,'recortes',`${save}-${side}.png`));}
    let different=0;for(let index=0;index<a.data.length;index+=4)if(Math.max(Math.abs(a.data[index]-b.data[index]),Math.abs(a.data[index+1]-b.data[index+1]),Math.abs(a.data[index+2]-b.data[index+2]))>32)different++;
    return {ratio:different/(a.info.width*a.info.height)};
  };
  const statesDir=join(output,'real');await mkdir(statesDir,{recursive:true});
  for(const config of PIXEL_CASES){
    hive.scenario=config.scenario;const wanted=hive.fixture.scenarios[config.scenario].mission.state;
    await real.waitForFunction(state=>window.hiveMindLive.getState().mission?.state===state&&!window.hiveMindLive.getState().error,wanted,{timeout:8000});
    await real.evaluate(async()=>{await document.fonts.ready;});
    // estado da tela real: gavetas abertas, agente selecionado, conexão, popup
    const state=await real.evaluate(()=>window.hiveMindLive.getState());
    if(state.selected!==config.agent){
      if(state.selected&&!config.agent)await real.locator(`.hm-live-workspace .hm-agent-row[data-id="${state.selected}"]`).click();
      else if(config.agent)await real.locator(`.hm-live-workspace .hm-agent-row[data-id="${config.agent}"]`).click();
    }
    for(const side of ['left','right','bottom'])if(!(await real.evaluate(side=>window.hiveMindLive.getState().drawers[side],side)))await real.locator(`.hm-live-workspace .hm-pull-${side}`).click();
    if((await real.evaluate(()=>window.hiveMindLive.getState().selectedLink))!==(config.link||null)){
      await real.evaluate(link=>{const current=window.hiveMindLive.getState().selectedLink;const hit=id=>document.querySelector(`.hm-live-workspace [data-link="${id}"] .hm-route-hit`)?.dispatchEvent(new MouseEvent('click',{bubbles:true}));if(current)hit(current);if(link)hit(link);},config.link||null);
    }
    if(config.agentTab)await real.locator('.hm-live-workspace .hm-agent-detail .hm-tabs button',{hasText:config.agentTab}).first().click();
    if(config.missionTab)await real.locator('.hm-live-workspace .hm-mission-tabs > .hm-tabs button',{hasText:config.missionTab}).first().click();
    if(config.delivery){await real.locator('.hm-live-workspace .hm-hud-action').click();}
    else if(await real.locator('.hm-live-workspace .hm-delivery:not([hidden])').count())await real.keyboard.press('Escape');
    await setProto(config.proto);
    await real.waitForTimeout(450);await reference.waitForTimeout(450);
    if(config.name==='execucao'){
      const duplicates=await real.evaluate(()=>{const counts=new Map();document.querySelectorAll('svg [id]').forEach(node=>counts.set(node.id,(counts.get(node.id)||0)+1));return [...counts].filter(([,count])=>count>1);});
      if(duplicates.length)failures.push(`[execucao] IDs SVG duplicados: ${JSON.stringify(duplicates)}`);
      const demoHidden=await real.locator('.hm-demo-workspace').evaluate(node=>getComputedStyle(node).display==='none'||!node.getClientRects().length);
      if(!demoHidden)failures.push('[execucao] demonstração deveria estar oculta durante a prova de pintura');
      // Amostras no interior lateral dos hexágonos, longe do texto e da abelha.
      const painted=async(selector,kind)=>{
        const image=await crop(real.locator(selector));const {width,height}=image.info;
        const samples=[[.16,.45],[.84,.45],[.16,.55],[.84,.55]].map(([x,y])=>{const i=(Math.floor(height*y)*width+Math.floor(width*x))*4;return [...image.data.subarray(i,i+3)];});
        const valid=samples.filter(rgb=>kind==='queen'?rgb.every(channel=>channel<80):rgb.every(channel=>channel>190));
        if(valid.length<2)failures.push(`[execucao] pintura ${kind} ausente: ${JSON.stringify(samples)}`);
        return samples;
      };
      report.paint={demoHidden,duplicates,queen:await painted('.hm-live-workspace .hm-cell-queen .hm-cell-visual','queen'),selected:await painted('.hm-live-workspace .hm-cell[data-agent="bee-documentos"] .hm-cell-visual','selected')};
    }
    const real_state=await real.evaluate(()=>window.hiveMindLive.getState());
    if(real_state.error)failures.push(`[${config.name}] a tela real mostra erro: ${real_state.error}`);
    const items=config.pairs.map(([name,css,tpl,,options={}])=>({name,css,tpl,...options}));
    const realMeasured=await real.evaluate(measureItems,{items:items.map(({tpl,pidx,...rest})=>rest),keys:STYLE_KEYS,realRoot:'.hm-live-workspace'});
    const protoMeasured=await reference.evaluate(measureItems,{items:items.map(({name,tpl,pidx})=>({name,tpl,pidx})),keys:STYLE_KEYS,realRoot:''});
    const crops=[];
    await setDemo(config.proto);await runtime.waitForTimeout(250);
    const demoMeasured=await runtime.evaluate(measureItems,{items:items.map(({tpl,pidx,...rest})=>({...rest,css:rest.css.replaceAll('bee-documentos','documentos')})),keys:STYLE_KEYS,realRoot:'.hm-demo-workspace'});
    const compared=compare(config.name,config.pairs,realMeasured,protoMeasured,demoMeasured);
    for(const [name,css,tpl] of config.crops){
      const protoLocator=reference.locator(`[data-dc-tpl="${tpl}"]`),own=await pixelRatio(real.locator(`.hm-live-workspace ${css}`),protoLocator,`${config.name}-${name}`),demo=await pixelRatio(runtime.locator(`.hm-demo-workspace ${css}`),protoLocator);
      const text=`[${config.name}] recorte ${name}: `;
      if(own.size){const message=`${text}tamanho real=${own.size} | demonstração=${demo.own}`;if(demo.own===own.own)inherited.push(message);else failures.push(message);}
      else if(own.ratio>0.005){const message=`${text}${(own.ratio*100).toFixed(2)} % dos pixels diferem do protótipo (demonstração ${demo.ratio===undefined?'—':(demo.ratio*100).toFixed(2)+' %'}; limite 0,5 %)`;if(demo.ratio!==undefined&&own.ratio<=demo.ratio+0.005)inherited.push(message);else failures.push(message);}
      crops.push({name,ratio:own.ratio??null,demo:demo.ratio??null});
    }
    await real.screenshot({path:join(statesDir,`real-${config.name}-1440x900.png`)});await reference.screenshot({path:join(statesDir,`reference-${config.name}-1440x900.png`)});
    let world=null;
    if(config.world){
      // região do mapa (entre as gavetas, abaixo do cabeçalho), com o rig PNG das abelhas mascarado nos dois lados
      const area={x:392,y:52,width:656,height:548},rects=(page,selector)=>page.evaluate(selector=>[...document.querySelectorAll(selector)].map(node=>{const r=node.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height};}),selector);
      const protoMask=await rects(reference,'[data-dc-tpl="49"] > svg,[data-dc-tpl="74"] > svg'),shot=async page=>sharp(await page.screenshot({clip:area})).ensureAlpha().raw().toBuffer(),b=await shot(reference);
      const ratioOf=async(page,beeSelector)=>{
        const mask=[...protoMask,...await rects(page,beeSelector)],a=await shot(page);let different=0,counted=0;
        for(let y=0;y<area.height;y++)for(let x=0;x<area.width;x++){
          const px=x+area.x,py=y+area.y;if(mask.some(r=>px>=r.x-2&&px<=r.x+r.w+2&&py>=r.y-2&&py<=r.y+r.h+2))continue;
          const index=(y*area.width+x)*4;counted++;if(Math.max(Math.abs(a[index]-b[index]),Math.abs(a[index+1]-b[index+1]),Math.abs(a[index+2]-b[index+2]))>32)different++;
        }
        return different/counted;
      };
      world={real:await ratioOf(real,'.hm-live-workspace .hm-bee-asset'),demo:await ratioOf(runtime,'.hm-demo-workspace .hm-bee-asset')};
      // só informativo (sem limite): o mapa real fica 20,6 px abaixo do protótipo (showSubs fixo, ver KNOWN), o que desloca rotas e bordas
    }
    summary.push({case:config.name,scenario:config.scenario,pairs:config.pairs.length,compared,crops,world});
  }
  const known=failures.filter(text=>KNOWN.some(([prefixes])=>prefixes.some(prefix=>text.startsWith(prefix)))).map(text=>({text,reason:KNOWN.find(([prefixes])=>prefixes.some(prefix=>text.startsWith(prefix)))[1]})),blocking=failures.filter(text=>!KNOWN.some(([prefixes])=>prefixes.some(prefix=>text.startsWith(prefix))));
  report.real={cases:summary,failures:blocking,known,inherited};
  return blocking;
}
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));const base=`http://127.0.0.1:${server.address().port}`;
const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'}),context=await browser.newContext({viewport:{width:1440,height:900},deviceScaleFactor:1}),errors=[];
try{
  const runtime=await context.newPage();runtime.on('pageerror',error=>errors.push('runtime: '+error.message));await runtime.addInitScript(()=>{localStorage.setItem('core.minimal',JSON.stringify({on:true,l:false,r:false}));localStorage.setItem('core.assistant','claude');localStorage.setItem('core.page','hive');});await runtime.goto(base+'/',{waitUntil:'domcontentloaded'});await runtime.locator('#hmPage').waitFor({state:'visible'});await runtime.locator('.hm-mode').click();await runtime.evaluate(()=>{window.hiveMindDemo.simulation.setScenario('mission');window.hiveMindDemo.simulation.go('idle');window.hiveMindDemo.simulation.setReduced(true);});
  const reference=await context.newPage();reference.on('pageerror',error=>errors.push('reference: '+(error.stack||error.message)));const reactRoot=join(root,'.test-tmp','hivemind-bees'),[react,reactDom,support]=await Promise.all([readFile(join(reactRoot,'react.js'),'utf8'),readFile(join(reactRoot,'react-dom.js'),'utf8'),readFile(join(root,'HiveMind','prototipo','support.js'),'utf8')]);await reference.goto(base+'/prototype/Hive%20Mind.dc.html',{waitUntil:'load'});await reference.addScriptTag({content:react+'\n'+reactDom+'\n'+support});await reference.waitForFunction(()=>document.querySelector('[data-screen-label="Hive Mind"]')?.textContent.includes('Operação de pedidos'));await Promise.all([runtime.evaluate(()=>document.fonts.ready),reference.evaluate(()=>document.fonts.ready)]);
  await reference.getByRole('switch').click();
  await runtime.locator('[data-action="toggle-left"]').click();await runtime.locator('[data-action="pick-agent"][data-id="documentos"]').click();await runtime.locator('[data-action="toggle-right"]').click();await runtime.locator('[data-action="toggle-bottom"]').click();
  await reference.getByRole('button',{name:/Agentes\s*6/}).click();await reference.getByRole('button',{name:/Documentos/}).first().click();await reference.getByRole('button',{name:/Missão\s*0\/7/}).click();await reference.getByRole('button',{name:/Conversa com a Rainha/}).first().click();
  const nativeMetrics=()=>{const box=element=>{const r=element.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height};};return {fonts:document.fonts.status,header:box(document.querySelector('.hm-header')),world:box(document.querySelector('.hm-world')),queen:box(document.querySelector('[data-agent="rainha"]')),left:box(document.querySelector('.hm-side-left')),right:box(document.querySelector('.hm-side-right')),bottom:box(document.querySelector('.hm-bottom')),hud:box(document.querySelector('.hm-hud-main')),worldStyle:{left:getComputedStyle(document.querySelector('.hm-world')).left,top:getComputedStyle(document.querySelector('.hm-world')).top,transform:getComputedStyle(document.querySelector('.hm-world')).transform},fontBody:getComputedStyle(document.querySelector('#hmPage')).fontFamily,fontHeading:getComputedStyle(document.querySelector('.hm-head-title strong')).fontFamily};};
  const referenceMetrics=()=>{const screen=document.querySelector('[data-screen-label="Hive Mind"]'),workspace=screen.children[1],all=[...workspace.querySelectorAll('div')],box=element=>{if(!element)return null;const r=element.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height};},world=workspace.children[0],positioned=all.filter(element=>getComputedStyle(element).position==='absolute'),left=positioned.find(element=>{const r=element.getBoundingClientRect();return Math.abs(r.width-392)<.1&&Math.abs(r.x)<.1;}),right=positioned.find(element=>{const r=element.getBoundingClientRect();return Math.abs(r.width-392)<.1&&Math.abs(r.right-innerWidth)<.1;}),bottom=positioned.find(element=>{const r=element.getBoundingClientRect();return Math.abs(r.height-300)<.1&&Math.abs(r.bottom-innerHeight)<.1;}),queen=positioned.find(element=>{const style=getComputedStyle(element);return Math.abs(parseFloat(style.width)-124.71)<.2&&Math.abs(parseFloat(style.height)-144)<.2&&element.textContent.includes('Rainha');}),hud=all.find(element=>{const r=element.getBoundingClientRect();return Math.abs(r.height-44)<.1&&element.textContent.toLowerCase().includes('missão simulada');});return {fonts:document.fonts.status,header:box(screen.children[0]),world:box(world),queen:box(queen),left:box(left),right:box(right),bottom:box(bottom),hud:box(hud),worldStyle:{left:getComputedStyle(world).left,top:getComputedStyle(world).top,transform:getComputedStyle(world).transform},fontBody:getComputedStyle(screen).fontFamily,fontHeading:left?getComputedStyle(left).fontFamily:''};};
  const nativeDetails=()=>{const box=element=>{if(!element)return null;const r=element.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height};},pick=selector=>box(document.querySelector(selector));return {project:pick('.hm-project'),scenarios:pick('.hm-scenarios'),reduced:pick('.hm-reduced'),demo:pick('.hm-demo-notice'),progress:pick('.hm-mission-progress'),steps:pick('.hm-step-strip'),phase:pick('.hm-phase'),controls:pick('.hm-controls'),approvals:pick('.hm-approvals'),approvalIdle:pick('.hm-approval-idle'),missionTabs:pick('.hm-mission-tabs>.hm-tabs'),planRow:pick('.hm-plan-row'),chatHead:pick('.hm-chat-head'),chatLog:pick('.hm-chat-log'),chatForm:pick('.hm-chat-form')};};
  const referenceDetails=()=>{const screen=document.querySelector('[data-screen-label="Hive Mind"]'),nodes=[...screen.querySelectorAll('*')],norm=node=>node.textContent.replace(/\s+/g,' ').trim(),leaf=text=>nodes.find(node=>!node.children.length&&norm(node)===text),box=element=>{if(!element)return null;const r=element.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height};},andamento=leaf('Andamento'),approval=leaf('Aprovações'),plan=leaf('Plano'),planRow=leaf('Receber e planejar')?.parentElement,chatEmpty=leaf('Nenhuma mensagem ainda. Escreva um pedido abaixo ou use “Simular missão”.'),formLabel=leaf('O que você quer que sua colmeia faça?'),project=leaf('Projeto'),example=leaf('Exemplo'),reduced=leaf('Reduzir movimento'),demo=leaf('DEMONSTRAÇÃO');return {project:box(project?.parentElement),scenarios:box(example?.parentElement),reduced:box(reduced?.parentElement),demo:box(demo),progress:box(andamento?.parentElement),steps:box(andamento?.nextElementSibling),phase:box(andamento?.nextElementSibling?.nextElementSibling),controls:box(andamento?.parentElement?.lastElementChild),approvals:box(approval?.parentElement),approvalIdle:box(approval?.parentElement?.lastElementChild),missionTabs:box(plan?.parentElement),planRow:box(planRow),chatHead:box(chatEmpty?.parentElement?.previousElementSibling),chatLog:box(chatEmpty?.parentElement),chatForm:box(formLabel?.closest('form'))};};
  const report={dpr:await runtime.evaluate(()=>devicePixelRatio),viewports:[]};
  for(const viewport of [{width:1280,height:800},{width:1440,height:900},{width:1920,height:1080}]){await runtime.setViewportSize(viewport);await reference.setViewportSize(viewport);await runtime.waitForTimeout(450);await reference.waitForTimeout(450);const native=await runtime.evaluate(nativeMetrics),source=await reference.evaluate(referenceMetrics),nativeDetailsValue=await runtime.evaluate(nativeDetails),sourceDetailsValue=await reference.evaluate(referenceDetails);for(const key of ['header','queen','left','right','bottom','hud']){if(!native[key]||!source[key])throw new Error(`${viewport.width} missing metric ${key}: ${JSON.stringify({native,source})}`);for(const dimension of ['x','y','w','h'])if(Math.abs(native[key][dimension]-source[key][dimension])>1.01)throw new Error(`${viewport.width} ${key}.${dimension}: native=${native[key][dimension]} source=${source[key][dimension]}`);}if(native.fonts!=='loaded'||source.fonts!=='loaded')throw new Error('Fonts not ready');await runtime.screenshot({path:join(output,`native-${viewport.width}x${viewport.height}-idle-drawers.png`)});await reference.screenshot({path:join(output,`reference-${viewport.width}x${viewport.height}-idle-drawers.png`)});report.viewports.push({viewport,native,source,nativeDetails:nativeDetailsValue,sourceDetails:sourceDetailsValue});}
  const statesDir=join(output,'states');await mkdir(statesDir,{recursive:true});await runtime.setViewportSize({width:1440,height:900});await reference.setViewportSize({width:1440,height:900});
  const setReferenceState=async config=>{const ok=await reference.evaluate(async config=>{const screen=document.querySelector('[data-screen-label="Hive Mind"]'),candidates=[screen,...screen.querySelectorAll('*')];let component=null;for(const node of candidates){const key=Object.keys(node).find(name=>name.startsWith('__reactFiber$'));let fiber=key?node[key]:null;while(fiber){const logic=fiber.stateNode?.logic||fiber.stateNode;if(logic&&typeof logic.go==='function'){component=logic;break;}fiber=fiber.return;}if(component)break;}if(!component)return false;await new Promise(resolve=>component.go(config.phase,{running:false,showDelivery:false,log:[]})||setTimeout(resolve,0));if(component.dt)clearTimeout(component.dt);await new Promise(resolve=>component.setState({adjusted:false,reduced:true,showSubs:!!config.showSubs,sel:config.selected||null,link:config.link||null,form:!!config.form,running:false,showDelivery:false,log:[],lo:true,ro:true,bo:true},resolve));return true;},config);if(!ok)throw new Error('Prototype React component not found for paired state setup');};
  const setRuntimeState=async config=>runtime.evaluate(config=>{const sim=window.hiveMindDemo.simulation;sim.go(config.phase,{running:false,delivery:false,log:[]});sim.freezeClock();Object.assign(sim.state,{adjusted:false,log:[],showSubs:!!config.showSubs,selected:config.selected||null,selectedLink:config.link||null,form:!!config.form,running:false,delivery:false,drawers:{left:true,right:true,bottom:true}});sim.emit();},config);
  const createDiffs=async(name,nativePath,referencePath)=>{const regions={header:{left:0,top:0,width:1440,height:52},left:{left:0,top:52,width:392,height:848},world:{left:392,top:52,width:656,height:548},right:{left:1048,top:52,width:392,height:848},bottom:{left:392,top:600,width:656,height:300}};const nativeBuffer=await readFile(nativePath);await sharp(referencePath).composite([{input:nativeBuffer,blend:'difference'}]).png().toFile(join(statesDir,`diff-${name}-full.png`));for(const [region,area] of Object.entries(regions)){const refCrop=await sharp(referencePath).extract(area).png().toBuffer(),nativeCrop=await sharp(nativePath).extract(area).png().toBuffer();await sharp(refCrop).composite([{input:nativeCrop,blend:'difference'}]).png().toFile(join(statesDir,`diff-${name}-${region}.png`));}};
  const statePairs=[
    {name:'p2b-subagent',phase:'p2b',showSubs:true,selected:'sub-anexos'},
    {name:'approval',phase:'approval'},
    {name:'failure',phase:'fail'},
    {name:'done',phase:'done'},
    {name:'selected-link',phase:'p2b',showSubs:true,link:'doc-s1'},
    {name:'worker-form',phase:'idle',form:true},
  ];
  report.states=[];for(const config of statePairs){await setReferenceState(config);await setRuntimeState(config);await runtime.waitForTimeout(150);await reference.waitForTimeout(150);if(config.name==='p2b-subagent'){const value=await runtime.locator('[data-link="doc-s1"]').getAttribute('data-state');if(value!=='out')throw new Error(`Subagent route direction mismatch: ${value}`);}if(config.name==='selected-link'&&!await runtime.locator('.hm-world-popup:not([hidden]) [aria-label="Fechar detalhes da conexão"]').count())throw new Error('Selected-link popup CTA missing');const nativePath=join(statesDir,`native-${config.name}-1440x900.png`),referencePath=join(statesDir,`reference-${config.name}-1440x900.png`);await runtime.screenshot({path:nativePath});await reference.screenshot({path:referencePath});await createDiffs(config.name,nativePath,referencePath);report.states.push({name:config.name,native:nativePath,reference:referencePath});}
  const realFailures=await compareReal({context,runtime,reference,errors,report});
  await writeFile(join(output,'metrics.json'),JSON.stringify({...report,errors},null,2));
  if(errors.length)throw new Error(errors.join(' | '));
  if(realFailures.length)throw new Error(`Modo real x protótipo: ${realFailures.length} diferença(s)\n`+realFailures.join('\n'));
  console.log(JSON.stringify({ok:true,dpr:report.dpr,idlePairs:report.viewports.length,statePairs:report.states.length,real:report.real.cases.map(item=>({case:item.case,compared:item.compared,crops:item.crops.length,world:item.world&&{real:item.world.real,demo:item.world.demo}})),output}));
}finally{await context.close();await browser.close();await new Promise(resolve=>server.close(resolve));}
