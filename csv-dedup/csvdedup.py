#!/usr/bin/env python3
"""Remove duplicate records from a CSV and keep everything else byte-for-byte.

usage: csvdedup.py IN.csv OUT.csv LOG.csv [--key COL[,COL...]] [--keep first|last] [--blank keep|drop]

- Records are split with full CSV quoting rules (quoted commas, quotes and line breaks inside fields).
- Kept records are copied as their ORIGINAL bytes: quoting, spacing, line endings and encoding are not rewritten.
- Duplicate = identical parsed values in every column (default) or in the --key columns. Comparison is exact:
  no trimming, no case folding. Anything looser must be agreed and is not a default.
- --keep first (default) keeps the earliest record of each group; --keep last keeps the latest.
- Blank records (all fields empty) are kept by default and never count as duplicates of each other;
  with --blank drop they are compared like any other record, so only the first blank record is kept.
- LOG.csv: removed record no., its first physical line, the kept record it duplicates, and the compared values.
- After writing, OUT is re-read and checked: header unchanged, kept + removed = input records, no duplicates
  left, and every kept record byte-identical to its input slice. Any failure exits 3 and OUT is deleted.
Exit codes: 0 ok, 2 usage/input error, 3 self-check failed.
"""
import argparse
import csv
import io
import os
import sys


def split_records(text):
    """Yield (raw_record_text, first_line_no). Line breaks inside quotes stay inside the record."""
    start, line, rec_line, inq, i, n = 0, 1, 1, False, 0, len(text)
    while i < n:
        c = text[i]
        if c == '"':
            inq = not inq
        elif not inq and c in "\r\n":
            end = i + (2 if c == "\r" and i + 1 < n and text[i + 1] == "\n" else 1)
            yield text[start:end], rec_line
            line += 1
            start, i, rec_line = end, end, line
            continue
        elif c == "\n":
            line += 1
        i += 1
    if start < n:
        yield text[start:], rec_line


def fields(raw, dialect):
    rows = list(csv.reader(io.StringIO(raw, newline=""), dialect))
    return rows[0] if rows else []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inp"); ap.add_argument("out"); ap.add_argument("log")
    ap.add_argument("--key"); ap.add_argument("--keep", choices=("first", "last"), default="first")
    ap.add_argument("--blank", choices=("keep", "drop"), default="keep")
    ap.add_argument("--delimiter", default=",")
    a = ap.parse_args()
    if not os.path.isfile(a.inp):
        print(f"no such input file: {a.inp}", file=sys.stderr); sys.exit(2)
    for p in (a.out, a.log):
        if not os.path.isdir(os.path.dirname(os.path.abspath(p))):
            print(f"output folder does not exist: {os.path.dirname(p)}", file=sys.stderr); sys.exit(2)
    real = [os.path.realpath(p) for p in (a.inp, a.out, a.log)]
    linked = any(os.path.exists(p) and os.path.samefile(p, a.inp) for p in (a.out, a.log))
    if len(set(real)) < 3 or linked:
        print("input, output and log must be three different files (hard links included)", file=sys.stderr); sys.exit(2)
    raw = open(a.inp, "rb").read()
    bom = raw.startswith(b"\xef\xbb\xbf")
    try:
        text = raw[3:].decode("utf-8") if bom else raw.decode("utf-8")
    except UnicodeDecodeError as e:
        print(f"input is not UTF-8 ({e}); agree the encoding first", file=sys.stderr); sys.exit(2)
    dialect = csv.excel; dialect.delimiter = a.delimiter
    recs = list(split_records(text))
    if not recs:
        print("empty input", file=sys.stderr); sys.exit(2)
    header = fields(recs[0][0], dialect)
    if a.key:
        cols = [c.strip() for c in a.key.split(",")]
        missing = [c for c in cols if c not in header]
        if missing:
            print(f"key column(s) not in header: {missing}", file=sys.stderr); sys.exit(2)
        idx = [header.index(c) for c in cols]
    else:
        idx = None
    body = recs[1:]
    order = range(len(body)) if a.keep == "first" else range(len(body) - 1, -1, -1)
    seen, removed, keep = {}, [], [True] * len(body)
    for k in order:
        r, line = body[k]
        f = fields(r, dialect)
        if not any(x != "" for x in f) and a.blank == "keep":
            continue
        key = tuple(f[i] if i < len(f) else None for i in idx) if idx else tuple(f)
        if key in seen:
            keep[k] = False
            removed.append((k + 2, line, seen[key] + 2, body[seen[key]][1], " | ".join("" if v is None else v for v in key)))
        else:
            seen[key] = k
    out_text = recs[0][0] + "".join(r for (r, _), kp in zip(body, keep) if kp)
    with open(a.out, "wb") as fh:
        fh.write((b"\xef\xbb\xbf" if bom else b"") + out_text.encode("utf-8"))
    removed.sort()
    with open(a.log, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["removed_record", "removed_line", "kept_record", "kept_line", "compared_values"])
        w.writerows(removed)
    # self-check on the written file
    chk = open(a.out, "rb").read()
    chk_text = chk[3:].decode("utf-8") if bom else chk.decode("utf-8")
    out_recs = list(split_records(chk_text))
    kept_raw = [r for (r, _), kp in zip(body, keep) if kp]
    problems = []
    if out_recs[0][0] != recs[0][0]:
        problems.append("header changed")
    if len(out_recs) - 1 + len(removed) != len(body):
        problems.append(f"count: {len(out_recs) - 1} kept + {len(removed)} removed != {len(body)} input records")
    if [r for r, _ in out_recs[1:]] != kept_raw:
        problems.append("a kept record is not byte-identical to its input")
    keys = [tuple(fields(r, dialect)[i] if i < len(fields(r, dialect)) else None for i in idx) if idx else tuple(fields(r, dialect))
            for r, _ in out_recs[1:] if any(x != "" for x in fields(r, dialect)) or a.blank == "drop"]
    if len(keys) != len(set(keys)):
        problems.append("duplicates remain")
    if problems:
        os.remove(a.out); print("SELF-CHECK FAILED: " + "; ".join(problems), file=sys.stderr); sys.exit(3)
    print(f"{len(body)} records in, {len(body) - len(removed)} kept, {len(removed)} removed "
          f"({'key ' + a.key if a.key else 'full row'}, keep {a.keep}); self-check passed")


if __name__ == "__main__":
    main()
