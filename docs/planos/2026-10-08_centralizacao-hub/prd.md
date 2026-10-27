# PRD — Centralização do projeto e separação do vault

Data: 08/10/2026. Faixa da implementação: **completa**.
Estado: plano aprovado em 08/10/2026; implementação no ciclo 1.
Decisões do usuário: projeto centralizado; vault exclusivamente pessoal;
relatórios visuais pessoais permanecem no vault.

## 1. Objetivo

Centralizar os componentes específicos do Hub na pasta atual do projeto e tratar
o vault do Obsidian como acervo de notas, ideias, memória e relatórios pessoais.
O Hub deve continuar conversando por voz e texto, acessando o acervo e atendendo
o celular, sem depender de código, documentação técnica, skills ou agentes
específicos do projeto instalados no vault ou na cópia antiga do Hub.

Raiz canônica:
`C:/Users/m.rafael/Desktop/Projetos Pessoais/core-voice-hub-v2-main/core-voice-hub-v2-main`.
Acervo atual: `C:/Users/m.rafael/Documents/Obsidian Vault`.
Esses caminhos descrevem esta instalação; código novo deve resolver o projeto
a partir dos próprios arquivos e receber o caminho do acervo por configuração.

## 2. Divisão acordada

| Conteúdo | Destino |
|---|---|
| Código, testes, dependências declaradas, scripts de execução e configuração do Hub | Projeto |
| Documentação técnica, PRDs, planos, Issues e verificações | Projeto |
| Instruções operacionais da IA do Hub, skills, agentes e hooks específicos | Projeto |
| Modelos locais e ambiente de voz específico do Hub | Pasta própria dentro do projeto, fora do versionamento |
| Estado técnico, logs de diagnóstico, token e configuração do gateway | Projeto, em arquivos privados quando necessário |
| Notas, ideias, informações pessoais e memória das conversas | Vault |
| Transcript `_agentes/voice-hub.md` | Vault, preservando o caminho atual |
| Relatórios pessoais `_agentes/relatorios/` e seus recursos | Vault, preservando o caminho atual |
| Histórico pessoal do celular | Vault; migrar o JSON atual com integridade comprovada |
| Conteúdo pessoal associado ao ForestOS antigo | Vault; não reativar a funcionalidade removida |
| Material técnico histórico do ForestOS específico do Hub | Arquivo histórico dentro do projeto, sem ativação automática |

Python, Chrome, a instalação e autenticação do CLI e caches genéricos dos
fornecedores podem permanecer no sistema. Centralizar o projeto não significa
copiar toda a instalação do Claude/Codex, seus ambientes globais ou credenciais.
Nenhum componente específico do Hub pode depender desses locais como única
fonte de código ou de instruções. Caches de sessão do fornecedor não substituem
a memória pessoal persistida no vault.

## 3. Requisitos e critérios de aceitação

| ID | Requisito | Aceitação verificável |
|---|---|---|
| R01 | Uma raiz canônica para o projeto | O manifesto lista origem, destino, responsável e estado de cada componente identificado; nenhum componente ativo do Hub usa a cópia antiga como fonte |
| R02 | Vault exclusivamente pessoal | Inventário final dos arquivos técnicos conhecidos confirma retirada dos componentes específicos do Hub; itens ambíguos foram classificados individualmente; notas pessoais foram preservadas |
| R03 | Código e ambiente de voz centralizados | O processo de fala usa fonte, modelos e Python do projeto; a configuração não aponta para `~/.claude/hooks/voice-input` ou `kokoro-tts`; recriação do ambiente está documentada |
| R04 | Separar instruções operacionais de instruções de desenvolvimento | A IA de uso cotidiano recebe instruções do projeto e acesso explícito ao acervo, sem iniciar o pipeline de desenvolvimento em um pedido de nota ou relatório; nenhum pedido depende de skill/configuração do vault |
| R05 | Diretório de execução independente do acervo | Os caminhos persistente e fallback do CLI usam a mesma configuração operacional do projeto, acessam notas e relatórios por caminho explícito e funcionam com um acervo de teste sem `.claude`, `CLAUDE.md`, skills ou código |
| R06 | Preservar conteúdo e memória | Manifesto e hashes comprovam preservação dos arquivos pessoais afetados; transcript e relatórios mantêm caminhos; histórico mobile conserva registros, ordem e formato; nenhuma sessão é prometida como retomável sem teste |
| R07 | Evitar perda por escrita concorrente | Proteção efetiva contra duas sessões alterando a mesma nota é testada com disputa real em acervo descartável; não basta citar um hook ausente ou instruir o modelo a ter cuidado |
| R08 | Preservar interfaces e comportamento | Testes existentes e testes da migração passam; voz, texto, streaming, cancelamento, troca de modelo/esforço, relatórios e mobile são exercitados conforme `verificacao.md` |
| R09 | Preservar isolamento e segurança | Ponte continua em `127.0.0.1:8765`; gateway mantém autenticação e whitelist; teto de sessões e fila única de fala permanecem; nenhum token/conteúdo pessoal aparece nos registros compartilháveis |
| R10 | Execução e atalhos identificáveis | Inicialização comprova a raiz da ponte antes de reutilizar a porta; parada/reinício atingem somente a instância identificada e seus filhos; outro ocupante da porta não é encerrado nem aceito como Hub |
| R11 | Recuperação e retirada segura | Backup e restauração dos componentes alterados têm procedimento validado; originais externos só são retirados após integridade, testes e consumidores conferidos; conteúdo técnico substituído não fica ativo em duplicidade |
| R12 | Documentação coerente | AGENTS, desenvolvimento, arquitetura, voz, operação, API e relatórios descrevem o estado final; referências antigas ficam claramente históricas; decisão sobre o CLAUDE do projeto foi resolvida |

## 4. Fora do escopo

- Trocar o motor de conversa do Hub de Claude para GPT. GPT continua sendo a
  escolha do fluxo de desenvolvimento pelo Codex.
- Reescrever `server.py` ou `index.html`, redesenhar interface ou adicionar
  funcionalidades de produto sem relação com a separação das pastas.
- Reconstruir o ForestOS, apagar notas/estado pessoal antigo ou limpar todo o
  vault e toda a instalação global do Claude.
- Alterar credenciais, expor a ponte na rede ou mudar contratos públicos.
- Migrar o histórico interno completo dos fornecedores sem necessidade
  comprovada para esta tarefa.

## 5. Decisões que precedem a implementação

1. Aprovação explícita do plano de implementação, incluindo a substituição
   controlada do antigo invariante `cwd = VAULT` por execução no projeto e acesso
   explícito ao acervo. Até lá, código e diretrizes vigentes permanecem intactos.
2. Decisão sobre `CLAUDE.md` do projeto: atualizar apenas referências técnicas
   obsoletas (recomendado), preservando a orquestração específica do Claude Code;
   ou preservar integralmente o arquivo e comprovar o isolamento dessas
   instruções no runtime. Decisão do usuário em 08/10/2026: atualizar somente as referências técnicas;
   preservar a orquestração do Claude Code.
3. Prova técnica de carregamento de instruções, autenticação, retomada de sessão
   e proteção de escrita. O resultado deve fechar o contrato de runtime antes
   de integrar ao servidor. Não adotar flags que silenciosamente desativem a
   autenticação, os hooks necessários ou as skills previstas.

Não há promessa de ausência absoluta de falhas. A conclusão exige evidências
dos critérios acima e um caminho de recuperação, sem esconder pendências.

## Aceite

Migração concluída e aprovada em08/10/2026 no ciclo2/3. Critérios R01–R12
atendidos conforme revisao-independente-ciclo-2.md, com limites de sessões
anteriores e guarda cooperativa explicitados no runtime.
