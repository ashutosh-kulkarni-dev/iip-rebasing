"""Stage 6a (A1): which sectors' short-run movements survive rebasing?

For every unit (General, 3 sectors, 4 common use-based categories; in Pair 3 also Primary and
Infrastructure/Construction goods and 23 NIC 2-digit manufacturing industries) and every
overlap, compare true YoY growth in the two bases.

Disagreement and signal
  level  : RMSD of YoY growth (new - old); its demeaned version SD(gap) (persistent gap removed;
           RMSD^2 = mean gap^2 + SD(gap)^2); signal = SD of YoY growth in each base.
  change : at every date with full windows, change_L = mean YoY over [t, t+L) - mean over [t-L, t),
           L = 6 and 12 months. Disagreement = median |change_new - change_old|; signal = median
           |change| in each base. A constant gap cancels in a change, so change ratios are already
           free of the persistent gap.
Reliability ratio = disagreement / signal, with signal = the LARGER of the two bases (headline,
as in the current paper) and the pooled version (root-mean-square of the two SDs for levels;
the mean of the two medians for changes). Ratio of medians everywhere (not median of per-date
ratios, which is bounded at 2).

Reading rule (fixed before results were computed): ratio < 1 -> short-run movements readable
on either base; ratio > 1 -> not readable on a single base. A classification is 'robust' only
if the 95% stationary-bootstrap interval lies on the same side of 1 at BOTH mean block lengths
(6 and 12 months for levels; L/2 and L for changes). Headline ratio: 6-month change, larger
signal. Pair 3 (24 months; 21 for Primary, Infrastructure and industries) is descriptive only:
its intervals rest on 2-4 blocks and are reported but never used to classify.

Mean gap inference for every unit: fixed-b Newey-West, EWC (harinf.py) and an ordinary t test
on non-overlapping fiscal-year gaps (all complete overlap years, and true-YoY years only).

Writes results/reliability.csv, results/reliability_intervals.csv, results/gap_inference.csv
"""
import numpy as np
import pandas as pd
from config import PAIRS, RESULTS, fy
from common import unit_pairs, window_change, levels, annual_growth, CLEAN
from harinf import boot, fixed_b_nw, ewc, annual_t

REPS = 2000


def level_stats(d):
    g = d['new'] - d['old']
    so, sn = d['old'].std(ddof=0), d['new'].std(ddof=0)
    big, pooled = max(so, sn), np.sqrt((so ** 2 + sn ** 2) / 2)
    rmsd, sdg = np.sqrt((g ** 2).mean()), g.std(ddof=0)
    return dict(months=len(d), mean_gap=g.mean(), rmsd=rmsd, sd_gap=sdg, sd_old=so, sd_new=sn,
                corr=d['old'].corr(d['new']), R_level=rmsd / big, R_level_demeaned=sdg / big,
                R_level_pooled=rmsd / pooled, R_level_demeaned_pooled=sdg / pooled)


def change_frame(d, L):
    full = d.asfreq('MS')
    if full.isna().any().any():  # never expected: overlaps are contiguous
        raise ValueError('gap in monthly data')
    return pd.concat([window_change(full['old'], L), window_change(full['new'], L)], axis=1,
                     keys=['old', 'new']).dropna()


def change_stats(c, L):
    if len(c) == 0:
        return {f'dates_{L}': 0}
    dis = np.median(np.abs(c['new'] - c['old']))
    mo, mn = np.median(np.abs(c['old'])), np.median(np.abs(c['new']))
    return {f'dates_{L}': len(c), f'indep_windows_{L}': len(c) / (2 * L), f'med_dis_{L}': dis,
            f'med_chg_old_{L}': mo, f'med_chg_new_{L}': mn,
            f'R_chg_{L}': dis / max(mo, mn), f'R_chg_{L}_pooled': dis / ((mo + mn) / 2),
            f'opp_dir_{L}': (np.sign(c['old']) != np.sign(c['new'])).mean()}


def r_level_dm(a):
    g = a[:, 1] - a[:, 0]
    return g.std() / max(a[:, 0].std(), a[:, 1].std())


def r_chg(a):
    dis = np.median(np.abs(a[:, 1] - a[:, 0]))
    return dis / max(np.median(np.abs(a[:, 0])), np.median(np.abs(a[:, 1])))


def classify(est, ivs, descriptive):
    side = 'below 1' if est < 1 else 'above 1'
    if descriptive:
        return side + ' (descriptive)'
    if all((iv['hi'] < 1) if est < 1 else (iv['lo'] > 1) for iv in ivs):
        return side + ' (robust)'
    return side + ' (not robust)'


def industry_levels(base):
    I = pd.read_csv(CLEAN / 'industry_monthly.csv', parse_dates=['date'])
    w = I[I['base_year'] == base].pivot_table(index='date', columns='industry', values='index').sort_index()
    first = w.index.min()
    pre = pd.DataFrame(100.0, index=pd.date_range(first - pd.DateOffset(months=12), periods=12, freq='MS'), columns=w.columns)
    return pd.concat([pre, w])


rows, ivrows, grows = [], [], []
for pair, old, new, start, end in PAIRS:
    versions = ['esankhyiki', 'june2026'] if new == '2022-23' else ['esankhyiki']
    for ver in versions:
        U = unit_pairs(old, new, start, end, ver, industries=True)
        ag_o = annual_growth(levels(old))
        ag_n = annual_growth(levels(new, ver if new == '2022-23' else 'esankhyiki'))
        if new == '2022-23' and ver == 'esankhyiki':
            ag_o = ag_o.join(annual_growth(industry_levels(old)))
            ag_n = ag_n.join(annual_growth(industry_levels(new)))
        first_true = fy(pd.Timestamp(start) + pd.DateOffset(months=12))
        for unit, (fam, d) in U.items():
            descriptive = pair == 'Pair 3'
            r = dict(pair=pair, data_version=ver, family=fam, unit=unit, first=d.index.min().strftime('%Y-%m'),
                     last=d.index.max().strftime('%Y-%m'), **level_stats(d))
            ch = {L: change_frame(d, L) for L in (6, 12)}
            for L in (6, 12):
                r.update(change_stats(ch[L], L))
            # intervals ------------------------------------------------------------------
            ivs_level = []
            for b in (6, 12):
                iv = boot(d[['old', 'new']].values, r_level_dm, b, REPS)
                ivs_level.append(iv)
                ivrows.append(dict(pair=pair, data_version=ver, unit=unit, statistic='R_level_demeaned', **iv))
            r['class_level_demeaned'] = classify(r['R_level_demeaned'], ivs_level, descriptive)
            if len(ch[6]) >= 6:
                ivs_chg = []
                for b in (3, 6):
                    iv = boot(ch[6][['old', 'new']].values, r_chg, b, REPS)
                    ivs_chg.append(iv)
                    ivrows.append(dict(pair=pair, data_version=ver, unit=unit, statistic='R_chg_6', **iv))
                r['R_chg_6_lo'] = min(iv['lo'] for iv in ivs_chg)
                r['R_chg_6_hi'] = max(iv['hi'] for iv in ivs_chg)
                r['class_chg_6'] = classify(r['R_chg_6'], ivs_chg, descriptive)
            r['R_level_dm_lo'] = min(iv['lo'] for iv in ivs_level)
            r['R_level_dm_hi'] = max(iv['hi'] for iv in ivs_level)
            rows.append(r)
            # mean gap inference --------------------------------------------------------------
            g = (d['new'] - d['old']).values
            for res in (fixed_b_nw(g), ewc(g)):
                grows.append(dict(pair=pair, data_version=ver, family=fam, unit=unit, sample='monthly true YoY', **res))
            if unit in ag_o.columns and unit in ag_n.columns or (unit == 'Electricity' and ver == 'june2026'):
                un = 'Electricity & Gas Supply' if (unit == 'Electricity' and ver == 'june2026') else unit
                yrs = [y for y in ag_n.index if y in ag_o.index and pd.Timestamp(start) <= pd.Timestamp(f'{y[:4]}-04-01') <= pd.Timestamp(end)]
                ann = (ag_n.loc[yrs, un] - ag_o.loc[yrs, unit]).dropna()
                for lab, sub in [('annual, all complete overlap years', ann),
                                 ('annual, true-YoY years only', ann[[y for y in ann.index if y >= first_true]])]:
                    if len(sub) >= 2:
                        res = annual_t(sub.values)
                        grows.append(dict(pair=pair, data_version=ver, family=fam, unit=unit, sample=lab,
                                          years=' '.join(f'{y}:{v:.2f}' for y, v in sub.items()), **res))

R = pd.DataFrame(rows)
R.round(4).to_csv(RESULTS / 'reliability.csv', index=False)
pd.DataFrame(ivrows).round(4).to_csv(RESULTS / 'reliability_intervals.csv', index=False)
GI = pd.DataFrame(grows)
GI.round(4).to_csv(RESULTS / 'gap_inference.csv', index=False)

pd.set_option('display.width', 250)
pd.set_option('display.max_rows', 200)
cols = ['pair', 'data_version', 'unit', 'months', 'mean_gap', 'rmsd', 'sd_gap', 'sd_old', 'sd_new', 'R_level_demeaned',
        'class_level_demeaned', 'dates_6', 'med_dis_6', 'med_chg_old_6', 'med_chg_new_6', 'R_chg_6', 'R_chg_6_lo', 'R_chg_6_hi',
        'class_chg_6', 'R_chg_12']
print(R[~R['family'].str.startswith('Industry')][cols].round(2).to_string(index=False))
print()
print(R[R['family'].str.startswith('Industry')][['unit', 'months', 'mean_gap', 'rmsd', 'R_level_demeaned', 'R_chg_6', 'corr']]
      .sort_values('R_level_demeaned').round(2).to_string(index=False))
print()
print(GI[GI['unit'] == 'General'][['pair', 'data_version', 'sample', 'T', 'est', 'lo', 'hi', 'reject']].round(2).to_string(index=False))
