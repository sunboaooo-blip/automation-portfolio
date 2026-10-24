# invoice-extraction

**Invoice PDFs → one Excel workbook**, with every number checked against the source.

```sh
python extract_invoices.py sample-invoices/ out.xlsx --api http://127.0.0.1:8005/v1 --model <local-model>
```

The workbook has four sheets:

| sheet | contents |
|---|---|
| **Invoices** | one row per invoice: supplier, number, date, line count, subtotal, discount, taxes, total |
| **Line items** | one row per line: description, qty, rate, line discount, amount |
| **Taxes** | one row per printed tax: label, rate %, amount (CGST and SGST kept separate) |
| **By supplier** | invoice count and printed totals per supplier |
| **Exceptions** | everything that does not add up or cannot be traced to the PDF |

## How it avoids silent errors

1. **Text comes from the PDF's own text layer** (PyMuPDF). A page without a text layer, such as a scan, is reported rather than guessed.
2. A **local language model on our own GPU** maps that text to fields. The invoices never leave the machine.
3. **Nothing the model returns is trusted.** Each of these goes to **Exceptions**, with the recomputed and printed values side by side; printed values are kept and never "fixed":
   - a required value (total, subtotal, each line's qty/rate/amount) that is **missing or unparsable**;
   - a number that does not literally appear in that invoice's text;
   - a supplier name, invoice number, date or **line description** that does not appear verbatim in the text;
   - a line whose qty, rate and amount are **not printed together on one row** of the PDF. Each printed row can back only **one** extracted line, so duplicates are caught;
   - **coverage:** the number of printed rows where qty × rate = amount is compared with the number of extracted lines, so a dropped line is caught;
   - arithmetic that does not add up when recomputed with Decimal: qty × rate = amount, the sum of lines = subtotal, subtotal − discount + taxes = total, and **taxable × the printed tax rate = tax amount**.
4. **Every page is checked for a text layer separately**, so one scanned page inside an otherwise digital PDF is reported, not silently skipped.
5. The XLSX holds values only. Text that looks like a formula (`=…`, `+…`, `-…`, `@…`) is stored as literal text.
6. The model endpoint must be on this machine (`127.0.0.1` or `localhost`); anything else is refused unless `--allow-remote` is given.

## Result on the included samples

Six fictional invoices in two different layouts:
- GST at 18%, with a 70-line invoice running over three pages;
- CGST/SGST split with a discount.

One invoice (`SE-0042`) was **planted with a wrong grand total**.

- 6 invoices and 80 line items extracted.
- Every number was traced to the source text, and every line passed the qty × rate check.
- **Exactly one exception:** `SE-0042`, where the recomputed total is 4,312.90 against a printed 4,900.00.
- About 3 minutes in total with a 12B local model, mostly the 70-line invoice.

## Negative tests (`negative-tests/`, log in `RUNLOG.txt`)

Four deliberately broken invoices:

| fixture | planted problem | result |
|---|---|---|
| `VH-101` | item text `=HYPERLINK(...)` | stored as literal text (cell type `s`), not a formula |
| `VH-102` | no grand total printed | "total missing – totals NOT verified" |
| `VH-103` | GST printed as 118.00 for 18% of 600.00 | recomputed 108.00 against printed 118.00 |
| `VH-104-hybrid` | page 2 is a scanned image | "page(s) [2] have no text layer" |

**Model-mistake simulation (`test_tamper.py`).** The real model answer for one invoice was altered after the call, and each mistake was caught:
- a dropped line → coverage (3 printed vs 2 extracted), plus the subtotal mismatch;
- a duplicated line → no unused printed row, plus coverage;
- an invented description → "description not found verbatim";
- a wrong supplier → "supplier not found verbatim".

A non-local endpoint was refused with exit 1. The six regular invoices were re-run and gave the same result as before: 80 lines and one exception, the planted wrong total. Because these fixtures have no column headers, the model also left `qty` empty on two of them. Those were **flagged, not filled in**, which is the intended behaviour.

## Limits

- Header fields (supplier, number, date) are checked for verbatim presence in the text, not for their position on the page.
- The coverage count recognises item rows that print qty, rate and amount. Layouts that print only an amount per line need a buyer-specific rule, set up at job time.
- Selectable-text PDFs only. Scanned invoices need a separate OCR or vision pass and are quoted after a sample.
- Multi-currency conversion and tax-rule validation (for example, whether 18% is the right rate) are not attempted. The workbook reports what is printed.
- The sample invoices are generated: three by [`invoice-generator`](../invoice-generator/) and three by `make_alt.py`, all with fictional suppliers.
