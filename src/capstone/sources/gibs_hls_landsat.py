"""Recent Landsat imagery (HLS L30) as ready-made map tiles from NASA GIBS.

GIBS has one layer per day, and each day only covers a few strips of the US. We stack 16 days
(two Landsat 8/9 revisit cycles) into one layer to get an almost complete picture.
GIBS serves pre-rendered images: no data values behind them.
"""

from datetime import date, timedelta

import folium

from capstone.sources.base import Source

TILES = (
    "https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/"
    "HLS_L30_Nadir_BRDF_Adjusted_Reflectance/default/{day}/"
    "GoogleMapsCompatible_Level12/{{z}}/{{y}}/{{x}}.png"
)
LAST_DAY = date(2026, 10, 7)  # NASA publishes a few days late: pick a day at least 4 days ago
DAYS = 16                     # 8 days left large gaps in the east, 16 covers almost all of the US

FIRST_DAY = LAST_DAY - timedelta(days=DAYS - 1)


def add_to_map(m: folium.Map, show: bool) -> None:
    group = folium.FeatureGroup(
        name=f"Landsat, {FIRST_DAY.day} {FIRST_DAY:%b}–{LAST_DAY.day} {LAST_DAY:%b %Y} (HLS)", show=show
    )
    for i in range(DAYS):  # oldest first, so the most recent images are drawn on top
        day = FIRST_DAY + timedelta(days=i)
        folium.TileLayer(
            tiles=TILES.format(day=day.isoformat()),
            attr="HLS Landsat (NASA GIBS)",
            name=f"Landsat {day}",
            overlay=True,
            max_native_zoom=12,
            max_zoom=18,
        ).add_to(group)
    group.add_to(m)


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
          "between strips from different days are visible. The HLS_S30 layer (Sentinel-2, European) is "
          "not used because we focus on US sources.",
)
