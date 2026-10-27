# Revisão independente — ciclo 2

Data: 08/10/2026. Faixa completa. Ciclo 2 de 3.
Verificador: o mesmo agente independente GPT-6.1 Sol, esforço high, selecionado explicitamente pela sessão principal. Não participou da implementação/correções. Não alterou código nem testes.

**Veredito global: APROVADO para o frontend Codex e os limites desta etapa.** CF-R1 e CF-R2 foram corrigidos na causa raiz, a suíte completa passou novamente e não há pendência necessária ao aceite frontend. Backend/headless Codex permanece explicitamente adiado.

## Evidências atuais

Revisados no estado integrado os novos métodos ModelPicker.selection e hubProviders.selection, currentModel/currentEffort com sessão opcional, snapshot do turno antes do STT, propagação por askAndSpeak/streamAsk e validação da aquisição local de microfone antes de atribuir stream/criar gravador. Lidos os novos testes diferidos e os registros atualizados de plano/Issues/verificação/documentação.

Suíte completa independente executada fora do sandbox, com temporários do workspace e diretório descartável específico do ciclo:

```powershell
$env:TEMP = Join-Path (Get-Location) '.test-tmp'
$env:TMP = $env:TEMP
& .\.venv\Scripts\python.exe -m pytest tests -q --basetemp=.test-tmp/codex-review-cycle2
```

Resultado independente: **229 passed in 22.66s**, inclusive teste Windows de encerramento de descendentes, catálogo/assets/guardas, frontend antigo e executable Node de comportamento. Resultado da sessão principal (15.41s) é evidência separada, não utilizado como substituto desta execução.

Os testes Node executam funções reais extraídas do index.html atual, com recursos externos simulados:

- onRecStop → askAndSpeak → streamAsk com /stt diferido; seleção SONNET/high antes do STT, foco Codex e GPT/Ultra antes da resolução. O /ask capturado conserva modelo sonnet, esforço high e sid claude-stt. Uma alteração posterior da preferência Claude para OPUS/max também não modifica a configuração do turno em andamento.
- ModelPicker.selection do provedor inativo retorna uma cópia; alteração dessa cópia não muda a seleção salva.
- getMic diferido resolvido após troca para Codex libera tracks, não atribui stream, não cria MediaRecorder, não inicia medidor e não reabilita o botão Codex.
- A captura válida da sessão Claude continua criando gravador/medidor e passando a listen.

Verificação adicional independente, sem editar testes: startListening real executado em Node VM com duas tracks adquiridas e três motivos de obsolescência (troca de foco, sessão removida de tabs, sessão agora ocupada). Nos três cenários: **2 tracks liberadas, 0 gravadores**, stream anterior preservado e controle principal mantido disabled. Nenhum microfone ou áudio real foi aberto.

Chrome QA recarregado com os assets atuais em http://127.0.0.1:8877/. Alternância confirmou controles/skills habilitados em Claude, indisponíveis em Codex, SONNET 5/high restaurados no painel completo e GPT-6.1 Sol/high restaurados no retorno ao minimalista. Nenhum erro/warning capturado no console. Inspecionados os PNGs atualizados codex-galaxia.png, codex-conversa.png e codex-skills.png; a imagem de skills agora corresponde à tipografia atual.

## Encerramento dos achados

| Achado | Estado | Evidência atual |
|---|---|---|
| CF-R1 — configuração GPT contaminava turno Claude | Corrigido | index.html:1901/1910 consulta seleção do provedor da sessão; :2106 captura antes do await STT; :2144/:2237 propagam snapshot; :2150 e payload usam essa configuração. Teste diferido confirma payload completo e imutabilidade durante a transcrição. |
| CF-R2 — mic pendente iniciava gravação oculta | Corrigido | index.html:2055 recebe aquisição local; :2057 valida foco, idle e presença em tabs; aquisição inválida para tracks e retorna antes de stream/Recorder. Teste diferido e três cenários independentes confirmam liberação/ausência de captura, com captura válida preservada. |

A adaptação de regex em test_frontend_static.py aceita a assinatura com argumento opcional; os asserts de normalização, whitelist e fallback DOM permanecem. Os novos testes comportamentais cobrem o payload efetivo, além da forma estática do código.

## Critérios do PRD no estado integrado

| Critério | Resultado | Evidência |
|---|---|---|
| 1 — seletor minimalista; Claude/grafo preservados | Passou | Smoke Chrome atual, CSS escopado e verificação visual do ciclo 1, sem redesenho nesta correção. |
| 2 — desenho/composição da galáxia do protótipo | Passou | Oito métodos de desenho idênticos constatados no ciclo 1; galáxia/CSS não foram substituídos neste ciclo. A/B e estado/áudio cobertos novamente no Node; três screenshots atuais inspecionados. |
| 3 — painel completo/restauração | Passou | Chrome atual restaurou SONNET 5/high no painel completo, ocultou navegação Codex e recuperou GPT-6.1 Sol/high no retorno. |
| 4 — cinco visões e recursos reais do Hub | Passou | Cinco visões verificadas no ciclo 1, integração visual preservada; todos os testes existentes desses contratos passaram novamente. Busca/filtros/densidade/resize/diffs/visor continuam componentes originais. Nenhum acervo pessoal foi acessado. |
| 5 — skills existentes, sem resultados mockados | Passou | Chrome atual habilita skills Claude e desabilita Codex; guardas e ausência de runtime/fake conversations verificadas novamente na suíte. |
| 6 — catálogo local público/fallback/esforços por modelo | Passou | Testes de catálogo/fallback/filtragem e Node de compatibilidade/sincronização passaram; cópia da seleção inativa verificada e preferências Claude restauradas no Chrome atual. |
| 7 — sessões Codex locais separadas/teto conjunto 6 | Passou | Testes reais de criação/fechamento/reset locais sem efeitos Claude passaram novamente; verificação Chrome de seis sessões totais do ciclo 1 permanece aplicável aos mesmos caminhos. |
| 8 — backend pendente/ações IA bloqueadas | Passou | Guardas diretas passaram; controles Codex indisponíveis no Chrome; CF-R2 eliminou captura obsoleta e reabilitação indevida. Rotas novas seguem somente assets/catálogo. |
| 9 — Claude background/mobile sem roubar provedor | Passou | CF-R1 agora mantém configuração/sid do turno em background. Mic obsoleto descartado. Guarda mobile e filtro padrão Claude permanecem e seus contratos passam; troca durante listen segue bloqueada. |
| 10 — modularidade/sem build/estado e áudio futuro | Passou | Módulos/blueprint preservados; somente ganchos mínimos da correção. Node reconfirmou geometria, reação ao estado/áudio e suspensão do loop; nenhuma dependência/build foi adicionado. |
| 11 — suíte completa e aprovação independente | Passou | 229 passed na execução independente atual; aprovação explícita neste relatório. |

## Limites da aprovação

A aprovação cobre a etapa frontend aprovada, com sessões Codex locais e backend indisponível claramente indicado. Não certifica operações GPT/headless, integração mobile Codex, serviços reais de STT/TTS/IA ou acesso ao vault, que não foram executados e são fora do escopo desta etapa.

Não há bloqueio de ambiente nem pendência de verificação necessária ao aceite frontend. Histórico do ciclo 1 permanece preservado no relatório anterior; foram utilizados **2 de 3 ciclos**, sem necessidade de iniciar o terceiro. Este veredito aprova exclusivamente o estado integrado congelado e verificado do ciclo 2.
