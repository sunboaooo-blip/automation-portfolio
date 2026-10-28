"""Score OUT xlsx against truth json: every cell, wrong, wrong-and-not-yellow."""
import json, sys
from openpyxl import load_workbook
truth, outdir = json.load(open(sys.argv[1])), sys.argv[2]
tot = wrong = unflagged = yel = 0
for f, pages in truth.items():
    wb = load_workbook(f"{outdir}/{f[:-4]}.xlsx")
    for p, tabs in pages.items():
        got, cur = [], None
        for r in wb[f"Page {p}"].iter_rows():
            if r[0].value and str(r[0].value).startswith("Table "): cur = []; got.append(cur); continue
            if cur is not None and any(c.value is not None for c in r): cur.append(r)
        for k, T in enumerate(tabs):
            G = got[k] if k < len(got) else []
            for i, tr in enumerate(T):
                for j, tv in enumerate(tr):
                    tot += 1
                    c = G[i][j] if i < len(G) and j < len(G[i]) else None
                    y = c is not None and c.fill.fgColor.rgb in ("00FFFF00", "FFFFFF00"); yel += y
                    if c is None or (c.value or "") != tv:
                        wrong += 1; unflagged += not y
print(f"truth cells {tot}: written wrong {wrong}, wrong AND not yellow {unflagged}, yellow {yel}")
