# Power BI Build Guide

Everything needed to assemble `luxury_housing_dashboard.pbix` against the
warehouse this project builds: connection options, the data model, a complete
DAX measure library, and page-by-page visual specifications.

The Streamlit app in `python_scripts/dashboard.py` implements the same five
pages, so you can run it side by side while building to check your work.

---

## 1. Connecting Power BI to the warehouse

Power BI has **no native SQLite connector**. Pick whichever of these three
routes fits your setup — the semantic model and every DAX measure below is
identical in all three cases.

### Option A — PostgreSQL (recommended for the graded submission)

This is the only option that literally satisfies "connect Power BI to a SQL
database" with a first-party connector.

1. Install PostgreSQL and create the database:
   ```bash
   createdb -U postgres luxury_housing
   ```
2. Point the loader at it — edit `python_scripts/config.py`:
   ```python
   DB_BACKEND = "postgresql"
   DB_CONFIG = {"host": "localhost", "port": 5432, "user": "postgres",
                "password": "<your password>", "database": "luxury_housing"}
   ```
3. Install the driver and load:
   ```bash
   pip install sqlalchemy psycopg2-binary
   ```
   ```bash
   python python_scripts/sql_loader.py --backend postgresql
   ```
4. In Power BI Desktop: **Home → Get Data → PostgreSQL database**
   - Server `localhost`, Database `luxury_housing`
   - Choose **Import** (100k rows imports in seconds and makes the report far
     more responsive than DirectQuery)
   - Select `vw_dashboard_base` plus any of the pre-aggregated `vw_*` views you
     want

### Option B — SQLite via ODBC

1. Install the SQLite ODBC driver (Christian Werner's build, 64-bit).
2. Create a System DSN pointing at
   `Luxury-Housing-Sales-Analysis/data/luxury_housing.db`.
3. **Get Data → ODBC → your DSN**.

Works, but the third-party driver is an extra dependency for whoever opens
your file.

### Option C — CSV import (fastest, no database)

**Get Data → Text/CSV →** `data/processed/luxury_housing_clean.csv`.

Use this only if you cannot install a database. You lose the SQL views, so
every aggregation has to be rebuilt in DAX, and it does not demonstrate the
SQL-integration part of the brief.

---

## 2. Data model

### Tables to load

| Table / view | Role | Notes |
|---|---|---|
| `vw_dashboard_base` | Fact table | 98,753 rows, price outliers already excluded |
| `DimDate` | Date dimension | Created in DAX, see below |
| `vw_builder_performance` | Optional | Pre-aggregated, useful for a summary page |
| `vw_competitive_pricing` | Optional | Builder premium vs local market |

Load `vw_dashboard_base` as the single fact table and let DAX do the
aggregation. The `vw_*` summary views are there if you prefer to push work into
SQL — do not load both and then join them, that creates ambiguous relationships.

### Date dimension

Power BI's time intelligence needs a contiguous date table. Create it with
**Modeling → New table**:

```dax
DimDate =
VAR MinDate = MIN ( vw_dashboard_base[purchase_date] )
VAR MaxDate = MAX ( vw_dashboard_base[purchase_date] )
RETURN
ADDCOLUMNS (
    CALENDAR ( MinDate, MaxDate ),
    "Year",           YEAR ( [Date] ),
    "Quarter Number", QUARTER ( [Date] ),
    "Quarter Label",  FORMAT ( [Date], "YYYY" ) & "-Q" & QUARTER ( [Date] ),
    "Fiscal Year",    "FY" & YEAR ( EDATE ( [Date], -3 ) ) & "-"
                          & RIGHT ( YEAR ( EDATE ( [Date], -3 ) ) + 1, 2 ),
    "Month Name",     FORMAT ( [Date], "MMM YYYY" ),
    "Month Number",   MONTH ( [Date] )
)
```

Then:
1. **Table tools → Mark as date table**, using `[Date]`.
2. Create the relationship `DimDate[Date]` → `vw_dashboard_base[purchase_date]`
   (one-to-many, single direction).
3. Sort `Quarter Label` by a numeric key so `2025-Q1` follows `2024-Q4`:
   add a calculated column `Quarter Sort = [Year] * 10 + [Quarter Number]` and
   set **Column tools → Sort by column → Quarter Sort**.

### Column configuration

| Column | Setting |
|---|---|
| `ticket_price_cr` | Decimal number, 2 dp |
| `price_per_sqft` | Whole number, thousands separator |
| `unit_size_sqft` | Whole number |
| `booking_flag` | Whole number, **Summarization = Don't summarize** |
| `latitude` | Decimal, data category = **Latitude**, Summarization = **Don't summarize** |
| `longitude` | Decimal, data category = **Longitude**, Summarization = **Don't summarize** |
| `map_location` | Data category = **Place** |
| `purchase_date` | Date |

No calculated column is needed for maps. The pipeline already ships three
geography columns: `latitude` and `longitude` (approximate locality centroids
for all 16 micro-markets, joined in `data_cleaning.py` from
`config.MICRO_MARKET_COORDS`), and `map_location`, which is the market name
already suffixed with "Bengaluru, Karnataka, India".

Prefer `latitude`/`longitude` for bubble maps — explicit coordinates are
deterministic, whereas geocoding these locality names by text resolves several
of them to the wrong country without a city qualifier. Use `map_location` for
filled maps, which require a named region rather than a point.

---

## 3. DAX measure library

Create a blank table called `_Measures` (**Enter data → rename → hide the
column**) and put every measure in it so they are easy to find.

### Core volume and conversion

```dax
Total Properties = COUNTROWS ( vw_dashboard_base )
```
```dax
Total Bookings = SUM ( vw_dashboard_base[booking_flag] )
```
```dax
Drop Offs = [Total Properties] - [Total Bookings]
```
```dax
Booking Conversion % = DIVIDE ( [Total Bookings], [Total Properties], 0 )
```
```dax
Drop Off Rate % = 1 - [Booking Conversion %]
```

### Pricing

```dax
Avg Ticket Price Cr = AVERAGE ( vw_dashboard_base[ticket_price_cr] )
```
```dax
Median Ticket Price Cr = MEDIAN ( vw_dashboard_base[ticket_price_cr] )
```
```dax
Avg Price per Sqft = AVERAGE ( vw_dashboard_base[price_per_sqft] )
```
```dax
Total Pipeline Value Cr = SUM ( vw_dashboard_base[ticket_price_cr] )
```
```dax
Avg Unit Size Sqft = AVERAGE ( vw_dashboard_base[unit_size_sqft] )
```

### Quality and sentiment

```dax
Avg Amenity Score = AVERAGE ( vw_dashboard_base[amenity_score] )
```
```dax
Positive Sentiment % =
DIVIDE (
    CALCULATE ( [Total Properties], vw_dashboard_base[comment_sentiment] = "Positive" ),
    CALCULATE ( [Total Properties], vw_dashboard_base[comment_sentiment] <> "No Comment" ),
    0
)
```
```dax
Negative Sentiment % =
DIVIDE (
    CALCULATE ( [Total Properties], vw_dashboard_base[comment_sentiment] = "Negative" ),
    CALCULATE ( [Total Properties], vw_dashboard_base[comment_sentiment] <> "No Comment" ),
    0
)
```

### Competitive positioning

`ALLEXCEPT` removes the builder filter but keeps the micro-market filter, which
is exactly what "compared with the local market" means:

```dax
Market Avg Price per Sqft =
CALCULATE (
    AVERAGE ( vw_dashboard_base[price_per_sqft] ),
    ALLEXCEPT ( vw_dashboard_base, vw_dashboard_base[micro_market] )
)
```
```dax
Price Premium vs Market % =
DIVIDE (
    [Avg Price per Sqft] - [Market Avg Price per Sqft],
    [Market Avg Price per Sqft],
    0
)
```
```dax
Builder Rank by Price =
RANKX ( ALLSELECTED ( vw_dashboard_base[builder] ), [Avg Ticket Price Cr],, DESC )
```

### Measures for the ten visualization questions

See [`powerbi_visualization_questions.md`](powerbi_visualization_questions.md)
for which visual each of these belongs to.

```dax
Booking Status Share % =
DIVIDE (
    [Total Properties],
    CALCULATE ( [Total Properties], ALL ( vw_dashboard_base[booking_status] ) )
)
```
```dax
Builder Revenue Rank =
RANKX ( ALLSELECTED ( vw_dashboard_base[builder] ), [Total Pipeline Value Cr],, DESC )
```
```dax
Is Top 5 Builder = IF ( [Builder Revenue Rank] <= 5, 1, 0 )
```
```dax
Top 5 Builders Revenue Cr =
SUMX (
    TOPN ( 5, ALLSELECTED ( vw_dashboard_base[builder] ),
           [Total Pipeline Value Cr], DESC ),
    [Total Pipeline Value Cr]
)
```
```dax
Top 5 Builders Bookings =
SUMX (
    TOPN ( 5, ALLSELECTED ( vw_dashboard_base[builder] ),
           [Total Pipeline Value Cr], DESC ),
    [Total Bookings]
)
```

### Time intelligence

```dax
Previous Quarter Bookings =
CALCULATE ( [Total Bookings], PREVIOUSQUARTER ( DimDate[Date] ) )
```
```dax
QoQ Booking Growth % =
VAR Previous = [Previous Quarter Bookings]
RETURN DIVIDE ( [Total Bookings] - Previous, Previous )
```
```dax
Previous Quarter Avg Price =
CALCULATE ( [Avg Ticket Price Cr], PREVIOUSQUARTER ( DimDate[Date] ) )
```
```dax
QoQ Price Change % =
VAR Previous = [Previous Quarter Avg Price]
RETURN DIVIDE ( [Avg Ticket Price Cr] - Previous, Previous )
```
```dax
Rolling 4Q Avg Price =
AVERAGEX (
    DATESINPERIOD ( DimDate[Date], MAX ( DimDate[Date] ), -12, MONTH ),
    [Avg Ticket Price Cr]
)
```

### Statistical honesty measures

These are what separate a defensible dashboard from a misleading one. The
conversion differences in this dataset are not statistically significant (see
`outputs/eda_findings.md`), and these measures make that visible in the report
rather than hiding it.

```dax
Conversion CI Half Width =
VAR N = [Total Properties]
VAR P = [Booking Conversion %]
RETURN IF ( N > 0, 1.96 * SQRT ( DIVIDE ( P * ( 1 - P ), N ) ) )
```
```dax
Conversion Lower Bound = [Booking Conversion %] - [Conversion CI Half Width]
```
```dax
Conversion Upper Bound = [Booking Conversion %] + [Conversion CI Half Width]
```
```dax
Conversion Signal =
IF (
    [Conversion Lower Bound] > 0.5 || [Conversion Upper Bound] < 0.5,
    "Distinguishable from baseline",
    "Within noise"
)
```

Use `Conversion Signal` as a conditional-formatting field or a card next to
any conversion ranking. On this dataset it will read "Within noise" everywhere,
which is the correct and defensible finding.

### Formatting

Set these once in **Measure tools → Format**:

| Measure pattern | Format |
|---|---|
| `... %` | Percentage, 2 dp |
| `Avg Ticket Price Cr`, `Median ...` | Decimal, 2 dp, prefix `₹`, suffix ` Cr` |
| `Avg Price per Sqft` | Whole number, prefix `₹` |
| `Total Properties`, `Total Bookings` | Whole number, thousands separator |

---

## 4. Report pages

Common to every page: a slicer panel across the top with **Builder**,
**Micro-market**, **Quarter Label**, **Configuration**, and a
**Possession Status** button slicer. Set **Format → Edit interactions** so
slicers filter all visuals.

### Page 1 — Market Intelligence

| Position | Visual | Fields |
|---|---|---|
| Top strip | 5 × Card | `Total Properties`, `Avg Ticket Price Cr`, `Avg Price per Sqft`, `Booking Conversion %`, `Total Pipeline Value Cr` |
| Left | Clustered bar | Axis `builder`, Values `Avg Ticket Price Cr`, add `Conversion CI Half Width` as an error bar if using a custom visual |
| Right | Scatter | X `Avg Price per Sqft`, Y `Booking Conversion %`, Legend `builder`, Size `Total Properties` |
| Bottom left | Map (bubble) | Latitude `latitude`, Longitude `longitude`, Size `Total Properties`, Legend `micro_market` |
| Bottom right | 100% stacked column | Axis `Quarter Label`, Legend `configuration`, Values `Total Properties` |

### Page 2 — Sales & Conversion

| Position | Visual | Fields |
|---|---|---|
| Top | Line and clustered column | Axis `Quarter Label`, Column `Total Properties`, Line `Avg Ticket Price Cr` |
| Middle left | Stacked column | Axis `sales_channel`, Values `Total Bookings` and `Drop Offs` |
| Middle right | Clustered bar | Axis `possession_status`, Values `Booking Conversion %`, constant line at 0.5 |
| Bottom | Table | Rows `micro_market`; Values `Total Properties`, `Booking Conversion %`, `Conversion Lower Bound`, `Conversion Upper Bound`, `Conversion Signal` |
| Bottom right | KPI | Indicator `Booking Conversion %`, Trend axis `Quarter Label`, Target 0.5 |

Add a **constant line at 50%** on every conversion visual
(**Analytics pane → Constant line**). Without it the ranking looks meaningful.

### Page 3 — Buyer Personas

| Position | Visual | Fields |
|---|---|---|
| Left | Matrix | Rows `buyer_type`, Columns `nri_buyer`, Values `Avg Ticket Price Cr`, conditional background colour |
| Centre | Stacked bar | Axis `buyer_type`, Legend `nri_buyer`, Values `Total Properties` |
| Right top | Donut | Legend `comment_sentiment`, Values `Total Properties` |
| Right bottom | Bar | Axis `buyer_comments`, Values `Total Properties`, colour by `comment_sentiment` |
| Footer | Text box | The buyer-comment insight narrative — see Page 5 note below |

Sentiment colours: Positive `#2E7D5B`, Neutral `#9AA0A6`,
Negative `#B4453C`, No Comment `#C9CCD1`.

### Page 4 — Pricing & Competition

| Position | Visual | Fields |
|---|---|---|
| Top left | Histogram | Axis `ticket_price_cr` binned at 0.5 Cr, Values `Total Properties` |
| Top right | Bar | Axis `price_segment`, Values `Total Properties` |
| Middle | Clustered bar | Axis `builder`, Values `Price Premium vs Market %`, diverging conditional colours around 0 |
| Bottom left | Bar + constant line | Axis `amenity_band`, Values `Booking Conversion %`, line at 0.5 |
| Bottom right | Matrix | Rows `micro_market`, Columns `builder`, Values `Avg Price per Sqft` |

### Page 5 — Data & Quality

| Position | Visual | Fields |
|---|---|---|
| Top | 4 × Card | Imputed prices, imputed sizes, imputed amenity scores, flagged outliers — build these from the source table with `is_price_outlier` etc. |
| Middle | Table | The detail grid, with drill-through enabled from every other page |
| Bottom | Text box | The assumptions note below, verbatim |

**Text box content (copy this in):**

> **Derived-field assumption.** The raw dataset contains no `Booking_Status`
> column. `Booking_Flag` is derived from `Transaction_Type`: a Primary
> transaction (direct from the developer) counts as a booking, a Secondary
> transaction (resale) does not. Every conversion figure in this report rests
> on that definition.
>
> **Statistical caveat.** Chi-square testing across 98,753 records finds no
> significant relationship between booking outcome and builder, micro-market,
> amenity band, sales channel, buyer type or configuration (all p > 0.05).
> Conversion rankings in this report are descriptive, not causal.

### Drill-through

On Page 5, drag `property_id` into the **Drill-through** well. Right-clicking
any bar on Pages 1–4 will then jump to the filtered detail list.

---

## 5. Build checklist

- [ ] Warehouse loaded and `vw_dashboard_base` returns 98,753 rows
- [ ] `DimDate` created and marked as a date table
- [ ] Relationship `DimDate[Date]` → `vw_dashboard_base[purchase_date]` active
- [ ] `Quarter Label` sorted by `Quarter Sort`
- [ ] `micro_market` and `Map Location` categorised as **Place**
- [ ] All measures created in `_Measures` and formatted
- [ ] Five pages built with the shared slicer panel
- [ ] Constant line at 50% on every conversion visual
- [ ] Drill-through configured to the detail page
- [ ] Assumptions text box present on Page 5
- [ ] Saved as `power_bi_dashboard/luxury_housing_dashboard.pbix`
