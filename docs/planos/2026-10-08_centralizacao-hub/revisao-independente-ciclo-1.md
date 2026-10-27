# Revisão independente — ciclo 1/3

Data: 08/10/2026. **Veredito: REPROVADO.**

Verificador independente, criado pela sessão principal com GPT-6.1 Sol, esforço
xhigh. Não participou da implementação e não alterou código nem testes.
Este relatório registra o estado anterior às correções do ciclo 2. Nenhuma
aprovação posterior deve apagar as evidências deste ciclo.

## Escopo e método

Lidos AGENTS.md, docs/desenvolvimento.md, CLAUDE.md, PRD, plano, Issues,
verificação, manifesto, runtime, implementação e testes da migração.
Comparados os arquivos existentes com os backups, incluindo servidor,
configuração mobile, CLAUDE e residente de voz. Revisados execução persistente,
fallback, cancelamento, guardas, inicialização e parada.

As provas reais existentes de voz, STT, CLI, relatório, retomada e parada foram
reutilizadas. A sessão principal acrescentou a prova da inicialização normal
pelo VBS, identidade e cadeias de processos. Não houve nova chamada à API,
alteração em conteúdo pessoal ou encerramento da instância do usuário.
Reproduções adicionais usaram fixtures privadas e processos que terminaram
sozinhos. TEMP/TMP e basetemp do pytest foram exclusivos no projeto.

## Testes e integridade

- Primeira suíte independente: **205 passaram, 1 falhou, 15,08 s**. Falha em
  `test_nota_existente_exige_leitura_e_falha_libera_lock`: `WinError 145` em
  `shutil.rmtree(active)` durante liberação após recusa. A causa do erro
  transitório não foi determinada; não foi atribuída a antivírus ou sandbox.
- Repetição focada justificada pela falha: **10 passaram, 1,60 s**.
- Repetição da suíte completa: **206 passaram, 8,13 s**, saída 0.
- Conferência independente: **42/42 backups** com SHA-256 do manifesto;
  **13/13 arquivos dos testes antigos** intactos; `index.html` intacto;
  **2/2 modelos de voz** com hashes originais.
- Diferença do residente limitada à pasta dos modelos e ao canal de TEMP
  explícito. A síntese e o protocolo foram preservados.
- Diferença do CLAUDE preserva a orquestração do Claude Code; alterações são
  referências técnicas da migração.
- Os registros de integridade pós-corte indicam 118 notas intactas, duas
  alterações de links previstas e nenhuma alteração inesperada. O histórico
  mobile vazio foi transferido com os mesmos bytes. Conteúdo e nomes de notas
  não são reproduzidos neste relatório.

## Reprovações necessárias

### REV-C1-01 — P1 — fallback não obedece cancelamento nem encerra árvore no timeout

Requisitos: R08 e R10. Local: `server.py:1017`, integração com
`server.py:612` e `server.py:752`.

O fallback usa `subprocess.run(shell=True, timeout=300)` sem registrar o processo
em SESS. `/abort` e `kill_all` alcançam somente `s["proc"]`. Em uma fixture com
persistente indisponível e fallback bloqueado, `/abort` retornou HTTP 200,
`ok=true` e `alive=false`, mas a chamada de fallback continuou executando.

Uma segunda fixture com subprocesso real e timeout de 0,2 s confirmou que o
descendente gravou um arquivo 1,188 s depois do início. O `TimeoutExpired`
retornou após 1,202 s: matar o shell não encerrou o descendente.
O novo wrapper pode manter CLI e escritor vivos depois do cancelamento/timeout.

Esperado: o mesmo controle da sessão deve alcançar persistente e fallback,
encerrar toda a árvore e impedir que um turno cancelado inicie um novo fallback
ou publique resposta/fala posteriormente.

Evidência privada: `.migration-checks/independent-cycle-1/`:
`fallback-cancel-result.json` e `fallback-timeout-result.json`.

### REV-C1-02 — P2 — morte durante publicação deixa guarda irrecuperável

Requisito: R07. Local: `hub_runtime/guards/file_guard.py:115` e `:121`.

A publicação cria `active/` antes de gravar `owner.json`. Uma fixture encerrou
um processo real com código 77 exatamente entre essas operações. A tentativa
seguinte de adquirir a guarda falhou imediatamente com `FileNotFoundError`;
o lock incompleto permaneceu. A recuperação de dono morto só funciona se o
JSON já estiver presente e válido.

Esperado: publicar um lock completo de modo atômico e/ou recuperar com segurança
publicações incompletas, sem roubar locks de escritores vivos. Também tratar a
liberação parcialmente concluída. O WinError 145 observado na suíte deve ser
registrado e a liberação precisa tolerar falhas transitórias limitadas, sem
silenciar uma falha definitiva ou liberar escritor alheio.

Evidência privada: `guard-abandon-result.json` na pasta de provas deste ciclo.

### REV-C1-03 — P1 — cleanup de outra ferramenta libera lock atual do mesmo dono

Requisito: R07. Local: `hub_runtime/guards/file_guard.py:185` e `:198`.

O ramo pós-ferramenta retorna quando o `tool_use_id` não coincide, mas seu
`finally` chama `release_owner` mesmo assim. Reproduzido: dono X adquiriu lock
para `current-B`; um `PostToolUseFailure` de `previous-A`, do mesmo dono X,
removeu o lock de B. Assim, uma notificação atrasada ou cleanup de batch pode
abrir o acervo para outra sessão enquanto a ferramenta atual ainda escreve.

Esperado: somente o evento que coincide com dono e ferramenta pode atualizar
o ledger e liberar a posse correspondente. A conferência e liberação precisam
preservar o casamento diante de notificações concorrentes.

Evidência privada: `guard-mismatch-result.json` na pasta de provas deste ciclo.

### REV-C1-04 — P2 — inicializações simultâneas podem duplicar ponte e residente

Requisito: R10. Local: `launch.py:38` e `server.py:1342`.

Não há exclusão mútua entre detectar a porta livre e iniciar o servidor. Dois
lançadores simultâneos produziram duas chamadas de criação da ponte em fixture.
Cada ponte inicia e limpa o canal do residente antes de tentar o bind do Flask.
A que perde a porta pode executar seu shutdown e enviar `__quit__` ao canal
que a outra acabou de usar. A identidade posterior não evita a corrida.

Esperado: uma única inicialização por instalação, inclusive durante carga dos
modelos, e uma ponte concorrente não deve limpar, iniciar ou parar o residente
da instância válida. Preservar conflito seguro com outro ocupante da porta.

Evidência privada: `launch-race-result.json` na pasta de provas deste ciclo.
A duplicação de chamadas foi reproduzida com mocks; o efeito sobre áudio foi
identificado por revisão do código e não provocado na produção.

### REV-C1-05 — P2 — protótipo específico do Voice Hub ficou como origem executável externa

Requisitos: R01 e R11. Locais externos enumerados: em
`~/.claude/hooks/voice-input/`, `voice_hub.ps1`, `launch_voice_hub.vbs` e
`launch_voice_hub.cmd`.

A leitura confirma que o WinForms é um protótipo do Voice Hub: usa o mesmo
transcript, roda Claude no vault com `--continue`, inicia o residente global e
usa o protocolo `hub_say_*`. Seus dois lançadores continuam apontando para ele.
Esse conjunto é específico do Hub, não uma ferramenta global genérica. O
manifesto o cita como candidato a consumidor, mas não fecha seu destino,
responsável, estado e retirada/arquivamento como componente específico.

Esperado: classificar e arquivar o protótipo e seus lançadores identificados com
hashes, consumidores e recuperação, ou registrar uma decisão explícita de
escopo que justifique preservá-los como produto independente. Preservar o TTS
global realmente compartilhado; não remover ferramentas globais indiscriminadamente.

## Aceitação por requisito

| Requisito | Resultado | Evidência e limite |
|---|---|---|
| R01 | **Falhou** | Raiz corrente, arquivos ativos e atalho canônicos; componente específico externo ainda sem destino final fechado: REV-C1-05. |
| R02 | **Passou no inventário identificado** | Quatro origens técnicas retiradas, conteúdo misto separado, configuração genérica preservada, hashes pós-corte sem alteração inesperada. Não certifica que todo arquivo arbitrário do vault seja pessoal. |
| R03 | **Passou** | Fonte/Python/modelos locais, hashes dos modelos conferidos, prova real READY/STARTED/DONE/envelope, lock de dependências e recriação documentada. |
| R04 | **Passou** | Lançador comum carrega instruções operacionais locais, exclui descoberta de instruções de desenvolvimento e hooks globais; prova real de nota/relatório sem pipeline de desenvolvimento. |
| R05 | **Passou** | Persistente e fallback usam o lançador comum e cwd do projeto; prova real em acervo descartável e teste de configuração/IDs do fallback. A falha de cancelamento é registrada em R08. |
| R06 | **Dados passaram; política de sessões anteriores pendente de explicitação** | Transcript/relatórios mantêm caminhos, mobile mantém bytes/formato e ID novo do runtime foi retomado de verdade. Não há prova de retomada de ID anterior à migração. Registrar que abertura normal inicia nova sessão quando não existe registro em memória; não anunciar importação automática de histórico antigo. |
| R07 | **Falhou** | Disputa real entre duas sessões e recusa de versão defasada passam; abandono incompleto e cleanup de tool diferente quebram o contrato: REV-C1-02/03. |
| R08 | **Falhou** | Suíte final passou e provas reais de voz/STT/texto/relatório foram registradas; cancelamento/timeout do fallback falhou: REV-C1-01. |
| R09 | **Passou na superfície da migração** | Bind loopback confirmado; autenticação/whitelist mobile e teto backend/frontend preservados; SPEAK_Q e LOG_LOCK preservados; relatório sem token ou conteúdo pessoal. |
| R10 | **Falhou** | Inicialização normal, identidade e dry-run da parada confirmados; conflito com origem alheia coberto; corrida de inicialização e lifecycle do fallback permanecem: REV-C1-01/04. |
| R11 | **Backup/restauração passaram; retirada incompleta** | 42 backups conferidos e restauração descartável registrada; corte controlado protege dados novos e checkout Git foi arquivado. Protótipo externo específico ainda sem encerramento: REV-C1-05. |
| R12 | **Passou na atualização técnica; requer acompanhar correções** | Busca de fontes antigas em arquivos ativos e docs correntes não achou dependência ativa do Flask; referências históricas identificadas e orquestração CLAUDE preservada. Atualizar runtime/operação/registro ao corrigir os achados e explicitar a política de sessões antigas. |

## Retorno ao implementador

Registrar **ciclo 2/3 antes de corrigir**. Corrigir REV-C1-01 a REV-C1-05 pela
cadeia responsável, incluindo provas de regressão adequadas e documentação da
transição de sessões. Fazer nova verificação integrada e preservar este relatório.
O contador global não reinicia. A suíte passando neste ciclo não aprova os
contratos que as reproduções adicionais demonstraram falhos.
