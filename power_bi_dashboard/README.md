# power_bi_dashboard — status

## What's here

`LuxuryHousing.pbip` and its two folders are a generated Power BI Project,
produced by [`../python_scripts/generate_pbip.py`](../python_scripts/generate_pbip.py).

The semantic model in `LuxuryHousing.SemanticModel/model.bim` is complete and
valid:

| Content | Count |
|---|---:|
| Tables | 3 (`luxury_housing`, `DimDate`, `Measures`) |
| Typed fact columns | 33 |
| Date dimension columns | 8 |
| DAX measures | 25 |
| Relationships | 1 (`luxury_housing[Purchase_Date]` → `DimDate[Date]`) |

It also carries the details that are tedious to set by hand: format strings on
every measure, `Micro_Market` categorised as **Place** for map visuals,
`Quarter Label` sorted by `Quarter Sort`, `DimDate` marked as a date table, and
audit columns hidden.

## Known issue — it does not open yet

**Power BI Desktop 2.155.756.0 rejects this project.** Launching it (both as a
command-line argument and via the registered `.pbip` shell association) opens a
blank "Untitled" document instead of the project, with no error dialog and
nothing written to the trace log.

Two serializations were tried and both failed the same way:

1. TMDL model folder + PBIR report folder (the newer format)
2. TMSL `model.bim` + legacy `report.json` (the conservative format, current
   state of this folder)

The model JSON itself parses cleanly and contains everything listed above, so
the problem is in the project container or report wrapper, not the model
content. Without a reference PBIP written by Power BI itself, fixing it is
guesswork — there is no such file anywhere on this machine to compare against.

## How to unblock it

**Option 1 — try opening it from inside Power BI (10 seconds).**
Shell-launching failed, but the in-app open path is different code. In Power BI
Desktop: **File → Open report → Browse this device**, set the file-type filter
to include Power BI project files, and select `LuxuryHousing.pbip`. If it
opens, everything above is immediately available and nothing else is needed.

**Option 2 — give the generator a reference to copy (30 seconds).**
In Power BI Desktop: open a blank report, then **File → Save as → Power BI
project (.pbip)** and save it anywhere. That produces a project folder written
by Power BI itself. With that as a template, the generator can be corrected to
emit a structure that is known to open.

**Option 3 — build the model by hand.**
[`../documentation/powerbi_build_guide.md`](../documentation/powerbi_build_guide.md)
contains every measure as a copy-paste DAX block, plus the `DimDate` table
definition, column settings and page-by-page visual specifications. This path
does not depend on the PBIP working at all — it is the reliable route and takes
roughly an hour.

## Data source

The model reads the cleaned CSV through a Power Query parameter called
`CleanedDataPath`, currently pointing at:

```
E:\Guvi project\Luxury-Housing-Sales-Analysis\data\processed\luxury_housing_clean.csv
```

To point Power BI at the SQL warehouse instead — which is what the project brief
asks for — see the three connection options in the build guide. PostgreSQL is
the recommended one, since Power BI has no native SQLite connector.
