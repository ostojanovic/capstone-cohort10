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


# E) The provider publishes a table or time series (CSV, plain text or an API), e.g. an index with one value per
#    month. It is shown as a chart under the map instead of a map layer: delete add_to_map above, uncomment
#    load() and chart() below, and in SOURCE replace `add_to_map=add_to_map` with `chart=chart`.
#    Working example: roni.py. For an API with query parameters, see load() in streamflow.py.
#
# import pandas as pd
# import plotly.graph_objects as go
#
# URL = "https://.../data.csv"  # the file to download; for an API, the address without the part after "?"
#
#
# def load() -> pd.DataFrame:
#     """Download the data: one row per date. Also useful on its own in a notebook."""
#     df = pd.read_csv(URL)  # plain text with spaces between columns: pd.read_csv(URL, sep=r"\s+")
#     # For an API, put the query parameters in a dict, so others can see what is asked for:
#     # import io, requests
#     # response = requests.get(URL, params={"state": "Washington", "format": "csv"}, timeout=60)
#     # df = pd.read_csv(io.StringIO(response.text))
#     df["date"] = pd.to_datetime(df["date_column"])
#     return df.rename(columns={"value_column": "value"})[["date", "value"]]
#
#
# def chart() -> go.Figure:
#     """The chart shown under the map. The website sets the font, background and width, so only the data,
#     title and axis labels are needed here."""
#     df = load()
#     fig = go.Figure()
#     fig.add_scatter(x=df["date"], y=df["value"], mode="lines", name="Dataset name",
#                     hovertemplate="%{x|%b %Y}: %{y:.2f} units<extra></extra>")
#     fig.update_layout(title="Chart title", yaxis_title="Units", height=420)
#     return fig


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
    add_to_map=add_to_map,           # pattern E: chart=chart instead
    notes="Anything surprising: broken links, login problems, format quirks, planned changes",
)
