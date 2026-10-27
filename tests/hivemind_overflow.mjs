// Teste de estouro do modo real do Hive Mind (V08): nenhuma gaveta, HUD ou popup pode ter conteúdo maior que a caixa.
//
// Como rodar (a partir da raiz do projeto; não há package.json nem node_modules no repositório):
//   $env:NODE_PATH = "<pasta com node_modules que tenha o playwright>"          # PowerShell
//   node tests/hivemind_overflow.mjs [pasta-de-saída]
// Nesta máquina: NODE_PATH="C:/Users/m.rafael/Desktop/projetos/CRM Clean Environment Brasil/frontend/node_modules"
// Pré-requisito: Chrome em C:/Program Files/Google/Chrome/Application/chrome.exe. Não usa o protótipo nem o `sharp`.
// Não toca a porta 8765: sobe o próprio servidor e responde `/hive-api` com tests/fixtures/hivemind_real_longo.json
// (textos longos e sem espaço em descrição, tarefas, caminho, objetivo, veredito e arquivos fora do plano).
//
// O que roda: 6 estados da missão (execução, plano pendente, entrega pendente, recuperação, aguarda você, concluída) x
// 1280x720, 1920x1080 e 1396x612 (Conversa inteira visível), com as três gavetas abertas, nas telas:
// lista de agentes, detalhe de cada agente (todas as abas), formulários de abelha e de missão, as quatro abas da
// Missão, popup de entrega e popup de conexão.
//
// Critérios (falha lista o elemento, a medida e o contexto):
//  1. `conteúdo extravasa`: elemento de bloco com scrollWidth > clientWidth sem rolagem própria (overflow visível ou
//     cortado sem reticências); `rolagem horizontal`: overflow-x auto/scroll com conteúdo largo (gavetas rolam só na vertical).
//  2. `fora da caixa`: descendente que passa da borda esquerda/direita da gaveta, do HUD, do popup de entrega ou do popup
//     de conexão (ignora o que está dentro de um ancestral que corta).
//  3. `cortado na vertical`: bloco com altura fixa e conteúdo maior, sem rolagem vertical (tolera `line-clamp` e reticências,
//     que são truncamentos de projeto e guardam o texto inteiro no `title`).
//  4. `aba sobre gaveta`: aba puxadora que cobre outra gaveta aberta (V04).
//  5. Conversa inteira visível com altura >= 600 px e a página sem rolagem do documento (V08).
// Avisos (não falham): células do mapa cobertas por gavetas abertas e HUD invadindo gavetas, que dependem do tamanho da janela.
import {createRequire} from 'node:module';
import {createServer} from 'node:http';
import {readFile,mkdir,writeFile} from 'node:fs/promises';
import {extname,join,normalize} from 'node:path';
import process from 'node:process';

const require=createRequire(import.meta.url),{chromium}=require('playwright'),root=process.cwd();
const output=process.argv[2]||join(root,'.qa-arquivo','2026-10-25_hivemind-visual-real','qa-estouro');
await mkdir(output,{recursive:true});
const mime={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.png':'image/png','.webp':'image/webp'};
const fileFor=url=>{
  const path=decodeURIComponent(new URL(url,'http://local').pathname);
  if(path==='/')return join(root,'index.html');
  if(path.startsWith('/codex-ui/static/'))return join(root,'codex_frontend','static',path.slice(17));
  if(path.startsWith('/hive-ui/static/'))return join(root,'HiveMind','frontend','static',path.slice(16));
  if(path.startsWith('/assets/'))return join(root,'assets',path.slice(8));
  return null;
};
const fixture=JSON.parse(await readFile(join(root,'tests','fixtures','hivemind_real_longo.json'),'utf8'));
let scenario='running';
const json=(res,body)=>{res.writeHead(200,{'content-type':'application/json'});res.end(JSON.stringify(body));};
const server=createServer(async(req,res)=>{
  const url=new URL(req.url,'http://local'),path=url.pathname;
  if(path.startsWith('/hive-api/')){
    const api=path.slice(9),current=fixture.scenarios[scenario];
    if(api==='/status')return json(res,fixture.status);
    if(api==='/catalog')return json(res,fixture.catalog);
    if(api==='/missions')return json(res,[current.mission]);
    if(api.startsWith('/missions/m1')){const after=Number(url.searchParams.get('after')||0);return json(res,{...current,events:current.events.filter(event=>event.seq>after)});}
    return json(res,{ok:true});
  }
  if(path==='/codex-ui/models')return json(res,{source:'snapshot',backendReady:false,models:[]});
  if(path==='/reports')return json(res,[]);
  if(path.startsWith('/session_watch/'))return json(res,{rev:0,lines:[]});
  if(['/session_start','/hud_ping','/hud_bye'].includes(path))return json(res,{ok:true});
  const file=fileFor(req.url);
  if(!file||!normalize(file).startsWith(root)){res.writeHead(404);res.end();return;}
  try{res.writeHead(200,{'content-type':mime[extname(file)]||'application/octet-stream'});res.end(await readFile(file));}catch{res.writeHead(404);res.end();}
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const base=`http://127.0.0.1:${server.address().port}`;

// Roda dentro da página: devolve a lista de problemas da tela atual.
const inspect=()=>{
  const problems=[],warnings=[];
  const describe=node=>`<${node.tagName.toLowerCase()}${node.className&&typeof node.className==='string'?'.'+node.className.trim().split(/\s+/).join('.'):''}> "${(node.textContent||'').replace(/\s+/g,' ').trim().slice(0,40)}"`;
  const visible=node=>node.getClientRects().length>0&&getComputedStyle(node).visibility!=='hidden';
  const inSvg=node=>!!node.closest('svg')&&node.tagName.toLowerCase()!=='svg';
  const boxes=[...document.querySelectorAll('.hm-live-workspace .hm-drawer,.hm-live-workspace .hm-delivery-dialog,.hm-live-workspace .hm-world-popup,.hm-live-workspace .hm-hud-main,.hm-live-workspace .hm-hud-alert')].filter(visible);
  const clamp=style=>style.getPropertyValue('-webkit-line-clamp')!=='none'&&style.getPropertyValue('-webkit-line-clamp')!=='';
  const seen=new Set();
  boxes.forEach(box=>{
    const outer=box.getBoundingClientRect(),area=box.className.split(' ').find(name=>name.startsWith('hm-')&&name!=='hm-drawer')||box.className;
    [box,...box.querySelectorAll('*')].forEach(node=>{
      if(seen.has(node)||inSvg(node)||!visible(node))return;
      seen.add(node);
      const style=getComputedStyle(node),rect=node.getBoundingClientRect(),block=!['inline','contents'].includes(style.display)&&node.tagName.toLowerCase()!=='svg';
      if(rect.width===0&&rect.height===0)return;
      const ellipsis=style.textOverflow==='ellipsis'&&style.whiteSpace==='nowrap',lines=clamp(style);
      if(block&&node.scrollWidth>node.clientWidth+1){
        if(['auto','scroll'].includes(style.overflowX))problems.push(`rolagem horizontal [${area}] ${describe(node)}: ${node.scrollWidth} > ${node.clientWidth}`);
        else if(['hidden','clip'].includes(style.overflowX)){if(!ellipsis&&!lines)problems.push(`conteúdo extravasa (cortado) [${area}] ${describe(node)}: ${node.scrollWidth} > ${node.clientWidth}`);}
        else problems.push(`conteúdo extravasa [${area}] ${describe(node)}: ${node.scrollWidth} > ${node.clientWidth}`);
      }
      if(block&&node.scrollHeight>node.clientHeight+1&&!lines&&!['auto','scroll'].includes(style.overflowY)&&(style.overflowY==='hidden'||style.overflowY==='clip')&&!ellipsis)problems.push(`cortado na vertical [${area}] ${describe(node)}: ${node.scrollHeight} > ${node.clientHeight}`);
      if(node!==box){
        let clipped=false;
        for(let parent=node.parentElement;parent&&parent!==box;parent=parent.parentElement){
          const parentStyle=getComputedStyle(parent);
          if(parentStyle.overflowX!=='visible'){const parentRect=parent.getBoundingClientRect();if(parentRect.left>=outer.left-1&&parentRect.right<=outer.right+1){clipped=true;break;}}
        }
        if(!clipped&&(rect.right>outer.right+1||rect.left<outer.left-1)&&style.position!=='fixed')problems.push(`fora da caixa [${area}] ${describe(node)}: ${Math.round(rect.left)}..${Math.round(rect.right)} vs ${Math.round(outer.left)}..${Math.round(outer.right)}`);
      }
    });
  });
  const intersects=(a,b)=>Math.min(a.right,b.right)-Math.max(a.left,b.left)>1&&Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)>1;
  const drawers=[...document.querySelectorAll('.hm-live-workspace .hm-drawer')].filter(visible);
  document.querySelectorAll('.hm-live-workspace .hm-pull').forEach(pull=>{
    const pullRect=pull.getBoundingClientRect();
    drawers.forEach(drawer=>{if(drawer.parentElement.contains(pull))return;if(drawer.inert)return;if(intersects(pullRect,drawer.getBoundingClientRect()))problems.push(`aba sobre gaveta: ${describe(pull)} cobre ${drawer.getAttribute('aria-label')}`);});
  });
  document.querySelectorAll('.hm-live-workspace .hm-cell').forEach(cell=>{if(!visible(cell))return;const cellRect=cell.getBoundingClientRect();drawers.forEach(drawer=>{if(!drawer.inert&&intersects(cellRect,drawer.getBoundingClientRect()))warnings.push(`célula ${cell.dataset.agent} coberta por ${drawer.getAttribute('aria-label')}`);});});
  const hud=document.querySelector('.hm-live-workspace .hm-hud-main');
  if(hud){const hudRect=hud.getBoundingClientRect();drawers.forEach(drawer=>{if(!drawer.inert&&intersects(hudRect,drawer.getBoundingClientRect()))warnings.push(`HUD invade ${drawer.getAttribute('aria-label')}`);});}
  const chat=document.querySelector('.hm-live-workspace .hm-chat');
  if(chat&&!chat.inert&&innerHeight>=600){
    const chatRect=chat.getBoundingClientRect(),form=chat.querySelector('.hm-chat-form').getBoundingClientRect(),head=chat.querySelector('.hm-chat-head').getBoundingClientRect();
    if(chatRect.bottom>innerHeight+1||form.bottom>innerHeight+1)problems.push(`Conversa cortada embaixo: caixa ${Math.round(chatRect.bottom)}, formulário ${Math.round(form.bottom)}, janela ${innerHeight}`);
    if(head.top<51)problems.push(`Conversa cortada em cima: cabeçalho em ${Math.round(head.top)}`);
    if(document.documentElement.scrollHeight>innerHeight+1)problems.push(`a página tem rolagem do documento: ${document.documentElement.scrollHeight} > ${innerHeight}`);
  }
  return {problems,warnings};
};

const VIEWPORTS=[{width:1280,height:720},{width:1920,height:1080},{width:1396,height:612}];
const STATES=['running','awaiting_plan_approval','awaiting_delivery_approval','recovery_required','awaiting_user','completed'];
const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});
const context=await browser.newContext({viewport:VIEWPORTS[0],deviceScaleFactor:1}),errors=[],failures=[],warned=new Set();
let checks=0;
try{
  const page=await context.newPage();
  page.on('pageerror',error=>errors.push(error.stack||error.message));
  page.on('console',message=>{if(message.type()==='error'&&!/404|fonts\.g/.test(message.text()))errors.push('console: '+message.text());});
  await page.addInitScript(()=>{localStorage.setItem('core.minimal',JSON.stringify({on:true,l:false,r:false}));localStorage.setItem('core.assistant','claude');localStorage.setItem('core.page','hive');sessionStorage.setItem('hivemind-mission','m1');});
  await page.goto(base+'/',{waitUntil:'domcontentloaded'});await page.locator('#hmPage').waitFor({state:'visible'});await page.evaluate(()=>document.fonts.ready);
  await page.locator('.hm-reduced').click();
  const live='.hm-live-workspace ';
  const get=expression=>page.evaluate(expression);
  const pause=ms=>page.waitForTimeout(ms);
  const click=async(selector,options={})=>{const target=page.locator(live+selector,options).first();if(await target.count()){await target.dispatchEvent('click');await pause(140);return true;}return false;};
  const openAll=async()=>{for(const side of ['left','right','bottom'])if(!await get(`window.hiveMindLive.getState().drawers.${side}`))await click(`.hm-pull-${side}`);};
  const select=async id=>{
    const selected=await get('window.hiveMindLive.getState().selected');
    if(selected===id)return true;
    const row=page.locator(`${live}.hm-agent-row[data-id="${id}"]`);
    if(!await row.count())return false;
    await row.dispatchEvent('click');await pause(140);await openAll();return true;
  };
  const deselect=async()=>{const selected=await get('window.hiveMindLive.getState().selected');if(selected){await click(`.hm-agent-row[data-id="${selected}"]`);await openAll();}};
  const check=async(tag,shot)=>{
    const {problems,warnings}=await page.evaluate(inspect);checks++;
    problems.forEach(text=>failures.push(`${tag}: ${text}`));
    warnings.forEach(text=>warned.add(`${tag}: ${text}`));
    if(shot)await page.screenshot({path:join(output,`${tag.replace(/[^\w-]+/g,'_')}.png`)});
    return problems.length;
  };
  for(const name of STATES){
    scenario=name;
    await page.waitForFunction(state=>window.hiveMindLive.getState().mission?.state===state&&!window.hiveMindLive.getState().error,fixture.scenarios[name].mission.state,{timeout:9000});
    for(const viewport of VIEWPORTS){
      await page.setViewportSize(viewport);await pause(200);
      await deselect();await openAll();
      const tag=view=>`${viewport.width}x${viewport.height} ${name} ${view}`;
      // padrão: lista de agentes, Missão em Plano, Conversa
      const issues=await check(tag('padrão'));if(issues)await page.screenshot({path:join(output,`${tag('padrão').replace(/\s+/g,'_')}.png`)});
      // abas da Missão
      for(const [label,text] of [['responsabilidades','Responsabilidades'],['conexões','Conexões'],['entrega','Entrega'],['plano','Plano']]){
        await click('.hm-mission-tabs > .hm-tabs button',{hasText:text});await check(tag(`missão ${label}`));
      }
      // detalhe de cada agente com todas as abas (só no estado em execução e no de falha, para não repetir os mesmos textos)
      if(name==='running'||name==='awaiting_user'){
        for(const id of ['rainha','bee-documentos','bee-extra','bee-verifier']){
          if(!await select(id))continue;
          for(const text of ['Visão geral','Tarefas','Skills','Ferramentas','Relações']){
            if(await click('.hm-agent-detail .hm-tabs button',{hasText:text}))await check(tag(`agente ${id} ${text}`));
          }
        }
        await deselect();
        // formulários da gaveta Agentes
        await select('bee-documentos');
        if(await click('.hm-drawer-foot button',{hasText:'Editar agente'})){await check(tag('formulário editar'));
          await click('.hm-worker-form button',{hasText:'Consultar modelos'});await pause(300);await check(tag('formulário com catálogo'));
          await click('.hm-worker-form button',{hasText:'Cancelar'});}
        await deselect();
        if(await click('.hm-drawer-foot button',{hasText:'Criar operária'})){
          await click('.hm-worker-form button',{hasText:'Adicionar'});await check(tag('formulário com erros'));
          await click('.hm-worker-form button',{hasText:'Cancelar'});}
        // criar missão
        if(await click('.hm-mission-picker button',{hasText:'Nova missão'})){await click('.hm-create-card button',{hasText:'Planejar com a Rainha'});await check(tag('nova missão com erros'));await click('.hm-create-card button',{hasText:'Cancelar'});}
      }
      // popup de conexão
      if(name==='running'||name==='awaiting_delivery_approval'){
        await page.evaluate(()=>document.querySelector('.hm-live-workspace [data-link="q-bee-documentos"] .hm-route-hit')?.dispatchEvent(new MouseEvent('click',{bubbles:true})));await pause(160);
        await check(tag('popup de conexão'));
        await page.evaluate(()=>document.querySelector('.hm-live-workspace .hm-world-popup:not([hidden]) button')?.dispatchEvent(new MouseEvent('click',{bubbles:true})));await pause(120);
      }
      // popup de entrega
      if(['awaiting_delivery_approval','completed','recovery_required'].includes(name)){
        const opened=await click('.hm-hud-action',{hasText:'Ver entrega'})||await click('.hm-mission-tabs button',{hasText:'Entrega'})&&await click('.hm-mission-body button',{hasText:'Ver entrega'});
        if(opened){await pause(160);await check(tag('popup de entrega'),viewport.width===1280);await page.keyboard.press('Escape');await pause(140);
          if(await page.locator(`${live}.hm-delivery:not([hidden])`).count())failures.push(`${tag('popup de entrega')}: Esc não fechou o popup`);}
        else failures.push(`${tag('popup de entrega')}: não foi possível abrir o popup`);
      }
    }
  }
  const summary={checks,failures:failures.length,warnings:[...warned],errors};
  await writeFile(join(output,'estouro.json'),JSON.stringify({...summary,problems:failures},null,2));
  if(errors.length)throw new Error('Erros na página: '+errors.join(' | '));
  if(failures.length){
    const unique=[...new Set(failures)];
    throw new Error(`Estouro: ${failures.length} problema(s) em ${checks} verificações (${unique.length} distintos; ${warned.size} avisos em ${join(output,'estouro.json')})\n`+unique.join('\n'));
  }
  console.log(JSON.stringify({ok:true,checks,warnings:[...warned],output}));
}finally{await context.close();await browser.close();await new Promise(resolve=>server.close(resolve));}
