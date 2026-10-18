"""Logo package builder for a FICTIONAL brand ("Solvane"), used as a portfolio sample.

Writes, per concept:
  svg/<concept>-live.svg      editable SVG: geometric shapes + live text (font-family Manrope)
  svg/<concept>-outlined.svg  same, text converted to vector paths (no font needed)
  png/<concept>-{64..2048}.png, jpg/<concept>-1024.jpg (white background)
plus style-guide.svg / style-guide.pdf with exact colours and fonts.
Shapes are hand-built geometry (circles, arcs, rects), never embedded rasters.
"""
import math
import os

import cairosvg
import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

INK, SUN, SEA, SKY, PAPER = "#1F2430", "#FF7A2F", "#14A38B", "#FFC94A", "#FFFFFF"
NAME = "solvane"
FONT_BOLD = "fonts/Manrope-Bold.ttf"
FONT_MED = "fonts/Manrope-Medium.ttf"
FONT_BODY = "fonts/Inter-Regular.ttf"


def text_path(text, font_file, size, x, y, tracking=0.0):
    """Shape `text` with HarfBuzz (kerning included) and return SVG path data placed at baseline (x, y)."""
    blob = hb.Blob.from_file_path(font_file)
    face = hb.Face(blob)
    font = hb.Font(face)
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(font, buf, {"kern": True, "liga": True})
    tt = TTFont(font_file)
    gs = tt.getGlyphSet()
    order = tt.getGlyphOrder()
    upm = tt["head"].unitsPerEm
    s = size / upm
    pen_x, out = x, []
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        pen = SVGPathPen(gs)
        # font units are y-up; SVG is y-down -> flip
        gs[order[info.codepoint]].draw(TransformPen(pen, (s, 0, 0, -s, pen_x + pos.x_offset * s, y - pos.y_offset * s)))
        out.append(pen.getCommands())
        pen_x += pos.x_advance * s + tracking
    return " ".join(c for c in out if c), pen_x - x - tracking


def text_width(text, font_file, size, tracking=0.0):
    return text_path(text, font_file, size, 0, 0, tracking)[1]


def mark_sun(cx, cy, r):
    """Concept A: rising sun over two waves, all circles/arcs."""
    w = r * 0.22
    return f"""
  <defs><clipPath id="disc"><circle cx="{cx}" cy="{cy}" r="{r}"/></clipPath></defs>
  <g id="mark" clip-path="url(#disc)">
    <circle cx="{cx}" cy="{cy}" r="{r}" fill="{SKY}"/>
    <path d="M {cx - r * 0.62} {cy + r * 0.05} A {r * 0.62} {r * 0.62} 0 0 1 {cx + r * 0.62} {cy + r * 0.05} Z" fill="{SUN}"/>
    <path d="M {cx - r} {cy + r * 0.28} q {r * 0.5} {-w} {r} 0 t {r} 0" fill="none" stroke="{SEA}" stroke-width="{w}" stroke-linecap="round"/>
    <path d="M {cx - r * 0.82} {cy + r * 0.62} q {r * 0.41} {-w * 0.8} {r * 0.82} 0 t {r * 0.82} 0" fill="none" stroke="{INK}" stroke-width="{w * 0.8}" stroke-linecap="round"/>
  </g>"""


def mark_grid(cx, cy, r):
    """Concept B: four quarter-circle tiles forming an S-like rotation, pure geometry."""
    h = r  # tile size
    x0, y0 = cx - h, cy - h
    q = lambda x, y, sweep_from, color: (
        f'<path d="{sweep_from(x, y)}" fill="{color}"/>')
    tiles = [
        # each: square tile with a quarter-circle; corners chosen so the 2x2 grid reads as an "S"
        f'<path d="M {x0} {y0 + h} A {h} {h} 0 0 1 {x0 + h} {y0} L {x0 + h} {y0 + h} Z" fill="{SUN}"/>',
        f'<rect x="{x0 + h}" y="{y0}" width="{h}" height="{h}" rx="{h * 0.08}" fill="{SKY}"/>',
        f'<rect x="{x0}" y="{y0 + h}" width="{h}" height="{h}" rx="{h * 0.08}" fill="{SEA}"/>',
        f'<path d="M {x0 + h} {y0 + h} L {x0 + 2 * h} {y0 + h} A {h} {h} 0 0 1 {x0 + h} {y0 + 2 * h} Z" fill="{INK}"/>',
    ]
    return '\n  <g id="mark">\n    ' + "\n    ".join(tiles) + "\n  </g>"


def lockup(concept, live):
    W, H = 1200, 400
    r = 120
    cx, cy = 200, H / 2
    mark = mark_sun(cx, cy, r) if concept == "A-sun" else mark_grid(cx, cy, r)
    size, tracking = 112, -1.5
    tx, ty = 370, H / 2 + 40
    if live:
        word = (f'<text x="{tx}" y="{ty}" font-family="Manrope" font-weight="700" font-size="{size}" '
                f'letter-spacing="{tracking}" fill="{INK}">{NAME}</text>')
    else:
        d, _ = text_path(NAME, FONT_BOLD, size, tx, ty, tracking)
        word = f'<path id="wordmark" d="{d}" fill="{INK}"/>'
    tag_d, _ = text_path("LIGHT · LOCAL · CLEAN", FONT_MED, 26, tx + 4, ty + 52, 4)
    tag = (f'<text x="{tx + 4}" y="{ty + 52}" font-family="Manrope" font-weight="500" font-size="26" '
           f'letter-spacing="4" fill="{SEA}">LIGHT · LOCAL · CLEAN</text>') if live else f'<path d="{tag_d}" fill="{SEA}"/>'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">\n'
            f'  <title>Solvane (fictional brand) - concept {concept}</title>{mark}\n  {word}\n  {tag}\n</svg>\n')


def style_guide():
    W, H = 1600, 1000
    parts = [f'<rect width="{W}" height="{H}" fill="{PAPER}"/>']
    title, _ = text_path("Solvane — logo style guide (fictional brand, portfolio sample)", FONT_BOLD, 40, 80, 110)
    parts.append(f'<path d="{title}" fill="{INK}"/>')
    sw = [(SUN, "Sun", "255 122 47"), (SKY, "Sky", "255 201 74"), (SEA, "Sea", "20 163 139"), (INK, "Ink", "31 36 48")]
    for i, (hexv, name, rgb) in enumerate(sw):
        x = 80 + i * 360
        parts.append(f'<rect x="{x}" y="180" width="320" height="200" rx="16" fill="{hexv}" stroke="#D0D3DA"/>')
        for j, line in enumerate((name, f"HEX {hexv}", f"RGB {rgb}")):
            d, _ = text_path(line, FONT_BODY if j else FONT_BOLD, 28, x, 430 + j * 40)
            parts.append(f'<path d="{d}" fill="{INK}"/>')
    rows = ["Primary typeface: Manrope Bold (wordmark), Manrope Medium (tagline) — SIL Open Font License",
            "Body / UI: Inter Regular — SIL Open Font License",
            "Clear space: at least the height of the wordmark's x-height on every side",
            "Minimum size: mark 24 px / 8 mm; full lockup 160 px / 40 mm wide",
            "Files: SVG with live text (editable), SVG outlined (no fonts needed), PNG 64–2048 px, JPG 1024 px"]
    for k, line in enumerate(rows):
        d, _ = text_path(line, FONT_BODY, 28, 80, 620 + k * 52)
        parts.append(f'<path d="{d}" fill="{INK}"/>')
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">\n' + "\n".join(parts) + "\n</svg>\n"


def main():
    for d in ("svg", "png", "jpg"):
        os.makedirs(d, exist_ok=True)
    for concept in ("A-sun", "B-tiles"):
        for live in (True, False):
            with open(f"svg/{concept}-{'live' if live else 'outlined'}.svg", "w") as f:
                f.write(lockup(concept, live))
        src = open(f"svg/{concept}-outlined.svg").read()
        for wpx in (64, 256, 512, 1024, 2048):
            cairosvg.svg2png(bytestring=src.encode(), write_to=f"png/{concept}-{wpx}.png", output_width=wpx)
        cairosvg.svg2png(bytestring=src.encode(), write_to="/tmp/_w.png", output_width=1024, background_color="white")
        from PIL import Image
        Image.open("/tmp/_w.png").convert("RGB").save(f"jpg/{concept}-1024.jpg", quality=95)
        # icon-only (mark) for favicons / app icons: square viewBox, no text
        r = 120
        mk = mark_sun(130, 130, r) if concept == "A-sun" else mark_grid(130, 130, r)
        icon = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 260 260" width="260" height="260">\n'
                f'  <title>Solvane (fictional brand) - icon {concept}</title>{mk}\n</svg>\n')
        open(f"svg/{concept}-icon.svg", "w").write(icon)
        for wpx in (32, 64, 512):
            cairosvg.svg2png(bytestring=icon.encode(), write_to=f"png/{concept}-icon-{wpx}.png", output_width=wpx)
    sg = style_guide()
    open("style-guide.svg", "w").write(sg)
    cairosvg.svg2pdf(bytestring=sg.encode(), write_to="style-guide.pdf")
    cairosvg.svg2png(bytestring=sg.encode(), write_to="png/style-guide.png", output_width=1600)
    print("built")


if __name__ == "__main__":
    main()
