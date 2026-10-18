"""Whisper large-v3 quality/speed check: LibriSpeech (en, WER) and FLEURS dev (zh/ja, CER).

usage: CUDA_VISIBLE_DEVICES=1 eval.py N_PER_LANG
"""
import csv
import io
import re
import sys
import time
import unicodedata
from pathlib import Path

import jiwer
import pandas as pd
import soundfile as sf
import torch
from transformers import pipeline

N = int(sys.argv[1]) if len(sys.argv) > 1 else 30
ROOT = Path(__file__).parent
asr = pipeline("automatic-speech-recognition", model=str(ROOT / "models/whisper-large-v3"),
               torch_dtype=torch.float16, device="cuda:0")


def norm(s, cjk):
    s = unicodedata.normalize("NFKC", s).lower()
    s = re.sub(r"[^\w\s]", "", s)
    return re.sub(r"\s+", "" if cjk else " ", s).strip()


def run(name, items, lang, cjk):
    refs, hyps, audio_s, t0 = [], [], 0.0, time.time()
    for k, (wav, sr, ref) in enumerate(items):
        audio_s += len(wav) / sr
        out = asr({"raw": wav, "sampling_rate": sr}, generate_kwargs={"language": lang, "task": "transcribe"})
        refs.append(norm(ref, cjk))
        hyps.append(norm(out["text"], cjk))
        PER_CLIP.append({"set": name, "clip": k, "audio_s": round(len(wav) / sr, 2), "reference": ref,
                         "hypothesis": out["text"].strip(),
                         "clip_error_pct": round(100 * (jiwer.cer if cjk else jiwer.wer)(refs[-1], hyps[-1]), 2)})
    wall = time.time() - t0
    err = jiwer.cer(refs, hyps) if cjk else jiwer.wer(refs, hyps)
    return {"set": name, "clips": len(items), "audio_min": round(audio_s / 60, 1),
            "metric": "CER" if cjk else "WER", "error_pct": round(100 * err, 2),
            "wall_s": round(wall, 1), "x_realtime": round(audio_s / wall, 1),
            "example_ref": refs[0][:80], "example_hyp": hyps[0][:80]}


rows = []
PER_CLIP = []
df = pd.read_parquet(ROOT / "data/librispeech_dummy/clean/validation-00000-of-00001.parquet").head(N)
items = []
for _, r in df.iterrows():
    wav, sr = sf.read(io.BytesIO(r["audio"]["bytes"]))
    items.append((wav, sr, r["text"]))
rows.append(run("librispeech-clean (en)", items, "en", False))

for code, lang in (("cmn_hans_cn", "zh"), ("ja_jp", "ja")):
    tsv = pd.read_csv(ROOT / f"data/fleurs/data/{code}/dev.tsv", sep="\t", header=None, quoting=csv.QUOTE_NONE)
    tsv = tsv.drop_duplicates(subset=0).head(N)  # one recording per sentence
    items = []
    for _, r in tsv.iterrows():
        path = next((ROOT / f"data/fleurs/{code}").rglob(r[1]))
        wav, sr = sf.read(path)
        items.append((wav, sr, r[2]))
    rows.append(run(f"fleurs-dev ({lang})", items, lang, True))

out = pd.DataFrame(rows)
print(out.to_string(index=False))
out.to_csv(ROOT / "eval-results.csv", index=False)
pd.DataFrame(PER_CLIP).to_csv(ROOT / "eval-per-clip.csv", index=False)
print("peak VRAM GiB", round(torch.cuda.max_memory_allocated() / 2**30, 2))
