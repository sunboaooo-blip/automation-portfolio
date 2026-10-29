# pdf-to-a4

Scales every page of a PDF onto A4, proportionally and centred, **never cropped or enlarged**, for example a print-ready book exported larger than A4.

```sh
python make_book.py book_in.pdf           # synthetic 159-page 8.75x11.25 in book: edge frame, vector circles, a raster image
python scale_a4.py book_in.pdf book_a4.pdf --box crop
```

- Each page is placed as a vector XObject (`show_pdf_page`). Drawings stay vector, and embedded images keep their original pixels (no re-rendering, no recompression).
- A page that already fits A4 is centred at 100%.
- `--box media|crop|trim` chooses which page box is scaled; for example, trim scales without the bleed.
- **Self-check per page:** page count and order, A4 size, scale ≤ 1, aspect ratio preserved, placed box inside the page. Any failure exits.

Result on the synthetic book: 159 → 159 pages, all A4, page order verified by label text, image bytes identical (1200×1200 → 1200×1200), vector drawings 7 → 7 per page, edge frame fully visible (`example-output/qa_p1.png`, `qa_p159.png`). Runtime 0.15 s.

## What it does not do

- It does not fill the A4 page. When the aspect ratio differs, a small white band is unavoidable without cropping.
- It does not check fonts or colour for print, and it gives no print-service (e.g. KDP) approval.
- It has been tested on a synthetic book, not a real Canva export.
