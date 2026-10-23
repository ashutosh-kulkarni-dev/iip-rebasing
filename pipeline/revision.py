"""Stage 5c: the deflator revision inside the 2022-23 base.

On 29 June 2026 MoSPI re-issued the whole 2022-23 series with the Output PPI replacing
the WPI as deflator for value-reported item groups, together with updated source data and
a correction to the Electricity index. Basket, panel and weights did not change. Comparing
the superseded version (1 June 2026 release) with the revised one (eSankhyiki) shows how
far measured growth moves without any rebasing.

Writes results/deflator_revision.csv: annual growth in both versions and the change, by
series and fiscal year, plus the largest monthly index difference.
"""
import pandas as pd
from config import RESULTS
from common import levels, wide, annual_growth

e = annual_growth(levels('2022-23', 'esankhyiki'))
j = annual_growth(levels('2022-23', 'june2026'))
ei, ji = wide('2022-23', 'index', 'esankhyiki'), wide('2022-23', 'index', 'june2026')
rows = []
order = ['General', 'Mining', 'Manufacturing', 'Electricity & Gas Supply', 'Primary Goods', 'Capital Goods',
         'Intermediate Goods', 'Infrastructure/ Construction Goods', 'Consumer Durables', 'Consumer Non-durables']
for s in order:
    d = (ei[s] - ji[s]).dropna()
    for y in ['2023-24', '2024-25', '2025-26']:
        rows.append(dict(series=s, fiscal_year=y, growth_june1=j.loc[y, s], growth_revised=e.loc[y, s],
                         change_pp=e.loc[y, s] - j.loc[y, s],
                         max_abs_monthly_index_diff=d.abs().max(), months_compared=len(d)))
R = pd.DataFrame(rows)
R.round(3).to_csv(RESULTS / 'deflator_revision.csv', index=False)
print(R.pivot_table(index='series', columns='fiscal_year', values='change_pp').round(2).to_string())
print(R.groupby('series')['max_abs_monthly_index_diff'].first().round(1).to_string())
