"""IMERG precipitation rate as ready-made map tiles from NASA GIBS (most recent available)."""

import folium

from capstone.sources.base import Source

TILES = (
    "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/"
    "IMERG_Precipitation_Rate/default/default/GoogleMapsCompatible_Level6/{z}/{y}/{x}.png"
)


def add_to_map(m: folium.Map, show: bool) -> None:
    folium.TileLayer(
        tiles=TILES,
        attr="IMERG precipitation (NASA GIBS)",
        name="Precipitation rate, latest (IMERG)",
        overlay=True,
        show=show,
        opacity=0.7,
        max_native_zoom=6,
        max_zoom=18,
    ).add_to(m)


SOURCE = Source(
    id="gibs_imerg_rate",
    name="IMERG precipitation rate (latest)",
    provider="NASA GIBS (data: NASA GPM)",
    url="https://nasa-gibs.github.io/gibs-api-docs/",
    access="Tile service (WMTS), no login",
    spatial_resolution="0.1° (~10 km)",
    temporal_coverage="Near real-time",
    update_frequency="Every 30 minutes",
    status="Active",
    license="NASA open data. Acknowledge NASA GIBS / ESDIS",
    add_to_map=add_to_map,
)
