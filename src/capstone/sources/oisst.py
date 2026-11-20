"""Sea surface temperature anomaly, from NOAA's OISST v2.1, as an animated layer on the El Niño map.

The layer plays the last 52 weeks (Sunday to Saturday) in a loop. A box on the map shows the week's dates, a pause
button and the colour key. Each week is the average of PSL's ready-made daily anomaly files, which PSL calculates
against the 1971–2000 average for that day of the year. It covers the whole world's oceans.

The data comes straight from NOAA PSL's server, with no login. Only the days we need are downloaded, at reduced
detail, and saved in data/raw/oisst/, so each week is only downloaded once. If PSL's server can't be reached (it
sometimes answers "too many requests"), the map shows the saved weeks instead; the dates on the map show which.
"""

import base64
import html
import io
import time
from pathlib import Path

import folium
import numpy as np
import pandas as pd
import xarray as xr
from folium.template import Template
from matplotlib import colormaps
from PIL import Image

from capstone.earthdata import DATA_DIR, KEY_STYLE, colour_key
from capstone.sources.base import Source

SERVER = "https://psl.noaa.gov/thredds/dodsC/Datasets/noaa.oisst.v2.highres/"  # OPeNDAP: read just a slice
DAILY_ANOMALIES = SERVER + "sst.day.anom.{year}.nc"  # PSL's ready-made daily anomalies, one file per year
BASELINE = "1971–2000"  # the average PSL's daily anomaly files are calculated against
FOLDER = DATA_DIR / "oisst"

WEST_EDGE = 20       # where the flat map cuts the globe: 20°E, through Africa, so the Pacific stays in one piece
LAT_LIMIT = 70       # leave out the polar seas, mostly ice
WEEK_STRIDE = 4      # every 4th grid point: 1° instead of 0.25°, so 52 maps still load quickly
WEEKS = 52           # how many weeks the layer plays (the last complete ones)
NINO34 = (-170, -120, -5, 5)  # Niño 3.4 box, outlined on the map: west, east (°E), south, north
PAUSE = 2            # seconds between downloads, so PSL's server doesn't answer "too many requests"
RETRY_WAITS = [20, 60]  # seconds to wait before the 2nd and 3rd try when a download fails

COLOURS = "RdBu_r"   # blue = cooler than average, red = warmer
LIMIT = 5            # the colours run from -5 to +5 °C; anything beyond gets the end colour
LEVELS = 100         # colour steps: 0.1 °C each, too fine to see but keeps the images small
OPACITY = 0.7        # how solid the layer is over the base map, like the other layers
FRAME_MS = 250       # each week shows for 0.25 seconds...
LAST_FRAME_MS = 2000  # ...and the latest week for 2 seconds before the loop starts again


def thin(data: xr.DataArray, stride: int) -> xr.DataArray:
    """Keep latitudes within LAT_LIMIT (whichever way the file stores them) and every stride-th grid point."""
    lat = slice(-LAT_LIMIT, LAT_LIMIT) if data.lat[0] < data.lat[-1] else slice(LAT_LIMIT, -LAT_LIMIT)
    return data.sel(lat=lat).isel(lat=slice(None, None, stride), lon=slice(None, None, stride))


def around_pacific(data: xr.DataArray) -> xr.DataArray:
    """Number longitudes from 20°E eastwards around the globe to 20°E as -340 to 20, so a flat map centred on
    the Pacific shows it in one piece."""
    lon = data.lon.where(data.lon >= WEST_EDGE, data.lon + 360)
    return data.assign_coords(lon=lon - 360).sortby("lon")


def open_year(year: int) -> xr.Dataset:
    """Open one yearly file on PSL's server. A busy server sometimes sends the file without its description
    (units and so on), so dates come through as plain numbers. That counts as a failure: wait and try again."""
    for wait in [0] + RETRY_WAITS:
        time.sleep(wait)
        try:
            ds = xr.open_dataset(DAILY_ANOMALIES.format(year=year))
        except OSError as error:
            problem = str(error)
            continue
        ds = ds.rename({k: v for k, v in {"latitude": "lat", "longitude": "lon"}.items() if k in ds.dims})
        if np.issubdtype(ds.time.dtype, np.datetime64) and pd.Timestamp(ds.time.values[0]).year == year:
            return ds  # the dates read as dates in the right year, so the description came through
        ds.close()
        problem = "the server sent an incomplete description of the file"
    raise RuntimeError(f"Could not open the OISST file for {year} on NOAA PSL's server ({problem})")


def latest_day() -> pd.Timestamp:
    """The newest day on PSL's server. The new year's file only appears a few days into January, so early in
    January last year's file is tried too."""
    today = pd.Timestamp.today()
    years = [today.year, today.year - 1] if today.dayofyear <= 10 else [today.year]
    for year in years:
        try:
            with open_year(year) as ds:
                return pd.Timestamp(ds.time.values[-1]).normalize()
        except RuntimeError as error:
            problem = error
    raise problem


def download(data: xr.DataArray) -> xr.DataArray:
    """Download one slice and check it came through complete. PSL's server sometimes drops part of a download,
    garbles it or answers "too many requests", so if anything looks wrong, wait and try again."""
    for wait in [0] + RETRY_WAITS:
        time.sleep(wait)
        try:
            result = data.compute()  # a new copy, so a retry downloads again instead of reusing a bad copy
        except (OSError, RuntimeError) as error:
            problem = str(error)
            continue
        values = result.values
        empty = float(np.isnan(values).mean(axis=(-2, -1)).max())  # share of empty points, worst day
        if empty >= 0.5:  # land is about a third of the map; more than half empty means data went missing
            problem = f"{empty:.0%} of the points are empty"
        elif np.nanmax(np.abs(values)) > 25 or np.nanstd(values, axis=(-2, -1)).min() < 0.05:
            problem = "the values are garbled"  # real anomalies stay within about ±15 °C and vary by place
        else:
            time.sleep(PAUSE)
            return result
    raise RuntimeError(f"OISST download from NOAA PSL failed ({problem}). Wait a few minutes and render again.")


def daily_anomalies(first: pd.Timestamp, last: pd.Timestamp, stride: int, days_per_request: int) -> xr.DataArray:
    """All daily anomalies from `first` to `last` (both included), every stride-th grid point. Each yearly file is
    opened once and the days are downloaded a few at a time, which PSL's server handles more reliably."""
    pieces = []
    for year in range(first.year, last.year + 1):  # the days can span two yearly files
        days = pd.date_range(max(first, pd.Timestamp(year, 1, 1)), min(last, pd.Timestamp(year, 12, 31)))
        with open_year(year) as ds:
            for i in range(0, len(days), days_per_request):
                chunk = days[i:i + days_per_request]
                period = slice(chunk[0], chunk[-1] + pd.Timedelta(hours=23))
                pieces.append(download(thin(ds["anom"].sel(time=period), stride)))
    return xr.concat(pieces, dim="time")


def weekly_anomalies() -> xr.DataArray:
    """The last WEEKS complete weeks (Sunday to Saturday), each the average of its 7 daily anomalies, at 1°.
    Weeks already calculated are reused. If PSL's server can't be reached, the newest saved weeks are used."""
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
    if missing:  # download all the days the missing weeks need, 4 weeks per request, then average each week
        days = daily_anomalies(missing[0], missing[-1] + pd.Timedelta(days=6), WEEK_STRIDE, 28)
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
                    font-family: "Source Sans Pro", "Helvetica Neue", Arial, sans-serif; }
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
            html='<div style="font: 13px \'Source Sans Pro\', Arial, sans-serif; color: #333; text-align: center; '
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
    provider="NOAA NCEI (daily anomaly files from NOAA PSL)",
    url="https://psl.noaa.gov/data/gridded/data.noaa.oisst.v2.highres.html",
    access="NetCDF from NOAA PSL's server (OPeNDAP), no login. Only the days we need are downloaded",
    spatial_resolution="0.25° (~28 km); shown at 1° on the map",
    temporal_coverage="1981–present, daily",
    update_frequency="Daily",
    status="Active",
    license="NOAA open data. Cite Huang et al. (2021), J. Climate. Data provided by NOAA PSL, Boulder, Colorado, USA",
    add_to_map=add_to_map,
    notes=(
        "Blends satellite, ship, buoy and Argo float data. Uses PSL's ready-made daily anomaly files, which are "
        f"calculated against the {BASELINE} average. The map plays the last {WEEKS} weeks (Sunday to Saturday), "
        "each the average of its 7 daily anomalies. NOAA CPC's El Niño monitoring (and so RONI) uses the "
        "1991–2020 average instead. The oceans have warmed since the 1970s, so these values run warmer than CPC's. "
        "NOAA uses OISST for maps of current conditions and ERSST (behind RONI) for comparing events across years. "
        "Data less than 15 days old may still be revised."
    ),
)
