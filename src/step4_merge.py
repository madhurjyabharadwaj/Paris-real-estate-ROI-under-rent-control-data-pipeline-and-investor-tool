"""
Step 4: The grand unification (merging DVF and DPE).

A left join on the standardised address key keeps every Paris apartment sale and
attaches the energy class and construction year wherever an address match exists.
The project observed roughly a 58% match rate between the two datasets.

Output: paris_transactions_merged.csv
"""

import pandas as pd

from config import DPE_CLEAN_FILE, DVF_CLEAN_FILE, MERGED_TRANSACTIONS_FILE


def merge_dvf_dpe(
    dvf_path=DVF_CLEAN_FILE,
    dpe_path=DPE_CLEAN_FILE,
    output_path=MERGED_TRANSACTIONS_FILE,
):
    """Left-join cleaned DVF sales onto cleaned DPE ratings and save the result."""
    print("Loading cleaned DVF and DPE files...")
    dvf_clean = pd.read_csv(dvf_path)
    dpe_clean = pd.read_csv(dpe_path)

    dpe_to_merge = dpe_clean[
        [
            "join_key",
            "annee_construction",
            "Rent_Target_Column",
            "classe_consommation_energie",
        ]
    ].copy()

    print(
        f"Merging DVF ({len(dvf_clean)} rows) with DPE "
        f"({len(dpe_to_merge)} unique keys)..."
    )

    merged = pd.merge(dvf_clean, dpe_to_merge, on="join_key", how="left")
    print(f"Merge complete. Total transactions: {len(merged)}")

    # Unmatched rows fall back to conservative defaults.
    merged["annee_construction"] = merged["annee_construction"].fillna(0).astype(int)
    merged["Rent_Target_Column"] = merged["Rent_Target_Column"].fillna("Loyer_Ref")
    merged["classe_consommation_energie"] = merged[
        "classe_consommation_energie"
    ].fillna("N")  # N for not available

    merged = merged.drop(columns=["join_key"])
    merged.to_csv(output_path, index=False)
    print(f"\nSUCCESS. Merged file saved as '{output_path}'.")

    match_count = merged["annee_construction"].astype(bool).sum()
    print(
        f"Transactions linked with DPE data: {match_count} "
        f"({match_count / len(merged):.1%})"
    )
    print(merged.head())

    return merged


if __name__ == "__main__":
    merge_dvf_dpe()
