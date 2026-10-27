# PRD — Hive Mind como terceira página do Hub

> **Status em 21/10/2026: CONCLUÍDA** — aprovada na verificação independente do ciclo 7 (13/10/2026). Este arquivo é registro histórico do processo e pode descrever intenções já superadas; a referência do código atual está em `docs/hivemind/README.md`. As capturas de QA foram movidas para `.qa-arquivo/2026-10-10_hivemind-frontend-hub/`; caminhos `qa*/` citados abaixo são relativos a essa pasta.

Data: 10/10/2026. Faixa: completa. Ciclo: 1 de 3, em andamento; referência visual atualizada pelo usuário.
Planejamento: agente GPT-6.1 Sol, high. Este registro não é evidência de implementação.

## Objetivo e decisões autorizadas

Portar HiveMind/prototipo/Hive Mind.dc.html (origem atual: Protótipo Hive Mind Desktop/Hive Mind.dc.html) para a terceira página do Hub junto a Claude Code e Codex. Preservar visual 2D mostarda, gavetas com todas as informações, relações/fluxos, simulação interativa e abelhas em três camadas PNG do bee-animation recém-adicionado. Primeiro frontend; backend Hive em tarefa futura.

O usuário aprovou o roteiro planejamento → implementação → verificação independente e autorizou prosseguir. Terra não está disponível no mecanismo atual; autorizou explicitamente “Autorizar GPT-5.6 Sol somente nesta implementação”. A exceção não modifica AGENTS.md/docs/desenvolvimento.md. O usuário autorizou especificamente “Autorizar os seis ganchos” em index.html, conforme §5.5 do processo. Plano liberado para execução dentro desse escopo.

Todo frontend, blueprint e backend futuro Hive ficam na pasta raiz exata HiveMind/. Protótipo inteiro será movido para HiveMind/prototipo; arte e prévia preservadas. Documentação processual em docs/planos e testes em tests seguem as convenções do Hub.

## Comportamento esperado

O minimalista terá Claude Code, Codex e Hive Mind. Hive é uma página de demonstração separada do provedor IA selecionado. Entrar conserva provedor, sid, modelos/esforços, rascunhos e gavetas do Hub, sem criar sessão nem consumir MAX_TABS. Retornar a Claude/Codex segue as regras atuais: se faltar sessão desse provedor, a navegação existente pode criá-la dentro do teto de seis. Painel completo continua a experiência Claude original.

Hive começa no cenário Missão, com identificação persistente “Demonstração simulada · backend Hive Mind pendente”. Dados e permissões de ferramentas descritos pertencem ao exemplo. Não consulta agentes locais, e-mails, cadastros, planilhas ou vault. Envio de texto apenas alimenta a simulação; durante missão em curso, registra texto e explica que não haverá execução/filas reais.

Troca de página é bloqueada em listen. Mic pendente que termina depois de entrar no Hive libera tracks e não cria MediaRecorder. Turnos Claude que já chegaram à transcrição/processamento/fala continuam no sid e opções originais. Eventos mobile atualizam o espelho em segundo plano, sem tomar foco.

Simulação suspende enquanto Hive está oculta ou document.hidden, conservando fase/progresso/decisões/rascunho/tempo restante. Retoma somente se estava rodando; pausa manual persiste. Tempo oculto não pula aprovação. Animações param com página oculta. Reduzir movimento afeta asas, fluxos e transições, mantendo informação textual legível.

## Requisitos e aceitação

| ID | Requisito | Critério verificável |
|---|---|---|
| R01 | Terceira página | Abre/fecha Hive sem modificar provider, sid ou quantidade de abas; abre com seis abas. Claude/Codex continuam selecionáveis conforme regras atuais. |
| R02 | Simulação explícita | Aviso de simulação/backend pendente sempre visível; agentes, ferramentas, missão, conversa e entrega têm contexto de demonstração; nenhum vínculo a agente real. |
| R03 | Fidelidade visual | Comparar 1440×900 e 1920×1080: fundo #B8860B, papel #F1EDE4, preto, fluxo #6500C9, malha/células hexagonais, Rainha central, operárias/subagentes. Gavetas alcançáveis em 1280×800 sem conteúdo irrecuperável. |
| R04 | Gaveta esquerda | Abre/fecha; lista/contadores. Rainha mantém Visão geral/Tarefas/Relações. Operárias/subagentes mantêm Visão geral/Tarefas/Skills/Ferramentas/Relações, textos, progresso, origem/destino, permissões descritivas e navegação entre relações. |
| R05 | Gaveta direita | Mantém Plano/Responsabilidades/Conexões/Entrega, sete etapas, progresso/estado, simular/pausar/continuar/próxima etapa/reiniciar, legendas, aprovação/ajuste e detalhes de falha. |
| R06 | Conversa e entrega | Gaveta inferior recebe texto sem rede IA, registra eventos e decisões simulados. Entrega abre/fecha com 23 pedidos e quatro divergências (três após ajuste), explicação de simulação e nenhuma gravação de relatório real. |
| R07 | Fluxos interativos | Célula seleciona agente/abre detalhes; mostrar/ocultar subagentes funciona; conexões mostram origem/destino/estado/explicação. Preservar tarefa/execução/espera/resultado/entregue/falha, sentidos ida/volta e pulsos simples/duplos. |
| R08 | Cenários e CRUD simulado | Missão/Colmeia vazia/Etapa com falha; aprovação continua, ajuste retorna à aprovação, retry recupera falha. Adicionar exige nome até 16 caracteres e especialidade até 40, ocupa três slots máximos; só adições são removíveis. Nenhum efeito em sessões IA. |
| R09 | Abelhas PNG | Asa-esquerda/asa-direita/corpo-sem-asas nessa ordem, tela alinhada 1254×1254. Preservar pivôs/cadências/sete estados bee-animation e tamanhos 64/56/40/26 px. Nenhuma abelha indica atividade real. |
| R10 | Movimento/lifecycle | Toggle e preferência do sistema reduzem movimento decorativo. Página oculta pausa timer/animações sem avançar fase; pausa manual persiste. Sem listeners/timers/observadores duplicados. Galáxia Codex inativa sob Hive. |
| R11 | Isolamento de ações | Enter/Espaço/Esc em Hive não abrem mic nem chamam /ask, /stt, /abort, /session_reset, /speak. Controles ocultos do Hub inacessíveis. Inputs tratados como texto seguro. |
| R12 | Continuidade | Troca recusada em listen; mic diferido descartado/liberado. STT anterior continua com modelo/esforço/sid originais. Mobile não muda aba ativa nem página Hive. Retorno conserva preferências/rascunhos/gavetas reais. |
| R13 | Encaixe modular | HiveMind/frontend com blueprint estático, ES modules/CSS por responsabilidade. Sem support.js/DCLogic/React/sc-for/sc-if/CDN JS/bundler/dependência nova. Rotas não executam IA nem leem dados pessoais. |
| R14 | Invariantes/conclusão | MAX_TABS/MAX_SESS seis; binding 127.0.0.1, SPEAK_Q, guardas/payloads intactos. Testes pertinentes, comportamentais e suíte tests passam; QA visual e verificador independente aprovam estado final por R01–R14. |

## Fora de escopo

Backend/execução/orquestração Hive; descoberta de agentes reais; autenticação/APIs/modelos Hive; persistir missões/agentes; criar recursos externos; acessar vault; mobile Hive; alterar backend Claude/Codex, voz/guardas/limites; refatorar monolitos; modificar CLAUDE.md; editar/remover o conteúdo do protótipo ou prévia bee-animation. A movimentação integral para HiveMind/prototipo está expressamente autorizada.

## Fontes e limites

AGENTS.md e docs/desenvolvimento.md: processo. CLAUDE.md, docs/arquitetura.md e docs/servidor-api.md: invariantes (ForestOS histórico). docs/frontend.md: HUD; docs/codex-frontend.md: navegação recente. Código prevalece sobre passagens históricas.

Protótipo Hive Mind.dc.html: Component.buildPhases/go/status/renderVals, templates de gavetas e linksLayer/getRoutes. Rig: bee-animation/README.md, bee.js, bee.css; assets/operaria-animacao e rainha-animacao. Hive Mind v1.dc.html não é a referência escolhida. Levantamento por leitura; comparação visual/testes de integração ainda não executados.

## Atualização aprovada de fidelidade — referência substituída pelo usuário

Em10/10/2026 às17:15:26BRT, o usuário substituiu os arquivos do protótipo e pediu fidelidade exata ao novo desenho: sombras, degradês, relevo/profundidade mantendo2D e gavetas menos monocromáticas. Esta atualização prevalece sobre o inventário visual anterior. Ciclo permanece1/3; não é reprovação nem reinício da tarefa.

Referência vigente HiveMind/prototipo/Hive Mind.dc.html,134879bytes, SHA25603B05ACDDD71DA6C6C2E81D3AE14ADC6B08D4EBB340E44C1CE3D41A92CF8DAD6. Inventário atual seis arquivos no adendo do plano. Inventário21/21 anterior/capturasqa anteriores são históricos; não restaurar versão antiga nem recriar arquivos removidos pela substituição humana. Protótipo vigente é somente leitura.

R03 agora exige **igualdade de composição/tipografia/layout/estados/gradientes/biséis/sombras/fluxos** com o HTML novo, e não semelhança geral de paleta. Requisitos R01–R14 de funcionamento, isolamento, frontend primeiro e invariantes permanecem. R04/R05/R06 incluem hierarquia visual completa das novas gavetas, campos/badges/actions/headers e layout do protótipo. Critérios V01–V08 no plano complementam R03/R07/R09/R14, com verificação por capturas pareadas e métricas locais.

A referência nova usa abelhas SVG e não contém o bee-animation/PNG antigo. A coordenação perguntou preferência opcional PNG previamente autorizadas versus SVG novo; preservar PNG como preferência até resposta. R09 será interpretado conforme decisão explícita, sem substituir silenciosamente a arte nem alegar igualdade dos pixels das abelhas casoPNG. Restante do desenho segue o novo HTML rigorosamente. Mudar proporções/tamanhos dos personagens deve seguir decisão da coordenação e ser explicitado no relatório.

## Registro de implementação — 12/10/2026

A implementação do ciclo 1 foi executada por **GPT-5.6 Terra, high**, conforme
AGENTS.md e a escolha permanente do usuário em 12/10. A menção anterior a uma
exceção Sol5.6 permanece como histórico de uma etapa anterior; não descreve o
implementador deste estado candidato.

O candidato conserva o rig PNG autorizado (64/56/40/26 px) e o aviso de
simulação/backend pendente. A exceção é limitada aos personagens; composição,
tipografia, gavetas, HUD, rotas, gradientes, biséis, sombras e estados foram
portados do protótipo vigente. Backend/agentes reais continuam fora de escopo.
O candidato aguarda a verificação independente obrigatória antes de qualquer
declaração de conclusão.

Menor mudança: corrigir diretamente render/geometry/drawers/styles Hive recém-criados, consolidar/remover layout.css redundante, usar navegação Hive com tipografia/underline source, preservar guardas/contratos/session/backends já encaixados. Sem redesign do Hub, novos sistemas, CSS remendado em cascata ou implementações simplificadas duplicadas. Antes do aceite, testes, novas capturas da referência atual e verificador independente do estado final.
