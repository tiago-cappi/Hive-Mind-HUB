# Verificação independente — backend HiveMind — C1/3

> **Status em 21/10/2026: CONCLUÍDA** — aprovada na verificação independente do C4 (20/10/2026, R01–R15). Este arquivo é registro histórico do processo e pode descrever intenções já superadas; a referência do código atual está em `docs/hivemind/README.md`. As ressalvas do C4 seguem como EQ-11 em `../2026-10-20_hivemind-escala-equipe/issues.md`.

19/10/2026. Verificador independente: GPT-6.1 Sol, esforço high, selecionado pela
coordenação. Não participou da implementação. Código e testes somente leitura;
nenhuma sessão ou turno real de IA iniciado nesta revisão. Contador permanece 1/3.

**Resultado global: REPROVADO.** Existem falhas reproduzidas de replanejamento e
recuperação, requisitos incompletos de correções/ciclos e R15 pendente. A suíte
verde não certifica a cadeia real. Ver `issues-c1.md` para correções exigidas.

## Integridade e execução

- Manifesto: `manifesto-c1.sha256`, SHA-256
  `cd9e56424c7533536c4675ac643c9619d31828096c81bc57b12c80b8fee15401`.
- Conferência inicial: **53/53 hashes correspondentes**. A conferência final deve
  ser registrada abaixo antes da devolução à coordenação. Este relatório e
  `issues-c1.md` são anexos novos e não alteram os registros congelados.
- Instruções lidas: AGENTS.md, docs/desenvolvimento.md, CLAUDE.md (arquitetura),
  docs/runtime.md, PRD/plano/Issues/verificação da tarefa. Revisados os módulos
  backend, launcher opt-in, pontos Flask/watchdog e conexão frontend real/demo.
- Uma execução completa controlada: `.venv/Scripts/python.exe -m pytest tests -q
  --basetemp=.test-tmp/hive-independent-c1/pytest
  --junitxml=.test-tmp/hive-independent-c1/full.xml`.
  TEMP/TMP próprios, `PYTHONDONTWRITEBYTECODE=1`, PowerShell elevado, `login:false`.
  **292 passed in 30.03s; exit 0**. Evidências: `full.log`, `full.xml`, `full.exit`
  sob `.test-tmp/hive-independent-c1/`. Isso resolve a inconclusão da tentativa
  anterior da suíte, sem alegar que aquela execução havia passado.
- O primeiro comando de leitura no sandbox ficou sem saída; leitura posterior e
  execução controlada usaram o caminho elevado já autorizado. Não se repetiu
  cegamente a suíte e não se alterou legado para o ambiente.
- Fixtures independentes adicionais: `probe.py`/`probes.json` (retry e presença),
  `replan_probe.py`/`replan.json` (sucesso de plano obsoleto),
  `stale_probe.py`/`stale.json` (origem divergente), `junction.json` (junction).
  Todos em `.test-tmp/hive-independent-c1/`; nenhum usa modelos ou dados pessoais.

## Resultado por critério

“Passou” abaixo se refere ao mecanismo verificável no candidato e às fixtures;
não transforma os smokes/missão real incompletos em aprovação operacional.

| ID | Veredito | Evidência e limite |
|---|---|---|
| R01 | Passou nos mecanismos; confirmação real pendente em R15 | Discovery tipado e sanitizado; gate bloqueia assinatura, quota e billing desconhecidos; overrides de API excluídos. Testes adapters e turnos passaram. Não foram lidos tokens, identidade ou históricos nesta revisão. Não se certifica acesso real a todo modelo listado. |
| R02 | Pendente | Seleção por papel, catálogo e esforço são separados do gate, sem fallback; testes invalidam seleção/controles. Entitlement individual continua `not_tested`; smoke Codex falhou e a missão real não alcançou worker/verificador. Não há prova de uso real de todas as seleções. |
| R03 | **Falhou** | Aprovações por hash, stale/revisão e Queen somente leitura estão cobertos. Porém plano B aprovado pode herdar sucesso do plano A, com outra descrição/arquivos, e ir à verificação sem executar B. `replan.json`: hashes diferentes, `worker_launches=[]`, estado `verifying`. HB-C1-01. |
| R04 | Passou nas fixtures; cadeia real pendente | Roster permanente/temporário persistido, identidade de processo Windows antes do turno, sessão por job e desativação de temporárias no completed; frontend exige `data.process` para “Executando”. A missão real só abriu Queen, portanto a comprovação operacional dos outros papéis permanece R15. |
| R05 | Passou | Reserva SQLite global conta worker/subagent/verifier, default 2; Queen separada; sobreposição/dependências e limite/pending testados. Agentes nativos desabilitados na configuração de sessão. Nenhuma inferência concorrente foi iniciada nesta revisão. |
| R06 | Passou nos mecanismos comprovados | Snapshot/worktree, exclusões, hashes, caminhos absolutos/escape e hardlinks cobertos pela suíte. Fixture adicional Windows junction recusou read e patch com `link_or_shared_file`, origem preservada. Checks têm perfil fechado, rede desabilitada, candidato read-only e scratch separado; evidência nativa prévia sem inferência está registrada no checkpoint P2. Não se amplia isso a qualquer interpretador/dependência não comprovado. |
| R07 | Passou nas fixtures; cadeia real pendente | Sessões worker/verificador distintas; lista editável vazia para verificador; checks read-only e scratch externo; manifesto conferido antes/depois do resultado; aceites incompletos/unverifiable não aprovam. Missão real independente ainda não chegou ao verificador (R15). |
| R08 | **Falhou parcialmente** | Persistência e teto de ciclos passam; falha no terceiro ciclo aguarda usuário, sem reset. A tela cria a missão com limite, mas não oferece ajuste do limite da missão existente apesar de a API suportá-lo. Correções também não passam pela Queen e não recebem o diagnóstico textual do verificador. HB-C1-03/04. |
| R09 | **Falhou parcialmente** | Aprovações exatas, stale, rollback parcial, corridas replace/add/remove, preservação da versão realmente deslocada e restrição ao mesmo volume passam. Entretanto não existe fluxo de reconciliação de origem stale: recover → novo plano aprovado → start mantém workspace/base antigos, sem rebase ou nova verificação sobre origem reconciliada. `stale.json` confirma base divergente. HB-C1-02. Não se exige relaxar isolamento nem aceitar hash+replace como CAS. |
| R10 | Passou nos mecanismos/fixtures | Presença nasce no módulo carregado em todo HUD e não para ao trocar página; minimizar só altera animação. Pausa fecha admissões, drena antes de interrupt e espera job terminar; store reiniciado entra recovery_required. Grace e duas janelas cobertos; reabertura de missão pausada não retoma. Sem teste destrutivo no Hub real 8765. |
| R11 | Passou nas fixtures | Lease impede segundo dono vivo; revisão/idempotência serializam comandos. Motivos last_viewer_closed e presence_uncertain distintos; ausência bloqueia `_can_dispatch()` antes da drenagem; reconexão não muda estado paused/pausing. `probes.json` adicional: missing_dispatch=false e closed_state=paused. |
| R12 | **Falhou parcialmente** | SQLite/event cursor/idempotência, proprietário único, orfandade e recovery conservador estão cobertos. A identidade da execução não é corretamente vinculada à geração do plano no cálculo de done/tentativa: sucesso antigo é reutilizado e falha antiga bloqueia nova aprovação no mesmo ciclo. HB-C1-01. Não houve repetição de efeito real nesta revisão. |
| R13 | Passou no escopo observado | Modo real usa jobs persistidos com processo, demo tem entrada explícita e estado separado; animação/render não despacham jobs. QA visual fornecida pela coordenação em fixture 18765 preserva PNG/2D/mostarda em 1440×900 e não teve pageerrors; não foi repetida. Campo de ciclos incompleto está em R08. |
| R14 | Passou | Hive sob HiveMind, testes/docs próprios, blueprint e hook de watchdog, opt-in separado sem vault/prompt pessoal. Sem alteração solicitada em providers/voz/mobile/CLAUDE; suíte de regressão completa passou. Bind local, MAX_SESS/MAX_TABS e SPEAK_Q preservados por inspeção/testes. |
| R15 | **Pendente — impede aprovação** | P0 local sem inferência e controles/versionamento já documentados; não se repetiram probes estáveis. Smoke Claude passou; smoke Codex histórico falhou sem categoria preservada. Missão Claude parou após Queen em awaiting_user/job_failed, sem worker/verificador/entrega. Causa histórica desconhecida. Os testes de contrato com mocks não substituem a missão real exigida. Nenhum reteste de IA foi realizado. |

## Síntese técnica dos achados

1. **Execuções de plano obsoleto contam para plano novo.** `advance()` e
   `Scheduler.reserve()` selecionam tarefas concluídas por `task_id` e `cycle`,
   ignorando o `plan_hash` que já está salvo no job. O bloqueio de tentativa
   anterior também ignora o plano. Há tanto avanço incorreto como recuperação
   bloqueada depois de nova aprovação humana.
2. **Stale é detectado com preservação, mas não reconciliado.** O journal faz
   sua função conservadora; depois de recuperar, o workspace antigo permanece
   associado e o start só cria snapshot quando nenhum workspace existe. Não há
   comando/broker de reconciliação separado capaz de produzir nova base.
3. **Queen não coordena as correções.** A passagem para correcting é automática,
   mas `advance()` lança diretamente os mesmos workers. Nunca lança Queen nessa
   fase. A evidência textual do verificador fica no resultado do job e não é
   incluída no `previous_verdict` enviado aos workers.
4. **Ajuste de ciclos incompleto na UI.** Existe endpoint auditado e proteção
   contra reduzir abaixo do ciclo corrente, mas nenhum controle da missão atual
   chama `cycle_limit`. O campo existente só é lido ao criar outra missão.

As correções devem manter os limites rígidos, aprovações, histórico e contador;
nenhum achado autoriza reabrir acesso ao vault, usar API/créditos extras,
substituir modelos ou repetir inferência histórica. A coordenação controla C2.

## Conferência final de integridade

Conferência final: **53/53 hashes correspondentes, zero divergências**; SHA-256 do
manifesto permanece `cd9e56424c7533536c4675ac643c9619d31828096c81bc57b12c80b8fee15401`.
Evidência persistida em `.test-tmp/hive-independent-c1/integrity-final.json`.
Somente anexos de revisão e fixtures/resultados próprios foram escritos.
