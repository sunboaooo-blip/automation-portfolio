# Automation portfolio

Small, tested tools for everyday file and data jobs: validating CSVs, cleaning text exports into Excel, pulling sheets or images out of PDFs, and transcribing audio.
Each tool is a single readable script with synthetic test data and a written list of what it does **not** do.
The tools are built with Claude.

This portfolio keeps growing. New tools are added as they are built and tested. Everything here uses synthetic or public-domain data only; no client files are ever published.

| Tool | What it does | Runs on |
|---|---|---|
| [csv-validate](csv-validate/) | Checks CSV files against editable rules and reports every issue with file / record / line / field. CI-friendly exit codes. | Python 3.8+, standard library only (tested on Ubuntu 22.04's Python 3.10.12) |
| [txt-to-xlsx](txt-to-xlsx/) | Text data file → clean XLSX: whole-row dedup, every blank filled with one placeholder, no empty cells, a step log. | Python + openpyxl |
| [pdf-sheet-picker](pdf-sheet-picker/) | Selects drawing sheets by discipline (e.g. electrical E/T) from a construction set by reading the title block, rotated pages included. | Python + PyMuPDF (pypdf fallback) |
| [pdf-image-extractor](pdf-image-extractor/) | Extracts every embedded image at native resolution, de-duplicates by pixels, and writes a CSV manifest with page / row / position. | Python + PyMuPDF |
| [logo-package-sample](logo-package-sample/) | Minimalist geometric logo package for a fictional brand: editable SVG (live text + outlined), icons, PNG/JPG exports, PDF style guide. | Python + CairoSVG + HarfBuzz + fontTools |
| [invoice-generator](invoice-generator/) | CSV / JSON / shared Google Sheet → branded invoice + receipt PDFs from one config; Decimal money, paginated long invoices. | Python + fpdf2 |
| [product-background-removal](product-background-removal/) | Batch cutouts at original resolution: transparent PNG, white JPEG, consistent-margin crop, 100% edge-check sheets; ~5 s per 2048×1536 image. | Python, local BiRefNet |
| [product-price-cards](product-price-cards/) | Product photo + facts file → 5 colourful JPEG cards with name, specs, struck-through MRP, offer price and computed discount; product never redrawn, text never AI-drawn. | Python + Pillow, local BiRefNet |
| [transcription](transcription/) | Audio/video → TXT / SRT / VTT with local Whisper on GPU, plus a punctuation pass that is guaranteed not to change any word. | Python, CUDA GPU |

## Case studies (real client work, privacy stripped)

- [AI-assisted character image edits](case-studies/ai-character-image-edits.md): the Gemini image-editing pipeline with sampling, masked repairs, a two-gate QA process and a 14-class defect register built from real client feedback.

## Profile kit

[profile-kit/](profile-kit/): portfolio cards and profile text, generated from this repo's own test results.

## Run the tests

```sh
./run_tests.sh          # creates a local venv, runs every tool on its fixtures, checks results and exit codes
```

The transcription tests need a GPU and model weights, so they are documented in that folder rather than run here.

## Principles used throughout

- **Never modify inputs.** Inputs are only read. csv-validate and txt-to-xlsx additionally refuse an output path that points at an input (including symlinks and hard links); pdf-sheet-picker refuses to write its PDF over the source. The other tools write only into a separate output folder.
- **Don't guess silently.** Ambiguous cases are reported for review instead of being decided quietly.
- **Self-check the output.** Tools re-read what they wrote (for example, empty cells = 0 and duplicate rows = 0) and report the result.
- **Honest limits.** Each README lists what was not tested.

License: MIT.
