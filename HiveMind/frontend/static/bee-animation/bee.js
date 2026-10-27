const NS = 'http://www.w3.org/2000/svg';
const states = new Set(['idle','working','coord','waiting','approval','done','failed']);
const assets = new URL('../assets/', import.meta.url);

export function createBee({queen=false,state='idle',size=56,paused=false,reduced=false} = {}) {
  const svg = document.createElementNS(NS,'svg');
  svg.setAttribute('class','hm-bee-asset');
  svg.setAttribute('viewBox','0 0 1254 1254');
  svg.setAttribute('width',size); svg.setAttribute('height',size);
  svg.setAttribute('aria-hidden','true'); svg.setAttribute('focusable','false');
  svg.dataset.queen = String(queen); svg.dataset.state = states.has(state) ? state : 'idle';
  svg.dataset.paused = String(paused); svg.dataset.reduced = String(reduced);
  const rig = document.createElementNS(NS,'g'); rig.setAttribute('class','hm-bee-rig');
  const dir = new URL(`${queen ? 'rainha' : 'operaria'}-animacao/`, assets);
  [['asa-esquerda','hm-bee-wing hm-bee-wing-left'],['asa-direita','hm-bee-wing hm-bee-wing-right'],['corpo-sem-asas','hm-bee-body']].forEach(([part,cls]) => {
    const g=document.createElementNS(NS,'g'); g.setAttribute('class',cls);
    const image=document.createElementNS(NS,'image'); image.setAttribute('href',new URL(`${part}.png`,dir)); image.setAttribute('width','1254'); image.setAttribute('height','1254');
    g.appendChild(image); rig.appendChild(g);
  });
  svg.appendChild(rig);
  return svg;
}

export function updateBee(svg,{state,paused,reduced}) {
  if (state) svg.dataset.state = states.has(state) ? state : 'idle';
  svg.dataset.paused = String(!!paused); svg.dataset.reduced = String(!!reduced);
}
