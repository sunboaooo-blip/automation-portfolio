# pdf-to-word

Selectable-text PDF → editable DOCX that keeps the **basic structure**: headings, paragraphs, bullet and numbered lists, bold and italic. It uses Word's built-in Heading and List styles. Exact fonts, pagination and margins are deliberately not copied.

```sh
python make_fixtures.py fixtures
python structdocx.py fixtures/structure.pdf out.docx
python structdocx.py fixtures/table.pdf out.docx --drop-tables   # ruled tables removed with their text, each removal listed
```

| Rule | Behaviour |
|---|---|
| Headings | Lines larger than the body font size become Heading 1/2/3 by size rank. A two-line heading stays one heading. |
| Lists | A bullet glyph becomes `List Bullet`. `1.` / `1)` / `a.` becomes `List Number`. **Each numbered list restarts where the source restarts** (its own Word numbering with a start value). A skipped or repeated source number is reported, never silently renumbered. |
| Paragraphs | Wrapped lines are joined. A wrapped list item continues only while indented; text back at the margin starts a new paragraph. |
| Bold / italic | Taken from each text span's font flags. |
| Ligatures | `ﬁ`, `ﬂ` and similar glyphs become plain letters, so Word search and spellcheck work. Nothing else is changed. |
| `--drop-tables` | Ruled tables found by PyMuPDF are removed **with** their text. Each one is listed (page, position, word count). |

**Self-check.** The DOCX word sequence must equal an independent word list of the PDF (PyMuPDF's word API), minus list markers and minus words inside removed tables. Any mismatch deletes the output (exit 3). A page without a text layer is reported as *not in the DOCX* (exit 1), never silently skipped.

Results on the fixtures (`example-output/`):
- `structure`: Heading 1/2, 3 bullets, 2 numbered items, bold and italic.
- `wrap` (2 pages): two-line heading, wrapped list item, paragraph after a list.
- `restart`: three lists numbered 1–2, 1–2, 5–6.
- `table --drop-tables`: 13 table words removed and listed; all body text kept.

## What it does not do

- It does not convert scanned pages; those need OCR first.
- It does not handle multi-column layouts.
- It does not detect tables without ruling lines; those stay as text.
- It does not detect headings marked only by bold or colour, or numbered headings such as "2.1". Headings come from font size, so the mapping is shown on page 1 for approval.
- It has not been tested in the Microsoft Word application. The output is checked by reopening it with python-docx.

Needs: Python 3.10+, PyMuPDF, python-docx.
