"""County crop yields from USDA NASS Quick Stats, as layers on the Agriculture map: canola, oil sunflower and oats.

Each crop is one layer showing the average yield per county over YEARS. NASS only publishes county yields for the
main producing counties, and fewer each year, so one year alone would show just a handful of counties. Counties in
the same states without a published yield are drawn grey, so they don't look like low yields.

The yields come from the Quick Stats API, which needs a free key in `.env` (QUICKSTATS_API_KEY, see .env.example).
County shapes come from the US Census Bureau. Both are downloaded once into data/raw/nass_yields/.
"""

import json
import os
from dataclasses import dataclass

import folium
import geopandas as gpd
import numpy as np
import pandas as pd
import requests
import shapely
from dotenv import load_dotenv
from folium.template import Template
from matplotlib import colormaps
from matplotlib.colors import LinearSegmentedColormap, Normalize, to_hex
from matplotlib.ticker import MaxNLocator

from capstone.earthdata import DATA_DIR, ROOT, ColourKey, colour_key
from capstone.sources.base import Source

API = "https://quickstats.nass.usda.gov/api/api_GET/"
# Census cartographic boundaries, 1:20 million (already simplified). 2021 is the last year with Connecticut's
# 8 counties; from 2022 Census files use its planning regions, which NASS doesn't.
COUNTIES = "https://www2.census.gov/geo/tiger/GENZ2021/shp/cb_2021_us_county_20m.zip"
FOLDER = DATA_DIR / "nass_yields"

# County estimates for a year come out around February of the next year. Move this on when the next year is out.
YEARS = range(2021, 2026)
OPACITY = 0.7     # how solid the counties are over the base map, like the other layers
GRID = 0.01       # round shape coordinates to 0.01° (about 1 km), as fine as the 1:20m shapes and keeps the page light

# The same for every crop: one yield per county and year, for the whole year, all farming practices together
COMMON = {"source_desc": "SURVEY", "statisticcat_desc": "YIELD", "agg_level_desc": "COUNTY", "freq_desc": "ANNUAL",
          "reference_period_desc": "YEAR", "prodn_practice_desc": "ALL PRODUCTION PRACTICES",
          "util_practice_desc": "ALL UTILIZATION PRACTICES"}


@dataclass
class Crop:
    id: str          # short name, used for the cached file
    name: str        # as shown on the map
    commodity: str   # NASS commodity_desc
    crop_class: str  # NASS class_desc
    unit: str        # NASS unit_desc
    colours: str     # matplotlib colour map, a different one for each crop


CROPS = [
    Crop("canola", "Canola", "CANOLA", "ALL CLASSES", "LB / ACRE", "YlGn"),
    # NASS stopped publishing county yields for all sunflower types together after 2008; oil type is the main one
    Crop("sunflower_oil", "Oil sunflower", "SUNFLOWER", "OIL TYPE", "LB / ACRE", "YlOrBr"),
    Crop("oats", "Oats", "OATS", "ALL CLASSES", "BU / ACRE", "PuBu"),
]

NOT_NUMBERS = {"(D)", "(NA)", "(Z)", "(S)", "(X)"}  # withheld, not available, too small, unreliable, not applicable


def api_key() -> str:
    load_dotenv(ROOT / ".env")
    key = os.environ.get("QUICKSTATS_API_KEY")
    if not key:
        raise RuntimeError("No USDA NASS Quick Stats key: add QUICKSTATS_API_KEY to .env (see .env.example).")
    return key


def load(crop: Crop) -> pd.DataFrame:
    """One row per county and year with a published yield: fips (state + county code), county, state, year, yield.
    Also useful on its own in a notebook."""
    path = FOLDER / f"{crop.id}_{YEARS[0]}_{YEARS[-1]}.csv"
    if not path.exists():
        params = dict(COMMON, commodity_desc=crop.commodity, class_desc=crop.crop_class, unit_desc=crop.unit,
                      year__GE=YEARS[0], year__LE=YEARS[-1], key=api_key())
        response = requests.get(API, params=params, timeout=120)
        response.raise_for_status()
        raw = pd.DataFrame(response.json()["data"])  # well under the API's limit of 50,000 rows
        FOLDER.mkdir(parents=True, exist_ok=True)
        raw.to_csv(path, index=False)
    raw = pd.read_csv(path, dtype=str)

    # "Other (combined) counties" (code 998) lumps the smaller counties of a state together and has no shape
    raw = raw[raw["county_code"] != "998"]
    values = raw["Value"].str.strip()
    df = pd.DataFrame({
        "fips": raw["state_fips_code"].str.zfill(2) + raw["county_code"].str.zfill(3),
        "county": raw["county_name"].str.title(),
        "state": raw["state_alpha"],
        "year": raw["year"].astype(int),
        "yield": pd.to_numeric(values.where(~values.isin(NOT_NUMBERS)).str.replace(",", ""), errors="coerce"),
    }).dropna(subset=["yield"])
    if df.duplicated(["fips", "year"]).any():
        raise ValueError(f"More than one {crop.name} yield for some counties: the NASS filters need narrowing")
    return df


def county_shapes(states: set[str]) -> gpd.GeoDataFrame:
    """Census county shapes for the given states (two-digit FIPS codes), with coordinates rounded to GRID."""
    path = FOLDER / COUNTIES.rsplit("/", 1)[1]
    if not path.exists():
        FOLDER.mkdir(parents=True, exist_ok=True)
        response = requests.get(COUNTIES, timeout=120)
        response.raise_for_status()
        path.write_bytes(response.content)
    gdf = gpd.read_file(path)
    gdf = gdf[gdf["STATEFP"].isin(states)].to_crs(4326)
    gdf["geometry"] = shapely.set_precision(gdf.geometry.values, GRID)
    return gdf[["GEOID", "NAMELSAD", "STUSPS", "STATEFP", "geometry"]]


def colour_map(crop: Crop) -> str:
    """The crop's colours without their palest part, so the lowest yields don't look like empty counties."""
    name = f"{crop.colours}_nass"
    if name not in colormaps:
        colormaps.register(LinearSegmentedColormap.from_list(name, colormaps[crop.colours](np.linspace(0.25, 1, 256))))
    return name


class CountyShapes(folium.MacroElement):
    """The county shapes, written into the page once and shared by all crop layers."""

    _template = Template("""
        {% macro script(this, kwargs) %}
            var {{ this.get_name() }} = {{ this.geojson|tojson }};
        {% endmacro %}
    """)

    def __init__(self, geojson: dict):
        super().__init__()
        self._name = "CountyShapes"
        self.geojson = geojson


class CropLayer(folium.map.Layer):
    """One crop's counties, drawn from the shared shapes: coloured where NASS published a yield, grey elsewhere in
    the same states. Hovering shows the county's yield."""

    _template = Template("""
        {% macro script(this, kwargs) %}
            var {{ this.get_name() }} = L.geoJSON({{ this.shapes.get_name() }}, {
                filter: function (f) { return {{ this.states|tojson }}.includes(f.properties.statefp); },
                style: function (f) {
                    const c = f.properties.crops[{{ this.crop_id|tojson }}];
                    return c ? {color: "#ffffff", weight: 0.6, fillColor: c.colour, fillOpacity: {{ this.opacity }}}
                             : {color: "#8c8c8c", weight: 0.6, dashArray: "2 3", fillColor: "#bdbdbd", fillOpacity: 0.2};
                },
                onEachFeature: function (f, layer) {
                    const c = f.properties.crops[{{ this.crop_id|tojson }}];
                    const place = f.properties.name + ", " + f.properties.state;
                    const text = c
                        ? place + "<br><b>" + c.mean.toLocaleString("en-US") + " {{ this.unit }}</b>, average of "
                          + (c.years === 1 ? "1 year" : c.years + " years") + " with data ({{ this.period }})"
                        : place + "<br>No county yield published ({{ this.period }})";
                    layer.bindTooltip(text, {sticky: true});
                },
            });
        {% endmacro %}
    """)

    def __init__(self, shapes: CountyShapes, crop: Crop, states: list[str], unit: str, period: str, show: bool):
        super().__init__(name=f"{crop.name} yield, {period} average (USDA NASS)", overlay=True, show=show)
        self._name = "CropLayer"
        self.shapes, self.crop_id, self.states = shapes, crop.id, states
        self.unit, self.period, self.opacity = unit, period, OPACITY


def no_data_note() -> str:
    """A line under the colour key with the grey swatch used for counties without a yield."""
    return ('<div style="display: flex; align-items: center; gap: 5px; font-size: 11px; margin: 1px 0 3px;">'
            '<span style="width: 14px; height: 9px; background: rgba(189, 189, 189, 0.2); '
            'border: 1px dashed #8c8c8c;"></span>No county yield published</div>')


def add_to_map(m: folium.Map, show: bool) -> None:
    period = f"{YEARS[0]}–{YEARS[-1]}"
    averages = {}
    for crop in CROPS:
        df = load(crop)
        averages[crop.id] = df.groupby("fips").agg(mean=("yield", "mean"), years=("year", "nunique"))

    # One set of shapes for all crops: every county in the states where any of the crops has a yield
    states = {fips[:2] for a in averages.values() for fips in a.index}
    shapes = county_shapes(states)

    scales = {}
    for crop in CROPS:
        means = averages[crop.id]["mean"]
        ticks = MaxNLocator(nbins=4).tick_values(means.min(), means.max())  # round numbers around the data
        scales[crop.id] = (colour_map(crop), float(ticks[0]), float(ticks[-1]))

    features = []
    for county in shapes.itertuples():
        crops = {}
        for crop in CROPS:
            if county.GEOID in averages[crop.id].index:
                row = averages[crop.id].loc[county.GEOID]
                cmap, vmin, vmax = scales[crop.id]
                colour = to_hex(colormaps[cmap](Normalize(vmin, vmax, clip=True)(row["mean"])))
                mean = round(row["mean"], -1 if row["mean"] >= 1000 else 0)  # e.g. 2,150 lb/acre but 74 bu/acre
                crops[crop.id] = {"mean": int(mean), "years": int(row["years"]), "colour": colour}
        features.append({"type": "Feature", "geometry": shapely.geometry.mapping(county.geometry), "properties": {
            "name": county.NAMELSAD, "state": county.STUSPS, "statefp": county.STATEFP, "crops": crops}})
    missing = set().union(*(a.index for a in averages.values())) - set(shapes["GEOID"])
    if missing:
        raise ValueError(f"NASS counties without a Census shape: {sorted(missing)}")

    geojson = json.loads(json.dumps({"type": "FeatureCollection", "features": features}))  # plain lists, no tuples
    shared = CountyShapes(geojson)
    shared.add_to(m)
    for crop in CROPS:
        unit = crop.unit.lower().replace(" / ", "/")
        crop_states = sorted({fips[:2] for fips in averages[crop.id].index})
        layer = CropLayer(shared, crop, crop_states, unit, period, show)
        layer.add_to(m)
        cmap, vmin, vmax = scales[crop.id]
        key = colour_key(cmap, vmin, vmax, f"{crop.name} yield, {period} average ({unit})", OPACITY)
        ColourKey(layer, key + no_data_note()).add_to(m)


SOURCE = Source(
    id="nass_yields",
    name="USDA NASS Quick Stats: county crop yields (canola, oil sunflower, oats)",
    provider="USDA National Agricultural Statistics Service (NASS)",
    url="https://quickstats.nass.usda.gov/",
    access="Quick Stats API (free key). County shapes from US Census cartographic boundary files (2021, 1:20m)",
    spatial_resolution="County level, main producing counties only",
    temporal_coverage=("Oats 1915–present, canola 1999–present, oil sunflower 1995–present (no 2019), yearly. "
                       "Map: 2021–2025 average"),
    update_frequency="Yearly; county estimates come out around February of the following year",
    status="Active, but publishing fewer counties over time (see notes)",
    license="Public domain (US government data). Cite: USDA National Agricultural Statistics Service, Quick Stats",
    add_to_map=add_to_map,
    notes=(
        "Yields come from NASS's county survey estimates, for all farming practices together: pounds per acre for "
        "canola and sunflower, bushels per acre for oats. "
        "NASS only publishes counties with enough farms and acres. The rest of a state is lumped into one "
        "\"other (combined) counties\" figure, which has no shape on the map and is left out. "
        "The number of counties has fallen a lot: canola from 81 counties in 1999 to 19 in 2025 (all in North "
        "Dakota), oil sunflower from 148 in 1995 to 10 in 2025, with no county figures at all for 2019, and oats "
        "from 1,814 counties in 1975 to 226 in 2025, with only 8 in 2024 (checked in November 2026). That's why "
        "the map shows a 2021–2025 average: a single year would show only a handful of counties for canola and "
        "sunflower. County figures for sunflower of all types together stopped after 2008. "
        "Values are text in the API: numbers have commas, and withheld or missing values are codes such as (D) "
        "or (NA)."
    ),
)
