<h1>Demo Solution Approach - 2</h1>

> **Context**: [`README.md`](../README.md)

---

**Contents**:

- [Overall Approach](#overall-approach)
- [Reference Implementation](#reference-implementation)
- [Anomaly Detection](#anomaly-detection)

---

# Overall Approach
Based on mentor review, the following approach was decided:

- No simulation of event stream; only batch processing
- The goal is to evaluate the whole dataset and produce:
  - Anomalies
  - Decomposition and attribution per anomaly
  - Summary per anomaly

The fixed components described in [`demo-solution-approach-1.md`](./demo-solution-approach-1.md) much easier to solve: event/metric stream components are redundant, the UI can be locally hosted (since the analysis data can be locally stored, even as we use ClickHouse Cloud for the analytical work), and ClickHouse Cloud + LLM remain as the only cloud-hosted components of our solution, everything else (including the orchestration and UI) being locally hosted.

# Reference Implementation
**See**: [`implementation`](../implementation/)

# Anomaly Detection
