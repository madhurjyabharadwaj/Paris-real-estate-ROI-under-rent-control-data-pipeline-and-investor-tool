"""
Step 1: Automated KML generation and download.

DRIHL publishes the Paris rent-control reference rents as one KML file per
combination of validity period, number of main rooms, and construction era.
This module builds every URL in that grid and downloads the files locally.

Constraints applied: unfurnished lets only, periods from 2019-07-01 onwards.
"""

import os

import requests
from tqdm import tqdm

from config import (
    BASE_URL,
    CONSTRUCTION_ERAS,
    KML_DIR,
    PERIODS,
    RENTAL_TYPE,
    ROOMS,
    ensure_directories,
)


def generate_and_download_kmls(kml_dir=KML_DIR):
    """
    Generate every required KML URL and download the files into `kml_dir`.

    Files already on disk are skipped, so the function is safe to re-run.

    Returns:
        bool: True if every expected file is present locally.
    """
    ensure_directories()

    all_parameters = [
        (period, room, era)
        for period in PERIODS
        for room in ROOMS
        for era in CONSTRUCTION_ERAS
    ]
    total_files = len(all_parameters)
    print(f"Total files to process: {total_files}")

    success_count = 0

    for period, room, construction in tqdm(all_parameters, desc="Downloading KMLs"):
        # Remote filename, e.g. drihl_medianes_3_1946-1970_non-meuble.kml
        filename_url = f"drihl_medianes_{room}_{construction}_{RENTAL_TYPE}.kml"
        full_url = f"{BASE_URL}{period}/{filename_url}"

        # Local filename, e.g. 20250701_3_1946-1970_non-meuble.kml
        local_filename = (
            f"{period.replace('-', '')}_{room}_{construction}_{RENTAL_TYPE}.kml"
        )
        local_path = os.path.join(kml_dir, local_filename)

        if os.path.exists(local_path):
            success_count += 1
            continue

        try:
            response = requests.get(full_url, timeout=10)
            response.raise_for_status()

            with open(local_path, "wb") as handle:
                handle.write(response.content)

            success_count += 1

        except requests.exceptions.RequestException as exc:
            tqdm.write(f"ERROR downloading {local_filename} from {full_url}: {exc}")

    print("\n--- Download Summary ---")
    print(f"Attempted: {total_files} files.")
    print(f"Successfully downloaded or found locally: {success_count} files.")

    if success_count == total_files:
        print(f"SUCCESS. All KML files are in '{kml_dir}'.")
    else:
        print("Warning: not all files were retrieved. Check the errors above.")

    return success_count == total_files


if __name__ == "__main__":
    generate_and_download_kmls()
