# Results of the pre-specified tests (Plan v2), and how strong they are

Run of 18 Oct 2026. The spec (`tests_spec.md`) was written to your folder **before**
`pipeline/tests.py` existed. Every number below is in `results/tests.csv` (the H2 tiers are in
`tests_h2_tiers.csv`) and reproduces with `python pipeline/run_all.py`. An independent
recomputation, written from scratch, matched every H1a, H1b, H3b and H4a value. Tags: [Certain] =
computed and recomputed; [Likely] = strong inference; [Guessing] = interpretation.

## 0. The uncomfortable part first

**Of the 8 confirmatory tests, 3 pass (H1a, H1b, H4d) and 5 fail (H2 mostly, H3a, H3d, H5a,
H5b).** [Certain]

* **The "sectoral reliability" pillar is strong.** It is the only formally established core
  claim.
* **The "diagnosis changes" pillar holds only as a bound, not as a test.**
  - H3a fails: there is no evidence that the bases agree on the leading category beyond chance.
  - That is absence of agreement, not proof of disagreement.
  - The usable claim is the H3b bound: the leading category agrees **at most 48% (Pair 1) and
    41% (Pair 2)** of the time (95% upper bounds).
* **The "category splices" pillar fails formally.**
  - Category persistent gaps are not distinguishable from zero.
  - The drift numbers are still true arithmetic, but they sit inside the noise of the gap
    estimate.
* **Two claims from the 18 Oct memo do not survive.**
  - "General is unreadable in Pair 2" misses Holm at block 6 (adjusted p = 0.051).
  - "Concentration is mostly volatility" is reversed: H4d shows concentration significantly
    beyond volatility.

## 1. What changed before testing (fixes from the plan)

| Fix | Done | Effect |
|---|---|---|
| Official 1993-94 sector weights (10.47 / 79.36 / 10.17) and 2011-12 (14.373 / 77.633 / 7.994) | Yes | Pair 1 sector diagnosis unchanged at the reported precision [Certain] |
| Geometric-mean switch links | Yes | General old-base-last growth 5.00 → 4.99%; capital goods 5.38 → 5.36% [Certain] |
| June-vintage electricity | Excluded (only Electricity & Gas is published) | Pair 3 June results have 7 units |
| 2011-12 item list (Appendix I, 12 May 2017) | Transcribed: 407 item groups, 109 value-reported | Every division weight and item count reproduces Table B.2 exactly; use-based totals match [Certain] |
| 1 June vintage industry data | Parsed from Statement II A of the 1 June release | Used for H6b |
| NIC concordance, 23 divisions | One-to-one by code (Table B.2 pairs them); names map uniquely | Content changes inside a division are not checked [Likely fine] |
| March 2026, 2011-12 base | A quick estimate never finalised (your source check) | State it in the paper |
| Annual t tests | Labelled as a check (dependent gaps) | n/a |

One discrepancy with the plan to fix in the text: the plan says the two 2022-23 vintages "differ
only in the deflator". The 29 June release also updated source-agency data and corrected the
Electricity index (`data/raw/README.md`). Food has zero value-reported items, yet its FY2025-26
growth moved 0.56 pp between vintages. [Certain] So the vintage difference is not a pure
deflator effect, which weakens H6b as a deflator test.

## 2. Results by hypothesis

### H1: reliability is sectoral (strong)

| Test | Pair 1 | Pair 2 | Pooled | Decision |
|---|---|---|---|---|
| H1a group contrast, log R(stable) − log R(manufacturing-based) | −2.00 (−2.93, −1.18), p < 0.001 | −0.80 (−1.24, −0.13), p = 0.004 | Z = 4.58, p < 0.001 | **PASS** (negative in both pairs) |
| Electricity vs manufacturing | −3.52, p < 0.001 | −1.33, p = 0.001 | Holm p < 0.001 | holds |
| Mining vs manufacturing | −0.85, p = 0.013 | −1.28, p = 0.002 | Holm p < 0.001 | holds |
| Block 6 (sensitivity) | same signs | same signs | Z = 4.44, p < 0.001 | holds |
| H1b rank stability, Spearman ρ (7 units) | | | ρ = 0.857, exact p = 0.012 | **PASS** |

In ratio terms, Pair 1 electricity's change ratio is about 3% of manufacturing's (e^−3.5), and
mining's is about 43%. The ranking repeats across rebasings. Electricity and mining rank 1 and
2 in both pairs, and manufacturing, capital goods and durables are among the worst three or four
in both. [Certain]

Pair 3 (exploratory): electricity vs manufacturing holds (−3.55). **Mining vs manufacturing
does not** (+0.01, p = 0.76): in Pair 3, mining is as unreliable as manufacturing. [Certain,
24 months]

### H2: readability tiers (mostly "undetermined")

| Unit | Pair 1 R | Pair 2 R | Pair 1 tier | Pair 2 tier | Pooled tier |
|---|---|---|---|---|---|
| Electricity | 0.03 | 0.44 | readable | undetermined (adj. p 0.055) | **readable** |
| Mining | 0.37 | 0.46 | readable | readable | **readable** |
| Intermediate goods | 0.50 | 0.81 | readable | undetermined | **readable** |
| Consumer non-durables | 0.66 | 0.68 | undetermined | undetermined | undetermined (adj. p 0.044 at block 12, 0.091 at block 6) |
| General | 0.74 | **1.50** | undetermined | undetermined (unreadable at block 12, adj. p 0.029; misses at block 6, 0.051) | undetermined |
| Manufacturing | 0.87 | 1.65 | undetermined | undetermined | undetermined |
| Capital goods | 0.79 | 1.13 | undetermined | undetermined | undetermined |
| Consumer durables | 0.90 | 0.95 | undetermined | undetermined | undetermined |

**No unit is formally unreadable.** [Certain] The honest reading is: three units (electricity,
mining, intermediate goods) are readable on one base, and for the rest a single base cannot
establish whether short-run movements are readable. With 3-5 blocks per pair, that is the most
the data can say.

Pair 3 (exploratory, unadjusted): electricity, capital goods and durables are readable;
**mining is undetermined** (R = 1.59, p_unread = 0.09). The 18 Oct claim that Pair 3 mining is
"unreadable" is not supported.

### H3: the diagnosis changes (bound holds; tests fail)

| Quantity | Pair 1 | Pair 2 |
|---|---|---|
| H3a leader agreement vs circular-shift null | 0.31, p = 0.40 (29 shifts) | 0.30, p = 0.20 (14 shifts; min. attainable p 0.067) |
| H3a pooled | p = 0.23 → **FAIL: no evidence of agreement beyond chance** | |
| Harris (2020) check, conservative p | 1.00 | 0.23 |
| **H3b agreement, margin ≥ 0.1 pp in both (primary)** | **0.34 (47 dates), at most 0.48** | **0.31 (32 dates), at most 0.41** |
| Margin ≥ 0.25 pp | 0.38 (34), at most 0.54 | 0.24 (17), at most 0.40 |
| Margin ≥ 0.5 pp | 0.48 (25), at most 0.65 | 0.14 (7), at most 0.67 |
| Unfiltered | 0.31, at most 0.44 | 0.30, at most 0.41 |
| H3c material sign flips (\|contribution\| ≥ 0.1 pp in both) | 24% (16-33%) of 183 unit-dates | 41% (31-50%) of 88 |
| H3c old-base leader ranked 3rd/4th of 4 in new base | 54% (37-73%) | 38% (24-51%) |
| H3c new-base leader ranked 3rd/4th of 4 in old base | 58% (44-73%) | 54% (43-65%) |
| H3d opposite direction of General (both moves > 1 pp) | 5% of 40 dates, p = 1.00 | 84% of 19 dates, p = 0.067 (the minimum attainable) |
| H3d pooled | **FAIL** (Pair 1's p = 1 makes pooling undefined) | |

Reading:

* **The near-tie worry is partly confirmed in Pair 1.** Agreement rises from 31% to 48% as the
  margin widens from 0 to 0.5 pp. In Pair 2 it falls. [Certain]
* Even so, the 0.1 pp primary bound says the leading category agrees at most about half the
  time in both pairs. [Certain]
* **Genuine reversals are common.** The leader on one base ranks in the bottom half of the other
  base on 38-58% of dates. This is the strongest anti-tie evidence. [Certain]
* **Direction disagreement is a Pair 2 phenomenon only.** In Pair 1 the bases agree on the
  direction of General 95% of the time. [Certain]

### H4: data, not weights or definitions (bounds informative; one test passes)

| Quantity | Result |
|---|---|
| H4a weight-effect share of MSD, 90% intervals, all units, Pairs 1-2 | Point estimates −0.03 to +0.04. **Bound b = 0.12** (driven by intermediate goods and "Other" in Pair 1); Pair 2 alone: 0.10 |
| H4b redefinition, P2 − P1 capital goods data share | +0.002, 90% interval (−0.21, +0.16). **Equivalence bound 0.21**, against a share of 0.48 |
| H4c difference-in-differences in log R, use-based vs all sectors | −1.00 (−1.83, −0.50): the categories deteriorated *less* than the sectors, driven by electricity's change from 0.03 to 0.44 |
| H4c sensitivity, manufacturing as the only control | −0.41 (−0.92, +0.15). Upper bound: categories at most **17% worse** relative to manufacturing (e^0.155) |
| H4d CG+CD data share minus volatility share | Pair 1 +0.25 (0.07, 0.41), p = 0.003; Pair 2 +0.16 (0.04, 0.38), p = 0.003; pooled p < 0.001 → **PASS** |

Reading:

* "Weights explain little" holds as a bound: at most about 12% of the mean squared
  disagreement. That is small next to the data effects (capital goods alone is about 47%). [Likely]
* The redefinition bound is moderate. We can rule out a redefinition effect larger than about
  0.21 of the gap variance, but not a smaller one. [Certain]
* The cleaner definitions evidence is H4c with manufacturing as the control: there is no sign
  that the 2017 redefinition degraded the use-based categories. [Likely]
* **Concentration exceeds volatility.** Capital goods and durables disagree more than their
  volatility alone predicts, in both pairs. This reverses the 18 Oct memo's "mostly volatility",
  which compared total shares, not data shares, and had no test. [Certain]
* Pair 3 shows no excess (−0.06 and −0.15). The concentration is an older-pairs phenomenon.

### H5: category gaps and splices (fails as a test; the arithmetic stands)

| | Pair 1 | Pair 2 | Pooled (EWC; fixed-b) | Decision |
|---|---|---|---|---|
| H5a capital goods mean gap (pp) | +4.5 (−12.9, 21.9) | +2.9 (−11.5, 17.3) | +3.5, p = 0.44; 0.44 | **FAIL** |
| H5a durables mean gap | +8.5 (−8.4, 25.4) | +5.8 (−8.1, 19.8) | +6.9, Holm p = 0.27; 0.33 | **FAIL** |
| H5b capital goods minus General | +3.9 | +0.6 | +2.0, p = 0.59 | **FAIL** |
| H5b durables minus General | +7.9 | +3.5 | +5.6, p = 0.18; 0.21 | **FAIL** |

What stands without a test (arithmetic, [Certain]):

* Capital goods level drift is −15.8% (Pair 1) and −19.0% (Pair 2); durables −32.4% and −25.0%.
* Capital goods growth over 2012-13 to 2016-17 is +0.2% a year (new base first) vs −3.7% (old
  base last).
* Capital goods long-run growth is 6.9% vs 5.4%; with a 1-month link window, 4.9%.

The paper can say: splice choice moves category growth by these amounts, and the underlying
gaps are too noisy to be called significant. It cannot say "significant drift".

The General gap in Pair 2 stays fragile (EWC −0.4 to 5.1; fixed-b 0.1 to 4.5).

### Pair 3 and H6 (exploratory)

* **Capital goods gap:** +2.1 pp revised (EWC p = 0.027; fixed-b p = 0.032) and +3.5 pp on the
  1 June vintage (0.015; 0.007). Both methods exclude zero on both vintages, but over 24 months
  and two calm years. [Certain for the numbers]
* **Durables gap minus General:** −2.1 pp (p = 0.037) revised, −1.4 pp June (0.016).
* **H6a**, value share vs Pair 3 industry reliability:
  - Primary (change ratio): ρ = 0.23, p = 0.14 → **FAIL**.
  - Secondary (level ratio): ρ = 0.45, p = 0.017.
* **H6b**, value share vs vintage revision:
  - Primary (\|Δ FY2025-26 growth\|): ρ = 0.35, p = 0.053 → **FAIL**, narrowly.
  - Secondary (\|Δ log FY2024-25 index\|): ρ = 0.43, p = 0.020.
  - The revision is not a pure deflator change.
* **Reading:** the signs point the way the deflation story predicts, but both primary tests fail.
  It can be reported as "suggestive, not established". [Likely]

## 3. Strength verdict per pillar

| Pillar | Verdict | What the paper can claim |
|---|---|---|
| Reliability is sectoral (H1) | **Strong.** Two tests pass, robust to block length, pattern repeats across rebasings | "Stable-source sectors (electricity, mining) are far more reliable across rebasings than manufacturing-based units; the ranking repeats." |
| Tiers (H2) | **Weak as tiers.** Only 3 units are formally readable; none is formally unreadable | "Three units are readable on one base; for the rest, one base cannot settle it." Present the undetermined tier as the finding |
| Diagnosis changes (H3) | **Moderate, as a bound.** Tests fail; the bound and reversal shares are informative | "The leading category agrees at most ~half the time; the leader on one base is often in the bottom half of the other." Avoid "significantly different diagnoses" |
| Data, not weights (H4) | **Moderate to strong.** Bounds are informative; H4d passes | "Weights account for at most ~12% of the disagreement; no sign the 2017 redefinition degraded categories; capital goods and durables disagree beyond their volatility." |
| Category splices (H5) | **Weak as a test, strong as arithmetic** | "Splice choice moves category growth by X; the gaps are too noisy to test." |
| Pair 3 and H6 | **Exploratory leads only** | Capital goods gap on both vintages; deflation channel suggestive |

**[Likely] Bottom line:** the evidence supports a narrower thesis than Plan v2's: *reliability
is sectoral and stable across rebasings, and comes from the data, not the weights; the sectoral
diagnosis of slowdowns is fragile.* "Systematic heterogeneity" is established. "Changes
conclusions" is established only as a bound plus the episodes.

## 4. For your goal: a Scopus-indexed conference

[Likely] This is more than enough evidence for a conference paper. The risk now is not too
little evidence but too much machinery for 6-10 pages and a 15-minute talk.

* **Keep in the main text:**
  - H1a and H1b (one table, one figure).
  - The H2 tier table with "undetermined" framed as the finding.
  - The H3b bound and reversal shares, with the GFC and demonetisation figure.
  - H4a, H4c and H4d in one small table.
  - The splice arithmetic, in one paragraph.
* **Put in an appendix or the repo:** H3a/H3d/Harris, H4b, H5, block sensitivity, Pair 3 and H6.
* **Methods paragraph:** one paragraph naming the joint stationary bootstrap, EWC and fixed-b,
  the circular-shift nulls, Holm and Stouffer, with citations. Plus one sentence that the tests
  were specified after the descriptive analysis and before being run, and that all results,
  including failures, are in the appendix.
* [Guessing] Conference reviewers will mostly check clarity, the novelty of the design
  (parallel bases as a measurement experiment) and honest limitations. Failed tests reported
  openly read as rigour, not weakness.
