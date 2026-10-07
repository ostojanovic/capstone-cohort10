"""All data sources shown on the website. To add one, see `_template.py`."""

from capstone.sources import gibs_imerg_rate, gibs_landsat, imerg_monthly
from capstone.sources.base import Source

SOURCES: dict[str, Source] = {
    s.id: s
    for s in [
        gibs_landsat.SOURCE,
        gibs_imerg_rate.SOURCE,
        imerg_monthly.SOURCE,
    ]
}
