"""Multivariate ENSO Index Version 2 (MEI.v2) from NOAA's Physical Sciences Laboratory.

MEI combines five ocean and atmosphere variables into one index, so it shows that El Niño changes the
atmosphere as well as the ocean. It is one number per 2-month season, so it is drawn as a chart: how the
current year is developing compared with past strong El Niño events. Plain text file, no login.
"""

import pandas as pd
import plotly.graph_objects as go

from capstone.sources.base import Source
from capstone.sources.psl_indices import read_psl  # MEI uses the same file format

URL = "https://psl.noaa.gov/enso/mei/data/meiv2.data"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
EVENTS = {1982: "1982–83", 1997: "1997–98", 2015: "2015–16", 2023: "2023–24"}  # year each El Niño began
# Matplotlib's royalblue, steelblue, cornflowerblue and skyblue, adjusted a bit so they show up on the chart.
# Same order as EVENTS: the oldest event is the darkest, the most recent the lightest.
EVENT_BLUES = ["#1F3F9A", "#3A6EA5", "#4F86E0", "#5FA8DC"]
CURRENT_COLOUR = "#B22222"  # firebrick. For indianred, use "#CD5C5C"
FIRST_MONTH = 7  # like NOAA's ENSO blog charts: start in July of the year each event began, run 24 months
THRESHOLD = 0.5  # MEI at or above +0.5 counts as El Niño conditions, at or below -0.5 as La Niña
THRESHOLD_LINES = [("El Niño threshold", THRESHOLD, "#E07070"), ("La Niña threshold", -THRESHOLD, "#4682B4")]


def load() -> pd.Series:
    """Download MEI.v2. Each value is a 2-month average, dated by its second month (Dec–Jan 1979 = Jan 1979)."""
    return read_psl(URL)


def current_start_year(mei: pd.Series) -> int:
    """The year the current line starts, taken from the latest data instead of typed in.

    Until July it is still the year before, because the chart starts in July: in early 2027 the line keeps
    showing the event that began in 2026 instead of disappearing.
    """
    latest = mei.index.max()
    return latest.year if latest.month >= FIRST_MONTH else latest.year - 1


def month_year(start_year: int, position: int) -> tuple[int, int]:
    """The (month, year) at a position on the chart: 1 is July of the start year, 24 is June two years later."""
    months_in = FIRST_MONTH - 1 + position - 1
    return months_in % 12 + 1, start_year + months_in // 12


def event(mei: pd.Series, start_year: int) -> pd.Series:
    """The 24 months from July of the year an event began, numbered 1 to 24."""
    position = (mei.index.year - start_year) * 12 + mei.index.month - FIRST_MONTH + 1
    keep = (position >= 1) & (position <= 24)
    return pd.Series(mei.values[keep], index=position[keep])


def hover_dates(start_year: int, positions) -> list[str]:
    return [f"{MONTHS[m - 1]} {y}" for m, y in (month_year(start_year, p) for p in positions)]


def chart() -> go.Figure:
    """The current year compared with past strong El Niño events, month by month."""
    mei = load()
    fig = go.Figure()
    for (start_year, label), colour in zip(EVENTS.items(), EVENT_BLUES):
        s = event(mei, start_year)
        fig.add_scatter(
            x=s.index, y=s.values, name=label, mode="lines", line=dict(color=colour, width=2.5),
            customdata=hover_dates(start_year, s.index), hovertemplate="%{customdata}: %{y:+.2f}",
        )
    start = current_start_year(mei)
    now = event(mei, start)
    label = f"{start}–{str(start + 1)[-2:]}"  # named like the past events, e.g. 2026–27
    fig.add_scatter(
        x=now.index, y=now.values, name=label, mode="lines+markers+text",
        line=dict(color=CURRENT_COLOUR, width=4), marker=dict(size=8),
        text=[""] * (len(now) - 1) + [label], textposition="middle right",
        textfont=dict(color=CURRENT_COLOUR),
        customdata=hover_dates(start, now.index), hovertemplate="%{customdata}: %{y:+.2f}",
    )

    for name, y, colour in THRESHOLD_LINES:
        fig.add_hline(
            y=y, line_dash="dash", line_color=colour, line_width=1.5, annotation_text=name,
            annotation_position="bottom left", annotation_font_color=colour,
        )

    # A small tick every month and a label every 4 months, with the year on January (the years of the
    # current event). Like NOAA's chart: Sep, Jan 2027, May, Sep, Jan 2028, May.
    labelled = list(range(3, 25, 4))
    ticktext = []
    for p in labelled:
        m, y = month_year(start, p)
        ticktext.append(f"Jan {y}" if m == 1 else MONTHS[m - 1])
    fig.update_xaxes(
        tickvals=labelled, ticktext=ticktext, range=[0.5, 24.5], ticks="outside", ticklen=8,
        minor=dict(ticks="outside", ticklen=4, dtick=1, tick0=1, showgrid=False),
    )
    fig.update_layout(
        title="Multivariate ENSO Index (MEI v2): Present Year vs Past Strong El Niño Years",
        yaxis_title="Index value (above 0 = El Niño-like)", height=440, hovermode="closest",
        legend=dict(orientation="h", y=-0.2), margin=dict(t=60, b=40, l=70, r=70),  # equal sides: plot centred
    )
    return fig


SOURCE = Source(
    id="mei_v2",
    name="Multivariate ENSO Index Version 2 (MEI.v2)",
    provider="NOAA Physical Sciences Laboratory (PSL)",
    url="https://psl.noaa.gov/enso/mei/",
    access="Plain text file download, no login",
    spatial_resolution="Single index for the tropical Pacific (30°S–30°N, 100°E–70°W)",
    temporal_coverage="1979–present, 2-month seasons (DJ, JF, …)",
    update_frequency="Monthly",
    status="Active",
    license="NOAA open data. Credit NOAA PSL. Method: Wolter & Timlin (1993, 1998, 2011); Zhang et al. (2019)",
    chart=chart,
    notes=(
        "Combines five variables into one index without units: sea level pressure, sea surface temperature, "
        "east-west and north-south surface winds, and outgoing longwave radiation. Standardised against "
        "1980–2018. Since March 2024 the whole series is calculated from the JRA-3Q reanalysis instead of "
        "JRA-55; the older values are kept in a separate file. NOAA also publishes a ready-made time series, "
        "lifecycle plot and correlation maps on the MEI page. The ±0.5 El Niño / La Niña lines on our chart "
        "are a widely used convention for MEI; NOAA's MEI page itself only says positive values mean El Niño "
        "and negative values La Niña."
    ),
)
