import {AGENTS, MISSION, PHASES, STEPS} from './demo-data.js';

const clone = value => JSON.parse(JSON.stringify(value));

export class HiveSimulation {
  constructor({now = () => performance.now(), schedule = fn => setInterval(fn, 100), cancel = id => clearInterval(id), scheduleTimeout = (fn, delay) => setTimeout(fn, delay), cancelTimeout = id => clearTimeout(id)} = {}) {
    this.now = now;
    this.schedule = schedule;
    this.cancel = cancel;
    this.scheduleTimeout = scheduleTimeout;
    this.cancelTimeout = cancelTimeout;
    this.listeners = new Set();
    this.timer = null;
    this.deliveryTimer = null;
    this.deliveryDueAt = 0;
    this.deliveryRemaining = 0;
    this.active = false;
    this.documentVisible = !document.hidden;
    this.state = {
      scenario:'mission', phase:'idle', running:false, manualPaused:false,
      elapsed:0, startedAt:0, adjusted:false, selected:null, selectedLink:null,
      showSubs:false, added:[], seq:0, form:false, reduced:false, drawers:{left:false,right:false,bottom:false},
      agentTab:'geral', missionTab:'plano', delivery:false,
      log:[],
    };
  }

  subscribe(listener) {
    this.listeners.add(listener);
    listener(this.snapshot());
    return () => this.listeners.delete(listener);
  }

  snapshot() {
    const phase = PHASES[this.state.phase] || PHASES.idle;
    const elapsed = this.currentElapsed();
    return {...clone(this.state), phaseId:this.state.phase, elapsed, phase:clone(phase), agents:this.agents(), progress:this.progress(elapsed), animationsPaused:!this.active||!this.documentVisible||this.state.manualPaused};
  }

  emit() { const value = this.snapshot(); this.listeners.forEach(fn => fn(value)); }
  currentElapsed() { return this.state.running ? this.state.elapsed + (this.now() - this.state.startedAt) : this.state.elapsed; }
  canRun() { return this.active && this.documentVisible && !this.state.manualPaused; }

  setLifecycle(active, visible = !document.hidden) {
    this.active = !!active;
    this.documentVisible = !!visible;
    if (!this.canRun()) { this.freezeClock(); this.freezeDelivery(); }
    else { this.resumeClock(); this.resumeDelivery(); }
    this.syncTimer();
    this.emit();
  }

  setDocumentVisible(visible) { this.setLifecycle(this.active, visible); }

  freezeClock() {
    if (!this.state.running) return;
    this.state.elapsed = this.currentElapsed();
    this.state.running = false;
  }

  clearDeliveryTimer() { if (this.deliveryTimer) this.cancelTimeout(this.deliveryTimer); this.deliveryTimer=null; this.deliveryDueAt=0; }
  freezeDelivery() { if (!this.deliveryTimer) return; this.deliveryRemaining=Math.max(0,this.deliveryDueAt-this.now()); this.clearDeliveryTimer(); }
  resumeDelivery() { if (this.state.phase!=='done'||this.state.delivery||!this.canRun()) return; if (!this.deliveryRemaining) return; const remaining=this.deliveryRemaining; this.deliveryRemaining=0; this.deliveryDueAt=this.now()+remaining; this.deliveryTimer=this.scheduleTimeout(()=>{this.deliveryTimer=null;this.deliveryDueAt=0;if(this.state.phase==='done'&&this.canRun()){this.state.delivery=true;this.emit();}},remaining); }
  armDelivery() { this.clearDeliveryTimer(); this.deliveryRemaining=this.state.reduced?400:1600; this.resumeDelivery(); }

  resumeClock() {
    const phase = PHASES[this.state.phase];
    if (this.state.running || this.state.manualPaused || !phase?.dur || phase.final || phase.failed) return;
    this.state.running = true;
    this.state.startedAt = this.now();
  }

  syncTimer() {
    if (this.canRun() && !this.timer) this.timer = this.schedule(() => this.tick());
    if (!this.canRun() && this.timer) { this.cancel(this.timer); this.timer = null; }
  }

  tick() {
    if (!this.canRun()) return;
    const phase = PHASES[this.state.phase];
    if (this.state.running && phase?.dur && this.currentElapsed() >= phase.dur) this.go(phase.next);
    else this.emit();
  }

  progress(elapsed = this.currentElapsed()) {
    const phase = PHASES[this.state.phase];
    if (!phase?.dur) return phase?.step ? 1 : 0;
    return Math.max(0, Math.min(1, elapsed / phase.dur));
  }

  stepProgress() {
    const groups={1:['p1a','p1b'],2:['p2a','p2b','p2c'],3:['p3a','p3b'],4:['p4a','p4b'],6:['p6a','p6b'],7:['p7a','p7b']};
    const phase=PHASES[this.state.phase],group=groups[phase?.step]||[],index=group.indexOf(this.state.phase);
    return index < 0 ? (phase?.step===5&&!phase?.failed&&this.state.phase!=='approval'?0.5:this.progress()) : Math.max(0,Math.min(1,(index+this.progress())/group.length));
  }

  go(phase, updates = {}) {
    if (!PHASES[phase]) return false;
    const previous = this.state.phase;
    this.state.phase = phase;
    this.state.elapsed = 0;
    this.state.startedAt = this.now();
    this.state.running = !!PHASES[phase].dur && this.canRun() && !this.state.manualPaused;
    Object.assign(this.state, updates);
    const current = PHASES[phase];
    if (phase === 'adj4' || (phase === 'approval' && previous.startsWith('adj'))) this.state.adjusted = true;
    if (current.step > 0 && phase !== previous) {
      const text = String(current.text || '').replaceAll('{n}', this.state.adjusted ? '3' : '4');
      const tag = current.final ? 'Missão concluída' : `Etapa ${current.step} · ${STEPS[current.step - 1][0]}${current.failed ? ' · falha' : ''}`;
      this.state.log.push({type:'event',id:phase,tag,text,kind:phase==='approval'?'approval':current.failed?'failed':current.final?'done':'working'});
    }
    this.clearDeliveryTimer(); this.deliveryRemaining=0;
    if (current.final) this.armDelivery();
    this.syncTimer();
    this.emit();
    return true;
  }

  start(text = MISSION) {
    if (this.state.scenario === 'empty') return false;
    this.state.manualPaused = false;
    this.state.log = [{type:'user', text:text || MISSION}];
    return this.go(this.state.scenario === 'failed' ? 'fail' : 'p1a', {adjusted:false, delivery:false, selectedLink:null});
  }

  pause() { if (!this.state.running && !this.deliveryTimer) return false; this.freezeClock(); this.freezeDelivery(); this.state.manualPaused = true; this.syncTimer(); this.emit(); return true; }
  resume() { if (this.state.running) return false; this.state.manualPaused = false; if (this.canRun()) { this.resumeClock(); this.resumeDelivery(); } this.syncTimer(); this.emit(); return true; }
  togglePause() { return this.state.manualPaused ? this.resume() : this.pause(); }
  approve() { if (this.state.phase !== 'approval') return false; this.state.log.push({type:'user',text:'Aprovar'}); return this.go('p6a'); }
  adjust() { if (this.state.phase !== 'approval') return false; this.state.log.push({type:'user',text:'Solicitar ajuste'}); return this.go('adj1'); }
  retry() { if (this.state.phase !== 'fail') return false; this.state.log.push({type:'user',text:'Tentar novamente'}); return this.go('retry'); }

  nextStep() {
    const phase = PHASES[this.state.phase];
    if (!phase?.next || this.state.phase === 'approval') return false;
    let next = phase.next;
    while (next && PHASES[next]?.step === phase.step && PHASES[next]?.dur && PHASES[next]?.next) next = PHASES[next].next;
    return this.go(next);
  }

  restart() {
    this.state.manualPaused = false;
    this.state.log = this.state.scenario === 'failed' ? [{type:'user',text:MISSION}] : [];
    return this.go(this.state.scenario === 'failed' ? 'fail' : 'idle', {adjusted:false, delivery:false, selectedLink:null});
  }

  setScenario(scenario) {
    if (!['mission','empty','failed'].includes(scenario)) return false;
    this.state.scenario = scenario;
    this.state.manualPaused = false;
    const reset={form:false,showSubs:false,selected:null,selectedLink:null,adjusted:false,delivery:false,log:[]};
    if (scenario === 'empty') return this.go('idle',{...reset,running:false});
    if (scenario === 'failed') return this.go('fail',{...reset,log:[{type:'user',text:MISSION}]});
    return this.go('idle',reset);
  }

  setReduced(value) { this.state.reduced = !!value; this.emit(); }
  selectAgent(id, fromHive = false) { const agent=this.agents().find(item=>item.id===id); if (!agent) return; if (this.state.selected===id) this.state.selected=null; else { this.state.selected=id; this.state.form=false; this.state.selectedLink=null; if (agent.kind==='sub') this.state.showSubs=true; if (fromHive) this.state.drawers.left=true; } this.emit(); }
  selectLink(id) { this.state.selectedLink = this.state.selectedLink === id ? null : id; this.emit(); }
  toggleSubs() { this.state.showSubs = !this.state.showSubs; this.emit(); }
  setAgentTab(tab) { if (['geral','tarefas','skills','ferramentas','relacoes'].includes(tab)) { this.state.agentTab = tab; this.emit(); } }
  setMissionTab(tab) { if (['plano','resp','conex','entrega'].includes(tab)) { this.state.missionTab = tab; this.emit(); } }
  toggleDrawer(name) { if (Object.hasOwn(this.state.drawers,name)) { this.state.drawers[name] = !this.state.drawers[name]; this.emit(); } }
  setDelivery(value) { this.state.delivery = !!value; this.emit(); }
  freeSlot() { if (this.state.scenario === 'empty') return null; return ['W','X1','X2'].find(slot => !this.state.added.some(agent => agent.slot === slot)) || null; }
  setWorkerForm(value) { this.state.form = !!value && !!this.freeSlot(); this.emit(); }

  sendMessage(text) {
    const clean = String(text || '').trim();
    if (!clean) return false;
    if (this.state.scenario === 'empty') return false;
    if (this.state.phase === 'idle' || PHASES[this.state.phase]?.final) return this.start(clean);
    this.state.log.push({type:'user', text:clean});
    this.state.log.push({type:'event', id:'queued', tag:'Demonstração', text:'A Rainha recebe um novo pedido quando a missão atual terminar.', kind:'idle'});
    this.state.drawers.bottom = true;
    this.emit();
    return true;
  }

  addWorker(name, spec) {
    name = String(name || '').trim(); spec = String(spec || '').trim();
    if (!name) return {ok:false,error:'Informe o nome da operária.'};
    if (name.length > 16) return {ok:false,error:'O nome pode ter até 16 caracteres.'};
    if (spec.length > 40) return {ok:false,error:'A especialidade pode ter até 40 caracteres.'};
    const slot = this.freeSlot();
    if (!slot) return {ok:false,error:'Os três espaços de demonstração já estão ocupados.'};
    const id = `demo-${++this.state.seq}`;
    this.state.added.push({id,kind:'added',slot,name,spec:spec||'Especialidade a definir',mission:'Operária criada por você nesta demonstração. A missão ainda não foi definida.',task:'Sem tarefa nesta missão.',duty:'Disponível para configuração futura',from:['rainha'],to:['rainha'],skills:[],tools:[],removable:true});
    this.state.selected = id;
    this.state.agentTab = 'geral';
    this.state.form = false;
    this.emit();
    return {ok:true,id};
  }

  removeSelected() {
    const index = this.state.added.findIndex(agent => agent.id === this.state.selected);
    if (index < 0) return false;
    this.state.added.splice(index,1);
    this.state.selected = null;
    this.emit();
    return true;
  }

  agents() {
    if (this.state.scenario === 'empty') return [];
    return [...AGENTS, ...this.state.added];
  }

  destroy() { if (this.timer) this.cancel(this.timer); if (this.deliveryTimer) clearTimeout(this.deliveryTimer); this.timer = null; this.deliveryTimer = null; this.listeners.clear(); }
}
