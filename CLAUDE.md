---
tipo: projeto
status: ativo
tags:
  - claude-code
  - hub
  - voz
  - web-app
criado: 2026-06-25
atualizado: 2026-08-28
---

# Hub C.O.R.E. — instruções do projeto

HUD web local (**C.O.R.E. — Claude Obsidian Reasoning Engine**) para conversar com
o Claude Code por voz ou texto no navegador. Stack: Flask em `127.0.0.1:8765` +
faster-whisper local + Kokoro residente + processos `claude` headless
persistentes (um por aba) + Chrome em app-mode.

**O projeto é a fonte de verdade técnica.** Código, documentação e recursos
específicos do Hub ficam nesta pasta. O vault Obsidian guarda somente conteúdo
pessoal: notas, memória, transcript, histórico mobile e relatórios visuais.
O CLI executa no projeto via `hub_runtime.assistant`, com acesso explícito ao
acervo configurado por `HUB_VAULT`; instruções de uso cotidiano ficam em
`hub_runtime/instructions/uso-pessoal.md`, isoladas destas regras de desenvolvimento.

## Documentação oficial — leia antes de mexer

A documentação completa vive em `docs/`. **Consulte o arquivo do assunto antes de
editar o código correspondente**; este CLAUDE.md é só o índice.

| Arquivo | Consulte quando |
|---|---|
| `docs/desenvolvimento.md` | **Antes de escrever qualquer código**: faixas, PRD, agentes, verificação, superfície de mudança |
| `docs/runtime.md` | Separação projeto/vault, runtime da IA, guardas, voz local e identidade |
| `docs/arquitetura.md` | Visão geral, mapa de peças, fluxos e invariantes — comece por aqui |
| `docs/servidor-api.md` | Mexer em `server.py`: rotas, payloads, sessões, eventos NDJSON, constantes |
| `docs/frontend.md` | Mexer em `index.html`: estados, grafo, abas, gavetas, atalhos |
| `docs/voz-tts.md` | Mexer em fala, Kokoro, streaming, earcon, watchdogs |
| `docs/hivemind/README.md` | Mexer na Hive Mind (`HiveMind/`): referência viva do código atual, encaixes intocáveis, testes e roadmap. `docs/planos/` guarda só registros de processo |
| `docs/forestos.md` | **Referência histórica** — o ForestOS foi removido do código em 28/08/2026; este doc é a base para reconstruí-lo |
| `docs/relatorios.md` | Mexer na geração, na sonda ou no visor de relatórios |
| `docs/mobile.md` | Mexer no acesso pelo celular (`mobile/`): cadeado, turno em thread, whitelist |
| `docs/operacao.md` | Subir, parar, reiniciar, testar, achar logs |
| `docs/prd.md` · `docs/issues.md` | Intenção do produto e o ciclo de redesign do `/forestos` (histórico) |

**ForestOS foi removido em 28/08/2026** (pasta `forestos/`, `forestos.html`, rotas
`/forestos*` e testes). Será refeito do zero como funcionalidade nova, modular
(regra 11). Menções a `/forestos`, `forestos/` ou `forestos.html` no restante de
`docs/` são **históricas** — a referência do que ele fazia é `docs/forestos.md`.

## Comandos essenciais

```powershell
# subir (ou usar o launch_hub.vbs, sem console)
./.venv/Scripts/python.exe launch.py
./restart_hub.ps1                      # derruba pela porta 8765 e resobe
./stop.cmd                             # encerra a ponte

# testes — a suite do Hub, na raiz
./.venv/Scripts/python.exe -m pytest

# celular na rede de casa (opcional, processo separado)
mobile\start_mobile.vbs                 # sobe sem console; link em mobile/LINK.txt
./mobile/stop_mobile.ps1               # derruba
```

## Regras críticas

1. **O protocolo de fala tem dois lados.** Mudou `hub_say_*`, `__stream__` ou
   `__quit__`? Mexa em `server.py` **e** em
   `hub_runtime/voice/speak_server.py`. Só um lado = fala quebrada em
   silêncio. Ver `docs/voz-tts.md`.
2. **Execução no projeto; acervo explícito.** Persistente e fallback usam
   `hub_runtime.assistant`: mesmas instruções, configuração e hooks locais;
   notas/relatórios usam caminhos do vault, não caminhos relativos ao `cwd`.
3. **`MAX_SESS` (`server.py`) e `MAX_TABS` (`index.html`) andam juntos** — hoje
   ambos valem 6.
4. **Toda fala passa pela fila única `SPEAK_Q`** — chamar o Kokoro direto
   atropela o áudio de outra sessão.
5. **Recurso compartilhado entre as N sessões tem guarda nomeada.** `SPEAK_Q`
   (fala), `LOG_LOCK`/`log_turn()` (transcript `voice-hub.md`) e o hook
   `hub_runtime/guards/file_guard.py` (versões lidas e exclusão mútua durante
   ferramentas no acervo, contra duas sessões sobrescreverem a mesma nota). Ver `docs/servidor-api.md` §3.4.
6. **ForestOS não existe mais no código** (removido em 28/08/2026). Não tente
   consertar rota `/forestos*`, `forestos/` ou `forestos.html`: eles foram
   apagados de propósito. A reconstrução futura é funcionalidade nova e segue
   a regra 11. Contexto: `docs/forestos.md`.
7. **A ponte fica em `127.0.0.1`.** Roda sem autenticação e com
   `--dangerously-skip-permissions`; nunca expor na rede. Quem fala com a
   rede de casa é o **`mobile/`** — processo separado, porta 8766, atrás de
   token + faixa privada, com whitelist de 5 rotas do Hub. Rota nova do Hub
   só chega ao celular se for escrita no `mobile/bridge.py`. Ver
   `docs/mobile.md`.
8. **Documentação junto com o código:** mudou comportamento, atualize o arquivo
   correspondente em `docs/` no mesmo commit.
9. **Todo desenvolvimento segue `docs/desenvolvimento.md`** (documentação
   técnica neste projeto), **antes** de escrever código: três faixas por
   tamanho da tarefa, PRD com critérios de aceite verificáveis para
   funcionalidade nova, subagentes Sonnet implementando lotes de arquivos
   disjuntos, verificação por um Opus limpo somente-leitura e ciclo de reparo
   com teto de 2 rodadas.
10. **Superfície de mudança.** Em código que já existe: a menor mudança que
    resolve a **causa raiz** — sem refatorar, renomear ou reformatar nada de
    passagem, sem trocar biblioteca ou assinatura pública fora do escopo
    declarado. Se a correção exigir refatoração maior ou tocar uma destas
    regras críticas: **pare e pergunte ao usuário**, não decida sozinho. Em
    funcionalidade **nova**: liberdade para criar quantos arquivos forem
    necessários, dentro das convenções existentes e com `docs/` no mesmo
    commit. Detalhe em `docs/desenvolvimento.md` §4.
11. **Modularidade só para o que é novo.** `server.py` e `index.html` **não
    são refatorados** — ficam como estão. Toda funcionalidade nova nasce em
    **uma pasta própria** (rotas com blueprint, lógica, dados, `static/` com
    JS e CSS da tela), e `server.py` ganha só o import e o
    `register_blueprint`; `index.html`, só a tag de script. Sem limite fixo de
    linhas: um arquivo, uma finalidade — se ficar grande, **avise o usuário**
    em vez de dividir por conta própria. Detalhe em
    `docs/desenvolvimento.md` §5.

## Relações

- [[Claude Code Index]] — índice de skills e arquitetura do Claude Code
- [[Dynamic Workflows]] — orquestração de subagentes
- [[voice-input-stt]] — notas de STT/captura do mic Cirrus
