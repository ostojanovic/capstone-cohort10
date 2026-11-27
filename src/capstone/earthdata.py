"""Helpers for NASA Earthdata via the earthaccess library.

Downloading needs a free Earthdata login, stored in the `.env` file (see CONTRIBUTING.md, section 2.4).
Files are kept in data/raw/, so each file is only downloaded once.

Check that your login works with:  python -m capstone.earthdata
"""

import html
from pathlib import Path

import earthaccess
import folium
import numpy as np
import xarray as xr
from dotenv import load_dotenv
from folium.template import Template
from matplotlib import colormaps
from matplotlib.colors import Normalize, to_hex
from matplotlib.ticker import MaxNLocator

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


# Colour keys for map layers: small boxes in the website's font, the same size as the list of layers
KEY_STYLE = """
<style>
    .colour-key-box { padding: 5px 9px 2px 9px; background: #fff; border-radius: 5px;
        box-shadow: 0 1px 5px rgba(0, 0, 0, 0.4); }
    .colour-key { min-width: 200px; color: #333; line-height: 1.3;
        font-family: "Roboto", "Helvetica Neue", Arial, sans-serif; }
    .colour-key .caption { font-size: 12px; margin-bottom: 3px; white-space: nowrap; }
    .colour-key .bar { height: 8px; }
    .colour-key .ticks { position: relative; height: 15px; font-size: 11px; }
    .colour-key .ticks span { position: absolute; transform: translateX(-50%); }
</style>
"""


def colour_key(cmap: str, vmin: float, vmax: float, caption: str, opacity: float = 0.7,
               ticks: list[float] | None = None) -> str:
    """HTML for a colour key: the caption, a colour bar and the values under it. The bar is as see-through as
    the layer, so its colours match what the map shows."""
    if ticks is None:
        ticks = [v for v in MaxNLocator(nbins=5).tick_values(vmin, vmax) if vmin <= v <= vmax]
    signed = vmin < 0 < vmax  # values on both sides of zero get a + or − sign

    def label(v: float) -> str:
        return (f"{v:+g}" if signed and v != 0 else f"{v:g}").replace("-", "−")

    stops = ", ".join(to_hex(c) for c in colormaps[cmap](np.linspace(0, 1, 11)))
    spans = "".join(f'<span style="left: {100 * (v - vmin) / (vmax - vmin):g}%">{label(v)}</span>' for v in ticks)
    return (
        f'<div class="colour-key"><div class="caption">{html.escape(caption)}</div>'
        f'<div class="bar" style="background: linear-gradient(to right, {stops}); opacity: {opacity};"></div>'
        f'<div class="ticks">{spans}</div></div>'
    )


class ColourKey(folium.MacroElement):
    """A layer's colour key in a box at the top right of the map, shown only while the layer is switched on."""

    _template = Template("""
        {% macro header(this, kwargs) %}{{ this.style }}{% endmacro %}
        {% macro script(this, kwargs) %}
            (function () {
                const map = {{ this._parent.get_name() }};
                const layer = {{ this.layer.get_name() }};
                const key = L.control({position: "topright"});
                key.onAdd = function () {
                    const box = L.DomUtil.create("div", "colour-key-box");
                    box.innerHTML = {{ this.html|tojson }};
                    return box;
                };
                function show() {  // above the list of layers, however often the layer is switched on and off
                    key.addTo(map);
                    const box = key.getContainer();
                    box.parentNode.insertBefore(box, box.parentNode.firstChild);
                }
                map.on("overlayadd", function (e) { if (e.layer === layer) show(); });
                map.on("overlayremove", function (e) { if (e.layer === layer) key.remove(); });
                if (map.hasLayer(layer)) show();
            })();
        {% endmacro %}
    """)

    def __init__(self, layer, html: str):
        super().__init__()
        self._name = "ColourKey"
        self.layer, self.html, self.style = layer, html, KEY_STYLE


def add_raster(m: folium.Map, data: xr.DataArray, name: str, caption: str, cmap: str = "viridis",
               vmin: float | None = None, vmax: float | None = None, show: bool = True,
               opacity: float = 0.7, bounds: tuple[float, float, float, float] = CONUS_BBOX) -> None:
    """Draw a 2D lat/lon grid on the map as a coloured image, with a colour key that shows while the layer is on.

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
    overlay = folium.raster_layers.ImageOverlay(
        image=colours,
        bounds=[[float(data.lat.min()) - half, float(data.lon.min()) - half],
                [float(data.lat.max()) + half, float(data.lon.max()) + half]],
        mercator_project=True, opacity=opacity, name=name, show=show,
    ).add_to(m)
    ColourKey(overlay, colour_key(cmap, float(vmin), float(vmax), caption, opacity)).add_to(m)


if __name__ == "__main__":
    login()
    print("Earthdata login works.")
