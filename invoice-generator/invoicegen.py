#!/usr/bin/env python3
"""Branded invoice + receipt PDFs from CSV, JSON or a shared Google Sheet.

usage:
  invoicegen.py --config brand.json --csv invoices.csv  --out out/
  invoicegen.py --config brand.json --json invoices.json --out out/
  invoicegen.py --config brand.json --sheet "https://docs.google.com/spreadsheets/d/<id>/edit#gid=0" --out out/

Input rows (one per line item): invoice_no, date, customer, item, qty, unit_price
JSON: a list of such objects. The Google Sheet must be shared "anyone with the link can view";
it is read via its CSV export URL (no account, no credentials).
All money is Decimal, rounded half-up to 2 places per line and on tax; totals are the sum of rounded lines.
Writes <out>/invoice-<no>.pdf and <out>/receipt-<no>.pdf, plus <out>/summary.csv for checking.
"""
import argparse
import csv
import io
import json
import os
import re
import sys
import urllib.request
import unicodedata
from collections import OrderedDict
from decimal import ROUND_HALF_UP, Decimal

from fpdf import FPDF

Q = Decimal("0.01")
MAX_LINES = 500
FIELDS = ["invoice_no", "date", "customer", "item", "qty", "unit_price"]


def money(x):
    return Decimal(str(x).replace(",", "").strip() or "0").quantize(Q, ROUND_HALF_UP)


def load_rows(a):
    if a.csv:
        return list(csv.DictReader(open(a.csv, encoding="utf-8-sig", newline="")))
    if a.json:
        return json.load(open(a.json, encoding="utf-8"))
    m = re.search(r"/spreadsheets/d/([A-Za-z0-9_-]+)", a.sheet)
    gid = (re.search(r"gid=(\d+)", a.sheet) or [None, "0"])[1]
    url = f"https://docs.google.com/spreadsheets/d/{m.group(1)}/export?format=csv&gid={gid}"
    with urllib.request.urlopen(url, timeout=30) as r:
        return list(csv.DictReader(io.StringIO(r.read().decode("utf-8-sig"))))


def check_headers(rows):
    """Run on the ORIGINAL rows, before any filling, so missing columns are detected."""
    if not rows:
        sys.exit("input has no data rows")
    missing = [f for f in FIELDS if f not in rows[0]]
    if missing:
        sys.exit(f"input is missing columns: {missing}")
    if len(rows) > MAX_LINES:
        sys.exit(f"{len(rows)} line items exceed the agreed limit of {MAX_LINES} per run")


def safe_name(s):
    """Invoice number -> safe file-name part: ASCII letters/digits/-/_ only."""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^A-Za-z0-9_-]+", "_", s).strip("_")[:60]
    return s or "invoice"


def group(rows):
    inv = OrderedDict()
    for r in rows:
        k = str(r["invoice_no"]).strip()
        d = inv.setdefault(k, {"invoice_no": k, "date": str(r["date"]).strip(),
                               "customer": str(r["customer"]).strip(), "lines": []})
        qty = Decimal(str(r["qty"]).strip())
        price = money(r["unit_price"])
        d["lines"].append({"item": str(r["item"]).strip(), "qty": qty, "price": price,
                           "amount": (qty * price).quantize(Q, ROUND_HALF_UP)})
    return list(inv.values())


class Doc(FPDF):
    def __init__(self, cfg, base):
        super().__init__(format=cfg.get("page", "A4"))
        self.cfg, self.base = cfg, base
        self.add_font("Body", "", os.path.join(base, cfg["font_regular"]))
        self.add_font("Body", "B", os.path.join(base, cfg["font_bold"]))
        self.set_auto_page_break(True, 25)

    def header(self):
        c = self.cfg
        if c.get("logo"):
            self.image(os.path.join(self.base, c["logo"]), x=15, y=12, h=18)
        self.set_xy(110, 12)
        self.set_font("Body", "B", 14); self.set_text_color(*hexrgb(c["color_primary"]))
        self.multi_cell(85, 7, c["business_name"], align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Body", "", 9); self.set_text_color(60, 60, 60)
        for line in c["business_address"]:
            self.set_x(110); self.multi_cell(85, 4.5, line, align="R", new_x="LMARGIN", new_y="NEXT")
        self.ln(8)

    def footer(self):
        self.set_y(-15); self.set_font("Body", "", 8); self.set_text_color(120, 120, 120)
        self.cell(0, 5, f"{self.cfg['footer']}   ·   page {self.page_no()}/{{nb}}", align="C")


def hexrgb(h):
    h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def render(inv, cfg, base, out, kind):
    pdf = Doc(cfg, base); pdf.alias_nb_pages(); pdf.add_page()
    cur, rate = cfg["currency"], Decimal(str(cfg["tax_rate"]))
    subtotal = sum((l["amount"] for l in inv["lines"]), Decimal("0"))
    tax = (subtotal * rate).quantize(Q, ROUND_HALF_UP)
    total = subtotal + tax
    pdf.set_font("Body", "B", 20); pdf.set_text_color(*hexrgb(cfg["color_primary"]))
    pdf.cell(0, 10, "INVOICE" if kind == "invoice" else "RECEIPT", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Body", "", 10); pdf.set_text_color(30, 30, 30)
    for k, v in (("No.", inv["invoice_no"]), ("Date", inv["date"]), ("Bill to", inv["customer"])):
        pdf.cell(25, 6, k); pdf.multi_cell(0, 6, v, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    widths, heads = (95, 20, 32, 33), ("Item", "Qty", f"Unit ({cur})", f"Amount ({cur})")
    pdf.set_fill_color(*hexrgb(cfg["color_primary"])); pdf.set_text_color(255, 255, 255); pdf.set_font("Body", "B", 10)
    for w, h in zip(widths, heads):
        pdf.cell(w, 8, h, border=0, fill=True, align="L" if h == "Item" else "R")
    pdf.ln(); pdf.set_text_color(30, 30, 30); pdf.set_font("Body", "", 10)
    for i, l in enumerate(inv["lines"]):
        fill = i % 2 == 1; pdf.set_fill_color(245, 246, 248)
        # long item text wraps inside its column; the numeric cells take the same row height
        lines = pdf.multi_cell(widths[0], 6, l["item"], dry_run=True, output="LINES")
        h = 6 * max(1, len(lines))
        if pdf.get_y() + h > pdf.page_break_trigger:
            pdf.add_page()
        x, y = pdf.get_x(), pdf.get_y()
        pdf.multi_cell(widths[0], 6, l["item"], fill=fill, new_x="RIGHT", new_y="TOP", max_line_height=6)
        pdf.set_xy(x + widths[0], y)
        pdf.cell(widths[1], h, f"{l['qty'].normalize():f}", fill=fill, align="R")
        pdf.cell(widths[2], h, f"{l['price']:,.2f}", fill=fill, align="R")
        pdf.cell(widths[3], h, f"{l['amount']:,.2f}", fill=fill, align="R")
        pdf.set_xy(x, y + h)
    pdf.ln(3)
    for label, val, bold in (("Subtotal", subtotal, False), (f"{cfg['tax_label']} ({rate * 100:.2f}%)", tax, False), ("Total", total, True)):
        pdf.set_font("Body", "B" if bold else "", 11 if bold else 10)
        pdf.cell(sum(widths[:3]), 7, label, align="R"); pdf.cell(widths[3], 7, f"{cur} {val:,.2f}", align="R", new_x="LMARGIN", new_y="NEXT")
    if kind == "receipt":
        pdf.ln(6); pdf.set_font("Body", "", 9); pdf.set_text_color(90, 90, 90)
        pdf.multi_cell(0, 5, cfg["receipt_note"])
    path = os.path.join(out, f"{kind}-{safe_name(inv['invoice_no'])}.pdf")
    if os.path.exists(path) and kind == "invoice" and path in render.written:
        sys.exit(f"two invoice numbers map to the same file name: {path}")
    render.written.add(path); pdf.output(path)
    return subtotal, tax, total


render.written = set()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--csv"); src.add_argument("--json"); src.add_argument("--sheet")
    ap.add_argument("--out", default="out")
    a = ap.parse_args()
    cfg = json.load(open(a.config, encoding="utf-8")); base = os.path.dirname(os.path.abspath(a.config))
    os.makedirs(a.out, exist_ok=True)
    raw = load_rows(a)
    check_headers(raw)
    rows = [{k: r.get(k, "") for k in FIELDS} for r in raw]
    summary = []
    for inv in group(rows):
        sub, tax, tot = render(inv, cfg, base, a.out, "invoice")
        render(inv, cfg, base, a.out, "receipt")
        summary.append({"invoice_no": inv["invoice_no"], "lines": len(inv["lines"]), "subtotal": f"{sub:.2f}",
                        "tax": f"{tax:.2f}", "total": f"{tot:.2f}"})
    with open(os.path.join(a.out, "summary.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(summary[0])); w.writeheader(); w.writerows(summary)
    print(f"{len(summary)} invoice(s) + receipt(s) written to {a.out}")


if __name__ == "__main__":
    main()
