# Automated Root-Cause Analyst — InMobi Click-a-thon 2026

Detects when a key ad-metric (revenue, fill rate, eCPM, requests, CTR) deviates
from its expected baseline, automatically drills down to the specific
segment(s) responsible, and writes a short plain-language diagnosis where
every number is real and reproducible from ClickHouse.

ClickHouse does all the analysis (baseline comparison, revenue-identity
decomposition, per-segment ranking). An LLM (Gemini) only narrates the
already-computed numbers. Every step — every SQL query and the final LLM
call — is captured in a trace (local JSON + Langfuse), so a judge can see
exactly what was checked, in what order, and why.

## How it works

1. **Detect** (`sql` via `src/rca/baseline.py`): for each day and each metric,
   compare against a *like-for-like* baseline — the same weekday, trailing
   weeks — instead of a flat global average (which would flag every weekend
   as anomalous). A robust (median/MAD) z-score plus a minimum relative-move
   floor avoids crying wolf on noise. A linear trend fit over the trailing
   points nets out the slow growth trend the data has, so being later in the
   dataset doesn't itself look anomalous. A two-pass contamination guard
   keeps one real one-day incident from poisoning the trend baseline of a
   later, otherwise-normal day.

2. **Decompose** (`src/rca/attribution.py::decompose_revenue`): walks the
   revenue identity `revenue = requests × fill_rate × render_rate × eCPM/1000`
   using an exact logarithmic-mean (LMDI) decomposition — the factor
   contributions sum exactly to the observed revenue delta, so "which factor
   moved" is never a guess.

3. **Drill down** (`src/rca/attribution.py::drill_down`): for the responsible
   factor, ranks every segment of every dimension (ad_format, category,
   publisher_tier, vertical, campaign_type, region, country, device_model,
   os_version) by **explanatory power** (Adtributor's formula — the share of
   the movement this segment accounts for, after removing the change a pure
   volume/mix shift at the baseline rate would predict). A segment is only
   declared the localized cause if its **lift** (explanatory power ÷ its own
   volume share) clears a threshold — a segment whose EP simply equals its
   size moved in exact proportion to everything else, which is evidence of a
   *broad* effect, not a localized one, and is reported as such instead of
   being forced into a story. Recurses one level deeper into the winning
   segment (e.g. device → device × region).

4. **Narrate** (`src/rca/narrate.py`): the only LLM call. It receives nothing
   but the structured JSON of computed numbers and is instructed to cite only
   what's in that JSON, name the ruled-out segments, and say plainly when
   nothing localizes.

5. **Trace** (`src/rca/tracing.py`): every stage above runs inside a span.
   Spans are always written to `traces/*.json` locally; if Langfuse
   credentials are set they're mirrored live to Langfuse as well, nested
   exactly as they nest in code.

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
cp .env.example .env   # fill in ClickHouse Cloud + Gemini + Langfuse creds
bash scripts/load_data.sh   # idempotent: drops + recreates + reloads everything
```

`scripts/load_data.sh` applies `sql/ddl.sql`, bulk-loads the three dimension
CSVs and `ad_events.parquet` via `clickhouse-client`, then runs
`sql/build_fact.sql` to build `fact_events` — a single denormalized table
(fact + all three dimensions pre-joined) so every drill-down query below is a
plain single-table `GROUP BY`, no joins at query time.

To point at a fresh dataset (e.g. the unseen-incident release), just replace
the files under `data/` and rerun the same script — nothing else changes.

## Usage

```bash
# Detect-only: which days, for which metrics, look anomalous (no drill-down)
rca scan
rca scan --metric revenue --metric fill_rate --lookback-weeks 4

# Full investigation of one specific window: decompose + drill-down + narrate
rca investigate --metric fill_rate --start 2026-06-23 --end 2026-06-25

# End to end: scan the whole loaded range, investigate + narrate every incident found
rca auto
```

`rca auto` (and `investigate`) write each result as JSON to `out/` and print
the local trace path (and the Langfuse trace URL, if configured). `rca auto`
with no arguments scans the full date range currently loaded in
`fact_events` — this is what to run against the unseen-incident dataset once
it's loaded, with no code changes.

## Project layout

```
sql/ddl.sql            table definitions (raw + denormalized fact_events)
sql/build_fact.sql      one-time join that builds fact_events
scripts/load_data.sh    idempotent full data load (Cloud or local)
src/rca/metrics.py      metric + dimension definitions (matches metrics_glossary.md exactly)
src/rca/baseline.py     like-for-like baseline + anomaly detection
src/rca/attribution.py  revenue decomposition + Adtributor-style segment ranking + drill-down
src/rca/narrate.py      the one LLM call (Gemini), strictly grounded in computed numbers
src/rca/tracing.py      local JSON trace + Langfuse mirroring
src/rca/pipeline.py     orchestrates detect -> decompose -> drill-down -> narrate
src/rca/cli.py          `rca scan|investigate|auto`
traces/                 per-investigation trace trees (local, always written)
out/                    per-investigation JSON results (diagnosis + full evidence)
```

## Design notes / what was deliberately ruled out

- **Ratio metrics are always `sum/sum`**, never an average of per-row or
  per-day ratios, per `metrics_glossary.md`'s explicit warning about rollup
  correctness.
- **`event_time` is pinned to `DateTime('UTC')`** in the DDL. Leaving it
  timezone-less lets ClickHouse silently interpret the (naive) source
  timestamps in the *server's* local timezone — on a server not already set
  to UTC this shifts every day/hour boundary and quietly corrupts every
  seasonality comparison. Caught by comparing a min/max date query against
  the documented Jun 1 – Jul 5 range before writing any analysis code.
- **Uniform/broad-based moves are reported as such, not forced into a
  segment-level story.** The Jun 21 request-volume crash in the sample data
  has explanatory-power ≈ volume-share (lift ≈ 1.0) for every segment of
  every dimension — i.e. it dropped everywhere in exact proportion to
  existing traffic. `drill_down` returns `primary = None` in that case, and
  the narration says the drop was broad-based rather than naming whichever
  segment happened to be largest.
