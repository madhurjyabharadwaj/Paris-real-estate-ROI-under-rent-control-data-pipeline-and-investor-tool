"""
Run the full pipeline end to end.

Usage:
    python src/run_pipeline.py

Steps 1 and 2 need only an internet connection. Steps 3 onwards need the DVF and
DPE extracts placed in data/ first, as described in data/README.md.
"""

import os

import config
from step1_download_kml import generate_and_download_kmls
from step2_rent_zones import prepare_geospatial_data, save_rent_zones
from step3_clean_dvf_dpe import run as clean_dvf_dpe
from step4_merge import merge_dvf_dpe
from step5_roi import calculate_roi
from step6_investor_tool import build_map_for, load_roi_data


def main():
    config.ensure_directories()

    print("\n=== Step 1: download DRIHL rent-control KML files ===")
    generate_and_download_kmls()

    print("\n=== Step 2: build the master rent-zone GeoDataFrame ===")
    zones = prepare_geospatial_data()
    save_rent_zones(zones)

    if not (os.path.exists(config.DVF_FILE) and os.path.exists(config.DPE_FILE)):
        print(
            "\nStopping after Step 2. Place the DVF and DPE extracts in data/ "
            "to run the rest of the pipeline (see data/README.md)."
        )
        return

    print("\n=== Step 3: clean DVF and DPE ===")
    clean_dvf_dpe()

    print("\n=== Step 4: merge DVF and DPE ===")
    merge_dvf_dpe()

    print("\n=== Step 5: spatial join and ROI calculation ===")
    calculate_roi()

    print("\n=== Step 6: build a sample investor map ===")
    roi_df = load_roi_data()
    build_map_for(roi_df, num_rooms=3, max_budget=400_000, arrondissement="All")

    print("\nPipeline complete.")


if __name__ == "__main__":
    main()
