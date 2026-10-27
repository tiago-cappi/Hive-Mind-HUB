# Plano — Centralização do Hub

Data: 08/10/2026. Referências: [PRD](prd.md), [Issues](issues.md),
[verificação](verificacao.md), `../../desenvolvimento.md` e `../../../AGENTS.md`.

## 1. Estado e limites

- Plano aprovado pelo usuário em 08/10/2026; autorizada a atualização somente
  das referências técnicas do CLAUDE.md. Orquestração do Claude Code preservada.
- Faixa da migração: **completa**, com verificação independente após implementar.
- **Ciclos utilizados: 2 de 3 — migração concluída e aprovada no ciclo 2.** Planejamento e teste de referência
  não são um ciclo de implementação.
- Ciclo 1: implementação inicial de todas as fases liberadas + verificação.
  Ciclos 2 e 3: correções + nova verificação. Fases não ganham contadores próprios.
- O contador deve ser atualizado antes da primeira alteração de implementação;
  não reinicia ao trocar agente, retomar sessão ou restaurar backup.
- Na etapa de planejamento, foram criados somente os quatro registros desta pasta.
  A execução aprovada foi iniciada em 08/10/2026, com backups antes das alterações.

Modelo previsto pelo processo: GPT-6.1 Sol (`gpt-6.1-sol`), `high` ou `xhigh`,
para planejamento e revisão; GPT-6.1 Sol como padrão de implementação.
Este registro define a seleção exigida; não certifica configuração da sessão
principal não exposta pelas ferramentas. Antes de delegar, selecionar e registrar
o modelo/esforço efetivo; comunicar eventual indisponibilidade.

## 2. Inventário confirmado nesta instalação

| Item | Situação observada | Tratamento previsto |
|---|---|---|
| Projeto atual | Código, docs, testes e venv; `.git` ausente | Raiz canônica; não inicializar Git como efeito colateral |
| `server.py:50–51,228` | Acervo fixo; transcript e relatórios derivados | Configurar acervo explicitamente, mantendo locais pessoais |
| `server.py:550,1013` | Persistente e fallback usam `cwd=VAULT` | Substituição conjunta, somente após prova de runtime |
| `server.py:68–69` | Python Kokoro e residente em pasta global | Fonte e ambiente específicos no projeto |
| `~/.claude/hooks/voice-input/speak_server.py` | Residente existente, 14.654 bytes; `KDIR` global | Copiar fonte, conferir integridade e mudar apenas resolução de caminhos |
| `~/.claude/hooks/kokoro-tts/` | Venv e dois modelos existentes, aproximadamente 354 MB somados | Registrar versões; copiar modelos com hash e recriar venv local; não copiar venv pronta |
| `~/.claude/hooks/voice-hub/` | Cópia antiga com Git e código diferente | Inventariar alterações/arquivos exclusivos antes de arquivar; não mesclar nem sobrescrever o projeto atual automaticamente |
| `launch.py` | Reutiliza porta aberta sem conferir raiz | Identificação mínima da instância antes de reutilização |
| Scripts da raiz | Caminhos absolutos e seleção ampla por nome/porta | Resolver raiz do script e limitar parada à instância identificada |
| Vault `CLAUDE.md` | Mistura instruções pessoais e técnicas históricas | Separar conhecimento pessoal de instruções operacionais; preservar pessoal como nota, centralizar parte técnica |
| Vault `.claude/skills/forestos-ops/SKILL.md` | Skill técnica histórica presente | Arquivar no projeto como histórico, sem ativá-la |
| Dois documentos técnicos em `vault/forestos/` | Documentação e modelo de dados presentes | Copiar para arquivo técnico histórico do projeto; revisar links antes de retirar originais |
| Vault `.claude/settings.local.json` | Configuração local presente | Classificar entradas pelo uso; mover só o que for específico do Hub, sem copiar permissões indiscriminadamente |
| Hook `vault/.claude/hooks/file_guard.py` e `settings.json` | Ausentes nos caminhos documentados | Não presumir proteção ativa; localizar alternativa e comprovar cobertura ou implementar proteção no escopo aprovado |
| Skill `desenvolver-hub` no caminho documentado | Ausente | Corrigir referência; não inventar uma instalação existente |
| `mobile/history.json` | Código configura histórico pessoal dentro do módulo | Inventariar arquivo/consumidores; transferir para `_agentes/historico-mobile.json` do vault com integridade |

Paths globais acima são abreviações de `C:/Users/m.rafael/.claude/hooks/`.
Documentos técnicos conhecidos no vault: `forestos/ForestOS - Documentação
Completa.md` e `forestos/Modelo de Dados ForestOS.md`. Conteúdo pessoal vizinho,
bancos experimentais, plugins do Obsidian e projetos alheios não são candidatos
automáticos à retirada. Inventário final deve localizar outros componentes
específicos do Hub sem divulgar notas ou tokens.

Consulta de porta realizada em 08/10/2026 não confirmou listener em 8765.
Isso não identifica qual cópia o usuário normalmente inicia; atalhos, tarefas
agendadas e processos deverão ser conferidos novamente no momento da transição.

## 3. Estrutura de destino proposta

```text
<projeto>/
  AGENTS.md                     regras de desenvolvimento pelo Codex
  CLAUDE.md                     referência técnica do projeto; orquestração preservada
  server.py / index.html        integração mínima, sem reescrever monolitos
  launch.py e scripts           execução da raiz canônica
  hub_runtime/                 pasta exclusiva da infraestrutura migrada
    paths.py                    resolução e validação dos caminhos
    assistant.py                configuração comum aos dois caminhos do CLI
    instructions/               instruções de uso cotidiano, voz e relatórios
    config/                     configuração explícita, exemplo sem segredos
    skills/                     apenas skills ativas do Hub, se necessárias
    agents/                     apenas agentes ativos do Hub, se necessários
    guards/                     proteção efetiva de escrita, se confirmada
    voice/
      speak_server.py           residente atual, com ajustes mínimos
      requirements.txt          dependências reproduzíveis de voz
      models/                   modelos locais, fora do versionamento
      .venv/                    ambiente recriável, fora do versionamento
    state/                      estado técnico privado, se necessário
  mobile/                      gateway existente e seu token privado
  docs/
    planos/                     planejamento, Issues e verificação
    historico/                  material técnico retirado do vault
  tests/                       testes existentes e testes da migração

<vault>/
  notas e demais pastas pessoais existentes
  _agentes/voice-hub.md         memória já existente
  _agentes/relatorios/          relatórios pessoais já existentes
  _agentes/historico-mobile.json histórico pessoal migrado
```

Nomes são contratos propostos, não pastas já criadas. Criar somente arquivos
necessários: não gerar agentes, skills ou camadas vazias para completar a árvore.
Cada arquivo tem uma responsabilidade; separação não depende de linhas. A migração
do residente existente não autoriza reescrever sua síntese/streaming. Blueprint
só se houver necessidade real de rota; este plano não exige rota de produto nova.
Uma identificação mínima local da instância pode ser necessária para os scripts.

Estado temporário do protocolo de voz pode continuar em `%TEMP%`, com dono e
ciclo de vida definidos; arquivos temporários não são fonte do projeto.

## 4. Contrato que precisa ser provado antes da integração

1. `PROJECT_ROOT` deriva da instalação atual; `VAULT_ROOT` é configuração de
   dados. Não inferir a raiz do projeto pelo vault ou por pasta global antiga.
2. Os dois caminhos do CLI recebem os mesmos caminhos, instruções operacionais,
   ambiente e proteção. O diretório de execução é controlado pelo projeto;
   notas/relatórios usam caminhos absolutos explícitos, inclusive comandos que
   anteriormente escreviam caminhos relativos ao vault.
3. A IA de uso cotidiano não recebe o fluxo de PRD/implementadores/verificador
   como obrigação em um pedido pessoal. Não basta mudar `cwd` para a raiz e
   carregar automaticamente o `CLAUDE.md` de desenvolvimento.
4. Descobrir localmente quais fontes de instrução/configuração o CLI carrega e
   escolher uma forma suportada de carregar recursos do projeto. `claude --help`
   confirmou opções como `--add-dir`, `--settings`, `--setting-sources` e
   `--append-system-prompt`; a presença de uma opção não comprova isolamento.
5. Não adotar `--bare` sem análise: o help local informa que altera autenticação
   e desliga hooks e descoberta de instruções. `--safe-mode` também desliga
   customizações. Nenhuma dessas flags é uma solução aprovada por este plano.
6. O help local também informa snapshots de system prompt em sessões retomadas.
   Comprovar se sessões antigas carregariam instruções obsoletas; testar retomada
   por ID no novo diretório. Não copiar cache nem usar `--continue` global para
   tentar restaurar várias sessões. Se continuidade não for suportada, registrar
   e obter decisão sobre uma transição com novas sessões antes do corte.
7. Guards precisam bloquear perdas de escrita de forma determinística, inclusive
   considerando ferramentas de arquivo e comandos de shell que possam escrever.
   Localizar solução existente primeiro; não copiar um hook sem prova de cobertura.
   Se isso exigir arquitetura adicional além da proteção mínima descrita, parar
   esse lote e submeter o escopo ampliado, mantendo a migração incompleta.

## 5. Fases e condições de liberação

### F0 — Aprovação e preparação do corte

Obter aprovação do plano e resolver a decisão do CLAUDE. Reconfirmar instalação
ativa, atalhos `.lnk/.vbs/.cmd`, inicialização automática e outros consumidores
dos componentes globais. Não reiniciar nem encerrar conversas em andamento
durante o planejamento. Programar a transição após turnos concluídos.

Entregáveis da implementação: `manifesto-migracao.json` com caminhos canônicos,
tipo de conteúdo, destino, tamanho/hash, consumidores, ação e estado; descrição
dos backups e passos de restauração. Não registrar valores de tokens nem notas.
Backup privado e excluído do versionamento, com destino decidido e registrado
antes de copiar arquivos mistos ou sensíveis. Validar que caminhos de retirada
pertencem aos diretórios e arquivos explicitamente aprovados.

**Liberação:** aprovação, nenhum item ambíguo destinado a remoção, baseline e
backup restaurável registrados. Checkout sem Git exige backup de arquivos;
não fingir que há commits de recuperação.

### F1 — Provas locais em ambiente descartável

Executar os testes do contrato de runtime (§4) com acervo descartável. Validar
autenticação existente, instruções, flags, acesso a dados, sessões, concorrência
de escrita e continuidade. Confirmar versões/dependências do Kokoro sem expor
credenciais nem instalar ambientes na configuração global.

**Liberação:** contrato fechado e registrado; limites e decisões pendentes
resolvidos. Teste com CLI real pode consumir uso e não deve ser repetido sem
necessidade; registrar evidência reutilizável por ciclo.

### F2 — Preparar componentes no projeto, sem retirar originais

Criar `hub_runtime/` por responsabilidade. Copiar residente e modelos, comparar
hashes, declarar dependências e recriar ambiente de voz. Consolidar instruções
operacionais e configurações específicas. Preparar proteção validada de escrita.
Copiar material técnico histórico para `docs/historico/`; preservar proveniência
e marcar ForestOS como removido. Resolver links técnicos sem reescrever notas
pessoais em massa. Preparar histórico mobile no destino sem sobrescrever um
histórico de destino já existente; conflito exige reconciliação registrada.

**Liberação:** componentes locais testáveis, backups conferidos, originais
externos disponíveis para recuperação. Não ligar dois residentes ao mesmo canal
`hub_say_*` durante a prova.

### F3 — Integração mínima e documentação corrente

Alterar apenas pontos necessários de `server.py`: caminhos/dados, residente,
configuração comum de spawn e fallback, acesso ao vault e identificação da
instância se necessária. Preservar payloads, eventos, fila, locks, watchdogs e
limites. Ajustar `mobile/config.py` para o histórico pessoal configurável.
Atualizar `launch.py`, VBS, restart e stop para resolver a raiz e conferir o
processo antes de reutilizar/encerrar a porta. Não mudar firewall ou token.

Atualizar `AGENTS.md`, `docs/desenvolvimento.md`, `docs/arquitetura.md`,
`docs/operacao.md`, `docs/voz-tts.md`, `docs/servidor-api.md`,
`docs/relatorios.md`, `docs/mobile.md` e README quando afetado. Substituir
explicitamente a antiga obrigação `cwd=VAULT`; não manter duas instruções atuais
incompatíveis. `CLAUDE.md` depende da decisão registrada em F0; se preservado,
comprovar isolamento e indicar a precedência da arquitetura corrente nos demais
documentos. Conteúdo histórico não deve parecer instalação ainda ativa.

**Liberação:** testes focados e suíte completa passando; comportamento real
essencial demonstrado antes de retirar qualquer origem.

### F4 — Corte controlado e retirada dos componentes externos identificados

Reconfirmar que não há turnos ativos. Encerrar somente instância do Hub e filhos
identificados; preservar outros consumidores globais. Aplicar configurações e
atalhos canônicos, iniciar uma ponte e um residente e conferir sua origem.

Após integridade e funcionamento comprovados, retirar do vault apenas itens
técnicos aprovados no manifesto. Preservar conteúdo pessoal do CLAUDE misto
como nota; instruções técnicas passam a residir no projeto. Conferir links e
originais um a um. Não executar exclusão recursiva de `forestos/`, `_agentes/`
ou `.claude/` do vault por conveniência.

Arquivar cópia antiga do Hub com sua história Git, alterações e arquivos
exclusivos preservados; retirar seus atalhos ativos. Não apagar ferramentas
globais compartilhadas. Se só o Hub consumir uma origem substituída, retirar
essa origem após backup; caso contrário, registrar consumidor e cessar apenas
a dependência do Hub. Backup é recuperação privada, não uma segunda fonte ativa.

**Liberação:** inventário final sem componentes específicos do Hub no vault,
uma origem ativa identificada, acervo pessoal íntegro e testes de corte aprovados.

### F5 — Verificação independente e encerramento

Agente GPT-6.1 Sol `high`/`xhigh`, sem participação na implementação, recebe
estes registros, manifesto e estado integrado. Revisa e executa o roteiro de
`verificacao.md`; não altera código/testes. Pode registrar Issues e evidências.
Ausência de prova necessária significa pendência, não aprovação.

Falhas retornam ao responsável da cadeia; ciclos 2 e 3 não ampliam o escopo.
Depois de três ciclos, parar e informar estado, falhas, recuperação e próximos
passos. Encerrar apenas com R01–R12 atendidos e aprovação independente do estado
final, incluindo retirada externa. Mudança posterior invalida aprovação anterior.

## 6. Responsáveis, dependências e paralelismo

| Lote | Responsável previsto | Dependência | Escrita permitida |
|---|---|---|---|
| Contrato e integração | Um implementador da cadeia | F0, depois F1 | `hub_runtime/`, server, scripts, mobile config e testes da integração, sequencialmente |
| Histórico técnico | Implementador separado, se trouxer ganho | Manifesto F0 aprovado | Somente novos arquivos em `docs/historico/`; sem tocar vault ou docs correntes em paralelo |
| Documentação corrente e corte | Mesmo responsável da integração | F3 testada | Docs correntes e ações externas explicitamente enumeradas |
| Revisão final | Verificador independente | F4 e estado integrado | Somente registros de verificação/Issues; código e testes apenas leitura |

Fases são dependentes. Não criar agentes apenas para aumentar paralelismo.
Material histórico e preparação de voz podem avançar em paralelo somente com
arquivos disjuntos, entradas aprovadas e ausência de dependência; integração e
corte ficam na cadeia única. Nunca dois agentes escrevendo no mesmo arquivo.

## 7. Recuperação

Antes do corte, testar restauração dos arquivos de configuração/código em cópia
descartável. Registrar raiz, arquivos, hashes e versões do estado anterior.
Se o corte falhar: bloquear novas solicitações, encerrar apenas nova instância
identificada, restaurar fontes/configuração/atalhos antigos e iniciar uma única
instância anterior. Não restaurar o vault inteiro sobre conteúdo pessoal novo.

Dados pessoais alterados depois do backup exigem reconciliação individual:
preservar novas notas, transcript, relatórios e turnos mobile; não substituir
pela cópia antiga. Não apagar sentinelas nem enviar `__quit__` a um residente
compartilhado sem verificar posse. Recuperação não reinicia o contador de ciclos.

Permissões de escrita fora do projeto são avaliadas no momento da ação concreta.
Enumerar cada origem/destino e executar primeiro o trabalho seguro dentro do
projeto. Não usar bloqueio de uma ação externa para deixar o restante indefinido.

## Encerramento em08/10/2026

F0inventário/backup, F1provas, F2preparação local, F3integração/documentação,
F4corte e F5verificação concluídos. A reprovação do ciclo1 gerou correções
no ciclo2, aprovado por GPT-6.1 Sol xhigh independente. Não executado ciclo3.
Relatórios dos dois ciclos preservados;220testes passaram na implementação
e na revisão independente. Instância reiniciada da raiz canônica.

Nota de limite: retomada real comprovada para IDs novos; sessões antigas não
são importadas automaticamente. Guarda cooperativa cobre sessões do Hub, não
escritores externos. Dados novos do transcript preservados e prefixo original
validado. Backups privados continuam disponíveis; recuperação exige reconciliar
dados pessoais recentes, sem restaurar o vault inteiro por cima deles.
