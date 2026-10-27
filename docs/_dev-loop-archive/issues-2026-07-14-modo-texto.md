# Issues — Modal de composição de texto + seletor de esforço (Hub C.O.R.E.)

> Ordem sugerida: ISS-001 (dropdown de esforço, front) e ISS-002 (propagação no server) formam o eixo de esforço ponta a ponta; ISS-003 (modal) é a melhoria de UX do modo texto e reusa os dois seletores. As três são verticais e verificáveis de forma independente. Restrição do usuário: **alterações mínimas** — não refatorar o entorno.

## Slices

### ISS-001 — Dropdown de esforço no HUD (F2, front)
- **Slice:** Um segundo `<select>` de esforço ao lado do de modelo, presente no rodapé (`#effort`) e no modal (`#modalEffort`), com as opções reais do CLI + PADRÃO; o valor escolhido passa a viajar como `esforco` nas chamadas ao servidor.
- **Critério de aceite:**
  1. No HUD há um dropdown de esforço com exatamente as opções: PADRÃO (value `""`), LOW (`low`), MEDIUM (`medium`), HIGH (`high`), XHIGH (`xhigh`), MAX (`max`) — os values conferem com `claude --help` (`low, medium, high, xhigh, max`).
  2. `currentEffort()` retorna o alias em minúsculas quando ∈ {low,medium,high,xhigh,max} e `""` caso contrário (incluindo a opção PADRÃO).
  3. As requisições `POST /ask`, `POST /session_start` e `POST /session_reset` incluem o campo `esforco` no corpo JSON com o valor de `currentEffort()` (verificável inspecionando o `body:JSON.stringify(...)` de cada fetch e/ou o payload na aba DEBUG).
  4. As opções do dropdown do rodapé e do modal são idênticas (mesmos values).
- **Status:** em-andamento

### ISS-002 — Propagação de `esforco` no servidor + reinício ao trocar (F3)
- **Slice:** O servidor lê `esforco` em `/ask`, `/session_start`, `/session_reset`, valida contra `ALLOWED_EFFORTS`, repassa `--effort <nivel>` ao `claude` (incl. o fallback sem processo persistente) e reinicia o processo da aba quando o esforço muda no meio da conversa — como já faz para o modelo.
- **Critério de aceite:**
  1. `spawn_claude` aceita o parâmetro de esforço e adiciona `--effort <nivel>` ao comando **somente** quando `nivel ∈ ALLOWED_EFFORTS`; esforço vazio/inválido → sem a flag (verificável logando/inspecionando o comando montado).
  2. Enviar `POST /ask` com `esforco:"high"` numa sessão nova faz o processo `claude` daquele `sid` subir com `--effort high` (verificável via evento `debug`/`ASK` do NDJSON, ex.: "claude persistente iniciado" e o estado `s["effort"]`).
  3. Com um processo já vivo, mudar apenas o `esforco` na próxima `/ask` (mantendo o `modelo`) reinicia o processo daquele `sid` e emite um evento `debug`/`ASK` indicando a troca de esforço (`... -> ...`). Mudar só o modelo continua funcionando igual. `curl -N` no `/ask` mostra o evento de reinício.
  4. `POST /ask` **sem** o campo `esforco` (payload antigo) não quebra: é tratado como padrão (`""`, sem flag).
  5. `esforco` fora do conjunto permitido (ex.: `"ultra"`) é ignorado e o turno roda no default, sem erro na rota.
  6. O caminho de contingência (`claude -p ...` sem processo persistente) inclui `--effort` quando o esforço é válido.
- **Status:** em-andamento

### ISS-003 — Modal de composição de prompt em tela cheia (F1)
- **Slice:** Focar/clicar a caixa pequena do rodapé abre um modal centralizado com textarea ampla + os seletores de modelo e esforço; Enter envia, Shift+Enter quebra linha, ESC/FECHAR/backdrop fecham sincronizando de volta, ENVIAR dispara o prompt pelo caminho normal do modo texto.
- **Critério de aceite:**
  1. Focar (ou clicar) `#textInput` remove o atributo `hidden` de `#textModalOverlay`, foca `#modalTextInput`, e o modal aparece centralizado; a textarea do modal herda o texto já digitado no rodapé e os seletores herdam `#model`/`#effort`.
  2. Dentro do modal: `Enter` (sem Shift) envia; `Shift+Enter` insere quebra de linha sem enviar; `Escape` fecha sem enviar.
  3. ENVIAR (`#modalSend`) e Enter copiam `#modalModel`/`#modalEffort` para `#model`/`#effort`, fecham o modal, limpam `#modalTextInput` e disparam `sendTextPrompt` → um único `POST /ask` com `{texto, modelo, esforco, sid, titulo}` refletindo as seleções feitas no modal.
  4. FECHAR (`#modalClose`), `Escape` e clique no backdrop (`.modal-overlay` fora da `.modal-box`) fecham o modal sincronizando texto + seleções de volta ao rodapé, **sem** disparar `/ask`.
  5. Enviar conteúdo vazio/só espaços pelo modal não dispara `/ask`.
  6. Com o modal aberto, atalhos/teclado global do HUD não interceptam a digitação (o texto digitado com o modal aberto chega intacto ao prompt enviado).
- **Status:** em-andamento

## Reprovas do Juíz
<vazio até a primeira reprova>
