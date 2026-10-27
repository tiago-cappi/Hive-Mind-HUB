# Issues — Migração ForestOS → Hub C.O.R.E.

> Slices verticais na ordem do contrato (`task-forestos.md`). Cada uma entrega valor observável
> e tem critério de aceite testável pelo Juíz. Dono do canal: Planejador. Detalhe de I/O no `prd.md`.
> Working dir do código: `C:\Users\Meu Computador\Desktop\core-voice-hub-master\core-voice-hub-master\` (repo git, branch `feature/forestos-integration`).
> Vault (não-git): `C:\Users\Meu Computador\Documents\Obsidian Vault\`.

## Slices

### ISS-000 — Prep git: isolar ciclo anterior + branch da feature
- **Slice:** Deixar o repo `voice-hub` limpo e numa branch dedicada ANTES de qualquer código ForestOS. Commitar as mudanças não commitadas do ciclo anterior (`index.html`, `server.py`, `test_effort_server.py`, `test_frontend_static.py`, `_dev-loop-archive/`, `task-forestos.md`, e as deleções de `prd.md`/`issues.md` antigos) num commit separado; criar/entrar na branch `feature/forestos-integration`.
- **Critério de aceite:**
  - Existe um commit `chore: ciclo modo-texto anterior + arquivos do dev-loop` contendo exatamente os arquivos do ciclo anterior (não mistura nada de ForestOS).
  - `git status` limpo após o commit (fora `prd.md`/`issues.md` deste ciclo, que podem entrar num commit de planejamento).
  - Branch ativa = `feature/forestos-integration`.
- **Status:** aprovado

### ISS-001 — CLI: store + lockfile + profile/events
- **Slice:** Fundação de I/O da engine em `voice-hub/forestos/`: `store/` lê/escreve `forestos/_state/profile.json` e `events.jsonl`, e lê/escreve frontmatter de `.md` preservando corpo/wikilinks; `.lock` com retry/timeout serializa escritas. Executável mínimo via `cli.js` para provar leitura/gravação de profile e append de evento. (PRD F1)
- **Critério de aceite (fake-vault temporário):**
  - Ler `profile.json` ausente devolve default seed `{total_xp:0, level:1, focus:{type:null}, updated_at}`; após escrever e reler, valores batem e `updated_at` muda.
  - `profile.json` NÃO contém campos `counter_*`; `focus` segue o shape do PRD F1.
  - Append em `events.jsonl` adiciona 1 linha JSON válida com os campos do PRD F1; reler devolve N eventos (tolera linha final vazia).
  - Escrever frontmatter numa nota `.md` com corpo + `[[wikilink]]` altera só o campo pedido; corpo e wikilinks ficam idênticos (diff só no frontmatter).
  - Lock: duas escritas concorrentes serializam (nenhuma corrompe o arquivo); lock é liberado mesmo quando a operação lança; `.lock` some ao fim.
- **Status:** aprovado

### ISS-002 — CLI: comandos de escrita e leitura + libs movidas
- **Slice:** Mover libs puras para `voice-hub/forestos/lib/` (`focus.js`, `productivity.js`, `forestos.js`; `calendar.js` se grep confirmar que Finanças não usa) e deletar os originais do vault; implementar todos os comandos de escrita e o `dashboard` de leitura em `cli.js`, reusando as libs SEM reescrever fórmulas. (PRD F2, F3, F4)
- **Critério de aceite (fake-vault temporário + testes node):**
  - Paridade das libs: `sessionXp`, `nextStreak`, `pesoTier`, `heatTierFor`, `cartografia`, `missionsBySector` etc. dão os mesmos resultados de antes (casos numéricos: XP `round(min×imp×dif/10)`, streak daily/weekly/monthly, tiers Trivial→Épico). Originais do vault (`scripts/lib/focus.js`, `scripts/lib/productivity.js`, `scripts/forestos.js`) não existem mais.
  - Criar cada uma das 7 entidades gera nota `.md` em `forestos/` com frontmatter idêntico ao contrato (id uuid, `tipo`, defaults como `capture.js`, vínculos `[[...]]`) e corpo `# Título`.
  - `focus start mission` → grava `profile.focus`; iniciar outro foco pausa (credita) o anterior; `focus stop` de missão acumula `focus_minutes`+`xp_gained` na nota e grava evento `focus_session` (não credita `total_xp`).
  - `focus stop` de hábito credita XP direto no `total_xp` + evento `xp_event`; `harvest` credita `xp_gained` no total, marca `done`+`harvested`, é idempotente (2ª vez → `{already:true}`, total inalterado).
  - `habit complete` aplica `nextStreak` e grava `habit_complete`; repetido no mesmo dia → `{already:true}`; `uncomplete` reverte e remove o evento de hoje.
  - `focus start multi` + mini-missão `add/toggle/remove` operam a sessão; `focus stop` multi ≥1min consolida nota `done`+`harvested` com XP direto; `<1min` descarta sem XP; `focus cancel` zera foco sem XP.
  - `reminder ack` grava `last_acked_at`=hoje + evento `reminder_ack`.
  - `dashboard` devolve UM JSON com `profile, focus, missionsBySector, habits, reminders, anotacoes, cartografia, heatmaps, sectorSummary`; vault vazio → listas vazias sem erro.
  - Comando/entidade inexistente → JSON de erro claro, sem stack trace/crash.
- **Status:** aprovado

### ISS-003 — Migração one-shot SQLite → JSON
- **Slice:** Script Node em `voice-hub/forestos/` que faz backup de `central.db`, lê `profile`+`events`+`multi_focus_sessions` e gera `profile.json`+`events.jsonl`, gera `.sql` de DROP das 3 tabelas ForestOS e atualiza `db/schema.sql` removendo a seção ForestOS — sem dropar nada no `.db` vivo. (PRD F5)
- **Critério de aceite (contra CÓPIA do `central.db`, nunca o vivo):**
  - Rodar sobre uma cópia gera `profile.json` com `total_xp`/`level` do SQLite, `focus` mapeado do foco corrente (mission/habit/multi + `focus_started_at`), sem `counter_*`.
  - `events.jsonl` tem 1 linha por evento do SQLite, `occurred_at` preservado, campos mapeados ao PRD F1.
  - Cria backup datado de `central.db`; gera `.sql` com DROP das 3 tabelas ForestOS (e nada de Finanças).
  - `db/schema.sql` resultante não tem a seção ForestOS (profile/events/multi_focus_sessions) e mantém Finanças + o aviso de `goals`=metas financeiras.
  - Relatório stdout mostra contagens migradas e deixa explícito que o DROP no `.db` vivo é manual/aprovado; o script NÃO altera o `.db` vivo.
  - Escolha do leitor SQLite (sql.js ou python sqlite3) documentada e roda sem native build.
- **Status:** aprovado

### ISS-004 — Rotas no `server.py`
- **Slice:** Três rotas novas no Flask sem tocar nas existentes: `GET /forestos` (serve `forestos.html`), `GET /forestos/state` (proxy `cli.js dashboard`), `POST /forestos/action {cmd,args}` (proxy `cli.js <cmd>` com whitelist). (PRD F6)
- **Critério de aceite (testes de handler Flask):**
  - `GET /forestos` → 200 + HTML da página.
  - `GET /forestos/state` → 200 + JSON do dashboard (mesmo shape do `cli.js dashboard`); erro do CLI → 500 com `{error}` (não HTML de stacktrace).
  - `POST /forestos/action` com `cmd` da whitelist → 200 + JSON do CLI; `cmd` fora da whitelist → 400; erro do CLI → 500 `{error}`.
  - Rotas de voz/sessão (`/`, `/stt`, `/ask`, `/speak`, `/session_*`) continuam respondendo como antes (smoke test).
- **Status:** aprovado

### ISS-005 — `forestos.html`: painel completo + ações
- **Slice:** Página v1 completa (CSS/JS próprios, estética do HUD) com todos os painéis do PRD F7, consumindo `GET /forestos/state` (polling 3s + refresh pós-ação) e disparando `POST /forestos/action`. Adicionar no `index.html` só o link "🌲 ForestOS" → `/forestos` (mesma janela). (PRD F7, decisão 1)
- **Critério de aceite:**
  - `GET /forestos` renderiza: barra de foco viva (timer client de `started_at` a 1s, cronômetro e pomodoro regressivo, XP previsto, botões iniciar/concluir/concluir-com-tempo-manual/cancelar), missões por setor ordenadas por peso com tier de cor, hábitos (streak/feito-hoje + ▶✅↩➕), multi-missão (🎯 modo/presets pomodoro 15/25/45/60+custom/mini-missões/imp-dif), cartografia (árvore + órfãos + criar), heatmaps de foco e hábitos (grade mensal escala verde), resumo/perfil, lembretes, anotações.
  - Cada botão de ação chama `POST /forestos/action` e a UI re-renderiza com o novo estado; feedback é visual e **silencioso** (sem voz).
  - Timer é sempre `now - started_at` (recarregar a página mantém a contagem correta).
  - `index.html` ganhou o link para `/forestos` e nada mais mudou nele (voz/sessão intactas); smoke test de servir a página e endpoints responderem.
- **Status:** aprovado

### ISS-006 — Alarme local de lembretes na página
- **Slice:** JS do client checa `time_of_day`/`frequency`/`custom_days`/`due_at`; ao vencer (e não `acked` hoje) toca earcon + fala via `POST /speak`. (PRD F8, decisão 9)
- **Critério de aceite:**
  - Lembrete vencido no horário com `last_acked_at != hoje` → dispara earcon + `POST /speak` (entra na `SPEAK_Q`); botão ✔ chama `reminder ack`.
  - Página aberta até 2h após a hora → fala "lembrete atrasado"; mais velho que 2h → só destaque visual, sem fala.
  - `once` usa `due_at`; não dispara duas vezes no mesmo dia se já `acked`.
- **Status:** aprovado

### ISS-007 — Skill `forestos-ops` no vault
- **Slice:** Criar `.claude/skills/forestos-ops/SKILL.md` no vault instruindo o claude headless a operar TODA ação ForestOS via `node C:/Users/Meu Computador/Desktop/core-voice-hub-master/core-voice-hub-master/forestos/cli.js <cmd>`, nunca editando estado/frontmatter na mão, sem pedir confirmação, declarando o efeito. Documenta todos os comandos + args. (PRD F9, decisão 10)
- **Critério de aceite:**
  - `SKILL.md` existe no caminho, com description que dispara nos verbos ForestOS (criar entidade, foco, colher, hábito, lembrete).
  - Documenta cada comando da CLI e seus args, com o caminho absoluto correto do `cli.js`.
  - Instrui explicitamente: nunca editar `.md`/`.json` na mão; sem confirmação; resposta declara o efeito (ex.: "Colhida: X, +42 XP").
- **Status:** aprovado
- **Verificação do Juíz (2026-07-15):** `SKILL.md` existe em `Obsidian Vault/.claude/skills/forestos-ops/`; `description` dispara nos verbos ForestOS (criar entidade, foco, colher, hábito, mini-missão, lembrete/ack). Documenta cada comando e seus args (`criar <tipo> '<json>'`, `focus start mission|habit|multi`, `focus stop [override]`, `focus cancel`, `harvest`, `habit complete|uncomplete`, `mini add|toggle|remove`, `reminder ack`, `dashboard`, `profile:*`/`event:*`) com o caminho absoluto correto `node C:/Users/Meu Computador/Desktop/core-voice-hub-master/core-voice-hub-master/forestos/cli.js` (Windows). Cruzei cada comando documentado com o dispatch real de `cli.js` — batem 1:1. Instrui explicitamente nunca editar `.md`/`.json`/`_state/*` na mão, sem pedir confirmação, e declarar o efeito. Exercitei a CLI num fake-vault (FORESTOS_VAULT): `criar missao` → `{ok,path,id,tipo}`; `focus start`+`focus stop 15` (imp4/dif3) → XP 18 (`round(15×4×3/10)`); `harvest` credita 18 e 2ª vez `{already:true}`; tipo/comando/entidade inexistente → `{ok:false,error}` sem crash — como a skill promete.

### ISS-008 — Faxina no vault + painel read-only
- **Slice:** Após CLI+página operantes: deletar `scripts/focus.js` e `scripts/focus-ui.js`; remover de `scripts/capture.js` só a parte ForestOS (mantendo Finanças); deletar `Templates/ForestOS/`; refazer `forestos/ForestOS - Painel.md` READ-ONLY (lê `_state/*` via fs, libs via require do Hub, sem botões/foco interativo); em `Central de Comando.md` remover captura/foco ForestOS e pôr link "ForestOS agora no Hub". (PRD F10, decisão 11)
- **Critério de aceite:**
  - `scripts/focus.js` e `scripts/focus-ui.js` não existem mais; `Templates/ForestOS/` removido.
  - `scripts/capture.js` sem as funções ForestOS (`novoSetor..novaAnotacao`, `dvOptions`, e `createEntityNote` se grep provar que Finanças não usa) e com Finanças 100% intacto (funções de Finanças e seu `module.exports` preservados).
  - `forestos/ForestOS - Painel.md` renderiza dados a partir de `forestos/_state/*.json[l]` (read-only, sem ▶/🌾/✅/🎯 nem barra de foco interativa) e não quebra com `_state/` vazio.
  - `Central de Comando.md` sem botões de captura/foco ForestOS, com o link "ForestOS agora no Hub"; captura de Finanças mantida.
- **Status:** aprovado
- **Verificação do Juíz (2026-07-15):** `ls` confirma que `scripts/focus.js`, `scripts/focus-ui.js` e `Templates/ForestOS/` não existem mais; `scripts/` só tem `capture.js, db.js, financas-ui.js, financas.js, lib`. `capture.js`: grep das funções ForestOS (`novoSetor..novaAnotacao`, `dvOptions`) = 0 ocorrências; `createEntityNote` removido e `grep -rn createEntityNote scripts/` = 0 (Finanças não usa, condição do PRD satisfeita); restam só as funções de Finanças (`novaCategoria/novoLancamento/novaRecorrencia/novaMeta/novoAporte/novoOrcamento`) + `module.exports`; `node --check` passa em `capture.js`/`financas.js`/`financas-ui.js`. `forestos/ForestOS - Painel.md` é read-only: lê `_state/profile.json`+`events.jsonl` via `fs`, libs via `require` do Hub, fallback quando `_state/` vazio; os 2 matches de "botão" são benignos (linha 42 = nota "aqui não há botões"; linha 177 = ícone 🌾 de exibição de missão colhida, não ação). `Central de Comando.md`: 0 botões de captura/foco ForestOS, com o bloco "🌲 ForestOS agora no Hub" apontando `http://localhost:8765/forestos`; captura de Finanças mantida. `vault-cleanup.test.js` verde (parte dos 113).

### ISS-009 — Documentação atualizada
- **Slice:** Reescrever `forestos/ForestOS - Documentação Completa.md`, `forestos/Modelo de Dados ForestOS.md`, `forestos/ForestOS Index.md` (estado em `_state/`, escritor único = CLI, Obsidian read-only); atualizar `CLAUDE.md` do vault (seções 3/6/8: `db/` só Finanças, engine no Hub); atualizar `voice-hub/CLAUDE.md` (nova página, rotas, pasta `forestos/`, pendências, política de lockfile no lugar da seção "sem lock"); atualizar `voice-hub/README.md` se citar estrutura. (PRD F11, decisão 12)
- **Critério de aceite:**
  - Os 3 docs do ForestOS refletem a nova arquitetura (estado em `_state/`, CLI escritor único, Obsidian read-only) e não citam mais o SQLite/engine antiga do ForestOS como fonte de escrita.
  - `CLAUDE.md` do vault: seções 3/6/8 dizem que `db/` é só Finanças e a engine ForestOS vive no Hub.
  - `voice-hub/CLAUDE.md`: documenta `/forestos`, as rotas novas, a pasta `forestos/`, pendências, e a seção "sem lock" foi substituída pela política de lockfile.
  - Nenhuma instrução obsoleta apontando ForestOS para SQLite/engine antiga.
- **Status:** aprovado
- **Verificação do Juíz (2026-07-15):** Os 3 docs refletem a nova arquitetura (estado em `_state/`, CLI escritor único, Obsidian read-only). Grep de ponteiros de engine antiga nos docs do ForestOS: `scripts/focus`/`focus-ui`/`processFrontMatter`/`scripts/forestos.js` só aparecem em tempo passado descrevendo a migração (`ForestOS - Documentação Completa.md` linhas 117-118 "foram removidos", linha 182 "foram deletados") — nenhuma instrução vigente. Todas as menções a `SQLite` nos 3 docs são passado ("aposentado/antigo/migrado") ou Finanças (`db/central.db` só Finanças). `CLAUDE.md` do vault: seção 3 (`db/` só Finanças, engine ForestOS no Hub fora do vault), seção 6 (Hub C.O.R.E./`/forestos`, Obsidian read-only, escrita só pela CLI), seção 8 (não alterar engine do Hub). `voice-hub/CLAUDE.md`: seção 13 documenta `/forestos`, `/forestos/state`, `/forestos/action` (whitelist), pasta `forestos/`, estado em `_state/`, pendências; a antiga "sem lock" da seção 12 foi substituída pela política de lockfile do ForestOS (`store/lock.js`), mantendo a convenção só para o resto/Finanças. `README.md` descreve `forestos/`. R4 (aberto) verificado corrigido abaixo, com teste de regressão. `docs-iss009.test.js` verde (parte dos 113).

## Reprovas do Juíz

### R1 — ISS-001 — patchFrontmatter corrompe campos inline-array de outras chaves
- **O quê:** ao aplicar `patchFrontmatter` a UM campo, o parser reescreve chaves NÃO pedidas cujo valor é um array inline YAML (`chave: []` ou `chave: [a, b]`), transformando-o em string entre aspas. Ex.: `custom_days: []` vira `custom_days: "[]"`. Isso quebra a invariante do critério de aceite "altera só o campo pedido; corpo e wikilinks ficam idênticos (diff só no frontmatter)" e corrompe o contrato de dados (o campo deixa de ser uma lista e vira string literal).
- **Onde:** `voice-hub/forestos/store/frontmatter.js` — `parseFrontmatterBlock` (linhas 40-70) só reconhece listas no formato block (`chave:` seguido de `  - item`); um valor inline `[...]` cai como escalar e `serializeScalar`/`needsQuotes` (linhas 28-38) o envolve em aspas por começar com `[`. A mesma raiz também reformata escalares inline com `:`/`#` (ex.: `time_of_day: 08:30` → `"08:30"`).
- **Por que falha (evidência real):** rodando `patchFrontmatter(copia, {focus_minutes:5})` sobre uma CÓPIA da nota real `forestos/Exercício Diário.md` (hábito, `custom_days: []`), o diff das linhas alteradas foi:
  `[{ "before": "custom_days: []", "after": "custom_days: \"[]\"" }, { "before": "focus_minutes: 0", "after": "focus_minutes: 5" }]`
  Ou seja: além do campo pedido (`focus_minutes`), a chave intocada `custom_days` foi corrompida. Há ao menos 1 nota-entidade real (`Exercício Diário.md`) com `custom_days: []` inline e várias com `tags: [..]` inline no vault — a CLI (ISS-002) patcha exatamente notas de hábito para streak/foco, então o dado real será corrompido na 1ª escrita.
- **Como reproduzir:**
  ```
  node -e 'const{patchFrontmatter}=require("C:/Users/Meu Computador/Desktop/core-voice-hub-master/core-voice-hub-master/forestos/store/frontmatter.js");const fs=require("fs"),os=require("os"),path=require("path");const d=fs.mkdtempSync(path.join(os.tmpdir(),"r-"));const f=path.join(d,"n.md");fs.copyFileSync("C:/Users/Meu Computador/Documents/Obsidian Vault/forestos/Exercício Diário.md",f);patchFrontmatter(f,{focus_minutes:5});process.stdout.write(fs.readFileSync(f,"utf8"))'
  ```
  Observar `custom_days: "[]"` na saída (deveria continuar `custom_days: []`). Sugestão de teste de regressão: incluir um caso em `frontmatter.test.js` com `custom_days: []` (e outro com `tags: [a, b]` inline e `time_of_day: 08:30`) e exigir que o único diff seja a chave patcheada.
- **Status:** corrigido
- **Verificação do Juíz (2026-07-15):** `parseFrontmatterBlock` agora reconhece listas inline (`/^\[.*\]$/` → `splitInlineList`, respeitando aspas) e `serializeFrontmatter` só reformata as chaves em `changedKeys`, mantendo as demais byte-a-byte via `raw[key]`. Repro exato da reprova sobre a cópia da nota real `Exercício Diário.md` (`patchFrontmatter(copia,{focus_minutes:5})`) agora dá diff único `focus_minutes: 0 → focus_minutes: 5`; `custom_days: []` intacto. Testes de regressão `R1: ...` adicionados e passando. Suíte completa: 13/13 passam (`node --test "test/*.test.js"`). Casos extras verificados: `tags: [foco, saude]` inline, `time_of_day: 08:30`, lista block-style e arquivo CRLF preservados.

### R2 — ISS-002 — nota consolidada da sessão multi-missão gera frontmatter que o próprio parser NÃO relê (corrupção de `description` multi-linha)
- **O quê:** o writer produz valores de frontmatter multi-linha (string com `\n`) entre aspas duplas quebrados em várias linhas físicas, mas o parser é linha-a-linha e não sabe ler valor multi-linha de volta. Resultado: ao reler a nota, `description` volta como uma string com aspa inicial literal e SEM aspa de fechamento (`"Sessão de foco multi-missão — itens trabalhados:`), perdendo o conteúdo das linhas seguintes. Pior: ao aplicar qualquer `patchFrontmatter` posterior nessa nota (campo não relacionado), a re-serialização DESCARTA de vez as linhas órfãs (`✓ A`, `○ B"`) e grava um frontmatter malformado com aspa pendente. Isso quebra o invariante de round-trip do store (PRD F1: "escrita de frontmatter idempotente por chave"; ISS-001: "altera só o campo pedido") e o critério de ISS-002 de que `focus stop` multi ≥1min "consolida nota `done`+`harvested`" — a nota nasce corrompida na leitura.
- **Onde:** `voice-hub/forestos/store/frontmatter.js` — `serializeScalar` (linhas 33-38) emite o valor multi-linha entre aspas (`needsQuotes` dispara por `:`/`#`/etc.), enquanto `parseFrontmatterBlock` (linhas 66-108) só reconhece `chave: valor` numa única linha, listas block (`- item`) e listas inline (`[...]`) — não há tratamento de escalar multi-linha (folded/literal `>`/`|` nem string com quebras). Gatilho garantido: `lib/focus.js#buildConsolidatedDescription` (linhas 56-61) monta `'…itens trabalhados:' + '' + linhas` unidos por `\n`, e `engine/focus.js#stopFocus` (linhas 128-135) grava esse texto no campo `description` do frontmatter da nota consolidada.
- **Por que falha (evidência real):** criei um fake-vault, rodei `focus start multi` (imp5/dif4, 2 mini-missões, uma marcada `done`) e `focus stop` com 20 min. A nota gerada tem no frontmatter:
  `description: "Sessão de foco multi-missão — itens trabalhados:` / `` (linha em branco) / `✓ A` / `○ B"`. Relendo pelo próprio parser (`readNote`), `description` = `"\"Sessão de foco multi-missão — itens trabalhados:"` (aspa inicial retida, conteúdo perdido). Em seguida, `patchFrontmatter(nota, {status:'inbox'})` reescreveu a nota como:
  ```
  description: "Sessão de foco multi-missão — itens trabalhados:
  sector: ""
  importance: 5
  status: inbox
  ```
  — ou seja, aspa não fechada e as linhas `✓ A`/`○ B"` sumiram. Mesma raiz atinge qualquer entidade criada via `criar` cujo `description`/`content`/`message` contenha `\n` (ex.: skill/claude headless passando descrição multi-linha).
- **Como reproduzir:**
  ```
  node -e 'const fs=require("fs"),os=require("os"),path=require("path");const fm=require("C:/Users/Meu Computador/Desktop/core-voice-hub-master/core-voice-hub-master/forestos/store/frontmatter.js");const d=fs.mkdtempSync(path.join(os.tmpdir(),"rt-"));const f=path.join(d,"n.md");fs.writeFileSync(f,"---\nid: abc\ntipo: missao\ndescription: \"Sessao — itens:\n\n✓ A\n○ B\"\nsector: \"\"\nstatus: done\n---\n# t\n\ncorpo\n","utf8");console.log("RELIDO:",JSON.stringify(fm.readNote(f).frontmatter.values.description));fm.patchFrontmatter(f,{status:"inbox"});process.stdout.write(fs.readFileSync(f,"utf8"))'
  ```
  Observar `description` relida com aspa inicial e, após o patch, o frontmatter com aspa pendente e as linhas dos itens perdidas. Fluxo real equivalente: `focus start multi` + `focus stop` (≥1 min) e depois reler/patchar a nota consolidada. Sugestão de teste de regressão: em `frontmatter.test.js`, escrever uma nota com `description` contendo `\n`, reler e exigir igualdade do valor; e patchar um campo não relacionado exigindo que `description` permaneça idêntica.
- **Status:** corrigido
- **Verificação do Juíz (2026-07-15):** `serializeScalar` agora emite valores multi-linha numa ÚNICA linha física, com `\n` escapado literal (`"…itens trabalhados:\n\n○ A\n○ B"`), e `parseScalar`/`unescapeDoubleQuoted` desfazem o escape ao reler — round-trip estável. Fluxo real (`focus.startMulti` imp5/dif4 + 2 mini-missões, depois `focus.stopFocus` 20 min) gera a nota consolidada `done`+`harvested` cujo `description` relido pelo próprio parser bate byte-a-byte com o valor original (com as quebras de linha de volta); `patchFrontmatter(nota,{sort_order:5})` num campo não relacionado mantém `description` idêntica (sem aspa pendente, sem linhas órfãs perdidas). Suíte completa: 76/76 passam (`node --test test/*.test.js`), incluindo os testes de regressão R2 em `frontmatter.test.js`/`focus-engine.test.js`. Critérios adjacentes reverificados sem regressão: harvest idempotente (2ª vez `{already:true}`, total inalterado), habit complete já-feito-hoje `{already:true}`, entidade inexistente → JSON de erro claro sem crash.

### R3 — ISS-006 — lembrete já `acked` REDISPARA à noite (mismatch data UTC no client × data local no CLI)
- **O quê:** o alarme de lembretes decide "acked hoje" comparando `last_acked_at` com `now.toISOString().slice(0,10)`, que é a data em **UTC**. Mas o CLI grava `last_acked_at` como data **LOCAL**. No fuso do usuário (America/Sao_Paulo, GMT-0300 — confirmado no ambiente) as duas datas divergem toda noite a partir das 21:00 local (aí o UTC já virou o dia seguinte). Consequência: um lembrete acked hoje passa a ser tratado como NÃO-acked à noite e **redispara earcon + fala** (`shouldSpeak:true`). Isso viola diretamente o critério de aceite de ISS-006 "não dispara duas vezes no mesmo dia se já `acked`" e a regra F8 "não disparar duas vezes no mesmo dia se já `acked` hoje". A mesma raiz atinge `isOverdue` (linha 460), que mantém o destaque vermelho `.reminder-overdue` num lembrete já acked durante a noite.
- **Onde:** `voice-hub/forestos.html` — `reminderAlarmState` (linha 507: `const todayISO = now.toISOString().slice(0,10)`) e `isOverdue` (linha 460: `now.toISOString().slice(0,10)`). O CLI grava em `voice-hub/forestos/engine/focus.js` — `reminderAck` (linha 325) usando `todayIso()` (linhas 29-33), que é data **local** (`getFullYear/getMonth/getDate`). O `dashboard` repassa `last_acked_at` cru (`lib/forestos.js#remindersView` faz `{...r}`), então o client recebe a data local e a compara contra a data UTC.
- **Por que falha (evidência real):** extraí `reminderDueDate`/`reminderAlarmState` do `forestos.html` e avaliei com `new Function` (mesmo método do teste). Cenário real: lembrete diário `time_of_day: 21:30`, o usuário deu `reminder ack` hoje (CLI gravou `last_acked_at: 2026-07-15`, data local), e a página checa às 22:00 local:
  ```
  now (local): Wed Jul 15 2026 22:00:00 GMT-0300
  now.toISOString().slice(0,10) [UTC]: 2026-07-16
  last_acked_at gravado pelo CLI (local): 2026-07-15
  reminderAlarmState => {"shouldSpeak":true,"message":"lembrete atrasado: Remedio"}
  ```
  Ou seja: já acked hoje, mas o alarme redispara (fala + earcon). Os testes de `reminder-alarm.test.js` não pegam isso porque montam `last_acked_at = now.toISOString().slice(0,10)` (também UTC), casando com o bug em vez de refletir o que o CLI realmente grava (local).
- **Como reproduzir:**
  ```
  node -e 'const fs=require("fs"),path=require("path");const p="C:/Users/Meu Computador/Desktop/core-voice-hub-master/core-voice-hub-master/forestos.html";const SRC=fs.readFileSync(p,"utf8");function bal(n){const re=new RegExp("function\\s+"+n+"\\s*\\(([^)]*)\\)\\s*\\{");const m=re.exec(SRC);let i=m.index+m[0].length,d=1,s=i;while(d>0&&i<SRC.length){if(SRC[i]==="{")d++;else if(SRC[i]==="}")d--;i++;}return{p:m[1],b:SRC.slice(s,i-1)};}const tol=/const\s+REMINDER_TOLERANCE_MS\s*=\s*([^;\n]+)/.exec(SRC)[1];const due=bal("reminderDueDate"),st=bal("reminderAlarmState");const code="const REMINDER_TOLERANCE_MS="+tol+";function reminderDueDate("+due.p+"){"+due.b+"}function reminderAlarmState("+st.p+"){"+st.b+"}module.exports={reminderAlarmState};";const mod={exports:{}};new Function("module","exports",code)(mod,mod.exports);const now=new Date(2026,6,15,22,0,0);const r={frequency:"daily",time_of_day:"21:30",name:"Remedio",last_acked_at:"2026-07-15"};console.log(JSON.stringify(mod.exports.reminderAlarmState(r,now)))'
  ```
  Rodar num ambiente GMT-0300 (o do usuário) → imprime `{"shouldSpeak":true,...}` para um lembrete já acked hoje. O correto seria `{"shouldSpeak":false,"reason":"acked"}`. Sugestão de correção: computar "hoje" no client em data LOCAL (mesma fórmula do `todayIso()` do CLI: `getFullYear/getMonth/getDate` com pad) em `reminderAlarmState` e em `isOverdue`, e ajustar o teste `reminder-alarm.test.js` para usar a data local (não `toISOString`) ao montar `last_acked_at`, de modo que passe a exercitar o caso noturno.
- **Status:** corrigido
- **Verificação do Juíz (2026-07-15):** `forestos.html` agora tem `localDateIso(d)` (linhas 492-495) idêntica bit-a-bit ao `todayIso()` do CLI (`getFullYear/getMonth/getDate` com pad — `forestos/engine/focus.js:29-33`), e ela substitui `now.toISOString().slice(0,10)` tanto em `reminderAlarmState` (linha 516) quanto em `isOverdue` (linha 460) e no controle `alarmedDay`/`checkReminders` (linhas 543/547-548). Repro exato da reprova rodado no fuso real America/Sao_Paulo (`TZ=America/Sao_Paulo`, offset 180 = GMT-0300): às 22:00 locais o UTC já é `2026-07-16`, mas para o lembrete diário `21:30` já `acked` hoje (`last_acked_at: "2026-07-15"`, data local gravada pelo CLI) o resultado agora é `{"shouldSpeak":false,"reason":"acked"}` — não redispara. Teste de regressão `R3: lembrete já acked HOJE (data local) não redispara à noite…` em `reminder-alarm.test.js` monta `last_acked_at` como data LOCAL crua (não `toISOString`) e trava a pré-condição de rollover UTC (linha 157), exercitando o caso noturno de verdade. Suítes completas verdes sem regressão: node 90/90 (`node --test test/*.test.js`), python 41/41 (`pytest test_forestos_page.py test_forestos_routes.py`). Critérios adjacentes de ISS-006 reverificados: vencido dentro de 2h → fala "atrasado"; >2h → só visual (`too-late`); `once` usa `due_at`; ack chama `reminder ack`.

### R4 — ISS-009 — `Modelo de Dados ForestOS.md` mantém dois ponteiros OBSOLETOS pós-migração (libs no vault + SQLite como store de estado)
- **O quê:** o rewrite da doc de modelo de dados deixou duas afirmações em **tempo presente** que contradizem a própria arquitetura migrada (e o próprio cabeçalho do doc, que diz "SQLite aposentado para o ForestOS" e "estado vive em `_state/`"):
  1. Aponta as libs puras portadas para `scripts/lib/*` — mas essas libs (`focus.js`, `productivity.js`, `forestos.js`, `calendar.js`) foram MOVIDAS para `voice-hub/forestos/lib/` na ISS-002/ISS-008 e os originais do vault foram deletados; `scripts/lib/*` hoje só tem as libs de **Finanças** (`dates/money/aggregations/recurrence/insights`).
  2. Afirma que "é por ele [o `id`] que **o SQLite referencia a nota** (foco corrente em `profile`, `events.entity_id`, `multi_focus_sessions.consolidated_mission_id`)" — descreve as 3 tabelas SQLite do ForestOS (aposentadas / com DROP planejado na ISS-003) como o mecanismo VIGENTE de referência. Pós-migração, o `id` é referenciado por `_state/profile.json` (`focus.entity_id`) e `_state/events.jsonl` (`entity_id`), não pelo SQLite.
  Isso viola diretamente o critério de aceite de ISS-009 "Nenhuma instrução obsoleta apontando ForestOS para SQLite/engine antiga" — um leitor da doc-contrato de dados é informado, no presente, que o estado/foco do ForestOS vive nas tabelas SQLite e que as libs vivem em `scripts/lib/*`.
- **Onde:** `Obsidian Vault/forestos/Modelo de Dados ForestOS.md` — linha 22-23 (`para as libs portadas (\`scripts/lib/*\`) operarem sem tradução`) e linhas 25-26 (`é por ele que o SQLite referencia a nota (foco corrente em \`profile\`, \`events.entity_id\`, \`multi_focus_sessions.consolidated_mission_id\`)`).
- **Por que falha (evidência real):**
  - `ls "Obsidian Vault/scripts/lib/focus.js" "…/productivity.js" "…/calendar.js" "Obsidian Vault/scripts/forestos.js"` → todos "No such file or directory"; as libs estão em `voice-hub/forestos/lib/` (`ls` confirma `calendar.js focus.js forestos.js productivity.js`). Logo o ponteiro `scripts/lib/*` da linha 23 aponta para local inexistente para essas libs.
  - As linhas 25-26 usam tempo presente ("o SQLite referencia") sem qualquer marcador de "modelo antigo / antes da migração", contradizendo o cabeçalho do mesmo doc (linhas 12-16) e a realidade migrada (estado em `_state/*`). `multi_focus_sessions` é exatamente uma das 3 tabelas que a ISS-003 gera DROP.
  - `forestos/test/docs-iss009.test.js` não pega: só checa presença de `_state/profile.json`/`events.jsonl` e a ausência do token literal `vivem no SQLite` (linha 41) — nenhuma asserção cobre `scripts/lib/*` como ponteiro de lib nem a frase "o SQLite referencia a nota".
- **Como reproduzir:**
  ```
  sed -n '11,26p' "C:/Users/Meu Computador/Documents/Obsidian Vault/forestos/Modelo de Dados ForestOS.md"
  ls "C:/Users/Meu Computador/Documents/Obsidian Vault/scripts/lib/focus.js" "C:/Users/Meu Computador/Documents/Obsidian Vault/scripts/forestos.js"
  ls "C:/Users/Meu Computador/Desktop/core-voice-hub-master/core-voice-hub-master/forestos/lib/"
  ```
  Observar o cabeçalho dizendo "SQLite aposentado / estado em `_state/`" versus a linha 23 apontando libs para `scripts/lib/*` (inexistentes ali) e as linhas 25-26 dizendo que o SQLite referencia a nota via `profile`/`events`/`multi_focus_sessions`. Correção sugerida: reapontar a linha 23 para `voice-hub/forestos/lib/*` (ou dropar o parêntese de local), e reescrever as linhas 25-26 para descrever o `id` como referenciado pelo estado em `_state/profile.json` (`focus.entity_id`) e `_state/events.jsonl` (`entity_id`) — deixando as tabelas SQLite apenas como origem histórica da migração, com marcador de tempo passado. Adicionar em `docs-iss009.test.js` uma asserção que reprove `scripts/lib/` como ponteiro de lib do ForestOS e a frase "o SQLite referencia a nota".
- **Status:** corrigido
- **Verificação do Juíz (2026-07-15):** ambos os ponteiros obsoletos foram reescritos em `Modelo de Dados ForestOS.md`. Linha 22-23 agora aponta as libs puras para `voice-hub/forestos/lib/` (confirmado por `ls`: os originais `scripts/lib/focus.js`/`productivity.js` e `scripts/forestos.js` não existem mais no vault; as libs estão em `voice-hub/forestos/lib/{calendar,focus,forestos,productivity}.js`). Linhas 25-28 descrevem o `id` como referenciado pelo **estado** (`_state/profile.json` `focus.entity_id` + `_state/events.jsonl` `entity_id`), com o SQLite explicitamente em tempo passado ("Antes da migração, esse papel era do SQLite (3 tabelas hoje aposentadas)"). Grep confirma que não sobrou `scripts/lib/*` como ponteiro de lib do ForestOS nem a frase "o SQLite referencia a nota". Teste de regressão adicionado (`docs-iss009.test.js` linhas 44-51: reprova `scripts/lib/*` como ponteiro, reprova "o SQLite referencia a nota", exige `voice-hub/forestos/lib` e `focus.entity_id`+`_state/profile.json`) e passa. Suíte node completa: 113/113 verdes.
