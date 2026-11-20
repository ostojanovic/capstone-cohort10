"""All data sources shown on the website. To add one, see `_template.py`."""

from capstone.sources import gibs_hls_landsat, gibs_imerg_rate, gibs_landsat, imerg_monthly, mei_v2, psl_indices, roni, streamflow
from capstone.sources.base import Source

SOURCES: dict[str, Source] = {
    s.id: s
    for s in [
        gibs_landsat.SOURCE,
        gibs_hls_landsat.SOURCE,
        gibs_imerg_rate.SOURCE,
        imerg_monthly.SOURCE,
        roni.SOURCE,
        mei_v2.SOURCE,
        psl_indices.SOURCE,
        streamflow.SOURCE,
    ]
}
