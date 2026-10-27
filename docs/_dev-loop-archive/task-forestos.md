# TAREFA: Migração ForestOS → Hub C.O.R.E. (unificação)

Contrato fechado com o usuário em sessão de grilling — implementar EXATAMENTE estas 12 decisões, sem re-decidir.

## Contexto

**ForestOS** = sistema de produtividade gamificada que hoje vive no vault Obsidian (`C:\Users\Meu Computador\Documents\Obsidian Vault\`):
- Entidades = notas `.md` com frontmatter em `forestos/` (tipos: `setor`, `projeto`, `objetivo`, `missao`, `habito`, `lembrete`, `anotacao`; contrato em `forestos/Modelo de Dados ForestOS.md`).
- Estado = 3 tabelas SQLite em `db/central.db` (`profile`, `events`, `multi_focus_sessions`; schema em `db/schema.sql`).
- Engine JS em `scripts/` (`db.js`, `capture.js`, `forestos.js`, `focus.js`, `focus-ui.js`, `lib/focus.js`, `lib/productivity.js`, `lib/calendar.js`).

**Regras de negócio (NÃO alterar, só reusar):**
- XP sessão = `round(min × importance × difficulty / 10)`; peso = `imp×dif` (tiers Trivial→Épico).
- Missão: acumula `xp_gained` na nota; XP só credita no total na colheita (`harvestMission`, idempotente).
- Hábito: XP credita direto ao parar foco (auto-harvest); `completeHabit` marca streak (`nextStreak`: daily diff==1, weekly/custom diff<=7, monthly diff<=31); `uncompleteHabit` desfaz hoje.
- Multi-missão: consolida em nota Mission `done`+`harvested` com XP direto; <1min descarta.
- Foco exclusivo (1 sessão por vez; iniciar novo pausa o anterior).
- Timer recalcula de `focus_started_at` (nunca conta em memória).
- Documentação completa: `forestos/ForestOS - Documentação Completa.md`.

**Hub C.O.R.E.** = web app de voz/texto em `C:\Users\Meu Computador\Desktop\core-voice-hub-master\core-voice-hub-master\` (repo git): `server.py` (Flask, porta 8765, rotas `/`, `/stt`, `/ask`, `/speak`, `/session_*`; processos claude headless persistentes por sid com cwd=vault), `index.html` (HUD único), `launch.py`, `speak_server.py` (Kokoro, em `../voice-input/`). Doc: `voice-hub/CLAUDE.md`.

## As 12 decisões (contrato)

1. **Página dedicada** `forestos.html` servida em `GET /forestos`. Hub atual (`index.html`) intocado, exceto: adicionar 1 botão/link "🌲 ForestOS" que navega para `/forestos` (mesma janela, ida e volta).

2. **SQLite aposentado para ForestOS.** Estado migra para 2 arquivos no vault:
   - `forestos/_state/profile.json`: `total_xp`, `level`, `focus` corrente (`{type: mission|habit|multi|null, entity_id, started_at ISO, mode: stopwatch|pomodoro, pomo_min, importance, difficulty, mini_missions[]}`), `updated_at`.
   - `forestos/_state/events.jsonl`: append-only, 1 JSON/linha, campos: `id`, `type` (`habit_complete|xp_event|focus_session|reminder_ack`), `entity_type`, `entity_id`, `entity_title`, `focus_minutes`, `xp_gained`, `total_xp_after`, `streak_before`, `streak_after`, `data{}`, `occurred_at` ISO.
   - Tabela `multi_focus_sessions` morre (sessão ativa vive em `profile.focus`; encerradas viram evento + nota consolidada).
   - `localStorage 'forestos.focus.mono'` morre (modo mono agora em `profile.focus`).
   - Campos `counter_*` do profile descartados (estado morto, nada os incrementa).
   - `central.db` continua existindo SÓ para Finanças.

3. **Engine única = Node CLI** em `voice-hub/forestos/` (pasta nova, bem isolada do resto do Hub): `cli.js` (entrada), `lib/` (libs puras movidas do vault), `store/` (I/O de `profile.json`, `events.jsonl` e frontmatter das notas `.md` — usar lib de frontmatter tipo gray-matter ou parser YAML próprio simples; escrita de frontmatter preserva corpo da nota e wikilinks).
   - Comandos de escrita: criar cada uma das 7 entidades (nota `.md` em `forestos/` com frontmatter idêntico ao contrato atual, `id` uuid, wikilinks `[[...]]` nos vínculos), `focus start mission|habit|multi`, `focus stop` (credita conforme regras), `focus cancel`, `harvest`, `habit complete/uncomplete`, mini-missão `add/toggle/remove`, `reminder ack`.
   - Comandos de leitura: `dashboard` devolve UM JSON com tudo (perfil + foco ativo + missões por setor + hábitos + lembretes + anotações + cartografia + heatmaps por dia).
   - Reusar as regras das libs puras SEM reescrever fórmulas.

4. **Libs puras MOVIDAS (não copiadas)** do vault para `voice-hub/forestos/lib/`: `scripts/lib/focus.js`, `scripts/lib/productivity.js`, `scripts/forestos.js`. `scripts/lib/calendar.js`: mover SÓ se grep provar que Finanças (`scripts/financas.js`, `financas-ui.js`, `Finanças - Painel.md`) não a usa; senão deixar no vault. Após mover, deletar os originais do vault.

5. **Lockfile na CLI**: toda operação de escrita adquire lock (arquivo `.lock` com retry/timeout, ~20 linhas) — serializa escrita entre abas/botões/claude.

6. **Migração one-shot**: script (node, em `voice-hub/forestos/`) que:
   1. Faz backup de `db/central.db` (cópia datada).
   2. Lê `profile`+`events`+`multi_focus_sessions` do SQLite e gera `profile.json` + `events.jsonl`.
   3. NÃO dropa tabelas automaticamente — gera junto um SQL de limpeza (DROP das 3 tabelas) e atualiza `db/schema.sql` removendo a seção ForestOS, deixando claro no relatório que o DROP no `.db` vivo é passo manual/aprovado.
   - Ler SQLite via pacote node sem native build se possível (ex: sql.js) ou via python sqlite3 chamado pelo script — escolher o mais simples e documentar.

7. **`server.py` ganha rotas**: `GET /forestos` (serve `forestos.html`), `GET /forestos/state` (proxy → `node cli.js dashboard`, JSON), `POST /forestos/action {cmd, args}` (proxy → `node cli.js <cmd>`, whitelist de comandos, JSON de retorno). Spawn de node por request é aceitável (local).

8. **`forestos.html` (v1 COMPLETA**, arquivo próprio, CSS/JS próprios, estética coerente com o HUD atual):
   - Barra de foco viva: timer client-side recalculado de `started_at` a cada 1s; cronômetro e pomodoro regressivo; XP previsto; botões iniciar/concluir/concluir-com-tempo-manual/cancelar.
   - Missões ativas por setor ordenadas por peso com tier de cor (botões ▶ focar, 🌾 colher, ➕ criar).
   - Hábitos com streak/feito-hoje (▶, ✅, ↩, ➕).
   - Sessão multi-missão (🎯 configurar: modo, presets pomodoro 15/25/45/60+custom, mini-missões add/toggle/remove/reorder, imp/dif 1–5).
   - Cartografia (árvore Setor→Projeto→Objetivo→Missão + órfãos, criar entidades).
   - Heatmaps de foco e de hábitos (grade mensal de `events.jsonl`, escala verde).
   - Resumo/perfil (XP total, foco por setor).
   - Lembretes (hora/frequência, ✔ ack, ➕ criar, vencidos destacados).
   - Anotações (cards por cor, ➕ criar).
   - Dados: polling `GET /forestos/state` a cada 3s + refresh imediato pós-ação. Botões = feedback visual silencioso (SEM voz).

9. **Alarme local de lembretes na página**: JS checa `time_of_day`/`frequency`/`custom_days`/`due_at` no client; ao disparar (e `last_acked_at != hoje`): earcon + fala via `POST /speak` existente (entra na `SPEAK_Q` normal). Tolerância: se a página abrir até 2h após a hora, fala "lembrete atrasado"; mais velho, só destaque visual. `once` usa `due_at`.

10. **Skill `forestos-ops`** criada em `.claude/skills/forestos-ops/SKILL.md` DO VAULT (o claude headless do Hub roda com cwd=vault): instrui que TODA ação ForestOS (criar entidade, foco, colher, hábito, lembrete) deve ser feita via `node C:/Users/Meu Computador/Desktop/core-voice-hub-master/core-voice-hub-master/forestos/cli.js <cmd>` — NUNCA editar frontmatter/estado na mão; sem pedir confirmação; a resposta declara o que fez (ex: "Colhida: X, +42 XP"). Documentar os comandos da CLI na skill.

11. **Faxina no vault** (após CLI+página funcionarem):
    - Deletar `scripts/focus.js` e `scripts/focus-ui.js`.
    - Em `scripts/capture.js` remover só a parte ForestOS (`novoSetor/novoProjeto/novoObjetivo/novaMissao/novoHabito/novoLembrete/novaAnotacao`, `dvOptions`, `createEntityNote` se nada de Finanças usar) mantendo Finanças intacto.
    - Deletar `Templates/ForestOS/`.
    - Refazer `forestos/ForestOS - Painel.md` READ-ONLY (sem botões ▶/🌾/✅/🎯, sem barra de foco interativa; DataviewJS lê `forestos/_state/*.json[l]` via fs e as libs via require do path do Hub).
    - Em `Central de Comando.md` remover botões de captura ForestOS e barra de foco, colocar link/nota "ForestOS agora no Hub" (captura Finanças fica).

12. **Documentação atualizada por último**: reescrever `forestos/ForestOS - Documentação Completa.md`, `forestos/Modelo de Dados ForestOS.md` e `forestos/ForestOS Index.md` refletindo a nova arquitetura (estado em `_state/`, escritor único = CLI, Obsidian read-only); atualizar CLAUDE.md do vault (seções 3/6/8 sobre ForestOS: `db/` agora só Finanças, engine no Hub); atualizar `voice-hub/CLAUDE.md` (nova página, rotas novas, pasta `forestos/`, seção 9 pendências, e substituir a seção 12 "sem lock" pela política de lockfile); atualizar `voice-hub/README.md` se citar estrutura.

## Restrições

- NÃO tocar em nada de Finanças (`scripts/db.js`, `financas*.js`, libs `dates/money/aggregations/recurrence/insights`, tabelas SQLite de finanças, `Finanças - Painel.md`).
- NÃO quebrar o Hub existente (`index.html`/fluxo voz/sessões) — única mudança nele é o link p/ `/forestos`.
- `prd.md` e `issues.md`: escrever NO REPO voice-hub (`C:\Users\Meu Computador\Desktop\core-voice-hub-master\core-voice-hub-master\`) — sobrescrever os existentes (são de ciclo anterior já concluído).
- Testes: libs movidas são puras → testes node diretos; store/lock/cli → testes com diretório temporário fake-vault; migração → testar contra CÓPIA do `central.db` real (nunca o vivo); rotas → testar handlers Flask; página → ao menos smoke test de servir e de os endpoints responderem.
- Fatiar em vertical slices na ordem: (1) CLI store+lock+profile/events, (2) comandos de escrita+leitura da CLI com libs movidas, (3) migração one-shot, (4) rotas `server.py`, (5) `forestos.html` painel+ações, (6) alarme lembretes, (7) skill `forestos-ops`, (8) faxina vault + painel read-only, (9) docs.
- Git: trabalhar no repo voice-hub em branch nova (ex: `feature/forestos-integration`), commits por slice. Mudanças no vault não são git (vault sem repo) — aplicar direto.
- ANTES da primeira slice: o repo tem mudanças não commitadas de um ciclo anterior já aprovado (modo texto: `index.html`, `server.py`, `test_effort_server.py`, `test_frontend_static.py`, `_dev-loop-archive/`, este `task-forestos.md`). Commitar tudo isso PRIMEIRO num commit separado (`chore: ciclo modo-texto anterior + arquivos do dev-loop`) para não misturar com as slices do ForestOS.
