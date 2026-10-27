# Revisão independente — ciclo 2/3

Data: 08/10/2026. **Veredito: APROVADO.**

Verificador independente GPT-6.1 Sol, esforço xhigh, o mesmo do ciclo 1,
sem participação na implementação. Código e testes permaneceram somente leitura.
O parecer reprovado do ciclo 1 está preservado em
`revisao-independente-ciclo-1.md`; o contador global não foi reiniciado.

## Método e evidência deste ciclo

Revisão proporcional às correções, comparando o estado atual com o snapshot
privado `cycle-1-implemented`. Conferidos fallback, geração de cancelamento,
encerramento de sessões, slots de processos, locks de inicialização/ponte,
shutdown do residente, publicação e liberação da guarda, regressões adicionadas,
arquivamento externo e política de sessões.

Suíte independente executada no ambiente autorizado do usuário, com TEMP/TMP e
basetemp exclusivos em `.migration-checks/tmp/independent-cycle-2`:

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q --tb=short -p no:cacheprovider --basetemp <temporario-exclusivo>/pytest
```

Resultado: **220 passed in 13.08s**, saída 0. Inclui o teste Windows com
descendente real que tentaria escrever após timeout. Não foram repetidas chamadas
à API nem sínteses de voz já suficientemente comprovadas. Nenhum processo de
produção foi encerrado pelo verificador.

As provas reais anteriores continuam aplicáveis aos caminhos, configuração,
modelos e protocolo preservados. O ciclo 2 acrescenta reinício normal bem-sucedido
e identificação da nova ponte/residente em `instancia-ciclo-2.json`, além da
integridade final em `integridade-final.json`.

## Encerramento das reprovações

| Item | Resultado | Correção e evidência |
|---|---|---|
| REV-C1-01 | **Corrigido** | Fallback usa Popen registrado em SESS e communicate; cancelamento alcança o processo; timeout encerra árvore. cancel_rev impede fallback, done e transcript tardios. `/session_end` e reset cancelam antes de esperar o lock do turno. Testes de abort/close, aborto antes do spawn e descendente real passaram. Slots são conferidos e registrados sob REG_LOCK, inclusive fallback. |
| REV-C1-02 | **Corrigido** | Owner completo preparado sob control e publicado por rename. Preparação abandonada e lock antigo incompleto são recuperados. Teste com morte real antes da publicação passou. Remoção tem cinco tentativas limitadas; teste exige propagação de erro definitivo e preservação do lock. |
| REV-C1-03 | **Corrigido** | Bookkeeping pós-ferramenta e liberação são serializados sob control; owner e tool_use_id precisam coincidir. Testes de callbacks atrasados para PostToolUse, PostToolUseFailure e PostToolBatch preservam a ferramenta atual e recusam outro escritor. |
| REV-C1-04 | **Corrigido** | Launcher segura startup durante detecção/criação/verificação; ponte segura bridge antes do residente e até terminar shutdown. Testes concorrentes criam uma única ponte e recusam segunda posse. Shutdown espera residente próprio, mantém posse e é idempotente. Reinício real registrado terminou com saída 0. |
| REV-C1-05 | **Corrigido** | Protótipo WinForms e seus dois lançadores foram arquivados e retirados após consumidores/hashes. Verificador confirmou 3/3 fontes ausentes, 3/3 hashes do arquivo histórico e 3/3 backups. Residente global antigo também ausente e arquivo histórico com hash original. Ferramentas/modelos/venv globais genéricos foram preservados. |
| DOC-R06 | **Corrigido** | docs/runtime.md declara SESS em memória, sessão nova ao reiniciar sem registro, retomada comprovada apenas de ID criado pelo runtime novo e ausência de promessa/importação automática de IDs anteriores à migração. |

O ajuste em `test_effort_server.py` adaptou os mocks de run para Popen e
communicate/poll; as asserções de esforço foram mantidas. Os testes antigos não
foram enfraquecidos para aceitar a implementação.

## Aceitação por requisito

| Requisito | Resultado | Evidência |
|---|---|---|
| R01 | **Passou** | Raiz, atalho e processos canônicos; cópia antiga arquivada. Arquivos específicos externos restantes do ciclo 1 agora têm destino histórico, backup e retirada registrados no manifesto/prototipo-winforms.json. Fontes antigas conferidas ausentes. |
| R02 | **Passou no inventário identificado** | Itens técnicos conhecidos retirados do vault, conteúdo misto separado e notas preservadas. Integridade final sem alteração inesperada. A revisão não promete classificação absoluta de todo arquivo arbitrário do vault. |
| R03 | **Passou** | Fonte, modelos e Python de voz locais; hashes e instalação reproduzível conferidos no ciclo 1; protocolo/síntese não foram alterados neste ciclo. Prova real de voz existente permanece aplicável; nova árvore de produção confirma residente local. |
| R04 | **Passou** | Runtime operacional comum e instruções locais preservados; descoberta do pipeline de desenvolvimento e hooks globais excluídos. Prova real anterior de nota e relatório em acervo descartável continua aplicável. |
| R05 | **Passou** | Persistente e fallback continuam com lançador/configuração comum, cwd do projeto e acervo explícito. Testes de isolamento/retomada de sids e configuração passam após a mudança do lifecycle. |
| R06 | **Passou com política explícita** | Dados e caminhos preservados; mobile íntegro. Prova real de retomada de ID novo existente e política de IDs antigos agora delimitada. Transcript recebeu append de uso normal: prefixo original validado, dados novos preservados; nenhuma substituição por backup antigo. |
| R07 | **Passou no contrato cooperativo do Hub** | Disputa real entre processos com leitura defasada, arquivo e shell; recuperação de abandono/publicação incompleta, callbacks atrasados, dono vivo e erros de remoção cobertos. Não é sandbox contra comandos maliciosos nem trava escritores externos; limite documentado. |
| R08 | **Passou** | Suíte independente 220/220; provas reais anteriores de voz, STT, texto e relatório; regressões novas de cancelamento, encerramento e timeout passaram. Streaming, fala serializada, eventos e gateway mantidos. |
| R09 | **Passou** | Listener loopback confirmado no estado final; autenticação/whitelist mobile preservadas. Teto seis vale para registro persistente e fallback sob REG_LOCK. SPEAK_Q/LOG_LOCK mantidos; relatório sem tokens ou conteúdo pessoal. |
| R10 | **Passou** | Identidade e conflito com origem alheia preservados; exclusão na inicialização e vida/shutdown demonstrada pelos testes; reinício real saída 0, nova raiz/processos confirmados e dry-run de parada registrado. |
| R11 | **Passou** | Backup/restauração original de 42 arquivos e mais três arquivos do protótipo registrados, total 45. Hashes adicionais conferidos pelo verificador. Retirada de fontes antigas fechada com consumidores e integridade; transcript novo preservado em recuperação individual, sem overwrite do vault. |
| R12 | **Passou** | Runtime/operação refletem cancelamento, locks, fontes locais, histórico e política de sessões. Arquivos históricos claramente inativos. Atualizações técnicas do CLAUDE preservam sua orquestração; ciclo 1 continua documentado. |

## Conclusão

Não há reprovação ou verificação necessária pendente no escopo acordado.
**Implementação aprovada no ciclo 2 de 3**, com suíte pertinente passando e
critérios R01–R12 atendidos nos limites explicitados acima. A sessão principal
pode consolidar o aceite e os estados finais do plano, manifesto, Issues e
verificação. Mudança posterior de código exige conferir novamente o estado
alterado; este parecer não aprova uma implementação futura.
