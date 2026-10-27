# Redesenho da gaveta CONVERSA (modo minimalista)

Contexto: o modo minimalista é o modo principal do Hub (o painel completo será
extinto no futuro). A gaveta esquerda — que é o painel `#txPanel`
(`.transcript`) reposicionado por CSS na seção 9b — concentra TRANSCRIPT,
ALTERAÇÕES, DEBUG, CONVERSAS e RELATÓRIOS. Hoje ela é estreita demais
(`--dock-w: min(370px,34vw)`), com tipografia miúda e duas fileiras de abas de
semânticas diferentes coladas uma na outra.

Decisão do usuário: a gaveta **continua flutuando por cima do núcleo**. Não
ancorar, não empurrar, não redimensionar o grafo. Ela só ganha largura e ajuste.

## Regras que valem para TODAS as etapas

1. Mexer **somente** em `index.html`. Nada de `server.py`, `forestos.html`,
   `forestos/`, `assets/`.
2. O modo painel completo tem que continuar funcionando **exatamente como
   está**. Toda mudança visual do redesenho fica escopada em `body.minimal` (ou
   em variáveis que só o minimalista usa). Não remover o CSS/JS do modo completo.
3. **Não alterar** o markup dos botões de aba. Os testes estáticos casam string
   literal, incluindo acentos:
   - `<button class="tab" data-tab="chg">ALTERAÇÕES</button>`
   - `<button class="tab" data-tab="reps">RELATÓRIOS</button>`
   O `textContent` desses botões continua sendo usado pelos badges de não-lidos
   (`DEBUG (3)`, `ALTERAÇÕES (2)`) — não trocar por ícone no DOM.
4. **Não reescrever** os trechos de JS que os testes casam por regex, incluindo
   o espaçamento interno: o handler
   `tabBtns.forEach(b => b.addEventListener('click', () => {` com as linhas
   `els.chg.hidden   = (t !== 'chg');` / `els.reps.hidden  = (t !== 'reps');`,
   e as funções `chgSummary`, `renderActiveTranscript`, `openReport`,
   `closeReport`, `pollReports`, `sendTextPrompt`, `currentEffort`, o handler
   global de `keydown`, e as chamadas `dockNotify('l')`.
   Acrescentar código novo ao lado é permitido; reformatar o existente não é.
5. Ao fim de cada etapa rodar `.venv/Scripts/python.exe -m pytest tests/ -q`.
   Baseline: **128 passed**. Se cair, consertar antes de seguir.
6. Comentários novos em português, no mesmo tom dos que já existem no arquivo
   (explicam o *porquê*, não o *o quê*).

---

## Etapa 1 — Largura ajustável e persistente

Objetivo: acabar com a largura fixa apertada.

- `--dock-w` passa de `min(370px, 34vw)` para `clamp(420px, 34vw, 760px)`.
- Nova alça de arrasto na borda direita da gaveta esquerda: elemento novo
  `<div id="dockGrip" class="dock-grip" aria-hidden="true"></div>` dentro de
  `#txPanel`, visível só em `body.minimal`. Faixa de ~6px, área de clique de
  ~14px, `cursor:col-resize`, discreta (acende no hover em `--accent`).
- Arrastar altera `--dock-w` no `documentElement` em tempo real. Limites:
  mínimo 340px, máximo `min(1100px, 92vw)`.
- Persistir em `localStorage` sob a chave `core.dockw`; ler na inicialização,
  junto do restante do estado do minimalista (perto de `MIN_KEY`).
- Duplo clique na alça alterna entre a largura salva e uma largura ampla
  (`min(1100px, 80vw)`) — leitura confortável de diff sem virar outra tela.
- Usar Pointer Events (`pointerdown`/`pointermove`/`pointerup` +
  `setPointerCapture`), `user-select:none` no `body` durante o arrasto.
- A gaveta continua `position:fixed` sobre o núcleo. **Não** chamar
  `graph.resize()` no arrasto — o núcleo não se mexe.
- O arrasto conta como atividade: chamar `armDockHide('l')` ao soltar, para a
  gaveta não sumir logo depois de ajustada.

## Etapa 2 — Rail vertical de visões + cabeçalho da visão

Objetivo: as 5 abas não cabem na horizontal e viram scroll escondido; e há duas
fileiras de abas parecidas com significados diferentes (visões x sessões).

- Só sob `body.minimal`: `#txPanel` vira `display:grid` com
  `grid-template-columns: 104px 1fr`, e `h3.tabs` ocupa a primeira coluna
  (`grid-row: 1 / -1`), com `flex-direction:column`, `overflow-y:auto`,
  `overflow-x:hidden`. Todos os demais filhos vão para a segunda coluna.
- Cada `.tab` no rail vira um bloco: ícone em cima (via `::before`), rótulo
  embaixo em ~8.5px, quebrando linha, alinhado à esquerda. Ícones por seletor de
  atributo, **sem tocar no markup**:
  `[data-tab="log"]::before{content:"▤"}`, `chg` → `"±"`, `debug` → `"⌗"`,
  `convs` → `"⟲"`, `reps` → `"◳"`.
- Aba ativa: barra dourada de 2px na borda **esquerda** do bloco (o
  `border-bottom` atual continua valendo no modo completo).
- Separador vertical de 1px (`--line`) entre rail e conteúdo.
- `#tabTag` sai do meio das abas: reposicionar por CSS para a nova faixa de
  cabeçalho (canto direito). Não remover o elemento nem mudar seu id.
- Nova faixa de cabeçalho na coluna de conteúdo, markup novo:
  `<div class="dock-head" id="dockHead"><span class="dh-title" id="dockTitle">TRANSCRIPT</span></div>`
  inserida como primeiro filho da coluna de conteúdo. O JS atualiza
  `#dockTitle` na troca de aba — **adicionar um listener novo** em `tabBtns`,
  não editar o handler existente.
- `.sessiontabs` fica logo abaixo do cabeçalho, com um rótulo `SESSÕES` de 10px
  em `--ink-faint` antes dos chips, para desfazer a confusão com as visões.
  O rótulo pode ser `::before` no próprio `.sessiontabs` (sem markup novo).
- `.dock-selects` continua no rodapé da coluna de conteúdo.

## Etapa 3 — Escala tipográfica, densidade e disciplina do dourado

Objetivo: legibilidade. Tudo escopado em `body.minimal`.

- Corpo: `#log` 12px → 13.5px; `#debug` 11px → 12.5px; `#chg` 11.5px → 12.5px;
  `.chg-diff` 10.5px → 11.5px; `.conv-item`/`.rep-item` 12px → 13px.
- Nenhum texto abaixo de 10px na gaveta (rótulos de 8.5px sobem para 10px).
- Reduzir `letter-spacing` do corpo para `.01em` (manter tracking largo só em
  rótulos e títulos em caixa alta).
- Contraste: criar `--ink-faint-2:#8A8069` e usar nos textos pequenos da gaveta
  (`.line.sys .txt`, `.dl .dt`, `.cmeta`, `.rmeta`, `.chg-sum`, `.hint`).
  Não alterar `--ink-faint` global.
- Densidade: classe `body.dense` alternando padding/`gap`/`line-height`
  (confortável = padrão, compacto = `dense`). Botão no `#dockHead`
  (`<button id="densToggle" class="dh-btn" type="button">`) com estado em
  `localStorage` sob `core.dense`.
- Disciplina do dourado: hoje `--accent` aparece na barra do `h3`, na tag, na
  aba ativa, no marcador `::before` de `.conv-item` e `.rep-item`, no cursor e
  nos hovers. Na gaveta, manter dourado **só** em: aba ativa, `#tabTag`, cursor
  vivo e linha de atividade atual. Os marcadores `›` e `◳` das listas passam
  para `--ink-faint-2`; o realce de hover das linhas fica
  `rgba(255,255,255,.04)`.

## Etapa 4 — Busca e filtro

Objetivo: achar coisa em log longo sem rolar.

- No `#dockHead`, campo novo:
  `<input id="dockFind" class="dh-find" type="search" placeholder="buscar…" autocomplete="off">`.
- Filtra **a visão ativa** escondendo linhas que não casam (case-insensitive,
  sem regex), via classe `.nomatch{display:none !important}`:
  - `#log` → `.line` (casa em `.txt` e `.who`)
  - `#debug` → `.dl` (casa na linha inteira)
  - `#chg` → `.chg-row` (casa em `.cf`; esconder junto o `.chg-diff` irmão)
  - `#convs` → `.conv-item`; `#reps` → `.rep-item`
- Contador discreto ao lado (`n de N`) quando o filtro está ativo.
- Reaplicar o filtro quando chegam linhas novas (as funções que fazem `append`
  devem chamar um `applyFind()` novo) e ao trocar de aba.
- `Esc` no campo limpa o filtro e **não** pode borbulhar para o handler global
  (que encerra a sessão): `e.stopPropagation()`.
- Chips de nível no DEBUG: fileira de botões `INFO OK WARN ERR NET STEP` que
  ligam/desligam classes; estado em `localStorage` sob `core.dbgLevels`.
  Visível só quando a visão ativa é `debug`.

## Etapa 5 — Ritmo do transcript e auto-hide

Objetivo: o transcript vira parede de texto na coluna estreita.

- `.line` deixa de usar a coluna fixa `.who{flex:0 0 64px}` (que rouba largura):
  em `body.minimal`, vira bloco com rótulo em cima (`.who` em ~9.5px, caixa
  alta) e texto embaixo em largura cheia.
- Faixa lateral de 2px colorida por autor (`--teal` eu, `--green` claude,
  `--err` sistema), `padding-left:9px`, `margin-bottom:9px` entre turnos.
- Linhas `.line.activity` consecutivas ficam visualmente agrupadas (indentadas,
  sem faixa, um tom abaixo) para não competirem com a conversa.
- `DOCK_HIDE_MS` sobe de 12000 para 45000: como este é o painel de trabalho
  principal, sumir em 12 segundos atrapalha. Manter a proteção de hover/foco
  que já existe e acrescentar: não recolher se houver texto selecionado dentro
  da gaveta (`window.getSelection()`), nem com o campo de busca preenchido.
- Legenda passageira (`.caption`): não mostrar enquanto a gaveta esquerda
  estiver aberta — vira eco redundante do que já está sendo lido.
