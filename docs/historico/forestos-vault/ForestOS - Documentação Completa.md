---
tipo: referencia
status: ativo
area: aprendizado
criado: 2026-06-18
atualizado: 2026-07-15
tags: [forestos, referencia, documentacao, obsidian, hub, manual]
---

# ForestOS — Documentação Completa (Hub C.O.R.E.)

> **Propósito deste documento.** Manual de referência único e autossuficiente do
> sistema **ForestOS**: descreve a arquitetura atual, o significado e a finalidade de
> cada módulo, o contrato de dados de cada entidade, as regras de negócio (XP, foco,
> streak) e como operar o sistema no dia a dia.
>
> Sempre que houver conflito, as **fontes de verdade** prevalecem sobre este resumo:
> `voice-hub/forestos/` (código da engine/CLI), `forestos/Modelo de Dados ForestOS.md`
> (frontmatter das entidades) e `voice-hub/prd.md`/`issues.md` (contrato da migração).
> Este documento reflete o estado **pós-migração** (ForestOS unificado no Hub C.O.R.E.;
> SQLite aposentado para o ForestOS; Obsidian read-only). Histórico da versão anterior
> (SQLite + engine no Obsidian) em `[[ForestOS e Finanças no Obsidian - Plano]]`.

---

## 0. O que é o ForestOS

ForestOS é um sistema de **produtividade gamificada**. A metáfora central: você
cultiva uma **floresta** de trabalho. Você **foca** em missões e hábitos
(cronômetro/pomodoro), acumula **XP**, e **colhe** missões concluídas. O progresso
acende **heatmaps** de foco e de hábitos, e tudo se organiza numa hierarquia
**Setor → Projeto → Objetivo → Missão**, além de **Hábitos**, **Lembretes** e
**Anotações**.

O sistema foi originalmente portado de um app React+Supabase para dentro do
Obsidian (SQLite + DataviewJS), e depois **migrado do Obsidian para o Hub C.O.R.E.**
(`voice-hub/`, Flask porta 8765) para poder ser operado por voz/texto e sem depender
do app Obsidian aberto. O modelo de armazenamento continua **híbrido** (seção 2),
mas as duas metades agora vivem em lugares diferentes: as notas continuam no vault;
o estado de execução e o escritor viraram parte do Hub.

---

## 1. Localização e pré-requisitos

- **Vault (entidades + leitura):** `C:\Users\m.rafael\Documents\Obsidian Vault\forestos\`
- **Engine/CLI (escritor único):** `C:\Users\m.rafael\.claude\hooks\voice-hub\forestos\`
- **Estado:** `forestos/_state/profile.json` + `forestos/_state/events.jsonl` (no vault, mas só a CLI escreve).
- **Página operacional:** `http://localhost:8765/forestos` (servida pelo `server.py` do Hub).
- **Painel de leitura no Obsidian:** `[[ForestOS - Painel]]` (read-only, sem botões).
- **Skill para operar por linguagem natural:** `.claude/skills/forestos-ops/SKILL.md` (no vault; instrui o claude headless do Hub a usar a CLI).
- **Plataforma:** a CLI é **Node puro** (sem SQLite, sem Electron/`app` do Obsidian) — roda em qualquer lugar que tenha Node; a página `/forestos` roda no navegador via o Hub Flask.

### Peças envolvidas
| Papel | Onde |
|---|---|
| Notas das 7 entidades (grafo, Dataview, Bases) | Vault, `forestos/*.md` |
| Estado (perfil/XP/foco/eventos) | Vault, `forestos/_state/*.json[l]` (só a CLI escreve) |
| Escritor único (regras de XP/streak, lock) | `voice-hub/forestos/cli.js` + `engine/` + `store/` |
| Libs puras de regras (XP, peso/tier, streak, calendário) | `voice-hub/forestos/lib/` (movidas do vault) |
| Rotas HTTP (`/forestos`, `/forestos/state`, `/forestos/action`) | `voice-hub/server.py` |
| Página operacional (ações + timer + alarme) | `voice-hub/forestos.html` |
| Painel read-only no Obsidian | `forestos/ForestOS - Painel.md` (DataviewJS, só leitura) |
| Operação por voz/texto (claude headless) | skill `forestos-ops` |

> ⚠️ **SQLite aposentado para o ForestOS.** `db/central.db` continua existindo só
> para **Finanças** (`db/schema.sql` não tem mais a seção ForestOS). Não há mais
> plugin SQLite DB nem Electron `require()` envolvidos no ForestOS.

---

## 2. Arquitetura híbrida (o conceito mais importante)

Duas camadas de armazenamento, escolhidas pela natureza do dado — a mesma ideia de
antes, só que a segunda camada não é mais SQLite:

### 2.1 Entidades conceituais → **notas + frontmatter** (`forestos/*.md`, no vault)
Setor, Projeto, Objetivo, Missão, Hábito, Lembrete, Anotação. Cada uma é um `.md` com
frontmatter estruturado. Razão: são "cidadãs do segundo cérebro" — queremos grafo,
backlinks, Bases, edição manual e durabilidade em texto puro. **Continuam no vault.**

Convenções (detalhe na seção 4):
- **Nome do arquivo = nome/título da entidade** (não se duplica em frontmatter).
- **Campos de dados em inglês** = idênticos ao contrato original, para as libs
  portadas operarem **sem tradução**.
- **`tipo`** (em português) = discriminador da entidade (`setor`, `projeto`, …).
- **`id`** = uuid estável; é por ele que o estado (foco corrente, eventos) referencia a nota.
- **Vínculos hierárquicos = wikilinks** (`sector: "[[Saúde]]"`).

### 2.2 Estado e volume → **arquivos JSON no vault** (`forestos/_state/`)
Migrado do SQLite (PRD F5/ISS-003):
- **`profile.json`**: `{ total_xp, level, focus: {type, entity_id, started_at, mode,
  pomo_min, importance, difficulty, mini_missions[]}, updated_at }`. Sem campos
  `counter_*` (existiam no SQLite; descartados na migração — não fazem falta).
- **`events.jsonl`**: log **imutável** append-only, 1 JSON por linha — fonte dos
  heatmaps e do histórico de XP. Tipos: `habit_complete`, `xp_event`, `focus_session`,
  `reminder_ack`.
- Sessão multi-missão **não tem mais estado próprio**: ao concluir com ≥1 min, a CLI
  já materializa direto **uma nota `missao`** `done`+`harvested` (sem tabela
  intermediária como o antigo `multi_focus_sessions`).

> **Por que o arquivo, e não mais o SQLite?** A engine virou uma CLI Node isolada,
> sem Electron/`app` do Obsidian — não fazia sentido carregar um plugin SQLite só
> para 2 tabelas. JSON simples + lockfile resolve o mesmo problema (serializar
> escritas concorrentes) com muito menos superfície.

### 2.3 Regra de ouro do fluxo de dados (mudou o "quem escreve")
- **Leitura:** tanto o painel do Obsidian (DataviewJS) quanto a página `/forestos`
  do Hub leem as notas (`dv.pages`/varredura de arquivos) e o estado
  (`_state/*.json[l]`).
- **Escrita — ÚNICA fonte:** a CLI `voice-hub/forestos/cli.js`. Ela escreve
  frontmatter (parser próprio em `store/frontmatter.js`, preserva corpo/wikilinks) e
  o estado (`store/profile.js`, `store/events.js`), sempre sob um **lockfile**
  (`store/lock.js`) que serializa escritas concorrentes entre página, botões e
  claude headless.
- **O Obsidian nunca escreve mais nada do ForestOS** — nem frontmatter (sem
  `processFrontMatter` para isso), nem estado. O painel antigo interativo foi
  removido (ISS-008); o que sobrou é 100% leitura.

---

## 3. Mapa de módulos — significado e finalidade

### 3.1 `voice-hub/forestos/` (engine — escritor único, fora do vault)

```
voice-hub/forestos/
  cli.js              # entrada: node cli.js <cmd> [args]
  store/
    paths.js           # caminhos de forestos/_state/* a partir do vaultRoot
    profile.js          # ler/escrever profile.json (default seed se ausente)
    events.js           # append/leitura de events.jsonl
    frontmatter.js       # parser/serializer de frontmatter YAML (preserva corpo/wikilinks/valores multi-linha)
    notes.js             # criar nota de entidade, localizar por id/nome, patch de frontmatter
    lock.js              # lockfile com retry/timeout, serializa escritas
  engine/
    entities.js          # criação das 7 entidades (defaults idênticos ao contrato antigo)
    focus.js              # foco/XP/streak/mini-missões/lembretes — o coração do "Run"
    dashboard.js           # agrega TUDO num único JSON para a página/painel
  lib/                    # libs PURAS (sem Obsidian/SQLite), movidas do vault (PRD F4)
    focus.js               # sessionXp, elapsedMinutesSince, nextStreak, normalizeMiniMissions...
    productivity.js         # PESO_TIERS, pesoOf/pesoTier, HEAT_TIERS, heatTierFor, formatMinutes
    forestos.js              # cartografia, missionsBySector, habitsView, remindersView, sectorSummary, heatmaps
    calendar.js               # buildMonthGrid (grade do heatmap)
  migrate.js                  # migração one-shot SQLite → JSON (roda 1x, contra CÓPIA do central.db)
  test/                        # testes node --test (paridade de libs, store, engine, CLI, migração)
```

Todos os módulos recebem `vaultRoot` **explícito** (nunca hardcoded) — permite testar
com fake-vault em diretório temporário; em produção é
`C:\Users\m.rafael\Documents\Obsidian Vault` (ou `FORESTOS_VAULT` via env).

### 3.2 Rotas HTTP (`voice-hub/server.py`)
| Rota | Método | Efeito |
|---|---|---|
| `/forestos` | GET | serve `forestos.html` |
| `/forestos/state` | GET | proxy → `node cli.js dashboard`; devolve o JSON consolidado |
| `/forestos/action` | POST | `{cmd, args}` → proxy → `node cli.js <cmd> ...`, com **whitelist** de comandos |

Spawn de `node` por request (local, aceitável). Erros do CLI viram JSON `{error}`
com status 500, nunca stacktrace HTML. `cmd` fora da whitelist → 400.

### 3.3 Página `voice-hub/forestos.html`
HTML/CSS/JS próprios (sem framework), estética coerente com o HUD do Hub. Consome
`GET /forestos/state` (polling 3s + refresh imediato pós-ação) e dispara
`POST /forestos/action` nos botões. Painéis: barra de foco viva, missões por setor,
hábitos, sessão multi-missão (mini-missões, presets pomodoro), cartografia,
heatmaps, resumo/perfil, lembretes (com alarme local — seção 8), anotações.
**Timer sempre recalculado de `started_at`** — nunca contado em memória (sobrevive a
reload de página). Feedback de ação é **visual e silencioso** (sem voz).

### 3.4 Vault (`forestos/` no Obsidian) — só leitura
| Arquivo | Papel |
|---|---|
| `ForestOS - Painel.md` | Painel **read-only** (DataviewJS): lê `_state/*.json[l]` via `fs` e as libs puras via `require` do caminho absoluto do Hub. Sem botões `▶/🌾/✅/🎯`, sem barra de foco interativa. |
| `Central de Comando.md` | Só a captura de **Finanças** continua aqui; ForestOS virou um link "ForestOS agora no Hub" |
| `Modelo de Dados ForestOS.md` | Contrato de frontmatter das entidades + shape do estado |
| `ForestOS Index.md` | MOC — ponto de entrada |

### 3.5 `scripts/` no vault — só Finanças
Depois da faxina (ISS-008), `scripts/` não tem mais nada de ForestOS:
`scripts/focus.js` e `scripts/focus-ui.js` foram deletados; `scripts/capture.js`
só tem os forms de Finanças; `Templates/ForestOS/` foi removido. O que resta
(`db.js`, `capture.js`, `lib/{dates,money,aggregations,recurrence,insights}.js`) é
100% Finanças — ver `[[Finanças - Painel]]`.

---

## 4. Contrato de dados das entidades (frontmatter)

Fonte de verdade: `[[Modelo de Dados ForestOS]]`. Resumo operacional abaixo — **sem
mudança nenhuma** em relação à versão pré-migração (só o escritor mudou, o shape das
notas é idêntico). Hierarquia: **Setor → Projeto → Objetivo → Missão**; mais
**Hábito**, **Lembrete**, **Anotação**. Vínculos hierárquicos são **wikilinks**; ao
ler no DataviewJS/CLI, normalize o wikilink para nome (basename) antes de comparar
com `file.name`.

### `setor`
`id` (uuid) · `tipo: setor` · `color` (hex, default `#a88a3d`) · `archived` (bool) · `created_at`.

### `projeto`
`id` · `tipo: projeto` · `description` · `sector` (→setor) · `status` (`active|paused|done|abandoned`) · `target_date` · `created_at`.

### `objetivo` (os "goals" do ForestOS — **não confundir** com `goals` do SQLite, que são metas financeiras)
`id` · `tipo: objetivo` · `description` · `sector` · `project` · `parent_goal` (→objetivo) · `horizon` (`quarter|year|multi_year`) · `status` (`active|paused|done|abandoned`) · `target_date` · `created_at`.

### `missao`
`id` · `tipo: missao` · `description` · `sector` · `goal` (→objetivo) · `parent_mission` (→missao) · `importance` (1–5) · `difficulty` (1–5) · `status` (`inbox|done`) · `harvested` (bool) · `focus_minutes` (acumula durante o foco) · `xp_gained` (acumula até a colheita) · `due_date` · `created_at` · `completed_at` · `harvested_at` · `sort_order`.
> **XP** = `round(focus_minutes × importance × difficulty / 10)`. **Peso** = `importance × difficulty` (define o tier de cor).

### `habito`
`id` · `tipo: habito` · `description` · `sector` · `goal` · `project` · `frequency` (`daily|weekly|monthly|custom`) · `custom_days` (list[int] 0–6) · `importance` (1–5) · `difficulty` (1–5) · `current_streak` · `best_streak` · `last_completed_at` · `active` (bool, default true) · `color` (hex) · `focus_minutes` · `xp_gained` · `sort_order` · `created_at`.

### `lembrete`
`id` · `tipo: lembrete` · `message` · `frequency` (`daily|weekly|monthly|custom|once`) · `custom_days` · `time_of_day` (`HH:MM`) · `sector` · `goal` · `due_at` · `last_acked_at` · `acknowledged` (bool) · `active` (bool) · `repeat` (`none` se `once`, senão = `frequency`) · `sort_order` · `created_at`.

### `anotacao`
`id` · `tipo: anotacao` · `category` (opcional) · `bg_color` (hex; vazio = pergaminho padrão) · `sort_order` (menor = topo) · `updated_at`. **Conteúdo = corpo da nota.**

---

## 5. Estado (resumo dos campos) — `forestos/_state/`

Detalhe completo em `voice-hub/forestos/store/profile.js`/`events.js`. Booleanos
JS nativos; datas/timestamps ISO 8601.

### `profile.json` (singleton)
`total_xp` (int) · `level` (int, estático) · `focus` (foco corrente, ou
`{type:null}` se nenhum): `type` (`"mission"|"habit"|"multi"|null`), `entity_id`,
`started_at` (ISO), `mode` (`"stopwatch"|"pomodoro"`), `pomo_min`, `importance`
(1–5), `difficulty` (1–5), `mini_missions` (array, só em `multi`) · `updated_at`.
> **Sem campos `counter_*`** (existiam no SQLite; a migração os descarta).
> O foco é **um único objeto**, não três IDs mutuamente exclusivos como no SQLite antigo — mais simples de representar "nenhum foco" (`type:null`).

### `events.jsonl` (log imutável, append-only)
1 JSON por linha: `id, type (habit_complete|xp_event|focus_session|reminder_ack),
entity_type, entity_id, entity_title, focus_minutes, xp_gained, total_xp_after,
streak_before, streak_after, data{}, occurred_at`. Fonte dos heatmaps (foco por dia;
conclusões de hábito por dia) e do histórico de XP. Tolera linha final vazia.

---

## 6. Regras de negócio — Foco, XP e Streak (engine `voice-hub/forestos/engine/focus.js`)

Idênticas à versão anterior (**nenhuma fórmula foi reescrita** na migração — só
porteadas de `lib/focus.js`). A **fórmula de XP** é a mesma em todos os casos:
`sessionXp = round(minutos × importância × dificuldade / 10)`. O que muda é
**quando** o XP entra no `profile.total_xp`. O timer **sobrevive a reload** porque a
página recalcula `now − started_at` a cada segundo (não conta em memória).

### 6.1 Exclusividade de sessão
Ao iniciar qualquer foco, se já houver outro ativo, a engine encerra/credita o
anterior (`stopFocus({silent:true})`) antes de começar o novo. Só existe **uma**
sessão por vez.

### 6.2 Foco em **Missão**
- `focus start mission <nome>` → grava `profile.focus` (`type:"mission"`).
- Ao parar (`focus stop`): os **minutos** e o **XP da sessão** **acumulam na nota**
  (`focus_minutes += min`, `xp_gained += xp`) e gera um evento `focus_session`.
- **O XP só entra no `total_xp` na colheita.** `harvest <nome>` marca `status: done`,
  `harvested: true`, datas, credita `xp_gained` acumulado no `profile.total_xp` e gera
  `xp_event`. **Idempotente** (colher de novo → `{already:true}`, sem creditar de novo).

### 6.3 Foco em **Hábito**
- `focus start habit <nome>` → grava `profile.focus` (`type:"habit"`).
- Ao parar: minutos acumulam na nota e o **XP vai DIRETO ao `total_xp`** (auto-harvest) +
  evento `xp_event`.
- **Completar** (`habit complete <nome>`) é separado do foco: marca `last_completed_at
  = hoje`, recalcula streak (`nextStreak`) e `best_streak`, gera `habit_complete`.
  Repetido no mesmo dia → `{already:true}`. `habit uncomplete <nome>` desfaz a
  conclusão de hoje e decrementa o streak (best-effort: remove o `habit_complete` de
  hoje do `.jsonl`).

### 6.4 **Sessão multi-missão**
- `focus start multi '<json>'` (`mode, importance, difficulty, pomoDuration,
  miniMissions`) grava a sessão em `profile.focus` (`type:"multi"`, sem tabela à parte).
- Mini-missões editáveis durante a sessão: `mini add/toggle/remove`.
- Ao concluir (`focus stop`): se ≥ 1 min, cria **uma nota `missao` consolidada**
  (nasce `status: done`, `harvested: true`, com `focus_minutes`/`xp_gained` da sessão
  e corpo listando as mini-missões), credita o **XP direto** no `total_xp`, limpa o
  foco e gera `xp_event`. **< 1 min → descartada** sem nota, sem XP.
- `focus cancel` zera o foco ativo **sem** creditar XP (multi descarta sem nota).

### 6.5 Streak (`nextStreak`)
Ao completar um hábito hoje, comparando com `last_completed_at`:
- `daily`: se a última foi **ontem** (diff = 1) → `+1`, senão reseta para `1`.
- `weekly`/`custom`: diff ≤ 7 → `+1`, senão `1`.
- `monthly`: diff ≤ 31 → `+1`, senão `1`.
- Sem conclusão anterior → `1`. Já concluído hoje → mantém (`{already:true}`).

### 6.6 Modos de timer
- **Cronômetro** (stopwatch): conta para cima.
- **Pomodoro**: conta regressivo a partir da duração escolhida (presets
  15/25/45/60 + custom, 1–480min). Modo e duração ficam em `profile.focus.mode`/
  `pomo_min` (tanto mono quanto multi — diferente da versão antiga, que só
  persistia o modo para multi e usava `localStorage` para foco mono).

---

## 7. As telas (views) e onde elas vivem

### 7.1 `http://localhost:8765/forestos` — página operacional (Hub)
Consolida os mesmos painéis de antes, agora **com ações reais** via
`POST /forestos/action`:
1. **Foco** — barra de foco viva (timer client de `started_at`, cronômetro/pomodoro
   regressivo, XP previsto, iniciar/concluir/concluir-com-tempo-manual/cancelar).
2. **Missões ativas por setor** — ordenadas por peso, tier de cor, ▶ focar / 🌾 colher.
3. **Hábitos** — streak/feito-hoje, ▶/✅/↩.
4. **Sessão multi-missão** — 🎯 configurar (modo, presets, mini-missões, imp/dif).
5. **Cartografia** — árvore + órfãos + criar entidade.
6. **Heatmap de foco** e **Heatmap de hábitos** — leem `events.jsonl`.
7. **Resumo por setor** — foco/XP acumulado + total.
8. **Lembretes** — hora/frequência, ✔ ack, alarme local (seção 8).
9. **Anotações** — cards por cor.

### 7.2 `[[ForestOS - Painel]]` — painel **read-only** no Obsidian
Os mesmos dados (lidos de `_state/*` + notas), **sem nenhum botão de ação** e sem
barra de foco interativa — só uma linha de status do foco atual, se houver.

### 7.3 `[[Central de Comando]]` — dashboard operacional (raiz do vault)
- **Captura rápida**: só os botões de **Finanças** continuam aqui.
- ForestOS virou um aviso/link: "🌲 ForestOS agora no Hub" → `http://localhost:8765/forestos`.
- Links para `[[ForestOS - Painel]]` e `[[Finanças - Painel]]`.

### 7.4 Índices (MOCs)
- `[[ForestOS Index]]` — porta de entrada do domínio.
- `[[Modelo de Dados ForestOS]]` — contrato de frontmatter (fonte de verdade).
- `[[ForestOS e Finanças no Obsidian - Plano]]` — plano por fases (histórico da versão pré-migração).

---

## 8. Alarme local de lembretes (só na página `/forestos`)

JS do client (`forestos.html`) checa `time_of_day`/`frequency`/`custom_days`/`due_at`
de cada lembrete a cada segundo. Ao vencer, se `last_acked_at` ≠ hoje: earcon + fala
via `POST /speak` (mesma fila `SPEAK_Q` do Hub de voz). Tolerância de **2h**: dentro
da janela fala "lembrete atrasado"; passado esse limite, só destaque visual, sem
fala (evita repetir alarme velho indefinidamente). `once` usa `due_at`. Não dispara
duas vezes no mesmo dia se já `acked`. **Gotcha corrigido (R3):** "hoje" é sempre
calculado em **data local** (`getFullYear/getMonth/getDate`), nunca
`toISOString()` (UTC) — à noite (GMT-0300) o UTC já virou o dia seguinte antes da
meia-noite local, o que fazia um lembrete já confirmado redisparar.

---

## 9. Convenções e armadilhas para um agente operar com segurança

- **Nunca** edite frontmatter, `profile.json` ou `events.jsonl` na mão — **sempre**
  via `node voice-hub/forestos/cli.js <cmd>` (skill `forestos-ops` documenta todos
  os comandos e é o caminho recomendado para o claude headless).
- **O Obsidian não escreve mais nada do ForestOS** — o painel é read-only por design;
  se algo parecer "faltando um botão" no vault, é intencional (a ação está no Hub).
- **Nomes previsíveis**: a entidade é localizada por `file.basename` ou por
  `frontmatter.id`. Renomear a nota muda a chave por nome — prefira o `id`.
- **Wikilinks** chegam como string `[[Nome]]`; normalize para nome puro antes de comparar.
- **`profile.level` é estático** (fiel ao original; não há cálculo de nível em JS).
- **Foco exclusivo**: nunca há duas sessões ativas; iniciar uma encerra/credita a outra.
- **Timer**: nunca conte segundos em memória — recalcule de `started_at` (sobrevive a reload).
- **Escrita concorrente**: o lockfile (`store/lock.js`) serializa escritas entre
  abas da página, botões e claude headless — não é preciso (nem permitido) coordenar
  isso manualmente.
- **`goals` ≠ objetivos**: no SQLite, `goals` são **metas financeiras**; os
  *objetivos* do ForestOS são **notas** `tipo: objetivo`. Sem colisão, mas atenção ao nomear.
- **Valor multi-linha em frontmatter** (ex.: `description` da nota consolidada de
  multi-missão): o parser (`store/frontmatter.js`) escapa `\n` numa única linha
  física para manter o round-trip estável — nunca quebre isso escrevendo frontmatter
  na mão.
- **`custom_days`/`tags` inline** (`[a, b]`) e escalares com `:`/`#` (ex.:
  `time_of_day: 08:30`) são preservados byte-a-byte por `patchFrontmatter` quando não
  são a chave alterada (R1) — outra razão para nunca reescrever frontmatter manualmente.

---

## 10. Glossário rápido

- **XP**: pontos de experiência. `round(min × imp × dif / 10)` por sessão.
- **Peso**: `importância × dificuldade` (1–25). Define o tier de cor (Trivial→Épico).
- **Score de missão**: `focus_minutes × imp × dif` (usado no resumo/heatmap por setor).
- **Colher (harvest)**: concluir uma missão e transferir seu `xp_gained` para o `total_xp`.
- **Auto-harvest**: crédito imediato de XP (hábitos e sessões multi) ao parar o foco.
- **Materializar**: termo do domínio **Finanças** (recorrência virtual → lançamento real) —
  não confundir com colher.
- **Heatmap**: grade de calendário colorida por intensidade (foco/dia ou conclusões/dia).
- **Escritor único**: a CLI `voice-hub/forestos/cli.js` — todo o resto (páginas,
  painel, claude headless) só lê ou chama a CLI; nunca escreve estado/frontmatter direto.

---

## Relacionado
- [[ForestOS Index]] · [[Modelo de Dados ForestOS]] · [[ForestOS - Painel]]
- [[Central de Comando]] · [[Finanças - Painel]]
- [[ForestOS e Finanças no Obsidian - Plano]] (histórico da versão pré-migração)
