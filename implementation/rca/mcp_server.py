"""MCP server exposing this project's validated investigation pipeline as
tools, so a chat client (LibreChat) can trigger the exact same deterministic
ClickHouse analysis + grounded narration as the CLI — not have the chat model
freehand its own SQL or invent numbers.

Run standalone: `python -m rca.mcp_server` (HTTP transport, for LibreChat).
"""

from . import baseline, pipeline
from .db import get_client
from .metrics import DIMENSIONS, METRICS

try:
    from fastmcp import FastMCP
except ImportError as e:  # pragma: no cover
    raise SystemExit("Install the optional MCP extra: pip install fastmcp") from e

mcp = FastMCP(
    "inmobi-rca",
    instructions=(
        "Tools for investigating anomalies in an ad-tech metrics dataset stored in ClickHouse "
        "(requests, fills, impressions, clicks, revenue across app/device/geo/advertiser dimensions). "
        "Prefer investigate_incident for root-cause questions: it runs the same deterministic "
        "ClickHouse decomposition + segment-ranking pipeline as the project's CLI and returns "
        "real, reproducible numbers. Use scan_for_incidents first if the user hasn't named a "
        "specific window."
    ),
)


@mcp.tool
def list_metrics_and_dimensions() -> dict:
    """List the metrics (revenue, fill_rate, ecpm, requests, ctr, ...) and the
    dimensions (ad_format, category, region, device_model, ...) this system can
    investigate. Call this if unsure what's available before scanning or
    investigating."""
    return {"metrics": list(METRICS.keys()), "dimensions": DIMENSIONS}


@mcp.tool
def scan_for_incidents(
    start: str, end: str, metrics: list[str] | None = None, lookback_weeks: int = 4
) -> dict:
    """Detect anomalous days for one or more metrics between start and end
    (YYYY-MM-DD), comparing each day against a like-for-like baseline (same
    weekday, trailing weeks, trend-adjusted) rather than a flat average.
    Returns incident windows found (metric, dates, size of the move) without
    root-cause detail — call investigate_incident on a window to get the full
    diagnosis."""
    client = get_client()
    start_d, end_d = pipeline.parse_date(start), pipeline.parse_date(end)
    results = pipeline.scan(start_d, end_d, metrics, lookback_weeks)
    incidents = []
    for entry in results:
        for inc in entry["incidents"]:
            peak = inc.peak
            incidents.append(
                {
                    "metric": entry["metric"],
                    "window_start": str(inc.start),
                    "window_end": str(inc.end),
                    "peak_date": str(peak.event_date),
                    "peak_value": round(peak.value, 6),
                    "baseline_expected": round(peak.baseline_median, 6),
                    "relative_delta": round(peak.rel_delta, 4),
                    "robust_z_score": round(peak.robust_z, 2),
                }
            )
    return {"incidents": incidents}


@mcp.tool
def investigate_incident(metric: str, start: str, end: str, max_depth: int = 2) -> dict:
    """Run the full root-cause investigation for one metric over one window
    (YYYY-MM-DD dates): decomposes the revenue identity
    (revenue = requests x fill_rate x render_rate x eCPM/1000) to see which
    factor moved, then ranks every segment of every dimension by explanatory
    power and lift to find (or rule out) a localized cause, recursing one
    level deeper into the top segment. Returns a plain-language diagnosis plus
    every computed number behind it (decomposition, ranked segments, ruled-out
    segments) and a Langfuse trace URL proving how the diagnosis was derived.
    This is the same deterministic pipeline the CLI uses — numbers are exactly
    reproducible, never invented."""
    result = pipeline.investigate(metric, pipeline.parse_date(start), pipeline.parse_date(end), max_depth=max_depth)
    return result


@mcp.tool
def get_metric_timeseries(metric: str, start: str, end: str) -> dict:
    """Return the raw daily values for a metric between start and end
    (YYYY-MM-DD) — e.g. to describe a trend or spot-check a date range before
    deciding whether to investigate it."""
    client = get_client()
    series = baseline.daily_series(client, metric, pipeline.parse_date(start), pipeline.parse_date(end))
    return {"metric": metric, "series": [{"date": str(p.event_date), "value": round(p.value, 6)} for p in series]}


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8001, path="/mcp")
