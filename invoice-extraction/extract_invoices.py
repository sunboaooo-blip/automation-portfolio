#!/usr/bin/env python3
"""Invoice PDFs (selectable text) -> one XLSX: Invoices, Line items, By supplier, Exceptions.

usage: extract_invoices.py PDF_DIR OUT.xlsx [--api http://127.0.0.1:8005/v1] [--model NAME]

1. PyMuPDF reads the text layer (no OCR; a page without text is reported, not guessed).
2. A LOCAL language model (OpenAI-compatible server on this machine) maps the text to fields as JSON.
3. Nothing the model returns is trusted:
   - every number it reports must literally appear in that invoice's text, otherwise -> Exceptions;
   - qty x rate = line amount, sum(lines) = subtotal, subtotal - discount + taxes = total are recomputed
     with Decimal; any difference > 0.01 -> Exceptions (the printed value is kept, never "fixed").
"""
import argparse
import json
import os
import re
import sys
import urllib.request
from collections import defaultdict
from decimal import Decimal, InvalidOperation

import pymupdf
from openpyxl import Workbook
from openpyxl.styles import Font

PROMPT = """Extract this invoice into JSON with exactly these keys:
supplier, invoice_no, date, currency, lines (list of {description, qty, rate, amount}),
subtotal, discount, taxes (list of {label, amount}), total.
Copy every value exactly as printed (numbers without thousands separators). Use null for anything not printed.
Do not calculate or correct anything. Output JSON only.

INVOICE TEXT:
"""


def ask(api, model, text):
    body = {"model": model, "temperature": 0, "messages": [{"role": "user", "content": PROMPT + text}],
            "response_format": {"type": "json_object"}}
    req = urllib.request.Request(api + "/chat/completions", json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        out = json.load(r)["choices"][0]["message"]["content"]
    return json.loads(re.sub(r"^```(?:json)?|```$", "", out.strip(), flags=re.M))


def D(x):
    if x is None or x == "":
        return None
    try:
        return Decimal(str(x).replace(",", "").strip())
    except InvalidOperation:
        return None


def in_text(val, text_nums):
    return val is None or val in text_nums


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf_dir"); ap.add_argument("out")
    ap.add_argument("--api", default="http://127.0.0.1:8005/v1"); ap.add_argument("--model", default="local")
    a = ap.parse_args()
    inv_rows, line_rows, exc = [], [], []
    for name in sorted(f for f in os.listdir(a.pdf_dir) if f.lower().endswith(".pdf")):
        doc = pymupdf.open(os.path.join(a.pdf_dir, name))
        text = "\n".join(p.get_text() for p in doc)
        if len(text.strip()) < 20:
            exc.append((name, "", "no text layer (scan?) - not extracted", "", "")); continue
        nums = {D(m) for m in re.findall(r"\d[\d,]*\.?\d*", text)} - {None}
        j = ask(a.api, a.model, text)
        no = str(j.get("invoice_no") or "")
        lines = j.get("lines") or []
        s = Decimal("0")
        for i, l in enumerate(lines, 1):
            q, r, amt = D(l.get("qty")), D(l.get("rate")), D(l.get("amount"))
            for lab, v in (("qty", q), ("rate", r), ("amount", amt)):
                if not in_text(v, nums):
                    exc.append((name, no, f"line {i} {lab} {v} not found in PDF text", "", ""))
            if q is not None and r is not None and amt is not None and abs(q * r - amt) > Decimal("0.01"):
                exc.append((name, no, f"line {i}: qty x rate = {q * r:.2f} but printed amount {amt}", f"{q * r:.2f}", str(amt)))
            s += amt or 0
            line_rows.append([name, j.get("supplier"), no, j.get("date"), i, l.get("description"), q, r, amt])
        sub, disc, tot = D(j.get("subtotal")), D(j.get("discount")) or Decimal("0"), D(j.get("total"))
        taxes = [(t.get("label"), D(t.get("amount"))) for t in (j.get("taxes") or [])]
        tax_sum = sum((t[1] or 0 for t in taxes), Decimal("0"))
        for lab, v in (("subtotal", sub), ("discount", D(j.get("discount"))), ("total", tot)) + tuple((f"tax {t[0]}", t[1]) for t in taxes):
            if not in_text(v, nums):
                exc.append((name, no, f"{lab} {v} not found in PDF text", "", ""))
        if sub is not None and abs(s - sub) > Decimal("0.01"):
            exc.append((name, no, "sum of line amounts differs from printed subtotal", f"{s:.2f}", str(sub)))
        if sub is not None and tot is not None:
            calc = sub - disc + tax_sum
            if abs(calc - tot) > Decimal("0.01"):
                exc.append((name, no, "subtotal - discount + taxes differs from printed total", f"{calc:.2f}", str(tot)))
        inv_rows.append([name, j.get("supplier"), no, j.get("date"), j.get("currency"), len(lines), sub, disc, tax_sum, tot])
        print(name, no, len(lines), "lines", "total", tot)
    wb = Workbook()
    def sheet(ws, head, rows):
        ws.append(head); [c.__setattr__("font", Font(bold=True)) for c in ws[1]]
        for r in rows:
            ws.append([float(v) if isinstance(v, Decimal) else v for v in r])
        ws.freeze_panes = "A2"
    sheet(wb.active, ["file", "supplier", "invoice_no", "date", "currency", "lines", "subtotal", "discount", "taxes", "total"], inv_rows)
    wb.active.title = "Invoices"
    sheet(wb.create_sheet("Line items"), ["file", "supplier", "invoice_no", "date", "line", "description", "qty", "rate", "amount"], line_rows)
    agg = defaultdict(lambda: [0, Decimal("0")])
    for r in inv_rows:
        agg[r[1]][0] += 1; agg[r[1]][1] += r[9] or 0
    sheet(wb.create_sheet("By supplier"), ["supplier", "invoices", "printed totals"], [[k, v[0], v[1]] for k, v in sorted(agg.items())])
    sheet(wb.create_sheet("Exceptions"), ["file", "invoice_no", "issue", "recomputed", "printed"], exc)
    wb.save(a.out)
    print(f"{len(inv_rows)} invoices, {len(line_rows)} line items, {len(exc)} exceptions -> {a.out}")


if __name__ == "__main__":
    main()
