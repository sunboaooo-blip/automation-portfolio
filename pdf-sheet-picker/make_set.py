"""Synthetic 12-sheet construction set (ARCH D landscape) with title blocks, mixed sheet-number styles."""
import pymupdf
sheets = ["G0.01", "A1.01", "A-201", "S101", "E0.01", "E1.01", "E-201", "M1.01", "ES-101", "T1.0", "P101", "E.000"]
doc = pymupdf.open()
for s in sheets:
    p = doc.new_page(width=2592, height=1728)  # 36x24 in
    p.draw_rect(pymupdf.Rect(36, 36, 2556, 1692), width=2)
    p.insert_text((200, 400), f"PLAN VIEW - see detail E2.01 and A-201", fontsize=24)  # cross-refs in body text
    tb = pymupdf.Rect(2100, 1300, 2556, 1692)
    p.draw_rect(tb, width=2)
    p.insert_text((2120, 1350), "ACME ARCHITECTS  PROJECT 24-118", fontsize=14)
    p.insert_text((2120, 1400), "REF: E1.01", fontsize=10)  # small cross-reference inside the title block
    p.insert_text((2120, 1620), "SHEET", fontsize=12)
    p.insert_text((2300, 1650), s, fontsize=48)
doc.save("fixtures/set12.pdf")
amb = pymupdf.open()
p = amb.new_page(width=2592, height=1728)
p.insert_text((2150, 1600), "E1.02", fontsize=48); p.insert_text((2350, 1650), "E1.03", fontsize=48)
p2 = amb.new_page(width=2592, height=1728); p2.insert_text((200, 300), "COVER", fontsize=60)
amb.save("fixtures/ambiguous.pdf")
