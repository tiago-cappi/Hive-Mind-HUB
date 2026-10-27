# Verificação — Hive Mind: modo real com o visual do protótipo

> **Status em 26/10/2026: ciclos 1 e 2 reprovados; ciclo 3 iniciado.** Relatório independente: `verificacao-c1-codex.md`.

## Linha de base (25/10/2026, antes de qualquer mudança)

Prints da sessão principal, janela 1396×612, Hub em `127.0.0.1:8765`, protótipo servido
localmente só para comparação:

| Tela | Observação |
|---|---|
| Modo real, gavetas Equipe e Missão abertas | Formulário cru. Abas puxadoras de 38 px com texto cortado. Modelo e esforço vazios com a equipe salva. |
| Modo real, Missão rolada | Hash solto, lista de veredito simples, JSON cru das alterações. |
| Modo real, Conversa aberta | Abas laterais sobre a Conversa. Texto da mensagem com 683 px em área de 559 px. Conversa cortada pela altura mínima de 760 px. |
| Demonstração | Equivalente ao protótipo (só o rig PNG difere, por decisão). |
| Protótipo (`Hive Mind.dc.html`) | Referência: gavetas Agentes e Missão, HUD com etapas, banner de aprovação, células com borda tracejada animada e rotas com setas. |

Varredura automática no modo real: único `scrollWidth > clientWidth` sem rolagem própria
na Conversa (`P`, 683 > 559). A aba "Equipe" tem 38 × 152 px com texto horizontal.

## Ciclos

### Ciclo 1 — retomada Codex em 26/10/2026

Verificador independente GPT-6.1 Sol high: **reprovado** por C1-01, C1-02 e C1-03; detalhes e evidências em `verificacao-c1-codex.md`. Integridade final do candidato: 59/59 arquivos iguais. Suíte com temporários locais: 458 passaram, 3 falharam, 1 ignorado; a falha Hive é C1-01, e as duas de ciclo de vida aguardam contraprova fora do sandbox.

### Ciclo 2 — em andamento

Correções por GPT-6.1 Terra high, troca de modelo autorizada explicitamente pelo usuário. A sessão principal fará missão real pelo Chrome e recolherá evidências visuais; o verificador independente avaliará o estado final.

### Fechamento C2

**Reprovado**, relatório independente `verificacao-c2-codex.md`: C1 confirmado corrigido; novas causas C2-01/02/03 comprovadas. Comparador 268 pares/13 casos sem falha de medição e estouro 237/0; inspeção dos PNGs reprovou pintura SVG. BrowserQA falhou por desprendimento contínuo do botão. Missão real UI interrompida após check no candidato (turn_start_failed), sem aplicação na origem. Suíte fora sandbox: 467 passaram/1 falhou; falha do gate Claude passou isoladamente, nova suíte limpa somente no candidato C3.

### Ciclo 3 — em andamento, último permitido

Correções mínimas por GPT-6.1 Terra high e nova verificação independente GPT-6.1 Sol high, com teste real diretamente pela página no navegador integrado após corrigir o adaptador.
