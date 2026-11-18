"""NOAA PSL's Climate Indices list: about 40 monthly climate index time series in one simple text format.

Shown as one small map, "where is the warm water?": how much warmer or cooler than normal the sea surface
was in the Niño regions in the latest month. read_psl() reads PSL's file format and is also used by mei_v2.py.
"""

import math

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
from plotly.colors import sample_colorscale

from capstone.sources.base import Source

BASE_URL = "https://psl.noaa.gov/data/correlation/"  # one file per index, e.g. nina34.anom.data, soi.data

# name: (file, box as (west, east, south, north) with longitudes in °E from 0 to 360 so 150°W = 210, description)
REGIONS = {
    "Niño 4": ("nina4.anom.data", (160, 210, -5, 5), "Central Pacific"),
    "Niño 3": ("nina3.anom.data", (210, 270, -5, 5), "Eastern Pacific"),
    "Niño 1+2": ("nina1.anom.data", (270, 280, -10, 0), "Off Peru and Ecuador, where El Niño was first noticed"),
    "Niño 3.4": ("nina34.anom.data", (190, 240, -5, 5), "NOAA's main El Niño region, which RONI is based on"),
}
FILLED = ["Niño 4", "Niño 3", "Niño 1+2"]  # side by side along the equator. Niño 3.4 overlaps two, so it's outlined
PLACES = {"Australia": (-24, 134), "Indonesia": (-8, 118), "Hawaii": (22, -157), "South America": (-24, -58)}


def read_psl(url: str) -> pd.Series:
    """Read a file in PSL's time series format into a monthly series, dated mid-month, without missing months.

    The format: a line with the first and last year, one line per year (the year, then 12 monthly values),
    then a line with the number used for missing values. Anything after that is a description.
    """
    lines = requests.get(url, timeout=60).text.splitlines()
    first, last = (int(x) for x in lines[0].split()[:2])
    n_years = last - first + 1
    missing = float(lines[1 + n_years].split()[0])
    values = {
        pd.Timestamp(int(row[0]), month, 15): float(value)
        for row in (line.split() for line in lines[1 : 1 + n_years])
        for month, value in enumerate(row[1:13], start=1)
    }
    series = pd.Series(values)
    return series[~np.isclose(series, missing)]


def outline(box: tuple, step: float = 1.0) -> tuple[list, list]:
    """Clockwise outline of a box (the map fills the inside only when drawn clockwise), with a point every
    degree so the edges follow the lines of latitude and longitude instead of bending."""
    w, e, s, n = box
    points = ([(w, y) for y in np.arange(s, n, step)] + [(x, n) for x in np.arange(w, e, step)]
              + [(e, y) for y in np.arange(n, s, -step)] + [(x, s) for x in np.arange(e, w, -step)] + [(w, s)])
    return [(x + 180) % 360 - 180 for x, _ in points], [y for _, y in points]


def place(box: tuple) -> str:
    """A box as text, e.g. 5°N–5°S, 160°E–150°W."""
    w, e, s, n = box
    lat = lambda y: f"{abs(y):g}°{'N' if y > 0 else 'S' if y < 0 else ''}"  # noqa: E731
    lon = lambda x: f"{x:g}°E" if x <= 180 else f"{360 - x:g}°W"  # noqa: E731
    return f"{lat(n)}–{lat(s)}, {lon(w)}–{lon(e)}"


def chart() -> go.Figure:
    """Map of the tropical Pacific: each Niño region coloured by how much warmer or cooler than normal it was."""
    series = {name: read_psl(BASE_URL + file) for name, (file, _, _) in REGIONS.items()}
    month = min(s.index.max() for s in series.values())  # latest month that every region has
    values = {name: s.loc[:month].iloc[-1] for name, s in series.items()}
    limit = max(2, math.ceil(max(abs(v) for v in values.values())))  # same scale either side of 0

    def colour(v: float) -> str:
        return sample_colorscale("RdBu_r", [(v + limit) / (2 * limit)])[0]

    fig = go.Figure()
    fig.add_scattergeo(  # the equator, for orientation
        lon=list(range(-180, 181)), lat=[0] * 361, mode="lines", line=dict(color="#cccccc", width=1, dash="dot"),
        hoverinfo="skip",
    )
    for name in FILLED:
        _, box, _ = REGIONS[name]
        lon, lat = outline(box)
        fig.add_scattergeo(lon=lon, lat=lat, mode="lines", fill="toself", fillcolor=colour(values[name]),
                           line=dict(color="#888888", width=1), hoverinfo="skip")
    lon, lat = outline(REGIONS["Niño 3.4"][1])
    fig.add_scattergeo(lon=lon, lat=lat, mode="lines", line=dict(color="#333333", width=2, dash="dash"),
                       hoverinfo="skip")

    labels = {  # where each label goes, just outside its box so it fits on any screen: (lat, lon in °E)
        "Niño 4": (-9, 178), "Niño 3": (-9, 238), "Niño 1+2": (-14, 279), "Niño 3.4": (9, 215),
    }
    for name, (lat, lon) in labels.items():
        _, box, description = REGIONS[name]
        v = values[name]
        text = f"<b>{name}</b> {v:+.1f} °C" if name != "Niño 3.4" else f"<b>Niño 3.4</b> (RONI's region) {v:+.1f} °C"
        fig.add_scattergeo(
            lon=[(lon + 180) % 360 - 180], lat=[lat], mode="text", text=[text],
            textfont=dict(color="#222222", size=12),
            hovertext=[f"<b>{name}</b>: {abs(v):.2f} °C {'warmer' if v >= 0 else 'cooler'} than average "
                       f"({month:%b %Y})<br>{description}<br>{place(box)}"],
            hoverinfo="text",
        )
    fig.add_scattergeo(
        lon=[lon for _, lon in PLACES.values()], lat=[lat for lat, _ in PLACES.values()], mode="text",
        text=list(PLACES), textfont=dict(color="#999999", size=11), hoverinfo="skip",
    )
    fig.add_scattergeo(  # invisible point, only to draw the colour key
        lon=[0], lat=[0], mode="markers", hoverinfo="skip",
        marker=dict(size=0, opacity=0, color=[0], colorscale="RdBu_r", cmin=-limit, cmax=limit, showscale=True,
                    colorbar=dict(title=dict(text="Difference from average (°C)", side="top"), orientation="h",
                              x=0.5, xanchor="center", y=-0.02, yanchor="top", len=0.45, thickness=10)),
    )

    fig.update_geos(
        projection_type="equirectangular", projection_rotation_lon=-150, lonaxis_range=[-270, -30],
        lataxis_range=[-28, 28], showland=True, landcolor="#ececec", coastlinecolor="#bbbbbb",
        showocean=False, showframe=False,
    )
    fig.update_layout(
        title=f"Where Is the Warm Water?<br><sup>How much warmer or cooler than average the ocean surface was in "
              f"{month:%B %Y}<br>Source: Niño region indices, NOAA PSL Climate Indices</sup>",
        height=360, showlegend=False, margin=dict(t=80, b=60, l=10, r=10),
    )
    return fig


SOURCE = Source(
    id="psl_indices",
    name="Climate Indices: Monthly Atmospheric and Ocean Time Series",
    provider="NOAA Physical Sciences Laboratory (PSL)",
    url="https://psl.noaa.gov/data/climateindices/list/",
    access="Plain text file download per index, no login",
    spatial_resolution="Single indices; the region differs per index",
    temporal_coverage="1948 (some earlier)–present, monthly",
    update_frequency="Monthly for indices marked * on the list; others irregularly or not at all",
    status="Active",
    license="NOAA open data. Credit NOAA PSL and the original provider of each index (e.g. NOAA CPC)",
    chart=chart,
    notes=(
        "About 40 monthly index series in one simple text format, one file per index: ENSO (Niño 1+2, 3, 3.4 "
        "and 4 sea surface temperature anomalies, ONI, MEI v2, SOI, BEST, TNI), NAO, PDO, AO, Atlantic SST and "
        "some regional rainfall. Only the indices marked * on the list are updated regularly; the four Niño "
        "regions and the SOI are among them. The map on the El Niño tab uses the four Niño regions."
    ),
)
