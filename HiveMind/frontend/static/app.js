import '/codex-ui/static/providers.js';
import {DEMO_NOTICE} from './demo-data.js';
import {HiveSimulation} from './simulation.js';
import {createHiveView} from './hive.js';
import {createDrawers} from './drawers.js';
import {HiveMissionState} from './mission-state.js';
import {createLiveDrawers} from './live-drawers.js';

const addStylesheet=href=>{if(!document.querySelector(`link[href="${href}"]`)){const link=document.createElement('link');link.rel='stylesheet';link.href=href;document.head.appendChild(link);}};
addStylesheet('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Source+Sans+3:wght@400;500;600;700&display=swap');
addStylesheet('/hive-ui/static/bee-animation/bee.css');
addStylesheet('/hive-ui/static/hive.css');

const root=document.createElement('main');root.id='hmPage';root.className='hm-page';root.hidden=true;root.inert=true;root.setAttribute('aria-hidden','true');
root.innerHTML=`<header class="hm-header"><div class="hm-project"><span>Projeto</span><strong>Hive Mind</strong></div><button type="button" class="hm-mode">Abrir demonstração</button><div class="hm-scenarios" role="group" aria-label="Cenário" hidden><span>Exemplo</span><span class="hm-scenario-buttons"><button type="button" data-scenario="mission">Missão</button><button type="button" data-scenario="empty">Colmeia vazia</button><button type="button" data-scenario="failed">Etapa com falha</button></span></div><i></i><label class="hm-reduced"><input type="checkbox"><span class="hm-switch"><b></b></span><span>Reduzir movimento</span></label><strong class="hm-demo-notice" role="status" hidden>DEMONSTRAÇÃO<span class="hm-backend-note">DADOS SIMULADOS</span></strong></header><div class="hm-workspace hm-demo-workspace" hidden></div><div class="hm-workspace hm-live-workspace"></div>`;
root.querySelector('.hm-demo-notice').setAttribute('aria-label',DEMO_NOTICE);
root.querySelector('.hm-demo-notice').title=DEMO_NOTICE;
document.body.appendChild(root);

const workspace=root.querySelector('.hm-demo-workspace'),liveWorkspace=root.querySelector('.hm-live-workspace');
const simulation=new HiveSimulation();
const hive=createHiveView(workspace,simulation);
const drawers=createDrawers(workspace,simulation);
const live=new HiveMissionState(),liveHive=createHiveView(liveWorkspace,live),liveDrawers=createLiveDrawers(liveWorkspace,live);
const media=window.matchMedia?.('(prefers-reduced-motion: reduce)');
let manualReduced=false,lastDrawerSignature='',mode='real',pageActive=false;
simulation.setReduced(!!media?.matches);
const isolated=new Map();
const navigationLabels=new Map();

function setHiveNavigationLabels(active) {
  const labels={claude:'Claude Code',codex:'Codex',hive:'Hive Mind'};
  document.querySelectorAll('#assistantNavigation button').forEach(button=>{
    const key=button.dataset.page||button.dataset.assistant;
    if(!navigationLabels.has(button))navigationLabels.set(button,button.lastChild?.textContent||'');
    if(button.lastChild?.nodeType===Node.TEXT_NODE)button.lastChild.textContent=active?labels[key]:navigationLabels.get(button);
  });
}

function setHubIsolated(on) {
  [...document.body.children].filter(node=>node.tagName!=='SCRIPT'&&node!==root&&node.id!=='assistantChrome').forEach(node=>{
    if(on){if(!isolated.has(node))isolated.set(node,{inert:node.inert,aria:node.getAttribute('aria-hidden')});node.inert=true;node.setAttribute('aria-hidden','true');}
    else if(isolated.has(node)){const before=isolated.get(node);node.inert=before.inert;if(before.aria===null)node.removeAttribute('aria-hidden');else node.setAttribute('aria-hidden',before.aria);isolated.delete(node);}
  });
}

root.querySelectorAll('[data-scenario]').forEach(button=>button.addEventListener('click',()=>simulation.setScenario(button.dataset.scenario)));
function setMode(value){mode=value;const demo=mode==='demo';workspace.hidden=!demo;liveWorkspace.hidden=demo;root.querySelector('.hm-scenarios').hidden=!demo;root.querySelector('.hm-demo-notice').hidden=!demo;root.querySelector('.hm-mode').textContent=demo?'Voltar à missão real':'Abrir demonstração';root.querySelector('.hm-project strong').textContent=demo?'Operação de pedidos':'Hive Mind';simulation.setLifecycle(pageActive&&demo,!document.hidden);live.setLifecycle(pageActive&&!demo);}
root.querySelector('.hm-mode').addEventListener('click',()=>setMode(mode==='demo'?'real':'demo'));
window.addEventListener('hivemind-demo-request',()=>setMode('demo'));
root.querySelector('.hm-reduced input').addEventListener('change',event=>{manualReduced=event.target.checked;simulation.setReduced(manualReduced||!!media?.matches);live.setReduced(manualReduced||!!media?.matches);});
media?.addEventListener?.('change',()=>{simulation.setReduced(manualReduced||media.matches);live.setReduced(manualReduced||media.matches);});
document.addEventListener('visibilitychange',()=>{simulation.setDocumentVisible(!document.hidden);live.setDocumentVisible(!document.hidden);});
root.addEventListener('keydown',event=>{if(event.key==='Escape'&&simulation.snapshot().delivery){event.preventDefault();simulation.setDelivery(false);}});

simulation.subscribe(state=>{
  if(mode==='demo')root.querySelector('.hm-reduced input').checked=state.reduced;
  hive.render(state);
  const signature=JSON.stringify([state.phaseId,state.scenario,state.manualPaused,state.adjusted,state.selected,state.selectedLink,state.showSubs,state.added,state.form,state.agentTab,state.missionTab,state.delivery,state.drawers,state.log]);
  if(signature!==lastDrawerSignature){lastDrawerSignature=signature;drawers.render(state);}
  else drawers.updateProgress(state);
  if(mode==='demo'){root.dataset.reduced=String(state.reduced);root.dataset.paused=String(state.animationsPaused);}
  root.querySelectorAll('[data-scenario]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.scenario===state.scenario)));
});
live.setReduced(!!media?.matches);
live.subscribe(state=>{liveHive.render(state);liveDrawers.render(state);if(mode==='real'){root.querySelector('.hm-reduced input').checked=state.reduced;root.dataset.reduced=String(state.reduced);root.dataset.paused=String(state.animationsPaused);}});

const lifecycle={
  activate(){pageActive=true;setHubIsolated(true);setHiveNavigationLabels(true);root.hidden=false;root.inert=false;root.setAttribute('aria-hidden','false');setMode(mode);},
  deactivate(){pageActive=false;simulation.setLifecycle(false,!document.hidden);live.setLifecycle(false);root.inert=true;root.hidden=true;root.setAttribute('aria-hidden','true');setHiveNavigationLabels(false);setHubIsolated(false);},
};

window.hubProviders?.registerPage?.('hive',lifecycle);
window.hiveMindDemo={simulation,getState:()=>simulation.snapshot()};
window.hiveMindLive={getState:()=>live.snapshot()};
