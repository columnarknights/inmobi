"""Orchestrates a full investigation: detect -> decompose -> drill-down ->
narrate, with every ClickHouse query and the final LLM call wrapped in a
Tracer span so the whole thing is auditable end to end.
"""

import json
from datetime import date, datetime, timedelta

from . import attribution, baseline
from . import narrate as narrate_mod
from .db import get_client
from .tracing import Tracer

DEFAULT_METRICS = ["revenue", "fill_rate", "ecpm", "requests", "ctr"]


def parse_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def investigation_id(metric: str, start: date, end: date) -> str:
    return f"{metric}_{start}_{end}"


def _persist_investigation(
    client, result: dict, current: tuple[date, date], baseline_range: tuple[date, date]
) -> None:
    """Writes the investigation to the `investigations` table — the only
    thing the LibreChat follow-up flow is allowed to read (see
    mcp_server.get_investigation/drill_deeper). Keeps the chat path off raw
    fact_events entirely, not just discouraged from it by a prompt."""
    client.insert(
        "investigations",
        [[
            result["id"],
            result["metric"],
            current[0],
            current[1],
            baseline_range[0],
            baseline_range[1],
            result["drill_factor"],
            json.dumps(result["decomposition"], default=str),
            json.dumps(result["drill_down"], default=str),
            result["narrative"],
            result["langfuse_trace_url"] or "",
            result["local_trace_path"] or "",
        ]],
        column_names=[
            "id", "metric", "current_window_start", "current_window_end",
            "baseline_window_start", "baseline_window_end", "drill_factor",
            "decomposition", "drill_down", "narrative", "langfuse_trace_url", "local_trace_path",
        ],
    )


def resolve_range(client, start: str | None, end: str | None) -> tuple[date, date]:
    if start and end:
        return parse_date(start), parse_date(end)
    row = client.query("SELECT min(event_date), max(event_date) FROM fact_events").result_rows[0]
    lo, hi = row[0], row[1]
    return (parse_date(start) if start else lo, parse_date(end) if end else hi)


def scan(
    start: date, end: date, metrics: list[str] | None = None, lookback_weeks: int = 4
) -> list[dict]:
    """Detect-only pass: which days, for which metrics, deviate from their
    like-for-like baseline. No drill-down yet."""
    metrics = metrics or DEFAULT_METRICS
    client = get_client()
    out = []
    with Tracer(
        "scan", input={"start": str(start), "end": str(end), "metrics": metrics, "lookback_weeks": lookback_weeks}
    ) as tracer:
        for metric in metrics:
            with tracer.span(f"daily_series[{metric}]", input={"metric": metric}) as span:
                series = baseline.daily_series(client, metric, start - timedelta(weeks=lookback_weeks), end)
                span.set_output({"n_days_fetched": len(series)})

            with tracer.span(f"detect_anomalies[{metric}]", input={"lookback_weeks": lookback_weeks}) as span:
                anomalies = baseline.detect_anomalies(series, metric, lookback_weeks=lookback_weeks)
                incidents = baseline.merge_into_incidents(anomalies)
                span.set_output(
                    {
                        "n_anomalous_days": len(anomalies),
                        "incidents": [
                            {"start": str(i.start), "end": str(i.end), "peak_rel_delta": round(i.peak.rel_delta, 4)}
                            for i in incidents
                        ],
                    }
                )
            out.append({"metric": metric, "incidents": incidents})
        tracer.set_output({"n_incidents_total": sum(len(e["incidents"]) for e in out)})
    return out


def _round(x, n=4):
    try:
        return round(float(x), n)
    except (TypeError, ValueError):
        return x


def _segment_dict(s: attribution.SegmentResult) -> dict:
    return {
        "dimension": s.dimension,
        "value": s.value,
        "explanatory_power": _round(s.ep, 3),
        "lift": _round(s.lift, 2),
        "volume_share_baseline": _round(s.volume_share_b, 4),
        "volume_share_current": _round(s.volume_share_c, 4),
        "rate_baseline": _round(s.rate_b, 6),
        "rate_current": _round(s.rate_c, 6),
        "requests_baseline": s.requests_b,
        "requests_current": s.requests_c,
        "ruled_out": s.ruled_out,
    }


def summarize_drill(level: attribution.DrillLevel, top_n: int = 5) -> dict:
    out = {
        "factor": level.factor,
        "filters": [{"dimension": d, "value": v} for d, v in level.filters],
        "dimensions_checked": {},
    }
    for dim, segs in level.dimension_results.items():
        out["dimensions_checked"][dim] = {
            "top_segments": [_segment_dict(s) for s in segs[:top_n]],
            "n_segments_checked": len(segs) + len(level.excluded.get(dim, [])),
            "n_excluded_low_volume": len(level.excluded.get(dim, [])),
        }
    out["primary_segment"] = _segment_dict(level.primary) if level.primary else None
    if level.child:
        out["deeper"] = summarize_drill(level.child, top_n)
    return out


def _build_payload(metric, current_start, current_end, baseline_range, decomposition, drill) -> dict:
    return {
        "anomaly": {
            "metric": metric,
            "current_window": [str(current_start), str(current_end)],
            "baseline_window": [str(baseline_range[0]), str(baseline_range[1])],
            "baseline_method": "like-for-like: same weekday(s), one week prior",
        },
        "revenue_decomposition": {
            "baseline_totals": decomposition.baseline,
            "current_totals": decomposition.current,
            "baseline_factors": {k: _round(v, 6) for k, v in decomposition.baseline_factors.items()},
            "current_factors": {k: _round(v, 6) for k, v in decomposition.current_factors.items()},
            "revenue_delta": _round(decomposition.revenue_delta, 2),
            "revenue_rel_delta": _round(decomposition.revenue_rel_delta, 4),
            "factor_contributions_to_revenue_delta": {
                k: _round(v, 2) for k, v in decomposition.factor_contributions.items()
            },
            "factor_rel_deltas": {k: _round(v, 4) for k, v in decomposition.factor_rel_deltas.items()},
        },
        "drill_down": summarize_drill(drill),
    }


def investigate(metric: str, incident_start: date, incident_end: date, max_depth: int = 2) -> dict:
    client = get_client()
    current = (incident_start, incident_end)
    baseline_range = (incident_start - timedelta(days=7), incident_end - timedelta(days=7))

    with Tracer(
        "investigate",
        input={
            "metric": metric,
            "current_window": [str(incident_start), str(incident_end)],
            "baseline_window": [str(baseline_range[0]), str(baseline_range[1])],
        },
    ) as tracer:
        with tracer.span("window_aggregate[baseline]", input={"range": [str(baseline_range[0]), str(baseline_range[1])]}) as span:
            baseline_agg = attribution.window_aggregate(client, *baseline_range)
            span.set_output(baseline_agg)

        with tracer.span("window_aggregate[current]", input={"range": [str(current[0]), str(current[1])]}) as span:
            current_agg = attribution.window_aggregate(client, *current)
            span.set_output(current_agg)

        with tracer.span("decompose_revenue") as span:
            decomposition = attribution.decompose_revenue(baseline_agg, current_agg)
            span.set_output(
                {
                    "revenue_delta": decomposition.revenue_delta,
                    "revenue_rel_delta": decomposition.revenue_rel_delta,
                    "factor_contributions": decomposition.factor_contributions,
                }
            )

        if metric == "revenue":
            drill_factor = max(
                attribution.REVENUE_FACTORS,
                key=lambda f: abs(decomposition.factor_contributions.get(f, 0.0)),
            )
        elif metric in attribution.REVENUE_FACTORS:
            drill_factor = metric
        else:
            drill_factor = metric  # e.g. ctr: quality signal, investigated directly

        with tracer.span(f"drill_down[{drill_factor}]", input={"factor": drill_factor, "max_depth": max_depth}) as span:
            drill = attribution.drill_down(client, drill_factor, baseline_range, current, max_depth=max_depth)
            span.set_output(summarize_drill(drill))

        payload = _build_payload(metric, incident_start, incident_end, baseline_range, decomposition, drill)
        narrative = narrate_mod.narrate(payload, tracer)

        result = {
            "id": investigation_id(metric, incident_start, incident_end),
            "metric": metric,
            "current_window": [str(incident_start), str(incident_end)],
            "baseline_window": [str(baseline_range[0]), str(baseline_range[1])],
            "drill_factor": drill_factor,
            "decomposition": payload["revenue_decomposition"],
            "drill_down": payload["drill_down"],
            "narrative": narrative,
            "local_trace_path": None,
            "langfuse_trace_url": tracer.trace_url,
        }
        tracer.set_output({"narrative": narrative})

    result["local_trace_path"] = str(tracer.local_trace_path) if tracer.local_trace_path else None
    _persist_investigation(client, result, current, baseline_range)
    return result
