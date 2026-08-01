"""Dashboard + incident-report web app.

Serves live ClickHouse-backed timeseries/detection data and the saved
investigation results (out/*.json) as JSON, plus the static dashboard/
incident-detail pages. Every number shown is either a live query result or a
result already produced (and traced) by the CLI pipeline — nothing here
invents data.
"""

import json
from datetime import date
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import baseline, pipeline
from .config import settings
from .db import get_client
from .metrics import DIMENSIONS, METRICS

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "out"
WEBAPP_DIR = Path(__file__).resolve().parent / "webapp"

app = FastAPI(title="InMobi RCA Dashboard")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


@app.get("/api/meta")
def meta():
    client = get_client()
    row = client.query("SELECT min(event_date), max(event_date), count() FROM fact_events").result_rows[0]
    return {
        "min_date": str(row[0]),
        "max_date": str(row[1]),
        "row_count": int(row[2]),
        "metrics": list(METRICS.keys()),
        "dimensions": DIMENSIONS,
        "librechat_base_url": settings.librechat_base_url,
        "librechat_followup_agent_id": settings.librechat_followup_agent_id,
    }


@app.get("/api/timeseries")
def timeseries(metric: str, start: str, end: str, lookback_weeks: int = 4):
    if metric not in METRICS:
        raise HTTPException(400, f"Unknown metric: {metric}")
    client = get_client()
    start_d, end_d = pipeline.parse_date(start), pipeline.parse_date(end)
    from datetime import timedelta

    series = baseline.daily_series(client, metric, start_d - timedelta(weeks=lookback_weeks), end_d)
    anomalies = baseline.detect_anomalies(series, metric, lookback_weeks=lookback_weeks)
    anomaly_by_date = {a.event_date: a for a in anomalies}
    points = [
        {
            "date": str(p.event_date),
            "value": p.value,
            "is_anomaly": p.event_date in anomaly_by_date,
            "baseline_expected": anomaly_by_date[p.event_date].baseline_median if p.event_date in anomaly_by_date else None,
            "rel_delta": anomaly_by_date[p.event_date].rel_delta if p.event_date in anomaly_by_date else None,
        }
        for p in series
        if p.event_date >= start_d
    ]
    return {"metric": metric, "points": points}


@app.get("/api/scan")
def scan(start: str, end: str, metrics: str | None = None, lookback_weeks: int = 4):
    metric_list = metrics.split(",") if metrics else None
    start_d, end_d = pipeline.parse_date(start), pipeline.parse_date(end)
    results = pipeline.scan(start_d, end_d, metric_list, lookback_weeks)
    out = []
    for entry in results:
        for inc in entry["incidents"]:
            peak = inc.peak
            out.append(
                {
                    "metric": entry["metric"],
                    "start": str(inc.start),
                    "end": str(inc.end),
                    "peak_date": str(peak.event_date),
                    "rel_delta": peak.rel_delta,
                    "robust_z": peak.robust_z,
                    "direction": peak.direction,
                }
            )
    return {"incidents": out}


@app.post("/api/investigate")
def investigate(metric: str, start: str, end: str, max_depth: int = 2):
    if metric not in METRICS:
        raise HTTPException(400, f"Unknown metric: {metric}")
    result = pipeline.investigate(metric, pipeline.parse_date(start), pipeline.parse_date(end), max_depth=max_depth)
    OUT_DIR.mkdir(exist_ok=True)
    fname = f"{result['metric']}_{result['current_window'][0]}_{result['current_window'][1]}.json"
    with open(OUT_DIR / fname, "w") as f:
        json.dump(result, f, indent=2, default=str)
    result["id"] = fname
    return result


def _summarize_incident_file(path: Path) -> dict:
    with open(path) as f:
        data = json.load(f)
    return {
        "id": path.name,
        "metric": data.get("metric"),
        "current_window": data.get("current_window"),
        "baseline_window": data.get("baseline_window"),
        "revenue_rel_delta": data.get("decomposition", {}).get("revenue_rel_delta"),
        "revenue_delta": data.get("decomposition", {}).get("revenue_delta"),
        "primary_segment": (data.get("drill_down") or {}).get("primary_segment"),
        "narrative": data.get("narrative"),
        "langfuse_trace_url": data.get("langfuse_trace_url"),
    }


@app.get("/api/incidents")
def list_incidents():
    if not OUT_DIR.exists():
        return {"incidents": []}
    files = sorted(OUT_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    return {"incidents": [_summarize_incident_file(p) for p in files]}


@app.get("/api/incidents/{incident_id}")
def get_incident(incident_id: str):
    path = OUT_DIR / incident_id
    if not path.exists() or path.parent != OUT_DIR:
        raise HTTPException(404, "Not found")
    with open(path) as f:
        return json.load(f)


app.mount("/", StaticFiles(directory=str(WEBAPP_DIR), html=True), name="webapp")
