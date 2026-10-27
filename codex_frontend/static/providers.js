// Navegação de assistentes e ligação do tema aos componentes reais do Hub.
import {CodexGalaxy} from './galaxy.js';
import {ModelPicker} from './models.js';

const hub = window.hubFrontend;
const originalTitle = document.title;
const byId = id => document.getElementById(id);
const link = document.createElement('link');
link.rel = 'stylesheet'; link.href = '/codex-ui/static/codex.css';
document.head.appendChild(link);

let selected = 'claude', preferred = 'claude', selectedPage = 'claude', preferredPage = 'claude', audioLevel = 0;
const pages = new Map();
const lastSession = new Map();
const drafts = {claude:{mode:hub.textMode, text:byId('textInput').value}, codex:{mode:false, text:''}};
try { if (localStorage.getItem('core.assistant') === 'codex') preferred = 'codex'; } catch {}
try { if (['claude','codex','hive'].includes(localStorage.getItem('core.page'))) preferredPage = localStorage.getItem('core.page'); } catch {}

const chrome = document.createElement('div');
chrome.id = 'assistantChrome';
chrome.innerHTML = `
  <div id="codexAtmosphere" aria-hidden="true"></div>
  <canvas id="codexGalaxy" aria-hidden="true"></canvas>
  <div id="codexFrame" aria-hidden="true"><i></i><i></i><i></i></div>
  <div id="codexNucleus">NÚCLEO · CODEX</div>
  <div id="assistantNavigation">
    <nav aria-label="Página"><button type="button" data-assistant="claude"><i></i>CLAUDE CODE</button><button type="button" data-assistant="codex"><i></i>CODEX</button><button type="button" data-page="hive"><i></i>HIVE MIND</button></nav>
    <div id="assistantModelReadout"></div>
  </div>
  <canvas id="codexMeter" aria-hidden="true"></canvas>
  <div id="codexBackendNote" role="status">BACKEND CODEX · INTEGRAÇÃO PENDENTE</div>
  <div id="codexVariants"><span>GALÁXIA</span><button type="button" data-variant="A" aria-label="Galáxia Via Láctea" aria-pressed="true">A</button><button type="button" data-variant="B" aria-label="Galáxia Grande desenho" aria-pressed="false">B</button></div>`;
document.body.appendChild(chrome);

const actions = document.createElement('div');
actions.id = 'codexDockActions';
byId('txPanel').appendChild(actions);
const controls = ['textForm','modeToggle','pause','newconv','stop'].map(id => {
  const element = byId(id), anchor = document.createComment(`original ${id}`);
  element.before(anchor);
  return {element, anchor};
});
const skillTitles = new Map([...document.querySelectorAll('#skills .skill')].map(b => [b, b.getAttribute('title')]));
const picker = new ModelPicker(updateReadout);
const galaxy = new CodexGalaxy(byId('codexGalaxy'), byId('codexMeter'), {
  getState:() => document.body.dataset.state,
  getLevel:() => audioLevel,
});

function current() { return hub.isMinimal ? selected : 'claude'; }
function accepts(tab) { return (tab.provider || 'claude') === current(); }
function currentPage() { return hub.isMinimal ? selectedPage : 'claude'; }
function canUseAssistantUI() { return currentPage() !== 'hive'; }

function allowAction(tab) {
  if (tab.provider !== 'codex') return true;
  hub.log('INFO', 'Codex: integração do backend pendente; comando não enviado.');
  return false;
}

function syncControls(tab) {
  const pending = tab.provider === 'codex';
  if (pending) { byId('main').disabled = true; byId('textSend').disabled = true; }
  byId('main').title = pending ? 'Disponível após integrar o backend Codex' : '';
  byId('modalSend').disabled = pending;
  byId('pause').disabled = pending;
  byId('stop').disabled = pending;
  document.querySelectorAll('#skills .skill').forEach(button => {
    button.disabled = pending;
    if (pending) button.title = 'Disponível após integrar o backend Codex';
    else if (skillTitles.get(button) === null) button.removeAttribute('title');
    else button.setAttribute('title', skillTitles.get(button));
  });
}

function updateReadout() {
  if (currentPage() === 'hive') {
    byId('assistantModelReadout').textContent = 'HIVE MIND · MISSÕES COM CLAUDE E CODEX';
    return;
  }
  byId('assistantModelReadout').textContent = picker.label();
  const note = picker.source === 'snapshot' ? ' · CATÁLOGO DE REFERÊNCIA' : '';
  byId('codexBackendNote').textContent = 'BACKEND CODEX · INTEGRAÇÃO PENDENTE' + note;
}

function decorate() {
  const page = currentPage(), codex = page === 'codex';
  document.body.dataset.assistant = current();
  document.body.dataset.page = page;
  document.title = page === 'hive' ? 'C.O.R.E. — Hive Mind' : codex ? 'C.O.R.E. — Codex' : originalTitle;
  controls.forEach(({element, anchor}) => {
    if (codex) actions.appendChild(element);
    else anchor.after(element);
  });
  chrome.querySelectorAll('[data-assistant]').forEach(button => {
    const on = button.dataset.assistant === page;
    button.classList.toggle('on', on);
    button.setAttribute('aria-pressed', String(on));
  });
  chrome.querySelectorAll('[data-page]').forEach(button => {
    const on = button.dataset.page === page;
    button.classList.toggle('on', on); button.setAttribute('aria-pressed', String(on));
  });
  galaxy.setActive(codex && !document.hidden);
  syncControls(hub.active);
  updateReadout();
}

function select(provider, remember = true) {
  if (provider !== 'claude' && provider !== 'codex') return false;
  if (provider !== selected && hub.active.ui === 'listen') {
    hub.log('WARN', 'termine ou envie a gravação antes de trocar de assistente'); return false;
  }
  let tab = hub.tabs.find(t => (t.provider || 'claude') === provider && t.sid === lastSession.get(provider))
    || hub.tabs.find(t => (t.provider || 'claude') === provider);
  if (!tab && hub.tabs.length >= 6) {
    hub.log('WARN', 'Feche uma sessão para abrir o outro assistente; limite de 6 sessões.'); return false;
  }
  hub.closeComposer();
  if (provider !== selected) {
    lastSession.set(selected, hub.active.sid);
    drafts[selected] = {mode:hub.textMode, text:byId('textInput').value};
    selected = provider;
    picker.setProvider(provider);
    if (!tab) { hub.createSession(); tab = hub.active; }
    else hub.selectSession(hub.tabs.indexOf(tab));
    hub.restoreInput(drafts[provider]);
    hub.refresh();
  }
  if (remember) {
    preferred = provider;
    preferredPage = provider;
    try { localStorage.setItem('core.assistant', provider); } catch {}
    try { localStorage.setItem('core.page', provider); } catch {}
  }
  const previousPage = selectedPage;
  selectedPage = provider;
  if (previousPage !== selectedPage) pages.get(previousPage)?.deactivate?.();
  decorate();
  return true;
}

function selectPage(page, remember = true) {
  if (page === 'claude' || page === 'codex') return select(page, remember);
  if (page !== 'hive' || !hub.isMinimal || !pages.has(page)) return false;
  if (selectedPage !== page && hub.active.ui === 'listen') {
    hub.log('WARN', 'termine ou envie a gravação antes de trocar de página'); return false;
  }
  hub.closeComposer();
  const previousPage = selectedPage;
  selectedPage = page;
  if (remember) {
    preferredPage = page;
    try { localStorage.setItem('core.page', page); } catch {}
  }
  if (previousPage !== page) {
    pages.get(previousPage)?.deactivate?.();
    pages.get(page)?.activate?.();
  }
  decorate();
  return true;
}

window.hubProviders = {
  current, currentPage, canUseAssistantUI, accepts, allowAction, syncControls,
  registerPage(id, lifecycle) {
    if (id !== 'hive' || !lifecycle) return false;
    pages.set(id, lifecycle);
    if (hub.isMinimal && preferredPage === id) {
      selectedPage = id; lifecycle.activate?.(); decorate();
    } else if (currentPage() === id) lifecycle.activate?.();
    else lifecycle.deactivate?.();
    return true;
  },
  selectPage,
  selection(provider) { return picker.selection(provider); },
  beforeModeChange(on) {
    if (!on) {
      pages.get(selectedPage)?.deactivate?.();
      selectedPage = 'claude';
      if (selected === 'codex') select('claude', false);
    }
  },
  afterModeChange(on) {
    if (on && preferredPage === 'hive') selectPage('hive', false);
    else if (on) select(preferredPage === 'codex' ? 'codex' : preferred, false);
    else decorate();
  },
  stateChanged() { if (currentPage() === 'codex') syncControls(hub.active); },
  setAudioLevel(pct) { audioLevel = Math.max(0, Math.min(1, Number(pct) / 100 || 0)); },
};

chrome.querySelectorAll('[data-assistant]').forEach(button => {
  button.onclick = () => select(button.dataset.assistant);
});
chrome.querySelectorAll('[data-page]').forEach(button => { button.onclick = () => selectPage(button.dataset.page); });
chrome.querySelectorAll('[data-variant]').forEach(button => button.addEventListener('click', () => {
  galaxy.setVariant(button.dataset.variant);
  chrome.querySelectorAll('[data-variant]').forEach(b => b.setAttribute('aria-pressed', String(b === button)));
}));
document.addEventListener('visibilitychange', () => galaxy.setActive(currentPage() === 'codex' && !document.hidden));
decorate();
await picker.load();
if (hub.isMinimal) {
  select(preferredPage === 'codex' ? 'codex' : preferred, false);
}
