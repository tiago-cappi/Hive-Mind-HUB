# Revisão independente — ciclo 1

Data: 08/10/2026. Faixa completa. Ciclo 1 de 3.
Verificador: agente independente GPT-6.1 Sol, esforço high, selecionado explicitamente pela sessão principal. Não participou da implementação. Código e testes não foram modificados.

**Veredito global: REPROVADO.** A suíte passa e o visual/seletores funcionam nos caminhos ociosos, mas há duas regressões reproduzíveis na troca de assistente durante a transição assíncrona de voz Claude.

## Fontes e ambiente

Lidos AGENTS.md, docs/desenvolvimento.md, CLAUDE.md como arquitetura, docs/codex-frontend.md e prd/plano/issues/verificacao desta tarefa. Revisados os módulos novos, catálogo, ganchos de index.html, registro do blueprint, testes Python/Node e documentação atualizada.

Suíte completa executada independentemente no estado integrado, fora do sandbox para permitir o teste Windows de encerramento de descendentes, com TEMP/TMP no workspace e basetemp descartável:

```powershell
$env:TEMP = Join-Path (Get-Location) '.test-tmp'
$env:TMP = $env:TEMP
& .\.venv\Scripts\python.exe -m pytest tests -q --basetemp=.test-tmp/codex-review-cycle1
```

Resultado: **229 passed in 21.75s**. Inclui os testes Codex e o executável Node de comportamento. Nenhum teste foi enfraquecido ou alterado.

QA no Chrome em aba independente, somente http://127.0.0.1:8877/, com servidor mockado existente. Sem CLI, Whisper, áudio real ou acervo pessoal. Reproduções adicionais utilizaram Node VM com funções extraídas do index.html atual, fetch/getMic/MediaRecorder simulados e sem rede/microfone reais.

## Achados obrigatórios

### CF-R1 — P1 — modelo/esforço Codex contaminam turno Claude após STT

Localização: index.html:1901 e :1908 (seleção global), :2128–2131 (continuação após STT), :2151–2154 (construção de /ask); codex_frontend/static/providers.js:98 (bloqueio de troca limitado a listen).

Reprodução:

1. Em Claude, iniciar voz e enviar a gravação. O /stt fica pendente e a sessão muda para think.
2. Selecionar Codex enquanto a transcrição aguarda. A troca é permitida; os seletores passam a GPT, por exemplo gpt-6.1-sol/ultra.
3. Resolver a transcrição. onRecStop continua com a sessão Claude original e chama askAndSpeak/streamAsk.
4. streamAsk usa currentModel/currentEffort dos seletores agora Codex, embora o sid pertença a Claude.

Evidência independente: funções currentModel, currentEffort e streamAsk reais foram executadas em Node VM com sessão Claude e seleção atual Codex. O fetch capturado foi:

```json
{"path":"/ask","texto":"texto transcrito depois da troca","modelo":"gpt-6.1-sol","esforco":"ultra","sid":"claude-stt-in-flight","titulo":"Claude","earcon_hz":220}
```

Esperado: o turno Claude em segundo plano conserva seu sid e a configuração Claude válida; a seleção Codex não altera seu payload.
Observado: modelo GPT e esforço Codex são enviados ao endpoint Claude com sid Claude. Pode escolher configuração inválida ou alterar o modelo da conversa.

Correção necessária: vincular a configuração de execução ao provedor/turno que o iniciou, antes dos awaits de voz, sem ler a seleção visual de outro assistente na continuação. Preservar a possibilidade aprovada de Claude trabalhar em segundo plano; bloquear toda troca em think não atende esse comportamento. Adicionar regressão com /stt diferido e troca para Codex, verificando sid, modelo e esforço no /ask resultante.

### CF-R2 — P1 — mic pendente inicia gravação Claude oculta após troca para Codex

Localização: index.html:2045–2074, especialmente aquisição do microfone e início/ativação do gravador; codex_frontend/static/providers.js:98–100.

Reprodução:

1. Em Claude, clicar INICIAR enquanto getMic ainda aguarda abertura/permissão do dispositivo.
2. A sessão continua ui=idle durante o await. Selecionar Codex: a guarda de troca só bloqueia ui=listen.
3. Resolver getMic. startListening continua na sessão Claude capturada, inicia MediaRecorder e medidor em segundo plano, e atribui els.main.disabled=false globalmente.
4. O usuário está em Codex; ENCERRAR atua na sessão Codex e retorna sem parar a gravação Claude. A captura pode seguir até o limite de gravação e enviar o turno automaticamente.

Evidência independente: startListening real em Node VM, getMic diferido, activeTab trocado de Claude para Codex antes de resolver. Resultado:

```json
{"active":"codex","claudeUi":"listen","recorderStarted":1,"codexMainDisabled":false}
```

Esperado: impedir uma troca que deixe captura órfã, ou cancelar com segurança a abertura pendente antes de trocar; nenhuma gravação invisível inicia depois da troca, nenhuma track fica aberta sem controle, e Codex conserva controles de voz indisponíveis.
Observado: gravador Claude inicia fora do foco e reabilita o botão Codex, contornando o isolamento visual/operacional.

Correção necessária: cobrir toda a transição de aquisição do microfone, além do estado listen; conferir validade/foco ao resolver e liberar tracks quando a operação deixar de ser válida. Adicionar regressão com getMic diferido e troca de assistente, incluindo controles, início do gravador e encerramento/liberação da captura. Não usar mic real no teste.

## Resultado por critério do PRD

| Critério | Resultado | Evidência e limite |
|---|---|---|
| 1 — seletor só no minimalista; Claude/grafo preservados | Passou nos caminhos ociosos | Chrome alternou Claude/Codex; painel completo ocultou navegação Codex; CSS escopado por body.minimal e data-assistant. A transição assíncrona defeituosa é registrada em 8/9. |
| 2 — galáxia, partículas, geometria, cores e composição do protótipo | Passou | Comparação automatizada dos corpos de rng, mix, css, buildBg, buildGalaxy, resize, draw e drawMeter: todos idênticos ao protótipo. Contagens A=10500/B=7800 verificadas pelo teste Node. Inspecionados os três PNGs existentes e screenshots atuais de galáxia, conversa e skills no Chrome. A imagem codex-skills.png é anterior ao ajuste de tipografia; a observação atual confirmou a tipografia maior/correta e botões indisponíveis. Não se exige identidade de pixels entre frames animados. |
| 3 — painel completo original/restauração | Passou | Selecionados SONNET 5/xhigh em Claude; ida Codex → painel completo restaurou esses valores e os controles Claude habilitados. Retorno ao minimalista recuperou Codex e rascunho. Elementos movidos voltam às âncoras originais. |
| 4 — cinco visões, busca/filtros/densidade/diffs/relatórios/resize | Passou nas verificações aplicáveis | As cinco visões acessadas no Chrome; DEBUG mostrou filtros reais, alterações/conversas/relatórios renderizaram estados vazios reais. Funções e elementos originais de busca, densidade, resize, diffs e visor foram preservados; testes existentes desses contratos passaram na suíte completa. Não foi utilizado relatório pessoal nem payload falso como resposta IA. |
| 5 — skills existentes, sem resultados mockados | Passou | Os oito comandos originais são reutilizados e ficam disabled em Codex com explicação no title; habilitados novamente em Claude. Nenhum runtime do editor/protótipo ou conversa fictícia foi carregado. |
| 6 — catálogo local público, fallback e esforços válidos | Passou para seletores/catálogo | Testes de sanitização, fallback ausente/corrompido/vazio, deduplicação, esforços e rotas passaram. Chrome exibiu sete modelos locais, Ultra em Sol, e removeu Ultra/voltou a PADRÃO ao trocar para Luna. Três pares sincronizados pelo ModelPicker; preservação Claude verificada. A configuração de turnos assíncronos é falha CF-R1 em 9. |
| 7 — sessões locais separadas e teto conjunto 6 | Passou | Node exercitou criação/fechamento/reset locais e histórico Codex sem fetch Claude. Chrome criou sessões Codex até seis totais (uma Claude + cinco Codex); + ficou disabled. Filtros por provedor e restauração da última sessão revisados. Espelho mobile mantém o comportamento existente, com classificação Claude pelo default. |
| 8 — backend pendente; voz/envio/skills/warmup Codex bloqueados | Falhou na transição | Aviso visível e guardas diretas passaram; sessões Codex não aquecem/resetam/encerram processos. CF-R2 permite captura Claude invisível e reabilita controle de voz quando Codex já está selecionado. |
| 9 — Claude funcional/background/mobile sem roubar foco | Falhou | sid de eventos, overlays condicionais e guarda mobile revisados; o espelho não assume foco em Codex. Entretanto CF-R1 mistura seleção Codex no /ask Claude após STT e CF-R2 deixa captura órfã. |
| 10 — modularidade/sem build; estados e nível real futuro | Passou | Blueprint só assets/catálogo; server.py tem import/registro. JS/CSS separados por responsabilidade. frame lê estado/áudio fornecidos, não simula IA; Node comprovou reação speak e idle sem amplitude inventada, além de pausa do loop. setActive cobre ocultação/Codex/painel completo/document.hidden. |
| 11 — testes completos e aprovação independente | Falhou | 229 testes passaram, mas aprovação independente recusada pelos dois achados acima. |

## Pendências e encaminhamento

Não há bloqueio de ambiente para a suíte completa. Headless Codex, paridade operacional de IA e integração mobile Codex permanecem fora do escopo aprovado; não foram aprovadas nem exigidas nesta fase.

A revisão não certifica uma sessão real de microfone/IA/acervo, que não foi executada; as regressões encontradas são determinísticas com o código atual e mocks. Visualmente a composição corresponde ao desenho aprovado; não há achado que exija redesenho.

Encaminhar CF-R1 e CF-R2 como correções obrigatórias do **ciclo 2 de 3**, com testes de regressão representando os awaits reais. Atualizar os registros de Issues/contador e reenviar o estado integrado para revisão independente. Este veredito cobre exclusivamente o estado congelado do ciclo 1.
