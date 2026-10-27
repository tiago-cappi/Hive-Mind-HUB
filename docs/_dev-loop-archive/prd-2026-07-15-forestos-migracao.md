# PRD — Migração ForestOS → Hub C.O.R.E. (unificação)

> Fonte de verdade do "o quê" e "porquê". Contrato completo em `voice-hub/task-forestos.md`
> (12 decisões fechadas em grilling — NÃO re-decidir). Este PRD detalha I/O por feature
> para o Juíz testar. As slices executáveis estão em `issues.md`.

## Contexto

O **ForestOS** (produtividade gamificada: XP, foco, hábitos, streaks) hoje vive espalhado no vault Obsidian: entidades = notas `.md` com frontmatter em `forestos/`; estado = 3 tabelas SQLite em `db/central.db`; engine JS em `scripts/` acoplada ao runtime do Obsidian (`app`, `processFrontMatter`, DataviewJS). Isso amarra o ForestOS ao desktop e ao app aberto, e impede operá-lo pelo Hub de voz.

Objetivo: **unificar o ForestOS dentro do Hub C.O.R.E.** (`voice-hub/`, Flask porta 8765) como uma página dedicada com engine própria (Node CLI, escritor único), aposentando o SQLite do ForestOS e transformando o Obsidian em leitor read-only. O Hub existente (voz/texto) fica intocado exceto por um link para a nova página. Finanças (que compartilha o `central.db` e libs) **não pode ser tocado**.

## Escopo

- **Dentro:**
  - Página `forestos.html` servida pelo Hub em `GET /forestos` + link no `index.html`.
  - Nova engine Node CLI isolada em `voice-hub/forestos/` (store, lock, comandos de escrita e leitura), reusando as libs puras de regras SEM reescrever fórmulas.
  - Estado do ForestOS migrado para arquivos no vault: `forestos/_state/profile.json` + `forestos/_state/events.jsonl` (SQLite aposentado para ForestOS; segue vivo só para Finanças).
  - Libs puras MOVIDAS do vault para o Hub; migração one-shot do SQLite; rotas no `server.py`; alarme de lembretes no client; skill `forestos-ops` no vault; faxina do vault (remoção da engine interativa antiga + painel read-only); documentação.
- **Fora (NÃO tocar):**
  - Qualquer coisa de **Finanças**: `scripts/db.js`, `scripts/financas.js`, `scripts/financas-ui.js`, libs `scripts/lib/{dates,money,aggregations,recurrence,insights}.js`, tabelas SQLite de Finanças, `Finanças - Painel.md`.
  - Fluxo de voz/sessões do Hub (`index.html` HUD, `/stt`, `/ask`, `/speak`, `/session_*`, processos claude headless) — única mudança no `index.html` é o link para `/forestos`.
  - Regras de negócio do ForestOS (fórmulas de XP/peso/streak) — reusar, nunca reescrever.
  - DROP das 3 tabelas no `central.db` vivo — a migração gera o SQL, mas o DROP é passo manual aprovado (não automático).

## Regras de negócio (invariantes — reusar das libs, não reescrever)

- **XP de sessão** = `round(focus_minutes × importance × difficulty / 10)` (`lib/focus.js#sessionXp`).
- **Peso** = `importance × difficulty`; tiers Trivial(1-4)/Padrão(5-9)/Notável(10-14)/Grave(15-19)/Épico(20-25) (`lib/productivity.js`).
- **Missão:** foco acumula `focus_minutes` e `xp_gained` na nota; XP só entra em `total_xp` na **colheita** (`harvest`, idempotente — nota já `harvested` não credita de novo).
- **Hábito:** foco acumula minutos na nota, XP da sessão credita **direto** no total ao parar (auto-harvest) + evento `xp_event`; `complete` marca streak via `nextStreak` (daily: diff===1 → +1 senão 1; weekly/custom: diff<=7; monthly: diff<=31); `uncomplete` desfaz o de hoje e decrementa streak.
- **Multi-missão:** ao parar, se ≥1 min consolida em UMA nota `missao` nascida `done`+`harvested` com XP direto no total + evento; `<1 min` descarta sem XP.
- **Foco exclusivo:** 1 sessão por vez; iniciar novo foco pausa (credita) o anterior.
- **Timer** sempre recalculado de `started_at` (ISO) — nunca contado em memória.
- **Frontmatter das 7 entidades** = idêntico ao contrato atual (ver `forestos/Modelo de Dados ForestOS.md` e defaults em `scripts/capture.js` `novoSetor..novaAnotacao`); vínculos `sector/project/goal/parent_*` como wikilinks `[[Nome]]`.

## Features

### F1 — Store + Lock (fundação de I/O)
- **Descrição:** camada de persistência da CLI em `voice-hub/forestos/store/`: leitura/escrita de `forestos/_state/profile.json`, append em `forestos/_state/events.jsonl`, e leitura/escrita de frontmatter das notas `.md` em `forestos/` (parser YAML próprio simples ou lib tipo gray-matter; escrita **preserva** corpo da nota e wikilinks). Lockfile (`.lock`, ~20 linhas com retry/timeout) que serializa toda operação de escrita entre abas/botões/claude.
- **Entradas esperadas:** caminho do vault (config/env); objetos de perfil/evento; caminho de nota + patch de frontmatter.
- **Saídas esperadas:**
  - `profile.json`: `{ total_xp:int, level:int, focus: {type: "mission"|"habit"|"multi"|null, entity_id, started_at (ISO), mode: "stopwatch"|"pomodoro", pomo_min:int|null, importance:int, difficulty:int, mini_missions:[{id,title,status,order,completed_at}] }, updated_at (ISO) }`. Sem campos `counter_*`.
  - `events.jsonl`: 1 JSON por linha, append-only, campos `id, type (habit_complete|xp_event|focus_session|reminder_ack), entity_type, entity_id, entity_title, focus_minutes, xp_gained, total_xp_after, streak_before, streak_after, data{}, occurred_at (ISO)`.
  - Nota `.md`: frontmatter atualizado, corpo e wikilinks intactos.
- **Regras / edge cases:** `_state/` criado se ausente; `profile.json` ausente → default seed (`total_xp:0, level:1, focus:{type:null}`); lock com retry até timeout, libera sempre (mesmo em erro); escrita de frontmatter idempotente por chave; leitura de `.jsonl` tolera linha final vazia; nunca reescrever o corpo da nota ao alterar frontmatter.

### F2 — Comandos de escrita da CLI
- **Descrição:** `voice-hub/forestos/cli.js <cmd> [args]` executa cada mutação. Comandos: criar cada uma das 7 entidades (`setor|projeto|objetivo|missao|habito|lembrete|anotacao`); `focus start mission|habit|multi`; `focus stop`; `focus cancel`; `harvest`; `habit complete|uncomplete`; mini-missão `add|toggle|remove`; `reminder ack`. Toda escrita passa pelo lock (F1) e reusa as regras das libs (F4).
- **Entradas esperadas:** `cmd` + args (nome/id da entidade, campos da entidade, imp/dif, modo/pomo, título de mini-missão, override de minutos manual etc.). Args via CLI (posicional/flags ou JSON) — formato documentado na skill (F9).
- **Saídas esperadas:** JSON no stdout descrevendo o efeito, ex.: criar → `{ok:true, path, id, tipo}`; `harvest` → `{ok:true, missionName, xpToHarvest, totalXp}`; `focus stop` (hábito) → `{ok:true, entityType:"habit", elapsedMin, xp, totalXpAfter}`; `focus stop` (multi ≥1min) → `{ok:true, entityType:"multi", missionId, missionTitle, xp}`; `habit complete` → `{ok:true, habit, newCurrent, newBest}`. Efeitos colaterais: `profile.json`/`events.jsonl`/frontmatter atualizados conforme regras.
- **Regras / edge cases:**
  - Novas entidades: frontmatter idêntico ao `capture.js` (id uuid, `tipo`, defaults, vínculos como `[[...]]`), corpo `# Título` + seções como hoje; nome-arquivo saneado, sufixo timestamp se colidir.
  - `focus start` respeita exclusividade (pausa o foco anterior, creditando); `focus stop` credita conforme tipo (missão acumula na nota; hábito credita direto; multi consolida/descarta); `focus cancel` zera foco sem XP (multi descarta).
  - `harvest` idempotente (nota já `harvested` → `{already:true}` sem creditar).
  - `habit complete` já-feito-hoje → `{already:true}`; `uncomplete` só desfaz se feito hoje, remove o `habit_complete` de hoje do log (best-effort no `.jsonl`).
  - Mini-missão só age na sessão multi ativa; entidade inexistente → erro JSON claro, sem crash.

### F3 — Comando de leitura `dashboard`
- **Descrição:** `node cli.js dashboard` devolve UM JSON com todo o estado para render da página e do painel read-only.
- **Entradas esperadas:** nenhum arg (lê `_state/*` + varre notas `forestos/*.md`).
- **Saídas esperadas:** JSON único com: `profile` (xp total, nível), `focus` ativo (tipo, id, título, started_at, imp/dif, mode/pomo, mini_missions, elapsedSec/elapsedMin, xp previsto), `missionsBySector` (ativas por setor ordenadas por peso desc com tier), `habits` (streak/doneToday), `reminders` (ativos, ordenados por hora), `anotacoes`, `cartografia` (árvore Setor→Projeto→Objetivo→Missão + órfãos), `heatmaps` (`focusByDay`, `habitCompletionsByDay` a partir de `events.jsonl`), `sectorSummary`. Estruturas idênticas às funções de `scripts/forestos.js` (reusadas via F4).
- **Regras / edge cases:** vínculos wikilink normalizados para nome puro antes de agrupar; vault vazio → JSON com listas vazias, sem erro; foco null → `focus:{type:null}`.

### F4 — Libs puras movidas
- **Descrição:** mover (não copiar) do vault para `voice-hub/forestos/lib/`: `scripts/lib/focus.js`, `scripts/lib/productivity.js`, `scripts/forestos.js`. `scripts/lib/calendar.js`: mover SÓ se grep confirmar que Finanças não a usa (evidência atual: só `forestos/ForestOS - Painel.md` e a própria lib a referenciam — Finanças não); senão deixar no vault. Após mover, deletar os originais do vault e reapontar os `require` internos.
- **Entradas esperadas:** arrays de entidades/eventos normalizados (como hoje).
- **Saídas esperadas:** mesmas funções puras, mesmos resultados numéricos (paridade bit-a-bit das fórmulas).
- **Regras / edge cases:** nenhuma fórmula reescrita; `require('./lib/productivity.js')` de `forestos.js` continua resolvendo após o move; libs de Finanças permanecem no vault.

### F5 — Migração one-shot SQLite → JSON
- **Descrição:** script Node em `voice-hub/forestos/` que: (1) faz backup datado de `db/central.db`; (2) lê `profile`+`events`+`multi_focus_sessions` do SQLite e gera `forestos/_state/profile.json` + `forestos/_state/events.jsonl` fiéis ao novo formato (F1); (3) NÃO dropa tabelas — gera um `.sql` de limpeza (DROP das 3 tabelas ForestOS) e atualiza `db/schema.sql` removendo a seção ForestOS, deixando claro no relatório que o DROP no `.db` vivo é passo manual/aprovado.
- **Entradas esperadas:** caminho de uma **cópia** de `central.db` (nunca o vivo em teste); ler SQLite via pacote node sem native build (ex.: sql.js) ou via `python sqlite3` chamado pelo script — escolher o mais simples e documentar a escolha.
- **Saídas esperadas:** `profile.json` + `events.jsonl` corretos; arquivo de backup datado; `.sql` de DROP; `db/schema.sql` sem a seção ForestOS (Finanças intacta); relatório stdout com contagens migradas e o aviso do DROP manual.
- **Regras / edge cases:** `total_xp`/`level` do profile preservados; foco corrente do SQLite (`current_focus_*_id`+`focus_started_at`) mapeado para `profile.focus`; sessão multi ativa (se houver) mapeada para `profile.focus` tipo `multi`; campos `counter_*` descartados; eventos preservam `occurred_at`; idempotência não exigida (rodada única), mas rerodar sobre cópia deve dar mesmo resultado.

### F6 — Rotas no `server.py`
- **Descrição:** três rotas novas no Flask, sem tocar nas existentes: `GET /forestos` (serve `forestos.html`), `GET /forestos/state` (proxy → `node cli.js dashboard`, devolve o JSON), `POST /forestos/action {cmd, args}` (proxy → `node cli.js <cmd> ...`, com **whitelist** de comandos, devolve JSON do CLI). Spawn de node por request é aceitável (local).
- **Entradas esperadas:** `GET /forestos` (sem body); `GET /forestos/state` (sem body); `POST /forestos/action` body JSON `{cmd:str, args:object|array}`.
- **Saídas esperadas:** `GET /forestos` → HTML 200; `GET /forestos/state` → `{...dashboard}` 200 (ou 500 com `{error}` se o CLI falhar); `POST /forestos/action` → JSON do CLI 200 / 400 se `cmd` fora da whitelist / 500 em erro do CLI.
- **Regras / edge cases:** whitelist rejeita comando desconhecido (nada de injeção/arg arbitrário para shell); erro do node capturado e devolvido como JSON, não HTML de stacktrace; rotas de voz/sessão inalteradas.

### F7 — Página `forestos.html` (v1 completa)
- **Descrição:** arquivo próprio (HTML/CSS/JS próprios, estética coerente com o HUD atual). Painéis: barra de foco viva (timer client recalculado de `started_at` a 1s, cronômetro e pomodoro regressivo, XP previsto, botões iniciar/concluir/concluir-com-tempo-manual/cancelar); missões ativas por setor ordenadas por peso com tier de cor (▶ focar, 🌾 colher, ➕ criar); hábitos com streak/feito-hoje (▶, ✅, ↩, ➕); sessão multi-missão (🎯 configurar: modo, presets pomodoro 15/25/45/60+custom, mini-missões add/toggle/remove/reorder, imp/dif 1-5); cartografia (árvore + órfãos, criar entidades); heatmaps de foco e de hábitos (grade mensal, escala verde); resumo/perfil (XP total, foco por setor); lembretes (hora/frequência, ✔ ack, ➕ criar, vencidos destacados); anotações (cards por cor, ➕ criar).
- **Entradas esperadas:** dados de `GET /forestos/state` (polling 3s + refresh imediato pós-ação); interações do usuário disparam `POST /forestos/action`.
- **Saídas esperadas:** UI renderizada com todos os painéis; ações refletem no estado e re-renderizam; feedback visual **silencioso** nos botões (SEM voz).
- **Regras / edge cases:** timer nunca conta em memória — sempre `now - started_at`; pomodoro regressivo estoura em 0 (earcon/estado visual, sem auto-stop obrigatório salvo se especificado); ordenação por peso desc; tier de cor do `lib/productivity.js`; página degrada com estado vazio.

### F8 — Alarme local de lembretes
- **Descrição:** JS na página checa `time_of_day`/`frequency`/`custom_days`/`due_at` no client; ao disparar (e `last_acked_at != hoje`): earcon + fala via `POST /speak` existente (entra na `SPEAK_Q` normal).
- **Entradas esperadas:** lista de lembretes do `dashboard`; relógio do client.
- **Saídas esperadas:** ao vencer no horário → earcon + `POST /speak` com a mensagem; botão ✔ ack chama `reminder ack` (grava `last_acked_at`=hoje + evento).
- **Regras / edge cases:** tolerância — página aberta até 2h após a hora fala "lembrete atrasado"; mais velho que 2h → só destaque visual, sem fala; `once` usa `due_at`; não disparar duas vezes no mesmo dia se já `acked` hoje.

### F9 — Skill `forestos-ops`
- **Descrição:** `SKILL.md` em `.claude/skills/forestos-ops/` **do vault** (o claude headless do Hub roda com cwd=vault). Instrui que TODA ação ForestOS (criar entidade, foco, colher, hábito, lembrete) seja feita via `node C:/Users/Meu Computador/Desktop/core-voice-hub-master/core-voice-hub-master/forestos/cli.js <cmd>` — NUNCA editar frontmatter/estado na mão; sem pedir confirmação; a resposta declara o que fez (ex.: "Colhida: X, +42 XP"). Documenta todos os comandos da CLI e seus args.
- **Entradas esperadas:** intenção do usuário em linguagem natural via claude headless.
- **Saídas esperadas:** invocação correta do CLI + resposta declarando o efeito.
- **Regras / edge cases:** description da skill dispara nos verbos ForestOS; caminho absoluto do `cli.js` correto (Windows); nunca sugere editar `.md`/`.json` na mão.

### F10 — Faxina no vault + painel read-only
- **Descrição:** após CLI+página funcionarem: deletar `scripts/focus.js` e `scripts/focus-ui.js`; em `scripts/capture.js` remover só a parte ForestOS (`novoSetor..novaAnotacao`, `dvOptions`, e `createEntityNote` se nada de Finanças usar) mantendo Finanças intacto; deletar `Templates/ForestOS/`; refazer `forestos/ForestOS - Painel.md` READ-ONLY (sem botões ▶/🌾/✅/🎯, sem barra de foco interativa; DataviewJS lê `forestos/_state/*.json[l]` via fs e as libs via `require` do path do Hub); em `Central de Comando.md` remover botões de captura ForestOS + barra de foco, colocar link/nota "ForestOS agora no Hub" (captura Finanças fica).
- **Entradas esperadas:** engine nova já operante.
- **Saídas esperadas:** vault sem a engine interativa antiga; painel Obsidian mostra dados (só leitura); captura/painel de Finanças 100% intactos.
- **Regras / edge cases:** confirmar por grep que `createEntityNote` não é usado por Finanças antes de removê-lo; painel read-only não deve quebrar se `_state/` estiver vazio; Finanças em `capture.js` intocado.

### F11 — Documentação
- **Descrição:** por último, refletir a nova arquitetura: reescrever `forestos/ForestOS - Documentação Completa.md`, `forestos/Modelo de Dados ForestOS.md`, `forestos/ForestOS Index.md` (estado em `_state/`, escritor único = CLI, Obsidian read-only); atualizar `CLAUDE.md` do vault (seções 3/6/8: `db/` agora só Finanças, engine no Hub); atualizar `voice-hub/CLAUDE.md` (nova página, rotas novas, pasta `forestos/`, seção de pendências, e substituir a seção "sem lock" pela política de lockfile); atualizar `voice-hub/README.md` se citar estrutura.
- **Entradas esperadas:** estado final do código.
- **Saídas esperadas:** docs coerentes com a implementação; nenhuma instrução obsoleta apontando para SQLite/engine antiga do ForestOS.
- **Regras / edge cases:** não duplicar regras entre docs (referenciar a fonte); manter aviso de que `goals` no SQLite = metas de Finanças.

## Convenções de trabalho (contrato)

- **Testes:** libs movidas → testes node diretos (paridade de fórmulas); store/lock/cli → testes com diretório temporário fake-vault; migração → testar contra CÓPIA do `central.db` real (nunca o vivo); rotas → testar handlers Flask; página → ao menos smoke test de servir e de os endpoints responderem.
- **Git:** repo `voice-hub` em branch nova `feature/forestos-integration`, **commits por slice**. Mudanças no vault não são git (vault sem repo) — aplicar direto. ANTES da 1ª slice: commitar as mudanças não commitadas do ciclo anterior (`index.html`, `server.py`, `test_effort_server.py`, `test_frontend_static.py`, `_dev-loop-archive/`, `task-forestos.md`) num commit separado `chore: ciclo modo-texto anterior + arquivos do dev-loop` — não misturar com as slices ForestOS.
- **Ordem das slices:** (1) CLI store+lock+profile/events → (2) comandos escrita+leitura+libs movidas → (3) migração one-shot → (4) rotas server.py → (5) forestos.html painel+ações → (6) alarme lembretes → (7) skill → (8) faxina+painel read-only → (9) docs.

## Perguntas abertas

Nenhuma bloqueante — o contrato (`task-forestos.md`) fechou as 12 decisões. Pontos deixados à escolha do Implementador, com evidência já levantada:

1. **Parser de frontmatter e leitor de SQLite:** a escolha (gray-matter vs. parser YAML próprio; sql.js vs. `python sqlite3`) é do Implementador — critério é "o mais simples sem native build" e deve ser documentado. Não bloqueia o plano.
2. **`calendar.js`:** evidência de grep aponta que Finanças NÃO usa (`financas.js`/`financas-ui.js` não referenciam `calendar`); portanto é movível. O Implementador deve re-confirmar por grep no momento do move antes de deletar o original.
3. **Formato de args do `POST /forestos/action` e da CLI** (posicional vs. JSON): à escolha do Implementador, desde que a whitelist de comandos seja respeitada e o formato fique documentado na skill (F9) — o Juíz testa contra o formato que a implementação declarar.
