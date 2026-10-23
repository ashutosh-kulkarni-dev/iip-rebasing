"""Stage 5b (outside benchmark): ASI real output growth vs IIP manufacturing growth.

Benchmark = growth of ASI value of output (all-India, current prices) deflated by the WPI
'Manufactured Products' annual average. WPI base 2004-05 is used for fiscal years up to
2011-12 and base 2011-12 from 2012-13 (each growth rate uses one base only). The base-year
annual average is 100 by definition (2004-05 on the 2004-05 base).

Caveats carried into the paper: ASI covers registered factories only; its output includes
a small non-manufacturing share; gross output is deflated by a single price index; ASI
changed its treatment of non-operating units in 2010-11 (a robustness row drops that year).

Writes:
  results/asi_benchmark.csv          per fiscal year: ASI nominal, deflator, real growth, IIP
                                     manufacturing growth in the old and the new base
  results/asi_benchmark_summary.csv  per pair: mean growth and mean absolute gap to ASI
"""
import numpy as np
import pandas as pd
from config import OFFICIAL, RESULTS, PAIRS

a = pd.read_csv(OFFICIAL / 'asi_output.csv')
a = a[a['fiscal_year'].str.fullmatch(r'\d{4}-\d{2}')].dropna(subset=['value_of_output_rs_lakh'])
asi = a.set_index('fiscal_year')['value_of_output_rs_lakh'].astype(float)
w = pd.read_csv(OFFICIAL / 'wpi_manufactured.csv')
w04 = w[w['base'] == '2004-05=100'].set_index('fiscal_year')['annual_avg_index'].astype(float)
w04.loc['2004-05'] = 100.0
w11 = w[w['base'] == '2011-12=100'].set_index('fiscal_year')['annual_avg_index'].astype(float)


def prev(y):
    s = int(y[:4]) - 1
    return f'{s}-{str(s + 1)[-2:]}'


ann = pd.read_csv(RESULTS / 'overlap_annual.csv')
ann = ann[(ann['series'] == 'Manufacturing') & (ann['data_version'] == 'esankhyiki')]
rows = []
for pair, old, new, start, end in PAIRS:
    for _, r in ann[ann['pair'] == pair].iterrows():
        y = r['fiscal_year']
        if pd.isna(r['old']) or y not in asi.index or prev(y) not in asi.index:
            continue
        defl = w04 if int(y[:4]) <= 2011 else w11
        nom = asi[y] / asi[prev(y)] - 1
        p = defl[y] / defl[prev(y)] - 1
        real = ((1 + nom) / (1 + p) - 1) * 100
        rows.append(dict(pair=pair, fiscal_year=y, asi_nominal_growth=nom * 100, wpi_mfg_inflation=p * 100,
                         asi_real_growth=real, iip_old=r['old'], iip_new=r['new'],
                         abs_gap_old=abs(r['old'] - real), abs_gap_new=abs(r['new'] - real),
                         closer='new' if abs(r['new'] - real) < abs(r['old'] - real) else 'old'))
B = pd.DataFrame(rows)
B.round(3).to_csv(RESULTS / 'asi_benchmark.csv', index=False)

srows = []
for label, sub in [('all years', B), ('excl. 2010-11 (ASI method change)', B[B['fiscal_year'] != '2010-11'])]:
    for pair, g in sub.groupby('pair'):
        srows.append(dict(sample=label, pair=pair, years=len(g), first=g['fiscal_year'].min(),
                          last=g['fiscal_year'].max(),
                          mean_asi_real=g['asi_real_growth'].mean(), mean_iip_old=g['iip_old'].mean(),
                          mean_iip_new=g['iip_new'].mean(),
                          mean_gap_old=g['iip_old'].mean() - g['asi_real_growth'].mean(),
                          mean_gap_new=g['iip_new'].mean() - g['asi_real_growth'].mean(),
                          mae_old=g['abs_gap_old'].mean(), mae_new=g['abs_gap_new'].mean(),
                          years_new_closer=int((g['closer'] == 'new').sum()),
                          corr_old=np.corrcoef(g['iip_old'], g['asi_real_growth'])[0, 1] if len(g) > 2 else np.nan,
                          corr_new=np.corrcoef(g['iip_new'], g['asi_real_growth'])[0, 1] if len(g) > 2 else np.nan))
S = pd.DataFrame(srows)
S.round(3).to_csv(RESULTS / 'asi_benchmark_summary.csv', index=False)
pd.set_option('display.width', 220)
print(B.round(1).to_string(index=False))
print(S.round(2).to_string(index=False))
