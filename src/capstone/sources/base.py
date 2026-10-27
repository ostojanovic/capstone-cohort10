"""What every data source on the website describes about itself."""

from dataclasses import dataclass
from typing import Callable

import folium


@dataclass
class Source:
    id: str                   # short unique name, used in topics.py
    name: str                 # dataset name as the provider calls it
    provider: str             # agency or organisation that publishes it
    url: str                  # landing page where people can find the dataset
    access: str               # how we get it, e.g. "earthaccess (NASA Earthdata login)", "Tile service (WMTS)"
    spatial_resolution: str   # e.g. "0.1° (~10 km)", "county level"
    temporal_coverage: str    # e.g. "2000–present, monthly"
    update_frequency: str     # e.g. "Monthly, ~2 months delay"
    status: str               # e.g. "Active", "At risk", "Migrating", "Discontinued", with details in notes
    license: str              # terms of use, and the citation the provider asks for
    add_to_map: Callable[[folium.Map, bool], None]  # draws the data on a map; the bool says if it starts switched on
    notes: str = ""
