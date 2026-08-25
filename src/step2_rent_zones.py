"""
Step 2: Loading and preparation of geospatial data.

Reads every KML file downloaded in Step 1, extracts the reference rents and the
zone polygons, tags each row with the parameters encoded in the filename, and
concatenates everything into a single GeoDataFrame saved as GeoJSON.

Output: Paris_Rent_Zones_GDF.geojson (8,960 rows across 112 source files).
"""

import os

import geopandas as gpd
import pandas as pd
from fiona.drvsupport import supported_drivers
from tqdm import tqdm

from config import KML_DIR, RENT_ZONES_GEOJSON


def prepare_geospatial_data(kml_dir=KML_DIR):
    """
    Read all KML files in `kml_dir` and return one master GeoDataFrame.

    Each KML carries the three rent-control thresholds per zone:
        ref     -> Loyer_Ref         (reference rent, EUR/m2/month)
        refmaj  -> Loyer_Ref_Majore  (120% ceiling)
        refmin  -> Loyer_Ref_Minore  (90% floor)

    Returns:
        geopandas.GeoDataFrame or None if nothing could be parsed.
    """
    all_gdfs = []

    # geopandas needs the KML driver explicitly enabled for reading.
    supported_drivers["KML"] = "r"

    kml_files = [f for f in os.listdir(kml_dir) if f.endswith(".kml")]
    print(f"Starting preparation of {len(kml_files)} KML files...")

    for filename in tqdm(kml_files, desc="Processing KML files"):

        # Filename layout: <period>_<rooms>_<era>_<rental_type>.kml
        parts = filename.replace(".kml", "").split("_")
        if len(parts) != 4:
            continue

        period_str, rooms_str, construction_str, _ = parts
        period_start_date = f"{period_str[:4]}-{period_str[4:6]}-{period_str[6:]}"

        file_path = os.path.join(kml_dir, filename)

        try:
            t_gdf = gpd.read_file(file_path, driver="KML")

            t_gdf = t_gdf.rename(
                columns={
                    "nameZone": "DRIHL_Zone_ID",
                    "ref": "Loyer_Ref",
                    "refmaj": "Loyer_Ref_Majore",
                    "refmin": "Loyer_Ref_Minore",
                }
            )

            t_gdf["Period_Start"] = period_start_date
            # 'piece' looks like "3 pieces", so take the leading integer.
            t_gdf["Rooms"] = t_gdf["piece"].str.split(" ").str[0].astype(int)
            t_gdf["Construction_Era"] = construction_str

            for col in ("Loyer_Ref_Minore", "Loyer_Ref", "Loyer_Ref_Majore"):
                t_gdf[col] = pd.to_numeric(t_gdf[col], errors="coerce")

            t_gdf = t_gdf[
                [
                    "DRIHL_Zone_ID",
                    "Loyer_Ref_Minore",
                    "Loyer_Ref",
                    "Loyer_Ref_Majore",
                    "Period_Start",
                    "Rooms",
                    "Construction_Era",
                    "geometry",
                ]
            ]

            all_gdfs.append(t_gdf)

        except Exception as exc:
            tqdm.write(f"ERROR processing {filename}: {exc}")
            continue

    if not all_gdfs:
        print("No GeoDataFrames were successfully processed.")
        return None

    paris_rent_zones_gdf = pd.concat(all_gdfs, ignore_index=True)
    paris_rent_zones_gdf = gpd.GeoDataFrame(
        paris_rent_zones_gdf, geometry="geometry", crs="EPSG:4326"
    )

    print("\n--- Preparation Summary ---")
    print(f"Total rows in master GeoDataFrame: {len(paris_rent_zones_gdf)}")
    print(f"Columns: {list(paris_rent_zones_gdf.columns)}")
    print(paris_rent_zones_gdf.head())

    return paris_rent_zones_gdf


def save_rent_zones(gdf, output_file=RENT_ZONES_GEOJSON):
    """Write the master GeoDataFrame to disk as GeoJSON."""
    if gdf is None:
        print("Nothing to save.")
        return None

    gdf.to_file(output_file, driver="GeoJSON")
    print(f"\nSUCCESS. Master GeoDataFrame saved as '{output_file}'.")
    return output_file


if __name__ == "__main__":
    zones = prepare_geospatial_data()
    save_rent_zones(zones)
