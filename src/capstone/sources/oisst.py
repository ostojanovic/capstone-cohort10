"""Sea surface temperature anomaly, from NOAA's OISST v2.1, as an animated layer on the El Niño map.

The layer plays the last 52 weeks (Sunday to Saturday) in a loop. A box on the map shows the week's dates, a pause
button and the colour key. Each week is the average of NCEI's daily anomalies, which NCEI calculates against the
1971–2000 average for that day of the year. It covers the whole world's oceans.

The data comes from NOAA CoastWatch's ERDDAP server, with no login. ERDDAP cuts out just the days and grid points we
ask for, so each download is small. The weeks are saved in data/raw/oisst/, so each week is only downloaded once. If
ERDDAP can't be reached, the map shows the saved weeks instead; the dates on the map show which.
We used NOAA PSL's copy of the same data until November 2026, when its server started refusing requests.
"""

import base64
import html
import io
import time
from pathlib import Path
from urllib.parse import quote

import folium
import numpy as np
import pandas as pd
import requests
import xarray as xr
from folium.template import Template
from matplotlib import colormaps
from PIL import Image

from capstone.earthdata import DATA_DIR, KEY_STYLE, colour_key
from capstone.sources.base import Source

# OISST v2.1 "final" daily data, with longitudes from 0 to 360°E. About 2 weeks behind real time.
ERDDAP = "https://coastwatch.pfeg.noaa.gov/erddap/griddap/ncdcOisst21Agg"
BASELINE = "1971–2000"  # the average NCEI's daily anomalies are calculated against
FOLDER = DATA_DIR / "oisst"

WEST_EDGE = 20       # where the flat map cuts the globe: 20°E, through Africa, so the Pacific stays in one piece
LAT_LIMIT = 70       # leave out the polar seas, mostly ice
WEEK_STRIDE = 4      # every 4th grid point: 1° instead of 0.25°, so 52 maps still load quickly
WEEKS = 52           # how many weeks the layer plays (the last complete ones)
DAYS_PER_REQUEST = 28  # about 1.4 MB per download at 1°
NINO34 = (-170, -120, -5, 5)  # Niño 3.4 box, outlined on the map: west, east (°E), south, north
PAUSE = 2            # seconds between downloads, to go easy on the server
RETRY_WAITS = [20, 60]  # seconds to wait before the 2nd and 3rd try when a download fails
# Seconds to connect, then to get the answer. On networks without IPv6, the IPv6 address only fails after the
# connect timeout, so it is short; one session reuses the connection, so this happens once, not every request.
TIMEOUT = (10, 120)
SESSION = requests.Session()

COLOURS = "RdBu_r"   # blue = cooler than average, red = warmer
LIMIT = 5            # the colours run from -5 to +5 °C; anything beyond gets the end colour
LEVELS = 100         # colour steps: 0.1 °C each, too fine to see but keeps the images small
OPACITY = 0.7        # how solid the layer is over the base map, like the other layers
FRAME_MS = 250       # each week shows for 0.25 seconds...
LAST_FRAME_MS = 2000  # ...and the latest week for 2 seconds before the loop starts again


def around_pacific(data: xr.DataArray) -> xr.DataArray:
    """Number longitudes from 20°E eastwards around the globe to 20°E as -340 to 20, so a flat map centred on
    the Pacific shows it in one piece."""
    lon = data.lon.where(data.lon >= WEST_EDGE, data.lon + 360)
    return data.assign_coords(lon=lon - 360).sortby("lon")


def get(query: str) -> bytes:
    """One ERDDAP request, e.g. "time[(last)]" as CSV or a data subset as NetCDF. Tries 3 times."""
    for wait in [0] + RETRY_WAITS:
        time.sleep(wait)
        try:
            response = SESSION.get(f"{ERDDAP}{quote(query, safe='.?=():,-')}", timeout=TIMEOUT)
        except requests.RequestException as error:
            problem = str(error)
            continue
        if response.status_code == 200:
            time.sleep(PAUSE)
            return response.content
        problem = f"HTTP {response.status_code}"
    raise RuntimeError(f"OISST download from NOAA CoastWatch ERDDAP failed ({problem}). Try again later.")


def latest_day() -> pd.Timestamp:
    """The newest day ERDDAP has."""
    lines = get(".csv?time[(last)]").decode().splitlines()  # a header line, a units line, then the date
    return pd.Timestamp(lines[2]).tz_localize(None).normalize()


def download(first: pd.Timestamp, last: pd.Timestamp, stride: int) -> xr.DataArray:
    """Daily anomalies from `first` to `last` (both included), every stride-th grid point within LAT_LIMIT.
    Checks the download came through complete; if anything looks wrong, waits and tries again."""
    lat = LAT_LIMIT - 0.125  # the grid points sit at 0.125, 0.375, ... so start just inside the limit
    query = (f".nc?anom[({first:%Y-%m-%d}T12:00:00Z):1:({last:%Y-%m-%d}T12:00:00Z)][(0.0)]"
             f"[({-lat}):{stride}:({lat})][(0.125):{stride}:(359.875)]")
    for wait in [0] + RETRY_WAITS:
        time.sleep(wait)
        with xr.open_dataset(io.BytesIO(get(query)), engine="scipy") as ds:
            result = ds["anom"].isel(zlev=0, drop=True).rename(latitude="lat", longitude="lon").load()
        values = result.values
        empty = float(np.isnan(values).mean(axis=(-2, -1)).max())  # share of empty points, worst day
        if empty >= 0.5:  # land is about a third of the map; more than half empty means data went missing
            problem = f"{empty:.0%} of the points are empty"
        elif np.nanmax(np.abs(values)) > 25 or np.nanstd(values, axis=(-2, -1)).min() < 0.05:
            problem = "the values are garbled"  # real anomalies stay within about ±15 °C and vary by place
        else:
            return result
    raise RuntimeError(f"OISST download from NOAA CoastWatch ERDDAP looks wrong ({problem}). Try again later.")


def daily_anomalies(first: pd.Timestamp, last: pd.Timestamp, stride: int) -> xr.DataArray:
    """All daily anomalies from `first` to `last` (both included), every stride-th grid point, a few weeks
    per download."""
    days = pd.date_range(first, last)
    pieces = [download(chunk[0], chunk[-1], stride)
              for chunk in (days[i:i + DAYS_PER_REQUEST] for i in range(0, len(days), DAYS_PER_REQUEST))]
    return xr.concat(pieces, dim="time")


def weekly_anomalies() -> xr.DataArray:
    """The last WEEKS complete weeks (Sunday to Saturday), each the average of its 7 daily anomalies, at 1°.
    Weeks already calculated are reused. If ERDDAP can't be reached, the newest saved weeks are used."""
    path = FOLDER / f"oisst_weekly_{WEEK_STRIDE}.nc"
    saved = None
    if path.exists():
        with xr.open_dataarray(path) as old:
            saved = old.load()
    try:
        return update_weeks(saved, path)
    except (OSError, RuntimeError):
        if saved is None or saved.sizes["time"] < WEEKS:
            raise  # nothing saved to fall back on
        return saved.isel(time=slice(-WEEKS, None))


def update_weeks(saved: xr.DataArray | None, path: Path) -> xr.DataArray:
    """Download the weeks that aren't saved yet, save them with the others and return the last WEEKS."""
    last = latest_day()
    last_saturday = last - pd.Timedelta(days=(last.dayofweek - 5) % 7)
    starts = pd.date_range(end=last_saturday - pd.Timedelta(days=6), periods=WEEKS, freq="7D")

    have = set(pd.DatetimeIndex(saved.time.values)) if saved is not None else set()
    missing = [s for s in starts if s not in have]
    if missing:  # download all the days the missing weeks need, then average each week
        days = daily_anomalies(missing[0], missing[-1] + pd.Timedelta(days=6), WEEK_STRIDE)
        new = [days.sel(time=slice(s, s + pd.Timedelta(days=6, hours=23))).mean("time").expand_dims(time=[s])
               for s in missing]
        weeks = xr.concat(([saved] if saved is not None else []) + new, dim="time").sortby("time")
        FOLDER.mkdir(parents=True, exist_ok=True)
        weeks.rename("anom").to_netcdf(path)
    else:
        weeks = saved
    return weeks.sel(time=starts)


# ---- Drawing the weeks on the map ----------------------------------------------------------------------------

def mercator(lat: np.ndarray) -> np.ndarray:
    """Latitude (degrees) to the web map's vertical position."""
    return np.arcsinh(np.tan(np.radians(lat)))


def frame(week: xr.DataArray, south: float, north: float) -> str:
    """One week as a small PNG image, stretched north-south to fit the web map, returned as a data URL."""
    # Web maps stretch latitudes towards the poles, so pick which data row each image row shows. Twice as many
    # rows as the data keeps 1° detail at the equator.
    rows = 2 * week.sizes["lat"]
    y = mercator(north) + (np.arange(rows) + 0.5) / rows * (mercator(south) - mercator(north))  # top to bottom
    values = week.sel(lat=np.degrees(np.arctan(np.sinh(y))), method="nearest").values

    steps = np.clip(np.floor((values + LIMIT) / (2 * LIMIT) * LEVELS), 0, LEVELS - 1)
    steps[np.isnan(values)] = LEVELS  # land and sea ice: the last palette entry, see-through
    image = Image.fromarray(steps.astype(np.uint8), mode="P")
    palette = colormaps[COLOURS].resampled(LEVELS)(np.arange(LEVELS))[:, :3]
    image.putpalette([round(255 * c) for c in palette.ravel()] + [0, 0, 0])
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True, transparency=LEVELS)
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()


class WeekPlayer(folium.MacroElement):
    """Plays the weekly images on the map one after another. A box at the bottom left shows the week's dates, a
    pause button and the colour key; it disappears when the layer is switched off."""

    _template = Template("""
        {% macro header(this, kwargs) %}
            {{ this.key_style }}
            <style>
                .week-player { padding: 5px 9px 2px 5px; color: #333; line-height: 1.3;
                    background: rgba(255, 255, 255, 0.92); border-radius: 5px; box-shadow: 0 1px 5px rgba(0,0,0,0.4);
                    font-family: "Roboto", "Helvetica Neue", Arial, sans-serif; }
                .week-player .top { display: flex; align-items: center; gap: 7px; margin-bottom: 5px; }
                .week-player .title { font-size: 13px; font-weight: 600; white-space: nowrap; }
                .week-player .dates { font-size: 13px; font-variant-numeric: tabular-nums; }
                .week-player button { width: 26px; height: 26px; flex: none; padding: 0; cursor: pointer;
                    border: 1px solid #bbb; border-radius: 4px; background: #fff; color: #333; font-size: 10px; }
                .week-player button:hover { background: #f2f2f2; }
                .week-player .colour-key { margin-left: 4px; }
            </style>
        {% endmacro %}

        {% macro script(this, kwargs) %}
            (function () {
                const map = {{ this._parent.get_name() }};
                const layer = {{ this.layer.get_name() }};
                const overlay = {{ this.overlay.get_name() }};
                const frames = {{ this.frames|tojson }};
                const dates = {{ this.dates|tojson }};
                const loaded = frames.map(function (src) { const img = new Image(); img.src = src; return img; });

                // Plays from the oldest week; people who ask their computer for less motion get the latest week, paused
                let playing = !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
                let week = playing ? 0 : frames.length - 1;
                let timer = null, button = null, label = null;

                function show(i) {
                    week = i;
                    overlay.setUrl(frames[i]);
                    if (label) label.textContent = dates[i];
                }
                function schedule() {
                    clearTimeout(timer);
                    if (playing && map.hasLayer(layer)) {
                        timer = setTimeout(function () { show((week + 1) % frames.length); schedule(); },
                                           week === frames.length - 1 ? {{ this.last_frame_ms }} : {{ this.frame_ms }});
                    }
                }
                function setPlaying(p) {
                    playing = p;
                    button.textContent = p ? "❚❚" : "▶";
                    button.title = p ? "Pause" : "Play";
                    button.setAttribute("aria-label", p ? "Pause the animation" : "Play the animation");
                    schedule();
                }

                const player = L.control({position: "bottomleft"});
                player.onAdd = function () {
                    const box = L.DomUtil.create("div", "week-player");
                    box.innerHTML = {{ this.box_html|tojson }};
                    button = box.querySelector("button");
                    label = box.querySelector(".dates");
                    L.DomEvent.disableClickPropagation(box);
                    L.DomEvent.disableScrollPropagation(box);
                    L.DomEvent.on(button, "click", function () { setPlaying(!playing); });
                    show(week);
                    setPlaying(playing);
                    return box;
                };

                map.on("overlayadd", function (e) { if (e.layer === layer) player.addTo(map); });
                map.on("overlayremove", function (e) {
                    if (e.layer === layer) { clearTimeout(timer); player.remove(); }
                });
                if (map.hasLayer(layer)) player.addTo(map);
                else show(week);
            })();
        {% endmacro %}
    """)

    def __init__(self, layer, overlay, frames: list[str], dates: list[str], title: str, caption: str):
        super().__init__()
        self._name = "WeekPlayer"
        self.layer, self.overlay, self.frames, self.dates = layer, overlay, frames, dates
        self.frame_ms, self.last_frame_ms = FRAME_MS, LAST_FRAME_MS

        # The colour key, in the same style as the other layers' keys
        key = colour_key(COLOURS, -LIMIT, LIMIT, caption, opacity=OPACITY, ticks=list(range(-LIMIT, LIMIT + 1)))
        self.key_style = KEY_STYLE
        self.box_html = (
            '<div class="top"><button type="button"></button>'
            f'<div><div class="title">{html.escape(title)}</div><div class="dates"></div></div></div>' + key
        )


def add_to_map(m: folium.Map, show: bool) -> None:
    weeks = around_pacific(weekly_anomalies()).sortby("lat", ascending=False)  # images are drawn north to south
    half = abs(float(weeks.lat[0] - weeks.lat[1])) / 2  # each value covers a 1° square around its point
    south, north = float(weeks.lat.min()) - half, float(weeks.lat.max()) + half
    west, east = float(weeks.lon.min()) - half, float(weeks.lon.max()) + half

    frames = [frame(weeks.sel(time=t), south, north) for t in weeks.time.values]
    dates = []
    for t in weeks.time.values:
        start = pd.Timestamp(t)
        end = start + pd.Timedelta(days=6)
        dates.append(f"{start.day} {start:%b %Y} – {end.day} {end:%b %Y}")

    layer = folium.FeatureGroup(name=f"Sea Surface Temperature Anomaly, Last {WEEKS} Weeks (OISST)", show=show)
    overlay = folium.raster_layers.ImageOverlay(frames[-1], bounds=[[south, west], [north, east]], opacity=OPACITY)
    overlay.add_to(layer)

    w, e, s, n = NINO34
    folium.Rectangle(
        bounds=[[s, w], [n, e]], color="#333333", weight=1.5, dash_array="6 4", fill=False,
        tooltip="Niño 3.4: the patch of the Pacific NOAA watches to call El Niño and La Niña",
    ).add_to(layer)
    folium.Marker(  # a small label just above the box
        location=[n, (w + e) / 2],
        icon=folium.DivIcon(
            html='<div style="font: 13px Roboto, Arial, sans-serif; color: #333; text-align: center; '
                 'white-space: nowrap;">Niño 3.4</div>',
            icon_size=(60, 16), icon_anchor=(30, 18),
        ),
    ).add_to(layer)
    layer.add_to(m)

    WeekPlayer(layer, overlay, frames, dates, title="Sea Surface Temperature Anomaly",
               caption=f"Difference from the {BASELINE} average (°C)").add_to(m)


SOURCE = Source(
    id="oisst",
    name="Optimum Interpolation Sea Surface Temperature (OISST) v2.1",
    provider="NOAA NCEI (served by NOAA CoastWatch ERDDAP)",
    url="https://www.ncei.noaa.gov/products/optimum-interpolation-sst",
    access="NetCDF from NOAA CoastWatch's ERDDAP server, no login. ERDDAP cuts out only the days and grid points "
           "we need",
    spatial_resolution="0.25° (~28 km); shown at 1° on the map",
    temporal_coverage="1981–present, daily",
    update_frequency="Daily; the final version we use is about 2 weeks behind",
    status="Active",
    license="NOAA open data. Cite Huang et al. (2021), J. Climate. Served by NOAA CoastWatch ERDDAP",
    add_to_map=add_to_map,
    notes=(
        "Blends satellite, ship, buoy and Argo float data. Uses NCEI's daily anomalies, which are calculated "
        f"against the {BASELINE} average. The map plays the last {WEEKS} weeks (Sunday to Saturday), each the "
        "average of its 7 daily anomalies. NOAA CPC's El Niño monitoring (and so RONI) uses the 1991–2020 average "
        "instead. The oceans have warmed since the 1970s, so these values run warmer than CPC's. NOAA uses OISST "
        "for maps of current conditions and ERSST (behind RONI) for comparing events across years. "
        "We first used NOAA PSL's copy of the same data, but since November 2026 PSL's data server (THREDDS) "
        "answers every request with \"Too Many Requests\", so we switched to ERDDAP. NCEI also has a preliminary "
        "version, closer to real time, that may still be revised."
    ),
)
