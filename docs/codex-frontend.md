# Codex no Hub — frontend minimalista

> Atualização de 12/10/2026: o seletor minimalista também expõe a página Hive
> Mind. Ela permanece separada dos provedores Claude/Codex: entrar nela não
> troca provider, não cria aba ou sessão e não inicia ações de voz/IA. Ao sair,
> a seleção e o estado locais de Claude ou Codex são preservados.

Implementado a partir do protótipo visual aprovado em 08/10/2026, em
`CODEX galáxia Frontend/Codex Hub.dc.html`. A integração headless está prevista
para uma etapa posterior, conforme decisão explícita do usuário.

## Uso e limites desta etapa

No modo minimalista, o seletor superior alterna Claude Code e Codex. Claude
preserva grafo, paleta e funcionamento. Codex apresenta fundo preto, galáxia
espiral, navegação, modelos e esforços, com indicação de backend pendente.
O painel completo mostra sempre a experiência Claude original; ao voltar ao
minimalista, a escolha anterior é restaurada.

As gavetas CONVERSA/SKILLS e as cinco visões são os componentes reais do Hub,
com busca, densidade, filtros DEBUG, diffs, relatórios e redimensionamento.
As sessões e conversas arquivadas são separadas por provedor. DEBUG e o acervo
de relatórios permanecem globais, como já eram no Hub. Não se copiam os dados
simulados, respostas ou comandos fictícios do protótipo.

As sessões Codex são locais nesta fase: criar, selecionar, fechar e limpar uma
conversa não inicia processos. Voz, envio, execução de skills, pausa e
encerramento de IA ficam indisponíveis. O modo texto permite preparar rascunhos,
mas não enviá-los. Não existem respostas GPT reais antes da etapa headless.
O teto compartilhado de seis abas segue MAX_TABS/MAX_SESS. Cada provedor
conserva sua última sessão, modelos/esforços e rascunho de texto; as sessões não
são persistidas entre recargas, seguindo o comportamento anterior do Hub.

Atividade Claude em segundo plano continua vinculada ao sid original. A aba
CELULAR continua sendo um espelho Claude, sem tomar o foco quando Codex está
selecionado. Troca de assistente é bloqueada durante gravação de voz.
Uma abertura de microfone que termina após troca de sessão é descartada e suas
tracks são liberadas. O turno de voz conserva modelo/esforço Claude antes da
transcrição; seletores GPT não contaminam seu payload em segundo plano.

## Peças

- `codex_frontend/routes.py`: blueprint de assets e catálogo, sem execução IA.
- `codex_frontend/catalog.py`: leitura e filtragem de metadados de modelos.
- `codex_frontend/models.json`: snapshot público de referência de 08/10/2026.
- `codex_frontend/static/models.js`: seletores/modelos/esforços e preferências.
- `codex_frontend/static/galaxy.js`: desenho extraído do protótipo, sem runtime
  do editor, React ou simulação de conversas.
- `codex_frontend/static/providers.js`: navegação e integração com o Hub.
- `codex_frontend/static/codex.css`: composição do protótipo, somente no
  minimalista; regras Codex escopadas por `data-assistant="codex"`.

`server.py` recebe apenas import/registro do blueprint. `index.html` carrega o
módulo e contém os ganchos mínimos aprovados para sessões e proteção dos envios.
`window.hubFrontend` expõe as operações do Hub; `window.hubProviders` define
provedor, filtro de sessão, guarda de ações e notificações de estado/áudio.
Não há build ou dependências adicionais de runtime.

## Catálogo de modelos

`GET /codex-ui/models` lê `CODEX_HOME/models_cache.json`, ou
`~/.codex/models_cache.json`. Só publica id, nome, esforços anunciados e padrão
dos modelos GPT visíveis. Nunca lê auth.json, tokens ou instruções internas.
Cache ausente/corrompido/vazio utiliza o snapshot e informa na interface
“CATÁLOGO DE REFERÊNCIA”. Falha HTTP de catálogo deixa seletores indisponíveis.

Há PADRÃO e todos os esforços que cada modelo anuncia, inclusive Max/Ultra
quando suportados. Ao mudar de modelo, um esforço incompatível volta a PADRÃO.
As três cópias dos seletores (principal, gaveta e modal) ficam sincronizadas.
As opções Claude são restauradas integralmente ao trocar de assistente ou
entrar no painel completo. A futura integração deve resolver disponibilidade
efetiva da conta e atualizar o catálogo pelo Codex app-server.

Fontes oficiais consultadas: [modelos Codex](https://learn.chatgpt.com/docs/models)
e [configuração/effort](https://learn.chatgpt.com/docs/config-file/config-reference).

## Galáxia e futura integração

Preserva as variantes A (Via Láctea, 10.500 partículas) e B (Grande desenho,
7.800 partículas), geometria, cores e desenho do protótipo. Usa canvas 2D e
recebe idle/listen/think/speak de `setState`, com áudio de `setMeter` entre 0–100.
Não inventa atividade nem amplitude de áudio. O loop para quando Codex fica
oculto, o painel completo é mostrado ou o navegador vai para segundo plano.

A etapa de backend deve substituir as guardas de indisponibilidade por um
adaptador real, mantendo isolamento de sid, limite de sessões, eventos NDJSON,
guardas do acervo e SPEAK_Q. Os endpoints Claude não são um fallback Codex.

## Validação

`tests/test_codex_frontend.py` testa catálogo, fallback, rotas, guardas e
fronteiras. `tests/codex_frontend_behavior.mjs` executa os caminhos reais de
sessão/envio e os seletores sem rede ou IA. QA visual usa servidor isolado com
endpoints simulados; resultados e screenshots ficam no plano desta tarefa.
