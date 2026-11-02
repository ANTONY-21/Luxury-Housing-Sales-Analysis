"""
config.py
=========
Single source of truth for file paths and database connection settings used by
every script in this project.

The warehouse backend is switchable. SQLite is the default because it needs no
server install and keeps the whole project self-contained; switch DB_BACKEND to
'postgresql' or 'mysql' (and fill in DB_CONFIG) to point the same loader at a
real server. Power BI can connect to any of the three.

Importing this module also switches stdout and stderr to UTF-8, since every
script in the pipeline imports it and several print non-ASCII characters.
"""

import os
import sys
from pathlib import Path


# --------------------------------------------------------------------------
# Console encoding
#
# Progress messages carry the rupee sign, which a Windows console or a
# redirected pipe running the legacy cp1252 code page cannot encode - it raises
# UnicodeEncodeError mid-run and kills the script. Every other module imports
# this one, so switching the streams to UTF-8 here covers the whole pipeline.
# --------------------------------------------------------------------------
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")


def _env_path(name: str, default: Path) -> Path:
    """Allow any path to be overridden by an environment variable."""
    value = os.getenv(name)
    return Path(value).expanduser().resolve() if value else default


# --------------------------------------------------------------------------
# Paths
#
# Everything is resolved relative to the repository root, which is derived from
# this file's own location - so the scripts run from any working directory and
# survive being moved or cloned elsewhere. Each path can still be overridden by
# an environment variable for CI or a different data drive.
# --------------------------------------------------------------------------
ROOT = _env_path("LUXURY_HOUSING_ROOT", Path(__file__).resolve().parents[1])

RAW_CSV = _env_path("LUXURY_HOUSING_RAW_CSV", ROOT / "Luxury_Housing_Bangalore.csv")

DATA_DIR = ROOT / "data"
PROCESSED_DIR = DATA_DIR / "processed"
CLEANED_CSV = PROCESSED_DIR / "luxury_housing_clean.csv"
SQLITE_PATH = DATA_DIR / "luxury_housing.db"

SQL_DIR = ROOT / "sql_scripts"
SCHEMA_SQL = SQL_DIR / "create_schema.sql"
VIEWS_SQL = SQL_DIR / "analytics_views.sql"
VALIDATION_SQL = SQL_DIR / "validation_queries.sql"

OUTPUT_DIR = ROOT / "outputs"
CHARTS_DIR = OUTPUT_DIR / "charts"
QUALITY_REPORT = OUTPUT_DIR / "data_quality_report.md"

DOCS_DIR = ROOT / "documentation"

TABLE_NAME = "luxury_housing"


def ensure_dirs() -> None:
    """Create every output directory the pipeline writes to."""
    for directory in (PROCESSED_DIR, CHARTS_DIR, SQL_DIR, DOCS_DIR):
        directory.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------------
# Database
# --------------------------------------------------------------------------
# Credentials come from the environment so nothing secret is committed. Set
# them in your shell (or a .env loaded by your runner) before switching backend:
#
#   setx LUXURY_DB_BACKEND  postgresql
#   setx LUXURY_DB_PASSWORD <your password>
#
# One of: 'sqlite' | 'postgresql' | 'mysql'
DB_BACKEND = os.getenv("LUXURY_DB_BACKEND", "sqlite")

_DEFAULT_PORTS = {"postgresql": 5432, "mysql": 3306}

DB_CONFIG = {
    "host": os.getenv("LUXURY_DB_HOST", "localhost"),
    "port": int(os.getenv("LUXURY_DB_PORT", _DEFAULT_PORTS.get(DB_BACKEND, 5432))),
    "user": os.getenv("LUXURY_DB_USER", "postgres"),
    "password": os.getenv("LUXURY_DB_PASSWORD", ""),
    "database": os.getenv("LUXURY_DB_NAME", "luxury_housing"),
}


def sqlalchemy_url() -> str:
    """Build the SQLAlchemy URL for the configured backend."""
    if DB_BACKEND == "sqlite":
        return f"sqlite:///{SQLITE_PATH}"
    if DB_BACKEND == "postgresql":
        return (
            f"postgresql+psycopg2://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
            f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
        )
    if DB_BACKEND == "mysql":
        return (
            f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
            f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
        )
    raise ValueError(f"Unsupported DB_BACKEND: {DB_BACKEND!r}")


# --------------------------------------------------------------------------
# Domain reference data
# --------------------------------------------------------------------------
# Title-casing mangles these two acronyms, so they get fixed up explicitly.
MICRO_MARKET_FIXES = {
    "Jp Nagar": "JP Nagar",
    "Mg Road": "MG Road",
}

# The raw file stores possession status in three different casings.
POSSESSION_FIXES = {
    "Ready To Move": "Ready to Move",
    "Under Construction": "Under Construction",
    "Launch": "Launch",
}

# Buyer_Comments is a closed set of nine canned phrases plus nulls, so sentiment
# is a lookup rather than an NLP problem.
COMMENT_SENTIMENT = {
    "Great value for money.": "Positive",
    "Excellent location!": "Positive",
    "Loved the amenities!": "Positive",
    "Great view from 15th floor.": "Positive",
    "Underpriced for location.": "Positive",
    "Too far from my office.": "Negative",
    "Connectivity is poor.": "Negative",
    "Agent was not responsive.": "Negative",
    "Will buy after possession.": "Neutral",
}

NO_COMMENT = "No Comment"

# Approximate locality centroids for the 16 Bengaluru micro-markets, in WGS84.
#
# The raw dataset carries no coordinates, and Power BI's built-in geocoding is
# unreliable for Indian locality names (several of these resolve to the wrong
# country without a city qualifier). Shipping explicit coordinates makes the
# map visuals deterministic.
#
# These are centroids of the locality, not of any individual project - accurate
# enough to position a bubble on a city map, not a property boundary.
MICRO_MARKET_COORDS = {
    "Bannerghatta Road": (12.8845, 77.5977),
    "Bellary Road":      (13.0480, 77.5910),
    "Domlur":            (12.9609, 77.6387),
    "Electronic City":   (12.8452, 77.6602),
    "Hebbal":            (13.0358, 77.5912),
    "Hennur Road":       (13.0281, 77.6408),
    "Indiranagar":       (12.9784, 77.6408),
    "JP Nagar":          (12.9063, 77.5857),
    "Jayanagar":         (12.9250, 77.5938),
    "Kanakapura Road":   (12.8797, 77.5502),
    "Koramangala":       (12.9352, 77.6245),
    "MG Road":           (12.9750, 77.6060),
    "Rajajinagar":       (12.9915, 77.5550),
    "Sarjapur Road":     (12.9121, 77.6446),
    "Whitefield":        (12.9698, 77.7500),
    "Yelahanka":         (13.1007, 77.5963),
}

# Used as the Power BI map "Place" field so geocoding has a city qualifier.
CITY_QUALIFIER = "Bengaluru, Karnataka, India"
