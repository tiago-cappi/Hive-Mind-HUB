# Reprovações da verificação independente C1/3

> **Status em 21/10/2026: CONCLUÍDA** — aprovada na verificação independente do C4 (20/10/2026, R01–R15). Este arquivo é registro histórico do processo e pode descrever intenções já superadas; a referência do código atual está em `docs/hivemind/README.md`. As ressalvas do C4 seguem como EQ-11 em `../2026-10-20_hivemind-escala-equipe/issues.md`.

19/10/2026 · GPT-6.1 Sol high · código/testes somente leitura.
Complemento de `issues.md` congelado, sem reiniciar contador. Responsável pelas
correções: implementador que a coordenação designar no C2; status de todos os
achados abaixo: **aberto**. Relatório: `verificacao-c1.md`.

## HB-C1-01 — P1 — plano novo herda execuções obsoletas ou fica bloqueado

- Requisitos: R03, R12; afeta a recuperação de R02/R08.
- Locais: `HiveMind/backend/service.py:247` e `:255`,
  `HiveMind/backend/scheduler.py:67` e `:75`.
- Reprodução mínima: concluir task `one` no plano A; entrar awaiting_user;
  aprovar plano B no mesmo mission/cycle, alterando descrição e arquivos de
  `one`; iniciar e chamar advance. Observado: `verifying`, nenhum worker B,
  embora `old_job_plan_hash != current_plan_hash`. Se o primeiro job falhar,
  nova aprovação do mesmo task_id recebe `task_already_attempted`.
- Evidências: `.test-tmp/hive-independent-c1/replan_probe.py`, `replan.json`,
  `probe.py`, `probes.json`.
- Esperado: cada versão aprovada só usa resultados válidos para sua identidade
  de execução. Nova aprovação não deve reutilizar sucesso de tarefa modificada
  nem ficar irrecuperável devido a tentativa terminal de outro plano. Manter
  histórico/idempotência e teto persistido; recuperação exige intenção explícita.
- Correção exigida: vincular cálculo done, tentativas, chaves de verificação e
  retomadas à geração aprovada, invalidando/reconciliando resultados conforme o
  escopo. Cobrir alteração de plano com IDs iguais e recuperação após falha sem
  duplicar efeito ambíguo. Não zerar ciclo nem apagar histórico.

## HB-C1-02 — P1 — origem stale não tem caminho de reconciliação

- Requisito: R09.
- Locais: `HiveMind/backend/delivery.py` (`apply`, `recover`),
  `HiveMind/backend/service.py:362`/`:379`,
  `HiveMind/backend/routes.py` (ações disponíveis).
- Reprodução: preparar/aprovar pacote; alterar origem externamente; apply
  retorna `source_changed`; recover conclui sem mutações; aprovar novo plano e
  iniciar. Observado: `running`, mesmo workspace, base diferente da origem atual.
  Não há operação de reconciliação/rebase no backend ou UI. Nova tentativa de
  entrega continua baseada no estado antigo.
- Evidências: `.test-tmp/hive-independent-c1/stale_probe.py`, `stale.json`;
  testes de stale/rollback existentes passaram e comprovam preservação, não
  reconciliação.
- Esperado/correção: caminho explícito para reconciliar as versões preservadas
  em área separada, produzir base/candidato novos, invalidar autorizações antigas,
  reverificar e reapresentar pacote exato. Preservar versões concorrentes e
  aprovações; jamais atualizar base por hash sem reconciliação efetiva.

## HB-C1-03 — P2 — correções ignoram Queen e diagnóstico do verificador

- Requisitos: comportamento aprovado de Queen coordenando correções; R07/R08.
- Locais: `HiveMind/backend/service.py:216`, `:269`, `:567`;
  `HiveMind/backend/missions.py:216`.
- Reprodução/inspeção: verdict failed antes do teto muda diretamente para
  correcting; advance lança somente workers. Queen só é lançada no planejamento.
  `previous_verdict` contém candidate_hash, criteria, cycle, passed, verifier_id;
  a propriedade `evidence` do relatório não é encaminhada.
- Evidência: `.test-tmp/hive-independent-c1/probes.json` e fluxo de despacho.
- Esperado/correção: Queen deve receber o relatório independente e coordenar
  correções dentro do escopo aprovado, sem editar como worker e sem consumir
  slot de worker indevidamente. Mudança de escopo exige nova aprovação. Registrar
  coordenação/feedback duráveis e encaminhar diagnóstico útil aos responsáveis.

## HB-C1-04 — P2 — limite de ciclos não pode ser ajustado na missão pela UI

- Requisito: R08.
- Locais: `HiveMind/frontend/static/live-drawers.js:24` e `:67` em diante;
  API já suporta `action=cycle_limit`, `Missions.set_cycle_limit` já audita.
- Reprodução: abrir missão existente; campo “Máximo de ciclos” pertence à criação
  e só é usado por “Planejar com a Rainha”. Não existe ação da missão atual para
  alterar seu teto, inclusive quando para no teto awaiting_user.
- Evidência: inspeção completa de live-drawers/mission-state;
  `probes.json`: cycle_control_in_ui=false.
- Esperado/correção: controle explícito do teto da missão selecionada, com
  limite mínimo do ciclo corrente e persistência/evento já presentes no backend.
  Ajustar teto não deve retomar trabalho sozinho.

## HB-C1-P15 — pendência necessária de validação real

R15 permanece não verificável: smoke Codex falho e missão real sem worker,
verificador ou entrega. Não é autorização de repetir inferência. A causa do
evento histórico não foi determinada; não inferir quota/causa. A coordenação
deve decidir a liberação necessária para completar a evidência mínima após as
correções, preservando gates e limite de consumo. A suíte passou 292/292 e não
substitui esta pendência.
