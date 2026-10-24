#!/usr/bin/env python3
"""Invoice PDFs (selectable text) -> one XLSX: Invoices, Line items, Taxes, By supplier, Exceptions.

usage: extract_invoices.py PDF_DIR OUT.xlsx [--api http://127.0.0.1:8005/v1] [--model NAME]

1. PyMuPDF reads the text layer (no OCR; a page without text is reported, not guessed).
2. A LOCAL language model (OpenAI-compatible server on this machine) maps the text to fields as JSON.
3. Nothing the model returns is trusted:
   - required values (total, subtotal, each line's qty/rate/amount) that are missing or unparsable -> Exceptions;
   - every number it reports must literally appear in that invoice's text, otherwise -> Exceptions;
   - supplier, invoice number, date and every line description must appear verbatim in the PDF text;
   - each line's qty, rate and amount must sit together on ONE printed row, and each printed row can back only
     one extracted line (one-to-one); printed rows that look like qty x rate = amount are counted and compared
     with the number of extracted lines (coverage);
   - qty x rate = line amount, sum(lines) = subtotal, subtotal - discount + taxes = total, and
     taxable x printed tax rate = tax amount are recomputed with Decimal; any difference > 0.01 -> Exceptions
     (the printed value is kept, never "fixed").
   - every page is checked for a text layer separately, so one scanned page inside a text PDF is reported.
The XLSX is written values-only: text that looks like a formula (=, +, -, @) is stored as literal text.
The model endpoint must be on this machine (127.0.0.1/localhost) unless --allow-remote is given.
"""
import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from collections import defaultdict
from decimal import Decimal, InvalidOperation

import pymupdf
from openpyxl import Workbook
from openpyxl.styles import Font

PROMPT = """Extract this invoice into JSON with exactly these keys:
supplier, invoice_no, date, currency, lines (list of {description, qty, rate, discount, amount}),
subtotal, discount, taxes (list of {label, rate_percent, amount}), total.
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
    return val in text_nums


def norm(t):
    return re.sub(r"\s+", " ", str(t)).strip().lower()


def in_text_str(v, flat):
    """A string field must appear verbatim (whitespace/case-insensitive) in the PDF text."""
    return v not in (None, "") and norm(v) in flat


def rows_of(doc):
    """Printed rows: words grouped by page and rounded baseline, as sets of numbers."""
    rows = []
    for page in doc:
        by_y = defaultdict(list)
        for w in page.get_text("words"):
            by_y[(page.number, round(w[3]))].append(w[4])
        for k in sorted(by_y):
            rows.append([v for v in (D(t) for t in by_y[k] if re.fullmatch(r"\d[\d,]*\.?\d*", t)) if v is not None])
    return rows


def safe(v):
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, str) and v[:1] in ("=", "+", "-", "@"):
        return v  # written below with data_type forced to string
    return v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf_dir"); ap.add_argument("out")
    ap.add_argument("--api", default="http://127.0.0.1:8005/v1"); ap.add_argument("--model", default="local")
    ap.add_argument("--allow-remote", action="store_true")
    a = ap.parse_args()
    if urllib.parse.urlparse(a.api).hostname not in ("127.0.0.1", "localhost", "::1") and not a.allow_remote:
        sys.exit("refusing a non-local model endpoint (invoices must stay on this machine); use --allow-remote to override")
    inv_rows, line_rows, tax_rows, exc = [], [], [], []
    for name in sorted(f for f in os.listdir(a.pdf_dir) if f.lower().endswith(".pdf")):
        doc = pymupdf.open(os.path.join(a.pdf_dir, name))
        texts = [p.get_text() for p in doc]
        blank = [i + 1 for i, t in enumerate(texts) if len(t.strip()) < 20]
        if len(blank) == len(texts):
            exc.append((name, "", "no text layer on any page (scan?) - not extracted", "", "")); continue
        if blank:
            exc.append((name, "", f"page(s) {blank} have no text layer (scanned?) - their content is NOT extracted", "", ""))
        text = "\n".join(texts)
        rows = rows_of(doc)
        nums = {D(m) for m in re.findall(r"\d[\d,]*\.?\d*", text)} - {None}
        j = ask(a.api, a.model, text)
        no = str(j.get("invoice_no") or "")
        lines = j.get("lines") or []
        s = Decimal("0"); used = set()
        flat = norm(text)
        for lab in ("supplier", "invoice_no", "date"):
            if not in_text_str(j.get(lab), flat):
                exc.append((name, no, f"{lab} {j.get(lab)!r} missing or not found verbatim in PDF text", "", ""))
        for i, l in enumerate(lines, 1):
            q, r, amt = D(l.get("qty")), D(l.get("rate")), D(l.get("amount"))
            for lab, v in (("qty", q), ("rate", r), ("amount", amt)):
                if v is None:
                    exc.append((name, no, f"line {i} {lab} missing or unparsable ({l.get(lab)!r})", "", ""))
                elif not in_text(v, nums):
                    exc.append((name, no, f"line {i} {lab} {v} not found in PDF text", "", ""))
            present = {v for v in (q, r, amt) if v is not None}
            hit = next((k for k, row in enumerate(rows) if k not in used and present and present <= set(row)), None)
            if present and hit is None:
                exc.append((name, no, f"line {i}: qty/rate/amount not found together on one unused printed row", "", ""))
            elif hit is not None:
                used.add(hit)  # each printed row can back only one extracted line (one-to-one)
            if not in_text_str(l.get("description"), flat):
                exc.append((name, no, f"line {i} description not found verbatim in PDF text", "", ""))
            if q is not None and r is not None and amt is not None and abs(q * r - amt) > Decimal("0.01"):
                exc.append((name, no, f"line {i}: qty x rate = {q * r:.2f} but printed amount {amt}", f"{q * r:.2f}", str(amt)))
            s += amt or 0
            line_rows.append([name, j.get("supplier"), no, j.get("date"), i, l.get("description"), q, r, D(l.get("discount")), amt])
        # positions, not values: "1 x 4,500.00 = 4,500.00" repeats a value on purpose
        item_rows = sum(1 for row in rows if any(abs(row[a] * row[b] - row[c]) <= Decimal("0.01")
                                                 for a in range(len(row)) for b in range(len(row)) for c in range(len(row))
                                                 if len({a, b, c}) == 3 and row[a] > 0 and row[b] > 0 and row[c] > 0))
        if item_rows != len(lines):
            exc.append((name, no, f"coverage: {item_rows} printed rows look like qty x rate = amount, {len(lines)} lines extracted", str(item_rows), str(len(lines))))
        sub, disc, tot = D(j.get("subtotal")), D(j.get("discount")) or Decimal("0"), D(j.get("total"))
        if not lines:
            exc.append((name, no, "no line items extracted", "", ""))
        for lab, v in (("subtotal", sub), ("total", tot)):
            if v is None:
                exc.append((name, no, f"{lab} missing or unparsable ({j.get(lab)!r}) - totals NOT verified", "", ""))
        taxes = [(t.get("label"), D(t.get("amount"))) for t in (j.get("taxes") or [])]
        for t in (j.get("taxes") or []):
            tax_rows.append([name, j.get("supplier"), no, t.get("label"), D(str(t.get("rate_percent") or "").replace("%", "")), D(t.get("amount"))])
        for t in (j.get("taxes") or []):
            rate, amt_t = D(str(t.get("rate_percent") or "").replace("%", "")), D(t.get("amount"))
            if rate is None:  # fall back to a rate printed in the label, e.g. "GST 18%" or "CGST 9 %"
                m = re.search(r"(\d+(?:\.\d+)?)\s*%", str(t.get("label") or ""))
                rate = D(m.group(1)) if m else None
            if amt_t is None:
                exc.append((name, no, f"tax {t.get('label')} amount missing or unparsable", "", ""))
            elif rate is not None and sub is not None:
                exp = ((sub - disc) * rate / 100).quantize(Decimal("0.01"))
                if abs(exp - amt_t) > Decimal("0.01"):
                    exc.append((name, no, f"tax {t.get('label')}: taxable x {rate}% differs from printed amount", f"{exp:.2f}", str(amt_t)))
        tax_sum = sum((t[1] or 0 for t in taxes), Decimal("0"))
        for lab, v in (("subtotal", sub), ("discount", D(j.get("discount"))), ("total", tot)) + tuple((f"tax {t[0]}", t[1]) for t in taxes):
            if v is not None and not in_text(v, nums):
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
            ws.append([safe(v) for v in r])
            for c in ws[ws.max_row]:
                if isinstance(c.value, str) and c.value[:1] in ("=", "+", "-", "@"):
                    c.data_type = "s"  # literal text, never a formula
        ws.freeze_panes = "A2"
    sheet(wb.active, ["file", "supplier", "invoice_no", "date", "currency", "lines", "subtotal", "discount", "taxes", "total"], inv_rows)
    wb.active.title = "Invoices"
    sheet(wb.create_sheet("Line items"), ["file", "supplier", "invoice_no", "date", "line", "description", "qty", "rate", "line_discount", "amount"], line_rows)
    sheet(wb.create_sheet("Taxes"), ["file", "supplier", "invoice_no", "label", "rate_percent", "amount"], tax_rows)
    agg = defaultdict(lambda: [0, Decimal("0")])
    for r in inv_rows:
        agg[r[1]][0] += 1; agg[r[1]][1] += r[9] or 0
    sheet(wb.create_sheet("By supplier"), ["supplier", "invoices", "printed totals"], [[k, v[0], v[1]] for k, v in sorted(agg.items())])
    sheet(wb.create_sheet("Exceptions"), ["file", "invoice_no", "issue", "recomputed", "printed"], exc)
    wb.save(a.out)
    print(f"{len(inv_rows)} invoices, {len(line_rows)} line items, {len(exc)} exceptions -> {a.out}")


if __name__ == "__main__":
    main()
