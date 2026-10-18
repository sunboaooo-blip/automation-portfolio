# pdf-image-extractor

Extract every embedded image from one or more PDFs at native resolution. Each picture is saved once, and a CSV manifest lists every place it appears.

```sh
pip install pymupdf pillow
python make_test_pdf.py test.pdf            # synthetic catalogue for a quick try
python extract.py out test.pdf              # out/images/*, out/manifest.csv, out/qa.txt
```

## Behaviour

- **Loss-free output:** JPEG streams are copied byte-for-byte. Everything else (Flate, JPX, CMYK, grayscale, soft-masked transparency) is written as lossless PNG at native pixel size, with alpha kept.
- **Inline images** (`BI … ID … EI`) are decoded too. Anything undecodable is listed in `qa.txt`, never dropped silently.
- **Dedup by decoded pixels:** the same picture embedded twice with different encodings (for example JPEG and Flate) is saved once. Repeats are flagged `repeat (first at file pN)`. Dedup works across several PDFs.
- **Manifest** columns: `pdf, page, zone (header/body/footer), row_reference (same-row text), image_file, width, height, colorspace, has_transparency, placed_bbox_pt, occurrence, sha256`.
- **QA notes:**
  - vector artwork beyond table lines (curves, polygons, filled shapes) is flagged, because it is not an image object;
  - PDFs with no images produce a header-only manifest plus a warning.

## Tested

Cross-checked page by page against poppler's `pdfimages -list`:
- **Synthetic catalogue:** 13 placements → 8 unique files. Covers a repeated header logo, a transparent footer, RGB/CMYK JPEGs, grayscale, and a product photo reused on a later page.
- **Re-encoded duplicate:** the same photo embedded as Flate deduped against its JPEG twin.
- **Inline 4×2 image, JPEG 2000 image, stroke-only polygon:** extracted, converted to PNG and flagged respectively.
- **Image-free PDF:** clean warning.

## Not covered

- Vector logos as images (they would need page-region rendering).
- OCR of scanned pages.
- Row mapping when the PDF has no text layer.
