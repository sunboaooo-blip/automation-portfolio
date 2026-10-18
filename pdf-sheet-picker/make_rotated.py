"""Rotated-page fixture. Each page LOOKS like a normal landscape sheet (title block bottom-right as viewed)
but is stored with /Rotate 0/90/180/270 and a matching unrotated media box, as CAD exports often are.
Construction: draw an upright page, then embed it into a page with /Rotate set and verify by rendering."""
import pymupdf

def upright(sheet):
    d = pymupdf.open()
    p = d.new_page(width=2592, height=1728)
    p.insert_text((200, 300), "DRAWING INDEX  E9.99  E9.98", fontsize=48)  # decoy refs top-left
    p.draw_rect(pymupdf.Rect(2100, 1300, 2556, 1692), width=2)
    p.insert_text((2300, 1650), sheet, fontsize=48)
    return d

out = pymupdf.open()
for rot, sheet in ((0, "E2.01"), (90, "E2.02"), (180, "A3.01"), (270, "T2.01")):
    src = upright(sheet)
    ref = src[0].get_pixmap(dpi=10).samples
    for sign in (1, -1):
        tmp = pymupdf.open()
        w, h = (2592, 1728) if rot in (0, 180) else (1728, 2592)
        t = tmp.new_page(width=w, height=h)
        t.show_pdf_page(t.rect, src, 0, rotate=sign * rot)
        t.set_rotation(rot)
        if t.get_pixmap(dpi=10).samples == ref:
            out.insert_pdf(tmp)
            print(rot, sheet, "sign", sign, "renders identical to upright sheet")
            break
    else:
        print(rot, "NO MATCH")
out.save("fixtures/rotated.pdf")
