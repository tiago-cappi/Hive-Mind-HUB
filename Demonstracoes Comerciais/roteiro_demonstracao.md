# Roteiro de demonstração comercial do Hub C.O.R.E.

Pacote de demonstração montado em 21/08/2026 para apresentar o Hub como
produto comercializável para pequenos e médios negócios, usando um
consultório de psicologia como cenário de exemplo.

## O que existe nesta pasta

- `dados/consultorio_dashboard.xlsx` — painel de gestão do consultório
  (KPIs, consultas semanais, faturamento mensal, horários populares e
  carteira de pacientes). Dados fictícios.
- `dados/agenda_consultas.xlsx` — agenda da semana. É um arquivo **vivo**:
  a demonstração de agendamento por voz grava de verdade nessa planilha.
- `dados/comparativo_antes_depois.xlsx` — quatro indicadores comparando a
  rotina do consultório sem e com o Hub. Dados fictícios.
- `dados/dado_real_hoje.xlsx` — cotação real do dólar (USD/BRL) no momento
  em que este pacote foi gerado, para mostrar que o Hub também busca
  informação real na web.
- `_gerar_planilhas.py` — script que gera as quatro planilhas acima; rodar
  de novo a qualquer momento para atualizar os dados fictícios ou o dado
  real do dia (`python _gerar_planilhas.py`, precisa da lib `openpyxl`).

Os quatro relatórios visuais correspondentes já foram salvos em
`_agentes/relatorios/` do vault do Obsidian e abrem sozinhos na tela do
Hub (a sonda de relatórios detecta e exibe automaticamente):

1. Painel de gestão do consultório (`painel_gestao_consultorio.html`)
2. Agenda semanal (`agenda_semanal_consultorio.html`)
3. Cotação do dólar hoje (`cotacao_dolar_hoje.html`)
4. Comparativo antes e depois (`comparativo_antes_depois_hub.html`)

## Roteiro sugerido (nessa ordem)

**1. Abertura — painel de gestão.** Peça por voz: "Cláudio, me mostra o
painel de gestão do consultório." O painel já vai estar aberto (foi gerado
antes), mas pedir de novo mostra que ele é gerado sob demanda. Comente os
números em voz alta: pacientes atendidos, taxa de comparecimento,
faturamento do mês, horário mais concorrido.

**2. Agendamento por voz — o momento mais forte.** Peça, com a agenda
semanal na tela: "Cláudio, agenda uma consulta pra [nome de alguém] na
[dia] às [hora]." Isso não é encenado: o Claude que atende a sessão de voz
tem acesso real a arquivos, então ele abre `dados/agenda_consultas.xlsx`,
adiciona a linha de verdade e pode gerar um relatório atualizado da agenda
na hora. Vale repetir com um pedido de remarcação ou cancelamento pra
mostrar que ele também edita e apaga.

**3. Comparativo antes e depois.** Peça: "Cláudio, me mostra o comparativo
de antes e depois do Hub." Reforça o argumento de venda: menos tempo
organizando agenda, menos faltas, mais satisfação — tudo com número.

**4. Dado real do dia.** Peça: "Cláudio, como está o dólar hoje?" — ou
troque por uma notícia do dia, à escolha na hora. Mostra que o sistema não
serve só para dados internos do negócio: ele busca qualquer informação
pública e transforma em relatório visual na hora, pra qualquer segmento.

## Observações

- Todos os números de consultório, pacientes e faturamento são fictícios,
  criados só para a demonstração.
- A cotação do dólar é real, mas fica desatualizada com o tempo — rode
  `_gerar_planilhas.py` de novo perto da apresentação se quiser um valor
  fresco, ou simplesmente peça "Cláudio, me mostra a cotação do dólar
  agora" na hora, ao vivo.
- Os relatórios HTML ficam no acervo do vault (aba RELATÓRIOS do Hub) até
  serem excluídos manualmente pelo visor.
