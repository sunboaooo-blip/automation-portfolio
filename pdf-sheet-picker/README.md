# pdf-sheet-picker

Pick drawing sheets by discipline from a construction document set (for example electrical **E** and telecom **T**). The sheet number is read from each page's title block, and the matching pages are written out in their original order.

```sh
pip install pymupdf pypdf          # PyMuPDF is optional but strongly recommended (see below)
python -I sheetpick.py fixtures/set12.pdf out --prefixes E,T
```

Outputs: `<name>-E-T.pdf` (selected pages), `sheets.csv` (every page with its number and status, plus a note) and `sheets.txt` (exported sheet numbers). The source PDF is only read.

## How it decides

- It looks only inside the title-block box. The default is the bottom-right of the page *as displayed*; it can be changed with `--region`. Within the box it takes the **largest** sheet-number-like token, so cross-references such as "see E2.01" are ignored.
- Recognised styles: `E1.01 E101 E-201 E.000 ES-101 EP101 T1.0 TA-1`. A prefix matches when it starts with a requested letter, so `E` covers E/ES/EP.
- **Rotated pages** (`/Rotate` 90/180/270, common in CAD exports) are mapped to the page as displayed.
- **No guessing:** a page with two equally large different numbers, or no number at all, is held for review (`REVIEW: …`) and not exported. `--include-ambiguous` exports a best guess, but the run still exits 1.

Exit: `0` = exported with nothing to review, `1` = review needed or nothing matched, `2` = error.

## Engines

- **PyMuPDF** (default when installed): fast, and handles text inside embedded form objects (Form XObjects).
- **pypdf** fallback (pure Python): handles rotation, but cannot place text inside Form XObjects reliably. It therefore **holds such pages for review** instead of guessing.

## Tested

| Fixture | PyMuPDF | pypdf |
|---|---|---|
| `set12.pdf`: 12 sheets, mixed number styles, decoy cross-refs | 6/6 E/T exported, exit 0 | same |
| `ambiguous.pdf`: two same-size numbers / no number | 0 exported, 2 held, exit 1 | same |
| `rotated.pdf`: 4 sheets stored at /Rotate 0/90/180/270 that render identical to upright sheets | E2.01, E2.02, T2.01 exported, A3.01 skipped, exit 0 | 4 held (Form XObject content), exit 1 |
| `make_heavy.py` (29 MB, 40 sheets × 20k vectors + 2k labels) | 14/14 in 2.7 s | 14/14 in 12.4 s |

The pypdf results were also reproduced independently on Windows (Python 3.12, pypdf 6.10).

**Real project set** (74 pages, 88 MB, client sample, not published):

| Engine | Time | Result |
|---|---|---|
| PyMuPDF 1.28.2 | 2.9 s | Sheet numbers found on 66 pages (G, SD, L, IR, S, A, M, P, E series). The 12 electrical sheets (E001–E701 incl. ES101/ES102) were exported in original order, and each exported page is text-identical to its source page. 8 civil pages numbered only "SHEET n OF 15" (no discipline letter) were held for review. Input unchanged. |
| pypdf fallback | ~104 s | Held 56 pages it could not read reliably. |

This is why PyMuPDF is the recommended engine.

## Not covered

- Scanned/raster title blocks (would need OCR).
- A GUI or folder watching (planned).
