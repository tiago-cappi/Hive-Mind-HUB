# Verificação independente — backend HiveMind — C2/3

> **Status em 21/10/2026: CONCLUÍDA** — aprovada na verificação independente do C4 (20/10/2026, R01–R15). Este arquivo é registro histórico do processo e pode descrever intenções já superadas; a referência do código atual está em `docs/hivemind/README.md`. As ressalvas do C4 seguem como EQ-11 em `../2026-10-20_hivemind-escala-equipe/issues.md`.

19/10/2026 · GPT-6.1 Sol, esforço high, selecionado pela coordenação. Mesmo
verificador independente do C1, sem participação na implementação. Código e
testes somente leitura. Nenhum CLI, discovery ou turno real de IA executado
nesta revisão. C1 e seu veredito permanecem preservados; contador atual **2/3**.

**Resultado global: REPROVADO.** HB-C1-03 e HB-C1-04 estão corrigidos no escopo
verificado. HB-C1-01 e HB-C1-02 tiveram avanços funcionais confirmados, mas restam
falhas reproduzidas de reautorização e integração da reconciliação com
idempotência/lifecycle. R15 continua **pendente necessário**, independentemente
dessas reprovações. O próximo ciclo, se liberado pela coordenação, é C3 e último.

## Candidato e testes

- `manifesto-c2.sha256`: SHA-256
  `0e00394cfda58bd9ca2f2b2caef05a141a15a21975a533f389f1a9ea81aea040`.
- Conferência inicial direta: **56 entradas**, zero divergências. A contagem
  declarada de 60 foi corrigida pela contagem do arquivo, sem alterar o manifesto.
- Escopo de revisão: módulos alterados de missões/scheduler/service/delivery,
  rotas, novos controles do drawer e regressões associadas. Hashes iguais ao C1
  permitiram reutilizar a revisão dos módulos estáveis, isolamento nativo e QA
  visual válidos, sem novos probes de CLIs ou repetição da QA ampla.
- Suíte independente única: `.venv/Scripts/python.exe -m pytest tests -q
  --basetemp=.test-tmp/hive-independent-c2/pytest
  --junitxml=.test-tmp/hive-independent-c2/full.xml`, com TEMP/TMP próprios,
  `PYTHONDONTWRITEBYTECODE=1`, PowerShell elevado e `login:false`.
  **300 passed in 39.85s, exit 0.** `full.log`, `full.xml` e `full.exit` estão
  sob `.test-tmp/hive-independent-c2/`. As regressões novas existentes passaram
  nessa execução; não foi necessário repeti-las isoladamente.
- Fixtures independentes adicionais, sem modelos: `probe.py`/`probes.json`,
  `same_plan_probe.py`/`same-plan.json`,
  `lifecycle_probe.py`/`reconcile-lifecycle.json`, na mesma pasta temporária.
- Código/testes não foram editados. Foram escritos apenas anexos de revisão e
  fixtures/resultados próprios.

## Conferência dos quatro achados C1

| Achado | Resultado C2 | Evidência |
|---|---|---|
| HB-C1-01 | **Parcial; permanece aberto** | Plano com hash novo não herda sucesso/falha: workspace novo, anterior preservado, task `one` despachada com novo hash e ciclo preservado. Porém conteúdo idêntico reautorizado depois de rejeição no teto ainda reutiliza done/chave de verificação e trava. HB-C2-01. |
| HB-C1-02 | **Parcial; permanece aberto** | Reconciliação limpa cria nova base/candidato, conserva alterações externas independentes e força verifying; conflito preserva origem, candidato antigo e cópia fresca. Entretanto o novo comando não participa corretamente de replay, checkpoint e drenagem. HB-C2-02/03. |
| HB-C1-03 | **Corrigido nas fixtures** | Evidence agora faz parte do verdict durável. Em correcting, Queen é despachada antes dos workers; scheduler recusa worker com correction_not_ready. Queen usa lista editável vazia, persiste feedback; workers recebem correction/previous_verdict completos. Teste `test_queen_coordinates_failed_verdict_before_worker_and_persists_feedback` passou. |
| HB-C1-04 | **Corrigido no escopo verificado** | Drawer da missão selecionada envia cycle_limit e aplica mínimo do ciclo corrente. Backend mantém revisão/evento e não retoma ao ajustar. Testes de UI/limite passaram; inspeção confirma o vínculo com a missão atual. A reautorização posterior ao teto ainda sofre HB-C2-01. |

## Reproduções independentes

### HB-C2-01 — reaprovação do mesmo conteúdo fica sem progresso

Fixture: worker concluído, verificação reprovada no teto (limite 1 para reproduzir
o mesmo comportamento do teto 3), missão awaiting_user. Usuário eleva limite a 3;
propõe, aprova e inicia novamente o mesmo conteúdo do plano. Essas transições
são aceitas pelo backend.

Observado após dois advance: `state=running`, `cycle=1`, `limit=3`, nenhum job
lançado, `verification_generation=null`, `verdict=null`, nenhuma mudança de
revisão. `done` reutiliza tarefa anterior porque plan_hash é igual; a chave
`verify:<plan_hash>:1` já existe com outra revisão. O Conflict é capturado e
ignorado pelo advance, mantendo o estado sem caminho produtivo. Plano com hash
novo funciona; isso não resolve a reaprovação idêntica que a API aceita.

Evidência: `.test-tmp/hive-independent-c2/same-plan.json` e script correspondente.
Locais: `missions.py:136`, `service.py:249` e `service.py:272`.

### HB-C2-02 — replay de reconcile_source não é idempotente

Após source_changed e recover, executar reconcile_source com uma chave/revisão
e repetir a mesma requisição. Reconciliação limpa: primeira chamada retorna
verifying; replay retorna `reconciliation_not_available`. Reconciliação com
conflito: primeira retorna awaiting_user e versões preservadas; replay retorna
`workspace_exists`. O replay não chega ao resultado já salvo no Store, pois
estado/snapshot são tratados antes da deduplicação.

Evidência: `.test-tmp/hive-independent-c2/probes.json`, campos clean.replay e
conflict.replay. Local: `service.py:415–456`. Esperado: devolver resultado
consistente da operação original sem nova cópia ou efeito.

### HB-C2-03 — fechamento considera reconciliação em curso como drenada

Bloquear snapshot da reconciliação com barreira de fixture; nenhuma IA ou Hub
real é encerrado. Enquanto reconcile_source já está em execução e ainda vai
copiar/escrever, consultar os mesmos hooks usados para fechamento.

Observado: missão ainda awaiting_user, `active_missions=[]`,
`ready_to_exit()=true` e `hub_exit_ready()=true`. Liberar a barreira continua a
operação, escreve o candidato e muda para verifying. Assim, no fechamento real
o watchdog pode encerrar a ponte durante a escrita, antes de um checkpoint de
intenção. O snapshot determinístico parcialmente criado também prejudica o
replay. A origem não foi modificada pela fixture e não se demonstrou perda de
dados de origem; a falha é de admissão/checkpoint/drain exigidos.

Evidência: `.test-tmp/hive-independent-c2/reconcile-lifecycle.json` e
`lifecycle_probe.py`. Locais: `service.py:122`, `:144`, `:148`, `:415` e `:430`.

## Matriz de aceitação C2

“Passou nas fixtures” não equivale à validação operacional real que falta em R15.

| ID | Veredito | Evidência/limitação |
|---|---|---|
| R01 | Passou nos mecanismos; uso real limitado por R15 | Gates/ambientes/adapters inalterados em relação à revisão C1; regressões passaram. Metadados C2 já existentes mostram gate apto antes do dispatch. Sem leitura de tokens, identidade, transcrições ou discovery novo nesta revisão. |
| R02 | **Pendente** | Seleção explícita/sem fallback e validações passam. Tentativas reais limitadas C2 falharam; não certificam entitlement/compatibilidade de execução. Codex gpt-5.6-luna/high e Queen Claude claude-fable-5/high foram seleções dos fixtures, não fallback. |
| R03 | **Falhou parcialmente** | Aprovação exata e hash novo corrigem o caso principal C1. Reaprovar o mesmo conteúdo é aceito, mas não cria execução produtiva após rejeição/teto. HB-C2-01. |
| R04 | Passou nas fixtures; operacional pendente | Histórico/roster/processo real por job preservados; suíte passou. Tentativa real C2 voltou a alcançar somente Queen; worker/verificador continuam sem prova real integrada. |
| R05 | Passou nos mecanismos/fixtures | Contagem global, dependências/arquivos e sessões isoladas preservadas. Queen agora coordena em slot separado antes dos workers; broker não lhe permite patch. Sem paralelismo nativo habilitado. |
| R06 | Passou nos mecanismos comprovados | Workspaces/tools/adapters estáveis por hash; suíte e provas C1 continuam válidas, incluindo junction recusada e checks restritos. Reconciliação escreve apenas cópia própria, conserva origem e versões; não se amplia suporte a dependências/intérpretes não comprovados. |
| R07 | Passou nas fixtures; operacional pendente | Verificador continua sem edição e em sessão separada; evidence é persistida e recebida pela Queen. Manifesto/hash e aceites completos continuam exigidos. Sem verificador real na missão limitada. |
| R08 | **Falhou parcialmente** | Controle da missão, limites/auditoria e teto persistido passam; não há retomada automática ao elevar teto. Reaprovação posterior de plano idêntico pode travar sem correção/verificação. HB-C2-01. |
| R09 | **Parcial; reconciliação funcional comprovada** | Novo snapshot/base/candidato e conflito preservador funcionam; verdict/delivery antigos invalidados; reverificação exigida. Aplicação Windows/journal/race/rollback estáveis e testados. A integração do comando com idempotência e fechamento falha em R10/R12 (HB-C2-02/03). |
| R10 | **Falhou parcialmente** | Fluxos existentes de job/broker continuam drenando, sem auto resume. Reconciliação não é rastreada como operação ativa: fechamento pode encerrar durante cópia admitida. HB-C2-03. |
| R11 | Passou nas fixtures estáveis | Presença entre HUDs, lease, motivos de fechamento/incerteza e bloqueio de novo despacho preservados. Não se repetiu QA de troca de página/minimização nem se mexeu no Hub 8765. |
| R12 | **Falhou parcialmente** | Persistência/histórico/unknown e geração com hash novo melhoraram e passaram. Replay de reconcile_source retorna erros distintos e não participa do checkpoint antes da escrita; reaprovação idêntica colide com chave antiga. HB-C2-01/02/03. |
| R13 | Passou no escopo observado | Visual/PNG/demo/navegação estáveis por hash; QA anterior reutilizada. Novos controles são locais ao drawer e vinculados ao backend, sem progresso fabricado. Não foi realizada nova QA visual ampla. |
| R14 | Passou | Três encaixes externos inalterados por hash, sem alteração de CLAUDE/providers/voz/mobile; 300 testes de regressão passam. Mesmos bind/limites pessoais/SPEAK_Q e opt-in preservados. |
| R15 | **Pendente necessário; impede aprovação** | Sem inferência nesta revisão. Tentativas C2 já encerradas: Codex gate apto, um dispatch e terminal turn_failed; Claude gate apto, uma Queen despachada, terminal awaiting_user, sem worker/verificador/entrega. Não existe missão ponta a ponta aprovada. |

## Evidência real C2 já existente e limite do diagnóstico

Foram lidos somente audit.jsonl e terminal.json dos caminhos explicitamente
fornecidos: `.test-tmp/hivemind-c2-codex-smoke/` e
`.test-tmp/hivemind-c2-claude-mission/`. O diagnóstico reportado pela coordenação
é que **o harness perdeu a categoria oficial Codex por uma segunda whitelist
incompatível**; não há evidência para afirmar que o fornecedor deixou de enviá-la.
O evento histórico não foi recuperado. O contrato sem IA em
`.test-tmp/hivemind-c2-diagnostic-contract.py` cobre categorias locais, mas não
reconstitui a causa do turno histórico nem aprova R15.

Não se conclui quota esgotada, necessidade de login, falha de autenticação ou
causa de fornecedor. Os gates informados estavam aptos/autenticados; autenticação
não é garantia de sucesso de um turno. Não foi iniciado login, discovery,
CLI/modelo, leitura de histórico/token ou nova inferência. Os registros congelados
anteriores aos retestes não substituem este anexo de evidências C2.

## Integridade final

Conferência final: **56/56 hashes correspondentes, zero divergências**. SHA-256
do manifesto preservado:
`0e00394cfda58bd9ca2f2b2caef05a141a15a21975a533f389f1a9ea81aea040`.
Evidência: `.test-tmp/hive-independent-c2/integrity-final.json`. Somente os novos
anexos de revisão e fixtures/resultados próprios foram escritos.
