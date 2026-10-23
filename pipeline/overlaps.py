"""Stage 3 (M1, M2): compare consecutive bases over each overlap.

Monthly YoY growth is compared only where it is a true 12-month growth rate in BOTH bases,
i.e. from the 13th published month of the new base (the first 12 published growth rates
of every base are index - 100 against a flat base year; validate.py, V2). A variant that
keeps those 12 months is reported for comparison with earlier drafts.

Writes:
  results/overlap_stats.csv          one row per pair x data version x series x sample
  results/overlap_annual.csv         annual April-March growth in both bases, each pair
  results/overlap_industries_pair3.csv  23 manufacturing industries, pair 3
"""
import numpy as np
import pandas as pd
from config import PAIRS, SERIES, RESULTS
from common import levels, true_yoy, yoy, annual_growth, wide

rng = np.random.default_rng(20261017)


def block_boot_corr(x, y, block=12, reps=2000):
    """95% moving-block bootstrap interval for the correlation (blocks of 12 months, which
    respects the overlap in consecutive YoY rates)."""
    n = len(x)
    if n < 2 * block:
        block = max(3, n // 4)
    starts = np.arange(n - block + 1)
    k = int(np.ceil(n / block))
    out = []
    for _ in range(reps):
        idx = np.concatenate([np.arange(s, s + block) for s in rng.choice(starts, k)])[:n]
        out.append(np.corrcoef(x[idx], y[idx])[0, 1])
    return np.nanpercentile(out, [2.5, 97.5])


def newey_west_se(x, lags=12):
    """Standard error of the mean of x allowing for autocorrelation up to `lags` months
    (Bartlett weights). Consecutive YoY rates share 11 of 12 months, so ordinary standard
    errors would be far too small."""
    x = np.asarray(x) - np.mean(x)
    n = len(x)
    lags = min(lags, n - 1)
    v = x @ x / n
    for k in range(1, lags + 1):
        v += 2 * (1 - k / (lags + 1)) * (x[k:] @ x[:-k]) / n
    return np.sqrt(v / n)


def stats(go, gn):
    d = pd.concat([go, gn], axis=1, keys=['old', 'new']).dropna()
    o, n = d['old'].values, d['new'].values
    lo, hi = block_boot_corr(o, n) if len(d) >= 12 else (np.nan, np.nan)
    se = newey_west_se(n - o)
    return dict(months=len(d), first=d.index.min().strftime('%Y-%m'), last=d.index.max().strftime('%Y-%m'),
                corr=np.corrcoef(o, n)[0, 1], corr_ci_lo=lo, corr_ci_hi=hi,
                mean_old=o.mean(), mean_new=n.mean(), mean_gap_new_minus_old=n.mean() - o.mean(),
                gap_se_nw=se, gap_ci_lo=n.mean() - o.mean() - 1.96 * se, gap_ci_hi=n.mean() - o.mean() + 1.96 * se,
                mean_abs_diff=np.abs(n - o).mean(),
                sd_old=o.std(ddof=1), sd_new=n.std(ddof=1), sd_ratio_new_old=n.std(ddof=1) / o.std(ddof=1),
                share_contract_old=(o < 0).mean(), share_contract_new=(n < 0).mean(),
                share_direction_disagree=(np.sign(o) != np.sign(n)).mean())


rows, ann_rows = [], []
for pair, old, new, start, end in PAIRS:
    s0, e0 = pd.Timestamp(start), pd.Timestamp(end)
    versions = ['esankhyiki', 'june2026'] if new == '2022-23' else ['esankhyiki']
    for ver in versions:
        yo_true, yn_true = true_yoy(old), true_yoy(new, ver)
        yo_all, yn_all = yoy(levels(old)), yoy(levels(new, ver))  # incl. first-year months
        cols = [c for c in yn_true.columns if c in yo_true.columns]
        extra = []
        if new == '2022-23' and ver == 'june2026':
            extra = [('Electricity', 'Electricity & Gas Supply')]  # June release has no NIC 351 by month
        pairs_of_cols = [(c, c) for c in cols] + extra
        for so, sn in pairs_of_cols:
            for sample, (a, b) in {'true YoY (from month 13)': (yo_true, yn_true),
                                   'all overlap months': (yo_all, yn_all)}.items():
                r = stats(a[so].loc[s0:e0], b[sn].loc[s0:e0])
                rows.append(dict(pair=pair, old_base=old, new_base=new, data_version=ver, series=so,
                                 new_series_used=sn, sample=sample, **r))
        # annual growth in both bases over the overlap's fiscal years
        ao, an = annual_growth(levels(old)), annual_growth(levels(new, ver))
        fys = [y for y in an.index if y in ao.index]
        for y in fys:
            for so, sn in pairs_of_cols:
                if so in ao.columns and sn in an.columns:
                    ann_rows.append(dict(pair=pair, data_version=ver, fiscal_year=y, series=so,
                                         old=ao.loc[y, so], new=an.loc[y, sn], gap=an.loc[y, sn] - ao.loc[y, so]))

S = pd.DataFrame(rows)
order = {s: i for i, s in enumerate(SERIES + ['Primary Goods', 'Infrastructure/ Construction Goods'])}
S['o'] = S['series'].map(order)
S = S.sort_values(['pair', 'data_version', 'sample', 'o']).drop(columns='o')
S.round(4).to_csv(RESULTS / 'overlap_stats.csv', index=False)
A = pd.DataFrame(ann_rows)
A.round(2).to_csv(RESULTS / 'overlap_annual.csv', index=False)

# --- 23 manufacturing industries, pair 3 ------------------------------------------------
I = pd.read_csv(RESULTS.parent / 'data' / 'clean' / 'industry_monthly.csv', parse_dates=['date'])
W = pd.read_csv(RESULTS.parent / 'data' / 'official' / 'industry_weights_2011-12_2022-23.csv')
W = W[W['nic'].astype(str).str.fullmatch(r'\d{2}')].copy()
W['industry_key'] = W['description'].str.lower().str.replace(r'\s+', ' ', regex=True).str.strip()
ind_rows = []
for name, g in I.groupby('industry'):
    lo = g[g['base_year'] == '2011-12'].set_index('date')['index']
    ln = g[g['base_year'] == '2022-23'].set_index('date')['index']
    go, gn = yoy(lo), yoy(ln)  # new base: from month 13 automatically (t-12 not published)
    r = stats(go.loc['2024-04-01':'2026-03-01'], gn.loc['2024-04-01':'2026-03-01'])
    key = name.lower().replace('  ', ' ').strip()
    w = W[W['industry_key'] == key]
    ind_rows.append(dict(industry=name, w_2011=float(w['w_2011'].iloc[0]) if len(w) else np.nan,
                         w_2022=float(w['w_2022'].iloc[0]) if len(w) else np.nan, **r))
IND = pd.DataFrame(ind_rows).sort_values('corr')
IND.round(3).to_csv(RESULTS / 'overlap_industries_pair3.csv', index=False)

# Does the industry growth gap follow the change in the item basket? Basket change = %
# change in the number of item groups between the bases (Table B.2 of the 1 June release).
W2 = W.copy()
for c in ['w_2011', 'n_2011', 'w_2022', 'n_2022']:
    W2[c] = pd.to_numeric(W2[c], errors='coerce')
W2['industry_key'] = W2['industry_key'].replace(
    {'manufacture of basic pharmaceuticals products and pharmaceutical preparations':
     'manufacture of basic pharmaceutical products and pharmaceutical preparations'})
J = IND.drop(columns=['w_2011', 'w_2022']).assign(
    industry_key=IND['industry'].str.lower().str.replace(r'\s+', ' ', regex=True).str.strip()).merge(
    W2[['industry_key', 'w_2011', 'n_2011', 'w_2022', 'n_2022']], on='industry_key')
assert len(J) == 23, len(J)
J['gap'] = J['mean_new'] - J['mean_old']
J['item_group_change_pct'] = (J['n_2022'] / J['n_2011'] - 1) * 100
J['weight_change_pct'] = (J['w_2022'] / J['w_2011'] - 1) * 100
J.round(3).to_csv(RESULTS / 'overlap_industries_pair3.csv', index=False)
IS = pd.DataFrame([dict(
    industries=len(J), months=int(J['months'].iloc[0]),
    share_new_faster=(J['gap'] > 0).mean(), n_new_faster=int((J['gap'] > 0).sum()),
    weighted_mean_gap=np.average(J['gap'], weights=J['w_2022']),
    median_corr=J['corr'].median(),
    spearman_gap_vs_item_group_change=J[['gap', 'item_group_change_pct']].corr('spearman').iloc[0, 1],
    spearman_absgap_vs_item_group_change=J['gap'].abs().corr(J['item_group_change_pct'], method='spearman'),
    spearman_corr_vs_item_group_change=J[['corr', 'item_group_change_pct']].corr('spearman').iloc[0, 1])])
IS.round(3).to_csv(RESULTS / 'industry_summary_pair3.csv', index=False)
print(IS.round(2).to_string(index=False))

pd.set_option('display.width', 250)
show = ['pair', 'data_version', 'series', 'months', 'corr', 'corr_ci_lo', 'corr_ci_hi', 'mean_old', 'mean_new',
        'share_direction_disagree', 'sd_ratio_new_old']
print(S[S['sample'] == 'true YoY (from month 13)'][show].round(2).to_string(index=False))
print('\nAll overlap months (first-year pseudo-growth included):')
print(S[(S['sample'] == 'all overlap months') & (S['series'].isin(['General', 'Manufacturing', 'Mining', 'Electricity']))][show].round(2).to_string(index=False))
print('\nIndustries, pair 3:', IND['w_2022'].notna().sum(), 'matched weights')
print(IND[['industry', 'w_2022', 'months', 'corr', 'mean_old', 'mean_new']].round(2).to_string(index=False))
