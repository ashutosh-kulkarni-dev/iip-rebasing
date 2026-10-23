"""Stage 5 (M5): spliced General-index series, April 1994 to March 2026, 2022-23 = 100.

Older series are linked to the newer base by dividing by the linking factor (MoSPI's
geometric-mean method; validate.py V4). Two splice rules use the same official data:
  'new base first'  switch to each new base at its first published month
                    (Apr 2005, Apr 2012, Apr 2023)
  'old base last'   keep each old base until its last published month (switch Jul 2011 and
                    Apr 2017; the 2011-12 base runs to the end of the sample), linking each old
                    base at the switch point: the factor is the ratio of the two bases' geometric
                    means over the 12 months before the switch (MoSPI's method), so the series has no jump at the link
  'old base last, base-year factor'  the same switch dates, but linking with the base-year
                    factor (MoSPI's method) instead of re-linking at the switch, so the drift
                    accumulated over the overlap appears as a one-off jump at the switch
Writes:
  results/splice_series.csv      monthly linked index and YoY under each rule
  results/splice_summary.csv     long-run growth, GFC reading, and link-month distortion
"""
import numpy as np
import pandas as pd
from config import PAIRS, RESULTS, GFC_START, GFC_END, fy
from common import levels, yoy

S = 'General'
lv = {b: levels(b, base_year=False)[S] for b in ['1993-94', '2004-05', '2011-12', '2022-23']}

# linking factors (validate.py reproduces the official 2011-12 -> 2022-23 factor exactly)
LF = {}
for _, old, new, start, _e in PAIRS:
    by = lv[old].loc[pd.Timestamp(start) - pd.DateOffset(months=12):pd.Timestamp(start) - pd.DateOffset(months=1)]
    LF[(old, new)] = np.exp(np.log(by).mean()) / 100
chain = {'2022-23': 1.0}
chain['2011-12'] = LF[('2011-12', '2022-23')]
chain['2004-05'] = chain['2011-12'] * LF[('2004-05', '2011-12')]
chain['2003-04'] = None
chain['1993-94'] = chain['2004-05'] * LF[('1993-94', '2004-05')]
linked = {b: lv[b] / chain[b] for b in lv}  # every base in 2022-23 = 100 units

END = pd.Timestamp('2026-03-01')
idx = pd.date_range('1994-04-01', END, freq='MS')
OLD_LAST = [('1993-94', '1994-04-01'), ('2004-05', '2011-07-01'), ('2011-12', '2017-04-01')]
rules = {
    'new base first': [('1993-94', '1994-04-01'), ('2004-05', '2005-04-01'), ('2011-12', '2012-04-01'),
                       ('2022-23', '2023-04-01')],
    'old base last': OLD_LAST,
    'old base last, base-year factor': OLD_LAST,
}
# Linking at the switch point, working backwards from the latest segment.
linked_sw = {'2011-12': linked['2011-12']}
for old, newer, sw in [('2004-05', '2011-12', '2017-04-01'), ('1993-94', '2004-05', '2011-07-01')]:
    w0, w1 = pd.Timestamp(sw) - pd.DateOffset(months=12), pd.Timestamp(sw) - pd.DateOffset(months=1)
    f = np.exp(np.log(lv[old].loc[w0:w1]).mean() - np.log(linked_sw[newer].loc[w0:w1]).mean())  # geometric means, as MoSPI's official link
    linked_sw[old] = lv[old] / f
series = {}
switches = {}
for rule, segs in rules.items():
    src = linked_sw if rule == 'old base last' else linked
    out = pd.Series(np.nan, index=idx)
    for i, (b, s) in enumerate(segs):
        e = pd.Timestamp(segs[i + 1][1]) - pd.DateOffset(months=1) if i + 1 < len(segs) else END
        out.loc[pd.Timestamp(s):e] = src[b].loc[pd.Timestamp(s):e]
    assert out.notna().all(), rule
    series[rule] = out
    switches[rule] = [pd.Timestamp(s) for _, s in segs[1:]]

SP = pd.DataFrame({f'{r} index': v for r, v in series.items()})
for r in rules:
    SP[f'{r} yoy'] = yoy(SP[f'{r} index'])
SP.round(4).to_csv(RESULTS / 'splice_series.csv', index_label='date')

rows = []
for r, x in series.items():
    a = x.groupby(x.index.map(fy)).mean()
    n_years = len(a) - 1
    rows.append(dict(rule=r, statistic='Cumulative growth 1994-95 to 2025-26 (%)', value=(a.iloc[-1] / a.iloc[0] - 1) * 100))
    rows.append(dict(rule=r, statistic='Average annual growth 1994-95 to 2025-26 (%)',
                     value=((a.iloc[-1] / a.iloc[0]) ** (1 / n_years) - 1) * 100))
    y = yoy(x)
    rows.append(dict(rule=r, statistic='GFC in-window mean YoY growth (%)', value=y[GFC_START:GFC_END].mean()))
    # Distortion at link months: spliced YoY in the 12 months after each switch vs the
    # true YoY of the base that is in use after the switch (where it exists) and of the
    # base in use before it.
    for sw in switches[r]:
        win = pd.date_range(sw, periods=12, freq='MS')
        win = win[win <= END]
        before = [b for b, s in rules[r] if pd.Timestamp(s) < sw][-1]
        after = [b for b, s in rules[r] if pd.Timestamp(s) == sw][0]
        ya, yb = yoy(lv[after]).reindex(win), yoy(lv[before]).reindex(win)
        rows.append(dict(rule=r, statistic=f'Link {sw:%Y-%m}: mean |spliced YoY - old-base YoY| (pp)',
                         value=(y.reindex(win) - yb).abs().mean()))
        rows.append(dict(rule=r, statistic=f'Link {sw:%Y-%m}: mean |spliced YoY - new-base YoY| (pp)',
                         value=(y.reindex(win) - ya).abs().mean()))
for (o, n), v in LF.items():
    rows.append(dict(rule='-', statistic=f'Linking factor {o} -> {n}', value=v))
# Level drift: by the end of each overlap, how far the linked old base sits from the new
# base (both in 2022-23 = 100 units); mean of the overlap's last 12 months.
for pair, o, n, s, e in PAIRS:
    last = pd.date_range(pd.Timestamp(e) - pd.DateOffset(months=11), pd.Timestamp(e), freq='MS')
    drift = (linked[o].reindex(last) / linked[n].reindex(last) - 1).mean() * 100
    rows.append(dict(rule='-', statistic=f'{pair}: linked {o} level vs {n}, last 12 overlap months (%)', value=drift))
SUM = pd.DataFrame(rows)
SUM.round(4).to_csv(RESULTS / 'splice_summary.csv', index=False)
pd.set_option('display.width', 200)
print(SUM.round(3).to_string(index=False))
