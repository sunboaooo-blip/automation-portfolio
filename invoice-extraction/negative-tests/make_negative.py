"""Negative fixtures (fictional): formula-looking text, a missing grand total, a wrong tax amount, and a hybrid PDF with a scanned page."""
import pymupdf
from fpdf import FPDF
F = "../../invoice-generator/assets/"
def base(path, no, rows, totals):
    p = FPDF(); p.add_font("R", "", F + "Inter-Regular.ttf"); p.add_page(); p.set_font("R", "", 11)
    p.cell(0, 8, "Vega Hardware (fictional)", new_x="LMARGIN", new_y="NEXT"); p.cell(0, 7, f"Invoice {no}   Date 22-10-2026", new_x="LMARGIN", new_y="NEXT"); p.ln(3)
    for d, rate, q, amt in rows:
        p.cell(90, 6, d); p.cell(25, 6, f"{rate:.2f}", align="R"); p.cell(20, 6, str(q), align="R"); p.cell(40, 6, f"{amt:.2f}", align="R", new_x="LMARGIN", new_y="NEXT")
    p.ln(3)
    for k, v in totals:
        p.cell(135, 6, k, align="R"); p.cell(40, 6, v, align="R", new_x="LMARGIN", new_y="NEXT")
    p.output(path)
# 1: formula-looking description; 2: no grand total printed; 3: printed GST amount wrong for the printed 18% rate
base("VH-101.pdf", "VH-101", [("=HYPERLINK(\"x\") cable ties", 40.0, 10, 400.0)], [("Subtotal", "400.00"), ("GST 18%", "72.00"), ("Total", "472.00")])
base("VH-102.pdf", "VH-102", [("Hex bolts M8 (pack)", 120.0, 5, 600.0)], [("Subtotal", "600.00"), ("GST 18%", "108.00")])
base("VH-103.pdf", "VH-103", [("Wall plugs 8 mm (box)", 60.0, 10, 600.0)], [("Subtotal", "600.00"), ("GST 18%", "118.00"), ("Total", "718.00")])
# 4: hybrid: page 1 text, page 2 an image of a page (no text layer)
base("tmp.pdf", "VH-104", [("Drill bit set", 450.0, 2, 900.0)], [("Subtotal", "900.00"), ("GST 18%", "162.00"), ("Total", "1062.00")])
src = pymupdf.open("tmp.pdf"); out = pymupdf.open(); out.insert_pdf(src)
pix = src[0].get_pixmap(dpi=100); pg = out.new_page(width=src[0].rect.width, height=src[0].rect.height); pg.insert_image(pg.rect, pixmap=pix)
out.save("VH-104-hybrid.pdf")
import os; os.remove("tmp.pdf")
