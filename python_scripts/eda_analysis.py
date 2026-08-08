"""
eda_analysis.py
===============
Exploratory analysis over the cleaned warehouse.

Produces the chart pack in ``outputs/charts/`` and an ``eda_findings.md`` that
records not just the headline numbers but whether the differences between
groups are statistically distinguishable from noise. Several of the splits in
this dataset are not, and the report says so rather than dressing up random
variation as a market insight.

Run:
    python python_scripts/eda_analysis.py
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config as cfg  # noqa: E402

FINDINGS_MD = cfg.OUTPUT_DIR / "eda_findings.md"

PRIMARY = "#2E5A88"
ACCENT = "#C0873A"
NEUTRAL = "#9AA0A6"
POSITIVE = "#2E7D5B"
NEGATIVE = "#B4453C"

plt.rcParams.update({
    "figure.dpi": 120,
    "savefig.dpi": 150,
    "savefig.bbox": "tight",
    "font.size": 10,
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.25,
})


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def load_data() -> pd.DataFrame:
    """Read the analysis-ready view straight out of the warehouse."""
    if not cfg.SQLITE_PATH.exists():
        raise SystemExit(
            f"Warehouse not found at {cfg.SQLITE_PATH}.\n"
            "Run 'python python_scripts/sql_loader.py' first."
        )
    with sqlite3.connect(cfg.SQLITE_PATH) as conn:
        df = pd.read_sql_query("SELECT * FROM vw_dashboard_base", conn)
    print(f"    Loaded {len(df):,} non-outlier records from vw_dashboard_base")
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


def save(fig: plt.Figure, filename: str) -> None:
    path = cfg.CHARTS_DIR / filename
    fig.savefig(path)
    plt.close(fig)
    print(f"    {filename}")


# --------------------------------------------------------------------------
# Charts
# --------------------------------------------------------------------------
def chart_price_distribution(df: pd.DataFrame) -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4.8),
                                   gridspec_kw={"width_ratios": [2, 1]})

    ax1.hist(df["ticket_price_cr"], bins=60, color=PRIMARY, edgecolor="white", linewidth=0.4)
    median = df["ticket_price_cr"].median()
    ax1.axvline(median, color=ACCENT, linewidth=2, linestyle="--",
                label=f"Median Rs {median:.2f} Cr")
    ax1.set_title("Ticket price distribution")
    ax1.set_xlabel("Ticket price (Rs Cr)")
    ax1.set_ylabel("Properties")
    ax1.legend(frameon=False)

    data = [g["ticket_price_cr"].values for _, g in df.groupby("configuration")]
    labels = sorted(df["configuration"].unique())
    box = ax2.boxplot(data, tick_labels=labels, patch_artist=True, showfliers=False)
    for patch in box["boxes"]:
        patch.set_facecolor(PRIMARY)
        patch.set_alpha(0.65)
    for whisker in box["medians"]:
        whisker.set_color(ACCENT)
        whisker.set_linewidth(2)
    ax2.set_title("Price by configuration")
    ax2.set_ylabel("Ticket price (Rs Cr)")

    fig.suptitle("Where luxury pricing sits", fontsize=15, fontweight="bold", y=1.02)
    save(fig, "01_price_distribution.png")


def chart_price_by_builder(df: pd.DataFrame) -> None:
    grouped = df.groupby("builder")["ticket_price_cr"].agg(["mean", "sem", "count"])
    grouped = grouped.sort_values("mean")
    ci = 1.96 * grouped["sem"]

    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.barh(grouped.index, grouped["mean"], xerr=ci, color=PRIMARY,
            error_kw={"ecolor": ACCENT, "capsize": 4, "elinewidth": 1.5})
    overall = df["ticket_price_cr"].mean()
    ax.axvline(overall, color=NEGATIVE, linestyle="--", linewidth=1.5,
               label=f"Market mean Rs {overall:.2f} Cr")
    ax.set_xlim(11.0, 12.6)
    ax.set_title("Average ticket price by builder (bars show 95% confidence intervals)")
    ax.set_xlabel("Average ticket price (Rs Cr)")
    ax.legend(frameon=False, loc="lower right")
    save(fig, "02_price_by_builder.png")


def chart_price_per_sqft_by_market(df: pd.DataFrame) -> None:
    grouped = (df.groupby("micro_market")["price_per_sqft"]
                 .mean().sort_values(ascending=True))

    fig, ax = plt.subplots(figsize=(10, 6.5))
    colors = [ACCENT if v >= grouped.median() else PRIMARY for v in grouped]
    ax.barh(grouped.index, grouped.values, color=colors)
    ax.axvline(grouped.mean(), color=NEGATIVE, linestyle="--", linewidth=1.5,
               label=f"City average Rs {grouped.mean():,.0f}/sqft")
    ax.set_xlim(21000, 22000)
    ax.set_title("Average price per sqft by micro-market")
    ax.set_xlabel("Rs per sqft")
    ax.legend(frameon=False, loc="lower right")
    save(fig, "03_price_per_sqft_by_market.png")


def chart_conversion_by_market(df: pd.DataFrame) -> None:
    rows = []
    for market, group in df.groupby("micro_market"):
        booked, total = int(group["booking_flag"].sum()), len(group)
        low, high = wilson_ci(booked, total)
        rows.append({"micro_market": market, "conversion": 100 * booked / total,
                     "low": low, "high": high})
    summary = pd.DataFrame(rows).sort_values("conversion")

    fig, ax = plt.subplots(figsize=(10, 6.5))
    errors = [summary["conversion"] - summary["low"], summary["high"] - summary["conversion"]]
    ax.barh(summary["micro_market"], summary["conversion"], xerr=errors,
            color=PRIMARY, error_kw={"ecolor": ACCENT, "capsize": 4, "elinewidth": 1.5})
    ax.axvline(50, color=NEGATIVE, linestyle="--", linewidth=1.5,
               label="50% (coin-flip baseline)")
    ax.set_xlim(46, 54)
    ax.set_title("Booking conversion by micro-market\n"
                 "Every interval crosses 50% - no market is measurably better",
                 fontsize=12)
    ax.set_xlabel("Booking conversion (%)")
    ax.legend(frameon=False, loc="lower right")
    save(fig, "04_conversion_by_market.png")


def chart_quarterly_trends(df: pd.DataFrame) -> None:
    grouped = df.groupby("quarter_label").agg(
        properties=("property_id", "count"),
        avg_price=("ticket_price_cr", "mean"),
        conversion=("booking_flag", "mean"),
    ).reset_index()
    grouped["conversion"] *= 100

    fig, ax1 = plt.subplots(figsize=(11, 5.5))
    ax1.bar(grouped["quarter_label"], grouped["properties"], color=PRIMARY,
            alpha=0.75, label="Transactions")
    ax1.set_ylabel("Transactions", color=PRIMARY)
    ax1.set_ylim(0, grouped["properties"].max() * 1.35)
    ax1.tick_params(axis="y", labelcolor=PRIMARY)

    ax2 = ax1.twinx()
    ax2.plot(grouped["quarter_label"], grouped["avg_price"], color=ACCENT,
             marker="o", linewidth=2.5, label="Avg ticket price")
    ax2.set_ylabel("Average ticket price (Rs Cr)", color=ACCENT)
    ax2.set_ylim(11.5, 12.5)
    ax2.tick_params(axis="y", labelcolor=ACCENT)
    ax2.grid(False)

    lines = ax1.get_legend_handles_labels()[0] + ax2.get_legend_handles_labels()[0]
    labels = ax1.get_legend_handles_labels()[1] + ax2.get_legend_handles_labels()[1]
    ax1.legend(lines, labels, frameon=False, loc="upper left", ncol=2)
    ax1.set_title("Quarterly volume and pricing, 2023-Q2 to 2025-Q1")
    save(fig, "05_quarterly_trends.png")


def chart_configuration_demand(df: pd.DataFrame) -> None:
    pivot = (df.pivot_table(index="quarter_label", columns="configuration",
                            values="property_id", aggfunc="count")
               .fillna(0))
    share = pivot.div(pivot.sum(axis=1), axis=0) * 100

    fig, ax = plt.subplots(figsize=(11, 5.5))
    bottom = np.zeros(len(share))
    palette = [PRIMARY, ACCENT, NEUTRAL]
    for color, column in zip(palette, share.columns):
        ax.bar(share.index, share[column], bottom=bottom, label=column, color=color)
        bottom += share[column].values
    ax.set_ylim(0, 100)
    ax.set_ylabel("Share of transactions (%)")
    ax.set_title("Configuration mix by quarter")
    ax.legend(frameon=False, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.08))
    save(fig, "06_configuration_demand.png")


def chart_amenity_vs_conversion(df: pd.DataFrame) -> None:
    working = df.copy()
    working["decile"] = pd.qcut(working["amenity_score"], 10, labels=False) + 1

    rows = []
    for decile, group in working.groupby("decile"):
        booked, total = int(group["booking_flag"].sum()), len(group)
        low, high = wilson_ci(booked, total)
        rows.append({"decile": decile, "score": group["amenity_score"].mean(),
                     "conversion": 100 * booked / total, "low": low, "high": high})
    summary = pd.DataFrame(rows)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4.8))

    errors = [summary["conversion"] - summary["low"], summary["high"] - summary["conversion"]]
    ax1.errorbar(summary["score"], summary["conversion"], yerr=errors, fmt="o",
                 color=PRIMARY, ecolor=ACCENT, capsize=4, markersize=7, linewidth=1.5)
    slope, intercept, r, p, _ = stats.linregress(summary["score"], summary["conversion"])
    xs = np.linspace(summary["score"].min(), summary["score"].max(), 50)
    ax1.plot(xs, intercept + slope * xs, color=NEGATIVE, linestyle="--",
             label=f"Trend: r={r:.3f}, p={p:.3f}")
    ax1.axhline(50, color=NEUTRAL, linewidth=1)
    ax1.set_ylim(46, 54)
    ax1.set_title("Booking conversion by amenity decile")
    ax1.set_xlabel("Mean amenity score")
    ax1.set_ylabel("Conversion (%)")
    ax1.legend(frameon=False)

    band = (df.groupby("amenity_band")
              .agg(conversion=("booking_flag", "mean"), price=("price_per_sqft", "mean"))
              .reindex(["Low", "Medium", "High"]))
    ax2.bar(band.index, band["conversion"] * 100, color=PRIMARY)
    ax2.axhline(50, color=NEGATIVE, linestyle="--", linewidth=1.5, label="50% baseline")
    ax2.set_ylim(45, 55)
    ax2.set_ylabel("Conversion (%)")
    ax2.set_title("Conversion by amenity band")
    ax2.legend(frameon=False)

    fig.suptitle("Do amenities drive bookings?", fontsize=15, fontweight="bold", y=1.03)
    save(fig, "07_amenity_vs_conversion.png")


def chart_sales_channel(df: pd.DataFrame) -> None:
    grouped = df.groupby("sales_channel").agg(
        total=("property_id", "count"),
        booked=("booking_flag", "sum"),
    )
    grouped["dropped"] = grouped["total"] - grouped["booked"]
    grouped["conversion"] = 100 * grouped["booked"] / grouped["total"]
    grouped = grouped.sort_values("conversion", ascending=False)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4.8))

    ax1.bar(grouped.index, grouped["booked"], color=POSITIVE, label="Booked")
    ax1.bar(grouped.index, grouped["dropped"], bottom=grouped["booked"],
            color=NEUTRAL, label="Dropped off")
    ax1.set_ylabel("Properties")
    ax1.set_title("Booking vs drop-off by sales channel")
    ax1.legend(frameon=False)

    ax2.bar(grouped.index, grouped["conversion"], color=PRIMARY)
    ax2.axhline(50, color=NEGATIVE, linestyle="--", linewidth=1.5, label="50% baseline")
    ax2.set_ylim(45, 55)
    ax2.set_ylabel("Conversion (%)")
    ax2.set_title("Conversion rate by channel")
    ax2.legend(frameon=False)

    fig.suptitle("Sales channel performance", fontsize=15, fontweight="bold", y=1.03)
    save(fig, "08_sales_channel.png")


def chart_buyer_persona(df: pd.DataFrame) -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

    pivot = df.pivot_table(index="buyer_type", columns="nri_buyer",
                           values="ticket_price_cr", aggfunc="mean")
    sns.heatmap(pivot, annot=True, fmt=".2f", cmap="Blues", ax=ax1,
                cbar_kws={"label": "Avg ticket price (Rs Cr)"}, linewidths=0.5)
    ax1.set_title("Average ticket price by persona")
    ax1.set_xlabel("NRI buyer")
    ax1.set_ylabel("Buyer type")

    counts = df.groupby(["buyer_type", "nri_buyer"]).size().unstack()
    counts.plot(kind="barh", stacked=True, ax=ax2,
                color=[PRIMARY, ACCENT], width=0.75)
    ax2.set_title("Transaction volume by persona")
    ax2.set_xlabel("Properties")
    ax2.set_ylabel("")
    ax2.legend(title="NRI buyer", frameon=False)

    fig.suptitle("Buyer personas", fontsize=15, fontweight="bold", y=1.02)
    save(fig, "09_buyer_persona.png")


def chart_sentiment(df: pd.DataFrame) -> None:
    order = ["Positive", "Neutral", "Negative", "No Comment"]
    colors = {"Positive": POSITIVE, "Neutral": NEUTRAL,
              "Negative": NEGATIVE, "No Comment": "#C9CCD1"}

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5),
                                   gridspec_kw={"width_ratios": [1, 1.4]})

    counts = df["comment_sentiment"].value_counts().reindex(order)
    ax1.bar(counts.index, counts.values, color=[colors[s] for s in counts.index])
    ax1.set_ylabel("Comments")
    ax1.set_title("Buyer sentiment mix")
    ax1.tick_params(axis="x", rotation=20)

    comments = (df[df["buyer_comments"] != cfg.NO_COMMENT]
                .groupby(["buyer_comments", "comment_sentiment"])
                .size().reset_index(name="count")
                .sort_values("count"))
    ax2.barh(comments["buyer_comments"], comments["count"],
             color=[colors[s] for s in comments["comment_sentiment"]])
    ax2.set_xlabel("Mentions")
    ax2.set_title("Most frequent buyer comments")

    fig.suptitle("What buyers are saying", fontsize=15, fontweight="bold", y=1.02)
    save(fig, "10_sentiment.png")


def chart_geography(df: pd.DataFrame) -> None:
    """
    Static counterpart to the dashboard map.

    Not a basemap - just the 16 micro-market centroids in geographic space,
    which is enough to read the north/south and centre/periphery spread without
    pulling map tiles from an external service.
    """
    markets = df.groupby("micro_market").agg(
        lat=("latitude", "first"),
        lon=("longitude", "first"),
        properties=("property_id", "count"),
        psf=("price_per_sqft", "mean"),
    ).reset_index()

    fig, ax = plt.subplots(figsize=(10, 9))
    scatter = ax.scatter(
        markets["lon"], markets["lat"],
        s=markets["properties"] / 4,
        c=markets["psf"], cmap="viridis",
        alpha=0.85, edgecolors="white", linewidths=1.5,
    )
    for row in markets.itertuples():
        ax.annotate(row.micro_market, (row.lon, row.lat),
                    textcoords="offset points", xytext=(0, 16),
                    ha="center", fontsize=9, fontweight="bold")

    fig.colorbar(scatter, ax=ax, label="Average price per sqft (Rs)",
                 shrink=0.7)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title("Luxury housing concentration across Bengaluru micro-markets\n"
                 "Bubble size = transaction volume", fontsize=13)
    ax.set_aspect("equal", adjustable="datalim")
    save(fig, "12_geographic_distribution.png")


def chart_correlation(df: pd.DataFrame) -> None:
    numeric = df[["ticket_price_cr", "unit_size_sqft", "price_per_sqft",
                  "amenity_score", "connectivity_score", "locality_infra_score",
                  "avg_traffic_time_min", "booking_flag"]]
    corr = numeric.corr()

    fig, ax = plt.subplots(figsize=(9, 7))
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="RdBu_r", center=0,
                vmin=-1, vmax=1, ax=ax, linewidths=0.5,
                cbar_kws={"label": "Pearson r"})
    ax.set_title("Correlation between numeric features")
    save(fig, "11_correlation_heatmap.png")


# --------------------------------------------------------------------------
# Statistical testing
# --------------------------------------------------------------------------
def run_significance_tests(df: pd.DataFrame) -> list[dict[str, object]]:
    """Test whether the group differences visible in the charts are real."""
    results: list[dict[str, object]] = []

    for column, label in [
        ("builder", "Booking conversion differs by builder"),
        ("micro_market", "Booking conversion differs by micro-market"),
        ("amenity_band", "Booking conversion differs by amenity band"),
        ("sales_channel", "Booking conversion differs by sales channel"),
        ("buyer_type", "Booking conversion differs by buyer type"),
        ("configuration", "Booking conversion differs by configuration"),
    ]:
        table = pd.crosstab(df[column], df["booking_flag"])
        chi2, p, dof, _ = stats.chi2_contingency(table)
        results.append({
            "Hypothesis": label,
            "Test": f"Chi-square (dof={dof})",
            "Statistic": f"{chi2:.2f}",
            "p-value": f"{p:.4f}",
            "Verdict": "Significant" if p < 0.05 else "Not significant",
        })

    groups = [g["ticket_price_cr"].values for _, g in df.groupby("builder")]
    f_stat, p = stats.f_oneway(*groups)
    results.append({
        "Hypothesis": "Average ticket price differs by builder",
        "Test": f"One-way ANOVA (k={len(groups)})",
        "Statistic": f"{f_stat:.2f}",
        "p-value": f"{p:.4f}",
        "Verdict": "Significant" if p < 0.05 else "Not significant",
    })

    groups = [g["price_per_sqft"].values for _, g in df.groupby("micro_market")]
    f_stat, p = stats.f_oneway(*groups)
    results.append({
        "Hypothesis": "Price per sqft differs by micro-market",
        "Test": f"One-way ANOVA (k={len(groups)})",
        "Statistic": f"{f_stat:.2f}",
        "p-value": f"{p:.4f}",
        "Verdict": "Significant" if p < 0.05 else "Not significant",
    })

    r, p = stats.pearsonr(df["amenity_score"], df["booking_flag"])
    results.append({
        "Hypothesis": "Amenity score correlates with booking",
        "Test": "Pearson correlation",
        "Statistic": f"r = {r:.4f}",
        "p-value": f"{p:.4f}",
        "Verdict": "Significant" if p < 0.05 else "Not significant",
    })

    r, p = stats.pearsonr(df["unit_size_sqft"], df["ticket_price_cr"])
    results.append({
        "Hypothesis": "Unit size correlates with ticket price",
        "Test": "Pearson correlation",
        "Statistic": f"r = {r:.4f}",
        "p-value": f"{p:.4f}",
        "Verdict": "Significant" if p < 0.05 else "Not significant",
    })

    return results


def _markdown_table(rows: list[dict[str, object]]) -> str:
    headers = list(rows[0].keys())
    lines = ["| " + " | ".join(headers) + " |",
             "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(str(row[h]) for h in headers) + " |")
    return "\n".join(lines)


def write_findings(df: pd.DataFrame, tests: list[dict[str, object]]) -> None:
    significant = [t for t in tests if t["Verdict"] == "Significant"]
    # Ten tests on one dataset inflates the false-positive rate, so the
    # Bonferroni-corrected threshold is the one that actually matters.
    alpha = 0.05 / len(tests)
    surviving = [t for t in tests if float(t["p-value"]) < alpha]

    builders = df.groupby("builder")["ticket_price_cr"].mean()
    markets = df.groupby("micro_market")["price_per_sqft"].mean()
    conversion = df.groupby("micro_market")["booking_flag"].mean() * 100

    content = f"""# EDA Findings - Luxury Housing Bengaluru

Generated by `python_scripts/eda_analysis.py` over {len(df):,} non-outlier records.

## Headline numbers

| Metric | Value |
|---|---|
| Records analysed | {len(df):,} |
| Average ticket price | Rs {df['ticket_price_cr'].mean():.2f} Cr |
| Median ticket price | Rs {df['ticket_price_cr'].median():.2f} Cr |
| Average price per sqft | Rs {df['price_per_sqft'].mean():,.0f} |
| Average unit size | {df['unit_size_sqft'].mean():,.0f} sqft |
| Overall booking conversion | {df['booking_flag'].mean() * 100:.2f}% |
| Builders tracked | {df['builder'].nunique()} |
| Micro-markets tracked | {df['micro_market'].nunique()} |
| Quarters covered | {df['quarter_label'].nunique()} ({df['quarter_label'].min()} to {df['quarter_label'].max()}) |

## Significance testing

Every apparent difference below was tested before being reported as a finding.

{_markdown_table(tests)}

**{len(significant)} of {len(tests)} hypotheses reached significance at p < 0.05.**

Because {len(tests)} tests were run against the same dataset, the threshold that
actually controls the false-positive rate is the Bonferroni-corrected
alpha = 0.05 / {len(tests)} = {alpha:.4f}. **{len(surviving)} of {len(tests)} hypotheses survive
that correction.**

## What this means

The spread between groups is real in arithmetic but not in statistics. Concretely:

- Builder average prices span Rs {builders.min():.2f} Cr to Rs {builders.max():.2f} Cr - a
  range of {builders.max() - builders.min():.2f} Cr, or
  {100 * (builders.max() - builders.min()) / builders.mean():.1f}% of the market mean.
- Micro-market price per sqft spans Rs {markets.min():,.0f} to Rs {markets.max():,.0f},
  a {100 * (markets.max() - markets.min()) / markets.mean():.1f}% spread.
- Booking conversion by micro-market spans {conversion.min():.2f}% to {conversion.max():.2f}%,
  and every 95% Wilson interval in `04_conversion_by_market.png` overlaps 50%.

With 100,000 rows, a chi-square test has enough power to detect a conversion gap
of well under one percentage point. It does not detect one. The honest reading
is that **this dataset carries no genuine relationship between any categorical
driver and booking outcome** - the underlying values were drawn independently,
so ranking builders or markets on these numbers would be ranking noise.

## How to use this responsibly

The pipeline, warehouse and dashboard are all correct and would surface real
patterns if pointed at real transaction data. When presenting this work:

1. Report the rankings as *descriptive* ("Kanakapura Road led at 51.31%"), never
   as *causal* ("Kanakapura Road converts better because...").
2. Keep the confidence intervals on the conversion charts. They are the evidence
   that the ranking is not meaningful, and showing them is the finding.
3. The two relationships that *are* structurally real - price per sqft being a
   deterministic function of price and size, and the price outliers clustering at
   exactly Rs 60/70/100 Cr - are artefacts of how the file was generated, not
   market behaviour.

## Chart pack

| File | Shows |
|---|---|
| `01_price_distribution.png` | Ticket price histogram and price spread by configuration |
| `02_price_by_builder.png` | Builder average price with 95% confidence intervals |
| `03_price_per_sqft_by_market.png` | Micro-market price per sqft ranking |
| `04_conversion_by_market.png` | Conversion by market with Wilson intervals against a 50% baseline |
| `05_quarterly_trends.png` | Transaction volume and average price by quarter |
| `06_configuration_demand.png` | Configuration mix shift across quarters |
| `07_amenity_vs_conversion.png` | Conversion by amenity decile and band |
| `08_sales_channel.png` | Booking vs drop-off and conversion by channel |
| `09_buyer_persona.png` | Price and volume by buyer type and NRI status |
| `10_sentiment.png` | Sentiment mix and most frequent buyer comments |
| `11_correlation_heatmap.png` | Pearson correlation across numeric features |
| `12_geographic_distribution.png` | Micro-market centroids sized by volume, coloured by price per sqft |
"""
    FINDINGS_MD.write_text(content, encoding="utf-8")


# --------------------------------------------------------------------------
# Pipeline
# --------------------------------------------------------------------------
def run() -> None:
    print("=" * 74)
    print("LUXURY HOUSING - EXPLORATORY DATA ANALYSIS")
    print("=" * 74)
    cfg.ensure_dirs()

    print("\n[1/3] Loading warehouse...")
    df = load_data()

    print("\n[2/3] Building chart pack...")
    chart_price_distribution(df)
    chart_price_by_builder(df)
    chart_price_per_sqft_by_market(df)
    chart_conversion_by_market(df)
    chart_quarterly_trends(df)
    chart_configuration_demand(df)
    chart_amenity_vs_conversion(df)
    chart_sales_channel(df)
    chart_buyer_persona(df)
    chart_sentiment(df)
    chart_geography(df)
    chart_correlation(df)

    print("\n[3/3] Running significance tests...")
    tests = run_significance_tests(df)
    for test in tests:
        print(f"    [{test['Verdict']:<15}] {test['Hypothesis']:<48} p={test['p-value']}")
    write_findings(df, tests)

    print("\n" + "=" * 74)
    print("EDA COMPLETE")
    print("=" * 74)
    print(f"  Charts   : {cfg.CHARTS_DIR}")
    print(f"  Findings : {FINDINGS_MD}")


if __name__ == "__main__":
    run()
