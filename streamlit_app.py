import streamlit as st
import pandas as pd
import numpy as np
import pydeck as pdk
import json


st.title("OSHA Severe Injury Visulization")


#Cache Non-Fatal Injury Data
@st.cache_data
def load_data():
    df = pd.read_csv("January2015toAugust2025.csv", usecols=["Latitude","Longitude","ID"])

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


df = load_data()
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
            get_radius=100,
            pickable=True
        ),
        pdk.Layer(
            'ColumnLayer',
            data=multi_points,
            get_position="[lon, lat]",
            radius=100,
            elevation_scale=250,
            get_elevation="count",
            get_fill_color="[255, 140, 0, 180]",
            extruded=True,
            pickable=True,
            auto_highlight=True,
            disk_resolution=6,
            wireframe=True
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