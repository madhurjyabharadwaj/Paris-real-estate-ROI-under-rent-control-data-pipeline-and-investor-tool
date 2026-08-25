"""
Step 6: Investor recommendation tool and interactive ROI map.

Takes the per-transaction ROI file from Step 5 and turns it into a
decision-support tool. The investor picks a number of rooms, a budget, and an
arrondissement; the tool returns the highest-ROI matches as a table and plots
them on a clustered Folium map colour-coded by return.

Marker colours
--------------
    green   high ROI    (>= 8%)
    orange  medium ROI  (3% to 8%)
    red     low ROI     (<= 3%)

Output: investment_map.html
"""

import folium
import numpy as np
import pandas as pd
from folium.plugins import MarkerCluster

from config import (
    BAD_ROI_THRESHOLD,
    GOOD_ROI_THRESHOLD,
    MAP_HTML_FILE,
    ROI_FILE,
)


# ---------------------------------------------------------------------------
# Data preparation
# ---------------------------------------------------------------------------


def load_roi_data(roi_file=ROI_FILE, trim_outliers=True):
    """
    Load the ROI dataset, derive the arrondissement, and trim extreme values.

    Cash_on_Cash_ROI is already expressed in percent. The 1st and 99th
    percentiles are dropped because a handful of near-zero sale prices in DVF
    (family transfers, partial shares) produce ROI figures in the hundreds of
    percent and would otherwise dominate the map.
    """
    roi_df = pd.read_csv(roi_file)
    print(f"Loaded ROI file '{roi_file}' with {len(roi_df)} rows.")

    if "code_postal" in roi_df.columns:
        # 75011 -> '11'
        roi_df["arrondissement"] = roi_df["code_postal"].astype(str).str[-2:]
    else:
        roi_df["arrondissement"] = np.nan

    if trim_outliers and "Cash_on_Cash_ROI" in roi_df.columns:
        q_low, q_high = roi_df["Cash_on_Cash_ROI"].quantile([0.01, 0.99])
        roi_df = roi_df[
            (roi_df["Cash_on_Cash_ROI"] >= q_low)
            & (roi_df["Cash_on_Cash_ROI"] <= q_high)
        ].copy()
        print(f"After ROI outlier filtering: {len(roi_df)} rows.")

    return roi_df


# ---------------------------------------------------------------------------
# Filtering and categorisation
# ---------------------------------------------------------------------------


def filter_properties(df, num_rooms, max_budget, arrondissement=None):
    """
    Filter the ROI dataset according to investor preferences.

    Args:
        df: the ROI DataFrame.
        num_rooms: exact number of main rooms.
        max_budget: maximum purchase price in EUR.
        arrondissement: '01' to '20', or None / 'All' for no filter.
    """
    if df.empty:
        return df.copy()

    filtered = df.copy()

    if "nombre_pieces_principales" in filtered.columns:
        filtered = filtered[filtered["nombre_pieces_principales"] == num_rooms]

    if "valeur_fonciere" in filtered.columns:
        filtered = filtered[filtered["valeur_fonciere"] <= max_budget]

    if arrondissement is not None and arrondissement != "All":
        filtered = filtered[filtered["arrondissement"] == arrondissement]

    required_cols = ["latitude", "longitude", "Cash_on_Cash_ROI"]
    existing_required = [c for c in required_cols if c in filtered.columns]
    if existing_required:
        filtered = filtered.dropna(subset=existing_required)

    return filtered


def color_for_roi(roi_percent):
    """Assign a marker colour based on ROI in percent."""
    if roi_percent >= GOOD_ROI_THRESHOLD:
        return "green"
    if roi_percent <= BAD_ROI_THRESHOLD:
        return "red"
    return "orange"


# ---------------------------------------------------------------------------
# Map
# ---------------------------------------------------------------------------


def show_investment_map(df_filtered, max_points=500):
    """
    Build a clustered Folium map of the filtered properties.

    Each marker is colour-coded by ROI and carries a popup with price, surface,
    ROI, postal code, and rent-control zone. Up to `max_points` rows are plotted
    so the map stays responsive.
    """
    if df_filtered.empty:
        print("No properties found with these criteria.")
        return None

    if len(df_filtered) > max_points:
        df_vis = df_filtered.sample(max_points, random_state=42)
    else:
        df_vis = df_filtered.copy()

    paris_center = [48.8566, 2.3522]
    m = folium.Map(location=paris_center, zoom_start=12)
    marker_cluster = MarkerCluster().add_to(m)

    for _, row in df_vis.iterrows():
        roi_percent = row["Cash_on_Cash_ROI"]
        color = color_for_roi(roi_percent)

        popup_html = ""
        if "valeur_fonciere" in row:
            popup_html += f"<b>Price:</b> {row['valeur_fonciere']:.0f} &euro;<br>"
        if "surface_reelle_bati" in row:
            popup_html += f"<b>Surface:</b> {row['surface_reelle_bati']} m&sup2;<br>"

        popup_html += f"<b>ROI:</b> {roi_percent:.1f}%<br>"

        if "code_postal" in row:
            popup_html += f"<b>Postal code:</b> {row['code_postal']}<br>"
        if "DRIHL_Zone_ID" in row:
            popup_html += f"<b>Zone:</b> {row['DRIHL_Zone_ID']}"

        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=4,
            color=color,
            fill=True,
            fill_opacity=0.7,
            popup=popup_html,
        ).add_to(marker_cluster)

    return m


def top_properties(df_filtered, n=10):
    """Return the n highest-ROI rows with the columns an investor cares about."""
    cols_to_show = [
        "code_postal",
        "valeur_fonciere",
        "surface_reelle_bati",
        "Cash_on_Cash_ROI",
    ]
    existing_cols = [c for c in cols_to_show if c in df_filtered.columns]
    return (
        df_filtered[existing_cols]
        .sort_values("Cash_on_Cash_ROI", ascending=False)
        .head(n)
    )


def build_map_for(
    roi_df, num_rooms, max_budget, arrondissement=None, output_html=MAP_HTML_FILE
):
    """
    Headless helper: filter, print the top matches, and save the map to HTML.

    Useful outside Jupyter, where the ipywidgets interface is not available.
    """
    df_filtered = filter_properties(roi_df, num_rooms, max_budget, arrondissement)

    if df_filtered.empty:
        print("No properties found for these filters.")
        return None

    print(top_properties(df_filtered).to_string(index=False))

    m = show_investment_map(df_filtered)
    if m is not None:
        m.save(output_html)
        print(f"\nInteractive map saved to '{output_html}'.")
    return m


# ---------------------------------------------------------------------------
# Notebook interface
# ---------------------------------------------------------------------------


def build_investor_ui(roi_df, output_html=MAP_HTML_FILE):
    """
    Build the ipywidgets control panel. Call inside Jupyter and display() it.

    Controls: rooms slider, budget slider, arrondissement dropdown, and a button
    that renders the top-10 table plus the interactive map.
    """
    import ipywidgets as widgets
    from IPython.display import HTML, display

    room_widget = widgets.IntSlider(
        value=2, min=1, max=6, step=1, description="Rooms:", continuous_update=False
    )

    budget_widget = widgets.IntSlider(
        value=600_000,
        min=100_000,
        max=2_000_000,
        step=50_000,
        description="Budget (EUR):",
        continuous_update=False,
    )

    if roi_df["arrondissement"].notna().any():
        arr_options = ["All"] + sorted(
            roi_df["arrondissement"].dropna().unique().tolist()
        )
    else:
        arr_options = ["All"]

    arr_widget = widgets.Dropdown(
        options=arr_options, value="All", description="Arrdt:"
    )

    button = widgets.Button(
        description="Show Investment Map", button_style="success", icon="map"
    )
    output = widgets.Output()

    def on_button_click(_):
        with output:
            output.clear_output()

            arr_value = None if arr_widget.value == "All" else arr_widget.value

            df_filtered = filter_properties(
                roi_df,
                num_rooms=room_widget.value,
                max_budget=budget_widget.value,
                arrondissement=arr_value,
            )

            if df_filtered.empty:
                print("No properties found for these filters.")
                return

            display(
                top_properties(df_filtered).style.format(
                    {"valeur_fonciere": "{:,.0f}", "Cash_on_Cash_ROI": "{:.1f}%"}
                )
            )

            m = show_investment_map(df_filtered)
            if m is not None:
                display(m)
                m.save(output_html)
                display(
                    HTML(
                        f"<p><b>Interactive map saved as <code>{output_html}</code>."
                        f"</b><br>If the map does not appear above, open that file "
                        f"in your browser.</p>"
                    )
                )

    button.on_click(on_button_click)

    return widgets.VBox(
        [widgets.HBox([room_widget, budget_widget, arr_widget]), button, output]
    )


if __name__ == "__main__":
    data = load_roi_data()
    build_map_for(data, num_rooms=3, max_budget=400_000, arrondissement="All")
