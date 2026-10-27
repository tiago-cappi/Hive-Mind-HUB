# Hive Mind — correções do teste no navegador

> **Status em 25/10/2026: CONCLUÍDA.** B4, B5, F8 e F9 resolvidos em `2026-10-25_hivemind-entrega-real.md` (opção (a) escolhida pelo usuário).
> Referência do código: `docs/hivemind/`. Teste que originou esta tarefa:
> `2026-10-24_hivemind-teste-navegador.md`.

24–25/10/2026 · faixa média · pedido do usuário em 24/10/2026: "Corrija B1 e B2,
repita a fase 2 com a missão real e corrija os achados 2, 5 e 6 da interface da hive
mind e deixe o 1, 3, 4 e 7 para escala." Implementação e validação pela sessão
principal (Opus 5.5), com testes de regressão escritos antes da correção e conferidos
vermelhos no código antigo. B3 apareceu ao repetir a fase 2 e entrou aqui porque
impedia a missão de chegar à entrega.

## Correções

| ID | Problema | Causa raiz | Correção | Teste |
|---|---|---|---|---|
| B1 | Com o Hub em `pythonw.exe`, nenhuma sessão de IA abria (`protocol_timeout`) | `launcher.main` chamava o CLI com `subprocess.run` sem stdio; sem console, o CLI não herdava os pipes | `HiveMind/backend/adapters/launcher.py`: `stdin=0, stdout=1`, stderr descartado, `CREATE_NO_WINDOW` | `test_launcher_hands_pipes_to_cli_when_started_without_console` (lança `pythonw.exe` real; vermelho no código antigo) |
| B2 | Depois de uma falha, `close()` travava para sempre e deixava o CLI órfão | Matava só o lançador; o CLI órfão segurava o pipe e `stdout.close()` esperava a thread leitora bloqueada | `adapters/base.py`: `_kill_tree` (`taskkill /T /F` e `kill`), `join` da leitora com prazo e stdout fechado só com a leitora encerrada; `adapters/claude.py` usa o mesmo `_start_reader` | `test_close_kills_orphaned_cli_after_failed_start` (neto real segurando o pipe; vermelho no código antigo) |
| B3 | Rainha (`planning_result_invalid`, intermitente) e verificador (`verdict_invalid`) recusados | O Codex manda uma mensagem de comentário (`phase: commentary`) antes de usar ferramentas; o adaptador juntava todas as mensagens e o JSON final deixava de ser JSON ("Extra data") | `adapters/codex.py:turn` devolve só as mensagens `final_answer` (todas, se nenhuma vier marcada) | `test_codex_turn_returns_only_final_answer_after_commentary` |
| F2 | Foco ou digitação numa gaveta fechada rolava a colmeia | Gavetas fechadas continuavam focáveis; `overflow:hidden` ainda permite rolagem programática | `live-drawers.js`: gaveta fechada `inert`; `hive.css`: `.hm-live-workspace{overflow:clip}` | `hivemind_frontend_behavior.mjs` (gavetas `inert`) |
| F5 | Rainha "Disponível" enquanto planejava | O estado só considerava job com `data.process` (sessão já aberta) | `mission-state.js:snapshot`: job `running` sem processo mostra "Iniciando — Abrindo a sessão do provedor." | `hivemind_frontend_behavior.mjs` |
| F6 | Faixa do topo com estado cru (`awaiting_user`) | `hive.js:renderHud` usava `mission.state` | `hive.js` importa `stateLabel` de `messages.js` | `test_live_hud_shows_translated_mission_state` |

F1, F3, F4 e F7 foram para a tarefa de escala como EQ-12
(`2026-10-20_hivemind-escala-equipe/issues.md`).

Diagnóstico reproduzível (fora do produto, sem contornar gate) em
`.test-tmp/hive-diag-2410/`: `probe_enter.py`/`probe_pythonw.py`/`probe_noconsole.py`
(B1), `probe_plan.py` e `probe_verify.py` (B3, com a resposta bruta em
`verify-log.json`), `probe_checks.py` e `probe_checks_grant.py` (B4).

## Validação

- Suíte completa: **407 passed** (eram 403; +2 em `test_hivemind_adapters.py`, +1 em
  `test_hivemind_adapter_turns.py`, +1 em `test_hivemind_frontend.py`);
  `node tests/hivemind_frontend_behavior.mjs` ok.
- Sondas reais sem console: sessão Codex aberta em 4,7 s com o lançador em `pythonw` e
  em 5,3 s com o processo inteiro em `pythonw` sem console (antes: trava).
- Fase 2 repetida no Chrome com o Hub em `pythonw.exe` (detalhe em
  `2026-10-24_hivemind-teste-navegador.md`, "Fase 2 — repetição"): F2, F5 e F6 conferidos
  na tela; Rainha Codex, operária Claude e verificador Codex abriram sessão, usaram o
  broker e responderam no formato; três ciclos de correção reais. A entrega não chegou à
  aprovação por B4/B5. Novos achados de interface F8 e F9 no registro do teste.

## Verificação independente (25/10/2026)

Opus 5.5 limpo e somente leitura (pedido de qualidade do usuário, além do mínimo da faixa
média). Veredito: **APROVADO COM RESSALVAS**, sem P1/P2. Diff do backend conferido contra
a cópia de runtime de 21/10; testes falham sem cada correção. P3 corrigidos pela sessão
principal: `base.py` e `claude.py` voltaram a LF (a gravação por script tinha trocado para
CRLF; os JS/CSS editados em `HiveMind/frontend/static` também voltaram a LF, como os
vizinhos); fallback do B3 exclui `commentary` mesmo sem `final_answer` (teste ampliado);
behavior confere que as abas puxadoras não ficam `inert`; contagem e datas em
`testes.md`/`backend.md` e uso de `messages.js` em `frontend.md`. Registrado sem ação:
se o lançador sair sozinho e deixar um processo segurando o pipe, `close()` não trava mais,
mas também não mata esse processo. `overflow:clip` só é verificável no navegador
(conferido na fase 2). Suíte final **407 passed**; behavior ok.

## Pendências (decididas em 25/10/2026: opção (a) para B4 e B5; F8 e F9 corrigidos em `2026-10-25_hivemind-entrega-real.md`)

| ID | Problema | Opções |
|---|---|---|
| B4 | `checks` nunca roda Python instalado por usuário: o perfil `hive-verify` nega leitura fora de `:minimal`, da raiz do candidato e do scratch; `python` sai com 127 sem saída (`cmd` e `node` rodam). Liberando a leitura da pasta do Python, `python --version` e `pytest` rodam, mas uma execução repetida travou (> 500 s) e outra saiu com 143; o `pyreadline3` falha ao fechar sem console. O C4 nunca exercitou `checks` (a `mission4` não tinha checks). | (a) liberar só leitura da pasta do interpretador resolvido no `PATH` e investigar o travamento (mexe no perfil de segurança); (b) checks fora do sandbox MXC, em processo próprio com ambiente mínimo (perde isolamento de escrita); (c) manter como está e orientar a Rainha a não propor checks com Python. |
| F8, F9 | Achados de interface novos (registro do teste) | Corrigir agora ou mandar para a escala (EQ-12). |
| B5 | O verificador não tem como confirmar "nenhum outro arquivo foi alterado" (só `read` por caminho e `checks`) e marca `unverifiable`; a missão gasta todos os ciclos de correção. A escrita já é restrita aos arquivos da tarefa pelo broker (`write_not_approved`). | (a) entregar ao verificador a lista de arquivos alterados em relação à origem, calculada pelo backend; (b) instruir a Rainha a não criar critérios que o verificador não consegue observar; (c) ambos. |
