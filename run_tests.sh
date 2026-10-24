#!/bin/sh
# Run every tool on its synthetic fixtures and check results + exit codes. Needs python3 (3.8+).
set -u
cd "$(dirname "$0")"
T=$(mktemp -d)
if command -v uv >/dev/null 2>&1; then
  uv venv -q "$T/venv" && uv pip install -q -p "$T/venv/bin/python" openpyxl pypdf pymupdf pillow
else
  python3 -m venv "$T/venv" && "$T/venv/bin/pip" install -q openpyxl pypdf pymupdf pillow
fi || { echo "setup failed: could not create a venv with openpyxl/pypdf/pymupdf/pillow"; exit 2; }
PY="$T/venv/bin/python"
fail=0
check() {  # name expected_exit actual_exit
  if [ "$2" = "$3" ]; then echo "PASS $1 (exit $3)"; else echo "FAIL $1 (expected $2, got $3)"; fail=1; fi
}
cd csv-validate
for f in clean:0 good_and_bad:1 latin1_ctrl:1 wrong_header:1; do
  python3 -I csvvalidate.py fixtures/rules.json "fixtures/${f%%:*}.csv" --report "$T/r.csv" >/dev/null; check "csv-validate ${f%%:*}" "${f##*:}" $?
done
cp fixtures/clean.csv "$T/in.csv"; python3 -I csvvalidate.py fixtures/rules.json "$T/in.csv" --report "$T/in.csv" 2>/dev/null; check "csv-validate refuses to overwrite input" 2 $?
cd ../csv-dedup
python3 -I csvdedup.py fixtures/sample.csv "$T/d.csv" "$T/d-log.csv" >/dev/null; check "csv-dedup full row" 0 $?
[ "$(($(python3 -c "import sys;print(sum(1 for _ in open(sys.argv[1],newline='')))" "$T/d-log.csv") ))" -ge 4 ] && cmp -s "$T/d.csv" example-output/full.csv; check "csv-dedup output matches expected bytes" 0 $?
python3 -I csvdedup.py fixtures/sample.csv fixtures/sample.csv "$T/x.csv" 2>/dev/null; check "csv-dedup refuses to overwrite input" 2 $?
python3 -I csvdedup.py fixtures/literal_quote.csv "$T/q.csv" "$T/q-log.csv" >/dev/null && [ "$(wc -l < "$T/q.csv")" -eq 3 ]; check "csv-dedup literal quote in unquoted field: duplicate removed" 0 $?
python3 -I fuzz_split.py 3 3000 >/dev/null; check "csv-dedup split agrees with csv parser (3,000 random texts)" 0 $?
cd ../txt-to-xlsx
for f in sample:0 order_matters:0 countercases:0 numeric_equal:0; do
  "$PY" -I txt2xlsx.py "fixtures/${f%%:*}.txt" "$T/o.xlsx" --placeholder N/A --normalize-ws --null-markers NULL >/dev/null; check "txt-to-xlsx ${f%%:*}" "${f##*:}" $?
done
"$PY" -I txt2xlsx.py fixtures/order_matters.txt "$T/o.xlsx" --placeholder N/A --normalize-ws --null-markers NULL --order dedup-then-fill >/dev/null; check "txt-to-xlsx dedup-then-fill flags post-fill duplicate" 1 $?
cd ../pdf-sheet-picker
for e in pymupdf pypdf; do
  "$PY" -I sheetpick.py fixtures/set12.pdf "$T/s-$e" --engine $e >/dev/null; check "sheet-picker set12 [$e]" 0 $?
  "$PY" -I sheetpick.py fixtures/ambiguous.pdf "$T/a-$e" --engine $e >/dev/null; check "sheet-picker ambiguous held [$e]" 1 $?
done
"$PY" -I sheetpick.py fixtures/rotated.pdf "$T/r" --engine pymupdf >/dev/null; check "sheet-picker rotated [pymupdf]" 0 $?
[ "$(cat "$T/r/sheets.txt" | tr '\n' ' ')" = "E2.01 E2.02 T2.01 " ]; check "sheet-picker rotated picks E2.01 E2.02 T2.01" 0 $?
cd ../pdf-image-extractor
"$PY" make_test_pdf.py "$T/cat.pdf" >/dev/null && "$PY" extract.py "$T/x" "$T/cat.pdf" >/dev/null; check "pdf-image-extractor runs" 0 $?
[ "$(ls "$T/x/images" | wc -l)" -eq 8 ] && [ "$(($(wc -l < "$T/x/manifest.csv") - 1))" -eq 13 ]; check "pdf-image-extractor 13 placements -> 8 unique" 0 $?
rm -rf "$T"
[ $fail = 0 ] && echo "ALL PASS" || echo "SOME FAILED"
exit $fail
