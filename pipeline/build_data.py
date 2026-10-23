"""Stage 1: assemble the monthly dataset for all four bases and the official tables.

Inputs (data/raw/, see data/raw/README.md for provenance):
  data/clean/tidy_long.csv                     1993-94, 2004-05, 2011-12 bases (from load_clean.py)
  esankhyiki_2022-23_iip_166.xlsx, _iip_6.xlsx  2022-23 base, eSankhyiki (two exports, combined)
  esankhyiki_2011-12_iip_68.xlsx               2011-12 base incl. the 23 manufacturing industries
  mospi_iip_2022-23_first_release_2026-06-01.html  the 1 June 2026 first release

Outputs:
  data/clean/iip_monthly.csv          long table: date, base_year, series, index, growth_rate
                                      (the analysis dataset; 2022-23 = eSankhyiki version)
  data/clean/iip_2022-23_june2026.csv the same series as printed in the 1 June 2026 release
  data/clean/industry_monthly.csv     23 NIC 2-digit manufacturing industries, 2011-12 and 2022-23
  data/official/mospi2026_pair3_annual_growth.csv   official annual growth, both bases
  data/official/industry_weights_2011-12_2022-23.csv  Table B.2 industry weights
"""
import re
import numpy as np
import pandas as pd
from config import RAW, CLEAN, OFFICIAL, SERIES, MONTHS

PR_HTML = RAW / 'mospi_iip_2022-23_first_release_2026-06-01.html'


def read_esank(path):
    d = pd.read_excel(path)
    d['date'] = pd.to_datetime(dict(year=d['year'], month=d['month'].map(MONTHS), day=1))
    for c in ['index', 'growth_rate']:
        d[c] = pd.to_numeric(d[c], errors='coerce')
    return d


# --- 2022-23, eSankhyiki: the two exports overlap and must agree exactly ----------------
a = read_esank(RAW / 'esankhyiki_2022-23_iip_166.xlsx')
b = read_esank(RAW / 'esankhyiki_2022-23_iip_6.xlsx')
key = ['date', 'type', 'category', 'sub_category']
both = a.merge(b, on=key, suffixes=('_a', '_b'))
assert (both['index_a'] - both['index_b']).abs().max() == 0, 'eSankhyiki exports disagree'
assert (both['growth_rate_a'] - both['growth_rate_b']).abs().max() == 0
e22 = pd.concat([a, b]).drop_duplicates(subset=key).sort_values(key)
months = pd.date_range(e22['date'].min(), e22['date'].max(), freq='MS')
assert set(months) == set(e22['date']), 'gap in the combined 2022-23 months'

NAME_22 = {('General', 'General', None): 'General',
           ('Sectoral', 'Mining & Quarrying', None): 'Mining',
           ('Sectoral', 'Manufacturing', None): 'Manufacturing',
           ('Sectoral', 'Electricity & Gas Supply', 'Electricity'): 'Electricity',
           ('Sectoral', 'Electricity & Gas Supply', None): 'Electricity & Gas Supply',
           ('Sectoral', 'Water Supply, Sewerage & Waste Management', None):
               'Water Supply, Sewerage & Waste Management'}


def pick(d, base, mapping, use_cats):
    out = []
    for (t, c, s), name in mapping.items():
        m = (d['type'] == t) & (d['category'] == c)
        m &= d['sub_category'].isna() if s is None else (d['sub_category'] == s)
        x = d.loc[m, ['date', 'index', 'growth_rate']].copy()
        x['series'] = name
        out.append(x)
    u = d[(d['type'] == 'Use-based category') & d['sub_category'].isna()
          & d['category'].isin(use_cats)][['date', 'category', 'index', 'growth_rate']]
    out.append(u.rename(columns={'category': 'series'}))
    r = pd.concat(out)
    r['base_year'] = base
    return r


USE6 = ['Primary Goods', 'Capital Goods', 'Intermediate Goods',
        'Infrastructure/ Construction Goods', 'Consumer Durables', 'Consumer Non-durables']
s22 = pick(e22, '2022-23', NAME_22, USE6)
s22['source'] = 'eSankhyiki'

# --- 2011-12 extra series (Primary, Infrastructure) from eSankhyiki iip_68 -------------
e11 = read_esank(RAW / 'esankhyiki_2011-12_iip_68.xlsx')
s11x = pick(e11, '2011-12', {}, ['Primary Goods', 'Infrastructure/ Construction Goods'])
s11x['source'] = 'eSankhyiki'

# --- older bases from the v5 cleaned file ----------------------------------------------
old = pd.read_csv(CLEAN / 'tidy_long.csv', parse_dates=['date'])
old = old[['date', 'index', 'growth_rate', 'series', 'base_year']].copy()
old['source'] = 'v5 cleaned file (eSankhyiki/MoSPI)'

# Cross-check: iip_68 must reproduce the v5 2011-12 file wherever both exist.
chk = old[old['base_year'] == '2011-12'].merge(
    pick(e11, '2011-12', {('General', 'General', None): 'General',
                          ('Sectoral', 'Mining', None): 'Mining',
                          ('Sectoral', 'Manufacturing', None): 'Manufacturing',
                          ('Sectoral', 'Electricity', None): 'Electricity'}, USE6),
    on=['date', 'series'], suffixes=('', '_68'))
assert len(chk) > 1000 and (chk['index'] - chk['index_68']).abs().max() == 0, '2011-12 sources disagree'

M = pd.concat([old, s11x, s22], ignore_index=True)
M = M.sort_values(['base_year', 'series', 'date']).reset_index(drop=True)
M.to_csv(CLEAN / 'iip_monthly.csv', index=False)

# --- industries (23 NIC 2-digit), 2011-12 and 2022-23 ---------------------------------
ind = []
for d, base in [(e11, '2011-12'), (e22, '2022-23')]:
    x = d[(d['category'] == 'Manufacturing') & d['sub_category'].notna()]
    x = x[['date', 'sub_category', 'index', 'growth_rate']].rename(columns={'sub_category': 'industry'})
    x['base_year'] = base
    ind.append(x)
ind = pd.concat(ind).sort_values(['base_year', 'industry', 'date'])
assert ind.groupby('base_year')['industry'].nunique().eq(23).all()
ind.to_csv(CLEAN / 'industry_monthly.csv', index=False)

# --- 1 June 2026 first release ----------------------------------------------------------
T = pd.read_html(PR_HTML)


def find(title):
    # Some tables are nested inside layout tables; take the innermost (smallest) match.
    hits = [t for t in T if str(t.iloc[0, 0]).startswith(title)]
    assert hits, title
    return min(hits, key=lambda t: t.size)


MON = ['Apr*', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar']


def monthly_from_statement(t, names_row, year_row):
    """Statement tables: header rows give series name and fiscal year per column."""
    rows = []
    names = t.iloc[names_row, 1:].tolist()
    years = t.iloc[year_row, 1:].tolist()
    body = t[t.iloc[:, 0].isin(MON)]
    for j, (nm, fy_) in enumerate(zip(names, years), start=1):
        y0 = int(str(fy_)[:4])
        for _, r in body.iterrows():
            mi = MON.index(r.iloc[0])
            date = pd.Timestamp(y0 + (1 if mi >= 9 else 0), (mi + 3) % 12 + 1, 1)
            v = pd.to_numeric(r.iloc[j], errors='coerce')
            if not np.isnan(v):
                rows.append(dict(date=date, series=nm, index=v))
    return pd.DataFrame(rows)


s1 = find('STATEMENT I: INDEX OF INDUSTRIAL PRODUCTION - SECTORAL')
st1 = monthly_from_statement(s1, 2, 4)
st1['series'] = st1['series'].replace({'Mining & Quarrying': 'Mining', 'General Index': 'General'})
s3 = find('STATEMENT III: INDEX OF INDUSTRIAL PRODUCTION - USE-BASED')
st3 = monthly_from_statement(s3, 2, 4)
st3['series'] = st3['series'].str.replace(r'\s+', ' ', regex=True).replace(
    {'Consumer durables': 'Consumer Durables', 'Consumer non-durables': 'Consumer Non-durables'})
J = pd.concat([st1, st3]).sort_values(['series', 'date'])
J['base_year'] = '2022-23'
J['source'] = 'MoSPI first release, 1 June 2026, Statements I and III'
J.to_csv(CLEAN / 'iip_2022-23_june2026.csv', index=False)

# Official annual growth in both bases (the release's comparison tables).
rows = []
name_by_weight = {'100.0000': 'General', '11.053': 'Mining', '76.062': 'Manufacturing',
                  '10.865': 'Electricity & Gas Supply'}
for t in T:
    hdr = [str(x) for x in t.iloc[0].tolist()]
    if hdr[:2] == ['Series', 'Weights'] and t.shape[1] == 5:
        body = t.iloc[2:]
        new = body[body.iloc[:, 0].astype(str) == '2022-23']
        if new.empty:
            continue
        w = str(new.iloc[0, 1])
        if w not in name_by_weight:
            continue
        for _, r in body.iterrows():
            for k, yr in enumerate(['2023-24', '2024-25', '2025-26']):
                rows.append(dict(series=name_by_weight[w], base_year=str(r.iloc[0]), weight=r.iloc[1],
                                 fiscal_year=yr, growth_pct=float(r.iloc[2 + k])))
    if hdr[1:3] == ['Weights', 'Series']:
        for _, r in t.iloc[1:].iterrows():
            for k, yr in enumerate(['2023-24', '2024-25', '2025-26']):
                nm = re.sub(r'\s+', ' ', str(r.iloc[0])).replace('Consumer durables', 'Consumer Durables') \
                    .replace('Consumer non-durables', 'Consumer Non-durables')
                rows.append(dict(series=nm, base_year=str(r.iloc[2]), weight=r.iloc[1],
                                 fiscal_year=yr, growth_pct=float(r.iloc[3 + k])))
P3 = pd.DataFrame(rows)
# In the 2011-12 base the sector is plain Electricity; label it so it pairs with the
# 2022-23 Electricity & Gas row it is printed against.
P3['pair'] = 'Pair 3'
P3['source'] = 'MoSPI first release of IIP base 2022-23, 1 June 2026, annual growth comparison tables'
P3.to_csv(OFFICIAL / 'mospi2026_pair3_annual_growth.csv', index=False)
assert len(P3) == 2 * 3 * 4 + 2 * 3 * 6, len(P3)

# Table B.2 industry weights.
b2 = [t for t in T if 'Sectoral and NIC Wise' in ' '.join(map(str, t.iloc[0].tolist()))][0]
b2 = b2.iloc[2:].copy()
b2.columns = ['nic', 'description', 'w_2011', 'n_2011', 'w_2022', 'n_2022']
b2.to_csv(OFFICIAL / 'industry_weights_2011-12_2022-23.csv', index=False)

print('iip_monthly.csv:')
print(M.groupby(['base_year', 'series'])['date'].agg(['min', 'max', 'size']).to_string())
print('\nJune 2026 version:', J['date'].min().date(), '->', J['date'].max().date(),
      sorted(J['series'].unique()))
print('Industries:', ind.groupby('base_year')['date'].agg(['min', 'max']).to_string())
