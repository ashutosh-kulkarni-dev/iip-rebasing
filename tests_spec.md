# Test specification (written before any test was run)

Written 18 Oct 2026, before `pipeline/tests.py` existed or was run. It implements "Research
Plan v2" (18 Oct 2026). The hypotheses were formed **after** the descriptive run of 18 Oct
2026 (`results/FINDINGS.md`) and **before** any test below was run. The paper must say so.
Every test and bound listed here is reported, including failures. Anything run beyond this
spec is labelled exploratory.

The file was written to the project folder before the tests were run; commit it with git
before running `tests.py` so the timestamp is recorded.

## Common definitions

* **Pairs.** P1 = 1993-94 / 2004-05 (true-YoY months Apr 2006-Jun 2011, T = 63);
  P2 = 2004-05 / 2011-12 (Apr 2013-Mar 2017, T = 48); P3 = 2011-12 / 2022-23 (Apr 2024-Mar 2026,
  T = 24). P1 and P2 are confirmatory and independent. P3 is exploratory: reported on both
  vintages of the 2022-23 series (29 June 2026 revised, primary; 1 June 2026), never pooled and
  never Holm-adjusted together with P1-P2. Electricity is excluded from the 1 June vintage,
  which publishes only Electricity & Gas Supply.
* **Units (U8).** General, Mining, Manufacturing, Electricity, Capital goods (CG),
  Intermediate (IG), Consumer durables (CD), Consumer non-durables (CND).
* **Growth.** True YoY growth from published levels (from month 13 of each base).
* **6-month change.** At each date t with 6 months before and after inside the overlap:
  c_t = mean YoY over [t, t+6) minus mean YoY over [t-6, t). That gives 52 dates in P1, 37 in
  P2 and 13 in P3.
* **R (primary): 6-month change ratio.**
  R = median_t |c_new - c_old| / max(median_t |c_old|, median_t |c_new|), a ratio of medians.
  **Secondary: demeaned level ratio** SD(gap) / max(SD_old, SD_new), with ddof = 0.
* **Contributions.** Laspeyres contributions C_c,t = w_c (I_c,t - I_c,t-12) / G_t-12. The
  contribution of c to the 6-month change in General growth is the change of C_c over the
  same windows. Use-based family: the 4 named categories, plus Other = the residual. Leaders are
  chosen among the 4 named categories. Sector weights are the verified ones in `config.py`.
* **Joint stationary bootstrap** (Politis-Romano). One index draw per replication is applied to
  every unit, so cross-unit dependence is preserved. Rows are change-dates for change-based
  statistics and months for level- and decomposition-based statistics.
  - Mean block length: 12 (primary) and 6 (sensitivity).
  - B = 9,999 replications.
  - Seed 20261018 plus the pair number, so the streams for different pairs are independent.
  - Every result reports the mean block length, the expected number of blocks, B and the
    bootstrap median.
* **One-sided bootstrap p** for H0: θ ≥ 0 is (1 + #{θ* ≥ 0}) / (B + 1). For H0: θ ≤ 0 it is
  (1 + #{θ* ≤ 0}) / (B + 1).
* **Pooling P1 and P2.** Weighted Z (Stouffer; Whitlock 2005):
  Z = Σ w_i Φ⁻¹(1 - p_i) / √Σ w_i², with w_i = √(T_i / 12): √5.25 for P1, √4.0 for P2.
  Pooled p = 1 - Φ(Z).
* **HAR tests for means.**
  - EWC with ν = ⌊0.4 T^(2/3)⌋ (6 / 5 / 3), referred to t(ν).
  - Fixed-b Newey-West with Bartlett kernel and M = ⌈1.3 √T⌉ (11 / 10 / 7), with simulated
    fixed-b critical values and p-values (iid Gaussian, T_sim = 1000, 20,000 draws, fixed seed).
  - A mean is "different from zero" only if **both** reject.
  - Pooled HAR (P1 + P2): inverse-variance-weighted mean and standard error. Its EWC p uses
    t(ν1 + ν2). Its fixed-b p uses the simulated fixed-b null at b = max(b1, b2), which is
    conservative.
  - Annual t tests on fiscal-year gaps are a check only. They treat dependent annual gaps as
    independent.
* **Multiplicity.** Holm (1979) within each hypothesis family, valid under any dependence. Both
  unadjusted and adjusted p are reported. α = 0.05.
* **Thresholds and their basis.**
  - 0 and chance: natural nulls.
  - R = 1: the disagreement equals the movement being measured.
  - 0.1 pp: MoSPI publishes growth rates to one decimal.
  - 1 pp (H3d only): selects dates with a clear move; the test itself is against the shift null.
  - No other cutoff is used.

## Confirmatory tests (8)

**H1a: stable-source sectors are more reliable.**
- Contrast: C = mean(log R_Electricity, log R_Mining) minus mean of log R over Manufacturing,
  CG, IG, CD and CND.
- H0: C ≥ 0. Joint bootstrap over change-dates, one-sided p per pair, pooled with Stouffer.
- **Pass:** pooled p < 0.05 and C < 0 in both P1 and P2.
- Also: the two individual contrasts (log R_Elec − log R_Mfg and log R_Mining − log R_Mfg),
  pooled and Holm-adjusted over the 2. Block 6 is a sensitivity check.

**H1b: the ranking is stable across rebasings.**
- Statistic: Spearman ρ between the P1 and P2 values of R for the 7 non-General units.
- H0: ρ ≤ 0. Exact permutation over all 5,040 orderings; p = share with ρ_perm ≥ ρ_obs.
- **Pass:** p < 0.05.

**H2: single-base readability tiers.**
- For each unit and pair: p_read for H0 log R ≥ 0, and p_unread for H0 log R ≤ 0.
- Holm over the 8 units within each pair, separately for each direction.
- **Readable** if the Holm-adjusted p_read < 0.05 at both mean block 12 and mean block 6.
  **Unreadable** if the same holds for p_unread. Otherwise **undetermined**.
- Pooled tier per unit: Stouffer of P1 and P2, then Holm over the 8 units, same rule.

**H3a: the bases share diagnostic information beyond chance (use-based family).**
- Statistic: A = share of dates on which the leading category is the same in both bases (all
  dates, no filter).
- Null: circular shift. The new base's per-date contribution vectors are shifted by
  k = 12, …, n − 12, wrapping within the overlap (29 shifts in P1, 14 in P2).
  p = (1 + #{A_k ≥ A}) / (1 + K). Smallest attainable p: 0.033 (P1), 0.067 (P2).
- Check: Harris (2020) non-wrapping shift test. Use central window D = n − 2N with
  N = ⌊(n − 12)/2⌋ (P1: N = 20, D = 12; P2: N = 12, D = 13), count
  m = #{s in −N..N : A_s ≥ A_0}, and take the conservative p = m / (N + 1).
- Pooled: Stouffer of the circular-shift p's.
- **Pass:** pooled p < 0.05.
- **Failure wording:** "no evidence that the bases agree on the leading category beyond chance."

**H3d: the bases disagree on the direction of General.**
- Statistic: share of dates, among those where |ΔG| > 1 pp in both bases, at which the two
  bases move General in opposite directions.
- Null: circular shift, with the 1 pp filter recomputed for each shift. One-sided (more
  disagreement than under the shift null).
- P1 and P2 are reported separately and pooled.
- **Pass:** p < 0.05.

**H4d: concentration beyond volatility.**
- θ = (CG + CD demeaned data-effect share of the gap variance) minus (CG + CD share of the
  variance of General growth, averaged over the two bases).
- H0: θ ≤ 0. Joint bootstrap over months, one-sided, Stouffer across P1 and P2.
- **Pass:** pooled p < 0.05.

**H5a: category persistent gaps.**
- Mean YoY gap (new − old) for CG and CD, per pair and pooled. EWC and fixed-b, two-sided,
  Holm over the 2 categories for each method.
- **Pass:** for a category, the pooled gap is "different from zero" under both methods after
  Holm.

**H5b: category gaps exceed the General gap.**
- Series: (category gap − General gap) for CG and CD. Same procedure as H5a.

## Reported bounds (5): no pass/fail

**H3b: how often the leading category agrees.**
- Agreement among dates where, in **both** bases, the leader exceeds the runner-up by
  ≥ 0.1 pp. Runner-up means the second-largest contribution signed in the base's own
  direction of change.
- Report the estimate, the number of dates, and a one-sided 95% upper bound (95th percentile of
  the joint bootstrap over dates, mean block 12).
- Also report the unfiltered value. Margins of 0.25 and 0.5 pp go in the appendix.

**H3c: material sign flips.**
- Among unit-dates (4 named categories) where |contribution to change| ≥ 0.1 pp in both bases,
  report the share with opposite signs, with a 95% two-sided bootstrap interval.
- Also report the share of dates on which base A's leader ranks 3rd or 4th of 4 in base B
  (signed in base B's direction), in both directions (old → new and new → old).

**H4a: weights are negligible.**
- For each use-based unit (4 categories + Other) and pair (P1, P2), compute the 90% joint
  bootstrap interval (months, block 12) of the weight-effect share of the MSD.
- Bound b = the largest absolute interval end across units and pairs. Also report b per pair.

**H4b: the 2017 redefinition adds nothing (capital goods).**
- 90% interval of (P2 − P1) CG demeaned data-effect share, using independent streams.
- Equivalence bound = max(|lo|, |hi|).

**H4c: the redefinition adds nothing (difference-in-differences).**
- D = [mean_use log R(P2) − mean_use log R(P1)] − [mean_sec log R(P2) − mean_sec log R(P1)].
  Use-based = 4 categories; sectors = Mining, Manufacturing, Electricity; R = primary ratio.
- Report the 90% interval (independent streams) and the bound as a ratio exp(max |end|).
- Sensitivity, fixed now: Manufacturing alone as the sector control, because Electricity's very
  small P1 ratio (about 0.03) could dominate the log contrast.

## Exploratory tests (2): Pair 3 only, unadjusted

**H6a: disagreement is larger where items are value-reported.**
- Value share = weight of item groups whose accounting unit is "Rs. Crore" or "Rs. Lakhs",
  divided by the division's weight, from the 2011-12 item list (MoSPI 12 May 2017, Appendix I;
  407 item groups; division totals checked against Table B.2).
- Statistic: Spearman ρ between value share and the P3 division R. Primary: 6-month change
  ratio (10 dates). Secondary: demeaned level ratio (21 months).
- H0: ρ ≤ 0. Monte Carlo permutation, 99,999 draws. An exact enumeration over 23! orderings is
  infeasible; this replaces the plan's "exact permutation".

**H6b: value share tracks the vintage revision.**
- Spearman ρ between value share and |FY2025-26 growth, 29 June vintage − 1 June vintage| by
  division. The 1 June figures are from Statement II A of the 1 June release.
- Secondary: |Δ log FY2024-25 annual index| between the vintages.
- H0: ρ ≤ 0, permutation as in H6a.
- Caveat: the 29 June release also revised source data and the Electricity index, so the
  revision is not a pure deflator change.

## Exploratory replications (unadjusted, never pooled)

H1a, H2, H3b, H3c and H5a are rerun on P3 (both vintages). Shift tests are not possible in P3,
which has only 13 dates.

## Not tested

Individual episodes (illustrations only) and splice arithmetic.
