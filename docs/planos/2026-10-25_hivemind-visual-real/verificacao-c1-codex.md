# Verificação independente Codex — ciclo 1/3

Data: 26/10/2026. Modelo/esforço do verificador: **GPT-6.1 Sol (`gpt-6.1-sol`), high**.
Verificador sem participação na implementação; não modificou código nem testes.
O contador pertence à tarefa e será consolidado pela sessão principal.

**Veredito inicial: REPROVADO**, pelos achados C1-01, C1-02 e C1-03 abaixo.
Verificação visual e missão real pela interface permanecem **pendentes** das
evidências da sessão principal. Este agente não abriu navegador, não acessou a porta
8765, não operou a interface e não executou turnos reais de IA.

## Candidato e integridade

Não há Git nem manifesto C1 prévio. Foram congelados 59 arquivos em
`.test-tmp/vrc1/hash-start.json`: Python de `HiveMind/backend`, JS/CSS de
`HiveMind/frontend`, testes pytest e Node da Hive, fixtures reais e CLI fake,
`server.py`, `index.html`, `codex_frontend/static/providers.js` e
`hub_runtime/assistant.py`. Estado da aplicação, caches e documentação em edição
pela sessão principal não entram neste conjunto.

Conferências intermediária e final: **59/59 iguais**, arquivos
`.test-tmp/vrc1/hash-interim.json` e `.test-tmp/vrc1/hash-final.json`.
O candidato permaneceu intacto durante esta verificação. Este é o congelamento
final do ciclo 1, anterior à liberação de correções pela sessão principal.

Os únicos arquivos escritos pelo agente são os harnesses/logs/manifestações de
integridade sob sua pasta exclusiva `.test-tmp/vrc1/` e este relatório. Nenhum
temporário anterior foi removido ou reutilizado.

## Achados que exigem correção

### C1-01 — P2: executável local homônimo impede buscar o programa autorizado no PATH

- Critério: B06, regressão da suíte de isolamento/checks.
- Local: `HiveMind/backend/tools.py:87-94` (`program_path`).
- Reprodução: `.venv/Scripts/python.exe -B -m pytest tests/test_hivemind_workspaces.py::test_check_program_read_roots_grant_only_the_install_and_venv_home -q -p no:cacheprovider --basetemp=.test-tmp/vrc1/p1`.
- Resultado: falha em `tests/test_hivemind_workspaces.py:171`, observado `()`,
  esperado `(scripts.resolve(), venv.resolve())`.
- Causa confirmada pelo harness `.test-tmp/vrc1/diagnose.py` e seu
  `diagnose.log`: em etapa anterior o teste cria `checktool.exe` no diretório
  atual. No Windows, `shutil.which('checktool')` passa a devolver
  `.\\checktool.EXE` mesmo com o `PATH` apontando para `venv/Scripts`.
  A função rejeita corretamente esse arquivo local, mas retorna `None` sem procurar
  o executável válido na pasta do PATH. `program_read_roots` retorna imediatamente,
  **antes de ler o `pyvenv.cfg`**. O `home` inexistente não é a causa da falha.
- Impacto: check legítimo pode deixar de iniciar quando o candidato contém
  executável homônimo. A guarda não concede acesso ao executável local: o defeito
  demonstrado é de disponibilidade, sem escape comprovado.
- Correção necessária: resolver o nome somente nas entradas autorizadas do PATH,
  preservando a recusa ao cwd e aos caminhos explícitos. Não enfraquecer o teste
  nem liberar a pasta atual. Não foi atribuída esta falha ao sandbox.

### C1-02 — P1: ferramentas cadastradas da Rainha são ignoradas no planejamento

- Critério: B02.
- Local: `HiveMind/backend/service.py:599-605` (`_plan_job`).
- Reprodução sem CLI: `.venv/Scripts/python.exe -B .test-tmp/vrc1/planning_tools.py`.
  Usa serviço e store reais, origem descartável, sessão falsa e validação local;
  não envia prompt a provedor real.
- Esperado: a sessão de planejamento recebe somente as ferramentas autorizadas
  para a Rainha e aplicáveis ao planejamento; `read` desautorizado deve ser
  recusado como `tool_not_allowed`.
- Observado em `.test-tmp/vrc1/planning-tools.log`: Rainha com
  `tools=['checks']`; broker anuncia `('read','patch','checks')`; chamada `read`
  devolve com sucesso o conteúdo do arquivo descartável `note.txt`. `patch` é
  anunciado apesar da proibição do papel e devolve `tool_failed`, via handler
  antigo `denied`, em vez de `tool_not_allowed`.
- Causa: o broker fixo anterior foi preservado no planejamento, enquanto somente
  `run_job` aplica `job_tools(bee)`.
- Correção necessária: aplicar a autorização por abelha também ao planejamento,
  mantendo a regra de somente leitura antes da aprovação e sem habilitar checks
  ou patch com efeitos sobre a origem. Cobrir com sessão fake para os dois
  adaptadores; não depender de o modelo obedecer à descrição do prompt.

### C1-03 — P2: consulta de modelos sem estado de carregamento no formulário

- Critério: V01/F1.
- Local: `HiveMind/frontend/static/live-team.js:211` e `280-283`.
- Reprodução sem navegador: `node .test-tmp/vrc1/form_loading.mjs`, harness que
  reutiliza o DOM falso do teste de comportamento sem modificar esse teste.
- Esperado: ao consultar modelos durante criar/editar abelha, o botão comunica o
  carregamento e bloqueia consultas repetidas, como já faz a lista de Agentes.
- Observado em `.test-tmp/vrc1/form-loading.log`:
  `{"catalogLoading":true,"label":"Consultar modelos","disabled":false}`.
- Causa: o botão do formulário tem texto fixo; a renderização que preserva o
  formulário só sincroniza selects quando o catálogo muda de ausente para
  presente. A versão da lista, nas linhas 233-235, trata corretamente
  `catalogLoading`; essa lógica não chega ao formulário.
- Correção necessária: sincronizar o estado do botão sem reconstruir o formulário
  e sem perder valores/foco. Cobrir criar e editar com consulta pendente.

## Evidências de testes

| Execução | Resultado | Observação |
|---|---|---|
| Teste isolado de `program_read_roots`, comando de C1-01 | 1 falhou | Reprodução estável com temporário exclusivo dentro do projeto. |
| `pytest tests/test_hivemind_bees.py -q -p no:cacheprovider --basetemp=.test-tmp/vrc1/bees` | **45 passaram** | Cadastro, broker em `run_job`, progress, prompts e resumo; não cobre a omissão do planejamento de C1-02. |
| `node tests/hivemind_frontend_behavior.mjs` | **passou**, `hivemind behavior ok` | Estados/HUD, operações de gavetas, formulários e permissões de conversa via DOM falso. |
| `pytest tests -q -p no:cacheprovider --basetemp=.test-tmp/vrc1/all` | 443 passaram, 18 falharam, 1 pulou; 152,51 s | A falha Hive é C1-01. Relatórios/STT mostram `PermissionError` ao escrever no TEMP do sandbox fora do projeto; são reavaliados com TEMP/TMP locais. As falhas de ciclo de vida não são atribuídas ao produto sem isolamento. |
| Suíte completa com `TEMP` e `TMP` locais, wrapper com guarda `__main__` | **458 passaram, 3 falharam, 1 pulou; 190,81 s** | `.test-tmp/vrc1/run_pytest.py`, `suite3.log`, `results3.xml`. C1-01 e dois testes de ciclo de vida descritos abaixo. |
| Dois testes de ciclo de vida fora do sandbox | **2 passaram; 9,25 s** | Pedido da sessão principal após o congelamento C1; só processos descartáveis dos testes, sem porta 8765. `.test-tmp/vrc1/outside.log` e `outside.xml`. |

Uma rodada intermediária (`suite.log`/`results.xml`) é **inválida para concluir
regressões**, pois o primeiro wrapper do verificador não tinha guarda
`if __name__ == '__main__'`, necessária ao `multiprocessing/spawn` do Windows. Foi
corrigido somente o harness descartável e iniciada nova rodada. Não houve
modificação do candidato para contornar erro de ambiente ou teste.

O único skip é `test_shared_or_linked_files_are_not_followed`, em
`tests/test_hivemind_workspaces.py:64`, motivo **`fixture hardlinks unavailable`**.
Não se declara comprovada neste ambiente a recusa de hardlinks a partir desse
teste pulado. A inspeção da guarda não substitui a evidência que ele daria.

Os outros dois testes que falharam na suíte final, além de C1-01, são:

- `test_timeout_fallback_mata_descendente_que_tentaria_escrever`: o descendente
  descartável criou `orphan.txt` após o timeout. `server.py:_kill_tree` depende de
  `taskkill /T`; a reprodução exclusiva de ambiente
  `.test-tmp/vrc1/taskkill_probe.py` lança apenas um Python descartável próprio e
  registra **taskkill código 1, “Nome de usuário ou senha incorretos.”** em
  `taskkill-probe2.log`. Há evidência concreta de falha da ferramenta de encerramento
  neste sandbox, e não só uma suposição baseada no teste.
- `test_stop_ignora_marcador_velho_sem_encerrar_processo_alheio`: PowerShell
  devolveu código 1 com **“Acesso a um recurso CIM não estava disponível para o
  cliente”**, além de falha de `InitializeDefaultDrives`. O teste usa porta 1 no
  script descartável e não depende nem altera o Hub real.

Ambos **passaram fora do sandbox** em 9,25 s, sem alterações de código ou testes
(`outside.log`, `outside.xml`). Assim, não entram como novas reprovações de código
nesta tarefa. Relatórios/STT passaram na rodada final com TEMP/TMP locais. Nenhuma
dessas limitações de ambiente explica C1-01. A suíte completa não fica declarada
integralmente verde: permanece a falha real C1-01 e o skip de hardlinks.

## Critérios, um a um

`Não verificável` abaixo significa que existe evidência parcial técnica, mas não
a prova completa exigida pelo critério. Não equivale a aprovação visual.

| Critério | Resultado | Evidência e limite |
|---|---|---|
| B01 | **Passou** | `bees.py`, validação em store e plano; testes de limites de descrição, skills, instruções, ferramentas, temporárias e elenco antigo incompleto; erro `roster_incomplete` de serviço/rota com identificação da abelha. |
| B02 | **Falhou** | C1-02. Operárias/verificador e coordenação usam o subconjunto correto e os testes de recusa nos adaptadores passam; o planejamento ignora o cadastro. |
| B03 | **Passou** | `validate_progress` rejeita bool, tipos, limites, controles e tamanho; handlers registram `bee_progress` com job/abelha sem escrita no candidato; argumentos inválidos retornam erro sem derrubar job; prompt explica uso; testes de broker/serviço. |
| B04 | **Passou** | `summary.py`, `Store.bee_events` sem paginação de 500 e rota GET; teste com 700 eventos, status por tarefa, ciclo, último job, progresso e contagem por ferramenta. |
| B05 | **Passou** | Prompt de planejamento inclui cadastro completo, preferência por permanentes e temporárias completas; prompts de execução incluem descrição e instruções das skills; sessões fake verificam os campos e a identidade exata do cadastro no plano. |
| B06 | **Falhou** | C1-01 impede a suíte completa de passar. Documentos vivos foram atualizados e os testes de códigos/mensagens e abertura de missões antigas passam. Suíte final no sandbox: 458 passaram, 3 falharam, 1 pulou; dois testes de ciclo de vida passaram na repetição fora do sandbox. |
| V01 | **Falhou** | C1-03/F1. Classes, abas, marca temporária, edição de permanentes e exibição de modelo/esforço salvos estão presentes; precisão visual e interação real aguardam evidências. |
| V02 | **Não verificável** | Gaveta usa componentes, abas, hashes abreviados, ações reais e formulários; behavior cobre estados especiais, confirmação inline, ciclos, recuperação e limpeza após criação. Desvio já registrado em VR-06: entrega sem “Solicitar ajuste”, porque backend não aceita mensagem nesse estado; requer decisão de aceite da sessão principal em relação ao PRD. Não é tratado como um quarto bug novo. |
| V03 | **Não verificável** | Código usa cabeçalho/balões/formulário esperados e texto como `textContent`; regras de habilitação cobertas pelo behavior. Quebra de textos e fidelidade visual precisam da prova de navegador. |
| V04 | **Não verificável** | Compositor cria abas com ícone/contador/seta, gavetas fechadas inertes; DOM falso confere contadores e ações. Sobreposição exige evidência geométrica de navegador. |
| V05 | **Não verificável** | `missionStep`, `hudOf`, `deriveRealView` e behavior cobrem etapas, pausa/falha, banner e ações; HUD não aprova diretamente. Formato/animação visual aguardam evidência. |
| V06 | **Não verificável** | Snapshot usa resumo do backend, temporárias, jobs, dependências, progresso e rotas; código preserva redução de movimento e rig PNG. Células limitadas a Rainha + 8, conforme escopo. Animações/posição/fidelidade aguardam evidência visual. |
| V07 | **Não verificável** | Popup usa dados reais, critérios/arquivos, aprovação/incorporação por hash e Escape; behavior cobre a composição e ações. Layout e acesso pela interface aguardam evidências. |
| V08 | **Não verificável** | Script de estouro e fixture longa existem, CSS tem quebra/rolagem/truncamentos; este agente não executou navegador por divisão explícita do trabalho. Aguardam-se resultados em 1280×720, 1920×1080 e janela baixa ≥600 px. |
| V09 | **Não verificável** | Comparador tem fixtures reais, 13 cenários, componentes equivalentes, medição com baseline da demonstração e lista `KNOWN` vazia; não foi executado por este agente. Exige métricas e capturas, incluindo regressão da demonstração. |

## Isolamento, compatibilidade e superfície

- Broker variável continua com catálogo fechado e handlers confiáveis;
  `dispatch_and_reply` recusa ferramenta conhecida fora do job antes de executar
  handler e respeita pausa/drenagem. Os adaptadores anunciam `broker.names`.
  C1-02 é a exceção concreta encontrada no planejamento.
- O handler de `progress` não recebe acesso novo ao sistema de arquivos; valida
  tipos e conteúdo antes de registrar evento. Skills continuam texto declarativo.
- `WorkspaceTools` mantém limites de arquivo, paths aprovados, CAS/hash e recusa a
  links/arquivos compartilhados. Verificador não recebe patch pelo cadastro nem
  pela lista de edição. Checks mantêm perfil restrito e recusa de concessões
  perigosas; C1-01 não justifica relaxar essas guardas.
- API mantém validação de origem local e aprovações por hash/revisão/lease. Os
  encaixes Hive foram conferidos por leitura e testes; não há base Git para
  atribuir alterações históricas fora dos encaixes. Voz/fila compartilhada e teto
  de sessões permanecem cobertos pelos testes existentes, sujeitos ao resultado
  final da suíte.
- Frontend foi dividido por responsabilidade; compositor tem 23 linhas; módulos
  de gaveta usam o estado e encaminham ações ao controlador, sem API própria.
  Classes substituídas são verificadas como ausentes por testes estáticos.
- A abertura de missões antigas sem os campos ricos usa defaults compatíveis;
  planejar novamente com cadastro antigo incompleto é bloqueado como solicitado.
- Ressalvas históricas de adaptadores e escala explicitamente fora do escopo não
  foram convertidas em novas reprovações desta tarefa.

## Pendências para fechamento

1. Corrigir C1-01, C1-02 e C1-03 no ciclo seguinte controlado pela sessão principal;
   este verificador não implementará as correções.
2. Após as correções, executar novamente os testes pertinentes e a suíte. Os dois
   testes de ciclo de vida já passaram fora do sandbox; skip de hardlinks permanece
   uma limitação explícita de evidência.
3. Receber/avaliar métricas e capturas de comparador/estouro e evidências da missão
   real pela interface conduzida pela sessão principal.
4. Resolver explicitamente o desvio de V02 em relação a “Solicitar ajuste” da entrega.
5. Hashes finais conferidos (59/59). Uma mudança posterior de candidato exige nova verificação;
   este relatório não aprova um estado modificado depois dele.
