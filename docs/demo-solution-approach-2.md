<h1>Demo Solution Approach - 2</h1>

> **Context**: [`README.md`](../README.md)

---

**Contents**:

- [Overall Approach](#overall-approach)
- [Reference Implementation](#reference-implementation)
- [Anomaly Detection - z-Score on Median/MAD](#anomaly-detection---z-score-on-medianmad)
  - [Setting the Baseline + Obtaining the Residual](#setting-the-baseline--obtaining-the-residual)
  - [Robust Deviation Scoring](#robust-deviation-scoring)
- [z-Score \& Thresholding](#z-score--thresholding)
- [Decomposition of Raw Metric](#decomposition-of-raw-metric)

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

# Anomaly Detection - z-Score on Median/MAD
> MAD = Median Absolute Deviation.

**Key variables to decide upon**:

| Variable | Description |
| --- | --- |
| Aggregation interval | Time interval by which we must aggregate data to compute metrics. |
| Seasonality interval | Time interval by which we must consider seasonality (i.e. repeating rhythm). |
| Deviation threshold | Threshold that decides how much deviation is too much, i.e. at what point is a deviation considered anomalous. |
| Recency window for seasonality | How many past seasonal-internal-spaced data points to consider? Setting this allows us to account for trend along with seasonality. |

These values are to be tuned until the output is satisfactory.

## Setting the Baseline + Obtaining the Residual
> Defining what "normal" looks like.

The raw metric calculated over the aggregation interval is split into:

```
- Trend       |
              +-> these set the baseline
- Seasonality |

- Residual    | = raw metric - baseline
```

**About each component**:

| Component | Description |
| --- | --- |
| Trend | Shows directional movement that is not noise. |
| Seasonality | Repeating shape tied to a calendar unit (e.g. hour-of-day, day-of-week, etc.) - a structural factor of change. |
| Residual | Difference between the actual raw metric value and the expected raw metric value (i.e. the baseline) - this is what is actually checked for anomalies. The greater the residual, the greater the deviation from the baseline. |

## Robust Deviation Scoring
> Addresses the question: "how unusual is this residual?"

To answer whether a raw metric value has varied from the baseline unusual, we must identify what is the usual level of variation in this raw metric value across the dataset. The approach used to obtain this in our case is the median absolute deviation, i.e. MAD (i.e. the sum of the absolute value of (median - raw metric value) across the dataset) - we use the median here because, unlike the mean, the median is insensitive to extremes (e.g. anomalies), and we do not want anomalies to alter our baseline (since they are considered as "deviant" or "uncharacteristic" with respect to the baseline).

# z-Score & Thresholding

```
z-score = (actual - median baseline) / (1.4826 × MAD)
```

- `actual` = raw metric value
- `median baseline` = median value of baseline values
  > baseline = trend + seasonality (expected raw metric value)
- `1.4826` = scaling factor to scale `MAD` to match standard deviation

# Decomposition of Raw Metric
