"""Stage 5d: three episodes, each measured in two official bases and in two spliced series.

Episodes and windows are fixed in advance:
  GFC            1993-94 vs 2004-05 base. Crisis window Sep 2008 - Mar 2010; 'before' = the 24
                 months before it (Sep 2006 - Aug 2008).
  2012-14        2004-05 vs 2011-12 base. Annual April-March growth in 2012-13 and 2013-14
                 (monthly growth in the 2011-12 base is not a true growth rate until April 2013).
  Demonetisation 2004-05 vs 2011-12 base. 'Before' = Apr - Oct 2016, 'after' = Nov 2016 - Mar 2017
                 (robustness: before = Jul - Oct 2016).
For each, the same statistic is computed from the two spliced series of splice.py.

Writes results/episodes.csv (one row per episode x statistic x series x source).
"""
import pandas as pd
from config import RESULTS
from common import true_yoy, levels, annual_growth, yoy

SP = pd.read_csv(RESULTS / 'splice_series.csv', parse_dates=['date']).set_index('date')
sp_yoy = {'spliced: new base first': SP['new base first yoy'], 'spliced: old base last': SP['old base last yoy']}
sp_lvl = {'spliced: new base first': SP['new base first index'], 'spliced: old base last': SP['old base last index']}
rows = []


def add(episode, stat, series, source, value):
    rows.append(dict(episode=episode, statistic=stat, series=series, source=source, value=value))


# GFC ---------------------------------------------------------------------------------------
W = [('crisis window (Sep 2008 - Mar 2010)', '2008-09-01', '2010-03-01'),
     ('24 months before (Sep 2006 - Aug 2008)', '2006-09-01', '2008-08-01')]
for base in ['1993-94', '2004-05']:
    y = true_yoy(base)
    for s in ['General', 'Manufacturing']:
        for lab, a, b in W:
            add('GFC', f'mean YoY growth, {lab}', s, f'{base} base', y[s][a:b].mean())
for src, y in sp_yoy.items():
    for lab, a, b in W:
        add('GFC', f'mean YoY growth, {lab}', 'General', src, y[a:b].mean())

# 2012-14 slowdown --------------------------------------------------------------------------
for base in ['2004-05', '2011-12']:
    ag = annual_growth(levels(base))
    for s in ['General', 'Manufacturing']:
        for fy in ['2012-13', '2013-14']:
            add('2012-14 slowdown', f'annual growth {fy}', s, f'{base} base', ag.loc[fy, s])
for src, lv in sp_lvl.items():
    a = lv.groupby(lv.index.map(lambda t: f'{t.year if t.month >= 4 else t.year - 1}')).mean()
    for fy in ['2012-13', '2013-14']:
        y0 = int(fy[:4])
        add('2012-14 slowdown', f'annual growth {fy}', 'General', src, (a[str(y0)] / a[str(y0 - 1)] - 1) * 100)

# Demonetisation ----------------------------------------------------------------------------
D = [('before (Apr - Oct 2016)', '2016-04-01', '2016-10-01'),
     ('before, short (Jul - Oct 2016)', '2016-07-01', '2016-10-01'),
     ('after (Nov 2016 - Mar 2017)', '2016-11-01', '2017-03-01')]
for base in ['2004-05', '2011-12']:
    y = true_yoy(base)
    for s in ['General', 'Manufacturing']:
        for lab, a, b in D:
            add('Demonetisation', f'mean YoY growth, {lab}', s, f'{base} base', y[s][a:b].mean())
        ag = annual_growth(levels(base))
        add('Demonetisation', 'annual growth 2016-17', s, f'{base} base', ag.loc['2016-17', s])
for src, y in sp_yoy.items():
    for lab, a, b in D:
        add('Demonetisation', f'mean YoY growth, {lab}', 'General', src, y[a:b].mean())

E = pd.DataFrame(rows)
E.round(3).to_csv(RESULTS / 'episodes.csv', index=False)
pd.set_option('display.width', 200)
print(E.pivot_table(index=['episode', 'statistic', 'series'], columns='source', values='value').round(1).to_string())

# ---------------------------------------------------------------------------------------
# Where each disagreement comes from: one statistic per episode, by sector and use-based
# category (categories with the same name in both bases; definitions changed somewhat in 2017).
CATS = ['Mining', 'Manufacturing', 'Electricity', 'Capital Goods', 'Intermediate Goods',
        'Consumer Durables', 'Consumer Non-durables']
crow = []
for ep, (old, new) in [('GFC', ('1993-94', '2004-05')), ('2012-14 slowdown', ('2004-05', '2011-12')),
                       ('Demonetisation', ('2004-05', '2011-12'))]:
    for base in (old, new):
        y = true_yoy(base)
        ag = annual_growth(levels(base))
        for c in ['General'] + CATS:
            if ep == 'GFC':
                v = y[c]['2008-09-01':'2010-03-01'].mean() - y[c]['2006-09-01':'2008-08-01'].mean()
                stat = 'change in mean YoY growth, crisis window minus 24 months before'
            elif ep == '2012-14 slowdown':
                v = ag.loc[['2012-13', '2013-14'], c].mean()
                stat = 'average annual growth 2012-13 and 2013-14'
            else:
                v = y[c]['2016-11-01':'2017-03-01'].mean() - y[c]['2016-04-01':'2016-10-01'].mean()
                stat = 'change in mean YoY growth, Nov 2016-Mar 2017 minus Apr-Oct 2016'
            crow.append(dict(episode=ep, statistic=stat, series=c, base=base,
                             role='older' if base == old else 'newer', value=v))
C = pd.DataFrame(crow)
C.round(3).to_csv(RESULTS / 'episodes_by_category.csv', index=False)
print(C.pivot_table(index='series', columns=['episode', 'role'], values='value').round(1).to_string())

# Outside benchmark for the episode years: ASI real output vs IIP manufacturing ----------------
A = pd.read_csv(RESULTS / 'asi_benchmark.csv')
A = A[A['fiscal_year'].isin(['2008-09', '2009-10', '2012-13', '2013-14', '2016-17'])]
A.round(3).to_csv(RESULTS / 'episodes_asi.csv', index=False)
print(A[['fiscal_year', 'asi_real_growth', 'iip_old', 'iip_new', 'closer']].round(1).to_string(index=False))

# A case where the bases agree: 2011-12 vs 2022-23 -----------------------------------------
S = pd.read_csv(RESULTS / 'overlap_stats.csv')
S = S[(S['pair'] == 'Pair 3') & (S['data_version'] == 'esankhyiki') & (S['series'] == 'General')
      & (S['sample'].str.startswith('true'))]
S.round(3).to_csv(RESULTS / 'agreement_pair3.csv', index=False)

# The first-year trap: published first-year growth = index - 100 (one worked example) -------
M = pd.read_csv(RESULTS.parent / 'data' / 'clean' / 'iip_monthly.csv', parse_dates=['date'])
ex = M[(M['base_year'] == '2011-12') & (M['series'] == 'General')].sort_values('date').head(12)
ex = ex.assign(index_minus_100=ex['index'] - 100)
ex.round(2).to_csv(RESULTS / 'first_year_example.csv', index=False)
print(ex[['date', 'index', 'growth_rate', 'index_minus_100']].to_string(index=False))
