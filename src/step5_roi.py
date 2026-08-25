"""
Step 5: Spatial association and ROI calculation.

Each transaction is placed inside its DRIHL rent-control zone with a spatial
join on latitude and longitude, the legal rent ceiling is applied according to
the property's energy class, and a cash-on-cash return is computed.

ROI model
---------
    Estimated_Monthly_Gross_Rent = capped_rent_per_m2 * surface
    Annual_Gross_Rent            = monthly gross rent * 12

    annual_taxes    = property_value * ASSUMED_PROPERTY_TAX_RATE
    annual_expenses = Annual_Gross_Rent * RENTAL_EXPENSE_RATIO
    loan_amount     = property_value * (1 - ASSUMED_DOWN_PAYMENT_PERCENT)
    annual_interest = loan_amount * ASSUMED_MORTGAGE_RATE

    Annual_Net_Cash_Flow = Annual_Gross_Rent
                           - annual_taxes - annual_expenses - annual_interest

    cash_invested    = property_value * ASSUMED_DOWN_PAYMENT_PERCENT
    Cash_on_Cash_ROI = Annual_Net_Cash_Flow / cash_invested * 100

Interest is treated as a flat rate on the full loan, with no amortisation. That
keeps the figure a clean cash-on-cash estimate rather than a full IRR.

Output: Paris_ROI_Calculated.csv
"""

import os

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

from config import (
    ASSUMED_DOWN_PAYMENT_PERCENT,
    ASSUMED_MORTGAGE_RATE,
    ASSUMED_PROPERTY_TAX_RATE,
    MERGED_TRANSACTIONS_FILE,
    RENTAL_EXPENSE_RATIO,
    RENT_ZONES_GEOJSON,
    ROI_FILE,
)

SAMPLE_THRESHOLD = 100_000  # cap on transactions to keep the spatial join tractable


def calculate_roi(
    merged_transactions_file=MERGED_TRANSACTIONS_FILE,
    rent_zones_file=RENT_ZONES_GEOJSON,
    output_file=ROI_FILE,
    sample_threshold=SAMPLE_THRESHOLD,
):
    """Attach each transaction to its rent zone and compute cash-on-cash ROI."""
    print("Starting Step 5: spatial association and ROI calculation...")

    # --- 1. Load -----------------------------------------------------------
    df_transactions = pd.read_csv(merged_transactions_file)

    # Only rows that matched a DPE record carry a usable construction year.
    df_transactions = df_transactions[df_transactions["annee_construction"] > 0].copy()

    if len(df_transactions) > sample_threshold:
        df_transactions = df_transactions.sample(
            n=sample_threshold, random_state=42
        ).copy()

    print(f"Loaded {len(df_transactions)} transactions after filtering and sampling.")

    gdf_rent_zones = gpd.read_file(rent_zones_file)

    # --- 2. Spatial join ---------------------------------------------------
    geometry = [
        Point(xy)
        for xy in zip(df_transactions["longitude"], df_transactions["latitude"])
    ]
    gdf_transactions = gpd.GeoDataFrame(
        df_transactions, geometry=geometry, crs=gdf_rent_zones.crs
    )

    print("Performing spatial join...")
    gdf_joined = gpd.sjoin(
        gdf_transactions,
        gdf_rent_zones[
            [
                "DRIHL_Zone_ID",
                "Loyer_Ref",
                "Loyer_Ref_Minore",
                "Loyer_Ref_Majore",
                "geometry",
            ]
        ],
        how="left",
        predicate="within",
    ).drop(columns=["index_right"])

    # --- 3. ROI ------------------------------------------------------------
    def select_max_rent(row):
        """Pick the rent ceiling unlocked by the property's energy class."""
        max_rent_per_sqm = row[row["Rent_Target_Column"]]
        return max_rent_per_sqm * row["surface_reelle_bati"]

    gdf_joined["Estimated_Monthly_Gross_Rent"] = gdf_joined.apply(
        select_max_rent, axis=1
    )
    gdf_joined["Annual_Gross_Rent"] = gdf_joined["Estimated_Monthly_Gross_Rent"] * 12

    property_value = gdf_joined["valeur_fonciere"]
    annual_taxes = property_value * ASSUMED_PROPERTY_TAX_RATE
    annual_expenses = gdf_joined["Annual_Gross_Rent"] * RENTAL_EXPENSE_RATIO
    loan_amount = property_value * (1 - ASSUMED_DOWN_PAYMENT_PERCENT)
    annual_interest = loan_amount * ASSUMED_MORTGAGE_RATE

    gdf_joined["Annual_Net_Cash_Flow"] = (
        gdf_joined["Annual_Gross_Rent"] - annual_taxes - annual_expenses - annual_interest
    )

    cash_invested = property_value * ASSUMED_DOWN_PAYMENT_PERCENT
    gdf_joined["Cash_on_Cash_ROI"] = (
        gdf_joined["Annual_Net_Cash_Flow"] / cash_invested
    ) * 100

    # --- 4. Save -----------------------------------------------------------
    final_cols = [
        "latitude",
        "longitude",
        "code_postal",
        "surface_reelle_bati",
        "valeur_fonciere",
        "annee_construction",
        "classe_consommation_energie",
        "nombre_pieces_principales",
        "Estimated_Monthly_Gross_Rent",
        "Annual_Net_Cash_Flow",
        "Cash_on_Cash_ROI",
        "DRIHL_Zone_ID",
    ]
    df_final_roi = gdf_joined[final_cols].copy()

    df_final_roi.to_csv(output_file, index=False)
    print(f"\nSUCCESS. Final ROI calculated and saved to '{output_file}'.")

    return df_final_roi


if __name__ == "__main__":
    if os.path.exists(RENT_ZONES_GEOJSON) and os.path.exists(MERGED_TRANSACTIONS_FILE):
        calculate_roi()
    else:
        print(
            f"Error: '{RENT_ZONES_GEOJSON}' or '{MERGED_TRANSACTIONS_FILE}' not found. "
            "Run Steps 2 and 4 first."
        )
