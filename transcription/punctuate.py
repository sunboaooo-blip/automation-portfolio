"""Restore punctuation/casing in a Whisper transcript with a local LLM, never changing the words.

usage: punctuate.py IN.txt OUT.txt [--url http://127.0.0.1:8095] [--words 120]
Each chunk is accepted only if its normalised word sequence is identical to the input chunk;
otherwise the original chunk is kept and counted as a fallback.
"""
import argparse
import difflib
import json
import re
import urllib.request

PROMPT = ("Add correct punctuation, capitalization and paragraph breaks to this speech transcript. "
          "Do not add, remove, reorder or change any word, number or spelling. Output only the text.\n\n")


def words(s):
    return re.sub(r"[^\w\s'-]", " ", s.lower().replace("’", "'")).split()


def transfer(orig, fixed):
    """Keep the original words; copy casing/punctuation from the LLM output wherever words align 1:1."""
    o_toks, f_toks = orig.split(), fixed.split()
    key = lambda t: re.sub(r"[^\w'-]", "", t.lower().replace("’", "'"))
    sm = difflib.SequenceMatcher(a=[key(t) for t in o_toks], b=[key(t) for t in f_toks], autojunk=False)
    out = list(o_toks)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            out[i1:i2] = f_toks[j1:j2]
    return " ".join(out)


def ask(url, text):
    body = json.dumps({"messages": [{"role": "user", "content": PROMPT + text}],
                       "temperature": 0, "max_tokens": 1024,
                       "chat_template_kwargs": {"enable_thinking": False}}).encode()
    req = urllib.request.Request(url + "/v1/chat/completions", body, {"Content-Type": "application/json"})
    out = json.load(urllib.request.urlopen(req, timeout=300))["choices"][0]["message"]["content"]
    return re.sub(r"<think>.*?</think>", "", out, flags=re.S).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--url", default="http://127.0.0.1:8095")
    ap.add_argument("--words", type=int, default=120)
    a = ap.parse_args()
    toks = open(a.src, encoding="utf-8").read().split()
    chunks = [" ".join(toks[i:i + a.words]) for i in range(0, len(toks), a.words)]
    out, fallback = [], 0
    for i, c in enumerate(chunks):
        fixed = ask(a.url, c)
        if words(fixed) == words(c):
            out.append(fixed)
        else:  # model edited words: keep every original word, borrow punctuation where aligned
            merged = transfer(c, fixed)
            assert words(merged) == words(c), f"chunk {i}: transfer changed words"
            out.append(merged)
            fallback += 1
            print(f"chunk {i}: word change by model, punctuation transferred onto original words", flush=True)
    open(a.dst, "w", encoding="utf-8").write(" ".join(out) + "\n")
    print(f"{len(chunks)} chunks, {len(chunks) - fallback} punctuated, {fallback} via alignment transfer; words identical to input: {words(" ".join(out)) == words(" ".join(chunks))}")


if __name__ == "__main__":
    main()
