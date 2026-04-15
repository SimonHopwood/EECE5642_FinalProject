import pandas as pd
import pydeck as pdk
import streamlit as st

import charts
import data
import filters
import map_utils
from constants import OUTCOME_COLS

st.set_page_config(layout="wide")
st.title("OSHA Severe Injury Database Visualization Demo")

# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

filters.init_session_state()

full_df     = data.load_injury_data()
states_json = data.load_state_boundaries()

# ---------------------------------------------------------------------------
# Sidebar: filter form
# ---------------------------------------------------------------------------

filters.render_filter_sidebar()

# ---------------------------------------------------------------------------
# Apply filters and show status
# ---------------------------------------------------------------------------

applied     = filters.get_applied_filters()
filtered_df = data.apply_prefix_filters(full_df, **applied)

filters.render_filter_status(
    total_rows=len(full_df),
    filtered_rows=len(filtered_df),
)

# ===========================================================================
# Helper functions
# ===========================================================================

def _update_selection(map_event, map_df: pd.DataFrame):
    """Sync session state selected IDs from a map click event."""
    if not (map_event.selection and map_event.selection.objects):
        return

    objects = map_event.selection.objects
    new_ids = None

    if objects.get("single-points"):
        new_ids = [objects["single-points"][0]["selected_id"]]
    elif objects.get("multi-points"):
        new_ids = objects["multi-points"][0]["ID"]

    if new_ids is None or new_ids == st.session_state.selected_ids:
        return

    valid   = set(map_df["ID"].astype(str))
    new_ids = [i for i in new_ids if str(i) in valid]

    st.session_state.selected_ids            = new_ids
    st.session_state.selected_case_dropdown  = new_ids[0] if new_ids else None


@st.fragment
def _render_case_detail(df: pd.DataFrame):
    """Detail panel for the currently selected map point(s)."""
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

    row_df = df[df["ID"].astype("string") == str(selected_id)]
    if row_df.empty:
        st.warning("No matching case found for the selected ID.")
        return

    row = row_df.iloc[0]

    with st.container(border=True):
        _detail_field("Employer",  row.get("Employer"))
        _detail_field("Date",      str(row.get("EventDate", ""))[:10] if pd.notna(row.get("EventDate")) else None)

        outcomes = [c for c in OUTCOME_COLS if row.get(c, 0) == 1]
        if outcomes:
            _detail_field("Outcomes", ", ".join(outcomes))

        _detail_field("Injury",    row.get("NatureTitle")          or row.get("Nature"))
        _detail_field("Body Part", row.get("Part of Body Title")   or row.get("Part of Body"))
        _detail_field("Cause",     row.get("EventTitle")           or row.get("Event"))
        _detail_field("Source",    row.get("SourceTitle")          or row.get("Source"))

        secondary = row.get("Secondary Source Title")
        if pd.notna(secondary) and str(secondary).strip() not in ("", "<NA>"):
            _detail_field("Source (Secondary)", secondary)

        naics = row.get("NAICS Sector")
        if pd.notna(naics) and str(naics).strip() not in ("", "Unknown"):
            _detail_field("Industry", f"{naics} ({row.get('Primary NAICS', '')})")

        _detail_field("Written Description", row.get("Final Narrative"))


def _detail_field(label: str, value):
    """Render a single labelled field in the case detail panel, skipping empty values."""
    if value is None:
        return
    value = str(value).strip()
    if value in ("", "nan", "<NA>", "N/A"):
        return
    st.markdown(f"**{label}:**")
    st.write(value)


def _render_overview_tab(df: pd.DataFrame):
    st.subheader("Cases by state")

    state_summary = data.summarize_by_state(df)
    if state_summary.empty:
        st.info("No state data available for the current filters.")
    else:
        st.altair_chart(charts.state_bar_chart(state_summary), use_container_width=True)
        with st.expander("Show state counts table"):
            st.dataframe(
                state_summary[["State", "Count"]],
                use_container_width=True,
                hide_index=True,
            )

    st.subheader("Top categories")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**Top Employers**")
        top_employers = data.top_counts(df, "Employer", top_n=10)
        if top_employers.empty:
            st.info("No employer data available.")
        else:
            st.altair_chart(charts.employer_bar_chart(top_employers), use_container_width=True)

    with col2:
        st.markdown("**Top Events**")
        top_events = data.top_code_title_counts(df, "Event", "EventTitle", top_n=10)
        if top_events.empty:
            st.info("No event data available.")
        else:
            st.altair_chart(charts.event_bar_chart(top_events), use_container_width=True)

    with col3:
        st.markdown("**Top Sources**")
        top_sources = data.top_code_title_counts(df, "Source", "SourceTitle", top_n=10)
        if top_sources.empty:
            st.info("No source data available.")
        else:
            st.altair_chart(charts.source_bar_chart(top_sources), use_container_width=True)


def _render_trends_tab(df: pd.DataFrame):

    # -- Time series --
    st.subheader("Cases over time")

    ts_left, ts_right = st.columns([3, 1])

    with ts_right:
        granularity = st.radio("Granularity", options=["Month", "Quarter", "Year"], index=1)
        show_outcomes = st.multiselect("Overlay outcomes", options=OUTCOME_COLS, default=[])

    time_df = data.build_time_series(df, granularity)

    with ts_left:
        if time_df.empty:
            st.info("No date data available for the current filters.")
        else:
            st.altair_chart(
                charts.time_series_chart(time_df, show_outcomes),
                use_container_width=True,
            )
            st.caption(
                "Solid blue = total cases. "
                + ("Dashed lines = selected outcome overlays."
                   if show_outcomes
                   else "Select outcomes above to overlay Hospitalized / Amputation / Loss of Eye.")
            )

    st.divider()

    # -- Outcome breakdown --
    st.subheader("Injury outcomes by state")

    ob_left, ob_right = st.columns([3, 1])

    with ob_right:
        dimension = st.radio("Break down by", options=["State", "NAICS Sector", "Employer"], index=0)
        top_n     = st.slider("Show top N", min_value=5, max_value=25, value=15)

    outcome_df = data.build_outcome_breakdown(df, dimension, top_n)

    with ob_left:
        if outcome_df.empty:
            st.info("No outcome data available for the current filters.")
        else:
            st.altair_chart(
                charts.outcome_breakdown_chart(outcome_df, dimension, top_n),
                use_container_width=True,
            )

    st.divider()

    # -- NAICS industry breakdown --
    st.subheader("Cases by industry (NAICS sector)")

    naics_df = data.build_naics_breakdown(df)
    if naics_df.empty:
        st.info("No NAICS data available for the current filters.")
    else:
        st.altair_chart(charts.naics_bar_chart(naics_df), use_container_width=True)

    st.divider()

    # -- CSV export --
    st.subheader("Export filtered data")

    export_cols = [
        "ID", "EventDate", "Employer", "State", "City",
        "Hospitalized", "Amputation", "Loss of Eye",
        "NatureTitle", "Part of Body Title", "EventTitle", "SourceTitle",
        "NAICS Sector", "Primary NAICS", "Final Narrative",
    ]
    export_cols = [c for c in export_cols if c in df.columns]
    export_df   = df[export_cols].copy()

    if "EventDate" in export_df.columns:
        export_df["EventDate"] = export_df["EventDate"].astype(str).str[:10]

    st.download_button(
        label=f"Download {len(df):,} filtered rows as CSV",
        data=export_df.to_csv(index=False).encode("utf-8"),
        file_name="osha_filtered_export.csv",
        mime="text/csv",
    )

    show_avg = st.checkbox("Show rolling average", value=True)
    time_df = data.build_time_series(df, granularity)
    time_df = data.add_rolling_average(time_df)

    st.altair_chart(
        charts.time_series_with_avg_chart(time_df, show_avg),
        use_container_width=True
    )


# ---------------------------------------------------------------------------
# Map
# ---------------------------------------------------------------------------

map_df = data.build_map_points(filtered_df)

if map_df.empty:
    st.warning("No rows match the current filters.")
    st.stop()

single_points, multi_points = map_utils.group_map_points(map_df)
annotated_states             = map_utils.annotate_state_geojson(states_json)
layers                       = map_utils.build_map_layers(annotated_states, single_points, multi_points)

deck = pdk.Deck(
    map_style="dark",
    initial_view_state=pdk.ViewState(
        latitude=39.8283,
        longitude=-98.5795,
        zoom=3.5,
        pitch=45,
    ),
    layers=layers,
    tooltip={"html": "<b>Entries:</b> {count}<br/><b>IDs:</b> {ID_text}"},
)

# ---------------------------------------------------------------------------
# Layout: map + detail panel
# ---------------------------------------------------------------------------

map_col, detail_col = st.columns([2.2, 1])

with map_col:
    st.write(f"Rows mapped: {len(map_df)}")
    map_event = st.pydeck_chart(
        deck,
        key="osha-map",
        on_select="rerun",
        selection_mode="single-object",
        width="stretch",
        height=700,
    )

_update_selection(map_event, map_df)

with detail_col:
    _render_case_detail(filtered_df)

# ---------------------------------------------------------------------------
# Analytics tabs
# ---------------------------------------------------------------------------

tab_overview, tab_trends = st.tabs(["Overview", "Trends & Industries"])

with tab_overview:
    _render_overview_tab(filtered_df)

with tab_trends:
    _render_trends_tab(filtered_df)
