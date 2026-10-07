"""Landsat true-colour imagery as ready-made map tiles from NASA GIBS.

GIBS serves pre-rendered images: good as a visual background, but there are no data values behind them.
"""

import folium

from capstone.sources.base import Source

TILES = (
    "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/"
    "Landsat_WELD_CorrectedReflectance_TrueColor_Global_Annual/default/2010-12-01/"
    "GoogleMapsCompatible_Level12/{z}/{y}/{x}.jpg"
)


def add_to_map(m: folium.Map, show: bool) -> None:
    folium.TileLayer(
        tiles=TILES,
        attr="Landsat WELD (NASA GIBS)",
        name="Landsat imagery (2010 annual composite)",
        overlay=True,
        show=show,
        opacity=0.85,
        max_native_zoom=12,
        max_zoom=18,
    ).add_to(m)


SOURCE = Source(
    id="gibs_landsat",
    name="Landsat WELD true-colour annual composite",
    provider="NASA GIBS (imagery: USGS/NASA Landsat)",
    url="https://nasa-gibs.github.io/gibs-api-docs/",
    access="Tile service (WMTS), no login",
    spatial_resolution="30 m (shown up to zoom 12)",
    temporal_coverage="2010 annual composite",
    update_frequency="Static (historical product)",
    status="Active",
    license="NASA open data. Acknowledge NASA GIBS / ESDIS",
    add_to_map=add_to_map,
)
