#!/usr/bin/env python3
"""Batch product background removal at original resolution, with 100% edge QA sheets.

usage: bgremove.py IN_DIR OUT_DIR [--margin 0.06] [--model PATH] [--infer 2048]

For every JPEG/PNG in IN_DIR (names kept):
  OUT_DIR/png/<name>.png      transparent cutout, ORIGINAL pixel size, original colours untouched (RGB copied, alpha added)
  OUT_DIR/white/<name>.jpg    product on pure white, ORIGINAL canvas size and aspect ratio, product centred
                              (scaled down only if it would break the margin; never upscaled)
  OUT_DIR/framed/<name>.jpg   same aspect ratio as the original, cropped so the product fills the frame to the
                              same margin on every image; product pixels are NOT resampled (output may be smaller)
  OUT_DIR/qa/<name>-edges.jpg 100% (1:1 pixel) crops of the product edge, on white and on dark, for inspection
  OUT_DIR/report.csv          size, mask coverage, soft-edge share, time per image
Nothing leaves the machine: the segmentation model runs on the local GPU.
"""
import argparse
import csv
import os
import time

import numpy as np
import torch
from PIL import Image
from torchvision import transforms
from transformers import AutoModelForImageSegmentation

EXT = (".jpg", ".jpeg", ".png")


def load_model(path):
    m = AutoModelForImageSegmentation.from_pretrained(path, trust_remote_code=True).eval().to("cuda").half()
    return m


def predict(model, img, side):
    t = transforms.Compose([transforms.Resize((side, side)), transforms.ToTensor(),
                            transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])])
    with torch.no_grad():
        p = model(t(img).unsqueeze(0).to("cuda").half())[-1].sigmoid().float().cpu()[0, 0]
    # upsample the probability map (not a hard mask) to full size, so edges stay smooth at 100%
    p = torch.nn.functional.interpolate(p[None, None], size=(img.height, img.width), mode="bilinear",
                                        align_corners=False)[0, 0].clamp(0, 1).numpy()
    return Image.fromarray((p * 255).round().astype(np.uint8), "L")


def on_white(cut, size, margin):
    W, H = size
    box = cut.getbbox()
    obj = cut.crop(box)
    avail_w, avail_h = W * (1 - 2 * margin), H * (1 - 2 * margin)
    k = min(avail_w / obj.width, avail_h / obj.height, 1.0)  # never upscale
    if k < 1.0:
        obj = obj.resize((round(obj.width * k), round(obj.height * k)), Image.LANCZOS)
    canvas = Image.new("RGB", (W, H), (255, 255, 255))
    canvas.paste(obj, ((W - obj.width) // 2, (H - obj.height) // 2), obj)
    return canvas, k


def framed(cut, size, margin):
    """Crop a box of the original aspect ratio around the product so the product's longer relative side
    touches the margin; pixels are copied 1:1, the white fill extends past the photo edge if needed."""
    W, H = size
    x0, y0, x1, y1 = cut.getbbox()
    ow, oh = x1 - x0, y1 - y0
    scale = max(ow / (W * (1 - 2 * margin)), oh / (H * (1 - 2 * margin)))
    fw, fh = round(W * scale), round(H * scale)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    canvas = Image.new("RGB", (fw, fh), (255, 255, 255))
    canvas.paste(cut, (round(fw / 2 - cx), round(fh / 2 - cy)), cut)
    return canvas


def edge_sheet(cut, n=4, crop=320):
    """n 1:1 crops centred on points along the mask boundary, each shown on white and on dark grey."""
    a = np.array(cut.getchannel("A"))
    edge = np.argwhere((a > 20) & (a < 235))
    if len(edge) == 0:
        edge = np.argwhere(a > 127)
    picks = edge[np.linspace(0, len(edge) - 1, n).astype(int)]
    sheet = Image.new("RGB", (crop * n, crop * 2), (255, 255, 255))
    for i, (y, x) in enumerate(picks):
        x0 = int(min(max(x - crop // 2, 0), cut.width - crop)); y0 = int(min(max(y - crop // 2, 0), cut.height - crop))
        c = cut.crop((x0, y0, x0 + crop, y0 + crop))
        for row, bg in enumerate(((255, 255, 255), (40, 40, 40))):
            tile = Image.new("RGB", c.size, bg); tile.paste(c, (0, 0), c)
            sheet.paste(tile, (i * crop, row * crop))
    return sheet


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inp"); ap.add_argument("out")
    ap.add_argument("--margin", type=float, default=0.06)
    ap.add_argument("--model", default=os.environ.get("BIREFNET", "ZhengPeng7/BiRefNet"))
    ap.add_argument("--infer", type=int, default=2048, help="model input side; 1024 or 2048")
    a = ap.parse_args()
    for sub in ("png", "white", "framed", "qa"):
        os.makedirs(os.path.join(a.out, sub), exist_ok=True)
    t0 = time.time(); model = load_model(a.model); load_s = time.time() - t0
    rows = []
    for name in sorted(f for f in os.listdir(a.inp) if f.lower().endswith(EXT)):
        t = time.time()
        src = Image.open(os.path.join(a.inp, name))
        rgb = src.convert("RGB")
        alpha = predict(model, rgb, a.infer)
        cut = rgb.copy(); cut.putalpha(alpha)
        stem = os.path.splitext(name)[0]
        cut.save(os.path.join(a.out, "png", stem + ".png"), optimize=True)
        white, k = on_white(cut, rgb.size, a.margin)
        white.save(os.path.join(a.out, "white", stem + ".jpg"), quality=95, subsampling=0)
        fr = framed(cut, rgb.size, a.margin)
        fr.save(os.path.join(a.out, "framed", stem + ".jpg"), quality=95, subsampling=0)
        edge_sheet(cut).save(os.path.join(a.out, "qa", stem + "-edges.jpg"), quality=92)
        al = np.array(alpha)
        rows.append({"file": name, "size": f"{rgb.width}x{rgb.height}", "coverage_%": f"{(al > 127).mean() * 100:.1f}",
                     "soft_edge_%": f"{((al > 20) & (al < 235)).mean() * 100:.2f}", "white_scale": f"{k:.3f}", "framed_size": f"{fr.width}x{fr.height}",
                     "seconds": f"{time.time() - t:.2f}"})
        print(rows[-1])
    with open(os.path.join(a.out, "report.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print(f"model load {load_s:.1f}s; {len(rows)} images; total {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
