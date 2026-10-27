# Verificação — backend HiveMind

> **Status em 21/10/2026: CONCLUÍDA** — aprovada na verificação independente do C4 (20/10/2026, R01–R15). Este arquivo é registro histórico do processo e pode descrever intenções já superadas; a referência do código atual está em `docs/hivemind/README.md`. As ressalvas do C4 seguem como EQ-11 em `../2026-10-20_hivemind-escala-equipe/issues.md`.

19/10/2026 · ciclo **1/3** · P0 concluído e liberado pela coordenação; P1–P5 liberados, backend final **não verificado**.
O usuário aprovou o plano, os três encaixes e a validação real mínima em
19/10/2026 (“Autorizo esse plano”). Planejador GPT-6.1 Sol high
somente leu fontes e escreveu os quatro documentos. Nenhum teste, inferência,
CLI de agente, login, instalação ou alteração de código executado pelo planejador.
Frontend C7 aprovado permanece registro próprio, sem certificar backend inexistente.

## Evidência de levantamento

- Lidos AGENTS.md, docs/desenvolvimento.md, CLAUDE.md como arquitetura e
  docs/runtime.md; assistant.py confirma injeção atual de uso-pessoal/vault.
- HiveMind/frontend/routes.py só serve assets; app.js instancia HiveSimulation,
  cuja setLifecycle/documentVisible pausa a demo. Isso não atende scheduler real.
- server.py:_hud_watchdog chama _shutdown/os._exit sem drain; index.html usa
  /hud_ping e /hud_bye best effort. Exceção estreita proposta em plano.md.
- Coordenação informou diagnóstico sem inferência: Codex 0.160.0 com assinatura
  ChatGPT autenticada; Claude 2.1.289 com assinatura claude.ai autenticada. Dados
  pessoais omitidos. Não comprova modelos disponíveis, billing ou isolamento.
- Schema Codex fornecido em .test-tmp/hivemind-backend-schema/ é artefato de
  levantamento transitório, não código de produto nem certificado de segurança.


### Evidências P0 sem inferência — ciclo 1, 19/10/2026

Implementação em andamento pelo agente selecionado explicitamente GPT-5.6 Terra,
esforço high. Nenhum turno de modelo foi iniciado. Catálogo não comprova direito
de acesso individual, que continua não testado até o smoke autorizado em P5.

- Codex CLI 0.160.0: app-server inicializado e conta de assinatura e catálogo
  consultados de modo sanitizado, com refreshToken=false. Rate limits informaram
  uso ordinário disponível e hasCredits=false no momento da observação; verificar
  novamente antes de cada despacho, sem presumir custo zero ou estado permanente.
- Claude Code 2.1.289: autenticação nativa da assinatura preservada com
  --safe-mode, distinto de --bare; catálogo de 12 entradas. Controle get_usage
  com skip_behaviors=true retornou behaviors=null, duas janelas ordinárias
  disponíveis e uso extra desabilitado. get_settings não mostrou hooks, status
  line, file suggestion ou fallback gerenciados. Revalidar antes do despacho;
  campos ausentes, adicionais não interpretáveis ou mudança fecham o gate.
- Codex: perfil MXC da fixture com :root=deny, :minimal=read, tmp negado e
  workspace autorizado bloqueou leitura e escrita externas, inclusive por
  junction e subprocesso, e permitiu escrita interna. O sandbox unelevated padrão
  sem MXC não comprovou leitura restrita e não foi aceito. A proteção deve ser
  revalidada para a configuração e ambiente usados; isolamento não é cwd/cópia.
- Schema experimental, handshake e thread/start sem turno confirmaram dynamicTools
  e environments=[]; sem handshake a requisição falhou. Fonte 0.160.0 vincula
  shell, apply_patch e view_image à presença de ambiente; agents.enabled=false
  e multi_agent_v2=false desabilitam subagentes. Referências versionadas:
  https://raw.githubusercontent.com/openai/codex/rust-v0.160.0/codex-rs/core/src/tools/spec_plan.rs
  e https://raw.githubusercontent.com/openai/codex/rust-v0.160.0/codex-rs/core/src/config/mod.rs.
- Uma fixture MCP só iniciou sem override; override por nome negou a inicialização
  e roster do thread registrou disabled. Tabela vazia não substitui override por
  nome. Inventário efetivo atual teve um servidor, sem expor seu nome ou valores;
  não havia AGENTS global. A presença futura, configuração desconhecida, mudança
  de fingerprint ou roster divergente deve fechar o gate, antes de cada turno.
- Claude com --tools vazio, MCP estrito vazio, fontes de settings vazias e
  --safe-mode forma o candidato sem ferramentas nativas. Configurações gerenciadas
  efetivas continuam uma condição de verificação, não são presumidas ausentes.
- Fixture de broker aceita apenas read/patch/checks; pausa fecha novas admissões
  e aguarda uma escrita admitida terminar antes de declarar drenagem. Os handlers
  ainda precisam de guardas de caminhos reais em P2 e integração de sessão/turno
  em P3; os testes de P0 não certificam o produto final.

#### Checkpoint P0 e contrato para fases seguintes

- Testes focados da fase: 11 passaram em 6,59 s. Código de emissão interna
  vincula evidência ao processo, seleção, inventário de configuração e broker;
  não existe entrada HTTP para fornecer evidência. Pausa, mudança de HOME,
  configuração, modelo, quota, cobrança ou fim do processo fecham o gate.
- As duas implementações de sessão passaram testes reais sem turno em fixture,
  com saída sanitizada e conta nativa: Codex 0.160.0 e Claude 2.1.289.
  Codex confirmou thread efêmero, environments=[], perfil, cwd, instruções vazias
  e status disabled para cada MCP inventariado. A lista sem filtro respondeu
  -32603 por erro ao recarregar a config; a consulta oficial por threadId e
  serverName usa snapshot do thread e passou. Não foram expostos nomes/valores.
- A resposta Codex retornou raízes suplementares vazias para o thread sem ambiente;
  nenhuma raiz adicional diferente do workspace é aceita. O isolamento não se
  baseia em cwd: não há ambiente nativo, o perfil restrito MXC foi testado fora
  do turno e o broker deverá aplicar os guardas reais de P2. Configuração global
  de perfil homônimo é recusada para evitar herança de raízes adicionais.
- Codex usa ephemeral=true e Claude --no-session-persistence: conteúdo da missão
  e checkpoints pertencem ao estado Hive futuro, não ao histórico pessoal dos
  fornecedores. O entitlement individual segue não testado até P5. P3 deve usar
  a mesma sessão e revalidar discovery/controles antes de cada turno, receber
  chamadas de ferramentas exclusivamente pelo broker guardado, drenar antes de
  interromper e bloquear estados desconhecidos; o P0 não despacha turnos.
- A coordenação liberou P1–P5 no mesmo ciclo 1/3; revisão independente continua
  pendente ao final. O fechamento do último HUD deve pausar Hive também com
  AUTOQUIT desativado, por lifecycle próprio da funcionalidade, sem novo hook
  global ou alteração do watchdog fora da exceção aprovada.

#### P1 — estado e missões

Testes focados: 4 passaram em 0,47 s. SQLite persiste eventos e comandos
idempotentes em transação, revisões concorrentes entram em conflito, aprovações
referem hashes e verificação exige critérios completos e outro papel. O teto de
três ciclos e recuperação explícita resistiram à reabertura. Integração de
jobs, escopo real e comprovação da sessão independente pertencem às fases
seguintes; estes testes não certificam o backend completo.

#### P2 — checkpoint parcial

No ciclo 1, 18 testes focados passaram em 1,94 s: snapshot sem Git e worktree
em repositório de fixture, exclusões, links, aprovação por hash, stale e rollback
por falha parcial. O plano rejeita aliases Windows de caminho compartilhado
sem dependência; patch compara hash conhecido sob lock local e rejeita edição
obsoleta. Ainda faltam integração de recuperação e geração imutável na cadeia.

O executor de checks foi testado sem inferência com Codex 0.160.0/MXC e somente
arquivos de fixture: leitura do candidato e escrita no scratch permitidas,
escrita no candidato e leitura de arquivo externo negadas; execução de arquivo
JS gerou relatório no scratch e deixou manifesto do candidato inalterado. O
perfil efetivo é conferido antes do comando e o wrapper fixa TEMP/TMP/HOME do
processo filho no scratch. O teste usa Node/VM; não comprova compatibilidade com
qualquer interpretador ou conjunto de dependências, especialmente pytest do Hub.

Complemento P2: geração do runtime por manifesto, carregamento em pacote privado
e recuperação explícita do journal foram exercitados em fixtures; 25 testes
combinados passaram em 2,75 s. O executor permanece limitado aos recursos
efetivamente comprovados, e a cadeia com UI ainda não foi validada.

#### P3 — checkpoint de implementação

O limite configurável de workers/subagentes/verificador é persistido e verificado
na reserva transacional; Queen tem slot próprio. Sessões usam o broker restrito,
o verificador tem sessão distinta e o hash do candidato é conferido. Pausa fecha
admissões, espera operação e resposta persistidas, solicita interrupção e só
declara pausa após saída do job. Fechamento e perda de heartbeat têm motivos
distintos nas fixtures; reconexão não retoma. Nove testes focados passaram; os
ajustes posteriores de evento obsoleto e replay de pausa passaram em sete testes.
O planejamento da Queen é de leitura e rejeitou patch antes da aprovação em
fixture. O despachante conserva limite global e a lease de comandos não permite
duas abas assumirem simultaneamente a mesma missão. O runtime é carregado por
manifesto e rejeita código extra; o perfil opt-in não injeta vault nem guardas
pessoais. A nova entrada inicializou Codex e Claude reais com gate válido sem
turno de modelo. Após os encaixes e testes adicionais, 41 testes focados passaram
em 8,91 s. O watchdog próprio funciona também sem AUTOQUIT; o hook de saída aguarda
drain, com grace para reload. O fluxo HTTP/UI, a recuperação operacional de jobs
ambíguos e o teste real com inferência seguem pendentes. O fechamento ainda não
foi exercitado no Hub real, e a suíte completa permanece para P5.

Uma janela entre a conferência de hash da origem e `os.replace` ainda permite
colisão com escritor externo. Não há prova de preservação da alteração concorrente;
a aplicação não pode ser exposta como segura até corrigir e testar essa corrida.

Durante a descoberta do executor, o primeiro teste de relatório usou TEMP nativo
do processo, que não correspondia ao scratch enviado; a chamada relatou sucesso,
mas o arquivo não apareceu no scratch. A localização e permanência desse artefato
de fixture não foram comprovadas. Uma proposta de pesquisa com exclusão de alvo
derivado desse TEMP foi rejeitada pela revisão automática antes da execução, por
não garantir que o alvo estivesse no scratch. Nenhuma exclusão foi executada nem
repetida; a alternativa testada não usa esse diretório para o filho. A limpeza
desse possível artefato externo permanece pendente de autorização específica.

#### Privacidade e aprovação automática

Durante a descoberta inicial, duas consultas exploratórias get_usage foram feitas
sem skip_behaviors. A documentação do SDK indica que elas podem examinar
transcrições recentes para calcular estatísticas comportamentais; não há evidência
para afirmar quais conteúdos foram lidos. Nenhum turno foi iniciado e nenhuma
estatística foi impressa, salva ou exposta. As consultas seguintes usam
skip_behaviors=true e verificam behaviors=null; não foram inspecionados históricos.

Uma proposta de link efêmero para o arquivo de autenticação foi rejeitada pela
revisão automática antes da execução, pois facilitaria acesso a credenciais
sensíveis. Nenhum link foi criado. A alternativa usada preserva o HOME e a
conta nativos, sem ler, copiar ou alterar credenciais e sem repetir a ação
rejeitada; configuração efetiva e fontes globais são checadas separadamente.

#### Checkpoint C1 — P3, P4 e P5 parcial

- O implementador foi GPT-5.6 Terra com esforço `high`, selecionado
  explicitamente. O ciclo permanece **1/3**. A implementação P1–P4 está
  presente; HB-05 e a verificação independente HB-06 continuam pendentes.
- P3 liga o limite transacional persistido a workers, subagentes e verificador;
  a Queen ocupa sua sessão própria. Cada papel tem uma sessão independente,
  ferramentas nativas ficam indisponíveis ao modelo e a pausa fecha admissões,
  drena operação admitida e só então interrompe. O watchdog do Hive pausa no
  último HUD mesmo com `HUB_AUTOQUIT=0`; recarregamento e minimização não
  retomam uma missão.
- P4 expõe somente os dados e comandos do backend por `/hive-api`, com lease de
  controle e revisão. O fluxo demonstrativo continua separado. A QA visual em
  fixture própria, sem IA e na porta 18765, confirmou a tela inicial, gavetas e
  demonstração em 1440×900 sem erros de página e preservou a arte PNG, o 2D e
  a paleta. Em 1180×760 o texto de cenário foi mantido em uma linha após ajuste
  local de flex; a captura e resultado estão em `.test-tmp/hive-root-visual-qa/`.
- R09 substituiu a janela insegura anteriormente registrada: no Windows,
  `ReplaceFileW` captura o arquivo que será substituído em backup journalado no
  mesmo volume; adição usa `MoveFileExW` sem substituição e remoção vai à
  quarentena journalada. Divergência, handle ambíguo ou erro parcial deixam
  artefatos e estado `recovery_required`; nenhuma versão é descartada. A origem
  e o journal em volumes diferentes falham antes de qualquer mutação. Isso não
  promete CAS global, exclusão contra escritor externo ou transação multiarquivo.
- A suíte focada mais recente executou 42 testes em 23,09 s. Ela inclui o caso
  de corrida entre conferência e troca, rollback concorrente, adição/remoção,
  volume diferente e contratos de planejamento. O resultado interno da Queen
  continua estrito: só o envelope do adaptador com `final` textual e um JSON
  interno exato de plano/esclarecimento é aceito; Markdown e objetos inválidos
  produzem o código local `planning_result_invalid`. Eventos só registram
  categorias allowlisted, nunca texto retornado pelo fornecedor.
- Smoke Claude único: passou com modelo `default` e esforço `low`, sem
  ferramentas nativas. Smoke Codex único: o turno terminou como falho, sem
  categoria preservada pela versão então executada; a descoberta posterior sem
  turno ainda confirmou gate e autenticação atuais. Não houve repetição. Assim,
  a compatibilidade real Codex R15 permanece não verificável neste candidato.
- A missão mínima Claude foi iniciada uma única vez. A primeira preparação falhou
  antes de sessão por `invalid_root`; a execução autorizada posterior abriu só a
  sessão da Queen e terminou em `awaiting_user` com evento histórico
  `job_failed`. Worker, verificador e entrega não foram iniciados. Não se leu
  conteúdo de resposta, histórico ou credencial. Uma tentativa de diagnóstico
  que poderia executar a missão foi rejeitada automaticamente antes de rodar;
  a descoberta isolada permitida depois não abriu sessão nem turno e registrou
  gate apto exceto pela evidência de enforcement, que só existe dentro da sessão.
  O contrato local foi então coberto por fixtures; a causa do turno histórico
  continua desconhecida e a missão não será repetida sem nova autorização.
- Portanto, P5 não aprova a cadeia ponta a ponta: entrega real, três papéis em
  missão e compatibilidade Codex seguem pendentes. O candidato deve ser revisado
  como implementação congelada, sem equivaler essas limitações a aprovação.
- A tentativa única de suíte completa de P5 com `pytest tests -q` e basetemp
  próprio em `.test-tmp/hivemind-final-full` publicou somente progresso de 24%
  e 49% antes de o processo encerrar sem linha terminal, contagem ou código de
  saída disponível ao implementador. Não é resultado aprovado nem reprovado e
  não foi repetida. A linha de base anterior e os 42 testes focados seguem as
  únicas evidências de teste concluído deste candidato.
- O manifesto congelado está em `manifesto-c1.sha256`. Qualquer alteração exige
  nova geração do manifesto e nova verificação; HB-06 deve decidir os testes
  adicionais e a situação das pendências sem disparar inferência não autorizada.

## Matriz futura — todos os resultados pendentes

| Critérios | Evidência exigida do candidato final |
|---|---|
| R01–02/R15 | Discovery local sem inferência; modelo/effort inválidos; catálogo vs acesso; credenciais ausentes de logs; quota e cobrança extra bloqueadas. Após aprovação deste plano e P0/quota aptos, um smoke curto por CLI habilitado e uma missão mínima ponta a ponta em fixture, consumindo franquia das assinaturas sem APIs/créditos extras. Não repetir livechecks válidos com hash/protocolo estáveis. |
| R03–04 | Zero ferramentas graváveis antes de aprovar plano exato; alterar escopo invalida aprovação; agentes/processos reais ligados a bee_id; temporárias removidas do roster com histórico íntegro. |
| R05/R08 | Scheduler instrumentado inclui subagentes/verificador no teto; DAG disjunto vs compartilhado; tentativas nested negadas; contador resiste a crash/retomada; terceiro ciclo reprovado para. |
| R06–07 | Worktree e Hub sem Git; snapshot sem segredos/recursão; tentativas de escapar por absoluto, shell, junction e processo filho negadas. Verificador não altera código/testes; artefatos de checks fora do candidato. |
| R09 | Hash aprovado corresponde ao aplicado; mudança externa após aprovação rejeita stale; falha no meio da aplicação recupera/rollback; remoções limitadas; reinício do Hub exige decisão própria. |
| R10–11 | TrocaHive→Claude/Codex e minimização não pausam; duas janelas/último fechamento; escrita em curso termina antes de paused; nova ferramenta negada; beacon perdido/heartbeat ambíguo diagnosticado; reconectar/reload não retoma. |
| R12 | Duplicação de evento/comando; crash antes/depois de ferramenta e durante entrega; job órfão/reuso de PID; recovery_required impede repetição ambígua. |
| R13–14 | QA focado da tela real preserva PNG/2D/mostarda e navegação; ausência de ticks simulados em missão real; seis sessões pessoais, SPEAK_Q, guardas, mobile e bind local preservados. |

## Procedimento e histórico

### Linha de base antes de P0 — 19/10/2026

- Suíte `pytest tests -q` no sandbox, TEMP/TMP sob `.test-tmp`: 234 passaram e
  `test_timeout_fallback_mata_descendente_que_tentaria_escrever` falhou porque
  o descendente da fixture sobreviveu ao timeout; 35,57 s. Nenhum código do P0
  existia ainda.
- O mesmo teste isolado, executado fora do sandbox com o Python da `.venv` e o
  mesmo TEMP/TMP, passou em 3,56 s. O teste usa `taskkill /T /F` para a árvore
  criada pela fixture; o resultado é consistente com a restrição do ambiente de
  teste. A linha de base completa não foi repetida. Isso não prova isolamento do
  produto nem altera a exigência de sandbox para as missões.

### Confirmação de escopo — 19/10/2026

O usuário confirmou que o plano não deve ser modificado nem flexibilizado:
a restrição de leitura entre projetos e clientes continua obrigatória, assim
como a proteção contra escrita fora do workspace.

Depois de testes focados e suíte completa pelo implementador, congelar manifesto
e entregar PRD/plano/Issues, arquivos alterados e evidências a Sol6.1 high em
contexto independente. Verificador executa checks pertinentes e suíte
`.\.venv\Scripts\python.exe -m pytest tests -q`, sem editar código/testes.
Pode escrever relatório/Issues. A aprovação única deste plano inclui os três encaixes e teste
real mínimo em fixture isolada com consumo de franquia das assinaturas, sem APIs
ou créditos extras: um smoke curto por CLI habilitado e uma missão mínima ponta
a ponta. Não inferir se P0/quota falhar nem repetir livechecks já válidos com
hash/protocolo estáveis. Não realizar esse trabalho no ciclo 0.

Cada ciclo registra modelo/esforço real, hashes, comandos/resultados pertinentes,
passou/falhou/não verificável por critério e veredito global. C1 implementação
inicial; C2/C3 apenas correções+nova verificação. Aprovação anterior não vale para
candidato alterado. Após C3 reprovado/pendente, diagnóstico e parada.

| Ciclo | Estado | Veredito |
|---|---|---|
| 0 | Planejamento escrito; aprovado em 19/10/2026. | Não submetido; nenhum aceite validado. |
| 1 | P0 iniciado; agente GPT-5.6 Terra high selecionado explicitamente. | Verificação independente final pendente. |
| 2 | Correções HB-C1-01 a HB-C1-04 iniciadas após reprovação independente C1; implementador GPT-5.6 Terra high. | Aberto; R15 continua pendente sem nova inferência. |

### Checkpoint C2 — correções locais

As correções C2 vinculam resultado, tentativa, dependência, pendência e início
de verificação ao `plan_hash` aprovado. O replanejamento preserva o workspace
anterior e não zera ciclo, eventos ou histórico; resultado desconhecido exige
recuperação explícita. A reconciliação stale é um comando separado: cria novo
snapshot/base/candidato, reaplica só diferenças sem conflito, invalida verdict e
entrega e inicia nova verificação. Conflito mantém origem e versões preservadas,
permanece em `awaiting_user` e orienta replanejamento explícito.

Após verdict falho, a Queen coordena primeiro usando critérios e evidence
duráveis; só depois workers podem reservar tarefas. Seu feedback é durável e
entra no prompt dos workers, que continuam limitados ao escopo aprovado. A UI
agora possui controle explícito do teto da missão selecionada, sem retomar a
missão ao ajustar. As regressões focadas concluídas estão registradas em
`issues.md`; nenhuma sessão ou turno real ocorreu em C2. A suíte completa e o
manifesto C2 são necessários antes de nova devolução ao verificador.

Atualização de fechamento C2: a suíte `pytest tests -q` com basetemp próprio e
JUnit em `.test-tmp/hivemind-c2-full.xml` concluiu com **300 passed**, zero
falhas e zero erros em **43,416 s**. Esse resultado valida as correções locais,
mas não altera a pendência R15 nem autoriza repetir smokes ou missão real.
O manifesto congelado do candidato é `manifesto-c2.sha256`.
