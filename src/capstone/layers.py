"""Satellite tile layers from NASA GIBS (Global Imagery Browse Services).

GIBS is a free public tile service, see https://nasa-gibs.github.io/gibs-api-docs/
"""

import folium

GIBS_URL = "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/"


def landsat(show: bool = False) -> folium.TileLayer:
    """Landsat WELD true-colour annual composite (2010)."""
    return folium.TileLayer(
        tiles=GIBS_URL
        + "Landsat_WELD_CorrectedReflectance_TrueColor_Global_Annual/default/2010-12-01/"
        "GoogleMapsCompatible_Level12/{z}/{y}/{x}.jpg",
        attr="Landsat WELD (NASA GIBS)",
        name="Landsat imagery (2010 annual composite)",
        overlay=True,
        show=show,
        opacity=0.85,
        max_native_zoom=12,
        max_zoom=18,
    )


def precipitation(show: bool = False) -> folium.TileLayer:
    """IMERG precipitation rate (most recent available)."""
    return folium.TileLayer(
        tiles=GIBS_URL
        + "IMERG_Precipitation_Rate/default/default/GoogleMapsCompatible_Level6/{z}/{y}/{x}.png",
        attr="IMERG precipitation (NASA GIBS)",
        name="Precipitation rate (IMERG)",
        overlay=True,
        show=show,
        opacity=0.7,
        max_native_zoom=6,
        max_zoom=18,
    )
