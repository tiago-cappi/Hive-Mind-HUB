# Plano

Status: implementação concluída e aprovada na revisão independente; backend adiado conforme escopo.
Ciclo: 2 de 3 utilizados. Ciclo 1 reprovado por CF-R1/CF-R2; ciclo 2 aprovado em GPT-6.1 Sol/high, com 229 testes passando.

## Execução

1. Criar `codex_frontend/`: blueprint somente de assets/catálogo, CSS do tema,
   desenho da galáxia extraído do protótipo, seleção de provedor e modelos.
2. Reutilizar os painéis e comportamentos existentes do Hub. Integrar através
   de carregamento de módulo e ganchos mínimos nos pontos de sessão/envio do
   `index.html`; registrar blueprint em `server.py`.
3. Distinguir sessões/seletores Claude e Codex. Bloquear execução Codex nesta
   etapa, preservando eventos Claude e espelho mobile em segundo plano.
4. Conferir visual no navegador; adicionar testes de integração de fronteiras,
   catálogo e navegação. Atualizar documentação frontend/arquitetura.
5. Rodar suíte completa e verificação independente somente leitura. Registrar
   resultado por critério e corrigir dentro do teto de três ciclos.

## Superfície existente

`server.py`: somente import e register_blueprint.
`index.html`: tag do módulo e ganchos explícitos mínimos para distinguir sessões,
filtrar navegação por provedor e impedir chamadas Claude nas sessões Codex.
Sem extrair/refatorar o frontend antigo nem mudar payloads/backend Claude.
Essa integração além da tag requer aprovação conforme desenvolvimento.md §5.5.

## Modelos e responsáveis

Sessão principal implementa a cadeia dependente; sua configuração efetiva é
gerida pelo app e não pode ser alterada/verificada por uma ferramenta desta
conversa. Não declarar uma seleção de modelo/esforço da sessão sem evidência.
Verificador independente: selecionar explicitamente `gpt-6.1-sol`, esforço
`high`, contexto novo, após implementação; não modifica código ou testes.

## Evidências iniciais

- Checkout sem Git: não há commits locais a produzir.
- Catálogo local `models_cache.json` lido somente para modelos e esforços.
- Fontes oficiais: https://learn.chatgpt.com/docs/models e
  https://learn.chatgpt.com/docs/config-file/config-reference.
- Suíte inicial em execução; resultado será registrado na verificação.
