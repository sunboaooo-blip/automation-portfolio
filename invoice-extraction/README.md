# invoice-extraction

**Invoice PDFs → one Excel workbook**, with every number checked against the source.

```sh
python extract_invoices.py sample-invoices/ out.xlsx --api http://127.0.0.1:8005/v1 --model <local-model>
```

The workbook has four sheets:

| sheet | contents |
|---|---|
| **Invoices** | one row per invoice: supplier, number, date, line count, subtotal, discount, taxes, total |
| **Line items** | one row per line: description, qty, rate, amount |
| **By supplier** | invoice count and printed totals per supplier |
| **Exceptions** | everything that does not add up or cannot be traced to the PDF |

## How it avoids silent errors

1. **Text comes from the PDF's own text layer** (PyMuPDF). A page without a text layer, such as a scan, is reported rather than guessed.
2. A **local language model on our own GPU** maps that text to fields. The invoices never leave the machine.
3. **Nothing the model returns is trusted.** Every number is checked two ways:
   - it must literally appear in that invoice's text;
   - the arithmetic is recomputed with Decimal: qty × rate = amount, the sum of lines = subtotal, and subtotal − discount + taxes = total.
   Any mismatch goes to **Exceptions**, with the recomputed and printed values side by side. Printed values are kept and never "fixed".

## Result on the included samples

Six fictional invoices in two different layouts:
- GST at 18%, with a 70-line invoice running over three pages;
- CGST/SGST split with a discount.

One invoice (`SE-0042`) was **planted with a wrong grand total**.

- 6 invoices and 80 line items extracted.
- Every number was traced to the source text, and every line passed the qty × rate check.
- **Exactly one exception:** `SE-0042`, where the recomputed total is 4,312.90 against a printed 4,900.00.
- About 3 minutes in total with a 12B local model, mostly the 70-line invoice.

## Limits

- Selectable-text PDFs only. Scanned invoices need a separate OCR or vision pass and are quoted after a sample.
- Multi-currency conversion and tax-rule validation (for example, whether 18% is the right rate) are not attempted. The workbook reports what is printed.
- The sample invoices are generated: three by [`invoice-generator`](../invoice-generator/) and three by `make_alt.py`, all with fictional suppliers.
