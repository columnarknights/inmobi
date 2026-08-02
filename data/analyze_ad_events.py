"""
ad_events.parquet analysis
===========================
Computes core funnel/revenue metrics *chronologically*, aggregated into buckets of
INTERVAL_SECONDS (hardcoded config, default one day), optionally restricted to events
up to MAX_TIME_PROPORTION of the full event_time range (hardcoded config, default 1.0
= all events). For each metric, two versions are computed and plotted per bucket:
  - cumulative: derived only from events up to and including that bucket (expanding /
    cumulative-since-start window), so nothing is computed using future data relative
    to the point being plotted.
  - interval: derived only from events within that bucket alone (non-cumulative).

Outputs (all saved, none displayed):
    plot/requests.png
    plot/requests_interval.png
    plot/fills.png
    plot/fills_interval.png
    plot/fill_rate.png
    plot/fill_rate_interval.png
    plot/impressions.png
    plot/impressions_interval.png
    plot/render_rate.png
    plot/render_rate_interval.png
    plot/clicks.png
    plot/clicks_interval.png
    plot/ctr.png
    plot/ctr_interval.png
    plot/revenue.png
    plot/revenue_interval.png
    plot/ecpm.png
    plot/ecpm_interval.png
    plot/rpr.png
    plot/rpr_interval.png
    plot/combined_revenue_requests_fillrate_ecpm.png"""

import matplotlib
matplotlib.use("Agg")  # no display, just save files

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
from pathlib import Path

# ------------------------------------------------------------------
# Config
# ------------------------------------------------------------------
DATA_PATH = "./ad_events.parquet"
INTERVAL_SECONDS = 604400  # size of each aggregation bucket, in seconds (86400 = 1 day)
MAX_TIME_PROPORTION = 1.0  # keep events up to this proportion (0-1) of the full [min, max] event_time range
OUT_DIR = Path(f"./plots--interval={INTERVAL_SECONDS}s")
OUT_DIR.mkdir(parents=True, exist_ok=True)

REQUIRED_COLS = [
    "event_time", "app_id", "geo_device_id", "advertiser_id", "ad_format",
    "is_filled", "is_impression", "is_click", "revenue",
]

# ------------------------------------------------------------------
# 1. Load
# ------------------------------------------------------------------
print(f"Loading {DATA_PATH} ...")
df = pd.read_parquet(DATA_PATH, columns=REQUIRED_COLS)
print(f"Loaded {len(df):,} rows")

missing = set(REQUIRED_COLS) - set(df.columns)
if missing:
    raise ValueError(f"Missing expected columns: {missing}")

# ------------------------------------------------------------------
# 2. Chronological ordering
# ------------------------------------------------------------------
df["event_time"] = pd.to_datetime(df["event_time"])

t_min, t_max = df["event_time"].min(), df["event_time"].max()
cutoff_time = t_min + MAX_TIME_PROPORTION * (t_max - t_min)
df = df[df["event_time"] <= cutoff_time]

df = df.sort_values("event_time", kind="mergesort").reset_index(drop=True)

# Make sure the 0/1 indicator columns are numeric (not bool/object) so cumsum works cleanly.
for c in ["is_filled", "is_impression", "is_click"]:
    df[c] = df[c].astype("int64")
df["revenue"] = df["revenue"].astype("float64")

# ------------------------------------------------------------------
# 3. Expanding (cumulative, "past-data-only") aggregates per event
#    Row i's cumulative value uses only rows 0..i (i.e. event_time <= row i's event_time), so nothing here ever looks ahead in time.
# ------------------------------------------------------------------
df["cum_requests"]    = np.arange(1, len(df) + 1, dtype="int64")
df["cum_fills"]       = df["is_filled"].cumsum()
df["cum_impressions"] = df["is_impression"].cumsum()
df["cum_clicks"]      = df["is_click"].cumsum()
df["cum_revenue"]     = df["revenue"].cumsum()

# Ratio metrics, always sum/sum (here: cumsum/cumsum), never an average of per-row ratios.
df["fill_rate"]   = df["cum_fills"] / df["cum_requests"]
df["render_rate"] = df["cum_impressions"] / df["cum_fills"]
df["ctr"]         = df["cum_clicks"] / df["cum_impressions"]
df["ecpm"]        = df["cum_revenue"] / df["cum_impressions"] * 1000
df["rpr"]         = df["cum_revenue"] / df["cum_requests"]

# ------------------------------------------------------------------
# 4. Downsample to one point per day for plotting.
#    Taking the LAST row of each calendar day preserves the true "as-of-that-day, using only past+current data" cumulative value - it is not a recomputation, just a snapshot of the expanding series.
# ------------------------------------------------------------------
df["event_datetime"] = df["event_time"].dt.floor(f"{INTERVAL_SECONDS}s")

period = df.groupby("event_datetime", as_index=False).agg(
    period_requests=("event_datetime", "size"),
    period_fills=("is_filled", "sum"),
    period_impressions=("is_impression", "sum"),
    period_clicks=("is_click", "sum"),
    period_revenue=("revenue", "sum"),
)
period["period_fill_rate"]   = period["period_fills"] / period["period_requests"]
period["period_render_rate"] = period["period_impressions"] / period["period_fills"]
period["period_ctr"]         = period["period_clicks"] / period["period_impressions"]
period["period_ecpm"]        = period["period_revenue"] / period["period_impressions"] * 1000
period["period_rpr"]         = period["period_revenue"] / period["period_requests"]

agg_interval = df.groupby("event_datetime", as_index=False).last()
agg_interval = agg_interval.merge(period, on="event_datetime", how="left")
agg_interval = agg_interval.sort_values("event_datetime").reset_index(drop=True)

print(f"Date range: {agg_interval['event_datetime'].min()} -> {agg_interval['event_datetime'].max()}")
print(f"Days plotted: {len(agg_interval)}")

# ------------------------------------------------------------------
# 5. Plotting helpers
# ------------------------------------------------------------------
def style_time_axis(ax):
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    ax.tick_params(axis="x", rotation=45)
    ax.grid(True, alpha=0.3)


def plot_metric(x, y, title, ylabel, fname, color="#2563eb", fmt_pct=False, fmt_money=False):
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(x, y, color=color, linewidth=2, label=title)
    ax.set_title(f"{title} (cumulative, chronological - as of each {INTERVAL_SECONDS}s)")
    ax.set_xlabel("Date")
    ax.set_ylabel(ylabel)
    if fmt_pct:
        ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))
    if fmt_money:
        ax.yaxis.set_major_formatter(
            mticker.FuncFormatter(lambda v, _: f"${v:,.0f}")
        )
    style_time_axis(ax)
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(OUT_DIR / fname, dpi=150)
    plt.close(fig)
    print(f"Saved {fname}")


x = agg_interval["event_datetime"]

# ------------------------------------------------------------------
# 6. Individual metric plots
# ------------------------------------------------------------------
plot_metric(x, agg_interval["cum_requests"], "Requests", "Cumulative requests",
            "requests.png", color="#334155")
plot_metric(x, agg_interval["period_requests"], "Requests (per interval)", "Requests",
            "requests_interval.png", color="#334155")

plot_metric(x, agg_interval["cum_fills"], "Fills", "Cumulative fills",
            "fills.png", color="#0ea5e9")
plot_metric(x, agg_interval["period_fills"], "Fills (per interval)", "Fills",
            "fills_interval.png", color="#0ea5e9")

plot_metric(x, agg_interval["fill_rate"], "Fill rate", "Fill rate",
            "fill_rate.png", color="#0891b2", fmt_pct=True)
plot_metric(x, agg_interval["period_fill_rate"], "Fill rate (per interval)", "Fill rate",
            "fill_rate_interval.png", color="#0891b2", fmt_pct=True)

plot_metric(x, agg_interval["cum_impressions"], "Impressions", "Cumulative impressions",
            "impressions.png", color="#7c3aed")
plot_metric(x, agg_interval["period_impressions"], "Impressions (per interval)", "Impressions",
            "impressions_interval.png", color="#7c3aed")

plot_metric(x, agg_interval["render_rate"], "Render rate", "Render rate (impressions/fills)",
            "render_rate.png", color="#8b5cf6", fmt_pct=True)
plot_metric(x, agg_interval["period_render_rate"], "Render rate (per interval)", "Render rate (impressions/fills)",
            "render_rate_interval.png", color="#8b5cf6", fmt_pct=True)

plot_metric(x, agg_interval["cum_clicks"], "Clicks", "Cumulative clicks",
            "clicks.png", color="#db2777")
plot_metric(x, agg_interval["period_clicks"], "Clicks (per interval)", "Clicks",
            "clicks_interval.png", color="#db2777")

plot_metric(x, agg_interval["ctr"], "CTR", "Click-through rate",
            "ctr.png", color="#e11d48", fmt_pct=True)
plot_metric(x, agg_interval["period_ctr"], "CTR (per interval)", "Click-through rate",
            "ctr_interval.png", color="#e11d48", fmt_pct=True)

plot_metric(x, agg_interval["cum_revenue"], "Revenue", "Cumulative revenue ($)",
            "revenue.png", color="#16a34a", fmt_money=True)
plot_metric(x, agg_interval["period_revenue"], "Revenue (per interval)", "Revenue ($)",
            "revenue_interval.png", color="#16a34a", fmt_money=True)

plot_metric(x, agg_interval["ecpm"], "eCPM", "eCPM ($ per 1,000 impressions)",
            "ecpm.png", color="#ca8a04", fmt_money=True)
plot_metric(x, agg_interval["period_ecpm"], "eCPM (per interval)", "eCPM ($ per 1,000 impressions)",
            "ecpm_interval.png", color="#ca8a04", fmt_money=True)

plot_metric(x, agg_interval["rpr"], "Revenue per request (RPR)", "RPR ($)",
            "rpr.png", color="#ea580c", fmt_money=True)
plot_metric(x, agg_interval["period_rpr"], "Revenue per request (RPR) (per interval)", "RPR ($)",
            "rpr_interval.png", color="#ea580c", fmt_money=True)

# ------------------------------------------------------------------
# 7. Combined plot: Revenue, Requests, Fill rate, eCPM
#    Different units/scales -> 4 stacked subplots sharing one time axis, presented as a single figure/file ("together in one plot").
# ------------------------------------------------------------------
fig, axes = plt.subplots(4, 1, figsize=(12, 14), sharex=True)

specs = [
    (axes[0], agg_interval["cum_revenue"], "Revenue ($)", "#16a34a", "Cumulative revenue"),
    (axes[1], agg_interval["cum_requests"], "Requests", "#334155", "Cumulative requests"),
    (axes[2], agg_interval["fill_rate"], "Fill rate", "#0891b2", "Fill rate"),
    (axes[3], agg_interval["ecpm"], "eCPM ($/1k impr.)", "#ca8a04", "eCPM"),
]

for ax, series, ylabel, color, label in specs:
    ax.plot(x, series, color=color, linewidth=2, label=label)
    ax.set_ylabel(ylabel)
    ax.legend(loc="upper left")
    ax.grid(True, alpha=0.3)

axes[2].yaxis.set_major_formatter(mticker.PercentFormatter(1.0))
style_time_axis(axes[-1])
axes[-1].set_xlabel("Date")

fig.suptitle(
    "Revenue identity walk - Requests, Fill rate & eCPM drive Revenue\n"
    f"(cumulative, chronological - as of each {INTERVAL_SECONDS}s)",
    fontsize=13,
)
fig.tight_layout(rect=[0, 0, 1, 0.96])
fig.savefig(OUT_DIR / "combined_revenue_requests_fillrate_ecpm.png", dpi=150)
plt.close(fig)
print("Saved combined_revenue_requests_fillrate_ecpm.png")

print("\nAll plots written to:", OUT_DIR)