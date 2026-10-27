import {el,svg,label,hex,caret,statusIcon,trailSample,statusShort} from './drawers.js';

// Peças compartilhadas pelas gavetas do modo real. Os componentes visuais vêm de drawers.js
// (os mesmos da demonstração); aqui ficam só os que dependem de dados reais.
export {el,svg,label,hex,caret,statusIcon,trailSample,statusShort};

export const btn=(text,fn,cls='hm-outline')=>{const node=el('button',cls,text);node.type='button';if(fn)node.addEventListener('click',fn);return node;};
export const shortHash=value=>String(value||'').slice(0,8);
export function hashNode(value,prefix='Versão '){const node=el('span','hm-hash',`${prefix}${shortHash(value)}`);node.title=String(value||'');return node;}
export const taskKind={done:'done',running:'working',failed:'failed',waiting:'waiting',pending:'idle'};

export function drawerHead(title,onClose,{badge='',subtitle='',chat=false}={}){
  const node=el('div',`hm-drawer-head${chat?' hm-chat-head':''}`),line=el('div','hm-head-line'),name=el('span','hm-head-title');
  name.append(hex(),el('strong','',title));line.append(name);
  const badgeNode=el('span','hm-head-badge',badge);badgeNode.hidden=!badge;node.badge=badgeNode;line.append(badgeNode);
  const sub=el('p','hm-head-sub',subtitle);node.sub=sub;
  if(chat)line.append(sub);
  const close=btn('×',onClose,'hm-close');close.setAttribute('aria-label',`Fechar ${title}`);line.append(close);
  node.append(line);
  if(!chat&&subtitle)node.append(sub);
  return node;
}
export function tabs(defs,active,onPick){
  const nav=el('div','hm-tabs');
  defs.forEach(([id,text])=>{const tab=btn(text,()=>onPick(id),'');tab.className=id===active?'active':'';nav.append(tab);});
  return nav;
}
// Aba puxadora igual à da demonstração: ícone, nome, contador e seta.
export function pullTab(side,title,onClick){
  const node=btn('',onClick,`hm-pull hm-pull-${side}`);
  node.setAttribute('aria-label',title);
  node.set=count=>{const key=String(count??'');if(node.key===key)return;node.key=key;node.replaceChildren(hex(),el('span','',title),...(count===''||count===undefined||count===null?[]:[el('b','',String(count))]),caret());};
  node.set('');
  return node;
}
// Segmentos de progresso do detalhe: no máximo 24, proporcionais ao total.
export function segmentBar(current,total){
  const bar=el('div','hm-segment-progress'),count=Math.min(Math.max(total,1),24),filled=Math.round(Math.min(current,total)/Math.max(total,1)*count);
  for(let index=0;index<count;index++){const segment=el('i');if(index<filled)segment.className='filled';bar.append(segment);}
  return bar;
}
