"""IMERG monthly precipitation, downloaded from NASA Earthdata with earthaccess.

Example of a source with real data values: we download the file, select the US and draw it as a coloured image.
Needs an Earthdata login (see CONTRIBUTING.md, section 2.4).
"""

import folium
import xarray as xr

from capstone import earthdata
from capstone.sources.base import Source

MONTH = "2023-12"  # winter of the strong 2023/24 El Niño


def add_to_map(m: folium.Map, show: bool) -> None:
    [path] = earthdata.download("GPM_3IMERGM", "07", temporal=(f"{MONTH}-01", f"{MONTH}-28"))
    with xr.open_dataset(path, engine="h5netcdf", group="Grid") as ds:
        precip = ds["precipitation"].isel(time=0) * 24  # mm/hour -> mm/day
    earthdata.add_raster(
        m, precip, name=f"Precipitation, monthly mean {MONTH} (IMERG)",
        caption="Precipitation (mm/day)", cmap="Blues", vmin=0, vmax=8, show=show,
    )


SOURCE = Source(
    id="imerg_monthly",
    name="GPM IMERG Final Precipitation L3 Monthly (GPM_3IMERGM v07)",
    provider="NASA GES DISC",
    url="https://disc.gsfc.nasa.gov/datasets/GPM_3IMERGM_07/summary",
    access="earthaccess (NASA Earthdata login)",
    spatial_resolution="0.1° (~10 km)",
    temporal_coverage="1998–present, monthly",
    update_frequency="Monthly, ~3–4 months delay",
    status="Active",
    license="NASA open data. Cite: Huffman et al., GPM IMERG Final Precipitation L3 Monthly, V07, GES DISC",
    add_to_map=add_to_map,
)
