# Hive Mind — teste no navegador real (Chrome do usuário)

> **Status em 25/10/2026: CONCLUÍDO — fase 1 aprovada; fase 2 completa pela interface, do
> pedido à entrega aplicada na origem de teste (missão "Teste real despedida 4").**
> Registro de teste, não de implementação. Correções: `2026-10-24_hivemind-correcoes-teste.md`.
> Referência do código: `docs/hivemind/`.

## Fase 1 — sem IA: aprovada

| Item | Resultado |
|---|---|
| Aba Hive Mind, isolamento do Hub, mostrador "HIVE MIND · MISSÕES COM CLAUDE E CODEX" | ok |
| Navegação Hive → Claude Code → Hive (estado e equipe preservados) | ok |
| Consultar modelos (Claude 2.1.306 opus/sonnet/haiku; Codex 0.160.0) | ok, mas ~10–20 s sem indicação de carregamento (F1) |
| Validação da equipe (modelo ausente, id repetido, id inválido) e salvar equipe | ok |
| Demonstração: missão completa, aprovação, relatório, cenário com falha, colmeia vazia | ok |
| Console sem erros | ok |

## Fase 2 — missão real: bloqueada

Equipe: Rainha Codex gpt-5.6-luna/medium, operária Claude sonnet/low, verificador Codex
gpt-5.6-luna/medium. Missão "Teste real despedida" criada às 20:46; a Rainha ficou em
`planning` por 20 min sem evento `provider_session_started`.

**B1 — sessões de IA não abrem quando o Hub roda em `pythonw.exe` (bloqueante).**
`adapters/launcher.py:adapters` monta `session_command` com `sys.executable`, que no Hub é
`pythonw.exe`. O lançador `--hivemind` roda sem console e chama `subprocess.run` sem
passar os handles de entrada/saída; o CLI filho (node/codex) não recebe os pipes do
backend, o `initialize` expira (`protocol_timeout`). Reproduzido fora do Hub em
`.test-tmp/hive-diag-2410/probe_pythonw.py`; com `python.exe` a mesma abertura passa
em 3,8 s (`probe_enter.py`). A validação real do C4 usou harness com `python.exe`, por
isso não pegou. Afeta Codex e, pelo mesmo caminho, Claude.

**B2 — `DiscoveryRpc.close()` trava para sempre após falha (bloqueante).** Depois do
`protocol_timeout`, `close()` mata só o processo intermediário, deixando o node/codex
órfão com o pipe aberto; `self.process.stdout.close()` fica preso no lock da thread
`_read`, bloqueada lendo esse pipe. Pilha em `.test-tmp/hive-diag-2410/stack-pythonw.txt`.
Efeito: job eterno em `running`, missão eterna em `planning`, processos órfãos. Ao
encerrar os órfãos manualmente, o job falhou com `protocol_timeout` e a gaveta mostrou a
mensagem nova corretamente ("O trabalho parou. Motivo: O provedor demorou demais para
responder. (protocol_timeout) …").

## Achados de interface (não bloqueantes)

| ID | Achado |
|---|---|
| F1 | "Consultar modelos" leva ~10–20 s sem indicação de carregamento. |
| F2 | No modo real, gavetas fechadas continuam focáveis; foco/digitação rola a área da colmeia (até 300 px), a colmeia sobe e a gaveta Conversa fechada aparece. Visto duas vezes em uso normal. |
| F3 | Abas laterais "Equipe"/"Missão" do modo real aparecem como caixas sem estilo sobre as gavetas abertas (na demonstração têm ícone e contador). |
| F4 | Botões do modo real com estilo inconsistente ("Consultar modelos", "Salvar equipe" como barra preta de texto pequeno; "Adicionar operária" só contorno). |
| F5 | Rainha aparece "Disponível" na colmeia enquanto planeja (job `running`). |
| F6 | Faixa do topo mostra o estado cru ("awaiting_user"), sem a tradução de `messages.js`. |
| F7 | Formulário de criação (Nome, Projeto, Objetivo, "Planejar com a Rainha") continua preenchido acima da missão criada. |

Fora da Hive (só registro): a página Claude Code do Hub mostra "FABLE 5 · PADRÃO" como
modelo padrão.

## Decisão do usuário (24/10/2026)

Corrigir B1, B2, F2, F5 e F6 e repetir a fase 2; F1, F3, F4 e F7 vão para a tarefa de
escala (EQ-12). Registro da correção: `2026-10-24_hivemind-correcoes-teste.md`.

## Fase 2 — repetição (24–25/10/2026)

Hub reiniciado em `pythonw.exe` (o `restart_hub.ps1` recusou parar porque o PID do
marcador `hub_runtime/state/instance.json` já pertencia a outro programa, o Relógio do
Windows; o Hub estava parado e foi aberto pelo `launch_hub.vbs`). Mesma equipe da fase 2.

| Etapa | Resultado |
|---|---|
| F2 | Digitar em Nome, Projeto e Objetivo não rola mais a colmeia (`scrollTop` 0); Conversa fechada fica `inert`. ok |
| F5 / F6 | Durante o planejamento: Rainha "Coordenando", título "Iniciando — Abrindo a sessão do provedor."; topo "a Rainha está planejando". ok |
| B1 | Missão "Teste real despedida 2": `provider_session_started` em 4 s (Rainha Codex) e, na execução, a operária Claude abriu a sessão e usou `read`, `patch` e `checks`. ok |
| B3 (novo) | Primeiro plano recusado com `planning_result_invalid`; o pedido de novo plano pela Conversa funcionou e gerou o plano. A operária terminou, mas o verificador Codex foi recusado com `verdict_invalid`. Sonda (`.test-tmp/hive-diag-2410/probe_verify.py`): o Codex mandou um JSON provisório como comentário e depois a resposta final, e o adaptador juntava as duas. Corrigido. |
| B4 (novo) | O check aprovado `python -m pytest` sai com 127 sem saída no runner restrito: o perfil `hive-verify` não deixa ler o Python instalado em `AppData`. `cmd` e `node` rodam. Pendente de decisão. |
| Após B3 | Hub reiniciado. Missão "Teste real despedida 3" sem checks: plano de primeira; aprovar e iniciar pela gaveta ok; operária Claude implementou; verificador Codex devolveu veredito válido `passed`, `passed`, `unverifiable`. |
| B5 (novo) | O critério "nenhum outro arquivo alterado" fica `unverifiable` (o verificador só tem `read` por caminho e `checks`). A missão percorreu os 3 ciclos de correção reais (Rainha coordena, operária corrige, verificador confere) e parou em `awaiting_user` no ciclo 3/3. Origem intacta, como esperado. Pendente de decisão. |
| Console | Sem erros. |

Não exercitados com IA real nesta rodada (dependiam de B4/B5): aprovação da entrega,
"Incorporar entrega aprovada" e a mudança na origem pela interface. Exercitados na
rodada final abaixo.

### Achados novos de interface

| ID | Achado |
|---|---|
| F8 | Missão parada no limite de ciclos (`awaiting_user`, ciclo 3/3, sem `job_error`): a gaveta mostra só o estado e o veredito em JSON cru; não explica que o limite foi atingido nem o próximo passo. |
| F9 | Depois de um novo plano bem-sucedido, a gaveta continua mostrando "Última interrupção: … (planning_result_invalid)" da tentativa anterior. |

Missões de teste que ficaram em `awaiting_user`: "Teste real despedida"
(`90520e76…`), "Teste real despedida 2" (`beb358d9…`) e "Teste real despedida 3"
(`ee453d3f…`). Nenhuma alterou `.test-tmp/hive-teste-real/`.

## Fase 2 — rodada final (25/10/2026)

Depois de `2026-10-25_hivemind-entrega-real.md` (B4 e B5 pela opção (a), F8, F9,
processo órfão e marcador velho). O Hub tinha encerrado sozinho (a aba de teste foi
fechada e o autoquit agiu); foi aberto pelo `launch_hub.vbs`, em `pythonw.exe`.

| Etapa | Resultado |
|---|---|
| F8 | Missão 3 (ciclo 3/3): aviso "A missão usou os 3 ciclos permitidos…" com o caminho (aumentar o máximo e conversar com a Rainha) e veredito legível por critério. ok |
| Planejamento | Missão "Teste real despedida 4": plano de primeira, uma tarefa, check `python -m pytest`, critérios "testes passam" e "só os dois arquivos mudam". ok |
| Execução | Operária Claude: `read`, `read`, `patch`, `patch`, `checks` (ok). ok |
| Verificação | Verificador Codex: `checks` ok; veredito `passed`/`passed` no ciclo 1, citando a lista de arquivos alterados do backend. ok |
| Entrega | Preparada com `saudacao.py` e `test_saudacao.py`; "Aprovar esta entrega" e "Incorporar entrega aprovada" pela gaveta; topo "concluída · ciclo 1/3". ok |
| Origem | `.test-tmp/hive-teste-real/` com `despedida()` e `test_despedida`; `pytest` 2 passed. ok |
| Limpeza | Nenhum processo da Hive sobrando; console sem erros. ok |

Missões de teste que ficaram em `awaiting_user`: as três primeiras ("Teste real
despedida", "… 2" e "… 3"), de antes das correções.
