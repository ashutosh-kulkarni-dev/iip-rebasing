"""Stage 6c (A3): where does each category's disagreement come from? Weights vs everything else.

Contribution of category c to General YoY growth: C_c = w_c * x_c, x_c = (I_c,t - I_c,t-12) / G_t-12
(w in % of General). Between bases, the contribution gap splits exactly (two-factor Shapley):
    w_n x_n - w_o x_o = (w_n - w_o) * (x_o + x_n) / 2      weight effect
                      + (w_o + w_n) / 2 * (x_n - x_o)      data effect (basket, panel, sources,
                                                           deflation and, in Pair 2, the 2017
                                                           use-based redefinition)
For the gap in General YoY growth, tot = sum_c gap_c, we report for each category and effect:
  share_msd        : mean(gap_c * tot) / mean(tot^2)          (as in noise.py; includes the mean gap)
  share_demeaned   : cov(gap_c, tot) / var(tot)               (persistent gap removed)
  share_mean_gap   : mean(gap_c) / mean(tot)
and a volatility benchmark: the category's share of the variance of General growth WITHIN each
base, cov(C_c, G) / var(G). A category whose disagreement share far exceeds its volatility share
is disagreeing beyond what its volatility alone would produce.

Controls with stable definitions: the three sectors (NIC-based, no redefinition), decomposed
the same way. Definitions test: only Pair 2 contains the 2017 use-based redefinition; if capital
goods' data-effect share and reliability ratio in Pair 2 do not exceed Pair 1's, the
redefinition is not the main driver. The Pair 1 - Pair 2 difference in capital goods' demeaned
data share gets a stationary-bootstrap interval (independent draws, mean block 12).
Writes results/sources_by_category.csv, results/sources_definitions_test.csv
"""
import numpy as np
import pandas as pd
from config import PAIRS, RESULTS, USE_WEIGHTS, SECTOR_WEIGHTS
from common import levels, SECTOR_UNITS, USE_UNITS
from harinf import stationary_indices, SEED


def frame(base, units, W):
    lv = levels(base, base_year=False)
    g12 = lv['General'].shift(12)
    G = (lv['General'] / g12 - 1) * 100
    X = pd.DataFrame({c: (lv[c] - lv[c].shift(12)) / g12 for c in units})
    C = X * pd.Series(W)
    wo = 100 - sum(W.values())
    C['Other'] = G - C.sum(axis=1)
    X['Other'] = C['Other'] / wo if abs(wo) > 1e-6 else 0.0
    return X, C, G, {**W, 'Other': wo}


def decompose(old, new, start, end, units, Wo, Wn):
    Xo, Co, Go, wo = frame(old, units, Wo)
    Xn, Cn, Gn, wn = frame(new, units, Wn)
    idx = Go.loc[start:end].dropna().index.intersection(Gn.loc[start:end].dropna().index)
    out = {}
    for c in list(units) + ['Other']:
        xo, xn = Xo.loc[idx, c], Xn.loc[idx, c]
        gap = Cn.loc[idx, c] - Co.loc[idx, c]
        # 'Other' for sectors is pure rounding (weight ~0): all of it goes to the data effect
        wgt = (wn[c] - wo[c]) * (xo + xn) / 2 if min(wo[c], wn[c]) > 0.5 else gap * 0
        out[c] = dict(weight=wgt, data=gap - wgt, Co=Co.loc[idx, c], Cn=Cn.loc[idx, c])
    return out, Go.loc[idx], Gn.loc[idx]


def shares(parts, tot):
    msd = (tot ** 2).mean()
    var = tot.var(ddof=0)
    td = tot - tot.mean()
    return dict(share_msd=(parts * tot).mean() / msd, share_demeaned=((parts - parts.mean()) * td).mean() / var,
                share_mean_gap=parts.mean() / tot.mean())


rows = []
store = {}
for pair, old, new, start, end in PAIRS:
    for fam, units, Wo, Wn in [
        ('use-based', USE_UNITS, USE_WEIGHTS[old], USE_WEIGHTS[new]),
        ('sector', SECTOR_UNITS, {k: SECTOR_WEIGHTS[old][k] for k in SECTOR_UNITS},
         {k: SECTOR_WEIGHTS[new][k] for k in SECTOR_UNITS})]:
        dec, Go, Gn = decompose(old, new, start, end, units, Wo, Wn)
        tot = sum(v['weight'] + v['data'] for v in dec.values())
        assert np.allclose(tot, Gn - Go, atol=1e-8)
        store[(pair, fam)] = (dec, tot)
        for c, v in dec.items():
            r = dict(pair=pair, family=fam, unit=c, months=len(tot),
                     weight_old=Wo.get(c, 100 - sum(Wo.values())), weight_new=Wn.get(c, 100 - sum(Wn.values())))
            for eff in ('total', 'weight', 'data'):
                part = v['weight'] + v['data'] if eff == 'total' else v[eff]
                for k, val in shares(part, tot).items():
                    r[f'{k}_{eff}'] = val
            r['vol_share_old_base'] = ((v['Co'] - v['Co'].mean()) * (Go - Go.mean())).mean() / Go.var(ddof=0)
            r['vol_share_new_base'] = ((v['Cn'] - v['Cn'].mean()) * (Gn - Gn.mean())).mean() / Gn.var(ddof=0)
            r['excess_over_volatility'] = r['share_demeaned_total'] - (r['vol_share_old_base'] + r['vol_share_new_base']) / 2
            rows.append(r)
S = pd.DataFrame(rows)
S.round(4).to_csv(RESULTS / 'sources_by_category.csv', index=False)

# Definitions test: Pair 1 vs Pair 2, capital goods (and capital goods + durables) --------------
def demeaned_data_share(arr):
    # arr columns: data part of the unit(s), total gap
    p, t = arr[:, 0], arr[:, 1]
    return ((p - p.mean()) * (t - t.mean())).mean() / t.var()


trows = []
for label, units in [('Capital Goods', ['Capital Goods']), ('Capital Goods + Consumer Durables', ['Capital Goods', 'Consumer Durables'])]:
    draws = {}
    for pair in ('Pair 1', 'Pair 2'):
        dec, tot = store[(pair, 'use-based')]
        data = sum(dec[u]['data'] for u in units)
        allp = sum(dec[u]['data'] + dec[u]['weight'] for u in units)
        arr = np.column_stack([data.values, tot.values])
        rng = np.random.default_rng(SEED + (1 if pair == 'Pair 2' else 0))  # independent streams
        draws[pair] = np.array([demeaned_data_share(arr[i]) for i in stationary_indices(len(arr), 12, 2000, rng)])
        trows.append(dict(units=label, pair=pair, demeaned_data_share=demeaned_data_share(arr),
                          demeaned_total_share=shares(allp, tot)['share_demeaned'],
                          lo=np.quantile(draws[pair], 0.025), hi=np.quantile(draws[pair], 0.975),
                          expected_blocks=len(arr) / 12))
    d = draws['Pair 1'] - draws['Pair 2']
    trows.append(dict(units=label, pair='Pair 1 - Pair 2', demeaned_data_share=trows[-2]['demeaned_data_share'] - trows[-1]['demeaned_data_share'],
                      lo=np.quantile(d, 0.025), hi=np.quantile(d, 0.975)))
T = pd.DataFrame(trows)
T.round(4).to_csv(RESULTS / 'sources_definitions_test.csv', index=False)

pd.set_option('display.width', 250)
cols = ['pair', 'family', 'unit', 'weight_old', 'weight_new', 'share_msd_total', 'share_msd_weight', 'share_msd_data',
        'share_demeaned_total', 'share_demeaned_weight', 'share_demeaned_data', 'share_mean_gap_total',
        'share_mean_gap_weight', 'vol_share_old_base', 'vol_share_new_base', 'excess_over_volatility']
print(S[cols].round(2).to_string(index=False))
print()
print(T.round(3).to_string(index=False))
