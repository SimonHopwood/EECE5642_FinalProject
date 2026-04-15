import altair as alt
import pandas as pd

from constants import LOW_PRIORITY_STATES, OUTCOME_COLORS


# ---------------------------------------------------------------------------
# Overview tab
# ---------------------------------------------------------------------------

def state_bar_chart(state_summary: pd.DataFrame):
    """Horizontal bar chart of cases per state, gray for low-priority states."""
    low_priority_upper = {s.upper() for s in LOW_PRIORITY_STATES}

    df = state_summary.copy()
    df["Low Priority"] = df["State"].str.upper().isin(low_priority_upper)

    return (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X("Count:Q", title="Case Count"),
            y=alt.Y("State:N", sort="-x", title="State"),
            color=alt.condition(
                alt.datum["Low Priority"],
                alt.value("#b4b4b4"),
                alt.value("#4169e1"),
            ),
            tooltip=[alt.Tooltip("State:N"), alt.Tooltip("Count:Q")],
        )
        .properties(height=900)
    )


def employer_bar_chart(top_employers: pd.DataFrame):
    return (
        alt.Chart(top_employers)
        .mark_bar()
        .encode(
            x=alt.X("Count:Q", title="Case Count"),
            y=alt.Y("Employer:N", sort="-x", title="Employer"),
            tooltip=[alt.Tooltip("Employer:N"), alt.Tooltip("Count:Q")],
        )
        .properties(height=350)
    )


def event_bar_chart(top_events: pd.DataFrame):
    return (
        alt.Chart(top_events)
        .mark_bar()
        .encode(
            x=alt.X("Count:Q", title="Case Count"),
            y=alt.Y("Label:N", sort="-x", title="Event"),
            tooltip=[
                alt.Tooltip("Label:N", title="Event"),
                alt.Tooltip("Event:N", title="OIICS Code"),
                alt.Tooltip("Count:Q"),
            ],
        )
        .properties(height=350)
    )


def source_bar_chart(top_sources: pd.DataFrame):
    return (
        alt.Chart(top_sources)
        .mark_bar()
        .encode(
            x=alt.X("Count:Q", title="Case Count"),
            y=alt.Y("Label:N", sort="-x", title="Source"),
            tooltip=[
                alt.Tooltip("Label:N", title="Source"),
                alt.Tooltip("Source:N", title="OIICS Code"),
                alt.Tooltip("Count:Q"),
            ],
        )
        .properties(height=350)
    )


# ---------------------------------------------------------------------------
# Trends & Industries tab
# ---------------------------------------------------------------------------

def time_series_chart(
    time_df: pd.DataFrame,
    show_outcomes: list[str],
):
    """Line chart of total cases over time with optional outcome overlays.

    Args:
        time_df:       Output of data.build_time_series().
        show_outcomes: Subset of OUTCOME_COLS to overlay as dashed lines.
    """
    base = alt.Chart(time_df).encode(x=alt.X("Period:T", title="Date"))

    total_line = base.mark_line(color="#4169e1", strokeWidth=2).encode(
        y=alt.Y("Total Cases:Q", title="Cases"),
        tooltip=[
            alt.Tooltip("Period:T", title="Period"),
            alt.Tooltip("Total Cases:Q"),
        ],
    )

    outcome_lines = [
        base.mark_line(strokeDash=[4, 2], strokeWidth=1.5, color=OUTCOME_COLORS[outcome]).encode(
            y=alt.Y(f"{outcome}:Q"),
            tooltip=[
                alt.Tooltip("Period:T", title="Period"),
                alt.Tooltip(f"{outcome}:Q", title=outcome),
            ],
        )
        for outcome in show_outcomes
        if outcome in time_df.columns
    ]

    return alt.layer(total_line, *outcome_lines).properties(height=350)

def time_series_with_avg_chart(time_df: pd.DataFrame, show_avg: bool):
    base = alt.Chart(time_df).encode(x="Period:T")

    total = base.mark_line().encode(
        y="Total Cases:Q",
        tooltip=["Period:T", "Total Cases:Q"]
    )

    if show_avg and "Rolling Avg" in time_df.columns:
        avg = base.mark_line(strokeDash=[5, 5]).encode(
            y="Rolling Avg:Q"
        )
        return alt.layer(total, avg)

    return total

def outcome_breakdown_chart(
    outcome_df: pd.DataFrame,
    dimension: str,
    top_n: int,
):
    """Stacked bar chart of injury outcomes broken down by a dimension."""
    return (
        alt.Chart(outcome_df)
        .mark_bar()
        .encode(
            x=alt.X("Count:Q", title="Cases"),
            y=alt.Y(f"{dimension}:N", sort="-x", title=dimension),
            color=alt.Color(
                "Outcome:N",
                scale=alt.Scale(
                    domain=list(OUTCOME_COLORS.keys()),
                    range=list(OUTCOME_COLORS.values()),
                ),
            ),
            tooltip=[
                alt.Tooltip(f"{dimension}:N"),
                alt.Tooltip("Outcome:N"),
                alt.Tooltip("Count:Q"),
            ],
        )
        .properties(height=max(350, top_n * 22))
    )


def naics_bar_chart(naics_df: pd.DataFrame):
    return (
        alt.Chart(naics_df)
        .mark_bar(color="#4169e1")
        .encode(
            x=alt.X("Count:Q", title="Case Count"),
            y=alt.Y("NAICS Sector:N", sort="-x", title="Industry Sector"),
            tooltip=[
                alt.Tooltip("NAICS Sector:N", title="Sector"),
                alt.Tooltip("Count:Q", title="Cases"),
            ],
        )
        .properties(height=400)
    )