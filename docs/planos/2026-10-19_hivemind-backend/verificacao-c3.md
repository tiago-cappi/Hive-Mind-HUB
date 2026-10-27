# Verificação independente — backend HiveMind — C3/3 (último ciclo)

> **Status em 21/10/2026: CONCLUÍDA** — aprovada na verificação independente do C4 (20/10/2026, R01–R15). Este arquivo é registro histórico do processo e pode descrever intenções já superadas; a referência do código atual está em `docs/hivemind/README.md`. As ressalvas do C4 seguem como EQ-11 em `../2026-10-20_hivemind-escala-equipe/issues.md`.

20/10/2026. Verificador: subagente Opus 5.5 novo, com contexto limpo e sem
participação na implementação. A substituição do GPT-6.1 Sol foi autorizada
pelo usuário em `issues.md` §C3. Código, testes, docs existentes e manifesto
ficaram somente leitura.

Nesta revisão não houve execução de CLI real (`claude`/`codex`), login,
discovery, turno de IA nem leitura de tokens, credenciais ou históricos. O Hub
da porta 8765 não foi tocado. C1 e C2 ficam preservados e o contador está em
**3/3**.

## Veredito global: **PENDENTE DE VERIFICAÇÃO**

O candidato C3 não está aprovado. A única pendência que impede a aprovação é o
**R15** (validação real com IA). Ele continua pendente necessário, porque não
existe evidência real nova: nenhuma missão ponta a ponta com operária,
verificador e entrega foi concluída com os CLIs reais.

**Correções locais do C3, sem considerar o R15: aprovadas.** HB-C2-01,
HB-C2-02 e HB-C2-03 estão corrigidos nas reproduções independentes, e o escopo
adicional de frontend foi atendido. Ficam três ressalvas P3 que não bloqueiam a
aprovação (§ Ressalvas). Nenhum critério R01–R14 falhou. Por isso
`issues-c3.md` não foi criado.

Como este é o ciclo 3/3, §3.F manda **parar**. Não haverá quarto ciclo
automático. Fechar o R15 depende de decisão explícita do usuário, dentro das
autorizações e gates do PRD.

## Candidato e integridade

- `manifesto-c3.sha256` tem SHA-256
  `a8e651580e9971d08ae567b9f76cdd62e9ea5e9b781ec45b7b66ff8e2d6538da` e
  62 entradas.
- A conferência inicial deu **62/62 OK**. A final, depois de todos os testes e
  probes, também deu **62/62 OK** e zero divergências. Evidência:
  `.test-tmp/hive-independent-c3/integrity-final.txt`.
- Diferenças em relação ao C2 (56 → 62 entradas):
  - Alterados:
    - `HiveMind/__init__.py`;
    - `HiveMind/backend/`: `README.md`, `adapters/claude.py`, `missions.py`,
      **`scheduler.py`**, `service.py` e `store.py`;
    - `HiveMind/frontend/static/`: `demo-data.js`, `drawers.js`,
      `live-drawers.js` e `mission-state.js`;
    - testes `test_hivemind_{adapter_turns,api,delivery,frontend,scheduler,service}.py`.
  - Novos: `tests/hivemind_browser_qa.mjs`,
    `tests/hivemind_frontend_behavior.mjs`, `docs/planos/roadmap-hivemind.md` e
    os registros C2.
  - Sem alteração: `server.py`, `delivery.py`, `lifecycle.py`, `routes.py`,
    `manager.py`, `workspaces.py`, `tools.py`, os adapters Codex/base e o
    protótipo.
  - `scheduler.py` mudou, embora não estivesse na lista da coordenação. A
    mudança acrescenta o filtro `plan_attempt` às tarefas concluídas e
    tentadas, é coerente com HB-C3-03 e foi revisada.

## Suíte completa (uma execução)

```
PYTHONDONTWRITEBYTECODE=1 ./.venv/Scripts/python.exe -m pytest tests -q -p no:cacheprovider \
  --basetemp=.test-tmp/hive-independent-c3/pytest
337 passed in 40.64s   (exit 0)
```

- Log: `.test-tmp/hive-independent-c3/full.log` e `full.exit`.
- O harness Node `tests/hivemind_frontend_behavior.mjs` rodou dentro da suíte,
  porque o Node está instalado.
- `tests/hivemind_browser_qa.mjs` não roda no pytest: ele depende da biblioteca
  `playwright`, que não está instalada localmente. Não foi executado.

## Revisão de código

### Backend

- **Reconciliação** (`service.py:443-511`, `missions.py:332-419` e
  `store.py:110-115`, `262-285`):
  - Fluxo: a deduplicação vem antes de qualquer verificação de estado.
    `begin_reconciliation` grava a intenção durável (`pending`) dentro de
    `_reconcile_lock`, antes do snapshot.
  - Resultado: os dois desfechos (limpo e conflito) ficam gravados sob a chave
    do usuário. Uma falha posterior a `begin` leva a `recovery_required`, com
    workspace e origem preservados. No boot, uma operação `pending` vira
    `recovery_required`.
  - O `_reconciling` antigo foi removido, sem resíduos.
- **Fechamento** (`service.py:139-187`): `active_missions` conta
  `awaiting_user` com operação `pending`. `request_pause_all` marca `_closing`
  sob o mesmo lock da admissão. `ready_to_exit` e `hub_exit_ready` só devolvem
  `True` depois que a operação admitida termina e a missão resultante é
  pausada.
- **Ciclos**:
  - `require_reauthorization_cycle` (`missions.py:17-20`) é aplicado em
    `approve_plan`, no `prepare` de `start_mission` (antes de `preparing` e do
    snapshot) e em `start`.
  - `propose` registra `pending_reauthorization` a partir de `attempt_outcome`
    (teto) e `start` consome um ciclo.
  - `plan_attempt` separa `done`, a chave de verificação, a chave da Queen, o
    workspace e as tentativas do scheduler.
- **Sanitização** (`service.py:37-68` e `adapters/claude.py:16-27`): só passam
  códigos que o próprio `turn_error_code` regenera. Subtypes Claude fora da
  whitelist, status fora de 100–599, dígitos não ASCII, sufixos extras e
  qualquer texto livre caem em `job_failed`/`unknown`. 28 casos-limite foram
  verificados (ver `probes.json` → `codes`).
- **§4.1**: não há código morto evidente nem faxina fora do escopo. Os imports
  novos são usados. `README.md` do backend descreve as regras C3.

### Frontend

- `mission-state.js:33-36`:
  - O cursor `?after=` pagina até 10 × 200 eventos por refresh e continua do
    `eventSeq` no refresh seguinte.
  - O histórico é limitado a 500 e reiniciado ao trocar de missão. Uma resposta
    de outra missão é descartada.
- `live-drawers.js:9-25`, `72-75` e `110`:
  - `validateTeam` mostra uma mensagem clara (modelo/esforço vazio, id
    inválido ou repetido, papéis obrigatórios) e desabilita “Salvar”. A regex
    coincide com `safe_name` do backend.
  - `chatQueen` usa a Rainha da equipe atual.
  - `queen_configuration_changed` tem uma mensagem amigável.
  - Um aviso no chat aparece quando a Rainha mudou.
- Textos obsoletos:
  - `demo-data.js:1` agora diz “separada do backend real; não controla missões
    reais”.
  - `HiveMind/__init__.py` foi corrigido.
  - Não restou “backend pendente/ausente” em `HiveMind/`.
  - A lacuna em docs está na ressalva P3-c.
- Beacon: `mission-state.js:13` envia `sendBeacon(Blob application/json)` no
  `pagehide` e é aceito pela rota real (ver reprodução abaixo).

## Reproduções independentes (fixtures próprias, sem IA)

Script: `.test-tmp/hive-independent-c3/c3_probes.py`; resultados em
`probes.json`. Usa os builders dos testes (`plan`, `running`) e um builder
próprio de missão stale com id parametrizável, para cobrir duas missões.

### HB-C2-01 — reautorização após o teto: **corrigido**

- **Mesmo plano depois de reprovação no teto (limite 1):**
  - `approve_plan` sem elevar o teto é recusado com `cycle_limit_reached`.
  - Elevando o teto para 3, `approve` e `start` funcionam: `cycle 1→2`,
    `plan_attempt 2` e `attempt_history=[{status: cycle_limit}]`.
  - O primeiro `advance` despacha a tarefa `one` com a chave
    `(m, hash, 2, 2, one)`. O sucesso da tentativa 1 não é reaproveitado.
  - Depois do novo trabalho, a missão vai a `verifying` com
    `verification_generation` `{plan_attempt: 2, cycle: 2}`, e o verificador é
    lançado. Não houve travamento: o caso C2 ficava em `running` sem jobs.
- **Mesmo plano depois de falha terminal de job** (pausa `job_failed` →
  `awaiting_user`, fora do teto): `propose`, `approve` e `start_mission`
  funcionam, com `cycle` mantido em 1 e `plan_attempt 2`. A tarefa é despachada
  de novo e a falha anterior não bloqueia.
- **Teto reduzido depois da aprovação e antes do start:** `start_mission`
  devolve `cycle_limit_reached`. O estado fica `ready`, sem workspace, sem
  nenhum snapshot e sem `recovery_required`.
- **Teto reduzido durante o snapshot** (corrida forçada chamando `Missions`
  direto): `stale_revision` leva a `recovery_required`. Pela API isso é
  inalcançável, porque `Lifecycle.controlled` serializa todos os comandos sob
  `_control_lock`. O comportamento é conservador e preexistente ao C3; foi
  registrado só como observação.

### HB-C2-02 — replay da reconciliação: **corrigido**

- **Limpo:** a primeira chamada vai a `verifying` (status `completed`). O
  replay com a mesma chave e a mesma revisão devolve um resultado idêntico, sem
  cópia nova e com a revisão inalterada.
- **Conflito:** a primeira vai a `awaiting_user` (status `conflict`). O replay
  é idêntico e também não faz cópia.
- **Chave de outro comando:** `idempotency_key_reused`.
- **Mesma chave com revisão diferente:** devolve o resultado salvo (ressalva
  P3-a).
- **Interrupção durante a cópia** (`copyfile` falha):
  - A missão vai a `recovery_required`. A origem fica com `old`, o candidato
    antigo com `candidate` e o workspace vinculado é preservado.
  - Não há missão ativa e nenhum diretório novo restou.
  - O replay de k1 devolve `recovery_required`. Uma chave nova antes da
    recuperação devolve `reconciliation_not_available`.
  - Depois de `recover_delivery` (`awaiting_user`), k2 vai a `verifying` e o
    replay de k2 é idêntico. A origem segue intacta.

### HB-C2-03 — reconciliação na drenagem de fechamento: **corrigido**

Montagem: duas missões stale. O snapshot de `ma` fica preso numa barreira.

- Durante a operação:
  - `active_missions=["ma"]`, `ready_to_exit()=False`,
    `hub_exit_ready()=False` e `_closing=True`.
  - A admissão de `mb` é recusada com `closing`, antes de qualquer escrita.
    `mb` segue na mesma revisão.
- Liberada a barreira, `ma` termina em `verifying`. Em seguida
  `ready_to_exit()=True` e as duas missões ficam `paused`. Nada é retomado.

Boot com operação pendente e cópia parcial simulada:

- O boot leva a missão a `recovery_required` (status `recovery_required`), sem
  missões ativas.
- O replay de `op-1` devolve `recovery_required`.
- `recover_delivery` leva a `awaiting_user` com marcador, e `op-2` leva a
  `verifying`.
- A origem fica intacta e a cópia parcial é mantida, sem limpeza automática.

### Escopo adicional de frontend: **atendido**

- O harness Node da suíte cobre:
  - cursor além de 200 (450 → 3 páginas; 451; 900 → janela de 500 a partir
    do seq 401; troca de missão reinicia);
  - todas as mensagens de `validateTeam`;
  - `chatQueen` com Rainha atual ou de fallback.
- Beacon reverificado de forma independente
  (`.test-tmp/hive-independent-c3/beacon_probe.py` e `beacon.json`):
  - Montagem: Chrome headless real, num servidor temporário em
    `127.0.0.1:18799` com o blueprint real `/hive-api` e um serviço falso. A
    página dispara o mesmo `sendBeacon(Blob application/json)`.
  - O navegador enviou `Origin` same-origin, `Sec-Fetch-Site: same-origin`,
    `Sec-Fetch-Mode: cors` e `Content-Type: application/json`.
  - A rota respondeu 200 e `bye("beaconhud")` foi chamado.
  - Limitação: o disparo foi no carregamento, não no `pagehide`. O formato da
    requisição é o mesmo.
- Textos “backend pendente/ausente” foram removidos da UI e do pacote.

## Ressalvas P3 (não bloqueantes, registradas para o usuário)

- **P3-a — Replay com revisão diferente devolve sucesso.**
  - Local: `service.py:450-454`.
  - O replay de `reconcile_source` não compara a revisão enviada. Os demais
    comandos (`Store.mutate`) recusam a mesma chave com outra revisão
    (`idempotency_key_reused`).
  - Não há efeito repetido nem nova cópia: o resultado original é devolvido.
    Há só uma inconsistência de contrato.
  - Correção sugerida: guardar a revisão de entrada na intenção e recusar
    divergência.
- **P3-b — Janela residual da barreira de fechamento.**
  - Local: `service.py:173-176` e `:224`.
  - (1) Quando não há missões ativas, `hub_exit_ready()` devolve `True` sem
    marcar `_closing`. A probe `early_exit_window` mostra uma reconciliação
    admitida depois do sinal de saída segura (`admitted:verifying`).
    `ready_to_exit()` marca corretamente e recusa com `closing`.
  - (2) `heartbeat()` zera `_closing` sem lock. Durante a drenagem de `ma`, um
    heartbeat permitiu admitir a reconciliação de `mb` (probe `lifecycle`).
    Nenhuma pausa foi cancelada, e `hub_exit_ready` continua `False` enquanto
    há HUD vivo. Mesmo assim, não há atomicidade entre a última checagem de
    ativas e a saída.
  - Alcance prático baixo: a UI Hive vive na mesma página do HUD do Hub, e o
    watchdog só pergunta depois de 90 s sem pulsos.
  - Consequência, se ocorrer: `os._exit` durante a cópia, e o boot seguinte
    marca `recovery_required` com origem e candidato antigo intactos
    (conservador).
  - Correção sugerida: marcar `_closing` também no caminho `True` de
    `hub_exit_ready` e só limpá-la sob `_reconcile_lock`.
- **P3-c — Documentação desatualizada.**
  - Local: `docs/frontend.md:21` e `:29`.
  - O texto ainda diz “A interface deixa visível o aviso de backend pendente” e
    “O backend de agentes Hive continua fora de escopo”. Isso contradiz a UI
    C3 e a regra 8 do CLAUDE.md.
  - Não afeta nenhum critério R01–R15. Deve ser corrigido no encerramento.

Outras observações:

- No estado `recovery_required` causado por uma reconciliação interrompida, o
  drawer mostra “Reconciliar origem” ao lado de “Recuperar entrega”, porque o
  marcador permanece. Clicar devolve `reconciliation_not_available` (código
  cru). É cosmético.
- No `boot_probe`, a tentativa de `resume` falhou com
  `runtime_generation_changed`, porque a fixture não tinha `generation`. A
  sonda não é informativa sobre resume. Isso não afeta o resultado: o resume
  exige `paused` e foi validado pela suíte.

## Matriz de aceitação C3

| ID | Veredito | Evidência / limitação |
|---|---|---|
| R01 | Passou (mecanismos) | Gates/adapters de discovery inalterados por hash desde C2; suíte 337/337 verde. Uso real depende de R15. Sem leitura de tokens/identidade. |
| R02 | **Pendente** | Seleção explícita sem fallback passa nas fixtures; entitlement/execução real dos modelos não comprovados (tentativas C2 falharam; sem evidência nova). |
| R03 | Passou | Reaprovação idêntica ou nova após teto: recusada sem ciclo, aceita com teto elevado, gera tentativa nova e progride (probe `reauthorization`). Aprovação obsoleta continua rejeitada (suíte). |
| R04 | Passou nas fixtures; parte operacional em R15 | Roster/histórico/processo por job inalterados e testados; nenhuma operária real executou ainda. |
| R05 | Passou | Slots/dependências/arquivos; `plan_attempt` agora também separa tentativas no scheduler (`scheduler.py:74-90`); suíte verde. |
| R06 | Passou | Workspaces/tools inalterados; reconciliação escreve só em cópia própria; origem intacta em todas as probes (limpa, conflito, interrupção, boot). |
| R07 | Passou nas fixtures; parte operacional em R15 | Verificador em sessão separada sem edição; nova geração de verificação após reautorização e após reconciliação. Sem verificador real. |
| R08 | Passou | Reautorização no teto consome ciclo novo (decisão do usuário), exige teto elevado, recusa antes do snapshot; ciclo nunca zera; `attempt_history` auditado; sem 4º ciclo automático. |
| R09 | Passou | Reconciliação limpa/conflito/interrupção/recuperação comprovadas; delivery antiga invalidada; reverificação obrigatória. |
| R10 | Passou (ressalva P3-b) | Reconciliação admitida conta como ativa; fechamento drena e pausa; sem retomada automática; sem kill durante escrita no caminho comprovado. |
| R11 | Passou | Lease/presença inalterados; beacon reverificado em Chrome real; reabertura não cancela pausas (missões ficam `paused`). |
| R12 | Passou (ressalva P3-a) | Intenção durável antes da cópia; replay devolve resultado salvo sem efeito; interrupção e boot → `recovery_required`; sem efeito repetido. |
| R13 | Passou no escopo observado | Mudanças de frontend restritas a drawer/estado/textos; CSS/PNG/demo visual inalterados por hash; sem progresso fabricado. Sem nova QA visual ampla. |
| R14 | Passou | `server.py`, rotas, `manager.py` e encaixes externos inalterados por hash; suíte de regressão do Hub (voz/mobile/Claude) verde. |
| R15 | **Pendente necessário — impede aprovação** | Nenhuma inferência nova nesta revisão nem evidência real nova no candidato. Continua sem missão real ponta a ponta (worker + verificador + entrega). |

## Arquivos escritos por este verificador

- `docs/planos/2026-10-19_hivemind-backend/verificacao-c3.md` (este relatório).
- `.test-tmp/hive-independent-c3/`: `m3.txt`, `full.log`, `full.exit`,
  `pytest/`, `c3_probes.py`, `probes.json`, `probes/`, `beacon_probe.py`,
  `beacon.json`, `chrome-profile/` e `integrity-final.txt`.

## Anexo da sessão principal — validação real R15 (20/10/2026)

Autorizada pelo usuário em 20/10/2026 ("pode rodar a validação real"). Esta
seção foi escrita pela sessão principal, não pelo verificador, e não altera
o veredito acima. Os scripts e resultados estão em `.test-tmp/hivemind-c3-r15/`.

1. **Descoberta, sem inferência** (`discover.py`, `discover.json`):
   - **Codex 0.160.0:** apto em todos os modelos e esforços do catálogo, com
     `enforcement_evidence_unverified` resolvido apenas na sessão.
   - **Claude:** **bloqueado** em todos os modelos por `version_unverified`. O
     CLI instalado agora é **2.1.305** (atualização automática); a prova P0 e o
     pin do adaptador são de **2.1.289**. O bloqueio está correto; nenhum turno
     Claude foi feito.
2. **Teste curto Codex pelo adaptador Hive** (`codex_smoke.py`,
   `gpt-5.6-luna`/`low`, 1 turno): falhou com `turn_failed:other`. A categoria
   oficial agora é preservada; no C2 ela se perdia.
3. **Diagnóstico** (`codex_diag.py`, 1 turno): a mensagem do Codex, mostrada
   só no terminal, foi `failed to load workspace requirements`.
4. **Controle fora do Hive** (`codex exec` puro, mesma conta e modelo, 1 turno):
   respondeu `OK`. A conta, a franquia e o modelo funcionam. A falha está na
   configuração de sessão que `HiveMind/backend/adapters/codex.py` envia
   (perfil de permissões isolado, overrides de config) no Codex 0.160.0.
5. **Missão mínima ponta a ponta:** não executada. Os dois gates ou sessões
   falham antes da Rainha, e o plano proíbe inferir além disso.

**R15 continua pendente necessário.** Destravar exige mudar código de adaptador
com nova prova de enforcement (P0):

- Codex: sessão que carregue os requisitos do workspace sem afrouxar o
  isolamento.
- Claude: prova e pin da versão 2.1.305.

Isso depende de decisão do usuário, porque o ciclo 3/3 já foi usado.
