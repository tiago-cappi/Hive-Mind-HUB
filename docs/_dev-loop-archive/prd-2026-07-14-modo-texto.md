# PRD — Modal de composição de texto + seletor de esforço (Hub C.O.R.E.)

## Contexto
O Hub de voz (C.O.R.E.) tem um modo de conversação por texto cujo campo de digitação é uma caixa pequena no rodapé — desconfortável para escrever prompts longos, e sem espaço para escolher parâmetros na hora. O usuário pediu (2026-07-15), com **alterações mínimas**: (1) ao clicar/focar a caixa de texto, abrir um **modal grande centralizado** para digitar o prompt à vontade e escolher o modelo Claude ali mesmo; (2) o Hub já tem um dropdown de **modelo**, mas falta um de **esforço** (`--effort` do CLI) — verificar todas as opções reais que o CLI aceita. É melhoria de UX + passagem de um novo parâmetro ao processo `claude`; não muda o comportamento do Claude, o STT, o TTS nem o protocolo de fala.

## Escopo
- **Dentro:**
  - F1 — Modal de composição em tela cheia que abre ao focar/clicar a caixa de texto pequena do rodapé, com textarea ampla e os seletores de modelo e esforço, sincronizado com os controles do rodapé.
  - F2 — Novo dropdown de **esforço** no HUD (rodapé e modal) com as opções reais do CLI (`low, medium, high, xhigh, max`) + uma opção **PADRÃO** (sem forçar nível).
  - F3 — Propagação do parâmetro `esforco` no servidor por **todas** as rotas que já carregavam `modelo` (`/session_start`, `/session_reset`, `/ask` e o caminho de contingência sem processo persistente), reiniciando o processo `claude` da aba quando o esforço muda no meio da conversa — mesmo comportamento já existente para troca de modelo.
- **Fora:**
  - Qualquer mudança no comportamento do Claude, no STT/whisper, no TTS/Kokoro, no protocolo `/speak`, no DB, nas skills ou no fluxo de voz.
  - Redesign do modo texto além do modal pedido (nada de rich text, anexos, histórico de prompts).
  - Alterar a lista de modelos existente (FABLE 5 / OPUS 4.8 / SONNET 5 / HAIKU 4.5) — só se acrescenta o eixo de esforço.

## Arquivos-alvo
- `C:\Users\Meu Computador\Desktop\core-voice-hub-master\core-voice-hub-master\index.html` — HUD: dropdowns `#model`/`#effort` (rodapé, ~612-627), modal `#textModalOverlay` (~743-771) com `#modalModel`/`#modalEffort`/`#modalTextInput`/`#modalSend`/`#modalClose`, funções `currentModel`/`currentEffort` (~1399-1411), `openTextModal`/`closeTextModal` e handlers (~1782-1813), `#textInput` do rodapé (~730).
- `C:\Users\Meu Computador\Desktop\core-voice-hub-master\core-voice-hub-master\server.py` — ponte Flask: `ALLOWED_EFFORTS` (~188), `spawn_claude(sid, model, effort)` (~259-281), rotas `/session_start` (~314), `/session_reset` (~336), `/ask` (~369, checagem de troca de modelo/esforço ~391-401), caminho de contingência (`claude -p ...`, ~533-535).

## Contrato base (o que já existe hoje — não quebrar)
- O front envia ao `/ask`, `/session_start` e `/session_reset` um corpo JSON que **já** inclui `modelo` (alias do CLI: `fable|opus|sonnet|haiku`, vazio = padrão) e `sid`. A adição de esforço deve ser **aditiva** (novo campo `esforco`), sem quebrar chamadas antigas.
- `ALLOWED_MODELS = {"fable","opus","sonnet","haiku"}`; o servidor só passa `--model` quando o alias é reconhecido, senão roda no default.
- Troca de **modelo** no meio da conversa reinicia o processo persistente daquele `sid` (`spawn_claude`) preservando o `sid`. O esforço deve seguir exatamente essa mesma regra.
- Toda UI é por aba; os dropdowns de modelo/esforço são controles **globais** do HUD (não por aba) e valem para a próxima pergunta enviada.
- `Enter` envia, `Shift+Enter` quebra linha na caixa do rodapé (comportamento já existente); o modal deve manter essa convenção e adicionar `ESC` para fechar.

---

## Features

### F1 — Modal de composição de prompt em tela cheia
- **Descrição:** Ao **focar ou clicar** na caixa de texto pequena do rodapé (`#textInput`), abre um modal centralizado (`#textModalOverlay` > `.modal-box`) com uma **textarea ampla** (`#modalTextInput`) para compor o prompt com espaço, mais os dois seletores (modelo e esforço) e os botões FECHAR/ENVIAR. O texto e as seleções são **sincronizados** entre o rodapé e o modal ao abrir e ao fechar/enviar.
- **Entradas esperadas:**
  - Evento de `focus`/clique em `#textInput` → abre o modal; o modal herda o valor atual de `#model`, `#effort` e o texto já digitado no rodapé.
  - Digitação livre na `#modalTextInput` (multi-linha).
  - Teclas dentro do modal: `Enter` (sem Shift) → envia; `Shift+Enter` → quebra de linha; `Escape` → fecha sincronizando o conteúdo de volta ao rodapé.
  - Cliques: `#modalSend` (ENVIAR) → envia; `#modalClose` (FECHAR) e clique no backdrop `.modal-overlay` (fora da `.modal-box`) → fecham sincronizando de volta.
- **Saídas esperadas:**
  - Modal visível e centralizado (`#textModalOverlay` deixa de ter `hidden`) com a textarea focada.
  - Ao ENVIAR/Enter: os valores de `#modalModel`/`#modalEffort` são copiados para `#model`/`#effort` do rodapé, o modal fecha, a `#modalTextInput` é limpa e o prompt é disparado pelo mesmo caminho de envio do modo texto (`sendTextPrompt` → `POST /ask` com `{texto, modelo, esforco, sid, titulo}`).
  - Ao FECHAR/ESC/backdrop: o modal fecha e o texto + seleções ficam refletidos no rodapé (nada é perdido); nenhum `/ask` é disparado.
- **Regras / edge cases:**
  - Com o modal aberto, o teclado global do HUD (atalhos, push-to-talk) **não** deve interceptar as teclas digitadas no modal.
  - Enviar prompt vazio/só espaços não deve disparar `/ask` (mesma guarda do envio de texto atual).
  - O modal reusa os mesmos aliases: seleção de modelo/esforço feita no modal produz exatamente os mesmos valores de `currentModel()`/`currentEffort()` que o rodapé produziria.
  - Não altera o fluxo de voz (push-to-talk / STT) nem o log em `_agentes/voice-hub.md`.

### F2 — Dropdown de esforço no HUD
- **Descrição:** Um segundo `<select>` ao lado do dropdown de modelo (no rodapé, `#effort`, e no modal, `#modalEffort`) para escolher o **nível de esforço** do modelo. As opções devem ser **as reais do CLI** — verificadas via `claude --help`: `low, medium, high, xhigh, max` — mais uma opção **PADRÃO** (value vazio) que não passa a flag.
- **Entradas esperadas:**
  - Seleção no `<select>` de esforço. `option value` ∈ {`""`, `low`, `medium`, `high`, `xhigh`, `max`}; label exibido em maiúsculas (PADRÃO/LOW/MEDIUM/HIGH/XHIGH/MAX).
  - `currentEffort()` normaliza para minúsculas e só retorna o valor se ∈ {low,medium,high,xhigh,max}; caso contrário retorna `""` (padrão).
- **Saídas esperadas:**
  - O valor selecionado viaja no corpo JSON como `esforco` em `/ask`, `/session_start` e `/session_reset` (junto de `modelo`).
  - PADRÃO (value vazio) → `esforco: ""` → servidor não adiciona `--effort` (roda no default do CLI).
- **Regras / edge cases:**
  - As opções de esforço no rodapé e no modal devem ser **idênticas** (mesmos values).
  - Nenhum valor fora do conjunto permitido pode chegar a virar flag do CLI — o servidor valida contra `ALLOWED_EFFORTS` e ignora o resto.
  - O eixo de esforço é **independente** do de modelo (qualquer combinação é válida, inclusive modelo padrão + esforço definido e vice-versa).

### F3 — Propagação de `esforco` no servidor + reinício ao trocar
- **Descrição:** O servidor passa a ler e honrar o campo `esforco` em todas as rotas que já liam `modelo`, validando-o contra `ALLOWED_EFFORTS` e repassando `--effort <nivel>` ao processo `claude`. Trocar o esforço no meio da conversa reinicia o processo persistente daquele `sid` — exatamente como já ocorre ao trocar de modelo.
- **Entradas esperadas:**
  - Corpo JSON com `esforco` (string; `""` = padrão) em `POST /ask`, `POST /session_start`, `POST /session_reset`.
  - `ALLOWED_EFFORTS = {"low","medium","high","xhigh","max"}`.
- **Saídas esperadas:**
  - `spawn_claude(sid, model, effort)` monta o comando com `--effort <nivel>` apenas quando `effort ∈ ALLOWED_EFFORTS`; caso contrário, sem a flag.
  - No `/ask`, se o esforço pedido difere do esforço do processo vivo daquele `sid` (`s["effort"] != want_effort`), o processo é reiniciado (`spawn_claude`) antes de processar o prompt, com um evento `debug`/`ASK` registrando a troca (`.../esforço mudou (... -> ...)`).
  - O caminho de contingência (fallback `claude -p ...` sem processo persistente) também inclui `--effort` quando aplicável.
  - O estado por sessão guarda `effort` junto de `model` (`s["effort"]`).
- **Regras / edge cases:**
  - Campo `esforco` ausente (chamada antiga) → tratado como `""` (padrão), sem erro.
  - Esforço inválido/desconhecido → ignorado (roda no default), sem quebrar a rota.
  - Trocar **só** o esforço (mantendo o modelo) deve reiniciar o processo; trocar só o modelo idem; trocar ambos, um reinício.
  - Não emitir/alterar nada além do já existente no protocolo NDJSON do `/ask` fora o evento `debug` informativo da troca.

---

## Perguntas abertas
<nenhuma — as opções reais do `--effort` foram confirmadas via `claude --help` (low, medium, high, xhigh, max); os aliases de modelo e as rotas alvo foram confirmados no código atual.>
