"""The three use cases shown on the map page, and which data sources each one uses.

The markers and shapes in `examples` are illustrative placeholders, not real data.
Remove them once a topic has real data sources.
"""

from dataclasses import dataclass, field
from typing import Callable

import folium
from IPython.display import Markdown, display

from capstone.earthdata import EarthdataLoginMissing
from capstone.sources import SOURCES

US_CENTER = (39.5, -98.35)


@dataclass
class Topic:
    name: str
    sources: list[str]                 # source ids (see capstone/sources), drawn in this order
    shown: list[str]                   # the sources that are switched on when the map opens
    planned: list[str] = field(default_factory=list)          # sources we still want to add
    examples: Callable[[], list] | None = None                # placeholder shapes, to be removed


def _agriculture_examples() -> list:
    points = [(36.7, -119.8), (42.0, -93.5), (38.5, -98.0), (27.5, -81.0)]
    return [folium.Marker(p, popup="Example point: farmland area") for p in points]


def _drought_examples() -> list:
    areas = [
        ((35.0, -111.0), 450_000, "#c8963c", 0.35),
        ((37.0, -120.0), 300_000, "#a8531f", 0.35),
        ((32.0, -100.0), 350_000, "#c8963c", 0.3),
    ]
    return [
        folium.Circle(loc, radius=r, color=c, fill=True, fill_opacity=o, popup="Example drought area")
        for loc, r, c, o in areas
    ]


TOPICS = {
    t.name: t
    for t in [
        Topic(
            name="Agriculture",
            sources=["gibs_landsat"],
            shown=["gibs_landsat"],
            planned=["Cropland data"],
            examples=_agriculture_examples,
        ),
        Topic(
            name="Droughts",
            sources=["gibs_imerg_rate", "imerg_monthly"],
            shown=["gibs_imerg_rate"],
            planned=["Drought index data"],
            examples=_drought_examples,
        ),
        Topic(
            name="El Niño",
            sources=["imerg_monthly", "gibs_imerg_rate"],
            shown=["imerg_monthly"],
            planned=["Ocean / climate index data (e.g. ENSO index)"],
        ),
    ]
}


def topic_map(name: str, height: int = 520) -> tuple[folium.Figure, list[str]]:
    """Build the interactive map for one topic. Also returns the sources that could not be loaded."""
    topic = TOPICS[name]
    fig = folium.Figure(width="100%", height=f"{height}px")
    m = folium.Map(location=US_CENTER, zoom_start=4, tiles="OpenStreetMap").add_to(fig)

    skipped = []
    for source_id in topic.sources:
        try:
            SOURCES[source_id].add_to_map(m, source_id in topic.shown)
        except EarthdataLoginMissing:
            skipped.append(source_id)

    if topic.examples:
        group = folium.FeatureGroup(name=f"{name} (example placeholders)")
        for shape in topic.examples():
            shape.add_to(group)
        group.add_to(m)

    folium.LayerControl(collapsed=False, position="topright").add_to(m)
    return fig, skipped


def sources_table(source_ids: list[str]) -> str:
    """Markdown table with the key facts about each source."""
    rows = ["| Dataset | Provider | Resolution | Updated | Status |", "|---|---|---|---|---|"]
    for s in (SOURCES[i] for i in source_ids):
        rows.append(f"| [{s.name}]({s.url}) | {s.provider} | {s.spatial_resolution} "
                    f"| {s.update_frequency} | {s.status} |")
    return "\n".join(rows)


def show_topic(name: str) -> None:
    """Display a topic's map followed by its data sources."""
    topic = TOPICS[name]
    fig, skipped = topic_map(name)
    display(fig)

    text = f"**Data sources for {name}**\n\n{sources_table(topic.sources)}\n"
    if topic.planned:
        text += "\n**Coming soon:** " + ", ".join(topic.planned) + "\n"
    if skipped:
        names = ", ".join(SOURCES[i].name for i in skipped)
        text += f"\n::: {{.callout-warning}}\nNot shown on the map (no Earthdata login when this page was built): {names}\n:::\n"
    display(Markdown(text))
