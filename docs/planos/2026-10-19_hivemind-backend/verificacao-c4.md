# Verificação independente — backend HiveMind — C4 (continuação autorizada, escopo R15)

> **Status em 21/10/2026: CONCLUÍDA** — aprovada na verificação independente do C4 (20/10/2026, R01–R15). Este arquivo é registro histórico do processo e pode descrever intenções já superadas; a referência do código atual está em `docs/hivemind/README.md`. As ressalvas do C4 seguem como EQ-11 em `../2026-10-20_hivemind-escala-equipe/issues.md`.

20/10/2026. Verificador: subagente Opus 5.5 novo, contexto limpo, sem participação
na implementação. Código, testes, docs existentes e manifesto ficaram somente
leitura. Sem turno de IA, login, leitura de tokens/credenciais/históricos e sem
tocar no Hub da porta 8765. Comandos reais usados: só `--version`, `--help` e
`discover()` dos adaptadores (sem prompt).

## Veredito global: **APROVADO** (com ressalvas não bloqueantes)

Os critérios R01–R15 estão atendidos no candidato `manifesto-c4.sha256`. A suíte
completa passou e a evidência real do R15 em `.test-tmp/hivemind-c4-r15/` atende
o PRD: há um smoke curto por CLI e uma missão mínima ponta a ponta, com equipe
mista e entrega aplicada na origem.

Ficam riscos residuais P2 e ressalvas P3 (§ Achados). Eles não impedem a
aceitação, mas mudam a postura de segurança e devem ser conhecidos pelo usuário.
`issues-c4.md` não foi criado, porque não houve reprovação.

## Candidato e integridade

- `manifesto-c4.sha256` (SHA-256 `9b5e5085…4af1b`, 64 entradas): **64/64 OK** no
  início e no fim (`.test-tmp/hive-independent-c4/integrity-final.txt`).
- Diferenças em relação ao C3:
  - Alterados: `adapters/{codex,claude}.py`, `service.py`, `README.md`,
    `docs/runtime.md`, `docs/planos/roadmap-hivemind.md`, `issues.md` e
    `tests/test_hivemind_{adapters,adapter_turns,service}.py`.
  - Novos: `manifesto-c3.sha256` e `verificacao-c3.md`.
  - Os demais arquivos do backend, o frontend e `server.py` estão inalterados.
- **`tests/fixtures/hivemind/fake_cli.py` está fora de todos os manifestos
  (C1–C4)**, mas foi alterado no C4, às 19:23: ganhou `--help` do Claude,
  `:read-only` e o modelo `fable`. Hash conferido nesta verificação:
  `372776f8…6af4aaf`. Ver P3-d.
- A versão C3 dos arquivos alterados foi recuperada de uma geração de runtime
  do diagnóstico C3-r15, cujos hashes coincidem com o manifesto C3. Com ela, o
  diff confere com o escopo declarado (HB-C4-01 a 05). Não há faxina fora do
  escopo.

## Suíte completa (uma execução)

```
PYTHONDONTWRITEBYTECODE=1 ./.venv/Scripts/python.exe -m pytest tests -q -p no:cacheprovider \
  --basetemp=.test-tmp/hive-independent-c4/pytest
346 passed in 48.30s   (exit 0)
```

São 337 testes do C3 mais 9 novos. Log: `.test-tmp/hive-independent-c4/full.log`.

## 1. Segurança/enforcement — `:read-only` no lugar de `hivemind-isolated`

**Escrita (R06): mantida e mais estrita.**

- O perfil antigo estendia `:workspace`. Uma ferramenta nativa podia escrever
  no workspace da missão, e só `:root`/tmp ficavam negados.
- `:read-only` nega qualquer escrita nativa.
- Toda escrita continua indo pelo broker (`patch`), com escopo e hash.
- Os checks seguem num perfil próprio, `hive-verify`, que nega `:root`, nega
  tmp e corta a rede (`tools.py`, inalterado).
- A sessão real Codex 0.160.0 confirmou `activePermissionProfile.id ==
  ":read-only"` (smoke e missão).

**Leitura: ficou mais ampla (risco residual P2-a).** O perfil antigo negava
`:root` e tmp. O `:read-only` permite ler o disco inteiro por ferramenta nativa,
se alguma existir: segredos de CLI, vault, outros projetos. A barreira primária
continua sendo a configuração:

- `shell_tool`, apps, plugins, multiagente e hooks desligados;
- `web_search` desabilitado;
- MCP desligado e conferido no roster;
- `environments: []`.

O Codex está fixado exatamente em `0.160.0`, então a superfície de ferramentas
não muda sem nova validação. O diagnóstico C3-r15 indica que todo perfil
customizado falhou no turno. Os resultados por variante não foram persistidos e
não puderam ser reconferidos, mas são consistentes com os turnos reais C4.

**A detecção não acontece antes do efeito.**

- `item/started` é uma notificação. O cliente não tem veto: quando
  `native_tool_unexpected` é levantado, o comando ou a leitura já começou no
  app-server.
- Depois disso, `__exit__` → `close()` fecha o stdin, espera até 5 s e então
  mata só o processo pai (não a árvore).
- Nenhum `turn/interrupt` é enviado.
- O efeito fica limitado pelo sandbox somente leitura. A allowlist é uma trava
  de integridade do resultado, não uma prevenção.

**Itens que escapam da allowlist (P3-a)**, reproduzidos em
`probes.json` → `codex_items`:

- `functionCallOutput` é aceito com **qualquer** `name` (por exemplo `shell`
  ou `read_file`). Pelo schema 0.160.0, esse é um item genérico de saída de
  função.
- Itens com outro `threadId` são ignorados. Um `commandExecution` de
  sub-thread é aceito. O multiagente está desligado, e um sub-agente emitiria
  `collabAgentToolCall` na thread principal, que é recusado.
- Recusados corretamente: `imageView`, `commandExecution`,
  `collabAgentToolCall`, `hookPrompt` e item sem `type`.

**Remoção de `profile_name_conflict`: segura.** Sem perfil customizado, o
conflito de nome deixou de existir. Não restaram referências no código, nos
testes ou nos docs. A validação acessória de `config.permissions` como objeto
saiu junto, e nada mais a usa. Ressalva menor: a checagem confere só o `id` do
perfil ativo, não `extends is None`. Se a configuração do usuário pudesse
redefinir um perfil embutido, isso passaria. Não verificável offline (P3-a).

## 2. Claude — versão, flags, evidência e catálogo

**Discovery real** (`discover.json`):

- 2.1.305, `compatible=True`;
- catálogo com só `opus`, `sonnet` e `haiku`;
- `fable` e `claude-fable-5` → `selection_model_unlisted`;
- `extra_usage=False`, `policy_clear=True`;
- as 14 flags aparecem declaradas como opção no `--help` real.

**Parsing de versão:**

- `fullmatch` estrito; `-beta` e `v…` → `version_unrecognized`.
- `2.1.0289` vira `(2,1,289)` (inócuo).
- `2.1.288` é recusado e `2.2.0` e `10.0.0` são aceitos (P2-b).

**Evidência atrelada à versão** (probe `claude_version_binding`):

| Caso | Resultado |
|---|---|
| Sessão não entrada (`version=None`) | `enforcement_evidence_unverified` |
| Mesma versão | Apta |
| Atualização no meio da sessão (305 → 306) | Bloqueada |
| Reversão | Apta de novo |

`_validate` e `evaluate` comparam `discovery.version` com `self.version`, que
vem do `discover()` feito no início da sessão.

**Cache e regex das flags:**

- Uma falha de `--help` não é cacheada: o retry funciona.
- O cache por versão mascara uma mudança de help com a mesma string de versão.
  Isso é por desenho e tem impacto prático nulo.
- A regex não confunde `--tools` com `--allowed-tools`.
- A regex aceita uma flag citada só na descrição de outra (P3-b).

**Testes:**

- Nenhum teste depende de "fixture-claude".
- O teste novo zera `_flag_proofs` por iteração.
- Os testes com `fake_cli` usam a versão 2.1.289 com help completo.
- Falta teste automatizado da vinculação de versão (P3-c); a probe cobre esse
  caso.

**P2-b — risco residual da política `>=`.** Uma versão nova só prova que as
flags existem, não que `--tools ""` mantém a semântica. A detecção de
`tool_use` também é posterior à execução pelo CLI. Os limites práticos são:

- `--print` sem permissões extras nega ferramentas que pedem permissão;
- o cwd é o workspace/cópia;
- a política foi decidida dentro da autorização do usuário.

Sugestão: teto de major (`< 3`) ou exigir que a flag apareça declarada como
opção.

## 3. Saída estruturada e sanitização

- `_QUEEN_OUTPUT` e `_verdict_output` são fechados: todo objeto tem
  `additionalProperties: false` e `required` igual a `properties` (teste novo e
  probe). O veredito usa os ids de aceite como propriedades, com enum
  `passed|failed|unverifiable`.
- O Codex envia `outputSchema` só quando há esquema (teste). O Claude recebe o
  esquema no texto, dentro do envelope `{"final": …}`.
- Por probe, a Rainha recebe `_QUEEN_OUTPUT` e o verificador recebe o esquema
  exato do plano. A operária recebe `None`.

Normalização de nulos e mapeamento de erros (probe `queen`/`verifier`):

| Resposta | Resultado |
|---|---|
| `clarification:null` + plano | `awaiting_plan_approval` |
| Pergunta + `plan:null` | `clarifying` |
| Ambos nulos | `planning_result_invalid` |
| Ambos presentes | `planning_result_invalid` |
| `ValueError` de `validate_plan` | `planning_result_invalid` (antes era `job_failed`) |
| Texto que não é JSON | `planning_result_invalid` |
| Veredito que não é JSON | `verdict_invalid` |
| Veredito `null` | `verdict_invalid` |
| Veredito sem um critério | `verdict_invalid` |

`_failure_reason` preserva `verdict_invalid` e `job_result_invalid`. Nenhum
texto do fornecedor aparece em eventos, nem nas probes nem nos 27 eventos da
mission4.

## 4. Evidência real R15 (`.test-tmp/hivemind-c4-r15/`)

**Smokes:**

- `smoke-claude`: 2.1.305, `sonnet/low`, gate `[]`, `OK` em 18,2 s.
- `smoke-codex`: 0.160.0, `gpt-5.6-luna/low`, gate `[]`, `OK` em 9,2 s.
- Ressalva: os dois rodaram na geração `eba0f3e5…`, anterior ao candidato. Ela
  difere só na passagem de `output_schema` (com `None`, o comportamento é
  idêntico). Perfil, versão, catálogo e allowlist são os mesmos.

**Missão `mission4`:**

- A geração `f9baac02…` é igual ao candidato em 19 de 20 arquivos; só o
  `README.md` difere.
- SQLite, lido somente leitura:
  - missão `completed`, ciclo 1/1;
  - 3 jobs `succeeded`: Rainha Codex `gpt-5.6-luna/medium`, operária Claude
    `sonnet/low` e verificador Codex;
  - cada job teve `provider_session_started` próprio e pid registrado;
  - operária: `read`, `patch` e `read` pelo broker;
  - verificador: `read`, com veredito `{exact-note-content: passed}`;
  - `delivery_prepared`, `approved`, `applying` e `completed`;
  - a origem e o workspace terminaram com `greeting=hello hive\n`.

**Harness C4 — sem contorno de gate:**

- `smoke.py` usa a geração, o adaptador e a sessão reais.
- `mission4.py` só envolve `turn()` com uma checagem extra de gate e um teto
  de 8 turnos antes de `super().turn`.
- Os planning-diag imprimem no terminal a saída do modelo e as falhas locais.
  É diagnóstico fora do produto, sem bypass.
- As aprovações de plano e pacote foram feitas pelo harness, pela API real com
  hash e sob a autorização do usuário. O caminho humano pela UI não foi
  exercitado aqui; ele é coberto pelos testes de R09/R13.

**Satisfaz R15:**

- gate sem inferência antes de habilitar;
- um smoke por CLI;
- uma missão mínima ponta a ponta;
- caminho de cobrança `ordinary_available`: Codex `has_credits=false` e Claude
  `extra_usage=false`;
- repetições só após falha com mudança de código ou de harness.

**Observações P3-e (registro):**

- `audit.jsonl` rotula `provider: "claude"` em todas as linhas, inclusive
  Rainha e verificador Codex. O SQLite tem os providers corretos.
- `issues.md` diz "Codex 6" turnos. Os artefatos somam 7 requisições Codex:
  smoke 1, mission 1, planning-diag 1, mission2 1, planning-diag2 1 e
  mission4 2. Claude são 2 sessões, com várias idas ao broker.
- A tabela C4 de `issues.md` ainda marca HB-C4-01 a 03 "em implementação".

## Achados

| ID | Sev. | Local | Achado / correção sugerida |
|---|---|---|---|
| P2-a | Residual, não bloqueante | `codex.py:95` | Leitura nativa ampla sob `:read-only` e detecção posterior ao efeito. Mitigado por ferramentas nativas desligadas e pin exato 0.160.0. Reavaliar perfil restrito quando o Codex aceitar perfil customizado em turno. |
| P2-b | Residual, não bloqueante | `claude.py:32-48,157` | Versões futuras (inclusive major) habilitadas só com prova de flags no help. Sugestão: teto de major ou regex de opção declarada. |
| P3-a | Menor | `codex.py:118-119,390-393` | `functionCallOutput` aceito com qualquer `name`; itens de outra thread ignorados; perfil checado só por `id`. Sugestão: restringir `functionCallOutput.name` a `read/patch/checks`, recusar itens de thread desconhecida e exigir `extends is None`. |
| P3-b | Menor | `claude.py:46` | A regex aceita uma flag mencionada só em prosa. |
| P3-c | Menor | `tests/` | Faltam regressões para: evidência Claude × versão, normalização de nulos, `verdict_invalid` e `functionCallOutput`. As probes desta verificação cobrem esses casos. |
| P3-d | Menor (processo) | manifestos | `tests/fixtures/hivemind/fake_cli.py`, alterado no C4, nunca entrou em manifesto. Incluí-lo no congelamento final; hash atual `372776f8…6af4aaf`. |
| P3-e | Menor (registro) | `issues.md`, harness | Status da tabela C4, contagem de turnos Codex e rótulo de provider no audit. |

## Matriz de aceitação C4

| ID | Veredito | Evidência |
|---|---|---|
| R01 | Passou | Discovery real sanitizada: instalado, autenticado, compatível e apto, sem identidade. Fable fora do catálogo; o 429 de créditos do C2 deixa de ser alcançável. O gate exige `extra_usage=false`/`has_credits=false`. |
| R02 | Passou | Seleção explícita, sem fallback: `allowProviderModelFallback=false` e checagem `model == self.model`. Modelo fora do catálogo dá erro explícito (`selection_model_unlisted`). Execução real comprovada para `sonnet/low` e `gpt-5.6-luna/low,medium`; demais modelos seguem `entitlement: not_tested` (catálogo ≠ direito). |
| R03 | Passou | Inalterado desde C3. A mission4 parou em `awaiting_plan_approval` antes de qualquer escrita. |
| R04 | Passou | Cada job real teve processo/sessão própria (pid e `provider_session_started`). |
| R05 | Passou | Scheduler inalterado; suíte verde. |
| R06 | Passou (P2-a) | Escrita nativa negada em todo lugar; broker é a única via de escrita; checks em `hive-verify`; origem só mudou pela entrega aprovada. |
| R07 | Passou | O verificador real Codex rodou em sessão separada, só com leitura pelo broker e veredito estruturado por critério. |
| R08 | Passou | Inalterado desde C3; ciclo 1/1 na mission4, sem 4º ciclo automático. |
| R09 | Passou | Entrega real: aprovação ligada a `candidate_hash`/`delivery_hash`, journal e aplicação concluída. |
| R10 | Passou (P3-b do C3) | Inalterado desde C3. |
| R11 | Passou | Inalterado desde C3. |
| R12 | Passou (P3-a do C3) | Inalterado; eventos/cursor na mission4 em sequência 1–27. |
| R13 | Passou | Frontend inalterado por hash desde C3. |
| R14 | Passou | `server.py`, rotas e encaixes inalterados; suíte de regressão do Hub verde. A geração Hive roda via `hub_runtime.assistant --hivemind`. |
| R15 | **Passou** | Gate sem inferência; smokes Claude e Codex `passed`; mission4 ponta a ponta `completed`, com 3 papéis reais e origem alterada; sem créditos extras; harness sem contorno (§4). |

## Arquivos escritos por este verificador

- `docs/planos/2026-10-19_hivemind-backend/verificacao-c4.md` (este relatório).
- `.test-tmp/hive-independent-c4/`: `m4.txt`, `full.log`, `full.exit`,
  `pytest/`, `discover_probe.py`, `discover.json`, `discover.err`,
  `inspect_m4.py`, `c4_probes.py`, `probes.json`, `probes/` e
  `integrity-final.txt`.
