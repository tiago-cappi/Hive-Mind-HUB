# Modelo dos agentes de implementação

Faixa trivial. Pedido explícito do usuário: alterar permanentemente o fluxo
para GPT-5.6 Terra nos agentes de implementação, mantendo GPT-6.1 Sol no
planejamento e na verificação. Ciclo atual: 1 de 3.

## Escopo e aceite

Atualizar AGENTS.md e docs/desenvolvimento.md, as duas fontes do fluxo Codex.
Preservar os modelos do planejador/verificador, faixas, aprovação de plano,
separação de papéis e teto de ciclos. Remover a permissão anterior de escolher
outro modelo nos agentes de implementação; nova substituição exige autorização.
Não alterar CLAUDE.md nem iniciar a integração do frontend nesta tarefa.

## Validação

Concluído e validado pela sessão principal no ciclo 1, sem agente independente
para esta alteração documental pequena. As quatro referências ativas ao modelo
de implementação foram atualizadas; planejador e verificador continuam GPT-6.1
Sol. A antiga permissão de escolher um modelo de menor custo foi removida.
CLAUDE.md e código do produto não foram alterados.

Suíte completa: **229 passed in 25.01s**, com .venv/Scripts/python.exe -m pytest
tests -q e temporários em uma pasta própria de .test-tmp. Nenhuma reprovação.

## Disponibilidade

O mecanismo de subagentes desta sessão não oferece gpt-5.6-terra. A preferência
foi registrada para uso futuro, mas não se declara que Terra foi executado.
Informar a limitação antes de uma etapa que exija esse agente.
