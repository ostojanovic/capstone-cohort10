"""Relative Oceanic Niño Index (RONI) from NOAA's Climate Prediction Center.

NOAA's main index for tracking El Niño and La Niña since February 2026. It is one number per 3-month
season, not a grid, so it is drawn as a timeline chart instead of a map layer. Plain text file, no login.
"""

import pandas as pd
import plotly.graph_objects as go

from capstone.sources.base import Source

URL = "https://www.cpc.ncep.noaa.gov/data/indices/RONI.ascii.txt"
SEASONS = ["DJF", "JFM", "FMA", "MAM", "AMJ", "MJJ", "JJA", "JAS", "ASO", "SON", "OND", "NDJ"]
THRESHOLD = 0.5        # °C. Above +0.5 is a warm (El Niño) season, below -0.5 a cold (La Niña) season
HIGHLIGHT_YEAR = 2026
COLOURS = {"Warm (≥ +0.5 °C)": "#c0392b", "Neutral": "#b0b0b0", "Cold (≤ −0.5 °C)": "#2471a3"}


def load() -> pd.DataFrame:
    """Download RONI: one row per 3-month season, dated by its middle month (DJF 1950 = January 1950)."""
    df = pd.read_csv(URL, sep=r"\s+")  # columns: SEAS, YR, ANOM
    df["month"] = df["SEAS"].map({season: i + 1 for i, season in enumerate(SEASONS)})
    df["date"] = pd.to_datetime(pd.DataFrame({"year": df["YR"], "month": df["month"], "day": 15}))
    return df.rename(columns={"SEAS": "season", "YR": "year", "ANOM": "anomaly"})[
        ["date", "season", "year", "anomaly"]
    ]


def chart() -> go.Figure:
    """Timeline of RONI from 1950 to the latest season, with the highlighted year shaded."""
    df = load()
    df["phase"] = "Neutral"
    df.loc[df["anomaly"] >= THRESHOLD, "phase"] = "Warm (≥ +0.5 °C)"
    df.loc[df["anomaly"] <= -THRESHOLD, "phase"] = "Cold (≤ −0.5 °C)"

    fig = go.Figure()
    for phase, colour in COLOURS.items():
        part = df[df["phase"] == phase]
        fig.add_bar(
            x=part["date"], y=part["anomaly"], name=phase, marker_color=colour, marker_line_width=0,
            customdata=part[["season", "year"]],
            hovertemplate="%{customdata[0]} %{customdata[1]}: %{y:+.2f} °C<extra></extra>",
        )
    for y in (THRESHOLD, -THRESHOLD):
        fig.add_hline(y=y, line_dash="dot", line_color="grey", line_width=1)

    fig.add_vrect(
        x0=f"{HIGHLIGHT_YEAR}-01-01", x1=f"{HIGHLIGHT_YEAR}-12-31", fillcolor="#f5b041", opacity=0.6,
        line_width=0, layer="below", annotation_text=str(HIGHLIGHT_YEAR), annotation_position="top left",
    )
    first, last = df.iloc[0], df.iloc[-1]
    fig.update_layout(
        title=f"Relative Oceanic Niño Index (RONI), {first['season']} {first['year']} to "
              f"{last['season']} {last['year']}",
        yaxis_title="Anomaly (°C)", bargap=0, height=420,
        legend=dict(orientation="h", y=-0.15), margin=dict(t=60, b=40),
    )
    return fig


SOURCE = Source(
    id="roni",
    name="Relative Oceanic Niño Index (RONI) v6",
    provider="NOAA Climate Prediction Center (CPC)",
    url="https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/roni/",
    access="Plain text file download, no login",
    spatial_resolution="Single index for the Niño 3.4 region (5°N–5°S, 120°–170°W)",
    temporal_coverage="1950–present, 3-month running seasons",
    update_frequency="Monthly, by the 5th of each month",
    status="Active",
    license="NOAA open data. Credit: NOAA Climate Prediction Center",
    chart=chart,
    notes=(
        "NOAA's main ENSO index since February 2026. It replaced the Oceanic Niño Index (ONI), which is still "
        "updated: https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso/oni/v6/. Calculated from "
        "ERSST v6. RONI v5 is also available. Recent values can change for up to two months after they are "
        "first posted."
    ),
)
