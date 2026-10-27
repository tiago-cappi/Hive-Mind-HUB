# Codex no modo minimalista — frontend

## Objetivo e decisões

Integrar ao Hub o visual aprovado de `CODEX galáxia Frontend/Codex Hub.dc.html`,
preservando o tema preto, composição, galáxia, gavetas e navegação. O usuário
confirmou em 08/10/2026: frontend nesta etapa; backend headless na próxima.

Faixa completa: nova experiência com integração de sessões, seletores e estados.
Protótipo é referência visual/código de desenho; seus dados, comandos e respostas
simulados não são funcionalidades reais nem instruções de desenvolvimento.

## Requisitos e aceite

1. Seletor Claude Code/Codex visível apenas no modo minimalista; troca real de
   identidade visual, mantendo Claude e seu grafo existentes.
2. Codex usa o desenho da galáxia do protótipo, mesmas partículas, geometria,
   cores e composição. Comparar screenshots em espera e com gavetas abertas.
3. Painel completo preservado: ao entrar nele, mostrar a experiência Claude
   original, sem seletores GPT nem estilos Codex; conferir retorno ao minimalista.
4. As cinco visões existentes continuam acessíveis: TRANSCRIPT, ALTERAÇÕES,
   DEBUG, CONVERSAS e RELATÓRIOS; preservar busca, filtros, densidade,
   redimensionamento, diffs e visor de relatórios utilizando os recursos do Hub.
5. SKILLS conserva os comandos existentes; nenhum mock do protótipo é usado
   como resultado real. Recursos que precisam de IA ficam pendentes do backend.
6. Modelos GPT recentes e esforços são obtidos do catálogo local do Codex,
   expondo somente metadados públicos; fallback explícito se indisponível.
   Esforços válidos dependem do modelo; preservar seleção por assistente.
7. Sessões Codex separadas das Claude, com criação, seleção, fechamento e nova
   conversa locais; conservar o teto conjunto de seis sessões normais.
8. Codex informa backend pendente e bloqueia voz, envio, skills e aquecimento
   de processos. Nenhuma ação Codex chama /ask, /stt, /session_start,
   /session_reset, /abort, /speak ou /session_end do Claude.
9. Claude continua funcional, inclusive processamento em segundo plano e
   espelho CELULAR; atividade do celular não muda o provedor selecionado.
10. Componente novo modular, sem build nem dependências adicionais; galáxia
    preparada para idle/listen/think/speak e nível de áudio real futuro.
11. Testes pertinentes e suíte completa passam; revisão independente aprovada.

## Fora de escopo

Codex headless, autenticação, ferramentas, memória/runtime Codex, TTS novo,
integração mobile Codex, alteração do painel completo e redesenho do protótipo.
Paridade operacional com Claude depende da futura etapa de backend.
