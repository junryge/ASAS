---
name: xlsx
description: Create, read, and manipulate Excel spreadsheets (.xlsx). TRIGGER when the user asks to generate Excel files, work with spreadsheets, create charts, apply formulas, or analyze tabular data in Excel format.
---
# Excel Spreadsheet Skill

Create, read, and manipulate Excel files using `openpyxl`.

## Reading Excel Files

```python
from openpyxl import load_workbook
wb = load_workbook("data.xlsx")
ws = wb.active
for row in ws.iter_rows(min_row=1, values_only=True):
    print(row)
```

## Creating Excel Files

```python
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

wb = Workbook()
ws = wb.active
ws.title = "Report"

# Headers with styling
headers = ["Name", "Value", "Date"]
for col, header in enumerate(headers, 1):
    cell = ws.cell(row=1, column=col, value=header)
    cell.font = Font(bold=True, size=12)
    cell.fill = PatternFill("solid", fgColor="4472C4")
    cell.font = Font(bold=True, color="FFFFFF")

wb.save("output.xlsx")
```

## Formulas and Charts

```python
# Add formulas
ws["C10"] = "=SUM(C2:C9)"
ws["C11"] = "=AVERAGE(C2:C9)"

# Add chart
from openpyxl.chart import BarChart, Reference
chart = BarChart()
data = Reference(ws, min_col=2, min_row=1, max_row=10)
chart.add_data(data, titles_from_data=True)
ws.add_chart(chart, "E2")
```

## Guidelines
- Preserve existing formatting when modifying files
- Auto-fit column widths for readability
- Use number_format for dates and currency
- Support multiple sheets when needed
