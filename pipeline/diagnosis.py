"""Stage 6b (A2): does rebasing change the sectoral diagnosis of a slowdown or acceleration?

Contributions (fixed-base Laspeyres): the contribution of unit c to General YoY growth at t is
    C_c,t = w_c * (I_c,t - I_c,t-12) / G_t-12        (w in % of the General index)
The 'Other' unit is the residual, so contributions add exactly to General YoY growth:
  sectors   : Mining, Manufacturing, Electricity; Other = rounding (and, in 2022-23, gas supply
              and water/sewerage, 2.7% weight, which have no counterpart in 2011-12).
  use-based : the 4 categories named alike in every base; Other = basic/primary and
              infrastructure goods (defined differently across bases) plus rounding.
At every date t with full windows (L = 6, 12), the contribution of c to the CHANGE in General
growth is mean C_c over [t, t+L) minus mean over [t-L, t). Per date we record:
  leader_same     : the unit contributing most in the direction of each base's own aggregate
                    change is the same unit in both bases
  leader_abs_same : the unit with the largest absolute contribution is the same
  sign_flip_share : share of named units whose contribution to the change has opposite signs
  spearman        : rank correlation of the units' contributions (use-based: 4 named + Other)
  agg_dir_same    : the two bases agree on the direction of the change in General growth
Summaries per pair use all dates and, separately, dates where General growth moves by more
than 1 pp in BOTH bases (a slowdown or acceleration worth diagnosing). Approximate
independent windows = dates / (2L). All of this is descriptive.

Episodes (worked examples, every window stated):
  GFC            Pair 1, t0 = Sep 2008; (before, after) months = (6,6), (12,12), (24,19)
  Demonetisation Pair 2, t0 = Nov 2016; (7,5), (5,5), (4,5), (12,5)
  2012-14        Pair 2: contributions to ANNUAL General growth in 2012-13 and 2013-14 (monthly
                 growth in the 2011-12 base is not true growth before April 2013)
Writes results/diagnosis_dates.csv, diagnosis_summary.csv, diagnosis_episodes.csv
"""
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from config import PAIRS, RESULTS, USE_WEIGHTS, SECTOR_WEIGHTS, OTHER_USE_WEIGHTS
from common import levels, SECTOR_UNITS, USE_UNITS, annual_growth

pd.set_option('display.width', 250)


def contributions(base, family, version='esankhyiki', six=False):
    lv = levels(base, version if base == '2022-23' else 'esankhyiki', base_year=False)
    g12 = lv['General'].shift(12)
    gy = (lv['General'] / g12 - 1) * 100
    if family == 'sector':
        W = dict(SECTOR_WEIGHTS[base])
        W = {k: W[k] for k in SECTOR_UNITS}
        if base == '2022-23' and version == 'june2026':
            W.pop('Electricity')
            W['Electricity'] = SECTOR_WEIGHTS['2022-23']['Electricity & Gas Supply']
            lv = lv.rename(columns={'Electricity & Gas Supply': 'Electricity'})
    else:
        W = dict(USE_WEIGHTS[base])
        if six:
            W.update(OTHER_USE_WEIGHTS[base])
    C = pd.DataFrame({c: w * (lv[c] - lv[c].shift(12)) / g12 for c, w in W.items()})
    C['Other'] = gy - C.sum(axis=1)
    C['General'] = gy
    return C


def wchange(C, t, pre, post):
    i = C.index.get_loc(t)
    if i - pre < 0 or i + post > len(C):
        return None
    a, b = C.iloc[i - pre:i], C.iloc[i:i + post]
    if a.isna().any().any() or b.isna().any().any():
        return None
    return b.mean() - a.mean()


def leader(x, units, direction):
    v = x[units] * (np.sign(direction) if direction != 0 else 1)
    return v.idxmax()


def compare(co, cn, named, rank_units):
    r = {}
    r['dG_old'], r['dG_new'] = co['General'], cn['General']
    r['agg_dir_same'] = np.sign(co['General']) == np.sign(cn['General'])
    lo, ln = leader(co, named, co['General']), leader(cn, named, cn['General'])
    r['leader_old'], r['leader_new'], r['leader_same'] = lo, ln, lo == ln
    r['leader_abs_same'] = co[named].abs().idxmax() == cn[named].abs().idxmax()
    r['weakest_old'], r['weakest_new'] = co[named].idxmin(), cn[named].idxmin()
    r['sign_flip_share'] = (np.sign(co[named]) != np.sign(cn[named])).mean()
    r['spearman'] = spearmanr(co[rank_units], cn[rank_units]).statistic
    return r


FAMILIES = [('sector', SECTOR_UNITS, SECTOR_UNITS, False),
            ('use-based', USE_UNITS, USE_UNITS + ['Other'], False)]
rows = []
for pair, old, new, start, end in PAIRS:
    versions = ['esankhyiki', 'june2026'] if new == '2022-23' else ['esankhyiki']
    for ver in versions:
        fams = FAMILIES + ([('use-based (6 categories)', USE_UNITS + ['Primary Goods', 'Infrastructure/ Construction Goods'],
                             USE_UNITS + ['Primary Goods', 'Infrastructure/ Construction Goods'], True)]
                           if new == '2022-23' else [])
        for fam, named, rank_units, six in fams:
            if fam == 'sector' and ver == 'june2026':
                continue  # 1 June 2026 release has no Electricity (NIC 351) series: excluded
            fk = 'sector' if fam == 'sector' else 'use'
            Co = contributions(old, fk, six=six).loc[start:end]
            Cn = contributions(new, fk, ver, six=six).loc[start:end]
            idx = Co.dropna().index.intersection(Cn.dropna().index)
            Co, Cn = Co.loc[idx], Cn.loc[idx]
            for L in (6, 12):
                for t in idx:
                    co, cn = wchange(Co, t, L, L), wchange(Cn, t, L, L)
                    if co is None or cn is None:
                        continue
                    rows.append(dict(pair=pair, data_version=ver, family=fam, L=L, date=t.strftime('%Y-%m'),
                                     **compare(co, cn, named, rank_units)))
D = pd.DataFrame(rows)
D.round(4).to_csv(RESULTS / 'diagnosis_dates.csv', index=False)


def chance(x):
    """Leader agreement expected if each base picked its leader independently with its own
    observed leader frequencies: sum over units of p_old(u) * p_new(u). Agreement is only
    informative relative to this (for sectors, Manufacturing's 75-79% weight makes it high)."""
    po, pn = x['leader_old'].value_counts(normalize=True), x['leader_new'].value_counts(normalize=True)
    return float((po * pn.reindex(po.index).fillna(0)).sum())


def summ(x):
    return pd.Series(dict(dates=len(x), indep_windows=len(x) / (2 * x['L'].iloc[0]) if len(x) else 0,
                          agg_dir_same=x['agg_dir_same'].mean(), leader_same=x['leader_same'].mean(),
                          leader_same_chance=chance(x),
                          leader_abs_same=x['leader_abs_same'].mean(), mean_sign_flip_share=x['sign_flip_share'].mean(),
                          any_sign_flip=(x['sign_flip_share'] > 0).mean(), median_spearman=x['spearman'].median()))


S = []
for keys, x in D.groupby(['pair', 'data_version', 'family', 'L']):
    S.append(dict(zip(['pair', 'data_version', 'family', 'L'], keys), subset='all dates', **summ(x)))
    m = x[(x['dG_old'].abs() > 1) & (x['dG_new'].abs() > 1)]
    if len(m):
        S.append(dict(zip(['pair', 'data_version', 'family', 'L'], keys), subset='|change in General| > 1 pp in both', **summ(m)))
S = pd.DataFrame(S)
S.round(3).to_csv(RESULTS / 'diagnosis_summary.csv', index=False)
print(S.round(2).to_string(index=False))

# --- episodes ----------------------------------------------------------------------------------
E = []
EPIS = [('GFC', 'Pair 1', '1993-94', '2004-05', '2008-09-01', [(6, 6), (12, 12), (24, 19)]),
        ('Demonetisation', 'Pair 2', '2004-05', '2011-12', '2016-11-01', [(7, 5), (5, 5), (4, 5), (12, 5)])]
for ep, pair, old, new, t0, wins in EPIS:
    for fam, named, rank_units, six in FAMILIES:
        fk = 'sector' if fam == 'sector' else 'use'
        Co, Cn = contributions(old, fk), contributions(new, fk)
        for pre, post in wins:
            co, cn = wchange(Co, pd.Timestamp(t0), pre, post), wchange(Cn, pd.Timestamp(t0), pre, post)
            cmp = compare(co, cn, named, rank_units)
            for u in rank_units + ([] if 'Other' in rank_units else ['Other']) + ['General']:
                E.append(dict(episode=ep, pair=pair, family=fam, window=f'{pre} before / {post} after',
                              statistic='contribution to change in General YoY growth (pp)', unit=u,
                              old=co[u], new=cn[u], leader_old=cmp['leader_old'], leader_new=cmp['leader_new'],
                              weakest_old=cmp['weakest_old'], weakest_new=cmp['weakest_new'],
                              sign_flip_share=cmp['sign_flip_share'], spearman=cmp['spearman']))
# 2012-14: contributions to annual growth
for fam, named, rank_units, six in FAMILIES:
    res = {}
    for role, b in [('old', '2004-05'), ('new', '2011-12')]:
        lv = levels(b)  # base-year months at 100: exact for annual means
        a = lv.groupby(lv.index.map(lambda t: t.year if t.month >= 4 else t.year - 1)).mean()
        W = {k: SECTOR_WEIGHTS[b][k] for k in SECTOR_UNITS} if fam == 'sector' else USE_WEIGHTS[b]
        out = {}
        for y in (2012, 2013):
            c = pd.Series({k: w * (a.loc[y, k] - a.loc[y - 1, k]) / a.loc[y - 1, 'General'] for k, w in W.items()})
            gy = (a.loc[y, 'General'] / a.loc[y - 1, 'General'] - 1) * 100
            c['Other'], c['General'] = gy - c.sum(), gy
            out[y] = c
        res[role] = (out[2012] + out[2013]) / 2
    cmp = compare(res['old'], res['new'], named, rank_units)
    for u in rank_units + ([] if 'Other' in rank_units else ['Other']) + ['General']:
        E.append(dict(episode='2012-14 slowdown', pair='Pair 2', family=fam, window='average of 2012-13 and 2013-14',
                      statistic='contribution to annual General growth (pp)', unit=u, old=res['old'][u], new=res['new'][u],
                      leader_old=cmp['leader_old'], leader_new=cmp['leader_new'],
                      weakest_old=cmp['weakest_old'], weakest_new=cmp['weakest_new'],
                      sign_flip_share=cmp['sign_flip_share'], spearman=cmp['spearman']))
E = pd.DataFrame(E)
E.round(3).to_csv(RESULTS / 'diagnosis_episodes.csv', index=False)
print()
print(E.round(2).to_string(index=False))
