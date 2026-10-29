"""Synthetic test PDFs for structdocx.py: structure, wrap (2 pages), restart (numbering), table (ruled table)."""
import os, sys
import pymupdf
out = sys.argv[1] if len(sys.argv) > 1 else "fixtures"
os.makedirs(out, exist_ok=True)


def one(name, pages, rect=(60, 60, 540, 780)):
    doc = pymupdf.open()
    for h in pages:
        doc.new_page().insert_htmlbox(pymupdf.Rect(*rect), h)
    doc.save(os.path.join(out, name))


one("structure.pdf", ["""<h1>Quarterly Operations Report</h1>
<p>This report covers <b>October 2026</b> and is written in <i>plain English</i> for the board.</p>
<h2>Key results</h2>
<ul><li>Orders shipped on time: <b>96.4%</b></li><li>Returns fell to <i>1.8%</i> of orders</li><li>Two new suppliers were approved</li></ul>
<h2>Next steps</h2>
<ol><li>Renew the warehouse lease</li><li>Hire one <b>senior</b> planner</li></ol>
<p>Questions go to the operations desk.</p>"""])
long = "The supplier review found that most delays came from late purchase orders rather than transport, and the team agreed a new cut-off. " * 3
items = "".join(f"<li>Item {k}: {'a longer list entry that wraps onto a second printed line because it keeps going and going ' if k == 2 else ''}point {k}</li>" for k in range(1, 5))
one("wrap.pdf", [f"<h1>Annual Supplier Review and Planning Notes for 2027</h1><p>{long}</p><h2>Findings</h2><ul>{items}</ul><p><i>Prepared by the planning team.</i></p>",
                 f"<h2>Appendix</h2><ol><li>First <b>numbered</b> step</li><li>Second step</li></ol><p>{long}</p>"], (60, 60, 400, 780))
one("restart.pdf", ["<h1>Two lists</h1><ol><li>Alpha</li><li>Beta</li></ol><p>Between the lists.</p><ol start='1'><li>Gamma</li><li>Delta</li></ol>"
                    "<p>A list that starts at five:</p><ol start='5'><li>Epsilon</li><li>Zeta</li></ol>"])
doc = pymupdf.open(); p = doc.new_page()
p.insert_htmlbox(pymupdf.Rect(60, 60, 540, 300), "<h1>Service Flyer</h1><p>We offer <b>three</b> services for small offices.</p><h2>Prices</h2>")
y = 310
for r in [["Service", "Price", "Time"], ["Cleaning", "INR 900", "2 h"], ["Repairs", "INR 1,500", "3 h"]]:
    x = 60
    for v in r:
        p.draw_rect(pymupdf.Rect(x, y, x + 120, y + 22)); p.insert_text((x + 4, y + 15), v, fontsize=11); x += 120
    y += 22
p.insert_htmlbox(pymupdf.Rect(60, y + 20, 540, 780), "<p>Call us to <i>book</i> a visit.</p><ul><li>Open Monday to Friday</li></ul>")
doc.save(os.path.join(out, "table.pdf"))
print("4 fixtures ->", out)
