import {el,label,btn,statusIcon,trailSample,hashNode,tabs,taskKind,drawerHead} from './live-ui.js';
import {STATE_INFO} from './demo-data.js';
import {describeCode,describeError,stateBadge,stateSentence} from './messages.js';
import {criteriaList,deliveryStats,deliveryView} from './live-delivery.js';
import {linkStatus} from './hive.js';

const PAUSABLE=['planning','running','verifying','correcting'];
const LEGEND=['out','flow','del','wait','done','idle','fail'];
const MISSION_TABS=[['plano','Plano'],['resp','Responsabilidades'],['conex','Conexões'],['entrega','Entrega']];

// Última interrupção de trabalho que ainda vale (nenhum plano novo nem retomada depois dela).
export function interruption(mission,events){
  const error=[...events].reverse().find(event=>event.kind==='job_error'),restart=[...events].reverse().find(event=>['plan_proposed','resumed','planning_requested'].includes(event.kind));
  if(!mission||!error||error.seq<=(restart?.seq||0))return '';
  const reason=describeCode(error.data?.reason);
  return mission.state==='awaiting_user'?`O trabalho parou. Motivo: ${reason} Para seguir, converse com a Rainha na gaveta Conversa ou peça um novo plano.`:`Última interrupção: ${reason}`;
}
export function cycleLimitNotice(mission){
  const data=mission?.data||{},outcome=data.attempt_outcome;
  return mission?.state==='awaiting_user'&&outcome?.status==='cycle_limit'&&outcome.plan_hash===data.plan_hash?`A missão usou os ${outcome.cycle} ciclos permitidos sem passar na verificação independente (veja a aba Entrega). Para seguir, aumente o máximo de ciclos desta missão e converse com a Rainha na gaveta Conversa para ela propor um plano ajustado.`:'';
}
export function reconcileText(reconciliation){
  const conflicts=reconciliation?.conflicts||[];
  return conflicts.length?`A origem mudou nestes arquivos: ${conflicts.join(', ')}. As versões foram preservadas em área isolada; revise e solicite um novo plano consciente.`:'A origem mudou. Criar nova base e candidato isolados, reaplicar mudanças não conflitantes e reverificar.';
}
export const planSummary=plan=>{
  if(!plan)return '';
  const temporary=(plan.bees||[]).filter(bee=>bee.temporary).length;
  return `${(plan.tasks||[]).length} tarefas · ${(plan.bees||[]).length} abelhas${temporary?` (${temporary} temporárias)`:''} · ${(plan.acceptance||[]).length} critérios de aceite`;
};
const card=({icon='approval',title,badge='',text=[],actions=[]})=>{
  const box=el('div','hm-approval'),line=el('div','hm-approval-title');
  line.append(statusIcon(icon),el('span','',title));if(badge)line.append(el('span','hm-approval-badge',badge));box.append(line);
  text.filter(Boolean).forEach(item=>box.append(typeof item==='string'?el('p','',item):item));
  if(actions.length){const row=el('div','hm-foot-actions');row.append(...actions);box.append(row);}
  return box;
};

// Gaveta Missão do modo real, com os componentes da gaveta "Missão" da demonstração.
export function createLiveMission(drawer,live){
  const head=missionHead(live);
  const scroll=el('div','hm-mission-scroll'),picker=el('div','hm-mission-picker'),select=el('select','hm-select'),dynamic=el('div','hm-mission-dynamic');
  let last=null,tab='plano',creating=false,confirmAbandon='',pickerSignature='';
  // Cartão de criar missão (persistente: os campos não se perdem com o polling)
  const create=el('section','hm-approvals hm-create-card'),form=el('form','hm-worker-form');
  const fields=el('div','hm-form-fields stack'),inputs={title:el('input'),source:el('input'),objective:el('textarea'),cycles:el('input')},errors={};
  inputs.title.placeholder='Nome da missão';inputs.source.placeholder='Caminho do projeto autorizado';inputs.objective.placeholder='Descreva o objetivo e os critérios esperados';
  inputs.cycles.type='number';inputs.cycles.min='1';inputs.cycles.max='20';inputs.cycles.value='3';
  [['title','Nome'],['source','Projeto'],['objective','Objetivo'],['cycles','Máximo de ciclos']].forEach(([key,text])=>{
    const box=el('label'),error=el('div','hm-form-error');error.setAttribute('role','alert');error.hidden=true;errors[key]=error;box.append(label(text),inputs[key],error);fields.append(box);
  });
  const submit=btn('Planejar com a Rainha',null,'hm-dark'),cancel=btn('Cancelar',()=>{creating=false;render(last);},'hm-outline'),createNotice=el('p','hm-foot-note'),actions=el('div','hm-foot-actions');
  submit.type='submit';actions.append(submit,cancel);
  form.append(el('div','hm-worker-title','Nova missão'),el('div','hm-worker-copy','A Rainha lê o objetivo, pergunta o que faltar e propõe um plano para a sua aprovação.'),fields,actions,createNotice);
  create.append(label('Criar missão'),form);
  form.addEventListener('submit',async event=>{
    event.preventDefault();
    const problems={title:inputs.title.value.trim()?'':'Informe o nome da missão.',source:inputs.source.value.trim()?'':'Informe o caminho do projeto autorizado.',objective:inputs.objective.value.trim()?'':'Descreva o objetivo da missão.',
      cycles:Number.isInteger(Number(inputs.cycles.value))&&Number(inputs.cycles.value)>=1&&Number(inputs.cycles.value)<=20?'':'Use um número de 1 a 20.'};
    Object.entries(problems).forEach(([key,text])=>{errors[key].textContent=text;errors[key].hidden=!text;});
    if(Object.values(problems).some(Boolean))return;
    if(await live.create(inputs.title.value.trim(),inputs.source.value.trim(),inputs.objective.value,Number(inputs.cycles.value))){
      inputs.title.value='';inputs.source.value='';inputs.objective.value='';inputs.cycles.value='3';creating=false;if(last)render(last);
    }
  });
  const newMission=btn('Nova missão',()=>{creating=true;render(last);},'hm-outline');
  select.addEventListener('change',()=>{if(select.value)live.selectMission(select.value);});
  picker.append(select,newMission);
  scroll.append(picker,create,dynamic);drawer.append(head,scroll);
  head.limitSave.addEventListener('click',()=>live.command('cycle_limit',{limit:Number(head.limitInput.value)}));

  function progressSection(state){
    const mission=state.mission,hud=state.hud,section=el('section','hm-mission-progress'),strip=el('div','hm-step-strip');
    const tasks=state.tasks||[],finished=tasks.filter(task=>task.status==='done').length;
    for(let index=1;index<=7;index++){
      const segment=el('i'),current=!!mission&&!hud.complete&&hud.step===index,classes=[];
      if(mission&&(hud.step>index||hud.complete))classes.push('done');
      if(current){classes.push('current');if(hud.paper)classes.push('paper');if(hud.failed)classes.push('failed');}
      segment.className=classes.join(' ');
      if(current&&!hud.paper&&!hud.failed&&index===3&&tasks.length){const share=Math.round(finished/tasks.length*100);segment.style.background=`linear-gradient(to right,#000 ${share}%,#CFC6B4 ${share}%)`;}
      strip.append(segment);
    }
    section.append(label('Andamento'),strip);
    const phase=el('p','hm-phase');
    phase.append(el('strong','hm-phase-step',mission?`${hud.text}.`:'Sem missão.'),document.createTextNode(mission?` ${stateSentence(mission.state)}`:' Crie uma missão para começar.'));section.append(phase);
    const controls=el('div','hm-controls');
    if(mission){
      if(hud.approval){const wait=el('span','hm-approval-wait');wait.append(statusIcon('approval'),el('span','','Aguardando sua decisão'));controls.append(wait);}
      if(mission.state==='ready')controls.append(btn('Iniciar',()=>live.command('start'),'hm-dark'));
      if(PAUSABLE.includes(mission.state))controls.append(btn('Pausar',()=>live.command('pause'),'hm-dark'));
      if(mission.state==='paused')controls.append(btn('Retomar',()=>live.command('resume'),'hm-dark'));
      if(mission.data.delivery)controls.append(btn('Ver entrega',()=>live.requestUi('delivery'),'hm-outline'));
    }
    section.append(controls);return section;
  }

  function approvalsSection(state){
    const mission=state.mission,data=mission.data,section=el('section','hm-approvals'),cards=[],recovering=mission.state==='recovery_required',abandoned=mission.state==='abandoned';
    if(confirmAbandon!==mission.id||!recovering)confirmAbandon='';
    const view=deliveryView(mission);
    if(mission.state==='awaiting_plan_approval'&&data.plan)cards.push(card({title:'O plano da Rainha aguarda você',badge:'Plano',
      text:[data.plan.objective,planSummary(data.plan),hashNode(data.plan_hash)],
      actions:[btn('Aprovar',()=>live.command('approve_plan',{plan_hash:data.plan_hash}),'hm-dark'),btn('Solicitar ajuste',()=>live.requestUi('chat'),'hm-outline')]}));
    if(mission.state==='awaiting_delivery_approval'&&view)cards.push(card({title:'A entrega verificada aguarda você',badge:'Entrega',
      text:[`${view.changes.length} ${view.changes.length===1?'arquivo alterado':'arquivos alterados'} · ${view.passed} de ${view.criteria.length} critérios aprovados${view.outside?` · ${view.outside} fora do plano`:''}`,hashNode(view.hash,'Versão da entrega ')],
      actions:[btn('Aprovar',()=>live.command('approve_delivery',{candidate_hash:data.candidate_hash,delivery_hash:data.delivery_hash}),'hm-dark'),btn('Ver entrega',()=>live.requestUi('delivery'),'hm-outline')]}));
    if(recovering){
      const buttons=[];
      if(data.delivery_hash)buttons.push(btn('Recuperar entrega',()=>live.command('recover_delivery'),'hm-dark'));
      if(confirmAbandon===mission.id)buttons.push(btn('Confirmar encerramento',()=>{confirmAbandon='';live.command('abandon');},'hm-dark'),btn('Cancelar',()=>{confirmAbandon='';render(last);},'hm-outline'));
      else buttons.push(btn('Encerrar missão',()=>{confirmAbandon=mission.id;render(last);},'hm-outline'));
      cards.push(card({icon:'failed',title:'Recuperação necessária',badge:'Atenção',
        text:['A missão exige recuperação explícita antes de continuar. Versões ambíguas são preservadas.',state.error==='delivery_recovery_required'?describeCode(state.error):'',confirmAbandon===mission.id?'Encerrar esta missão? O histórico será preservado e nenhum arquivo do projeto será alterado.':''],actions:buttons}));
    }
    if(data.reconciliation_required&&!recovering&&!abandoned)cards.push(card({title:'A origem mudou',badge:'Reconciliação',text:[reconcileText(data.reconciliation_required)],actions:[btn('Reconciliar origem em área isolada',()=>live.command('reconcile_source'),'hm-dark')]}));
    const interrupted=interruption(mission,state.events);
    if(interrupted)cards.push(card({icon:'failed',title:'Trabalho interrompido',text:[interrupted]}));
    const limit=cycleLimitNotice(mission);
    if(limit)cards.push(card({icon:'failed',title:'Limite de ciclos',text:[limit]}));
    section.append(label('Aprovações'));
    cards.forEach(item=>section.append(item));
    if(abandoned){const idle=el('p','hm-approval-idle');idle.append(statusIcon('idle'),el('span','','Missão encerrada por você. O histórico foi preservado e a origem não foi alterada.'));section.append(idle);}
    else if(!cards.length){const idle=el('p','hm-approval-idle');idle.append(statusIcon(mission.state==='completed'?'done':'idle'),el('span','',mission.state==='completed'?'Tudo aprovado e incorporado.':'Nenhuma aprovação pendente.'));section.append(idle);}
    if(state.error)section.append(el('p','hm-form-error',`Não foi possível concluir: ${describeError(state.error,state.errorDetail)}`));
    return section;
  }

  function tabBody(state){
    const mission=state.mission,data=mission.data,body=el('div','hm-mission-body'),names=new Map(state.agents.map(agent=>[agent.id,agent.name]));
    if(tab==='plano'){
      const tasks=state.tasks||[];
      if(!tasks.length)body.append(el('p','','O plano aparece aqui quando a Rainha propuser tarefas.'));
      tasks.forEach((task,index)=>{const row=el('div','hm-plan-row');row.append(statusIcon(taskKind[task.status]||'idle'),el('strong','',String(index+1)),el('span','',task.description),el('small','',task.bee_id));body.append(row);});
      const verdict=new Map(Object.entries(data.verdict?.criteria||{})),criteria=(data.plan?.acceptance||[]).map(item=>({id:item.id,description:item.description,status:verdict.get(item.id)||'pending'}));
      if(criteria.length){const group=el('div','hm-mission-group');group.append(label('Critérios de aceite'),...criteriaList(criteria));body.append(group);}
      if(data.plan_hash){const version=el('p','hm-mission-version');version.append(hashNode(data.plan_hash,'Versão do plano '));body.append(version);}
    }else if(tab==='resp'){
      const workers=state.agents.filter(agent=>agent.kind!=='queen');
      if(!workers.length)body.append(el('p','','Nenhuma abelha neste plano ainda.'));
      workers.forEach(agent=>{
        const item=btn('',()=>live.selectAgent(agent.id),'hm-duty'),copy=el('span','hm-duty-copy'),ending=el('span','hm-duty-status'),status=state.phase.agents[agent.id]||['idle','Disponível'];
        copy.append(el('span','hm-duty-name',agent.name),el('span','hm-duty-text',agent.info?.tasks.items[0]?.description||'Sem tarefa nesta missão.'));ending.append(statusIcon(status[0]),el('span','',status[1]));item.append(copy,ending);body.append(item);
      });
    }else if(tab==='conex'){
      body.append(el('p','hm-connections-intro','As trilhas seguem as bordas das células. Clique em uma trilha na colmeia ou na lista para ver o que ela representa.'));
      const legend=el('div','hm-connection-legend');
      LEGEND.forEach(kind=>{const row=el('div','hm-legend-row'),copy=el('span'),info=STATE_INFO[kind];copy.append(el('strong','',info[0]),document.createTextNode(` · ${info[1]}`));row.append(trailSample(kind),copy);legend.append(row);});
      const current=label('Conexões agora'),rows=el('div','hm-connection-list');current.classList.add('hm-connections-current');
      (state.connections||[]).forEach(([id,from,to])=>{
        const status=linkStatus(id,state),reverse=['in','ret'].includes(status),item=btn('',()=>live.selectLink(id),'hm-connection-row'),copy=el('span');
        item.classList.toggle('selected',state.selectedLink===id);
        copy.append(el('strong','',`${names.get(reverse?to:from)||'—'} → ${names.get(reverse?from:to)||'—'}`),el('small','',STATE_INFO[status]?.[0]||'Sem atividade'));item.append(trailSample(status),copy);item.title=state.linkInfo?.[id]?.[1]||'';rows.append(item);
      });
      body.append(legend,current,rows);
    }else{
      const view=deliveryView(mission);
      if(data.verdict){body.append(el('h3','','Verificação independente'),el('p','',`${data.verdict.passed?'Aprovada':'Não aprovada'} no ciclo ${data.verdict.cycle}.`),...criteriaList(deliveryCriteria(data)),el('p','',`Evidência: ${data.verdict.evidence||'não informada'}`));}
      if(view){
        const version=el('p','hm-mission-version');version.append(hashNode(view.hash,'Versão da entrega '));
        body.append(el('h3','','Alterações para revisão'),deliveryStats(view),version);
        view.changes.forEach(item=>{const row=el('div','hm-plan-row');row.append(statusIcon(item.inPlan?'done':'failed'),el('strong','',item.task),el('span','',item.path),el('small','',item.inPlan?'No plano':'Fora do plano'));body.append(row);});
        const buttons=el('div','hm-foot-actions');buttons.append(btn('Ver entrega',()=>live.requestUi('delivery'),'hm-dark'));
        if(mission.state==='delivery_approved')buttons.append(btn('Incorporar entrega aprovada',()=>live.command('apply',{delivery_hash:data.delivery_hash}),'hm-dark'));
        if(mission.state==='delivery_approved')body.append(el('p','hm-foot-note','A origem e o journal precisam estar no mesmo volume.'));
        body.append(buttons);
      }else if(!data.verdict)body.append(el('p','','A entrega aparece aqui quando a verificação independente terminar.'));
    }
    return body;
  }
  const deliveryCriteria=data=>{const described=new Map((data.plan?.acceptance||[]).map(item=>[item.id,item.description]));return Object.entries(data.verdict?.criteria||{}).map(([id,status])=>({id,status,description:described.get(id)||id}));};

  function render(state){
    last=state;
    const mission=state.mission,data=mission?.data||{},missions=state.missions||[];
    head.badge.textContent=mission?stateBadge(mission.state):'Sem missão';
    head.sub.textContent=mission?data.title:'Nenhuma missão selecionada';head.sub.title=mission?data.title:'';
    const objective=data.plan?.objective||data.planning?.messages?.find(message=>message.role==='user')?.text||'';
    head.objective.textContent=objective;head.objective.hidden=!objective;head.objective.title=objective;
    const project=data.plan?.project?.path||data.planning?.source||'';
    head.limits.textContent=mission?`Projeto: ${project||'ainda não definido'} · Ciclo ${mission.cycle} de ${mission.cycle_limit}`:'';head.limits.title=project;head.limits.hidden=!mission;
    head.limitEdit.hidden=!mission||mission.state==='abandoned';
    if(mission){head.limitInput.min=String(mission.cycle);if(document.activeElement!==head.limitInput)head.limitInput.value=String(mission.cycle_limit);}
    const signature=JSON.stringify(missions.map(item=>[item.id,item.data.title]));
    if(signature!==pickerSignature){pickerSignature=signature;select.replaceChildren(...[['','Selecione uma missão'],...missions.map(item=>[item.id,item.data.title])].map(([value,text])=>{const option=el('option','',text);option.value=value;return option;}));}
    select.value=mission?.id||'';picker.hidden=!missions.length;
    const roster=state.status?.roster,incomplete=roster?.incomplete||[];
    create.hidden=!(creating||!mission);cancel.hidden=!mission;
    submit.disabled=!roster?.bees?.length||incomplete.length>0;
    createNotice.textContent=!roster?.bees?.length?'Configure a equipe (Rainha, operária e verificador) na gaveta Agentes antes de planejar.':incomplete.length?`Complete o cadastro de ${incomplete.map(item=>item.id).join(', ')} na gaveta Agentes antes de planejar.`:'';
    dynamic.hidden=creating||!mission;
    if(!mission||creating){dynamic.replaceChildren();return;}
    const tabsNode=el('section','hm-mission-tabs');
    tabsNode.append(tabs(MISSION_TABS,tab,id=>{tab=id;render(last);}),tabBody(state));
    dynamic.replaceChildren(progressSection(state),approvalsSection(state),tabsNode);
  }
  return {render};
}

function missionHead(live){
  const node=drawerHead('Missão',()=>live.toggleDrawer('right'),{badge:'Sem missão',subtitle:'Nenhuma missão selecionada'});
  const edit=el('div','hm-limit-edit'),input=el('input'),save=btn('Salvar',null,'hm-outline');
  input.type='number';input.min='1';input.max='20';input.setAttribute('aria-label','Máximo de ciclos desta missão');save.title='Salvar o máximo de ciclos desta missão';save.setAttribute('aria-label','Salvar o máximo de ciclos desta missão');
  edit.append(el('span','','Máximo de ciclos'),input,save);edit.hidden=true;
  Object.assign(node,{objective:el('p','hm-head-limit'),limits:el('p','hm-head-limit hm-head-path'),limitEdit:edit,limitInput:input,limitSave:save});
  node.append(node.objective,node.limits,edit);
  return node;
}
