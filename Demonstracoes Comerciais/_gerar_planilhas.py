# Script utilitário para gerar as planilhas de demonstração comercial do Hub.
# Rodar com: python _gerar_planilhas.py
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

OURO = "B88A3F"
FUNDO_HEADER = "1A2226"
BRANCO = "FFFFFF"

HEADER_FONT = Font(bold=True, color=BRANCO, size=11)
HEADER_FILL = PatternFill("solid", fgColor=FUNDO_HEADER)
TITLE_FONT = Font(bold=True, color=OURO, size=14)
THIN = Side(style="thin", color="CCCCCC")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def estiliza_cabecalho(ws, linha, ncols):
    for c in range(1, ncols + 1):
        cell = ws.cell(row=linha, column=c)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = BORDER


def auto_largura(ws, larguras):
    for i, w in enumerate(larguras, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w


def titulo(ws, texto, ncols):
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=ncols)
    c = ws.cell(row=1, column=1, value=texto)
    c.font = TITLE_FONT
    c.alignment = Alignment(horizontal="left")
    ws.row_dimensions[1].height = 24


# ---------------------------------------------------------------------------
# 1) Painel de gestão de consultório — dados fictícios
# ---------------------------------------------------------------------------
wb1 = Workbook()

ws = wb1.active
ws.title = "Resumo"
titulo(ws, "Painel de Gestão do Consultório — Agosto de 2026 (dados fictícios)", 2)
resumo = [
    ("Indicador", "Valor"),
    ("Pacientes atendidos no mês", 86),
    ("Consultas realizadas", 94),
    ("Faltas (no-show)", 8),
    ("Taxa de comparecimento", "91%"),
    ("Faturamento do mês", "R$ 25.800,00"),
    ("Ticket médio por consulta", "R$ 300,00"),
    ("Horário mais procurado", "Tarde (12h–18h)"),
]
for r, row in enumerate(resumo, start=2):
    for c, val in enumerate(row, start=1):
        ws.cell(row=r, column=c, value=val).border = BORDER
estiliza_cabecalho(ws, 2, 2)
auto_largura(ws, [32, 20])

ws2 = wb1.create_sheet("Consultas Semanais")
titulo(ws2, "Consultas realizadas por semana", 2)
semanas = [
    ("Semana", "Consultas"),
    ("07 a 13/jul", 18),
    ("14 a 20/jul", 20),
    ("21 a 27/jul", 19),
    ("28/jul a 03/ago", 22),
    ("04 a 10/ago", 24),
    ("11 a 17/ago", 21),
]
for r, row in enumerate(semanas, start=2):
    for c, val in enumerate(row, start=1):
        ws2.cell(row=r, column=c, value=val).border = BORDER
estiliza_cabecalho(ws2, 2, 2)
auto_largura(ws2, [22, 14])

ws3 = wb1.create_sheet("Faturamento Mensal")
titulo(ws3, "Faturamento dos últimos 6 meses", 2)
fat = [
    ("Mês", "Faturamento (R$)"),
    ("Março/2026", 17400),
    ("Abril/2026", 19200),
    ("Maio/2026", 21000),
    ("Junho/2026", 22500),
    ("Julho/2026", 24300),
    ("Agosto/2026", 25800),
]
for r, row in enumerate(fat, start=2):
    for c, val in enumerate(row, start=1):
        ws3.cell(row=r, column=c, value=val).border = BORDER
estiliza_cabecalho(ws3, 2, 2)
auto_largura(ws3, [18, 20])

ws4 = wb1.create_sheet("Horários Populares")
titulo(ws4, "Distribuição de consultas por período do dia", 2)
hor = [
    ("Período", "Consultas"),
    ("Manhã (8h–12h)", 22),
    ("Tarde (12h–18h)", 41),
    ("Noite (18h–21h)", 23),
]
for r, row in enumerate(hor, start=2):
    for c, val in enumerate(row, start=1):
        ws4.cell(row=r, column=c, value=val).border = BORDER
estiliza_cabecalho(ws4, 2, 2)
auto_largura(ws4, [20, 14])

ws5 = wb1.create_sheet("Pacientes")
titulo(ws5, "Carteira de pacientes (amostra fictícia)", 4)
pacientes = [
    ("Paciente", "Sessões no mês", "Última consulta", "Status"),
    ("Mariana Silva", 4, "19/08/2026", "Ativo"),
    ("João Pedro Alves", 2, "15/08/2026", "Ativo"),
    ("Carla Nogueira", 3, "20/08/2026", "Ativo"),
    ("Rafael Torres", 1, "05/08/2026", "Inativo"),
    ("Beatriz Lima", 4, "18/08/2026", "Ativo"),
    ("Eduardo Ramos", 2, "12/08/2026", "Ativo"),
    ("Fernanda Costa", 3, "21/08/2026", "Ativo"),
    ("Gustavo Pires", 1, "02/08/2026", "Inativo"),
]
for r, row in enumerate(pacientes, start=2):
    for c, val in enumerate(row, start=1):
        ws5.cell(row=r, column=c, value=val).border = BORDER
estiliza_cabecalho(ws5, 2, 4)
auto_largura(ws5, [24, 16, 18, 12])

wb1.save("dados/consultorio_dashboard.xlsx")

# ---------------------------------------------------------------------------
# 2) Agenda de consultas — arquivo "vivo", usado na demonstração de voz
# ---------------------------------------------------------------------------
wb2 = Workbook()
ws = wb2.active
ws.title = "Agenda"
titulo(ws, "Agenda de Consultas — semana de 21 a 28/08/2026", 6)
cols = ("Data", "Hora", "Paciente", "Tipo", "Status", "Observação")
agenda = [
    cols,
    ("21/08/2026", "09:00", "Mariana Silva", "Retorno", "Confirmada", ""),
    ("21/08/2026", "14:00", "Fernanda Costa", "Retorno", "Confirmada", ""),
    ("22/08/2026", "10:00", "Eduardo Ramos", "Retorno", "Confirmada", ""),
    ("24/08/2026", "16:00", "Carla Nogueira", "Retorno", "Confirmada", ""),
    ("25/08/2026", "11:00", "Beatriz Lima", "Retorno", "Confirmada", ""),
    ("26/08/2026", "15:00", "João Pedro Alves", "Retorno", "Confirmada", ""),
]
for r, row in enumerate(agenda, start=2):
    for c, val in enumerate(row, start=1):
        ws.cell(row=r, column=c, value=val).border = BORDER
estiliza_cabecalho(ws, 2, 6)
auto_largura(ws, [14, 10, 22, 12, 14, 28])
wb2.save("dados/agenda_consultas.xlsx")

# ---------------------------------------------------------------------------
# 3) Comparativo antes e depois do Hub
# ---------------------------------------------------------------------------
wb3 = Workbook()
ws = wb3.active
ws.title = "Comparativo"
titulo(ws, "Rotina do consultório: antes e depois do Hub C.O.R.E.", 3)
comp = [
    ("Indicador", "Antes", "Depois"),
    ("Horas por semana organizando agenda", 5.0, 1.0),
    ("Faltas por mês (no-show)", 12, 8),
    ("Horas administrativas economizadas por mês", 0, 16),
    ("Satisfação do paciente (nota de 0 a 10)", 7.8, 9.1),
]
for r, row in enumerate(comp, start=2):
    for c, val in enumerate(row, start=1):
        ws.cell(row=r, column=c, value=val).border = BORDER
estiliza_cabecalho(ws, 2, 3)
auto_largura(ws, [42, 12, 12])
wb3.save("dados/comparativo_antes_depois.xlsx")

# ---------------------------------------------------------------------------
# 4) Dado real do dia — cotação do dólar (AwesomeAPI)
# ---------------------------------------------------------------------------
wb4 = Workbook()
ws = wb4.active
ws.title = "Dólar Hoje"
titulo(ws, "Cotação do Dólar (USD/BRL) — dado real, fonte AwesomeAPI", 2)
dolar = [
    ("Indicador", "Valor"),
    ("Data/hora da cotação", "21/08/2026 15:34:59"),
    ("Compra (bid)", "R$ 5,1353"),
    ("Venda (ask)", "R$ 5,1356"),
    ("Variação no dia", "-1,10921%"),
    ("Máxima do dia", "R$ 5,1951"),
    ("Mínima do dia", "R$ 5,1347"),
    ("Fonte", "economia.awesomeapi.com.br"),
]
for r, row in enumerate(dolar, start=2):
    for c, val in enumerate(row, start=1):
        ws.cell(row=r, column=c, value=val).border = BORDER
estiliza_cabecalho(ws, 2, 2)
auto_largura(ws, [26, 26])
wb4.save("dados/dado_real_hoje.xlsx")

print("Planilhas geradas em dados/")
