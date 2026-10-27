# ForestOS no Hub C.O.R.E. — integração

> ## ⚠️ CÓDIGO REMOVIDO EM 28/08/2026 — ESTE DOCUMENTO É A REFERÊNCIA HISTÓRICA
>
> A pasta `forestos/` (CLI e engine Node), o `forestos.html`, as três rotas
> `/forestos*` do `server.py`, o botão no `index.html` e os testes
> (`forestos/test/`, `tests/test_forestos_page.py`, `tests/test_forestos_routes.py`)
> foram **apagados de propósito**: a funcionalidade estava ultrapassada e será
> **refeita do zero**. As notas do ForestOS já não existiam no vault.
>
> **Não tente "consertar" nada disso.** Este documento fica no repositório com um
> único objetivo: descrever o que o ForestOS fazia e como se encaixava no Hub,
> para que a reconstrução futura tenha de onde partir. Leia-o como
> especificação-fonte, não como descrição do código atual.
>
> A reconstrução é **funcionalidade nova** e segue a regra 11 do `CLAUDE.md`:
> pasta própria, blueprint Flask, frontend em arquivos da própria pasta —
> **nada volta para dentro de `server.py` ou `index.html`**. Ver
> `docs/desenvolvimento.md` §5. Contexto de produto: `docs/prd.md`,
> `docs/issues.md` e `docs/_dev-loop-archive/`.

> Estado do código em 20/08/2026. Fontes: server.py, speak_server.py, forestos.html, forestos/.

Este documento cobre a **integração** do ForestOS com o Hub: a página
`/forestos`, as três rotas Flask, a engine Node em `forestos/`, onde vive o
estado e como o vault Obsidian entra na história. As **regras de negócio**
(fórmulas de XP, streaks, colheita, multi-missão, modelo de dados das 7
entidades) NÃO são redocumentadas aqui — a fonte de verdade delas é
`forestos/ForestOS - Documentação Completa.md` **no vault Obsidian**. Para o
resto do Hub, veja `arquitetura.md`, `servidor-api.md`, `frontend.md` e
`operacao.md` nesta pasta.

## 1. Visão geral

O Hub só faz duas coisas com o ForestOS: **serve a página** (`forestos.html`) e
**faz proxy** para a engine Node isolada (`forestos/cli.js`), que é o escritor
único do estado. Cada request spawna um processo `node` (aceitável: uso local,
1 usuário, timeout de 30 s em `_run_forestos_cli`). O Flask nunca toca no estado
diretamente.

```
navegador ── GET /forestos ───────────► forestos.html (página)
forestos.html ── GET /forestos/state ─► node forestos/cli.js dashboard ─► JSON
forestos.html ── POST /forestos/action {cmd,args} ─► node forestos/cli.js <cmd> ...args
claude headless (skill forestos-ops) ─► node forestos/cli.js <cmd> ...  (mesmo CLI, direto)
```

## 2. A página /forestos (forestos.html)

Arquivo único, HTML+CSS+JS vanilla sem build step, estética HUD do Hub (tokens
honey+ink+sage, painéis chanfrados, scanlines). Estrutura:

- **Barra de foco sticky** (`#focusPanel`): título do foco atual, timer, XP
  previsto e botões (iniciar multi-missão, concluir, concluir com tempo manual,
  cancelar). O timer é **sempre recalculado de `focus.started_at`**
  (`tickFocus()`, 1x/s) — nunca um contador incrementado em memória; em modo
  pomodoro mostra a contagem regressiva de `pomo_min`.
- **Seis abas client-side** (sem reload): Visão Geral, Missões, Hábitos,
  Multi-missão, Cartografia (árvore Setor→Projeto→Objetivo→Missão + heatmaps de
  foco e hábitos), Lembretes (+ Anotações).
- **Polling:** `loadState()` busca `GET /forestos/state` a cada **3 s** e
  re-renderiza tudo (`renderAll`). Toda ação de botão passa por
  `doAction(cmd, args)` → `POST /forestos/action` → `loadState()`. O feedback
  dos botões é só visual (classe `.flash`) — `doAction()` é **silencioso**, não
  fala nada (garantido por `tests/test_forestos_page.py`).
- Missões exibem tier de cor por peso (`peso = importance × difficulty`,
  faixas 1-4/5-9/10-14/15-19/20-25 — mesma tabela de
  `forestos/lib/productivity.js`).

### Alarme de lembretes (client-side) e o gotcha de data local

A **única fala** da página é o alarme de lembretes vencidos. `checkReminders()`
roda a cada **15 s** e, para cada lembrete ativo:

1. Calcula o vencimento local (`reminderDueDate`): `frequency === 'once'` usa
   `due_at`; diário/semanal/custom usa `time_of_day` (e `custom_days` contra
   `now.getDay()`).
2. Só dispara se ainda não foi confirmado hoje (`last_acked_at` ≠ hoje) e se o
   atraso está dentro da tolerância `REMINDER_TOLERANCE_MS = 2h`. Mais velho
   que isso, fica só o destaque visual `.reminder-overdue`, sem fala.
3. Ao disparar: earcon local de 880 Hz via WebAudio (`playEarcon()`) + `POST
   /speak` fire-and-forget com `"lembrete: <label>"` (ou `"lembrete atrasado:
   <label>"` se o atraso passou de 60 s) — entra na mesma `SPEAK_Q` do Hub
   (ver `voz-tts.md`).
4. Nunca dispara 2x no mesmo dia para o mesmo lembrete: `Set` local
   `alarmedToday` com chave `nome|data`, zerado na virada do dia.

> **Gotcha data local vs UTC:** "hoje" é sempre `localDateIso()` —
> `getFullYear/getMonth/getDate` locais — e **nunca**
> `toISOString().slice(0,10)`, que é UTC e diverge da data local gravada em
> `last_acked_at` a partir do fim da tarde em fusos negativos (Brasil): o
> lembrete confirmado às 21h voltaria a tocar. É a mesma fórmula do
> `todayIso()` de `forestos/engine/focus.js`; os dois lados precisam continuar
> iguais (regra R3 da documentação completa; coberto por
> `forestos/test/reminder-alarm.test.js`).

## 3. As três rotas e a whitelist

| Rota | Método | O que faz |
|---|---|---|
| `/forestos` | GET | `send_from_directory` de `forestos.html` |
| `/forestos/state` | GET | `node forestos/cli.js dashboard` → JSON consolidado (profile/focus, missionsBySector, habits, cartografia, heatmaps, sectorSummary, reminders, anotacoes); erro do CLI → `500 {error}` |
| `/forestos/action` | POST | `{cmd, args}` → `node forestos/cli.js <cmd> ...args`; `cmd` fora da whitelist → `400 {error}`; erro do CLI → `500 {error}` (nunca stacktrace HTML) |

A whitelist em `server.py` (`FOREST_ALLOWED_CMDS`) contém os **comandos de
topo** que o `cli.js` reconhece:

```python
FOREST_ALLOWED_CMDS = {
    "profile:read", "profile:write", "event:append", "event:read",
    "dashboard", "criar", "focus", "harvest", "habit", "mini", "reminder",
}
```

Subcomandos viajam dentro de `args` e são validados pelo próprio `cli.js`
(subcomando desconhecido → JSON `{ok:false, error}`):

- `focus start mission <nome>` · `focus start habit <nome>` ·
  `focus start multi '<json {mode,importance,difficulty,pomoDuration,miniMissions}>'` ·
  `focus stop [minutosOverride]` · `focus cancel`
- `habit complete <nome>` · `habit uncomplete <nome>`
- `mini add <titulo>` · `mini toggle <id>` · `mini remove <id>`
- `reminder ack <nome>`
- `criar <setor|projeto|objetivo|missao|habito|lembrete|anotacao> '<json campos>'`
- `harvest <nome-da-missao>`

`_run_forestos_cli(argv)` roda `["node", FOREST_CLI] + argv` com
`capture_output`, `timeout=30`, e faz parse **da última linha** do stdout como
JSON (o resto é log). Testes: `tests/test_forestos_routes.py` (mocka
`subprocess.run` — nenhum node real).

## 4. A pasta forestos/ (engine Node, neste repo — fora do vault)

| Item | Responsabilidade |
|---|---|
| `cli.js` | Entrada única/dispatcher. Resolve o vault (`FORESTOS_VAULT` ou `DEFAULT_VAULT = C:\Users\Meu Computador\Documents\Obsidian Vault`), despacha para store/engine e imprime **uma linha JSON** no stdout; erro vira `{ok:false, error}` com exit code 1, nunca stack trace |
| `store/paths.js` | Todos os caminhos derivados de `vaultRoot` explícito (testável com fake-vault em tmp): `<vault>/forestos/`, `_state/`, `profile.json`, `events.jsonl`, `.lock` |
| `store/lock.js` | Lockfile de escrita serializada (ver seção 5) |
| `store/profile.js` | Leitura/escrita de `_state/profile.json` (seed default `{total_xp:0, level:1, focus:{type:null}}`); toda escrita passa pelo lock |
| `store/events.js` | Append/leitura de `_state/events.jsonl` (evento normalizado com os campos do contrato: id, type, entity_*, focus_minutes, xp_gained, total_xp_after, streak_*, data, occurred_at); append sob lock |
| `store/frontmatter.js` | Parser/serializer YAML próprio (escalares + listas), round-trip estável: regrava só as chaves do patch e preserva corpo/wikilinks da nota |
| `store/notes.js` | Leitura/escrita das notas `.md` das 7 entidades em `<vault>/forestos/` (flat); converte vínculos nome↔wikilink (`sector`, `project`, `goal`, `parent_*`, `category`) |
| `engine/entities.js` | Criação das 7 entidades (`criar`) com defaults do modelo de dados |
| `engine/focus.js` | Orquestra foco/XP/hábitos/lembretes: start/stop/cancel, harvest, complete/uncomplete, mini-missões, `reminder ack`. Invariantes: missão acumula minutos/XP na nota (total só na colheita); hábito credita XP direto; multi ≥1 min consolida nota done+harvested; foco novo pausa (credita) o anterior |
| `engine/dashboard.js` | Comando de leitura `dashboard`: agrega profile/_state + notas num único JSON, reusando as libs puras |
| `lib/` | Funções **puras** (sem Obsidian, testáveis em Node): `focus.js` (XP da sessão = `round(min × importance × difficulty / 10)`, streaks), `forestos.js` (cartografia/agrupamentos), `productivity.js` (peso/heat tiers), `calendar.js` (grade do mês) |
| `migrate.js` | Migração one-shot SQLite → JSON (`--db --vault [--schema]`): despeja `profile`/`events`/`multi_focus_sessions` do `central.db` via `python -c` (sqlite3 da stdlib — sem dependência node nativa), faz backup `.bak-<timestamp>`, escreve `profile.json`/`events.jsonl` e gera um `.sql` de DROP que é **passo manual** — nunca dropa o banco vivo sozinho |
| `test/` | 17 suítes `node:test` (store, engine, libs, cli, migrate, alarme de lembretes, skill, docs) |

## 5. Estado, lockfile e o vault Obsidian

- **Estado vivo:** `<vault>/forestos/_state/profile.json` (perfil + foco
  corrente) e `<vault>/forestos/_state/events.jsonl` (log append-only). O
  `central.db` (SQLite) não guarda mais nada de ForestOS — só Finanças.
- **Lockfile:** `store/lock.js` cria `<vault>/forestos/_state/.lock` com flag
  exclusiva (`wx` falha se já existir) e retry de **20 ms** até timeout de
  **5000 ms**; `withLock()` libera sempre, mesmo com exceção. **Toda escrita**
  (profile, events, notas) passa por ele — serializa qualquer combinação de
  abas do Hub, botões da página `/forestos` e claude headless escrevendo ao
  mesmo tempo. (O resto do vault não tem lock — ver `arquitetura.md`.)
- **Vault read-only para o Obsidian:** as entidades continuam sendo notas `.md`
  em `<vault>/forestos/` (legíveis/linkáveis no Obsidian normalmente), mas o
  Obsidian **não escreve mais** — toda mutação passa por `forestos/cli.js`.
  Diretórios/arquivos de estado são criados sob demanda (`mkdirSync recursive`)
  na primeira escrita.
- **Skill `forestos-ops`:** `.claude/skills/forestos-ops/SKILL.md` no vault
  instrui o claude headless do Hub (cwd = vault) a operar toda ação ForestOS
  via `node .../forestos/cli.js <cmd>` com o caminho absoluto do CLI deste
  repo — nunca editando frontmatter/estado na mão. O contrato dela é validado
  por `forestos/test/forestos-ops-skill.test.js` (frontmatter, caminho do CLI,
  todos os comandos, 7 tipos de entidade). Atenção: em 20/08/2026 esse arquivo
  **não existe** no vault atual (nem `<vault>/forestos/`) — o teste da skill
  falha até o vault ser repovoado; ver `operacao.md`.

## 6. Rodando os testes

```
# Flask (mocks, sem node/whisper reais):
python -m pytest tests/test_forestos_routes.py tests/test_forestos_page.py -q

# Engine Node (node:test, sem dependências externas — usa fake-vault em %TEMP%):
node --test forestos/test/
```

Os testes Node criam vaults temporários via `FORESTOS_VAULT`/parâmetro
`vaultRoot`; nenhum toca o vault real. `migrate.test.js` roda só contra cópias
de banco (contrato: **nunca** rodar `migrate.js` contra o `central.db` vivo em
teste).

## 7. Referências

- `forestos/ForestOS - Documentação Completa.md` (no vault) — fonte de verdade
  das regras de negócio (XP, streaks, colheita, modelo de dados, gotchas R1-R3).
- `docs/prd.md`, `docs/issues.md`, `docs/task-forestos.md`,
  `docs/task-forestos-redesign.md` — histórico do dev-loop da migração.
- `voz-tts.md` — o canal `/speak` usado pelo alarme de lembretes.
