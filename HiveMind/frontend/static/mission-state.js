import {hiveApi} from './api.js';
import {describeCode,stateLabel} from './messages.js';

const id=()=>crypto.randomUUID().replaceAll('-','');
const slots=['NW','NE','E','SE','SW','W','X1','X2'];

export const STEP_NAMES=['Planejamento','Aprovação do plano','Execução','Verificação','Aprovação da entrega','Incorporação','Concluída'];
const STEP_BY_STATE={draft:1,clarifying:1,planning:1,awaiting_plan_approval:2,ready:2,preparing:2,running:3,correcting:3,verifying:4,awaiting_delivery_approval:5,delivery_approved:6,applying:6,recovery_required:6,completed:7};
const RUNNING=new Set(['running','tool_active','draining']),FAILED=new Set(['failed','unknown']);
const APPROVALS=['awaiting_plan_approval','awaiting_delivery_approval'];
const PAUSED=['paused','pausing','awaiting_user'];

// Etapa (1 a 7) em que a missão está ou parou; 0 sem missão.
export function missionStep(mission){
  if(!mission)return 0;
  const data=mission.data||{};let state=mission.state;
  const fallback=data.delivery?5:data.workspace?3:data.plan?2:1;
  if(state==='awaiting_user'&&data.attempt_outcome?.status==='cycle_limit'&&data.attempt_outcome.plan_hash===data.plan_hash)return 4;
  if(PAUSED.includes(state))state=data.pause?.from;
  else if(state==='abandoned')state=data.abandoned?.previous_state;
  return STEP_BY_STATE[state]||fallback;
}
// Motivo da parada que merece o aviso de falha no HUD; '' quando não há.
export function missionFailure(mission,events=[]){
  if(!mission)return '';
  const data=mission.data||{},outcome=data.attempt_outcome;
  if(mission.state==='recovery_required')return 'A missão exige recuperação explícita.';
  if(mission.state!=='awaiting_user')return '';
  if(outcome?.status==='cycle_limit'&&outcome.plan_hash===data.plan_hash)return `Os ${outcome.cycle} ciclos permitidos acabaram sem passar na verificação.`;
  const error=[...events].reverse().find(event=>event.kind==='job_error'),restart=[...events].reverse().find(event=>['plan_proposed','resumed','planning_requested'].includes(event.kind));
  return error&&error.seq>(restart?.seq||0)?describeCode(error.data?.reason):'';
}
function hudOf(mission,failure){
  const state=mission?.state||'',data=mission?.data||{},step=missionStep(mission),approval=APPROVALS.includes(state),failed=!!failure||state==='abandoned';
  const suffix={paused:' · Pausada',pausing:' · Pausando',recovery_required:' · Recuperação necessária',abandoned:' · Encerrada',awaiting_user:failure?' · falhou':' · Aguardando você'}[state]||'';
  let action=null,alert=null;
  if(state==='awaiting_plan_approval'&&data.plan_hash)action={id:'view_approval',label:'Ver aprovação'};
  else if(state==='ready')action={id:'start',label:'Iniciar'};
  else if(['planning','running','verifying','correcting'].includes(state))action={id:'pause',label:'Pausar'};
  else if(state==='paused')action={id:'resume',label:'Retomar'};
  else if((approval||['delivery_approved','completed'].includes(state))&&data.delivery)action={id:'view_delivery',label:'Ver entrega'};
  if(approval)alert={approval:true,title:'Aprovação pendente.',text:state==='awaiting_plan_approval'?'O plano da Rainha aguarda a sua decisão.':'A entrega aguarda a sua decisão.',button:'Ver aprovação',target:'approval'};
  else if(failure)alert={approval:false,title:`Falha na etapa ${STEP_NAMES[step-1]}.`,text:failure,button:'Ver detalhes',target:'details'};
  return {step,text:mission?`Etapa ${step} de 7 · ${STEP_NAMES[step-1]}${suffix}`:'Nenhuma missão selecionada',
    title:mission?`${data.title||''} · ${stateLabel(state)} · ciclo ${mission.cycle}/${mission.cycle_limit}`:'',
    failed,paper:approval||(PAUSED.includes(state)&&!failed),complete:state==='completed',approval,action,alert};
}
// Status de cada tarefa do plano calculado só de jobs, para missões sem bees_summary.
function localTasks(data,jobs,cycle){
  const tasks=data.plan?.tasks||[],byId=new Map(tasks.map(task=>[task.id,task])),memo=new Map();
  const status=task=>{
    if(memo.has(task.id))return memo.get(task.id);
    memo.set(task.id,'waiting');
    const mine=jobs.filter(job=>job.data?.task_id===task.id&&job.data.cycle===cycle&&job.data.plan_hash===data.plan_hash&&(job.data.plan_attempt??null)===(data.plan_attempt??null));
    let value;
    if(mine.some(job=>RUNNING.has(job.state)))value='running';
    else if(mine.some(job=>job.state==='succeeded'))value='done';
    else if(mine.length&&FAILED.has(mine.at(-1).state))value='failed';
    else value=(task.depends_on||[]).every(dep=>byId.has(dep)&&status(byId.get(dep))==='done')?'pending':'waiting';
    memo.set(task.id,value);return value;
  };
  return tasks.map(task=>({id:task.id,description:task.description,bee_id:task.bee_id,depends_on:task.depends_on||[],files:task.files||[],status:status(task)}));
}
// Tudo que a colmeia real desenha: células, estados, rotas e HUD. Puro: só lê os dados recebidos.
export function deriveRealView({mission=null,jobs=[],events=[],team=[],summary=null,now=Date.now()/1000}={}){
  const data=mission?.data||{},state=mission?.state||'',cycle=mission?.cycle,step=missionStep(mission),failure=missionFailure(mission,events),hud=hudOf(mission,failure);
  const executing=step>=3&&state!=='abandoned',hasSummary=Array.isArray(summary)&&summary.length>0;
  const roster=hasSummary?summary.filter(bee=>bee.active!==false):team,sumById=new Map((hasSummary?summary:[]).map(bee=>[bee.id,bee]));
  const bees=[...roster.filter(bee=>bee.role==='queen'),...roster.filter(bee=>bee.role!=='queen')].slice(0,9);
  const summarized=hasSummary?summary.flatMap(bee=>(bee.tasks?.items||[]).map(item=>({...item,bee_id:bee.id,depends_on:item.depends_on||[]}))):[];
  const tasks=summarized.length?summarized:localTasks(data,jobs,cycle);
  const taskById=new Map(tasks.map(task=>[task.id,task]));
  const busy=bees.filter(bee=>bee.role!=='queen'&&(jobs.some(item=>item.bee_id===bee.id&&RUNNING.has(item.state))||sumById.get(bee.id)?.job?.state==='running')).length;
  const recent=beeId=>{const ids=new Set(jobs.filter(job=>job.bee_id===beeId).map(job=>job.id));return events.some(event=>event.kind==='job_finished'&&event.data?.state==='succeeded'&&ids.has(event.data.job_id)&&now-event.created_at<6);};
  const agents=[],phaseAgents={},phaseLinks={},connections=[],linkInfo={};
  bees.forEach((bee,index)=>{
    const queen=bee.role==='queen',slot=queen?'Q':slots[bees.slice(0,index).filter(item=>item.role!=='queen').length];if(!slot)return;
    const agent={id:queen?'rainha':`bee-${bee.id}`,sourceId:bee.id,kind:queen?'queen':bee.role==='subagent'?'sub':'added',slot,name:queen?'Rainha':bee.id,spec:`${bee.provider} · ${bee.model} · ${bee.effort}`,role:bee.role,temporary:!!bee.temporary};
    const sum=sumById.get(bee.id),mine=tasks.filter(task=>task.bee_id===bee.id),total=mine.length,done=mine.filter(task=>task.status==='done').length;
    const pending=mine.find(task=>['pending','waiting'].includes(task.status)),running=mine.find(task=>task.status==='running');
    const job=jobs.find(item=>item.bee_id===bee.id&&RUNNING.has(item.state))||(sum?.job?.state==='running'?{data:{process:sum.job.started}}:null);
    const last=jobs.filter(item=>item.bee_id===bee.id&&(item.data?.cycle===undefined||item.data.cycle===cycle)).at(-1);
    const failed=sum?.job?.state?sum.job.state==='failed':!!last&&FAILED.has(last.state),succeeded=sum?.job?.state==='completed'||last?.state==='succeeded';
    const started=!!job?.data?.process,progress=sum?.progress||null,verdictDone=!total&&bee.role==='verifier'&&succeeded&&executing;
    let status,link='idle';
    if(job){
      status=[queen?'coord':'working',started?'Executando':'Iniciando',started?(running?.description||'Sessão ativa.'):'Abrindo a sessão do provedor.'];
      if(!queen&&progress?.total>0){status[2]=progress.note||running?.description||'Sessão ativa.';status.push([Math.min(progress.done,progress.total),progress.total,'passos']);}
      else if(!queen&&total>0)status.push([done,total,'tarefas']);
    }else if(queen){
      status=state==='completed'?['done','Entrega concluída','A entrega foi incorporada ao projeto.']
        :busy&&['running','verifying','correcting'].includes(state)?['coord','Acompanhando o andamento',`${busy} ${busy===1?'abelha trabalhando':'abelhas trabalhando'}.`]
        :failure?['approval','Impedimento',failure]
        :APPROVALS.includes(state)?['approval','Aguardando sua decisão',state==='awaiting_plan_approval'?'A missão continua depois que você aprovar o plano.':'A missão continua depois que você aprovar a entrega.']
        :['clarifying','awaiting_user'].includes(state)?['approval','Aguardando você','Responda na gaveta Conversa.']
        :['idle','Disponível','Nenhuma sessão ativa.'];
    }else if(failed)status=['failed','Falhou','O último trabalho desta abelha falhou.'];
    else if(total&&done===total)status=['done','Entregue',`${total} ${total===1?'tarefa concluída':'tarefas concluídas'}.`];
    else if(verdictDone)status=['done','Veredito entregue','O verificador concluiu o ciclo atual.'];
    else if(executing&&pending){
      const needs=[...new Set((pending.depends_on||[]).map(id=>taskById.get(id)).filter(task=>task&&task.status!=='done').map(task=>task.bee_id))];
      status=pending.status==='waiting'?['waiting','Aguardando informação',`Depende de ${needs.join(', ')||'tarefas anteriores'}.`]:['waiting',state==='paused'?'Em pausa':'Tarefa na fila','Delegada pela Rainha; começa quando houver vaga.'];
    }else if(bee.role==='verifier'&&state==='verifying')status=['waiting','Tarefa na fila','A verificação começa quando houver vaga.'];
    else status=['idle','Disponível',total?`${total} ${total===1?'tarefa':'tarefas'} no plano.`:'Sem tarefa nesta missão.'];
    if(!queen){
      if(job)link='del';else if(failed)link='fail';
      else if((total&&done===total)||verdictDone)link=recent(bee.id)?'in':'ret';
      else if(executing&&pending)link=pending.status==='waiting'?'wait':'out';
      else if(bee.role==='verifier'&&state==='verifying')link='out';
      phaseLinks[`q-${agent.id}`]=link;
    }
    agent.info={description:bee.description||'',skills:bee.skills||{tags:[],instructions:''},tools:bee.tools||[],tasks:{total,done,current:running?.id||pending?.id||null,items:mine},progress,toolsUsed:sum?.tools_used||{},job:{state:job?'running':failed?'failed':succeeded?'completed':null,started}};
    agents.push(agent);phaseAgents[agent.id]=status;
  });
  const queenAgent=agents.find(agent=>agent.kind==='queen');
  if(queenAgent)agents.filter(agent=>agent!==queenAgent).forEach(agent=>{connections.push([`q-${agent.id}`,queenAgent.id,agent.id]);linkInfo[`q-${agent.id}`]=[`Rainha → ${agent.name}`,`A Rainha delega tarefas a ${agent.name} e recebe o resultado.`];});
  const byBee=new Map(agents.map(agent=>[agent.sourceId,agent])),pairs=new Map();
  tasks.forEach(task=>task.depends_on.forEach(dep=>{
    const before=taskById.get(dep),from=byBee.get(before?.bee_id),to=byBee.get(task.bee_id);if(!from||!to||from===to)return;
    const id=`dep-${from.id}-${to.id}`;if(!pairs.has(id))pairs.set(id,{from,to,deps:[],later:[]});
    pairs.get(id).deps.push(before);pairs.get(id).later.push(task);
  }));
  pairs.forEach(({from,to,deps,later},id)=>{
    connections.push([id,from.id,to.id]);linkInfo[id]=[`${from.name} → ${to.name}`,`Dependência: ${to.name} só avança com o que ${from.name} entregar.`];
    phaseLinks[id]=deps.some(task=>task.status==='failed')?'fail':!executing?'idle':deps.every(task=>task.status==='done')?(later.some(task=>task.status==='pending')?'flow':'done'):'wait';
  });
  return {agents,tasks,phase:{agents:phaseAgents,links:phaseLinks,step:hud.step,failed:hud.failed},connections,linkInfo,hud};
}

export class HiveMissionState {
  constructor(){
    this.hud=id();this.owner=id();this.listeners=new Set();this.active=false;this.reduced=false;
    this.drawers={left:true,right:true,bottom:false};this.selected=null;this.selectedLink=null;
    this.mission=null;this.jobs=[];this.events=[];this.eventMission='';this.eventSeq=0;this.roster=[];this.beesSummary=null;this.uiHandlers=new Set();this.catalog=null;this.catalogLoading=false;this.status=null;this.error='';this.errorDetail=null;
    this.missionId=sessionStorage.getItem('hivemind-mission')||'';
    this.ping();this.heartbeat=setInterval(()=>this.ping(),15000);
    window.addEventListener('pagehide',event=>{if(!event.persisted)navigator.sendBeacon('/hive-api/presence',new Blob([JSON.stringify({hud:this.hud,present:false})],{type:'application/json'}));});
  }
  subscribe(fn){this.listeners.add(fn);fn(this.snapshot());return()=>this.listeners.delete(fn);}
  emit(){const state=this.snapshot();this.listeners.forEach(fn=>fn(state));}
  async ping(){try{await hiveApi.post('/presence',{hud:this.hud,present:true});}catch{} }
  setReduced(value){this.reduced=!!value;this.emit();}
  setLifecycle(active){this.active=!!active;if(active){this.refresh();if(!this.timer)this.timer=setInterval(()=>this.refresh(),2500);}else if(this.timer){clearInterval(this.timer);this.timer=null;}this.emit();}
  setDocumentVisible(){this.emit();}
  selectAgent(agent){this.selected=this.selected===agent?null:agent;this.drawers.left=!!this.selected;this.emit();}
  selectLink(link){this.selectedLink=this.selectedLink===link?null:link;this.emit();}
  toggleDrawer(name){this.drawers[name]=!this.drawers[name];this.emit();}
  setScenario(){window.dispatchEvent(new Event('hivemind-demo-request'));}
  async refresh(){
    if(this.refreshing)await this.refreshing;
    let done;this.refreshing=new Promise(resolve=>{done=resolve;});
    try{
      this.status=await hiveApi.get('/status');
      const missions=await hiveApi.get('/missions');
      if(!this.missionId&&missions.length)this.missionId=missions[0].id;
      this.missions=missions;
      if(this.missionId){const wanted=this.missionId,path=`/missions/${encodeURIComponent(wanted)}`;if(this.eventMission!==wanted){this.eventMission=wanted;this.events=[];this.eventSeq=0;}
        let result=await hiveApi.get(`${path}?after=${this.eventSeq}`),fresh=result.events;
        for(let page=0;page<9&&result.events.length>=200;page++){result=await hiveApi.get(`${path}?after=${fresh.at(-1).seq}`);fresh=fresh.concat(result.events);}
        if(wanted===this.missionId){this.mission=result.mission;this.jobs=result.jobs;this.events=[...this.events,...fresh].slice(-500);if(fresh.length)this.eventSeq=fresh.at(-1).seq;this.roster=result.roster;this.beesSummary=Array.isArray(result.bees_summary)?result.bees_summary:null;}}
      return true;
    }catch(error){this.fail(error);return false;}
    finally{this.refreshing=null;done();this.emit();}
  }
  fail(error){this.error=error.message;this.errorDetail=error.detail||null;}
  clearError(){this.error='';this.errorDetail=null;}
  async loadCatalog(){this.catalogLoading=true;this.emit();try{this.catalog=await hiveApi.get('/catalog');this.clearError();}catch(error){this.fail(error);}this.catalogLoading=false;this.emit();}
  async saveTeam(bees){let saved=false;try{this.status.roster=await hiveApi.post('/settings',{kind:'roster',bees,key:id(),revision:this.status.roster.revision});this.clearError();saved=true;}catch(error){this.fail(error);}this.emit();return saved;}
  async saveLimit(value){try{this.status.settings=await hiveApi.post('/settings',{kind:'worker_limit',value,key:id(),revision:this.status.settings.revision});this.clearError();}catch(error){this.fail(error);}this.emit();}
  async create(title,source,message,limit){
    try{
      const queen=this.status?.roster?.bees?.find(bee=>bee.role==='queen');
      if(!queen)throw new Error('configure_a_equipe');
      const missionId=id();await hiveApi.post('/missions',{id:missionId,key:id(),title,cycle_limit:limit});
      this.missionId=missionId;this.mission=null;this.beesSummary=null;sessionStorage.setItem('hivemind-mission',missionId);if(!await this.refresh()||this.mission?.id!==missionId)throw new Error('missão_não_carregada');
      return await this.command('ask',{source,queen,message});
    }catch(error){this.fail(error);this.emit();return false;}
  }
  async command(action,extra={}){
    try{
      if(!this.mission)throw new Error('missão_ausente');
      const path=`/missions/${encodeURIComponent(this.mission.id)}`;
      await hiveApi.post(`${path}/lease`,{owner:this.owner});
      await hiveApi.post(`${path}/command`,{owner:this.owner,action,key:id(),revision:this.mission.revision,...extra});
      this.clearError();await this.refresh();return true;
    }catch(error){this.fail(error);this.emit();return false;}
  }
  selectMission(value){this.missionId=value;sessionStorage.setItem('hivemind-mission',value);this.mission=null;this.beesSummary=null;this.refresh();}
  hudAction(id){
    if(['start','pause','resume'].includes(id))return this.command(id);
    return this.requestUi({view_delivery:'delivery',view_approval:'approval'}[id]||'details');
  }
  onUiRequest(fn){this.uiHandlers.add(fn);return()=>this.uiHandlers.delete(fn);}
  requestUi(target){this.drawers[target==='chat'?'bottom':'right']=true;this.uiHandlers.forEach(fn=>fn(target));this.emit();}
  snapshot(){
    const record=this.mission,data=record?.data||{},team=data.plan?.bees||data.planning?.team||this.status?.roster?.bees||[];
    const view=deriveRealView({mission:record,jobs:this.jobs,events:this.events,team,summary:record?this.beesSummary:null}),agents=view.agents;
    return {real:true,mission:record,jobs:this.jobs,events:this.events,roster:this.roster,team,beesSummary:this.beesSummary,messages:data.planning?.messages||[],
      missions:this.missions||[],status:this.status,catalog:this.catalog,catalogLoading:this.catalogLoading,error:this.error,errorDetail:this.errorDetail,tasks:view.tasks,agents,added:agents.filter(bee=>bee.kind!=='queen'),
      phase:view.phase,connections:view.connections,linkInfo:view.linkInfo,hud:view.hud,phaseId:record?.state==='completed'?'done':'real',scenario:agents.length?'real':'empty',progress:0,adjusted:false,
      selected:this.selected,selectedLink:this.selectedLink,drawers:{...this.drawers},showSubs:agents.some(bee=>bee.kind==='sub'),form:false,
      reduced:this.reduced,manualPaused:record?.state==='paused',animationsPaused:!this.active||document.hidden||this.reduced};
  }
}
