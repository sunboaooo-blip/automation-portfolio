#!/bin/sh
# Run every tool on its synthetic fixtures and check results + exit codes. Needs python3 (3.8+).
set -u
cd "$(dirname "$0")"
T=$(mktemp -d)
if command -v uv >/dev/null 2>&1; then
  uv venv -q "$T/venv" && uv pip install -q -p "$T/venv/bin/python" openpyxl pypdf "pymupdf==1.28.2" pillow python-docx
else
  python3 -m venv "$T/venv" && "$T/venv/bin/pip" install -q openpyxl pypdf "pymupdf==1.28.2" pillow python-docx
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
cd ../list-compare
"$PY" -I listdiff.py fixtures/list_a.csv fixtures/list_b.csv "$T/lc.xlsx" --col "Full Name" --col-b Name --norm nfkc | grep -q "A: 9 rows = 3 matched + 5 missing from B + 1 blank"; check "list-compare nfkc counts" 0 $?
"$PY" -I listdiff.py fixtures/list_a.csv fixtures/list_b.csv "$T/lc.xlsx" --col Nope 2>/dev/null; check "list-compare unknown column refused" 2 $?
"$PY" -c "import csv,sys; a=next(csv.reader(open('fixtures/schema_a.csv'))); b=next(csv.reader(open('fixtures/schema_b.csv'))); sys.exit(0 if a!=b else 1)" && "$PY" -I listdiff.py fixtures/schema_a.csv fixtures/schema_b.csv "$T/ls.xlsx" --col "$("$PY" -c "import csv;print(next(csv.reader(open('fixtures/schema_a.csv')))[0])")" --col-b "$("$PY" -c "import csv;print(next(csv.reader(open('fixtures/schema_b.csv')))[0])")" >/dev/null && "$PY" -c "
import csv,openpyxl,sys; wb=openpyxl.load_workbook(sys.argv[1]); hb=next(csv.reader(open('fixtures/schema_b.csv')))
sys.exit(0 if [c.value for c in wb['Blank names B'][1]][2:]==hb else 1)" "$T/ls.xlsx"; check "list-compare blank names keep each list's own headers" 0 $?
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
cd ../pdf-to-word
"$PY" make_fixtures.py "$T/w" >/dev/null && "$PY" -I structdocx.py "$T/w/structure.pdf" "$T/s.docx" >/dev/null; check "pdf-to-word structure self-check" 0 $?
"$PY" -c "
import docx,sys,collections; c=collections.Counter(p.style.name for p in docx.Document(sys.argv[1]).paragraphs if p.text.strip())
sys.exit(0 if c['Heading 1']==1 and c['Heading 2']==2 and c['List Bullet']==3 and c['List Number']==2 else 1)" "$T/s.docx"; check "pdf-to-word headings and lists mapped" 0 $?
"$PY" -I structdocx.py "$T/w/restart.pdf" "$T/r.docx" 2>/dev/null | grep -q "1...2.', '1...2.', '5...6."; check "pdf-to-word numbered lists restart like the source" 0 $?
"$PY" -I structdocx.py "$T/w/table.pdf" "$T/t.docx" --drop-tables 2>&1 | grep -q "TABLE REMOVED: .*page 1"; check "pdf-to-word ruled table removed and listed" 0 $?
"$PY" -c "import docx,sys; t=' '.join(p.text for p in docx.Document(sys.argv[1]).paragraphs); sys.exit(0 if 'Cleaning' not in t and 'Call us to book a visit.' in t else 1)" "$T/t.docx"; check "pdf-to-word table text gone, body kept" 0 $?
cd ../pdf-to-a4
"$PY" make_book.py "$T/book.pdf" && "$PY" -I scale_a4.py "$T/book.pdf" "$T/a4.pdf" >/dev/null; check "pdf-to-a4 159 pages self-check" 0 $?
"$PY" -c "
import pymupdf,sys; a,b=pymupdf.open(sys.argv[1]),pymupdf.open(sys.argv[2])
ok=len(a)==len(b)==159 and all(abs(p.rect.width-595)<1 and abs(p.rect.height-842)<1 for p in b) and all(f'page {i+1}' in b[i].get_text() for i in range(159))
ia=a.extract_image(a[0].get_images()[0][0])['image']; ib=b.extract_image(b[0].get_images(full=True)[0][0])['image']
sys.exit(0 if ok and ia==ib else 1)" "$T/book.pdf" "$T/a4.pdf"; check "pdf-to-a4 all A4, order kept, image bytes identical" 0 $?
rm -rf "$T"
[ $fail = 0 ] && echo "ALL PASS" || echo "SOME FAILED"
exit $fail
