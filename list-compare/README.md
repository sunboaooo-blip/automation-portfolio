# list-compare

Compare **two contact lists on one name column** and report who is missing from which list. The result is one Excel workbook with the full original rows.

```sh
python listdiff.py list_a.csv list_b.xlsx result.xlsx --col "Full Name" --col-b "Name" --norm space
```

| sheet | contents |
|---|---|
| **Missing from B** | every row of A whose name does not occur in B (all original columns, plus the source row number) |
| **Missing from A** | the same in the other direction |
| **Blank names** | rows with an empty name. They are never matched, and listed instead of dropped |
| **Repeated names** | names that occur more than once in a list. They are **not merged**: every row is reported |
| **Note** | inputs, key columns, row counts and the normalisation level used |

## Name matching is explicit, never silent

`--norm` is chosen and stated before work. The levels are cumulative:

| level | rule |
|---|---|
| `exact` | identical text |
| `space` | + trim the ends and collapse repeated spaces (`"  Ben   Lee "` = `"Ben Lee"`) |
| `case` | + case-insensitive (`"asha rao"` = `"Asha Rao"`) |
| `nfkc` | + Unicode NFKC (full-width `Ｄｅｖ` = `Dev`) |

**Accents are never removed** (`José Álvarez` ≠ `Jose Alvarez`). Looser matching, such as dropping accents or middle names, or nicknames, would be a separate, agreed rule.

## Checks

- For each list, matched + missing + blank = total rows. Otherwise the run exits 3 and no output is kept.
- Text that looks like a formula (`=…`) is stored as literal text.
- Values are written exactly as read, so leading zeros in phone numbers stay.
- An unknown column name exits 2 and prints the header.

## Tested (`RUNLOG.txt`, `fixtures/`)

The fixture is a 9-row list A against a 6-row list B. They include spacing and case variants, a full-width name, an accented/unaccented pair, a blank name in each list, a repeated name and a formula-looking name. Each stricter level matches fewer names:

| level | A matched / missing / blank | B matched / missing / blank |
|---|---|---|
| exact | 0 / 8 / 1 | 0 / 5 / 1 |
| space | 1 / 7 / 1 | 1 / 4 / 1 |
| case | 2 / 6 / 1 | 2 / 3 / 1 |
| nfkc | 3 / 5 / 1 | 3 / 2 / 1 |

The repeated `Chen Wei` is reported on both of its rows, and the accented pair stays unmatched on purpose.

CSV needs only the standard library; XLSX input and output need `openpyxl`. Inputs must be UTF-8 (CSV) or .xlsx; anything else is refused rather than guessed.
