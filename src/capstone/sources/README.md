# Data sources

Every dataset on the website has its own file in this folder. No notebook needed.
Notebooks are optional, for extra analysis.

## How it works

Each file has two parts:

1. **`SOURCE`**: a description of the dataset: provider, link, how we access it, resolution, update frequency,
   status and license. It appears on the website's **Data sources** page and in the table under each map.
2. **`add_to_map`**: the code that gets the data and draws it on the map.

The files are connected like this:

```
sources/my_source.py      1. you write this file
        ▼
sources/__init__.py       2. "register" it: add one line, so the website knows it exists
        ▼
topics.py                 3. add its id to the use cases (Agriculture, Droughts, El Niño) that should show it
        ▼
website                   the map and the Data sources page update automatically
```

The **id** is the source's short name, in lowercase without spaces (for example `imerg_monthly`).

## Add a source in 6 steps

1. **Copy the template** (from the repository root):
   ```bash
   cp src/capstone/sources/_template.py src/capstone/sources/usdm_drought.py
   ```
2. **Fill in `SOURCE`** at the bottom of the file. For `status`, see [below](#status).
3. **Fill in `add_to_map`**: keep the pattern that fits (see the [table](#which-pattern)) and delete the others.
4. **Register it** in `__init__.py`: add your file to the `import` line and `usdm_drought.SOURCE,` to the list.
5. **Add its id to a topic** in `src/capstone/topics.py`, under `sources`. Add it to `shown` too, if it
   should be switched on when the map opens. Once a topic has real data, delete its placeholder `examples`.
6. **Check** with `quarto preview`: your layer should be in the layer box on the map, and your dataset on
   the Data sources page. Then commit and open a pull request as usual.

## Which pattern?

| The provider publishes… | Pattern in `_template.py` | Example | Real data values? |
|---|---|---|---|
| Map tiles (URL with `{z}/{x}/{y}`) | A | `gibs_landsat.py` | No, images only |
| A WMS service (common for USDA, NOAA, USGS) | B | — | No, images only |
| Vector files (GeoJSON, shapefile) | C | — | Yes |
| NASA Earthdata files (needs login) | D | `imerg_monthly.py` | Yes |

A and B are quickest. With C and D you have the actual values, so you can also select regions, average or compare years.

**NASA Earthdata (pattern D)** needs your login in `.env` (see [CONTRIBUTING.md](../../../CONTRIBUTING.md#24-add-your-logins-only-for-nasa-data)).
Files are downloaded once into `data/raw/`. If the website is built without a login, the layer is left out
with a warning. If a download fails with an authorisation error, log in at <https://urs.earthdata.nasa.gov>,
open **Applications → Authorized Apps**, and approve the app named in the error (for example *NASA GESDISC DATA ARCHIVE*).

## Example: `imerg_monthly.py`

NASA's monthly precipitation, downloaded with `earthaccess`:

```python
def add_to_map(m, show):    # m = the map, show = switched on when the map opens?
    # Download the file (only the first time; afterwards it's reused from data/raw/)
    [path] = earthdata.download("GPM_3IMERGM", "07", temporal=("2023-12-01", "2023-12-28"))
    # Open it and take the variable we want
    with xr.open_dataset(path, engine="h5netcdf", group="Grid") as ds:
        precip = ds["precipitation"].isel(time=0) * 24  # mm/hour -> mm/day
    # Draw it as a coloured image over the US, with a legend
    earthdata.add_raster(m, precip, name="Precipitation, Dec 2023 (IMERG)",
                         caption="Precipitation (mm/day)", cmap="Blues", vmin=0, vmax=8, show=show)


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
    license="NASA open data. Cite: Huffman et al., ...",
    add_to_map=add_to_map,
)
```

For the simplest case, see `gibs_landsat.py`: it only passes a tile URL to folium.

## Status

Whether public data stays available is part of our research, so please fill in `status` carefully:

- **Active**: maintained and updated as described.
- **At risk**: affected by funding cuts or announced changes, or not updated for longer than expected.
- **Migrating**: moving to a new website, format or access method. Put the date and new location in `notes`.
- **Discontinued**: no longer updated or available. Put since when in `notes`.

Use `notes` for anything surprising too: broken links, login problems, confusing documentation.
