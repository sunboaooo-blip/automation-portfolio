#!/usr/bin/env python3
"""Pick drawing sheets by discipline (default E and T) from a text-based construction set PDF.

Engine: PyMuPDF if installed (fast, handles rotated pages and embedded form content); otherwise pypdf
(pure Python). The pypdf engine cannot place text inside Form XObjects reliably, so such pages are held
for review instead of guessed.

usage: sheetpick.py SET.pdf OUT_DIR [--prefixes E,T] [--region 0.55,0.70,1,1] [--include-ambiguous]
Reads the sheet number from the title-block region (fractions of the page AS DISPLAYED, origin top-left,
honouring /Rotate 0/90/180/270; default bottom-right) and keeps matching pages in
original order. Writes OUT_DIR/<stem>-E-T.pdf, sheets.csv (every page) and sheets.txt (exported numbers).
Pages whose number is ambiguous or missing are NOT exported unless --include-ambiguous; they are listed
in sheets.csv for review. The source PDF is only read, never written.
Exit 0 = exported and nothing to review, 1 = review needed or nothing matched, 2 = error.
"""
import argparse
import csv
import os
import re
import sys

try:
    import pymupdf
except ImportError:
    pymupdf = None
from pypdf import PdfReader, PdfWriter

# sheet numbers as they appear in title blocks: E1.01, E101, E-101, E-1001, E.000, T1.0, ES-101, EP101, TA-1
SHEET_RE = re.compile(r"^(?P<prefix>[A-Z]{1,3})[-.\s]?(?P<num>\d{1,4}(?:\.\d{1,3})?[A-Z]?)$")


def viewed(x, y, box, rot):
    """Unrotated PDF point -> (fx, fy) fractions of the page AS DISPLAYED (origin top-left), honouring /Rotate."""
    u = (x - float(box.left)) / float(box.width)    # 0..1 left->right in unrotated space
    v = (y - float(box.bottom)) / float(box.height)  # 0..1 bottom->top in unrotated space
    return {0: (u, 1 - v), 90: (v, u), 180: (1 - u, v), 270: (1 - v, 1 - u)}[rot]


def has_form_xobject(page):
    res = page.get("/Resources") or {}
    xo = res.get("/XObject") or {}
    return any(xo[k].get_object().get("/Subtype") == "/Form" for k in xo)


def candidates_pypdf(page, region):
    """(size, token, prefix) list, or None if the page cannot be read reliably with pypdf."""
    if has_form_xobject(page):
        return None
    box = page.mediabox
    rot = (page.get("/Rotate", 0) or 0) % 360
    found = []

    def visit(text, cm, tm, font_dict, font_size):
        if not text.strip():
            return
        a, b, c, d, e, f = tm
        A, B, C, D, E, F = cm
        x, y = e * A + f * C + E, e * B + f * D + F
        size = abs(font_size) * (((c * A + d * C) ** 2 + (c * B + d * D) ** 2) ** 0.5 or 1)
        fx, fy = viewed(x, y, box, rot)
        if region[0] <= fx <= region[2] and region[1] <= fy <= region[3]:
            for tok in text.split():
                tok = tok.strip().upper().strip(",;:")
                m = SHEET_RE.match(tok)
                if m:
                    found.append((round(size, 1), tok, m.group("prefix")))

    page.extract_text(visitor_text=visit)
    return sorted(set(found), reverse=True)


def candidates_mupdf(page, region):
    """(size, token, prefix) list using PyMuPDF; word boxes are mapped to the page as displayed."""
    W, H = page.rect.width, page.rect.height
    found = []
    for w in page.get_text("words"):
        r = pymupdf.Rect(w[:4]) * page.rotation_matrix
        fx, fy = r.x0 / W, r.y0 / H
        if region[0] <= fx <= region[2] and region[1] <= fy <= region[3]:
            tok = w[4].strip().upper().strip(",;:")
            m = SHEET_RE.match(tok)
            if m:
                found.append((round(min(r.width, r.height) if len(tok) > 3 else r.height, 1), tok, m.group("prefix")))
    return sorted(set(found), reverse=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf")
    ap.add_argument("out")
    ap.add_argument("--prefixes", default="E,T", help="a sheet matches if its prefix starts with one of these")
    ap.add_argument("--region", default="0.55,0.70,1,1", help="title-block box x0,y0,x1,y1 as page fractions "
                    "(0,0 = top-left as viewed)")
    ap.add_argument("--engine", choices=["auto", "pymupdf", "pypdf"], default="auto")
    ap.add_argument("--include-ambiguous", action="store_true",
                    help="also export ambiguous pages (best guess); default is to hold them for review")
    a = ap.parse_args()
    prefixes = tuple(p.strip().upper() for p in a.prefixes.split(",") if p.strip())
    region = tuple(float(v) for v in a.region.split(","))
    ap_engine = a.engine
    try:
        src = PdfReader(a.pdf)
        mdoc = pymupdf.open(a.pdf) if (pymupdf and ap_engine != "pypdf") else None
    except Exception as e:
        print(f"cannot open {a.pdf}: {e}", file=sys.stderr)
        return 2
    rows, keep, review = [], [], []
    for i, page in enumerate(src.pages):
        c = candidates_mupdf(mdoc[i], region) if mdoc is not None else candidates_pypdf(page, region)
        if c is None:
            rows.append({"page": i + 1, "sheet": "", "status": "REVIEW: unreadable with pypdf, not exported",
                         "note": "embedded form content; install pymupdf (pip install pymupdf) and rerun"})
            review.append(i + 1)
            continue
        sheet, prefix = (c[0][1], c[0][2]) if c else ("", "")
        # ambiguous: two different sheet-number candidates of the same (largest) size
        amb = len(c) > 1 and abs(c[0][0] - c[1][0]) < 0.5 and c[0][1] != c[1][1]
        match = bool(sheet) and prefix.startswith(prefixes)
        if amb:
            match_any = any(p.startswith(prefixes) for _, _, p in c[:2])
            status = "export (ambiguous, --include-ambiguous)" if match_any and a.include_ambiguous else \
                ("REVIEW: ambiguous, not exported" if match_any else "skip")
            note = "AMBIGUOUS: " + " / ".join(t for _, t, _ in c[:3])
            if match_any:
                review.append(i + 1)
        elif not sheet:
            status, note = "REVIEW: no sheet number found, not exported", "check title-block region"
            review.append(i + 1)
        else:
            status, note = ("export" if match else "skip"), ""
        if status.startswith("export"):
            keep.append(i)
        rows.append({"page": i + 1, "sheet": sheet, "status": status, "note": note})
    os.makedirs(a.out, exist_ok=True)
    stem = os.path.splitext(os.path.basename(a.pdf))[0]
    with open(os.path.join(a.out, "sheets.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["page", "sheet", "status", "note"])
        w.writeheader()
        w.writerows(rows)
    exported = [rows[i]["sheet"] for i in keep]
    with open(os.path.join(a.out, "sheets.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(exported) + ("\n" if exported else ""))
    if keep:
        out = PdfWriter()
        for i in keep:  # original order
            out.add_page(src.pages[i])
        dst = os.path.join(a.out, f"{stem}-{'-'.join(prefixes)}.pdf")
        if os.path.exists(dst) and os.path.samefile(dst, a.pdf):
            print("refusing to overwrite the source PDF", file=sys.stderr)
            return 2
        with open(dst, "wb") as f:
            out.write(f)
    print(f"engine: {'pymupdf' if mdoc is not None else 'pypdf'}")
    print(f"{len(src.pages)} pages, {len(keep)} exported ({', '.join(exported) or 'none'}); "
          f"{len(review)} page(s) held for review: {review or 'none'}")
    return 0 if keep and not review else 1


if __name__ == "__main__":
    sys.exit(main())
