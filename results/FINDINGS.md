# What the revised analysis shows: numbers and how far to trust them

Run of 18 Oct 2026. Every number below is in a CSV in `results/` (file named in each section)
and is reproduced by `python pipeline/run_all.py`. Confidence tags: **[Certain]** = computed and
independently recomputed; **[Likely]** = strong inference from the numbers; **[Guessing]** =
interpretation that goes beyond what the data can show.

"pp" = percentage points of YoY growth. Ratio < 1 = short-run movements readable on either
base; > 1 = not readable on a single base. Pair 1 = 1993-94 vs 2004-05 (63 months),
Pair 2 = 2004-05 vs 2011-12 (48), Pair 3 = 2011-12 vs 2022-23 (24, descriptive only).

---

## 0. The uncomfortable results first

1. **Almost nothing is statistically "robust" at these sample sizes.** Our own rule (the
   interval must sit on one side of 1 at both bootstrap block lengths) passes only a few cells.
   On the headline 6-month change ratio: **Mining and Electricity (Pairs 1 and 2) and
   Intermediate goods (Pair 1) robustly below 1, and General (Pair 2) robustly above 1.** On the
   demeaned level ratio, General and Manufacturing (Pair 1) are also robustly below 1. Every
   other cell is "not robust", including every capital goods and durables cell. The bootstraps rest on
   3-5 expected blocks. The reliability table is a **descriptive** table with honest error bands,
   not a test. [Certain]
2. **The Pair 2 persistent gap (2.3 pp) is fragile, as the plan anticipated.** Fixed-b NW
   excludes zero (0.1 to 4.5); EWC does not (-0.4 to 5.1); the 4-year annual t test does not
   (-0.03 to 4.72); the 5-year one does (0.7 to 3.9). It cannot be called "clearly different
   from zero". [Certain]
3. **"Which category led the slowdown" barely agrees across bases more often than chance would
   predict.** In Pair 1 the leading use-based category is the same in both bases at 31% of dates
   against 29% expected by chance; in Pair 2 it is 30% against 22%. [Certain for the numbers;
   ~1-4 independent windows]
4. **The 2017 redefinition is not what makes capital goods disagree.** Capital goods' share of
   the (demeaned) disagreement is 0.48 in Pair 1, with no redefinition, and 0.48 in Pair 2, with
   it. The difference is -0.00 (-0.20 to 0.23). [Likely]
5. **Re-weighting explains almost none of the disagreement.** Durables' weight rose by more than
   50% at two rebasings, yet the weight effect is at most ±0.04 of the mean squared difference
   (MSD) for every category in Pairs 1-2. It is the underlying data. [Certain within the
   decomposition]
6. **Capital goods' "concentration" is mostly its volatility.** Capital goods + durables have
   0.71 (Pair 1) and 0.64 (Pair 2) of the demeaned disagreement, against volatility benchmarks of
   about 0.48 and 0.50. The excess (+0.23 and +0.14) is real but much smaller than the 73% / 61%
   headline of the current draft. [Likely]
7. **The category-splice warning is not specific to 2017.** Capital goods' level drift is -15.8%
   at the 2004-05 joint (no redefinition) and -19.0% at the 2011-12 joint (with the redefinition).
   Durables drift -32.4% and -25.0%. Category splices are unsafe at **every** joint, not just
   across the redefinition. [Certain for the drift numbers]

What survives well: **sectors with stable data sources (Electricity, Mining in Pairs 1-2) are
readable on either base; manufacturing-heavy aggregates and the volatile use-based categories
are borderline to unreadable; and the episode diagnoses change sharply across bases.** That is
the paper.

---

## 1. Repo reconciliation and data checks

| Item | Finding |
|---|---|
| Bootstrap code | Present (`inference.py`), now rewritten (stationary bootstrap; reports blocks, bootstrap median, centring). [Certain] |
| Ratio definition | Unified on **ratio of medians** (paper: 2.047 / 1.361 = 1.50). `noise.py` no longer reports the median of per-date ratios (bounded at 2). [Certain] |
| Reproduction | All earlier headline numbers reproduce exactly (mean gaps 0.62 / 2.33 / 0.92; RMSD 4.79 / 3.70 / 1.55; correlation 0.67 / 0.37 / 0.80; drift -2.9 / -10.6 / -2.4%). `build_data.py` rebuilds clean data byte-identical. [Certain] |
| 1993-94 sector weights | Added (10.473 / 79.358 / 10.169) for the sector diagnosis. **Not transcribed from an official table**; regression of General on sectors recovers 10.46 / 79.38 / 10.14. Check against CSO (2011) before publishing. [Likely] |
| Industry data for 1993-94 / 2004-05 | Not in the repo; I did not check eSankhyiki. Industry analysis is **Pair 3 only** for now. [Certain that it's absent here] |
| A4 gate (value-reported items by industry) | **Not passed.** The MoSPI FAQ on the 2022-23 series and the microdata catalogue entry describe the method (WPI deflation of value-based items) but publish no item list with reporting type. A4 not run. [Likely: such a list may exist in the technical report; not found] |
| Status of the last 2011-12-base months (Jan-Mar 2026) | **Unresolved.** Nothing in the data or the FAQ says whether they were revised to final before the base was retired. [Unknown] |
| Pair 3 June vintage | Publishes only Electricity & Gas Supply, not Electricity (NIC 351). Its "Electricity" row compares different units; flagged in every output. [Certain] |

## 2. Inference fix (`gap_inference.csv`, `inference.csv`, `inference_sensitivity.csv`)

Methods: EWC (ν = ⌊0.4 T^(2/3)⌋: 6 / 5 / 3), fixed-b Newey-West (M = ⌈1.3√T⌉: 11 / 10 / 7;
critical values 2.44 / 2.55 / 2.83, simulated), annual t tests. The decision rule was fixed
before results: "different from zero" only if all four intervals exclude zero.

**General index mean gap (new - old), pp**

| | Estimate | EWC | Fixed-b NW | Annual t (all yrs) | Annual t (true-YoY yrs) | Verdict |
|---|---|---|---|---|---|---|
| Pair 1 | 0.62 | -3.6 to 4.8 | -3.3 to 4.5 | -3.6 to 4.6 (n=6) | -4.9 to 5.8 (n=5) | not distinguishable from 0 |
| Pair 2 | 2.33 | -0.4 to 5.1 | 0.1 to 4.5 | 0.7 to 3.9 (n=5) | -0.03 to 4.7 (n=4) | **fragile** |
| Pair 3 (revised) | 0.92 | -1.0 to 2.9 | -0.5 to 2.3 | -1.0 to 2.8 (n=3) | -8.8 to 10.6 (n=2) | not distinguishable |
| Pair 3 (1 June) | 1.32 | -1.1 to 3.8 | -0.5 to 3.2 | -1.5 to 3.8 | -11.6 to 14.2 | not distinguishable |

Bandwidth sensitivity for Pair 2: fixed-b excludes zero at M = 7, 10 and 14 (lower bounds
0.38, 0.13, 0.02); EWC excludes it only at ν = 7 (0.12). [Certain]

Across all 26 unit-pair cells (sectors and categories), only **Pair 3 capital goods** has all
four intervals excluding zero (+2.1 pp; EWC 0.5 to 3.7; annual gaps 3.8, 2.3, 2.1). On the
1 June vintage it is +3.5 pp. With T = 24 and n = 2-3 years, treat this as a lead, not a
finding. Pair 2 manufacturing is fragile like General. [Certain for the numbers]

**Bootstrap diagnostics.** The draft's Pair 3 correlation interval (0.78-0.93 around 0.80) was a
**moving-block artefact**: only 10% of the moving-block draws fall below the point estimate. The
stationary bootstrap gives **0.80 (0.68 to 0.91)**, with 37% of draws below, close to centred.
All General-index bootstrap intervals rest on 4-5 expected blocks and are flagged "coarse".
[Certain]

| Stationary bootstrap, mean block 12 (6 in Pair 3) | Pair 1 | Pair 2 | Pair 3 |
|---|---|---|---|
| RMSD | 4.79 (3.64-5.73) | 3.70 (2.83-4.44) | 1.55 (1.22-1.83) |
| Correlation | 0.67 (0.49-0.81) | 0.37 (0.15-0.61) | 0.80 (0.68-0.91) |
| Cap. goods + durables share of MSD | 0.73 (0.56-0.91) | 0.61 (0.52-0.77) | 0.20 (0.10-0.25) |
| 6-month change ratio | 0.74 (0.41-1.05) | 1.50 (1.18-2.04) | 0.74 (0.36-1.29) |
| Expected blocks | 5.3 / 4.3 | 4.0 / 3.1 | 4.0 / 2.2 |

## 3. A1: reliability by sector (`reliability.csv`, `fig4_reliability.png`)

Headline: the **6-month change ratio** = median |disagreement in 6-month changes| / larger median
|6-month change|. A constant gap cancels in a change, so this ratio is already free of the
persistent gap. Second measure: the **demeaned level ratio** = SD(gap) / larger SD of YoY. The
range is the widest 95% interval across the two block lengths.

| Unit | P1 change ratio | P1 level (dm) | P2 change ratio | P2 level (dm) | P3 change | P3 level (dm) |
|---|---|---|---|---|---|---|
| General | 0.74 (0.40-1.07) | 0.75 robust<1 | **1.50 (1.06-2.04) robust>1** | 1.02 | 0.74 | 0.61 |
| Mining | **0.37 robust<1** | 0.28 robust | **0.46 robust<1** | 0.61 robust | 1.59 | 1.25 |
| Manufacturing | 0.87 (0.41-1.07) | 0.77 robust<1 | 1.65 (0.89-2.17) | 1.04 | 1.58 | 0.77 |
| Electricity | **0.03 robust<1** | 0.03 | **0.44 robust<1** | 0.50 robust | 0.05 | 0.01 |
| Capital goods | 0.79 (0.37-1.68) | 0.96 | 1.13 (0.62-2.12) | 1.16 | 0.25 | 0.87 |
| Intermediate | **0.50 robust<1** | 0.62 robust | 0.81 (0.53-1.57) | 0.92 | 0.64 | 0.95 |
| Cons. durables | 0.90 (0.50-1.50) | 1.31 | 0.95 (0.72-1.41) | 0.99 | 0.54 | 0.69 |
| Cons. non-durables | 0.66 (0.48-1.00) | 0.80 | 0.68 (0.50-1.35) | 1.21 | 0.82 | 1.03 |
| Primary (P3 only) | | | | | 0.82 | 0.67 |
| Infra/construction (P3 only) | | | | | 0.32 | 0.33 |

Readings:

* **Electricity** is close to identical across bases: RMSD 0.08 pp in Pair 1 and 0.05 pp in
  Pair 3 (revised vintage). Pair 2 is the exception (ratio 0.44). [Certain] That the bases share
  the CEA source data for electricity is my explanation, not something the repo shows. [Guessing]
* **Mining** is readable in Pairs 1-2 but **not in Pair 3** (change ratio 1.59, level 1.25),
  where the 2022-23 base split mining into three groups and cut its weight from 14.4 to 11.1.
  [Certain for the ratios; the cause is a guess]
* **Manufacturing and General are borderline in Pair 1 and unreadable in Pair 2.** In Pair 2,
  disagreement about 6-month changes is 1.5 times the size of the changes themselves. [Certain;
  robust only for General]
* **The volatile use-based categories (capital goods, durables) sit near 1 everywhere**, with
  intervals that span 1. They are not demonstrably unreadable; they are demonstrably not
  reliable. [Likely]
* The 12-month change ratios (column `R_chg_12`) have 40 / 25 / 1 dates (1.7 / 1.0 / 0.04
  independent windows). Ignore them for Pair 3.

**Pair 3 industries (21 months; descriptive):** median demeaned level ratio 0.79 and median change
ratio 0.71. **8 of 23 industries exceed 1 on the level ratio** and 7 on the change ratio.
Worst: pharmaceuticals 1.30, electrical equipment 1.29 (correlation -0.21), printing 1.20, wood
1.18, computers/electronics 1.12. Best: coke & refined petroleum 0.33, other manufacturing
0.41, paper, food and basic metals about 0.5. [Certain] The best are mostly homogeneous,
quantity-measured products, consistent with the deflation channel, but A4 could not test it.
[Guessing]

**Vintage (1 June vs 29 June 2026):** the Pair 3 General mean gap is 1.32 on 1 June and 0.92
revised. Capital goods is +3.5 vs +2.1. The revision moved 2024-25 Electricity & Gas growth by
-4.25 pp and Primary goods 2025-26 by -2.45 pp. Pair 3 conclusions are vintage-dependent.
[Certain]

## 4. A2: does the diagnosis change? (`diagnosis_summary.csv`, `diagnosis_episodes.csv`, `fig5_episodes.png`)

"Leader" = the unit contributing most in the direction of each base's own change in General
growth. "Chance" = agreement expected if the bases picked leaders independently with their
observed frequencies.

| 6-month windows | Dates (indep.) | General moves same direction | Leader same | Chance | Mean share of units with sign flip | Median Spearman |
|---|---|---|---|---|---|---|
| P1 sectors | 52 (4.3) | 85% | 92% | 92% | 9% | 1.00 |
| P1 use-based | 52 (4.3) | 85% | **31%** | 29% | 26% | 0.35 |
| P2 sectors | 37 (3.1) | **41%** | 57% | 53% | 37% | -0.50 |
| P2 use-based | 37 (3.1) | 41% | **30%** | 22% | 38% | 0.30 |
| P3 sectors | 13 (1.1) | 77% | 54% | 53% | 28% | 0.50 |
| P3 use-based | 13 (1.1) | 77% | 54% | 33% | 35% | 0.00 |

The pattern is the same at dates where General moves more than 1 pp in both bases. For Pair 2,
those 19 dates (1.6 independent windows) show the **two bases moving General in opposite
directions 84% of the time**. Sector leader agreement is mechanical: manufacturing carries 75-79%
of the weight, so it nearly always leads and chance is 92%. The informative sector measures are
the sign flips and the direction of General. [Certain]

**Episodes (contributions, pp of General YoY growth):**

* **GFC (Pair 1), 12 months from Sep 2008 vs 12 before:** General slows -2.9 pp (old) vs
  **-11.4 pp (new)**. Capital goods -0.9 vs **-5.2**; durables **+0.6 vs -2.5** (sign flip).
  Leader: consumer non-durables (old) vs **capital goods (new)**. Leaders differ at all three
  windows (6/6, 12/12, 24/19). Manufacturing: -2.9 vs -11.5. [Certain] "Capital goods led the
  GFC slowdown" is true only on the 2004-05 base.
* **Demonetisation (Pair 2), Nov 2016-Mar 2017 vs Apr-Oct 2016:** General **+2.5 (old) vs -2.3
  (new)**, opposite signs. Capital goods +3.3 vs -0.2; leader capital goods (old) vs consumer
  durables (new). Leaders differ at every window (7/5, 5/5, 4/5, 12/5); the General sign flips
  at all four. [Certain] The Economic Survey 2016-17 already noted the base disagreement here,
  so this example is not new.
* **2012-14 slowdown (Pair 2), contributions to annual growth (2012-13/2013-14 average):**
  General 0.5 (old) vs 3.3 (new). Durables **-0.76 vs +0.68** (sign flip); capital goods -0.65
  vs -0.13. The weakest category is durables (old) vs capital goods (new). Manufacturing
  contributes 0.2 vs 3.3. [Certain]

## 5. A3: sources of disagreement (`sources_by_category.csv`, `sources_definitions_test.csv`)

Shares of the demeaned disagreement (cov(gap_c, total gap) / var(total gap)), split into
weight and data effects, against a volatility benchmark (each category's share of the variance
of General growth within a base, averaged over the two bases):

| | P1 total | P1 weight | P1 volatility | P2 total | P2 weight | P2 volatility | P3 total | P3 volatility |
|---|---|---|---|---|---|---|---|---|
| Capital goods | 0.47 | -0.01 | 0.35 | 0.49 | 0.01 | 0.29 | -0.03 | 0.05 |
| Cons. durables | 0.24 | -0.01 | 0.13 | 0.15 | -0.03 | 0.22 | 0.18 | 0.18 |
| Intermediate | 0.08 | -0.01 | 0.20 | 0.01 | 0.00 | 0.09 | 0.13 | 0.13 |
| Cons. non-durables | 0.09 | -0.01 | 0.16 | 0.12 | 0.00 | 0.12 | **0.41** | 0.20 |
| Other (basic etc.) | 0.13 | 0.02 | 0.18 | 0.22 | 0.00 | 0.30 | 0.31 | 0.45 |
| Manufacturing (sector) | 1.00 | -0.02 | 0.95 | 0.96 | -0.01 | 0.84 | 0.79 | 0.66 |

* Weight effects are negligible for every unit; the largest is intermediate goods in Pair 3
  at 0.11 of the raw MSD. [Certain]
* **Definitions test:** capital goods' demeaned data share is 0.478 in Pair 1 vs 0.480 in Pair 2;
  difference -0.002 (-0.20 to 0.23). For capital goods + durables: 0.72 vs 0.65, difference
  +0.07 (-0.17 to 0.23). The redefinition adds nothing detectable. [Likely; the intervals are
  wide]
* Pair 3 concentrates in **consumer non-durables** (0.41 vs a volatility share of 0.20), not
  capital goods. [Certain, 24 months]

## 6. Secondary: splicing (`splice_summary.csv`, `splice_rules_by_series.csv`)

Average annual growth, 1994-95 to 2025-26:

| Series | New base first | Old base last (12-m link) | Old base last (1-m link) | Base-year factor at switch | Overlap blend |
|---|---|---|---|---|---|
| General | 5.56 | 5.00 | 4.94 | 5.47 | 5.56 |
| Manufacturing | 5.94 | 5.16 | 5.09 | 5.84 | 5.93 |
| Capital goods | 6.94 | 5.38 | 4.88 | 6.69 | 6.94 |
| Consumer durables | 8.02 | 5.71 | 6.24 | 8.06 | 8.03 |
| Mining | 2.74 | 2.96 | 2.95 | 2.86 | 2.74 |

* The link window matters little for General (5.00 vs 4.94) but a lot for capital goods (5.38
  vs 4.88) and durables (5.71 vs 6.24). Any category splice must state its link window. [Certain]
* Average capital goods growth over 2012-13 to 2016-17 is +0.2% (new base first) vs -3.7%
  (old base last): the sign of the period's capital goods story depends on the splice. [Certain]
* Level drift of the linked old base vs the new base at the end of each overlap: capital goods
  -15.8 / -19.0 / -6.6%, durables -32.4 / -25.0 / +1.1%, General -2.9 / -10.6 / -2.4%.
* The overlap blend tracks "new base first" in long-run growth, as it must by construction
  (both end on the new base). It is a smoother bridge, not a different estimate.
* Pair 2's drift is 68% of the General splice-level difference (log terms), as before.
  [Certain]

## 7. What changed in the code

New: `harinf.py` (EWC, fixed-b NW with simulated critical values, annual t, stationary and
moving-block bootstraps), `reliability.py` (A1 + per-unit gap inference), `diagnosis.py` (A2),
`sources.py` (A3), `splice_extra.py`, `charts_reliability.py`. Changed: `inference.py`
(rewritten), `noise.py` (ratio of medians), `common.py` (unit loaders), `config.py` (1993-94
sector weights), `splice.py`, `charts.py` and README (neutral wording; no "misuse"),
`run_all.py`. Not done: A4 (gate failed), break tests on spliced series (optional), literature.

An independent recomputation, from scratch and without the pipeline's code, matched every
number checked (Section 1-4 headline values, the EWC and annual-t intervals, the GFC
contributions, leader agreement). It flagged three issues, all fixed: correlated bootstrap
streams in two Pair 1 - Pair 2 difference intervals; an incomplete Pair 3 blend in the overlap
splice; and arithmetic-mean link factors, now documented. A further caveat stands: consecutive
annual gaps share a year's level, so the annual t tests treat dependent observations as
independent.

## 8. What this implies for the paper (to decide before writing)

* Lead with A2, not A1. The diagnosis instability (leaders near chance; sign flips in 26-38% of
  units; the GFC and demonetisation reversals) is the strongest and most original result. The
  reliability table is the user-facing deliverable, but most of its cells are "not robust".
* Drop "capital goods drives the disagreement because of the redefinition" entirely. Replace it
  with: disagreement concentrates in the most volatile categories, slightly beyond their
  volatility, and is driven by data rather than weights, with or without a redefinition.
* Rewrite the splice guidance: category splices are unsafe at every joint, and the link window
  must be stated.
* Pair 3: report capital goods' +2.1 pp gap and mining's unreliability as provisional leads,
  with both vintages.
