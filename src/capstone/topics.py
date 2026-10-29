"""The three use cases shown on the map page, and which data sources each one uses."""

from dataclasses import dataclass, field
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
    planned: list[str] = field(default_factory=list)  # sources we still want to add


TOPICS = {
    t.name: t
    for t in [
        Topic(
            name="Agriculture",
            sources=["gibs_landsat", "gibs_hls_landsat"],
            shown=["gibs_hls_landsat"],
            planned=["Cropland data"],
        ),
        Topic(
            name="Droughts",
            sources=["gibs_imerg_rate", "imerg_monthly"],
            shown=["gibs_imerg_rate"],
            planned=["Drought index data"],
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

    folium.LayerControl(collapsed=False, position="topright").add_to(m)
    if skipped:
        names = ", ".join(SOURCES[i].name for i in skipped)
        m.get_root().html.add_child(folium.Element(
            '<div style="position:absolute; bottom:24px; left:10px; z-index:1000; max-width:60%;'
            ' padding:6px 10px; background:#fff3cd; border:1px solid #c8963c; border-radius:4px;'
            f' font:13px sans-serif;">⚠️ Not shown (no Earthdata login when this page was built): {names}</div>'
        ))
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
    fig, _ = topic_map(name)  # missing sources are flagged on the map itself
    display(fig)

    text = f"**Data sources for {name}**\n\n{sources_table(topic.sources)}\n"
    if topic.planned:
        text += "\n**Coming soon:** " + ", ".join(topic.planned) + "\n"
    display(Markdown(text))
