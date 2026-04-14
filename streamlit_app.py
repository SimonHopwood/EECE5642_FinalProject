#NEW
import streamlit as st
import pandas as pd
import pydeck as pdk
import json

st.set_page_config(layout="wide")
st.title("OSHA Severe Injury Visualization TEST")

# -----------------------------
# Data loading
# -----------------------------
@st.cache_data
def load_map_data():
    df = pd.read_csv(
        "January2015toAugust2025.csv",
        usecols=["Latitude", "Longitude", "ID"]
    )

    df = df.rename(columns={
        "Latitude": "lat",
        "Longitude": "lon"
    })

    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
    df = df.dropna(subset=["lat", "lon", "ID"])

    return df

@st.cache_data
def load_full_data():
    df = pd.read_csv("January2015toAugust2025.csv")
    return df

@st.cache_data
def load_states():
    with open("StateBoundryData.json", "r") as f:
        return json.load(f)

df = load_map_data()
full_df = load_full_data()
states_json = load_states()

# -----------------------------
# Group map points
# -----------------------------
df_grouped = df.groupby(["lat", "lon"])["ID"].apply(list).reset_index()
df_grouped["count"] = df_grouped["ID"].apply(len)
df_grouped["ID_text"] = df_grouped["ID"].apply(lambda ids: ", ".join(map(str, ids)))

single_points = df_grouped[df_grouped["count"] == 1].copy()
multi_points = df_grouped[df_grouped["count"] > 1].copy()

# For easier selection handling, store the one ID directly on single points
single_points["selected_id"] = single_points["ID"].apply(lambda x: x[0])

# -----------------------------
# Process state GeoJSON
# -----------------------------
low_priority_states = {
    "California", "Oregon", "Washington", "Nevada", "Arizona", "New Mexico",
    "Utah", "Wyoming", "Minnesota", "Iowa", "Michigan", "Indiana", "Kentucky",
    "Tennessee", "North Carolina", "South Carolina", "Virginia", "Maryland",
    "Vermont", "Alaska", "Hawaii"
}

for feature in states_json["features"]:
    state_name = feature["properties"].get("NAME")
    is_low_priority = state_name in low_priority_states
    feature["properties"]["fill_color"] = (
        [180, 180, 180, 40] if is_low_priority else [65, 105, 225, 120]
    )

# -----------------------------
# Layout
# -----------------------------
map_col, detail_col = st.columns([2.2, 1])

tooltip = {
    "html": "<b>Entries:</b> {count}<br/><b>IDs:</b> {ID_text}"
}

deck = pdk.Deck(
    map_style="dark",
    initial_view_state=pdk.ViewState(
        latitude=39.8283,
        longitude=-98.5795,
        zoom=3.5,
        pitch=45,
    ),
    layers=[
        pdk.Layer(
            "GeoJsonLayer",
            id="states",
            data=states_json,
            stroked=True,
            filled=True,
            pickable=False,
            get_fill_color="properties.fill_color",
            get_line_color=[255, 255, 255, 120],
            line_width_min_pixels=1,
        ),
        pdk.Layer(
            "ScatterplotLayer",
            id="single-points",
            data=single_points,
            get_position="[lon, lat]",
            get_color="[255, 140, 0, 180]",
            radius_min_pixels=1,
            get_radius=100,
            pickable=True,
            auto_highlight=True,
        ),
        pdk.Layer(
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
        ),
        pdk.Layer(
            "ScatterplotLayer",
            id="multi-points-underside",
            data=multi_points,
            get_position="[lon, lat]",
            get_color="[255, 140, 0, 180]",
            radius_min_pixels=1,
            get_radius=100,
            pickable=False,
            auto_highlight=True,
        ),
    ],
    tooltip=tooltip,
)

with map_col:
    event = st.pydeck_chart(
        deck,
        key="osha-map",
        on_select="rerun",
        selection_mode="single-object",
        width="stretch",
        height=700,
    )

# -----------------------------
# Session state for stable details panel
# -----------------------------
if "selected_ids" not in st.session_state:
    st.session_state.selected_ids = []

if "selected_case_dropdown" not in st.session_state:
    st.session_state.selected_case_dropdown = None

# -----------------------------
# Detail panel fragment
# Changing the dropdown reruns only this fragment,
# not the whole app / map.
# -----------------------------
@st.fragment
def selected_case_panel(full_df):
    st.subheader("Selected case details")

    ids = st.session_state.get("selected_ids", [])

    if not ids:
        st.info("Click a point or column on the map to view case details.")
        return

    st.write(f"Selected entries: {len(ids)}")

    if len(ids) > 1:
        selected_id = st.selectbox(
            "Choose an ID to inspect",
            options=ids,
            key="selected_case_dropdown",
        )
    else:
        selected_id = ids[0]
        st.markdown(f"**Selected ID:** {selected_id}")

    selected_case = full_df[full_df["ID"] == selected_id].copy()

    if selected_case.empty:
        st.warning("No matching case found for the selected ID.")
        return

    row = selected_case.iloc[0]

    #st.markdown(f"### Case ID: {selected_id}")

    with st.container(border=True):
        st.markdown("**Employer:**")
        st.write(row.get("Employer", "N/A"))

        if row.get("**EventDate**") != "" and pd.notna(row.get("EventDate")):
            st.markdown("**Date:**")
            st.write(row.get("EventDate", "N/A"))

        st.markdown("**Injury:**")
        st.write(row.get("NatureTitle", "N/A"))

        st.markdown("**Body Part:**")
        st.write(row.get("Part of Body Title", "N/A"))


        st.markdown("**Cause:**")
        st.write(row.get("EventTitle", "N/A"))

        if row.get("SourceTitle") != "" and pd.notna(row.get("SourceTitle")):
            st.markdown("**Source:**")
            st.write(row.get("SourceTitle", "N/A"))

        if row.get("Secondary Source Title") != "" and pd.notna(row.get("Secondary Source Title")):
            st.markdown("**Source (Secondary):**")
            st.write(row.get("Secondary Source Title", "N/A"))

        st.markdown("**Written Description:**")
        st.write(row.get("Final Narrative", "N/A"))
# -----------------------------
# Update selected IDs from map click
# Clicking the map reruns the app.
# Changing the dropdown does not rerun the map because
# the dropdown lives inside the fragment above.
# -----------------------------
if event.selection and event.selection.objects:
    new_selected_ids = None

    if "single-points" in event.selection.objects and event.selection.objects["single-points"]:
        obj = event.selection.objects["single-points"][0]
        new_selected_ids = [obj["selected_id"]]

    elif "multi-points" in event.selection.objects and event.selection.objects["multi-points"]:
        obj = event.selection.objects["multi-points"][0]
        new_selected_ids = obj["ID"]

    if new_selected_ids is not None and new_selected_ids != st.session_state.selected_ids:
        st.session_state.selected_ids = new_selected_ids
        st.session_state.selected_case_dropdown = new_selected_ids[0]

# -----------------------------
# Render detail panel
# -----------------------------
with detail_col:
    selected_case_panel(full_df)








#Original
"""
import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk
import json


st.title("OSHA Severe Injury Visulization TEST")


#Cache Non-Fatal Injury Data (Lightweight and Full)
@st.cache_data
def load_lightweight_data():
    df = pd.read_csv("January2015toAugust2025.csv", usecols=["Latitude","Longitude","ID"])

    df = df.rename(columns={
        "Latitude": "lat",
        "Longitude": "lon"
    })

    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")

    df = df.dropna(subset=["lat", "lon"])

    return df

@st.cache_data
def load_full_data():
    df = pd.read_csv("January2015toAugust2025.csv")

    df = df.rename(columns={
        "Latitude": "lat",
        "Longitude": "lon"
    })

    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")

    df = df.dropna(subset=["lat", "lon"])

    return df

#Cache State Boundry GeoJSONs
@st.cache_data
def load_states():
    with open("StateBoundryData.json", "r") as f:
        return json.load(f)


df = load_lightweight_data()
full_df = load_full_data()
states_json = load_states()

#Process Non-Fatal Injury data
df_grouped = df.groupby(["lat", "lon"])["ID"].apply(list).reset_index()
df_grouped["count"] = df_grouped["ID"].apply(len)
multi_points = df_grouped[df_grouped["count"] > 1]
single_points = df_grouped[df_grouped["count"] == 1]

#Process state GeoJSON information
low_priority_states = {"California", "Oregon", "Washington", "Nevada", "Arizona", "New Mexico", "Utah", "Wyoming", "Minnesota", "Iowa", "Michigan", "Indiana", "Kentucky", "Tennessee", "North Carolina", "South Carolina", "Virginia", "Maryland", "Vermont", "Alaska", "Hawaii"}

for feature in states_json["features"]:
    abbr = feature["properties"].get("NAME")
    is_low_priority = abbr in low_priority_states

    feature["properties"]["priority"] = is_low_priority
    feature["properties"]["fill_color"] = (
        [180, 180, 180, 40] if is_low_priority else [65, 105, 225, 120]
    )


#Front End
st.write(f"Rows mapped: {len(df)}")
st.dataframe(df.head(), use_container_width=True)


tooltip = {
   "html": "<b>Entries:</b> {count}<br/><b>IDs:</b> {ID} \n "
}

st.pydeck_chart(pdk.Deck(
    map_style='dark',
    initial_view_state=pdk.ViewState(
        latitude=42.3398,
        longitude=-71.0892,
        zoom=10,
        pitch=50,
    ),
    layers=[
        pdk.Layer(
            'ScatterplotLayer',
            data=single_points,
            get_position='[lon, lat]',
            get_color='[255, 140, 0, 180]',
            radius_min_pixels=1,
            #radius_max_pixels=20,
            stroked=True,
            get_radius=100,
            pickable=True,
        ),
        pdk.Layer(
            'ColumnLayer',
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
            #wireframe=True
        ),
        pdk.Layer(
            'GeoJsonLayer',
            data=states_json,
            id="states",
            stroked=True,
            filled=True,
            pickable=False,
            get_fill_color="properties.fill_color",
            get_line_color=[255, 255, 255, 120],
            line_width_min_pixels=1,
        )
    ],
    tooltip=tooltip
))



"""