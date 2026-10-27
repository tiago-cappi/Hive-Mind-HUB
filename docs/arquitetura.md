# Arquitetura do Hub C.O.R.E.

Estado atualizado em 08/10/2026. Fontes: server.py, index.html, launch.py, mobile/ e hub_runtime/.

## 1. O que o Hub faz

Interface local no Chrome para conversar com Claude Code por voz ou texto.
Flask em 127.0.0.1:8765 recebe áudio/texto, faster-whisper transcreve localmente,
processos Claude mantêm contexto por sessão e Kokoro sintetiza a resposta.
A fala passa pela fila única SPEAK_Q. O gateway mobile é um processo protegido
separado. ForestOS foi removido; sua documentação é histórica.

## 2. Projeto e acervo

O projeto é a fonte de verdade técnica: código, docs, testes, configuração,
agentes, skills e instruções operacionais ficam aqui. O vault é acervo pessoal:
notas, ideias, memória, transcript, histórico mobile e relatórios visuais.
O CLI roda no projeto com configuração comum via hub_runtime.assistant,
recebendo acesso explícito ao vault. Não depende de CLAUDE.md/skills/hooks no
acervo. Instruções de desenvolvimento e de uso pessoal são separadas.
Detalhes e configuração: [runtime.md](runtime.md).

## 3. Componentes

| Peça | Responsabilidade |
|---|---|
| index.html | HUD desktop, captura, estados, sessões e visor de relatórios; sem build |
| codex_frontend/ | Tema/galáxia e seleção Codex no minimalista; assets/catálogo, sem backend IA nesta etapa |
| server.py | Flask, STT, sessões, eventos NDJSON, fila de fala e relatórios |
| hub_runtime/paths.py | Raiz do projeto, acervo e caminhos de voz |
| hub_runtime/assistant.py | Configuração operacional comum do CLI, hooks e instruções |
| hub_runtime/instructions/ | Regras de uso cotidiano da IA, voz e relatórios |
| hub_runtime/guards/ | Posse do acervo durante ferramentas e recusa de versão defasada |
| hub_runtime/voice/ | Residente Kokoro, ambiente separado e modelos locais |
| hub_runtime/instance.py | Identificação da instalação local |
| launch.py e scripts | Abrir, identificar, parar e reiniciar esta instalação |
| mobile/ | Gateway com autenticação, whitelist e turnos em thread |
| docs/, tests/ | Documentação técnica, planos e testes do projeto |

Instalações genéricas de Python, CLI/autenticação e Chrome permanecem no
sistema. O projeto não depende da cópia antiga em ~/.claude/hooks/voice-hub.
Backups privados preservam origens e alterações locais durante a migração.

## 4. Fluxos

Voz: microfone do Chrome → /stt → /ask → processo do sid → NDJSON no HUD →
SPEAK_Q → residente local → áudio. Texto entra diretamente em /ask.
Streaming pode começar a fala antes do fim da resposta, usando a mesma fila.
Cada sid tem processo e contexto próprios; fallback/retomada usam ID explícito,
sem --continue global ao diretório. Transcript pessoal recebe append sob LOG_LOCK.

Relatórios: IA grava HTML no acervo configurado → /reports lista → HUD sonda e
abre relatório novo no visor. Os caminhos pessoais foram preservados.
Mobile: gateway autentica e chama rotas permitidas da ponte; o turno continua
mesmo com a tela apagada; o histórico pessoal fica no vault.

## 5. Invariantes

1. Ponte somente em loopback; rede somente pelo gateway protegido.
2. Persistente e fallback compartilham runtime/instruções/acervo explícito.
3. MAX_SESS e MAX_TABS continuam 6 e devem permanecer sincronizados.
4. Toda fala passa por SPEAK_Q; protocolo exige os dois lados coerentes.
5. STT_LOCK protege Whisper; LOG_LOCK protege transcript; guardas do runtime
   protegem concorrência de ferramentas no acervo. Limites em runtime.md.
6. Reutilização/parada da porta exige identificar esta instalação.
7. Novos componentes são modulares por responsabilidade; código antigo recebe
   somente mudanças necessárias. Processo em desenvolvimento.md.

## 6. Índice

- [desenvolvimento.md](desenvolvimento.md): fluxo do Codex e regras de alteração.
- [runtime.md](runtime.md): separação das pastas, configuração e guardas.
- [servidor-api.md](servidor-api.md): rotas, sessões e contratos.
- [frontend.md](frontend.md): HUD, captura, estados e visor.
- [voz-tts.md](voz-tts.md): fila, streaming, sentinelas e watchdogs.
- [relatorios.md](relatorios.md): geração e acervo de relatórios.
- [mobile.md](mobile.md): gateway e autenticação.
- [operacao.md](operacao.md): execução, testes e logs.
- [historico/forestos-vault/README.md](historico/forestos-vault/README.md): material
  técnico retirado do vault; não descreve uma funcionalidade ativa.
- forestos.md, prd.md, issues.md e _dev-loop-archive/: referências históricas.
