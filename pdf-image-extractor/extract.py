"""Extract every embedded raster image from PDFs at native resolution, dedupe, and write a manifest.

usage: extract.py OUT_DIR PDF [PDF ...]
Writes OUT_DIR/images/*, OUT_DIR/manifest.csv (one row per occurrence), OUT_DIR/qa.txt.
"""
import csv
import hashlib
import sys
from pathlib import Path

import pymupdf

HEADER_FRAC, FOOTER_FRAC = 0.12, 0.88


def row_ref(page, bbox, words):
    """Text on the same horizontal band as the image (the table row), or header/footer zone."""
    h = page.rect.height
    cy = (bbox.y0 + bbox.y1) / 2
    zone = "header" if cy < h * HEADER_FRAC else "footer" if cy > h * FOOTER_FRAC else "body"
    band = [w for w in words if w[1] < bbox.y1 and w[3] > bbox.y0 and w[2] <= bbox.x0]
    text = " ".join(w[4] for w in sorted(band, key=lambda w: (w[0], w[1])))
    return zone, text[:120]


def save_pixmap(pix, mask_pix, stem, img_dir):
    if mask_pix is not None:
        pix = pymupdf.Pixmap(pix, mask_pix)
    if pix.n - pix.alpha >= 4:  # CMYK/DeviceN -> RGB for PNG
        pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
    path = img_dir / f"{stem}.png"
    pix.save(path)
    return path, pix.width, pix.height


def save_image(doc, xref, smask, stem, img_dir):
    """Write loss-free: JPEG streams as-is when no mask, everything else (incl. JPX) as PNG."""
    info = doc.extract_image(xref)
    if not smask and info["ext"] == "jpeg":
        path = img_dir / f"{stem}.jpg"
        path.write_bytes(info["image"])
        return path, info["width"], info["height"], info.get("cs-name", "")
    path, w, h = save_pixmap(pymupdf.Pixmap(doc, xref), pymupdf.Pixmap(doc, smask) if smask else None,
                             stem, img_dir)
    return path, w, h, info.get("cs-name", "")


def inline_images(page):
    """Image blocks from the text layer; used for inline (BI/ID/EI) images that have no xref."""
    blocks = page.get_text("dict", flags=pymupdf.TEXT_PRESERVE_IMAGES)["blocks"]
    return [b for b in blocks if b["type"] == 1]


def near(a, b, tol=0.5):
    return all(abs(x - y) <= tol for x, y in zip(a, b))


def main(out_dir, pdfs):
    out = Path(out_dir)
    img_dir = out / "images"
    img_dir.mkdir(parents=True, exist_ok=True)
    seen = {}  # content hash -> output filename
    rows, qa = [], []
    for pdf in map(Path, pdfs):
        doc = pymupdf.open(pdf)
        n_listed = n_occ = 0
        for page in doc:
            words = page.get_text("words")
            images = page.get_images(full=True)
            n_listed += len(images)
            smasks = {im[0]: im[1] for im in images}
            all_infos = page.get_image_info(xrefs=True)
            infos = [i for i in all_infos if i["xref"]]
            inl = [i for i in all_infos if not i["xref"]]
            iblocks = inline_images(page) if inl else []
            missing = set(smasks) - {i["xref"] for i in infos}
            if missing:
                qa.append(f"{pdf.name} p{page.number + 1}: image xrefs without placement {sorted(missing)}")
            # vector content beyond plain table lines/cell rectangles: curves, polygons, filled shapes
            vec = [d for d in page.get_drawings() if d["items"] and (
                any(it[0] in ("c", "qu") for it in d["items"]) or
                (d.get("fill") and not all(it[0] == "re" for it in d["items"])) or
                sum(it[0] == "l" for it in d["items"]) >= 3)]  # polygon/icon outline, not a rule
            if vec:
                qa.append(f"{pdf.name} p{page.number + 1}: {len(vec)} vector path(s) beyond table lines - "
                          "not image objects; need region render if buyer counts them as graphics")
            for k, info in enumerate(sorted(infos, key=lambda i: (i["bbox"][1], i["bbox"][0]))):
                xref = info["xref"]
                smask = smasks.get(xref, 0)
                # hash decoded pixels so the same picture embedded twice with different encoding still dedupes
                pix = pymupdf.Pixmap(doc, xref)
                raw = f"{pix.width}x{pix.height}n{pix.n}".encode() + pix.samples + \
                    (pymupdf.Pixmap(doc, smask).samples if smask else b"")
                h = hashlib.sha256(raw).hexdigest()
                bbox = pymupdf.Rect(info["bbox"])
                zone, ref = row_ref(page, bbox, words)
                first = h not in seen
                if first:
                    stem = f"{pdf.stem}_p{page.number + 1:03d}_{zone}_{len(seen) + 1:04d}"
                    path, w, hgt, cs = save_image(doc, xref, smask, stem, img_dir)
                    seen[h] = (path.name, w, hgt, cs, f"{pdf.name} p{page.number + 1}")
                name, w, hgt, cs, first_at = seen[h]
                rows.append({"pdf": pdf.name, "page": page.number + 1, "zone": zone,
                             "row_reference": ref, "image_file": name, "width": w, "height": hgt,
                             "colorspace": cs, "has_transparency": bool(smask),
                             "placed_bbox_pt": ",".join(f"{v:.0f}" for v in bbox),
                             "occurrence": "first" if first else f"repeat (first at {first_at})",
                             "sha256": h[:16]})
                n_occ += 1
            for info in inl:
                bbox = pymupdf.Rect(info["bbox"])
                blk = next((b for b in iblocks if near(b["bbox"], bbox)), None)
                if blk is None:
                    qa.append(f"{pdf.name} p{page.number + 1}: inline image at {tuple(round(v) for v in bbox)} "
                              "could not be decoded - needs manual review")
                    continue
                pix = pymupdf.Pixmap(blk["image"])
                mpix = pymupdf.Pixmap(blk["mask"]) if blk.get("mask") else None
                h = hashlib.sha256(f"{pix.width}x{pix.height}n{pix.n}".encode() + pix.samples +
                                   (mpix.samples if mpix else b"")).hexdigest()
                zone, ref = row_ref(page, bbox, words)
                first = h not in seen
                if first:
                    stem = f"{pdf.stem}_p{page.number + 1:03d}_{zone}_{len(seen) + 1:04d}"
                    path, w, hgt = save_pixmap(pix, mpix, stem, img_dir)
                    seen[h] = (path.name, w, hgt, "inline", f"{pdf.name} p{page.number + 1}")
                name, w, hgt, cs, first_at = seen[h]
                rows.append({"pdf": pdf.name, "page": page.number + 1, "zone": zone,
                             "row_reference": ref, "image_file": name, "width": w, "height": hgt,
                             "colorspace": cs, "has_transparency": mpix is not None,
                             "placed_bbox_pt": ",".join(f"{v:.0f}" for v in bbox),
                             "occurrence": "first" if first else f"repeat (first at {first_at})",
                             "sha256": h[:16]})
                n_occ += 1
        qa.append(f"{pdf.name}: {doc.page_count} pages, {n_listed} image refs, {n_occ} placements")
    if not rows:
        qa.append("NO embedded raster images found - check for vector-only or scanned content")
    fields = ["pdf", "page", "zone", "row_reference", "image_file", "width", "height", "colorspace",
              "has_transparency", "placed_bbox_pt", "occurrence", "sha256"]
    with open(out / "manifest.csv", "w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=fields)
        wr.writeheader()
        wr.writerows(rows)
    files = sorted(p.name for p in img_dir.iterdir())
    qa.append(f"unique images saved: {len(seen)}; files on disk: {len(files)}; "
              f"manifest rows: {len(rows)}; repeats flagged: {sum(r['occurrence'] != 'first' for r in rows)}")
    assert len(files) == len(seen), "file count != unique count"
    (out / "qa.txt").write_text("\n".join(qa) + "\n")
    print("\n".join(qa))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
