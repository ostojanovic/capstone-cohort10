# US Agriculture & Climate Data Map

Capstone project of **Cohort 10 of the [Climatebase Fellowship](https://climatebase.org/)**.

## Why

Publicly available data is not the same as usable data. Each US agency publishes its own data on its own
website, in its own format, with its own documentation and access method. Links break, logins fail, and
datasets stop being updated. Even when a dataset is technically public, people often don't know it exists
or how to reach it. Before analysis can even start, climate and geospatial sources have to be aligned in
time and space (for example, state vs. county level) and their collection methods understood. Public data
can also be affected by government funding cuts, which exposes the teams that depend on it.

This hits small climate-tech teams, researchers and nonprofits hardest, because they rarely have dedicated
data engineering capacity.

## What we do

We research and showcase how **publicly available US climate and Earth observation datasets** can be found,
accessed, combined and used in practice. Rather than cataloguing everything, we go in depth on three
connected use cases:

- **Agriculture**: where and what is farmed, and how it changes over time
- **Droughts**: where water is scarce and how this affects farmland
- **El Niño**: how this climate pattern shifts precipitation and drought risk across the US

For each use case we document what we learn about the sources along the way: where to get them, how to access them,
their spatial and temporal resolution, how often they are updated, and their current status.

The results are published as an interactive website built with [Quarto](https://quarto.org) and Python.
It has a map for each use case, a blog, and Jupyter notebooks with our analyses.

> **Status:** early stage. The map currently shows real NASA satellite layers together with
> *illustrative placeholder* markers and areas. These are not real data yet.

## Repository structure

```
├── _quarto.yml          # website configuration (navigation, theme, execution)
├── index.qmd            # home page: one interactive map per topic
├── sources.qmd          # data sources page: details of every dataset
├── about.qmd            # about page, disclaimer, licenses and team
├── blog/
│   ├── index.qmd        # blog listing page
│   └── posts/           # one folder per post (index.qmd or index.ipynb)
├── src/capstone/        # Python package used by the pages
│   ├── sources/         # one file per data source: its details and how to draw it on the map
│   │   └── _template.py # copy this to add a new source
│   ├── earthdata.py     # NASA Earthdata helpers (earthaccess login, download, drawing grids)
│   └── topics.py        # the three use cases and which sources each one shows
├── data/
│   ├── raw/             # downloaded data (not committed)
│   └── processed/       # cleaned data (not committed)
├── environment.yml      # conda environment (Python, Jupyter, Quarto, libraries)
├── .env.example         # template for your logins: copy to .env (never committed)
└── pyproject.toml       # makes src/capstone installable
```

## Setup

> **New to the project or to GitHub?** Follow the step-by-step guide in [CONTRIBUTING.md](CONTRIBUTING.md).
> It covers installing the tools, cloning, the conda environment, branches, commits and pull requests.
> The short version is below.

You need [conda](https://docs.conda.io/en/latest/miniconda.html) (Miniconda or Anaconda).
Quarto is installed into the environment, so you don't need a separate install.

```bash
git clone git@github.com:ostojanovic/capstone-cohort10.git
cd capstone-cohort10
conda env create -f environment.yml
conda activate capstone-cohort10
python -m ipykernel install --user --name capstone-cohort10 --display-name "Python (capstone-cohort10)"
```

The last command registers the environment as a Jupyter kernel. Quarto uses it to run the pages, and you
can select it in JupyterLab or VS Code. You only need to run it once.

Some data sources need a free login (for example NASA Earthdata, which we access with `earthaccess`).
Copy `.env.example` to `.env` and fill in your logins. Git ignores `.env`, so it is never committed.
See [CONTRIBUTING.md, section 2.7](CONTRIBUTING.md#27-add-your-logins-env-file).

If `environment.yml` changes later, update your environment with:

```bash
conda env update -f environment.yml --prune
```

## Working on the website

```bash
quarto preview    # live preview in the browser, reloads on save
quarto render     # build the full site into _site/
```

- **Data sources**: each dataset is one Python file in `src/capstone/sources/`, describing the dataset
  and how to draw it on the map. To add one, copy `_template.py`. See
  [CONTRIBUTING.md, section 4](CONTRIBUTING.md#4-adding-a-data-source).
- **Maps**: `src/capstone/topics.py` lists which sources each use case shows. `index.qmd` only calls `show_topic(...)`.
- **New blog post**: create a folder `blog/posts/YYYY-MM-DD-short-title/` with an `index.qmd` or
  `index.ipynb` file. Copy the header of an existing post. It appears on the Blog page automatically.
- **Pages with Python code** need `jupyter: capstone-cohort10` in their header (see `index.qmd`). Otherwise
  Quarto may pick a Jupyter kernel from a different environment. For `.ipynb` files, select the
  "Python (capstone-cohort10)" kernel instead.
- **Notebooks**: Quarto ignores files and folders whose names start with `_`. Use that for scratch
  notebooks you don't want published.
- **Freeze**: Quarto stores executed results in `_freeze/` and only re-runs a page when its source changes.
  Commit `_freeze/` along with your changes.

## Data sources

All data belongs to its respective owners and is used under their terms. We do not redistribute raw data.
Download it from the original source.

| Dataset | Provider | Used for | Terms |
|---|---|---|---|
| Base map tiles | © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors | Base map | [ODbL](https://opendatacommons.org/licenses/odbl/), attribution required. [Tile usage policy](https://operations.osmfoundation.org/policies/tiles/) |
| Landsat WELD true-colour annual composite | NASA [GIBS](https://nasa-gibs.github.io/gibs-api-docs/) | Agriculture | NASA open data policy |
| IMERG precipitation rate | NASA GPM via [GIBS](https://nasa-gibs.github.io/gibs-api-docs/) | Droughts, El Niño | NASA open data policy |
| IMERG monthly precipitation (GPM_3IMERGM v07) | [NASA GES DISC](https://disc.gsfc.nasa.gov/datasets/GPM_3IMERGM_07/summary) | Droughts, El Niño | NASA open data policy. Cite Huffman et al. |

<!-- Add a row for every dataset you start using, including the provider's preferred citation. -->
The full details of every dataset (access, resolution, update frequency, status) are on the website's
**Data sources** page, generated from `src/capstone/sources/`.

We acknowledge the use of imagery provided by services from NASA's Global Imagery Browse Services (GIBS),
part of NASA's Earth Science Data and Information System (ESDIS).

## Disclaimer

- This project is for **educational and research purposes only**. It is not a commercial product.
- It is **not affiliated with or endorsed by** Climatebase, NASA, USDA, NOAA or any other data provider.
  Mentioning a dataset or organisation does not imply its endorsement.
- **All data belongs to its respective owners** and is subject to their licenses and terms of use.
  Anyone reusing the data must follow those terms.
- Maps, analyses and figures are provided **"as is", without any warranty** of accuracy, completeness
  or timeliness. They must **not be used for agricultural, financial, insurance or emergency decisions**.
  Please use official sources for that, such as [drought.gov](https://www.drought.gov) or the
  [NOAA Climate Prediction Center](https://www.cpc.ncep.noaa.gov).
- Views and conclusions are those of the authors. They do not represent Climatebase or any data provider.
- If you are a data owner and have concerns about how your data is used here, please
  [open an issue](https://github.com/ostojanovic/capstone-cohort10/issues) and we will address it promptly.

## License

- **Code** in this repository is released under the [MIT License](LICENSE).
- **Written content and figures** we created (blog posts, page text, our own charts and maps) are licensed under
  [Creative Commons Attribution 4.0 (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/). You may share
  and adapt them, as long as you credit the project.
- **Third-party data and imagery** are not covered by either license. They remain under their original
  terms (see [Data sources](#data-sources)).

## Team

<!-- TODO: add team members (name, role, GitHub/LinkedIn). Keep this in sync with the Team section in about.qmd -->
Climatebase Fellowship Cohort 10 capstone team.
