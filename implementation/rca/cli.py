import json
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from . import pipeline
from .db import get_client

console = Console()


@click.group()
def main():
    """Automated root-cause analyst for ad-metrics anomalies."""


@main.command()
@click.option("--host", default="127.0.0.1")
@click.option("--port", type=int, default=8000)
def serve(host, port):
    """Run the dashboard + incident-report web app."""
    import uvicorn

    uvicorn.run("rca.web:app", host=host, port=port, reload=False)


@main.command()
@click.option("--host", default="0.0.0.0")
@click.option("--port", type=int, default=8001)
def mcp_serve(host, port):
    """Run the MCP server exposing scan/investigate as tools (for LibreChat etc.)."""
    from .mcp_server import mcp

    mcp.run(transport="http", host=host, port=port, path="/mcp")


@main.command()
@click.option("--start", type=str, default=None, help="YYYY-MM-DD; defaults to the earliest date loaded")
@click.option("--end", type=str, default=None, help="YYYY-MM-DD; defaults to the latest date loaded")
@click.option("--metric", "metrics", multiple=True, help="Repeatable; defaults to revenue,fill_rate,ecpm,requests,ctr")
@click.option("--lookback-weeks", type=int, default=4)
def scan(start, end, metrics, lookback_weeks):
    """Detect anomalous days per metric (no drill-down)."""
    client = get_client()
    start_d, end_d = pipeline.resolve_range(client, start, end)
    results = pipeline.scan(start_d, end_d, list(metrics) or None, lookback_weeks)
    for entry in results:
        table = Table(title=f"{entry['metric']} — {len(entry['incidents'])} incident window(s)")
        table.add_column("Window")
        table.add_column("Peak date")
        table.add_column("Value")
        table.add_column("Baseline median")
        table.add_column("Rel. delta")
        table.add_column("Robust z")
        for inc in entry["incidents"]:
            peak = inc.peak
            table.add_row(
                f"{inc.start} .. {inc.end}",
                str(peak.event_date),
                f"{peak.value:.4f}",
                f"{peak.baseline_median:.4f}",
                f"{peak.rel_delta:+.1%}",
                f"{peak.robust_z:.2f}",
            )
        console.print(table)


@main.command()
@click.option("--metric", required=True)
@click.option("--start", required=True, help="YYYY-MM-DD")
@click.option("--end", required=True, help="YYYY-MM-DD")
@click.option("--max-depth", type=int, default=2)
def investigate(metric, start, end, max_depth):
    """Run the full drill-down + narration for one metric over one window."""
    result = pipeline.investigate(metric, pipeline.parse_date(start), pipeline.parse_date(end), max_depth=max_depth)
    _print_result(result)
    _save_result(result)


@main.command()
@click.option("--start", type=str, default=None)
@click.option("--end", type=str, default=None)
@click.option("--metric", "metrics", multiple=True)
@click.option("--lookback-weeks", type=int, default=4)
@click.option("--max-depth", type=int, default=2)
def auto(start, end, metrics, lookback_weeks, max_depth):
    """End to end: scan for anomalies, then investigate + narrate each one found."""
    client = get_client()
    start_d, end_d = pipeline.resolve_range(client, start, end)
    scan_results = pipeline.scan(start_d, end_d, list(metrics) or None, lookback_weeks)
    any_found = False
    for entry in scan_results:
        for inc in entry["incidents"]:
            any_found = True
            console.rule(f"[bold]{entry['metric']}[/bold]: {inc.start} .. {inc.end}")
            result = pipeline.investigate(entry["metric"], inc.start, inc.end, max_depth=max_depth)
            _print_result(result)
            _save_result(result)
    if not any_found:
        console.print(f"[yellow]No anomalies detected between {start_d} and {end_d} at current thresholds.[/yellow]")


def _print_result(result):
    console.print(Panel(result["narrative"], title=f"Diagnosis: {result['metric']} ({result['current_window'][0]}..{result['current_window'][1]})"))
    if result.get("langfuse_trace_url"):
        console.print(f"[dim]Langfuse trace: {result['langfuse_trace_url']}[/dim]")
    console.print(f"[dim]Local trace: {result.get('local_trace_path')}[/dim]")


def _save_result(result):
    out_dir = Path("out")
    out_dir.mkdir(exist_ok=True)
    fname = f"{result['metric']}_{result['current_window'][0]}_{result['current_window'][1]}.json"
    with open(out_dir / fname, "w") as f:
        json.dump(result, f, indent=2, default=str)
    console.print(f"[dim]Saved: {out_dir / fname}[/dim]")


if __name__ == "__main__":
    main()
