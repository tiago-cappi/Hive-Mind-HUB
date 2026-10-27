/* C.O.R.E. · celular
 *
 * Modelo: o turno NAO vive nesta pagina. Ele roda numa thread do servidor
 * (mobile/session.py) e a pagina so observa, por long-poll em /api/state?rev=N.
 * Consequencia pratica: apagar a tela, trocar de app ou perder o Wi-Fi no meio
 * de uma resposta nao cancela nada — ao voltar, o texto esta la, do ponto em
 * que estiver. E por isso que aqui nao ha streaming nem reconexao complicada.
 */
'use strict';

const $ = (id) => document.getElementById(id);
const fio = $('fio'), dot = $('dot'), txt = $('txt');

let rev = -1;              // versao do estado que esta na tela
let seqNaTela = 0;         // turno desenhado no momento
let elResp = null, elPassos = null;
let laco = 0;              // geracao do laco de polling (aborta os antigos)
let falado = 0;            // chars ja lidos em voz alta neste turno

const opt = {
  falar:  localStorage.getItem('falar') === '1',  // voz alta no PC
  ler:    localStorage.getItem('ler') === '1',    // voz alta aqui
  modelo: localStorage.getItem('modelo') || '',   // '' = default do Hub
  esforco: localStorage.getItem('esforco') || '', // '' = default do Hub
};

/* ---------- texto ---------- */

function esc(s) {
  return s.replace(/[&<>]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
}

// markdown minimo: blocos de codigo e codigo em linha. O resto e texto corrido
// (as respostas por voz ja vem sem formatacao).
function fmt(s) {
  return esc(s || '')
    .replace(/```[a-z]*\n?([\s\S]*?)```/g, (_, c) => `<pre><code>${c}</code></pre>`)
    .replace(/`([^`\n]+)`/g, '<code>$1</code>');
}

function hora(ts) {
  const d = ts ? new Date(ts * 1000) : new Date();
  return d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
}

function noFim() {
  return fio.scrollHeight - fio.scrollTop - fio.clientHeight < 120;
}
function rolar(forcar) {
  if (forcar || noFim()) fio.scrollTop = fio.scrollHeight;
}

function bolha(classe, html) {
  const el = document.createElement('div');
  el.className = 'msg ' + classe;
  el.innerHTML = html;
  fio.appendChild(el);
  return el;
}

/* ---------- voz no celular ---------- */

let vozPT = null;
function achaVoz() {
  const vs = speechSynthesis.getVoices() || [];
  vozPT = vs.find((v) => /^pt.BR/i.test(v.lang)) || vs.find((v) => /^pt/i.test(v.lang)) || null;
}
if ('speechSynthesis' in window) {
  achaVoz();
  speechSynthesis.onvoiceschanged = achaVoz;
}

function ler(trecho) {
  if (!opt.ler || !trecho.trim() || !('speechSynthesis' in window)) return;
  const u = new SpeechSynthesisUtterance(trecho);
  u.lang = 'pt-BR';
  if (vozPT) u.voice = vozPT;
  u.rate = 1.05;
  speechSynthesis.speak(u);
}

// Le so o que ja fechou frase: evita cortar palavra no meio enquanto o texto
// ainda esta crescendo.
function lerNovo(completo, fim) {
  if (!opt.ler) { falado = completo.length; return; }
  const pend = completo.slice(falado);
  if (!pend) return;
  const corte = fim ? pend.length : Math.max(
    pend.lastIndexOf('. '), pend.lastIndexOf('! '),
    pend.lastIndexOf('? '), pend.lastIndexOf('\n'));
  if (corte <= 0) return;
  ler(pend.slice(0, corte + 1));
  falado += corte + 1;
}

/* ---------- estado ---------- */

function novoTurno(pergunta) {
  bolha('eu', esc(pergunta));
  elPassos = document.createElement('div');
  elPassos.className = 'passos';
  fio.appendChild(elPassos);
  elResp = bolha('ele', '<span class="cursor"></span>');
  falado = 0;
  rolar(true);
}

function aplicar(s) {
  dot.className = 'dot ' + (!s.hub ? 'off' : s.busy ? 'busy' : 'on');
  $('btCancelar').hidden = !s.busy;
  $('btEnviar').disabled = s.busy;

  if (s.seq !== seqNaTela) {
    if (!s.busy && !s.erro) return;        // turno velho: ja esta no historico
    seqNaTela = s.seq;
    novoTurno(s.q);
  }
  if (!elResp) return;

  if (elPassos) {
    const passos = (s.passos || []).slice(-4);
    elPassos.textContent = '';
    elPassos.hidden = !s.busy || !passos.length;
    passos.forEach((p) => {
      const l = document.createElement('div');
      l.textContent = '· ' + p;
      elPassos.appendChild(l);
    });
  }

  const perto = noFim();
  elResp.innerHTML = fmt(s.txt) + (s.busy ? '<span class="cursor"></span>' : '');
  lerNovo(s.txt || '', !s.busy);

  if (!s.busy) {
    if (elPassos) { elPassos.remove(); elPassos = null; }
    if (s.erro && !(s.txt || '').trim()) {
      elResp.className = 'msg erro';
      elResp.textContent = '⚠ ' + s.erro;
    } else {
      elResp.insertAdjacentHTML('beforeend', `<span class="hora">${hora(s.ts)}</span>`);
    }
    elResp = null;
  }
  rolar(perto);
}

async function observar() {
  const meu = ++laco;
  while (meu === laco) {
    try {
      const r = await fetch('/api/state?rev=' + rev, { cache: 'no-store' });
      if (r.status === 401 || r.status === 403) { location.href = '/login'; return; }
      const s = await r.json();
      if (meu !== laco) return;
      rev = s.rev;
      aplicar(s);
    } catch (e) {
      if (meu !== laco) return;
      dot.className = 'dot off';
      await new Promise((ok) => setTimeout(ok, 2000));
    }
  }
}

/* ---------- acoes ---------- */

async function enviar() {
  const t = txt.value.trim();
  if (!t) return;
  txt.value = '';
  txt.style.height = 'auto';
  speechSynthesis && speechSynthesis.cancel();
  try {
    const r = await fetch('/api/ask', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ texto: t, falar: opt.falar, modelo: opt.modelo,
                             esforco: opt.esforco }),
    });
    const s = await r.json();
    if (s.erro) { bolha('erro', '⚠ ' + esc(s.erro)); rolar(true); return; }
    rev = s.rev; aplicar(Object.assign({ hub: true }, s));
  } catch (e) {
    bolha('erro', '⚠ sem ligacao com o servidor'); rolar(true);
  }
}

async function carregarHistorico() {
  try {
    const r = await fetch('/api/history?limit=40', { cache: 'no-store' });
    if (r.status === 401 || r.status === 403) { location.href = '/login'; return; }
    const { turnos } = await r.json();
    (turnos || []).forEach((t) => {
      bolha('eu', esc(t.q));
      bolha('ele', fmt(t.a) + `<span class="hora">${hora(t.ts)}</span>`);
    });
    rolar(true);
  } catch (e) { /* sem historico e so uma tela vazia */ }
}

async function relatorios() {
  const cx = $('relLista');
  cx.textContent = 'carregando...';
  try {
    const { reports, erro } = await (await fetch('/api/reports', { cache: 'no-store' })).json();
    cx.textContent = '';
    if (erro || !reports || !reports.length) {
      const v = document.createElement('div');
      v.className = 'vazio';
      v.textContent = erro ? '⚠ ' + erro : 'nenhum relatorio ainda';
      cx.appendChild(v);
      return;
    }
    reports.slice(0, 30).forEach((rp) => {
      const a = document.createElement('a');
      a.href = '/api/reports/' + encodeURIComponent(rp.file);
      a.target = '_blank'; a.rel = 'noopener';
      a.textContent = rp.title || rp.file;
      const s = document.createElement('small');
      s.textContent = new Date(rp.mtime * 1000).toLocaleString('pt-BR');
      a.appendChild(s);
      cx.appendChild(a);
    });
  } catch (e) { cx.textContent = 'nao consegui listar'; }
}

/* ---------- ligacoes de tela ---------- */


$('btEnviar').onclick = enviar;
txt.addEventListener('input', () => {
  txt.style.height = 'auto';
  txt.style.height = Math.min(txt.scrollHeight, window.innerHeight * 0.38) + 'px';
});
txt.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); enviar(); }
});

$('btCancelar').onclick = () => fetch('/api/cancel', { method: 'POST' });

$('btNova').onclick = async () => {
  if (!confirm('Comecar uma conversa nova? O que esta na tela sai.')) return;
  if ('speechSynthesis' in window) speechSynthesis.cancel();
  await fetch('/api/reset', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ modelo: opt.modelo, esforco: opt.esforco }),
  });
  fio.textContent = ''; elResp = null; elPassos = null; seqNaTela = 0; rev = -1;
};

$('btCfg').onclick = () => {
  $('rel').hidden = true;
  $('cfg').hidden = !$('cfg').hidden;
};
$('btRel').onclick = () => {
  $('cfg').hidden = true;
  $('rel').hidden = !$('rel').hidden;
  if (!$('rel').hidden) relatorios();
};

$('optFalar').checked = opt.falar;
$('optFalar').onchange = (e) => {
  opt.falar = e.target.checked;
  localStorage.setItem('falar', opt.falar ? '1' : '0');
};

$('optLer').checked = opt.ler;
$('optLer').onchange = (e) => {
  opt.ler = e.target.checked;
  localStorage.setItem('ler', opt.ler ? '1' : '0');
  // iOS/Android so liberam a sintese depois de um toque: aquece aqui, no toque.
  if (!('speechSynthesis' in window)) return;
  if (opt.ler) { achaVoz(); ler(' '); } else speechSynthesis.cancel();
};

$('optModelo').value = opt.modelo;
$('optModelo').onchange = (e) => {
  opt.modelo = e.target.value;
  localStorage.setItem('modelo', opt.modelo);
  // So vale a partir do proximo turno: e la que o Hub decide se resobe o
  // claude deste sid com a flag --model nova.
};

$('optEsforco').value = opt.esforco;
$('optEsforco').onchange = (e) => {
  opt.esforco = e.target.value;
  localStorage.setItem('esforco', opt.esforco);
  // Mesmo caminho do modelo: vale do proximo turno em diante, via --effort.
};

$('btLimpar').onclick = async () => {
  if (!confirm('Apagar o historico guardado no celular?')) return;
  await fetch('/api/history/clear', { method: 'POST' });
  fio.textContent = ''; elResp = null; elPassos = null; seqNaTela = 0; rev = -1;
};

// Voltar de segundo plano: o fetch pendurado morreu com a aba congelada.
document.addEventListener('visibilitychange', () => {
  if (!document.hidden) observar();
});

carregarHistorico().then(observar);
