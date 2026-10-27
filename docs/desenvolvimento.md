# Desenvolvimento do Hub C.O.R.E.

> Processo definido em 28/08/2026; adaptado para desenvolvimento pelo Codex em
> 07/10/2026. As fontes deste processo são o `AGENTS.md` da raiz e este documento.
> A referência antiga à skill `desenvolver-hub` no vault e as instruções de orquestração do
> `CLAUDE.md` pertencem ao fluxo do Claude Code e não definem o fluxo do Codex.

Como conduzir correções, modificações e funcionalidades novas no Hub pelo Codex.
O objetivo é esclarecer o pedido, implementar com escopo controlado e validar
o resultado. Reservar a verificação independente para mudanças grandes e limitar
o consumo com três ciclos totais.
A conversa pode ser por texto ou voz; requisitos e decisões ficam registrados.

Índice relacionado: `arquitetura.md` (componentes e fluxos), `operacao.md`
(execução e testes) e `CLAUDE.md` (referência da arquitetura e dos invariantes).
Quando houver divergência de modelos ou de orquestração, aplicar o fluxo do
Codex deste documento e do `AGENTS.md`. Isso não altera o uso do Claude CLI
pelo próprio Hub nem autoriza modificar `CLAUDE.md`.

---

## 1. Quem faz o quê

| Papel | Modelo e esforço | Responsabilidade | Conversa com o usuário? |
|---|---|---|---|
| Planejador / orquestrador | Sessão principal com GPT-6.1 Sol (`gpt-6.1-sol`), `high` ou `xhigh` | Esclarecer, sugerir, planejar, registrar e coordenar | Sim |
| Implementador | GPT-5.6 Terra (`gpt-5.6-terra`), esforço definido conforme o lote e registrado | Implementar apenas o lote ou a cadeia atribuída | Não; reporta à sessão principal |
| Verificador (somente faixa completa) | GPT-6.1 Sol, `high` ou `xhigh`, em contexto independente | Revisar mudanças grandes, testar, conferir critérios e emitir veredito | Não; reporta à sessão principal |

Nas faixas trivial e média, a própria sessão principal revisa e testa a mudança;
não criar um verificador independente para pequenas correções, alterações ou
funcionalidades. Na faixa completa, usar o verificador independente.

Usar `high` como padrão para planejamento e verificação; escolher `xhigh`
quando a complexidade exigir maior profundidade. Registrar modelo e esforço
selecionados. Nos agentes de implementação, usar GPT-5.6 Terra; ajustar e registrar
o esforço conforme a complexidade do lote. Não substituir por outro modelo sem
autorização do usuário nem reduzir o rigor da verificação.

A sessão principal concentra perguntas, aprovações, decisões de escopo e
relatórios ao usuário. O implementador que precisar de uma decisão deve
reportá-la, sem presumir a resposta. O verificador não pode ter participado da
implementação ou das correções e não modifica código nem testes.

A sessão principal cria os agentes e controla os lotes; os subagentes não
criam outros subagentes neste fluxo. A organização tem no máximo dois níveis.
Selecionar explicitamente modelo e esforço na criação dos agentes ou na
configuração disponível do Codex. O Markdown não muda sozinho a seleção real
da sessão. Se não for possível usar o modelo, o esforço ou o agente independente
exigido, informar a limitação antes da etapa afetada e não simular conformidade.

---

## 2. As três faixas

Classificar antes de agir pela abrangência e complexidade do trabalho. Mudanças
grandes incluem funcionalidades amplas, alterações estruturais e integrações
complexas entre componentes ou fluxos. O número de linhas ou arquivos, isoladamente,
não define a faixa. Uma funcionalidade pequena pode ter vários arquivos por
modularidade sem exigir o processo completo. Se a classificação estiver ambígua,
esclarecer o escopo com o usuário. Ele pode pedir "faz simples" ou "faz completo".

| Faixa | Exemplos | Fluxo |
|---|---|---|
| **Trivial** | typo, bug pontual e óbvio, ajuste de texto ou estilo | escopo e aceite concisos → implementar → validação pela sessão principal e suíte pytest → encerrar |
| **Média** | pequena alteração local de comportamento, rota simples ou funcionalidade nova pequena | plano curto → aprovação → implementar → validação pela sessão principal e suíte pytest → encerrar |
| **Completa** | grande funcionalidade, grande modificação estrutural ou integração complexa entre componentes e fluxos | pipeline completo, com verificação independente (§3) |

Na faixa trivial, objetivo, escopo, aceite e eventuais Issues podem ficar em um
registro curto; na média, usar um plano curto. Ambas são validadas pela sessão
principal, sem agente verificador independente, e mantêm os testes e o teto de
três ciclos totais (§3.F). A faixa completa exige todos os registros e etapas
de §3, inclusive o verificador independente. A dispensa do agente nas mudanças
pequenas não dispensa conferir o comportamento e executar os testes.

### 2.1 Esclarecimento em todas as faixas

O esclarecimento e as sugestões de §3.A valem para **correções, modificações e
funcionalidades novas nas três faixas**, antes da implementação. A profundidade
acompanha a complexidade do pedido: uma correção bem definida exige pouco
esclarecimento; uma funcionalidade grande pode exigir várias rodadas. Quando
houver ambiguidades relevantes, fazer quantas perguntas forem necessárias até
que o pedido esteja suficientemente definido.

---

## 3. Pipeline completo (faixa completa)

### A — Esclarecimento

A sessão principal conduz o esclarecimento e ajuda o usuário a construir a
solução quando ele ainda não souber exatamente como ela deve funcionar. Antes
de perguntar, consultar o código e a documentação para responder às dúvidas
técnicas que possam ser verificadas diretamente.

- **Perguntas objetivas, em rodadas curtas:** fazer uma pergunta por vez ou
  pequenos grupos de perguntas relacionadas, conforme o meio da conversa e a
  complexidade do pedido. Esclarecer objetivo, comportamento e aparência
  esperados, casos-limite, alcance e resultado esperado.
- **Sugestões concretas:** quando o usuário estiver indeciso ou solicitar
  orientação, apresentar alternativas com exemplos de funcionamento, explicar
  vantagens e limitações e recomendar uma abordagem fundamentada no projeto.
  Os exemplos devem ajudar o usuário a avaliar as opções.
- **Conversa iterativa:** retomar as perguntas quando uma resposta revelar novas
  dúvidas e ajustar as sugestões conforme o entendimento evoluir. Não assumir
  decisões que alterem significativamente a experiência, o escopo ou a
  arquitetura sem esclarecer com o usuário.
- **Consolidar o entendimento:** resumir o que será feito, como deverá funcionar,
  os limites do escopo e como verificaremos que atende ao pedido. Para mudanças
  grandes, consolidar também os critérios de aceitação antes de elaborar o
  plano de implementação (§3.B).

### B — PRD, plano e Issues em disco

Na faixa completa, criar uma pasta por tarefa em
`docs/planos/AAAA-MM-DD_assunto/`, com:

1. **`prd.md`** — objetivo, requisitos, comportamento esperado, fora de escopo
   e critérios de aceitação verificáveis, um por requisito.
2. **`plano.md`** — fases pequenas, arquivos afetados, decisões, modelo/esforço,
   dependências, agentes responsáveis e o contador de ciclos da tarefa.
3. **`issues.md`** — tarefas com identificadores, requisitos relacionados,
   arquivos, dependências, critérios de aceitação, responsável e status.
   Registrar também as reprovações e correções requeridas.
4. **`verificacao.md`** — evidências, testes e vereditos de cada ciclo, incluindo
   o resultado global. Preservar o histórico das verificações anteriores.

Preparar instruções de execução para cada implementador com objetivo, lote,
arquivos permitidos, dependências, critérios de aceitação, decisões e referências
aos registros. Um agente deve entender a tarefa sem conhecer a conversa inteira.

Nas faixas trivial e média, esses registros podem ser seções de um único arquivo
`docs/planos/AAAA-MM-DD_assunto.md`. Ainda registrar o contador e as reprovações.
`docs/prd.md`, `docs/issues.md` e `docs/_dev-loop-archive/` são referências
históricas do ForestOS; não sobrescrevê-las para tarefas novas.

Registros do desenvolvimento pelo Codex ficam dentro deste repositório. Não
exigir a skill externa do Claude ou escrita no vault para conduzir o processo.
Persistir plano, decisões e resultado para permitir retomada entre sessões.

### C — Aprovação do plano

Apresentar um resumo do plano por texto ou voz e obter aprovação explícita antes
da implementação na faixa completa ou média. Uma aprovação já dada para o
escopo continua válida; esclarecer novamente apenas decisões ou alterações de
escopo relevantes. Na faixa trivial, o pedido claro do usuário define o escopo.

### D — Implementação

- Usar GPT-5.6 Terra (`gpt-5.6-terra`) nos agentes de implementação; a sessão
  principal pode implementar um lote quando o fluxo permitir ou atribuí-lo a
  um subagente conforme o planejamento. Na faixa completa, manter um
  verificador independente com GPT-6.1 Sol.
- **Paralelizar apenas lotes sem dependências entre si e com arquivos disjuntos.**
  Arquivos separados não bastam: se B depende do resultado de A, executar A antes
  de B. Registrar esse vínculo e o resultado necessário para liberar B.
- **Cadeias dependentes ou lotes que compartilham arquivos entram em sequência**,
  sob um único agente implementador responsável pela cadeia. Não permitir dois
  implementadores escrevendo simultaneamente no mesmo arquivo.
- A sessão principal libera cada etapa quando os pré-requisitos do plano estiverem
  atendidos. Mudanças nas dependências exigem atualizar o planejamento.
- Cada implementador respeita os invariantes técnicos do Hub, as regras deste
  processo, a superfície de mudança (§4) e a modularidade (§5).
- Quando o checkout possuir Git, fazer um commit por fase concluída.
- Falha repetida ou conflito com uma guarda exige reportar e replanejar dentro do
  ciclo atual; não abrir ciclos extras fora do contador de §3.F.

### E — Validação conforme a faixa

**Faixas trivial e média:** a sessão principal revisa o código e as remoções de
trechos substituídos, confere os critérios de aceitação e executa os testes
pertinentes e a suíte pytest. Registrar o resultado no registro curto da tarefa
ou no plano, com eventuais falhas e limitações. **Não chamar um agente verificador
independente para pequenas correções, alterações ou funcionalidades.**

**Faixa completa — verificação independente:** usar um agente GPT-6.1 Sol em esforço `high` ou `xhigh`, em contexto próprio,
que não participou da implementação ou das correções. Fornecer o PRD, plano,
Issues, arquivos alterados e estado atual da tarefa; não orientar o agente a
confirmar a hipótese dos implementadores.

1. Revisar o código modificado e sua integração, procurando regressões e
   violações de escopo, segurança, invariantes e modularidade. Conferir também
   a remoção segura dos trechos substituídos ou tornados obsoletos pela mudança.
2. Executar os testes pertinentes e a suíte do Hub na raiz:
   `./.venv/Scripts/python.exe -m pytest tests -q`.
3. Conferir cada critério de aceitação, exercitando o comportamento real quando
   necessário. Testes passando não substituem verificar o objetivo do pedido.
4. Registrar por critério: **passou**, **falhou** ou **não verificável**, com
   evidência, teste executado ou motivo da limitação.
5. Para reprovações, registrar nas Issues o critério afetado, o problema, sua
   localização, passos de reprodução, resultado esperado e observado, evidências
   e o que precisa ser corrigido. Atualizar o relatório de verificação do ciclo.
6. Emitir um veredito global: **aprovado**, **reprovado** ou **pendente de
   verificação**. Aprovar somente com os testes pertinentes passando, critérios
   atendidos e nenhuma pendência necessária à aceitação.

O verificador é somente leitura **no código e nos testes**; pode registrar seu
relatório e as Issues. Não implementa correções nem enfraquece testes ou critérios
para aprovar. A sessão principal consolida os registros se o agente não puder
escrevê-los. Esse agente participa somente de grandes modificações e grandes
implementações (faixa completa). Nas demais faixas, a sessão principal faz a
validação. Informar limitações de ambiente sem declarar como aprovado o que não
foi verificado.

### F — Ciclos de implementação e verificação, com teto

**Máximo de três ciclos totais por tarefa, incluindo o inicial.** Na faixa
completa, a verificação é do agente independente; nas faixas trivial e média,
é da sessão principal, sem criar um agente revisor:

| Ciclo | Trabalho permitido |
|---|---|
| **1** | Implementação inicial e validação conforme a faixa (§3.E) |
| **2** | Correções das falhas do ciclo 1 e nova validação conforme a faixa |
| **3** | Correções das falhas do ciclo 2 e última validação conforme a faixa |

Registrar o ciclo antes de começar sua implementação. O contador pertence à
tarefa inteira: fases e lotes paralelos não ganham contadores separados. Não
reiniciar ao trocar de agente, criar outro verificador, retomar uma sessão ou
mudar o nome de uma fase. Interromper cedo quando a validação aprovar.

Havendo reprovação, a sessão principal atualiza o plano e encaminha o relatório
e as Issues aos implementadores responsáveis, com instruções de correção
restritas aos problemas encontrados. Após as correções, verificar o estado
integrado atual; um veredito anterior não aprova código alterado depois dele.

Se ao terminar o ciclo 3 o resultado estiver reprovado ou pendente de verificação,
**parar**. Registrar ciclos utilizados, falhas, evidências e bloqueios e apresentar
o diagnóstico ao usuário. Não iniciar um quarto ciclo automaticamente nem marcar
a tarefa como concluída. Uma continuação exige uma decisão explícita do usuário.

### G — Encerramento

Declarar a implementação concluída somente com testes pertinentes passando e
critérios de aceitação atendidos. Na faixa completa, exigir aprovação explícita
do verificador independente sobre o estado final. Nas faixas trivial e média,
a sessão principal registra a validação, sem chamar um agente revisor. Registrar
o resultado, ciclos utilizados e status final no registro da tarefa ou no plano
e nas Issues. Por texto ou voz, resumir o que mudou e como foi validado. Quando
houver falha ou verificação pendente, apresentar o diagnóstico e o estado incompleto.

---

## 4. Superfície de mudança

A regra de maior impacto no dia a dia. **Entra no prompt de todo subagente
implementador** e vale para as três faixas.

### 4.1 Código que já existe (bug, correção, ajuste)

Mudança **mínima e objetiva**:

- Corrija a **causa raiz**, com a menor superfície possível. Escopo mínimo **não
  é** remendo: um `if` que esconde o sintoma é proibido.
- **Remover o código substituído:** apagar, na mesma alteração, a implementação
  antiga que foi substituída e os trechos que a própria mudança tornou obsoletos
  ou sem uso, incluindo imports, variáveis, helpers e caminhos inativos diretamente
  relacionados. Não manter versões antigas duplicadas nem blocos comentados
  como sobra da substituição.
- **Conferir antes de apagar:** verificar referências, chamadas e dependências
  para não remover comportamento ou compatibilidade ainda necessários. Confirmar
  com os testes que a substituição preserva o que deve continuar funcionando.
- **Nada de faxina não solicitada** — não refatore, renomeie, reordene nem
  reformate o que não é necessário para a correção. A remoção dos trechos que
  esta mudança substituiu faz parte da correção mínima; não autoriza eliminar
  código legado alheio ao pedido.
- Não troque bibliotecas, não mude assinatura pública nem formato de payload sem
  que isso seja o objetivo declarado da tarefa.
- Leia o trecho e entenda **por que ele está como está** antes de editar. Este
  código tem invariantes não óbvias: protocolo de fala nos dois lados,
  `SPEAK_Q`, `MAX_SESS`/`MAX_TABS`, guardas nomeadas, execução no projeto com acesso explícito ao vault.
- Prefira poucas linhas em poucos arquivos a reescrever um bloco.
- Se a correção correta **exigir** refatoração maior, ou tocar uma regra crítica
  do `CLAUDE.md`: **pare, não implemente**, reporte à sessão principal — ela
  pergunta ao usuário. Essa decisão nunca é do subagente.
- Regressão: o que já funcionava continua funcionando; a suíte pytest passa
  antes e depois.

### 4.2 Funcionalidade nova

**Liberdade** para criar quantos arquivos e módulos forem necessários, desde que:

- siga as convenções que o Hub já usa (estrutura, nomes, estilo, camadas) em vez
  de introduzir um padrão paralelo;
- respeite as regras críticas do `CLAUDE.md` da raiz;
- venha com documentação em `docs/` **no mesmo commit**;
- não force reescrita de código antigo que funciona — se a integração exigir
  mexer no existente, **essa parte volta a valer §4.1**.

---

## 5. Modularidade

> Decisão de 28/08/2026, tomada por voz com o usuário.

### 5.1 O que NÃO muda

**`server.py` (1312 linhas) e `index.html` (3188 linhas) ficam como estão.** Não
há refatoração retroativa, nem em massa nem "aos poucos, de passagem". O Hub
funciona; reescrever monolito que funciona é a forma mais eficiente de quebrá-lo,
e contraria diretamente §4.1.

Se um dia essa divisão for desejada, será uma **tarefa dedicada** de faixa
completa, com PRD, critérios de aceite e verificação própria — nunca um efeito
colateral de outra tarefa.

### 5.2 O que muda: tudo que nascer daqui para frente

Cada funcionalidade nova vive em **uma pasta exclusiva dentro do projeto**,
na raiz do Hub, com módulos que se encaixam como **peças de Lego**. Cada arquivo
representa uma única responsabilidade funcional bem definida ou uma parte coesa
da funcionalidade. A separação é por função e responsabilidade, independentemente
do número de linhas. Uma responsabilidade pode precisar de muitas linhas e outra
de poucas. Exemplo de uma funcionalidade "agenda":

```
agenda/
  __init__.py      # expõe o blueprint
  rotas.py         # blueprint Flask: as URLs (/agenda, /agenda/criar…)
  logica.py        # regras de negócio — não sabe nada de web
  dados.py         # leitura/escrita (arquivo, JSON, vault)
  static/
    agenda.js      # JS da tela (ES module)
    agenda.css     # CSS da tela
```

O **blueprint** é o mecanismo padrão do Flask para isso e funciona como o encaixe
da peça de Lego: a pasta é o bloco, o blueprint é o pino. No `server.py` entram
**duas linhas** — o import e o `app.register_blueprint(...)`. O servidor não
sabe nada de dentro da pasta. Remover a funcionalidade = apagar a pasta e as
duas linhas; nada mais no sistema fica sabendo que ela existiu.

Benefício direto para o processo de §3.D: pastas independentes são **lotes
naturalmente disjuntos**, então funcionalidades diferentes paralelizam sem
conflito e sem esbarrar na guarda do vault.

### 5.3 Frontend

Tela nova **não** entra no `index.html`. O JS e o CSS da funcionalidade vivem em
arquivos dentro da pasta dela; o `index.html` ganha apenas a linha que carrega o
módulo (`<script type="module" src="…">`). ES modules nativos — sem build, sem
bundler, sem ferramenta nova no projeto.

### 5.4 Separação por responsabilidade, sem limite de linhas

**Não existe limite fixo de linhas.** Dividir por função ou parte da funcionalidade:
cada arquivo deve ter uma responsabilidade clara, explicável em uma frase, com
interfaces definidas para se encaixar nos demais módulos.

Aqui, função significa **responsabilidade funcional**. Um arquivo pode conter
várias funções de código relacionadas à mesma responsabilidade; não há obrigação
de criar um arquivo para cada `def` ou função JavaScript. O que determina a
separação é a finalidade, não o tamanho.

- Não juntar responsabilidades independentes somente para reduzir o número de
  arquivos; também não fragmentar uma responsabilidade apenas para encurtá-la.
- Se surgirem responsabilidades distintas, identificar seus limites no
  planejamento e organizar os módulos por esses limites.
- O crescimento de um arquivo, por si só, não exige divisão nem bloqueia a
  implementação. A divisão é justificada pelas responsabilidades e segue o
  escopo e a arquitetura aprovados.

### 5.5 Integração com o existente

Se a funcionalidade nova precisar tocar `server.py` ou `index.html`, o toque é
**mínimo** (registrar o blueprint, carregar o script) e volta a valer §4.1.
Qualquer coisa além disso: **pare e pergunte**.

---

## 6. Regras transversais

1. **Nunca pular a validação.** Nas faixas trivial e média, a sessão principal
   revisa e testa, sem agente verificador. Somente a faixa completa exige
   verificação independente. Todas seguem §3.E, executam os testes pertinentes
   e a suíte pytest da raiz e respeitam o teto de três ciclos totais de §3.F.
2. **Restrição dura vive em código, não em prompt.** Validação, limite e guarda
   são código determinístico; o modelo entra só onde há interpretação semântica.
3. **Erro se classifica por tipo**: rede → retry; rate limit → esperar; entrada
   inválida → validar; violação de regra → parar e avisar.
4. **Documentação junto com o código**, no mesmo commit.
5. **Ler tarde**: leia cada arquivo imediatamente antes de editá-lo — o Hub
   roda até seis sessões simultâneas, com a guarda do projeto no runtime.

---

## 7. Fundamentação

Nas mudanças grandes, o desenho separa planejamento, implementação e verificação
em papéis distintos. Nas pequenas, a sessão principal implementa e valida para
reduzir o consumo de agentes. O processo mantém contratos explícitos,
dependências registradas, estado durável em disco,
aprovação humana do escopo e ciclos limitados. O verificador tem acesso somente
leitura ao código e aos testes; decisões e evidências ficam nos registros.

Levantamento completo, com fontes: `<vault>/pesquisas/Programacao por grafos com
agentes de IA.md`.

## 8. Fronteira entre projeto e acervo pessoal

Código, testes, documentação, configuração, instruções operacionais, skills,
agentes e registros de desenvolvimento específicos do Hub ficam neste projeto.
O vault guarda notas, ideias, memória, transcript, histórico mobile e relatórios
visuais pessoais. O código HTML/JS de um relatório pessoal faz parte do acervo,
não é uma funcionalidade do projeto.

O CLI de uso cotidiano executa por `hub_runtime.assistant` a partir do projeto,
com acervo explícito por `HUB_VAULT`, configuração local e hooks do projeto.
Instruções operacionais são separadas do pipeline de desenvolvimento deste
documento. Não colocar skills, hooks, agentes ou docs do Hub no vault.
Não copiar venvs globais: recriar a voz por `hub_runtime/voice/requirements-lock.txt`.
Instalações/autenticação do fornecedor e recursos globais genéricos podem
continuar no sistema; não são a fonte dos componentes específicos do Hub.
