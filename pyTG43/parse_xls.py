from glob import glob
import xlrd

fname = glob("examples/HDR/*.xls")[0]
wb = xlrd.open_workbook(fname)

def format_cell(cell, width=12):
    text = str(cell)

    # 数值格式化
    if isinstance(cell, float):
        text = f"{cell:.4f}"

    # 超出截断
    if len(text) > width:
        text = text[:width-3] + "..."

    return f"{text:<{width}}"

for sheet in wb.sheets():
    print(f"\n===== Sheet: {sheet.name} =====")

    for row_idx in range(sheet.nrows):
        row = sheet.row_values(row_idx)
        formatted = " | ".join(f"{format_cell(cell):<12}" for cell in row)
        print(formatted)

