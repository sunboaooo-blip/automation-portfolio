"""Simulate model mistakes on a real fixture and confirm each one lands in Exceptions.
usage: test_tamper.py PDF_DIR_WITH_KP-7795  (uses the local model, then tampers with its answer)"""
import importlib.util, os, sys, tempfile, shutil
import openpyxl
spec = importlib.util.spec_from_file_location("e", os.path.join(os.path.dirname(os.path.abspath(__file__)), "extract_invoices.py"))
e = importlib.util.module_from_spec(spec); spec.loader.exec_module(e)
real = e.ask
CASES = {
    "dropped last line": lambda j: j.update(lines=j["lines"][:-1]),
    "duplicated a line": lambda j: j.update(lines=j["lines"] + [dict(j["lines"][0])]),
    "invented description": lambda j: j["lines"][0].update(description="Premium executive gift set"),
    "wrong supplier": lambda j: j.update(supplier="Some Other Traders"),
}
src = sys.argv[1]
for label, tamper in CASES.items():
    d = tempfile.mkdtemp(); shutil.copy(os.path.join(src, "KP-7795.pdf"), d)
    def fake(api, model, text, t=tamper):
        j = real(api, model, text); t(j); return j
    e.ask = fake
    out = os.path.join(d, "o.xlsx")
    sys.argv = ["x", d, out, "--model", os.environ.get("MODEL", "local")]
    import contextlib, io
    with contextlib.redirect_stdout(io.StringIO()):
        e.main()
    issues = [r[2] for r in openpyxl.load_workbook(out)["Exceptions"].iter_rows(min_row=2, values_only=True)]
    print(f"{label}: {issues}")
