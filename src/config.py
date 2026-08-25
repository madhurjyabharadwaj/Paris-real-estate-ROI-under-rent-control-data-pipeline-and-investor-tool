"""
Central configuration for the Paris ROI pipeline.

Every path and every modelling assumption lives here so that the rest of the
pipeline stays free of magic numbers.
"""

import os

# ---------------------------------------------------------------------------
# Directories
# ---------------------------------------------------------------------------

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
KML_DIR = os.path.join(DATA_DIR, "paris_kml_data")

# ---------------------------------------------------------------------------
# Source data
# ---------------------------------------------------------------------------

# DRIHL publishes one KML per (validity period, room count, construction era).
BASE_URL = (
    "http://www.referenceloyer.drihl.ile-de-france.developpement-durable."
    "gouv.fr/paris/kml/"
)

# Raw inputs that have to be downloaded manually (see data/README.md).
DVF_FILE = os.path.join(DATA_DIR, "DVF_departement_75.csv")
DPE_FILE = os.path.join(DATA_DIR, "DPE_avant_2021_departement_75.csv")

# ---------------------------------------------------------------------------
# Generated artefacts
# ---------------------------------------------------------------------------

RENT_ZONES_GEOJSON = os.path.join(DATA_DIR, "Paris_Rent_Zones_GDF.geojson")
DVF_CLEAN_FILE = os.path.join(DATA_DIR, "dvf_clean.csv")
DPE_CLEAN_FILE = os.path.join(DATA_DIR, "dpe_clean.csv")
MERGED_TRANSACTIONS_FILE = os.path.join(DATA_DIR, "paris_transactions_merged.csv")
ROI_FILE = os.path.join(DATA_DIR, "Paris_ROI_Calculated.csv")
MAP_HTML_FILE = os.path.join(DATA_DIR, "investment_map.html")

# ---------------------------------------------------------------------------
# KML download grid (7 periods x 4 room counts x 4 construction eras = 112)
# ---------------------------------------------------------------------------

PERIODS = [
    "2019-07-01",
    "2020-07-01",
    "2021-07-01",
    "2022-07-01",
    "2023-07-01",
    "2024-07-01",
    "2025-07-01",
]

ROOMS = ["1", "2", "3", "4"]

CONSTRUCTION_ERAS = ["inf1946", "1946-1970", "1971-1990", "sup1990"]

RENTAL_TYPE = "non-meuble"  # unfurnished lets only

# ---------------------------------------------------------------------------
# Financial assumptions used by the cash-on-cash ROI model
# ---------------------------------------------------------------------------

ASSUMED_MORTGAGE_RATE = 0.04  # 4.0% annual interest on the loan
ASSUMED_DOWN_PAYMENT_PERCENT = 0.20  # 20% cash invested
ASSUMED_PROPERTY_TAX_RATE = 0.005  # 0.5% of property value per year
RENTAL_EXPENSE_RATIO = 0.15  # 15% of gross rent for vacancy, management, upkeep

# ---------------------------------------------------------------------------
# ROI colour bands used by the investor map
# ---------------------------------------------------------------------------

GOOD_ROI_THRESHOLD = 8.0  # green marker at or above this ROI (%)
BAD_ROI_THRESHOLD = 3.0  # red marker at or below this ROI (%)


def ensure_directories():
    """Create the data folders if they are not already present."""
    for path in (DATA_DIR, KML_DIR):
        os.makedirs(path, exist_ok=True)
    return DATA_DIR
