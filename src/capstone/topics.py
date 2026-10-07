"""The three research topics shown on the map page.

Markers and shapes are illustrative placeholders, not real data. Replace each
topic's `features` function with layers built from the actual datasets.
"""

from dataclasses import dataclass
from typing import Callable

import folium
from IPython.display import Markdown, display

from capstone import layers

US_CENTER = (39.5, -98.35)


@dataclass
class Topic:
    name: str
    color: str
    sources: list[str]
    default_layer: str  # "landsat" or "precipitation": the satellite layer switched on first
    features: Callable[[], list]  # returns fresh folium objects (each can only be on one map)


def _agriculture_features() -> list:
    points = [(36.7, -119.8), (42.0, -93.5), (38.5, -98.0), (27.5, -81.0)]
    return [folium.Marker(p, popup="Example point: farmland area") for p in points]


def _drought_features() -> list:
    areas = [
        ((35.0, -111.0), 450_000, "#c8963c", 0.35),
        ((37.0, -120.0), 300_000, "#a8531f", 0.35),
        ((32.0, -100.0), 350_000, "#c8963c", 0.3),
    ]
    return [
        folium.Circle(loc, radius=r, color=c, fill=True, fill_opacity=o, popup="Example drought area")
        for loc, r, c, o in areas
    ]


def _el_nino_features() -> list:
    return [
        folium.Rectangle(
            [[25, -125], [49, -100]], color="#3b6fb0", fill=True, fill_opacity=0.2,
            popup="Example region: wetter than normal",
        ),
        folium.Rectangle(
            [[25, -100], [40, -75]], color="#3b6fb0", fill=True, fill_opacity=0.1, dash_array="6",
            popup="Example region: transition",
        ),
    ]


TOPICS = {
    t.name: t
    for t in [
        Topic(
            name="Agriculture",
            color="#2f6b4f",
            sources=["Landsat imagery (NASA GIBS, live layer)", "Cropland data source (placeholder)"],
            default_layer="landsat",
            features=_agriculture_features,
        ),
        Topic(
            name="Droughts",
            color="#c8963c",
            sources=["Precipitation (IMERG via NASA GIBS, live layer)", "Drought index data source (placeholder)"],
            default_layer="precipitation",
            features=_drought_features,
        ),
        Topic(
            name="El Niño",
            color="#3b6fb0",
            sources=["Precipitation (IMERG via NASA GIBS, live layer)", "Ocean / climate index data source (placeholder)"],
            default_layer="precipitation",
            features=_el_nino_features,
        ),
    ]
}


def topic_map(name: str, height: int = 520) -> folium.Figure:
    """Build the interactive map for one topic."""
    topic = TOPICS[name]
    fig = folium.Figure(width="100%", height=f"{height}px")
    m = folium.Map(location=US_CENTER, zoom_start=4, tiles="OpenStreetMap").add_to(fig)

    layers.landsat(show=topic.default_layer == "landsat").add_to(m)
    layers.precipitation(show=topic.default_layer == "precipitation").add_to(m)

    group = folium.FeatureGroup(name=f"{name} (example data)")
    for feature in topic.features():
        feature.add_to(group)
    group.add_to(m)

    folium.LayerControl(collapsed=False, position="topright").add_to(m)
    return fig


def show_topic(name: str) -> None:
    """Display a topic's map followed by its list of data sources."""
    display(topic_map(name))
    sources = "\n".join(f"- {s}" for s in TOPICS[name].sources)
    display(Markdown(f"**Data sources for {name}**\n\n{sources}"))
