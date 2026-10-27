# Plano — backend HiveMind

> **Status em 21/10/2026: CONCLUÍDA** — aprovada na verificação independente do C4 (20/10/2026, R01–R15). Este arquivo é registro histórico do processo e pode descrever intenções já superadas; a referência do código atual está em `docs/hivemind/README.md`. As ressalvas do C4 seguem como EQ-11 em `../2026-10-20_hivemind-escala-equipe/issues.md`.

19/10/2026 · faixa completa · **aprovado pelo usuário** (“Autorizo esse plano”).
Contador backend **1/3**. Planejamento: GPT-6.1 Sol high. Implementação atribuída:
GPT-5.6 Terra high, selecionados explicitamente na criação do único agente
responsável pela cadeia dependente. Verificação futura:
GPT-6.1 Sol high independente, sem implementar/corrigir código ou testes.
Se modelo/esforço exigido estiver indisponível, reportar antes da etapa; não
substituir. Frontend aprovado C7 permanece tarefa encerrada, sem novo ciclo ali.

## Decisões técnicas propostas

Um serviço Hive local no processo da ponte, com scheduler próprio e armazenamento
SQLite; blueprint apenas expõe comandos/consultas. Sem microserviços, Redis,
framework de agentes ou dependência do aplicativo Codex. Um único dono scheduler
por banco, reserva de slots transacional e recuperação conservadora. Import não
dispara CLI, modelo ou retomada de missão. Adapters encapsulam protocolo do CLI;
capacidades descrevem leitura/patch/checks e podem receber conectores futuros.

O checkpoint P0 foi concluído; P1–P5 foram liberados em sequência no mesmo ciclo.
Os caminhos seguintes descrevem a arquitetura aprovada; fases posteriores ainda não estão concluídas:

| Caminho | Responsabilidade |
|---|---|
| HiveMind/backend/__init__.py, routes.py | Blueprint /hive-api; validação web e comandos, sem lógica de subprocessos nas rotas. |
| HiveMind/backend/service.py | Montagem/lifecycle do serviço; único dono por instância. |
| HiveMind/backend/store.py | Migração SQLite, transações, event log, idempotência e consultas. |
| HiveMind/backend/missions.py | Transições, aprovações versionadas, ciclos e escopo. |
| HiveMind/backend/scheduler.py | DAG, slots globais, exclusão por arquivos e despacho/drain. |
| HiveMind/backend/lifecycle.py | Leases de controle/observação, pausa e checkpoint/recovery. |
| HiveMind/backend/adapters/{base,codex,claude}.py | Discovery sanitizado e protocolo normalizado de sessão/turn/tool/usage/erro. |
| HiveMind/backend/capabilities.py, tools.py | Política determinística e broker de ferramentas com destinos e comandos autorizados. |
| HiveMind/backend/workspaces.py | Git worktree/snapshot, manifesto, exclusões e geração imutável do runtime. |
| HiveMind/backend/delivery.py | Pacote por hash, comparação origem/base/candidato, aplicação e rollback. |
| HiveMind/backend/instructions/ | Prompts específicos por papel, sem uso-pessoal/vault. |
| HiveMind/state/ | hive.sqlite3, manifests/, workspaces/, verification/, deliveries/, runtime/ e logs sanitizados; dados privados excluídos de empacotamento. |
| HiveMind/frontend/static/{api,mission-state}.js | Cliente HTTP/eventos e estado real, independente do clock de demo. |
| HiveMind/frontend/static/{app,hive,drawers}.js | Conectar dados reais e controles indispensáveis, preservando desenho/rig/assets. |

SQLite guarda projects, bee_configs, missions, plan_versions, task_dag, jobs,
provider_sessions, approvals, checkpoints, leases, events e deliveries. São
entidades do mesmo store, não obrigação de criar um módulo por tabela. Eventos
carregam mission_id/job_id/bee_id, sequência, origem e horário; nunca credenciais.
Comando mutante exige idempotency_key + expected_revision; aprovações incluem
hashes e a identidade local da decisão, não apenas um booleano. Eventos duplicados
do fornecedor são deduplicados; texto/eventos/tool outputs são sanitizados.

## Contrato mínimo ponta a ponta

GET /hive-api/bootstrap fornece projetos, configurações e estado sanitizado dos
adaptadores; POST /hive-api/compatibility faz apenas discovery sem inferência.
POST /hive-api/projects registra caminho escolhido validado; configuração de
abelhas e modelos por revisão, sem interpretar texto como comando. POST
/hive-api/missions cria pedido; /missions/<id>/messages leva esclarecimentos à
Queen; /plan/approve aprova versão/equipe; /pause e /resume controlam missão;
/delivery/approve e /delivery/apply referem pacote exato. GET /missions/<id> e
/events?after=<seq> (long-poll limitado) reconstroem estado. /leases permite
observar, adquirir controle explícito e heartbeat; baixa usa beacon best effort.
Rotas retornam conflitos de revisão/estado, sem iniciar efeitos em GET.

Primeira missão: projeto/roles válidos → conversa Queen → plano/equipe temporária
propostos → aprovação humana → workspace → jobs → verificador independente →
correções limitadas ou pacote → aprovação humana → aplicação/recibo. Inicialmente
somente capacidade software local; modelo não seleciona projetos/destinos livres
nem instala conectores. Histórico permanece depois da remoção de temporárias.

## P0 — compatibilidade e proteção, gate antes de qualquer missão gravável

1. Registrar versão/caminho CLI e gerar/validar schema de protocolo da versão
instalada em fixture técnica, sem inferência. Inicializar Codex app-server, ler
catálogo/account status sanitizado; Claude auth status e parâmetros documentados.
Versões fornecidas pela coordenação: Codex 0.160.0, Claude 2.1.289; confirmar no
momento do gate sem instalar/atualizar. Ambos com conta de assinatura autenticada
segundo diagnóstico sanitizado já feito pela coordenação; isso não valida modelo.
2. Separar catálogo, suporte a esforço, entitlement e evidência de uso incluído.
Não habilitar --bare, chaves ou ambiente API. Não passar variáveis de chave para
CLI; preservar autenticação gerida pelo fornecedor sem inspecionar token. Claude
pode ter modelos/contextos com créditos extras; se não houver sinal verificável
de elegibilidade/limite, combinação fica bloqueada. Não provocar inferência para
descobrir custo. Limitação de quota não autoriza usar créditos pagos.
3. Provar política de ferramentas de cada versão no Windows. Não reutilizar
--dangerously-skip-permissions do Hub pessoal. Queen usa leitura limitada do
projeto permitido; workers só workspace; verificador lê candidato e escreve
artefatos apenas na área de verificação. Não permitir MCP/plugins globais,
ferramentas web, shells irrestritos, tarefas detached/background ou agentes
nativos não contabilizados. Direitos de ler também são restritos, não só escrita.
4. Caminho preferido: broker com operações read/patch/checks e negação de builtins
que o contornem, comprovada pelo adaptador; se a versão não suporta isso, sandbox
nativo/OS equivalente precisa comprovar proteção de origem, segredos e guardas de
pausa. Não inventar campo de schema. Hooks/allowlists são defesa adicional e
precisam cobrir Bash, caminhos absolutos, links e subprocessos; prompt/cwd não
comprovam enforcement. Se nenhuma opção cumprir, adaptador permanece incapaz de
executar missão gravável e o gate bloqueia liberação, sem reduzir o requisito.
5. Instrumentar início/fim real de ferramentas e drenagem: pausa nega novos tools,
aguarda operação em curso e só interrompe turno em limite seguro. Protocolo sem
visibilidade suficiente não é habilitado para execução gravável. SIGTERM/kill de
árvore não é pausa segura. A aprovação deste plano inclui validação real em fixture isolada: um smoke
curto por CLI habilitado e uma missão mínima ponta a ponta, com consumo da
franquia das assinaturas, sem APIs ou créditos extras. Não executar inferência
se P0/quota falhar nem repetir livechecks já válidos com hash/protocolo estáveis.
Essa validação está aprovada para P5 condicionada ao gate e à quota; nenhuma
inferência será feita no P0.

Referências fornecidas pela coordenação: [Codex app-server](https://learn.chatgpt.com/docs/app-server),
[Claude headless](https://code.claude.com/docs/en/headless) e
[Claude modelos](https://code.claude.com/docs/en/model-config). O schema local e
os achados do gate prevalecem sobre assumir que documentação genérica garante
uma função disponível/segura na instalação. Nenhuma API do chat implementa o produto.
Schema local já exportado pela coordenação sem inferência em
.test-tmp/hivemind-backend-schema/: ThreadStartParams inclui sandbox/approvalPolicy;
isso não comprova enforcement. dynamicTools permanece capability experimental
a validar; flags removidas não servem como mecanismo de segurança.

## Áreas de trabalho e aplicação

Resolver/validar caminhos canônicos, recusar volumes/destinos ambíguos e links
que escapem da raiz permitida; manifesto explícito não segue junction/symlink.
Git: registrar HEAD/base, alterações locais e arquivos necessários antes de
worktree; não descartar sujeira nem supor worktree contém alterações não commitadas.
Preparar snapshot adicional explícito dos arquivos locais aprovados quando
necessário, conservando sua base. Sem Git: allowlist de conteúdo do projeto e
hashes SHA256, exclusões padrão para .env, credenciais, vault, .venv/node_modules,
logs, caches e HiveMind/state; configuração necessária será referenciada de modo
explícito, nunca copiada silenciosamente. Mudança durante snapshot invalida base.

Para missão sobre o próprio Hub, copiar código permitido para workspace dentro
de HiveMind/state sem recursão: excluir toda state na enumeração da origem.
Executar orquestrador por geração imutável em HiveMind/state/runtime/<generation>,
com manifesto do código Hive e do lançador compartilhado necessário, de modo que
aplicar código na origem não altere módulo já em uso. Não copiar runtime/dados
pessoais para o candidato. Gate confirma esse bootstrap e seus imports; se exigir
mais superfície compartilhada que a listada abaixo, retornar ao usuário.

Entrega contém diff/arquivos/hash base/hash candidato, testes e veredito, riscos,
arquivos removidos e plano de rollback. Imediatamente antes de aplicar, comparar
origem inteira relevante, inclusive adições/remoções, com base; divergência marca
stale e invalida aprovação. Reconciliar fora da origem, reverificar/aprovar novo
pacote. Aplicação usa staging+backup+journal por arquivo, checkpoints e recibo;
renames atômicos por arquivo não equivalem a transação atômica multiarquivo.
Falha recupera journal sem repetir efeito confirmado. Permissões/links são
revalidados no momento da escrita. Reiniciar o Hub exige etapa humana separada.

## Pausa, múltiplas abas e falhas

Proposta: fechamento do último HUD solicita pausa, seguindo o conceito atual
do Hub; fechar uma de várias janelas não fecha a operação. Lease por missão
serializa comandos mutantes, sem atribuir a uma aba o direito de matar jobs.
Troca de página/minimização só suspende render/animação se conveniente, nunca
scheduler nem presença. document.hidden não é critério de vida. Renovação
reconectada não desfaz pausa; Retomar é explícito por missão.

Baixa explícita: gravar pausing + generation fence; não despachar jobs nem iniciar
nova ferramenta; drenar a ferramenta já concedida, persistir resultado/checkpoint
e só então paused. Operação demorada pode manter ponte em drenagem; sem timeout
que mate escrita. Se houver ferramenta sem fim demonstrável, diagnosticar e
aguardar intervenção, não declarar paused. Não é possível congelar PC desligado.

Ausência de heartbeat é ambígua: registrar motivo de presença incerta, suspender
novas admissões e drenar conservadoramente, diferente de fechamento comprovado.
Timer de fundo pode ser throttled: grace configurável, eventos/erros visíveis e
checagem de conexões; não prometer ausência absoluta de falso positivo. Crash da
ponte/PC pode interromper operação: ao boot recovery_required, reconciliar jobs,
processos identificados por owner/instância e journal antes de qualquer Retomar.
Nunca matar processo alheio por PID reutilizado nem lançar duplicata por timeout.

## Encaixes mínimos fora de HiveMind — aprovados para fases dependentes

`docs/desenvolvimento.md` §5.5: “Qualquer coisa além disso: pare e pergunte.”
O usuário aprovou concretamente estas exceções; a regra não foi alterada:

1. server.py: import/registro do blueprint backend junto do Hive frontend existente.
2. server.py:_hud_watchdog: antes de _shutdown/os._exit, consultar hook único
HiveMind de request_pause_all/ready_to_exit; repetir enquanto houver tool ativo
ou checkpoint pendente. Sem Hive ativo, resultado imediato conserva autoquit.
Não mover lógica de scheduler para servidor nem mudar _shutdown/kill_all/SPEAK_Q.
Hook deve considerar perda de todos os HUDs mesmo sem beacon; ele não pode ser
um await bloqueando locks HTTP. Esse ponto é necessário porque o watchdog hoje
derruba a ponte e o runtime pessoal mata processos, incompatível com drenagem.
3. hub_runtime/assistant.py: extensão explícita de entrada/perfil Hive que delega
para launcher em HiveMind/backend/adapters, com cwd da missão/geração e política
Hive. Default bridge_command/main pessoal continua byte a byte equivalente em
comportamento; não injeta uso-pessoal.md, HUB_VAULT ou guardas de vault no Hive.
Não afrouxar guarda pessoal. Validar argumentos do opt-in antes de executar CLI.

Frontend Hive possui seu próprio lease/beacon: não precisa alterar beforeunload
do index.html nem /hud_ping e /hud_bye; a guarda do watchdog cobre último HUD.
Se investigação mostrar que preservar minimização ou verificar fechamento exige
outro hook, registrar evidência e voltar à aprovação; não ampliar genericamente.
Não modificar CLAUDE.md, navegação/provider, limites, voz, mobile ou stop/restart.
Stop/restart forçados existentes continuam interrupção abrupta explicitamente
diagnosticada; proteção a desligamento forçado do sistema não pode ser prometida.

## Fases e liberação

Toda a cadeia em sequência pelo mesmo Terra high; sem paralelismo artificial.
Cada fase entrega contrato verificável antes de liberar a próxima. Registrar
**ciclo 1/3 antes de implementar P0**; fases não criam ciclos novos.

| Fase | Resultado e arquivos permitidos | Dependência |
|---|---|---|
| P0 | Diagnóstico + contrato real dos adapters/enforcement/billing, adapters/base e testes de protocolo em fixture. Se gate falhar, registrar bloqueio sem executar missão. | Aprovação humana deste plano, três encaixes e validação real mínima incluída; P0 sem inferência. |
| P1 | Store, missions, capabilities e eventos; testes de transições, idempotência, aprovações/ciclos. | P0 comprova capacidade mínima para ambos CLIs pretendidos; limitações explícitas. |
| P2 | Workspaces, tools, delivery; testes de isolamento, stale, snapshot sem Git e rollback. | P1, política aprovada de P0. |
| P3 | Adapters completos, scheduler e lifecycle; launcher opt-in; hook watchdog; testes de pausa, quota, jobs órfãos e contabilidade. | P2; exceções explicitamente aprovadas. |
| P4 | routes, cliente/estado UI e ligação app/hive/drawers; testes integração e documentação em HiveMind/backend/README.md e atualização focada docs/runtime.md. | P3; sem redesenhar. |
| P5 | Validação real mínima em fixture incluída na aprovação do plano, regressões focadas + suíte completa; congelar manifesto candidato e registrar evidências. | P4; gate P0, quota apta e aprovação deste plano. |
| P6 | Verificador Sol6.1 high independente confere todos aceites/estado final; aprova, reprova ou deixa pendente com evidência. | P5; nenhuma escrita em código/testes. |

Testes previstos: tests/test_hivemind_{store,missions,adapters,workspaces,delivery,
scheduler,lifecycle,api}.py e tests/hivemind_backend_behavior.mjs, com fixtures
em tests/fixtures/hivemind/. Adaptar testes frontend existentes só quando contrato
afetado, preservando cobertura visual e navegação aprovada. Em P0 executam-se
somente testes da fase e a medição inicial da suíte, sem inferência.
Sem Git neste checkout: registrar manifesto por fase; não prometer commit/PR.

Reprovação final alimenta Issues e ciclos 2/3, mesma cadeia/modelo; verificador
não implementa reparos. Depois do terceiro veredito reprovado/pendente, parar e
apresentar diagnóstico, sem renomear tarefa ou reiniciar contador.
