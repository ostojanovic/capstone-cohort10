"""The three use cases shown on the map page, and which data sources each one uses."""

from dataclasses import dataclass, field
import folium
from IPython.display import HTML, Markdown, display

from capstone.earthdata import EarthdataLoginMissing
from capstone.sources import SOURCES

US_CENTER = (39.5, -98.35)


@dataclass
class Topic:
    name: str
    sources: list[str]                 # source ids (see capstone/sources), drawn in this order
    shown: list[str]                   # the sources that are switched on when the map opens
    planned: list[str] = field(default_factory=list)  # sources we still want to add
    center: tuple[float, float] = US_CENTER  # where the map opens: (latitude, longitude)
    zoom: int = 4                            # how far in the map opens: lower shows more of the world


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
            sources=["gibs_imerg_rate", "imerg_monthly", "noaa_departure"],
            shown=["gibs_imerg_rate", "noaa_departure"],
            planned=["Drought index data"],
        ),
        Topic(
            name="El Niño",
            sources=["imerg_monthly", "gibs_imerg_rate", "oisst", "roni", "mei_v2", "psl_indices"],
            shown=["oisst"],  # opens with just the sea surface temperature playing; precipitation can be ticked on
            center=(25, -140),  # zoomed out to show the Pacific and the US
            zoom=2,
        ),
    ]
}


# The box listing the map's layers: smaller than folium's default, in the website's font. ".leaflet-container" in
# front makes these rules win over Leaflet's own, which load later.
LAYER_LIST_STYLE = """
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;500&display=swap">
<style>
    .leaflet-container .leaflet-control-layers-expanded { padding: 4px 8px 4px 6px; }
    .leaflet-container .leaflet-control-layers, .leaflet-container .leaflet-control-layers label {
        font-family: "Roboto", "Helvetica Neue", Arial, sans-serif; font-size: 13px; line-height: 1.4; }
    .leaflet-container .leaflet-control-layers label { margin: 0; }
    .leaflet-container .leaflet-control-layers-selector { margin: 0 5px 0 0; vertical-align: -1px; }
    .leaflet-container .leaflet-control-layers-separator { margin: 3px -8px 3px -6px; }
</style>
"""


def topic_map(name: str, height: int = 520) -> tuple[folium.Figure, list[str]]:
    """Build the interactive map for one topic. Also returns the sources that could not be loaded."""
    topic = TOPICS[name]
    fig = folium.Figure(width="100%", height=f"{height}px")
    m = folium.Map(location=topic.center, zoom_start=topic.zoom, tiles="OpenStreetMap").add_to(fig)

    skipped = []
    for source_id in topic.sources:
        if SOURCES[source_id].add_to_map is None:  # e.g. an index, shown as a chart instead
            continue
        try:
            SOURCES[source_id].add_to_map(m, source_id in topic.shown)
        except EarthdataLoginMissing:
            skipped.append(source_id)

    folium.LayerControl(collapsed=False, position="topright").add_to(m)
    fig.header.add_child(folium.Element(LAYER_LIST_STYLE))
    if skipped:
        names = ", ".join(SOURCES[i].name for i in skipped)
        m.get_root().html.add_child(folium.Element(
            '<div style="position:absolute; bottom:24px; left:10px; z-index:1000; max-width:60%;'
            ' padding:6px 10px; background:#fff; border-left:3px solid #182d78; border-radius:2px;'
            f' font:13px Roboto, Arial, sans-serif; color:#22252d;">Not shown (no Earthdata login when this page was'
            f' built): {names}</div>'
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

    for s in (SOURCES[i] for i in topic.sources):
        if s.chart is not None:
            chart = s.chart()
            chart.update_layout(  # same look for every chart: plain white background, centred title
                template="plotly_white", plot_bgcolor="white", paper_bgcolor="white",
                title_x=0.5, title_xanchor="center", title_xref="paper",  # centred over the plot area
                legend_x=0.5, legend_xanchor="center",  # legend centred under the chart
                # same fonts and colours as the website: Roboto for text, Poppins in navy for the title
                font_family='Roboto, -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif',
                font_color="#22252d",
                title_font_family="Poppins, Roboto, Arial, sans-serif", title_font_color="#182d78",
                title_font_size=18,
                hoverlabel=dict(bgcolor="white", bordercolor="#d9d9d9", font_family="Roboto, Arial, sans-serif"),
            )
            chart.update_xaxes(gridcolor="#eeeeee", linecolor="#d9d9d9")
            chart.update_yaxes(zeroline=False, gridcolor="#eeeeee")  # the 0 line looks like the other grid lines
            chart.show(renderer="notebook_connected", config={"responsive": True})  # fills the page width
            # A chart on a hidden tab is drawn at a default 700 px wide. This redraws it at the full page
            # width when its tab is opened, so it sits in the middle of the page.
            display(HTML("<script>if (!window.resizeOnTabOpen) { window.resizeOnTabOpen = true; "
                         "document.addEventListener('shown.bs.tab', () => window.dispatchEvent(new Event('resize'))); }"
                         "</script>"))

    text = f"**Data sources for {name}**\n\n{sources_table(topic.sources)}\n"
    if topic.planned:
        text += "\n**Coming soon:** " + ", ".join(topic.planned) + "\n"
    display(Markdown(text))
