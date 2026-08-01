<h1>LiveDumpDetective</h1>

---

**Contents**:

- [The Event Stream](#the-event-stream)
- [The Metrics Stream](#the-metrics-stream)
- [Alerting - Prerequisite, Not Problem Statement](#alerting---prerequisite-not-problem-statement)
- [Problem Statement](#problem-statement)
- [Key Concepts](#key-concepts)
  - [Metric Dimensions](#metric-dimensions)
  - [Advertisement Cost Models](#advertisement-cost-models)
- [Demo Solution Approach](#demo-solution-approach)
  - [Overall Approach](#overall-approach)
  - [Build the Event/Metric Streams](#build-the-eventmetric-streams)
  - [Investigation](#investigation)

---

# The Event Stream
A digital add stack (InMobi) provides a stream of events (see: [`data/ad_events.parquet`](./data/ad_events.parquet)).

Each event consisting of the following columns:

- `event_time`
- `app_id` (ID of app associated with the event)
    > Foreign key from [`data/apps.csv`](./data/apps.csv)
- `geo_device_id` (ID of device associated with the event)
    > Foreign key from [`data/geo_device.csv`](./data/geo_device.csv)
- `advertiser_id` (ID of the advertiser associated with the event)
    > Foreign key from [`data/advertisers.csv`](./data/advertisers.csv)
- `ad_format`:
  - `native`
  - `video`
  - `banner`
  - `interstitial`
  - `rewarded`
- `is_filled` (indicator for whether ad request is filled)
- `is_impression` (indicator for whether ad is rendered)
- `is_click` (indicator for whether ad is clicked on)
- `revenue` (revenue received by InMobi as per some cost model)

> **NOTE**: The dataset [`data/ad_events.parquet`](./data/ad_events.parquet) is a synthetic ad-events dataset capturing ~9 million events over 5 weeks, along with dimensions: impressions, requests, fills, clicks, and revenue events across dimensions (app, device, OS, geo, advertiser, ad format), with realistic seasonality and noise.

# The Metrics Stream
Key metrics must be calculated from the event stream and monitored for deviations/anomalies. [`docs/metrics_glossary.md`](./docs/metrics_glossary.md) provides an overview about the metrics used and how they are calculated. The columns `is_filled`, `is_impression`, `is_click`, and `revenue` in the event stream serve as the raw data from which metrics are calculated.

# Alerting - Prerequisite, Not Problem Statement
We must set up alerts per metric, based on:

- Defined threshold values
- Calculated running averages
- Calculated deviations

> **NOTE**: This is an in-development list, not a definitive.

The key problem statement:

- Not **what** has deviated/changed enough to notice/investigate
- But the actual investigation itself

# Problem Statement
> **Reference**: [`InMobi/PROBLEM_STATEMENT.md`, **github.com**](https://github.com/sidagarwal04/click-a-thon-2026/blob/main/InMobi/PROBLEM_STATEMENT.md)

- Auto-investigation of why a metric moved
    > The definition of "moved" may be threshold-based.
- Returns a short, evidence-backed explanation in seconds, not days <br> =>
  - Clear breakdown of [metric dimensions](#metric-dimensions) (part of "evidence-backed")
  - Reasoning from the above breakdown (part of "evidence-backed")
  - Low latency ("seconds, not days")

Essentially, this is automatic root-cause analysis for real-time metric deviations.

**Bonus**:

- State what metric dimensions were checked
- State what metric dimensions were ruled out

# Key Concepts
## Metric Dimensions
Here, we interpret the term "metric dimension" as one of two things:

- A qualitative categorization/filtering of the metric
    > E.g.: Categorizing "fill rate" into "fill rate per app".
- A metric contributing to the metric's value
    > E.g.: CTR is calculated from clicks and impressions.
 
Metric dimensions serve as the basis for root-cause analysis.

## Advertisement Cost Models
- Cost per Mille (CPM)
- Cost per Click (CPC)
- Cost per Installation (CPI)

The cost model determines how `revenue` is calculated as per:

- `is_impression`
- `is_click`

# Demo Solution Approach
> For the demo as a whole (not just the particular problem statement).

- Build an event stream
- Build a metrics stream
- Define alerts on the metrics stream - **anomaly detection**
- Investigation - **attribution**
- Presentation

## Overall Approach
1. Break the whole solution into components:
   1. Fixed components (infrastructure)
   2. Plug-and-play components (logic/AI)
2. Build fixed components:
   1. Event and metric streams
   2. 

## Build the Event/Metric Streams
What we have:

- Dataset of ad events
- Metrics definitions

Key tasks:

- Simulate real-time event stream (metric stream is built on event stream)
- Allow creating events with user input (for testing)

## Investigation
Approach:

- Identify the direction and magnitude (D&M) of the metric movement
- Break down the metric into its metric dimensions
- Identify the relevant metrics dimensions
- Identify which metric dimension(s)'s D&M contribute to the metric's D&M
- Obtain a list of:
  - Checked metric dimensions (relevant metric dimensions)
  - Ruled out metric dimensions (irrelevant metric dimensions)
- Obtain analysis summary

Key questions:

- How to define "relevance"?
- How would we apply this investigation approach:
  - using deterministic workflow(s) (defined per metric perhaps)?
  - using AI workflow(s)

Action:

- Compare the aforementioned deterministic and AI approaches
- Outline a conceptual workflow that applies for both