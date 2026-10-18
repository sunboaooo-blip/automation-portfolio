import sys, time, subprocess, numpy as np, imageio_ffmpeg
from faster_whisper import WhisperModel
m = WhisperModel(sys.argv[1], device="cuda", compute_type="float16")
t = time.time()
cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-nostdin", "-i", sys.argv[2], "-f", "f32le", "-ac", "1", "-ar", "16000", "-loglevel", "error", "-"]
audio = np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, np.float32)
segs, info = m.transcribe(audio, language="en", beam_size=5, vad_filter=False)
segs = list(segs)
open(sys.argv[3], "w").write("\n".join(s.text.strip() for s in segs) + "\n")
print(f"{len(segs)} segments, {time.time()-t:.1f}s for {info.duration/60:.1f} min")
