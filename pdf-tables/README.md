# pdf-tables

PDF tables, **selectable text and scanned pages mixed**, become one XLSX per PDF with one worksheet per page.

```sh
mkdir -p in && python make_test.py && python make_hard.py        # synthetic test PDFs + truth files
python pdftables.py in out --api http://127.0.0.1:8002/v1 --model gemma-4-31b
python score.py truth.json out                                     # every cell vs. the typed truth
python pdftables.py in_hard out_hard --api http://127.0.0.1:8002/v1 --model gemma-4-31b
python score.py truth_hard.json out_hard
```

## How each page is read

| Page type | Route |
|---|---|
| Has a text layer | PyMuPDF `find_tables()`. Cell text is copied from the PDF's own text layer, so there is no OCR on these pages. |
| Scanned | Deskew, median-filter + Otsu, detect the ruled grid, then read **every cell twice**: (1) Tesseract on each cell, (2) a local vision model on the whole table. The model is *not* told the grid shape, so the row/column count it reads independently checks the grid detector. |
| No table | The page still gets a worksheet that says so. On a scanned page, "no ruled table detected" is also listed as an exception, never treated as a silent empty result. |

- Cells where both readers agree are written plainly.
- Cells where the readers differ are written **yellow** and listed on the Exceptions sheet with both readings. They are meant to be checked by hand against the page image before delivery.
- If the two grid shapes disagree, or more than 20% of a table's cells are unconfirmed, the whole table is marked unconfirmed and reported as below scan eligibility.
- All values are literal text: `007` and `1,200.00` stay exactly as printed, and no formulas are written.
- The model endpoint must be on the same machine unless `--allow-remote` is passed. Documents are not sent to cloud services.

## Results (synthetic data, see RUNLOG.txt)

| Set | Content | Result |
|---|---|---|
| `in/` | text-layer table; 200 dpi skewed noisy scan; text-only page; a scan with two tables | **145 / 145 cells exact, 0 yellow**, 32 s total |
| `in_hard/` | deliberately bad 110 dpi blurred scan | grid misdetected (17 rows vs 11). Reader 2's independent shape caught it: whole table marked unconfirmed, page reported below eligibility. Nothing wrong was presented as confirmed. |

`example-output/` holds the three workbooks.

## What it does not do

- It does not handle unruled tables on scanned pages; scanned pages need ruling lines.
- It does not rebuild merged cells on scanned pages (text-layer pages keep PyMuPDF's merge handling).
- It does not read handwriting.
- It does not repair poor scans. Below about 200 dpi, or when many cells disagree, it asks for a re-scan instead of guessing.
- It has been tested on synthetic tables only. Real scan quality varies and is checked per job before work starts.

Needs: Python 3.10+, PyMuPDF 1.28, numpy, Pillow, openpyxl, Tesseract 5, and an OpenAI-compatible local vision model (tested with Gemma 4 31B on vLLM). Because of the GPU and model requirement, these tests are documented here rather than run by `run_tests.sh`.
