// Seletores existentes espelhados, com preferências separadas por assistente.
export const EFFORT_LABELS = {
  none:'Nenhum', minimal:'Mínimo', low:'Baixo', medium:'Médio', high:'Alto',
  xhigh:'Extra alto', max:'Máximo', ultra:'Ultra',
};

export class ModelPicker {
  constructor(onChange) {
    this.modelSelects = ['model','dockModel','modalModel'].map(id => document.getElementById(id));
    this.effortSelects = ['effort','dockEffort','modalEffort'].map(id => document.getElementById(id));
    this.originalModels = [...this.modelSelects[0].options].map(o => [o.text, o.value]);
    this.originalEfforts = [...this.effortSelects[0].options].map(o => [o.text, o.value]);
    this.provider = 'claude';
    this.saved = {claude:this.capture(), codex:{model:'gpt-6.1-sol', effort:''}};
    try {
      const saved = JSON.parse(localStorage.getItem('core.codex.selection') || 'null');
      if (saved && typeof saved.model === 'string' && typeof saved.effort === 'string') this.saved.codex = saved;
    } catch {}
    this.models = [];
    this.source = 'unavailable';
    this.onChange = onChange;
    this.modelSelects.forEach(select => select.addEventListener('change', () => {
      this.saved[this.provider].model = select.value;
      this.render(); this.persist(); this.onChange();
    }));
    this.effortSelects.forEach(select => select.addEventListener('change', () => {
      this.saved[this.provider].effort = select.value;
      this.render(); this.persist(); this.onChange();
    }));
  }

  capture() { return {model:this.modelSelects[0].value, effort:this.effortSelects[0].value}; }

  selection(provider) {
    return provider === this.provider ? this.capture() : {...this.saved[provider]};
  }

  async load() {
    try {
      const response = await fetch('/codex-ui/models', {cache:'no-store'});
      if (!response.ok) throw new Error('catálogo indisponível');
      const catalog = await response.json();
      this.models = catalog.models.filter(m => typeof m.id === 'string' && Array.isArray(m.efforts));
      this.source = catalog.source;
    } catch { this.models = []; }
    if (this.provider === 'codex') this.render();
    this.onChange();
  }

  setProvider(provider) {
    this.saved[this.provider] = this.capture();
    this.provider = provider;
    this.render();
  }

  options(selects, items, value) {
    selects.forEach(select => {
      select.replaceChildren(...items.map(([label, id]) => new Option(label, id)));
      select.value = value;
    });
  }

  render() {
    const saved = this.saved[this.provider];
    if (this.provider === 'claude') {
      this.options(this.modelSelects, this.originalModels, saved.model);
      this.options(this.effortSelects, this.originalEfforts, saved.effort);
      this.modelSelects.forEach(s => s.disabled = false);
      this.effortSelects.forEach(s => s.disabled = false);
      return;
    }
    const model = this.models.find(m => m.id === saved.model) || this.models[0];
    if (!model) {
      this.options(this.modelSelects, [['CATÁLOGO INDISPONÍVEL','']], '');
      this.options(this.effortSelects, [['PADRÃO','']], '');
      [...this.modelSelects, ...this.effortSelects].forEach(s => s.disabled = true);
      return;
    }
    saved.model = model.id;
    if (saved.effort && !model.efforts.includes(saved.effort)) saved.effort = '';
    this.options(this.modelSelects, this.models.map(m => [m.name.toUpperCase(), m.id]), saved.model);
    const efforts = [[`PADRÃO · ${EFFORT_LABELS[model.defaultEffort] || model.defaultEffort}`, ''],
      ...model.efforts.map(e => [(EFFORT_LABELS[e] || e).toUpperCase(), e])];
    this.options(this.effortSelects, efforts, saved.effort);
    [...this.modelSelects, ...this.effortSelects].forEach(s => s.disabled = false);
  }

  persist() {
    if (this.provider === 'codex') {
      try { localStorage.setItem('core.codex.selection', JSON.stringify(this.saved.codex)); } catch {}
    }
  }

  label() {
    const saved = this.saved[this.provider];
    if (this.provider === 'claude') return `${this.modelSelects[0].selectedOptions[0]?.text || ''} · ${saved.effort || 'PADRÃO'}`;
    const model = this.models.find(m => m.id === saved.model);
    if (!model) return 'CATÁLOGO INDISPONÍVEL';
    return `${model.name} · ${EFFORT_LABELS[saved.effort || model.defaultEffort] || 'PADRÃO'}`.toUpperCase();
  }
}
