"""Transcribe any audio/video file to TXT + SRT + VTT with Whisper large-v3 (local GPU).

usage: CUDA_VISIBLE_DEVICES=1 transcribe.py MEDIA [MEDIA ...] [--lang en|zh|ja|auto] [--out DIR] [--translate]
"""
import argparse
import subprocess
from pathlib import Path

import imageio_ffmpeg
import numpy as np
import torch
from transformers import pipeline

ROOT = Path(__file__).parent
SR = 16000


def load_media(path):
    """Decode any container/codec ffmpeg understands to 16 kHz mono float32."""
    cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-nostdin", "-i", str(path), "-f", "f32le",
           "-ac", "1", "-ar", str(SR), "-loglevel", "error", "-"]
    return np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, np.float32)


def ts(t, sep):
    t = max(t or 0.0, 0.0)
    h, rem = divmod(int(t * 1000), 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("media", nargs="+")
    ap.add_argument("--lang", default="auto")
    ap.add_argument("--out", default="out")
    ap.add_argument("--translate", action="store_true", help="output English translation instead")
    ap.add_argument("--model", default="whisper-large-v3", help="folder under models/")
    a = ap.parse_args()
    asr = pipeline("automatic-speech-recognition", model=str(ROOT / "models" / a.model),
                   torch_dtype=torch.float16, device="cuda:0")  # sequential long-form: chunked batching dropped text
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for m in map(Path, a.media):
        audio = load_media(m)
        # no conditioning on previous text: avoids long-form drift into lowercase/no punctuation
        gk = {"task": "translate" if a.translate else "transcribe", "condition_on_prev_tokens": False,
              "temperature": (0.0, 0.2, 0.4, 0.6, 0.8, 1.0), "compression_ratio_threshold": 1.35,
              "logprob_threshold": -1.0, "no_speech_threshold": 0.6}
        if a.lang != "auto":
            gk["language"] = a.lang
        res = asr({"raw": audio, "sampling_rate": SR}, return_timestamps=True, generate_kwargs=gk)
        chunks = [c for c in res["chunks"] if c["text"].strip()]
        dur = len(audio) / SR
        for i, c in enumerate(chunks):  # last chunk may lack an end time
            if c["timestamp"][1] is None:
                c["timestamp"] = (c["timestamp"][0], chunks[i + 1]["timestamp"][0] if i + 1 < len(chunks) else dur)
        (out / f"{m.stem}.txt").write_text("\n".join(c["text"].strip() for c in chunks) + "\n", encoding="utf-8")
        srt = [f"{i}\n{ts(c['timestamp'][0], ',')} --> {ts(c['timestamp'][1], ',')}\n{c['text'].strip()}\n"
               for i, c in enumerate(chunks, 1)]
        (out / f"{m.stem}.srt").write_text("\n".join(srt), encoding="utf-8")
        vtt = ["WEBVTT\n"] + [f"{ts(c['timestamp'][0], '.')} --> {ts(c['timestamp'][1], '.')}\n{c['text'].strip()}\n"
                              for c in chunks]
        (out / f"{m.stem}.vtt").write_text("\n".join(vtt), encoding="utf-8")
        print(f"{m.name}: {dur / 60:.1f} min audio, {len(chunks)} segments -> {out}/{m.stem}.(txt|srt|vtt)")


if __name__ == "__main__":
    main()
