# Tarefas

| ID | Tarefa | Dependência | Responsável | Estado |
|---|---|---|---|---|
| CF-01 | Tema e galáxia fiel ao protótipo | aprovação | principal | implementado |
| CF-02 | Blueprint assets/catálogo e seletores | aprovação | principal | implementado |
| CF-03 | Sessões, navegação, bloqueio backend e preservação Claude | CF-01, CF-02 | principal | implementado |
| CF-04 | QA visual, testes e documentação | CF-03 | principal | validação principal concluída |
| CF-05 | Verificação independente de todos os critérios | CF-04 | verificador | aprovado no ciclo 2 |

## Reprovação do ciclo 1 e correções do ciclo 2

- CF-R1 (P1, aceite 9): após STT Claude pendente, trocar para Codex enviava modelo GPT/esforço Codex a /ask com sid Claude. Corrigido por seleção vinculada ao provedor da sessão e snapshot do turno antes do await STT; teste diferido confere payload completo. Reverificação aprovada.
- CF-R2 (P1, aceites 8/9): getMic pendente resolvia após troca e iniciava gravador Claude oculto, reabilitando o botão Codex. Corrigido por validação de sessão/foco/estado ao resolver e liberação de tracks obsoletas antes de atribuir stream; teste diferido confere ausência de Recorder/meter, tracks e controles. Reverificação aprovada.

Relatório inicial: revisao-independente-ciclo-1.md. CF-R1/CF-R2 resolvidas e aprovadas na revisao-independente-ciclo-2.md. 2 de 3 ciclos utilizados; sem pendências nesta etapa frontend.
