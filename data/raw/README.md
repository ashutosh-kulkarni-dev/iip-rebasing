# Raw inputs and provenance

All IIP data come from MoSPI, Government of India. Retrieval dates are the download
timestamps of the files (IST). SHA-256 checksums let anyone confirm they hold the same files.

| File | Content | Source | Retrieved | SHA-256 |
|---|---|---|---|---|
| `esankhyiki_2022-23_iip_166.xlsx` | Base 2022-23, monthly, Apr 2023 to Dec 2025: General, sectors and sub-sectors, 23 manufacturing industries, six use-based categories | eSankhyiki portal, https://esankhyiki.mospi.gov.in/ (IIP data export) | 17 Oct 2026 | `355f81e68835fcd7c64fa58c191f6cc403699b8e01f9c21583d20e7a1d7753af` |
| `esankhyiki_2022-23_iip_6.xlsx` | Base 2022-23, same series, months January to August of 2023 to 2026 (export filter); overlaps iip_166 in 21 months, where the two agree exactly | eSankhyiki portal | 17 Oct 2026 | `6802b5ce92128181a94a2ff3e9ef9394c66b9ff4ff40f9d5545ef8dff55a62b1` |
| `esankhyiki_2011-12_iip_68.xlsx` | Base 2011-12, monthly, Apr 2012 to Dec 2025, incl. 23 manufacturing industries and all six use-based categories | eSankhyiki portal | 17 Oct 2026 | `49d541b09528d3e6795c8338ade891a28817389e98e52d8f1d61d1f6b67d4545` |
| `mospi_iip_2022-23_first_release_2026-06-01.html` | First press release of the 2022-23 series (1 June 2026), as saved from the PIB page: Statements I-III, weight tables B.1 and B.2, annual growth comparison with the 2011-12 base | Press Information Bureau / MoSPI | 17 Oct 2026 | `e1a135c86170727d381419e0eca4da6f7bbf029a1a48b783f6a36188d83f79d9` |
| `linking_factor.pdf` | "Linking Factor for IIP": method and the four official 2011-12 to 2022-23 factors | MoSPI | 17 Oct 2026 | `afc9b511827d3585719af6085ee489052ba4155c129aaca88d771454ebbb041b` |

## Which 2022-23 series

Two official versions of the 2022-23 series exist. The first release (1 June 2026) was
superseded by MoSPI's release of 29 June 2026, which replaced the WPI deflator with the
Output PPI, incorporated updated source-agency data from April 2022, and corrected the
Electricity index. The eSankhyiki files are the revised series: they reproduce the 29 June
2026 annual growth figures to within 0.1 pp (`results/validation_v3_summary.csv`). The
analysis uses eSankhyiki; the 1 June version is kept for comparison.

## Older bases (not redistributed)

`data/clean/tidy_long.csv` holds the 1993-94, 2004-05 and 2011-12 series (General, Mining,
Manufacturing, Electricity and the four common use-based categories) as cleaned for v1 of
this repository from MoSPI/eSankhyiki exports in long format
(`year, month, type, category, sub_category, index, growth_rate`). The original exports
(`1993-94.xlsx`, `2004-05.xlsx`, `2011-12.xlsx`) are needed only to rerun
`pipeline/load_clean.py`. Its 2011-12 series is identical to `esankhyiki_2011-12_iip_68.xlsx`
in every common month (checked in `build_data.py`); the retrieval date of the older exports
was not recorded.

## Official documents used for validation (not redistributed; tables transcribed in `data/official/`)

* CSO/MoSPI (2011), note on the revision of the IIP base year to 2004-05, dated 29 Nov 2011,
  Section 4.2, Tables 4.2.1-4.2.3.
  https://www.mospi.gov.in/sites/default/files/iip/base_revision_2004-05_29nov11.pdf
* MoSPI (2017), press release on the IIP with base 2011-12, 12 May 2017, Statement III.
  https://www.mospi.gov.in/sites/default/files/iip/iip_PR_12may17.pdf
* MoSPI (2026), IIP press release for May 2026, 29 June 2026, Statements I and III.
  https://www.mospi.gov.in/uploads/latestReleases/latest_release_1782727994645_1af6a37e-b7fb-4ee8-bf52-96fcea2a47e2_IIP_Press_release_May_2026.pdf

## Outside benchmark (in `data/official/`, transcribed from official tables)

* `asi_output.csv`: ASI all-India value of output, current prices (Rs lakh). 2004-05 to 2016-17 from RBI Handbook of
  Statistics on Indian Economy 2022-23, Table 124 (https://www.rbi.org.in/Scripts/PublicationsView.aspx?id=22188);
  2004-05 to 2009-10 and 2013-14 confirmed against MoSPI ASI press notes / Volume I; 2017-18 onward from MoSPI ASI
  press notes, including the ASI 2024-25 note of 30 Sep 2026. Covers all ASI sectors (mostly manufacturing).
  ASI changed its treatment of non-operating units in 2010-11.
* `wpi_manufactured.csv`: WPI Manufactured Products, annual averages. Base 2004-05 from Economic Survey 2017-18
  Statistical Appendix Table 5.4; base 2011-12 from RBI Handbook 2025-26 Table 33
  (https://rbi.org.in/Scripts/PublicationsView.aspx?id=23858). Implied inflation matches published WPI
  manufactured-products inflation to within 0.1 pp in every year checked.

All values were read from the official web pages with a text-extraction tool on 17 Oct 2026; each row records its
source table and URL. Spot-check single-source years (2011-12, 2012-13, 2014-15, 2015-16, 2016-17 ASI) against the
original tables before publication.
