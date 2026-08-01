"""
ad_events.parquet analysis
===========================
Computes core funnel/revenue metrics *chronologically*: every plotted point for a given day is derived only from events with event_time up to and including that day (expanding / cumulative-since-day-1 window), so nothing is computed using future data relative to the point being plotted.

Outputs (all saved, none displayed):
  plots/requests.png
  plots/fills.png
  plots/fill_rate.png
  plots/impressions.png
  plots/render_rate.png
  plots/clicks.png
  plots/ctr.png
  plots/revenue.png
  plots/ecpm.png
  plots/rpr.png
  plots/combined_revenue_requests_fillrate_ecpm.png
"""

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
OUT_DIR = Path("./plots")
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
df["event_date"] = df["event_time"].dt.floor("D")
daily = df.groupby("event_date", as_index=False).last()
daily = daily.sort_values("event_date").reset_index(drop=True)

print(f"Date range: {daily['event_date'].min()} -> {daily['event_date'].max()}")
print(f"Days plotted: {len(daily)}")

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
    ax.set_title(f"{title} (cumulative, chronological - as of each day)")
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


x = daily["event_date"]

# ------------------------------------------------------------------
# 6. Individual metric plots
# ------------------------------------------------------------------
plot_metric(x, daily["cum_requests"], "Requests", "Cumulative requests",
            "requests.png", color="#334155")

plot_metric(x, daily["cum_fills"], "Fills", "Cumulative fills",
            "fills.png", color="#0ea5e9")

plot_metric(x, daily["fill_rate"], "Fill rate", "Fill rate",
            "fill_rate.png", color="#0891b2", fmt_pct=True)

plot_metric(x, daily["cum_impressions"], "Impressions", "Cumulative impressions",
            "impressions.png", color="#7c3aed")

plot_metric(x, daily["render_rate"], "Render rate", "Render rate (impressions/fills)",
            "render_rate.png", color="#8b5cf6", fmt_pct=True)

plot_metric(x, daily["cum_clicks"], "Clicks", "Cumulative clicks",
            "clicks.png", color="#db2777")

plot_metric(x, daily["ctr"], "CTR", "Click-through rate",
            "ctr.png", color="#e11d48", fmt_pct=True)

plot_metric(x, daily["cum_revenue"], "Revenue", "Cumulative revenue ($)",
            "revenue.png", color="#16a34a", fmt_money=True)

plot_metric(x, daily["ecpm"], "eCPM", "eCPM ($ per 1,000 impressions)",
            "ecpm.png", color="#ca8a04", fmt_money=True)

plot_metric(x, daily["rpr"], "Revenue per request (RPR)", "RPR ($)",
            "rpr.png", color="#ea580c", fmt_money=True)

# ------------------------------------------------------------------
# 7. Combined plot: Revenue, Requests, Fill rate, eCPM
#    Different units/scales -> 4 stacked subplots sharing one time axis, presented as a single figure/file ("together in one plot").
# ------------------------------------------------------------------
fig, axes = plt.subplots(4, 1, figsize=(12, 14), sharex=True)

specs = [
    (axes[0], daily["cum_revenue"], "Revenue ($)", "#16a34a", "Cumulative revenue"),
    (axes[1], daily["cum_requests"], "Requests", "#334155", "Cumulative requests"),
    (axes[2], daily["fill_rate"], "Fill rate", "#0891b2", "Fill rate"),
    (axes[3], daily["ecpm"], "eCPM ($/1k impr.)", "#ca8a04", "eCPM"),
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
    "(cumulative, chronological - as of each day)",
    fontsize=13,
)
fig.tight_layout(rect=[0, 0, 1, 0.96])
fig.savefig(OUT_DIR / "combined_revenue_requests_fillrate_ecpm.png", dpi=150)
plt.close(fig)
print("Saved combined_revenue_requests_fillrate_ecpm.png")

print("\nAll plots written to:", OUT_DIR)