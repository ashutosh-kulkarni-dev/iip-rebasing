"""Stage 0 (optional): rebuild data/clean/tidy_long.csv for the 1993-94, 2004-05 and
2011-12 bases from the original eSankhyiki/MoSPI Excel exports.

The exports are not redistributed (see data/raw/README.md); tidy_long.csv is committed, so
the pipeline runs from build_data.py without them.

Place the three source files in data/raw/ named exactly:
    1993-94.xlsx   2004-05.xlsx   2011-12.xlsx
Each must be a long-format monthly table with columns:
    year, month, type, category, sub_category, index, growth_rate
Run from the repository root:  python pipeline/load_clean.py
"""
import pandas as pd, os

SRC = "data/raw/"
OUT = "data/clean/"
files = {'1993-94': '1993-94.xlsx', '2004-05': '2004-05.xlsx', '2011-12': '2011-12.xlsx'}
MONTH = {'January':1,'February':2,'March':3,'April':4,'May':5,'June':6,
         'July':7,'August':8,'September':9,'October':10,'November':11,'December':12}
# 4 common use-based categories across all base years
USE4 = ['Capital Goods','Intermediate Goods','Consumer Durables','Consumer Non-durables']
SECT = ['Mining','Manufacturing','Electricity']

def load(by):
    df = pd.read_excel(SRC + files[by])
    df['m'] = df['month'].map(MONTH)
    df['date'] = pd.to_datetime(dict(year=df['year'], month=df['m'], day=1))
    df['index'] = pd.to_numeric(df['index'], errors='coerce')
    df['growth_rate'] = pd.to_numeric(df['growth_rate'], errors='coerce')
    return df

os.makedirs(OUT, exist_ok=True)
all_long = []
for by in files:
    df = load(by)
    # General
    gen = df[(df['type']=='General')][['date','index','growth_rate']].copy()
    gen['series'] = 'General'; gen['family'] = 'General'
    # Use-based (top-level category, sub_category null)
    ub = df[(df['type']=='Use-based category') & (df['category'].isin(USE4)) & (df['sub_category'].isna())][['date','category','index','growth_rate']].copy()
    ub = ub.rename(columns={'category':'series'}); ub['family'] = 'Use-based'
    # Sectoral top-level (sub_category null = the aggregate Mining/Mfg/Elec)
    sec = df[(df['type']=='Sectoral') & (df['category'].isin(SECT)) & (df['sub_category'].isna())][['date','category','index','growth_rate']].copy()
    sec = sec.rename(columns={'category':'series'}); sec['family'] = 'Sectoral'
    part = pd.concat([gen,ub,sec], ignore_index=True)
    part['base_year'] = by
    all_long.append(part)

L = pd.concat(all_long, ignore_index=True).sort_values(['base_year','family','series','date'])
L.to_csv(OUT+'tidy_long.csv', index=False)

print(f"Saved {OUT}tidy_long.csv")
