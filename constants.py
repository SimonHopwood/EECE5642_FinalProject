# NAICS 2-digit code to readable industry sector name
NAICS_SECTORS: dict[str, str] = {
    "11": "Agriculture, Forestry, Fishing",
    "21": "Mining, Quarrying, Oil & Gas",
    "22": "Utilities",
    "23": "Construction",
    "31": "Manufacturing",
    "32": "Manufacturing",
    "33": "Manufacturing",
    "42": "Wholesale Trade",
    "44": "Retail Trade",
    "45": "Retail Trade",
    "48": "Transportation & Warehousing",
    "49": "Transportation & Warehousing",
    "51": "Information",
    "52": "Finance & Insurance",
    "53": "Real Estate",
    "54": "Professional & Technical Services",
    "55": "Management of Companies",
    "56": "Administrative & Support Services",
    "61": "Educational Services",
    "62": "Health Care & Social Assistance",
    "71": "Arts, Entertainment & Recreation",
    "72": "Accommodation & Food Services",
    "81": "Other Services",
    "92": "Public Administration",
}

# States with historically lower OSHA federal jurisdiction activity.
# These are rendered in gray on the map and state breakdown chart;
# all others are rendered in blue.
LOW_PRIORITY_STATES: set[str] = {
    "California", "Oregon", "Washington", "Nevada", "Arizona", "New Mexico",
    "Utah", "Wyoming", "Minnesota", "Iowa", "Michigan", "Indiana", "Kentucky",
    "Tennessee", "North Carolina", "South Carolina", "Virginia", "Maryland",
    "Vermont", "Alaska", "Hawaii",
}

# Outcome columns present in the CSV, in display order
OUTCOME_COLS: list[str] = ["Hospitalized", "Amputation", "Loss of Eye"]

# Colors used consistently for each outcome across all charts
OUTCOME_COLORS: dict[str, str] = {
    "Hospitalized": "#e05c2a",
    "Amputation":   "#9b2335",
    "Loss of Eye":  "#6a0dad",
}