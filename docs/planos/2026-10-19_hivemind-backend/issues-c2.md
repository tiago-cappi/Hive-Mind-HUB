# Reprovações da verificação independente C2/3

> **Status em 21/10/2026: CONCLUÍDA** — aprovada na verificação independente do C4 (20/10/2026, R01–R15). Este arquivo é registro histórico do processo e pode descrever intenções já superadas; a referência do código atual está em `docs/hivemind/README.md`. As ressalvas do C4 seguem como EQ-11 em `../2026-10-20_hivemind-escala-equipe/issues.md`.

19/10/2026 · GPT-6.1 Sol high · somente leitura em código/testes.
Resultado global: **reprovado**. Suíte independente: 300 passed/39,85 s, exit 0.
C1 preservado; estas são pendências do **ciclo 2/3**, sem reiniciar o contador.
Implementador C3 a designar pela coordenação. Todos os achados abaixo: **abertos**.

HB-C1-03 (Queen+evidence) e HB-C1-04 (teto da missão na UI) foram corrigidos nas
fixtures. HB-C1-01 e HB-C1-02 permanecem parcialmente abertos pelos casos abaixo.

## HB-C2-01 — P2 — reaprovação idêntica após teto aceita e trava

- Origem: residual de HB-C1-01; R03/R08/R12.
- Locais: `HiveMind/backend/missions.py:136`,
  `HiveMind/backend/service.py:249` e `:272`.
- Reprodução: worker succeeded; begin_verification usando chave de produção
  `verify:<hash>:<cycle>`; reprovar no teto; elevar limite explicitamente;
  propose/approve/start do mesmo conteúdo do plano. Todas as ações são aceitas.
  advance duas vezes deixa running, zero jobs, verdict/verification_generation
  nulos e nenhuma mudança de revisão. Há reutilização de done e colisão com chave
  de verificação antiga; o Conflict é engolido.
- Evidências: `.test-tmp/hive-independent-c2/same_plan_probe.py`, `same-plan.json`.
  O limite 1 da fixture reproduz o mesmo ramo do teto 3 sem gastar ciclos reais.
- Esperado: reautorização aceita deve produzir transição válida e auditar nova
  tentativa/ciclo conforme a decisão explícita; se não for operação suportada,
  recusá-la antes de aceitar início, com caminho claro de recuperação. Nunca
  declarar running sem possibilidade de progresso, zerar ciclos ou reutilizar
  verificação obsoleta. Não exigir alteração artificial do texto para destravar.
- Correção exigida: distinguir identidade da tentativa/reautorização da mera
  igualdade do conteúdo, ou oferecer transição explícita equivalente que preserve
  o teto, histórico e efeitos confirmados. Cobrir plano idêntico após rejeição e
  falha terminal, além do caso de hash novo que já passa.

## HB-C2-02 — P2 — replay da reconciliação não é idempotente

- Origem: integração da correção HB-C1-02; R12.
- Local: `HiveMind/backend/service.py:415` e `:430` (antes de Store.mutate).
- Reprodução: após apply stale e recover, reconcile_source com key/revision;
  repetir exatamente. Clean: verifying na primeira chamada,
  reconciliation_not_available no replay. Conflito: awaiting_user na primeira,
  workspace_exists no replay. O resultado já persistido não é devolvido.
- Evidências: `.test-tmp/hive-independent-c2/probe.py`, `probes.json`.
- Esperado/correção: deduplicação e intenção durável antes da criação de snapshot;
  replay devolve resultado original, sem nova cópia. Interrupção entre intenção,
  snapshot e commit deve ter recuperação explícita, preservando candidato antigo
  e origem, sem repetir efeito ambíguo. Cobrir clean, conflito e interrupção.

## HB-C2-03 — P2 — reconciliação não participa da drenagem de fechamento

- Origem: integração da correção HB-C1-02; R10/R12.
- Locais: `HiveMind/backend/service.py:122`, `:144`, `:148`, `:415` e `:430`.
- Reprodução: bloquear snapshot de reconcile_source com barreira da fixture.
  Com operação em curso, active_missions é vazio e ready_to_exit/hub_exit_ready
  retornam true; missão continua awaiting_user. Liberar a barreira ainda cria
  candidato e muda a missão para verifying. Nenhum Hub real foi encerrado.
- Evidências: `.test-tmp/hive-independent-c2/lifecycle_probe.py`,
  `reconcile-lifecycle.json`.
- Impacto: watchdog pode sair durante escrita de cópia, antes do checkpoint de
  intenção. Não foi demonstrada perda de origem; ela permaneceu intacta.
- Esperado/correção: registrar/admitir reconciliação como operação ativa antes de
  escrever, bloquear novas admissões ao pausar/fechar, drenar a admitida e
  persistir resultado/checkpoint antes de sinalizar saída segura. Não matar
  escrita nem retomar/despachar trabalho automaticamente ao reconectar/reiniciar.
  Pode compartilhar a correção de intenção/idempotência com HB-C2-02.

## R15 — pendência necessária, sem novos turnos nesta revisão

Os retestes limitados C2 já terminaram: um dispatch Codex gpt-5.6-luna/high e uma
Queen Claude claude-fable-5/high falharam. Gates estavam aptos/autenticados.
Categoria Codex perdeu-se no **harness**, por whitelist incompatível; não se
atribui ausência de categoria ao fornecedor nem se inventa causa/quota/login.
Missão real ainda não alcançou worker/verificador/entrega. Consultados apenas os
metadados sanitizados dos diretórios explicitamente indicados pela coordenação.
Nenhuma descoberta, CLI, login, token, histórico ou modelo real foi iniciado/lido
para investigar esta revisão. R15 impede aprovação mesmo se C3 corrigir os
achados locais; qualquer validação real adicional depende da decisão da
coordenação dentro das autorizações e gates aplicáveis.
