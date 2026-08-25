# Data

No datasets are committed to this repository. The raw extracts run to hundreds of megabytes and the generated intermediates are reproducible from them.

## What you need to place here

| File | Source | Notes |
|---|---|---|
| `DVF_departement_75.csv` | [data.gouv.fr, Demandes de valeurs foncières](https://www.data.gouv.fr/fr/datasets/demandes-de-valeurs-foncieres-geolocalisees/) | Use the geolocated version. Latitude and longitude are required for the spatial join in Step 5. Filter to département 75 (Paris). |
| `DPE_avant_2021_departement_75.csv` | [ADEME open data](https://data.ademe.fr/) | Energy performance diagnostics. Filter to département 75. |

Filenames are configurable in `src/config.py` if yours differ.

## What gets generated here

Running the pipeline creates the following in this folder:

| File | Created by | Contents |
|---|---|---|
| `paris_kml_data/` | Step 1 | 112 DRIHL rent-control KML files |
| `Paris_Rent_Zones_GDF.geojson` | Step 2 | 8,960 rent-control zone records with polygons and legal rent thresholds |
| `dvf_clean.csv` | Step 3 | Filtered Paris apartment sales with a standardised address key |
| `dpe_clean.csv` | Step 3 | Deduplicated energy ratings with the same address key |
| `paris_transactions_merged.csv` | Step 4 | Sales joined to energy ratings |
| `Paris_ROI_Calculated.csv` | Step 5 | Per-transaction cash-on-cash ROI |
| `investment_map.html` | Step 6 | Standalone interactive map, openable in any browser |

Steps 1 and 2 need only an internet connection, so `Paris_Rent_Zones_GDF.geojson` can be regenerated without obtaining DVF or DPE at all.

Everything in this folder except this README is gitignored.
