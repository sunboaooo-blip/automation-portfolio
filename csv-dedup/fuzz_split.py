"""Property test: on random CSV-ish text, split_records + per-record parse must equal Python's csv parser
over the whole text, or the tool must refuse (exit 3). Prints counts; any silent disagreement is a failure."""
import csv, importlib.util, io, os, random, sys
spec = importlib.util.spec_from_file_location("d", os.path.join(os.path.dirname(os.path.abspath(__file__)), "csvdedup.py"))
d = importlib.util.module_from_spec(spec); spec.loader.exec_module(d)
rnd = random.Random(int(sys.argv[1]) if len(sys.argv) > 1 else 1)
alphabet = ['a', 'b', ',', '"', '\n', '\r\n', '\r', ' ', 'x', '""']
agree = refuse = silent = 0
for _ in range(int(sys.argv[2]) if len(sys.argv) > 2 else 20000):
    text = "".join(rnd.choice(alphabet) for _ in range(rnd.randint(0, 30)))
    recs = list(d.split_records(text))
    try:
        bad = d.reconcile(text, recs, csv.excel)
    except d.SplitError:
        bad = "split error"
    except csv.Error:
        bad = "csv error"
    if bad:
        refuse += 1
    else:
        agree += 1
        # extra: the raw slices must concatenate back to the exact text
        if "".join(r for r, _ in recs) != text:
            silent += 1
print(f"random docs: {agree} split agrees with csv parser, {refuse} refused (fail closed), {silent} silent mismatches")
sys.exit(1 if silent else 0)
