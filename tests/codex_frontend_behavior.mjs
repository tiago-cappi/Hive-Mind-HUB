// Exercita código real sem navegador, microfone, processos de IA ou rede.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {ModelPicker} from '../codex_frontend/static/models.js';
import {CodexGalaxy} from '../codex_frontend/static/galaxy.js';

const source = fs.readFileSync(new URL('../index.html', import.meta.url), 'utf8');
function definition(name) {
  let start = source.indexOf('function ' + name + '(');
  if (source.slice(start - 6, start) === 'async ') start -= 6;
  const brace = source.indexOf('{', start);
  let depth = 1, end = brace + 1;
  for (; depth; end++) depth += (source[end] === '{') - (source[end] === '}');
  return source.slice(start, end);
}

let calls = 0;
const tab = {provider:'codex', ui:'idle', titulo:'Codex', turns:[{who:'EU', text:'teste local'}], changes:[]};
const context = vm.createContext({
  window:{hubProviders:{allowAction:() => false, accepts:t => (t.provider || 'claude') === 'codex', current:() => 'codex'}},
  fetch:() => { calls++; throw new Error('Não deve acessar Claude'); },
  getMic:() => { calls++; throw new Error('Não deve abrir microfone'); },
  activeTab:() => tab, recordTurn:() => { calls++; },
  finishIdle:t => { t.ui = 'idle'; },
  dbg:() => {}, renderActiveTranscript:() => {}, applyUiIfActive:() => {}, renderTabBar:() => {}, renderConvList:() => {},
  tabs:[tab], activeIdx:0, MAX_TABS:6, newTab:() => ({...tab, turns:[]}),
  history:[], tickClockStamp:() => '12:00', els:{convs:{hidden:true}},
});
for (const name of ['startListening','sendTextPrompt','runSkill','askAndSpeak','onStop','addTab','closeTab','onNewConv'])
  vm.runInContext(definition(name), context);
await context.startListening();
context.sendTextPrompt('teste');
context.runSkill(tab, 'REVISAR DIA');
await context.askAndSpeak(tab, 'teste');
tab.ui = 'think'; context.onStop(); assert.equal(tab.ui, 'idle');
await context.addTab(); assert.equal(context.tabs.length, 2);
await context.closeTab(1); assert.equal(context.tabs.length, 1);
await context.onNewConv(); assert.equal(context.history[0].provider, 'codex');
assert.equal(calls, 0, 'ações Codex não podem executar efeitos Claude');

class Select {
  constructor(options) { this.options = options.map(([text,value]) => ({text,value})); this.value = this.options[0].value; this.events = {}; }
  addEventListener(type, listener) { this.events[type] = listener; }
  replaceChildren(...options) { this.options = options; this.value = options[0]?.value || ''; }
  get selectedOptions() { return this.options.filter(o => o.value === this.value); }
  choose(value) { this.value = value; this.events.change(); }
}
globalThis.Option = class { constructor(text, value) { this.text = text; this.value = value; } };
const selects = {};
for (const id of ['model','dockModel','modalModel']) selects[id] = new Select([['OPUS 5','OPUS 5'], ['SONNET 5','SONNET 5']]);
for (const id of ['effort','dockEffort','modalEffort']) selects[id] = new Select([['PADRÃO',''], ['HIGH','high']]);
selects.model.value = 'SONNET 5'; selects.effort.value = 'high';
globalThis.document = {getElementById:id => selects[id]};
const storage = new Map();
globalThis.localStorage = {getItem:k => storage.get(k), setItem:(k,v) => storage.set(k,v)};
const picker = new ModelPicker(() => {});
picker.models = JSON.parse(fs.readFileSync(new URL('../codex_frontend/models.json', import.meta.url), 'utf8'));
picker.setProvider('codex');
assert.ok(selects.dockEffort.options.some(o => o.value === 'ultra'));
selects.dockEffort.choose('ultra');
assert.equal(selects.modalEffort.value, 'ultra');
selects.dockModel.choose('gpt-6-luna');
assert.ok(!selects.dockEffort.options.some(o => o.value === 'ultra'));
assert.equal(selects.effort.value, '', 'esforço incompatível deve voltar ao padrão');
selects.dockEffort.choose('max');
picker.setProvider('claude');
assert.equal(selects.model.value, 'SONNET 5');
assert.equal(selects.effort.value, 'high');
assert.ok(!selects.dockEffort.options.some(o => o.value === 'ultra'));
picker.setProvider('codex');
assert.equal(selects.model.value, 'gpt-6-luna'); assert.equal(selects.effort.value, 'max');
assert.equal(selects.modalEffort.value, 'max');
assert.deepEqual(picker.selection('claude'), {model:'SONNET 5', effort:'high'});
const detached = picker.selection('claude'); detached.model = 'OPUS 5';
assert.equal(picker.selection('claude').model, 'SONNET 5');
console.log('Codex: isolamento de efeitos, sessões locais e seletores compatíveis aprovados.');

// Transições reais diferidas: STT Claude em background e mic que abre após troca.
function deferred() {
  let resolve;
  const promise = new Promise(r => { resolve = r; });
  return {promise, resolve};
}
const claude = {provider:'claude', sid:'claude-stt', titulo:'Claude', earconHz:220, ui:'listen'};
const codex = {provider:'codex', sid:'codex-local', ui:'idle'};
let focused = claude;
const stt = deferred(), complete = deferred();
const posts = [];
const noop = () => {};
const voice = vm.createContext({
  window:{hubProviders:{allowAction:t => t.provider !== 'codex',
    selection:p => picker.selection(p)}},
  activeTab:() => focused, tabs:[claude,codex], els:{model:selects.model, effort:selects.effort, main:{disabled:true}},
  pendingSend:true, rec:{mimeType:'audio/webm'}, chunks:[new Blob(['audio'])],
  Blob, FormData, AbortController, TextDecoder, performance,
  STT_MAX_MS:1000, setTimeout:() => 1, clearTimeout:noop, setInterval:() => 1, clearInterval:noop,
  clearRecCap:noop, dbg:noop, applyUiIfActive:noop, renderTabBar:noop,
  setStep:noop, clearWatchdog:noop, clearLiveResp:noop, clearPlan:noop,
  hideErrBanner:noop, clearActivity:noop, recordTurn:noop, finalizeResp:noop,
  setSpeaking:noop,
  finishIdle:t => { t.ui = 'idle'; complete.resolve(); },
  fetch:async (path, options) => {
    if (path === '/stt') return stt.promise;
    posts.push({path, body:JSON.parse(options.body)});
    return {ok:true, status:200, body:{getReader:() => ({read:async () => ({done:true,
      value:new TextEncoder().encode('{"t":"done","reply":"ok","spoken":true}\n')})})}};
  },
});
for (const name of ['currentModel','currentEffort','onRecStop','askAndSpeak','streamAsk'])
  vm.runInContext(definition(name), voice);
picker.setProvider('claude');
selects.model.choose('SONNET 5'); selects.effort.choose('high');
const transcribing = voice.onRecStop(claude);
assert.equal(claude.ui, 'think');
focused = codex; picker.setProvider('codex');
selects.model.choose('gpt-6.1-sol'); selects.effort.choose('ultra');
assert.equal(voice.currentModel(), 'gpt-6.1-sol');
assert.equal(voice.currentModel(claude), 'sonnet');
assert.equal(voice.currentEffort(claude), 'high');
// Mesmo uma nova preferência Claude não muda a configuração do turno já enviado.
picker.saved.claude = {model:'OPUS 5', effort:'max'};
stt.resolve({status:200, json:async () => ({texto:'voz transcrita após a troca'})});
await transcribing; await complete.promise;
assert.equal(posts.length, 1);
assert.deepEqual(posts[0], {path:'/ask', body:{texto:'voz transcrita após a troca',
  modelo:'sonnet', esforco:'high', sid:'claude-stt', titulo:'Claude', earcon_hz:220}});

let released = 0, recorded = 0, metered = 0;
const opening = deferred();
claude.ui = 'idle'; focused = claude;
voice.getMic = () => opening.promise;
voice.stream = null;
voice.MediaRecorder = class { constructor() { recorded++; } start() {} };
voice.pickMime = () => '';
voice.armRecCap = noop;
voice.startMeter = () => { metered++; };
vm.runInContext(definition('startListening'), voice);
const capturing = voice.startListening();
focused = codex;
opening.resolve({getTracks:() => [{stop:() => { released++; }}]});
await capturing;
assert.equal(released, 1, 'aquisição obsoleta deve liberar todas as tracks');
assert.equal(recorded, 0); assert.equal(metered, 0);
assert.equal(voice.stream, null); assert.equal(claude.ui, 'idle');
assert.equal(voice.els.main.disabled, true, 'Codex permanece sem captura habilitada');
// A captura válida Claude continua funcionando.
focused = claude;
voice.getMic = async () => ({getTracks:() => [], getAudioTracks:() => [{label:'teste'}]});
await voice.startListening();
assert.equal(recorded, 1); assert.equal(metered, 1); assert.equal(claude.ui, 'listen');
assert.equal(voice.els.main.disabled, false);
console.log('Codex: STT diferido conserva configuração Claude; mic obsoleto é liberado.');

globalThis.ResizeObserver = class { observe() {} };
globalThis.window = {devicePixelRatio:1};
let scheduled = 0, cancelled = 0;
globalThis.requestAnimationFrame = () => ++scheduled;
globalThis.cancelAnimationFrame = () => cancelled++;
globalThis.Path2D = class { rect() {} moveTo() {} lineTo() {} };
const ctx = new Proxy({}, {get:(_, key) => key === 'createRadialGradient'
  ? () => ({addColorStop() {}}) : () => {}});
const canvas = {getContext:() => ctx, getBoundingClientRect:() => ({width:1280,height:720})};
let phase = 'idle';
const galaxy = new CodexGalaxy(canvas, canvas, {getState:() => phase, getLevel:() => .8});
assert.equal(galaxy.gal.n, 10500);
galaxy.setActive(true);
galaxy.frame(galaxy.last + 50);
assert.equal(galaxy.lvl, 0, 'idle não pode inventar amplitude de áudio');
phase = 'speak'; galaxy.frame(galaxy.last + 50);
assert.ok(galaxy.p.blue > 0 && galaxy.lvl > 0, 'fala reage ao estado/áudio fornecidos');
galaxy.setVariant('B'); assert.equal(galaxy.gal.n, 7800);
galaxy.setActive(false); assert.ok(cancelled > 0);
const count = scheduled; galaxy.frame(galaxy.last + 50); assert.equal(scheduled, count);
console.log('Codex: geometria original, estado/áudio e pausa do loop aprovados.');
