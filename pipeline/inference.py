"""Stage 5f: inference for the whole-overlap General-index statistics (revised Oct 2026).

Changes from the first version, after review: Newey-West with 12 lags and normal critical
values is dropped (over-sized at T = 24-63 with overlapping YoY data).

Mean gap (new - old): four results per overlap, all reported (harinf.py):
  EWC (headline; Lazarus, Lewis, Stock and Watson 2018), fixed-b Newey-West (Kiefer and
  Vogelsang 2005; M = ceil(1.3 sqrt T)), and t tests on non-overlapping fiscal-year gaps (all
  complete overlap years; true-YoY years only).
  Decision rule: the gap is called 'different from zero' only if ALL FOUR intervals exclude 0;
  'fragile' if some do and some do not; otherwise 'not distinguishable from zero'.
Bootstrap statistics (RMSD, correlation, capital goods + durables share of the MSD, ratio of the
median disagreement in 6-month changes to the larger median change): stationary bootstrap
(Politis and Romano 1994), mean block 12 months (6 for the 24-month Pair 3), 2,000 draws, fixed
seed, percentile intervals. Every row reports the expected number of blocks, the bootstrap
median and the share of draws below the point estimate (0.5 when the distribution is centred on
it). Intervals resting on fewer than 8 expected blocks are flagged 'coarse' and must be read as
descriptive. A moving-block version (Kunsch 1989) and mean blocks 6/12/18 are sensitivity checks.
Effective number of independent windows for direction shares = dates / (2 x window length).
Writes results/inference.csv and results/inference_sensitivity.csv (same columns as before plus
method, expected_blocks, boot_median, share_below_est, flag).
"""
import numpy as np
import pandas as pd
from config import PAIRS, RESULTS, USE_WEIGHTS, fy
from common import levels, true_yoy, annual_growth
from harinf import boot, fixed_b_nw, ewc, annual_t, stationary_indices, SEED

REPS = 2000


def change(s, t, L):
    a = s[t - pd.DateOffset(months=L):t - pd.DateOffset(months=1)]
    b = s[t:t + pd.DateOffset(months=L - 1)]
    return b.mean() - a.mean() if len(a) == L and len(b) == L else np.nan


D = {}
for pair, old, new, start, end in PAIRS:
    o, n = true_yoy(old)['General'], true_yoy(new)['General']
    d = pd.concat([o, n], axis=1, keys=['old', 'new']).loc[start:end].dropna()
    con = {}
    for role, b in [('old', old), ('new', new)]:
        lv = levels(b, base_year=False)
        g12 = lv['General'].shift(12)
        con[role] = sum(USE_WEIGHTS[b][c] * (lv[c] - lv[c].shift(12)) / g12 for c in ['Capital Goods', 'Consumer Durables'])
    d['capdur_gap'] = (con['new'] - con['old']).reindex(d.index)
    ch = pd.DataFrame({t: (change(d['old'], t, 6), change(d['new'], t, 6)) for t in d.index}, index=['old', 'new']).T.dropna()
    ag_o, ag_n = annual_growth(levels(old))['General'], annual_growth(levels(new))['General']
    yrs = [y for y in ag_n.index if y in ag_o.index and pd.Timestamp(start) <= pd.Timestamp(f'{y[:4]}-04-01') <= pd.Timestamp(end)]
    ann = (ag_n[yrs] - ag_o[yrs]).dropna()
    first_true = fy(pd.Timestamp(start) + pd.DateOffset(months=12))
    D[pair] = (d, ch, ann, ann[[y for y in ann.index if y >= first_true]])

# statistics on an array with columns old, new, capdur_gap
f_rmsd = lambda a: np.sqrt(((a[:, 1] - a[:, 0]) ** 2).mean())
f_corr = lambda a: np.corrcoef(a[:, 0], a[:, 1])[0, 1]
f_capdur = lambda a: (a[:, 2] * (a[:, 1] - a[:, 0])).mean() / ((a[:, 1] - a[:, 0]) ** 2).mean()


def f_ratio(a):
    dis = np.median(np.abs(a[:, 1] - a[:, 0]))
    return dis / max(np.median(np.abs(a[:, 0])), np.median(np.abs(a[:, 1])))


STATS = [('rmsd', f_rmsd), ('corr', f_corr), ('capdur_share', f_capdur)]
RATIO = 'ratio: median disagreement / larger median change (6-month)'


def gap_rows(tag):
    rows = []
    for pair, (d, ch, ann, ann_true) in D.items():
        g = (d['new'] - d['old']).values
        res = [('EWC', ewc(g)), ('fixed-b NW', fixed_b_nw(g)),
               (f'annual t, {len(ann)} fiscal years', annual_t(ann.values)),
               (f'annual t, {len(ann_true)} true-YoY fiscal years', annual_t(ann_true.values))]
        excl = [r['lo'] > 0 or r['hi'] < 0 for _, r in res]
        verdict = 'different from zero' if all(excl) else ('fragile' if any(excl) else 'not distinguishable from zero')
        for m, r in res:
            rows.append(dict(sample=tag, pair=pair, statistic='mean gap (new - old)' if m == 'EWC' else f'mean gap (new - old), {m}',
                             method=m, months_or_dates=r['T'], block=np.nan, estimate=r['est'], se=r['se'], lo=r['lo'], hi=r['hi'],
                             crit=r['crit'], df=r.get('df', np.nan), bandwidth=r.get('bandwidth', np.nan), flag=verdict))
    return rows


def boot_rows(mean_block, small_block, tag, kind='stationary'):
    rows, draws = [], {}
    for pair, (d, ch, ann, ann_true) in D.items():
        n = len(d)
        bl = mean_block if n >= 36 else small_block
        A = d[['old', 'new', 'capdur_gap']].values
        for nm, f in STATS:
            r = boot(A, f, bl, REPS, kind)
            rows.append(dict(sample=tag, pair=pair, statistic=nm, method=f'{kind} bootstrap', months_or_dates=n, block=bl,
                             estimate=r['est'], lo=r['lo'], hi=r['hi'], expected_blocks=r['expected_blocks'],
                             boot_median=r['boot_median'], share_below_est=r['share_below_est'],
                             flag='coarse (<8 blocks)' if r['expected_blocks'] < 8 else ''))
        rng = np.random.default_rng(SEED + int(pair[-1]))  # independent streams per overlap
        draws[pair] = np.array([f_capdur(A[i]) for i in stationary_indices(n, bl, REPS, rng)])
        m = len(ch)
        blc = bl if m >= 2 * bl else max(3, m // 3)
        r = boot(ch[['old', 'new']].values, f_ratio, blc, REPS, kind)
        rows.append(dict(sample=tag, pair=pair, statistic=RATIO, method=f'{kind} bootstrap', months_or_dates=m, block=blc,
                         estimate=r['est'], lo=r['lo'], hi=r['hi'], expected_blocks=r['expected_blocks'],
                         boot_median=r['boot_median'], share_below_est=r['share_below_est'],
                         flag='coarse (<8 blocks)' if r['expected_blocks'] < 8 else ''))
    diff = draws['Pair 1'] - draws['Pair 2']
    est = f_capdur(D['Pair 1'][0][['old', 'new', 'capdur_gap']].values) - f_capdur(D['Pair 2'][0][['old', 'new', 'capdur_gap']].values)
    rows.append(dict(sample=tag, pair='Pair 1 - Pair 2', statistic='capdur_share difference', method='stationary bootstrap',
                     block=mean_block, estimate=est, lo=np.quantile(diff, 0.025), hi=np.quantile(diff, 0.975)))
    return rows


main = pd.DataFrame(gap_rows('main') + boot_rows(12, 6, 'main'))
NC = pd.read_csv(RESULTS / 'noise_changes.csv')
eff = []
for _, r in NC.iterrows():
    for th in ['', '_1']:
        col = 'dates' if th == '' else 'dates_both_above_1'
        eff.append(dict(sample='main', pair=r['pair'], statistic=f"effective windows, L={int(r['window_months'])}"
                        + (' (both changes > 1 pp)' if th else ''), months_or_dates=r[col],
                        estimate=r[col] / (2 * r['window_months'])))
main = pd.concat([main, pd.DataFrame(eff)], ignore_index=True)
main.round(4).to_csv(RESULTS / 'inference.csv', index=False)

sens = sum([boot_rows(b, max(3, b // 2), f'block {b}') for b in (6, 12, 18)], [])
sens += boot_rows(12, 6, 'moving block 12', kind='moving')
# bandwidth sensitivity for the HAR tests
for pair, (d, ch, ann, ann_true) in D.items():
    g = (d['new'] - d['old']).values
    T = len(g)
    from harinf import _bartlett_lrv, fixed_b_cv
    from scipy import stats as st
    for mult in (0.75, 1.0, 1.5):
        M = max(2, int(np.ceil(mult * 1.3 * np.sqrt(T))))
        se = np.sqrt(_bartlett_lrv(g, M) / T)
        cv = fixed_b_cv(M / T)
        sens.append(dict(sample=f'fixed-b NW, M={M}', pair=pair, statistic='mean gap (new - old)', method='fixed-b NW',
                         months_or_dates=T, estimate=g.mean(), se=se, lo=g.mean() - cv * se, hi=g.mean() + cv * se, crit=cv, bandwidth=M))
    for nu in sorted({max(2, int(np.floor(0.4 * T ** (2 / 3))) - 1), int(np.floor(0.4 * T ** (2 / 3))), int(np.floor(0.4 * T ** (2 / 3))) + 2}):
        t_ = np.arange(1, T + 1)
        u = g - g.mean()
        lam = np.array([np.sqrt(2 / T) * (np.cos(np.pi * j * (t_ - 0.5) / T) @ u) for j in range(1, nu + 1)])
        se = np.sqrt((lam ** 2).mean() / T)
        cv = st.t.ppf(0.975, nu)
        sens.append(dict(sample=f'EWC, nu={nu}', pair=pair, statistic='mean gap (new - old)', method='EWC', months_or_dates=T,
                         estimate=g.mean(), se=se, lo=g.mean() - cv * se, hi=g.mean() + cv * se, crit=cv, df=nu))
sens = pd.DataFrame(sens)
sens.round(4).to_csv(RESULTS / 'inference_sensitivity.csv', index=False)

pd.set_option('display.width', 250)
print(main.drop(columns=['se'], errors='ignore').round(3).to_string(index=False))
print()
print(sens[sens['statistic'].str.startswith('mean gap')][['sample', 'pair', 'estimate', 'lo', 'hi']].round(2).to_string(index=False))
print(sens[(sens['statistic'] == 'corr')][['sample', 'pair', 'estimate', 'lo', 'hi', 'boot_median', 'share_below_est', 'expected_blocks']].round(3).to_string(index=False))
