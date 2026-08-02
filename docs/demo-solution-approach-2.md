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
- [Decomposition of Metrics](#decomposition-of-metrics)
- [Why \& When to Decompose Metrics?](#why--when-to-decompose-metrics)
  - [Which Metrics Need Decomposing?](#which-metrics-need-decomposing)
    - [Composite Metrics](#composite-metrics)
      - [Revenue](#revenue)
      - [Revenue per request (RPR)](#revenue-per-request-rpr)
  - [Atomic Metrics](#atomic-metrics)
- [Decomposition of Revenue - LMDI Decomposition](#decomposition-of-revenue---lmdi-decomposition)
  - [About Revenue as a Metric](#about-revenue-as-a-metric)
  - [About LMDI Decomposition](#about-lmdi-decomposition)
    - [Motivating Problem](#motivating-problem)
      - [Attempted Approach 1](#attempted-approach-1)
      - [Attempted Approach 2](#attempted-approach-2)
      - [Potential Approach - Using Logarithms](#potential-approach---using-logarithms)
    - [What LMDI Decomposition Provides](#what-lmdi-decomposition-provides)
  - [Usage](#usage)
  - [What Remains](#what-remains)
- [From "Which Factor" to "Which Segment"](#from-which-factor-to-which-segment)
- [Explanatory Power](#explanatory-power)
  - [Motivating Problem](#motivating-problem-1)
  - [What Explanatory Power Provides](#what-explanatory-power-provides)
  - [Additive vs. Ratio Measures](#additive-vs-ratio-measures)
  - [Configured Parameters - Explanatory Power](#configured-parameters---explanatory-power)
- [Surprise / Lift](#surprise--lift)
  - [Motivating Problem](#motivating-problem-2)
  - [What Surprise / Lift Provides](#what-surprise--lift-provides)
  - [Configured Parameters - Surprise / Lift](#configured-parameters---surprise--lift)
- [Drill-Down](#drill-down)
  - [General Mechanism](#general-mechanism)
  - [Dimension Sources in This Dataset](#dimension-sources-in-this-dataset)
  - [Why the Valid Dimension Set Changes per Metric](#why-the-valid-dimension-set-changes-per-metric)
  - [Worked Example Across Metrics](#worked-example-across-metrics)
  - [Configured Parameters - Drill-Down](#configured-parameters---drill-down)
- [Integration - Anomaly Detection -\> Drill Down](#integration---anomaly-detection---drill-down)

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

# Decomposition of Metrics
# Why & When to Decompose Metrics?
- A metric can be a composition of other metrics.
- To analyze a change in such a metric's values, we must analyze:
  - Which of its composing metrics contribute to the change?
  - How much each contributing metric actually contributes?

Hence, composite metrics must be decomposed appropriately.

## Which Metrics Need Decomposing?
### Composite Metrics
- Revenue (calculated over aggregation interval)
- Revenue per request (calculated over aggregation interval)

#### Revenue
Per [`docs/metrics_glossary.md`](./metrics_glossary.md), the full revenue identity is:
 
```
Revenue  =  Requests  ×  Fill rate  ×  (Impressions / Fills)  ×  eCPM / 1000
         =  Requests  ×  Fill rate  ×  Render rate            ×  eCPM / 1000
```
 
We simplify (per the glossary's ~one-impression-per-fill assumption) to:
 
```
Revenue  ≈  Requests  ×  Fill rate  ×  eCPM / 1000
```
 
> **NOTE**: This 3-factor identity already used in [`implementation/rca/attribution.py`](../implementation/rca/attribution.py)'s `REVENUE_FACTORS`

#### Revenue per request (RPR)
`sum(revenue) / count(*)` is nothing but revenue with `Requests` divided out:
 
```
RPR  =  Revenue / Requests  ≈  Fill rate  ×  eCPM / 1000
```
 
Hence, RPR is decomposable by the same LMDI mechanism, but we do not implement it as a separate decomposition because it would be redundant: an RPR anomaly is just a revenue anomaly with the contribution of "requests" cancelled out by construction, which means anything RPR's decomposition would tell us is already visible by reading the contribution of fill rate and eCMP off the existing revenue decomposition.
 
## Atomic Metrics
The remaining metrics in [`docs/metrics_glossary.md`](./metrics_glossary.md)...

- **Requests**
- **Fill rate**
- **Render rate**
- **CTR**
- **eCPM**

... are *not* composites of other tracked metrics:
 
- **Requests** is a raw count (`count(*)`)
- **Fill rate**, **Render rate**, **CTR**, **eCPM**
  - Each is a single ratio.
  - None of their numerators or denominators is itself a tracked metric
      > They are derived directly from the event-level fields: <br> `is_filled`, `is_impression`, `is_click`, `revenue` 
  - There is no second multiplicative identity one level down.

# Decomposition of Revenue - LMDI Decomposition
> **NOTE**: LMDI = Log-Mean Divisia Index.

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
> When revenue moves, walk this identity to find *which factor* is responsible (volume? fill? price?), then slice that factor by dimension to find *which segment*. CTR is a sibling engagement/quality signal - useful context, not a direct revenue factor in this CPM model.

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

# From "Which Factor" to "Which Segment"
The rest of this document covers the three steps that apply to *any* metric once you have a metric of interest, whether that metric arrived via LMDI (e.g. if [`implementation/rca/attribution.py`](../implementation/rca/attribution.py) decided `fill_rate` explains most of a revenue anomaly) or was anomaly-detected directly (e.g. CTR itself spiked):
 
```
Explanatory Power  |
                   +-> (A)
Surprise / Lift    |    
    
Drill-Down         | (B)
                         
                         
```

(A) "Explanatory Power" and "Surprise / Life" together identify which segment(s) of a dimension are responsible for the metric's movement and rule out segments that only look responsible because of their size. (B) Having localized to one segment, check whether a further sub-segment inside it is where the effect actually concentrates.
  
# Explanatory Power
> **NOTE**: Explanatory Power = EP.

> Adapted from the Adtributor "explanatory power" formula, from:
>
> (Bhagwan et al, 2016): Bhagwan, R., Kumar, R., Ramjee, R., Varghese, G., Mohapatra, S., Manoharan, H., & Shah, P. *Adtributor: Revenue Debugging in Advertising Systems*. Microsoft Research. [`microsoft.com/en-us/research/wp-content/uploads/2016/02/main-14.pdf`](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/main-14.pdf) - source of Explanatory Power (§3.2, §4.1) and Surprise via Jensen–Shannon divergence (§3.3).

## Motivating Problem
Consider a metric that has moved anomalously, and a dimension you could slice it by - say `region`, with two elements, `NAM` and `EU`. You want to know: of the total movement, how much is `NAM`'s fault, and how much is `EU`'s?

---

**For additive metric**:

For an additive metric - like `Requests` or `Revenue` - the answer is direct. Say total requests dropped from `1,000,000` (baseline) to `800,000` (current), a drop of `200,000`. Suppose `NAM` dropped from `500,000` to `400,000` (a drop of `100,000`) and `EU` dropped from `500,000` to `400,000` (also `100,000`). Each segment's share of the total drop is:
 
```
EP(NAM) = (400,000 - 500,000) / (800,000 - 1,000,000) = 100,000 / 200,000 = 50%
EP(EU)  = (400,000 - 500,000) / (800,000 - 1,000,000) = 100,000 / 200,000 = 50%
```
 
Here:

- Both segments explain exactly half the drop.
- Every segment's EP sums to 100% across the dimension.

---

**For ratio metric**:

We cannot use the same logic for a ratio metric, e.g. `Fill rate`. Suppose overall fill rate dropped from `0.50` (forecast) to `0.44` (actual). Suppose `NAM`'s own fill rate did not move at all - `0.50` forecast, `0.50` actual - while `EU`'s fill rate also did not move - `0.40` forecast, `0.40` actual. If neither segment's *rate* moved, does that mean fill rate's drop is unexplainable by region? Not necessarily: if `EU` (the lower-rate region) grew its *share of requests* - say from 30% to 60% of total volume - the blended overall rate drops purely from **mix shift**, even though no segment's own rate changed at all (i.e. shift that occurs when the numerator sum (a + b) and denominator sum (c + d) shift, but the specific rates a/c and b/d are the same). A naive "did this segment's rate change" check would say "region explains nothing," which is wrong.
 
> TL;DR: For additive metrics, EP is just "share of the total delta." For ratio metrics, a segment can be entirely responsible for the overall movement via volume/mix shift alone, even with an unchanged own-rate - so EP for ratio metrics must separate the rate-driven effect from the volume-driven effect, not just diff the segment's own rate.
 
## What Explanatory Power Provides
Explanatory Power (EP) is a normalized attribution of the overall metric movement to a segment. For additive metrics, all segments' EPs sum to 100% of the total change (Bhagwan et al, 2016). For ratio metrics, EP is computed via a finite-difference decomposition that isolates the portion of the overall rate's movement attributable to this segment's numerator/denominator changing, after holding the segment's own volume-weighted contribution to the *rest of the dataset* constant (Bhagwan et al, 2016) - this is exactly the volume-vs-rate separation the fill-rate example above needs.
 
**Implementation**: See `explanatory_power` in [`implementation/rca/attribution.py`](../implementation/rca/attribution.py). The `is_ratio` branch matches the additive/ratio distinction above; `is_ratio=False` is the direct share-of-delta formula, `is_ratio=True` subtracts the baseline-rate-weighted volume effect before taking the ratio.
 
## Additive vs. Ratio Measures
 
| Metric | Additive or ratio? | EP formula family |
| --- | --- | --- |
| Requests | Additive | Share of total delta |
| Revenue | Additive | Share of total delta |
| Fill rate | Ratio | Volume/mix-adjusted (finite-difference) |
| Render rate | Ratio | Volume/mix-adjusted (finite-difference) |
| CTR | Ratio | Volume/mix-adjusted (finite-difference) |
| eCPM | Ratio | Volume/mix-adjusted (finite-difference) |
 
## Configured Parameters - Explanatory Power
 
| Variable | Description |
| --- | --- |
| `min_volume_share` | Minimum share of total volume a segment must carry to be treated as "significant" rather than noise (below this, a segment can have a large EP purely from a tiny denominator and should not be trusted). |
| `ep_threshold` | Minimum `\|EP\|` a segment must clear to be considered meaningfully explanatory at all, distinct from being ruled out for low volume. |
 
# Surprise / Lift
> `lift` is this codebase's simplified stand-in for the Adtributor "surprise" concept in:
>
> (Bhagwan et al, 2016): Bhagwan, R., Kumar, R., Ramjee, R., Varghese, G., Mohapatra, S., Manoharan, H., & Shah, P. *Adtributor: Revenue Debugging in Advertising Systems*. Microsoft Research. [`microsoft.com/en-us/research/wp-content/uploads/2016/02/main-14.pdf`](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/main-14.pdf) - source of Explanatory Power (§3.2, §4.1) and Surprise via Jensen–Shannon divergence (§3.3).

 
## Motivating Problem
EP alone can be misleading. Consider two dimensions for a revenue drop: `Data Center` and `Device Type`. Suppose `Data Center X` provides 94% of forecasted revenue and 94% of actual revenue - its EP for the drop is a huge 94%, just because it is most of the traffic. Its *share* of revenue barely moved (94% forecasted vs. 94% actual). Meanwhile `Device Type: PC` provided 50% of forecasted revenue but swelled to 98% of actual revenue, while `Mobile` and `Tablet` collapsed from a combined 50% to near 0%. This kind of large *swing in share* - not just a large absolute number - is what should draw attention, because a segment that stays proportionally the same size while carrying a big absolute EP is just "along for the ride" of a broad, uniform effect; it is not a localized cause.
 
> TL;DR: A segment with high EP but a stable share is evidence of a broad, dataset-wide effect. A segment with high EP *and* a share that swung disproportionately is evidence of a localized cause specific to that segment.
 
## What Surprise / Lift Provides
The Adtributor paper (Bhagwan et al, 2016) formalizes this with Jensen–Shannon divergence between the forecasted and actual probability distributions across a dimension's elements, calling it **surprise** [1]. This codebase uses a simpler proxy, **lift**:
 
```
lift = EP / expected_share
```
 
Here, `expected_share` is the maximum of the segment's baseline share of total volume and the current share of total volume. A `lift` near `1` means the segment explained roughly as much of the movement as its size alone would predict - i.e. proportional, not a cause. A `lift` well above `1` means the segment is disproportionately responsible relative to its size - i.e. a genuine candidate cause.
 
**Implementation**: See `SegmentResult.lift` and its use as the ranking key in `drill_down`, in [`implementation/rca/attribution.py`](../implementation/rca/attribution.py).
 
## Configured Parameters - Surprise / Lift
 
| Variable | Description |
| --- | --- |
| `lift_thresh` | Minimum lift a segment must clear to be declared the `primary` (localized) cause at a given drill-down level, rather than dismissed as a proportional/broad effect. |
 
# Drill-Down
## General Mechanism
Having found a segment whose EP and lift both clear their thresholds within one dimension (e.g. `region = EU`), the next question is whether the effect is *uniform across* EU, or further concentrated inside it (e.g. `region = EU AND device_model = iPhone 13`). Drill-down answers this by re-running Explanatory Power + Surprise/Lift, scoped to the already-identified segment, across the *remaining* dimensions - recursing until no further sub-segment clears the lift threshold, or a maximum depth is reached.
 
## Dimension Sources in This Dataset
Per the event-stream context (see: ["The Event Stream", `README.md`](../README.md#the-event-stream)) and [`docs/metrics_glossary.md`](./metrics_glossary.md), every event row carries three foreign keys (`app_id`, `geo_device_id`, `advertiser_id`) plus the intrinsic `ad_format` field. Each foreign key resolves, via its lookup table, to dimensions:
 
| Source | Dimensions | When present on a row |
| --- | --- | --- |
| `ad_events` (intrinsic) | `ad_format` (`native`, `video`, `banner`, `interstitial`, `rewarded`) | Always - chosen at request time, before fill/impression/click are known. |
| [`apps.csv`](../data/apps.csv) | `category` (`gaming`, `social`, `entertainment`, `news`, `ecommerce`, `utility`, `finance`), `publisher_tier` (`tier_1`, `tier_2`, `tier_3`) | Always - `app_id` is set on every request, since the request originates from a specific app. |
| [`geo_device.csv`](../data/geo_device.csv) | `region` (`NAM`, `EU`, `APAC`, `LATAM`, `MEA`), `country`, `device_model`, `os_version` | Always - the requesting device/geo is known before the ad decision is made. |
| [`advertisers.csv`](../data/advertisers.csv) | `vertical` (`gaming`, `ecommerce`, `finance`, `travel`, `entertainment`, `auto`, `cpg`), `campaign_type` (`CPM`, `CPC`, `CPI`) | **Only on filled requests** - `advertiser_id` is empty (`''`) until an ad is actually won and served, since no advertiser is associated with an unfilled request. |
 
## Why the Valid Dimension Set Changes per Metric
This last row is the crux of why drill-down is *not* the same recursion over the same seven dimensions for every metric. `Requests` and `Fill rate` are defined over the **pre-fill population**, i.e. every request, filled or not. Slicing that population by `vertical` or `campaign_type` is a category error: a request that never filled has no advertiser, and therefore no vertical, to be grouped by. In [`implementation/rca/attribution.py`](../implementation/rca/attribution.py), `dimensions_for_factor` encodes exactly this:
 
```python
_ADVERTISER_ONLY_DIMENSIONS = {"vertical", "campaign_type"}
_PRE_FILL_FACTORS = {"requests", "fill_rate"}
```
 
| Metric | Population the metric is computed over | Valid drill-down dimensions |
| --- | --- | --- |
| Requests | All requests (pre-fill) | `ad_format`, `category`, `publisher_tier`, `region`, `country`, `device_model`, `os_version` (5 dimension *groups*, 7 columns - advertiser dimensions excluded) |
| Fill rate | All requests (pre-fill, since the denominator `count(*)` spans unfilled rows) | Same as Requests - advertiser dimensions excluded |
| Render rate | Filled requests only (numerator and denominator both post-fill) | All dimension groups, including `vertical`, `campaign_type` |
| CTR | Impressions (post-fill, post-render) | All dimension groups, including `vertical`, `campaign_type` |
| eCPM | Impressions (post-fill, post-render) | All dimension groups, including `vertical`, `campaign_type` |
| Revenue | Impressions (post-fill, post-render) | All dimension groups, including `vertical`, `campaign_type` |
 
So the drill-down recursion for a `Requests` or `Fill rate` anomaly can never propose "advertiser vertical X is the cause" - that candidate is structurally excluded before the query is even run, rather than filtered out after the fact by EP/lift thresholds. For every other metric, all four source tables are eligible dimension providers at every depth of the recursion (subject only to `used_dims`, so a dimension already fixed by a parent level isn't re-evaluated as its own child).
 
## Worked Example Across Metrics
Two anomalies, same underlying dataset, illustrate the difference:
 
- **A `Fill rate` anomaly**: `drill_down(factor="fill_rate", ...)` evaluates `ad_format`, `category`, `publisher_tier`, `region`, `country`, `device_model`, `os_version`. Suppose `os_version = Android 12` shows high EP and lift at depth 0 (e.g. a rendering SDK regression on an older OS build). The recursive call at depth 1 re-evaluates the *same six remaining* dimensions (all but `os_version`, now fixed) - it will never consider `vertical`, because fill rate's population makes that dimension undefined.
- **A `CTR` anomaly**: `drill_down(factor="ctr", ...)` evaluates all seven dimension columns from the start, since CTR is computed over impressions (all post-fill, so `advertiser_id` - and hence `vertical`/`campaign_type` - is always populated). Suppose `vertical = finance` shows high EP and lift (e.g. finance-vertical creatives systematically under-perform on click-through). This candidate cause is only reachable for metrics computed on the filled/impression population; the exact same drill-down run for `Fill rate` structurally cannot surface it.

## Configured Parameters - Drill-Down
 
| Variable | Description |
| --- | --- |
| `max_depth` | Maximum recursion depth - how many dimension-clauses can be conjoined in the final Boolean expression (e.g. `max_depth=2` allows at most `dimension_1 = value_1 AND dimension_2 = value_2`). |
| `dimensions` (or the default from `dimensions_for_factor(factor)`) | The candidate dimension universe at depth 0, which - per the table above - must already be scoped correctly per metric before drill-down starts. |
| `min_volume_share`, `ep_threshold`, `lift_thresh` | Same knobs as the standalone EP/Surprise steps, re-applied at every recursion level to decide whether to keep drilling or stop. |
 
# Integration - Anomaly Detection -> Drill Down
 
```
Metric anomaly detected (z-score on Median/MAD)
        |
        v
Is the metric a composite (currently: only Revenue)?
        |                                   |
       Yes                                  No
        |                                   |
        v                                   v
LMDI decomposition                  Metric is already "atomic":
(decompose_revenue)                 skip straight to EP/Surprise/Drill-down
        |                                   |
        v                                   |
Pick the dominant factor                    |
(largest |factor_contributions[f]|)         |
        |                                   |
        +------------------+----------------+
                            |
                            v
        Explanatory Power, per dimension valid
        ... for this factor's population (dimensions_for_factor)
                            |
                            v
        Surprise / Lift, to separate localized causes
        ... from segments that just moved in proportion
                            |
                            v
        Drill-Down: recurse into the winning segment:
        - Re-scoping the dimension universe if needed
        - Until max_depth or no segment clears lift_thresh
```