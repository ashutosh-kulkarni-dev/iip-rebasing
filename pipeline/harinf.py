"""Small-sample inference helpers shared by the reliability, diagnosis and gap analyses.

Why these and not Newey-West with 12 lags: monthly YoY growth rates overlap (adjacent months
share 11 of 12 months), and the overlaps are short (T = 24 to 63). Conventional HAC standard
errors with normal critical values are badly over-sized in that setting. Following Lazarus,
Lewis, Stock and Watson (2018, JBES 36(4)), we report two tests with size control in small
samples:

  fixed_b_nw : Newey-West (Bartlett) with bandwidth M = ceil(1.3 * sqrt(T)) and fixed-b
               critical values (Kiefer and Vogelsang 2005). The critical values are simulated
               here (iid Gaussian, T_sim = 1000, 20,000 draws) for b = M / T, so they do not
               depend on a published polynomial approximation.
  ewc        : equal-weighted cosine (EWC) estimator with nu = floor(0.4 * T^(2/3)) cosine
               terms; the t statistic is referred to Student t with nu degrees of freedom.
  annual_t   : ordinary t test on non-overlapping fiscal-year means (n - 1 df).

Bootstrap helpers: a stationary bootstrap (Politis and Romano 1994; geometric block lengths,
circular) and a moving-block bootstrap (Kunsch 1989). Every bootstrap result reports the mean
block length and the expected number of blocks (T / block), because with fewer than about 8
blocks the bootstrap distribution is too coarse to be trusted; callers flag such intervals.
"""
import json
import numpy as np
from scipy import stats
from config import RESULTS

SEED = 20261018
_CV_CACHE = {}
_CACHE_FILE = RESULTS / 'fixed_b_critical_values.json'  # deterministic (fixed seed); delete to re-simulate


def _bartlett_lrv(u, M):
    u = np.asarray(u, float) - np.mean(u)
    T = len(u)
    v = u @ u / T
    for j in range(1, int(M)):
        w = 1 - j / M
        v += 2 * w * (u[j:] @ u[:-j]) / T
    return v


def fixed_b_cv(b, alpha=0.05, reps=20000, T_sim=1000):
    """Two-sided fixed-b critical value for the Bartlett kernel with bandwidth ratio b."""
    key = f'{b:.4f}|{alpha}'
    if not _CV_CACHE and _CACHE_FILE.exists():
        _CV_CACHE.update(json.loads(_CACHE_FILE.read_text()))
    if key in _CV_CACHE:
        return _CV_CACHE[key]
    rng = np.random.default_rng(SEED)
    M = max(1, int(round(b * T_sim)))
    tt = []
    for _ in range(reps // 1000):
        e = rng.standard_normal((1000, T_sim))
        m = e.mean(axis=1, keepdims=True)
        u = e - m
        v = (u * u).sum(axis=1) / T_sim
        for j in range(1, M):
            v += 2 * (1 - j / M) * (u[:, j:] * u[:, :-j]).sum(axis=1) / T_sim
        tt.append(np.sqrt(T_sim) * m[:, 0] / np.sqrt(v))
    cv = np.quantile(np.abs(np.concatenate(tt)), 1 - alpha)
    _CV_CACHE[key] = float(cv)
    _CACHE_FILE.write_text(json.dumps(_CV_CACHE, indent=1))
    return float(cv)


def fixed_b_nw(x, alpha=0.05):
    x = np.asarray(x, float)
    T = len(x)
    M = int(np.ceil(1.3 * np.sqrt(T)))
    se = np.sqrt(_bartlett_lrv(x, M) / T)
    cv = fixed_b_cv(M / T, alpha)
    m = x.mean()
    t = m / se
    return dict(method='fixed-b NW', T=T, bandwidth=M, b=M / T, est=m, se=se, crit=cv,
                lo=m - cv * se, hi=m + cv * se, t=t, reject=abs(t) > cv)


def ewc(x, alpha=0.05):
    x = np.asarray(x, float)
    T = len(x)
    nu = max(1, int(np.floor(0.4 * T ** (2 / 3))))
    t_ = np.arange(1, T + 1)
    u = x - x.mean()
    lam = np.array([np.sqrt(2 / T) * (np.cos(np.pi * j * (t_ - 0.5) / T) @ u) for j in range(1, nu + 1)])
    omega = (lam ** 2).mean()
    se = np.sqrt(omega / T)
    cv = stats.t.ppf(1 - alpha / 2, nu)
    m = x.mean()
    tstat = m / se
    return dict(method='EWC', T=T, bandwidth=nu, b=np.nan, est=m, se=se, crit=cv, df=nu,
                lo=m - cv * se, hi=m + cv * se, t=tstat, p=2 * stats.t.sf(abs(tstat), nu), reject=abs(tstat) > cv)


def annual_t(x, alpha=0.05):
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    n = len(x)
    m, se = x.mean(), x.std(ddof=1) / np.sqrt(n)
    cv = stats.t.ppf(1 - alpha / 2, n - 1)
    return dict(method='annual t', T=n, est=m, se=se, crit=cv, df=n - 1, lo=m - cv * se, hi=m + cv * se,
                t=m / se, p=2 * stats.t.sf(abs(m / se), n - 1), reject=abs(m / se) > cv)


def stationary_indices(n, mean_block, reps, rng):
    p = 1 / mean_block
    for _ in range(reps):
        idx = np.empty(n, dtype=int)
        i = rng.integers(n)
        for k in range(n):
            if k > 0:
                i = rng.integers(n) if rng.random() < p else (i + 1) % n
            idx[k] = i
        yield idx


def moving_block_indices(n, block, reps, rng):
    starts = np.arange(n - block + 1)
    k = int(np.ceil(n / block))
    for _ in range(reps):
        yield np.concatenate([np.arange(s, s + block) for s in rng.choice(starts, k)])[:n]


def boot(data, fn, mean_block, reps=2000, kind='stationary', seed=SEED, alpha=0.05):
    """Bootstrap a statistic fn(data_subset) over rows of `data` (a numpy array, rows = time).
    Returns the percentile interval plus diagnostics: the bootstrap median, the share of draws
    below the point estimate (0.5 if centred), the expected number of blocks."""
    rng = np.random.default_rng(seed)
    n = len(data)
    gen = stationary_indices if kind == 'stationary' else moving_block_indices
    est = fn(data)
    vals = np.array([fn(data[i]) for i in gen(n, mean_block, reps, rng)], float)
    vals = vals[np.isfinite(vals)]
    lo, hi = np.quantile(vals, [alpha / 2, 1 - alpha / 2])
    return dict(est=est, lo=lo, hi=hi, boot_median=np.median(vals), share_below_est=(vals < est).mean(),
                mean_block=mean_block, expected_blocks=n / mean_block, reps=len(vals), kind=kind,
                interval='percentile')


_NULL_DRAWS = {}


def fixed_b_null(b, reps=20000, T_sim=1000):
    """Simulated |t| draws under the fixed-b null (Bartlett, bandwidth ratio b), cached."""
    key = round(b, 4)
    if key in _NULL_DRAWS:
        return _NULL_DRAWS[key]
    rng = np.random.default_rng(SEED)
    M = max(1, int(round(b * T_sim)))
    tt = []
    for _ in range(reps // 1000):
        e = rng.standard_normal((1000, T_sim))
        m = e.mean(axis=1, keepdims=True)
        u = e - m
        v = (u * u).sum(axis=1) / T_sim
        for j in range(1, M):
            v += 2 * (1 - j / M) * (u[:, j:] * u[:, :-j]).sum(axis=1) / T_sim
        tt.append(np.abs(np.sqrt(T_sim) * m[:, 0] / np.sqrt(v)))
    _NULL_DRAWS[key] = np.sort(np.concatenate(tt))
    return _NULL_DRAWS[key]


def fixed_b_pvalue(t, b):
    d = fixed_b_null(b)
    return (1 + (d >= abs(t)).sum()) / (1 + len(d))


def stationary_matrix(n, mean_block, reps, seed):
    """reps x n index matrix of a circular stationary bootstrap (vectorised over replications)."""
    rng = np.random.default_rng(seed)
    p = 1 / mean_block
    idx = np.empty((reps, n), dtype=int)
    idx[:, 0] = rng.integers(n, size=reps)
    for k in range(1, n):
        jump = rng.random(reps) < p
        idx[:, k] = np.where(jump, rng.integers(n, size=reps), (idx[:, k - 1] + 1) % n)
    return idx


def holm(p):
    """Holm step-down adjusted p-values (valid under any dependence)."""
    p = np.asarray(p, float)
    order = np.argsort(p)
    m = len(p)
    adj = np.empty(m)
    run = 0.0
    for r, i in enumerate(order):
        run = max(run, (m - r) * p[i])
        adj[i] = min(1.0, run)
    return adj


def stouffer(ps, weights):
    from scipy.stats import norm
    ps, w = np.asarray(ps, float), np.asarray(weights, float)
    z = (w * norm.isf(ps)).sum() / np.sqrt((w ** 2).sum())
    return float(norm.sf(z)), float(z)
