# Hive Mind — checks com Python, escopo verificável e acabamentos

> **Status em 25/10/2026: CONCLUÍDA no ciclo 3/3** — duas conferências independentes (Opus), todas as ressalvas corrigidas; fase 2 completa pela interface. Referência do código: `docs/hivemind/`.

25/10/2026 · faixa média · pedido do usuário em 25/10/2026: "Eu escolho a opção (a) que
você sugeriu tanto do B4 quanto do B5. Pode corrigir todos os outros problemas
mencionados também, incluindo o F8 e F9 e todos os outros problemas menores."
Origem: `2026-10-24_hivemind-correcoes-teste.md` (pendências) e
`2026-10-24_hivemind-teste-navegador.md` (achados). F1, F3, F4 e F7 continuam na escala
(EQ-12), conforme decisão de 24/10/2026. Implementação e validação pela sessão principal;
conferência final por um Opus limpo somente leitura; depois, nova rodada da fase 2 até a
entrega aplicada na origem de teste.

## Diagnóstico que fundamenta as decisões

- B4: `python` instalado por usuário fica fora de `:minimal`; o perfil `hive-verify`
  nega a leitura e o processo sai com 127. Com a leitura da pasta liberada, o pytest roda
  mas trava ao terminar: o `cacheprovider` tenta criar `.pytest_cache` no candidato
  (somente leitura) e o `tempfile.mkdtemp` do Python no Windows repete `PermissionError`
  indefinidamente (pilha capturada com `faulthandler` em `.test-tmp/hive-diag-2410/`).
- B5: o verificador só tem `read` por caminho e `checks`; não enxerga quais arquivos
  mudaram. O backend já calcula isso para a entrega (`Delivery.prepare`: manifesto-base
  do snapshot × manifesto do candidato).

## Requisitos e critérios de aceite

| ID | Requisito | Critério verificável |
|---|---|---|
| D1 | B4 (a): leitura da pasta do interpretador | `RestrictedCheckRunner` resolve `argv[0]` pelo `PATH` do Hub e acrescenta ao perfil `hive-verify` leitura da pasta do executável (e, se houver `pyvenv.cfg` no pai, do ambiente virtual e da `home` dele). Nunca concede raiz de unidade, a pasta do usuário ou ancestrais dela, nem pasta que contenha ou esteja dentro do candidato ou do scratch. `_verified_profile` confere o perfil com exatamente essas entradas. Testes unitários das regras e do perfil. |
| D2 | B4: o pytest não trava | O ambiente do check recebe `PYTEST_ADDOPTS` com `cache_dir` dentro do scratch. Conferido de verdade (sem IA): `python -m pytest` no projeto de teste devolve `exit_code` 0 em 5 execuções seguidas. |
| D3 | B4: teto de tempo | `command/exec` com `timeoutMs` (padrão 600 s) em vez de `disableTimeout`; a espera do RPC é limitada ao mesmo teto mais margem. Check que estoura vira resultado com código de saída não zero (ou `restricted_check_failed`), nunca job eterno. Conferido de verdade com teto curto. |
| D4 | B5 (a): escopo verificável | O prompt do verificador traz `changed_files` (lista calculada pelo backend com a mesma regra do `Delivery.prepare`) e `files_outside_plan`, com a explicação de que é evidência do backend. Teste de serviço confere o conteúdo do prompt. |
| D5 | F8: limite de ciclos explicado | Em `awaiting_user` com `attempt_outcome.status == "cycle_limit"` do plano atual, a gaveta Missão explica que os N ciclos acabaram sem aprovação e o caminho: aumentar o máximo de ciclos e conversar com a Rainha. O veredito aparece legível (critério, situação traduzida, evidência) em vez de JSON cru. Teste de comportamento. |
| D6 | F9: aviso antigo some | "Última interrupção" só aparece se o `job_error` for posterior ao último `planning_requested`, `plan_proposed` ou `resumed`. Teste de comportamento. |
| D7 | Processo órfão no caminho normal (P3 da verificação de 25/10) | O RPC põe o processo lançado num Job Object do Windows com encerramento ao fechar; `close()` fecha o job e nenhum descendente sobrevive, mesmo quando o lançador sai sozinho. `taskkill` continua como reserva. Teste com processo real. |
| D8 | Marcador velho do Hub | `hub_runtime/stop_instance.ps1`: um PID vindo só do marcador `state/instance.json` que não pertence a esta instalação é ignorado com aviso (o marcador está velho), em vez de recusar a parada; o PID informado pela identidade viva continua recusado se não bater. Nada fora desta instalação é encerrado. |
| D9 | Documentação e registros | `docs/hivemind/{README,backend,adaptadores,frontend,testes,roadmap}.md`, `docs/operacao.md` se o reinício mudar, e este registro. |
| D10 | Regressão | Suíte completa verde e `node tests/hivemind_frontend_behavior.mjs` ok. |

## Ciclos

| Ciclo | Resultado |
|---|---|
| 1 | D1–D10 implementados pela sessão principal, com teste antes da correção quando automatizável. Validações: (D1/D2) `RestrictedCheckRunner` real, sem IA: `python -m pytest` no projeto de teste deu `exit_code` 0 em 5 de 5 execuções (~2 s cada), sem gravar nada no candidato; antes travava. Causa do travamento capturada com `faulthandler`: `_pytest/cacheprovider.py` → `tempfile.mkdtemp` em laço. (D3) check com `time.sleep(60)` e teto de 5 s voltou com 124 em 5,7 s, sem processo sobrando. (D7) teste vermelho antes do Job Object; checks e sessão Codex conferidos de novo com o job. (D8) cópia isolada do script com marcador apontando para um `ping`: aviso, `ping` vivo, marcador descartado. Suíte **410 passed**; behavior ok. **Fase 2 completa pela interface** (missão "Teste real despedida 4", Hub em `pythonw`): plano de primeira com check `python -m pytest` e critério de escopo; aprovar e iniciar pela gaveta; operária Claude (`read`, `read`, `patch`, `patch`, `checks`); verificador Codex (`checks` ok) com veredito `passed`/`passed` no ciclo 1, citando "o backend reporta apenas saudacao.py e test_saudacao.py alterados"; entrega preparada com essas duas mudanças; "Aprovar esta entrega" e "Incorporar entrega aprovada" pela gaveta; missão `completed`; origem `.test-tmp/hive-teste-real/` com `despedida()` e o teste, `pytest` 2 passed; nenhum processo da Hive sobrando; console sem erros. F8 conferido na tela com a missão 3 (aviso de limite e veredito legível). |
| 2 | Verificação independente do ciclo 1 (Opus 5.5 limpo, somente leitura): **APROVADO COM RESSALVAS**, sem P1. P2: a `home` de um `pyvenv.cfg` era concedida mesmo com o venv barrado (um venv dentro do candidato liberava, por exemplo, `Documents`), e `argv[0]` com caminho era aceito e resolvido contra o cwd do Hub. P3: barreira da pasta do usuário estreita (filhos diretos e raízes do `AppData` concedíveis); job não fechado se o fechamento falhasse; `_track` sem proteção; `PYTEST_ADDOPTS` com `--strict-config` sem registro; D2, D3 e D8 sem teste automatizado; manifesto do candidato calculado duas vezes e teste do B5 sem arquivo fora do plano. Correções: `program_read_roots` só aceita nome puro, segue o `pyvenv.cfg` só com o venv concedido e `home` absoluta com `python.exe`, e barra filhos diretos da pasta do usuário e as raízes do `AppData`; `close()` fecha o job em `finally`; `_kill_on_close_job` não levanta; ressalva do `--strict-config` documentada; testes novos: RPC falso do executor de checks (`timeoutMs`, espera, leituras extras no perfil, cache do pytest no scratch), parada com marcador velho (`tests/test_runtime_lifecycle.py`, cópia do script com porta livre) e arquivo fora do plano no teste do verificador; o manifesto é reaproveitado. Suíte **412 passed**; behavior ok; executor real sem IA (pytest 2 passed, teto 124 em 5,7 s) e sessão Codex conferidos de novo. |
| 3 | Conferência focada do ciclo 2 (Opus 5.5 limpo, somente leitura): **APROVADO COM RESSALVAS**, sem P1/P2; P2 anterior confirmado corrigido. P3: três ramos do P2 sem teste (detectado por mutação); o programa executado podia ser um homônimo na raiz do candidato (busca do `spawnSync`); barreira só por profundidade (OneDrive, outros perfis, `Public`, `AppData` como junção); `finally` do `close()` sem teste; frases imprecisas em `README.md` e data do B4 em `backend.md`. Correções: `tools.program_path` (nome puro numa pasta do `PATH`, nunca a pasta atual) usado na concessão e no comando executado, que passa a ser o caminho absoluto resolvido; barreira para `OneDrive*`, outros perfis e `Public`, com raízes do `AppData` resolvidas; limitação por posição documentada; testes reescritos cobrindo os três ramos (venv barrado, `home` relativa, `home` barrada), a pasta atual e o caminho executado; teste do `finally` e de `_kill_on_close_job` com processo sem handle; documentação corrigida. Suíte **413 passed**; behavior ok; executor real sem IA (pytest 2 passed, `cmd` ok, teto 124). **Tarefa concluída** (ciclo 3/3). |
