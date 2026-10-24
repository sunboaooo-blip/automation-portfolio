"""Second, deliberately different invoice layout (fictional suppliers): CGST/SGST split, discount, qty x rate column order."""
import sys
from fpdf import FPDF
F = "../invoice-generator/assets/"
def inv(path, supplier, no, date, lines, disc, printed_total=None):
    p = FPDF(); p.add_font("R", "", F + "Inter-Regular.ttf"); p.add_font("B", "", F + "Manrope-Bold.ttf"); p.add_page()
    p.set_font("B", "", 16); p.cell(0, 9, supplier, new_x="LMARGIN", new_y="NEXT")
    p.set_font("R", "", 9); p.cell(0, 5, "GSTIN 27ABCDE1234F1Z5 (fictional)", new_x="LMARGIN", new_y="NEXT"); p.ln(4)
    p.set_font("R", "", 10); p.cell(95, 6, f"Tax Invoice {no}"); p.cell(0, 6, f"Dated: {date}", align="R", new_x="LMARGIN", new_y="NEXT"); p.ln(3)
    p.set_font("B", "", 10)
    for w, h in ((10, "#"), (85, "Description"), (25, "Rate"), (20, "Qty"), (40, "Line total")): p.cell(w, 7, h, border="B")
    p.ln(); p.set_font("R", "", 10); sub = 0
    for i, (d, rate, q) in enumerate(lines, 1):
        amt = round(rate * q, 2); sub += amt
        for w, v, a in ((10, str(i), "L"), (85, d, "L"), (25, f"{rate:.2f}", "R"), (20, str(q), "R"), (40, f"{amt:,.2f}", "R")): p.cell(w, 6, v, align=a)
        p.ln()
    sub = round(sub, 2); taxable = round(sub - disc, 2); cg = round(taxable * 0.09, 2); sg = cg; tot = round(taxable + cg + sg, 2)
    p.ln(3)
    for k, v in (("Sub total", sub), ("Less discount", disc), ("Taxable value", taxable), ("CGST 9%", cg), ("SGST 9%", sg), ("Grand total (Rs.)", printed_total if printed_total is not None else tot)):
        p.cell(140, 6, k, align="R"); p.cell(40, 6, f"{v:,.2f}", align="R", new_x="LMARGIN", new_y="NEXT")
    p.output(path)
inv("pdfs/KP-7781.pdf", "Kumar Paper Mart (fictional)", "KP/7781", "12-10-2026", [("A4 copier paper 75 gsm (ream)", 245.0, 20), ("Stapler pins No.10 (box)", 18.5, 12)], 150.0)
inv("pdfs/KP-7795.pdf", "Kumar Paper Mart (fictional)", "KP/7795", "19-10-2026", [("Box file, blue", 95.0, 15), ("Gel pen 0.5 mm, black", 12.0, 50), ("Sticky notes 3x3 (pad)", 35.0, 24)], 0.0)
inv("pdfs/SE-0042.pdf", "Shreeji Electricals (fictional)", "SE-0042", "21-10-2026", [("LED tube light 20 W", 310.0, 8), ("Ceiling fan regulator", 425.0, 3)], 100.0, printed_total=4900.00)  # wrong printed total on purpose
