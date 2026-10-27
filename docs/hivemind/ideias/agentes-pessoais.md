# Ideia registrada — agentes pessoais da Hive Mind

20/10/2026 · **somente registro, sem implementação**. Pedido do usuário por voz.
Entra depois de concluída a tarefa `2026-10-20_hivemind-escala-equipe` (o backend
`2026-10-19_hivemind-backend` já foi concluído no C4). Quando for iniciada, vira faixa completa
com PRD próprio, esclarecimento (§3.A de `docs/desenvolvimento.md`) e aprovação.

## O que o usuário quer

- Dentro da aba **Hive Mind** do Hub, uma **segunda página** dedicada a agentes
  pessoais, além da colmeia de missões.
- Os agentes pessoais são **as mesmas abelhas permanentes** que o usuário cria
  para trabalhar com a Rainha. Uma abelha permanente existe uma vez e aparece nas
  duas páginas: na colmeia, como operária de missões; na página pessoal, como
  assistente próprio.
- Cada assistente executa tarefas para o negócio ou a vida pessoal do usuário,
  **sob demanda** (o usuário pede) e **de forma proativa** (rotinas e gatilhos que
  o usuário programou, ou sugestões a partir do que observa).
- Abelhas temporárias, criadas pela Rainha para uma missão, **não** aparecem aqui.

## Referências pesquisadas (20/10/2026)

| Produto | Ideias aproveitáveis |
|---|---|
| **OpenAI Dots** (ChatGPT, DevDay 29/09/2026) | Agente persistente com nome/avatar; computador e navegador próprios na nuvem; **aba Agendados** com execuções ativas/pausadas/concluídas; **gatilhos** (novo feedback, nova transcrição); **pesquisa proativa somente leitura** nos apps conectados; **Regras** por ação: agir sem perguntar, agir se pré-aprovado, perguntar antes, devolver ao usuário; ações sensíveis sempre com o usuário; memória própria; acesso local desligado por padrão. |
| **Meta Muse** (08/09/2026) | VM dedicada e isolada com agente, dados e credenciais; agente **sentinela** separado que aprova acesso à internet; continua trabalhando com o app fechado e volta quando algo muda ou precisa de aprovação; **trilha de auditoria** do que fez e do que pretende fazer; acesso por app com escopo (ex.: e-mail só leitura ou também envio); credenciais e pagamentos escondidos do modelo; "esquecer" memórias específicas. |
| **xAI Grok Bot** (beta, 11/08/2026) | Vários bots em paralelo, cada um com máquina própria; **ensinar uma tarefa** gravando a tela uma vez, que vira rotina reutilizável; **delegação entre bots** em threads compartilhadas ("equipe pequena com um chefe de gabinete"), análogo à Rainha; trabalho concluído vai para **fila de aprovação**. |

## Encaixe com a arquitetura atual (a validar no PRD futuro)

- Cadastro único de abelhas permanentes (criado na tarefa de escala de equipe),
  estendido com rotinas, gatilhos, memória e regras de ação.
- Execução continua pelos adaptadores Codex/Claude com gates de cobrança/quota
  e sem fallback; limite global de slots e guarda de memória compartilhados
  com as missões, para não estourar a franquia nem a RAM de PCs modestos.
- Proatividade só com o Hub aberto ou com processo próprio explicitamente
  aprovado: hoje a ponte encerra ao fechar o último HUD (R10) e não há "PC
  desligado". Agentes 24/7 exigem decisão de arquitetura.
- Ferramentas além de `read/patch/checks` (e-mail, agenda, WhatsApp, navegador,
  arquivos pessoais) são conectores novos, cada um com escopo, aprovação por
  ação e auditoria. Coincide com os conectores futuros previstos no PRD do backend.
- Privacidade: dados pessoais fora do candidato de missões e do vault, salvo
  autorização explícita; nada de credenciais visíveis ao modelo.

## Perguntas para o esclarecimento futuro

1. Proatividade com o Hub fechado: aceitar um processo residente separado?
2. Quais conectores primeiro (agenda, e-mail, WhatsApp, navegador, planilhas)?
3. Nível de autonomia padrão por ação (modelo de Regras dos Dots)?
4. Memória: por agente, compartilhada, ou ambas? Onde fica (projeto ou vault)?
5. Canal de conversa: só o Hub, ou também o celular (`mobile/`) / WhatsApp?

Fontes: [CBS — Dots](https://www.cbsnews.com/news/sam-altman-openai-dots-chatgpt-agents-safety/),
[TechCrunch — Dots](https://techcrunch.com/2026/09/29/openai-launches-dots-its-bubbly-agentic-avatar/),
[DataCamp — Dots](https://www.datacamp.com/blog/openai-dots),
[Meta — Muse](https://about.fb.com/news/2026/09/introducing-muse-personal-ai-agent/),
[TechCrunch — Muse](https://techcrunch.com/2026/09/08/meta-debuts-its-muse-ai-agent-will-consumers-trust-it/),
[Unite.ai — Grok Bot](https://www.unite.ai/xai-launches-grok-bot-always-on-ai-teammates-with-their-own-cloud-computers/),
[VentureBeat — Grok Bot](https://venturebeat.com/orchestration/spacexais-grok-bot-turns-agents-into-persistent-digital-coworkers-that-can-operate-your-apps-for-120-per-month).
