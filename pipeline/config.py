"""Shared configuration: bases, overlaps, weights, windows, paths.

Every constant that enters a reported number is defined here once, with its source.
Run all scripts from the repository root.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data' / 'raw'
CLEAN = ROOT / 'data' / 'clean'
OFFICIAL = ROOT / 'data' / 'official'
RESULTS = ROOT / 'results'
CHARTS = ROOT / 'charts'

BASES = ['1993-94', '2004-05', '2011-12', '2022-23']

# Series compared in every pair. For 2022-23, "Electricity" is the Electricity sub-index
# (NIC 351), not "Electricity & Gas Supply", so the gas supply added in 2022-23 does not
# enter the comparison.
SECTORS = ['Mining', 'Manufacturing', 'Electricity']
USE4 = ['Capital Goods', 'Intermediate Goods', 'Consumer Durables', 'Consumer Non-durables']
SERIES = ['General'] + SECTORS + USE4

# Consecutive-base overlaps: (label, old base, new base, first month, last month).
# Each overlap starts at the first month published in the new base and ends at the last
# month published in the old base (or the last month of the data for pair 3).
PAIRS = [
    ('Pair 1', '1993-94', '2004-05', '2005-04-01', '2011-06-01'),
    ('Pair 2', '2004-05', '2011-12', '2012-04-01', '2017-03-01'),
    ('Pair 3', '2011-12', '2022-23', '2023-04-01', '2026-03-01'),
]

# Use-based weights (% of the General index) for the four categories common to all bases.
#  1993-94, 2004-05: CSO/MoSPI (2011), "Revision of base year to 2004-05: an overview"
#                    (stored per 1000 in the v5 weights file; converted to % here).
#  2011-12, 2022-23: MoSPI first release of the 2022-23 series, 1 June 2026, use-based
#                    comparison table (weights column), identical to Statement III.
USE_WEIGHTS = {
    '1993-94': {'Capital Goods': 9.257, 'Intermediate Goods': 26.514,
                'Consumer Durables': 5.365, 'Consumer Non-durables': 23.299},
    '2004-05': {'Capital Goods': 8.825, 'Intermediate Goods': 15.686,
                'Consumer Durables': 8.460, 'Consumer Non-durables': 21.347},
    '2011-12': {'Capital Goods': 8.224, 'Intermediate Goods': 17.221,
                'Consumer Durables': 12.839, 'Consumer Non-durables': 15.329},
    '2022-23': {'Capital Goods': 8.082, 'Intermediate Goods': 22.416,
                'Consumer Durables': 11.311, 'Consumer Non-durables': 16.147},
}
# Categories outside the common four (for Table I only).
OTHER_USE_WEIGHTS = {
    '2011-12': {'Primary Goods': 34.049, 'Infrastructure/ Construction Goods': 12.338},
    '2022-23': {'Primary Goods': 31.136, 'Infrastructure/ Construction Goods': 10.908},
}
# Sectoral weights (%). 1993-94 is not used in any computation and is not listed.
#  2004-05: MoSPI press release, 12 May 2017, Statement III.
#  2011-12, 2022-23: MoSPI first release, 1 June 2026, Table B.1 (Electricity for 2022-23
#  is the NIC 351 sub-index weight from Table B.2; Electricity & Gas = 10.865).
SECTOR_WEIGHTS = {
    # 1993-94: RBI Handbook of Statistics on Indian Economy / RBI Bulletin Table 28 (official
    # CSO weights, two decimals). Verified 18 Oct 2026; replaces the regression-recovered values
    # 10.473 / 79.358 / 10.169 used in the first revision run.
    '1993-94': {'Mining': 10.47, 'Manufacturing': 79.36, 'Electricity': 10.17},
    '2004-05': {'Mining': 14.157, 'Manufacturing': 75.527, 'Electricity': 10.316},
    '2011-12': {'Mining': 14.373, 'Manufacturing': 77.633, 'Electricity': 7.994},  # MoSPI 12 May 2017 (Appendix I: 14.3725 / 7.9943)
    '2022-23': {'Mining': 11.053, 'Manufacturing': 76.062, 'Electricity': 10.171,
                'Electricity & Gas Supply': 10.865,
                'Water Supply, Sewerage & Waste Management': 2.020},
}

# Official linking factor, 2011-12 -> 2022-23 (MoSPI, "Linking Factor for IIP", 2026).
OFFICIAL_LINKING = {'General': 1.3834, 'Mining': 1.1890, 'Manufacturing': 1.3700,
                    'Electricity': 1.8495}

# Official CSO linking factor, 1993-94 -> 2004-05, computed by CSO with an arithmetic
# method (CSO/MoSPI 2011, base revision note). Reported for comparison only.
CSO2011_LINKING = {'General': 2.111, 'Manufacturing': 2.225}

# GFC window and pre-crisis anchor (unchanged from v5).
GFC_START, GFC_END = '2008-09-01', '2010-03-01'
GFC_ANCHOR = ('2007-09-01', '2008-08-01')

# Validation tolerance against official published annual growth (percentage points).
# Published monthly indices are rounded to 0.1, so each annual mean we compute can be off
# by up to 0.05 index points (about 0.05% of an index near 100); the growth rate between
# two such means can therefore be off by about 0.1 pp, and the official figure itself is
# rounded to 0.1 (a further 0.05 pp). A correct reproduction differs by at most ~0.15 pp.
TOL_PP = 0.15 + 1e-9

MONTHS = {m: i + 1 for i, m in enumerate(
    ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August',
     'September', 'October', 'November', 'December'])}


def fy(ts):
    """April-March fiscal year label for a timestamp, e.g. 2008-09."""
    y = ts.year if ts.month >= 4 else ts.year - 1
    return f'{y}-{str(y + 1)[-2:]}'
