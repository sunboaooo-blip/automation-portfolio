# csv-validate

Validate one or more CSV files against written rules. Every issue is reported with its exact location, and the input files are never modified.

```sh
python3 -I csvvalidate.py fixtures/rules.json fixtures/good_and_bad.csv --report issues.csv --md report.md
```

Exit codes: `0` = no issues, `1` = issues found, `2` = rules/IO error (bad JSON, invalid regex, unreadable file, or an output path that points at an input). Existing CI can gate on these.

## Checks

- **Encoding:** bytes valid in the declared encoding (reports the byte offset and line); UTF-8 BOM.
- **Header:** required columns present; duplicate column names.
- **Structure:** field-count mismatch per record; blank records; embedded newlines (with the line span).
- **Content:**
  - required fields empty;
  - regex formats per column;
  - allowed-character sets;
  - control characters;
  - undecodable characters;
  - leading/trailing spaces;
  - non-standard spaces.
- **Duplicates:** single or composite keys, pointing to the first occurrence.

The rules live in a JSON file (see `fixtures/rules.json`), so they can be adjusted without touching code.

## Report columns

`file, record, line, field, rule, value, detail`, where `record` is the logical CSV record and `line` is the physical line it starts on. Values are escaped, so newlines and control characters are visible.

## Tested

| Fixture | Planted problems | Result |
|---|---|---|
| clean.csv | none | 0 issues, exit 0 |
| good_and_bad.csv | bad email/date/amount formats, duplicate id, missing id, multi-line field, disallowed character, padded value, blank line, unquoted `1,000` | 12 issues, exit 1 |
| latin1_ctrl.csv | Latin-1 byte in a UTF-8 file, BEL control character | 3 issues, exit 1 |
| wrong_header.csv | missing required columns | 3 issues, exit 1 |

Further cases:
- Output path = an input, symlink, hard link or the rules file: refused with exit 2, and the input is unchanged.
- Invalid regex in the rules: exit 2 with a clear message.

These cases were run with Ubuntu 22.04.5's own `python3` (3.10.12) inside a rootless Ubuntu 22.04 userland (`ubuntu2204-bwrap.sh`: official ubuntu-base rootfs plus bubblewrap, no Docker or sudo). That is the real distro userland on the host kernel, not a VM or a CI runner. The cases were also run independently on Windows with Python 3.12.

## Not covered

- Cleaning or fixing data; this tool only validates.
- Schema inference.
- Files that do not fit in memory.
