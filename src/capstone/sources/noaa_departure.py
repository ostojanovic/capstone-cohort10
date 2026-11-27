"""NOAA's 7-day precipitation departure from normal, as a WMS layer from the National Weather Service.

Shows where the last 7 days were wetter or drier than the PRISM 30-year normal. NOAA updates it daily.
"""

import folium

from capstone.sources.base import Source

WMS_URL = "https://mapservices.weather.noaa.gov/raster/services/obs/rfc_qpe/MapServer/WMSServer"
LAYER = "99"  # "Last 7 Days Departure from Normal (inches)", the image layer (see the service's GetCapabilities)


def add_to_map(m: folium.Map, show: bool) -> None:
    folium.WmsTileLayer(
        url=WMS_URL,
        layers=LAYER,
        fmt="image/png",
        transparent=True,
        attr="NOAA / PRISM Climate Group (Oregon State University)",
        name="Wetter or drier than usual, last 7 days",
        overlay=True,
        show=show,
    ).add_to(m)


SOURCE = Source(
    id="noaa_departure",
    name="NOAA 7-Day Precipitation Departure from Normal",
    provider="NOAA National Weather Service / PRISM Climate Group",
    url=WMS_URL,
    access="Public WMS service",
    spatial_resolution="~4 km",
    temporal_coverage="Last 7 days (updated daily)",
    update_frequency="Daily",
    status="Active",
    license="Public Domain. Normal values calculated by PRISM Climate Group (Oregon State University 30-year average).",
    add_to_map=add_to_map,
)
