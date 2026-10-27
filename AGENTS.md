# Repository Guidelines

## Project Structure & Module Organization

`server.py` implements the local Flask bridge, speech transcription, Claude CLI sessions, and serialized TTS. `index.html` contains the desktop HUD, including JavaScript and CSS; there is no frontend build step. `launch.py` opens Chrome and starts the bridge. Windows launch, restart, and stop scripts live at the root.

`mobile/` contains a separate authenticated gateway and its `static/` interface. `assets/` holds shared imagery. `tests/` contains pytest suites; `docs/` covers architecture, APIs, voice, mobile access, and development. ForestOS was removed; references in older documents are historical. `hub_runtime/` contains project-owned assistant configuration, instructions, file guards, voice runtime and instance identification. The Obsidian vault contains personal data, never project code or development documentation. `HiveMind/` is the Hive Mind feature (backend and frontend); before touching it, read `docs/hivemind/README.md`, the living reference of the current code. `docs/planos/` holds process records (PRDs, plans, verifications) that may describe superseded intentions.

## Build, Test, and Development Commands

Run from the repository root in PowerShell:

- `python -m venv .venv` — create the Python environment (Python 3.11+).
- `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` — install runtime dependencies.
- `.\.venv\Scripts\python.exe -m pip install pytest` — install the test runner separately.
- `.\.venv\Scripts\python.exe launch.py` — start the bridge and desktop HUD.
- `.\restart_hub.ps1` — restart the bridge on port 8765.
- `.\stop.cmd` — stop bridge and resident speech processes.
- `.\.venv\Scripts\python.exe -m pytest tests -q` — run the test suite.

## Esclarecimento e sugestões antes da implementação

Antes de implementar uma correção, modificação ou funcionalidade, esclarecer o objetivo, o escopo e o comportamento esperado. Quando houver ambiguidades relevantes, fazer quantas perguntas forem necessárias, em rodadas curtas, até que o pedido esteja suficientemente definido. Consultar o código e a documentação para responder às dúvidas técnicas que possam ser verificadas diretamente.

Quando o usuário estiver indeciso ou solicitar orientação, apresentar alternativas concretas, explicar vantagens e limitações e recomendar uma abordagem fundamentada no projeto. Não assumir decisões que alterem significativamente a experiência, o escopo ou a arquitetura sem esclarecer com o usuário.

Ajustar a profundidade desse processo à complexidade da tarefa. Para mudanças grandes, consolidar o entendimento e os critérios de aceitação antes de elaborar o plano de implementação. Seguir o procedimento de `docs/desenvolvimento.md`.

## Fluxo de desenvolvimento pelo Codex

Para desenvolver este projeto pelo Codex, as fontes do processo são este `AGENTS.md` e `docs/desenvolvimento.md`. Consultar `CLAUDE.md` como referência da arquitetura e dos invariantes do Hub; suas instruções de orquestração para Claude Code (modelos, esforço, aprovações e ciclos) não substituem o fluxo do Codex definido aqui. Não modificar `CLAUDE.md` para adaptar o processo do Codex sem um pedido específico do usuário.

- **Planejamento:** GPT-6.1 Sol (`gpt-6.1-sol`), esforço `high` ou `xhigh`, conduz esclarecimentos, sugestões, PRD, plano, tarefas/Issues e critérios de aceitação. Ajustar a profundidade à faixa da tarefa.
- **Implementação:** usar GPT-5.6 Terra (`gpt-5.6-terra`) nos agentes de implementação, registrando o esforço selecionado. Não substituir por outro modelo sem autorização do usuário. Lotes sem dependências entre si e com arquivos disjuntos podem rodar em paralelo. Lotes dependentes ou que compartilham arquivos devem ser executados em sequência por um único agente responsável pela cadeia.
- **Verificação:** chamar um agente independente **somente para grandes modificações ou grandes implementações (faixa completa)**. Ele usa GPT-6.1 Sol em esforço `high` ou `xhigh`, não participou da implementação, não modifica código nem testes e registra evidências, reprovações e pendências. Para pequenas correções, alterações e funcionalidades (faixas trivial e média), **não chamar o verificador independente**: a sessão principal revisa a mudança, executa os testes e confere os critérios de aceitação.
- **Teto:** no máximo **três ciclos totais por tarefa**. Ciclo 1 = implementação inicial + verificação; ciclos 2 e 3 = correções + nova verificação. Persistir o contador e não reiniciá-lo ao trocar agentes, fases ou sessões. Após a terceira reprovação, interromper e apresentar o diagnóstico.
- **Conclusão:** declarar implementação concluída com testes pertinentes passando e critérios de aceitação atendidos. Na faixa completa, exigir também aprovação explícita do verificador independente; nas faixas trivial e média, a sessão principal registra sua validação, sem criar um agente revisor. Verificação necessária não executada ou não verificável permanece pendente. Classificar pela abrangência e complexidade; uma funcionalidade nova pequena não exige revisão independente apenas por ser nova.

Selecionar explicitamente o modelo e o esforço dos subagentes nos mecanismos disponíveis do Codex. Se a configuração exigida não estiver disponível, informar a limitação antes da etapa afetada; não alegar que usou um modelo, esforço ou verificador independente que não foi utilizado. Registros e instruções detalhados em `docs/desenvolvimento.md`.

## Alterações mínimas e remoção de código substituído

Em código existente, corrigir a causa raiz com a menor alteração necessária, preservando o comportamento que já funciona. Não refatorar, renomear, reformatar nem mudar interfaces, dependências ou trechos fora do escopo do pedido.

Remover, na mesma alteração, o código antigo que foi substituído e os trechos que a própria mudança tornou obsoletos ou sem uso. Não deixar implementações antigas duplicadas, blocos comentados ou caminhos inativos como sobra da substituição. Antes de remover, conferir referências, chamadas e dependências para preservar comportamentos e compatibilidade ainda necessários. Essa remoção faz parte da mudança mínima; não autoriza limpar código legado alheio ao pedido. Detalhes em `docs/desenvolvimento.md` §4.1.

## Coding Style & Naming Conventions

Match surrounding code: four-space Python indentation, `snake_case` functions and variables, `PascalCase` classes, and uppercase constants. Frontend JavaScript uses camelCase and generally two-space indentation. No repository-wide formatter or linter configuration is present.

Read `CLAUDE.md`, `docs/desenvolvimento.md`, and the relevant topic document before changing code. Keep existing-code fixes focused. Cada funcionalidade nova deve ter uma pasta exclusiva dentro do projeto, com módulos que se encaixam como peças de Lego. Cada arquivo deve ter uma única responsabilidade funcional bem definida; separar por função ou parte da funcionalidade, nunca pelo número de linhas. Não há limite de linhas. Usar Flask blueprints e arquivos estáticos próprios e atualizar a documentação quando o comportamento mudar.

## Testing Guidelines

Use `tests/test_<feature>.py` and descriptive `test_*` functions. Existing tests use pytest, Flask test clients, mocks, and static frontend checks. Stub speech models and external processes rather than downloading models or invoking live services. Run focused tests during development and the full suite before submitting. No coverage threshold is configured.

## Commit & Pull Request Guidelines

Git history is unavailable in this checkout, so established message conventions cannot be verified. Use concise imperative commit subjects and focused changes. PRs should explain behavior changes, link relevant issues, report test results, and include screenshots for interface changes.

## Security & Configuration

Keep the unauthenticated bridge bound to `127.0.0.1:8765`; network access belongs through the protected mobile gateway. Review `VAULT`, `KPY`, `SPEAK_SRV`, and Chrome paths locally. Run assistant processes from the project through `hub_runtime.assistant`, with explicit access to the configured personal vault (`HUB_VAULT`). Preserve the shared `SPEAK_Q`, runtime file guards, and matching backend/frontend session limits.
