# Issues — Centralização do Hub

Data: 08/10/2026. Estado geral: **migração concluída e aprovada**.
**Ciclos utilizados: 2/3**. Verificador independente aprovou o ciclo2.

Implementação pela sessão principal; arquivo histórico por agente delegado
GPT-6.1 Sol, high. Modelo/esforço da sessão principal não são expostos pelas ferramentas.
Verificador independente: GPT-6.1 Sol, xhigh, sem participação na implementação.

| ID | Trabalho | Requisitos | Dependências | Responsável | Estado |
|---|---|---|---|---|---|
| MIG-01 | Aprovar plano e resolver tratamento do CLAUDE do projeto | R04,R05,R12 | — | Usuário / sessão principal | Concluído; aprovado no ciclo2 |
| MIG-02 | Inventariar consumidores, instalação ativa, atalhos e cópia antiga; preparar manifesto e backup restaurável | R01,R06,R10,R11 | MIG-01 | Implementador da cadeia | Concluído; aprovado no ciclo2 |
| MIG-03 | Provar carregamento de instruções, autenticação e acesso explícito ao acervo nos dois caminhos do CLI | R04,R05 | MIG-02 | Implementador da cadeia | Concluído; aprovado no ciclo2 |
| MIG-04 | Provar retomada/isolamento de sessões e definir transição caso contexto antigo não seja portável | R06,R08 | MIG-03 | Implementador da cadeia | Concluído; aprovado no ciclo2 |
| MIG-05 | Localizar e validar proteção efetiva de notas concorrentes; centralizar ou implementar mínimo necessário | R07 | MIG-03 | Implementador da cadeia | Concluído; aprovado no ciclo2 |
| MIG-06 | Centralizar residente, modelos e ambiente reproduzível de voz | R03,R08 | MIG-02 | Implementador da cadeia | Concluído; aprovado no ciclo2 |
| MIG-07 | Separar instruções pessoais/técnicas e arquivar documentação/skill histórica do vault no projeto | R01,R02,R04,R12 | MIG-02,MIG-03 | Implementador de histórico; corte pela cadeia | Concluído; aprovado no ciclo2 |
| MIG-08 | Integrar caminhos de runtime, dados, spawn persistente e fallback com alterações mínimas | R03,R04,R05,R07,R08,R09 | MIG-03,MIG-04,MIG-05,MIG-06 | Implementador da cadeia | Concluído; aprovado no ciclo2 |
| MIG-09 | Migrar histórico pessoal mobile com preservação e configuração explícita | R06,R08,R09 | MIG-02,MIG-08 | Implementador da cadeia | Concluído; aprovado no ciclo2 |
| MIG-10 | Corrigir identificação, inicialização, parada, reinício e atalhos canônicos | R01,R09,R10 | MIG-08 | Implementador da cadeia | Concluído; aprovado no ciclo2 |
| MIG-11 | Atualizar documentação corrente e referências substituídas | R12 | MIG-07,MIG-08,MIG-09,MIG-10 | Implementador da cadeia | Concluído; aprovado no ciclo2 |
| MIG-12 | Executar testes focados, suíte e provas reais em acervo descartável antes do corte | R03–R11 | MIG-08,MIG-09,MIG-10,MIG-11 | Implementador da cadeia | Concluído; aprovado no ciclo2 |
| MIG-13 | Efetuar corte, conferir dados, retirar origens técnicas aprovadas e arquivar cópia antiga sem perder história | R01,R02,R06,R10,R11 | MIG-07,MIG-12 | Implementador da cadeia | Concluído; aprovado no ciclo2 |
| MIG-14 | Revisar estado final de forma independente e decidir aceite por R01–R12 | Todos | MIG-13 | Verificador independente | Concluído; aprovado no ciclo2 |

## Contratos de execução

- **MIG-02:** listar caminhos exatos antes de qualquer ação externa; hashes,
  consumidores e restauração são obrigatórios. Ausência de listener não prova
  que os atalhos estão corretos. Preservar alterações da cópia antiga com Git.
- **MIG-03/04/05:** provas em diretório descartável; não gastar uso tentando
  repetidamente resolver uma arquitetura ainda indefinida. Atualizar contrato
  do plano com resultados. Não usar guarda apenas em prompt como solução.
- **MIG-06:** `hub_runtime/voice/`, dependências e caminhos locais; manter
  protocolo e parâmetros de voz atuais. Modelos têm hash; venv é recriada.
- **MIG-07:** docs técnicas e skill ForestOS são históricas. Notas e estado
  pessoais não entram no arquivo técnico. Conteúdo misto exige separação e
  verificação, não remoção integral da pasta de origem.
- **MIG-08/09:** `server.py`, `hub_runtime/`, `mobile/config.py` e testes;
  preservar contratos públicos. Remover somente código/caminhos substituídos
  pela migração. Histórico de destino existente exige reconciliação, não overwrite.
- **MIG-10:** scripts e identificação da instância; não matar processo arbitrário
  porque escuta 8765 ou contém `python`/`speak_server` no nome.
- **MIG-11:** arquivos enumerados em F3. Não sobrescrever PRD/Issues históricos
  existentes nem alterar orquestração do Claude Code por causa do Codex.
- **MIG-12/13:** usar roteiro de verificação, preservar dados criados durante
  a transição e confirmar cada retirada. Retirada externa bloqueada fica
  pendente; não marcar R02/R11 atendidos apenas com cópia interna pronta.
- **MIG-14:** modelo e esforço explícitos; não participou das mudanças; não
  altera código/testes. Reprovações vão para o responsável original.

## Reprovações e correções

Ciclo 1 implementado. Ainda sem veredito independente. Durante a preparação,
o ensaio sem bypass revelou lock após recusa manual: PostToolBatch foi incorporado
ao cleanup e ganhou teste de regressão. Ensaios seguintes e 206 testes passaram.
O corte passou na conferência de integridade. Nenhuma reprovação independente registrada.

Para cada falha, acrescentar: ID da Issue, ciclo, requisito/critério afetado,
arquivo/localização, passos de reprodução, esperado, observado, evidência,
correção necessária, responsável e status. Não apagar resultados anteriores
nem criar ciclo por fase. Máximo global: implementação inicial + duas correções.

## Revisão independente — ciclo 1 reprovado / ciclo 2 iniciado

Parecer: [revisao-independente-ciclo-1.md](revisao-independente-ciclo-1.md).
Implementação inicial conta como ciclo1; correções abaixo compõem ciclo2.

| Finding | Correção necessária | Responsável | Estado |
|---|---|---|---|
| REV-C1-01 | Registrar fallback e matar árvore em cancelamento/timeout; não iniciar fallback após abortar persistente | Sessão principal | Corrigido e aprovado no ciclo2 |
| REV-C1-02 | Publicação recuperável do lock quando processo morre antes do owner | Sessão principal | Corrigido e aprovado no ciclo2 |
| REV-C1-03 | Cleanup só libera lock do tool_id/owner correspondentes | Sessão principal | Corrigido e aprovado no ciclo2 |
| REV-C1-04 | Serializar inicialização antes de criar ponte/residente | Sessão principal | Corrigido e aprovado no ciclo2 |
| REV-C1-05 | Arquivar protótipo específico WinForms e seus launchers após conferir consumidores/hashes | Sessão principal | Corrigido e aprovado no ciclo2 |
| DOC-R06 | Distinguir retomada provada de IDs novos da transição das conversas anteriores | Sessão principal | Corrigido e aprovado no ciclo2 |

Falha transitória WinError145 na primeira suíte independente também fica registrada;
segunda suíte passou206/206, sem atribuição de causa externa não comprovada.

### Implementação do ciclo2

Popen fallback rastreado, geração de cancelamento e kill de árvore no timeout;
slots serializados respeitam o teto6. Lock de startup e lock de vida/encerramento
da ponte; shutdown aguarda o residente próprio antes de ceder o canal. Guardas
publicadas completas por rename, release casado com tool/owner e retries limitados.
Protótipo e fonte original do residente sem consumidores arquivados; ferramentas
genéricas preservadas. Política R06 explicitada no runtime. Teste de esforço
existente teve mocks adaptados a Popen sem remover critérios/asserções.
Suite220passed13.27s;51testes focados passaram6.12s no ambiente do usuário.

## Aceite final

[Revisão independente do ciclo2](revisao-independente-ciclo-2.md): APROVADO,
R01–R12 atendidos nos limites documentados. Suíte independente220passed13.08s,
saída0; implementação220passed13.27s. Nenhuma reprovação aberta. Contador final2/3.
Reprovações/limitações anteriores acima são histórico preservado, não pendências
da implementação final. Fontes/código não foram alterados após esse parecer.
