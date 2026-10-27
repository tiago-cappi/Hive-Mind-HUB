# Animação das abelhas do protótipo Hive Mind

> **Status em 21/10/2026: CONCLUÍDA** — aprovada pela sessão principal no ciclo 1 (10/10/2026); o rig está em `HiveMind/frontend/static/bee-animation/`. Este arquivo é registro histórico do processo e pode descrever intenções já superadas; a referência do código atual está em `docs/hivemind/README.md`.

Faixa média. Plano aprovado pelo usuário em 10/10/2026: prévia isolada,
conferência visual e integração no protótipo existente. Ciclo atual: **1 de 3**.
Implementação e validação pela sessão principal; sem verificador independente.
A interface da sessão não expõe alteração de modelo/esforço; não se registra
uma seleção que não foi realizada.

## Objetivo e escopo

Usar as seis imagens fornecidas (corpo e duas asas por personagem) para animar
rainha, operárias e subagentes. Criar um módulo reutilizável e uma prévia local.
Substituir somente as abelhas procedurais do protótipo atual, preservando as
informações, gavetas, simulação, fluxos e demais elementos visuais.
Não inclui backend nem integração da terceira página ao Hub.

## Critérios de aceitação

- Asas alinhadas ao corpo, atrás dele, preservando as imagens originais.
- Rainha e operária reconhecíveis na prévia e nos tamanhos do protótipo.
- Processamento/coordenação, espera e repouso com movimentos distintos;
  pausa e redução de movimento respeitadas, inclusive preferência do sistema.
- Imagens presentes em células, subagentes e lista lateral; interação preservada.
- Módulo compartilhado entre prévia e protótipo, sem dependências adicionais.
- Movimento interrompido quando a página estiver oculta.

## Plano

1. Montar SVGs com imagens em camadas e CSS com pivôs por personagem.
2. Criar prévia com controles de estado, pausa, movimento e tamanho.
3. Conferir no navegador e substituir o método de renderização de abelhas.
4. Rever o escopo, verificar interações e executar a suíte pytest.

## Verificação

**Aprovado pela sessão principal, ciclo 1 de 3.**

- Prévia e protótipo conferidos visualmente em Chrome, viewport 1440 × 960.
  Imagens alinhadas e reconhecíveis nos tamanhos ampliado, célula e lista.
- Verificação executada em navegador real via Playwright: transformação das asas
  varia durante processamento; pausa conserva o quadro; seis estados, ritmo da
  rainha, redução manual e preferência do sistema validados.
- Listener de visibilidade conferido disparando o evento com a página marcada
  como oculta; CSS interrompe o movimento. Este item é uma verificação do listener,
  não uma medição de desempenho de uma aba em segundo plano.
- Seis imagens carregadas com dimensão original 1254 × 1254. Gaveta, seleção,
  subagentes, criação/exclusão de operária e estados da missão exercitados.
- Sem exceções JavaScript na execução. Prévia e protótipo usam o mesmo módulo.
- Método SVG procedural e três keyframes antigos removidos. Nenhuma imagem,
  código do Hub, backend ou runtime exportado support.js modificado.
- Suíte completa: **229 passed in 13.30s**.
  Comando: .venv/Scripts/python.exe -m pytest tests -q
  --basetemp .test-tmp/pytest-bees-run-final, com TEMP/TMP apontando para uma
  pasta temporária do projeto.

Limitações do ambiente foram contornadas sem alterar o produto: a primeira
execução de pytest não conseguiu criar temporários do sandbox; a segunda ficou
presa em subprocessos do ambiente. A execução com acesso aos temporários e
subprocessos locais passou. O navegador automatizado do plugin não inicializou;
a inspeção foi feita no Chrome por Playwright. Para testar o protótipo sem depender
na hora do CDN, a inspeção carregou localmente as mesmas versões React 18.3.1
que support.js já utiliza. O protótipo continua com o carregamento original do CDN.

Artefatos de inspeção e script de verificação ficam em .test-tmp/hivemind-bees/.
Ajustou-se um seletor do script de inspeção para o primeiro dos dois botões de
pausa existentes; não houve reprovação de comportamento nem ciclo de correção
no produto. Não há Git neste checkout; nenhum commit foi criado.
