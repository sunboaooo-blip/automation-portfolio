# txt-to-xlsx

Turn a plain-text data export into a clean Excel file. It removes exact duplicate rows, fills every missing value with one placeholder, guarantees there are no empty cells in the data range, and adds a log sheet so the job can be repeated on new data.

```sh
pip install openpyxl
python -I txt2xlsx.py fixtures/sample.txt out.xlsx --placeholder "N/A" --normalize-ws --null-markers NULL
```

## Behaviour

- **Delimiter:** detected from field-count consistency (`,` `;` tab `|`), or forced with `--delimiter`. BOM handled.
- **Ragged rows:** padded to full width, and the padded cells count as missing. Fully empty rows are dropped.
- **Missing values:** with `--normalize-ws`, whitespace-only cells count as missing; `--null-markers NULL,NA` treats those markers as missing too.
- **Exact text by default:** every cell is stored as its exact source text.
  - Leading-zero codes stay `01234`.
  - Formula-looking text like `=1+1` is stored as literal text, never as a formula.
  - `--numeric-cols amount` stores the listed columns as numbers. In that case `1`, `1.0` and `1.00` are equal, as they are in Excel, and any rows merged because of this are counted in the log.
- **Order:** the default is `fill-then-dedup`, because filling blanks can make two rows identical. Only this order passes a "no blanks and no duplicates" check. `--order dedup-then-fill` is available, and it reports the rows that became identical after filling.
- **Self-check:** the written file is re-opened and the tool reports formula cells, empty cells and duplicate rows. The exit code is 0 only when all three are 0.
- **Safety:** an output path equal to the input (including a symlink or hard link) is refused with exit 2.

## Tested

4 fixtures × 2 orders × 2 type modes, plus the hard-link case:
- 14 runs exit 0.
- The 2 runs that exit 1 do so on purpose: `order_matters.txt` with dedup-then-fill leaves 1 row duplicated after filling.
- The hard-link output exits 2.

The suite was also run independently on Windows with Python 3.12 and openpyxl 3.1.5.

## Not covered

- Excel's own `COUNTBLANK` was not run, because no Excel was available. The self-check counts None/"" cells in the same range, which is what COUNTBLANK counts on a values-only sheet.
- Power Query and VBA versions.
