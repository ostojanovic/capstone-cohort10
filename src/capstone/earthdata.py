"""Helpers for NASA Earthdata via the earthaccess library.

Downloading needs a free Earthdata login, stored in the `.env` file (see CONTRIBUTING.md, section 2.4).
Files are kept in data/raw/, so each file is only downloaded once.

Check that your login works with:  python -m capstone.earthdata
"""

from pathlib import Path

import branca.colormap
import earthaccess
import folium
import numpy as np
import xarray as xr
from dotenv import load_dotenv
from matplotlib import colormaps
from matplotlib.colors import Normalize, to_hex

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "raw"
CONUS_BBOX = (-125.0, 24.0, -66.0, 50.0)  # west, south, east, north


class EarthdataLoginMissing(RuntimeError):
    """Raised when a download is needed but no Earthdata login is set up on this computer."""


def login() -> None:
    """Log in with the details from `.env` (or ~/.netrc). Never prompts, so a website build can't hang."""
    load_dotenv(ROOT / ".env")
    for strategy in ("environment", "netrc"):
        try:
            earthaccess.login(strategy=strategy)
            return
        except earthaccess.exceptions.LoginStrategyUnavailable:
            continue
    raise EarthdataLoginMissing(
        "No NASA Earthdata login found. See CONTRIBUTING.md, section 2.4."
    )


def download(short_name: str, version: str, temporal: tuple[str, str],
             bounding_box: tuple[float, float, float, float] = CONUS_BBOX) -> list[Path]:
    """Search a NASA dataset and download the matching files into data/raw/<short_name>.<version>/.

    `short_name` and `version` are on the dataset's page at https://search.earthdata.nasa.gov.
    Files that are already downloaded are reused, without logging in.
    """
    folder = DATA_DIR / f"{short_name}.{version}"
    granules = earthaccess.search_data(
        short_name=short_name, version=version, temporal=temporal, bounding_box=bounding_box
    )
    if not granules:
        raise ValueError(f"No {short_name} v{version} files found for {temporal}")

    paths = [folder / Path(g.data_links()[0]).name for g in granules]
    missing = [g for g, p in zip(granules, paths) if not p.exists()]
    if missing:
        login()
        earthaccess.download(missing, local_path=str(folder))
    return paths


def add_raster(m: folium.Map, data: xr.DataArray, name: str, caption: str, cmap: str = "viridis",
               vmin: float | None = None, vmax: float | None = None, show: bool = True,
               opacity: float = 0.7, bounds: tuple[float, float, float, float] = CONUS_BBOX) -> None:
    """Draw a 2D lat/lon grid on the map as a coloured image, with a colour legend.

    `data` must have latitude and longitude coordinates (named lat/lon or latitude/longitude).
    Missing values (NaN) are transparent.
    """
    data = data.rename({k: v for k, v in {"latitude": "lat", "longitude": "lon"}.items() if k in data.dims})
    west, south, east, north = bounds
    data = data.sortby("lat", ascending=False).sortby("lon")   # images are drawn top (north) to bottom
    data = data.sel(lat=slice(north, south), lon=slice(west, east)).transpose("lat", "lon")

    values = data.values.astype(float)
    vmin = np.nanmin(values) if vmin is None else vmin
    vmax = np.nanmax(values) if vmax is None else vmax
    colours = colormaps[cmap](Normalize(vmin, vmax, clip=True)(values))
    colours[np.isnan(values), 3] = 0  # transparent where there is no data

    half = abs(float(data.lat[0] - data.lat[1])) / 2 if data.sizes["lat"] > 1 else 0
    folium.raster_layers.ImageOverlay(
        image=colours,
        bounds=[[float(data.lat.min()) - half, float(data.lon.min()) - half],
                [float(data.lat.max()) + half, float(data.lon.max()) + half]],
        mercator_project=True, opacity=opacity, name=name, show=show,
    ).add_to(m)

    legend = branca.colormap.LinearColormap(
        [to_hex(c) for c in colormaps[cmap](np.linspace(0, 1, 8))], vmin=vmin, vmax=vmax, caption=caption
    )
    legend.add_to(m)


if __name__ == "__main__":
    login()
    print("Earthdata login works.")
