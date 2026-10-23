"""Price/spec product cards from one cutout + one facts file. Text is typeset, never AI-drawn.

usage: cards.py facts.json cutout.png OUTDIR [--size 1080x1080]
Every visible fact (name, specs, MRP, offer price) comes from facts.json; the discount is computed.
Writes 5 colour/layout variants as JPEG plus check.txt listing the exact text on each card.
"""
import json
import os
import sys
from decimal import ROUND_HALF_UP, Decimal

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "..", "invoice-generator", "assets")  # Inter + Manrope, SIL OFL
BOLD, REG = os.path.join(FONTS, "Manrope-Bold.ttf"), os.path.join(FONTS, "Inter-Regular.ttf")

THEMES = [  # (background top, background bottom, accent, ink, badge ink, layout)
    ("#0F766E", "#14B8A6", "#FACC15", "#FFFFFF", "#111827", "right"),
    ("#FFF7ED", "#FED7AA", "#EA580C", "#1F2937", "#FFFFFF", "left"),
    ("#1E1B4B", "#6D28D9", "#F472B6", "#FFFFFF", "#FFFFFF", "right"),
    ("#ECFDF5", "#A7F3D0", "#047857", "#064E3B", "#FFFFFF", "center"),
    ("#111827", "#374151", "#22D3EE", "#F9FAFB", "#111827", "left"),
]


def rgb(h):
    h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def gradient(w, h, top, bottom):
    a, b = rgb(top), rgb(bottom)
    g = Image.new("RGB", (1, h))
    for y in range(h):
        t = y / (h - 1); g.putpixel((0, y), tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3)))
    return g.resize((w, h))


def font(path, px):
    return ImageFont.truetype(path, px)


def fit(draw, text, path, px, max_w):
    """Largest size <= px whose text fits max_w; text is never cut or squeezed."""
    while px > 12 and draw.textlength(text, font=font(path, px)) > max_w:
        px -= 2
    return font(path, px)


def money(x, sym):
    return f"{sym}{Decimal(str(x)):,.0f}" if Decimal(str(x)) == Decimal(str(x)).to_integral() else f"{sym}{Decimal(str(x)):,.2f}"


def card(facts, cut, size, theme, out):
    W, H = size
    top, bottom, accent, ink, badge_ink, layout = theme
    im = gradient(W, H, top, bottom).convert("RGBA")
    d = ImageDraw.Draw(im)
    s = W / 1080
    # product: scaled to 78% of height, never upscaled beyond the source pixels
    ph = min(int(H * 0.78), cut.height); pw = int(cut.width * ph / cut.height)
    prod = cut.resize((pw, ph), Image.LANCZOS)
    px = {"right": int(W * 0.70 - pw / 2), "left": int(W * 0.28 - pw / 2), "center": int(W * 0.5 - pw / 2)}[layout]
    py = int(H * 0.5 - ph / 2) if layout != "center" else int(H * 0.40 - ph * 0.5)
    if layout == "center":
        ph2 = int(H * 0.40); pw2 = int(cut.width * ph2 / cut.height); prod = cut.resize((pw2, ph2), Image.LANCZOS)
        pw, ph = pw2, ph2; px = int(W * 0.5 - pw / 2); py = int(H * 0.05)
    shadow = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).ellipse([px + pw * 0.05, py + ph - 18 * s, px + pw * 0.95, py + ph + 22 * s], fill=(0, 0, 0, 90))
    im = Image.alpha_composite(im, shadow.filter(ImageFilter.GaussianBlur(14 * s)))
    im.alpha_composite(prod, (px, py))
    d = ImageDraw.Draw(im)
    sym = facts["currency_symbol"]
    mrp, offer = Decimal(str(facts["mrp"])), Decimal(str(facts["offer_price"]))
    pct = ((mrp - offer) / mrp * 100).quantize(Decimal("1"), ROUND_HALF_UP)
    # text column
    if layout == "center":
        x0, colw, y = int(W * 0.08), int(W * 0.84), int(H * 0.49)
    else:
        x0 = int(W * 0.06) if layout == "right" else int(W * 0.52)
        colw, y = int(W * 0.42), int(H * 0.10)
    f = fit(d, facts["name"], BOLD, int(64 * s), colw)
    d.text((x0, y), facts["name"], font=f, fill=ink); y += int(f.size * 1.25)
    if facts.get("tagline"):
        ft = fit(d, facts["tagline"], REG, int(30 * s), colw)
        d.text((x0, y), facts["tagline"], font=ft, fill=ink); y += int(ft.size * 1.8)
    fs = font(REG, int(28 * s))
    specs = facts["specs"] if layout != "center" else facts["specs"][:2]
    for sp in specs:
        d.ellipse([x0, y + fs.size * 0.35, x0 + fs.size * 0.4, y + fs.size * 0.75], fill=accent)
        fsp = fit(d, sp, REG, fs.size, colw - int(fs.size * 0.8))
        d.text((x0 + int(fs.size * 0.8), y), sp, font=fsp, fill=ink); y += int(fs.size * 1.55)
    y += int(18 * s)
    # prices: MRP struck through, offer large, discount badge
    fm = font(REG, int(32 * s)); mtxt = f"MRP {money(mrp, sym)}"
    d.text((x0, y), mtxt, font=fm, fill=ink)
    tw = d.textlength(mtxt, font=fm); mid = y + fm.size * 0.62
    d.line([x0, mid, x0 + tw, mid], fill=ink, width=max(2, int(3 * s)))
    y += int(fm.size * 1.4)
    fo = font(BOLD, int(92 * s)); otxt = money(offer, sym)
    d.text((x0, y), otxt, font=fo, fill=accent if layout != "left" or theme[0] != "#FFF7ED" else accent)
    ow = d.textlength(otxt, font=fo)
    fb = font(BOLD, int(30 * s)); btxt = f"{pct}% OFF"
    bw, bh = d.textlength(btxt, font=fb) + 36 * s, fb.size + 22 * s
    bx, by = x0 + ow + 24 * s, y + fo.size * 0.35
    if bx + bw > x0 + colw + (W * 0.3 if layout == "center" else 0):
        bx, by = x0, y + fo.size * 1.25
    d.rounded_rectangle([bx, by, bx + bw, by + bh], radius=int(bh / 2), fill=accent)
    d.text((bx + 18 * s, by + 9 * s), btxt, font=fb, fill=badge_ink)
    if facts.get("footer"):
        ff = font(REG, int(22 * s)); d.text((int(W * 0.06), int(H - 48 * s)), facts["footer"], font=ff, fill=ink)
    im.convert("RGB").save(out, "JPEG", quality=92, optimize=True, progressive=True)
    return [facts["name"], facts.get("tagline", ""), *specs, mtxt, otxt, btxt, facts.get("footer", "")]


def main():
    facts = json.load(open(sys.argv[1], encoding="utf-8"))
    cut = Image.open(sys.argv[2]).convert("RGBA")
    out = sys.argv[3]; os.makedirs(out, exist_ok=True)
    size = (1080, 1080)
    if "--size" in sys.argv:
        size = tuple(int(v) for v in sys.argv[sys.argv.index("--size") + 1].split("x"))
    if max(size) > 2000:
        sys.exit("longest edge is capped at 2000 px")
    lines = []
    for i, th in enumerate(THEMES, 1):
        p = os.path.join(out, f"card-{i}.jpg")
        txt = card(facts, cut, size, th, p)
        lines.append(f"{os.path.basename(p)}: " + " | ".join(t for t in txt if t))
    open(os.path.join(out, "check.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
