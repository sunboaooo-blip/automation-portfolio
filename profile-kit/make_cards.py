"""Render 1200x900 showcase cards for the profile portfolio from the repo's own synthetic fixtures/results.

Every number on a card comes from a file in this repo (fixtures, run logs or READMEs). No client data.
"""
import csv
import os
import subprocess
import sys
import tempfile

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
INK, ACCENT, MUTED, BG = "#1F2430", "#14A38B", "#6B7280", "#FFFFFF"


def card(title, subtitle, table=None, col_labels=None, bullets=(), out="card.png", col_widths=None,
         footer="synthetic test data only", bullets_y=0.31):
    fig = plt.figure(figsize=(12, 9), dpi=100, facecolor=BG)
    fig.text(0.05, 0.92, title, fontsize=30, weight="bold", color=INK)
    fig.text(0.05, 0.875, subtitle, fontsize=16, color=ACCENT)
    y = 0.80
    if table:
        ax = fig.add_axes([0.05, 0.36, 0.90, 0.42]); ax.axis("off")
        t = ax.table(cellText=table, colLabels=col_labels, loc="upper left", cellLoc="left",
                     colLoc="left", colWidths=col_widths)
        t.auto_set_font_size(False); t.set_fontsize(12); t.scale(1, 1.6)
        for (r, c), cell in t.get_celld().items():
            cell.set_edgecolor("#E5E7EB")
            if r == 0:
                cell.set_text_props(weight="bold", color=BG); cell.set_facecolor(INK)
        y = bullets_y
    for b in bullets:
        fig.text(0.06, y, "•  " + b, fontsize=15, color=INK, wrap=True)
        y -= 0.055
    fig.text(0.05, 0.03, "github.com/sunboaooo-blip/automation-portfolio  ·  " + footer, fontsize=11,
             color=MUTED)
    fig.savefig(os.path.join(HERE, out), facecolor=BG); plt.close(fig)
    print("wrote", out)


def csv_validate():
    with tempfile.TemporaryDirectory() as d:
        rep = os.path.join(d, "r.csv")
        subprocess.run([sys.executable, "-I", os.path.join(REPO, "csv-validate/csvvalidate.py"),
                        os.path.join(REPO, "csv-validate/fixtures/rules.json"),
                        os.path.join(REPO, "csv-validate/fixtures/good_and_bad.csv"), "--report", rep],
                       capture_output=True)
        rows = list(csv.DictReader(open(rep, encoding="utf-8")))[:8]
    table = [[r["record"], r["line"], r["field"] or "-", r["rule"], r["value"][:22]] for r in rows]
    card("CSV validation with exact locations", "Every problem reported by record, line and field — inputs never modified",
         table, ["record", "line", "field", "rule", "value"],
         ["12 planted problems found in the sample file, exit code 1 for CI",
          "Encoding, duplicates, formats, embedded newlines, control characters",
          "Runs on plain Python 3.8+ (tested on Ubuntu 22.04's Python 3.10)"],
         "01-csv-validate.png", [0.1, 0.08, 0.12, 0.28, 0.42])


def txt_to_xlsx():
    raw = open(os.path.join(REPO, "txt-to-xlsx/fixtures/sample.txt"), encoding="utf-8").read().splitlines()[:7]
    table = [[l[:44]] for l in raw]
    card("Messy text export → clean Excel", "Duplicates removed, every blank filled, codes like 01234 kept as text",
         table, ["source rows (excerpt, ';'-separated, gaps and duplicates)"],
         ["Output re-checked automatically: 0 empty cells, 0 duplicate rows, 0 formulas",
          "Order matters: blanks are filled before de-duplication so both checks pass",
          "A Log sheet records every step so the job can be rerun on new data"],
         "02-txt-to-xlsx.png", [1.0])


def sheet_picker():
    table = [["Synthetic 12-sheet set", "6/6 E/T sheets", "mixed numbering styles"],
             ["Rotated pages (0/90/180/270)", "3/3 E/T sheets", "rotation-aware title-block read"],
             ["Heavy set, 40 sheets, 29 MB", "14/14 in 2.7 s", "20k vectors per sheet"],
             ["Real 74-page project set*", "12/12 in 2.9 s", "8 unnumbered pages held for review"]]
    card("Pick electrical sheets from drawing sets", "Reads each title block, keeps original order, never guesses",
         table, ["test", "result", "note"],
         ["Ambiguous or unnumbered pages are listed for review instead of guessed",
          "Exports a PDF of the selected sheets plus CSV/TXT sheet lists",
          "*client sample, results only; the file itself is not published"],
         "03-pdf-sheet-picker.png", [0.36, 0.22, 0.42],
         footer="synthetic fixtures + one client sample (results only, file not published)", bullets_y=0.52)


def image_extractor():
    table = [["13 placements → 8 unique files", "cross-checked with poppler pdfimages"],
             ["JPEG copied byte-for-byte", "others saved as lossless PNG"],
             ["Same photo, different encoding", "detected as a repeat (pixel hash)"],
             ["Inline images, JPEG 2000, transparency", "all extracted at native size"]]
    card("Extract every image from PDFs", "Native resolution, de-duplicated, with a CSV manifest of where each appears",
         table, ["what was tested", "result"],
         ["Manifest: PDF, page, header/body/footer, same-row text, size, colour space",
          "Vector artwork is flagged rather than silently skipped"],
         "04-pdf-image-extractor.png", [0.5, 0.5], bullets_y=0.52)


def transcription():
    table = [["LibriSpeech, English", "3.8 min", "WER 3.6 %", "~11× realtime"],
             ["FLEURS, Japanese", "6.7 min", "CER 4.1 %", "~11×"],
             ["FLEURS, Chinese", "6.2 min", "CER 10.3 %", "~10×"],
             ["Audiobook chapter, English", "27.8 min", "WER 2.0 %", "20 s total"]]
    card("Audio & video → text and subtitles", "Local Whisper on GPU: TXT, SRT and VTT with timestamps",
         table, ["public test set", "audio", "error rate", "speed"],
         ["Punctuation pass that provably never changes a single word",
          "Files stay on our own hardware — nothing uploaded to cloud services",
          "Speaker labels and translation are not offered yet"],
         "05-transcription.png", [0.38, 0.14, 0.2, 0.28],
         footer="public test sets (LibriSpeech, FLEURS, LibriVox)", bullets_y=0.52)


if __name__ == "__main__":
    csv_validate(); txt_to_xlsx(); sheet_picker(); image_extractor(); transcription()
