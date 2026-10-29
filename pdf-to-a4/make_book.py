"""Synthetic stand-in for a Canva colouring book: 159 vector + raster pages, larger than A4 (8.5x11in+bleed)."""
import pymupdf, io
from PIL import Image, ImageDraw
W, H = 8.75 * 72, 11.25 * 72
doc = pymupdf.open()
img = Image.new("L", (1200, 1200), 255); d = ImageDraw.Draw(img)
for r in range(50, 600, 50): d.ellipse((600 - r, 600 - r, 600 + r, 600 + r), outline=0, width=4)
buf = io.BytesIO(); img.save(buf, "PNG"); png = buf.getvalue()
for n in range(1, 160):
    p = doc.new_page(width=W, height=H)
    p.draw_rect(pymupdf.Rect(2, 2, W - 2, H - 2), color=(0, 0, 0), width=1.5)  # edge-to-edge frame: cropping would show
    for k in range(6): p.draw_circle((W / 2, H / 2 + 40), 40 + 35 * k, color=(0, 0, 0), width=2)
    p.insert_image(pymupdf.Rect(40, 40, 200, 200), stream=png)
    p.insert_text((W / 2 - 40, H - 30), f"page {n}", fontsize=18)
import sys; doc.save(sys.argv[1] if len(sys.argv) > 1 else "book_in.pdf")
