"""Apply pdftables.fit_columns to already-written workbooks (layout only; no extraction, OCR or model run)."""
import sys
from openpyxl import load_workbook
from pdftables import fit_columns
for path in sys.argv[1:]:
    wb = load_workbook(path)
    for ws in wb.worksheets:
        fit_columns(ws)
    wb.save(path); print("relaid", path)
