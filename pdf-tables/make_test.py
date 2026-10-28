"""Synthetic mixed test set: selectable-text and scanned table pages, plus a page without a table.
A.pdf: p1 selectable 9x5 table, p2 the same kind of table as a 200 dpi noisy slightly-rotated scan, p3 text only.
B.pdf: p1 scan with two tables.  truth.json holds every cell as typed."""
import io
import json
import random

import numpy as np
import pymupdf
from PIL import Image

random.seed(7)
HEAD = ["Item code", "Description", "Qty", "Unit price", "Amount"]


def rows(n, tag):
    out = []
    for i in range(n):
        q = random.randint(1, 250); p = round(random.uniform(3, 9999), 2)
        out.append([f"{tag}-{1000 + i * 37}", random.choice(["Steel bolt M8", "Copper wire 2.5mm", "PVC pipe 3/4\"",
                    "Cable tie (100 pcs)", "Circuit breaker 32A", "LED panel 18W", "Wall socket, white"]),
                    str(q), f"{p:,.2f}", f"{q * p:,.2f}"])
    return out


def draw_table(page, x0, y0, data, widths, rh=22):
    y = y0
    for r in data:
        x = x0
        for w, v in zip(widths, r):
            page.draw_rect(pymupdf.Rect(x, y, x + w, y + rh), width=0.8)
            page.insert_text((x + 4, y + 15), v, fontsize=9.5)
            x += w
        y += rh
    return y


def scan(page_doc, dpi=200, angle=0.4):
    pix = page_doc[0].get_pixmap(dpi=dpi, colorspace=pymupdf.csGRAY)
    im = Image.frombytes("L", (pix.width, pix.height), pix.samples).rotate(angle, fillcolor=255, resample=Image.BICUBIC)
    a = np.array(im).astype(np.int16) + np.random.default_rng(1).normal(0, 12, (im.height, im.width)).astype(np.int16)
    buf = io.BytesIO(); Image.fromarray(a.clip(0, 255).astype(np.uint8)).save(buf, "PNG")
    return buf.getvalue()


W = [80, 170, 50, 90, 100]
truth = {}
t1, t2 = [HEAD] + rows(8, "AX"), [HEAD] + rows(8, "BX")
a = pymupdf.open()
p = a.new_page(); p.insert_text((50, 70), "Purchase summary - page 1 (text layer)", fontsize=12); draw_table(p, 50, 90, t1, W)
tmp = pymupdf.open(); q = tmp.new_page(); q.insert_text((50, 70), "Purchase summary - page 2 (scanned)", fontsize=12); draw_table(q, 50, 90, t2, W)
p2 = a.new_page(); p2.insert_image(p2.rect, stream=scan(tmp))
p3 = a.new_page(); p3.insert_text((50, 70), "Notes: all prices in INR, GST extra. No table on this page.", fontsize=11)
a.save("in/A.pdf")
truth["A.pdf"] = {"1": [t1], "2": [t2], "3": []}
t3, t4 = [HEAD] + rows(5, "CX"), [HEAD] + rows(4, "DX")
tmp = pymupdf.open(); q = tmp.new_page(); y = draw_table(q, 50, 80, t3, W); draw_table(q, 50, y + 60, t4, W)
b = pymupdf.open(); pb = b.new_page(); pb.insert_image(pb.rect, stream=scan(tmp, angle=-0.3))
b.save("in/B.pdf")
truth["B.pdf"] = {"1": [t3, t4]}
json.dump(truth, open("truth.json", "w"), indent=1)
print("A.pdf 3 pages, B.pdf 1 page; tables:", sum(len(v) for d in truth.values() for v in d.values()))
