"""Stage 7b: the single-source contrast of Section 6.1 at other window lengths.

Contrast = mean log R of electricity and mining minus mean log R of the five
manufacturing-based units (manufacturing and the four use-based categories),
computed from the window-sensitivity ratios that tests.py writes to results/tests.csv
(rows with id 'R-window'); tests.py also prints the same contrasts in the note of its
'H1a group contrast with N-month windows' rows. Point estimates only.
Writes results/window_contrast.csv.
"""
import math
import pandas as pd
from config import RESULTS

STABLE = ['Electricity', 'Mining']
MFG = ['Manufacturing', 'Capital Goods', 'Intermediate Goods', 'Consumer Durables', 'Consumer Non-durables']

T = pd.read_csv(RESULTS / 'tests.csv')
W = T[(T['id'] == 'R-window') & T['item'].str.startswith('R with ')].copy()
W['window'] = W['item'].str.extract(r'R with (\d+)-month windows')[0].astype(int)
W['unit'] = W['item'].str.split(': ').str[1]
rows = []
for (pair, win), g in W.groupby(['pair', 'window']):
    r = g.set_index('unit')['estimate']
    if not set(STABLE + MFG) <= set(r.index):
        continue
    stable = sum(math.log(r[u]) for u in STABLE) / len(STABLE)
    mfg = sum(math.log(r[u]) for u in MFG) / len(MFG)
    rows.append(dict(pair=pair, window=win, mean_log_R_stable=stable, mean_log_R_mfg=mfg,
                     contrast=stable - mfg))
out = pd.DataFrame(rows).sort_values(['pair', 'window'])
out.to_csv(RESULTS / 'window_contrast.csv', index=False)
print(out.round(3).to_string(index=False))
