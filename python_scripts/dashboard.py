"""
dashboard.py
============
Step 3 of the Luxury Housing Sales Analysis pipeline - the interactive layer.

A Streamlit dashboard served directly off the SQL warehouse. It mirrors the
Power BI report described in `documentation/powerbi_build_guide.md`, so the two
can be compared page for page.

Run:
    streamlit run python_scripts/dashboard.py
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config as cfg  # noqa: E402

PRIMARY = "#2E5A88"
ACCENT = "#C0873A"
NEUTRAL = "#9AA0A6"
POSITIVE = "#2E7D5B"
NEGATIVE = "#B4453C"

SENTIMENT_COLORS = alt.Scale(
    domain=["Positive", "Neutral", "Negative", "No Comment"],
    range=[POSITIVE, NEUTRAL, NEGATIVE, "#C9CCD1"],
)

st.set_page_config(
    page_title="Luxury Housing Sales Analysis - Bengaluru",
    page_icon="🏙️",
    layout="wide",
)


# --------------------------------------------------------------------------
# Data
# --------------------------------------------------------------------------
@st.cache_data(show_spinner="Loading warehouse...")
def load_data() -> pd.DataFrame:
    """Read the whole warehouse table once and keep it in the session cache."""
    if not cfg.SQLITE_PATH.exists():
        st.error(
            f"Warehouse not found at `{cfg.SQLITE_PATH}`.\n\n"
            "Run `python python_scripts/data_cleaning.py` then "
            "`python python_scripts/sql_loader.py` first."
        )
        st.stop()
    with sqlite3.connect(cfg.SQLITE_PATH) as conn:
        df = pd.read_sql_query(f"SELECT * FROM {cfg.TABLE_NAME}", conn)
    df = df.rename(columns={"developer_name": "builder"})
    return df


def wilson_ci(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for a proportion, as percentages."""
    if total == 0:
        return 0.0, 0.0
    p = successes / total
    denom = 1 + z**2 / total
    centre = (p + z**2 / (2 * total)) / denom
    half = z * np.sqrt(p * (1 - p) / total + z**2 / (4 * total**2)) / denom
    return (centre - half) * 100, (centre + half) * 100


def conversion_with_ci(df: pd.DataFrame, dimension: str) -> pd.DataFrame:
    """Conversion rate plus Wilson bounds for each level of a dimension."""
    rows = []
    for level, group in df.groupby(dimension, observed=True):
        booked, total = int(group["booking_flag"].sum()), len(group)
        low, high = wilson_ci(booked, total)
        rows.append({
            dimension: level,
            "properties": total,
            "bookings": booked,
            "conversion": 100 * booked / total,
            "ci_low": low,
            "ci_high": high,
        })
    return pd.DataFrame(rows).sort_values("conversion", ascending=False)


# --------------------------------------------------------------------------
# Filters
# --------------------------------------------------------------------------
def sidebar_filters(df: pd.DataFrame) -> tuple[pd.DataFrame, bool]:
    st.sidebar.title("Filters")
    st.sidebar.caption("Every visual on every tab respects these selections.")

    def picker(label: str, column: str, default_all: bool = True):
        options = sorted(df[column].dropna().unique().tolist())
        return st.sidebar.multiselect(
            label, options, default=options if default_all else [], key=column
        )

    builders = picker("Builder", "builder")
    markets = picker("Micro-market", "micro_market")
    quarters = picker("Quarter", "quarter_label")
    configurations = picker("Configuration", "configuration")

    with st.sidebar.expander("More filters"):
        possession = st.multiselect(
            "Possession status",
            sorted(df["possession_status"].unique()),
            default=sorted(df["possession_status"].unique()),
        )
        channels = st.multiselect(
            "Sales channel",
            sorted(df["sales_channel"].unique()),
            default=sorted(df["sales_channel"].unique()),
        )
        buyers = st.multiselect(
            "Buyer type",
            sorted(df["buyer_type"].unique()),
            default=sorted(df["buyer_type"].unique()),
        )

    st.sidebar.divider()
    exclude_outliers = st.sidebar.toggle(
        "Exclude flagged price outliers",
        value=True,
        help="1,247 records sit above the IQR upper fence at exactly Rs 60, 70 "
             "or 100 Cr. They drag every average upward and are excluded by "
             "default.",
    )

    mask = (
        df["builder"].isin(builders)
        & df["micro_market"].isin(markets)
        & df["quarter_label"].isin(quarters)
        & df["configuration"].isin(configurations)
        & df["possession_status"].isin(possession)
        & df["sales_channel"].isin(channels)
        & df["buyer_type"].isin(buyers)
    )
    if exclude_outliers:
        mask &= df["is_price_outlier"] == 0

    return df[mask], exclude_outliers


# --------------------------------------------------------------------------
# KPI header
# --------------------------------------------------------------------------
def kpi_row(filtered: pd.DataFrame, full: pd.DataFrame) -> None:
    columns = st.columns(6)
    metrics = [
        ("Properties", f"{len(filtered):,}", f"{len(filtered) / len(full) * 100:.1f}% of total"),
        ("Avg ticket price", f"₹{filtered['ticket_price_cr'].mean():.2f} Cr", None),
        ("Avg price / sqft", f"₹{filtered['price_per_sqft'].mean():,.0f}", None),
        ("Booking conversion", f"{filtered['booking_flag'].mean() * 100:.2f}%", None),
        ("Avg amenity score", f"{filtered['amenity_score'].mean():.2f} / 10", None),
        ("Pipeline value", f"₹{filtered['ticket_price_cr'].sum():,.0f} Cr", None),
    ]
    for column, (label, value, delta) in zip(columns, metrics):
        column.metric(label, value, delta, delta_color="off")


# --------------------------------------------------------------------------
# Tabs
# --------------------------------------------------------------------------
def tab_market_intelligence(df: pd.DataFrame) -> None:
    # ---- Q10: top performers ---------------------------------------------
    st.subheader("Q10 · Top 5 builders by revenue")
    ranked = df.groupby("builder").agg(
        revenue=("ticket_price_cr", "sum"),
        bookings=("booking_flag", "sum"),
        properties=("property_id", "count"),
    ).reset_index().sort_values("revenue", ascending=False)
    top5 = ranked.head(5)

    cards = st.columns(5)
    for card, row in zip(cards, top5.itertuples()):
        card.metric(
            row.builder,
            f"₹{row.revenue:,.0f} Cr",
            f"{row.bookings:,} bookings · {100 * row.bookings / row.properties:.2f}%",
            delta_color="off",
        )

    # ---- Q9: geography ----------------------------------------------------
    st.subheader("Q9 · Where the projects are")
    st.caption(
        "Bubble size is transaction volume. Coordinates are approximate "
        "locality centroids — the raw dataset ships none."
    )
    geo = df.groupby(["micro_market", "latitude", "longitude"]).agg(
        properties=("property_id", "count"),
    ).reset_index()
    geo["size"] = geo["properties"] / 8
    st.map(geo, latitude="latitude", longitude="longitude", size="size",
           color="#2E5A88AA")

    # ---- Q1: quarterly bookings by micro-market ---------------------------
    st.subheader("Q1 · Bookings by quarter and micro-market")
    top_n = st.slider("Show top N micro-markets by bookings", 3, 16, 6,
                      key="q1_top_n")
    by_market = (df.groupby("micro_market")["booking_flag"].sum()
                   .sort_values(ascending=False).head(top_n).index)
    trend = (df[df["micro_market"].isin(by_market)]
             .groupby(["quarter_label", "micro_market"])["booking_flag"]
             .sum().reset_index(name="bookings"))
    chart = alt.Chart(trend).mark_line(point=True, strokeWidth=2).encode(
        x=alt.X("quarter_label:N", title=None),
        y=alt.Y("bookings:Q", title="Bookings", scale=alt.Scale(zero=False)),
        color=alt.Color("micro_market:N", title="Micro-market"),
        tooltip=["micro_market", "quarter_label",
                 alt.Tooltip("bookings:Q", format=",")],
    ).properties(height=340)
    st.altair_chart(chart, use_container_width=True)

    st.subheader("Q2 · Builder performance")

    builders = df.groupby("builder").agg(
        properties=("property_id", "count"),
        avg_price=("ticket_price_cr", "mean"),
        sem_price=("ticket_price_cr", "sem"),
        avg_psf=("price_per_sqft", "mean"),
        conversion=("booking_flag", "mean"),
        avg_amenity=("amenity_score", "mean"),
    ).reset_index()
    builders["conversion"] *= 100
    builders["ci_low"] = builders["avg_price"] - 1.96 * builders["sem_price"]
    builders["ci_high"] = builders["avg_price"] + 1.96 * builders["sem_price"]

    left, right = st.columns(2)
    with left:
        # A dot plot, not a bar chart: a non-zero axis is only legitimate when
        # the mark does not encode magnitude by length, and the intervals show
        # that the builders are statistically indistinguishable.
        points = alt.Chart(builders).mark_circle(size=140, color=PRIMARY).encode(
            x=alt.X("avg_price:Q", title="Average ticket price (₹ Cr)",
                    scale=alt.Scale(zero=False)),
            y=alt.Y("builder:N", sort="-x", title=None),
            tooltip=["builder", alt.Tooltip("avg_price:Q", format=".2f"),
                     alt.Tooltip("properties:Q", format=",")],
        )
        errors = alt.Chart(builders).mark_errorbar(color=ACCENT).encode(
            x=alt.X("ci_low:Q", title="Average ticket price (₹ Cr)"),
            x2="ci_high:Q",
            y=alt.Y("builder:N", sort="-x"),
        )
        st.altair_chart(
            (errors + points).properties(
                height=320,
                title="Average ticket price by builder (95% CI)"),
            use_container_width=True)

    with right:
        chart = alt.Chart(builders).mark_circle(size=180, opacity=0.85).encode(
            x=alt.X("avg_psf:Q", title="Average price per sqft (₹)",
                    scale=alt.Scale(zero=False)),
            y=alt.Y("conversion:Q", title="Booking conversion (%)",
                    scale=alt.Scale(zero=False)),
            color=alt.Color("builder:N", legend=None),
            size=alt.Size("properties:Q", legend=None),
            tooltip=["builder", alt.Tooltip("avg_psf:Q", format=",.0f"),
                     alt.Tooltip("conversion:Q", format=".2f")],
        ).properties(height=320, title="Price positioning vs conversion")
        st.altair_chart(chart, use_container_width=True)

    st.subheader("Micro-market landscape")
    markets = df.groupby("micro_market").agg(
        properties=("property_id", "count"),
        avg_psf=("price_per_sqft", "mean"),
        sem_psf=("price_per_sqft", "sem"),
        conversion=("booking_flag", "mean"),
        avg_amenity=("amenity_score", "mean"),
        avg_traffic=("avg_traffic_time_min", "mean"),
    ).reset_index()
    markets["conversion"] *= 100
    markets["ci_low"] = markets["avg_psf"] - 1.96 * markets["sem_psf"]
    markets["ci_high"] = markets["avg_psf"] + 1.96 * markets["sem_psf"]

    points = alt.Chart(markets).mark_circle(size=160).encode(
        x=alt.X("avg_psf:Q", title="Average price per sqft (₹)",
                scale=alt.Scale(zero=False)),
        y=alt.Y("micro_market:N", sort="-x", title=None),
        color=alt.Color("avg_amenity:Q", scale=alt.Scale(scheme="blues"),
                        title="Amenity score"),
        tooltip=["micro_market", alt.Tooltip("avg_psf:Q", format=",.0f"),
                 alt.Tooltip("conversion:Q", format=".2f"),
                 alt.Tooltip("properties:Q", format=",")],
    )
    errors = alt.Chart(markets).mark_errorbar(color=NEUTRAL).encode(
        x=alt.X("ci_low:Q", title="Average price per sqft (₹)"),
        x2="ci_high:Q",
        y=alt.Y("micro_market:N", sort="-x"),
    )
    st.altair_chart(
        (errors + points).properties(
            height=420, title="Price per sqft by micro-market (95% CI)"),
        use_container_width=True)

    st.subheader("Q5 · Configuration demand")
    left, right = st.columns([1, 1.4])

    with left:
        demand = (df.groupby("configuration")["booking_flag"]
                    .sum().reset_index(name="bookings"))
        demand["share"] = 100 * demand["bookings"] / demand["bookings"].sum()
        chart = alt.Chart(demand).mark_arc(innerRadius=70).encode(
            theta="bookings:Q",
            color=alt.Color("configuration:N",
                            scale=alt.Scale(range=[PRIMARY, ACCENT, NEUTRAL]),
                            title="Configuration"),
            tooltip=["configuration", alt.Tooltip("bookings:Q", format=","),
                     alt.Tooltip("share:Q", format=".2f", title="Share %")],
        ).properties(height=320, title="Bookings by configuration")
        st.altair_chart(chart, use_container_width=True)

    with right:
        mix = (df.groupby(["quarter_label", "configuration"])
                 .size().reset_index(name="properties"))
        chart = alt.Chart(mix).mark_bar().encode(
            x=alt.X("quarter_label:N", title=None),
            y=alt.Y("properties:Q", stack="normalize",
                    title="Share of transactions"),
            color=alt.Color("configuration:N",
                            scale=alt.Scale(range=[PRIMARY, ACCENT, NEUTRAL]),
                            title="Configuration"),
            tooltip=["quarter_label", "configuration",
                     alt.Tooltip("properties:Q", format=",")],
        ).properties(height=320, title="Configuration mix by quarter")
        st.altair_chart(chart, use_container_width=True)

    st.subheader("Q7 · Builder revenue by quarter")
    st.caption("Total ticket value in ₹ Cr. Darker cells are higher revenue.")
    matrix = df.pivot_table(index="builder", columns="quarter_label",
                            values="ticket_price_cr", aggfunc="sum")
    st.dataframe(
        matrix.style.format("{:,.0f}").background_gradient(cmap="Blues", axis=None),
        use_container_width=True,
    )


def tab_sales_conversion(df: pd.DataFrame) -> None:
    st.subheader("Quarterly trend")

    quarterly = df.groupby("quarter_label").agg(
        properties=("property_id", "count"),
        avg_price=("ticket_price_cr", "mean"),
        conversion=("booking_flag", "mean"),
    ).reset_index()
    quarterly["conversion"] *= 100

    base = alt.Chart(quarterly).encode(x=alt.X("quarter_label:N", title=None))
    volume = base.mark_bar(color=PRIMARY, opacity=0.75).encode(
        y=alt.Y("properties:Q", title="Transactions"),
        tooltip=["quarter_label", alt.Tooltip("properties:Q", format=",")],
    )
    price = base.mark_line(color=ACCENT, strokeWidth=3, point=True).encode(
        y=alt.Y("avg_price:Q", title="Avg ticket price (₹ Cr)",
                scale=alt.Scale(zero=False)),
        tooltip=[alt.Tooltip("avg_price:Q", format=".2f")],
    )
    st.altair_chart(
        alt.layer(volume, price).resolve_scale(y="independent").properties(height=320),
        use_container_width=True,
    )

    st.subheader("Where deals drop off")
    left, right = st.columns(2)

    with left:
        channel = df.groupby("sales_channel").agg(
            booked=("booking_flag", "sum"),
            total=("property_id", "count"),
        ).reset_index()
        channel["dropped"] = channel["total"] - channel["booked"]
        melted = channel.melt(id_vars="sales_channel",
                              value_vars=["booked", "dropped"],
                              var_name="outcome", value_name="properties")
        chart = alt.Chart(melted).mark_bar().encode(
            x=alt.X("sales_channel:N", title=None),
            y=alt.Y("properties:Q", title="Properties"),
            color=alt.Color("outcome:N",
                            scale=alt.Scale(domain=["booked", "dropped"],
                                            range=[POSITIVE, NEUTRAL]),
                            title="Outcome"),
            tooltip=["sales_channel", "outcome",
                     alt.Tooltip("properties:Q", format=",")],
        ).properties(height=320, title="Booked vs dropped by channel")
        st.altair_chart(chart, use_container_width=True)

    with right:
        possession = conversion_with_ci(df, "possession_status")
        chart = alt.Chart(possession).mark_bar(color=PRIMARY).encode(
            x=alt.X("possession_status:N", title=None),
            y=alt.Y("conversion:Q", title="Conversion (%)",
                    scale=alt.Scale(domain=[45, 55])),
            tooltip=["possession_status", alt.Tooltip("conversion:Q", format=".2f")],
        )
        errors = alt.Chart(possession).mark_errorbar(color=ACCENT).encode(
            x="possession_status:N",
            y=alt.Y("ci_low:Q", title="Conversion (%)"),
            y2="ci_high:Q",
        )
        st.altair_chart((chart + errors).properties(
            height=320, title="Conversion by possession status"),
            use_container_width=True)

    st.subheader("Conversion by micro-market")
    st.caption(
        "Error bars are 95% Wilson intervals. They all cross the 50% line, "
        "which means the ranking below is not statistically meaningful — see "
        "`outputs/eda_findings.md`."
    )
    markets = conversion_with_ci(df, "micro_market")
    bars = alt.Chart(markets).mark_bar(color=PRIMARY).encode(
        x=alt.X("conversion:Q", title="Booking conversion (%)",
                scale=alt.Scale(domain=[44, 56])),
        y=alt.Y("micro_market:N", sort="-x", title=None),
        tooltip=["micro_market", alt.Tooltip("conversion:Q", format=".2f"),
                 alt.Tooltip("properties:Q", format=",")],
    )
    errors = alt.Chart(markets).mark_errorbar(color=ACCENT).encode(
        x=alt.X("ci_low:Q", title="Booking conversion (%)"),
        x2="ci_high:Q",
        y=alt.Y("micro_market:N", sort="-x"),
    )
    baseline = alt.Chart(pd.DataFrame({"x": [50]})).mark_rule(
        color=NEGATIVE, strokeDash=[6, 4], strokeWidth=2).encode(x="x:Q")
    st.altair_chart((bars + errors + baseline).properties(height=460),
                    use_container_width=True)


def tab_buyer_personas(df: pd.DataFrame) -> None:
    st.subheader("Persona economics")

    left, right = st.columns([1.2, 1])
    with left:
        persona = df.groupby(["buyer_type", "nri_buyer"]).agg(
            avg_price=("ticket_price_cr", "mean"),
            properties=("property_id", "count"),
        ).reset_index()
        chart = alt.Chart(persona).mark_rect().encode(
            x=alt.X("nri_buyer:N", title="NRI buyer"),
            y=alt.Y("buyer_type:N", title=None),
            color=alt.Color("avg_price:Q", scale=alt.Scale(scheme="blues"),
                            title="Avg ₹ Cr"),
            tooltip=["buyer_type", "nri_buyer",
                     alt.Tooltip("avg_price:Q", format=".2f"),
                     alt.Tooltip("properties:Q", format=",")],
        ).properties(height=320, title="Average ticket price by persona")
        labels = chart.mark_text(baseline="middle", fontWeight="bold").encode(
            text=alt.Text("avg_price:Q", format=".2f"),
            color=alt.value("white"),
        )
        st.altair_chart(chart + labels, use_container_width=True)

    with right:
        volume = df.groupby(["buyer_type", "nri_buyer"]).size().reset_index(
            name="properties")
        chart = alt.Chart(volume).mark_bar().encode(
            x=alt.X("properties:Q", title="Properties", stack="zero"),
            y=alt.Y("buyer_type:N", sort="-x", title=None),
            color=alt.Color("nri_buyer:N",
                            scale=alt.Scale(range=[PRIMARY, ACCENT]),
                            title="NRI buyer"),
            tooltip=["buyer_type", "nri_buyer",
                     alt.Tooltip("properties:Q", format=",")],
        ).properties(height=320, title="Volume by persona")
        st.altair_chart(chart, use_container_width=True)

    st.subheader("Buyer sentiment")
    left, right = st.columns([1, 1.4])

    with left:
        sentiment = df["comment_sentiment"].value_counts().reset_index()
        sentiment.columns = ["sentiment", "mentions"]
        chart = alt.Chart(sentiment).mark_arc(innerRadius=70).encode(
            theta="mentions:Q",
            color=alt.Color("sentiment:N", scale=SENTIMENT_COLORS, title="Sentiment"),
            tooltip=["sentiment", alt.Tooltip("mentions:Q", format=",")],
        ).properties(height=330, title="Sentiment mix")
        st.altair_chart(chart, use_container_width=True)

    with right:
        comments = (df[df["buyer_comments"] != cfg.NO_COMMENT]
                    .groupby(["buyer_comments", "comment_sentiment"])
                    .size().reset_index(name="mentions"))
        chart = alt.Chart(comments).mark_bar().encode(
            x=alt.X("mentions:Q", title="Mentions"),
            y=alt.Y("buyer_comments:N", sort="-x", title=None),
            color=alt.Color("comment_sentiment:N", scale=SENTIMENT_COLORS,
                            title="Sentiment"),
            tooltip=["buyer_comments", "comment_sentiment",
                     alt.Tooltip("mentions:Q", format=",")],
        ).properties(height=330, title="What buyers actually said")
        st.altair_chart(chart, use_container_width=True)


def tab_pricing(df: pd.DataFrame) -> None:
    st.subheader("Price distribution")

    left, right = st.columns([1.4, 1])
    with left:
        chart = alt.Chart(df.sample(min(len(df), 5000), random_state=0)).mark_bar(
            color=PRIMARY).encode(
            x=alt.X("ticket_price_cr:Q", bin=alt.Bin(maxbins=50),
                    title="Ticket price (₹ Cr)"),
            y=alt.Y("count():Q", title="Properties (5k sample)"),
            tooltip=[alt.Tooltip("count():Q", format=",")],
        ).properties(height=330, title="Ticket price histogram")
        st.altair_chart(chart, use_container_width=True)

    with right:
        segments = df["price_segment"].value_counts().reset_index()
        segments.columns = ["segment", "properties"]
        chart = alt.Chart(segments).mark_bar(color=ACCENT).encode(
            x=alt.X("properties:Q", title="Properties"),
            y=alt.Y("segment:N", sort="-x", title=None),
            tooltip=["segment", alt.Tooltip("properties:Q", format=",")],
        ).properties(height=330, title="Price segment mix")
        st.altair_chart(chart, use_container_width=True)

    st.subheader("Competitive pricing — builder premium vs market")
    st.caption(
        "How each builder's price per sqft compares with the average of the "
        "micro-markets it operates in. Positive means priced above the local market."
    )

    builder_market = df.groupby(["micro_market", "builder"]).agg(
        properties=("property_id", "count"),
        avg_psf=("price_per_sqft", "mean"),
    ).reset_index()
    market_avg = df.groupby("micro_market")["price_per_sqft"].mean().rename("market_psf")
    merged = builder_market.join(market_avg, on="micro_market")
    merged["premium_pct"] = 100 * (merged["avg_psf"] - merged["market_psf"]) / merged["market_psf"]

    premium = (merged.groupby("builder")
                     .apply(lambda g: np.average(g["premium_pct"], weights=g["properties"]),
                            include_groups=False)
                     .reset_index(name="premium_pct"))

    chart = alt.Chart(premium).mark_bar().encode(
        x=alt.X("premium_pct:Q", title="Premium vs local market (%)"),
        y=alt.Y("builder:N", sort="-x", title=None),
        color=alt.condition(alt.datum.premium_pct > 0,
                            alt.value(ACCENT), alt.value(PRIMARY)),
        tooltip=["builder", alt.Tooltip("premium_pct:Q", format="+.2f")],
    ).properties(height=340)
    st.altair_chart(chart, use_container_width=True)

    st.subheader("Amenity score vs conversion")
    amenity = conversion_with_ci(df, "amenity_band")
    order = [b for b in ["Low", "Medium", "High"] if b in amenity["amenity_band"].values]
    bars = alt.Chart(amenity).mark_bar(color=PRIMARY).encode(
        x=alt.X("amenity_band:N", sort=order, title="Amenity band"),
        y=alt.Y("conversion:Q", title="Conversion (%)",
                scale=alt.Scale(domain=[45, 55])),
        tooltip=["amenity_band", alt.Tooltip("conversion:Q", format=".2f"),
                 alt.Tooltip("properties:Q", format=",")],
    )
    errors = alt.Chart(amenity).mark_errorbar(color=ACCENT).encode(
        x=alt.X("amenity_band:N", sort=order),
        y=alt.Y("ci_low:Q", title="Conversion (%)"), y2="ci_high:Q",
    )
    baseline = alt.Chart(pd.DataFrame({"y": [50]})).mark_rule(
        color=NEGATIVE, strokeDash=[6, 4], strokeWidth=2).encode(y="y:Q")
    st.altair_chart((bars + errors + baseline).properties(height=320),
                    use_container_width=True)


def tab_data(df: pd.DataFrame, full: pd.DataFrame) -> None:
    st.subheader("Filtered records")
    st.caption(f"{len(df):,} rows match the current filters.")

    st.dataframe(df.head(1000), use_container_width=True, height=420)
    st.download_button(
        "Download filtered data as CSV",
        df.to_csv(index=False).encode("utf-8"),
        file_name="luxury_housing_filtered.csv",
        mime="text/csv",
    )

    st.subheader("Cleaning transparency")
    columns = st.columns(4)
    columns[0].metric("Imputed prices", f"{int(full['price_imputed'].sum()):,}")
    columns[1].metric("Imputed sizes", f"{int(full['size_imputed'].sum()):,}")
    columns[2].metric("Imputed amenity scores", f"{int(full['amenity_imputed'].sum()):,}")
    columns[3].metric("Flagged price outliers", f"{int(full['is_price_outlier'].sum()):,}")

    st.info(
        "**Derived-field assumption.** The raw file has no `Booking_Status` "
        "column. `Booking_Flag` is derived from `Transaction_Type`: a Primary "
        "transaction (direct from the developer) counts as a booking, a "
        "Secondary transaction (resale) does not. Every conversion figure in "
        "this dashboard rests on that definition."
    )


# --------------------------------------------------------------------------
# App
# --------------------------------------------------------------------------
def main() -> None:
    full = load_data()
    filtered, exclude_outliers = sidebar_filters(full)

    st.title("Luxury Housing Sales Analysis — Bengaluru")
    st.caption(
        f"{len(full):,} transactions · {full['builder'].nunique()} builders · "
        f"{full['micro_market'].nunique()} micro-markets · "
        f"{full['quarter_label'].min()} to {full['quarter_label'].max()}"
        + ("  ·  price outliers excluded" if exclude_outliers else
           "  ·  **price outliers included**")
    )

    if filtered.empty:
        st.warning("No records match the current filters. Widen the selection "
                   "in the sidebar.")
        st.stop()

    kpi_row(filtered, full)
    st.divider()

    tabs = st.tabs([
        "Market Intelligence",
        "Sales & Conversion",
        "Buyer Personas",
        "Pricing",
        "Data & Quality",
    ])
    with tabs[0]:
        tab_market_intelligence(filtered)
    with tabs[1]:
        tab_sales_conversion(filtered)
    with tabs[2]:
        tab_buyer_personas(filtered)
    with tabs[3]:
        tab_pricing(filtered)
    with tabs[4]:
        tab_data(filtered, full)


if __name__ == "__main__":
    main()
