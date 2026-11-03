"""TEMPLATE for a new data source. Copy this file, rename it (e.g. `usdm_drought.py`) and fill it in.

Then register it in `sources/__init__.py` and add its id to a topic in `topics.py`.
See README.md in this folder for the step-by-step guide.
"""

import folium

from capstone.sources.base import Source


def add_to_map(m: folium.Map, show: bool) -> None:
    # Pick the pattern that fits how the provider publishes the data:

    # A) The provider has a map tile service (XYZ or WMTS): give folium the URL.
    #folium.TileLayer(tiles="https://.../{z}/{x}/{y}.png", attr="Provider name", name="Layer name",
      #               overlay=True, show=show).add_to(m)

    # B) The provider has a WMS service (common for USDA, NOAA, USGS): give folium the URL and layer name.
    folium.WmsTileLayer(url="https://mapservices.weather.noaa.gov/raster/services/obs/rfc_qpe/MapServer/WMSServer",
                        layers="99",
                        fmt="image/png",
                        transparent=True,
                        attr="NOAA / PRISM Climate Group (Oregon State University)",
                        name="Wetter or drier than usual, last 7 days",
                        overlay=True,
                        show=show,
    ).add_to(m)

    # C) The provider has vector files (GeoJSON, shapefile): load with geopandas and draw the shapes.
    # import geopandas as gpd
    # gdf = gpd.read_file("https://.../data.geojson")
    # folium.GeoJson(gdf, name="Layer name", show=show).add_to(m)

    # D) NASA Earthdata (needs login): download with earthaccess, open with xarray, draw as a coloured image.
    # import xarray as xr
    # from capstone import earthdata
    # [path] = earthdata.download("SHORT_NAME", "VERSION", temporal=("2023-12-01", "2023-12-31"))
    # with xr.open_dataset(path) as ds:
    #     values = ds["variable"].isel(time=0)
    # earthdata.add_raster(m, values, name="Layer name", caption="Units", cmap="viridis", show=show)


SOURCE = Source(
    id="noaa_departure",                  # unique, lowercase, no spaces
    name="NOAA 7-Day Precipitation Departure from Normal",
    provider="NOAA National Weather Service / PRISM Climate Group",
    url="https://mapservices.weather.noaa.gov/raster/services/obs/rfc_qpe/MapServer/WMSServer",               # landing page of the dataset
    access="Public WMS service",
    spatial_resolution="~4 km",
    temporal_coverage="Last 7 days (updated daily)",
    update_frequency="Daily",
    status="Active",
    license="Public Domain. Normal values calculated by PRISM Climate Group (Oregon State University 30-year average).",
    add_to_map=add_to_map,
    notes="Anything surprising: broken links, login problems, format quirks, planned changes",
)
