"""WER of a long transcript vs the Gutenberg text: align on the reference span that starts at the story opening."""
import re, sys, jiwer
def norm(s): return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9' ]", " ", s.lower().replace("’", "'"))).split()
ref = open(sys.argv[1], encoding="utf-8").read()
ref = ref[ref.index("To Sherlock Holmes she is always"):]
hyp = open(sys.argv[2], encoding="utf-8").read()
hyp = " ".join(norm(hyp)); hyp = hyp[hyp.index("to sherlock holmes she is always"):]
h = norm(hyp); r = norm(ref)
# trim LibriVox outro and choose reference length that minimises WER
best = min((jiwer.wer(" ".join(r[:n]), " ".join(h[:-12] if len(h) > 50 else h)), n) for n in range(len(h) - 300, len(h) + 300, 10))
print(f"{sys.argv[2]}: hyp words {len(h)}, best ref words {best[1]}, WER {100*best[0]:.2f}%")
