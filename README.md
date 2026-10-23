# Which sectors survive rebasing? Cross-base agreement in India's IIP

Replication code, data and results for the paper (working title)
**"Which Sectors Survive Rebasing? Cross-Base Agreement in India's Index of Industrial Production"** (earlier drafts: "Official but Different: How Much India's Industrial Production Base Years Disagree")
by Ashutosh Kulkarni, Caxton Emerald S and Radhalakshmi K N
(CHRIST (Deemed to be University), Bengaluru, 2026).

## What the pipeline does

India's IIP has four base years: 1993-94, 2004-05, 2011-12 and 2022-23. Every pair of
consecutive bases was published in parallel for a while, so the same months were measured
twice. The pipeline compares the two measurements over each overlap:

| Pair | Older / newer base | Overlap | Months of true YoY in both |
|---|---|---|---|
| 1 | 1993-94 / 2004-05 | Apr 2005 to Jun 2011 | 63 (Apr 2006 to Jun 2011) |
| 2 | 2004-05 / 2011-12 | Apr 2012 to Mar 2017 | 48 (Apr 2013 to Mar 2017) |
| 3 | 2011-12 / 2022-23 | Apr 2023 to Mar 2026 | 24 (Apr 2024 to Mar 2026) |

Why "true YoY": no base publishes monthly indices for its own base year, and the growth
rates published for a base's first 12 months equal `index - 100`. They measure the level
against a flat base year, not growth, so monthly comparisons start in month 13
(`validate.py`, check V2). Annual growth for the first year is still exact.

## Run

```bash
pip install -r requirements.txt
python pipeline/run_all.py        # from the repository root
```

| Stage | Script | Output |
|---|---|---|
| 0 (optional) | `load_clean.py` | rebuilds `data/clean/tidy_long.csv` (1993-94, 2004-05, 2011-12) from the original Excel exports, which are not redistributed |
| 1 | `build_data.py` | `data/clean/iip_monthly.csv` (all four bases), the 1 June 2026 version of the 2022-23 series, 23 manufacturing industries, the official tables in the 1 June 2026 release |
| 2 | `validate.py` | `results/validation_v1..v5_*.csv`; **stops the pipeline if an enforced check fails** |
| 3 | `overlaps.py` | `results/overlap_stats.csv`, `overlap_annual.csv`, `overlap_industries_pair3.csv` |
| 4 | `decomposition.py` | `results/decomposition_pairs.csv`, `gfc_measures.csv`, `gfc_decomposition.csv` |
| 5 | `splice.py` | `results/splice_series.csv`, `splice_summary.csv` (three rules: new base first; old base last, linked at the switch point; old base last, linked with the base-year factor so the overlap drift becomes a jump at the switch) |
| 5b | `benchmark.py` | `results/asi_benchmark.csv`, `asi_benchmark_summary.csv` (ASI real output vs IIP manufacturing) |
| 5d | `episodes.py` | `results/episodes.csv` (GFC, 2012-14 slowdown and demonetisation in each base and each spliced series) |
| 5e | `noise.py` | `results/noise_overlap.csv`, `noise_changes.csv`, `noise_placebo.csv`, `noise_annual_gaps.csv`, `noise_contributions.csv` (persistent gap; disagreement about short-run changes, with thresholded direction shares; episode placebo against comparison windows that share no month with the event; annual gaps; category covariance shares of the squared disagreement) |
| 5f | `inference.py` | `results/inference.csv`, `inference_sensitivity.csv` (HAC intervals for the mean gaps; block-bootstrap intervals for RMSD, correlation, the capital goods + durables share and the disagreement-to-change ratio; effective window counts; block-length sensitivity). The episode placebo in `noise_placebo.csv` is not reported in the paper: the overlaps are too short for it to be informative. |
| 5c | `revision.py` | `results/deflator_revision.csv` (the two official versions of the 2022-23 series) |
| 6 | `charts.py` | `charts/fig1..3_*.png` |
| 7 | `paper_numbers.py` | `results/paper_numbers.json`, the registry of every number the paper quotes |

Shared settings (bases, overlaps, weights, windows, tolerances) are in `pipeline/config.py`,
each with its source. The pipeline is deterministic: the block bootstrap uses a fixed seed.

## Revision of October 2026: sectoral reliability

Stages added for the reframed paper ("Which sectors survive rebasing?"). **Read
[`results/FINDINGS.md`](results/FINDINGS.md) first**: it summarises every number with confidence tags.

| Stage | Script | Output |
|---|---|---|
| 5f | `inference.py` (rewritten) | mean gap by EWC, fixed-b Newey-West and annual t tests; stationary-bootstrap intervals with block counts and centring diagnostics |
| 5g | `splice_extra.py` | five splice rules (incl. overlap blend and 1-month vs 12-month link) for every series, incl. category splices; `splice_rules_by_series.csv` |
| 6a | `reliability.py` | A1 reliability ratios by sector, category and (Pair 3) industry, both 2022-23 vintages; `reliability.csv`, `reliability_intervals.csv`, `gap_inference.csv` |
| 6b | `diagnosis.py` | A2 diagnosis stability (leading contributor, sign flips, rank correlation) and episode contributions; `diagnosis_*.csv` |
| 6c | `sources.py` | A3 weight vs data split, demeaned shares, volatility benchmark, Pair 1 vs Pair 2 definitions test; `sources_*.csv` |
| 6d | `charts_reliability.py` | `charts/fig4_reliability.png`, `charts/fig5_episodes.png` |

### Plan v2: pre-specified tests

`tests_spec.md` (repository root) fixes every test, bound and decision rule. It was written
before `pipeline/tests.py`. **Results and their strength: [`results/RESULTS_v2.md`](results/RESULTS_v2.md).**

| Stage | Script | Output |
|---|---|---|
| 1b | `value_shares.py` | value-reported weight shares from the 2011-12 item list (`data/official/mospi2017_item_list_2011-12.csv`, checked against Table B.2); 1 June 2026 industry indices (`data/official/mospi2026jun01_industry_annual.csv`); `results/value_shares_2011-12*.csv`, `results/industry_vintage_revision.csv` |
| 7 | `tests.py` | 8 confirmatory tests, 5 bounds, 2 exploratory tests: `results/tests.csv`, `results/tests_h2_tiers.csv` |

Shared helpers: `harinf.py` (small-sample HAR tests and bootstraps; fixed-b critical values are
cached in `results/fixed_b_critical_values.json`). Requires `scipy`.

## Validation

`validate.py` checks the data against every official figure available:

* **V1** published monthly YoY = YoY recomputed from published levels (all bases).
* **V2** the first-year convention above.
* **V3** annual April-March growth against the official overlap tables: CSO (2011) Tables
  4.2.1-4.2.3 for pair 1; MoSPI (12 May 2017) Statement III for pair 2; and for pair 3, the
  MoSPI release of 29 June 2026 (eSankhyiki version of the 2022-23 series) and the
  first release of 1 June 2026 (its superseded version). Tolerance: 0.15 pp (see `config.py`).
  The 2011-12 side of pair 2 is reported but not enforced: the 2017 release printed the
  then-provisional 2011-12 series, and our data are the later revised series.
* **V4** linking factors recomputed with MoSPI's geometric-mean formula reproduce the four
  official 2011-12 to 2022-23 factors exactly; the two older factors use the same formula.
* **V5** the two official versions of the 2022-23 series, compared month by month.

## Data

See [`data/raw/README.md`](data/raw/README.md) for sources, retrieval dates and checksums,
and `data/official/` for the official tables used in V3 (each row cites its source table).

## Licence

Code: MIT (see [`LICENSE`](LICENSE)). The IIP data are published by MoSPI, Government of
India, and are redistributed here for reproducibility; please cite the original source.

## Paper draft

The current manuscript is `IIP_rebasing_paper_13.docx` (Springer LNCS layout). From v12 onwards the
paper is descriptive: it reports 95% block-bootstrap intervals for each overlap and no longer uses the
pre-specified tests, pooling, Holm adjustment or readability tiers. `tests_spec.md`, `pipeline/tests.py`
and `results/RESULTS_v2.md` are kept as the archived exploratory plan; the paper quotes from them only
the interval estimates and sensitivity checks listed below.

Where the numbers in the current paper come from:

| Paper | File |
|---|---|
| Table 3, Fig. 1 (R and intervals) | `results/tests_h2_tiers.csv` (columns `R`, `lo`, `hi`) drawn by `charts_reliability.py` |
| Single-source contrast and its intervals (Section 6.1) | `results/tests.csv`, rows `H1a group contrast` (blocks 12 and 6) and `H1a-geo` |
| Contrast with 3- and 12-month windows | `results/window_contrast.csv` (`window_contrast.py`) |
| Leader agreement, bounds, reversals | `results/tests.csv`, rows `H3b`, `H3c`, `H3-other` |
| Leader agreement against independent choice | `results/diagnosis_summary.csv`, `leader_same` and `leader_same_chance` |
| Weight vs data shares | `results/sources_*.csv` |

`paper/build_paper.py` and `paper/render.js` build an earlier draft (v9) and do not produce the
current manuscript, which was edited directly; do not use them to regenerate the paper.

Before submission: confirm that the repository cited in the paper (github.com/ashutosh-kulkarni-dev/iip-rebasing) is
public and matches this folder.
