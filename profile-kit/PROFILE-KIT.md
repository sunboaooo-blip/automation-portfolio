# Profile kit (Freelancer)

Ready-to-paste material for the public profile. Every claim links back to a tested folder in this repo.

## Skills to add (owner-approved 2026-10-22)

Excel · Data Processing · Data Entry · Python · Data Analysis · PDF · Google Sheets

## Headline (≤ 50 characters)

`Data, PDF & Excel Automation · AI Image Editing`

## Summary

> I turn messy files into clean, checked results: CSV and Excel cleanup, PDF text, table and image extraction, data validation, and audio/video transcription. Every job ends with a self-check, such as zero empty cells, zero duplicate rows, or an exact page and row match with the source, and anything uncertain is flagged for you instead of guessed.
>
> I work with Claude (AI) plus scripted tools that I test before quoting. The tools and test results are public: github.com/sunboaooo-blip/automation-portfolio
>
> Typical small jobs: PDF → Word/TXT/Excel, CSV validation reports, text exports → clean XLSX, picking sheets from drawing sets, subtitles (SRT/VTT), product-image cutouts and edits.
>
> I prefer a small paid first batch with clear limits, then scale up once you are happy with the result.

## Portfolio items (title / image / description / link)

| # | Title | Image | Description | Link |
|---|---|---|---|---|
| 1 | CSV validation with exact locations | `01-csv-validate.png` | Checks CSV files against editable rules and reports each problem with record, line and field. Exit codes plug into CI. Tested on Ubuntu 22.04's Python 3.10. | repo/csv-validate |
| 2 | Messy text export → clean Excel | `02-txt-to-xlsx.png` | Removes duplicate rows, fills every blank with your placeholder and keeps codes like 01234 as text. The written file is re-checked automatically (0 empty cells, 0 duplicates, 0 formulas). | repo/txt-to-xlsx |
| 3 | Pick electrical sheets from drawing sets | `03-pdf-sheet-picker.png` | Reads each sheet's title block (rotated pages included), exports the selected sheets in their original order, and lists unclear pages for review instead of guessing. On a real 74-page set: 12/12 electrical sheets in 2.9 s. | repo/pdf-sheet-picker |
| 4 | Extract every image from PDFs | `04-pdf-image-extractor.png` | Native-resolution images, duplicates detected by pixel content, and a CSV manifest of page, position and same-row text. | repo/pdf-image-extractor |
| 5 | Audio & video → text and subtitles | `05-transcription.png` | Local Whisper on our own GPU, with TXT/SRT/VTT output and a punctuation pass that never changes a word. Error rates measured on public test sets. | repo/transcription |
| 6 | Minimal logo package (fictional brand) | `06-logo-package.png` | Two concepts as editable SVG (live text plus outlined), icons, PNG/JPG exports and a one-page style guide with exact colours and open-licence fonts. | repo/logo-package-sample |

Optional 7th item, text only, no client images: **AI-assisted character image edits**. Process case study → repo/case-studies/ai-character-image-edits.md

## Rules for whoever pastes this

- Public text says "Claude" only; never name model tiers.
- No client names, IDs, images or payment claims.
- Do not claim human proofreading, Adobe-native files or results that are not in the linked folders.
- `make_cards.py` regenerates cards 1–5 from the repo's own fixtures and results.
