# Servidor — referência da API (`server.py`)

> Estado do código em 20/08/2026. Fonte: server.py e scripts da raiz.

A ponte local do Hub C.O.R.E. é um único arquivo, `server.py`: Flask escutando **somente em `127.0.0.1:8765`** (`PORT = 8765`, `app.run(host="127.0.0.1", port=PORT, threaded=True)`). Ela serve o front (`index.html`, `forestos.html`), faz STT com faster-whisper local, orquestra processos `claude` headless persistentes (um por sessão) e dispara a fala no Kokoro residente. Visão geral das peças em `arquitetura.md`; front em `frontend.md`; fala em `voz-tts.md`; ForestOS em `forestos.md`; relatórios em `relatorios.md`; operação em `operacao.md`.

Todas as respostas levam `Cache-Control: no-store, max-age=0` (hook `no_cache` em `@app.after_request`). As rotas de streaming (`/ask`, `/speak`) respondem `application/x-ndjson` com `X-Accel-Buffering: no`.

---

> Atualização de 08/10/2026: runtime e caminhos centralizados no projeto;
> GET `/hub_identity` identifica protocolo, raiz e PID somente na ponte local.
> Não está na whitelist mobile. Configuração em `runtime.md`.

## 1. Mapa de rotas

| Rota | Método | Entrada | Saída |
|---|---|---|---|
| `/` | GET | — | `index.html` |
| `/assets/<fn>` | GET | — | arquivo estático de `assets/` |
| `/hud_ping` | POST | JSON `{hud}` | `{ok, huds, ttl, autoquit}` — pulso de uma janela do HUD (seção 2.1) |
| `/hud_bye` | POST | JSON `{hud}` | `{ok, huds}` — baixa da janela ao fechar (`sendBeacon`) |
| `/stt` | POST | multipart, campo `audio` (webm) + campo `sid` (opcional) | `{"texto": "..."}` |
| `/ask` | POST | JSON `{texto, modelo, esforco, sid, titulo, earcon_hz, mudo}` | **NDJSON em streaming** (seção 4) |
| `/speak` | POST | JSON `{reply, sid, titulo, earcon_hz}` | NDJSON `speak_queued`/`speak_start`/`speak_env`/`speak_done` — detalhes em `voz-tts.md` |
| `/session_start` | POST | JSON `{sid, modelo, esforco}` | `{ok, alive, spawned, model, sid}` |
| `/session_reset` | POST | JSON `{sid, modelo, esforco}` | `{ok, alive}` |
| `/session_end` | POST | JSON `{sid}` | `{ok: true}` |
| `/abort` | POST | JSON `{sid}` | `{ok, alive}` |
| `/session_watch/<sid>` | GET | `?rev=N` (long-poll) | `{rev, lines: [...], line}` — espelho somente-leitura do NDJSON daquele sid (seção 4.6) |
| `/reports` | GET | — | `{"reports": [{file, title, mtime, size}]}` |
| `/reports/<fn>` | GET | — | arquivo da pasta de relatórios |
| `/reports/<fn>` | DELETE | — | `{ok: true}` \| erro 400/404/500 |
| `/forestos` | GET | — | `forestos.html` |
| `/forestos/state` | GET | — | JSON do `node forestos/cli.js dashboard` |
| `/forestos/action` | POST | JSON `{cmd, args}` | JSON do CLI \| `{error}` 400/500 |

---

## 2.1 Ciclo de vida — a ponte morre junto com o HUD

A ponte era residente de propósito: reabrir o Hub reaproveitava o servidor no ar. O preço apareceu na prática — fechar a janela do Chrome não derrubava nada, e um `pythonw server.py` ficou **18 h** segurando a 8765 com **código velho em memória**: editar o `server.py` não mudava nada, porque o processo no ar era o de ontem.

Hoje cada janela do HUD gera um `HUD_ID` próprio, pulsa em `POST /hud_ping` a cada 15 s e dá baixa em `POST /hud_bye` (`sendBeacon` no `beforeunload`). Um watchdog (`_hud_watchdog`, thread daemon iniciada no `__main__`) acorda a cada 2 s, recolhe os HUDs calados há mais de `HUD_TTL` e, quando não sobra nenhum, chama `_shutdown()` e `os._exit(0)`.

Três decisões que o desenho carrega:

- **Registro por id, não contador.** Com duas janelas abertas, fechar uma não pode derrubar a ponte da outra.
- **Só arma depois do primeiro pulso** (`HUD_EVER`). A suíte de testes, o cliente do celular (`mobile/`) e scripts auxiliares sobem o `server` sem nenhum HUD — sem essa trava, a ponte se mataria sozinha logo após o boot.
- **`HUD_TTL` folgado (90 s).** O Chrome estrangula timers de janela em segundo plano até ~1 pulso/minuto; um TTL curto derrubaria a ponte com o HUD apenas minimizado. O caminho rápido é o `/hud_bye`, não o TTL — o TTL cobre `kill`/crash, em que nenhum `beforeunload` dispara.

`HUB_AUTOQUIT=0` desliga o mecanismo (útil para deixar a ponte de pé só para o celular, sem HUD aberto). Coberto por `tests/test_autoquit.py`.

---

## 2. STT — `POST /stt`

Recebe o áudio como multipart (`request.files["audio"]`), salva em `%TEMP%\hub_stt_in_<sid>.webm` (`_stt_path(sid)`) e transcreve com o modelo global `WMODEL = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")`, com `language="pt"` e `vad_filter=True`. Sem arquivo de áudio, devolve `{"texto": ""}` sem erro. O campo `sid` é opcional (ausente = `DEFAULT_SID`), então quem já chamava a rota sem ele continua funcionando.

**Um arquivo por sessão, uma transcrição por vez.** Antes havia um único `hub_stt_in.webm` global: duas abas gravando ao mesmo tempo sobrescreviam o áudio uma da outra. Hoje o nome sai de `_stt_path(sid)` (sid sanitizado para `[A-Za-z0-9_-]`, 40 chars). E o `WMODEL` é **um só objeto** num Flask `threaded=True`, e o faster-whisper não é thread-safe — por isso a transcrição roda sob a guarda nomeada **`STT_LOCK`** (regra 5 do `CLAUDE.md`, ao lado de `SPEAK_Q` e `LOG_LOCK`). O `"".join(...)` fica **dentro** do lock: o trabalho do faster-whisper acontece ao iterar o generator, não na chamada de `transcribe()`.

**Custo real e por que o padrão é `base`.** O STT é síncrono e roda na CPU. Medido nesta máquina (i5-1235U, int8, `vad_filter=True`): `small` transcreve a **0,37× o tempo real** e `base` a **0,72×** — num áudio de 4 min 42 s isso é ~13 min contra ~6,5 min, e no mesmo áudio o `base` transcreveu **melhor** que o `small`. Por isso `WHISPER_MODEL = os.environ.get("HUB_WHISPER", "base")`. O modelo é carregado **no import do módulo** — é por isso que o boot da ponte demora (e por isso os testes stubam `faster_whisper` antes de importar `server`).

Como a rota é bloqueante e pode levar minutos, quem segura o outro lado é o front: teto de gravação de 180 s, cronômetro visível na fase de transcrição e `AbortController` com teto de 420 s (`frontend.md` §6).

---

## 3. Modelo de sessões — `SESS[sid]` e os processos `claude`

Cada aba do front tem um `sid` próprio com um processo `claude` headless **persistente e isolado** — contexto em memória, sem reinício por mensagem. O registro global é:

```python
SESS = {}                    # sid -> {"proc","model","effort","q","lock","fresh","last_used"}
REG_LOCK = threading.Lock()  # protege criação/remoção/ITERAÇÃO de entradas em SESS
DEFAULT_SID = "default"      # usado se o front não mandar sid (defensivo)
MAX_SESS = 6                 # teto de sessões simultâneas vivas (RAM: whisper + kokoro + N*claude)
REAP_IDLE_SECS = 6 * 3600    # sessão sem uso há mais de 6h -> zumbi
```

- `get_sess(sid)` cria a entrada sob `REG_LOCK` se não existir (com `lock` próprio por sid — turnos da **mesma** sessão são serializados por ele; sessões diferentes rodam em paralelo de verdade).
- `_alive_count()` conta processos vivos (`poll() is None`) sob `REG_LOCK`; `_multi_session_active()` é `_alive_count() > 1`.
- `_reap_stale(exclude_sid)` roda a cada `/session_start`: mata e remove de `SESS` toda sessão com `last_used` há mais de `REAP_IDLE_SECS` — sobra de fechamento abrupto do Chrome cujo `sendBeacon`/`/session_end` nunca disparou. Sem isso, zumbis inflariam `_alive_count()` e ocupariam slots sem uma aba real.

### 3.4 Recursos compartilhados e guardas

SPEAK_Q/SPEAK_GATE protegem fala; STT_LOCK protege o modelo Whisper; LOG_LOCK
protege o transcript pessoal. A guarda de arquivos fica no projeto, em
hub_runtime/guards/file_guard.py, carregada explicitamente pelo runtime nos
dois caminhos do CLI. Recusa versões defasadas e segura o acervo durante a
ferramenta; ferramentas de arquivo, shell síncrono e MCP são cobertos.
A proteção é cooperativa entre sessões, não sandbox de processos externos.
Detalhes, falhas e limites em runtime.md; testes em test_runtime_guard.py.
O hook anteriormente documentado no vault não existia nesse caminho.

### 3.1 Spawn — `spawn_claude(sid, model, effort="")`

Linha de comando montada (com `shell=True`, `cwd = PROJECT_ROOT` via `hub_runtime.assistant`, `env` com `VOICE_HUB=1`, `text=True`, `encoding="utf-8"`, `bufsize=1`):

```
claude -p --input-format stream-json --output-format stream-json \
  --verbose --include-partial-messages --dangerously-skip-permissions \
  [--model X] [--effort Y]
```

- `--model X` só entra se `modelo ∈ ALLOWED_MODELS = {"fable", "opus", "sonnet", "haiku"}`; valor inválido ou vazio é ignorado (fica no default do CLI).
- `--effort Y` só entra se `esforco ∈ ALLOWED_EFFORTS = {"low", "medium", "high", "xhigh", "max"}`; idem.
- `PERMISSION_FLAG = " --dangerously-skip-permissions"` — autorizado explicitamente pelo usuário; no modo headless não há como aprovar prompts.
- `--include-partial-messages` habilita os deltas token a token (eventos `partial`/`thinking`). Se um CLI futuro rejeitar a flag, o processo morre no start, `claude_alive()` fica falso e o `/ask` cai no fallback — degrada sem quebrar.
- Duas threads `_claude_reader` (stdout com tag `out`, stderr com tag `err`) alimentam a `Queue` daquele sid; quando o stream fecha, entra o sentinela `("out_end"/"err_end", None)`.
- Ao final, grava em `SESS[sid]`: `proc`, `model`, `effort`, `q` e `last_used = time.time()`.

### 3.2 Morte de processo — `kill_claude` e `_kill_tree`

`spawn_claude` usa `shell=True`: o `Popen` é o `cmd.exe` e o `claude` real é filho dele. `p.kill()` sozinho deixava o `claude` órfão, vivo e editando arquivos por baixo do turno seguinte. Por isso `_kill_tree(p)` roda, no Windows (`os.name == "nt"`), `taskkill /PID <pid> /T /F` (timeout 10s) **e** `p.kill()`. Fora do Windows, só `p.kill()`. `kill_claude(sid)` zera `proc` e `q` no registro; `kill_all()` itera os sids sob `REG_LOCK` e mata todos.

No encerramento da ponte, `atexit` chama `_shutdown()`: manda `__quit__` ao Kokoro e roda `kill_all()` — mas **só se este processo subiu o Kokoro** (flag `SPEAK_OWNED`), para que importar o módulo (suíte de testes, script auxiliar) não mate o Kokoro da ponte que está no ar.

### 3.3 Rotas de ciclo de vida

- **`POST /session_start`** — chamado ao abrir uma aba (warm-up). Roda `_reap_stale(sid)`, e sob o lock do sid: se o processo não está vivo e `_alive_count() >= MAX_SESS`, devolve `{"ok": false, "err": "limite de 6 sessoes simultaneas"}`; senão spawna. Resposta: `{ok, alive, spawned, model, sid}`.
- **`POST /session_reset`** — NOVA CONVERSA daquela aba: `kill_claude(sid)`, marca `s["fresh"] = True` (garante que o fallback também crie uma conversa nova) e respawna com modelo/esforço pedidos. Resposta: `{ok, alive}`.
- **`POST /session_end`** — fechar a aba (via `sendBeacon` no `beforeunload`): mata o processo **e remove a entrada de `SESS`**.
- **`POST /abort`** — CANCELAR do front: mata o processo do turno em curso **sem remover o registro** (a aba segue viva; o próximo `/ask` respawna e, no fallback, o ID explícito recupera o contexto). Deliberadamente **não pega o lock do sid** — o `/ask` em curso o segura até o fim do turno, e o objetivo aqui é justamente interrompê-lo. `sid` desconhecido devolve `{"ok": true, "alive": false}` sem erro.

---

## 4. `POST /ask` — o turno de conversa (NDJSON em streaming)

Payload: `{texto, modelo, esforco, sid, titulo, earcon_hz, mudo}`. `texto` vazio devolve `{"reply": "(sem pergunta)"}` direto (JSON simples). Modelo/esforço fora das whitelists são tratados como vazio (default). Tudo roda dentro do `lock` do sid.

### 4.1 Fluxo

1. **Garantir o processo** — se o processo está vivo mas `model` **ou** `effort` mudou em relação ao pedido, mata e respawna **retomando a mesma conversa**: o respawn leva `--resume s["cid"]`, o id de conversa que o próprio CLI reporta (campo `session_id` de qualquer evento do stream-json, guardado a cada evento em `/ask`). O processo é outro; a conversa é a mesma. Sem isso, trocar de modelo no meio do papo zerava o contexto — era o bug de "ele esqueceu tudo quando eu troquei o modelo". O `debug` sai como "reiniciando claude" + "claude persistente iniciado · modelo=X · retomando <8 chars do cid>". `POST /session_reset` limpa `s["cid"]`: **nova conversa não retoma nada**. Se não está vivo: respeita `MAX_SESS` também aqui (não spawna um N+1 por baixo dos panos — emite `debug` WARN; fallback também confere o teto e não cria um processo extra); senão spawna e zera `s["fresh"]`.
2. **Caminho persistente** — escreve na stdin do processo a mensagem `{"type":"user","message":{"role":"user","content":[{"type":"text","text":texto}]}}` (uma linha JSON) e drena a `Queue` até o evento `result` do stream-json, emitindo os eventos NDJSON da seção 4.2. Constantes locais do laço: `HB = 5` (cadência do heartbeat, em segundos) e `THROTTLE = 0.3` (agrupamento dos deltas parciais, em segundos).
3. **Fallback** — se o persistente não subiu, morreu no meio ou não produziu `reply`, roda por chamada:

   ```
   claude -p [--resume <cid> | --session-id <novo-id>] --dangerously-skip-permissions [--model X] [--effort Y]
   ```

   com `Popen` registrado na sessão, `communicate(input=texto, timeout=300)`,
   `cwd=PROJECT_ROOT` e `env VOICE_HUB=1`, através do mesmo lançador operacional.
   Cancelamento e timeout encerram toda a árvore; o turno cancelado não reinicia fallback. O fallback retoma o ID do sid ou cria um UUID explícito e o guarda após sucesso; nunca usa `--continue` global ao diretório.
4. **Log** — todo turno (pergunta + resposta) é appendado por `log_turn()` em `LOG = <vault>\_agentes\voice-hub.md` com timestamp e o prefixo `[titulo ou sid]`. O append vai **sob `LOG_LOCK`**: todas as sessões escrevem nesse mesmo arquivo e o Flask é `threaded`, e o modo append do CRT no Windows faz *seek-para-o-fim + write* em duas etapas — sem o lock, duas sessões que fecham o turno juntas apontam para o mesmo offset e uma sobrescreve a outra, perdendo o turno inteiro em silêncio. Medido: 58–59 de 60 turnos sobrevivendo sem o lock, 60 de 60 com ele (`tests/test_concorrencia.py`).
5. **Fechamento** — emite `done` (antes de esperar o fim da fala em streaming, se houver) e, por último, os eventos restantes de fala.

### 4.2 Eventos NDJSON do `/ask`

Uma linha JSON por evento, campo `t` discrimina o tipo:

| Evento | Campos | Quando |
|---|---|---|
| `debug` | `{t, lv, msg}` — `lv` ∈ ASK/WARN/ERR/STEP/SPEAK/OK | diagnóstico contínuo p/ a aba DEBUG do front |
| `ask` | `{t, q, titulo}` | primeiro evento do turno: a pergunta como chegou. Os consumidores do `/ask` a ignoram (já a conhecem); existe para o espelho `/session_watch` — sem ele o HUD não teria como mostrar o que veio do celular |
| `step` | `{t, msg}` | a cada `tool_use` do Claude, traduzido por `friendly_step` ("Lendo server.py", "Rodando comando", "Delegando a subagente", "Ferramenta externa" p/ `mcp__*`...) |
| `plan` | `{t, items: [{txt, status}]}` | quando o Claude chama `TodoWrite`; `todos_to_plan` converte `input.todos` (usa `content` ou `activeForm` como texto, `status` default `pending`; formato inválido → sem evento) |
| `partial` | `{t, txt}` | deltas de texto (`text_delta`) acumulados e emitidos com throttle de `THROTTLE = 0.3`s — nunca 1 evento por token |
| `thinking` | `{t, chars}` | total acumulado de caracteres de raciocínio (`thinking_delta`) no turno; emitido junto do flush do `partial` |
| `hb` | `{t, idle_s, limit_s, tool}` | heartbeat a cada `HB = 5`s de silêncio: quanto tempo ocioso, o teto vigente do watchdog e a ferramenta em aberto (informativo — não encurta o watchdog) |
| `change` | `{t, ch}` | fechamento de ferramenta que mudou algo (seção 4.4) |
| `done` | `{t, reply, spoken}` | fim do turno; `spoken: true` = a fala já correu em streaming por este mesmo NDJSON e o front **não** deve chamar `/speak` |
| `speak_start` / `speak_env` / `speak_done` | ver `voz-tts.md` | só quando a fala em streaming foi acionada neste turno |

### 4.3 Watchdog de ociosidade

Silêncio não é sinal de travamento: um subagente, um build ou uma suíte de testes passam minutos sem emitir evento. O teto depende do que o turno estava fazendo quando calou — `inact_limit(open_tool, events)` devolve `(teto_em_segundos, motivo)`:

| Constante | Valor | Situação |
|---|---|---|
| `INACT_BOOT` | 90 | turno enviado e nem o `system/init` voltou (nenhum evento) — não engatou |
| `INACT_IDLE` | 300 | já produziu eventos, nenhuma ferramenta em aberto — raciocínio ou rede |
| `INACT_TOOL` | 1200 | ferramenta em aberto (`Agent`, `Bash`, build...) — ocupado lá dentro |

A cada 5s de fila vazia o laço calcula o ocioso; se `idle >= limit`, emite `debug` ERR e `kill_claude(sid)` — o fallback assume o turno. Antes disso, emite o evento `hb`. Processo **morto de verdade** não depende do watchdog: o stream fechado chega como tag `*_end` e quebra o laço na hora (também com `kill_claude`).

### 4.4 Registro de alterações — evento `change`

No evento `user` do stream-json que fecha cada ferramenta, o campo `tool_use_result` traz `structuredPatch` (hunks unified diff) para as ferramentas de escrita. `change_from_tool(name, input, result, is_error)` monta o item:

- `CHANGE_TOOLS = ("Edit", "MultiEdit", "Write", "NotebookEdit")` → `{"kind": "edit"|"create", "file", "path", "add", "del", "diff", "truncated", "ok"}`. `Write` de arquivo **novo** vem com `structuredPatch` vazio e `type: "create"` — o conteúdo inteiro conta como adição (`+linha` por linha).
- `Bash`/`PowerShell` → `{"kind": "cmd", "cmd" (≤400 chars), "desc" (≤80), "ok"}`; comando vazio não gera evento.
- Ferramentas de leitura (`Read`, `Grep`, `Glob`...) → `None`, sem evento.
- Tetos: `MAX_DIFF_LINES = 300` linhas de diff por alteração (`truncated: true` quando corta; a **contagem** `add`/`del` não é truncada) e `MAX_DIFF_COLS = 240` colunas por linha. `ok: false` quando o `tool_result` veio com `is_error`.

### 4.5 Fala em streaming dentro do `/ask`

Se `SPEAK_STREAM` está ligado (`HUB_SPEAK_STREAM != "0"`, default ligado) e o texto acumulado da resposta atinge `SPEAK_MIN` (env `HUB_SPEAK_MIN`, default **320** chars) com o árbitro de fala livre (`SPEAK_Q` vazia e `SPEAK_BUSY` desarmado), o turno instancia um `SpeakStream(sid, titulo, earcon_hz)`: a fala começa com a resposta ainda nascendo, enfileirada no **mesmo** árbitro das outras falas, e os eventos `speak_*` saem pelo NDJSON do próprio `/ask`. Texto emitido **antes** de um `tool_use` é narração de progresso, não resposta — é descartado do buffer de fala. O `done` sai com `spoken: true` e o front não chama `/speak`. Salvaguardas: watchdog interno do `SpeakStream` fecha o texto após 45s sem alimentação (turno morto no meio), e `close()` espera o `go` do árbitro por até 120s. Protocolo de arquivos e detalhes do Kokoro em `voz-tts.md`.

Se a resposta for curta, o árbitro estiver ocupado ou `SPEAK_STREAM` desligado, nada muda: `done` sai com `spoken: false` e o front chama `POST /speak` como sempre.

**`mudo`** (bool, default `false`) suprime a fala em streaming **daquele turno**, sem mexer em `SPEAK_STREAM`. Quem manda `true` é o cliente do celular (`mobile/`): a pessoa está longe do PC e lê a resposta na tela do aparelho — sem o campo, a casa declamaria sozinha. Campo ausente = comportamento de sempre. Ver `mobile.md` §6.

**`mudo` presente e `false`** é um pedido explícito de fala nesta máquina (o celular com "falar a resposta no computador" ligado). Como esse cliente não tem o fallback `/speak` do HUD (a rota não está na whitelist do `bridge`), se a fala em streaming não engatar (resposta < `SPEAK_MIN`, árbitro ocupado), o próprio `/ask` enfileira a fala clássica no fim do turno e emite `speak_queued`/`speak_start`/`speak_env`/`speak_done` depois do `done` — o espelho `/session_watch` os leva à aba CELULAR. O HUD do computador **não** manda o campo, então segue chamando `/speak` como sempre (sem fala dupla).

### 4.6 Espelho de sessão — `GET /session_watch/<sid>`

Toda linha NDJSON que `/ask` e `/speak` emitem passa por `_watched(sid, gen)`, que a copia para um buffer por sid (`WATCH`, teto `WATCH_KEEP = 400` linhas) **sem alterar** o que o chamador original recebe. `GET /session_watch/<sid>?rev=N` é long-poll (segura até 25 s): devolve `{rev, lines, line}` com **todas** as linhas publicadas depois de `N` (não só a última — um turno emite rajadas, e perder um `partial` corromperia o texto espelhado). `rev` negativo = sincronização: devolve só o `rev` atual, sem replay do passado (o HUD usa isso ao abrir, para não reencenar turnos velhos do buffer). `line` (a linha mais recente) é mantido por compatibilidade com consumidores antigos.

É assim que o HUD do computador reproduz, na aba **CELULAR** (somente leitura), o que a pessoa manda pelo celular: pergunta (evento `ask`), etapas, resposta nascendo, plano e alterações — ver `frontend.md` e `mobile.md` §6-bis. A rota é só leitura do espelho: não consome nada de `/ask`/`/speak` e não alcança o processo `claude`.

---

## 5. Esforço (`esforco` / `--effort`)

O eixo de esforço acompanha o de modelo em toda a superfície da API:

- Aceito em `/ask`, `/session_start` e `/session_reset` (campo `esforco`), repassado a `spawn_claude(sid, model, effort)`.
- Whitelist `ALLOWED_EFFORTS = {"low", "medium", "high", "xhigh", "max"}`. Valor inválido (ex.: `"ultra"`) ou ausente → flag omitida e `SESS[sid]["effort"] = ""` (default do CLI), **sem erro** — payload antigo sem o campo continua funcionando.
- Mudar **só** o esforço numa sessão viva (modelo igual) reinicia o processo daquele sid, igual à troca de modelo (a flag só existe no spawn).
- O fallback `claude -p` também inclui `--effort` quando o nível é válido.

Comportamento coberto por `tests/test_effort_server.py`.

---

## 6. `POST /speak` — resumo

Enfileira `{sid, reply, earcon_hz, announce: titulo, events}` no árbitro de fala (`SPEAK_Q`, fila única + 1 worker `speak_worker` — nunca duas sessões falam ao mesmo tempo) e devolve NDJSON: `speak_queued` (`{pos}`), `speak_start` (`{start_ms, ready, envelope, step_ms}` — quando o áudio de fato começa), `speak_env` (`{levels}` — níveis novos do envelope durante a fala) e `speak_done` (`{ok, ready, started, spoke_ms, chars, timeout}`). O protocolo de arquivos com o `speak_server.py` (Kokoro), os sentinelas `hub_say_*` no `%TEMP%` e os tempos de espera estão documentados em **`voz-tts.md`** — não repita aqui.

---

## 7. Relatórios — `/reports`

Pasta: `REPORTS_DIR = <vault>\_agentes\relatorios` (dentro do vault de propósito — o histórico vira acervo do Obsidian). Extensões de relatório: `REPORT_EXTS = (".html", ".htm")`.

- **`GET /reports`** — cria a pasta se não existir (1º uso) e lista **só** arquivos `REPORT_EXTS`, mais recente primeiro (ordenado por `mtime` desc, desempate pelo nome). Cada item: `{file, title, mtime, size}`. O `title` vem de `_report_title`: o `<title>` dos primeiros 4KB do arquivo (normalizado, ≤120 chars); sem `<title>`, o nome do arquivo sem o prefixo de timestamp `AAAA-MM-DD[_HHMMSS]_` e sem `_`/`-`. Nunca lança — um arquivo problemático não derruba a listagem.
- **`GET /reports/<fn>`** — serve **qualquer** arquivo da pasta (um relatório pode referenciar um CSV/imagem vizinho), mas só ela: `send_from_directory` barra path traversal (404).
- **`DELETE /reports/<fn>`** — só apaga arquivos com extensão de relatório (400 caso contrário) e só dentro de `REPORTS_DIR` (`safe_join`; fora da pasta ou inexistente → 404). Sucesso: `{"ok": true}`.

O fluxo completo (como o Claude gera o HTML, sondagem do front a cada 4s, visor automático) está em `relatorios.md`.

---

## 8. ForestOS — `/forestos/*`

O Hub só serve a página e faz **proxy** para a engine Node isolada (`forestos/cli.js`, escritor único do estado). `_run_forestos_cli(argv)` roda `node forestos/cli.js <argv...>` (`cwd = raiz do repo`, `timeout=30`), parseia a **última linha** do stdout como JSON e converte qualquer erro/saída não-JSON em `RuntimeError` — que as rotas devolvem como `{error}` 500, nunca stacktrace HTML.

- **`GET /forestos`** → `forestos.html`.
- **`GET /forestos/state`** → `cli.js dashboard`.
- **`POST /forestos/action`** `{cmd, args}` → whitelist de comandos de topo `FOREST_ALLOWED_CMDS = {"profile:read", "profile:write", "event:append", "event:read", "dashboard", "criar", "focus", "harvest", "habit", "mini", "reminder"}`; comando fora dela → `{error}` 400. `args` aceita lista, valor único (vira lista) ou ausente. Subcomandos viajam dentro de `args` e são validados pelo próprio `cli.js`.

Detalhes da engine, estado e página em `forestos.md`.

---

## 9. Constantes de configuração — tabela consolidada

| Constante | Valor | Papel |
|---|---|---|
| `PORT` | `8765` | porta da ponte (binding `127.0.0.1`) |
| `VAULT` | `HUB_VAULT` ou `~/Documents/Obsidian Vault` | acervo pessoal explícito, separado do projeto |
| `LOG` | `<VAULT>\_agentes\voice-hub.md` | transcript permanente de todos os turnos |
| `KPY` | `hub_runtime/voice/.venv/Scripts/python.exe` | Python local da voz |
| `SPEAK_SRV` | `hub_runtime/voice/speak_server.py` | servidor de fala local |
| `WHISPER_MODEL` | env `HUB_WHISPER`, default `"base"` | modelo do faster-whisper (`tiny` \| `base` \| `small` \| `medium`); `base` é 2× mais rápido que `small` nesta máquina |
| `STT_LOCK` | `threading.Lock()` | guarda nomeada do `WMODEL` — serializa o STT entre sessões |
| `STT_DIR` | `%TEMP%` | pasta do áudio recebido; o arquivo é por sid (`_stt_path`) |
| `AUTOQUIT` | env `HUB_AUTOQUIT`, default ligado (`!= "0"`) | a ponte se encerra quando não sobra HUD vivo |
| `HUD_TTL` | env `HUB_HUD_TTL`, default `90` (s) | silêncio de uma janela do HUD antes de considerá-la morta |
| `HUDS` / `HUD_LOCK` / `HUD_EVER` | — | janelas vivas por id, guarda do dicionário, e se algum HUD já se conectou |
| `SPEAK_STREAM` | env `HUB_SPEAK_STREAM`, default ligado (`!= "0"`) | fala em streaming no `/ask` |
| `SPEAK_MIN` | env `HUB_SPEAK_MIN`, default `320` | chars de resposta p/ acionar a fala em streaming |
| `ALLOWED_MODELS` | `{"fable", "opus", "sonnet", "haiku"}` | aliases aceitos p/ `--model` |
| `ALLOWED_EFFORTS` | `{"low", "medium", "high", "xhigh", "max"}` | níveis aceitos p/ `--effort` |
| `PERMISSION_FLAG` | `" --dangerously-skip-permissions"` | headless sem prompts de aprovação |
| `DEFAULT_SID` | `"default"` | sid quando o front não manda nenhum |
| `MAX_SESS` | `6` | teto de sessões (processos `claude`) vivas |
| `REAP_IDLE_SECS` | `21600` (6h) | idade p/ considerar uma sessão zumbi |
| `INACT_BOOT` / `INACT_IDLE` / `INACT_TOOL` | `90` / `300` / `1200` s | tetos do watchdog de ociosidade |
| `HB` / `THROTTLE` (locais do `/ask`) | `5` s / `0.3` s | cadência do heartbeat / agrupamento dos deltas |
| `CHANGE_TOOLS` | `("Edit", "MultiEdit", "Write", "NotebookEdit")` | ferramentas que geram `change` de arquivo |
| `MAX_DIFF_LINES` / `MAX_DIFF_COLS` | `300` / `240` | tetos do diff no evento `change` |
| `REPORTS_DIR` | `<VAULT>\_agentes\relatorios` | pasta dos relatórios visuais |
| `REPORT_EXTS` | `(".html", ".htm")` | extensões listadas/apagáveis em `/reports` |
| `FOREST_ALLOWED_CMDS` | ver seção 8 | whitelist do proxy ForestOS |
| timeout do fallback `claude -p` | `300` s | `Popen.communicate(timeout=300)`; timeout encerra a árvore |
| timeout do CLI ForestOS | `30` s | `subprocess.run(..., timeout=30)` |
| arquivos `hub_say_*` | `%TEMP%` | protocolo com o Kokoro — ver `voz-tts.md` |
