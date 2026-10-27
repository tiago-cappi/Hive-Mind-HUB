# PRD — backend HiveMind

> **Status em 21/10/2026: CONCLUÍDA** — aprovada na verificação independente do C4 (20/10/2026, R01–R15). Este arquivo é registro histórico do processo e pode descrever intenções já superadas; a referência do código atual está em `docs/hivemind/README.md`. As ressalvas do C4 seguem como EQ-11 em `../2026-10-20_hivemind-escala-equipe/issues.md`.

19/10/2026 · faixa completa · plano **aprovado pelo usuário em 19/10/2026**
(“Autorizo esse plano”), incluindo os três encaixes e validação real mínima.
Nova tarefa: ciclo **1/3**, P0 concluído e P1–P5 liberados; verificação final pendente. O frontend
aprovado no ciclo 7 da tarefa anterior continua preservado; seu histórico não é
reiniciado nem transferido para este contador.

## Objetivo e primeira entrega

Transformar a demonstração Hive em uma equipe real para missões de software em
projetos locais diferentes. A primeira entrega deve concluir uma missão pequena,
do pedido ao pacote aprovado e sua incorporação controlada na origem. Queen
esclarece e propõe plano/equipe; usuário aprova; operárias trabalham em área
separada; verificador independente avalia; usuário aprova o pacote final exato.

O desenho permite capacidades futuras de pesquisa, relatórios, planilhas,
documentos, arquivos, prospecção, WhatsApp e agenda. Esses conectores não serão
implementados agora. A configuração do produto não depende do SDK nem das
ferramentas multiagente deste chat.

## Requisitos e aceites

| ID | Comportamento obrigatório e evidência de aceite |
|---|---|
| R01 | Contas de assinatura Codex e Claude Code já locais, sem chaves/API, login, instalação ou atualização nesta etapa. Diagnóstico sanitizado distingue instalado, autenticado, compatível e apto ao modelo. Não lê/copia tokens nem imprime identidade pessoal. Caminho que possa gerar cobrança extra não é habilitado sem prova de elegibilidade; ausência dessa informação bloqueia o modelo, sem promessa falsa de gratuidade. |
| R02 | Modelo e esforço por Queen, operária, subagente e verificador, inclusive mistura GPT/Claude. Defaults desejados Queen/verificador GPT-6.1 Sol high e operárias eficientes Luna/Terra configuráveis. Catálogo não prova direito de uso; registrar seleção, catálogo e confirmação separadamente. Nome/effort inválido, indisponível ou quota gera erro explícito; nunca fallback/substituição automática. Não prometer que nomes do picker do aplicativo existem nos CLIs. |
| R03 | Queen só analisa/esclarece antes da aprovação humana de uma versão imutável do plano/equipe, com projetos, capacidade, arquivos/escopo, modelos/efforts, dependências e aceites. Teste prova que não há trabalho gravável pré-aprovação e aprovação obsoleta é rejeitada. Mudança de escopo exige nova aprovação; correção dentro do escopo segue automaticamente. |
| R04 | Abelhas permanentes configuráveis pelo usuário; temporárias pertencem ao plano aprovado e saem da escala ativa ao encerrar, preservando identidade, eventos, resultados e custos/uso conhecidos no histórico. Cada abelha executando aponta para agente/processo real e sessão própria. Roster configurado ocioso não será apresentado como processo em execução. |
| R05 | Default de duas operárias simultâneas, total compartilhado por workers, subagentes e verificador; Queen tem slot separado de coordenação, sem executar trabalho de worker para contornar limite. Limite configurável e persistido. Dependências ou arquivos compartilhados serializam; somente lotes independentes/disjuntos paralelizam. Agentes nativos aninhados não podem contornar o scheduler. Teste conta jobs reais, inclusive falha/reconexão. |
| R06 | Desenvolvimento sempre separado da origem: worktree para projeto Git elegível; snapshot/cópia explícita para checkout sem Git. Este Hub não possui .git; não inicializar Git. Manifesto/hashes, exclusões de segredos, detecção de mudança externa e rollback acompanham a entrega. Testes tentam escrever na origem por caminho absoluto/symlink/junction/shell e devem ser impedidos; cwd/cópia sozinhos não são sandbox. |
| R07 | Verificador com contexto/sessão independente, modelo/effort configurável adequado, sem participação na implementação. Pode ler e executar checks aprovados em cópia de verificação; não pode modificar código/testes. Cache, temporários e relatórios de teste ficam fora da árvore do candidato. Relatório por aceite: passou/falhou/não verificável. Critério necessário pendente impede aprovação. |
| R08 | Três ciclos totais por missão por padrão, UI ajustável de modo explícito e auditado. Ciclo 1 implementação+verificação; seguintes correções+nova verificação. Não zerar ao retomar, trocar modelo/agente ou dividir fases; não reduzir abaixo do ciclo corrente. Ao teto reprovado/pendente, diagnóstico e aguardar usuário; sem quarto ciclo automático. Uso desconhecido aparece desconhecido, nunca zero; não inventar preço monetário para assinatura. |
| R09 | Só incorporar após aprovação do verificador E aprovação humana do pacote final exato, identificadas pelo hash do candidato/manifesto. Origem alterada invalida autorização anterior: reconciliar em área separada, reverificar e reapresentar. Aplicação transacional recuperável, sem overwrite silencioso, remoções limitadas ao pacote e rollback verificável. Não sobrescrever dados pessoais/runtime. |
| R10 | Trocar Hive por Claude/Codex ou minimizar não pausa missão. Fechar o Hub solicita pausa: bloqueia novos jobs/ferramentas, deixa escrita em curso terminar e grava checkpoint antes de paused. Proposta multijanela: considerar o último HUD aberto, preservando o conceito atual do Hub. Nunca matar árvore CLI durante escrita para fingir pausa. Retomar exige abrir Hub e clicar Retomar naquela missão; reload, reboot e crash nunca retomam trabalho automaticamente. |
| R11 | Lease de comando por missão evita comandos/jobs duplicados; presença é acompanhada globalmente entre os HUDs. Fechamento informado e perda de conexão são motivos distintos. beforeunload/sendBeacon é melhor esforço; TTL não distingue fechamento, suspensão e rede. Presença incerta impede novo despacho e drena com diagnóstico explícito, sem alegar que o navegador comprovou fechamento. Reabertura não cancela pausa pendente. Caso não alcance ponto seguro, fica pausing com motivo, sem kill por timeout. |
| R12 | SQLite + event log duráveis, sequência/cursor e comandos idempotentes. Reinício identifica jobs órfãos, registra recovery_required e conserva contador/artefatos; não repete ferramenta/entrega ambígua. Estados e permissões validados no backend; render/clock nunca decide execução. Testes interrompem entre gravação de intenção e resultado e conferem recuperação sem duplicar efeito. |
| R13 | Frontend aprovado 2D/mostarda/rig PNG preservado. Somente campos/controles necessários a projeto, contas/modelos, aprovações, missão, equipe, pausa/retomada e entrega reais. Estado/eventos reais alimentam abelhas; sem progresso/contagem fabricados. Percentual só de unidades concluídas conhecidas, senão atividade indeterminada. Demo, se mantida, tem entrada explícita separada e nunca controla missão real. |
| R14 | Código/estado/dados Hive sob HiveMind/, testes em tests/, processo em docs/planos/. Flask continua 127.0.0.1:8765, sem exposição mobile. MAX_SESS/MAX_TABS=6 e SPEAK_Q intactos; Hive não é provider nem ocupa sessões pessoais. Execução passa por extensão opt-in de hub_runtime.assistant sem prompt/vault/guardas pessoais herdados. Regressão demonstra caminhos Claude/voz/mobile existentes preservados. |
| R15 | Gate de compatibilidade local sem inferência antes de habilitar: schemas da versão instalada, inicialização, estado sanitizado da conta, catálogo e controle de ferramentas/pausa/billing. A aprovação deste plano inclui validação em fixture isolada: um smoke curto por CLI habilitado e uma missão mínima ponta a ponta, consumindo franquia das assinaturas, sem APIs ou créditos extras. Não inferir se P0/quota falhar nem repetir livechecks válidos com hash/protocolo estáveis. Integração sobre o próprio Hub não reinicia serviço automaticamente: aplicação e reinício são etapas aprováveis distintas. |

## Estados visíveis

Missão: draft → clarifying/planning → awaiting_plan_approval → ready → running
→ verifying → awaiting_delivery_approval → applying → completed. Caminhos
adicionais: awaiting_user, correcting, quota_wait, failed, pausing, paused e
recovery_required. Estado resume_allowed não significa retomada automática.
Job distingue queued/running/tool_active/draining/completed/failed/unknown.
Correções mantêm o mesmo mission_id e incrementam ciclo de forma transacional.

## Fora do escopo

Backend Codex global/voz, novos providers do Hub, redesenho visual, acesso remoto,
API paga, conectores de negócio, login, instalação/upgrade CLI, alteração de
CLAUDE.md, implantação/publicação automática e promessa de continuar com o PC
desligado. Configuração de modelos deste produto não muda os modelos exigidos
pelo processo de desenvolvimento deste backend.
