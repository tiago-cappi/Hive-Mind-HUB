import {el,btn,drawerHead,statusIcon} from './live-ui.js';

export const CHAT_STATES=['clarifying','awaiting_plan_approval','awaiting_user'];
// A Rainha atual do cadastro vale; a do início da missão é só reserva.
export const chatQueen=(status,planning)=>status?.roster?.bees?.find(bee=>bee.role==='queen')||planning.queen;
export const chatBlockedReason=mission=>!mission?'Crie ou selecione uma missão para conversar com a Rainha.':CHAT_STATES.includes(mission.state)?'':'A Rainha só recebe mensagens quando pede esclarecimentos, aguarda a aprovação do plano ou depende de você.';
export function teamChangeNotice(planning,status){
  if(!planning)return '';
  const queen=chatQueen(status,planning);
  return JSON.stringify(queen)!==JSON.stringify(planning.queen)?`A equipe mudou desde o início desta missão: as próximas mensagens usam a Rainha atual (${queen.id} · ${queen.provider} · ${queen.model} · ${queen.effort}).`:'';
}

// Gaveta Conversa do modo real: mesmas classes da Conversa da demonstração.
export function createLiveChat(drawer,live){
  const head=drawerHead('Conversa com a Rainha',()=>live.toggleDrawer('bottom'),{chat:true,subtitle:'Nenhuma missão selecionada'});
  const log=el('div','hm-chat-log'),form=el('form','hm-chat-form'),field=el('label'),line=el('div'),input=el('input'),send=btn('Enviar para a Rainha',null,'hm-dark'),hint=el('p','hm-foot-note');
  let last=null,signature='';
  input.name='message';send.type='submit';
  line.append(input,send);field.append(el('strong','','Sua mensagem para a Rainha'),line);form.append(field,hint);
  drawer.append(head,log,form);
  form.addEventListener('submit',event=>{
    event.preventDefault();
    const planning=last?.mission?.data?.planning;
    if(!planning||send.disabled||!input.value.trim())return;
    live.command('ask',{source:planning.source,queen:chatQueen(last.status,planning),message:input.value});input.value='';
  });
  live.onUiRequest?.(target=>{if(target==='chat')setTimeout(()=>input.focus(),0);});
  function render(state){
    last=state;
    const mission=state.mission,planning=mission?.data?.planning,reason=chatBlockedReason(mission),notice=teamChangeNotice(planning,state.status);
    head.sub.textContent=mission?mission.data.title:'Nenhuma missão selecionada';
    send.disabled=!!reason;hint.textContent=reason;input.placeholder=reason?'Aguardando uma missão que aceite mensagens':'Escreva para a Rainha';
    const next=JSON.stringify([state.messages,notice]);
    if(next===signature)return;
    signature=next;
    log.replaceChildren();
    if(!state.messages.length&&!notice)log.append(el('p','','Nenhuma mensagem ainda. Crie uma missão ou escreva para a Rainha abaixo.'));
    state.messages.forEach(message=>{
      if(message.role==='user'){const row=el('div','hm-chat-user');row.append(el('strong','','Você'),el('span','',message.text));log.append(row);}
      else{const row=el('div','hm-chat-event'),copy=el('span'),text=el('span');text.append(el('strong','','Rainha'),document.createTextNode(` · ${message.text}`));copy.append(text);row.append(statusIcon('coord'),copy);log.append(row);}
    });
    if(notice){const row=el('div','hm-chat-event'),copy=el('span');copy.append(el('strong','','Equipe'),document.createTextNode(` · ${notice}`));row.append(statusIcon('approval'),copy);log.append(row);}
    log.scrollTop=log.scrollHeight;
  }
  return {render};
}
