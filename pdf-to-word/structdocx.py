#!/usr/bin/env python3
"""Selectable-text PDF -> editable DOCX that keeps BASIC structure: headings, paragraphs, bullet and numbered
lists, bold and italic. Exact fonts, pagination and margins are deliberately not copied.

usage: structdocx.py IN.pdf OUT.docx [--drop-tables]

--drop-tables: ruled tables found by PyMuPDF find_tables() are removed WITH their text. Every removed table is
  listed (page, position, word count) so the buyer can see exactly what was stripped. Unruled "tables" (text
  aligned with spaces only) are not detected and stay as text - they show up in the page-1 review.

- Text comes from the PDF text layer (PyMuPDF spans); no OCR. A page without a text layer is reported, not guessed.
- Headings: lines whose font size is larger than the body size (the most common size by character count)
  become Heading 1 / 2 / 3 by size rank. Bold-only body lines are NOT promoted (stated rule, shown for approval).
- Lists: a line starting with a bullet glyph becomes "List Bullet"; "1." / "1)" / "a." becomes "List Number".
  The bullet glyph / number itself is dropped because Word renders it from the list style.
- Paragraphs: consecutive body lines are joined into one paragraph unless the vertical gap is larger than
  1.5x the line height; a hyphen at a line end is kept as printed.
- Bold / italic come from each span's font flags and font name.
Self-check: the word sequence of the DOCX equals the PDF text-layer word sequence, minus the dropped list markers;
any difference exits 3 and deletes OUT.
"""
import os
import re
import sys
from collections import Counter

import docx
import pymupdf

BULLET = re.compile(r"^\s*([•●▪–\-\*·])\s+")
NUMBER = re.compile(r"^\s*(\d{1,3}[.)]|[a-z][.)])\s+")


def new_numbering(d, start):
    """A fresh w:num on the List Number style's abstract numbering, restarting at `start`, so every numbered list
    in the source restarts where the source does instead of continuing the previous list's count."""
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    numbering = d.part.numbering_part.element
    style_numpr = d.styles["List Number"].element.pPr.numPr
    base = numbering.num_having_numId(style_numpr.numId.val)
    num = numbering.add_num(base.abstractNumId.val)
    ov = OxmlElement("w:lvlOverride"); ov.set(qn("w:ilvl"), "0")
    so = OxmlElement("w:startOverride"); so.set(qn("w:val"), str(start)); ov.append(so); num.append(ov)
    return num.numId


def set_num(par, num_id):
    p_pr = par._p.get_or_add_pPr()
    num_pr = p_pr.get_or_add_numPr()
    num_pr.get_or_add_ilvl().val = 0
    num_pr.get_or_add_numId().val = num_id


LIGATURES = {chr(c): __import__("unicodedata").normalize("NFKC", chr(c)) for c in range(0xFB00, 0xFB07)}


def spans_of(line):
    """Spans as (text, size, bold, italic); typographic ligature glyphs (fi, fl, ff...) become plain letters so the
    Word text is searchable and spell-checkable; no other character is changed."""
    out = []
    for s in line["spans"]:
        s = dict(s, text="".join(LIGATURES.get(ch, ch) for ch in s["text"]))
        if not s["text"]:
            continue
        name = s["font"].lower()
        bold = bool(s["flags"] & 16) or "bold" in name
        italic = bool(s["flags"] & 2) or "italic" in name or "oblique" in name
        out.append((s["text"], round(s["size"], 1), bold, italic))
    return out


def main(src, dst, drop_tables=False):
    pdf = pymupdf.open(src)
    lines, blank = [], []
    removed, ref_words = [], []

    def in_table(rect, boxes):
        cx, cy = (rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2
        return any(b.x0 <= cx <= b.x1 and b.y0 <= cy <= b.y1 for b in boxes)

    for page in pdf:
        if len(page.get_text().strip()) < 5:
            blank.append(page.number + 1); continue
        boxes = [pymupdf.Rect(t.bbox) for t in page.find_tables().tables] if drop_tables else []
        for b in boxes:
            n = sum(1 for w in page.get_text("words") if in_table(w[:4], [b]))
            removed.append((page.number + 1, tuple(round(v) for v in b), n))
        # independent reference for the completeness check: PyMuPDF's word list (a different extraction path),
        # minus words inside removed tables
        ref_words += ["".join(LIGATURES.get(ch, ch) for ch in w[4]) for w in page.get_text("words") if not in_table(w[:4], boxes)]
        for b in page.get_text("dict")["blocks"]:
            for ln in b.get("lines", []):
                sp = spans_of(ln)
                if boxes and in_table(ln["bbox"], boxes):
                    continue
                if "".join(t for t, *_ in sp).strip():
                    lines.append(dict(page=page.number, x0=ln["bbox"][0], y0=ln["bbox"][1], y1=ln["bbox"][3], spans=sp))
    if blank:
        print(f"page(s) {blank} have no text layer - not converted (scan?)", file=sys.stderr)
    sizes = Counter()
    for ln in lines:
        for t, s, *_ in ln["spans"]:
            sizes[s] += len(t)
    body = sizes.most_common(1)[0][0]
    head_sizes = sorted({s for s in sizes if s > body + 0.5}, reverse=True)[:3]
    d = docx.Document()
    para, prev, prev_kind, list_x0 = None, None, None, 0
    lists, problems, label, num_id, expect = [], [], None, None, 1
    dropped = []
    for ln in lines:
        size = max(s for _, s, *_ in ln["spans"])
        text = "".join(t for t, *_ in ln["spans"])
        kind, spans = "body", list(ln["spans"])
        if size in head_sizes:
            kind = f"Heading {head_sizes.index(size) + 1}"
        else:
            for rx, k in ((BULLET, "List Bullet"), (NUMBER, "List Number")):
                m = rx.match(text)
                if m:
                    kind = k; dropped.append(m.group(1)); label = m.group(1)
                    cut = m.end()  # remove the marker from the first span(s)
                    new = []
                    for t, *rest in spans:
                        if cut >= len(t):
                            cut -= len(t); continue
                        new.append((t[cut:], *rest)); cut = 0
                    spans = new
                    break
        gap = prev is not None and (ln["page"] != prev["page"] or ln["y0"] - prev["y1"] > 0.5 * (ln["y1"] - ln["y0"]))
        cont = para is not None and not gap and (
            (kind == "body" and prev_kind == "body")
            # a wrapped list item continues only if indented past the item's marker; text back at the margin is a new paragraph
            or (kind == "body" and prev_kind in ("List Bullet", "List Number") and ln["x0"] > list_x0 + 2)
            or (kind.startswith("Heading") and kind == prev_kind))                    # two-line heading
        if not cont:
            para = d.add_paragraph(style=None if kind == "body" else kind)
            if kind in ("List Bullet", "List Number"):
                list_x0 = ln["x0"]
            if kind == "List Number":
                n = int(label[:-1]) if label[:-1].isdigit() else ord(label[0]) - 96
                if prev_kind != "List Number":  # a new numbered list in the source -> its own Word numbering
                    num_id, expect = new_numbering(d, n), n
                    lists.append([])
                if n != expect:  # source skips or repeats a number: reported, never silently renumbered
                    problems.append(f"numbered list {len(lists)}: source label {label!r} where {expect} was expected")
                set_num(para, num_id); lists[-1].append(label); expect = n + 1
        elif para.runs:
            para.runs[-1].text = para.runs[-1].text.rstrip() + (" " if not para.runs[-1].text.endswith("-") else "")
        for t, s, bold, italic in spans:
            r = para.add_run(t); r.bold = bold or None; r.italic = italic or None
        prev = ln
        if not cont:
            prev_kind = kind
    d.save(dst)
    w_pdf = re.findall(r"\S+", " ".join(ref_words))
    for m in dropped:
        w_pdf.remove(m)
    w_doc = re.findall(r"\S+", " ".join(p.text for p in docx.Document(dst).paragraphs))
    if w_pdf != w_doc:
        os.remove(dst)
        i = next((k for k, (a, b) in enumerate(zip(w_pdf, w_doc)) if a != b), min(len(w_pdf), len(w_doc)))
        sys.exit(f"SELF-CHECK FAILED: words differ at {i}: pdf {w_pdf[i:i + 5]} docx {w_doc[i:i + 5]}")
    for pg, box, n in removed:
        print(f"TABLE REMOVED: page {pg} at {box}, {n} words", file=sys.stderr)
    if blank:
        problems.append(f"page(s) {blank} have no text layer and are NOT in the DOCX")
    for msg in problems:
        print("CHECK:", msg, file=sys.stderr)
    st = Counter(p.style.name for p in docx.Document(dst).paragraphs if p.text.strip())
    print(f"{len(pdf)} pages, {len(w_doc)} words -> {dst}; body {body}pt, heading sizes {head_sizes}; styles {dict(st)}; numbered lists {[f"{l[0]}..{l[-1]}" for l in lists]}; self-check passed" + (f"; {len(problems)} item(s) to review" if problems else ""))
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], "--drop-tables" in sys.argv[3:])
