# Luxury Housing Sales Analysis — Bengaluru

End-to-end real estate analytics pipeline over 100,000 luxury property
transactions: Python cleaning and feature engineering → SQL warehouse →
interactive dashboard.

**Tags:** EDA · Data Visualization · SQL

---

## What this does

| Stage | Script | Output |
|---|---|---|
| Clean 101,000 raw rows | `python_scripts/data_cleaning.py` | `data/processed/luxury_housing_clean.csv` (36 cols) + audit report |
| Build the warehouse | `python_scripts/sql_loader.py` | `data/luxury_housing.db` (1 table, 14 views, 10 indexes) |
| Analyse | `python_scripts/eda_analysis.py` | 12 charts + significance-tested findings |
| Visualise | `python_scripts/dashboard.py` | 5-page Streamlit dashboard |
| Power BI model | `python_scripts/generate_pbip.py` | PBIP project: 36 typed columns, `DimDate`, 30 DAX measures |
| Power BI report | `documentation/powerbi_build_guide.md` | DAX library + page-by-page build spec |

---

## Quick start

```bash
pip install -r requirements.txt
```

Run the pipeline (about a minute end to end):

```bash
python python_scripts/data_cleaning.py
```
```bash
python python_scripts/sql_loader.py
```
```bash
python python_scripts/eda_analysis.py
```

Launch the dashboard:

```bash
streamlit run python_scripts/dashboard.py
```

Every stage is idempotent — re-running drops and rebuilds cleanly.

---

## Project structure

```
Luxury-Housing-Sales-Analysis/
├── Luxury_Housing_Bangalore.csv          raw dataset, 101,000 x 18
├── requirements.txt
├── README.md
│
├── python_scripts/
│   ├── config.py                         paths, DB switch, coordinates, reference data
│   ├── data_cleaning.py                  Stage 1 — clean + feature engineer
│   ├── sql_loader.py                     Stage 2 — schema, load, validate
│   ├── eda_analysis.py                   Stage 3a — charts + significance tests
│   ├── dashboard.py                      Stage 3b — Streamlit dashboard
│   └── generate_pbip.py                  Stage 3c — Power BI semantic model
│
├── sql_scripts/
│   ├── create_schema.sql                 fact table + 10 indexes
│   ├── analytics_views.sql               14 views, incl. one per brief question
│   └── validation_queries.sql            12 labelled validation queries
│
├── power_bi_dashboard/                   generated PBIP + status notes
│
├── data/
│   ├── processed/luxury_housing_clean.csv   100,000 x 36  (git-ignored)
│   └── luxury_housing.db                    SQLite warehouse (git-ignored)
│
├── outputs/
│   ├── data_quality_report.md            every repair the cleaner made
│   ├── sql_validation_results.md         all 12 queries with their results
│   ├── eda_findings.md                   headline numbers + significance table
│   └── charts/                           12 PNGs
│
└── documentation/
    ├── project_plan.md                   architecture and design decisions
    ├── powerbi_build_guide.md            connection, model, DAX, page specs
    ├── powerbi_visualization_questions.md  the 10 brief questions -> visuals
    └── insights_report.md                business findings
```

Generated artifacts (the 26 MB cleaned CSV and 50 MB SQLite file) are
git-ignored and rebuilt by the pipeline; the raw dataset **is** committed, so a
clean clone reproduces everything.

## Configuration

No paths or credentials are hardcoded. Everything resolves from the repository
root, derived from `config.py`'s own location, so the scripts run from any
working directory. Each value can be overridden by an environment variable:

| Variable | Default | Purpose |
|---|---|---|
| `LUXURY_HOUSING_ROOT` | repo root | Relocate the whole project |
| `LUXURY_HOUSING_RAW_CSV` | `Luxury_Housing_Bangalore.csv` | Point at a different extract |
| `LUXURY_DB_BACKEND` | `sqlite` | `sqlite` / `postgresql` / `mysql` |
| `LUXURY_DB_HOST`, `LUXURY_DB_PORT` | `localhost`, backend default | Server address |
| `LUXURY_DB_USER`, `LUXURY_DB_PASSWORD` | `postgres`, empty | Credentials — never committed |
| `LUXURY_DB_NAME` | `luxury_housing` | Database name |

---

## Dataset

`Luxury_Housing_Bangalore.csv` — 101,000 rows × 18 columns covering
2023-Q2 to 2025-Q1, 11 developers and 16 Bengaluru micro-markets.

**Raw columns:** `Property_ID`, `Micro_Market`, `Project_Name`,
`Developer_Name`, `Unit_Size_Sqft`, `Configuration`, `Ticket_Price_Cr`,
`Transaction_Type`, `Buyer_Type`, `Purchase_Quarter`, `Connectivity_Score`,
`Amenity_Score`, `Possession_Status`, `Sales_Channel`, `NRI_Buyer`,
`Locality_Infra_Score`, `Avg_Traffic_Time_Min`, `Buyer_Comments`.

### Data quality repaired

40,477 of the 100,000 de-duplicated rows carried at least one defect:

| Defect | Records |
|---|---:|
| Exact duplicate rows | 1,000 |
| Prices stored as `₹12.75 Cr` text | 18,038 |
| Missing ticket prices | 9,913 |
| Zero or negative ticket prices | 5 |
| Missing unit sizes | 9,957 |
| `-1` sentinel in unit size | 500 |
| Missing amenity scores | 10,000 |
| Missing buyer comments | 18,099 |
| `Micro_Market` casing variants | 48 → 16 |
| `Configuration` casing variants | 9 → 3 |

Full detail in [`outputs/data_quality_report.md`](outputs/data_quality_report.md).

### Two things to know before reading any result

**1. `Booking_Status` does not exist in the raw file.** The brief names it, the
data does not have it. `Booking_Flag` is derived from `Transaction_Type`: a
Primary transaction (direct from the developer) counts as a booking, a
Secondary transaction (resale) does not. Every conversion figure in this
project rests on that definition.

**2. The dataset carries no real signal.** Chi-square and ANOVA testing across
ten hypotheses finds no significant relationship between booking outcome and
builder, micro-market, amenity band, sales channel, buyer type or
configuration. Unit size and ticket price are uncorrelated (r ≈ 0), and a 3BHK
averages the same floor area as a 5BHK+ — both structurally impossible in a
real market. Rankings in the dashboard are descriptive, not causal, and every
conversion visual carries a 50% baseline and confidence intervals to make that
visible. See [`outputs/eda_findings.md`](outputs/eda_findings.md).

---

## Business use cases addressed

| Use case | Where |
|---|---|
| Market Intelligence — localities, builder trends, configuration demand | `vw_builder_performance`, `vw_micro_market_summary`, `vw_configuration_demand`; dashboard page 1 |
| Sales Optimization — booking vs inquiry drop-off | `vw_sales_channel_performance`; dashboard page 2 |
| Buyer Persona Building — buyer type and comment sentiment | `vw_buyer_persona`, `vw_sentiment_summary`; dashboard page 3 |
| Competitive Pricing — pricing across builders and segments | `vw_competitive_pricing`; dashboard page 4 |
| Amenity Score & Conversion | `vw_amenity_conversion`; dashboard page 4 |
| Quarterly Trend Tracking | `vw_quarterly_trends`; dashboard page 2 |

### The 10 Power BI visualization questions

Each numbered question in the brief is mapped to an exact visual — chart type,
field wells, required DAX and page — in
[`documentation/powerbi_visualization_questions.md`](documentation/powerbi_visualization_questions.md),
with a supporting SQL view for each so the numbers can be checked outside Power
BI. The Streamlit dashboard implements the same ten, labelled `Q1 ·`, `Q2 ·`
and so on.

Maps (Q9) use explicit `latitude` / `longitude` columns rather than name
geocoding: the raw dataset ships no coordinates, so the pipeline joins
approximate locality centroids for all 16 micro-markets from
`config.MICRO_MARKET_COORDS`.

---

## SQL backend

SQLite is the default — no server, no install, the warehouse is a single file
at `data/luxury_housing.db`.

To target PostgreSQL or MySQL, edit `DB_BACKEND` and `DB_CONFIG` in
`python_scripts/config.py`, install the driver, and pass the backend:

```bash
pip install sqlalchemy psycopg2-binary
```
```bash
python python_scripts/sql_loader.py --backend postgresql
```

Power BI has no native SQLite connector, so **PostgreSQL is the recommended
backend if you are building the .pbix** — see
[`documentation/powerbi_build_guide.md`](documentation/powerbi_build_guide.md)
for all three connection options.

---

## Key findings

- Average ticket price **₹11.97 Cr**, median ₹11.98 Cr, average **₹21,694/sqft**
- Overall booking conversion **50.0%**, flat across every dimension tested
- Builder price spread is **₹0.07 Cr** (0.6% of the market average)
- Micro-market price-per-sqft spread is **2.9%** across all 16 markets
- **55.6%** of buyers who commented were positive; 62.4% of those expressing a
  clear opinion
- Including the 1,247 flagged outliers (clustered at exactly ₹60, ₹70 and
  ₹100 Cr) inflates the reported average price from ₹11.97 Cr to **₹12.65 Cr**

Full analysis in
[`documentation/insights_report.md`](documentation/insights_report.md).

---

## Skills demonstrated

Data cleaning with pandas/NumPy · missing-value strategy and imputation
auditing · outlier detection · feature engineering · SQL schema design and
indexing · view-based data modelling · SQLAlchemy/DBAPI loading · statistical
hypothesis testing with multiple-comparison correction · matplotlib/seaborn
charting · interactive dashboarding · Power BI semantic modelling and DAX ·
analytical communication.
