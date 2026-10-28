"""Harder scan for the flagging check: 110 dpi, heavy noise, 0.9 deg skew, light blur. C.pdf, truth_hard.json."""
import io, json, random
import numpy as np, pymupdf
from PIL import Image, ImageFilter
random.seed(11)
HEAD = ["Item code", "Description", "Qty", "Unit price", "Amount"]
def rows(n, tag):
    out = []
    for i in range(n):
        q = random.randint(1, 250); p = round(random.uniform(3, 9999), 2)
        out.append([f"{tag}-{1000 + i * 37}", random.choice(["Steel bolt M8", "Copper wire 2.5mm", "PVC pipe 3/4\"", "Cable tie (100 pcs)", "LED panel 18W"]), str(q), f"{p:,.2f}", f"{q * p:,.2f}"])
    return out
W = [80, 170, 50, 90, 100]; t = [HEAD] + rows(10, "EX")
tmp = pymupdf.open(); q = tmp.new_page(); y = 90
for r in t:
    x = 50
    for w, v in zip(W, r):
        q.draw_rect(pymupdf.Rect(x, y, x + w, y + 22), width=0.8); q.insert_text((x + 4, y + 15), v, fontsize=9.5); x += w
    y += 22
pix = tmp[0].get_pixmap(dpi=110, colorspace=pymupdf.csGRAY)
im = Image.frombytes("L", (pix.width, pix.height), pix.samples).rotate(0.9, fillcolor=255, resample=Image.BICUBIC).filter(ImageFilter.GaussianBlur(0.8))
a = np.array(im).astype(np.int16) + np.random.default_rng(3).normal(0, 35, (im.height, im.width)).astype(np.int16)
buf = io.BytesIO(); Image.fromarray(a.clip(0, 255).astype(np.uint8)).save(buf, "PNG")
d = pymupdf.open(); p = d.new_page(); p.insert_image(p.rect, stream=buf.getvalue())
import os; os.makedirs("in_hard", exist_ok=True); d.save("in_hard/C.pdf")
json.dump({"C.pdf": {"1": [t]}}, open("truth_hard.json", "w"))
