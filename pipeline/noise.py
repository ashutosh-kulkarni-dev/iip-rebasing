"""Stage 5e: how large is the disagreement between bases in ordinary months?

For each overlap (General index, true YoY months in both bases):
  overlap metrics : mean gap (new - old), root-mean-square difference, correlation, share of
                    months with opposite signs
  change noise    : at every date t with L months before and after, the 'change' in a base is
                    mean growth over [t, t+L) minus mean growth over [t-L, t). We compare the change
                    in the two bases: |change_new - change_old| (the disagreement), |change| in each
                    base (the size of what is being measured), and the share of dates at which the
                    two bases change in opposite directions.
  episode placebo : each episode's disagreement in the change, against the same statistic at every
                    other date of the overlap (pseudo-events); share of dates with a disagreement at
                    least as large: over all other dates, over dates more than 6 months away, and over
                    dates whose window shares no month with the event's window (the clean test).
  annual gaps     : General-index annual gap (new - old) in every complete overlap year.
  contributions   : each use-based category's share of the mean gap and of the mean squared
                    difference between the bases' General YoY growth, over each whole overlap.
Writes results/noise_overlap.csv, noise_changes.csv, noise_placebo.csv, noise_annual_gaps.csv,
       noise_contributions.csv
"""
import numpy as np
import pandas as pd
from config import PAIRS, RESULTS
from common import true_yoy

rows_o, rows_c, rows_p = [], [], []
G = {}
for pair, old, new, start, end in PAIRS:
    o, n = true_yoy(old)['General'], true_yoy(new)['General']
    d = pd.concat([o, n], axis=1, keys=['old', 'new']).loc[start:end].dropna()
    G[pair] = d
    gap = d['new'] - d['old']
    rows_o.append(dict(pair=pair, months=len(d), first=d.index.min().strftime('%Y-%m'), last=d.index.max().strftime('%Y-%m'),
                       mean_gap=gap.mean(), rmsd=np.sqrt((gap ** 2).mean()), corr=d['old'].corr(d['new']),
                       opposite_sign_share=(np.sign(d['old']) != np.sign(d['new'])).mean(),
                       sd_old=d['old'].std(), sd_new=d['new'].std()))


def change(s, t, pre, post):
    a = s[t - pd.DateOffset(months=pre):t - pd.DateOffset(months=1)]
    b = s[t:t + pd.DateOffset(months=post - 1)]
    if len(a) != pre or len(b) != post:
        return np.nan
    return b.mean() - a.mean()


THRESH = [1, 2]  # percentage points of YoY growth
for pair, d in G.items():
    for L in [6, 12]:
        recs = []
        for t in d.index:
            co, cn = change(d['old'], t, L, L), change(d['new'], t, L, L)
            if np.isnan(co) or np.isnan(cn):
                continue
            recs.append((co, cn))
        if not recs:
            continue
        r = np.array(recs)
        dis = np.abs(r[:, 1] - r[:, 0])
        rows_c.append(dict(pair=pair, window_months=L, dates=len(r), median_abs_disagreement=np.median(dis),
                           p90_abs_disagreement=np.percentile(dis, 90),
                           median_abs_change_old=np.median(np.abs(r[:, 0])), median_abs_change_new=np.median(np.abs(r[:, 1])),
                           # ratio of medians (the paper's definition; reliability.py uses the same).
                           # The earlier median of per-date ratios (bounded at 2) is dropped.
                           ratio_disagreement_to_larger_change=np.median(dis) / max(np.median(np.abs(r[:, 0])), np.median(np.abs(r[:, 1]))),
                           opposite_direction_share=(np.sign(r[:, 0]) != np.sign(r[:, 1])).mean()))
        # the same share, only at dates where both bases' changes exceed a threshold
        # (sign flips between two near-zero changes say little)
        for th in THRESH:
            m = (np.abs(r) > th).all(axis=1)
            rows_c[-1][f'dates_both_above_{th}'] = int(m.sum())
            rows_c[-1][f'opposite_share_both_above_{th}'] = (np.sign(r[m, 0]) != np.sign(r[m, 1])).mean() if m.sum() else np.nan

EPIS = [('GFC', 'Pair 1', '2008-09-01', 24, 19), ('GFC', 'Pair 1', '2008-09-01', 12, 12),
        ('GFC', 'Pair 1', '2008-09-01', 6, 6),
        ('Demonetisation', 'Pair 2', '2016-11-01', 7, 5), ('Demonetisation', 'Pair 2', '2016-11-01', 4, 5),
        ('Demonetisation', 'Pair 2', '2016-11-01', 12, 5), ('Demonetisation', 'Pair 2', '2016-11-01', 5, 5)]
EXCL = 6  # comparison dates within 6 months of the event share most of its window; reported separately
for ep, pair, t0, pre, post in EPIS:
    d = G[pair]
    t0 = pd.Timestamp(t0)
    ev = change(d['new'], t0, pre, post) - change(d['old'], t0, pre, post)
    pl, gap, clean = [], [], []
    for t in d.index:
        if t == t0:
            continue
        v = change(d['new'], t, pre, post) - change(d['old'], t, pre, post)
        if not np.isnan(v):
            pl.append(v)
            k = (t.year - t0.year) * 12 + t.month - t0.month
            gap.append(abs(k))
            clean.append(k >= pre + post or k <= -(pre + post))  # window shares no month with the event's
    pl, gap, clean = np.array(pl), np.array(gap), np.array(clean, dtype=bool)
    far = pl[gap > EXCL]  # comparison dates more than EXCL months from the event
    sep = pl[clean]       # comparison windows entirely separate from the event window
    rows_p.append(dict(episode=ep, pair=pair, months_before=pre, months_after=post,
                       change_old=change(d['old'], t0, pre, post), change_new=change(d['new'], t0, pre, post),
                       disagreement=ev, pseudo_dates=len(pl), share_as_large=(np.abs(pl) >= abs(ev)).mean(),
                       median_abs_placebo=np.median(np.abs(pl)),
                       pseudo_dates_far=len(far), share_as_large_far=(np.abs(far) >= abs(ev)).mean() if len(far) else np.nan,
                       pseudo_dates_separate=len(sep),
                       share_as_large_separate=(np.abs(sep) >= abs(ev)).mean() if len(sep) else np.nan))

# 2012-14: annual gap in the episode years vs the average annual gap of the overlap
A = pd.read_csv(RESULTS / 'overlap_annual.csv')
A = A[(A['pair'] == 'Pair 2') & (A['series'] == 'General') & (A['data_version'] == 'esankhyiki')].set_index('fiscal_year')
rows_p.append(dict(episode='2012-14 slowdown', pair='Pair 2', months_before=np.nan, months_after=np.nan,
                   change_old=np.nan, change_new=np.nan,
                   disagreement=A.loc[['2012-13', '2013-14'], 'gap'].mean(), pseudo_dates=len(A),
                   share_as_large=(A['gap'] >= A.loc[['2012-13', '2013-14'], 'gap'].mean()).mean(),
                   median_abs_placebo=A['gap'].mean()))
A_all = pd.read_csv(RESULTS / 'overlap_annual.csv')
A_all = A_all[(A_all['series'] == 'General') & (A_all['data_version'] == 'esankhyiki')]
A_all[['pair', 'fiscal_year', 'old', 'new', 'gap']].round(3).to_csv(RESULTS / 'noise_annual_gaps.csv', index=False)

# Which categories account for the disagreement over each whole overlap ---------------------
# In a fixed-base Laspeyres index, General = sum of w_c * I_c / 100 over the use-based
# categories, so General YoY growth = sum over c of w_c * (I_c,t - I_c,t-12) / G_t-12 (w in %).
# Contributions are computed for the four categories with the same names in every base; the
# remainder (basic/primary and infrastructure goods, defined differently across bases, plus
# rounding) is 'Other'. The YoY gap (new - old) is the sum of contribution gaps, and its mean
# square splits exactly as MSD = sum over c of mean(contribution gap_c x total gap).
from config import USE4, USE_WEIGHTS
from common import levels
rows_k = []
for pair, old, new, start, end in PAIRS:
    gaps = {}
    for role, b in [('old', old), ('new', new)]:
        lv = levels(b, base_year=False)
        g = (lv['General'] / lv['General'].shift(12) - 1) * 100
        con = pd.DataFrame({c: USE_WEIGHTS[b][c] * (lv[c] - lv[c].shift(12)) / lv['General'].shift(12) for c in USE4})
        con['Other'] = g - con.sum(axis=1)
        gaps[role] = con
    idx = G[pair].index
    dc = (gaps['new'] - gaps['old']).reindex(idx)
    tot = dc.sum(axis=1)
    msd = (tot ** 2).mean()
    h = len(idx) // 2  # half-sample shares: a check that equal full-sample shares are not mechanical
    half = lambda x, t: (x * t).mean() / (t ** 2).mean()
    for c in USE4 + ['Other']:
        rows_k.append(dict(pair=pair, category=c, months=len(idx), mean_contribution_gap=dc[c].mean(),
                           share_of_mean_gap=dc[c].mean() / tot.mean(),
                           share_of_msd=(dc[c] * tot).mean() / msd,
                           share_of_msd_first_half=half(dc[c][:h], tot[:h]),
                           share_of_msd_second_half=half(dc[c][h:], tot[h:]),
                           weight_old=USE_WEIGHTS[old][c] if c != 'Other' else 100 - sum(USE_WEIGHTS[old].values()),
                           weight_new=USE_WEIGHTS[new][c] if c != 'Other' else 100 - sum(USE_WEIGHTS[new].values())))
# Check of the additivity identity in the bases that publish every use-based category
from config import OTHER_USE_WEIGHTS
for b in OTHER_USE_WEIGHTS:
    lv = levels(b, base_year=False)
    g12 = lv['General'].shift(12)
    allc = {**USE_WEIGHTS[b], **OTHER_USE_WEIGHTS[b]}
    res = ((lv['General'] / g12 - 1) * 100 - sum(w * (lv[c] - lv[c].shift(12)) / g12 for c, w in allc.items())).dropna()
    rows_k.append(dict(pair='identity check', category=b, months=len(res), max_abs_residual=res.abs().max()))
K = pd.DataFrame(rows_k)
K.round(4).to_csv(RESULTS / 'noise_contributions.csv', index=False)

O, C, Pl = pd.DataFrame(rows_o), pd.DataFrame(rows_c), pd.DataFrame(rows_p)
O.round(3).to_csv(RESULTS / 'noise_overlap.csv', index=False)
C.round(3).to_csv(RESULTS / 'noise_changes.csv', index=False)
Pl.round(3).to_csv(RESULTS / 'noise_placebo.csv', index=False)
pd.set_option('display.width', 220)
for X in (O, C, Pl, K):
    print(X.round(2).to_string(index=False)); print()
