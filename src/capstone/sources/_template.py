"""TEMPLATE for a new data source. Copy this file, rename it (e.g. `usdm_drought.py`) and fill it in.

Then register it in `sources/__init__.py` and add its id to a topic in `topics.py`.
See README.md in this folder for the step-by-step guide.
"""

import folium

from capstone.sources.base import Source


def add_to_map(m: folium.Map, show: bool) -> None:
    # Pick the pattern that fits how the provider publishes the data:

    # A) The provider has a map tile service (XYZ or WMTS): give folium the URL.
    folium.TileLayer(tiles="https://.../{z}/{x}/{y}.png", attr="Provider name", name="Layer name",
                     overlay=True, show=show).add_to(m)

    # B) The provider has a WMS service (common for USDA, NOAA, USGS): give folium the URL and layer name.
    # folium.WmsTileLayer(url="https://.../wms", layers="layer_name", fmt="image/png", transparent=True,
    #                     attr="Provider name", name="Layer name", overlay=True, show=show).add_to(m)

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
    id="my_source",                  # unique, lowercase, no spaces
    name="Dataset name",
    provider="Agency / organisation",
    url="https://...",               # landing page of the dataset
    access="e.g. Tile service, WMS, file download, API, earthaccess (NASA Earthdata login)",
    spatial_resolution="e.g. 30 m, 0.1°, county level",
    temporal_coverage="e.g. 2000–present, weekly",
    update_frequency="e.g. Weekly on Thursdays",
    status="e.g. Active, At risk, Migrating, Discontinued",
    license="Terms of use and how the provider wants to be cited",
    add_to_map=add_to_map,
    notes="Anything surprising: broken links, login problems, format quirks, planned changes",
)
