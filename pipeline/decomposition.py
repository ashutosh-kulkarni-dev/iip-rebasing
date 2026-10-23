"""Stage 4 (M3, M4): weight/residual decomposition for each pair, and the GFC case.

For a pair (old, new) the four-category aggregate is built four ways: each base's data
with each base's weights. Category indices are rescaled to 100 over a common anchor before
weighting, so the versions differ only in data and weights. The gap between the new-base
version (new data, new weights) and the old-base version (old data, old weights) is split
with the two-factor Shapley average into a weight effect and a residual (everything that is
not the four category weights: item basket, factory panel, data sources, deflation, and the
category definitions themselves). The split is exact: weight + residual = gap.

Writes:
  results/decomposition_pairs.csv   M3: mean growth and SD of the aggregate's YoY, each pair
  results/gfc_measures.csv          M4: GFC depth, General index and aggregate, both bases
  results/gfc_decomposition.csv     M4: Shapley decomposition under five depth measures
"""
import numpy as np
import pandas as pd
from config import PAIRS, USE4, GFC_START, GFC_END, GFC_ANCHOR, RESULTS
from common import levels, yoy, aggregate, shapley

# --- M3 -----------------------------------------------------------------------------------
rows = []
for pair, old, new, start, end in PAIRS:
    s0, e0 = pd.Timestamp(start), pd.Timestamp(end)
    true_from = s0 + pd.DateOffset(months=12)          # first true YoY month of the new base
    anchor = (s0 - pd.DateOffset(months=12), s0 - pd.DateOffset(months=1))  # new base year
    versions = ['esankhyiki', 'june2026'] if new == '2022-23' else ['esankhyiki']
    for ver in versions:
        lo, ln = levels(old), levels(new, ver)
        for cats_name, cats in [('four categories', USE4),
                                ('excl. Capital Goods', [c for c in USE4 if c != 'Capital Goods'])]:
            A = {}
            for dk, lv in [('o', lo), ('n', ln)]:
                for wk, wb in [('o', old), ('n', new)]:
                    A[dk + wk] = yoy(aggregate(lv, wb, cats, anchor)).loc[true_from:e0]
            for stat, f in [('mean YoY growth', np.mean), ('SD of YoY growth', lambda x: np.std(x, ddof=1))]:
                v = {k: f(x.dropna().values) for k, x in A.items()}
                w, r = shapley(v['oo'], v['on'], v['no'], v['nn'])
                gap = v['nn'] - v['oo']
                rows.append(dict(pair=pair, data_version=ver, category_set=cats_name, statistic=stat,
                                 months=int(A['oo'].dropna().size),
                                 old_data_old_wts=v['oo'], old_data_new_wts=v['on'],
                                 new_data_old_wts=v['no'], new_data_new_wts=v['nn'],
                                 gap=gap, weight_effect=w, residual=r,
                                 weight_share_of_gap=w / gap if gap else np.nan))
D = pd.DataFrame(rows)
D.round(4).to_csv(RESULTS / 'decomposition_pairs.csv', index=False)

# --- M4: GFC ---------------------------------------------------------------------------------
S, E = pd.Timestamp(GFC_START), pd.Timestamp(GFC_END)


def ma_drawdown(x):
    """Peak-to-trough fall of the 12-month moving average: peak in the 12 months to onset,
    trough between the peak and the window end (v5 definition). 0 if no fall."""
    mm = x.rolling(12, min_periods=12).mean()
    pre = mm[S - pd.DateOffset(months=12):S]
    peak_date = pre.idxmax()
    trough = mm[peak_date:E].min()
    return min(0.0, (trough / pre.max() - 1) * 100)


def window_mean(x):
    return yoy(x)[S:E].mean()


def growth_gap(x):
    y = yoy(x)
    return y[S:E].mean() - y[S - pd.DateOffset(months=24):S - pd.DateOffset(months=1)].mean()


def yoy_fall(x):
    y = yoy(x)
    return y[S:E].min() - y[S - pd.DateOffset(months=12):S - pd.DateOffset(months=1)].mean()


def trend_shortfall(x):
    lx = np.log(x)
    pre = lx[S - pd.DateOffset(months=36):S - pd.DateOffset(months=1)]
    coef = np.polyfit(np.arange(len(pre)), pre.values, 1)
    win = lx[S:E]
    t = np.arange(len(pre), len(pre) + len(win))
    return (np.exp(win.values - np.polyval(coef, t)) - 1).min() * 100


MEASURES = [('In-window mean YoY growth (%)', window_mean), ('MA drawdown (%)', ma_drawdown),
            ('Growth gap vs prior 24 months (pp)', growth_gap), ('YoY fall vs prior 12 months (pp)', yoy_fall),
            ('Trend shortfall (%)', trend_shortfall)]

l93, l04 = levels('1993-94', base_year=False), levels('2004-05', base_year=False)
mrows = []
for b, lv in [('1993-94', l93), ('2004-05', l04)]:
    for s in ['General', 'Manufacturing', 'Mining', 'Electricity'] + USE4:
        for mname, f in MEASURES:
            mrows.append(dict(base_year=b, series=s, measure=mname, value=f(lv[s])))
    agg = aggregate(lv, b, USE4, GFC_ANCHOR)
    for mname, f in MEASURES:
        mrows.append(dict(base_year=b, series='Four-category aggregate (own weights)', measure=mname, value=f(agg)))
M = pd.DataFrame(mrows)
M.round(3).to_csv(RESULTS / 'gfc_measures.csv', index=False)

drows = []
for cats_name, cats in [('four categories', USE4),
                        ('excl. Capital Goods', [c for c in USE4 if c != 'Capital Goods'])]:
    for mname, f in MEASURES:
        v = {'oo': f(aggregate(l93, '1993-94', cats, GFC_ANCHOR)), 'on': f(aggregate(l93, '2004-05', cats, GFC_ANCHOR)),
             'no': f(aggregate(l04, '1993-94', cats, GFC_ANCHOR)), 'nn': f(aggregate(l04, '2004-05', cats, GFC_ANCHOR))}
        w, r = shapley(v['oo'], v['on'], v['no'], v['nn'])
        gap = v['nn'] - v['oo']
        drows.append(dict(category_set=cats_name, measure=mname,
                          old_data_old_wts=v['oo'], old_data_new_wts=v['on'],
                          new_data_old_wts=v['no'], new_data_new_wts=v['nn'],
                          gap=gap, weight_effect=w, residual=r, weight_share_of_gap=w / gap,
                          max_single_order_weight_share=max(abs(v['on'] - v['oo']), abs(v['nn'] - v['no'])) / abs(gap)))
G = pd.DataFrame(drows)
G.round(4).to_csv(RESULTS / 'gfc_decomposition.csv', index=False)

pd.set_option('display.width', 250)
print(D[['pair', 'data_version', 'category_set', 'statistic', 'months', 'old_data_old_wts', 'new_data_new_wts',
         'gap', 'weight_effect', 'residual', 'weight_share_of_gap']].round(2).to_string(index=False))
print()
print(M[M['series'].isin(['General', 'Four-category aggregate (own weights)'])].pivot_table(
    index=['series', 'measure'], columns='base_year', values='value').round(2).to_string())
print()
print(G.round(2).to_string(index=False))
