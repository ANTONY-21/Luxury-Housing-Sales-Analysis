"""
generate_pbip.py
================
Generates a Power BI Project (PBIP) containing the full semantic model for the
Luxury Housing warehouse: typed tables, a marked date dimension, the
relationship, data categories, and the complete DAX measure library from
`documentation/powerbi_build_guide.md`.

Opening the generated `.pbip` in Power BI Desktop gives you a working model with
every measure already defined and formatted, so the only manual work left is
dragging visuals onto the canvas per the build guide.

Serialization
-------------
The model is written as TMSL (`model.bim`) and the report as a legacy
`report.json` layout. Both are the older, most broadly accepted PBIP
serializations - the newer TMDL folder and PBIR folder formats are version
sensitive, and this project has to open on whatever Desktop build is installed.

Run:
    python python_scripts/generate_pbip.py
"""

from __future__ import annotations

import json
import shutil
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config as cfg  # noqa: E402

PBIP_DIR = cfg.ROOT / "power_bi_dashboard"
PROJECT = "LuxuryHousing"
MODEL_DIR = PBIP_DIR / f"{PROJECT}.SemanticModel"
REPORT_DIR = PBIP_DIR / f"{PROJECT}.Report"

FACT = "luxury_housing"


def guid() -> str:
    return str(uuid.uuid4())


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8", newline="\n")


def annotations(**pairs) -> list[dict]:
    return [{"name": k, "value": v} for k, v in pairs.items()]


# --------------------------------------------------------------------------
# Fact table columns
# --------------------------------------------------------------------------
# (name, TMSL dataType, formatString, dataCategory, hidden)
COLUMNS: list[tuple[str, str, str | None, str | None, bool]] = [
    ("Property_ID",          "string",   None,         None,    False),
    ("Project_Name",         "string",   None,         None,    False),
    ("Developer_Name",       "string",   None,         None,    False),
    ("Micro_Market",         "string",   None,         None,    False),
    ("Latitude",             "double",   "0.000000",   "Latitude",  False),
    ("Longitude",            "double",   "0.000000",   "Longitude", False),
    ("Map_Location",         "string",   None,         "Place", False),
    ("Configuration",        "string",   None,         None,    False),
    ("Unit_Size_Sqft",       "double",   "#,0",        None,    False),
    ("Size_Category",        "string",   None,         None,    False),
    ("Ticket_Price_Cr",      "double",   "#,0.00",     None,    False),
    ("Price_per_Sqft",       "double",   "#,0",        None,    False),
    ("Price_Segment",        "string",   None,         None,    False),
    ("Is_Price_Outlier",     "int64",    "0",          None,    False),
    ("Transaction_Type",     "string",   None,         None,    False),
    ("Booking_Flag",         "int64",    "0",          None,    False),
    ("Booking_Status",       "string",   None,         None,    False),
    ("Possession_Status",    "string",   None,         None,    False),
    ("Sales_Channel",        "string",   None,         None,    False),
    ("Buyer_Type",           "string",   None,         None,    False),
    ("NRI_Buyer",            "string",   None,         None,    False),
    ("Buyer_Comments",       "string",   None,         None,    False),
    ("Comment_Sentiment",    "string",   None,         None,    False),
    ("Amenity_Score",        "double",   "#,0.00",     None,    False),
    ("Amenity_Band",         "string",   None,         None,    False),
    ("Connectivity_Score",   "double",   "#,0.00",     None,    False),
    ("Locality_Infra_Score", "double",   "#,0.00",     None,    False),
    ("Avg_Traffic_Time_Min", "int64",    "#,0",        None,    False),
    ("Purchase_Date",        "dateTime", "Short Date", None,    False),
    ("Purchase_Year",        "int64",    "0",          None,    False),
    ("Quarter_Number",       "int64",    "0",          None,    False),
    ("Quarter_Label",        "string",   None,         None,    False),
    ("Fiscal_Year",          "string",   None,         None,    False),
    ("Price_Imputed",        "int64",    "0",          None,    True),
    ("Size_Imputed",         "int64",    "0",          None,    True),
    ("Amenity_Imputed",      "int64",    "0",          None,    True),
]

M_TYPES = {
    "string": "type text",
    "double": "type number",
    "int64": "Int64.Type",
    "dateTime": "type date",
}


# --------------------------------------------------------------------------
# Measures  (name, DAX, formatString, description)
# --------------------------------------------------------------------------
MEASURES: list[tuple[str, str, str | None, str]] = [
    ("Total Properties", f"COUNTROWS ( {FACT} )", "#,0",
     "Row count of the fact table under the current filter context."),
    ("Total Bookings", f"SUM ( {FACT}[Booking_Flag] )", "#,0",
     "Count of Primary transactions, treated as bookings."),
    ("Drop Offs", "[Total Properties] - [Total Bookings]", "#,0",
     "Transactions that did not convert to a booking."),
    ("Booking Conversion %", "DIVIDE ( [Total Bookings], [Total Properties], 0 )",
     "0.00%", "Share of transactions that are bookings."),
    ("Drop Off Rate %", "1 - [Booking Conversion %]", "0.00%",
     "Complement of booking conversion."),

    ("Avg Ticket Price Cr", f"AVERAGE ( {FACT}[Ticket_Price_Cr] )", '#,0.00 "Cr"',
     "Mean ticket price in crore rupees."),
    ("Median Ticket Price Cr", f"MEDIAN ( {FACT}[Ticket_Price_Cr] )", '#,0.00 "Cr"',
     "Median ticket price in crore rupees."),
    ("Avg Price per Sqft", f"AVERAGE ( {FACT}[Price_per_Sqft] )", "#,0",
     "Mean price per square foot in rupees."),
    ("Total Pipeline Value Cr", f"SUM ( {FACT}[Ticket_Price_Cr] )", '#,0 "Cr"',
     "Sum of ticket prices in crore rupees."),
    ("Avg Unit Size Sqft", f"AVERAGE ( {FACT}[Unit_Size_Sqft] )", "#,0",
     "Mean unit size in square feet."),

    ("Avg Amenity Score", f"AVERAGE ( {FACT}[Amenity_Score] )", "#,0.00",
     "Mean amenity score out of 10."),
    ("Positive Sentiment %",
     f'DIVIDE ( CALCULATE ( [Total Properties], {FACT}[Comment_Sentiment] = "Positive" ), '
     f'CALCULATE ( [Total Properties], {FACT}[Comment_Sentiment] <> "No Comment" ), 0 )',
     "0.00%", "Positive share of buyers who left a comment."),
    ("Negative Sentiment %",
     f'DIVIDE ( CALCULATE ( [Total Properties], {FACT}[Comment_Sentiment] = "Negative" ), '
     f'CALCULATE ( [Total Properties], {FACT}[Comment_Sentiment] <> "No Comment" ), 0 )',
     "0.00%", "Negative share of buyers who left a comment."),

    ("Market Avg Price per Sqft",
     f"CALCULATE ( AVERAGE ( {FACT}[Price_per_Sqft] ), "
     f"ALLEXCEPT ( {FACT}, {FACT}[Micro_Market] ) )",
     "#,0", "Price per sqft for the whole micro-market, ignoring builder filters."),
    ("Price Premium vs Market %",
     "DIVIDE ( [Avg Price per Sqft] - [Market Avg Price per Sqft], "
     "[Market Avg Price per Sqft], 0 )",
     "+0.00%;-0.00%;0.00%",
     "How far above or below the local market a builder prices."),
    ("Builder Rank by Price",
     f"RANKX ( ALLSELECTED ( {FACT}[Developer_Name] ), [Avg Ticket Price Cr],, DESC )",
     "0", "Rank of the builder by average ticket price."),

    # --- Measures backing the brief's ten visualization questions -----------
    ("Booking Status Share %",
     f"DIVIDE ( [Total Properties], CALCULATE ( [Total Properties], "
     f"ALL ( {FACT}[Booking_Status] ) ) )",
     "0.00%",
     "Share of a segment's rows in each booking status. Drives the 100% "
     "stacked columns for questions 4 and 6."),
    ("Builder Revenue Rank",
     f"RANKX ( ALLSELECTED ( {FACT}[Developer_Name] ), "
     "[Total Pipeline Value Cr],, DESC )",
     "0", "Rank of the builder by total revenue. Question 10."),
    ("Is Top 5 Builder", "IF ( [Builder Revenue Rank] <= 5, 1, 0 )", "0",
     "Flag for the top five builders by revenue. Use as a visual filter."),
    ("Top 5 Builders Revenue Cr",
     f"SUMX ( TOPN ( 5, ALLSELECTED ( {FACT}[Developer_Name] ), "
     "[Total Pipeline Value Cr], DESC ), [Total Pipeline Value Cr] )",
     '#,0 "Cr"', "Combined revenue of the top five builders. Question 10 KPI card."),
    ("Top 5 Builders Bookings",
     f"SUMX ( TOPN ( 5, ALLSELECTED ( {FACT}[Developer_Name] ), "
     "[Total Pipeline Value Cr], DESC ), [Total Bookings] )",
     "#,0", "Combined bookings of the top five builders by revenue. Question 10 KPI card."),

    ("Previous Quarter Bookings",
     "CALCULATE ( [Total Bookings], PREVIOUSQUARTER ( DimDate[Date] ) )", "#,0",
     "Bookings in the preceding quarter."),
    ("QoQ Booking Growth %",
     "VAR Previous = [Previous Quarter Bookings] "
     "RETURN DIVIDE ( [Total Bookings] - Previous, Previous )",
     "+0.00%;-0.00%;0.00%", "Quarter-over-quarter change in bookings."),
    ("Previous Quarter Avg Price",
     "CALCULATE ( [Avg Ticket Price Cr], PREVIOUSQUARTER ( DimDate[Date] ) )",
     '#,0.00 "Cr"', "Average ticket price in the preceding quarter."),
    ("QoQ Price Change %",
     "VAR Previous = [Previous Quarter Avg Price] "
     "RETURN DIVIDE ( [Avg Ticket Price Cr] - Previous, Previous )",
     "+0.00%;-0.00%;0.00%", "Quarter-over-quarter change in average price."),
    ("Rolling 4Q Avg Price",
     "AVERAGEX ( DATESINPERIOD ( DimDate[Date], MAX ( DimDate[Date] ), -12, MONTH ), "
     "[Avg Ticket Price Cr] )",
     '#,0.00 "Cr"', "Trailing four-quarter average ticket price."),

    ("Conversion CI Half Width",
     "VAR N = [Total Properties] VAR P = [Booking Conversion %] "
     "RETURN IF ( N > 0, 1.96 * SQRT ( DIVIDE ( P * ( 1 - P ), N ) ) )",
     "0.00%", "Half width of the 95% confidence interval on conversion."),
    ("Conversion Lower Bound",
     "[Booking Conversion %] - [Conversion CI Half Width]", "0.00%",
     "Lower bound of the 95% confidence interval on conversion."),
    ("Conversion Upper Bound",
     "[Booking Conversion %] + [Conversion CI Half Width]", "0.00%",
     "Upper bound of the 95% confidence interval on conversion."),
    ("Conversion Signal",
     'IF ( [Conversion Lower Bound] > 0.5 || [Conversion Upper Bound] < 0.5, '
     '"Distinguishable from baseline", "Within noise" )',
     None,
     "Whether conversion differs measurably from the 50% baseline. Reads "
     "'Within noise' everywhere on this dataset - that is the finding."),
]


# --------------------------------------------------------------------------
# Semantic model (TMSL)
# --------------------------------------------------------------------------
def fact_table() -> dict:
    transforms = ", ".join(
        f'{{"{name}", {M_TYPES[dtype]}}}' for name, dtype, *_ in COLUMNS
    )
    expression = [
        "let",
        '    Source = Csv.Document(File.Contents(CleanedDataPath), '
        f'[Delimiter=",", Columns={len(COLUMNS)}, Encoding=65001, '
        "QuoteStyle=QuoteStyle.Csv]),",
        "    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),",
        f"    Typed = Table.TransformColumnTypes(Promoted, {{{transforms}}})",
        "in",
        "    Typed",
    ]

    columns = []
    for name, dtype, fmt, category, hidden in COLUMNS:
        column: dict = {
            "name": name,
            "dataType": dtype,
            "sourceColumn": name,
            "summarizeBy": "none",
            "annotations": annotations(SummarizationSetBy="Automatic"),
        }
        if fmt:
            column["formatString"] = fmt
        if category:
            column["dataCategory"] = category
        if hidden:
            column["isHidden"] = True
        columns.append(column)

    return {
        "name": FACT,
        "columns": columns,
        "partitions": [{
            "name": FACT,
            "mode": "import",
            "source": {"type": "m", "expression": expression},
        }],
        "annotations": annotations(PBI_ResultType="Table"),
    }


DIMDATE_DAX = (
    "VAR MinDate = MIN ( luxury_housing[Purchase_Date] ) "
    "VAR MaxDate = MAX ( luxury_housing[Purchase_Date] ) "
    "RETURN ADDCOLUMNS ( CALENDAR ( MinDate, MaxDate ), "
    '"Year", YEAR ( [Date] ), '
    '"Quarter Number", QUARTER ( [Date] ), '
    '"Quarter Label", FORMAT ( [Date], "YYYY" ) & "-Q" & QUARTER ( [Date] ), '
    '"Quarter Sort", YEAR ( [Date] ) * 10 + QUARTER ( [Date] ), '
    '"Fiscal Year", "FY" & YEAR ( EDATE ( [Date], -3 ) ) & "-" '
    '& RIGHT ( YEAR ( EDATE ( [Date], -3 ) ) + 1, 2 ), '
    '"Month Name", FORMAT ( [Date], "MMM YYYY" ), '
    '"Month Number", MONTH ( [Date] ) )'
)

# (name, dataType, formatString, hidden, sortBy)
DIMDATE_COLUMNS: list[tuple[str, str, str | None, bool, str | None]] = [
    ("Date",           "dateTime", "Short Date", False, None),
    ("Year",           "int64",    "0",          False, None),
    ("Quarter Number", "int64",    "0",          False, None),
    ("Quarter Label",  "string",   None,         False, "Quarter Sort"),
    ("Quarter Sort",   "int64",    "0",          True,  None),
    ("Fiscal Year",    "string",   None,         False, None),
    ("Month Name",     "string",   None,         False, "Month Number"),
    ("Month Number",   "int64",    "0",          True,  None),
]


def dimdate_table() -> dict:
    columns = []
    for name, dtype, fmt, hidden, sort_by in DIMDATE_COLUMNS:
        column: dict = {
            "type": "calculatedTableColumn",
            "name": name,
            "dataType": dtype,
            "sourceColumn": f"[{name}]",
            "summarizeBy": "none",
            "annotations": annotations(SummarizationSetBy="Automatic"),
        }
        if fmt:
            column["formatString"] = fmt
        if hidden:
            column["isHidden"] = True
        if sort_by:
            column["sortByColumn"] = sort_by
        if name == "Date":
            column["isKey"] = True
        columns.append(column)

    return {
        "name": "DimDate",
        "dataCategory": "Time",
        "columns": columns,
        "partitions": [{
            "name": "DimDate",
            "mode": "import",
            "source": {"type": "calculated", "expression": DIMDATE_DAX},
        }],
    }


def measures_table() -> dict:
    measures = []
    for name, expression, fmt, description in MEASURES:
        measure: dict = {"name": name, "expression": expression,
                         "description": description}
        if fmt:
            measure["formatString"] = fmt
        measures.append(measure)

    return {
        "name": "Measures",
        "columns": [{
            "type": "calculatedTableColumn",
            "name": "Placeholder",
            "dataType": "int64",
            "isHidden": True,
            "sourceColumn": "[Placeholder]",
            "summarizeBy": "none",
            "annotations": annotations(SummarizationSetBy="Automatic"),
        }],
        "measures": measures,
        "partitions": [{
            "name": "Measures",
            "mode": "import",
            "source": {"type": "calculated",
                       "expression": 'ROW("Placeholder", 1)'},
        }],
    }


def build_model() -> None:
    if MODEL_DIR.exists():
        shutil.rmtree(MODEL_DIR)

    path_literal = str(cfg.CLEANED_CSV)
    model = {
        "name": PROJECT,
        "compatibilityLevel": 1550,
        "model": {
            "culture": "en-US",
            "defaultPowerBIDataSourceVersion": "powerBI_V3",
            "discourageImplicitMeasures": True,
            "sourceQueryCulture": "en-US",
            "dataAccessOptions": {
                "legacyRedirects": True,
                "returnErrorValuesAsNull": True,
            },
            "expressions": [{
                "name": "CleanedDataPath",
                "kind": "m",
                "expression": (
                    f'"{path_literal}" meta [IsParameterQuery=true, '
                    'Type="Text", IsParameterQueryRequired=true]'
                ),
            }],
            "tables": [fact_table(), dimdate_table(), measures_table()],
            "relationships": [{
                "name": guid(),
                "fromTable": FACT,
                "fromColumn": "Purchase_Date",
                "toTable": "DimDate",
                "toColumn": "Date",
            }],
            "annotations": annotations(
                PBI_QueryOrder=json.dumps(["CleanedDataPath", FACT]),
                __PBI_TimeIntelligenceEnabled="0",
            ),
        },
    }

    write_json(MODEL_DIR / "model.bim", model)
    write_json(MODEL_DIR / "definition.pbism", {"version": "1.0", "settings": {}})


# --------------------------------------------------------------------------
# Report (legacy layout)
# --------------------------------------------------------------------------
PAGES = [
    ("MarketIntelligence", "Market Intelligence"),
    ("SalesConversion",    "Sales & Conversion"),
    ("BuyerPersonas",      "Buyer Personas"),
    ("Pricing",            "Pricing"),
    ("DataQuality",        "Data & Quality"),
]


def build_report() -> None:
    if REPORT_DIR.exists():
        shutil.rmtree(REPORT_DIR)

    sections = []
    for ordinal, (name, title) in enumerate(PAGES):
        sections.append({
            "name": name,
            "displayName": title,
            "displayOption": 1,
            "height": 720.0,
            "width": 1280.0,
            "ordinal": ordinal,
            "config": "{}",
            "filters": "[]",
            "visualContainers": [],
        })

    layout = {
        "config": json.dumps({
            "version": "5.43",
            "activeSectionIndex": 0,
            "defaultDrillFilterOtherVisuals": True,
        }),
        "layoutOptimization": 0,
        "resourcePackages": [],
        "sections": sections,
        "filters": "[]",
        "pods": [],
        "publicCustomVisuals": [],
    }

    write_json(REPORT_DIR / "report.json", layout)
    write_json(REPORT_DIR / "definition.pbir", {
        "version": "1.0",
        "datasetReference": {"byPath": {"path": f"../{PROJECT}.SemanticModel"}},
    })


def build_pbip() -> None:
    write_json(PBIP_DIR / f"{PROJECT}.pbip", {
        "version": "1.0",
        "artifacts": [{"report": {"path": f"{PROJECT}.Report"}}],
        "settings": {"enableAutoRecovery": True},
    })


def run() -> None:
    print("=" * 74)
    print("GENERATING POWER BI PROJECT (PBIP)")
    print("=" * 74)

    if not cfg.CLEANED_CSV.exists():
        raise SystemExit(
            f"Cleaned dataset not found at {cfg.CLEANED_CSV}.\n"
            "Run 'python python_scripts/data_cleaning.py' first."
        )

    build_model()
    build_report()
    build_pbip()

    print(f"\n  Project     : {PBIP_DIR / (PROJECT + '.pbip')}")
    print(f"  Model       : {len(COLUMNS)} typed columns, "
          f"{len(DIMDATE_COLUMNS)} date columns, {len(MEASURES)} measures")
    print(f"  Data source : {cfg.CLEANED_CSV}")
    print(f"  Pages       : {len(PAGES)} blank canvases")
    print("=" * 74)


if __name__ == "__main__":
    run()
