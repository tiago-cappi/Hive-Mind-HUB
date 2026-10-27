import {el,label,btn,statusIcon,hashNode} from './live-ui.js';
import {describeError} from './messages.js';

export const CRITERION={passed:['done','aprovado'],failed:['failed','reprovado'],unverifiable:['waiting','não verificável'],pending:['idle','pendente']};
export const criterionText=item=>`${Object.hasOwn(CRITERION,item.status)?CRITERION[item.status][1]:item.status} — ${item.description} (${item.id})`;

// Dados da entrega prontos para exibir: arquivos com a tarefa dona, critérios e veredito.
export function deliveryView(mission){
  const data=mission?.data||{},delivery=data.delivery;
  if(!delivery)return null;
  const owners=new Map();(data.plan?.tasks||[]).forEach(task=>(task.files||[]).forEach(file=>owners.set(file,task)));
  const changes=(delivery.changes||[]).map(item=>{const path=typeof item==='string'?item:String(item?.path||item?.name||'');const task=owners.get(path);return {path,task:task?.id||'—',bee:task?.bee_id||'—',inPlan:!!task};});
  const described=new Map((data.plan?.acceptance||[]).map(item=>[item.id,item.description]));
  const criteria=Object.entries(data.verdict?.criteria||{}).map(([id,status])=>({id,status,description:described.get(id)||id}));
  return {hash:data.delivery_hash,changes,outside:changes.filter(item=>!item.inPlan).length,verdict:data.verdict||null,criteria,passed:criteria.filter(item=>item.status==='passed').length};
}
export function criteriaList(criteria,className='hm-plan-row'){
  return criteria.map((item,index)=>{const row=el('div',className);row.append(statusIcon(CRITERION[item.status]?.[0]||'idle'),el('strong','',String(index+1)),el('span','',criterionText(item)),el('small',''));return row;});
}
export function deliveryStats(view){
  const stats=el('div','hm-delivery-stats');
  [[String(view.changes.length),view.changes.length===1?'arquivo alterado':'arquivos alterados'],[`${view.passed}/${view.criteria.length}`,'critérios aprovados'],[String(view.outside),'fora do plano']].forEach(([value,name],index)=>{
    const card=el('div',index===2?'dark':'');card.append(el('strong','',value),el('span','',name));stats.append(card);
  });
  return stats;
}

// Popup de entrega do modo real (mesmas classes da demonstração). Abre por onUiRequest('delivery'); Esc fecha.
export function createLiveDelivery(root,live){
  const box=el('div','hm-delivery');box.hidden=true;root.append(box);
  let open=false,last=null,focused=false,signature='';
  const close=()=>{open=false;focused=false;if(last)render(last);};
  live.onUiRequest?.(target=>{if(target==='delivery')open=true;});
  root.addEventListener('keydown',event=>{if(event.key==='Escape'&&open){event.preventDefault();close();}});
  function render(state){
    last=state;
    const mission=state.mission,view=deliveryView(mission),next=JSON.stringify([open,!!view,mission?.state,mission?.revision,state.error]);
    if(next===signature)return;
    signature=next;
    if(!open||!view){box.hidden=true;box.replaceChildren();focused=false;return;}
    const data=mission.data,dialog=el('div','hm-delivery-dialog');
    dialog.setAttribute('role','dialog');dialog.setAttribute('aria-label','Entrega da missão');dialog.tabIndex=-1;
    const top=el('div','hm-delivery-top');top.append(label('Entrega · missão real'),btn('Fechar',close,'hm-outline'));
    const title=el('div','hm-delivery-title',data.title||'Entrega');title.title=data.title||'';
    dialog.append(top,title,
      el('p','',view.verdict?`${view.verdict.passed?'Aprovada':'Não aprovada'} pela verificação independente no ciclo ${view.verdict.cycle}. Estas são as alterações prontas para a sua revisão.`:'Alterações prontas para a sua revisão.'),deliveryStats(view));
    const table=el('div','hm-delivery-table'),header=el('div','hm-delivery-row header');
    ['Tarefa','Abelha','Arquivo','Situação'].forEach(text=>header.append(el('span','',text)));table.append(header);
    view.changes.forEach(item=>{const row=el('div','hm-delivery-row');[item.task,item.bee,item.path,item.inPlan?'No plano':'Fora do plano'].forEach(value=>row.append(el('span','',value)));table.append(row);});
    if(!view.changes.length)table.append(el('p','','Nenhum arquivo foi alterado.'));
    dialog.append(table);
    if(view.criteria.length){const group=el('div','hm-delivery-criteria');group.append(label('Critérios de aceite'),...criteriaList(view.criteria));dialog.append(group);if(view.verdict?.evidence)dialog.append(el('p','',`Evidência: ${view.verdict.evidence}`));}
    const note=el('p','hm-delivery-note');note.append(hashNode(view.hash,'Versão da entrega '));
    if(mission.state==='delivery_approved')note.append(document.createTextNode(' · A origem e o journal precisam estar no mesmo volume.'));
    dialog.append(note);
    if(state.error)dialog.append(el('p','hm-form-error',`Não foi possível concluir: ${describeError(state.error,state.errorDetail)}`));
    const actions=el('div','hm-foot-actions');
    if(mission.state==='awaiting_delivery_approval')actions.append(btn('Aprovar entrega',()=>live.command('approve_delivery',{candidate_hash:data.candidate_hash,delivery_hash:data.delivery_hash}),'hm-dark'));
    if(mission.state==='delivery_approved')actions.append(btn('Incorporar entrega aprovada',()=>live.command('apply',{delivery_hash:data.delivery_hash}),'hm-dark'));
    actions.append(btn('Fechar',close,'hm-outline'));dialog.append(actions);
    box.replaceChildren(dialog);box.hidden=false;
    if(!focused){focused=true;dialog.focus?.();}
  }
  return {render,isOpen:()=>open};
}
