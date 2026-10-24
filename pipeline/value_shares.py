"""Stage 1b: inputs for the exploratory deflation-channel tests (H6).

1. Value-reported weight shares from the 2011-12 item list (MoSPI release of 12 May 2017,
   Appendix I, 407 item groups; data/official/mospi2017_item_list_2011-12.csv). An item group
   is value-reported when its accounting unit is 'Rs. Crore' or 'Rs. Lakhs'. Share = weight of
   value-reported item groups / total weight, by NIC-2008 division (first two digits of the
   5-digit code) and by use-based category. Check: division weights and item counts must
   reproduce Table B.2 of the 1 June 2026 release (data/official/industry_weights_...csv).
2. Industry annual indices in the superseded 1 June 2026 vintage of the 2022-23 series
   (Statement II A of the release: cumulative Apr-Mar index 2024-25 and 2025-26, growth 2025-26),
   compared with the revised (29 June 2026, eSankhyiki) vintage.
3. NIC concordance check for the 23 manufacturing divisions (2011-12: NIC-2008; 2022-23:
   NIC-2025): Table B.2 pairs the divisions one-to-one by code 10-32; the check confirms that each
   eSankhyiki industry name maps to one code in both bases.
Writes results/value_shares_2011-12.csv, results/industry_vintage_revision.csv,
       data/official/mospi2026jun01_industry_annual.csv
"""
import re
import numpy as np
import pandas as pd
from config import RAW, OFFICIAL, RESULTS, CLEAN, fy

IT = pd.read_csv(OFFICIAL / 'mospi2017_item_list_2011-12.csv', dtype={'nic5': str})
IT['nic2'] = IT['nic5'].str[:2]
assert len(IT) == 407 and IT['value_reported'].sum() == 109
W = pd.read_csv(OFFICIAL / 'industry_weights_2011-12_2022-23.csv', dtype=str)
W = W[W['nic'].str.fullmatch(r'\d\d') & W['nic'].between('10', '32')].copy()
W['w_2011'] = W['w_2011'].astype(float)
W['n_2011'] = W['n_2011'].astype(int)

g = IT.groupby('nic2').apply(lambda x: pd.Series(dict(
    weight=x['weight'].sum(), items=len(x), value_items=int(x['value_reported'].sum()),
    value_weight=x.loc[x['value_reported'], 'weight'].sum())), include_groups=False)
g['value_share'] = g['value_weight'] / g['weight']
chk = g.join(W.set_index('nic')[['description', 'w_2011', 'n_2011']], how='inner')
assert (chk['items'] == chk['n_2011']).all(), 'item counts differ from Table B.2'
assert (chk['weight'] - chk['w_2011']).abs().max() < 0.001, 'division weights differ from Table B.2'

# map eSankhyiki industry names to NIC divisions
I = pd.read_csv(CLEAN / 'industry_monthly.csv', parse_dates=['date'])
names = sorted(I['industry'].unique())


def norm(s):
    return re.sub(r'[^a-z]', '', s.lower().replace('pharmaceuticals', 'pharmaceutical'))


nm = {norm(d): k for k, d in W.set_index('nic')['description'].items()}
MAP = {}
for n in names:
    k = nm.get(norm(n))
    if k is None:  # fall back on the longest common prefix
        k = max(nm, key=lambda z: len(__import__('os').path.commonprefix([z, norm(n)])))
        k = nm[k]
    MAP[n] = k
assert len(set(MAP.values())) == 23, 'industry names do not map one-to-one to NIC divisions'
present = I.groupby('industry')['base_year'].nunique()
assert (present == 2).all(), 'an industry is missing in one base'

out = chk.copy()
out['industry'] = out.index.map({v: k for k, v in MAP.items()})
out['nic_concordance'] = 'one-to-one by code in Table B.2 (NIC-2008 and NIC-2025 divisions 10-32); content changes within a division not checked'
use = IT.groupby('use_based').apply(lambda x: pd.Series(dict(
    weight=x['weight'].sum(), value_share=x.loc[x['value_reported'], 'weight'].sum() / x['weight'].sum())), include_groups=False)
out.reset_index(names='nic2').to_csv(RESULTS / 'value_shares_2011-12.csv', index=False)
use.to_csv(RESULTS / 'value_shares_2011-12_by_use.csv')

# 1 June vintage industry annual indices (Statement II A) -------------------------------------
s = open(RAW / 'mospi_iip_2022-23_first_release_2026-06-01.html', encoding='utf-8', errors='ignore').read()
t = re.sub(r'\s+', ' ', re.sub('<[^>]+>', ' ', s)).replace('&amp;', '&')
a = t.index('STATEMENT II A')
seg = t[a:t.index('STATEMENT', a + 20)]
rows = re.findall(r'\b(1\d|2\d|3[0-2])\s+((?:Manufacture|Other|Printing)[^0-9]+?)\s+(\d+\.\d{3})\s+(-?\d+\.\d)\s+(-?\d+\.\d)'
                  r'\s+(-?\d+\.\d)\s+(-?\d+\.\d)\s+(-?\d+\.\d)\s+(-?\d+\.\d)', seg)
J = pd.DataFrame(rows, columns=['nic2', 'description', 'weight', 'index_apr25', 'index_apr26', 'cum_index_2024_25',
                                'cum_index_2025_26', 'growth_apr26', 'growth_2025_26'])
assert len(J) == 23
for c in J.columns[2:]:
    J[c] = J[c].astype(float)
J['source'] = 'MoSPI first release, 1 June 2026, Statement II A'
J.to_csv(OFFICIAL / 'mospi2026jun01_industry_annual.csv', index=False)

# revised vintage: annual means of the eSankhyiki 2022-23 industry indices
R = I[I['base_year'] == '2022-23'].copy()
R['fy'] = R['date'].map(fy)
A = R.groupby(['industry', 'fy'])['index'].agg(['mean', 'count']).reset_index()
A = A[A['count'] == 12].pivot(index='industry', columns='fy', values='mean')
A['nic2'] = A.index.map(MAP)
A = A.set_index('nic2')
V = J.set_index('nic2').join(A[['2024-25', '2025-26']].rename(columns=lambda c: 'rev_' + c))
V['rev_growth_2025_26'] = (V['rev_2025-26'] / V['rev_2024-25'] - 1) * 100
V['jun_growth_2025_26_from_index'] = (V['cum_index_2025_26'] / V['cum_index_2024_25'] - 1) * 100
V['abs_change_growth_2025_26'] = (V['rev_growth_2025_26'] - V['growth_2025_26']).abs()
V['abs_change_log_index_2024_25'] = (np.log(V['rev_2024-25']) - np.log(V['cum_index_2024_25'])).abs() * 100
V = V.join(g[['value_share']])
V.round(4).to_csv(RESULTS / 'industry_vintage_revision.csv')
pd.set_option('display.width', 220)
print(out[['description', 'weight', 'items', 'value_items', 'value_share']].round(3).to_string())
print(use.round(3))
print(V[['description', 'growth_2025_26', 'rev_growth_2025_26', 'abs_change_growth_2025_26', 'abs_change_log_index_2024_25', 'value_share']].round(2).to_string())
