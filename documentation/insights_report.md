# Business Insights Report
## Luxury Housing Sales, Bengaluru — 2023-Q2 to 2025-Q1

Prepared from 100,000 cleaned property transactions across 11 developers and
16 micro-markets. Unless stated otherwise, every figure excludes the 1,247
records flagged as price outliers.

---

## Executive summary

Four things are worth a decision-maker's attention. Only the first three are
about the market; the fourth is about the data, and it is the most important.

1. **The market is remarkably flat.** Average ticket price sits at ₹11.97 Cr
   with a spread of just ₹0.07 Cr between the most and least expensive
   developer. Price per sqft varies by 2.9% across all 16 micro-markets.
2. **Booking conversion is 50.0% and does not move.** No builder, market,
   channel, buyer type, amenity level or configuration converts measurably
   better than any other.
3. **Buyer sentiment is net positive** — 55.6% of buyers who left a comment
   said something favourable, and 62.4% of those who expressed a clear
   positive or negative opinion were positive — but sentiment has no
   relationship with whether the deal closed.
4. **The dataset does not support causal conclusions.** Statistical testing
   across ten hypotheses found none that survive correction for multiple
   comparisons. Any recommendation of the form "focus on market X because it
   converts better" would be reading noise. Details in §5.

---

## 1. Market intelligence

### Pricing is uniform across developers

| Builder | Properties | Avg ticket price | Avg ₹/sqft |
|---|---:|---:|---:|
| Sobha | 8,837 | ₹12.01 Cr | ₹21,610 |
| L&T Realty | 9,013 | ₹12.00 Cr | ₹21,756 |
| Embassy | 8,978 | ₹11.99 Cr | ₹21,869 |
| Tata Housing | 8,826 | ₹11.98 Cr | ₹21,638 |
| Total Environment | 8,992 | ₹11.98 Cr | ₹21,695 |
| RMZ | 8,893 | ₹11.97 Cr | ₹21,717 |
| Brigade | 9,029 | ₹11.96 Cr | ₹21,596 |
| Puravankara | 8,960 | ₹11.96 Cr | ₹21,718 |
| Godrej | 8,996 | ₹11.95 Cr | ₹21,719 |
| Prestige | 9,108 | ₹11.95 Cr | ₹21,631 |
| SNN Raj | 9,121 | ₹11.94 Cr | ₹21,678 |

The gap between first and last is ₹0.07 Cr — 0.6% of the market average. A
one-way ANOVA across the eleven groups returns **p = 0.84**: there is no
detectable price differentiation between developers at all.

### Micro-market pricing spans under 3%

Hennur Road is the most expensive at ₹22,033/sqft and Indiranagar the least at
₹21,411/sqft — a 2.9% spread across the whole city. For context, real Bengaluru
luxury micro-markets differ by 2–3× on this metric.

Hennur Road commanding a premium over Indiranagar is itself implausible on
domain grounds: Indiranagar is a central, high-demand locality and Hennur Road
is a northern corridor. The ordering is arbitrary.

### Configuration does not predict unit size

| Configuration | Properties | Avg size | Avg price | Avg ₹/sqft |
|---|---:|---:|---:|---:|
| 3BHK | 32,980 | 6,002 sqft | ₹11.99 Cr | ₹21,714 |
| 4BHK | 32,660 | 6,008 sqft | ₹11.95 Cr | ₹21,650 |
| 5BHK+ | 33,113 | 6,006 sqft | ₹11.98 Cr | ₹21,716 |

**A 3BHK and a 5BHK+ average the same floor area to within 6 sqft.** This is
structurally impossible in a real market and is the single clearest signal that
the underlying values were generated independently rather than observed. It
also means `Configuration` carries no information for any model or
segmentation built on this data.

---

## 2. Sales optimisation

### Channel performance

| Channel | Properties | Conversion | Avg price |
|---|---:|---:|---:|
| Broker | 24,840 | 50.16% | ₹11.97 Cr |
| Direct | 24,335 | 50.07% | ₹11.99 Cr |
| NRI Desk | 24,723 | 49.94% | ₹11.98 Cr |
| Online | 24,855 | 49.83% | ₹11.95 Cr |

Range: 0.33 percentage points. Chi-square **p = 0.89**. There is no
best-performing channel.

### Possession status

| Status | Properties | Conversion |
|---|---:|---:|
| Launch | 32,905 | 50.58% |
| Under Construction | 32,991 | 49.85% |
| Ready to Move | 32,857 | 49.57% |

Launch-stage inventory converting best would be a genuinely interesting
finding — early-bird pricing pulling demand forward. The gap is 1.01 points and
the confidence intervals overlap, so it cannot be claimed.

### Where the drop-offs are

49,987 of 100,000 transactions are Secondary (resale) rather than Primary. Under
the definition used here that is a 50% drop-off, distributed evenly across every
channel and stage. There is no funnel leak to fix because there is no funnel
structure in the data.

---

## 3. Buyer personas

| Buyer type | Properties | Avg price | Conversion |
|---|---:|---:|---:|
| CXO | 19,879 | ₹11.98 Cr | 50.31% |
| HNI | 19,687 | ₹11.97 Cr | 50.41% |
| NRI | 19,734 | ₹11.97 Cr | 50.14% |
| Startup Founder | 19,754 | ₹11.97 Cr | 49.72% |
| Other | 19,699 | ₹11.97 Cr | 49.42% |

NRI-flagged buyers (49,347) and domestic buyers (49,406) are split almost
exactly in half and spend within ₹0.02 Cr of each other.

### Sentiment

| Sentiment | Comments | Share of all records |
|---|---:|---:|
| Positive | 45,548 | 45.55% |
| Negative | 27,453 | 27.45% |
| Neutral | 8,900 | 8.90% |
| No comment | 18,099 | 18.10% |

Among the 81,901 buyers who said anything, **55.6% were positive**; among the
73,001 who expressed a clear positive or negative view, **62.4% were positive**.
The three most common
complaints are "Too far from my office" (9,310), "Connectivity is poor" (9,302)
and "Agent was not responsive" (9,105).

Two of those three are location complaints, which would normally suggest
prioritising connectivity in marketing. But `Connectivity_Score` has no
correlation with whether a buyer complains about connectivity in this dataset,
so the complaint text is decorative rather than diagnostic.

---

## 4. Amenity score and conversion

| Amenity band | Properties | Avg score | Conversion |
|---|---:|---:|---:|
| Low | 26,703 | 5.76 | 50.03% |
| Medium | 36,524 | 7.32 | 49.90% |
| High | 35,526 | 9.00 | 50.08% |

Pearson correlation between amenity score and booking flag: **r = 0.002,
p = 0.54**. Amenities do not predict bookings here. With 98,753 observations
this test would detect a correlation as small as r = 0.01, so the null result
is informative rather than merely underpowered.

---

## 5. Why no causal claims are made

Ten hypotheses were tested. One reached p < 0.05 (price per sqft differing by
micro-market, p = 0.0106). With ten tests on one dataset the Bonferroni-corrected
threshold is α = 0.005, and that result does not clear it — it is the false
positive you expect from running ten tests.

| Hypothesis | Test | p | Verdict |
|---|---|---:|---|
| Conversion differs by builder | Chi-square | 0.2408 | Not significant |
| Conversion differs by micro-market | Chi-square | 0.4573 | Not significant |
| Conversion differs by amenity band | Chi-square | 0.8765 | Not significant |
| Conversion differs by sales channel | Chi-square | 0.8938 | Not significant |
| Conversion differs by buyer type | Chi-square | 0.2418 | Not significant |
| Conversion differs by configuration | Chi-square | 0.1232 | Not significant |
| Avg ticket price differs by builder | ANOVA | 0.8397 | Not significant |
| Price per sqft differs by micro-market | ANOVA | 0.0106 | Fails Bonferroni |
| Amenity score correlates with booking | Pearson | 0.5402 | Not significant |
| Unit size correlates with ticket price | Pearson | 0.8561 | Not significant |

That last row deserves a second look. **Unit size and ticket price are
uncorrelated (r ≈ 0, p = 0.86).** In any real property market these two are the
strongest relationship in the dataset. Their independence here confirms the
columns were drawn separately.

---

## 6. Data quality findings

These are real findings about the file itself, and they are actionable.

| Defect | Records | Impact if unhandled |
|---|---:|---|
| Exact duplicate rows | 1,000 | 1% inflation of every count |
| Prices stored as `₹12.75 Cr` text | 18,038 | 18% of prices silently become null on numeric cast |
| Missing ticket prices | 9,913 | Skewed averages |
| Zero or negative ticket prices | 5 | Impossible values passed through as real |
| Missing unit sizes | 9,957 | Price-per-sqft cannot be computed |
| `-1` sentinel in unit size | 500 | Negative price per sqft |
| Missing amenity scores | 10,000 | Amenity analysis loses 10% of rows |
| Missing buyer comments | 18,099 | Sentiment analysis silently drops a fifth of buyers |
| Casing variants in `Micro_Market` | 48 → 16 | Every market split three ways in a group-by |
| Casing variants in `Configuration` | 9 → 3 | Every layout split three ways |

**40,477 of the 100,000 de-duplicated rows (40.5%) carried at least one
defect**, counting nulls and sentinel values across price, size, amenity score
and buyer comments.

### The outlier injection

Flagged price outliers cluster at exactly three values:

| Price | Records |
|---|---:|
| ₹100 Cr | 349 |
| ₹70 Cr | 330 |
| ₹60 Cr | 321 |

These are not a natural ultra-luxury tail; a real distribution would not spike
at three round numbers. Including them raises the reported average ticket price
from **₹11.97 Cr to ₹12.65 Cr — a 5.7% overstatement** on 1.2% of the records.
Every view and dashboard page in this project excludes them by default, with a
toggle to include them.

---

## 7. Recommendations

**For anyone presenting this analysis:**

1. Present rankings as descriptive, never causal. "Kanakapura Road led at
   51.31%" is defensible; "Kanakapura Road converts better" is not.
2. Keep the 50% baseline and confidence intervals on every conversion visual.
   The overlap *is* the finding.
3. Lead with the data-quality work. Recovering 18,038 prices from currency
   strings and collapsing 48 spurious market labels into 16 is the substantive
   analytical contribution here.

**For anyone extending this pipeline to real data:**

1. The pipeline is sound and will surface genuine patterns unchanged. Point
   `config.RAW_CSV` at a real extract and re-run.
2. Replace the `Booking_Flag` derivation. Deriving it from `Transaction_Type`
   is a workaround for a missing column; real transaction data should carry an
   explicit booking status.
3. Re-run `eda_analysis.py` after any data change. It re-tests every hypothesis
   automatically, so the significance table stays honest as the data evolves.
4. Add lat/long per micro-market. Power BI geocodes place names, but explicit
   coordinates make map visuals reliable.

---

## Appendix — figures referenced

All charts live in `outputs/charts/`. Statistical detail is in
`outputs/eda_findings.md`. Cleaning detail is in
`outputs/data_quality_report.md`. Raw query output is in
`outputs/sql_validation_results.md`.
