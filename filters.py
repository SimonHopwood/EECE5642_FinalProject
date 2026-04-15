import streamlit as st

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

_DEFAULT_FILTERS = {"nature": "", "part": "", "source": "", "event": ""}


def init_session_state():
    """Initialise all session state keys exactly once."""
    defaults = {
        "selected_ids": [],
        "selected_case_dropdown": None,
        "applied_filters": _DEFAULT_FILTERS.copy(),
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_applied_filters():
    return st.session_state.applied_filters


def clear_map_selection():
    st.session_state.selected_ids = []
    st.session_state.selected_case_dropdown = None


# ---------------------------------------------------------------------------
# Sidebar UI
# ---------------------------------------------------------------------------

def render_filter_sidebar():
    """Render the OIICS filter form in the sidebar.

    Calls st.rerun() when the user submits or clears filters,
    so callers do not need to handle that themselves.
    """
    with st.sidebar:
        st.header("OIICS Code Filters")
        st.caption("Enter OIICS codes directly, then click **Submit Filters**.")
        st.caption("Filters use prefix matching — entering `1` matches all codes starting with 1.")

        with st.form("oiics_filter_form"):
            current = st.session_state.applied_filters

            nature_input  = st.text_input("Nature",      value=current["nature"])
            part_input    = st.text_input("Part of Body", value=current["part"])
            source_input  = st.text_input("Source",      value=current["source"])
            event_input   = st.text_input("Event",       value=current["event"])

            col1, col2 = st.columns(2)
            submitted = col1.form_submit_button("Submit Filters", use_container_width=True)
            cleared   = col2.form_submit_button("Clear Filters",  use_container_width=True)

        if submitted:
            st.session_state.applied_filters = {
                "nature": nature_input.strip(),
                "part":   part_input.strip(),
                "source": source_input.strip(),
                "event":  event_input.strip(),
            }
            clear_map_selection()
            st.rerun()

        if cleared:
            st.session_state.applied_filters = _DEFAULT_FILTERS.copy()
            clear_map_selection()
            st.rerun()


# ---------------------------------------------------------------------------
# Filter status display
# ---------------------------------------------------------------------------

def render_filter_status(total_rows: int, filtered_rows: int):
    """Show active filter labels and the filtered/total row count."""
    applied = st.session_state.applied_filters

    active = []
    if applied["nature"]: active.append(f"Nature starts with **{applied['nature']}**")
    if applied["part"]:   active.append(f"Part of Body starts with **{applied['part']}**")
    if applied["source"]: active.append(f"Source starts with **{applied['source']}**")
    if applied["event"]:  active.append(f"Event starts with **{applied['event']}**")

    if active:
        st.caption("Active filters: " + " | ".join(active))

    pct = (filtered_rows / total_rows * 100) if total_rows > 0 else 0
    st.write(
        f"Rows after filtering: **{filtered_rows:,}** / {total_rows:,} "
        f"({pct:.2f}% of total)"
    )