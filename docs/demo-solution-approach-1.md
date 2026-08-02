<h1>Demo Solution Approach - 1</h1>

> **Context**: [`README.md`](../README.md)

---

**Contents**:

- [To Do](#to-do)
- [Overall Approach](#overall-approach)
- [Build the Event/Metric Streams](#build-the-eventmetric-streams)
- [Investigation](#investigation)

---

# To Do
- Build an event stream
- Build a metrics stream
- Define alerts on the metrics stream - **anomaly detection**
- Investigation - **attribution**
- Presentation

# Overall Approach
1. Break the whole solution into components:
   1. Fixed components (infrastructure)
   2. Plug-and-play components (logic/AI)
2. Build fixed components:
   1. Event and metric streams
   2. ClickHouse-LLM-Langfuse integration
   3. UI

# Build the Event/Metric Streams
What we have:

- Dataset of ad events
- Metrics definitions

Key tasks:

- Simulate real-time event stream (metric stream is built on event stream)
- Allow creating events with user input (for testing)

**To simulate real-time event stream**:

Instead of producing the data periodically, we shall be querying it in progressing time windows that shall be updated periodically. Hence, the output looks as if it is for real-time data, while the underlying dataset is static. This enables us to simplify the real-time aspect of the demo and focus on anomaly detection and attribution.

# Investigation
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