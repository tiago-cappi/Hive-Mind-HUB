# Issues — Redesign visual + UX da página /forestos

> Alvo único: `C:\Users\Meu Computador\Desktop\core-voice-hub-master\core-voice-hub-master\forestos.html` (self-contained). Branch: `feature/forestos-integration`, um commit por slice. Restrições em `prd.md` (Escopo/Fora + Contrato funcional intocável). Após cada slice: suíte verde (`./.venv/Scripts/python.exe -m pytest` na raiz + `node --test forestos/test/`) e `GET /forestos` → 200 com hooks `/forestos/state` e `/forestos/action`. NÃO tocar `server.py`/`forestos/`/`index.html`.

## Slices

### ISS-001 — Fundação visual HUD + shell dashboard com abas (F1, F5-base)
- **Slice:** Trocar tokens/reset/fonts e a linguagem de painéis por HUD C.O.R.E. e reestruturar o corpo da página num shell (barra de foco topo + barra de abas + containers de aba), com **todo o conteúdo funcional atual realocado** para dentro das abas — sem perder nenhum id/handler existente. Navegação de aba client-side funcional (uma aba visível por vez, "Visão Geral" default), sem reload.
- **Critério de aceite:**
  - `<style>` de `forestos.html` define os tokens HUD: `--bg`, `--bg2`, `--ink`, `--ink-bright`, `--ink-dim`, `--ink-faint`, `--line`, `--panel`, `--accent`, `--mono`, `--display`, `--chamf` (verificável por presença no CSS).
  - `.panel` usa `clip-path` chanfrado e `h3` de painel usa `--display`/uppercase; fundo tem scanlines/vinheta (elementos/regras presentes).
  - Existe uma barra de abas com ≥2 abas e um mecanismo JS que mostra só o painel da aba ativa; ao trocar de aba, nenhum `location.reload`/navegação é usada.
  - Todos os ids/handlers funcionais do arquivo antigo continuam presentes (ver ISS-002..005 para a lista); `GET /forestos` → 200 e o HTML contém `fetch('/forestos/state')` e `/forestos/action`.
  - Suíte pytest + node --test verdes (as asserções de `test_forestos_page.py` que dependem de markup movido podem ser atualizadas nesta ou nas slices seguintes, sem afrouxar cobertura de comportamento).
- **Status:** em-andamento

### ISS-002 — Barra de foco fixa no topo (F2)
- **Slice:** Barra de foco sempre visível no topo em qualquer aba, com timer grande display, entidade focada, XP previsto, controles e estado vazio elegante.
- **Critério de aceite:**
  - Existem `#focusTitle`, `#focusTimer`, `#focusXp` e os botões `#focusStartBtn`, `#focusStopBtn`, `#focusManualBtn`, `#focusCancelBtn`.
  - `tickFocus()` recalcula sempre de `started_at` usando `Date.now()` e **não** incrementa contador acumulado (`elapsed++`/`elapsed +=`); pomodoro regressivo preservado; XP = `elapsedMin*imp*dif/10`.
  - `stopFocusManual()` envia `focus`+`stop`+minutos; `stopFocus`→`focus stop`; `cancelFocus`→`focus cancel`; abrir multi-form pelo botão de iniciar.
  - Sem foco: `#focusTitle`="Nenhum foco ativo", `#focusTimer`="00:00", `#focusXp` zerado.
  - Barra permanece visível ao trocar de aba (verificável: o container da barra não está dentro de um painel de aba que é ocultado).
  - Botões dão flash visual e `doAction` continua sem `/speak`. Suíte verde.
- **Status:** em-andamento

### ISS-003 — Aba "Visão Geral" (F3)
- **Slice:** Aba default que resume o dia (perfil/XP/nível, missões de maior peso, hábitos de hoje, lembretes vencidos/próximos), reusando os dados e handlers existentes.
- **Critério de aceite:**
  - Ao carregar a página, a aba "Visão Geral" é a ativa.
  - Mostra XP total e nível (via `state.profile`/`renderProfile` ou equivalente com `#profileXp`), missões de maior peso com tier de cor, hábitos com streak/feito-hoje, e lembretes vencidos destacados / próximos.
  - Empty states desenhados quando uma lista está vazia (texto/placeholder visível, sem quebrar layout).
  - Ações disparadas da Visão Geral usam os mesmos comandos das abas dedicadas (nenhum endpoint novo). Suíte verde.
- **Status:** em-andamento

### ISS-004 — Abas Missões, Hábitos e Multi-missão (F4)
- **Slice:** Conteúdo operacional realocado com estética HUD, mantendo todas as ações.
- **Critério de aceite:**
  - Missões: `renderMissions` + `pesoTier` presentes; classes `btn-focus-mission`, `btn-harvest`, `btn-create-mission`; ▶ chama `focus start mission`, 🌾 chama `harvest`, ➕ chama `criar missao`; tier de cor+glow por peso.
  - Hábitos: `renderHabits` + `doneToday`/`done-today`; classes `btn-habit-focus`, `btn-habit-complete`, `btn-habit-uncomplete`, `btn-create-habit`; chamam `focus start habit`/`habit complete`/`habit uncomplete`/`criar habito`; streak visível.
  - Multi-missão: `#multiMode`, presets `data-min="15|25|45|60"`, `#multiCustomMin`, `#multiImportance`, `#multiDifficulty`; mini-missões `multiMiniAddBtn`/`mini-toggle`/`mini-remove`; iniciar chama `focus start multi <json>` com modo/pomoDuration/importance/difficulty/miniMissions.
  - Empty states quando listas vazias. Suíte verde.
- **Status:** em-andamento

### ISS-005 — Aba Cartografia + Heatmaps (F6)
- **Slice:** Árvore + órfãos + criar entidades e heatmaps repaginados.
- **Critério de aceite:**
  - `renderCartografia` presente, usa `orphanMissions`; `btn-create-entity` chama `criar` para setor/projeto/objetivo.
  - `renderHeatmap` + `heatTier` presentes; consome `focusByDay` e `habitCompletionsByDay`; células arredondadas com escala verde; cada célula tem `title` (tooltip) com data e valor.
  - Empty states quando sem dados. Suíte verde.
- **Status:** em-andamento

### ISS-006 — Aba Lembretes + Anotações + polimento final + testes (F7)
- **Slice:** Lembretes e Anotações repaginados (alarme intocado), passe de polimento (microinterações, espaçamento 4/8px, skeleton/empty, responsividade, acessibilidade) e atualização/execução da suíte completa.
- **Critério de aceite:**
  - Lembretes: `renderReminders` + `btn-reminder-ack` (→`reminder ack`) + `btn-create-reminder` (→`criar lembrete`) + destaque `reminder-overdue`.
  - Anotações: `renderAnotacoes` + `anotacao-card` (respeita `bg_color`) + `btn-create-anotacao` (→`criar anotacao`).
  - Alarme idêntico: `REMINDER_TOLERANCE_MS = 2*60*60*1000`, `reminderDueDate` usa `time_of_day/due_at/custom_days/frequency`, `reminderAlarmState` usa `last_acked_at`+tolerância, `checkReminders` dispara `playEarcon()` + `/speak` e guarda `alarmedToday` (`.has`/`.add`), checado por `setInterval(() => checkReminders(...))`; `localDateIso` preservado; `doAction` sem `/speak`.
  - Responsivo: em viewport estreita as colunas empilham, sem scroll horizontal (verificável por CSS: grid/flex com fallback de coluna única / media query).
  - Acessibilidade: `:focus-visible` definido e botões com `title`/aria-label.
  - `test_forestos_page.py` atualizado para o novo markup (sem afrouxar); suíte completa verde: `./.venv/Scripts/python.exe -m pytest` na raiz e `node --test forestos/test/`; smoke `GET /forestos` → 200 com hooks `/forestos/state` e `/forestos/action`.
- **Status:** em-andamento

## Reprovas do Juíz

### R1 — ISS-004 — Aba "Multi-missão" abre vazia (formulário permanece invisível)
- **O quê:** Ao entrar na aba "Multi-missão" pela barra de abas, o painel mostra só o título "Multi-missão"; o formulário de configuração (`#multiForm`) e todos os seus controles (modo, presets 15/25/45/60, custom, mini-missões, importância/dificuldade, `▶ iniciar sessão`) ficam `display:none`. Não existe nenhum gatilho dentro da própria aba para exibir o form — o único que o abre vive fora dela.
- **Onde:** `forestos.html` — CSS `#multiForm{ display:none; }` (linha 189) só é revertido por `#multiForm.open{ display:flex }` (linha 190); a classe `.open` é adicionada apenas por `openMultiForm()` (linhas 538-540), que está ligado exclusivamente ao `#focusStartBtn` da barra de foco (linha 232). O botão da aba (linha 244) chama só `onclick="selectTab('multi')"`, e `selectTab()` (linhas 396-406) não toca em `#multiForm`.
- **Por que falha:** F4 pede a Multi-missão "realocada em aba de conteúdo, mantendo 100% das ações e controles" e F5 pede que "ao clicar numa aba, só o painel dela fica visível" — mas o painel aparece sem conteúdo utilizável. É um beco-sem-saída dentro da aba: quem clica na aba dedicada não tem como usar/abrir a configuração ali; precisa descobrir que o gatilho está no botão da barra de foco. Os testes estáticos (`test_forestos_page.py`) só checam presença de elementos no markup e não pegam esse toggle, por isso a suíte passa mesmo com o defeito.
- **Como reproduzir:** `GET /forestos` (servido 200 pelo `server.py`), clicar na aba "Multi-missão". Observado: o painel exibe apenas o cabeçalho "Multi-missão"; nenhum dos controles (`#multiMode`, presets, `#multiStartBtn`, etc.) fica visível. Esperado: o formulário de configuração visível — ou um controle dentro da aba para abri-lo — ao selecionar a aba.
- **Status:** corrigido — `#multiForm` agora é `display:flex` fixo (linha 189), sem classe `.open` nem `display:none`; o form fica visível ao entrar na aba, sem gatilho externo. Verificado pelo teste `test_multi_form_visivel_ao_entrar_na_aba_sem_gatilho_externo` (passa) e por inspeção do markup/CSS.
