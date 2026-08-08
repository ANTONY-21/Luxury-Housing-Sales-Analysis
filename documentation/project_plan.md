# Project Plan & Pipeline Documentation

How the Luxury Housing Sales Analysis solution is put together, in the order it
runs.

---

## Architecture

```
Luxury_Housing_Bangalore.csv          raw, 101,000 x 18
        |
        |  python_scripts/data_cleaning.py
        v
data/processed/luxury_housing_clean.csv    cleaned, 100,000 x 33
outputs/data_quality_report.md             audit of every repair
        |
        |  python_scripts/sql_loader.py
        v
data/luxury_housing.db                     SQLite warehouse
  +-- luxury_housing                       fact table, 10 indexes
  +-- vw_dashboard_base                    flat view for BI, 98,753 rows
  +-- vw_builder_performance               \
  +-- vw_micro_market_summary               |
  +-- vw_quarterly_trends                   |  one view per
  +-- vw_configuration_demand               |  business use case
  +-- vw_sales_channel_performance          |
  +-- vw_buyer_persona                      |
  +-- vw_amenity_conversion                 |
  +-- vw_sentiment_summary                  |
  +-- vw_competitive_pricing               /
outputs/sql_validation_results.md          12 validation queries + results
        |
        +-----------------------------+
        |                             |
        v                             v
python_scripts/eda_analysis.py   python_scripts/dashboard.py
outputs/charts/*.png (11)        Streamlit, 5 pages
outputs/eda_findings.md                    |
                                           v
                              documentation/powerbi_build_guide.md
                              -> luxury_housing_dashboard.pbix
```

---

## Stage 1 — Python cleaning and feature engineering

`python_scripts/data_cleaning.py`

Eight steps, each logged to the console and to
`outputs/data_quality_report.md`.

### 1. Load
Read with `dtype=str` so pandas cannot silently coerce a malformed value before
it has been inspected. The script has **no synthetic-data fallback** — if the
raw file is missing it raises rather than fabricating rows.

### 2. Deduplicate
1,000 exactly duplicated rows removed, then `Property_ID` checked for
uniqueness.

### 3. Normalise text
| Column | Problem | Fix |
|---|---|---|
| `Micro_Market` | 48 casing variants of 16 markets | Title case, then a lookup for `JP Nagar` and `MG Road` which title case mangles |
| `Configuration` | 9 casing variants of 3 layouts | Upper case, strip spaces |
| `Possession_Status` | Inconsistent sentence case | Title case with `Ready to Move` restored |
| `NRI_Buyer` | `yes` / `no` | `Yes` / `No` |

### 4. Parse numerics
- `Ticket_Price_Cr`: 18,038 values arrive as `₹12.75 Cr`. Strip the symbol,
  the thousands separator and the unit suffix, then cast. Values ≤ 0 become
  null.
- `Unit_Size_Sqft`: `-1` is a missing-value sentinel, not a measurement.
- Score columns cast to float, traffic time to nullable integer.

### 5. Flag outliers
IQR rule on ticket price (Q3 + 1.5 × IQR = ₹20.23 Cr) flags 1,247 records.
They are **flagged, not deleted** — the dashboard can include them
deliberately — but they are held out of the imputation medians so they cannot
skew the fill values.

### 6. Impute
Group medians, from specific to general, rather than one global number:

| Column | Grouping | Rows filled |
|---|---|---:|
| `Ticket_Price_Cr` | Micro_Market × Configuration → Micro_Market → Configuration → global | 9,918 |
| `Unit_Size_Sqft` | Micro_Market × Configuration → Configuration → global | 10,457 |
| `Amenity_Score` | Micro_Market → global | 10,000 |
| `Buyer_Comments` | Literal `"No Comment"` | 18,099 |

Every imputation sets an audit flag (`Price_Imputed`, `Size_Imputed`,
`Amenity_Imputed`) so downstream analysis can exclude synthetic values.

### 7. Engineer features
15 derived columns:

| Column | Definition |
|---|---|
| `Price_per_Sqft` | `Ticket_Price_Cr × 1e7 / Unit_Size_Sqft` |
| `Purchase_Date`, `Purchase_Year`, `Quarter_Number`, `Quarter_Label` | Parsed from the quarter-end date |
| `Fiscal_Year` | Indian FY, April–March, formatted `FY2023-24` |
| `Booking_Flag`, `Booking_Status` | Derived from `Transaction_Type` — see the assumption below |
| `Comment_Sentiment` | Lookup over the nine canned comments |
| `Price_Segment` | Entry Luxury / Premium / Ultra Luxury / Elite |
| `Size_Category` | Compact / Mid-Size / Large / Ultra Large |
| `Amenity_Band` | Low / Medium / High |
| `Is_Price_Outlier` | IQR flag |
| `Price_Imputed`, `Size_Imputed`, `Amenity_Imputed` | Audit flags |

> **Stated assumption.** The project brief names a `Booking_Status` column, but
> the raw file does not contain one. `Transaction_Type` is the only
> booking-related field available, so `Booking_Flag` is defined as
> `Transaction_Type == 'Primary'` — a sale direct from the developer counts as
> a booking, a resale does not. Every conversion metric in the project rests on
> this definition, and it is restated in the dashboard and the Power BI guide.

### 8. Validate and write
Ten assertions run before anything is written — no duplicate keys, no nulls in
required columns, all prices and sizes positive, `Booking_Flag` binary,
`Quarter_Number` in 1–4, `Configuration` collapsed to 3, `Micro_Market`
collapsed to 16. The script fails loudly rather than writing bad data.

---

## Stage 2 — SQL warehouse

`python_scripts/sql_loader.py` + `sql_scripts/*.sql`

1. **Schema** (`create_schema.sql`) — one fact table with a `property_id`
   primary key and 10 indexes covering every column the dashboard slices by.
   Written against the common subset of SQLite, PostgreSQL and MySQL; column
   names are lower snake_case so PostgreSQL never needs quoting.
2. **Load** — the cleaned CSV inserted in 1,000-row chunks.
3. **Views** (`analytics_views.sql`) — ten views, one per business use case,
   plus `vw_dashboard_base` which exposes `developer_name` under the brief's
   name (`builder`) and filters out flagged outliers.
4. **Validate** (`validation_queries.sql`) — 12 queries, including the three
   named in the brief (`COUNT(*)`, group by booking status, average ticket
   price per builder). The loader parses the `-- name:` annotations, runs each
   query, prints the result and writes
   `outputs/sql_validation_results.md`.

### Switching backend

SQLite is the default because it needs no server. To target a real server, set
`DB_BACKEND` in `config.py` or pass `--backend`:

```bash
python python_scripts/sql_loader.py --backend postgresql
```

---

## Stage 3 — Analysis and visualisation

### EDA — `python_scripts/eda_analysis.py`

Produces 11 charts and `outputs/eda_findings.md`. Its distinguishing feature is
that it **tests every apparent difference before reporting it**: six chi-square
tests, two ANOVAs and two correlations, with a Bonferroni correction for
multiple comparisons. On this dataset nothing survives, and the report says so.

### Streamlit — `python_scripts/dashboard.py`

```bash
streamlit run python_scripts/dashboard.py
```

Five pages (Market Intelligence, Sales & Conversion, Buyer Personas, Pricing,
Data & Quality), seven cross-filtering slicers, six KPI cards, and an
outlier-inclusion toggle. Reads directly from the SQLite warehouse.

### Power BI — `documentation/powerbi_build_guide.md`

Connection options, the semantic model, a `DimDate` table, 25 DAX measures and
page-by-page visual specifications mirroring the Streamlit pages.

---

## Design decisions worth defending

| Decision | Why |
|---|---|
| No synthetic-data fallback | The original script silently generated 10,000 random rows when the input path was wrong, and wrote them out as "cleaned data". Failing loudly is better than producing plausible-looking nonsense. |
| Group-median imputation, not global mean | Price and size vary by market and layout. A global mean would flatten exactly the variation the analysis is trying to measure. |
| Outliers flagged, not dropped | Dropping records silently changes the denominator of every rate. A flag plus a default filter is reversible and visible. |
| Audit flags on every imputation | 10% of prices are synthetic. Anyone modelling on this data needs to be able to exclude them. |
| Confidence intervals on every rate | Without them, a 51.31% vs 48.75% gap looks like a finding. With them, it visibly is not. |
| Lower snake_case in SQL | PostgreSQL folds unquoted identifiers to lower case; mixed-case column names would need quoting in every query forever. |
| `-- name:` annotated SQL | One source of truth for the validation queries — the `.sql` file is both the deliverable and what the loader executes. |

---

## Reproducing the whole pipeline

```bash
pip install -r requirements.txt
```
```bash
python python_scripts/data_cleaning.py && python python_scripts/sql_loader.py && python python_scripts/eda_analysis.py
```
```bash
streamlit run python_scripts/dashboard.py
```

Total runtime is roughly one minute on a laptop. Every stage is idempotent —
re-running drops and rebuilds cleanly.
