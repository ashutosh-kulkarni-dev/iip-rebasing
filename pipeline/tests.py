"""Stage 7: the pre-specified tests and bounds of tests_spec.md (written before this file).

Runs 8 confirmatory tests (H1a, H1b, H2, H3a, H3d, H4d, H5a, H5b), 5 reported bounds (H3b, H3c,
H4a, H4b, H4c), 2 exploratory tests (H6a, H6b) and exploratory Pair 3 replications.
Writes results/tests.csv (one row per reported quantity) and results/tests_h2_tiers.csv.
Every definition is in tests_spec.md; comments here only point to it.
Implementation details not fixed in the spec: bootstrap seeds are 20261018 + pair number, plus
+100 for block-6 draws, +200 for H3b/H3c, +300 for H4 and +10 for the 1 June vintage, so every
stream is independent. Pair 3 (T = 24) uses mean block 6 for the month-level H4 bootstraps.
H3d: shifts that leave no qualifying date are dropped from the null.
"""
import itertools
import numpy as np
import pandas as pd
from scipy.stats import spearmanr, t as tdist
from config import PAIRS, RESULTS, USE_WEIGHTS
from common import unit_pairs, window_change, levels, USE_UNITS
from harinf import (stationary_matrix, holm, stouffer, ewc, fixed_b_nw, fixed_b_pvalue, SEED)

B = 9999
U8 = ['General', 'Mining', 'Manufacturing', 'Electricity', 'Capital Goods', 'Intermediate Goods',
      'Consumer Durables', 'Consumer Non-durables']
MFG5 = ['Manufacturing', 'Capital Goods', 'Intermediate Goods', 'Consumer Durables', 'Consumer Non-durables']
STABLE = ['Electricity', 'Mining']
SECT3 = ['Mining', 'Manufacturing', 'Electricity']
PAIRNO = {'Pair 1': 1, 'Pair 2': 2, 'Pair 3': 3}
ROWS = []


def row(**k):
    ROWS.append(k)


# ------------------------------------------------------------------ data
def change_arrays(old, new, start, end, version):
    U = unit_pairs(old, new, start, end, version)
    units = [u for u in U8 if u in U]
    CO, CN = {}, {}
    for u in units:
        d = U[u][1].asfreq('MS')
        CO[u], CN[u] = window_change(d['old'], 6), window_change(d['new'], 6)
    CO, CN = pd.DataFrame(CO), pd.DataFrame(CN)
    return units, CO, CN, {u: U[u][1] for u in units}


def R_of(co, cn):
    """6-month change ratio for each column; co, cn: (..., n, units) arrays (last two axes)."""
    dis = np.median(np.abs(cn - co), axis=-2)
    return dis / np.maximum(np.median(np.abs(co), axis=-2), np.median(np.abs(cn), axis=-2))


def boot_R(co, cn, block, seed):
    idx = stationary_matrix(len(co), block, B, seed)
    out = np.empty((B, co.shape[1]))
    for s in range(0, B, 500):  # chunks to bound memory
        ii = idx[s:s + 500]
        out[s:s + 500] = R_of(co[ii], cn[ii])
    return out


def contrib(base, version='esankhyiki'):
    lv = levels(base, version if base == '2022-23' else 'esankhyiki', base_year=False)
    g12 = lv['General'].shift(12)
    G = (lv['General'] / g12 - 1) * 100
    C = pd.DataFrame({c: USE_WEIGHTS[base][c] * (lv[c] - lv[c].shift(12)) / g12 for c in USE_UNITS})
    C['Other'] = G - C.sum(axis=1)
    C['General'] = G
    return C


def change_contrib(C, idx):
    C = C.loc[idx]
    out = {}
    for i in range(6, len(C) - 6 + 1):
        out[C.index[i]] = C.iloc[i:i + 6].mean() - C.iloc[i - 6:i].mean()
    return pd.DataFrame(out).T


def p_one(draws, null_side):
    """One-sided bootstrap p: share of draws on the null side (>= 0 or <= 0), (1+count)/(B+1)."""
    draws = np.asarray(draws)
    cnt = (draws >= 0).sum() if null_side == 'ge' else (draws <= 0).sum()
    return (1 + cnt) / (1 + len(draws))


DATA = {}
for pair, old, new, start, end in PAIRS:
    for ver in (['esankhyiki', 'june2026'] if new == '2022-23' else ['esankhyiki']):
        units, CO, CN, LV = change_arrays(old, new, start, end, ver)
        Co, Cn = contrib(old), contrib(new, ver)
        months = LV['General'].index
        cco, ccn = change_contrib(Co, months), change_contrib(Cn, months)
        DATA[(pair, ver)] = dict(units=units, CO=CO, CN=CN, LV=LV, Co=Co.loc[months], Cn=Cn.loc[months],
                                 cco=cco, ccn=ccn, T=len(months), old=old, new=new)
CONF = [('Pair 1', 'esankhyiki'), ('Pair 2', 'esankhyiki')]
EXPL = [('Pair 3', 'esankhyiki'), ('Pair 3', 'june2026')]
W = {p: np.sqrt(DATA[(p, 'esankhyiki')]['T'] / 12) for p in ('Pair 1', 'Pair 2')}

# ------------------------------------------------------------------ H1a, H2 (and P3 replications)
RB = {}
for key in CONF + EXPL:
    D = DATA[key]
    co, cn = D['CO'][D['units']].values, D['CN'][D['units']].values
    for blk in (12, 6):
        RB[key + (blk,)] = boot_R(co, cn, blk, SEED + PAIRNO[key[0]] + (100 if blk == 6 else 0) + (10 if key[1] == 'june2026' else 0))
    D['R'] = pd.Series(R_of(co, cn), index=D['units'])


def contrast(R, units, a, b):
    ia = [units.index(u) for u in a if u in units]
    ib = [units.index(u) for u in b if u in units]
    return np.log(R[..., ia]).mean(axis=-1) - np.log(R[..., ib]).mean(axis=-1)


h1 = {}
for blk in (12, 6):
    for name, a, b in [('H1a group contrast', STABLE, MFG5), ('H1a Electricity vs Manufacturing', ['Electricity'], ['Manufacturing']),
                       ('H1a Mining vs Manufacturing', ['Mining'], ['Manufacturing'])]:
        ps = {}
        for key in CONF + EXPL:
            D = DATA[key]
            if not all(u in D['units'] for u in a + b):
                continue
            est = float(contrast(D['R'].values, D['units'], a, b))
            dr = contrast(RB[key + (blk,)], D['units'], a, b)
            p = p_one(dr, 'ge')
            lo, hi = np.quantile(dr, [0.025, 0.975])
            ps[key] = (p, est)
            row(id='H1a', type='test' if key in CONF else 'exploratory', item=name, pair=key[0], version=key[1], block=blk,
                estimate=est, lo=lo, hi=hi, p=p, n=len(D['CO']), expected_blocks=len(D['CO']) / blk, B=B,
                boot_median=float(np.median(dr)), note='log ratio; negative = stable-source units more reliable')
        pp, z = stouffer([ps[k][0] for k in CONF], [W['Pair 1'], W['Pair 2']])
        h1[(name, blk)] = pp
        same_sign = all(ps[k][1] < 0 for k in CONF)
        row(id='H1a', type='test' if blk == 12 else 'sensitivity', item=name, pair='Pooled P1+P2', version='esankhyiki', block=blk, p=pp, estimate=z,
            note=f'Stouffer Z; negative contrast in both pairs: {same_sign}')
for blk in (12, 6):
    adj = holm([h1[('H1a Electricity vs Manufacturing', blk)], h1[('H1a Mining vs Manufacturing', blk)]])
    for nm, a in zip(['H1a Electricity vs Manufacturing', 'H1a Mining vs Manufacturing'], adj):
        for r in ROWS:
            if r['id'] == 'H1a' and r['item'] == nm and r['pair'] == 'Pooled P1+P2' and r['block'] == blk:
                r['p_adj'] = a
for r in ROWS:
    if r['id'] == 'H1a' and r['item'] == 'H1a group contrast' and r['pair'] == 'Pooled P1+P2':
        neg = 'True' in r['note']
        r['decision'] = 'PASS' if (r['p'] < 0.05 and neg) else 'FAIL'

# H1b
r1, r2 = DATA[('Pair 1', 'esankhyiki')]['R'], DATA[('Pair 2', 'esankhyiki')]['R']
u7 = [u for u in U8 if u != 'General']
x, y = r1[u7].rank().values, r2[u7].rank().values
rho = spearmanr(x, y).statistic
perm = np.array([spearmanr(x, np.array(pp)).statistic for pp in itertools.permutations(y)])
p = (perm >= rho - 1e-12).mean()
row(id='H1b', type='test', item='Spearman rho of R ranks, P1 vs P2 (7 units)', pair='P1 vs P2', estimate=rho, p=p, n=7,
    note=f'exact permutation over {len(perm)} orderings; ranks P1 {dict(zip(u7, x))}; P2 {dict(zip(u7, y))}',
    decision='PASS' if p < 0.05 else 'FAIL')

# H2
tiers = []
for key in CONF + EXPL:
    D = DATA[key]
    res = {}
    for blk in (12, 6):
        lr = np.log(RB[key + (blk,)])
        pr = np.array([p_one(lr[:, i], 'ge') for i in range(len(D['units']))])
        pu = np.array([p_one(lr[:, i], 'le') for i in range(len(D['units']))])
        conf = key in CONF
        res[blk] = (pr, pu, holm(pr) if conf else pr, holm(pu) if conf else pu,
                    np.quantile(np.exp(lr), 0.025, axis=0), np.quantile(np.exp(lr), 0.975, axis=0))
    for i, u in enumerate(D['units']):
        read = all(res[b][2][i] < 0.05 for b in (12, 6))
        unread = all(res[b][3][i] < 0.05 for b in (12, 6))
        tier = 'readable' if read else ('unreadable' if unread else 'undetermined')
        tiers.append(dict(pair=key[0], version=key[1], unit=u, R=D['R'][u], lo=min(res[b][4][i] for b in (12, 6)),
                          hi=max(res[b][5][i] for b in (12, 6)), p_read_b12=res[12][0][i], p_read_adj_b12=res[12][2][i],
                          p_read_adj_b6=res[6][2][i], p_unread_b12=res[12][1][i], p_unread_adj_b12=res[12][3][i],
                          p_unread_adj_b6=res[6][3][i], tier=tier + ('' if key in CONF else ' (exploratory, unadjusted)')))
T2 = pd.DataFrame(tiers)
# pooled tiers
pool = []
for blk in (12, 6):
    pr, pu = [], []
    for u in U8:
        a = T2[(T2['unit'] == u) & T2['pair'].isin(['Pair 1', 'Pair 2'])].set_index('pair')
        # recompute unadjusted p at this block for pooling
        prs, pus = [], []
        for k in CONF:
            lr = np.log(RB[k + (blk,)][:, DATA[k]['units'].index(u)])
            prs.append(p_one(lr, 'ge'))
            pus.append(p_one(lr, 'le'))
        pr.append(stouffer(prs, [W['Pair 1'], W['Pair 2']])[0])
        pu.append(stouffer(pus, [W['Pair 1'], W['Pair 2']])[0])
    pool.append((np.array(pr), np.array(pu), holm(pr), holm(pu)))
for i, u in enumerate(U8):
    read = all(pool[j][2][i] < 0.05 for j in (0, 1))
    unread = all(pool[j][3][i] < 0.05 for j in (0, 1))
    T2 = pd.concat([T2, pd.DataFrame([dict(pair='Pooled P1+P2', version='esankhyiki', unit=u, p_read_b12=pool[0][0][i],
                                           p_read_adj_b12=pool[0][2][i], p_read_adj_b6=pool[1][2][i], p_unread_b12=pool[0][1][i],
                                           p_unread_adj_b12=pool[0][3][i], p_unread_adj_b6=pool[1][3][i],
                                           tier='readable' if read else ('unreadable' if unread else 'undetermined'))])])
T2.round(4).to_csv(RESULTS / 'tests_h2_tiers.csv', index=False)
for _, r in T2.iterrows():
    row(id='H2', type='test' if r['pair'] in ('Pair 1', 'Pair 2', 'Pooled P1+P2') else 'exploratory', item=f"tier: {r['unit']}",
        pair=r['pair'], version=r['version'], estimate=r.get('R'), lo=r.get('lo'), hi=r.get('hi'),
        p=min(r['p_read_b12'], r['p_unread_b12']), p_adj=min(r['p_read_adj_b12'], r['p_unread_adj_b12']), decision=r['tier'])

# ------------------------------------------------------------------ H3
NAMED = USE_UNITS


def leaders(cc):
    s = np.sign(cc['General'].values)[:, None]
    s[s == 0] = 1
    v = cc[NAMED].values * s
    order = np.argsort(-v, axis=1)
    top = order[:, 0]
    margin = v[np.arange(len(v)), order[:, 0]] - v[np.arange(len(v)), order[:, 1]]
    rank = np.argsort(order, axis=1)  # rank[i, j] = position of unit j in date i's ordering (0 = leader)
    return top, margin, rank


def circ_p(stat_fn, n, k_lo=12):
    obs = stat_fn(0)
    ks = list(range(k_lo, n - k_lo + 1))
    vals = np.array([stat_fn(k) for k in ks])
    vals = vals[~np.isnan(vals)]  # shifts with no qualifying dates are dropped
    return obs, (1 + (vals >= obs - 1e-12).sum()) / (1 + len(vals)), len(vals), vals


def harris_p(stat_window, n):
    N = (n - 12) // 2
    vals = np.array([stat_window(s, N) for s in range(-N, N + 1)])
    v0 = stat_window(0, N)
    m = int((vals[~np.isnan(vals)] >= v0 - 1e-12).sum())
    return v0, min(1.0, m / (N + 1)), N, n - 2 * N  # Harris (2020) conservative p, capped at 1


h3a, h3d = {}, {}
for key in CONF + EXPL:
    D = DATA[key]
    co, cn = D['cco'], D['ccn']
    n = len(co)
    to, mo, ro = leaders(co)
    tn, mn, rn = leaders(cn)
    dgo, dgn = co['General'].values, cn['General'].values
    agree = (to == tn)
    # H3a
    if key in CONF:
        A, p, K, _ = circ_p(lambda k: (to == np.roll(tn, -k)).mean(), n)
        v0, ph, N, Dw = harris_p(lambda s, N: (to[N:n - N] == tn[N + s:n - N + s]).mean(), n)
        h3a[key[0]] = p
        row(id='H3a', type='test', item='leader agreement vs circular-shift null', pair=key[0], version=key[1], estimate=A, p=p,
            n=n, note=f'{K} shifts; smallest attainable p {1 / (K + 1):.3f}; Harris check: A(window)={v0:.3f}, conservative p={ph:.3f} (N={N}, D={Dw})')

        # H3d
        def opp(k):
            g2 = np.roll(dgn, -k)
            m = (np.abs(dgo) > 1) & (np.abs(g2) > 1)
            return (np.sign(dgo[m]) != np.sign(g2[m])).mean() if m.sum() else np.nan
        A3, p3, K3, _ = circ_p(opp, n)

        def opp_w(s, N):
            a, b = dgo[N:n - N], dgn[N + s:n - N + s]
            m = (np.abs(a) > 1) & (np.abs(b) > 1)
            return (np.sign(a[m]) != np.sign(b[m])).mean() if m.sum() else np.nan
        v0d, phd, _, _ = harris_p(opp_w, n)
        msk = (np.abs(dgo) > 1) & (np.abs(dgn) > 1)
        h3d[key[0]] = p3
        row(id='H3d', type='test', item='opposite direction of General (|move|>1 pp in both) vs circular-shift null', pair=key[0],
            version=key[1], estimate=A3, p=p3, n=int(msk.sum()),
            note=f'{K3} shifts; smallest attainable p {1 / (K3 + 1):.3f}; Harris conservative p={phd:.3f}; independent windows ~{msk.sum() / 12:.1f}')
    # H3b (bound)
    idx = stationary_matrix(n, 12, B, SEED + PAIRNO[key[0]] + 200 + (10 if key[1] == 'june2026' else 0))
    for margin in (0.1, 0.25, 0.5, 0.0):
        ok = (mo >= margin) & (mn >= margin)
        est = agree[ok].mean() if ok.sum() else np.nan
        num = (agree & ok)[idx].sum(axis=1)
        den = ok[idx].sum(axis=1)
        dr = np.where(den > 0, num / np.maximum(den, 1), np.nan)
        ub = np.nanquantile(dr, 0.95)
        row(id='H3b', type='bound' if key in CONF else 'exploratory', item=f'leader agreement, margin >= {margin} pp in both' if margin else 'leader agreement, unfiltered',
            pair=key[0], version=key[1], estimate=est, hi=ub, n=int(ok.sum()), block=12, B=B,
            note='one-sided 95% upper bound in hi' + ('' if margin != 0.1 else ' [primary]'))
    # H3c (bound)
    a, b = co[NAMED].values, cn[NAMED].values
    mat = (np.abs(a) >= 0.1) & (np.abs(b) >= 0.1)
    flip = (np.sign(a) != np.sign(b)) & mat
    est = flip.sum() / mat.sum()
    dr = flip[idx].sum(axis=(1, 2)) / np.maximum(mat[idx].sum(axis=(1, 2)), 1)
    lo, hi = np.quantile(dr, [0.025, 0.975])
    row(id='H3c', type='bound' if key in CONF else 'exploratory', item='material sign flips (|contribution| >= 0.1 pp in both)', pair=key[0],
        version=key[1], estimate=est, lo=lo, hi=hi, n=int(mat.sum()), block=12, B=B, note='share of unit-dates; 95% interval')
    for lab, top_a, rank_b in [('old leader ranked 3rd/4th in new', to, rn), ('new leader ranked 3rd/4th in old', tn, ro)]:
        rv = rank_b[np.arange(n), top_a] >= 2
        dr = rv[idx].mean(axis=1)
        lo, hi = np.quantile(dr, [0.025, 0.975])
        row(id='H3c', type='bound' if key in CONF else 'exploratory', item=f'reversal: {lab}', pair=key[0], version=key[1],
            estimate=rv.mean(), lo=lo, hi=hi, n=n, block=12, B=B, note='share of dates; 95% interval')
pp, z = stouffer([h3a['Pair 1'], h3a['Pair 2']], [W['Pair 1'], W['Pair 2']])
row(id='H3a', type='test', item='leader agreement vs circular-shift null', pair='Pooled P1+P2', p=pp, estimate=z,
    note='Stouffer Z', decision='PASS' if pp < 0.05 else 'FAIL (no evidence of agreement beyond chance)')
if max(h3d.values()) >= 1:  # a p of exactly 1 makes the Stouffer Z -inf; pooling is not informative
    row(id='H3d', type='test', item='opposite direction of General vs circular-shift null', pair='Pooled P1+P2', p=1.0,
        note='Pair 1 p = 1 (the bases agree on direction more than at any shift); pooled Z undefined', decision='FAIL')
else:
    pp, z = stouffer([h3d['Pair 1'], h3d['Pair 2']], [W['Pair 1'], W['Pair 2']])
    row(id='H3d', type='test', item='opposite direction of General vs circular-shift null', pair='Pooled P1+P2', p=pp, estimate=z,
        note='Stouffer Z', decision='PASS' if pp < 0.05 else 'FAIL')
for r in ROWS:
    if r['id'] == 'H3d' and r['pair'] in ('Pair 1', 'Pair 2'):
        r['decision'] = 'PASS' if r['p'] < 0.05 else 'FAIL'


# ------------------------------------------------------------------ H4 (months)
def decomp(key):
    D = DATA[key]
    old, new = D['old'], D['new']
    Co, Cn = D['Co'], D['Cn']
    wo = {**USE_WEIGHTS[old], 'Other': 100 - sum(USE_WEIGHTS[old].values())}
    wn = {**USE_WEIGHTS[new], 'Other': 100 - sum(USE_WEIGHTS[new].values())}
    tot = (Cn['General'] - Co['General']).values
    wt, dt = {}, {}
    for c in USE_UNITS + ['Other']:
        xo, xn = Co[c].values / wo[c], Cn[c].values / wn[c]
        wt[c] = (wn[c] - wo[c]) * (xo + xn) / 2
        dt[c] = (Cn[c].values - Co[c].values) - wt[c]
    return tot, wt, dt, Co, Cn


def msd_share(part, tot):
    return (part * tot).mean(axis=-1) / (tot ** 2).mean(axis=-1)


def dm_share(part, tot):
    p = part - part.mean(axis=-1, keepdims=True)
    t_ = tot - tot.mean(axis=-1, keepdims=True)
    return (p * t_).mean(axis=-1) / (t_ ** 2).mean(axis=-1)


h4a_ends = {}
cg_draws, h4d_p = {}, {}
for key in CONF + EXPL:
    tot, wt, dt, Co, Cn = decomp(key)
    T = len(tot)
    idx = stationary_matrix(T, 12 if T >= 36 else 6, B, SEED + PAIRNO[key[0]] + 300 + (10 if key[1] == 'june2026' else 0))
    TT = tot[idx]
    for c in USE_UNITS + ['Other']:
        est = msd_share(wt[c], tot)
        dr = msd_share(wt[c][idx], TT)
        lo, hi = np.quantile(dr, [0.05, 0.95])
        if key in CONF:
            h4a_ends.setdefault(key[0], []).append(max(abs(lo), abs(hi)))
        row(id='H4a', type='bound' if key in CONF else 'exploratory', item=f'weight-effect share of MSD: {c}', pair=key[0],
            version=key[1], estimate=est, lo=lo, hi=hi, n=T, block=12 if T >= 36 else 6, B=B, note='90% interval')
    cg_draws[key] = (dm_share(dt['Capital Goods'], tot), dm_share(dt['Capital Goods'][idx], TT))
    # H4d
    part = dt['Capital Goods'] + dt['Consumer Durables']
    vo = (Co['Capital Goods'] + Co['Consumer Durables']).values
    vn = (Cn['Capital Goods'] + Cn['Consumer Durables']).values
    Go, Gn = Co['General'].values, Cn['General'].values

    def theta(pt, tt, a, ga, b, gb):
        return dm_share(pt, tt) - (dm_share(a, ga) + dm_share(b, gb)) / 2
    est = theta(part, tot, vo, Go, vn, Gn)
    dr = theta(part[idx], TT, vo[idx], Go[idx], vn[idx], Gn[idx])
    p = p_one(dr, 'le')
    lo, hi = np.quantile(dr, [0.025, 0.975])
    if key in CONF:
        h4d_p[key[0]] = p
    row(id='H4d', type='test' if key in CONF else 'exploratory', item='CG+CD demeaned data share minus volatility share', pair=key[0],
        version=key[1], estimate=est, lo=lo, hi=hi, p=p, n=T, block=12 if T >= 36 else 6, B=B)
allb = max(max(v) for v in h4a_ends.values())
row(id='H4a', type='bound', item='bound b: largest |90% interval end| of weight-effect share, all units, P1 and P2', pair='P1 and P2',
    estimate=allb, note='; '.join(f'{k}: {max(v):.3f}' for k, v in h4a_ends.items()))
pp, z = stouffer([h4d_p['Pair 1'], h4d_p['Pair 2']], [W['Pair 1'], W['Pair 2']])
row(id='H4d', type='test', item='CG+CD concentration beyond volatility', pair='Pooled P1+P2', p=pp, estimate=z, note='Stouffer Z',
    decision='PASS' if pp < 0.05 else 'FAIL')
# H4b
e1, d1 = cg_draws[('Pair 1', 'esankhyiki')]
e2, d2 = cg_draws[('Pair 2', 'esankhyiki')]
diff = d2 - d1
lo, hi = np.quantile(diff, [0.05, 0.95])
row(id='H4b', type='bound', item='P2 - P1 capital goods demeaned data share', pair='P2 - P1', estimate=e2 - e1, lo=lo, hi=hi,
    note=f'90% interval, independent streams; equivalence bound = {max(abs(lo), abs(hi)):.3f}; P1 {e1:.3f}, P2 {e2:.3f}')
# H4c
for lab, sec in [('sectors = Mining, Manufacturing, Electricity', SECT3), ('sensitivity: sector control = Manufacturing only', ['Manufacturing'])]:
    k1, k2 = ('Pair 1', 'esankhyiki', 12), ('Pair 2', 'esankhyiki', 12)
    u1, u2 = DATA[k1[:2]]['units'], DATA[k2[:2]]['units']

    def mlog(R, units, us):
        return np.log(R[..., [units.index(u) for u in us]]).mean(axis=-1)
    est = (mlog(DATA[k2[:2]]['R'].values, u2, USE_UNITS) - mlog(DATA[k1[:2]]['R'].values, u1, USE_UNITS)) - \
          (mlog(DATA[k2[:2]]['R'].values, u2, sec) - mlog(DATA[k1[:2]]['R'].values, u1, sec))
    dr = (mlog(RB[k2], u2, USE_UNITS) - mlog(RB[k1], u1, USE_UNITS)) - (mlog(RB[k2], u2, sec) - mlog(RB[k1], u1, sec))
    lo, hi = np.quantile(dr, [0.05, 0.95])
    row(id='H4c', type='bound', item=f'DiD in log R (use-based minus sectors), P1 to P2; {lab}', pair='P2 - P1', estimate=est, lo=lo, hi=hi,
        note=f'90% interval; ratio bound exp(max|end|) = {np.exp(max(abs(lo), abs(hi))):.2f}; positive = use-based deteriorated more')


# ------------------------------------------------------------------ H5
def har(x):
    e, f = ewc(x), fixed_b_nw(x)
    pe = 2 * tdist.sf(abs(e['t']), e['df'])
    pf = fixed_b_pvalue(f['t'], f['b'])
    return e, f, pe, pf


for hid, lab in [('H5a', 'mean gap'), ('H5b', 'mean of (category gap - General gap)')]:
    pooled = {}
    for c in ['Capital Goods', 'Consumer Durables']:
        parts = []
        for key in CONF + EXPL:
            L = DATA[key]['LV']
            g = (L[c]['new'] - L[c]['old']).values
            if hid == 'H5b':
                g = g - (L['General']['new'] - L['General']['old']).values
            e, f, pe, pf = har(g)
            row(id=hid, type='test' if key in CONF else 'exploratory', item=f'{lab}: {c}', pair=key[0], version=key[1], estimate=e['est'],
                lo=e['lo'], hi=e['hi'], p=pe, n=len(g), note=f"EWC (nu={e['df']}); fixed-b p={pf:.4f}, interval {f['lo']:.2f} to {f['hi']:.2f}")
            if key in CONF:
                parts.append((e['est'], e['se'], e['df'], f['se'], f['b']))
        m_e = sum(m / s ** 2 for m, s, *_ in parts) / sum(1 / s ** 2 for _, s, *_ in parts)
        se_e = sum(1 / s ** 2 for _, s, *_ in parts) ** -0.5
        df = sum(p[2] for p in parts)
        pe = 2 * tdist.sf(abs(m_e / se_e), df)
        m_f = sum(p[0] / p[3] ** 2 for p in parts) / sum(1 / p[3] ** 2 for p in parts)
        se_f = sum(1 / p[3] ** 2 for p in parts) ** -0.5
        pf = fixed_b_pvalue(m_f / se_f, max(p[4] for p in parts))
        pooled[c] = (m_e, se_e, df, pe, m_f, se_f, pf)
    adj_e = holm([pooled[c][3] for c in pooled])
    adj_f = holm([pooled[c][6] for c in pooled])
    for (c, v), ae, af in zip(pooled.items(), adj_e, adj_f):
        cv = tdist.ppf(0.975, v[2])
        row(id=hid, type='test', item=f'{lab}: {c}', pair='Pooled P1+P2', estimate=v[0], lo=v[0] - cv * v[1], hi=v[0] + cv * v[1],
            p=v[3], p_adj=max(ae, af), note=f'EWC pooled (df {v[2]}) p={v[3]:.4f} adj {ae:.4f}; fixed-b pooled p={v[6]:.4f} adj {af:.4f}',
            decision='PASS' if (ae < 0.05 and af < 0.05) else 'FAIL')

# ------------------------------------------------------------------ H6 (exploratory)
VS = pd.read_csv(RESULTS / 'value_shares_2011-12.csv', dtype={'nic2': str})
REL = pd.read_csv(RESULTS / 'reliability.csv')
REL = REL[(REL['pair'] == 'Pair 3') & (REL['data_version'] == 'esankhyiki') & REL['family'].str.startswith('Industry')]
V = pd.read_csv(RESULTS / 'industry_vintage_revision.csv', dtype={'nic2': str})
rng = np.random.default_rng(SEED + 600)


def perm_spearman(a, b, reps=99999):
    a, b = np.asarray(a, float), np.asarray(b, float)
    rho = spearmanr(a, b).statistic
    ra, rb = pd.Series(a).rank().values, pd.Series(b).rank().values
    ra, rb = ra - ra.mean(), rb - rb.mean()
    den = np.sqrt((ra ** 2).sum() * (rb ** 2).sum())
    cnt = 0
    for s in range(0, reps, 10000):
        k = min(10000, reps - s)
        P = np.argsort(rng.random((k, len(rb))), axis=1)
        cnt += ((rb[P] @ ra) / den >= rho - 1e-12).sum()
    return rho, (1 + cnt) / (1 + reps)


M = VS.merge(REL[['unit', 'R_chg_6', 'R_level_demeaned']], left_on='industry', right_on='unit')
assert len(M) == 23
for col, lab in [('R_chg_6', 'Pair 3 6-month change ratio [primary]'), ('R_level_demeaned', 'Pair 3 demeaned level ratio')]:
    rho, p = perm_spearman(M['value_share'], M[col])
    row(id='H6a', type='exploratory', item=f'Spearman(value share, {lab})', pair='Pair 3', estimate=rho, p=p, n=23,
        note='99,999 permutations, one-sided', decision='PASS' if p < 0.05 else 'FAIL')
for col, lab in [('abs_change_growth_2025_26', '|change in FY2025-26 growth| between vintages [primary]'),
                 ('abs_change_log_index_2024_25', '|change in log FY2024-25 index| between vintages')]:
    rho, p = perm_spearman(V['value_share'], V[col])
    row(id='H6b', type='exploratory', item=f'Spearman(value share, {lab})', pair='Pair 3 vintages', estimate=rho, p=p, n=23,
        note='99,999 permutations, one-sided; revision also includes source-data updates', decision='PASS' if p < 0.05 else 'FAIL')

# ------------------------------------------------------------------ added after review (NOT in tests_spec.md)
# 1. Out-of-sample check of H1b: rank correlation of R between each historical overlap and Pair 3.
for key3 in EXPL:
    r3 = DATA[key3]['R']
    u = [x for x in u7 if x in r3.index]
    for pk in ('Pair 1', 'Pair 2'):
        rp = DATA[(pk, 'esankhyiki')]['R']
        xx, yy = rp[u].rank().values, r3[u].rank().values
        rho_o = spearmanr(xx, yy).statistic
        perm_o = np.array([spearmanr(xx, np.array(q)).statistic for q in itertools.permutations(yy)])
        row(id='H1b-oos', type='post-review check', item=f'Spearman rho of R ranks, {pk} vs Pair 3 ({len(u)} units)', pair=f'{pk} vs Pair 3',
            version=key3[1], estimate=rho_o, p=(perm_o >= rho_o - 1e-12).mean(), n=len(u),
            note='not in tests_spec.md; Pair 3 used as the held-out overlap', decision='PASS' if (perm_o >= rho_o - 1e-12).mean() < 0.05 else 'FAIL')


# 2. Denominator sensitivity: R with the geometric mean of the two typical changes instead of the larger one.
def R_geo(co, cn):
    dis = np.median(np.abs(cn - co), axis=-2)
    return dis / np.sqrt(np.median(np.abs(co), axis=-2) * np.median(np.abs(cn), axis=-2))


RG = {}
for key in CONF:
    D = DATA[key]
    co, cn = D['CO'][D['units']].values, D['CN'][D['units']].values
    idx = stationary_matrix(len(co), 12, B, SEED + PAIRNO[key[0]])  # same draws as the primary H1a/H2 (block 12)
    dr = np.empty((B, co.shape[1]))
    for s0 in range(0, B, 500):
        ii = idx[s0:s0 + 500]
        dr[s0:s0 + 500] = R_geo(co[ii], cn[ii])
    RG[key] = (pd.Series(R_geo(co, cn), index=D['units']), dr)
pr, pu = [], []
for u in U8:
    prs, pus = [], []
    for key in CONF:
        lr = np.log(RG[key][1][:, DATA[key]['units'].index(u)])
        prs.append(p_one(lr, 'ge'))
        pus.append(p_one(lr, 'le'))
    pr.append(stouffer(prs, [W['Pair 1'], W['Pair 2']])[0])
    pu.append(stouffer(pus, [W['Pair 1'], W['Pair 2']])[0])
ar, au = holm(pr), holm(pu)
for i, u in enumerate(U8):
    t_ = 'readable' if ar[i] < 0.05 else ('unreadable' if au[i] < 0.05 else 'undetermined')
    row(id='H2-geo', type='post-review check', item=f'tier with geometric-mean denominator: {u}', pair='Pooled P1+P2',
        estimate=float(RG[CONF[0]][0][u]), lo=float(RG[CONF[1]][0][u]), p=min(pr[i], pu[i]), p_adj=min(ar[i], au[i]), decision=t_,
        note='estimate = R_geo Pair 1, lo column = R_geo Pair 2 (block 12 only); not in tests_spec.md')
ps = []
for key in CONF:
    D = DATA[key]
    est = float(contrast(RG[key][0].values, D['units'], STABLE, MFG5))
    dr = contrast(RG[key][1], D['units'], STABLE, MFG5)
    ps.append(p_one(dr, 'ge'))
    row(id='H1a-geo', type='post-review check', item='H1a group contrast, geometric-mean denominator', pair=key[0], estimate=est,
        lo=np.quantile(dr, 0.025), hi=np.quantile(dr, 0.975), p=ps[-1], note='not in tests_spec.md')
pp, z = stouffer(ps, [W['Pair 1'], W['Pair 2']])
row(id='H1a-geo', type='post-review check', item='H1a group contrast, geometric-mean denominator', pair='Pooled P1+P2', p=pp, estimate=z,
    decision='PASS' if pp < 0.05 else 'FAIL', note='Stouffer Z; not in tests_spec.md')

# ------------------------------------------------------------------ added after the second review (NOT in tests_spec.md)
# 3. H4 with effective weights. In a fixed-base Laspeyres index C_c,t = w_c (I_c,t - I_c,t-12) / G_t-12
#    = omega_c,t * g_c,t, with omega_c,t = w_c I_c,t-12 / G_t-12 (the category's effective weight at t-12, in %
#    of General) and g_c,t = I_c,t / I_c,t-12 - 1. The nominal split puts the drift of omega since the base year
#    into the data effect; this split puts it into the weight effect. Same bootstrap draws as the nominal H4.
def eff_parts(base, version, months):
    lv = levels(base, version if base == '2022-23' else 'esankhyiki', base_year=False)
    g12 = lv['General'].shift(12)
    om = pd.DataFrame({c: USE_WEIGHTS[base][c] * lv[c].shift(12) / g12 for c in USE_UNITS})
    gr = pd.DataFrame({c: lv[c] / lv[c].shift(12) - 1 for c in USE_UNITS})
    om['Other'] = 100 - om.sum(axis=1)
    return om.loc[months], gr.loc[months]


def decomp_eff(key):
    D = DATA[key]
    Co, Cn = D['Co'], D['Cn']
    months = Co.index
    oo, go = eff_parts(D['old'], 'esankhyiki', months)
    on, gn = eff_parts(D['new'], key[1], months)
    go['Other'] = Co['Other'] / oo['Other']
    gn['Other'] = Cn['Other'] / on['Other']
    for c in USE_UNITS:  # identity check: omega * g reproduces the contribution
        assert np.allclose(oo[c] * go[c], Co[c]) and np.allclose(on[c] * gn[c], Cn[c])
    tot = (Cn['General'] - Co['General']).values
    wt, dt = {}, {}
    for c in USE_UNITS + ['Other']:
        wt[c] = ((on[c] - oo[c]) * (go[c] + gn[c]) / 2).values
        dt[c] = (Cn[c].values - Co[c].values) - wt[c]
    drift = {c: (float((oo[c] / D_w(D['old'], c)).mean()), float((on[c] / D_w(D['new'], c)).mean())) for c in USE_UNITS}
    return tot, wt, dt, Co, Cn, drift


def D_w(base, c):
    return USE_WEIGHTS[base][c]


ends_eff, cg_eff, h4d_eff = {}, {}, {}
for key in CONF + EXPL:
    tot, wt, dt, Co, Cn, drift = decomp_eff(key)
    T = len(tot)
    idx = stationary_matrix(T, 12 if T >= 36 else 6, B, SEED + PAIRNO[key[0]] + 300 + (10 if key[1] == 'june2026' else 0))
    TT = tot[idx]
    for c in USE_UNITS + ['Other']:
        est = msd_share(wt[c], tot)
        dr = msd_share(wt[c][idx], TT)
        lo, hi = np.quantile(dr, [0.05, 0.95])
        if key in CONF:
            ends_eff.setdefault(key[0], []).append(max(abs(lo), abs(hi)))
        note = '90% interval; effective weights'
        if c in drift:
            note += f'; mean effective/nominal weight old {drift[c][0]:.3f}, new {drift[c][1]:.3f}'
        row(id='H4a-eff', type='post-review check', item=f'weight-effect share of MSD (effective weights): {c}', pair=key[0],
            version=key[1], estimate=est, lo=lo, hi=hi, n=T, block=12 if T >= 36 else 6, B=B, note=note)
    for c in USE_UNITS + ['Other']:
        row(id='H4a-eff', type='post-review check', item=f'data-effect share of MSD (effective weights): {c}', pair=key[0],
            version=key[1], estimate=msd_share(dt[c], tot), n=T)
    cg_eff[key] = (dm_share(dt['Capital Goods'], tot), dm_share(dt['Capital Goods'][idx], TT))
    part = dt['Capital Goods'] + dt['Consumer Durables']
    vo = (Co['Capital Goods'] + Co['Consumer Durables']).values
    vn = (Cn['Capital Goods'] + Cn['Consumer Durables']).values
    Go, Gn = Co['General'].values, Cn['General'].values

    def theta_e(pt, tt, a, ga, b, gb):
        return dm_share(pt, tt) - (dm_share(a, ga) + dm_share(b, gb)) / 2
    est = theta_e(part, tot, vo, Go, vn, Gn)
    dr = theta_e(part[idx], TT, vo[idx], Go[idx], vn[idx], Gn[idx])
    p = p_one(dr, 'le')
    lo, hi = np.quantile(dr, [0.025, 0.975])
    if key in CONF:
        h4d_eff[key[0]] = p
    row(id='H4d-eff', type='post-review check', item='CG+CD demeaned data share minus volatility share (effective weights)',
        pair=key[0], version=key[1], estimate=est, lo=lo, hi=hi, p=p, n=T, block=12 if T >= 36 else 6, B=B)
row(id='H4a-eff', type='post-review check', item='bound b: largest |90% interval end| of weight-effect share, all units, P1 and P2 (effective weights)',
    pair='P1 and P2', estimate=max(max(v) for v in ends_eff.values()), note='; '.join(f'{k}: {max(v):.3f}' for k, v in ends_eff.items()))
pp, z = stouffer([h4d_eff['Pair 1'], h4d_eff['Pair 2']], [W['Pair 1'], W['Pair 2']])
row(id='H4d-eff', type='post-review check', item='CG+CD concentration beyond volatility (effective weights)', pair='Pooled P1+P2',
    p=pp, estimate=z, note='Stouffer Z', decision='PASS' if pp < 0.05 else 'FAIL')
e1, d1 = cg_eff[('Pair 1', 'esankhyiki')]
e2, d2 = cg_eff[('Pair 2', 'esankhyiki')]
lo, hi = np.quantile(d2 - d1, [0.05, 0.95])
row(id='H4b-eff', type='post-review check', item='P2 - P1 capital goods demeaned data share (effective weights)', pair='P2 - P1',
    estimate=e2 - e1, lo=lo, hi=hi, note=f'90% interval; P1 {e1:.3f}, P2 {e2:.3f}')

# 4. Window length of the change c (3 and 12 months on each side, against the primary 6).
for L in (3, 6, 12):
    Rw = {}
    for key in CONF + [('Pair 3', 'esankhyiki')]:
        U = unit_pairs(DATA[key]['old'], DATA[key]['new'], *[p[3:5] for p in PAIRS if p[0] == key[0]][0], key[1])
        units = [u for u in U8 if u in U]
        co = pd.DataFrame({u: window_change(U[u][1].asfreq('MS')['old'], L) for u in units})
        cn = pd.DataFrame({u: window_change(U[u][1].asfreq('MS')['new'], L) for u in units})
        R = pd.Series(R_of(co.values, cn.values), index=units)
        Rw[key[0]] = R
        ps = []
        if key in CONF:
            dr = contrast(boot_R(co.values, cn.values, 12, SEED + PAIRNO[key[0]] + 500 + L), units, STABLE, MFG5)
            ps.append(p_one(dr, 'ge'))
            Rw[key[0] + '_p'] = ps[0]
            Rw[key[0] + '_c'] = float(contrast(R.values, units, STABLE, MFG5))
        for u in units:
            row(id='R-window', type='post-review check', item=f'R with {L}-month windows: {u}', pair=key[0], version=key[1],
                estimate=R[u], n=len(co), note='not in tests_spec.md')
    pp, z = stouffer([Rw['Pair 1_p'], Rw['Pair 2_p']], [W['Pair 1'], W['Pair 2']])
    rho_w = spearmanr(Rw['Pair 1'][u7].rank().values, Rw['Pair 2'][u7].rank().values).statistic
    row(id='R-window', type='post-review check', item=f'H1a group contrast with {L}-month windows', pair='Pooled P1+P2', p=pp,
        estimate=z, note=f"contrast P1 {Rw['Pair 1_c']:.3f}, P2 {Rw['Pair 2_c']:.3f}; Spearman P1 vs P2 {rho_w:.3f}",
        decision='PASS' if (pp < 0.05 and Rw['Pair 1_c'] < 0 and Rw['Pair 2_c'] < 0) else 'FAIL')
    row(id='R-window', type='post-review check', item=f'Spearman rho of R ranks, P1 vs P2, {L}-month windows', pair='P1 vs P2',
        estimate=rho_w)

# 5. Leading category with 'Other' (the residual) allowed to lead.
h3o = {}
for key in CONF:
    co, cn = DATA[key]['cco'], DATA[key]['ccn']
    n = len(co)

    def lead5(cc):
        s = np.sign(cc['General'].values)[:, None]
        s[s == 0] = 1
        v = cc[NAMED + ['Other']].values * s
        o = np.argsort(-v, axis=1)
        return o[:, 0], v[np.arange(len(v)), o[:, 0]] - v[np.arange(len(v)), o[:, 1]]
    to5, mo5 = lead5(co)
    tn5, mn5 = lead5(cn)
    ok = (mo5 >= 0.1) & (mn5 >= 0.1)
    ag = to5 == tn5
    idx = stationary_matrix(n, 12, B, SEED + PAIRNO[key[0]] + 200)
    dr = np.where(ok[idx].sum(axis=1) > 0, (ag & ok)[idx].sum(axis=1) / np.maximum(ok[idx].sum(axis=1), 1), np.nan)
    A, p, K, _ = circ_p(lambda k: (to5 == np.roll(tn5, -k)).mean(), n)
    h3o[key[0]] = p
    row(id='H3-other', type='post-review check', item="leader agreement incl. 'Other', margin >= 0.1 pp in both", pair=key[0],
        estimate=ag[ok].mean(), hi=np.nanquantile(dr, 0.95), n=int(ok.sum()),
        note=f"one-sided 95% upper bound in hi; 'Other' leads on {(to5 == 4).mean():.2f} (old) / {(tn5 == 4).mean():.2f} (new) of dates; unfiltered agreement {ag.mean():.3f}, circular-shift p {p:.3f}")
pp, z = stouffer([h3o['Pair 1'], h3o['Pair 2']], [W['Pair 1'], W['Pair 2']])
row(id='H3-other', type='post-review check', item="leader agreement incl. 'Other' vs circular-shift null", pair='Pooled P1+P2', p=pp, estimate=z,
    note='Stouffer Z', decision='PASS' if pp < 0.05 else 'FAIL')

OUT = pd.DataFrame(ROWS)
cols = ['id', 'type', 'item', 'pair', 'version', 'block', 'estimate', 'lo', 'hi', 'p', 'p_adj', 'decision', 'n', 'expected_blocks', 'B',
        'boot_median', 'note']
OUT = OUT.reindex(columns=cols)
OUT.round(4).to_csv(RESULTS / 'tests.csv', index=False)
pd.set_option('display.width', 260)
pd.set_option('display.max_colwidth', 90)
pd.set_option('display.max_rows', 400)
print(OUT.drop(columns=['B', 'expected_blocks', 'boot_median']).round(3).to_string(index=False))
