# Relatórios visuais — de ponta a ponta

> Estado do código em 20/08/2026. Fonte: index.html.

O sistema de relatórios permite que o Claude da sessão de voz (que executa no projeto com
acesso explícito ao acervo) gere um dashboard/gráfico em HTML e o Hub o **abra sozinho na
tela** enquanto a resposta é falada — o usuário ouve o comentário e vê o
visual ao mesmo tempo. Três lados: o **gerador** (Claude no vault), o
**servidor** (rotas `/reports` do Flask) e o **front** (sonda + visor, seção
8e do `index.html`).

## 1. O contrato de geração (instruções do projeto)

Definido em `hub_runtime/instructions/uso-pessoal.md`, carregado pelo
lançador operacional. O vault guarda os relatórios, não as instruções do Hub. Quando o usuário pede um gráfico, tabela,
dashboard, comparativo ou relatório visual:

1. Buscar os dados (web, APIs públicas, arquivos do vault).
2. Gerar um HTML **auto-contido** (CSS e JS inline; biblioteca de gráficos via
   CDN é aceitável) e salvar em `_agentes/relatorios/` do vault com o nome
   `AAAA-MM-DD_HHMMSS_assunto.html`.
3. Dar ao arquivo um `<title>` curto e descritivo em português — o Hub usa o
   `<title>` como nome do relatório na lista e no visor.
4. **Não é preciso avisar o Hub** nem recarregar nada: o front sonda a pasta a
   cada poucos segundos e abre o relatório sozinho.
5. Na resposta falada, comentar os destaques — sem ler URLs, tabelas ou números
   longos (modo voz).

Estética sugerida (combina com o HUD): fundo escuro `#0a0f12`, acento dourado
`#B88A3F`, texto claro, fonte mono para números. Se a skill `dataviz` estiver
disponível, consultá-la antes de montar o gráfico.

A pasta fica **dentro do vault de propósito** (comentário no `server.py`): o
histórico de relatórios vira parte do acervo do Obsidian, consultável depois.

## 2. Lado servidor (rotas `/reports` — contrato coberto por `tests/test_reports.py`)

Constantes no `server.py`: `REPORTS_DIR = os.path.join(VAULT, "_agentes",
"relatorios")` e `REPORT_EXTS = (".html", ".htm")`. Detalhes de implementação
em `servidor-api.md`; o contrato que o front consome:

### `GET /reports`

Devolve `{"reports": [{file, title, mtime, size}, …]}`:

- Lista **só** arquivos `.html`/`.htm` da pasta (um `dados.csv` ou `nota.md` ao
  lado não aparece na lista).
- Ordenada por `mtime` decrescente — **mais recente primeiro** (desempate pelo
  nome do arquivo).
- `title` vem do `<title>` lido dos primeiros 4 KB do arquivo
  (`_report_title`); sem `<title>`, cai no nome do arquivo **sem o timestamp**
  e sem extensão, com `_`/`-` viradas em espaço (ex.:
  `2026-08-18_120000_vendas_do_mes.html` → `vendas do mes`). Nunca lança — a
  listagem não cai por causa de um arquivo ruim.
- `mtime` é inteiro (epoch em segundos) — é a chave da detecção de novidade no
  front.
- A pasta é criada no primeiro uso (`os.makedirs(..., exist_ok=True)`): pasta
  vazia/inexistente devolve `{"reports": []}`, não erro.

### `GET /reports/<fn>`

Serve o arquivo via `send_from_directory` — **qualquer extensão** (um relatório
pode referenciar um CSV/imagem vizinho), mas só de dentro da pasta: path
traversal (`..%2F...`) devolve 404, assim como arquivo inexistente.

### `DELETE /reports/<fn>`

Usado pelo botão EXCLUIR do visor:

- Extensão fora de `REPORT_EXTS` → **400** (só relatórios podem ser apagados;
  isso também barra traversal sem `.html` antes mesmo do `safe_join`).
- Traversal com extensão `.html` → **404** (`safe_join` barra).
- Inexistente → 404; sucesso → `{"ok": true}`.

## 3. Lado front (seção 8e do `index.html`)

### Sondagem (`pollReports`)

Roda desde o load, reagendando-se com `setTimeout(pollReports, REPS_POLL_MS)` —
`REPS_POLL_MS = 4000` (4 s). A cada sonda faz `GET /reports` e compara `mtime`
com `repsSeen` (maior `mtime` já visto):

- **Linha de base na primeira sonda**: enquanto `repsSeen === 0`, a lista
  inteira é considerada acervo antigo (`fresh = []`) — relatórios pré-existentes
  **não** abrem sozinhos ao abrir o HUB, só populam a aba (com um
  `dbg('INFO','relatórios no acervo: N')`).
- Nas sondas seguintes, todo item com `x.mtime > repsSeen` é novidade
  (`fresh`). Para cada leva nova: `dbg('OK','relatório novo: …')`,
  `dockNotify('l')` (ponto âmbar na alça da gaveta CONVERSA, se recolhida no
  minimalista), badge `RELATÓRIOS (n)` se a aba `#reps` está oculta (senão
  repinta a lista), e — a promessa da feature —
  **`openReport(fresh[0])`: o visor abre sozinho** com o relatório mais
  recente.
- Erros de rede são silenciosos de propósito (a ponte pode estar reiniciando);
  a próxima sonda resolve.

### Visor overlay (`#repOverlay`)

`openReport(r)` monta a URL `'/reports/' + encodeURIComponent(r.file)`, escreve
o título em `#repTitle` (o `<title>` do arquivo, via servidor), aponta o link
`#repOpen` e o **iframe `#repFrame`** para a URL e mostra o overlay. O corpo do
visor é o iframe (`.rep-frame`) com o HTML auto-contido renderizado dentro do
Hub — caixa `.rep-box` de `min(1180px, 95vw)` × `92vh`.

- **`ESC` fecha só o visor** — o handler global de teclado testa
  `!els.repOverlay.hidden` antes dos atalhos e chama `closeReport()`,
  **nunca** `onStop()` (a sessão de voz continua intacta; garantido por
  `test_esc_com_visor_aberto_fecha_o_visor_e_nao_encerra_a_sessao`). Clicar no
  backdrop ou no botão FECHAR (`#repClose`) faz o mesmo.
- `closeReport()` além de esconder o overlay zera o iframe
  (`src = 'about:blank'`) — libera o documento e mata timers/áudio que o
  relatório tenha criado.
- **Botão NOVA GUIA** (`#repOpen`, um `<a target="_blank" rel="noopener">`)
  abre o mesmo `/reports/<fn>` numa aba própria do Chrome.
- **Botão EXCLUIR** (`#repDelete`): `confirm()` nativo e, confirmado,
  `DELETE /reports/<fn>`; sucesso remove o item de `repsList`, repinta a lista
  e fecha o visor. O arquivo aberto fica em `repOpenFile`.

### Aba RELATÓRIOS (`#reps`)

Quinta aba de visão do `#txPanel` (`data-tab="reps"`, tag `VISUAIS` no
`#tabTag`; no rail do minimalista, ícone `◳`). `renderReports()` lista
`repsList` (a resposta mais recente do `GET /reports`, já ordenada) como linhas
`.rep-item`: título + data/hora `DD/MM HH:MM` (`fmtRepTime`, a partir de
`mtime`), nome do arquivo no tooltip; clicar reabre o visor. Vazia, mostra
"NENHUM RELATÓRIO AINDA. PEÇA UM GRÁFICO OU RELATÓRIO POR VOZ.". Ativar a aba
zera o contador (`repsUnread = 0`) e repinta. A aba é **global** — a pasta é
uma só, não há separação por sessão/sid.

### Resumo do fluxo

```
usuário pede "faz um gráfico de X" por voz
  → claude (cwd=projeto, acervo explícito) busca dados e salva
    _agentes/relatorios/2026-08-20_153000_x.html  (<title> descritivo)
  → em ≤ 4 s o pollReports vê o mtime novo
  → visor #repOverlay abre sozinho (iframe → GET /reports/<fn>)
    + ponto na alça da gaveta + badge na aba RELATÓRIOS
  → usuário ouve os destaques pela voz enquanto olha o visual
  → ESC fecha o visor (a sessão segue); o arquivo fica no acervo
    (aba RELATÓRIOS e pasta do vault), até ser excluído pelo visor
```

Ver também: `frontend.md` (abas de visão, gavetas e atalhos), `servidor-api.md`
(implementação das rotas), `arquitetura.md` (visão geral) e `voz-tts.md` (a
fala que acompanha o relatório).
