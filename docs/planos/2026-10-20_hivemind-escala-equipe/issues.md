# Issues — Hive Mind: escala da equipe e navegação da colmeia

> **Status em 21/10/2026: SUSPENSA, ciclo 0/3** — aguardando o usuário mandar iniciar; nada desta tarefa existe no código ainda. A referência do código atual está em `docs/hivemind/README.md`.

20/10/2026 · ciclo **0/3** · suspenso por decisão do usuário; Claude e Codex destravados no C4 do backend (20/10/2026), início depende só do usuário.

| ID | Requisitos | Lote | Dependência | Status |
|---|---|---|---|---|
| EQ-01 | E01, E02 — limite 1–8 (padrão 4) e guarda de memória | L1 | C3 encerrado | aberto |
| EQ-02 | E03, E04 — limites do plano e `resources` | L1 | C3 encerrado | aberto |
| EQ-03 | E05 — temporárias inativas em todo encerramento, histórico preservado | L1 | C3 encerrado | aberto |
| EQ-04 | E06, E07 — cadastro rico, `roster_incomplete`, ferramentas por abelha, prompt da Rainha | L1 | C3 encerrado | transferido em 26/10/2026 para `../2026-10-25_hivemind-visual-real/issues.md` (VR-01, VR-02, VR-03) |
| EQ-05 | E09 — layout em anéis preservando as posições C7 | L2 | C3 encerrado | aberto |
| EQ-06 | E10 — zoom, arrasto, teclado e "Ajustar" | L2 | EQ-05 | aberto |
| EQ-07 | E05 (UI), E08 — gaveta Equipe e histórico das temporárias | L3 | EQ-04, EQ-06 | E08 (cadastro na gaveta Equipe) transferido em 26/10/2026 para `../2026-10-25_hivemind-visual-real/issues.md` (VR-05); E05 da UI (histórico das temporárias) continua aqui, aberto |
| EQ-08 | E11, E12 — regressão e documentação | todos | EQ-01 a EQ-07 | aberto |
| EQ-09 | E13 (a, b) — ressalvas P3 do backend: replay com revisão diferente, janela de fechamento | L1 | C3 encerrado | aberto |
| EQ-10 | E13 (c) — botão de reconciliação em `recovery_required` e mensagens dos códigos | L3 | EQ-09 | transferido para `../2026-10-21_hivemind-correcoes-pre-teste.md` (C04, C05) |
| EQ-11 | E14 — endurecimento dos adaptadores (ressalvas do C4 do backend). (a) item nativo no Codex: `turn/interrupt` e encerramento da árvore de processos do HiveMind, além do erro; (b) Claude: teto de major (< 3) e exigência de que cada flag apareça declarada como opção no `--help`; (c) `functionCallOutput` só para chamadas do broker, item de outro `threadId` falha fechado, conferir `extends` do perfil ativo; (d) testes de regressão: vínculo de versão do Claude, normalização de nulos, `verdict_invalid` e `functionCallOutput`; (e) `fake_cli.py` no manifesto | L1 | C4 do backend aprovado | aberto |
| EQ-12 | Achados de interface do teste no navegador (`../2026-10-24_hivemind-teste-navegador.md`), adiados pelo usuário em 24/10/2026 para esta tarefa. (F1) "Consultar modelos" leva ~10–20 s sem indicação de carregamento; (F3) abas puxadoras "Equipe"/"Missão" do modo real sem estilo (na demonstração têm ícone e contador); (F4) botões do modo real com estilo inconsistente ("Consultar modelos" e "Salvar equipe" como barra preta de texto pequeno, "Adicionar operária" só contorno); (F7) formulário de criação da missão continua preenchido acima da missão criada | L3 | — | transferido em 26/10/2026 para `../2026-10-25_hivemind-visual-real/issues.md` (VR-05, VR-06) |

## Registro de ciclos

### Suspensão — 20/10/2026

C3 do backend encerrado em 20/10/2026: pendente só de R15, sem falha local.
O usuário aprovou iniciar esta tarefa e incluir as ressalvas P3 (EQ-09/EQ-10).
Antes de iniciar o ciclo 1, o usuário pediu prioridade para corrigir a execução
real de Claude e Codex no Hive (R15). Nenhum lote foi disparado. Quando retomar:
L1 (Sonnet A) e L2 (Sonnet B) em paralelo; L3 com Sonnet B
depois de L1 e L2.
