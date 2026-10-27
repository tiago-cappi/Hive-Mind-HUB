# PRD — Redesign visual + UX da página /forestos (Hub C.O.R.E.)

## Contexto

A página ForestOS (`forestos.html`, servida em `GET /forestos` pelo `server.py`, porta 8765) está 100% funcional, mas o design é "feio e simplista demais": grade estática de 9 painéis iguais, sem hierarquia, sem a identidade HUD do resto do Hub. Este ciclo é **redesign visual + UX** — reorganiza layout, hierarquia e navegação e aplica a estética HUD C.O.R.E. (a mesma de `index.html`). **A lógica de dados/ações NÃO muda**: mesmos endpoints, payloads, whitelist, regras de negócio e semântica de ações. O arquivo continua self-contained (CSS/JS inline), só fonts/ícones/libs pequenas podem vir de CDN, com degradação graciosa offline.

## Escopo

- **Dentro:**
  - Reescrita da apresentação de `forestos.html`: design tokens HUD (paleta warm-dark honey+ink+sage, fontes JetBrains Mono + Space Grotesk, painéis chanfrados, scanlines/vinheta, dots de status com glow, uppercase letter-spacing, `tabular-nums`).
  - Novo layout: **barra de foco fixa no topo** (sempre visível) + **shell dashboard com abas** client-side (aba padrão "Visão Geral" + demais seções em abas).
  - Microinterações (hover/active/`:focus-visible`, transições curtas), empty/skeleton states desenhados, tiers de missão com cor+glow, heatmap polido (células arredondadas, tooltip data/minutos), feedback visual silencioso de ação.
  - Responsividade (desktop multi-coluna → estreito empilhado, sem scroll horizontal) e acessibilidade básica (contraste, `:focus-visible`, `title`/aria-label nos botões).
  - Atualização das asserções de `test_forestos_page.py` para refletir o novo markup (testar o novo, sem afrouxar cobertura de comportamento).
- **Fora:**
  - `server.py` (salvo ajuste trivial se um teste de estático exigir), `forestos/` (CLI/engine), `index.html`, Finanças, qualquer coisa do vault.
  - Mudança de endpoints, payloads, whitelist de ações, regras de XP/foco/streak, semântica de qualquer ação.
  - Mudança da lógica do alarme de lembretes (só a apresentação visual dele muda).
  - Novas dependências instaladas localmente; qualquer CDN é opcional e não pode ser requisito de funcionamento de dados/ações.

## Contrato funcional intocável (comportamento que já existe e DEVE continuar idêntico)

Referência do payload de estado (`GET /forestos/state`, JSON do `cli.js dashboard`), consumido em `renderAll`:
`focus`, `missionsBySector` (obj setor→[missões]), `habits[]`, `cartografia{tree[],orphanMissions[]}`, `heatmaps{focusByDay,habitCompletionsByDay}`, `profile{total_xp,level}`, `sectorSummary{rows[]}`, `reminders[]`, `anotacoes[]`.

Ações via `POST /forestos/action {cmd, args}` (whitelist no server.py), sempre seguidas de refresh de estado:
- `focus [start mission <name>]`, `focus [start habit <name>]`, `focus [start multi <json>]`, `focus [stop]`, `focus [stop <min>]`, `focus [cancel]`
- `harvest <name>`; `habit [complete <name>]`, `habit [uncomplete <name>]`
- `reminder [ack <name>]`; `criar <tipo> <json>`

Regras de tempo/alarme que não mudam: polling 3s + refresh pós-ação; timer de foco recalculado de `started_at` a cada 1s (nunca contador em memória); pomodoro regressivo; XP previsto = `elapsedMin * imp * dif / 10`; alarme de lembrete (earcon + `POST /speak`, tolerância 2h, `last_acked_at != hoje` via `localDateIso`, sem disparo duplo no dia); botões de ação = feedback visual silencioso (sem voz, exceto o alarme).

## Features

### F1 — Fundação visual HUD + shell dashboard com abas

- **Descrição:** Substituir os tokens/reset atuais pelos tokens HUD do `index.html` (variáveis CSS `--bg/--bg2/--ink*/--line*/--panel*/--accent/--amber/--teal/--green/--err/--mono/--display/--chamf`), aplicar fundo (radial + scanlines + vinheta), painéis chanfrados (clip-path + moldura via mask-composite), `h3` com barra accent+glow e uppercase. Trocar a grade fixa de 9 painéis por um **shell dashboard**: barra de foco no topo (F2) + navegação por abas (F5) cujo conteúdo é o conteúdo funcional atual realocado. Fonts via Google Fonts CDN com font stack de fallback local; nenhuma função de dados/ação depende de CDN.
- **Entradas esperadas:** nenhuma nova entrada de dados; consome o mesmo `state` de `GET /forestos/state`. Entrada de ambiente: rede pode estar offline (CDN indisponível).
- **Saídas esperadas:** `forestos.html` renderiza com a linguagem visual HUD (tokens presentes no `<style>`, painéis `.panel` com `clip-path` chanfrado, `--display` em títulos/números). Com CDN indisponível o layout continua legível e todas as ações continuam funcionando (fallback de fonte). `GET /forestos` → 200 e o HTML contém os hooks `fetch('/forestos/state')` e `/forestos/action`.
- **Regras / edge cases:** arquivo permanece self-contained; nenhum `<script src>`/`<link>` de CDN pode ser condição para dados/ações. Nenhum token/handler funcional removido sem substituto equivalente.

### F2 — Barra de foco fixa no topo (o coração da página)

- **Descrição:** Barra de foco sempre visível no topo, em qualquer aba: timer grande em fonte display com `tabular-nums`, entidade focada, XP previsto, e os controles (iniciar multi-missão, concluir, concluir com tempo manual, cancelar). Estado vazio elegante quando não há foco.
- **Entradas esperadas:** `state.focus` (`{type, title, started_at, mode, pomo_min, importance, difficulty}` ou vazio); clique nos controles; campo de minutos manual.
- **Saídas esperadas:** timer atualiza a cada 1s recalculado de `started_at` (regressivo no pomodoro); `+N XP previsto` visível; controles disparam as ações `focus stop` / `focus stop <min>` / `focus cancel` / abrir form multi; sem foco mostra estado vazio ("Nenhum foco ativo", timer `00:00`, `+0 XP`). Botões dão flash visual silencioso.
- **Regras / edge cases:** barra fixa/sticky e visível em todas as abas; nunca contar tempo em memória (sempre `Date.now() - started_at`); XP previsto = `elapsedMin*imp*dif/10`.

### F3 — Aba "Visão Geral" (resumo do dia, aba padrão)

- **Descrição:** Aba ativa por padrão ao abrir a página. Consolida o resumo do dia: perfil (XP total, nível), missões de maior peso, hábitos de hoje, lembretes vencidos/próximos. Reaproveita os dados já existentes, apenas reorganizados numa visão-resumo.
- **Entradas esperadas:** `state.profile`, `state.sectorSummary`, `state.missionsBySector` (top por peso), `state.habits`, `state.reminders`.
- **Saídas esperadas:** ao carregar, a aba "Visão Geral" está ativa; mostra XP/nível, as missões de maior peso (tier de cor coerente), hábitos de hoje com streak/feito-hoje, e lembretes vencidos destacados / próximos. Empty states desenhados quando alguma lista está vazia.
- **Regras / edge cases:** é uma visão derivada — não duplica ações nem cria endpoints; ações acionadas daqui usam os mesmos handlers das abas dedicadas. "Maior peso" = `imp*dif` já ordenado pelo servidor.

### F4 — Abas de conteúdo operacional (Missões, Hábitos, Multi-missão)

- **Descrição:** Realocar Missões por setor, Hábitos e Multi-missão em aba(s) de conteúdo, mantendo 100% das ações e controles atuais, com a estética HUD (tiers com cor+glow, linhas, presets pomodoro, mini-missões).
- **Entradas esperadas:** `state.missionsBySector`, `state.habits`; interações: focar/colher/criar missão; focar/completar/desfazer/criar hábito; configurar e iniciar multi-missão (modo, presets 15/25/45/60/custom, mini-missões add/toggle/remove, imp/dif 1–5).
- **Saídas esperadas:** missões agrupadas por setor com tier de cor por peso e botões ▶/🌾/➕ que chamam `focus start mission`, `harvest`, `criar missao`; hábitos com streak/feito-hoje e ▶/✅/↩/➕ (`focus start habit`, `habit complete`, `habit uncomplete`, `criar habito`); multi-missão inicia com `focus start multi <json>` carregando modo/pomoDuration/importance/difficulty/miniMissions. Empty states quando vazio.
- **Regras / edge cases:** presets 15/25/45/60 e custom presentes; mini-missões vivem em draft local até "iniciar sessão"; escaping de aspas em nomes preservado.

### F5 — Navegação por abas client-side (estado preservado entre pollings)

- **Descrição:** Troca de abas 100% client-side (sem reload); a aba ativa é preservada quando o polling de 3s re-renderiza o conteúdo. Abas com `:focus-visible`, aria e microtransição.
- **Entradas esperadas:** clique/teclado na barra de abas; ticks de polling que re-renderizam o `state`.
- **Saídas esperadas:** ao clicar numa aba, só o painel dela fica visível; o re-render do polling **não** volta para a aba padrão nem esconde a aba escolhida; a barra de foco (F2) permanece visível em todas as abas.
- **Regras / edge cases:** estado da aba ativa guardado em variável/atributo client-side, não depende do servidor; sem uso de `location.reload`.

### F6 — Cartografia + Heatmaps (aba)

- **Descrição:** Árvore Setor→Projeto→Objetivo→Missão + órfãos e criação de entidades (setor/projeto/objetivo), mais os heatmaps de foco e de hábitos, repaginados: células arredondadas, escala verde por tiers, tooltip com data e valor (minutos/contagem).
- **Entradas esperadas:** `state.cartografia{tree,orphanMissions}`, `state.heatmaps{focusByDay,habitCompletionsByDay}`; cliques de criar entidade.
- **Saídas esperadas:** árvore renderizada e órfãos listados; botões criam via `criar <tipo> <json>`; heatmaps renderizam grade mensal com escala verde (`heatTier` por % do máximo do período) e cada célula tem tooltip (`title`) com a data e o valor. Empty states quando sem dados.
- **Regras / edge cases:** `focusByDay` e `habitCompletionsByDay` continuam sendo as duas fontes; escala relativa ao máximo do período.

### F7 — Lembretes + Anotações (aba) + polimento + testes

- **Descrição:** Lembretes (ack, criar, vencidos destacados) e Anotações (cards por cor, criar) repaginados na estética HUD, **preservando integralmente a lógica de alarme local** (só a apresentação muda). Passe final de polimento: microinterações, consistência de espaçamento (escala 4/8px), skeleton/empty states, feedback de ação (pulso/confirmação silenciosos), responsividade e acessibilidade. Atualizar `test_forestos_page.py` para o novo markup e rodar toda a suíte.
- **Entradas esperadas:** `state.reminders`, `state.anotacoes`; ack/criar; relógio local (alarme).
- **Saídas esperadas:** lembretes com ✔ (`reminder ack`) e ➕ (`criar lembrete`), vencidos com destaque visual; anotações como cards que respeitam `bg_color` e ➕ (`criar anotacao`); alarme continua idêntico (earcon + `POST /speak`, tolerância 2h, `localDateIso`, sem disparo duplo). Suíte verde: `python -m pytest` (via `./.venv/Scripts/python.exe`) e `node --test forestos/test/`. Smoke: `GET /forestos` → 200 com os hooks JS de `/forestos/state` e `/forestos/action`.
- **Regras / edge cases:** nenhuma constante/função do alarme (`REMINDER_TOLERANCE_MS`, `reminderDueDate`, `reminderAlarmState`, `checkReminders`, `localDateIso`, `playEarcon`) pode mudar de comportamento; `doAction` continua sem `/speak`.

## Perguntas abertas

(vazio — o contrato do grilling está fechado; agrupamento de abas foi decidido pelo Planejador dentro da liberdade dada pelo contrato.)
