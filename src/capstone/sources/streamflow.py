"""Daily streamflow at USGS stream gauges in any US state, from the USGS Water Data API.

Registered so it is listed on the Data sources page. Not shown on a map or chart yet: use it in a notebook.
Every call needs either a state (full name) or a list of gauge ids:

    from capstone.sources import streamflow
    flow = streamflow.load(state="Washington")                          # last 30 days, every gauge in the state
    flow = streamflow.load("2025-10-01", "2026-09-30", state="Oregon")  # any date range
    flow = streamflow.load(gauge_ids=["USGS-12113000"])                 # only these gauges, in any state
    gauges = streamflow.gauges(state="Washington")                      # name, location, drainage area of active gauges
    gauges = streamflow.gauges(gauge_ids=flow["gauge_id"].unique())     # the gauges in your data, also closed ones

To select gauges by county, river, area or size, filter `gauges()` with pandas and pass the ids to `load()`:

    g = streamflow.gauges(state="Washington")
    big = g[g["drainage_area_sq_mi"] > 1000]
    flow = streamflow.load(gauge_ids=big["gauge_id"])

The API can also do these filters itself, which is faster for areas across many states (tested Nov 2026, not
built in here yet): `county_name` (with `state_name`), `bbox=west,south,east,north`, and CQL filters with
`filter-lang=cql-text`, e.g. `filter=hydrologic_unit_code LIKE '170300%'` (a watershed: codes are stored with
12 digits, so use "starts with"), `filter=drainage_area>1000` or `filter=state_name IN ('Washington','Oregon')`
(a comma list in `state_name` returns nothing). Docs: https://api.waterdata.usgs.gov/ogcapi/v1/

No login needed. A free API key (https://api.waterdata.usgs.gov/signup/) gives higher rate limits:
add `API_USGS_PAT=...` to `.env`, the same name USGS's own `dataretrieval` package uses.
"""

import os
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

from capstone.sources.base import Source

API = "https://api.waterdata.usgs.gov/ogcapi/v1/collections"
DISCHARGE = "00060"   # USGS parameter code: discharge (streamflow), cubic feet per second
DAILY_MEAN = "00003"  # USGS statistic code: mean of the day
ACTIVE_DAYS = 30      # a gauge counts as active if it reported within this many days
ROOT = Path(__file__).resolve().parents[3]


def _get(collection: str, params: dict) -> list[dict]:
    """All results of a query, following the API's "next page" links (at most 50,000 rows per page)."""
    load_dotenv(ROOT / ".env")
    headers = {"X-Api-Key": key} if (key := os.environ.get("API_USGS_PAT")) else {}
    url, params = f"{API}/{collection}/items", {"f": "json", "limit": 50_000, **params}
    rows = []
    while url:
        response = requests.get(url, params=params, headers=headers, timeout=120)
        response.raise_for_status()
        page = response.json()
        rows += [{**f["properties"], "geometry": f.get("geometry")} for f in page["features"]]
        url = next((link["href"] for link in page["links"] if link["rel"] == "next"), None)
        params = None  # the next link already contains the query
    return rows


def _check_where(state: str | None, gauge_ids: list[str] | None) -> None:
    if (state is None) == (gauge_ids is None):
        raise ValueError('Give either a state or a list of gauges, e.g. state="Washington" or '
                         'gauge_ids=["USGS-12113000"].')


def _daily_filter(state: str | None, gauge_ids: list[str] | None) -> dict:
    """Daily mean discharge at USGS gauges, either in one state or at the given gauges."""
    where = {"monitoring_location_id": ",".join(gauge_ids)} if gauge_ids is not None else {"state_name": state}
    return {**where, "parameter_code": DISCHARGE, "statistic_id": DAILY_MEAN, "agency_code": "USGS"}


def _no_data(state: str | None, gauge_ids: list[str] | None, what: str) -> ValueError:
    where = f"gauges {', '.join(gauge_ids)}" if gauge_ids is not None else f"state {state!r}"
    return ValueError(f"No streamflow found for {where} {what}. Check the spelling: states need their full "
                      f'name (e.g. "Oregon"), gauges their full id (e.g. "USGS-12113000").')


def _batches(gauge_ids: list[str] | None, size: int = 100) -> list[list[str] | None]:
    """Split a long list of gauges into several requests, to keep the URLs short. `None` stays one request."""
    if gauge_ids is None:
        return [None]
    return [gauge_ids[i:i + size] for i in range(0, len(gauge_ids), size)]


def load(start: str | date | None = None, end: str | date | None = None, state: str | None = None,
         gauge_ids: list[str] | None = None) -> pd.DataFrame:
    """Daily mean streamflow between `start` and `end` (default: the last 30 days).

    For every gauge in `state`, or for the gauges in `gauge_ids`: give exactly one of the two.
    One row per gauge and day. Recent values are "Provisional" and can still be revised by USGS.
    """
    _check_where(state, gauge_ids)
    end = pd.Timestamp(end or date.today()).date()
    start = pd.Timestamp(start or end - timedelta(days=30)).date()
    gauge_ids = None if gauge_ids is None else list(gauge_ids)
    rows = []
    for ids in _batches(gauge_ids):
        rows += _get("daily", {**_daily_filter(state, ids), "time": f"{start}/{end}"})
    if not rows:
        raise _no_data(state, gauge_ids, f"between {start} and {end}")
    df = pd.DataFrame(rows, columns=["monitoring_location_id", "time", "value", "approval_status"])
    df = df.rename(columns={"monitoring_location_id": "gauge_id", "time": "date", "value": "flow_cfs"})
    df["date"] = pd.to_datetime(df["date"])
    df["flow_cfs"] = pd.to_numeric(df["flow_cfs"])
    return df.sort_values(["gauge_id", "date"]).reset_index(drop=True)


def gauges(state: str | None = None, gauge_ids: list[str] | None = None) -> pd.DataFrame:
    """Name, location and drainage area of gauges. Give exactly one of `state` and `gauge_ids`.

    With `state`: the gauges there that reported streamflow in the last 30 days. With `gauge_ids`: exactly
    those gauges, including ones that have closed, e.g. the ids from `load()`.
    """
    _check_where(state, gauge_ids)
    if gauge_ids is None:
        latest = pd.DataFrame(_get("latest-daily", _daily_filter(state, None)))
        if latest.empty:
            raise _no_data(state, None, "at all")
        recent = pd.to_datetime(latest["time"]) >= pd.Timestamp(date.today() - timedelta(days=ACTIVE_DAYS))
        gauge_ids = sorted(latest.loc[recent, "monitoring_location_id"].unique())
    gauge_ids = list(gauge_ids)

    rows = []
    for ids in _batches(gauge_ids):
        rows += _get("monitoring-locations", {
            "id": ",".join(ids),
            "properties": "id,monitoring_location_name,county_name,drainage_area",
        })
    if not rows:
        raise _no_data(state, gauge_ids, "in the list of gauges")
    df = pd.DataFrame(rows)
    df["lon"] = df["geometry"].map(lambda g: g["coordinates"][0])
    df["lat"] = df["geometry"].map(lambda g: g["coordinates"][1])
    df = df.rename(columns={"id": "gauge_id", "monitoring_location_name": "name", "county_name": "county",
                            "drainage_area": "drainage_area_sq_mi"})
    return df[["gauge_id", "name", "county", "lat", "lon", "drainage_area_sq_mi"]].sort_values("gauge_id")


SOURCE = Source(
    id="streamflow",
    name="USGS daily streamflow (daily mean discharge) at stream gauges",
    provider="U.S. Geological Survey (USGS) Water Data for the Nation",
    url="https://waterdata.usgs.gov/",
    access="USGS Water Data API (api.waterdata.usgs.gov/ogcapi/v1), no login. Optional free API key",
    spatial_resolution="Individual stream gauges, any US state (e.g. ~250 active in Washington)",
    temporal_coverage="Varies by gauge, some since the late 1800s; daily",
    update_frequency="Daily, values for yesterday usually available today",
    status="Active",
    license="USGS public domain. Cite: U.S. Geological Survey, National Water Information System, "
            "https://doi.org/10.5066/F7P55KJN",
    notes="Recent values are provisional and can be revised. Not every gauge measures streamflow every day. "
          "USGS is retiring its old WaterServices API (waterservices.usgs.gov): service degrades from November 2026 "
          "and it is switched off on 22 February 2027. We use the new Water Data API that replaces it.",
)
