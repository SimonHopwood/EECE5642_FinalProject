import json
import pandas as pd
import streamlit as st

from constants import NAICS_SECTORS, OUTCOME_COLS

# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------
@st.cache_data
def load_injury_data():
    """Load and pre-process the OSHA severe injury CSV.

    Performs all one-time type coercions so downstream code can assume:
    - String columns are clean str/StringDtype without leading/trailing spaces.
    - EventDate is a parsed datetime (NaT else).
    - Outcome columns (Hospitalized, Amputation, Loss of Eye) are int (0/1).
    - NAICS2 and NAICS Sector columns are derived from Primary NAICS.
    """
    df = pd.read_csv("January2015toAugust2025.csv")

    _clean_string_columns(df, [
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
         "FederalState",
    ])

    _parse_dates(df)
    _coerce_outcome_flags(df)
    _derive_naics_sector(df)

    return df


@st.cache_data
def load_state_boundaries():
    """Load US state boundary GeoJSON."""
    with open("StateBoundryData.json", "r") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------

def apply_prefix_filters(
    df: pd.DataFrame,
    nature: str = "",
    part: str = "",
    source: str = "",
    event: str = "",
):
    """Return a filtered copy of df using OIICS prefix matching on each field."""
    df = _apply_prefix_filter(df, "Nature", nature)
    df = _apply_prefix_filter(df, "Part of Body", part)
    df = _apply_prefix_filter(df, "Source", source)
    df = _apply_prefix_filter(df, "Event", event)
    return df


# ---------------------------------------------------------------------------
# Summary builders
# ---------------------------------------------------------------------------

def summarize_by_state(df: pd.DataFrame):
    """Return a (State, Count) dataframe sorted descending by count."""
    if "State" not in df.columns:
        return pd.DataFrame(columns=["State", "Count"])

    return (
        df["State"]
        .dropna()
        .loc[lambda s: s != ""]
        .value_counts()
        .reset_index(name="Count")
        .rename(columns={"index": "State"})
    )


def top_counts(df: pd.DataFrame, column: str, top_n: int = 10):
    """Return the top N most frequent values for a single column."""
    if column not in df.columns:
        return pd.DataFrame(columns=[column, "Count"])

    return (
        df[column]
        .dropna()
        .loc[lambda s: s.astype(str).str.strip() != ""]
        .value_counts()
        .head(top_n)
        .reset_index(name="Count")
        .rename(columns={"index": column})
    )


def top_code_title_counts(
    df: pd.DataFrame,
    code_col: str,
    title_col: str,
    top_n: int = 10,
):
    """Return top N (code, title, count) rows, with a combined Label column."""
    missing = [c for c in [code_col, title_col] if c not in df.columns]
    if missing:
        return pd.DataFrame(columns=[code_col, title_col, "Label", "Count"])

    result = (
        df[[code_col, title_col]]
        .dropna()
        .loc[lambda d: (d[code_col].str.strip() != "") & (d[title_col].str.strip() != "")]
        .value_counts()
        .head(top_n)
        .reset_index(name="Count")
    )
    result["Label"] = result[title_col]
    return result


def build_time_series(df: pd.DataFrame, granularity: str = "Quarter"):
    """Aggregate case counts and outcome totals by time period.

    Args:
        granularity: One of "Month", "Quarter", or "Year".

    Returns:
        DataFrame with columns: Period, Total Cases, Hospitalized, Amputation, Loss of Eye.
    """
    if "EventDate" not in df.columns:
        return pd.DataFrame()

    freq_map = {"Month": "M", "Quarter": "Q", "Year": "Y"}
    freq = freq_map.get(granularity, "Q")

    period_col = df["EventDate"].dt.to_period(freq).dt.to_timestamp()
    df = df.copy()
    df["Period"] = period_col
    df = df.dropna(subset=["Period"])

    present_outcomes = [c for c in OUTCOME_COLS if c in df.columns]
    agg = {"ID": "count", **{c: "sum" for c in present_outcomes}}

    return (
        df.groupby("Period")
        .agg(agg)
        .reset_index()
        .rename(columns={"ID": "Total Cases"})
    )


def build_outcome_breakdown(
    df: pd.DataFrame,
    dimension: str = "State",
    top_n: int = 15,
):
    """Return a melted dataframe of outcome counts grouped by a dimension.

    Suitable for a stacked/grouped bar chart.
    """
    present_outcomes = [c for c in OUTCOME_COLS if c in df.columns]
    if dimension not in df.columns or not present_outcomes:
        return pd.DataFrame()

    summary = (
        df[[dimension] + present_outcomes]
        .dropna(subset=[dimension])
        .loc[lambda d: d[dimension].astype(str).str.strip() != ""]
        .groupby(dimension)[present_outcomes]
        .sum()
        .reset_index()
    )
    summary["_total"] = summary[present_outcomes].sum(axis=1)
    summary = summary.nlargest(top_n, "_total").drop(columns="_total")

    return summary.melt(
        id_vars=[dimension],
        value_vars=present_outcomes,
        var_name="Outcome",
        value_name="Count",
    )


def build_naics_breakdown(df: pd.DataFrame, top_n: int = 15):
    """Return top N industry sectors by case count."""
    if "NAICS Sector" not in df.columns:
        return pd.DataFrame()

    return (
        df["NAICS Sector"]
        .loc[lambda s: s != "Unknown"]
        .dropna()
        .value_counts()
        .head(top_n)
        .reset_index(name="Count")
        .rename(columns={"index": "NAICS Sector"})
    )


def build_map_points(df: pd.DataFrame):
    """Get and clean lat/lon/ID columns for map rendering."""
    map_df = (
        df[["Latitude", "Longitude", "ID"]]
        .rename(columns={"Latitude": "lat", "Longitude": "lon"})
        .copy()
    )
    map_df["lat"] = pd.to_numeric(map_df["lat"], errors="coerce")
    map_df["lon"] = pd.to_numeric(map_df["lon"], errors="coerce")
    map_df["ID"] = map_df["ID"].astype("string")
    return map_df.dropna(subset=["lat", "lon", "ID"])

def add_rolling_average(time_df: pd.DataFrame, window: int = 3):
    if "Total Cases" not in time_df.columns:
        return time_df
    df = time_df.copy()
    df["Rolling Avg"] = df["Total Cases"].rolling(window=window).mean()
    return df


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _clean_string_columns(df: pd.DataFrame, columns: list[str]):
    for col in columns:
        if col in df.columns:
            df[col] = df[col].astype("string").str.strip()


def _parse_dates(df: pd.DataFrame):
    if "EventDate" not in df.columns:
        return
    df["EventDate"] = pd.to_datetime(df["EventDate"], format="mixed", errors="coerce")


def _coerce_outcome_flags(df: pd.DataFrame):
    for col in OUTCOME_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)


def _derive_naics_sector(df: pd.DataFrame):
    if "Primary NAICS" not in df.columns:
        return
    df["Primary NAICS"] = df["Primary NAICS"].astype("string").str.strip()
    df["NAICS2"] = df["Primary NAICS"].str[:2]
    df["NAICS Sector"] = df["NAICS2"].map(NAICS_SECTORS).fillna("Unknown")


def _apply_prefix_filter(df: pd.DataFrame, column: str, prefix: str):
    if not prefix or column not in df.columns:
        return df
    prefix = prefix.strip()
    if not prefix:
        return df
    mask = df[column].astype("string").str.strip().str.startswith(prefix, na=False)
    return df[mask]