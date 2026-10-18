"""Build a synthetic table-style catalogue PDF for testing extract.py (no customer data)."""
import io
import sys

import pymupdf
from PIL import Image, ImageDraw


def img_bytes(size, color, fmt, alpha=False, mode="RGB"):
    im = Image.new("RGBA" if alpha else mode, size, color)
    d = ImageDraw.Draw(im)
    d.ellipse([size[0] // 4, size[1] // 4, size[0] * 3 // 4, size[1] * 3 // 4],
              fill=(255, 255, 255, 0) if alpha else ("white" if mode == "RGB" else 0))
    d.text((5, 5), f"{size[0]}x{size[1]}", fill="black" if mode == "RGB" else 255)
    b = io.BytesIO()
    im.save(b, fmt, quality=92) if fmt == "JPEG" else im.save(b, fmt)
    return b.getvalue()


out = sys.argv[1] if len(sys.argv) > 1 else "test_catalogue.pdf"
logo = img_bytes((600, 200), "navy", "PNG")
footer = img_bytes((300, 60), (200, 0, 0, 180), "PNG", alpha=True)  # has soft mask
products = [img_bytes((1200, 900), c, "JPEG") for c in ("orange", "green", "purple", "teal")]
cmyk = img_bytes((800, 800), (0, 80, 80, 10), "JPEG", mode="CMYK")
gray = img_bytes((500, 500), 120, "PNG", mode="L")

doc = pymupdf.open()
rows = [("SKU-001", "Orange widget", products[0]), ("SKU-002", "Green widget", products[1]),
        ("SKU-003", "Purple widget", products[2]), ("SKU-004", "Teal widget", products[3]),
        ("SKU-005", "Cyan magenta part", cmyk), ("SKU-006", "Grey part", gray),
        ("SKU-007", "Orange widget (again)", products[0])]  # duplicate content in a later row
per_page = 3
for p in range(0, len(rows), per_page):
    page = doc.new_page(width=595, height=842)
    page.insert_image(pymupdf.Rect(40, 20, 220, 80), stream=logo)  # repeated header logo
    page.insert_text((240, 55), "ACME catalogue (synthetic test)", fontsize=14)
    y = 110
    for sku, name, data in rows[p:p + per_page]:
        page.draw_rect(pymupdf.Rect(40, y, 555, y + 200), color=(0, 0, 0), width=0.5)
        page.insert_text((50, y + 100), sku, fontsize=11)
        page.insert_text((150, y + 100), name, fontsize=11)
        page.insert_image(pymupdf.Rect(360, y + 10, 540, y + 190), stream=data)
        y += 210
    # a vector-only "badge" (not an image object) to exercise the vector flag
    page.draw_circle((500, 790), 18, color=(0, 0.5, 0), fill=(0, 0.8, 0))
    page.insert_image(pymupdf.Rect(40, 770, 190, 800), stream=footer)
    page.insert_text((300, 820), f"Page {page.number + 1}", fontsize=9)
doc.save(out, garbage=4, deflate=True)
print(out, doc.page_count, "pages")
