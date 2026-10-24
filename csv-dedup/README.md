# csv-dedup

Remove duplicate records from a CSV and keep **everything else byte-for-byte**, with a traceable log of every removal.

```sh
python csvdedup.py in.csv out.csv removed-log.csv                         # full-row duplicates, keep first
python csvdedup.py in.csv out.csv removed-log.csv --key id --keep last    # duplicates by key column(s)
```

## What "byte-for-byte" means here

- Records are split with full CSV quoting rules: quoted commas, doubled quotes `""`, and **line breaks inside quoted fields**.
- Kept records are copied as their **original bytes**. Quoting, spacing, CRLF/LF line endings and a UTF-8 BOM are not rewritten. The output is the input with the duplicate records cut out.
- Comparison is **exact on parsed values**. `1,"Asha Rao",…` and `1,Asha Rao,…` are the same record, while `Chen` vs `chen` and `Chen` vs `Chen ` are **not**. Looser matching (trim, case) must be agreed first and is never a default.
- Blank records are kept by default. With `--blank drop`, only the first blank record is kept.

## Built-in self-check

After writing, the output is re-read. The run **fails (exit 3) and the output is deleted** if any of these is not true:
- the header is unchanged;
- kept + removed = input records;
- no duplicates remain;
- every kept record is byte-identical to its input slice.

## The log

`removed_record, removed_line, kept_record, kept_line, compared_values`. Each removal points to the record it duplicates, by record number and physical line, so any row can be checked in the source.

## Tested (`RUNLOG.txt`, fixture `fixtures/sample.csv`)

The fixture has a BOM, CRLF line endings, quoted commas, doubled quotes, an embedded line break, case/space near-duplicates and blank rows.

| run | result |
|---|---|
| full row, keep first | 11 records in → 8 kept, 3 removed (two quoting variants of one record and a duplicate containing a line break); near-duplicates kept; BOM and CRLF preserved |
| `--key id --keep last` | 6 kept, 5 removed; every removal points to the **later** record it was kept in favour of |
| `--blank drop` | one blank record removed as well |
| guards | output = input → exit 2; unknown key column → exit 2; non-UTF-8 input → exit 2 ("agree the encoding first"); missing output folder → exit 2 |

Standard library only (Python 3.8+). Other encodings and delimiters are agreed per job (`--delimiter` exists; encodings other than UTF-8 are refused rather than guessed).
