import pandas as pd
import pydeck as pdk

from constants import LOW_PRIORITY_STATES


# ---------------------------------------------------------------------------
# Point grouping
# ---------------------------------------------------------------------------

def group_map_points(map_df: pd.DataFrame):
    """Split map points into single-incident and multi-incident groups.

    Returns:
        (single_points, multi_points) — each is a DataFrame with columns
        lat, lon, ID (list), count, ID_text. single_points also has selected_id.
    """
    grouped = (
        map_df.groupby(["lat", "lon"])["ID"]
        .apply(list)
        .reset_index()
    )
    grouped["count"]   = grouped["ID"].apply(len)
    grouped["ID_text"] = grouped["ID"].apply(lambda ids: ", ".join(map(str, ids)))

    single = grouped[grouped["count"] == 1].copy()
    multi  = grouped[grouped["count"] > 1].copy()

    if not single.empty:
        single["selected_id"] = single["ID"].apply(lambda x: x[0])

    return single, multi


# ---------------------------------------------------------------------------
# State GeoJSON
# ---------------------------------------------------------------------------

def annotate_state_geojson(states_json: dict):
    """Add a fill_color property to each state feature.

    Low-priority states (those with historically lower federal OSHA
    jurisdiction activity) are rendered in gray; all others in blue.
    """
    for feature in states_json["features"]:
        name = feature["properties"].get("NAME", "")
        is_low_priority = name in LOW_PRIORITY_STATES
        feature["properties"]["fill_color"] = (
            [180, 180, 180, 40] if is_low_priority else [65, 105, 225, 120]
        )
    return states_json


# ---------------------------------------------------------------------------
# Layer builders
# ---------------------------------------------------------------------------

def build_map_layers(
    states_json: dict,
    single_points: pd.DataFrame,
    multi_points: pd.DataFrame,
):
    """Construct the full ordered list of PyDeck layers for the map."""
    layers = [_states_layer(states_json)]

    if not single_points.empty:
        layers.append(_single_points_layer(single_points))

    if not multi_points.empty:
        layers.extend(_multi_points_layers(multi_points))

    return layers


# ---------------------------------------------------------------------------
# Private layer helpers
# ---------------------------------------------------------------------------

def _states_layer(states_json: dict):
    return pdk.Layer(
        "GeoJsonLayer",
        id="states",
        data=states_json,
        stroked=True,
        filled=True,
        pickable=False,
        get_fill_color="properties.fill_color",
        get_line_color=[255, 255, 255, 120],
        line_width_min_pixels=1,
    )


def _single_points_layer(single_points: pd.DataFrame):
    return pdk.Layer(
        "ScatterplotLayer",
        id="single-points",
        data=single_points,
        get_position="[lon, lat]",
        get_color="[255, 140, 0, 180]",
        radius_min_pixels=1,
        get_radius=100,
        pickable=True,
        auto_highlight=True,
    )


def _multi_points_layers(multi_points: pd.DataFrame):
    """Multi-incident locations get a 3D column plus a flat base marker."""
    column_layer = pdk.Layer(
        "ColumnLayer",
        id="multi-points",
        data=multi_points,
        get_position="[lon, lat]",
        radius=100,
        elevation_scale=250,
        get_elevation="count",
        get_fill_color="[255, 200, 0, 230]",
        extruded=True,
        pickable=True,
        auto_highlight=True,
        disk_resolution=6,
    )
    base_layer = pdk.Layer(
        "ScatterplotLayer",
        id="multi-points-underside",
        data=multi_points,
        get_position="[lon, lat]",
        get_color="[255, 140, 0, 180]",
        radius_min_pixels=1,
        get_radius=100,
        pickable=False,
        auto_highlight=True,
    )
    return [column_layer, base_layer]