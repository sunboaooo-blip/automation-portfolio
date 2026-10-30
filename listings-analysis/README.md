# listings-analysis

Several messy Excel workbooks with several sheets each are merged, cleaned and summarised with pandas. The output is a cleaned CSV/XLSX, charts and a short PDF report. A script and a notebook version are both included.

```sh
pip install -r requirements.txt
python make_data.py      # writes listings_1..3.xlsx (2 sheets each, 24,240 rows)
python analysis.py       # clean.csv, clean.xlsx, chart_borough.png, chart_time.png, summary.pdf
jupyter nbconvert --to notebook --execute analysis.ipynb --output executed.ipynb   # same steps as a notebook
```

**The data is synthetic.** `make_data.py` generates random listings in the column layout of the public NYC short-term-rental listings datasets, with deliberate mess added:
- inconsistent headers (`"Host Name "`, `room type`, `last review`);
- untrimmed, upper-case and lower-case names;
- prices as text with `$` and thousands separators, and some blank;
- missing dates;
- 40 duplicated rows per sheet.

No real listing, host or company data is included. Because the values are random, the averages are all close to each other. This example demonstrates the cleaning and reporting pipeline; it does not produce market insight.

## Steps (`analysis.py`)

1. Read every sheet of every workbook and stack them (24,240 rows).
2. Normalise headers to snake_case. Trim and title-case the text columns. Parse prices (`"$1,250"` → 1250) and dates. Unparsable values become blank and are counted, never guessed.
3. Remove exact duplicate rows: 253 removed, leaving 23,987.
4. Report missing values (712 prices, 298 dates). Rows without a price are left out of the price averages only; they stay in the cleaned file.
5. Compute averages by borough and by room type, plus a quarterly trend that uses only rows that have a date.
6. Write `clean.csv` / `clean.xlsx`, two PNG charts and a 2-page PDF (`example-output/`).

The run is reproducible: the random seed is fixed, and a rerun gives exactly the numbers above.

## What it does not do

- It does not merge near-duplicates (for example the same listing with a slightly different price). Only exact duplicate rows are removed; any looser rule must be agreed first.
- It does not fill missing values.
- It does not model or forecast; the output is descriptive statistics only.

Needs: Python 3.10+, pandas, openpyxl, matplotlib (versions pinned in `requirements.txt`). It is not part of `run_tests.sh` because it needs the heavier pandas stack.
