"""Shared loaders and calculations used by every analysis stage."""
import numpy as np
import pandas as pd
from config import CLEAN, USE_WEIGHTS, fy

_M = None


def monthly(version='esankhyiki'):
    """Long monthly table. version='june2026' swaps in the 1 June 2026 release for 2022-23."""
    global _M
    if _M is None:
        _M = pd.read_csv(CLEAN / 'iip_monthly.csv', parse_dates=['date'])
    if version == 'esankhyiki':
        return _M
    J = pd.read_csv(CLEAN / 'iip_2022-23_june2026.csv', parse_dates=['date'])
    J = J.sort_values(['series', 'date'])
    J['growth_rate'] = np.nan  # the release prints levels by month, not growth
    return pd.concat([_M[_M['base_year'] != '2022-23'], J], ignore_index=True)


def wide(base, value='index', version='esankhyiki'):
    m = monthly(version)
    return m[m['base_year'] == base].pivot_table(index='date', columns='series', values=value).sort_index()


def levels(base, version='esankhyiki', base_year=True):
    """Index levels from the first published month.

    No base publishes monthly indices for its own base year: the published series start
    12 months after the base year begins, and the published YoY growth for the first 12
    months equals index - 100 (validate.py checks this). That is, the base year is treated
    as 100 in every month. If base_year=True the 12 base-year months are prepended at 100,
    which is exact for annual growth (the base-year average is 100 by definition) but NOT
    for monthly YoY in the first published year, whose seasonal pattern is then spurious.
    Use true_yoy() for monthly growth."""
    lv = wide(base, 'index', version)
    if not base_year:
        return lv
    first = lv.index.min()
    idx = pd.date_range(first - pd.DateOffset(months=12), first - pd.DateOffset(months=1), freq='MS')
    prev = pd.DataFrame(100.0, index=idx, columns=lv.columns)
    return pd.concat([prev, lv]).sort_index()


def yoy(lv):
    return (lv / lv.shift(12) - 1) * 100


def true_yoy(base, version='esankhyiki'):
    """Monthly YoY growth computed from published levels, defined only from the 13th
    published month onward (so never against the flat base-year 100)."""
    return yoy(levels(base, version, base_year=False))


def annual_growth(lv, round_index=False):
    """April-March growth of the annual mean index, complete fiscal years only (a series
    with fewer than 12 months in a year gets NaN for that year). Published monthly indices
    are rounded to one decimal, so this reproduces MoSPI's figures (computed from unrounded
    indices) only to within about 0.15 pp; see TOL_PP in config.py."""
    k = lv.index.map(fy)
    grp = lv.groupby(k)
    a = grp.mean().where(grp.count() == 12)
    if round_index:
        a = a.round(1)
    years = sorted(a.index)
    out = {}
    for y0, y1 in zip(years[:-1], years[1:]):
        if int(y1[:4]) == int(y0[:4]) + 1:
            out[y1] = (a.loc[y1] / a.loc[y0] - 1) * 100
    return pd.DataFrame(out).T


def weights(base, cats):
    w = pd.Series(USE_WEIGHTS[base]).reindex(cats)
    return w / w.sum()


def aggregate(lv, wbase, cats, anchor):
    """Fixed-weight aggregate of category indices, each rescaled to 100 over `anchor`
    (a (start, end) pair), weighted with base `wbase` weights."""
    a0, a1 = pd.Timestamp(anchor[0]), pd.Timestamp(anchor[1])
    x = lv[cats] / lv.loc[a0:a1, cats].mean() * 100
    return (x * weights(wbase, cats)).sum(axis=1, min_count=len(cats))


def shapley(a_oo, a_on, a_no, a_nn):
    """Two-factor Shapley split of a_nn - a_oo (first letter = data, second = weights;
    o = old base, n = new base). Returns (weight effect, residual); they sum to the gap."""
    w = ((a_on - a_oo) + (a_nn - a_no)) / 2
    r = ((a_no - a_oo) + (a_nn - a_on)) / 2
    return w, r


# ---------------------------------------------------------------------------------------
# Units compared in each overlap (used by reliability.py, diagnosis.py, sources.py)
SECTOR_UNITS = ['Mining', 'Manufacturing', 'Electricity']
USE_UNITS = ['Capital Goods', 'Intermediate Goods', 'Consumer Durables', 'Consumer Non-durables']
PAIR3_EXTRA = ['Primary Goods', 'Infrastructure/ Construction Goods']


def industry_true_yoy(base):
    I = pd.read_csv(CLEAN / 'industry_monthly.csv', parse_dates=['date'])
    w = I[I['base_year'] == base].pivot_table(index='date', columns='industry', values='index').sort_index()
    return yoy(w)


def unit_pairs(old, new, start, end, version='esankhyiki', industries=False):
    """{unit: (family, DataFrame[old, new])} of true YoY growth over the overlap, both bases
    present. In the 1 June 2026 version of the 2022-23 series only 'Electricity & Gas Supply'
    is published, so it stands in for Electricity (flagged in the family label)."""
    yo, yn = true_yoy(old), true_yoy(new, version if new == '2022-23' else 'esankhyiki')
    units = [('General', 'General')] + [(u, 'Sector') for u in SECTOR_UNITS] + [(u, 'Use-based') for u in USE_UNITS]
    if new == '2022-23':
        units += [(u, 'Use-based (Pair 3 only)') for u in PAIR3_EXTRA]
    out = {}
    for u, fam in units:
        un = u
        if new == '2022-23' and version == 'june2026' and u == 'Electricity':
            continue  # the 1 June 2026 release publishes only Electricity & Gas Supply: excluded
        if u not in yo or un not in yn:
            continue
        d = pd.concat([yo[u], yn[un]], axis=1, keys=['old', 'new']).loc[start:end].dropna()
        if len(d):
            out[u] = (fam, d)
    if industries and new == '2022-23' and version == 'esankhyiki':
        io, inn = industry_true_yoy(old), industry_true_yoy(new)
        for u in sorted(set(io.columns) & set(inn.columns)):
            d = pd.concat([io[u], inn[u]], axis=1, keys=['old', 'new']).loc[start:end].dropna()
            if len(d):
                out[u] = ('Industry (NIC 2-digit)', d)
    return out


def window_change(s, L):
    """Change in mean YoY growth at every date t with full windows: mean over [t, t+L) minus
    mean over [t-L, t). s is a Series on a complete monthly index."""
    v = s.values
    idx = s.index
    out = {}
    for i in range(L, len(v) - L + 1):
        out[idx[i]] = v[i:i + L].mean() - v[i - L:i].mean()
    return pd.Series(out, dtype=float)
