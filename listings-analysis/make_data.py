import numpy as np, pandas as pd
rng = np.random.default_rng(1)
boroughs = {"Manhattan": ["Harlem", "Chelsea"], "Brooklyn": ["Williamsburg", "Bushwick"], "Queens": ["Astoria"], "Bronx": ["Fordham"], "Staten Island": ["St. George"]}
for w in range(3):
    with pd.ExcelWriter(f"listings_{w+1}.xlsx") as xw:
        for s in range(2):
            n = 4000
            b = rng.choice(list(boroughs), n)
            df = pd.DataFrame({"Host Name ": rng.choice(["  Anna", "BOB", "carl "], n), "neighbourhood_group": b,
                               "Neighbourhood": [rng.choice(boroughs[x]) for x in b],
                               "room type": rng.choice(["Entire home/apt", "Private room", "Shared room"], n),
                               "Price": [f"${p:,.0f}" if rng.random() > .03 else "" for p in rng.gamma(2, 80, n)],
                               "last review": pd.to_datetime("2019-01-01") + pd.to_timedelta(rng.integers(0, 1500, n), "D")})
            df.loc[rng.choice(n, 50), "last review"] = pd.NaT
            df = pd.concat([df, df.sample(40, random_state=s)])  # duplicates
            df.to_excel(xw, sheet_name=f"sheet{s+1}", index=False)
