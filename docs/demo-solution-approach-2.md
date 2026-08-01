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
- [Decomposition of Raw Metric (Revenue) - LMDI Decomposition](#decomposition-of-raw-metric-revenue---lmdi-decomposition)
  - [About Revenue as a Metric](#about-revenue-as-a-metric)
  - [About LMDI Decomposition](#about-lmdi-decomposition)
    - [Motivating Problem](#motivating-problem)
      - [Attempted Approach 1](#attempted-approach-1)
      - [Attempted Approach 2](#attempted-approach-2)
      - [Potential Approach - Using Logarithms](#potential-approach---using-logarithms)
    - [What LMDI Decomposition Provides](#what-lmdi-decomposition-provides)
  - [Usage](#usage)
  - [What Remains](#what-remains)
- [](#)

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

**How each component is applied**:

| Component | Description | Reasoning |
| --- | --- | --- |
| Trend | Estimated using linear regression over previous seasonal points (going as far back as the recency window for seasonality specifies). | Studying the metric graphs in [`data/plots--interval=86400s`](../data/plots--interval=86400s/), we observe that shape of the requests graph closely follows the shape of the revenue graph, when calculated over the aggregation interval, whereas fill rate and eCPM are relatively noisy with a relatively stable moving averages. Hence, we assume that revenue changes relatively linearly with respect to requests when calculated over previous seasonal points. |
| Seasonality | Seasonality is specified by specifying the seasonality interval by which previous seasonal points are obtained in the trend. | - |
| Residual | Raw metric value minus expected metric value as per trend. |

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

# Decomposition of Raw Metric (Revenue) - LMDI Decomposition
> **NOTE**:
>
> - LMDI = Log-Mean Divisia Index
> - The raw metric here is revenue summed over aggregation interval.

## About Revenue as a Metric
> **Reference**: [`docs/metrics_glossary.md`](./metrics_glossary.md)

Quote from the above reference

> ```
> Revenue  =  Requests  ×  Fill rate  ×  (Impressions / Fills)  ×  eCPM / 1000
> ```
> 
> With ~one impression per fill, this simplifies to:
> 
> ```
> Revenue  ≈  Requests  ×  Fill rate  ×  eCPM / 1000
> ```
> 
> When revenue moves, walk this identity to find *which factor* is responsible (volume? fill? price?), then slice that factor by dimension to find *which segment*. CTR is a sibling engagement/quality signal — useful context, not a direct revenue factor in this CPM model.

Hence, we see that, revenue is a metric that is a multiplicative composition of other metrics; going with the simplifying assumption, these metrics are requests and fill rate. Hence, to perform a root cause analysis of the change in revenue, we must decompose the change to the contributions of requests and fill rate. This is where LMDI decomposition comes in.

## About LMDI Decomposition
### Motivating Problem
Consider a variable that is a multiplicative composition of n variables:

```
a = x_1 * x_2 ... x_n
```

Now, let us say:

- `a_i` is the value of `a` at time `i`
- `x_1_i, x_2_i... x_n_i` are the values of `x_1, x_2... x_n` at time `i`
- `a_j` is the value of `a` at time `j` (where `j > i`)
- `x_1_j, x_2_j... x_n_j` are the values of `x_1, x_2... x_n` at time `j`

For clarity, let us call `a` the target variable and `x_1, x_2... x_n` the factor variables. To evaluate the contribution of the factor variables to the change of the target variable from `a_i` to `a_j` (i.e. `a_j - a_i`), we may propose two approaches:

#### Attempted Approach 1
We can change one factor variable at a time, from its value at time `i` to its value at time `j`, and with each factor variable change, we can evaluate the change in the target variable due to the change in the factor variable (making sure to revert previous factor variable changes). This would look like this:

| Step | Factor variable change | Target variable change | Effect |
| --- | --- | --- | --- |
| 1 | `x_1: x_1_i -> x_1_j` | `a: a_i -> a_i_step_1` | `a_i_step_1 - a_i` |
| 2 | `x_2: x_2_i -> x_2_j` | `a: a_i -> a_i_step_2` | `a_i_step_2 - a_i` |
| 3 | `x_3: x_3_i -> x_3_j` | `a: a_i -> a_i_step_3` | `a_i_step_3 - a_i` |

This goes on up to (and including) `x_n`.

---

The problem with this approach is that the factor variable change is that, for a multiplicative composition of factor variables, the target variable change does not help reflect the proportion of change caused by the change in the factor variable. Consider an example: `a = x * y`. Let us say:

- `a_i = x_i * y_i = 2 * 3 = 6`
- `a_j = x_j * y_j = 4 * 6 = 24`

Following the above steps:

| Step | Factor variable change | Target variable change | Effect |
| --- | --- | --- | --- |
| 1 | `x: 2 -> 4` | `a: 6 -> 12` | `12 - 6 = 6` |
| 2 | `y: 3 -> 6` | `a: 6 -> 12` | `12 - 6 = 6` |

According to this breakdown, the changes in `x` and `y` contribute equally to the change in the target variable, which means `delta x` (2) times `delta y` (3), which is 6, does not reflect the actual magnitude of the change to the target variable, which is 18.

> TL;DR: Not an effective approach in measuring the factors' contribution.

#### Attempted Approach 2
We can change one factor variable at a time, from its value at time `i` to its value at time `j`, and with each factor variable change, we can evaluate the change in the target variable due to the change in the factor variable (without reverting previous factor variable changes). This would look like this:

| Step | Factor variable change | Target variable change | Effect |
| --- | --- | --- | --- |
| 1 | `x_1: x_1_i -> x_1_j` | `a: a_i -> a_i_step_1` | `a_i_step_1 - a_i` |
| 2 | `x_2: x_2_i -> x_2_j` | `a: a_i_step_1 -> a_i_step_2` | `a_i_step_2 - a_i_step_1` |
| 3 | `x_3: x_3_i -> x_3_j` | `a: a_i_step_2 -> a_i_step_3` | `a_i_step_3 - a_i_step_2` |

This goes on up to (and including) `x_n`, where `a` finally reaches `a_j`.

---

The problem with this approach is that the target variable change evaluated for each factor variable change is sensitive to the order in which the factor variable was changed. Consider an example: `a = x * y`. Let us say:

- `a_i = x_i * y_i = 2 * 3 = 6`
- `a_j = x_j * y_j = 4 * 8 = 32`

Following the above steps in one order:

| Step | Factor variable change | Target variable change | Effect |
| --- | --- | --- | --- |
| 1 | `x: 2 -> 4` | `a: 6 -> 12` | `12 - 6 = 6` |
| 2 | `y: 3 -> 8` | `a: 12 -> 32` | `32 - 12 = 20` |

Now following the above steps in another order:

| Step | Factor variable change | Target variable change | Effect |
| --- | --- | --- | --- |
| 1 | `y: 3 -> 8` | `a: 6 -> 16` | `16 - 6 = 10` |
| 2 | `x: 2 -> 4` | `a: 16 -> 32` | `32 - 16 = 16` |

> TL;DR:
> 
> - This is a very unreliable tool to measure factors' contribution.
> - This also does not seem to reflect the actual contribution of factors.

#### Potential Approach - Using Logarithms
If we could somehow decompose the target variable into an additive composition of factor variables, each change in the factor variable would correspond proportionally to a change in the target variable, and the order in which the changes occur would not change the measured contributions. To do this, logarithms are a possible tool, if they can be made to work. This is what LMDI decomposition achieves.

### What LMDI Decomposition Provides
> **References**:
>
> - [*Log-Mean Divisia Index Method*, Abdulkadir Bektas](https://www.tespam.org/wp-content/uploads/2020/03/Log-Mean-Divisia-Index-Method700068-996678.pdf)
> - [*Derivation of index decomposition analysis*, **economics.stackexchange.com/questions/53765**](https://economics.stackexchange.com/questions/53765/derivation-of-index-decomposition-analysis)

LMDI decomposition expresses the difference between two values of a target variable - the target variable being a multiplicative composition of factor variables - as a sum of terms, each term associated with the change in one factor variable, and expressed as a log-mean times a log-based divisia, i.e. `(new value - old value) /( ln(new value) - ln(old value))` times `ln(new value) / ln(old value)`.

## Usage
**See**: `decomponse_revenue` function in [`implementation/rca/attribution.py`](../implementation/rca/attribution.py)

## What Remains
All LMDI does is decompose revenue. It does not yet tell us about the contribution the change in each factor (requests and fill rate) has to the change in the target variable. However, analyzing this is easier now that we have decomposed revenue into an additive composition of factors.

# 