"""Edge-case fixtures: inline image, JPEG2000 image, vector polygon, and an image-free PDF."""
import io

import pymupdf
from PIL import Image

doc = pymupdf.open()
page = doc.new_page(width=595, height=842)
page.insert_text((50, 200), "ROW-A inline swatch", fontsize=11)
# inline image: 4x2 RGB raster written directly into the content stream (BI ... ID ... EI)
px = bytes([255, 0, 0, 0, 255, 0, 0, 0, 255, 255, 255, 0] * 2)
content = (b"q 120 0 0 60 360 600 cm BI /W 4 /H 2 /CS /RGB /BPC 8 ID " + px + b" EI Q\n")
xref = doc.get_new_xref()
doc.update_object(xref, "<<>>")
doc.update_stream(xref, content)
doc.xref_set_key(page.xref, "Contents", f"[{' '.join(f'{x} 0 R' for x in page.get_contents())} {xref} 0 R]")
page.insert_text((50, 400), "ROW-B jpx photo", fontsize=11)
b = io.BytesIO()
Image.new("RGB", (400, 300), "olive").save(b, "JPEG2000")
page.insert_image(pymupdf.Rect(360, 330, 540, 465), stream=b.getvalue())
page.draw_polyline([(100, 600), (150, 650), (120, 700), (80, 660)], color=(0, 0, 1), closePath=True)
doc.save("test/test_edge.pdf")

empty = pymupdf.open()
empty.new_page().insert_text((50, 50), "text only")
empty.save("test/test_empty.pdf")
print("ok")
