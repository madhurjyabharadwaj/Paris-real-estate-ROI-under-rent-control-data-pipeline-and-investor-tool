"""
Step 3: Ingestion and cleaning of DVF and DPE.

DVF (property sales) and DPE (energy performance) have no shared identifier, so
both are reduced to a standardised address key of the form ZIP_STREET_NUMBER.
Accents, punctuation, and inconsistent number formats are stripped so that the
two datasets can be joined in Step 4.

Outputs: dvf_clean.csv, dpe_clean.csv
"""

import os
import re
import unicodedata

import pandas as pd

from config import DPE_CLEAN_FILE, DPE_FILE, DVF_CLEAN_FILE, DVF_FILE


# ---------------------------------------------------------------------------
# Shared address key
# ---------------------------------------------------------------------------


def create_join_key(row, street_col, num_col, zip_col):
    """
    Build a standardised join key: ZIP_STREET_NUMBER.

    Accents are folded to ASCII and punctuation is removed so that
    "Rue de l'Eglise" and "RUE DE L EGLISE" collapse to the same key.
    """
    try:
        street = str(row[street_col]).strip()
        street = (
            unicodedata.normalize("NFKD", street)
            .encode("ascii", "ignore")
            .decode("utf-8")
        )
        street = street.upper()
        street = re.sub(r"[^\w\s]", "", street)

        num = str(row[num_col]).split(" ")[0]
        zip_code = str(row[zip_col]).replace(".0", "")

        return f"{zip_code}_{street}_{num}"
    except Exception:
        return None


# ---------------------------------------------------------------------------
# DVF
# ---------------------------------------------------------------------------


def load_and_clean_dvf(filepath=DVF_FILE):
    """
    Load DVF and keep only genuine Paris apartment sales.

    Filters applied:
        - postal code starts with 75
        - nature_mutation == 'Vente'
        - code_type_local == 2 (apartment)
        - price above 1,000 EUR and surface above 9 m2
    """
    print("Loading DVF data...")
    df = pd.read_csv(filepath, low_memory=False)

    # Robust type casting before any comparison.
    df["code_type_local"] = (
        pd.to_numeric(df["code_type_local"], errors="coerce").fillna(0).astype(int)
    )
    df["valeur_fonciere"] = pd.to_numeric(df["valeur_fonciere"], errors="coerce")
    df["surface_reelle_bati"] = pd.to_numeric(
        df["surface_reelle_bati"], errors="coerce"
    )
    df["code_postal"] = (
        pd.to_numeric(df["code_postal"], errors="coerce")
        .fillna(0)
        .astype(int)
        .astype(str)
    )

    df = df[df["code_postal"].str.startswith("75")].copy()
    df = df[df["nature_mutation"] == "Vente"].copy()
    df = df[df["code_type_local"] == 2].copy()
    df = df[(df["valeur_fonciere"] > 1000) & (df["surface_reelle_bati"] > 9)].copy()

    cols_to_keep = [
        "id_mutation",
        "date_mutation",
        "valeur_fonciere",
        "adresse_numero",
        "adresse_nom_voie",
        "code_postal",
        "nom_commune",
        "nombre_pieces_principales",
        "surface_reelle_bati",
        "latitude",
        "longitude",
    ]
    df = df[[col for col in cols_to_keep if col in df.columns]].copy()

    print("Generating address keys for DVF...")
    df["join_key"] = df.apply(
        lambda x: create_join_key(x, "adresse_nom_voie", "adresse_numero", "code_postal"),
        axis=1,
    )

    df["date_mutation"] = pd.to_datetime(df["date_mutation"])

    print(f"DVF cleaned: {len(df)} valid apartment sales found.")
    return df


# ---------------------------------------------------------------------------
# DPE
# ---------------------------------------------------------------------------


def map_dpe_quality(letter):
    """
    Map an energy class to the rent-control threshold it unlocks.

        A, B, C -> Loyer_Ref_Majore (120% of reference)
        D, E    -> Loyer_Ref        (reference)
        F, G    -> Loyer_Ref_Minore (90% of reference)

    Anything unrecognised falls back to the conservative reference rent.
    """
    letter = str(letter)
    if letter in ["A", "B", "C"]:
        return "Loyer_Ref_Majore"
    if letter in ["D", "E"]:
        return "Loyer_Ref"
    if letter in ["F", "G"]:
        return "Loyer_Ref_Minore"
    return "Loyer_Ref"


def fix_dpe_address_parsing(row):
    """
    Repair the DPE address fields.

    DPE frequently leaves numero_rue empty and folds the street number into
    nom_rue instead. Where that happens, the number is pulled back out with a
    regex so that the join key can be built consistently.
    """
    num = pd.to_numeric(row["numero_rue"], errors="coerce")
    if not pd.isna(num):
        row["numero_rue_clean"] = str(int(num))  # '32.0' -> '32'
        row["nom_rue_clean"] = str(row["nom_rue"]).strip()
        return row

    street_name = str(row["nom_rue"]).strip()
    match = re.match(r"^\s*(\d+)\s+([\w\s\'\-]+)", street_name, re.IGNORECASE)

    if match:
        row["numero_rue_clean"] = match.group(1)
        row["nom_rue_clean"] = match.group(2).strip()
    else:
        row["numero_rue_clean"] = "nan"
        row["nom_rue_clean"] = street_name

    return row


def load_and_clean_dpe(filepath=DPE_FILE):
    """Load DPE, keep valid energy ratings, and build the same join key."""
    print("Loading DPE data (this might take a moment)...")

    try:
        df = pd.read_csv(filepath, low_memory=False, sep=",")
    except Exception:
        df = pd.read_csv(filepath, low_memory=False, sep=";")

    target_cols = [
        "annee_construction",
        "classe_consommation_energie",
        "nom_rue",
        "numero_rue",
        "code_postal",
    ]
    existing_cols = [c for c in target_cols if c in df.columns]
    df = df[existing_cols].copy()

    df = df.dropna(subset=["annee_construction", "classe_consommation_energie"])
    df = df[df["annee_construction"].astype(str).str.isnumeric()]
    df["annee_construction"] = df["annee_construction"].astype(int)
    df = df[(df["annee_construction"] > 1600) & (df["annee_construction"] <= 2025)]

    df["Rent_Target_Column"] = df["classe_consommation_energie"].apply(map_dpe_quality)

    print("Fixing DPE address parsing and preparing join columns...")
    df = df.apply(fix_dpe_address_parsing, axis=1)

    print("Generating final address keys for DPE...")
    df["join_key"] = df.apply(
        lambda x: create_join_key(x, "nom_rue_clean", "numero_rue_clean", "code_postal"),
        axis=1,
    )

    df = df.drop(columns=["nom_rue_clean", "numero_rue_clean"], errors="ignore")
    df = df.drop_duplicates(subset=["join_key"])

    print(f"DPE cleaned: {len(df)} unique energy ratings found.")
    return df


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def run(dvf_file=DVF_FILE, dpe_file=DPE_FILE):
    """Clean both raw datasets and write them to disk."""
    if os.path.exists(dvf_file):
        dvf_clean = load_and_clean_dvf(dvf_file)
        dvf_clean.to_csv(DVF_CLEAN_FILE, index=False)
        print(f"File '{DVF_CLEAN_FILE}' created successfully.")
    else:
        print(f"Error: DVF file {dvf_file} not found. See data/README.md.")

    if os.path.exists(dpe_file):
        dpe_clean = load_and_clean_dpe(dpe_file)
        dpe_clean.to_csv(DPE_CLEAN_FILE, index=False)
        print(f"File '{DPE_CLEAN_FILE}' created successfully.")
    else:
        print(f"Error: DPE file {dpe_file} not found. See data/README.md.")


if __name__ == "__main__":
    run()
