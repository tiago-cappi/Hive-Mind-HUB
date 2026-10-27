import {el,svg,label,btn,statusIcon,trailSample,drawerHead,tabs,segmentBar,taskKind} from './live-ui.js';
import {STATE_INFO} from './demo-data.js';
import {createBee} from './bee-animation/bee.js';
import {linkStatus} from './hive.js';
import {describeError,fieldName} from './messages.js';

const roleNames={queen:'Rainha',worker:'Operária',subagent:'Subagente',verifier:'Verificador independente'};
const TOOLS={read:['Ler arquivos do projeto','Somente leitura'],patch:['Alterar arquivos do plano','Leitura e escrita'],checks:['Rodar verificações aprovadas','Execução restrita']};
const FIELDS=['id','description','skills','tools','provider','model','effort'];
const shortStatus=kind=>({working:'Trabalhando',coord:'Coordenando',waiting:'Aguardando',approval:'Aguarda você',done:'Entregue',failed:'Falhou',idle:'Disponível'})[kind]||'Disponível';

export function validateTeam(rows){
  const seen=new Set();
  for(const row of rows){
    const name=`${roleNames[row.role]||row.role} "${row.id||''}"`;
    if(!/^[A-Za-z0-9_.-]{1,100}$/.test(row.id||''))return `${name}: use um identificador com letras, números, ponto, hífen ou sublinhado.`;
    if(seen.has(row.id))return `Identificador repetido: ${row.id}.`;
    seen.add(row.id);
    if(!row.model)return `${name}: selecione um modelo.`;
    if(!row.effort)return `${name}: selecione o esforço.`;
  }
  const count=role=>rows.filter(row=>row.role===role).length;
  if(count('queen')!==1)return 'A equipe precisa de exatamente uma Rainha.';
  if(count('verifier')!==1)return 'A equipe precisa de exatamente um Verificador independente.';
  if(!count('worker'))return 'A equipe precisa de ao menos uma Operária.';
  return '';
}
export const parseTags=text=>[...new Set(String(text||'').split(/[,\n]/).map(item=>item.trim()).filter(Boolean))];
// Validação por campo do formulário de abelha; devolve {campo: mensagem}.
export function validateBeeForm(values,{role,rows,editing}){
  const errors={};
  if(!/^[A-Za-z0-9_.-]{1,100}$/.test(values.id||''))errors.id='Use letras, números, ponto, hífen ou sublinhado (até 100 caracteres).';
  else if(!editing&&rows.some(row=>row.id===values.id))errors.id='Já existe uma abelha com este identificador.';
  const description=(values.description||'').trim();
  if(!description)errors.description='Descreva o que esta abelha faz.';else if(description.length>2000)errors.description='Use no máximo 2000 caracteres.';
  const tags=values.tags||[];
  if(tags.length>20)errors.skills='Use no máximo 20 skills.';else if(tags.some(tag=>tag.length>60))errors.skills='Cada skill pode ter até 60 caracteres.';
  else if((values.instructions||'').length>4000)errors.skills='As instruções aceitam até 4000 caracteres.';
  if(!values.tools?.length)errors.tools='Autorize ao menos uma ferramenta.';
  else if(values.tools.includes('patch')&&['queen','verifier'].includes(role))errors.tools=`${roleNames[role]} não pode alterar arquivos.`;
  if(!values.provider)errors.provider='Escolha o provedor.';
  if(!values.model)errors.model='Escolha o modelo.';
  if(!values.effort)errors.effort='Escolha o esforço.';
  return errors;
}
const modelsOf=(catalog,provider)=>catalog?.[provider]?.models||[];
const optionNode=(value,text)=>{const node=el('option','',text);node.value=value;return node;};
function fillSelect(node,values,current,empty){
  const list=values.includes(current)||!current?values:[current,...values];
  node.replaceChildren(optionNode('',empty),...list.map(value=>optionNode(value,value)));node.value=current||'';
}
const rowIcon=(agent,kind,paused,reduced)=>{
  const icon=el('span',`hm-row-icon ${agent.kind}`),frame=svg('svg',{viewBox:'0 0 34 39.26',width:'34',height:'39.26','aria-hidden':'true'});
  const attrs={points:'17,0.8 33.2,10.2 33.2,29.1 17,38.46 0.8,29.1 0.8,10.2',fill:agent.kind==='queen'?'#000000':'none',stroke:'#000000','stroke-width':'1.5'};
  if(agent.kind==='sub'||agent.temporary)attrs['stroke-dasharray']='3 2.5';
  frame.append(svg('polygon',attrs));icon.append(frame,createBee({queen:agent.kind==='queen',state:kind,size:26,paused,reduced}));return icon;
};

// Gaveta Agentes do modo real: lista, detalhe com abas e formulário de cadastro.
export function createLiveTeam(drawer,live){
  const headHost=el('div','hm-team-head'),scroll=el('div','hm-drawer-scroll'),foot=el('div','hm-drawer-foot');
  let last=null,tab='geral',form=null,edits={},draft=[];
  const limitInput=el('input');limitInput.type='number';limitInput.min='1';limitInput.max='20';limitInput.value='2';
  drawer.append(headHost,scroll,foot);

  const savedOf=state=>state.status?.roster?.bees||[],rosterOf=state=>savedOf(state).length?savedOf(state):draft;
  const incompleteOf=(state,id)=>(state.status?.roster?.incomplete||[]).find(item=>item.id===id)?.missing;
  const permanent=(state,agent)=>!agent.temporary&&rosterOf(state).some(bee=>bee.id===agent.sourceId);
  const fail=state=>state.error?el('p','hm-form-error',`Não foi possível concluir: ${describeError(state.error,state.errorDetail)}`):null;

  function headNode(state,visible){
    const title=drawerHead('Agentes',()=>live.toggleDrawer('left'),{subtitle:'',chat:false});
    const roles=role=>visible.filter(agent=>agent.role===role).length,temporary=visible.filter(agent=>agent.temporary).length;
    title.sub.textContent=visible.length?[roles('queen')?`${roles('queen')} rainha`:'',`${roles('worker')} operárias`,roles('subagent')?`${roles('subagent')} subagentes`:'',roles('verifier')?'1 verificador':'',temporary?`${temporary} temporárias`:''].filter(Boolean).join(', '):'Nenhum agente na equipe ainda.';
    if(visible.length)title.append(title.sub);
    const counters=el('div','hm-counters'),kindOf=agent=>(state.phase.agents[agent.id]||['idle'])[0];
    const count=kind=>visible.filter(agent=>{const value=kindOf(agent);return kind==='working'?['working','coord'].includes(value):kind==='waiting'?['waiting','approval'].includes(value):value===kind;}).length;
    if(visible.length){
      [['working','trabalhando'],['waiting','aguardando'],['idle','disponíveis'],['done','entregues']].forEach(([kind,text])=>{const item=el('span');item.append(statusIcon(kind),document.createTextNode(`${count(kind)} ${text}`));counters.append(item);});
      if(count('failed')){const item=el('span');item.append(statusIcon('failed'),document.createTextNode(`${count('failed')} com falha`));counters.append(item);}
      const incomplete=state.status?.roster?.incomplete?.length||0;
      if(incomplete){const item=el('span');item.append(statusIcon('approval'),document.createTextNode(`${incomplete} ${incomplete===1?'incompleta':'incompletas'}`));counters.append(item);}
    }
    title.append(counters);return title;
  }

  function relationsOf(state,agent){
    const names=new Map(state.agents.map(item=>[item.id,item.name])),from=[],to=[];
    (state.connections||[]).forEach(([id,source,target])=>{if(id.startsWith('dep-')){if(target===agent.id)from.push(source);if(source===agent.id)to.push(target);}});
    return {from:from.map(id=>names.get(id)||id),to:to.map(id=>names.get(id)||id),fromIds:from,toIds:to};
  }
  function connectionRows(state,agent){
    const names=new Map(state.agents.map(item=>[item.id,item.name])),own=(state.connections||[]).filter(([,from,to])=>from===agent.id||to===agent.id);
    if(!own.length)return null;
    const group=el('div','hm-detail-group'),rows=el('div','hm-connection-list');
    own.forEach(([id,from,to])=>{
      const status=linkStatus(id,state),reverse=['in','ret'].includes(status),item=btn('',()=>live.selectLink(id),'hm-connection-row'),copy=el('span');
      item.classList.toggle('selected',state.selectedLink===id);copy.append(el('strong','',`${names.get(reverse?to:from)}  →  ${names.get(reverse?from:to)}`),el('small','',STATE_INFO[status]?.[0]||'Sem atividade'));item.append(trailSample(status),copy);rows.append(item);
    });
    group.append(label('Conexões na colmeia'),rows);return group;
  }
  function quickEdit(state,agent){
    const bee=rosterOf(state).find(item=>item.id===agent.sourceId),box=el('div','hm-quick-edit'),catalog=state.catalog;
    if(incompleteOf(state,bee.id)){box.append(el('p','hm-empty-detail','Complete o cadastro em “Editar agente” antes de trocar provedor, modelo ou esforço.'));return box;}
    const edit=edits[bee.id]||{provider:bee.provider,model:bee.model,effort:bee.effort},provider=el('select'),model=el('select'),effort=el('select');
    const update=patch=>{edits[bee.id]={...edit,...patch};render(last);};
    fillSelect(provider,['codex','claude'],edit.provider,'Provedor');fillSelect(model,modelsOf(catalog,edit.provider).map(item=>item.name),edit.model,'Modelo');
    fillSelect(effort,modelsOf(catalog,edit.provider).find(item=>item.name===edit.model)?.efforts||[],edit.effort,'Esforço');
    [provider,model,effort].forEach(node=>{node.disabled=!catalog;});
    provider.addEventListener('change',()=>update({provider:provider.value,model:'',effort:''}));model.addEventListener('change',()=>update({model:model.value,effort:''}));effort.addEventListener('change',()=>update({effort:effort.value}));
    const changed=edit.provider!==bee.provider||edit.model!==bee.model||edit.effort!==bee.effort,save=btn('Salvar',async()=>{if(await live.saveTeam(rosterOf(last).map(item=>item.id===bee.id?{...item,...edit}:{...item}))){delete edits[bee.id];render(last);}},'hm-dark');
    save.disabled=!changed||!edit.model||!edit.effort;
    const line=el('div','hm-quick-row');line.append(provider,model,effort);box.append(line,save);
    if(!catalog)box.append(el('p','hm-empty-detail','Consulte os modelos para trocar o modelo ou o esforço.'));
    return box;
  }

  function details(state,agent){
    const box=el('div','hm-agent-detail'),queen=agent.kind==='queen',info=agent.info,status=state.phase.agents[agent.id]||['idle','Disponível',''];
    const defs=queen?[['geral','Visão geral'],['tarefas','Tarefas'],['relacoes','Relações']]:[['geral','Visão geral'],['tarefas','Tarefas'],['skills','Skills'],['ferramentas','Ferramentas'],['relacoes','Relações']];
    const active=defs.some(([id])=>id===tab)?tab:'geral',body=el('div','hm-tab-body');
    const group=(title,...children)=>{const node=el('div','hm-detail-group');node.append(label(title),...children);return node;};
    box.append(tabs(defs,active,id=>{tab=id;render(last);}));
    if(active==='geral'){
      const kindName=`${roleNames[agent.role]||'Operária'}${agent.temporary?' temporária':''}`;
      body.append(group(kindName,el('p','',agent.spec)));
      if(permanent(state,agent))body.append(quickEdit(state,agent));
      const missing=incompleteOf(state,agent.sourceId);
      if(missing)body.append(group('Cadastro',el('p','hm-form-error',`Incompleto: falta ${missing.map(fieldName).join(', ')}. Use “Editar agente” para completar.`)));
      const stateLine=el('div','hm-detail-state'),stateGroup=group('Estado',stateLine,el('p','hm-detail-copy',status[2]||''));
      stateLine.append(statusIcon(status[0]),el('strong','',status[1]));
      if(status[3])stateGroup.append(segmentBar(status[3][0],status[3][1]));
      body.append(stateGroup);
      body.append(group('Descrição',el('p','',info.description||'Sem descrição cadastrada.')));
      if(queen){
        const objective=state.mission?.data?.plan?.objective||'';
        const goal=group('Objetivo geral',el('p','',objective||'A missão ainda não tem um plano.'));
        if(state.mission?.data?.delivery)goal.append(btn('Ver entrega',()=>live.requestUi('delivery'),'hm-dark'));
        body.append(goal);
      }
    }else if(active==='tarefas'){
      const items=queen?state.tasks||[]:info.tasks.items;
      if(!queen){const current=info.tasks.items.find(task=>task.status==='running')||info.tasks.items.find(task=>task.id===info.tasks.current);body.append(group('Tarefa atual',el('p','',current?.description||'Sem tarefa no momento.')));}
      const list=el('div','hm-plan-list');
      items.forEach((task,index)=>{const row=el('div','hm-plan-row');row.append(statusIcon(taskKind[task.status]||'idle'),el('strong','',String(index+1)),el('span','',task.description),el('small','',task.bee_id));list.append(row);});
      body.append(group(queen?'Plano':'Tarefas na missão',items.length?list:el('p','hm-empty-detail','Nenhuma tarefa neste plano.')));
    }else if(active==='skills'){
      const tags=el('div','hm-tags'),list=info.skills?.tags||[];list.forEach(item=>tags.append(el('span','',item)));
      body.append(group('Capacidades',list.length?tags:el('p','hm-empty-detail','Nenhuma capacidade configurada.')));
      if(info.skills?.instructions)body.append(group('Instruções',el('p','',info.skills.instructions)));
    }else if(active==='ferramentas'){
      const tools=group('Ferramentas');
      if(!info.tools.length)tools.append(el('p','hm-empty-detail','Nenhuma ferramenta autorizada.'));
      else{
        const rows=el('div','hm-tools');
        [...info.tools,'progress'].forEach(name=>{
          const row=el('div','hm-tool'),icon=el('span','hm-tool-icon'),mark=svg('svg',{width:10,height:10,viewBox:'0 0 10 10','aria-hidden':'true'}),used=info.toolsUsed?.[name];
          mark.append(svg('path',{d:'M1.5 2.5 H8.5 M1.5 5 H8.5 M1.5 7.5 H5.5',stroke:'#F1EDE4','stroke-width':1.4}));icon.append(mark);
          const [title,access]=name==='progress'?['Informar progresso','Automática']:TOOLS[name]||[name,''];
          row.append(icon,el('span','',title),el('span',`hm-tool-access ${name==='patch'?'write':''}`,`${access}${used?` · ${used} ${used===1?'uso':'usos'}`:''}`));rows.append(row);
        });
        tools.append(rows);
      }
      body.append(tools);
    }else{
      const relation=relationsOf(state,agent);
      if(!queen){
        const relations=el('div','hm-relations'),grid=el('div','hm-rel-grid'),from=btn('',()=>relation.fromIds[0]&&live.selectAgent(relation.fromIds[0]),''),to=btn('',()=>relation.toIds[0]&&live.selectAgent(relation.toIds[0]),'');
        from.append(label('Recebe de'),el('strong','',relation.from.join(' e ')||'Rainha'));to.append(label('Entrega para'),el('strong','',relation.to.join(' e ')||'Rainha'));
        const arrow=svg('svg',{width:16,height:10,viewBox:'0 0 16 10','aria-hidden':'true'});arrow.append(svg('line',{x1:0,y1:5,x2:10,y2:5,stroke:'#000','stroke-width':2}),svg('polygon',{points:'16,5 10,9 10,1',fill:'#000'}));
        grid.append(from,arrow,to);relations.append(grid);body.append(relations);
      }else{
        const duties=group('Responsabilidades distribuídas'),rows=el('div','hm-duty-list');
        state.agents.filter(item=>item.kind!=='queen'&&item.role!=='verifier').forEach(worker=>{
          const item=btn('',()=>live.selectAgent(worker.id),'hm-duty'),copy=el('span','hm-duty-copy'),ending=el('span','hm-duty-status'),kind=(state.phase.agents[worker.id]||['idle'])[0];
          copy.append(el('span','hm-duty-name',worker.name),el('span','hm-duty-text',worker.info.tasks.items[0]?.description||worker.info.description||'Sem tarefa nesta missão.'));ending.append(statusIcon(kind),el('span','',shortStatus(kind)));item.append(copy,ending);rows.append(item);
        });
        duties.append(rows);body.append(duties);
      }
      const own=connectionRows(state,agent);if(own)body.append(own);
    }
    box.append(body);return box;
  }

  // Formulário de criar/editar abelha: persistente enquanto aberto, para o polling não apagar o que foi digitado.
  function openForm(state,bee){
    const editing=!!bee,rows=rosterOf(state),free=['queen','verifier'].filter(name=>!rows.some(row=>row.role===name)),roles=editing?[bee.role]:['worker',...free],roleSelect=el('select'),fieldsNode=el('div','hm-form-fields stack'),errors={};
    let role=bee?.role||'worker';
    const wrap=el('form','hm-worker-form'),general=el('div','hm-form-error');general.setAttribute('role','alert');general.hidden=true;
    const add=(key,title,control,hint,extra)=>{const box=el('label'),error=el('div','hm-form-error');error.setAttribute('role','alert');error.hidden=true;errors[key]=error;box.append(label(title),control);if(extra)box.append(extra);if(hint)box.append(el('small','hm-form-hint',hint));box.append(error);fieldsNode.append(box);};
    const id=el('input'),description=el('textarea'),skills=el('input'),instructions=el('textarea'),provider=el('select'),model=el('select'),effort=el('select');
    id.maxLength=100;id.value=bee?.id||'';id.readOnly=editing;id.placeholder='Ex.: financeiro';
    description.maxLength=2000;description.value=bee?.description||'';description.placeholder='Ex.: Confere pagamentos e aponta divergências nas planilhas.';
    skills.value=(bee?.skills?.tags||[]).join(', ');skills.placeholder='python, testes, revisão (separe por vírgula)';
    instructions.maxLength=4000;instructions.value=bee?.skills?.instructions||'';instructions.placeholder='Opcional: como a abelha deve usar essas skills.';
    const preview=el('div','hm-tags'),syncPreview=()=>preview.replaceChildren(...parseTags(skills.value).map(tag=>el('span','',tag)));skills.addEventListener('input',syncPreview);syncPreview();
    roles.forEach(name=>roleSelect.append(optionNode(name,roleNames[name])));roleSelect.value=role;
    if(roles.length>1)add('role','Papel',roleSelect,'A equipe precisa de uma Rainha, ao menos uma operária e um verificador independente.');
    add('id','Identificador',id);add('description','Descrição',description);add('skills','Skills',skills,null,preview);add('instructions','Instruções das skills',instructions);
    const toolsBox=el('div','hm-tool-boxes'),boxes={};
    ['read','patch','checks'].forEach(name=>{
      const line=el('label','hm-tool-check'),input=el('input');input.type='checkbox';input.value=name;input.checked=(bee?.tools||(editing?[]:['read','patch'])).includes(name);
      input.disabled=name==='patch'&&['queen','verifier'].includes(role);if(input.disabled)input.checked=false;boxes[name]=input;line.append(input,el('span','',TOOLS[name][0]),el('small','',input.disabled?'Indisponível para este papel':TOOLS[name][1]));toolsBox.append(line);
    });
    const syncTools=()=>{const blocked=['queen','verifier'].includes(role);boxes.patch.disabled=blocked;if(blocked)boxes.patch.checked=false;};syncTools();roleSelect.addEventListener('change',()=>{role=roleSelect.value;syncTools();});
    add('tools','Ferramentas',toolsBox,'Informar progresso é automático.');
    const selected={provider:bee?.provider||'codex',model:bee?.model||'',effort:bee?.effort||''};
    const syncSelects=()=>{fillSelect(provider,['codex','claude'],selected.provider,'Provedor');fillSelect(model,modelsOf(last.catalog,selected.provider).map(item=>item.name),selected.model,'Modelo');fillSelect(effort,modelsOf(last.catalog,selected.provider).find(item=>item.name===selected.model)?.efforts||[],selected.effort,'Esforço');[provider,model,effort].forEach(node=>{node.disabled=!last.catalog;});};
    provider.addEventListener('change',()=>{selected.provider=provider.value;selected.model='';selected.effort='';syncSelects();});model.addEventListener('change',()=>{selected.model=model.value;selected.effort='';syncSelects();});effort.addEventListener('change',()=>{selected.effort=effort.value;});
    add('provider','Provedor',provider);add('model','Modelo',model);add('effort','Esforço',effort);
    const consult=btn('Consultar modelos',()=>live.loadCatalog(),'hm-outline'),actions=el('div','hm-foot-actions'),submit=btn(editing?'Salvar alterações':'Adicionar à equipe',null,'hm-dark');
    submit.type='submit';actions.append(submit,btn('Cancelar',()=>{form=null;render(last);},'hm-outline'));
    wrap.append(el('div','hm-worker-title',editing?`Editar ${bee.id}`:roles.length>1?'Nova abelha':'Nova operária'),el('div','hm-worker-copy',editing?`${roleNames[role]} do cadastro. A descrição, as skills e as ferramentas entram no prompt da abelha.`:'Ela entra na equipe salva e pode receber tarefas nas próximas missões. Descrição, skills e ferramentas entram no prompt da abelha.'),fieldsNode,consult,general,actions);
    const showErrors=map=>{FIELDS.concat('instructions').forEach(key=>{if(!errors[key])return;errors[key].textContent=map[key]||'';errors[key].hidden=!map[key];});};
    wrap.addEventListener('submit',async event=>{
      event.preventDefault();
      const values={id:id.value.trim(),description:description.value,tags:parseTags(skills.value),instructions:instructions.value,tools:['read','patch','checks'].filter(name=>boxes[name].checked),...selected};
      const found=validateBeeForm(values,{role,rows:rosterOf(last),editing});showErrors(found);general.hidden=true;
      if(Object.keys(found).length)return;
      const entry={id:values.id,role,provider:values.provider,model:values.model,effort:values.effort,temporary:false,description:values.description.trim(),skills:{tags:values.tags,instructions:values.instructions},tools:values.tools};
      if(!savedOf(last).length&&!editing){draft=[...draft,entry];form=null;render(last);return;}
      const rows=editing?rosterOf(last).map(item=>item.id===bee.id?entry:{...item}):[...rosterOf(last).map(item=>({...item})),entry],problem=validateTeam(rows);
      if(problem){general.textContent=problem;general.hidden=false;return;}
      if(await live.saveTeam(rows)){form=null;render(last);return;}
      const detail=last.errorDetail||{};
      if(detail.bee===entry.id&&FIELDS.includes(detail.field))showErrors({[detail.field]:describeError(last.error,detail)});
      else{general.textContent=describeError(last.error,detail);general.hidden=false;}
    });
    const syncLoading=()=>{consult.textContent=last.catalogLoading?'Consultando modelos…':'Consultar modelos';consult.disabled=!!last.catalogLoading;};
    form={node:wrap,syncSelects,syncLoading};syncSelects();syncLoading();
  }

  function listView(state,visible){
    const catalogLine=el('div','hm-catalog-row'),load=btn(state.catalogLoading?'Consultando modelos…':'Consultar modelos',()=>live.loadCatalog(),'hm-outline');
    load.disabled=!!state.catalogLoading;
    const notice=el('p','hm-foot-note',state.catalogLoading?'Consultando os provedores instalados…':state.catalog?Object.entries(state.catalog).map(([name,result])=>`${name}: ${result.authenticated&&result.compatible?'disponível para configurar':'indisponível'}${result.errors?.length?` (${result.errors.join(', ')})`:''}`).join(' · '):'Consulte os modelos antes de trocar o modelo ou o esforço de uma abelha.');
    catalogLine.append(load,notice);scroll.append(catalogLine);
    const problem=fail(state);if(problem)scroll.append(problem);
    const incomplete=state.status?.roster?.incomplete||[];
    if(incomplete.length)scroll.append(el('p','hm-form-error',`${incomplete.length===1?'Uma abelha tem':`${incomplete.length} abelhas têm`} cadastro incompleto (${incomplete.map(item=>item.id).join(', ')}). Não dá para planejar com a Rainha até completar.`));
    if(!visible.length)scroll.append(el('p','hm-empty-detail',draft.length?'Equipe em montagem: ainda não foi salva.':'Nenhuma abelha cadastrada. Monte a equipe com uma Rainha, ao menos uma operária e um verificador independente.'));
    draft.filter(()=>!visible.length).forEach(item=>{const line=el('div','hm-plan-row');line.append(statusIcon('idle'),el('strong','',String(draft.indexOf(item)+1)),el('span','',`${item.id} · ${roleNames[item.role]}`),el('small','',item.model));scroll.append(line);});
    visible.forEach(agent=>{
      const selected=state.selected===agent.id,wrap=el('div',`hm-agent-row-wrap ${agent.kind==='sub'?'sub ':''}${selected?'selected':''}`),row=btn('',()=>live.selectAgent(agent.id),'hm-agent-row');
      wrap.dataset.agent=agent.id;row.dataset.id=agent.id;row.setAttribute('aria-expanded',String(selected));
      const status=state.phase.agents[agent.id]||['idle','Disponível'],copy=el('span','hm-row-copy'),titleLine=el('span','hm-row-title'),ending=el('span','hm-row-ending');
      titleLine.append(el('strong','',agent.name));
      if(agent.temporary)titleLine.append(el('small','','Temporária'));else if(agent.kind==='sub')titleLine.append(el('small','','Subagente'));
      if(incompleteOf(state,agent.sourceId))titleLine.append(el('small','hm-row-incomplete','Incompleta'));
      copy.append(titleLine,el('span','',status[1]));
      if(status[3])ending.append(el('span','hm-row-progress',`${status[3][0]}/${status[3][1]}`));
      ending.append(statusIcon(status[0]));row.append(rowIcon(agent,status[0],state.animationsPaused,state.reduced),copy,ending);wrap.append(row);
      if(selected)wrap.append(details(state,agent));scroll.append(wrap);
    });
    const settings=el('div','hm-detail-group hm-limit-group'),saveLimit=btn('Salvar limite',()=>live.saveLimit(Number(limitInput.value)),'hm-outline'),line=el('div','hm-quick-row');
    saveLimit.disabled=!state.status;line.append(limitInput,saveLimit);
    settings.append(label('Máximo de operárias, subagentes e verificador em execução'),line);scroll.append(settings);
    if(document.activeElement!==limitInput&&state.status?.settings)limitInput.value=state.status.settings.worker_limit;
  }

  function footView(state){
    const selected=state.agents.find(agent=>agent.id===state.selected),bee=selected&&permanent(state,selected)?rosterOf(state).find(item=>item.id===selected.sourceId):null;
    if(!savedOf(state).length&&draft.length){
      const problem=validateTeam(draft),actions=el('div','hm-foot-actions'),save=btn('Salvar equipe',async()=>{if(await live.saveTeam(draft.map(item=>({...item})))){draft=[];render(last);}},'hm-dark');
      save.disabled=!!problem||!state.status?.roster;actions.append(btn('＋ Adicionar abelha',()=>{openForm(last,null);render(last);},'hm-outline'),save,btn('Descartar',()=>{draft=[];render(last);},'hm-outline'));
      foot.replaceChildren(actions,el('p','hm-foot-note',problem||'Equipe completa: salve para poder planejar missões.'));return;
    }
    const actions=el('div','hm-foot-actions'),create=btn('＋ Criar operária',()=>{tab='geral';openForm(last,null);render(last);},'hm-dark'),edit=btn('Editar agente',()=>{openForm(last,bee);render(last);},'hm-outline'),remove=btn('Excluir agente',()=>{live.saveTeam(rosterOf(last).filter(item=>item.id!==bee.id).map(item=>({...item})));},'hm-outline');
    const removable=!!bee&&['worker','subagent'].includes(bee.role)&&!validateTeam(rosterOf(state).filter(item=>item.id!==bee.id));
    create.disabled=!state.status?.roster;edit.disabled=!bee;remove.disabled=!removable;
    actions.append(create,edit,remove);
    const note=!state.status?.roster?'Aguardando o cadastro da equipe.':!selected?'Selecione um agente para editar ou excluir.':!bee?'Abelhas temporárias são somente leitura: só a Rainha as cria e elas saem com a missão.':!removable?(bee.role==='queen'||bee.role==='verifier'?'A Rainha e o verificador não podem ser excluídos.':'A equipe precisa de ao menos uma operária.'):'Excluir remove a abelha do cadastro; missões antigas não mudam.';
    foot.replaceChildren(actions,el('p','hm-foot-note',note));
  }

  function render(state){
    last=state;
    const visible=state.agents;
    headHost.replaceChildren(headNode(state,visible));
    // Com o formulário aberto (ou o limite sendo digitado) nada é reconstruído: o polling não pode tirar o foco do campo.
    if(form){
      if(scroll.children[0]!==form.node){scroll.replaceChildren(form.node);foot.replaceChildren();form.key=null;}
      form.syncLoading();
      const key=state.catalog?'catalogo':'vazio';if(form.key!==key){form.key=key;form.syncSelects();}
      return;
    }
    if(document.activeElement===limitInput)return;
    scroll.replaceChildren();listView(state,visible);footView(state);
  }
  return {render,count:state=>state.agents.length};
}
