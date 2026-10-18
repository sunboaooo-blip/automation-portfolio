#!/usr/bin/env python3
"""Validate CSV files against written rules; report every issue with its location. Never modifies input.

Python 3.8+ standard library only (Ubuntu 22.04 ships 3.10).

usage: csvvalidate.py RULES.json FILE.csv [FILE.csv ...] [--report issues.csv] [--md report.md]
exit:  0 = no issues, 1 = issues found, 2 = usage/rules/IO error   (CI can gate on this)

RULES.json example:
{
  "encoding": "utf-8", "delimiter": ",", "quotechar": "\\"",
  "required_columns": ["id", "email", "date"],
  "required_fields": ["id", "email"],
  "unique_keys": [["id"]],
  "formats": {"email": "^[^@\\\\s]+@[^@\\\\s]+\\\\.[^@\\\\s]+$", "date": "^\\\\d{4}-\\\\d{2}-\\\\d{2}$"},
  "allowed_chars": {"id": "^[A-Za-z0-9-]*$"},
  "forbid_embedded_newlines": true,
  "forbid_control_chars": true,
  "trim_check": true
}
"""
import argparse
import csv
import json
import os
import re
import sys
import unicodedata

CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


class Report:
    def __init__(self):
        self.rows = []

    def add(self, file, record, line, field, rule, value, detail=""):
        v = value if len(value) <= 80 else value[:77] + "..."
        self.rows.append({"file": file, "record": record, "line": line, "field": field,
                          "rule": rule, "value": v.encode("unicode_escape").decode("ascii"), "detail": detail})


def check_encoding(path, enc, rep):
    raw = open(path, "rb").read()
    if raw.startswith(b"\xef\xbb\xbf"):
        rep.add(path, "", 1, "", "bom", "", "file starts with a UTF-8 BOM")
    try:
        raw.decode(enc)
        return True
    except UnicodeDecodeError as e:
        line = raw[:e.start].count(b"\n") + 1
        rep.add(path, "", line, "", "encoding", raw[e.start:e.start + 8].hex(),
                f"not valid {enc} at byte {e.start}")
        return False


def validate(path, rules, rep):
    enc = rules.get("encoding", "utf-8")
    ok_enc = check_encoding(path, enc, rep)
    seen = {tuple(k): {} for k in rules.get("unique_keys", [])}
    with open(path, newline="", encoding=enc, errors="replace" if not ok_enc else "strict") as f:
        reader = csv.reader(f, delimiter=rules.get("delimiter", ","), quotechar=rules.get("quotechar", '"'),
                            strict=False)
        try:
            header = next(reader)
        except StopIteration:
            rep.add(path, "", 1, "", "empty_file", "", "no header row")
            return
        header = [h.lstrip("﻿") for h in header]
        for i, h in enumerate(header):
            if header.count(h) > 1 and header.index(h) == i:
                rep.add(path, 0, 1, h, "duplicate_column", h, f"appears {header.count(h)} times")
        for col in rules.get("required_columns", []):
            if col not in header:
                rep.add(path, 0, 1, col, "missing_column", "", "required column absent from header")
        formats = {k: re.compile(v) for k, v in rules.get("formats", {}).items()}
        allowed = {k: re.compile(v) for k, v in rules.get("allowed_chars", {}).items()}
        record = 0
        prev_line = reader.line_num
        for row in reader:
            record += 1
            start_line = prev_line + 1  # physical line where this logical record begins
            prev_line = reader.line_num
            if not any(c.strip() for c in row):
                rep.add(path, record, start_line, "", "blank_record", "", "")
                continue
            if len(row) != len(header):
                rep.add(path, record, start_line, "", "field_count", str(len(row)),
                        f"expected {len(header)} fields")
            rec = dict(zip(header, row))
            for col in rules.get("required_fields", []):
                if col in header and not rec.get(col, "").strip():
                    rep.add(path, record, start_line, col, "required_missing", rec.get(col, ""))
            for col, val in rec.items():
                if rules.get("forbid_embedded_newlines") and ("\n" in val or "\r" in val):
                    rep.add(path, record, start_line, col, "embedded_newline", val,
                            f"record spans lines {start_line}-{reader.line_num}")
                if rules.get("forbid_control_chars") and CONTROL.search(val):
                    rep.add(path, record, start_line, col, "control_char", val)
                if "�" in val:
                    rep.add(path, record, start_line, col, "undecodable_char", val)
                if rules.get("trim_check") and val != val.strip():
                    rep.add(path, record, start_line, col, "leading_trailing_space", val)
                if any(unicodedata.category(c) == "Zs" and c != " " for c in val):
                    rep.add(path, record, start_line, col, "nonstandard_space", val)
                if val.strip() and col in formats and not formats[col].search(val):
                    rep.add(path, record, start_line, col, "format", val, f"does not match {formats[col].pattern}")
                if col in allowed and not allowed[col].search(val):
                    rep.add(path, record, start_line, col, "allowed_chars", val)
            for key in seen:
                if all(k in header for k in key):
                    kv = tuple(rec.get(k, "").strip() for k in key)
                    if all(kv):
                        if kv in seen[key]:
                            rep.add(path, record, start_line, "+".join(key), "duplicate_key", "|".join(kv),
                                    f"first seen at record {seen[key][kv]}")
                        else:
                            seen[key][kv] = record


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("rules")
    ap.add_argument("files", nargs="+")
    ap.add_argument("--report", default="issues.csv")
    ap.add_argument("--md")
    a = ap.parse_args()
    # never write over an input: compare real paths and inode identity of every output vs every input
    inputs = [a.rules] + a.files
    for out in filter(None, [a.report, a.md]):
        for src in inputs:
            same = os.path.realpath(out) == os.path.realpath(src)
            try:
                same = same or os.path.samefile(out, src)
            except OSError:
                pass  # output does not exist yet
            if same:
                print(f"refusing to write report to input file: {out}", file=sys.stderr)
                return 2
    try:
        rules = json.load(open(a.rules, encoding="utf-8"))
        for key in ("formats", "allowed_chars"):
            for col, pat in rules.get(key, {}).items():
                try:
                    re.compile(pat)
                except re.error as e:
                    raise ValueError(f"{key}.{col}: invalid regex {pat!r}: {e}")
    except (OSError, ValueError) as e:
        print(f"rules error: {e}", file=sys.stderr)
        return 2
    rep = Report()
    for p in a.files:
        try:
            validate(p, rules, rep)
        except OSError as e:
            print(f"cannot read {p}: {e}", file=sys.stderr)
            return 2
    fields = ["file", "record", "line", "field", "rule", "value", "detail"]
    with open(a.report, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rep.rows)
    counts = {}
    for r in rep.rows:
        counts[r["rule"]] = counts.get(r["rule"], 0) + 1
    if a.md:
        with open(a.md, "w", encoding="utf-8") as f:
            f.write(f"# CSV validation report\n\nFiles: {', '.join(a.files)}\n\nIssues: {len(rep.rows)}\n\n")
            f.write("| rule | count |\n|---|---|\n" + "".join(f"| {k} | {v} |\n" for k, v in sorted(counts.items())))
            f.write("\n| " + " | ".join(fields) + " |\n|" + "---|" * len(fields) + "\n")
            f.writelines("| " + " | ".join(str(r[k]).replace("|", "\\|") for k in fields) + " |\n" for r in rep.rows)
    print(f"{len(rep.rows)} issue(s) in {len(a.files)} file(s): " +
          ", ".join(f"{k}={v}" for k, v in sorted(counts.items())) if rep.rows else "OK: no issues")
    return 1 if rep.rows else 0


if __name__ == "__main__":
    sys.exit(main())
