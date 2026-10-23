"""Stage 2: validate the dataset against every official figure available.

Writes results/validation_*.csv and exits with status 1 if a check that must pass fails.
Checks:
  V1  published monthly YoY = YoY recomputed from published levels (month 13 onward)
  V2  first-year convention: published YoY in the first 12 months = index - 100
  V3  annual April-March growth vs the official overlap tables, all three pairs
  V4  linking factors: recomputed vs official (2011-12 -> 2022-23); the two older
      factors are computed by the same formula
  V5  the two official versions of the 2022-23 series (eSankhyiki vs 1 June 2026 release)
"""
import sys
import numpy as np
import pandas as pd
from config import OFFICIAL, RESULTS, BASES, PAIRS, TOL_PP, OFFICIAL_LINKING, SERIES
from common import monthly, wide, levels, annual_growth, true_yoy

RESULTS.mkdir(exist_ok=True)
fail = []

# V1 ----------------------------------------------------------------------------------
rows = []
for b in BASES:
    rep = wide(b, 'growth_rate')
    rec = true_yoy(b)
    for s in rep.columns:
        d = (rep[s] - rec[s]).dropna()
        rows.append(dict(base_year=b, series=s, months_compared=len(d),
                         max_abs_dev_pp=round(d.abs().max(), 3), mean_abs_dev_pp=round(d.abs().mean(), 3)))
v1 = pd.DataFrame(rows)
v1.to_csv(RESULTS / 'validation_v1_yoy_recompute.csv', index=False)
if (v1['max_abs_dev_pp'] > 0.06).any():
    fail.append('V1')

# V2 ----------------------------------------------------------------------------------
rows = []
for b in BASES:
    lv, g = wide(b, 'index'), wide(b, 'growth_rate')
    first12 = lv.index[:12]
    d = (g.loc[first12] - (lv.loc[first12] - 100)).abs()
    rows.append(dict(base_year=b, first_month=first12[0].strftime('%Y-%m'),
                     months=len(first12), max_abs_dev_pp=round(np.nanmax(d.values), 3)))
v2 = pd.DataFrame(rows)
v2.to_csv(RESULTS / 'validation_v2_first_year_convention.csv', index=False)

# V3 ----------------------------------------------------------------------------------
off = pd.concat([pd.read_csv(OFFICIAL / 'cso2011_pair1_annual_growth.csv').assign(target='esankhyiki'),
                 pd.read_csv(OFFICIAL / 'mospi2017_pair2_annual_growth.csv').assign(target='esankhyiki'),
                 pd.read_csv(OFFICIAL / 'mospi2026_pair3_annual_growth.csv').assign(target='june2026'),
                 pd.read_csv(OFFICIAL / 'mospi2026jun29_2022-23_annual_growth.csv').assign(target='esankhyiki')],
                ignore_index=True)
off.loc[(off['base_year'] == '2011-12') & (off['series'] == 'Electricity & Gas Supply'), 'series'] = 'Electricity'
# The 1 June 2026 table's 2011-12 rows are checked against our (single) 2011-12 series.
off.loc[off['base_year'] == '2011-12', 'target'] = 'esankhyiki'
rows = []
for version in ['esankhyiki', 'june2026']:
    ann = {b: annual_growth(levels(b, version)) for b in BASES}
    for _, r in off[off['target'] == version].iterrows():
        a = ann[r['base_year']]
        ours = a.loc[r['fiscal_year'], r['series']] if (r['fiscal_year'] in a.index and r['series'] in a.columns) else np.nan
        rows.append(dict(pair=r['pair'], data_version=version, base_year=r['base_year'], series=r['series'],
                         fiscal_year=r['fiscal_year'], official=r['growth_pct'],
                         ours=round(ours, 2), diff_pp=round(ours - r['growth_pct'], 2)))
v3 = pd.DataFrame(rows)
v3['within_tol'] = v3['diff_pp'].abs() <= TOL_PP
v3.to_csv(RESULTS / 'validation_v3_annual_vs_official.csv', index=False)
summ = v3.groupby(['pair', 'data_version', 'base_year']).agg(
    n=('diff_pp', 'count'), max_abs_diff_pp=('diff_pp', lambda x: x.abs().max()),
    n_outside_tol=('within_tol', lambda x: int((~x).sum()))).reset_index()
summ.to_csv(RESULTS / 'validation_v3_summary.csv', index=False)
# Must pass: everything except the 2011-12 side of pair 2. The May 2017 release printed
# the then-provisional 2011-12 series; our 2011-12 data are the later revised series, so
# these rows are reported, not enforced (the 2004-05 side, which was frozen, is enforced).
must = v3[~((v3['pair'] == 'Pair 2') & (v3['base_year'] == '2011-12'))]
# Rows with no data on our side (2011-12 Primary and Infrastructure end in Dec 2025) are
# reported as NaN and not enforced.
must = must[must['ours'].notna()]
if (~must['within_tol']).any():
    fail.append('V3')

# V4 ----------------------------------------------------------------------------------
rows = []
for _, old, new, start, _end in PAIRS:
    by0 = pd.Timestamp(start) - pd.DateOffset(months=12)  # new base year = 12 months before
    by1 = pd.Timestamp(start) - pd.DateOffset(months=1)
    lo = levels(old, base_year=False).loc[by0:by1]
    for s in ['General', 'Mining', 'Manufacturing', 'Electricity']:
        gm = np.exp(np.log(lo[s]).mean()) if len(lo) == 12 else np.nan
        lf = gm / 100
        offv = OFFICIAL_LINKING.get(s) if new == '2022-23' else np.nan
        rows.append(dict(transition=f'{old} -> {new}', series=s, months_used=len(lo),
                         linking_factor=round(lf, 4), official=offv,
                         diff=round(lf - offv, 4) if offv == offv else np.nan))
v4 = pd.DataFrame(rows)
v4.to_csv(RESULTS / 'validation_v4_linking_factors.csv', index=False)
if (v4['diff'].abs() > 0.00005).any():
    fail.append('V4')

# V5 ----------------------------------------------------------------------------------
e = wide('2022-23', 'index', 'esankhyiki')
j = wide('2022-23', 'index', 'june2026')
rows = []
for s in j.columns:
    d = (e[s] - j[s]).dropna()
    rows.append(dict(series=s, months_compared=len(d), months_differing=int((d.abs() > 0.05).sum()),
                     max_abs_diff_index_pts=round(d.abs().max(), 1),
                     mean_diff_index_pts=round(d.mean(), 2)))
v5 = pd.DataFrame(rows)
v5.to_csv(RESULTS / 'validation_v5_2022-23_versions.csv', index=False)

pd.set_option('display.width', 200)
print('V1 max |reported - recomputed YoY|:', v1['max_abs_dev_pp'].max())
print('V2 first-year YoY = index - 100:\n', v2.to_string(index=False))
print('\nV3 annual growth vs official:\n', summ.to_string(index=False))
print('\nV3 rows outside tolerance:\n', v3[~v3['within_tol']].to_string(index=False))
print('\nV4 linking factors:\n', v4.to_string(index=False))
print('\nV5 2022-23 versions:\n', v5.to_string(index=False))
if fail:
    print('\nFAILED:', fail)
    sys.exit(1)
print('\nAll enforced checks passed.')
