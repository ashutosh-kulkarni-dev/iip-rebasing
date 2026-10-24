"""Stage 5g: splice-rule additions (Oct 2026 revision).

Builds on splice.py (General index, April 1994 - March 2026, 2022-23 = 100) and adds:
  1. 'overlap blend' (interpolation-type) splice: before each overlap the linked old base
     (base-year factor), after it the new base; inside the overlap the log level moves
     linearly from the old base to the new one (weight on the new base = 0 in the first
     overlap month, 1 in the last). The level drift accumulated over the overlap is thus spread
     over the overlap instead of appearing as a jump or being ignored. Applied to Pairs 1 and 2;
     Pair 3's overlap ends with the data, so there the rule switches at the new base's first month.
     All link factors, including the 'old base last' switch-point links, are ratios of GEOMETRIC
     means, as in MoSPI's official linking method. In the spirit of de la
     Fuente's interpolation splice, applied to the overlap rather than retropolated.
  2. Link-window sensitivity for 'old base last': link factor from the 12-month average before
     the switch (as in splice.py) vs the single month before the switch.
  3. The same rules for every series common to all bases, including the use-based categories,
     to show what a category splice across the 2017 use-based redefinition (the 2004-05 ->
     2011-12 joint, Pair 2) does relative to a joint without redefinition (Pair 1).
All linking factors use MoSPI's geometric-mean method over the new base year (validate.py V4).
Writes results/splice_rules_by_series.csv
"""
import numpy as np
import pandas as pd
from config import PAIRS, RESULTS, SERIES, fy
from common import levels

END = pd.Timestamp('2026-03-01')
IDX = pd.date_range('1994-04-01', END, freq='MS')
B = ['1993-94', '2004-05', '2011-12', '2022-23']
NEW_START = {'2004-05': '2005-04-01', '2011-12': '2012-04-01', '2022-23': '2023-04-01'}
OLD_LAST_SW = [('2004-05', '2011-07-01'), ('2011-12', '2017-04-01')]


def build(S):
    lv = {b: levels(b, base_year=False)[S] for b in B}
    LF = {}
    for _, old, new, start, _e in PAIRS:
        by = lv[old].loc[pd.Timestamp(start) - pd.DateOffset(months=12):pd.Timestamp(start) - pd.DateOffset(months=1)]
        LF[(old, new)] = np.exp(np.log(by).mean()) / 100
    chain = {'2022-23': 1.0}
    chain['2011-12'] = LF[('2011-12', '2022-23')]
    chain['2004-05'] = chain['2011-12'] * LF[('2004-05', '2011-12')]
    chain['1993-94'] = chain['2004-05'] * LF[('1993-94', '2004-05')]
    linked = {b: lv[b] / chain[b] for b in B}

    out = {}
    # new base first
    x = pd.Series(np.nan, index=IDX)
    segs = [('1993-94', '1994-04-01')] + [(b, NEW_START[b]) for b in B[1:]]
    for i, (b, s) in enumerate(segs):
        e = pd.Timestamp(segs[i + 1][1]) - pd.DateOffset(months=1) if i + 1 < len(segs) else END
        x.loc[pd.Timestamp(s):e] = linked[b].loc[pd.Timestamp(s):e]
    out['new base first'] = x
    # old base last, link at switch (12-month average, and single month)
    for lab, win in [('old base last (12-month link)', 12), ('old base last (1-month link)', 1)]:
        ls = {'2011-12': linked['2011-12']}
        for old, newer, sw in [('2004-05', '2011-12', '2017-04-01'), ('1993-94', '2004-05', '2011-07-01')]:
            w0, w1 = pd.Timestamp(sw) - pd.DateOffset(months=win), pd.Timestamp(sw) - pd.DateOffset(months=1)
            f = np.exp(np.log(lv[old].loc[w0:w1]).mean() - np.log(ls[newer].loc[w0:w1]).mean())  # geometric means, as MoSPI's official link
            ls[old] = lv[old] / f
        x = pd.Series(np.nan, index=IDX)
        segs = [('1993-94', '1994-04-01'), ('2004-05', '2011-07-01'), ('2011-12', '2017-04-01')]
        for i, (b, s) in enumerate(segs):
            e = pd.Timestamp(segs[i + 1][1]) - pd.DateOffset(months=1) if i + 1 < len(segs) else END
            x.loc[pd.Timestamp(s):e] = ls[b].loc[pd.Timestamp(s):e]
        out[lab] = x
    # old base last with the base-year factor (no re-linking at the switch)
    x = pd.Series(np.nan, index=IDX)
    segs = [('1993-94', '1994-04-01'), ('2004-05', '2011-07-01'), ('2011-12', '2017-04-01')]
    for i, (b, s) in enumerate(segs):
        e = pd.Timestamp(segs[i + 1][1]) - pd.DateOffset(months=1) if i + 1 < len(segs) else END
        x.loc[pd.Timestamp(s):e] = linked[b].loc[pd.Timestamp(s):e]
    out['old base last, base-year factor'] = x
    # overlap blend
    lx = np.log(linked['1993-94'].reindex(IDX))
    for pair, old, new, start, end in PAIRS:
        if pair == 'Pair 3':
            # Pair 3's overlap runs to the end of the data, so a blend would never complete:
            # switch to the new base at its first month instead (as in 'new base first').
            after = IDX[IDX >= pd.Timestamp(start)]
            lx.loc[after] = np.log(linked[new]).reindex(after)
            continue
        ov = pd.date_range(start, end, freq='MS')
        lam = pd.Series(np.linspace(0, 1, len(ov)), index=ov)
        lo, ln = np.log(linked[old]), np.log(linked[new])
        lx.loc[ov] = (1 - lam) * lo.reindex(ov) + lam * ln.reindex(ov)
        after = IDX[IDX > pd.Timestamp(end)]
        lx.loc[after] = ln.reindex(after)
    out['overlap blend'] = np.exp(lx)
    drift = {}
    for pair, o, n, s, e in PAIRS:
        last = pd.date_range(pd.Timestamp(e) - pd.DateOffset(months=11), pd.Timestamp(e), freq='MS')
        drift[pair] = (linked[o].reindex(last) / linked[n].reindex(last) - 1).mean() * 100
    return out, drift


rows = []
for S in SERIES:
    out, drift = build(S)
    for r, x in out.items():
        assert x.notna().all(), (S, r)
        a = x.groupby(x.index.map(fy)).mean()
        n = len(a) - 1
        rows.append(dict(series=S, rule=r, statistic='average annual growth 1994-95 to 2025-26 (%)',
                         value=((a.iloc[-1] / a.iloc[0]) ** (1 / n) - 1) * 100))
        y = (x / x.shift(12) - 1) * 100
        for lab, a0, a1 in [('2005-06 to 2010-11', '2005-04-01', '2011-03-01'), ('2012-13 to 2016-17', '2012-04-01', '2017-03-01'),
                            ('2017-18 to 2025-26', '2017-04-01', '2026-03-01')]:
            g = x.groupby(x.index.map(fy)).mean()
            ys = g.loc[fy(pd.Timestamp(a0)):fy(pd.Timestamp(a1))]
            prev = g.loc[:fy(pd.Timestamp(a0))].iloc[-2]
            rows.append(dict(series=S, rule=r, statistic=f'average annual growth {lab} (%)',
                             value=((ys.iloc[-1] / prev) ** (1 / len(ys)) - 1) * 100))
    for p, v in drift.items():
        rows.append(dict(series=S, rule='-', statistic=f'{p}: linked old-base level vs new base, last 12 overlap months (%)', value=v))
R = pd.DataFrame(rows)
R.round(3).to_csv(RESULTS / 'splice_rules_by_series.csv', index=False)
pd.set_option('display.width', 250)
print(R[R['statistic'].str.startswith('average annual growth 1994')].pivot_table(index='series', columns='rule', values='value').round(2).to_string())
print(R[R['rule'] == '-'].pivot_table(index='series', columns='statistic', values='value').round(1).to_string())
print(R[R['statistic'].str.contains('2012-13 to 2016-17')].pivot_table(index='series', columns='rule', values='value').round(2).to_string())
