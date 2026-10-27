# C.O.R.E. — Voice Hub

Ponte local (Flask, `127.0.0.1:8765`) entre um HUD web (voz) e o `claude` CLI
rodando headless. Fala vira texto (STT local, faster-whisper), o texto vira um
turno de `claude -p` com streaming de eventos (etapas, plano, texto/raciocínio
parciais), e a resposta final é falada de volta via Kokoro TTS.

Este repo é a **base** — pensado para servir de ponto de partida para
diferentes versões futuras do Hub.

## Arquitetura, em uma frase por peça

- **`server.py`** — servidor Flask. Faz STT (`/stt`), spawna um processo
  `claude` por sessão/aba (`/ask`, `sid` isolado em `SESS[sid]`), traduz o
  stream do CLI em eventos NDJSON (`step`, `hb`, `partial`, `thinking`,
  `plan`, `done`, `debug`) e enfileira a fala final numa fila única
  (`SPEAK_Q`) para nunca sobrepor áudio entre sessões.
- **`index.html`** — o HUD (single-page, sem build step). Consome o NDJSON
  do `/ask` e renderiza timeline de atividade, watchdog de silêncio, resposta
  nascendo ao vivo, painel de plano (via `TodoWrite`) e feedback sonoro.
- **`launch.py`** — sobe o servidor (se ainda não estiver no ar) e abre o
  HUD em `--app` mode no Chrome **normal** do usuário (perfil default —
  necessário para o microfone funcionar).
- **`launch_hub.vbs`** — atalho para rodar `launch.py` sem janela de console
  (pode virar botão/atalho no Windows).
- **`stop.cmd`** — encerra somente a ponte e o residente identificados desta instalação.
- **`hub_runtime/`** — instruções operacionais, guarda de notas, voz local e identidade da instância.
- **`tests/`** — testes de backend, frontend, voz, relatórios, concorrência e gateway móvel.
- **`docs/`** — arquitetura, contratos, operação e desenvolvimento; ForestOS está removido e aparece apenas como histórico.

## Pré-requisitos

- Windows + Python 3.11+ (3.13 tolerado — ver blindagem de WMI em `server.py`).
- Google Chrome instalado em `C:\Program Files\Google\Chrome\Application\chrome.exe`.
- [Claude Code](https://docs.claude.com/claude-code) instalado e autenticado
  (`claude` disponível no PATH) — é o processo que o Hub spawna por trás.
- Voz Kokoro provisionada dentro de `hub_runtime/voice/`, incluindo modelos e ambiente Python. Veja [runtime](docs/runtime.md).

## Setup

```powershell
cd voice-hub
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
```

O primeiro boot do `server.py` baixa o modelo faster-whisper (`base` por
padrão) — pode levar até ~90s.

### Caminhos e configuração

A raiz deriva da localização do projeto; o acervo pode ser definido por `HUB_VAULT`. Revisar os caminhos e dependências ao instalar em outra máquina:

| Constante | Arquivo | Aponta para |
|---|---|---|
| `VAULT` | `server.py` | acervo pessoal por `HUB_VAULT`; CLI executa no projeto, transcript em `_agentes/voice-hub.md` |
| `KPY` / `SPEAK_SRV` | `server.py` | venv, modelos e residente locais em `hub_runtime/voice/` |
| `CHROME` | `launch.py` | binário do Chrome |
| `VHPYW` | `launch.py` | `pythonw.exe` da própria venv do Hub |

Fechar a janela do HUB derruba a ponte (o HUD pulsa em `/hud_ping`);
`HUB_AUTOQUIT=0` a mantém residente, para usar só pelo celular.

Variável de ambiente opcional: `HUB_WHISPER` (`tiny` | `base` | `small` |
`medium`, default `base`) controla o modelo de STT. O STT roda local na CPU e é
síncrono — modelo maior custa minutos por turno; a gravação tem teto de 180 s.

## Uso

**Subir o Hub:**
```powershell
python launch.py
```
Reaproveita o servidor se ele já estiver no ar (não sobe processo duplicado).
Alternativa sem console: rodar `launch_hub.vbs`.

**Encerrar:**
```cmd
stop.cmd
```

**No HUD:** falar (STT transcreve), o pedido vira um turno de `claude` na
sessão daquela aba. Durante o processamento aparecem, em tempo real: timeline
de atividade (ferramentas rodando), aviso de silêncio prolongado + botão
cancelar, resposta nascendo ao vivo, painel de plano (quando o Claude usa
`TodoWrite`) e blips/anúncios sonoros de progresso (toggle no HUD,
persistido em `localStorage`).

## Testes

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
```
A suíte inteira vive em `tests/` (o `conftest.py` de lá põe a raiz do repo no
`sys.path` para os testes importarem `server`).

## Notas de segurança

O `claude` é spawnado com `--dangerously-skip-permissions` — o processo tem
autonomia total de ferramentas sem prompts de confirmação. Isso é intencional
para uso por voz (não dá para aprovar tool call falando), mas implica confiar
no ambiente onde o Hub roda. O servidor só escuta em `127.0.0.1`.

## Documentação adicional

`CLAUDE.md` (neste repo) traz o histórico de decisões de arquitetura e
gotchas específicos deste Hub. `docs/prd.md`/`docs/issues.md` documentam o
ciclo de desenvolvimento corrente e seu status de aprovação; ciclos
anteriores estão em `docs/_dev-loop-archive/`.

## Projeto e acervo pessoal

Todo componente específico do Hub fica nesta pasta. O vault contém notas,
ideias, memória e relatórios pessoais; não é o diretório de execução da IA
em uso cotidiano. Configuração, instruções e hooks ficam em `hub_runtime/`.
Definir `HUB_VAULT` como caminho absoluto de um acervo existente. Recriar
a voz local por `hub_runtime/voice/requirements-lock.txt` (Python 3.13);
modelos locais em `hub_runtime/voice/models/`, fora do versionamento.
Guia completo em [docs/runtime.md](docs/runtime.md).
A migração preserva autenticação do CLI e componentes globais genéricos.
