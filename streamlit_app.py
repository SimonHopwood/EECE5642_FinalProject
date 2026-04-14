import streamlit as st
import pandas as pd
import pydeck as pdk
import json
import altair as alt

st.set_page_config(layout="wide")
st.title("OSHA Severe Injury Database Visualization Demo")

# -----------------------------
# Data loading
# -----------------------------
@st.cache_data
def load_full_data():
    df = pd.read_csv("January2015toAugust2025.csv")

    string_cols = [
        "ID",
        "Employer",
        "Nature",
        "NatureTitle",
        "Part of Body",
        "Part of Body Title",
        "Source",
        "SourceTitle",
        "Event",
        "EventTitle",
        "State",
    ]

    for col in string_cols:
        if col in df.columns:
            df[col] = df[col].astype("string").str.strip()

    return df


@st.cache_data
def load_states():
    with open("StateBoundryData.json", "r") as f:
        return json.load(f)


def build_map_data(df):
    map_df = df[["Latitude", "Longitude", "ID"]].copy()

    map_df = map_df.rename(columns={
        "Latitude": "lat",
        "Longitude": "lon"
    })

    map_df["lat"] = pd.to_numeric(map_df["lat"], errors="coerce")
    map_df["lon"] = pd.to_numeric(map_df["lon"], errors="coerce")
    map_df["ID"] = map_df["ID"].astype("string")

    map_df = map_df.dropna(subset=["lat", "lon", "ID"])
    return map_df


def apply_prefix_filter(df, column_name, code_value):
    if not code_value:
        return df

    if column_name not in df.columns:
        return df

    code_value = str(code_value).strip()
    if code_value == "":
        return df

    working_col = df[column_name].astype("string").str.strip()
    return df[working_col.str.startswith(code_value, na=False)]


def build_state_summary(df):
    if "State" not in df.columns:
        return pd.DataFrame(columns=["State", "Count"])

    state_df = df[["State"]].copy()
    state_df["State"] = state_df["State"].astype("string").str.strip()
    state_df = state_df.dropna(subset=["State"])
    state_df = state_df[state_df["State"] != ""]

    summary = (
        state_df.groupby("State")
        .size()
        .reset_index(name="Count")
        .sort_values("Count", ascending=False)
    )

    return summary


def build_top_counts(df, column_name, top_n=10):
    if column_name not in df.columns:
        return pd.DataFrame(columns=[column_name, "Count"])

    working = df[[column_name]].copy()
    working[column_name] = working[column_name].astype("string").str.strip()
    working = working.dropna(subset=[column_name])
    working = working[working[column_name] != ""]

    summary = (
        working.groupby(column_name)
        .size()
        .reset_index(name="Count")
        .sort_values("Count", ascending=False)
        .head(top_n)
    )

    return summary


def build_top_code_title_counts(df, code_col, title_col, top_n=10):
    missing_cols = [col for col in [code_col, title_col] if col not in df.columns]
    if missing_cols:
        return pd.DataFrame(columns=[code_col, title_col, "Label", "Count"])

    working = df[[code_col, title_col]].copy()
    working[code_col] = working[code_col].astype("string").str.strip()
    working[title_col] = working[title_col].astype("string").str.strip()

    working = working.dropna(subset=[code_col, title_col])
    working = working[(working[code_col] != "") & (working[title_col] != "")]

    summary = (
        working.groupby([code_col, title_col])
        .size()
        .reset_index(name="Count")
        .sort_values("Count", ascending=False)
        .head(top_n)
    )

    summary["Label"] = summary[title_col]

    return summary


# -----------------------------
# Load data
# -----------------------------
full_df = load_full_data()
states_json = load_states()

# -----------------------------
# Session state
# -----------------------------
if "selected_ids" not in st.session_state:
    st.session_state.selected_ids = []

if "selected_case_dropdown" not in st.session_state:
    st.session_state.selected_case_dropdown = None

if "applied_filters" not in st.session_state:
    st.session_state.applied_filters = {
        "nature": "",
        "part": "",
        "source": "",
        "event": "",
    }

# -----------------------------
# Sidebar filter form
# Filters only apply after submit
# -----------------------------
with st.sidebar:
    st.header("OIICS Code Filters")
    st.caption("Enter OIICS codes directly, then click Submit Filters.")
    st.caption("Filters use prefix matching.")

    with st.form("oiics_filter_form"):
        nature_code = st.text_input(
            "Nature",
            value=st.session_state.applied_filters["nature"]
        )

        part_code = st.text_input(
            "Part of Body",
            value=st.session_state.applied_filters["part"]
        )

        source_code = st.text_input(
            "Source",
            value=st.session_state.applied_filters["source"]
        )

        event_code = st.text_input(
            "Event",
            value=st.session_state.applied_filters["event"]
        )

        col1, col2 = st.columns(2)
        submit_filters = col1.form_submit_button("Submit Filters", use_container_width=True)
        clear_filters = col2.form_submit_button("Clear Filters", use_container_width=True)

    if submit_filters:
        st.session_state.applied_filters = {
            "nature": nature_code.strip(),
            "part": part_code.strip(),
            "source": source_code.strip(),
            "event": event_code.strip(),
        }
        st.session_state.selected_ids = []
        st.session_state.selected_case_dropdown = None
        st.rerun()

    if clear_filters:
        st.session_state.applied_filters = {
            "nature": "",
            "part": "",
            "source": "",
            "event": "",
        }
        st.session_state.selected_ids = []
        st.session_state.selected_case_dropdown = None
        st.rerun()

# -----------------------------
# Apply filters to full dataset
# -----------------------------
filtered_full_df = full_df.copy()
applied = st.session_state.applied_filters

filtered_full_df = apply_prefix_filter(filtered_full_df, "Nature", applied["nature"])
filtered_full_df = apply_prefix_filter(filtered_full_df, "Part of Body", applied["part"])
filtered_full_df = apply_prefix_filter(filtered_full_df, "Source", applied["source"])
filtered_full_df = apply_prefix_filter(filtered_full_df, "Event", applied["event"])

active_filters = []
if applied["nature"]:
    active_filters.append(f"Nature starts with {applied['nature']}")
if applied["part"]:
    active_filters.append(f"Part of Body starts with {applied['part']}")
if applied["source"]:
    active_filters.append(f"Source starts with {applied['source']}")
if applied["event"]:
    active_filters.append(f"Event starts with {applied['event']}")

if active_filters:
    st.caption("Active filters: " + " | ".join(active_filters))

total_rows = len(full_df)
filtered_rows = len(filtered_full_df)
filtered_pct = (filtered_rows / total_rows * 100) if total_rows > 0 else 0

st.write(
    f"Rows after filtering: {filtered_rows:,} / {total_rows:,} "
    f"({filtered_pct:.2f}% of total)"
)

# -----------------------------
# Build summaries
# -----------------------------
state_summary = build_state_summary(filtered_full_df)

top_employers = build_top_counts(filtered_full_df, "Employer", top_n=10)

top_events = build_top_code_title_counts(
    filtered_full_df,
    code_col="Event",
    title_col="EventTitle",
    top_n=10
)

top_sources = build_top_code_title_counts(
    filtered_full_df,
    code_col="Source",
    title_col="SourceTitle",
    top_n=10
)

# -----------------------------
# Build filtered map data
# -----------------------------
map_df = build_map_data(filtered_full_df)

if map_df.empty:
    st.warning("No rows match the current filters.")
    st.stop()

# -----------------------------
# Group map points
# -----------------------------
df_grouped = map_df.groupby(["lat", "lon"])["ID"].apply(list).reset_index()
df_grouped["count"] = df_grouped["ID"].apply(len)
df_grouped["ID_text"] = df_grouped["ID"].apply(lambda ids: ", ".join(map(str, ids)))

single_points = df_grouped[df_grouped["count"] == 1].copy()
multi_points = df_grouped[df_grouped["count"] > 1].copy()

if not single_points.empty:
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
# Keep selected IDs valid after filtering
# -----------------------------
current_id_set = set(map_df["ID"].astype(str))

if st.session_state.selected_ids:
    valid_ids = [x for x in st.session_state.selected_ids if str(x) in current_id_set]
    if valid_ids != st.session_state.selected_ids:
        st.session_state.selected_ids = valid_ids
        st.session_state.selected_case_dropdown = valid_ids[0] if valid_ids else None

# -----------------------------
# Layout
# -----------------------------
map_col, detail_col = st.columns([2.2, 1])

tooltip = {
    "html": "<b>Entries:</b> {count}<br/><b>IDs:</b> {ID_text}"
}

layers = [
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
    )
]

if not single_points.empty:
    layers.append(
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
        )
    )

if not multi_points.empty:
    layers.append(
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
        )
    )
    layers.append(
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
        )
    )

deck = pdk.Deck(
    map_style="dark",
    initial_view_state=pdk.ViewState(
        latitude=39.8283,
        longitude=-98.5795,
        zoom=3.5,
        pitch=45,
    ),
    layers=layers,
    tooltip=tooltip,
)

with map_col:
    st.write(f"Rows mapped: {len(map_df)}")

    event = st.pydeck_chart(
        deck,
        key="osha-map",
        on_select="rerun",
        selection_mode="single-object",
        width="stretch",
        height=700,
    )

# -----------------------------
# Update selected IDs from map click
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
        st.session_state.selected_case_dropdown = new_selected_ids[0] if new_selected_ids else None

# -----------------------------
# State breakdown chart
# -----------------------------
st.subheader("Filtered cases by state")

if state_summary.empty:
    st.info("No state data available for the current filters.")
else:
    normalized_low_priority_states = {state.upper() for state in low_priority_states}

    chart_df = state_summary.copy()
    chart_df["State_Normalized"] = chart_df["State"].astype("string").str.strip().str.upper()
    chart_df["Low Priority"] = chart_df["State_Normalized"].isin(normalized_low_priority_states)

    state_chart = (
        alt.Chart(chart_df)
        .mark_bar()
        .encode(
            x=alt.X("Count:Q", title="Case Count"),
            y=alt.Y("State:N", sort="-x", title="State"),
            color=alt.condition(
                alt.datum["Low Priority"],
                alt.value("#b4b4b4"),
                alt.value("#4169e1")
            ),
            tooltip=[
                alt.Tooltip("State:N"),
                alt.Tooltip("Count:Q"),
                alt.Tooltip("Low Priority:N")
            ]
        )
        .properties(height=900)
    )

    st.altair_chart(state_chart, use_container_width=True)

    with st.expander("Show state counts table"):
        st.dataframe(chart_df[["State", "Count"]], use_container_width=True, hide_index=True)

# -----------------------------
# Top category charts
# -----------------------------
st.subheader("Top filtered categories")

chart_col1, chart_col2, chart_col3 = st.columns(3)

with chart_col1:
    st.markdown("**Top Employers**")
    if top_employers.empty:
        st.info("No employer data available.")
    else:
        employer_chart = (
            alt.Chart(top_employers)
            .mark_bar()
            .encode(
                x=alt.X("Count:Q", title="Case Count"),
                y=alt.Y("Employer:N", sort="-x", title="Employer"),
                tooltip=[
                    alt.Tooltip("Employer:N"),
                    alt.Tooltip("Count:Q")
                ]
            )
            .properties(height=350)
        )
        st.altair_chart(employer_chart, use_container_width=True)

with chart_col2:
    st.markdown("**Top Events**")
    if top_events.empty:
        st.info("No event data available.")
    else:
        event_chart = (
            alt.Chart(top_events)
            .mark_bar()
            .encode(
                x=alt.X("Count:Q", title="Case Count"),
                y=alt.Y("Label:N", sort="-x", title="Event"),
                tooltip=[
                    alt.Tooltip("Label:N", title="Event"),
                    alt.Tooltip("Event:N", title="OIICS Event Code"),
                    alt.Tooltip("Count:Q")
                ]
            )
            .properties(height=350)
        )
        st.altair_chart(event_chart, use_container_width=True)

with chart_col3:
    st.markdown("**Top Sources**")
    if top_sources.empty:
        st.info("No source data available.")
    else:
        source_chart = (
            alt.Chart(top_sources)
            .mark_bar()
            .encode(
                x=alt.X("Count:Q", title="Case Count"),
                y=alt.Y("Label:N", sort="-x", title="Source"),
                tooltip=[
                    alt.Tooltip("Label:N", title="Source"),
                    alt.Tooltip("Source:N", title="OIICS Source Code"),
                    alt.Tooltip("Count:Q")
                ]
            )
            .properties(height=350)
        )
        st.altair_chart(source_chart, use_container_width=True)

# -----------------------------
# Detail panel fragment
# -----------------------------
@st.fragment
def selected_case_panel(df_for_details):
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

    selected_case = df_for_details[df_for_details["ID"].astype("string") == str(selected_id)].copy()

    if selected_case.empty:
        st.warning("No matching case found for the selected ID.")
        return

    row = selected_case.iloc[0]

    with st.container(border=True):
        st.markdown("**Employer:**")
        st.write(row.get("Employer", "N/A"))

        if pd.notna(row.get("EventDate")) and row.get("EventDate") != "":
            st.markdown("**Date:**")
            st.write(row.get("EventDate", "N/A"))

        st.markdown("**Injury:**")
        st.write(row.get("NatureTitle", row.get("Nature", "N/A")))

        st.markdown("**Body Part:**")
        st.write(row.get("Part of Body Title", row.get("Part of Body", "N/A")))

        st.markdown("**Cause:**")
        st.write(row.get("EventTitle", row.get("Event", "N/A")))

        if pd.notna(row.get("SourceTitle")) and row.get("SourceTitle") != "":
            st.markdown("**Source:**")
            st.write(row.get("SourceTitle", "N/A"))
        else:
            st.markdown("**Source:**")
            st.write(row.get("Source", "N/A"))

        if pd.notna(row.get("Secondary Source Title")) and row.get("Secondary Source Title") != "":
            st.markdown("**Source (Secondary):**")
            st.write(row.get("Secondary Source Title", "N/A"))

        st.markdown("**Written Description:**")
        st.write(row.get("Final Narrative", "N/A"))

# -----------------------------
# Render detail panel
# -----------------------------
with detail_col:
    selected_case_panel(filtered_full_df)