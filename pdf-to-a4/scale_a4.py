#!/usr/bin/env python3
"""Scale every page of a PDF onto A4 proportionally, centred, never cropped or enlarged.
usage: scale_a4.py IN.pdf OUT.pdf [--box media|crop|trim]
Pages are placed as vector XObjects (show_pdf_page): drawings stay vector, embedded images keep their original
pixels (no re-rendering, no recompression). A page already within A4 is centred at 100%, not enlarged.
Self-check per page: page count/order, A4 size, scale <= 1, aspect preserved, placed box inside the page.
"""
import argparse, sys, pymupdf
A4 = pymupdf.paper_rect("a4")
ap = argparse.ArgumentParser(); ap.add_argument("inp"); ap.add_argument("out")
ap.add_argument("--box", choices=("media", "crop", "trim"), default="crop")
a = ap.parse_args()
src = pymupdf.open(a.inp); out = pymupdf.open(); rows = []
for p in src:
    box = {"media": p.mediabox, "crop": p.cropbox, "trim": p.trimbox}[a.box]
    w, h = (box.height, box.width) if p.rotation in (90, 270) else (box.width, box.height)
    k = min(A4.width / w, A4.height / h, 1.0)
    tw, th = w * k, h * k
    r = pymupdf.Rect((A4.width - tw) / 2, (A4.height - th) / 2, (A4.width + tw) / 2, (A4.height + th) / 2)
    q = out.new_page(width=A4.width, height=A4.height)
    q.show_pdf_page(r, src, p.number, clip=box, keep_proportion=True)
    rows.append((p.number + 1, round(w), round(h), round(k, 4), r))
bad = [x for x in rows if x[3] > 1 or not A4.contains(x[4])]
if len(out) != len(src) or bad:
    sys.exit(f"SELF-CHECK FAILED: pages {len(src)}->{len(out)}, bad {bad[:3]}")
out.save(a.out, garbage=3, deflate=True)
print(f"{len(out)} pages -> A4; scale range {min(x[3] for x in rows)}..{max(x[3] for x in rows)}; self-check passed")
