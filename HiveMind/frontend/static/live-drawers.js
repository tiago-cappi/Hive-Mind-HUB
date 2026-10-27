import {el,pullTab} from './live-ui.js';
import {createLiveTeam,validateTeam} from './live-team.js';
import {createLiveMission} from './live-mission.js';
import {createLiveChat,chatQueen} from './live-chat.js';
import {createLiveDelivery} from './live-delivery.js';

export {validateTeam,chatQueen};

// Compositor das gavetas do modo real: cada gaveta tem o seu módulo (live-team, live-mission, live-chat) e o popup de entrega (live-delivery).
export function createLiveDrawers(root,live){
  const leftWrap=el('div','hm-side hm-side-left'),rightWrap=el('div','hm-side hm-side-right'),bottomWrap=el('div','hm-bottom');
  const left=el('aside','hm-drawer hm-agents'),right=el('aside','hm-drawer hm-mission'),bottom=el('section','hm-drawer hm-chat');
  left.setAttribute('aria-label','Agentes');right.setAttribute('aria-label','Missão');bottom.setAttribute('aria-label','Conversa com a Rainha');
  const leftPull=pullTab('left','Agentes',()=>live.toggleDrawer('left')),rightPull=pullTab('right','Missão',()=>live.toggleDrawer('right')),bottomPull=pullTab('bottom','Conversa com a Rainha',()=>live.toggleDrawer('bottom'));
  leftWrap.append(left,leftPull);rightWrap.append(right,rightPull);bottomWrap.append(bottom,bottomPull);root.append(leftWrap,rightWrap,bottomWrap);
  const team=createLiveTeam(left,live),mission=createLiveMission(right,live),chat=createLiveChat(bottom,live),delivery=createLiveDelivery(root,live);
  function render(state){
    [[leftWrap,leftPull,left,state.drawers.left],[rightWrap,rightPull,right,state.drawers.right],[bottomWrap,bottomPull,bottom,state.drawers.bottom]].forEach(([wrap,pull,drawer,open])=>{wrap.classList.toggle('open',open);pull.setAttribute('aria-expanded',String(open));drawer.inert=!open;});
    leftPull.set(state.agents.length);rightPull.set(`${state.hud.step}/7`);bottomPull.set(state.messages.length||'');
    team.render(state);mission.render(state);chat.render(state);delivery.render(state);
  }
  return {render};
}
