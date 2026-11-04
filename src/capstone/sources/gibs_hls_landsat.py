"""Recent Landsat imagery (HLS L30) as ready-made map tiles from NASA GIBS.

GIBS has one layer per day, and each day only covers a few strips of the US. We stack 16 days
(two Landsat 8/9 revisit cycles) into one layer to get an almost complete picture.
GIBS serves pre-rendered images: no data values behind them.

The dates update by themselves on the website: when it is published, the workflow writes the latest
day into `landsat.json` next to the page, and a small script on the map moves the layers to those
dates. `LAST_DAY` below is only used when that file is missing, e.g. in `quarto preview`.
How often this happens is set in `.github/workflows/refresh-landsat.yml`.
"""

from datetime import date, timedelta

import folium
from branca.element import MacroElement
from folium.template import Template

from capstone.sources.base import Source

# `{time}` is filled in by Leaflet from each layer's `time` option, so the script can change it
TILES = (
    "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/"
    "HLS_L30_Nadir_BRDF_Adjusted_Reflectance/default/{time}/"
    "GoogleMapsCompatible_Level12/{z}/{y}/{x}.png"
)
LAST_DAY = date(2026, 10, 30)  # fallback only. NASA publishes a few days late: pick a day at least 4 days ago
DAYS = 16                      # 8 days left large gaps in the east, 16 covers almost all of the US


def _dates_label(last_day: date) -> str:
    """E.g. "15 Oct–30 Oct 2026". The script below builds the same text in JavaScript."""
    first_day = last_day - timedelta(days=DAYS - 1)
    return f"{first_day.day} {first_day:%b}–{last_day.day} {last_day:%b %Y}"


class _LatestDates(MacroElement):
    """Moves the layers in `group` to the dates in landsat.json, if the website has that file."""

    _template = Template("""
        {% macro script(this, kwargs) %}
        fetch("landsat.json", {cache: "no-cache"})
            .then((response) => response.ok ? response.json() : Promise.reject())
            .then((window_) => {
                const lastDay = new Date(window_.last_day + "T00:00:00Z");
                if (isNaN(lastDay)) return;
                const daysBefore = (n) => new Date(lastDay.getTime() - n * 86400000);
                {{ this.group.get_name() }}.eachLayer((layer) => {
                    layer.options.time = daysBefore(layer.options.daysBeforeLast).toISOString().slice(0, 10);
                    layer.redraw();
                });
                const firstDay = daysBefore({{ this.days }} - 1);
                const month = (d) => d.toLocaleString("en-US", {month: "short", timeZone: "UTC"});
                const label = `${firstDay.getUTCDate()} ${month(firstDay)}–${lastDay.getUTCDate()} `
                    + `${month(lastDay)} ${lastDay.getUTCFullYear()}`;
                document.querySelectorAll(".hls-dates").forEach((el) => { el.textContent = label; });
            })
            .catch(() => {});  // no landsat.json: keep the dates from the Python file
        {% endmacro %}
    """)

    def __init__(self, group: folium.FeatureGroup):
        super().__init__()
        self.group = group
        self.days = DAYS


def add_to_map(m: folium.Map, show: bool) -> None:
    group = folium.FeatureGroup(
        name=f'Landsat, <span class="hls-dates">{_dates_label(LAST_DAY)}</span> (HLS)', show=show
    )
    for n in reversed(range(DAYS)):  # oldest first, so the most recent images are drawn on top
        folium.TileLayer(
            tiles=TILES,
            attr="HLS Landsat (NASA GIBS)",
            name=f"Landsat, {n} days before the last day",
            overlay=True,
            max_native_zoom=12,
            max_zoom=18,
            time=(LAST_DAY - timedelta(days=n)).isoformat(),
            days_before_last=n,
        ).add_to(group)
    group.add_to(m)
    _LatestDates(group).add_to(m)


SOURCE = Source(
    id="gibs_hls_landsat",
    name="Harmonized Landsat Sentinel-2 (HLS) Landsat Surface Reflectance (HLSL30 v2.0)",
    provider="NASA GIBS (data: NASA LP DAAC, imagery: USGS/NASA Landsat 8 and 9)",
    url="https://doi.org/10.5067/HLS/HLSL30.002",
    access="Tile service (WMTS), no login. One layer per day",
    spatial_resolution="30 m (shown up to zoom 12)",
    temporal_coverage="Nov 2020–present, daily (a few missing days)",
    update_frequency="Daily, ~2–4 days delay",
    status="Active",
    license="NASA open data. Cite: Masek et al., HLS Operational Land Surface Reflectance V2.0, "
            "LP DAAC. Acknowledge NASA GIBS / ESDIS",
    add_to_map=add_to_map,
    notes="One day covers only ~10% of the US. Although Landsat 8 and 9 together revisit every 8 days, "
          "8 days of GIBS images left about a third of the eastern US empty (checked for 30 Sep–7 Oct 2026). "
          "16 days fill almost everything except a few small gaps. Clouds are not removed, and the edges "
          "between strips from different days are visible. The map shows the 16 days ending 4 days before "
          "the website was last published, refreshed monthly. The HLS_S30 layer (Sentinel-2, European) is "
          "not used because we focus on US sources.",
)
