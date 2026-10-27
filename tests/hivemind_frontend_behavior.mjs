import assert from 'node:assert/strict';

globalThis.document = {hidden:false};
let now=0;
const timers=[];
const {HiveSimulation}=await import('../HiveMind/frontend/static/simulation.js');
const {agentStatus}=await import('../HiveMind/frontend/static/hive.js');
const sim=new HiveSimulation({now:()=>now,schedule:fn=>(timers.push(fn),fn),cancel:fn=>{const i=timers.indexOf(fn);if(i>=0)timers.splice(i,1);}});
sim.setLifecycle(true,true);
assert.equal(sim.snapshot().phaseId,'idle');
sim.start('<img src=x onerror=alert(1)>');
assert.equal(sim.snapshot().phaseId,'p1a');
assert.equal(sim.snapshot().log[0].text,'<img src=x onerror=alert(1)>');

now=1600;sim.tick();assert.equal(sim.snapshot().phaseId,'p1b');
sim.pause();const held=sim.snapshot().elapsed;now+=9000;sim.tick();assert.equal(sim.snapshot().phaseId,'p1b');assert.equal(sim.snapshot().elapsed,held);
sim.setLifecycle(false,true);sim.resume();assert.equal(sim.snapshot().running,false);
sim.setLifecycle(true,true);assert.equal(sim.snapshot().running,true);

sim.go('approval');assert.equal(sim.nextStep(),false);assert.equal(sim.snapshot().phaseId,'approval');
sim.adjust();assert.equal(sim.snapshot().phaseId,'adj1');sim.go('approval');assert.equal(sim.snapshot().adjusted,true);sim.approve();assert.equal(sim.snapshot().phaseId,'p6a');
sim.go('done');sim.setDelivery(true);assert.equal(sim.snapshot().delivery,true);

const delayed=[];
const clocked=new HiveSimulation({now:()=>now,schedule:fn=>(timers.push(fn),fn),cancel:()=>{},scheduleTimeout:(fn,delay)=>(delayed.push({fn,delay}),delayed.at(-1)),cancelTimeout:item=>{item.cancelled=true;}});
clocked.setLifecycle(true,true);clocked.go('done',{delivery:false});assert.equal(delayed.at(-1).delay,1600);
now+=700;clocked.setLifecycle(false,true);assert.equal(clocked.snapshot().delivery,false);assert.equal(delayed.at(-1).cancelled,true);
now+=2000;clocked.setLifecycle(true,true);assert.equal(delayed.at(-1).delay,900);delayed.at(-1).fn();assert.equal(clocked.snapshot().delivery,true);
clocked.go('done',{delivery:false});clocked.setReduced(true);clocked.go('done',{delivery:false});assert.equal(delayed.at(-1).delay,400);clocked.pause();assert.equal(delayed.at(-1).cancelled,true);clocked.resume();assert.equal(delayed.at(-1).delay,400);delayed.at(-1).fn();assert.equal(clocked.snapshot().delivery,true);
clocked.destroy();

sim.setScenario('failed');assert.equal(sim.snapshot().phaseId,'fail');sim.retry();assert.equal(sim.snapshot().phaseId,'retry');
sim.setScenario('empty');assert.equal(sim.start(),false);assert.equal(sim.snapshot().agents.length,0);
assert.equal(sim.freeSlot(),null);assert.equal(sim.setWorkerForm(true),undefined);assert.equal(sim.snapshot().form,false);
sim.setScenario('mission');
assert.deepEqual(sim.addWorker('', 'x'),{ok:false,error:'Informe o nome da operária.'});
assert.equal(sim.addWorker('Financeiro','Conferência de pagamentos').ok,true);
assert.equal(sim.addWorker('Fiscal','Notas e impostos').ok,true);
assert.equal(sim.addWorker('Compras','Cotações').ok,true);
assert.equal(sim.addWorker('Quarto','Sem vaga').ok,false);
assert.equal(sim.snapshot().added.length,3);
sim.selectAgent(sim.snapshot().added[1].id);assert.equal(sim.removeSelected(),true);assert.equal(sim.snapshot().added.length,2);
assert.equal(sim.addWorker('Novo','Especialidade').ok,true);
const added=sim.snapshot().added.at(-1);assert.equal(added.spec,'Especialidade');assert.equal(agentStatus(added,sim.snapshot())[2],'Sem tarefa nesta missão.');

sim.go('p2b');now+=800;sim.setLifecycle(false,true);const hidden=sim.snapshot().elapsed;now+=10000;sim.tick();assert.equal(sim.snapshot().elapsed,hidden);assert.equal(sim.snapshot().phaseId,'p2b');
sim.state.elapsed=1800;sim.state.running=false;assert.equal(sim.snapshot().progress,.5);assert.equal(sim.stepProgress(),.5);const documentos=sim.snapshot().agents.find(agent=>agent.id==='documentos'),analise=sim.snapshot().agents.find(agent=>agent.id==='analise'),subAnexos=sim.snapshot().agents.find(agent=>agent.id==='sub-anexos');assert.equal(documentos.id,'documentos');assert.equal(agentStatus(analise,sim.snapshot())[2],'Depende das entregas de Documentos e Cadastros.');sim.go('idle',{delivery:false,log:[]});assert.equal(agentStatus(subAnexos,sim.snapshot())[2],'Acionado por Documentos quando houver leitura.');sim.go('p2b',{delivery:false,log:[]});sim.state.elapsed=1800;sim.state.running=false;
sim.state.showSubs=false;sim.selectAgent('sub-anexos');assert.equal(sim.snapshot().showSubs,true);const drawersBefore=JSON.stringify(sim.snapshot().drawers);sim.selectLink('doc-s1');assert.equal(JSON.stringify(sim.snapshot().drawers),drawersBefore);
sim.setLifecycle(true,true);assert.equal(sim.snapshot().running,true);
sim.sendMessage('<script>bad()</script>');assert.equal(sim.snapshot().log.at(-2).text,'<script>bad()</script>');
sim.destroy();
const store=new Map(),beacons=[];
globalThis.sessionStorage={getItem:key=>store.get(key)??null,setItem:(key,value)=>store.set(key,value)};
globalThis.window={addEventListener:(name,fn)=>{if(name==='pagehide')beacons.push(fn);},dispatchEvent(){}};
Object.defineProperty(globalThis,'navigator',{value:{sendBeacon:()=>true},configurable:true});
let seqs={a:450,b:3};const urls=[];
globalThis.fetch=async url=>{
  urls.push(url);
  const ok=data=>({ok:true,json:async()=>data});
  const path=url.replace('/hive-api','');
  if(path==='/presence'||path==='/status')return ok(path==='/status'?{roster:{bees:[],revision:0},settings:{}}:{ok:true});
  if(path==='/missions')return ok([{id:'a',data:{title:'A'}},{id:'b',data:{title:'B'}}]);
  const [, id, query]=path.match(/^\/missions\/(\w+)\?after=(\d+)$/);
  const after=Number(query),events=[];
  for(let seq=after+1;seq<=seqs[id]&&events.length<200;seq++)events.push({seq,kind:'x',data:{}});
  return ok({mission:{id,revision:1,data:{}},events,roster:[],jobs:[],...(id==='b'?{bees_summary:[{id:'queen',role:'queen'}]}:{})});
};
const {HiveMissionState}=await import('../HiveMind/frontend/static/mission-state.js');
const live=new HiveMissionState();clearInterval(live.heartbeat);live.missionId='a';
await live.refresh();
assert.equal(live.events.length,450);assert.equal(live.events.at(-1).seq,450);
assert.deepEqual(urls.filter(url=>url.includes('/missions/a')),['/hive-api/missions/a?after=0','/hive-api/missions/a?after=200','/hive-api/missions/a?after=400']);
seqs.a=451;urls.length=0;await live.refresh();
assert.equal(live.events.at(-1).seq,451);assert.equal(live.events.length,451);assert.ok(urls.includes('/hive-api/missions/a?after=450'));
seqs.a=900;await live.refresh();
assert.equal(live.events.length,500);assert.equal(live.events.at(-1).seq,900);assert.equal(live.events[0].seq,401);
assert.equal(live.beesSummary,null,'missão antiga, sem bees_summary, abre sem erro');
live.selectMission('b');await live.refresh();
assert.deepEqual(live.beesSummary,[{id:'queen',role:'queen'}]);
assert.deepEqual(live.events.map(event=>event.seq),[1,2,3]);
seqs.b=4;await live.refresh();assert.deepEqual(live.events.map(event=>event.seq),[1,2,3,4]);

const {validateTeam,chatQueen}=await import('../HiveMind/frontend/static/live-drawers.js');
const bee=(id,role,model='m',effort='high')=>({id,role,provider:'codex',model,effort,temporary:false});
const team=[bee('queen','queen'),bee('worker1','worker'),bee('verifier','verifier')];
assert.equal(validateTeam(team),'');
assert.match(validateTeam([bee('queen','queen'),bee('worker1','worker',''),bee('verifier','verifier')]),/Operária "worker1": selecione um modelo/);
assert.match(validateTeam([bee('queen','queen'),bee('worker1','worker','m',''),bee('verifier','verifier')]),/Operária "worker1": selecione o esforço/);
assert.match(validateTeam([bee('queen','queen'),bee('queen','worker'),bee('verifier','verifier')]),/Identificador repetido: queen/);
assert.match(validateTeam([bee('queen','queen'),bee('w','worker')]),/exatamente um Verificador/);
assert.match(validateTeam([bee('q','queen'),bee('q2','queen'),bee('w','worker'),bee('v','verifier')]),/exatamente uma Rainha/);
assert.match(validateTeam([bee('queen','queen'),bee('verifier','verifier')]),/ao menos uma Operária/);
assert.match(validateTeam([bee('',  'queen'),bee('w','worker'),bee('v','verifier')]),/identificador/);
const staleQueen=bee('queen','queen','old'),newQueen=bee('queen','queen','new');
assert.deepEqual(chatQueen({roster:{bees:[newQueen,bee('w','worker')]}},{queen:staleQueen}),newQueen);
assert.deepEqual(chatQueen({roster:{bees:[]}},{queen:staleQueen}),staleQueen);
const {describeCode,stateLabel}=await import('../HiveMind/frontend/static/messages.js');
assert.equal(describeCode('stale_revision'),'A missão mudou enquanto você olhava; aguarde a tela atualizar e tente de novo. (stale_revision)');
assert.equal(describeCode('context_unverified'),'Não foi possível confirmar o contexto do provedor. (context_unverified)');
assert.equal(describeCode('codigo_que_nao_existe'),'Erro inesperado (codigo_que_nao_existe)');
assert.equal(describeCode('invalid_state:abandoned'),'Ação indisponível no estado “encerrada por você”. (invalid_state:abandoned)');
assert.equal(describeCode('delivery_recovery_required'),'Há uma aplicação na origem pendente de recuperação: use “Recuperar entrega” antes de continuar. (delivery_recovery_required)');
for(const code of ['toString','constructor','__proto__','hasOwnProperty'])assert.equal(describeCode(code),`Erro inesperado (${code})`);
assert.equal(stateLabel('toString'),'toString');
assert.match(describeCode('invalid_state:novo_estado'),/novo_estado/);
assert.match(describeCode('turn_failed:claude:api_error_500'),/^O provedor encerrou o turno com falha\. \(turn_failed:claude:api_error_500\)$/);
assert.match(describeCode('api_error_429'),/\(api_error_429\)/);
assert.equal(describeCode(''),'');
for(const state of ['draft','clarifying','planning','awaiting_plan_approval','ready','preparing','running','verifying','correcting','awaiting_delivery_approval','delivery_approved','applying','completed','pausing','paused','awaiting_user','recovery_required','abandoned'])assert.notEqual(stateLabel(state),state);
for(const state of ['draft','clarifying','planning','awaiting_plan_approval','ready','preparing','running','verifying','correcting','awaiting_delivery_approval','delivery_approved','applying','completed','pausing','paused','awaiting_user','recovery_required','abandoned'])assert.equal(describeCode('invalid_state:'+state),`Ação indisponível no estado “${stateLabel(state)}”. (invalid_state:${state})`);

// Gavetas do modo real (VR-05 a VR-07), com um DOM mínimo de teste
class FakeNode{
  constructor(tag){this.tag=tag;this.children=[];this.listeners={};this.attrs={};this.dataset={};this.style={};this.className='';this.hidden=false;this.disabled=false;this.value='';this.checked=false;this.scrollTop=0;this.scrollHeight=0;this.inert=false;this._text=null;
    const owner=this;this.classList={toggle(name,on){const set=new Set(owner.className.split(' ').filter(Boolean));if(on===undefined?!set.has(name):on)set.add(name);else set.delete(name);owner.className=[...set].join(' ');},add(name){this.toggle(name,true);}};}
  append(...items){items.forEach(item=>this.children.push(typeof item==='string'?Object.assign(new FakeNode('#text'),{_text:item}):item));}
  appendChild(item){this.children.push(item);return item;}
  replaceChildren(...items){this.children=[];this.append(...items);}
  addEventListener(name,fn){(this.listeners[name]??=[]).push(fn);}
  fire(name,event={}){(this.listeners[name]||[]).forEach(fn=>fn({preventDefault(){},...event}));}
  click(){if(this.disabled)return;this.fire('click');}
  setAttribute(name,value){this.attrs[name]=String(value);}
  focus(){globalThis.document.activeElement=this;}
  get textContent(){return this._text!==null?this._text:this.children.map(child=>child.textContent).join('');}
  set textContent(value){this._text=String(value);this.children=[];}
  get firstChild(){return this.children[0];}
}
const walk=(node,out=[])=>{out.push(node);node.children.forEach(child=>walk(child,out));return out;};
const rendered=(node,out=[])=>{if(node.hidden)return out;out.push(node);node.children.forEach(child=>rendered(child,out));return out;};
globalThis.document={hidden:false,activeElement:null,createElement:tag=>new FakeNode(tag),createElementNS:(ns,tag)=>new FakeNode(tag),createTextNode:text=>Object.assign(new FakeNode('#text'),{_text:text})};
// A função real conserva botão e foco enquanto atualiza conteúdo e ação do alerta.
const {readFile}=await import('node:fs/promises');
const hiveSource=await readFile(new URL('../HiveMind/frontend/static/hive.js',import.meta.url),'utf8');
const alertDefinition=hiveSource.slice(hiveSource.indexOf('function fillAlert('),hiveSource.indexOf('\n\nexport function createHiveView'));
const fillAlert=Function('svg','document',alertDefinition+';return fillAlert;')((tag,attrs)=>{const node=new FakeNode(tag);Object.entries(attrs).forEach(([key,value])=>node.setAttribute(key,value));return node;},document);
const alertNode=new FakeNode('div'),actions=[];
fillAlert(alertNode,true,'Aprovação pendente.','Aguarda decisão.','Ver aprovação',()=>actions.push('approval'));
const alertButton=alertNode.children[3];alertButton.focus();
fillAlert(alertNode,true,'Aprovação pendente.','Aguarda decisão.','Ver aprovação',()=>actions.push('updated'));
assert.equal(alertNode.children[3],alertButton);assert.equal(document.activeElement,alertButton);alertButton.onclick();assert.deepEqual(actions,['updated']);
fillAlert(alertNode,false,'Falha.','Detalhes da falha.','Ver detalhes',()=>actions.push('failure'));
assert.equal(alertNode.children[3],alertButton);assert.equal(document.activeElement,alertButton);assert.equal(alertNode.children[0].children[0].tag,'rect');assert.equal(alertButton.textContent,'Ver detalhes');alertButton.onclick();assert.deepEqual(actions,['updated','failure']);
const {createLiveDrawers,validateTeam:teamValidator}=await import('../HiveMind/frontend/static/live-drawers.js');
const {deriveRealView:derive}=await import('../HiveMind/frontend/static/mission-state.js');
const {parseTags,validateBeeForm}=await import('../HiveMind/frontend/static/live-team.js');
const {interruption,cycleLimitNotice}=await import('../HiveMind/frontend/static/live-mission.js');
const {deliveryView,criterionText}=await import('../HiveMind/frontend/static/live-delivery.js');
const {shortHash}=await import('../HiveMind/frontend/static/live-ui.js');
assert.equal(teamValidator,validateTeam);

// Funções puras
assert.deepEqual(parseTags(' python, testes ,python,\n revisão ,, '),['python','testes','revisão']);
const form=(extra={})=>({id:'financeiro',description:'Confere pagamentos.',tags:['python'],instructions:'',tools:['read'],provider:'codex',model:'m',effort:'high',...extra});
const ctx={role:'worker',rows:[],editing:false};
assert.deepEqual(validateBeeForm(form(),ctx),{});
assert.ok(validateBeeForm(form({id:'a b'}),ctx).id);
assert.ok(validateBeeForm(form({id:'x'}),{...ctx,rows:[{id:'x'}]}).id);
assert.equal(validateBeeForm(form({id:'x'}),{...ctx,rows:[{id:'x'}],editing:true}).id,undefined);
assert.ok(validateBeeForm(form({description:'  '}),ctx).description);
assert.ok(validateBeeForm(form({description:'x'.repeat(2001)}),ctx).description);
assert.ok(validateBeeForm(form({tags:Array.from({length:21},(_,i)=>`t${i}`)}),ctx).skills);
assert.ok(validateBeeForm(form({tags:['x'.repeat(61)]}),ctx).skills);
assert.ok(validateBeeForm(form({instructions:'x'.repeat(4001)}),ctx).skills);
assert.ok(validateBeeForm(form({tools:[]}),ctx).tools);
assert.ok(validateBeeForm(form({tools:['read','patch']}),{...ctx,role:'queen'}).tools,'a Rainha não altera arquivos');
assert.ok(validateBeeForm(form({tools:['patch']}),{...ctx,role:'verifier'}).tools);
assert.equal(validateBeeForm(form({tools:['read','checks']}),{...ctx,role:'verifier'}).tools,undefined);
assert.deepEqual(Object.keys(validateBeeForm(form({model:'',effort:'',provider:''}),ctx)).sort(),['effort','model','provider']);
assert.equal(shortHash('a'.repeat(64)),'aaaaaaaa');
assert.equal(criterionText({id:'ac',status:'unverifiable',description:'Só os arquivos da tarefa mudam.'}),'não verificável — Só os arquivos da tarefa mudam. (ac)');
assert.equal(interruption({state:'running'},[{seq:2,kind:'job_error',data:{reason:'nao_mapeado'}}]),'Última interrupção: Erro inesperado (nao_mapeado)');
assert.equal(interruption({state:'running'},[{seq:2,kind:'job_error',data:{reason:'x'}},{seq:3,kind:'resumed',data:{}}]),'');
assert.equal(cycleLimitNotice({state:'running',data:{}}),'');
assert.equal(deliveryView({data:{}}),null);
const dv=deliveryView({data:{plan:{tasks:[{id:'t1',bee_id:'w1',files:['a.py']}],acceptance:[{id:'ac',description:'D'}]},delivery:{changes:['a.py','z.py']},delivery_hash:'h',verdict:{criteria:{ac:'passed'}}}});
assert.deepEqual([dv.changes.length,dv.outside,dv.passed,dv.changes[0].task,dv.changes[0].bee],[2,1,1,'t1','w1']);

// Compositor com DOM falso
const calls=[],requests=[],handlers=[];
const liveStub={toggleDrawer:name=>calls.push(['toggle',name]),loadCatalog:()=>calls.push(['catalog']),selectMission:id=>calls.push(['select',id]),selectAgent:id=>calls.push(['agent',id]),selectLink:id=>calls.push(['link',id]),
  command:(...args)=>{calls.push(['command',...args]);return Promise.resolve(true);},requestUi:target=>{requests.push(target);handlers.forEach(fn=>fn(target));},onUiRequest:fn=>{handlers.push(fn);return()=>{};},
  create:async(...args)=>{calls.push(['create',...args]);return true;},saveTeam:async bees=>{calls.push(['saveTeam',bees]);return liveStub.saveResult;},saveLimit:value=>calls.push(['limit',value]),saveResult:true};
const rootNode=new FakeNode('div'),drawers=createLiveDrawers(rootNode,liveStub);
const [leftWrap,rightWrap,bottomWrap]=rootNode.children;
const missionDrawer=rightWrap.children[0],dynamic=walk(missionDrawer).find(node=>node.className==='hm-mission-dynamic'),chatDrawer=bottomWrap.children[0];
const texts=(node=dynamic)=>walk(node).map(item=>item.textContent).filter(Boolean);
const commandButtons=(node=dynamic)=>walk(node).filter(item=>item.tag==='button'&&/hm-(dark|outline)/.test(item.className));
const labels=()=>commandButtons().map(item=>item.textContent);
const pressed=name=>commandButtons().find(item=>item.textContent===name).click();
const pickTab=name=>walk(dynamic).find(item=>item.tag==='button'&&item.textContent===name&&!/hm-/.test(item.className)).click();
const hash='a1b2c3d4'.repeat(8);
const rosterBees=[bee('queen','queen'),bee('worker1','worker'),bee('verifier','verifier')].map(item=>({...item,description:'D',skills:{tags:[],instructions:''},tools:['read']}));
const base={drawers:{left:false,right:true,bottom:false},status:{roster:{bees:rosterBees,revision:1,incomplete:[]},settings:{worker_limit:2}},catalog:null,error:'',errorDetail:null,missions:[],messages:[],events:[],agents:[],tasks:[],connections:[],linkInfo:{},selected:null,selectedLink:null,phase:{agents:{},links:{},step:0},animationsPaused:false,reduced:false};
const shown=(state,extra={})=>{
  const mission={id:'m1',revision:3,state,cycle:1,cycle_limit:3,data:{title:'T',...(extra.data||{})}},view=derive({mission,events:extra.events||[],team:rosterBees});
  const snapshot={...base,...extra,mission,missions:[mission],agents:view.agents,tasks:view.tasks,connections:view.connections,linkInfo:view.linkInfo,phase:view.phase,hud:view.hud,events:extra.events||[]};
  drawers.render(snapshot);return snapshot;
};

// aba puxadora com contador e gavetas fechadas inertes
shown('running');
assert.equal(leftWrap.children[1].children.at(-2).textContent,String(3));assert.equal(rightWrap.children[1].children.at(-2).textContent,'3/7');
assert.equal(rightWrap.children[1].attrs['aria-expanded'],'true');
assert.equal(leftWrap.children[0].inert,true);assert.equal(missionDrawer.inert,false);assert.equal(chatDrawer.inert,true);
assert.ok([leftWrap,rightWrap,bottomWrap].every(wrap=>wrap.children[1].inert!==true),'abas puxadoras continuam clicáveis');
assert.ok(/hm-pull/.test(leftWrap.children[1].className));leftWrap.children[1].click();assert.deepEqual(calls.pop(),['toggle','left']);

// Missão: recuperação sem botão de avanço e encerramento confirmado na própria gaveta
shown('recovery_required');
assert.ok(texts().some(text=>text.includes('A missão exige recuperação explícita antes de continuar')));
assert.deepEqual(labels().filter(name=>/Reconciliar|Recuperar|Encerrar|Confirmar|Retomar|Iniciar|Aprovar/.test(name)),['Encerrar missão']);
shown('recovery_required',{data:{delivery_hash:'h',reconciliation_required:{conflicts:['a.txt']}}});
assert.deepEqual(labels().filter(name=>/Reconciliar|Recuperar|Encerrar|Confirmar|Retomar|Iniciar|Aprovar/.test(name)),['Recuperar entrega','Encerrar missão']);
pressed('Recuperar entrega');assert.deepEqual(calls.pop(),['command','recover_delivery']);
pressed('Encerrar missão');assert.ok(!calls.some(call=>call[1]==='abandon'));
assert.ok(labels().includes('Confirmar encerramento')&&labels().includes('Cancelar')&&!labels().includes('Encerrar missão'));
assert.ok(texts().some(text=>text.startsWith('Encerrar esta missão?')));
let snapshot=shown('recovery_required',{data:{delivery_hash:'h'}});drawers.render(snapshot);
assert.ok(labels().includes('Confirmar encerramento'),'a confirmação sobrevive à nova renderização');
pressed('Cancelar');assert.ok(labels().includes('Encerrar missão')&&!labels().includes('Confirmar encerramento'));
pressed('Encerrar missão');pressed('Confirmar encerramento');assert.deepEqual(calls.pop(),['command','abandon']);
drawers.render(snapshot);assert.ok(labels().includes('Encerrar missão'));
pressed('Encerrar missão');shown('running');assert.ok(!labels().includes('Confirmar encerramento'));
shown('recovery_required');assert.ok(labels().includes('Encerrar missão'),'a confirmação não volta depois de sair do estado');
shown('recovery_required',{error:'delivery_recovery_required'});
assert.ok(texts().some(text=>text.includes('Recuperar entrega')&&text.includes('(delivery_recovery_required)')&&!text.includes('encerrar')));
const limitEdit=walk(missionDrawer).find(item=>item.className==='hm-limit-edit');
shown('abandoned',{data:{delivery_hash:'h',reconciliation_required:{conflicts:[]},plan:{x:1},plan_hash:'p'}});
assert.ok(texts().includes('Missão encerrada por você. O histórico foi preservado e a origem não foi alterada.'));
assert.deepEqual(labels(),[]);assert.equal(limitEdit.hidden,true,'sem botão de ciclos em missão encerrada');

// interrupções (F9) e limite de ciclos (F8)
const failure={seq:9,kind:'job_error',data:{reason:'security_config_invalid'}};
shown('awaiting_user',{events:[{seq:1,kind:'plan_proposed',data:{}},failure]});
assert.ok(texts().some(text=>text.startsWith('O trabalho parou.')&&text.includes('(security_config_invalid)')&&text.includes('gaveta Conversa')));
assert.ok(!labels().includes('Retomar'));
shown('awaiting_plan_approval',{events:[failure,{seq:10,kind:'plan_proposed',data:{}}]});assert.ok(!texts().some(text=>text.includes('security_config_invalid')));
shown('paused',{events:[failure,{seq:10,kind:'resumed',data:{}}]});assert.ok(!texts().some(text=>text.includes('security_config_invalid')));
const verdictData={plan_hash:'p',plan:{acceptance:[{id:'ac-escopo',description:'Só os arquivos da tarefa mudam.'}],tasks:[],bees:[]},
  attempt_outcome:{plan_hash:'p',plan_attempt:1,cycle:3,status:'cycle_limit'},verdict:{criteria:{'ac-escopo':'unverifiable'},evidence:'Sem lista de arquivos.',passed:false,cycle:3}};
shown('awaiting_user',{data:verdictData});
assert.ok(texts().some(text=>text.startsWith('A missão usou os 3 ciclos permitidos')&&text.includes('aumente o máximo de ciclos')));
pickTab('Entrega');
assert.ok(texts().includes('não verificável — Só os arquivos da tarefa mudam. (ac-escopo)'));
assert.ok(texts().includes('Evidência: Sem lista de arquivos.')&&texts().includes('Não aprovada no ciclo 3.'));
assert.ok(!texts().some(text=>text.includes('"criteria"')),'nenhum JSON cru');
pickTab('Plano');
shown('awaiting_user',{data:{...verdictData,plan_hash:'outro'}});assert.ok(!texts().some(text=>text.startsWith('A missão usou os')));
shown('paused',{events:[failure]});assert.ok(labels().includes('Retomar'));pressed('Retomar');assert.deepEqual(calls.pop(),['command','resume']);
shown('running',{events:[{seq:2,kind:'job_error',data:{reason:'nao_mapeado'}}]});assert.ok(texts().includes('Última interrupção: Erro inesperado (nao_mapeado)'));
assert.ok(labels().includes('Pausar'));pressed('Pausar');assert.deepEqual(calls.pop(),['command','pause']);
shown('ready',{data:{plan_hash:'p'}});pressed('Iniciar');assert.deepEqual(calls.pop(),['command','start']);

// Aprovações: plano e entrega, hash curto com o completo no title, nada de JSON
const bigPlan={objective:'Objetivo do plano',bees:[...rosterBees.map(b=>({...b})),{...bee('tmp','worker'),temporary:true}],tasks:[{id:'t1',description:'Fazer',bee_id:'worker1',depends_on:[],files:['a.py']}],acceptance:[{id:'ac-1',description:'Critério um'}]};
shown('awaiting_plan_approval',{data:{plan:bigPlan,plan_hash:hash}});
assert.deepEqual(labels().filter(name=>/Aprovar|ajuste/.test(name)),['Aprovar','Solicitar ajuste']);
assert.ok(texts().includes('1 tarefas · 4 abelhas (1 temporárias) · 1 critérios de aceite'));
const versionNode=walk(dynamic).find(item=>item.textContent==='Versão a1b2c3d4');assert.equal(versionNode.title,hash);
assert.ok(!texts().some(text=>text.includes(hash)||text.includes('{')||text.includes('"')),'sem hash completo nem JSON na tela');
pressed('Aprovar');assert.deepEqual(calls.pop(),['command','approve_plan',{plan_hash:hash}]);
pressed('Solicitar ajuste');assert.deepEqual(requests.pop(),'chat');
shown('awaiting_plan_approval',{data:{plan:bigPlan,plan_hash:hash}});
assert.deepEqual(texts().filter(text=>/^[1-9]$/.test(text)),['1','1'],'o plano lista as tarefas e os critérios');
const delivered={plan:bigPlan,plan_hash:hash,candidate_hash:'c'.repeat(64),delivery_hash:'d'.repeat(64),delivery:{changes:['a.py','b.py']},verdict:{passed:true,cycle:1,criteria:{'ac-1':'passed'},evidence:'ok'}};
shown('awaiting_delivery_approval',{data:delivered});
assert.deepEqual(labels().filter(name=>/Aprovar|Ver entrega/.test(name)),['Ver entrega','Aprovar','Ver entrega'],'o botão do andamento e o cartão levam à entrega');
assert.ok(texts().includes('2 arquivos alterados · 1 de 1 critérios aprovados · 1 fora do plano'));
commandButtons().filter(item=>item.textContent==='Aprovar')[0].click();assert.deepEqual(calls.pop(),['command','approve_delivery',{candidate_hash:'c'.repeat(64),delivery_hash:'d'.repeat(64)}]);
commandButtons().filter(item=>item.textContent==='Ver entrega')[0].click();assert.equal(requests.pop(),'delivery');
shown('delivery_approved',{data:delivered});pickTab('Entrega');
assert.ok(labels().includes('Incorporar entrega aprovada')&&texts().includes('A origem e o journal precisam estar no mesmo volume.'));
pressed('Incorporar entrega aprovada');assert.deepEqual(calls.pop(),['command','apply',{delivery_hash:'d'.repeat(64)}]);
assert.ok(texts().includes('a.py')&&texts().includes('Fora do plano'));
pickTab('Plano');

// limite de ciclos no cabeçalho
shown('running');
const limitInput=limitEdit.children[1],limitSave=limitEdit.children[2];
assert.equal(limitEdit.hidden,false);assert.equal(limitInput.value,'3');limitInput.value='5';limitSave.click();assert.deepEqual(calls.pop(),['command','cycle_limit',{limit:5}]);

// popup de entrega: abre por onUiRequest, mostra dados reais e fecha com Esc
const popup=rootNode.children.at(-1);
rootNode.fire('keydown',{key:'Escape'});
shown('awaiting_delivery_approval',{data:delivered});
assert.equal(popup.hidden,true);
handlers.forEach(fn=>fn('delivery'));shown('awaiting_delivery_approval',{data:delivered});
assert.equal(popup.hidden,false);
const popupTexts=texts(popup);
assert.ok(popupTexts.includes('Entrega · missão real')&&popupTexts.includes('b.py')&&popupTexts.includes('Versão da entrega dddddddd'));
assert.deepEqual(commandButtons(popup).map(item=>item.textContent),['Fechar','Aprovar entrega','Fechar']);
commandButtons(popup).find(item=>item.textContent==='Aprovar entrega').click();assert.deepEqual(calls.pop(),['command','approve_delivery',{candidate_hash:'c'.repeat(64),delivery_hash:'d'.repeat(64)}]);
rootNode.fire('keydown',{key:'Escape'});assert.equal(popup.hidden,true,'Esc fecha o popup');
shown('running');handlers.forEach(fn=>fn('delivery'));shown('running');assert.equal(popup.hidden,true,'sem entrega o popup não abre');

// criar missão: validação por campo, campos limpos depois de criar (F7)
const createCard=walk(missionDrawer).find(item=>/hm-create-card/.test(item.className)),createForm=walk(createCard).find(item=>item.tag==='form');
const fields=walk(createCard).filter(item=>['input','textarea'].includes(item.tag)),[nameField,projectField,goalField,cyclesField]=fields;
drawers.render({...base,mission:null,missions:[],agents:[],hud:{step:0,approval:false,paper:false,failed:false,complete:false,text:'',action:null,alert:null}});
assert.equal(createCard.hidden,false,'sem missão o cartão de criar aparece');
await Promise.all(createForm.listeners.submit.map(fn=>fn({preventDefault(){}})));
assert.equal(calls.filter(call=>call[0]==='create').length,0);
assert.ok(texts(createCard).includes('Informe o nome da missão.')&&texts(createCard).includes('Descreva o objetivo da missão.'));
nameField.value='Nome';projectField.value='C:/proj';goalField.value='Objetivo';cyclesField.value='4';
await Promise.all(createForm.listeners.submit.map(fn=>fn({preventDefault(){}})));
assert.deepEqual(calls.pop(),['create','Nome','C:/proj','Objetivo',4]);
assert.deepEqual([nameField.value,projectField.value,goalField.value,cyclesField.value],['','','','3'],'os campos limpam depois de criar');
shown('running');assert.equal(createCard.hidden,true);
walk(missionDrawer).find(item=>item.textContent==='Nova missão'&&item.tag==='button').click();
assert.equal(createCard.hidden,false);assert.equal(dynamic.hidden,true);
walk(createCard).find(item=>item.textContent==='Cancelar').click();assert.equal(createCard.hidden,true);
// equipe incompleta bloqueia o planejamento
const submitCreate=walk(createCard).find(item=>item.textContent==='Planejar com a Rainha');
drawers.render({...base,status:{roster:{bees:rosterBees,revision:1,incomplete:[{id:'worker1',missing:['description']}]},settings:{}},mission:null,missions:[],agents:[],hud:{step:0,approval:false,paper:false,failed:false,complete:false,text:'',action:null,alert:null}});
assert.equal(submitCreate.disabled,true);assert.ok(texts(createCard).some(text=>text.includes('worker1')&&text.includes('antes de planejar')));

// Conversa
calls.length=0;
const chatLog=walk(chatDrawer).find(item=>item.className==='hm-chat-log'),chatForm=walk(chatDrawer).find(item=>item.tag==='form'),chatInput=walk(chatDrawer).find(item=>item.tag==='input'),chatSend=walk(chatDrawer).find(item=>item.tag==='button'&&item.textContent==='Enviar para a Rainha');
const planning={source:'C:/proj',queen:rosterBees[0],messages:[{role:'user',text:'Oi <b>x</b>'},{role:'assistant',text:'Olá, usuário'}]};
shown('awaiting_plan_approval',{messages:planning.messages,data:{planning}});
assert.deepEqual(chatLog.children.map(item=>item.className),['hm-chat-user','hm-chat-event']);
assert.ok(texts(chatLog).includes('Oi <b>x</b>')&&texts(chatLog).some(text=>text.startsWith('Rainha')));
assert.equal(chatSend.disabled,false);
chatInput.value='Ajuste o plano';chatForm.listeners.submit.forEach(fn=>fn({preventDefault(){}}));
assert.deepEqual(calls.pop(),['command','ask',{source:'C:/proj',queen:rosterBees[0],message:'Ajuste o plano'}]);assert.equal(chatInput.value,'');
chatInput.value='   ';chatForm.listeners.submit.forEach(fn=>fn({preventDefault(){}}));assert.equal(calls.length,0);
shown('running',{messages:planning.messages,data:{planning}});assert.equal(chatSend.disabled,true);
assert.ok(texts(chatDrawer).some(text=>text.startsWith('A Rainha só recebe mensagens')));
chatInput.value='não envia';chatForm.listeners.submit.forEach(fn=>fn({preventDefault(){}}));assert.equal(calls.length,0);
shown('clarifying',{messages:planning.messages,data:{planning:{...planning,queen:{...rosterBees[0],model:'antiga'}}}});
assert.ok(texts(chatLog).some(text=>text.includes('A equipe mudou desde o início desta missão')&&text.includes('(queen · codex ·')));

// Agentes: linhas, marcas, contadores e detalhe
const teamBees=[...rosterBees.map(b=>({...b})),{...bee('tmp','worker'),temporary:true,description:'Temporária',skills:{tags:['sql'],instructions:'Use com cuidado.'},tools:['read','checks']}];
const teamPlan={...bigPlan,bees:teamBees};
const teamState=(extra={},stateName='running',data={})=>{const mission={id:'m1',revision:2,state:stateName,cycle:1,cycle_limit:3,data:{title:'T',plan:teamPlan,plan_hash:'p',plan_attempt:1,...data}},view=derive({mission,jobs:extra.jobs||[],events:[],team:teamBees});
  const snap={...base,drawers:{left:true,right:false,bottom:false},...extra,mission,missions:[mission],agents:view.agents,tasks:view.tasks,connections:view.connections,linkInfo:view.linkInfo,phase:view.phase,hud:view.hud};drawers.render(snap);return snap;};
const leftDrawer=leftWrap.children[0],rows=()=>walk(leftDrawer).filter(item=>/hm-agent-row-wrap/.test(item.className));
teamState();
assert.equal(rows().length,4);
assert.ok(texts(leftDrawer).includes('Temporária'));assert.ok(texts(leftDrawer).includes('1 rainha, 2 operárias, 1 verificador, 1 temporárias'));
assert.ok(texts(leftDrawer).some(text=>text==='0 trabalhando'));
teamState({status:{roster:{bees:rosterBees,revision:1,incomplete:[{id:'worker1',missing:['description','skills','tools']}]},settings:{worker_limit:2}}});
assert.ok(texts(leftDrawer).includes('Incompleta'));assert.ok(texts(leftDrawer).some(text=>text.includes('1 incompleta')));
assert.ok(texts(leftDrawer).some(text=>text.includes('Não dá para planejar com a Rainha até completar')));
// detalhe: abas, skills e ferramentas vindas do cadastro
teamState({selected:'bee-tmp'});
const tabNames=()=>walk(leftDrawer).filter(item=>item.tag==='button'&&['Visão geral','Tarefas','Skills','Ferramentas','Relações'].includes(item.textContent)).map(item=>item.textContent);
assert.deepEqual(tabNames(),['Visão geral','Tarefas','Skills','Ferramentas','Relações']);
assert.ok(texts(leftDrawer).includes('Operária temporária'));
assert.ok(!walk(leftDrawer).some(item=>item.tag==='select'),'temporária é somente leitura');
const openTab=name=>walk(leftDrawer).find(item=>item.tag==='button'&&item.textContent===name).click();
openTab('Skills');assert.ok(texts(leftDrawer).includes('sql')&&texts(leftDrawer).includes('Use com cuidado.'));
openTab('Ferramentas');assert.ok(texts(leftDrawer).includes('Ler arquivos do projeto')&&texts(leftDrawer).includes('Rodar verificações aprovadas')&&texts(leftDrawer).includes('Informar progresso')&&!texts(leftDrawer).includes('Alterar arquivos do plano'));
openTab('Tarefas');
teamState({selected:'rainha'});
assert.deepEqual(tabNames(),['Visão geral','Tarefas','Relações'],'a Rainha tem as abas do protótipo para ela');
teamState({selected:'bee-worker1'});openTab('Visão geral');
assert.ok(walk(leftDrawer).filter(item=>item.tag==='select').length===3,'permanente tem provedor, modelo e esforço editáveis');
const [providerSelect,modelSelect,effortSelect]=walk(leftDrawer).filter(item=>item.tag==='select');
assert.equal(modelSelect.value,'m');assert.equal(effortSelect.value,'high');assert.equal(modelSelect.disabled,true,'sem catálogo não troca, mas o salvo aparece');
assert.ok(modelSelect.children.some(option=>option.value==='m'),'modelo salvo aparece antes de consultar o catálogo');
// Consultar modelos mostra carregamento (F1)
teamState({selected:null,catalogLoading:true});
const loadButton=()=>walk(leftDrawer).find(item=>item.tag==='button'&&/modelos/.test(item.textContent));
assert.equal(loadButton().textContent,'Consultando modelos…');assert.equal(loadButton().disabled,true);
teamState({selected:null});assert.equal(loadButton().textContent,'Consultar modelos');loadButton().click();assert.deepEqual(calls.pop(),['catalog']);
// excluir: só operária permanente
teamState({selected:'bee-tmp'});
const footButton=name=>walk(leftDrawer).find(item=>item.tag==='button'&&item.textContent===name);
assert.equal(footButton('Excluir agente').disabled,true);assert.equal(footButton('Editar agente').disabled,true);
teamState({selected:'rainha'});assert.equal(footButton('Excluir agente').disabled,true);assert.equal(footButton('Editar agente').disabled,false);
teamState({selected:'bee-worker1'});assert.equal(footButton('Excluir agente').disabled,true,'a equipe precisa de ao menos uma operária');
const twoWorkers=[...rosterBees.map(b=>({...b})),{...bee('worker2','worker'),description:'D2',skills:{tags:[],instructions:''},tools:['read']}];
const twoState={status:{roster:{bees:twoWorkers,revision:1,incomplete:[]},settings:{}}};
{const mission=null,view=derive({mission,team:twoWorkers});drawers.render({...base,...twoState,drawers:{left:true,right:false,bottom:false},mission,agents:view.agents,tasks:view.tasks,connections:view.connections,linkInfo:view.linkInfo,phase:view.phase,hud:view.hud,selected:'bee-worker2'});}
assert.equal(footButton('Excluir agente').disabled,false);footButton('Excluir agente').click();
assert.deepEqual(calls.pop(),['saveTeam',rosterBees.map(b=>({...b}))]);

// formulário de criar operária: lista inteira, abelha nova completa, erro no campo certo
const catalog={codex:{authenticated:true,compatible:true,errors:[],models:[{name:'m',efforts:['high','low']}]}};
const open=(extra={})=>{const mission=null,view=derive({mission,team:rosterBees});drawers.render({...base,drawers:{left:true,right:false,bottom:false},mission,agents:view.agents,tasks:view.tasks,connections:view.connections,linkInfo:view.linkInfo,phase:view.phase,hud:view.hud,catalog,...extra});};
open();footButton('＋ Criar operária').click();
const formNode=walk(leftDrawer).find(item=>item.tag==='form'),control=(tag,index=0)=>walk(formNode).filter(item=>item.tag===tag)[index];
const [idInput,skillsInput]=walk(formNode).filter(item=>item.tag==='input'&&!item.type);
const textareas=walk(formNode).filter(item=>item.tag==='textarea'),checks=walk(formNode).filter(item=>item.tag==='input'&&item.type==='checkbox');
assert.deepEqual(checks.map(item=>[item.value,item.checked,item.disabled]),[['read',true,false],['patch',true,false],['checks',false,false]],'operária nova começa com leitura e escrita');
const [formProvider,formModel,formEffort]=walk(formNode).filter(item=>item.tag==='select');
const submitForm=()=>Promise.all(formNode.listeners.submit.map(fn=>fn({preventDefault(){}})));
await submitForm();
assert.ok(texts(formNode).includes('Use letras, números, ponto, hífen ou sublinhado (até 100 caracteres).')&&texts(formNode).includes('Descreva o que esta abelha faz.')&&texts(formNode).includes('Escolha o modelo.'));
assert.equal(calls.filter(call=>call[0]==='saveTeam').length,0);
idInput.value='financeiro';textareas[0].value='Confere pagamentos.';skillsInput.value='python, sql';textareas[1].value='Cuidado com datas.';
const formConsult=()=>walk(formNode).find(item=>item.tag==='button'&&/modelos/.test(item.textContent));
idInput.focus();formConsult().click();assert.deepEqual(calls.pop(),['catalog']);
open({catalogLoading:true});assert.equal(formConsult().textContent,'Consultando modelos…');assert.equal(formConsult().disabled,true);
assert.equal(document.activeElement,idInput);assert.equal(idInput.value,'financeiro');assert.equal(textareas[0].value,'Confere pagamentos.');
open({catalogLoading:false});assert.equal(formConsult().textContent,'Consultar modelos');assert.equal(formConsult().disabled,false);assert.equal(document.activeElement,idInput);
formModel.value='m';formModel.fire('change');
const [,formModel2,formEffort2]=walk(formNode).filter(item=>item.tag==='select');formEffort2.value='high';formEffort2.fire('change');
liveStub.saveResult=false;
liveStub.errorProbe=null;
await submitForm();
const saved=calls.pop();assert.equal(saved[0],'saveTeam');
assert.deepEqual(saved[1].at(-1),{id:'financeiro',role:'worker',provider:'codex',model:'m',effort:'high',temporary:false,description:'Confere pagamentos.',skills:{tags:['python','sql'],instructions:'Cuidado com datas.'},tools:['read','patch']});
assert.deepEqual(saved[1].slice(0,3),rosterBees,'a lista inteira vai junto, sem mexer nas outras abelhas');
// erro do backend no campo certo
open({error:'invalid_request',errorDetail:{error:'invalid_request',bee:'financeiro',field:'description'}});
assert.ok(walk(leftDrawer).some(item=>item===formNode),'o formulário continua aberto com o que foi digitado');
await submitForm();
assert.ok(texts(formNode).some(text=>text.includes('Solicitação inválida.')&&text.includes('campo descrição')));
liveStub.saveResult=true;await submitForm();calls.pop();
assert.ok(!walk(leftDrawer).some(item=>item===formNode),'salvou: o formulário fecha');
liveStub.saveResult=true;
open({selected:'bee-worker1'});footButton('Editar agente').click();
const editForm=walk(leftDrawer).find(item=>item.tag==='form'),editDescription=walk(editForm).find(item=>item.tag==='textarea');
const editConsult=()=>walk(editForm).find(item=>item.tag==='button'&&/modelos/.test(item.textContent));
editDescription.value='Texto editado';editDescription.focus();editConsult().click();assert.deepEqual(calls.pop(),['catalog']);
open({selected:'bee-worker1',catalogLoading:true});assert.equal(editConsult().textContent,'Consultando modelos…');assert.equal(editConsult().disabled,true);
assert.equal(document.activeElement,editDescription);assert.equal(editDescription.value,'Texto editado');
open({selected:'bee-worker1',catalogLoading:false});assert.equal(editConsult().textContent,'Consultar modelos');assert.equal(editConsult().disabled,false);assert.equal(document.activeElement,editDescription);
walk(editForm).find(item=>item.tag==='button'&&item.textContent==='Cancelar').click();
assert.match(describeCode('planning_read_required'),/Rainha precisa da ferramenta Ler arquivos do projeto/);
// Rainha com job rodando antes da sessão abrir não aparece "Disponível" (F5)
live.status={roster:{bees:[bee('queen','queen'),bee('worker1','worker'),bee('verifier','verifier')]}};live.mission=null;
live.jobs=[{state:'running',bee_id:'queen',data:{}}];
assert.deepEqual(live.snapshot().phase.agents.rainha,['coord','Iniciando','Abrindo a sessão do provedor.']);
live.jobs=[{state:'running',bee_id:'queen',data:{process:{pid:1,created:1}}}];
assert.deepEqual(live.snapshot().phase.agents.rainha.slice(0,2),['coord','Executando']);
assert.equal(live.snapshot().phase.agents['bee-worker1'][1],'Disponível');
// VR-04 (26/10/2026): snapshot real com etapas, estados, rotas, progresso e temporárias
const {deriveRealView,missionStep,missionFailure,STEP_NAMES}=await import('../HiveMind/frontend/static/mission-state.js');
const planBee=(id,role,temporary=false,extra={})=>({id,role,provider:'codex',model:'m',effort:'high',temporary,...extra});
const realPlan={bees:[planBee('queen','queen'),planBee('w1','worker'),planBee('w2','worker'),planBee('tmp','worker',true),planBee('verifier','verifier')],
  tasks:[{id:'t1',description:'Extrair os dados',bee_id:'w1',depends_on:[],files:['a.py']},{id:'t2',description:'Analisar',bee_id:'w2',depends_on:['t1'],files:['b.py']},{id:'t3',description:'Tarefa extra',bee_id:'tmp',depends_on:[],files:['c.py']}]};
const mk=(state,extra={},cycle=1)=>({id:'m1',revision:1,state,cycle,cycle_limit:3,data:{title:'Missão de teste',plan:realPlan,plan_hash:'p1',plan_attempt:1,...extra}});
const taskJob=(bee,task,state,extra={})=>({id:`${bee}-${task}-${state}`,bee_id:bee,role:'worker',state,data:{task_id:task,cycle:1,plan_hash:'p1',plan_attempt:1,...extra}});
const realView=(mission,jobs=[],extra={})=>deriveRealView({mission,jobs,events:[],team:realPlan.bees,...extra});
const kind=(result,id)=>result.phase.agents[id][0];

assert.equal(STEP_NAMES.length,7);
const stepOf=(state,data={})=>missionStep({state,cycle:1,data});
for(const [state,step] of Object.entries({clarifying:1,planning:1,awaiting_plan_approval:2,ready:2,running:3,correcting:3,verifying:4,awaiting_delivery_approval:5,delivery_approved:6,applying:6,recovery_required:6,completed:7}))assert.equal(stepOf(state),step,state);
assert.equal(missionStep(null),0);
assert.equal(stepOf('paused',{pause:{from:'verifying'}}),4);
assert.equal(stepOf('awaiting_user',{pause:{from:'running'}}),3);
assert.equal(stepOf('awaiting_user',{plan:{},pause:{}}),2,'sem origem registrada, usa o que a missão já tem');
assert.equal(stepOf('awaiting_user',{plan_hash:'p',attempt_outcome:{status:'cycle_limit',plan_hash:'p',cycle:3}}),4);
assert.equal(stepOf('abandoned',{abandoned:{previous_state:'awaiting_delivery_approval'}}),5);

// sem missão: HUD zerado e equipe salva
const empty=realView(null);
assert.equal(empty.hud.step,0);assert.equal(empty.hud.text,'Nenhuma missão selecionada');assert.equal(empty.hud.action,null);assert.equal(empty.hud.alert,null);
assert.equal(empty.agents.length,5);assert.equal(kind(empty,'rainha'),'idle');

// execução sem nenhum job: delegação, fila e dependência
let result=realView(mk('running'));
assert.deepEqual(result.agents.map(agent=>[agent.id,agent.slot]),[['rainha','Q'],['bee-w1','NW'],['bee-w2','NE'],['bee-tmp','E'],['bee-verifier','SE']]);
assert.equal(result.agents.find(agent=>agent.id==='bee-tmp').temporary,true);assert.equal(result.agents.find(agent=>agent.id==='bee-w1').temporary,false);
assert.deepEqual(result.phase.agents['bee-w1'].slice(0,2),['waiting','Tarefa na fila']);
assert.deepEqual(result.phase.agents['bee-w2'],['waiting','Aguardando informação','Depende de w1.']);
assert.deepEqual([result.phase.links['q-bee-w1'],result.phase.links['q-bee-w2'],result.phase.links['dep-bee-w1-bee-w2'],result.phase.links['q-bee-verifier']],['out','wait','wait','idle']);
assert.deepEqual(result.connections.map(item=>item[0]),['q-bee-w1','q-bee-w2','q-bee-tmp','q-bee-verifier','dep-bee-w1-bee-w2']);
assert.ok(result.connections.every(([,from,to])=>result.agents.some(agent=>agent.id===from)&&result.agents.some(agent=>agent.id===to)));
assert.equal(result.hud.step,3);assert.equal(result.hud.text,'Etapa 3 de 7 · Execução');assert.deepEqual(result.hud.action,{id:'pause',label:'Pausar'});assert.equal(result.hud.alert,null);
// antes de iniciar, tudo fica parado
result=realView(mk('ready'));
assert.deepEqual(result.phase.agents['bee-w1'].slice(0,2),['idle','Disponível']);assert.equal(result.phase.links['q-bee-w1'],'idle');assert.equal(result.phase.links['dep-bee-w1-bee-w2'],'idle');
assert.deepEqual(result.hud.action,{id:'start',label:'Iniciar'});

// uma abelha trabalhando: anel por tarefas e rota em execução
result=realView(mk('running'),[taskJob('w1','t1','running',{process:{pid:1}})]);
assert.deepEqual(result.phase.agents['bee-w1'],['working','Executando','Extrair os dados',[0,1,'tarefas']]);
assert.equal(result.phase.links['q-bee-w1'],'del');assert.deepEqual(result.phase.agents.rainha,['coord','Acompanhando o andamento','1 abelha trabalhando.'],'a Rainha acompanha enquanto uma abelha executa');
assert.equal(kind(realView(mk('running')),'rainha'),'idle','sem abelha executando a Rainha não coordena');
assert.equal(kind(realView(mk('paused',{pause:{from:'running'}}),[taskJob('w1','t1','paused',{process:{pid:1}})]),'rainha'),'idle');
assert.equal(realView(mk('running'),[taskJob('w1','t1','running',{process:{}}),taskJob('tmp','t3','running',{process:{}})]).phase.agents.rainha[2],'2 abelhas trabalhando.');
result=realView(mk('running'),[{id:'q',bee_id:'queen',role:'queen',state:'running',data:{process:{pid:2},cycle:1}}]);
assert.equal(kind(result,'rainha'),'coord');

// tarefa concluída: rota de retorno e entrega para a dependente
const finished=[taskJob('w1','t1','succeeded'),taskJob('tmp','t3','succeeded')];
result=realView(mk('running'),finished);
assert.deepEqual(result.phase.agents['bee-w1'],['done','Entregue','1 tarefa concluída.']);
assert.equal(result.phase.links['q-bee-w1'],'ret');assert.equal(result.phase.links['dep-bee-w1-bee-w2'],'flow');
assert.deepEqual(result.phase.agents['bee-w2'].slice(0,2),['waiting','Tarefa na fila']);assert.equal(result.phase.links['q-bee-w2'],'out');
const justFinished=[{seq:5,kind:'job_finished',created_at:100,data:{job_id:'w1-t1-succeeded',state:'succeeded'}}];
assert.equal(realView(mk('running'),finished,{events:justFinished,now:102}).phase.links['q-bee-w1'],'in');
assert.equal(realView(mk('running'),finished,{events:justFinished,now:140}).phase.links['q-bee-w1'],'ret');
result=realView(mk('running'),[...finished,taskJob('w2','t2','running',{process:{pid:3}})]);
assert.equal(result.phase.links['dep-bee-w1-bee-w2'],'done');
// job de outro ciclo não conta
assert.equal(realView(mk('running'),[taskJob('w1','t1','succeeded',{cycle:1})],{}).phase.agents['bee-w1'][0],'done');
assert.equal(deriveRealView({mission:mk('correcting',{},2),jobs:[taskJob('w1','t1','succeeded')],team:realPlan.bees}).phase.agents['bee-w1'][0],'waiting');

// falha de uma abelha
result=realView(mk('running'),[taskJob('w1','t1','succeeded'),taskJob('w2','t2','failed')]);
assert.equal(kind(result,'bee-w2'),'failed');assert.equal(result.phase.links['q-bee-w2'],'fail');
assert.equal(realView(mk('running'),[taskJob('w1','t1','succeeded'),taskJob('w2','t2','failed'),taskJob('w2','t2','running',{process:{}})]).phase.agents['bee-w2'][0],'working');
// pausa e interrupção mostram a etapa onde pararam
result=realView(mk('paused',{pause:{from:'running'}}));
assert.equal(result.hud.text,'Etapa 3 de 7 · Execução · Pausada');assert.equal(result.hud.paper,true);assert.equal(result.hud.failed,false);assert.deepEqual(result.hud.action,{id:'resume',label:'Retomar'});assert.equal(result.hud.alert,null);
assert.deepEqual(result.phase.agents['bee-w1'].slice(0,2),['waiting','Em pausa']);
const failEvents=[{seq:1,kind:'plan_proposed',data:{}},{seq:9,kind:'job_error',data:{reason:'security_config_invalid'}}];
const stopped=mk('awaiting_user',{pause:{from:'running',reason:'job_failed'}});
result=realView(stopped,[],{events:failEvents});
assert.equal(result.hud.text,'Etapa 3 de 7 · Execução · falhou');assert.equal(result.hud.failed,true);assert.equal(result.hud.paper,false);
assert.equal(result.hud.alert.approval,false);assert.equal(result.hud.alert.title,'Falha na etapa Execução.');assert.match(result.hud.alert.text,/\(security_config_invalid\)/);assert.equal(result.hud.alert.button,'Ver detalhes');
assert.deepEqual(result.phase.agents.rainha,['approval','Impedimento',result.hud.alert.text]);assert.equal(result.phase.failed,true);
assert.equal(missionFailure(stopped,[...failEvents,{seq:10,kind:'resumed',data:{}}]),'');
result=realView(mk('awaiting_user',{attempt_outcome:{status:'cycle_limit',plan_hash:'p1',cycle:3}}));
assert.equal(result.hud.step,4);assert.match(result.hud.alert.text,/3 ciclos permitidos/);
result=realView(mk('recovery_required',{delivery_hash:'h'}));
assert.equal(result.hud.step,6);assert.equal(result.hud.failed,true);assert.equal(result.hud.text,'Etapa 6 de 7 · Incorporação · Recuperação necessária');assert.equal(result.hud.action,null);
result=realView(mk('abandoned',{abandoned:{previous_state:'running'}}));
assert.equal(result.hud.text,'Etapa 3 de 7 · Execução · Encerrada');assert.equal(result.hud.action,null);assert.equal(result.hud.alert,null);

// aprovações pendentes: ação do HUD e banner
result=realView(mk('awaiting_plan_approval'));
assert.equal(result.hud.step,2);assert.equal(result.hud.approval,true);assert.equal(result.hud.paper,true);assert.deepEqual(result.hud.action,{id:'view_approval',label:'Ver aprovação'},'o HUD não aprova direto');
assert.deepEqual([result.hud.alert.approval,result.hud.alert.title,result.hud.alert.button,result.hud.alert.target],[true,'Aprovação pendente.','Ver aprovação','approval']);
assert.equal(kind(result,'rainha'),'approval');assert.equal(result.phase.agents.rainha[1],'Aguardando sua decisão');assert.equal(result.phase.failed,false);
result=realView(mk('awaiting_delivery_approval',{delivery:{files:[]},delivery_hash:'d'}));
assert.equal(result.hud.step,5);assert.deepEqual(result.hud.action,{id:'view_delivery',label:'Ver entrega'});assert.equal(result.hud.alert.approval,true);
assert.equal(realView(mk('awaiting_delivery_approval')).hud.action,null,'sem entrega preparada não há o que ver');
assert.equal(realView(mk('clarifying')).phase.agents.rainha[1],'Aguardando você');assert.equal(realView(mk('clarifying')).hud.action,null);
assert.deepEqual(realView(mk('planning')).hud.action,{id:'pause',label:'Pausar'});

// verificação e conclusão
result=realView(mk('verifying'));
assert.equal(result.hud.step,4);assert.deepEqual(result.phase.agents['bee-verifier'].slice(0,2),['waiting','Tarefa na fila']);assert.equal(result.phase.links['q-bee-verifier'],'out');
result=realView(mk('verifying'),[{id:'v',bee_id:'verifier',role:'verifier',state:'running',data:{process:{pid:4},cycle:1}}]);
assert.equal(kind(result,'bee-verifier'),'working');assert.equal(result.phase.links['q-bee-verifier'],'del');assert.equal(kind(result,'rainha'),'coord','a Rainha acompanha a verificação');
const everything=[taskJob('w1','t1','succeeded'),taskJob('w2','t2','succeeded'),taskJob('tmp','t3','succeeded'),{id:'v',bee_id:'verifier',role:'verifier',state:'succeeded',data:{cycle:1}}];
result=realView(mk('completed',{delivery:{files:[]}}),everything);
assert.equal(result.hud.step,7);assert.equal(result.hud.complete,true);assert.equal(result.hud.text,'Etapa 7 de 7 · Concluída');assert.deepEqual(result.hud.action,{id:'view_delivery',label:'Ver entrega'});
assert.deepEqual(['rainha','bee-w1','bee-w2','bee-tmp','bee-verifier'].map(id=>kind(result,id)),['done','done','done','done','done']);
assert.deepEqual(Object.values(result.phase.links),['ret','ret','ret','ret','done']);

// com bees_summary: ordem, temporárias, progresso fino e status vindos do backend
const summaryBee=(id,role,extra={})=>({id,role,temporary:false,active:true,description:`descrição de ${id}`,skills:{tags:['python'],instructions:''},tools:['read'],provider:'codex',model:'m',effort:'high',tasks:{total:0,done:0,current:null,items:[]},progress:null,tools_used:{},job:{state:null,cycle:1,started:false},...extra});
const summary=[summaryBee('queen','queen'),
  summaryBee('w1','worker',{tasks:{total:2,done:1,current:'t2',items:[{id:'t1',description:'Primeira',status:'done',depends_on:[],files:['a.py']},{id:'t2',description:'Segunda',status:'running',depends_on:['t1'],files:['a.py']}]},progress:{done:3,total:23,note:'lendo anexos',seq:812},tools_used:{read:4},job:{state:'running',cycle:1,started:true}}),
  summaryBee('tmp','worker',{temporary:true,tasks:{total:1,done:0,current:'t3',items:[{id:'t3',description:'Extra',status:'waiting',depends_on:['t2'],files:['c.py']}]}}),
  summaryBee('gone','worker',{active:false}),summaryBee('verifier','verifier')];
result=realView(mk('running'),[],{summary});
assert.deepEqual(result.agents.map(agent=>agent.id),['rainha','bee-w1','bee-tmp','bee-verifier']);
assert.deepEqual(result.phase.agents['bee-w1'],['working','Executando','lendo anexos',[3,23,'passos']]);
assert.deepEqual(result.phase.agents['bee-tmp'],['waiting','Aguardando informação','Depende de w1.']);
assert.equal(result.agents[2].temporary,true);assert.equal(result.agents[1].info.description,'descrição de w1');assert.deepEqual(result.agents[1].info.toolsUsed,{read:4});assert.deepEqual(result.agents[1].info.tasks,{total:2,done:1,current:'t2',items:summary[1].tasks.items.map(item=>({...item,bee_id:'w1'}))});
assert.deepEqual([result.phase.links['q-bee-w1'],result.phase.links['dep-bee-w1-bee-tmp']],['del','wait']);
assert.deepEqual(realView(mk('awaiting_plan_approval'),[],{summary:[summaryBee('queen','queen'),summaryBee('w1','worker')]}).tasks.map(task=>[task.id,task.status]),[['t1','pending'],['t2','waiting'],['t3','pending']],'resumo sem itens: as tarefas vêm do plano proposto');
assert.deepEqual(realView(mk('running'),[],{summary:[]}).agents.map(agent=>agent.id),['rainha','bee-w1','bee-w2','bee-tmp','bee-verifier'],'resumo vazio cai no plano');

// teto Rainha + 8
const crowd=[planBee('queen','queen'),...Array.from({length:12},(_,index)=>planBee(`w${index}`,'worker')),planBee('verifier','verifier')];
result=deriveRealView({mission:null,team:crowd});
assert.equal(result.agents.length,9);assert.equal(result.agents[0].slot,'Q');assert.deepEqual(result.agents.slice(1).map(agent=>agent.slot),['NW','NE','E','SE','SW','W','X1','X2']);

// HiveMissionState: resumo guardado, snapshot completo e ações do HUD
live.status={roster:{bees:realPlan.bees}};live.mission=mk('awaiting_plan_approval');live.jobs=[];live.events=[];live.beesSummary=null;
let snap=live.snapshot();
assert.equal(snap.phaseId,'real');assert.equal(snap.hud.step,2);assert.equal(snap.agents.length,5);assert.equal(snap.connections.length,5);assert.equal(snap.progress,0);assert.equal(snap.beesSummary,null);
live.mission=mk('completed');assert.equal(live.snapshot().phaseId,'done');
const sent=[],ui=[];live.command=(...args)=>{sent.push(args);return Promise.resolve();};const stopListening=live.onUiRequest(target=>ui.push(target));
live.mission=mk('awaiting_plan_approval');live.drawers.right=false;
live.hudAction('start');live.hudAction('pause');live.hudAction('resume');
assert.deepEqual(sent,[['start'],['pause'],['resume']]);
live.hudAction('view_delivery');live.hudAction('view_approval');live.hudAction('qualquer');
assert.deepEqual(ui,['delivery','approval','details']);assert.equal(live.drawers.right,true);
stopListening();live.hudAction('view_delivery');assert.equal(ui.length,3);
console.log('hivemind behavior ok');
