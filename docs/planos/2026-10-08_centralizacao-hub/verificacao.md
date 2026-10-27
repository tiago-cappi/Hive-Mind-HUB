# Verificação — Centralização do Hub

Data: 08/10/2026. Estado: **migração concluída**.
Veredito final: **APROVADO por verificador independente no ciclo2**.
Ciclos utilizados: **2/3**.

## 1. Evidências de referência

Leitura de AGENTS, CLAUDE do projeto, desenvolvimento, arquitetura, operação,
voz, relatórios, mobile, requisitos, fontes e testes pertinentes. Conferência
pontual de existência dos arquivos técnicos externos; nenhum conteúdo pessoal
ou token foi transcrito para estes registros.

- Residente global e modelos existem nos caminhos listados no plano.
- `file_guard.py`, `settings.json` e skill `desenvolver-hub` não existem nos
  caminhos do vault citados pela documentação; não afirmar proteção ativa.
- `server.py`, `index.html` e `launch.py` da cópia global antiga diferem da raiz
  atual. Não houve merge, exclusão, movimentação ou inicialização do Git.
- CLI local descoberto em `AppData/Roaming/npm/claude.ps1`; executado somente
  `claude --help`. Help confirma opções descritas em §4 do plano; não foram
  abertas sessões de IA para provar comportamento ou consumir uso nesta etapa.
- Consulta `Get-NetTCPConnection -LocalPort 8765 -State Listen` não confirmou
  listener. Ambiente PowerShell emitiu aviso de inicialização de drives; não
  usar essa observação isolada para certificar a cópia normalmente utilizada.

### Teste da versão atual

Executado na raiz, usando Python da venv:

```powershell
# TEMP/TMP e basetemp apontaram para diretório exclusivo dentro de .pytest_tmp.
.\.venv\Scripts\python.exe -m pytest tests -q --tb=short -p no:cacheprovider --basetemp <temporario-exclusivo>/pytest
```

Resultado em 08/10/2026: **189 passed in 7.32s**, código de saída 0.
TEMP/TMP foram ajustados somente no processo de teste para evitar limitações de
escrita do sandbox. Nenhum teste foi alterado; suíte usa mocks e não comprova
voz, CLI real, proteção externa ou transição real. Esta é a linha de base.

### Integridade antes do planejamento

Hashes SHA-256 dos arquivos existentes conferidos, para comprovar que o
planejamento não alterou código ou diretrizes vigentes:

| Arquivo | SHA-256 |
|---|---|
| AGENTS.md | `7e2bb2caad4759af0a74f13151a356236391a38afb7a92e8588966f4f18c3c60` |
| CLAUDE.md | `c47eaac873e6b930d62052d5092c3d0eeb0b9a68ce16167b03286c1d29d2c8fd` |
| server.py | `de316e2116f27e5b3f9c339c78e5186ef29ed12a3b37590aba841408df650895` |
| index.html | `337a97eaa265af33773c9a86164d71bbfc291d86be671b484f790692649c5d17` |
| launch.py | `17def8d33dbb7ffcbef95247496fa05a40a3f717a25a355b1a89569098368d42` |
| launch_hub.vbs | `665cd3d3d08858e0de7db27cd834d26bead0ca07138b7d6d6d138859159530e5` |
| restart_hub.ps1 | `b6fbc831a2844fe3099a599966af4f538ebdc4a97acdba7141ce9ef37a891cf3` |
| stop.cmd | `5eb813cd1a3f79d3cca9df9c2070886258bdf44e198dffe066a008aa97d1f687` |
| requirements.txt | `3bf1f5fb59b9864306d082f46cd75f310bfff8c3b6eb64c5a1906d402db68e5a` |
| docs/desenvolvimento.md | `7752dd87cd911eb77dee80cbaa80fb7e1fce21654a5159f6d16d396ab5920bc7` |

## 2. Roteiro de aceitação da implementação

Este é o roteiro original. Resultados executados estão no registro do ciclo 1 abaixo;
a tabela define os critérios e não é um veredito de aprovação.
Usar acervo descartável sem instruções/configuração/código de agente. Não testar
exclusões em relatórios pessoais reais. Tokens e notas não devem aparecer nos logs
de evidência compartilháveis. CLI/áudio real só durante a execução aprovada.

| Critério | Verificação e evidência exigida |
|---|---|
| R01 | Manifesto completo; comparação da cópia antiga, consumidores e atalhos; processo ativo e fontes identificados |
| R02 | Inventário antes/depois dos itens técnicos identificados; itens mistos separados; hashes dos arquivos pessoais afetados, links revisados e nenhuma retirada ambígua |
| R03 | Hash da cópia inicial do residente/modelos; versões e instalação reproduzível; comando do processo usa paths locais; voz real comprovada |
| R04 | Pedidos de nota e relatório usam instruções operacionais; nenhuma etapa de desenvolvimento disparada; rastrear origem das instruções e skills em sessão real |
| R05 | Testes de spawn e fallback verificam configuração comum; leitura/criação/edição de nota e relatório real em acervo descartável sem `.claude`/CLAUDE; nenhum arquivo gerado indevidamente na raiz do projeto |
| R06 | Transcript e relatórios preservados; migração JSON mobile sem perda/overwrite; retomada por ID, troca de modelo/esforço e isolamento entre sids; política de sessões antigas registrada |
| R07 | Duas sessões tentam editar simultaneamente a mesma nota, com leituras defasadas: não há atualização perdida; testar abandono/liberação e ferramentas/shell cobertos; ausência de cobertura necessária reprova |
| R08 | Suíte completa mais regressões específicas; roteiro real de voz/texto, áudio e cancelamento; mobile termina turno com cliente desconectado e resposta reaparece |
| R09 | Bind loopback, token/whitelist mobile, limite de seis sessões, fala serializada, log protegido e segredos fora dos registros |
| R10 | Abrir/reabrir Hub sem duplicar ponte/residente; ocupante alheio da porta gera conflito claro sem reutilização/kill; restart/stop identificam árvore correta e não atingem outro consumidor |
| R11 | Restauração comprovada em cópia descartável; backup privado enumerado; retirada só após hashes/consumidores; dados criados depois do backup preservados na recuperação |
| R12 | Busca por caminhos antigos nos arquivos ativos e docs; referências remanescentes classificadas como histórico/genéricas, sem código morto substituído; decisão CLAUDE cumprida |

### Regressões específicas

1. STT e envio por texto continuam usando o mesmo fluxo de conversa.
2. Streaming e fala clássica preservam earcon, título, envelope, ordem dos
   sentinelas e posse do `__quit__`; testes nunca colidem com residente real.
3. Duas abas podem pensar simultaneamente, mas não falar sobrepostas.
4. Reset, cancelamento e encerramento não deixam CLI órfão nem fala fantasma.
5. Relatório pessoal novo aparece no visor; relatórios antigos não reabrem no
   boot; ESC fecha apenas visor; traversal continua barrado. DELETE só em fixture.
6. Gateway preserva autenticação, silêncio padrão, histórico e espelho no desktop.
7. Configuração ausente/inválida gera erro compreensível e não cria um novo vault
   silenciosamente nem recorre automaticamente à cópia antiga.
8. Caminhos com espaços funcionam, inclusive a raiz e o vault desta instalação.

Arquivos existentes pertinentes: `test_concorrencia.py`, `test_speak_stream.py`,
`test_watchdog.py`, `test_reports.py`, `test_mobile.py`, `test_effort_server.py`,
`test_session_watch.py`, `test_autoquit.py`, `test_stt.py` e os testes de frontend.
Criar somente testes adicionais que provem regressões/contratos da migração;
não enfraquecer testes existentes para encaixar a implementação.

## 3. Registro por ciclo

Ciclo 1 iniciado após aprovação. Para cada ciclo, acrescentar, preservando histórico:

- Número global, data, arquivos alterados e modelo/esforço dos responsáveis.
- Comandos, resultados e limitações; evidência por R01–R12: passou, falhou ou
  não verificável. Evidência antiga não aprova uma implementação depois alterada.
- IDs de reprovação nas Issues, diagnóstico e retorno ao implementador.
- Veredito independente: aprovado, reprovado ou pendente de verificação.
- Estado das retiradas externas e integridade do acervo após corte/recuperação.

Depois do terceiro ciclo sem aprovação, interromper. Não inventar evidências,
declarar perfeição pelo resultado do pytest ou executar quarto ciclo automaticamente.

## Execução — ciclo 1, em andamento

Plano aprovado em 08/10/2026; CLAUDE autorizado somente para referências técnicas.
Backup privado dos arquivos existentes em `.migration-backups/2026-10-08_centralizacao-hub/`.
CLI local 2.1.289; autenticação existente preservada. Primeiro ensaio sem bypass
de permissões revelou lock após recusa manual; cleanup por PostToolBatch corrigido
e coberto por teste. Ensaio seguinte, com as permissões headless do Hub, alterou
a nota descartável e gerou relatório; nenhuma recusa; custo indicado pelo CLI
US$ 0,0249604. Ensaio inicial consumiu US$ 0,1099104. Ambos são testes descartáveis,
não conversas no acervo pessoal.

Teste integrado inicial: **199 passed in 9.61s**. Guardas testadas entre processos
independentes em ferramentas de arquivo e shell; recusa de versão defasada seguida
de releitura permite recalcular sem perda. Naquele momento voz real, retomada, corte e revisão ainda estavam pendentes;
resultados posteriores registrados abaixo. Fontes de configuração: help
local e [memória](https://code.claude.com/docs/en/memory),
[hooks](https://code.claude.com/docs/en/hooks) do fornecedor.

## Ciclo 1 — evidências após implementação e corte

- Suíte final da implementação: **206 passed in 8.66s**, código 0.
  Fonte: execução antes do corte, em `.migration-checks/final-before-cut-tests`.
- Voz real com ambiente/modelos locais: READY, STARTED, DONE e envelope confirmados;
  residente de teste encerrado. Ambos os modelos têm SHA-256 igual aos originais
  (hashes e tamanhos no manifesto). Lock de dependências instalado e `pip check` passou.
- Ponte real em acervo descartável: identidade, leitura de relatório, transcrição
  de WAV pelo Whisper e pedido textual ao CLI passaram; parada identificou e encerrou
  ponte/residente, código 0. Nenhuma nota pessoal usada nas provas.
- Retomada real por ID explícito: CLI lembrou o valor da nota e nome do relatório
  criados no ensaio anterior. Sucesso, custo US$ 0,029199. Auth existente preservada.
- Após corte: 120 notas conferidas, **118 byte a byte intactas e 2 apenas com os
  links técnicos previstos**, zero alterações inesperadas. Preferências pessoais
  preservadas como nota; histórico mobile vazio (`null`, 4 bytes) transferido
  sem alteração; origem no projeto retirada.
- Quatro origens técnicas enumeradas saíram do vault após backup; material ForestOS
  ficou inativo em `docs/historico/forestos-vault/`. Configuração genérica do vault
  contém zero regras do Hub e permanece íntegra; runtime não a carrega. Projetos
  pessoais alheios não foram tratados como código do Hub.
- Cópia antiga global arquivada integralmente, inclusive `.git` e alteração local
  de `index.html`. HEAD `49ff940` e `git status` continuam indicando apenas esse
  arquivo modificado. Ferramentas globais de voz genéricas foram preservadas.
- Restauração ensaiada em cópia descartável: **42 arquivos** de backup recuperados
  e conferidos por SHA-256. Não houve rollback ou sobrescrita do acervo real.
- CLAUDE.md teve apenas referências técnicas atualizadas. Orquestração Claude Code
  (modelos, esforço, aprovações e ciclos) foi preservada.
- Evidências agregadas: `manifesto-migracao.json`, `integridade-pos-migracao.json`,
  `restauracao-prova.json`; logs descartáveis privados em `.migration-checks/`.

Inicialização normal pelo `launch_hub.vbs` confirmada no ambiente do usuário:
identidade e raiz canônicas, listener `127.0.0.1:8765`, ponte/residente locais,
endpoint de relatórios respondeu sem expor conteúdo. PIDs duplos de ponte/voz
são cadeias pai/filho dos shims da venv, não duas instâncias. Registro em
`instancia-pos-migracao.json`. Revisão independente ainda pendente.
A proteção de notas é cooperativa entre sessões do Hub, não bloqueio de programas
externos. Provas de CLI real usaram Haiku/low para limitar custo; não confundir
modelo de conversa de teste com seleção exigida para desenvolver/revisar.

Simulação de parada normal: `stop_instance.ps1 -DryRun` identificou somente
ponte PID14944 e residente PID16544, código0, sem encerramento. A sessão warm
ativa está ligada à ponte por cmd.exe (14944→11324→18588→15132), não é órfã.

## Revisão independente ciclo1 — REPROVADO

GPT-6.1 Sol, xhigh, não participou da implementação. Relatório separado preservado
em revisao-independente-ciclo-1.md, cinco findings reproduzidos sem API.
Suíte independente repetida206passed8.13s; primeira205passed/1failed por WinError145.
**Ciclo2/3 iniciado antes das correções**, sem reiniciar contador por fase/agente.

## Ciclo2 — correções executadas / veredito independente pendente

REV-C1-01 a05 corrigidos, detalhes em Issues e fontes. Novo teste real confirma
que descendente de fallback não escreve após timeout; /abort e /session_end
alcançam o processo e não publicam done/transcript tardio. Guarda cobre morte
real durante preparação do owner, publicação antiga incompleta, callbacks
atrasados e falhas de remoção transitórias/definitivas. Testes entre processos
e entre lançadores concorrentes comprovam exclusão. Shutdown aguarda residente
próprio sob posse da ponte. Teto de seis slots vale para persistente e fallback.

Primeira execução focada no sandbox:50passed/1failed porque taskkill da árvore
real não foi permitido; não foi apagado nem reclassificado como sucesso.
No ambiente do usuário:51passed6.12s; após completar shutdown/slots,
**suíte final220passed13.27s**, código0. Ajustes subsequentes de código foram
seguidos pela nova suíte, sem usar evidência anterior para aprová-los.

Três arquivos WinForms retirados só após hashes iguais, zero processos/atalhos/
tarefas consumidores encontrados. Busca global após retirada mostrou residente
original sem consumidores: sua fonte foi arquivada e retirada separadamente com
hash validado. Hooks genéricos say.py/speak.py e modelos/venv globais continuam.
Dados pessoais não alterados por essas correções. Mais três backups do protótipo
restaurados por hash em cópia descartável, total45arquivos.

Retomada comprovada é de ID novo; a abertura após reinício inicia nova sessão
quando registro em memória não existe. Não prometida importação/retomada
automática de conversas anteriores. Histórico, transcript e dados continuam.
Modelo/esforço do verificador: GPT-6.1 Sol xhigh, mesmo independente do ciclo1.

Reinício real do ciclo2: código0, identidade canônica PID3800, listener loopback
e relatórios HTTP200; DryRun identificou somente ponte3800 e residente1752.
Registro em instancia-ciclo-2.json. Integridade final:117notas intactas,2links
previstos e1transcript com novos turnos durante o uso normal do Hub. SHA-256
do prefixo original de123781bytes confere: somente acréscimo de3090bytes, sem
substituição do histórico. Novos dados preservados; snapshots privados original
validado e pós-corte disponíveis. Nada restaurado por cima do transcript novo.
Mais nenhum arquivo pessoal mudou. Ver detalhes sem conteúdo pessoal em
integridade-final.json.

## Aceite final — ciclo2 APROVADO

Parecer completo em [revisao-independente-ciclo-2.md](revisao-independente-ciclo-2.md).
GPT-6.1 Sol, xhigh, somente leitura de código/testes, sem participação na
implementação. R01–R12 passaram nos limites declarados. Suíte independente
**220passed13.08s**, saída0. REV-C1-01..05 e DOC-R06 corrigidos. Não há
verificação necessária ou reprovação pendente no escopo aprovado.

Código e testes permaneceram no estado revisado. Este fechamento somente
atualiza registros do plano/Issues/manifesto. Parecer reprovado e ensaios
com falhas estão preservados como histórico; não foi executado quarto ciclo
ou reiniciado contador. Total2/3, nenhum custoAPI adicional na revisão.
Backups privados e provas permanecem disponíveis.
