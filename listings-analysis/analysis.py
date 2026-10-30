# %% load every sheet of every workbook
import glob, re, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
frames = [pd.read_excel(f, sheet_name=None) for f in sorted(glob.glob("listings_*.xlsx"))]
df = pd.concat([d for wb in frames for d in wb.values()], ignore_index=True)
raw = len(df)
# %% normalise headers, strings, prices, dates
df.columns = [re.sub(r"[^a-z0-9]+", "_", c.strip().lower()).strip("_") for c in df.columns]
df = df.rename(columns={"neighbourhood_group": "borough"})
for c in ("host_name", "borough", "neighbourhood", "room_type"):
    df[c] = df[c].astype(str).str.strip().str.title()
df["price"] = pd.to_numeric(df["price"].astype(str).str.replace(r"[$,]", "", regex=True), errors="coerce")
df["last_review"] = pd.to_datetime(df["last_review"], errors="coerce")
dups = df.duplicated().sum(); df = df.drop_duplicates()
missing = df[["price", "last_review"]].isna().sum().to_dict()
clean = df.dropna(subset=["price"])  # agreed rule placeholder: rows without price excluded from price averages only
# %% averages
by_borough = clean.groupby("borough")["price"].mean().round(2)
by_room = clean.groupby("room_type")["price"].mean().round(2)
by_month = clean.dropna(subset=["last_review"]).groupby(clean["last_review"].dt.to_period("Q"))["price"].mean().round(2)
df.to_csv("clean.csv", index=False); df.to_excel("clean.xlsx", index=False)
# %% charts + PDF
with PdfPages("summary.pdf") as pdf:
    fig, ax = plt.subplots(figsize=(8.27, 5)); by_borough.plot.bar(ax=ax, title="Average nightly price by borough"); fig.tight_layout(); pdf.savefig(fig); fig.savefig("chart_borough.png")
    fig, ax = plt.subplots(figsize=(8.27, 5)); by_month.plot(ax=ax, marker="o", title="Average price by quarter (last review)"); fig.tight_layout(); pdf.savefig(fig); fig.savefig("chart_time.png")
print(f"rows raw={raw} after_dedup={len(df)} duplicates_removed={dups} missing={missing}")
print(by_borough.to_dict()); print(by_room.to_dict())
