# The 10 Power BI Visualization Questions — Build Specification

Each question from the project brief, mapped to an exact visual: chart type,
field wells, the measures it needs, which report page it belongs on, and the
SQL view that answers the same question if you prefer to check the numbers
outside Power BI.

Every measure named here exists in the generated model
(`power_bi_dashboard/LuxuryHousing.SemanticModel/model.bim`) and in the measure
library in [`powerbi_build_guide.md`](powerbi_build_guide.md).

Table names below refer to `vw_dashboard_base`, imported as the single fact
table. The brief's "Builder" is the `builder` column (aliased from
`developer_name`), and "Booking_Count" is the `Total Bookings` measure.

---

## Q1 — Market Trends

> How have luxury housing bookings changed quarter by quarter across
> micro-markets?

| | |
|---|---|
| **Visual** | Line chart |
| **Page** | 1 — Market Intelligence |
| **X axis** | `DimDate[Quarter Label]` (sorted by `Quarter Sort`) |
| **Y axis** | `[Total Bookings]` |
| **Legend** | `micro_market` |
| **SQL view** | `vw_market_quarterly_bookings` |

Sixteen lines on one chart is unreadable. Add a **Top N filter** on the legend
(Top 5 by `Total Bookings`), or convert to **small multiples** — Format pane →
Small multiples → `micro_market`, 4 × 4 grid.

*What you will see:* flat lines averaging 386 bookings per market per quarter
(range 337–432 across all 128 market-quarter combinations), with no trend in any
market. That is the correct result, not a build error.

---

## Q2 — Builder Performance

> Which builders have the highest total ticket sales and how do they rank in
> terms of average ticket size?

| | |
|---|---|
| **Visual** | Table (plus a bar chart for total sales) |
| **Page** | 1 — Market Intelligence |
| **Rows** | `builder` |
| **Values** | `[Total Pipeline Value Cr]`, `[Avg Ticket Price Cr]`, `[Builder Rank by Price]`, `[Total Properties]` |
| **Sort** | `[Total Pipeline Value Cr]` descending |
| **SQL view** | `vw_top_builders` |

Add a data bar to the revenue column: **Conditional formatting → Data bars**.

*What you will see:* revenue ranges ₹107,766 Cr to ₹108,915 Cr — a 1.1% spread
driven almost entirely by row counts, not by pricing power.

---

## Q3 — Amenity Impact

> Is there a correlation between amenity score and booking success rate?

| | |
|---|---|
| **Visual** | Scatter chart |
| **Page** | 4 — Pricing |
| **X axis** | `[Avg Amenity Score]` |
| **Y axis** | `[Booking Conversion %]` |
| **Size** | `[Total Properties]` |
| **Details** | `micro_market` (or `builder` for a second view) |
| **SQL view** | `vw_amenity_conversion` |

Add **Analytics pane → Trend line**, and a **constant line at 0.5** on the Y
axis.

*What you will see:* a flat cloud. Pearson r = 0.002, p = 0.54 across 98,753
records — there is no relationship. Put the `[Conversion Signal]` measure in a
card beside it; it will read "Within noise".

---

## Q4 — Booking Conversion

> Which micro-markets have the highest and lowest booking conversion rates?

| | |
|---|---|
| **Visual** | 100% stacked column chart |
| **Page** | 2 — Sales & Conversion |
| **X axis** | `micro_market` |
| **Y axis** | `[Booking Status Share %]` |
| **Legend** | `booking_status` |
| **SQL view** | `vw_micro_market_summary` |

Pair it with a table showing `[Booking Conversion %]`,
`[Conversion Lower Bound]`, `[Conversion Upper Bound]` and
`[Conversion Signal]`, so the ranking is presented with its uncertainty.

*What you will see:* Kanakapura Road highest at 51.31%, Yelahanka lowest at
48.75%. Every confidence interval crosses 50%, so the ordering is not
meaningful — say so when presenting.

---

## Q5 — Configuration Demand

> What are the most in-demand housing configurations?

| | |
|---|---|
| **Visual** | Donut chart |
| **Page** | 1 — Market Intelligence |
| **Legend** | `configuration` |
| **Values** | `[Total Bookings]` |
| **SQL view** | `vw_configuration_demand` |

Turn on **Detail labels → Label style → Category, percent of total**.

*What you will see:* a near-perfect three-way split (3BHK 33.65%, 4BHK 33.09%,
5BHK+ 33.26% of bookings). Worth noting in your commentary: average unit size is
identical across all three configurations (6,002 / 6,008 / 6,006 sqft), which
is structurally impossible in a real market.

---

## Q6 — Sales Channel Efficiency

> Which sales channels contribute most to successful bookings?

| | |
|---|---|
| **Visual** | 100% stacked column chart |
| **Page** | 2 — Sales & Conversion |
| **X axis** | `sales_channel` |
| **Y axis** | `[Booking Status Share %]` |
| **Legend** | `booking_status` |
| **SQL view** | `vw_sales_channel_performance` |

*What you will see:* Broker 50.16%, Direct 50.07%, NRI Desk 49.94%,
Online 49.83%. Chi-square p = 0.89.

---

## Q7 — Quarterly Builder Contribution

> Which builders dominate the market each quarter?

| | |
|---|---|
| **Visual** | Matrix |
| **Page** | 1 — Market Intelligence |
| **Rows** | `builder` |
| **Columns** | `DimDate[Quarter Label]` |
| **Values** | `[Total Pipeline Value Cr]` |
| **SQL view** | `vw_builder_quarter_revenue` |

Apply **Conditional formatting → Background colour** on the value field to make
the matrix readable as a heatmap.

---

## Q8 — Possession Status Analysis

> How does possession status affect buyer type and booking decisions?

| | |
|---|---|
| **Visual** | Clustered column chart |
| **Page** | 3 — Buyer Personas |
| **X axis** | `possession_status` |
| **Y axis** | `[Booking Conversion %]` |
| **Legend** | `buyer_type` |
| **SQL view** | `vw_possession_buyer_matrix` |

The brief asks for booking status coloured by buyer type. Plotting
`[Booking Conversion %]` with `buyer_type` as the legend conveys the same
comparison in one bar per group instead of two, and keeps the Y axis readable —
set the Y axis range to 45–55 so the differences are visible.

*What you will see:* Launch 50.58%, Under Construction 49.85%, Ready to Move
49.57%. A 1.01-point spread with overlapping intervals.

---

## Q9 — Geographical Insights

> Where are most luxury housing projects concentrated within Bangalore?

| | |
|---|---|
| **Visual** | Map (bubble) |
| **Page** | 1 — Market Intelligence |
| **Latitude** | `latitude` |
| **Longitude** | `longitude` |
| **Bubble size** | `[Total Properties]` |
| **Legend** | `micro_market` |
| **Tooltips** | `[Avg Price per Sqft]`, `[Booking Conversion %]` |
| **SQL view** | `vw_micro_market_summary` |

The dataset ships no coordinates, so the pipeline adds them: approximate
locality centroids for all 16 micro-markets, joined in
`data_cleaning.py` from `config.MICRO_MARKET_COORDS`. Using explicit
latitude/longitude rather than name geocoding matters here — several of these
locality names resolve to the wrong country without a city qualifier.

If you prefer a filled map, use the `map_location` column instead (already
categorised as **Place**, and already suffixed with
"Bengaluru, Karnataka, India").

> **Note:** Power BI map visuals need **File → Options → Global → Security →
> uncheck "Block all map visuals"** if maps are disabled in your tenant.

---

## Q10 — Top Performers

> Who are the top 5 builders in terms of revenue and booking success?

| | |
|---|---|
| **Visual** | KPI cards + a table with drill-through |
| **Page** | 1 — Market Intelligence, drilling to page 5 |
| **Cards** | `[Top 5 Builders Revenue Cr]`, `[Top 5 Builders Bookings]` |
| **Table** | Rows `builder`; Values `[Total Pipeline Value Cr]`, `[Total Bookings]`, `[Booking Conversion %]`, `[Builder Revenue Rank]` |
| **Filter** | Visual-level filter: `[Is Top 5 Builder]` is 1 — or Top N filter, Top 5 by `[Total Pipeline Value Cr]` |
| **SQL view** | `vw_top_builders` |

Set up drill-through on page 5 (Data & Quality) with `builder` in the
Drill-through well, so right-clicking a builder opens its detailed project list.

*Top 5 by revenue:* SNN Raj (₹108,915 Cr), Prestige (₹108,807 Cr),
L&T Realty (₹108,164 Cr), Brigade (₹107,990 Cr), Total Environment
(₹107,766 Cr).

Note that ranking by revenue and by conversion give different orders — Total
Environment is 5th by revenue but last by conversion (49.14%), while Prestige is
2nd by revenue and 1st by conversion (50.69%). Both orderings are noise.

---

## Coverage check

| Requirement from the brief | Where it is satisfied |
|---|---|
| Slicers | Shared slicer panel on every page: Builder, Micro-market, Quarter, Configuration, Possession Status |
| Filters | Top N on Q1 and Q10; visual-level filter on Q10 |
| KPIs | Six cards on the page-1 header, plus the KPI visual on page 2 and the Q10 cards |
| Maps | Q9, using explicit latitude/longitude |
| At least one DAX measure or calculated column | 30 measures, plus the `DimDate` calculated table |
| Interactivity | Cross-filtering between all visuals, drill-through to the detail page |
