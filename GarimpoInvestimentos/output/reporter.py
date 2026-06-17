import csv
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.formatting.rule import CellIsRule
from openpyxl.chart import BarChart, Reference
from openpyxl.chart.label import DataLabelList

from GarimpoInvestimentos.core.paths import OUTPUT_DIR

def export_results(resultados: list[dict]):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_filename = str(OUTPUT_DIR / f"garimpo_resultados_{timestamp}.csv")
    xlsx_filename = str(OUTPUT_DIR / f"garimpo_resultados_{timestamp}.xlsx")

    # CSV
    fieldnames = ["Ativo", "Sentimento", "Score", "Resumo", "Data", "Preço USD"]
    with open(csv_filename, mode="w", newline="", encoding="utf-8-sig") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for r in resultados:
            writer.writerow({
                "Ativo": r.get("ativo", "").upper(),
                "Sentimento": r.get("sentimento", ""),
                "Score": round(r.get("score", 0), 2),
                "Resumo": r.get("resumo", ""),
                "Data": r.get("data", ""),
                "Preço USD": round(r.get("price_usd", 0), 2),
            })

    # XLSX
    wb = Workbook()
    ws = wb.active
    ws.title = "Análises"

    headers = ["Ativo", "Sentimento", "Score", "Resumo", "Data", "Preço USD"]
    ws.append(headers)

    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="B00020")
    for col in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")

    for r in resultados:
        ws.append([
            r.get("ativo", "").upper(),
            r.get("sentimento", ""),
            round(r.get("score", 0), 2),
            r.get("resumo", ""),
            r.get("data", ""),
            round(r.get("price_usd", 0), 2),
        ])

    for col in ws.columns:
        max_length = 0
        col_letter = col[0].column_letter
        for cell in col:
            if cell.value:
                max_length = max(max_length, len(str(cell.value)))
        ws.column_dimensions[col_letter].width = max_length + 2

    score_col = "C"
    start_row = 2
    end_row = len(resultados) + 1

    green_fill = PatternFill("solid", fgColor="C6EFCE")
    yellow_fill = PatternFill("solid", fgColor="FFF3B0")
    red_fill = PatternFill("solid", fgColor="FFC7CE")

    ws.conditional_formatting.add(
        f"{score_col}{start_row}:{score_col}{end_row}",
        CellIsRule(operator="greaterThan", formula=["70"], fill=green_fill)
    )
    ws.conditional_formatting.add(
        f"{score_col}{start_row}:{score_col}{end_row}",
        CellIsRule(operator="between", formula=["50", "70"], fill=yellow_fill)
    )
    ws.conditional_formatting.add(
        f"{score_col}{start_row}:{score_col}{end_row}",
        CellIsRule(operator="lessThan", formula=["50"], fill=red_fill)
    )

    chart = BarChart()
    chart.title = "Pontuação de Oportunidade (Score)"
    chart.y_axis.title = "Ativos"
    chart.x_axis.title = "Score"
    chart.style = 13
    chart.type = "bar"
    chart.width = 15
    chart.height = 6

    data = Reference(ws, min_col=3, min_row=1, max_row=end_row)
    cats = Reference(ws, min_col=1, min_row=2, max_row=end_row)
    chart.add_data(data, titles_from_data=True)
    chart.set_categories(cats)
    chart.dataLabels = DataLabelList()
    chart.dataLabels.showVal = True

    chart_anchor_row = end_row + 3
    ws.add_chart(chart, f"A{chart_anchor_row}")

    wb.save(xlsx_filename)

    print("✅ Resultados exportados com sucesso:")
    print(f"   • CSV  → {csv_filename}")
    print(f"   • XLSX → {xlsx_filename} (com gráfico e formatação condicional)")
