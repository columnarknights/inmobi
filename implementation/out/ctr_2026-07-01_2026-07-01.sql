-- Investigation: ctr, 2026-07-01 to 2026-07-01 (baseline: 2026-06-24 to 2026-06-24)

-- Step 1: Baseline window aggregate (2026-06-24 to 2026-06-24)
SELECT
            count() AS requests,
            sum(is_filled) AS fills,
            sum(is_impression) AS impressions,
            sum(is_click) AS clicks,
            sum(revenue) AS revenue_sum
        FROM fact_events
        WHERE event_date BETWEEN '2026-06-24' AND '2026-06-24';

-- Step 2: Current window aggregate (2026-07-01 to 2026-07-01)
SELECT
            count() AS requests,
            sum(is_filled) AS fills,
            sum(is_impression) AS impressions,
            sum(is_click) AS clicks,
            sum(revenue) AS revenue_sum
        FROM fact_events
        WHERE event_date BETWEEN '2026-07-01' AND '2026-07-01';

-- Step 3: Depth 0 — rank segments for dimension 'ad_format'
SELECT
            ad_format AS segment,
            countIf(event_date BETWEEN '2026-06-24' AND '2026-06-24') AS requests_b,
            sumIf(is_filled, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS fills_b,
            sumIf(is_impression, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS impressions_b,
            sumIf(is_click, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS clicks_b,
            sumIf(revenue, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS revenue_b,
            countIf(event_date BETWEEN '2026-07-01' AND '2026-07-01') AS requests_c,
            sumIf(is_filled, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS fills_c,
            sumIf(is_impression, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS impressions_c,
            sumIf(is_click, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS clicks_c,
            sumIf(revenue, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS revenue_c
        FROM fact_events
        WHERE event_date BETWEEN '2026-06-24' AND '2026-07-01'
        -- vertical/campaign_type are '' on unfilled requests (no advertiser assigned,
        -- per metrics_glossary.md); that bucket isn't a real segment value and its
        -- rate is trivially fixed at 0 for any fill-dependent factor, which otherwise
        -- shows up as a phantom high-lift "segment".
        AND ad_format != ''
        GROUP BY segment;

-- Step 4: Depth 0 — rank segments for dimension 'category'
SELECT
            category AS segment,
            countIf(event_date BETWEEN '2026-06-24' AND '2026-06-24') AS requests_b,
            sumIf(is_filled, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS fills_b,
            sumIf(is_impression, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS impressions_b,
            sumIf(is_click, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS clicks_b,
            sumIf(revenue, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS revenue_b,
            countIf(event_date BETWEEN '2026-07-01' AND '2026-07-01') AS requests_c,
            sumIf(is_filled, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS fills_c,
            sumIf(is_impression, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS impressions_c,
            sumIf(is_click, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS clicks_c,
            sumIf(revenue, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS revenue_c
        FROM fact_events
        WHERE event_date BETWEEN '2026-06-24' AND '2026-07-01'
        -- vertical/campaign_type are '' on unfilled requests (no advertiser assigned,
        -- per metrics_glossary.md); that bucket isn't a real segment value and its
        -- rate is trivially fixed at 0 for any fill-dependent factor, which otherwise
        -- shows up as a phantom high-lift "segment".
        AND category != ''
        GROUP BY segment;

-- Step 5: Depth 0 — rank segments for dimension 'publisher_tier'
SELECT
            publisher_tier AS segment,
            countIf(event_date BETWEEN '2026-06-24' AND '2026-06-24') AS requests_b,
            sumIf(is_filled, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS fills_b,
            sumIf(is_impression, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS impressions_b,
            sumIf(is_click, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS clicks_b,
            sumIf(revenue, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS revenue_b,
            countIf(event_date BETWEEN '2026-07-01' AND '2026-07-01') AS requests_c,
            sumIf(is_filled, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS fills_c,
            sumIf(is_impression, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS impressions_c,
            sumIf(is_click, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS clicks_c,
            sumIf(revenue, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS revenue_c
        FROM fact_events
        WHERE event_date BETWEEN '2026-06-24' AND '2026-07-01'
        -- vertical/campaign_type are '' on unfilled requests (no advertiser assigned,
        -- per metrics_glossary.md); that bucket isn't a real segment value and its
        -- rate is trivially fixed at 0 for any fill-dependent factor, which otherwise
        -- shows up as a phantom high-lift "segment".
        AND publisher_tier != ''
        GROUP BY segment;

-- Step 6: Depth 0 — rank segments for dimension 'vertical'
SELECT
            vertical AS segment,
            countIf(event_date BETWEEN '2026-06-24' AND '2026-06-24') AS requests_b,
            sumIf(is_filled, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS fills_b,
            sumIf(is_impression, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS impressions_b,
            sumIf(is_click, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS clicks_b,
            sumIf(revenue, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS revenue_b,
            countIf(event_date BETWEEN '2026-07-01' AND '2026-07-01') AS requests_c,
            sumIf(is_filled, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS fills_c,
            sumIf(is_impression, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS impressions_c,
            sumIf(is_click, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS clicks_c,
            sumIf(revenue, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS revenue_c
        FROM fact_events
        WHERE event_date BETWEEN '2026-06-24' AND '2026-07-01'
        -- vertical/campaign_type are '' on unfilled requests (no advertiser assigned,
        -- per metrics_glossary.md); that bucket isn't a real segment value and its
        -- rate is trivially fixed at 0 for any fill-dependent factor, which otherwise
        -- shows up as a phantom high-lift "segment".
        AND vertical != ''
        GROUP BY segment;

-- Step 7: Depth 0 — rank segments for dimension 'campaign_type'
SELECT
            campaign_type AS segment,
            countIf(event_date BETWEEN '2026-06-24' AND '2026-06-24') AS requests_b,
            sumIf(is_filled, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS fills_b,
            sumIf(is_impression, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS impressions_b,
            sumIf(is_click, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS clicks_b,
            sumIf(revenue, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS revenue_b,
            countIf(event_date BETWEEN '2026-07-01' AND '2026-07-01') AS requests_c,
            sumIf(is_filled, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS fills_c,
            sumIf(is_impression, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS impressions_c,
            sumIf(is_click, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS clicks_c,
            sumIf(revenue, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS revenue_c
        FROM fact_events
        WHERE event_date BETWEEN '2026-06-24' AND '2026-07-01'
        -- vertical/campaign_type are '' on unfilled requests (no advertiser assigned,
        -- per metrics_glossary.md); that bucket isn't a real segment value and its
        -- rate is trivially fixed at 0 for any fill-dependent factor, which otherwise
        -- shows up as a phantom high-lift "segment".
        AND campaign_type != ''
        GROUP BY segment;

-- Step 8: Depth 0 — rank segments for dimension 'region'
SELECT
            region AS segment,
            countIf(event_date BETWEEN '2026-06-24' AND '2026-06-24') AS requests_b,
            sumIf(is_filled, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS fills_b,
            sumIf(is_impression, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS impressions_b,
            sumIf(is_click, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS clicks_b,
            sumIf(revenue, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS revenue_b,
            countIf(event_date BETWEEN '2026-07-01' AND '2026-07-01') AS requests_c,
            sumIf(is_filled, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS fills_c,
            sumIf(is_impression, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS impressions_c,
            sumIf(is_click, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS clicks_c,
            sumIf(revenue, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS revenue_c
        FROM fact_events
        WHERE event_date BETWEEN '2026-06-24' AND '2026-07-01'
        -- vertical/campaign_type are '' on unfilled requests (no advertiser assigned,
        -- per metrics_glossary.md); that bucket isn't a real segment value and its
        -- rate is trivially fixed at 0 for any fill-dependent factor, which otherwise
        -- shows up as a phantom high-lift "segment".
        AND region != ''
        GROUP BY segment;

-- Step 9: Depth 0 — rank segments for dimension 'country'
SELECT
            country AS segment,
            countIf(event_date BETWEEN '2026-06-24' AND '2026-06-24') AS requests_b,
            sumIf(is_filled, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS fills_b,
            sumIf(is_impression, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS impressions_b,
            sumIf(is_click, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS clicks_b,
            sumIf(revenue, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS revenue_b,
            countIf(event_date BETWEEN '2026-07-01' AND '2026-07-01') AS requests_c,
            sumIf(is_filled, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS fills_c,
            sumIf(is_impression, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS impressions_c,
            sumIf(is_click, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS clicks_c,
            sumIf(revenue, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS revenue_c
        FROM fact_events
        WHERE event_date BETWEEN '2026-06-24' AND '2026-07-01'
        -- vertical/campaign_type are '' on unfilled requests (no advertiser assigned,
        -- per metrics_glossary.md); that bucket isn't a real segment value and its
        -- rate is trivially fixed at 0 for any fill-dependent factor, which otherwise
        -- shows up as a phantom high-lift "segment".
        AND country != ''
        GROUP BY segment;

-- Step 10: Depth 0 — rank segments for dimension 'device_model'
SELECT
            device_model AS segment,
            countIf(event_date BETWEEN '2026-06-24' AND '2026-06-24') AS requests_b,
            sumIf(is_filled, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS fills_b,
            sumIf(is_impression, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS impressions_b,
            sumIf(is_click, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS clicks_b,
            sumIf(revenue, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS revenue_b,
            countIf(event_date BETWEEN '2026-07-01' AND '2026-07-01') AS requests_c,
            sumIf(is_filled, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS fills_c,
            sumIf(is_impression, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS impressions_c,
            sumIf(is_click, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS clicks_c,
            sumIf(revenue, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS revenue_c
        FROM fact_events
        WHERE event_date BETWEEN '2026-06-24' AND '2026-07-01'
        -- vertical/campaign_type are '' on unfilled requests (no advertiser assigned,
        -- per metrics_glossary.md); that bucket isn't a real segment value and its
        -- rate is trivially fixed at 0 for any fill-dependent factor, which otherwise
        -- shows up as a phantom high-lift "segment".
        AND device_model != ''
        GROUP BY segment;

-- Step 11: Depth 0 — rank segments for dimension 'os_version'
SELECT
            os_version AS segment,
            countIf(event_date BETWEEN '2026-06-24' AND '2026-06-24') AS requests_b,
            sumIf(is_filled, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS fills_b,
            sumIf(is_impression, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS impressions_b,
            sumIf(is_click, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS clicks_b,
            sumIf(revenue, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS revenue_b,
            countIf(event_date BETWEEN '2026-07-01' AND '2026-07-01') AS requests_c,
            sumIf(is_filled, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS fills_c,
            sumIf(is_impression, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS impressions_c,
            sumIf(is_click, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS clicks_c,
            sumIf(revenue, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS revenue_c
        FROM fact_events
        WHERE event_date BETWEEN '2026-06-24' AND '2026-07-01'
        -- vertical/campaign_type are '' on unfilled requests (no advertiser assigned,
        -- per metrics_glossary.md); that bucket isn't a real segment value and its
        -- rate is trivially fixed at 0 for any fill-dependent factor, which otherwise
        -- shows up as a phantom high-lift "segment".
        AND os_version != ''
        GROUP BY segment;

-- Step 12: Depth 1 (within ad_format=rewarded) — rank segments for dimension 'category'
SELECT
            category AS segment,
            countIf(event_date BETWEEN '2026-06-24' AND '2026-06-24') AS requests_b,
            sumIf(is_filled, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS fills_b,
            sumIf(is_impression, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS impressions_b,
            sumIf(is_click, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS clicks_b,
            sumIf(revenue, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS revenue_b,
            countIf(event_date BETWEEN '2026-07-01' AND '2026-07-01') AS requests_c,
            sumIf(is_filled, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS fills_c,
            sumIf(is_impression, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS impressions_c,
            sumIf(is_click, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS clicks_c,
            sumIf(revenue, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS revenue_c
        FROM fact_events
        WHERE event_date BETWEEN '2026-06-24' AND '2026-07-01'
        -- vertical/campaign_type are '' on unfilled requests (no advertiser assigned,
        -- per metrics_glossary.md); that bucket isn't a real segment value and its
        -- rate is trivially fixed at 0 for any fill-dependent factor, which otherwise
        -- shows up as a phantom high-lift "segment".
        AND category != ''
        AND ad_format = 'rewarded'
        GROUP BY segment;

-- Step 13: Depth 1 (within ad_format=rewarded) — rank segments for dimension 'publisher_tier'
SELECT
            publisher_tier AS segment,
            countIf(event_date BETWEEN '2026-06-24' AND '2026-06-24') AS requests_b,
            sumIf(is_filled, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS fills_b,
            sumIf(is_impression, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS impressions_b,
            sumIf(is_click, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS clicks_b,
            sumIf(revenue, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS revenue_b,
            countIf(event_date BETWEEN '2026-07-01' AND '2026-07-01') AS requests_c,
            sumIf(is_filled, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS fills_c,
            sumIf(is_impression, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS impressions_c,
            sumIf(is_click, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS clicks_c,
            sumIf(revenue, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS revenue_c
        FROM fact_events
        WHERE event_date BETWEEN '2026-06-24' AND '2026-07-01'
        -- vertical/campaign_type are '' on unfilled requests (no advertiser assigned,
        -- per metrics_glossary.md); that bucket isn't a real segment value and its
        -- rate is trivially fixed at 0 for any fill-dependent factor, which otherwise
        -- shows up as a phantom high-lift "segment".
        AND publisher_tier != ''
        AND ad_format = 'rewarded'
        GROUP BY segment;

-- Step 14: Depth 1 (within ad_format=rewarded) — rank segments for dimension 'vertical'
SELECT
            vertical AS segment,
            countIf(event_date BETWEEN '2026-06-24' AND '2026-06-24') AS requests_b,
            sumIf(is_filled, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS fills_b,
            sumIf(is_impression, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS impressions_b,
            sumIf(is_click, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS clicks_b,
            sumIf(revenue, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS revenue_b,
            countIf(event_date BETWEEN '2026-07-01' AND '2026-07-01') AS requests_c,
            sumIf(is_filled, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS fills_c,
            sumIf(is_impression, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS impressions_c,
            sumIf(is_click, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS clicks_c,
            sumIf(revenue, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS revenue_c
        FROM fact_events
        WHERE event_date BETWEEN '2026-06-24' AND '2026-07-01'
        -- vertical/campaign_type are '' on unfilled requests (no advertiser assigned,
        -- per metrics_glossary.md); that bucket isn't a real segment value and its
        -- rate is trivially fixed at 0 for any fill-dependent factor, which otherwise
        -- shows up as a phantom high-lift "segment".
        AND vertical != ''
        AND ad_format = 'rewarded'
        GROUP BY segment;

-- Step 15: Depth 1 (within ad_format=rewarded) — rank segments for dimension 'campaign_type'
SELECT
            campaign_type AS segment,
            countIf(event_date BETWEEN '2026-06-24' AND '2026-06-24') AS requests_b,
            sumIf(is_filled, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS fills_b,
            sumIf(is_impression, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS impressions_b,
            sumIf(is_click, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS clicks_b,
            sumIf(revenue, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS revenue_b,
            countIf(event_date BETWEEN '2026-07-01' AND '2026-07-01') AS requests_c,
            sumIf(is_filled, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS fills_c,
            sumIf(is_impression, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS impressions_c,
            sumIf(is_click, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS clicks_c,
            sumIf(revenue, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS revenue_c
        FROM fact_events
        WHERE event_date BETWEEN '2026-06-24' AND '2026-07-01'
        -- vertical/campaign_type are '' on unfilled requests (no advertiser assigned,
        -- per metrics_glossary.md); that bucket isn't a real segment value and its
        -- rate is trivially fixed at 0 for any fill-dependent factor, which otherwise
        -- shows up as a phantom high-lift "segment".
        AND campaign_type != ''
        AND ad_format = 'rewarded'
        GROUP BY segment;

-- Step 16: Depth 1 (within ad_format=rewarded) — rank segments for dimension 'region'
SELECT
            region AS segment,
            countIf(event_date BETWEEN '2026-06-24' AND '2026-06-24') AS requests_b,
            sumIf(is_filled, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS fills_b,
            sumIf(is_impression, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS impressions_b,
            sumIf(is_click, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS clicks_b,
            sumIf(revenue, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS revenue_b,
            countIf(event_date BETWEEN '2026-07-01' AND '2026-07-01') AS requests_c,
            sumIf(is_filled, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS fills_c,
            sumIf(is_impression, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS impressions_c,
            sumIf(is_click, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS clicks_c,
            sumIf(revenue, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS revenue_c
        FROM fact_events
        WHERE event_date BETWEEN '2026-06-24' AND '2026-07-01'
        -- vertical/campaign_type are '' on unfilled requests (no advertiser assigned,
        -- per metrics_glossary.md); that bucket isn't a real segment value and its
        -- rate is trivially fixed at 0 for any fill-dependent factor, which otherwise
        -- shows up as a phantom high-lift "segment".
        AND region != ''
        AND ad_format = 'rewarded'
        GROUP BY segment;

-- Step 17: Depth 1 (within ad_format=rewarded) — rank segments for dimension 'country'
SELECT
            country AS segment,
            countIf(event_date BETWEEN '2026-06-24' AND '2026-06-24') AS requests_b,
            sumIf(is_filled, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS fills_b,
            sumIf(is_impression, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS impressions_b,
            sumIf(is_click, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS clicks_b,
            sumIf(revenue, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS revenue_b,
            countIf(event_date BETWEEN '2026-07-01' AND '2026-07-01') AS requests_c,
            sumIf(is_filled, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS fills_c,
            sumIf(is_impression, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS impressions_c,
            sumIf(is_click, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS clicks_c,
            sumIf(revenue, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS revenue_c
        FROM fact_events
        WHERE event_date BETWEEN '2026-06-24' AND '2026-07-01'
        -- vertical/campaign_type are '' on unfilled requests (no advertiser assigned,
        -- per metrics_glossary.md); that bucket isn't a real segment value and its
        -- rate is trivially fixed at 0 for any fill-dependent factor, which otherwise
        -- shows up as a phantom high-lift "segment".
        AND country != ''
        AND ad_format = 'rewarded'
        GROUP BY segment;

-- Step 18: Depth 1 (within ad_format=rewarded) — rank segments for dimension 'device_model'
SELECT
            device_model AS segment,
            countIf(event_date BETWEEN '2026-06-24' AND '2026-06-24') AS requests_b,
            sumIf(is_filled, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS fills_b,
            sumIf(is_impression, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS impressions_b,
            sumIf(is_click, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS clicks_b,
            sumIf(revenue, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS revenue_b,
            countIf(event_date BETWEEN '2026-07-01' AND '2026-07-01') AS requests_c,
            sumIf(is_filled, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS fills_c,
            sumIf(is_impression, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS impressions_c,
            sumIf(is_click, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS clicks_c,
            sumIf(revenue, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS revenue_c
        FROM fact_events
        WHERE event_date BETWEEN '2026-06-24' AND '2026-07-01'
        -- vertical/campaign_type are '' on unfilled requests (no advertiser assigned,
        -- per metrics_glossary.md); that bucket isn't a real segment value and its
        -- rate is trivially fixed at 0 for any fill-dependent factor, which otherwise
        -- shows up as a phantom high-lift "segment".
        AND device_model != ''
        AND ad_format = 'rewarded'
        GROUP BY segment;

-- Step 19: Depth 1 (within ad_format=rewarded) — rank segments for dimension 'os_version'
SELECT
            os_version AS segment,
            countIf(event_date BETWEEN '2026-06-24' AND '2026-06-24') AS requests_b,
            sumIf(is_filled, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS fills_b,
            sumIf(is_impression, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS impressions_b,
            sumIf(is_click, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS clicks_b,
            sumIf(revenue, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS revenue_b,
            countIf(event_date BETWEEN '2026-07-01' AND '2026-07-01') AS requests_c,
            sumIf(is_filled, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS fills_c,
            sumIf(is_impression, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS impressions_c,
            sumIf(is_click, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS clicks_c,
            sumIf(revenue, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS revenue_c
        FROM fact_events
        WHERE event_date BETWEEN '2026-06-24' AND '2026-07-01'
        -- vertical/campaign_type are '' on unfilled requests (no advertiser assigned,
        -- per metrics_glossary.md); that bucket isn't a real segment value and its
        -- rate is trivially fixed at 0 for any fill-dependent factor, which otherwise
        -- shows up as a phantom high-lift "segment".
        AND os_version != ''
        AND ad_format = 'rewarded'
        GROUP BY segment;

-- Step 20: Depth 1 (within os_version=Android 13) — rank segments for dimension 'ad_format'
SELECT
            ad_format AS segment,
            countIf(event_date BETWEEN '2026-06-24' AND '2026-06-24') AS requests_b,
            sumIf(is_filled, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS fills_b,
            sumIf(is_impression, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS impressions_b,
            sumIf(is_click, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS clicks_b,
            sumIf(revenue, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS revenue_b,
            countIf(event_date BETWEEN '2026-07-01' AND '2026-07-01') AS requests_c,
            sumIf(is_filled, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS fills_c,
            sumIf(is_impression, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS impressions_c,
            sumIf(is_click, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS clicks_c,
            sumIf(revenue, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS revenue_c
        FROM fact_events
        WHERE event_date BETWEEN '2026-06-24' AND '2026-07-01'
        -- vertical/campaign_type are '' on unfilled requests (no advertiser assigned,
        -- per metrics_glossary.md); that bucket isn't a real segment value and its
        -- rate is trivially fixed at 0 for any fill-dependent factor, which otherwise
        -- shows up as a phantom high-lift "segment".
        AND ad_format != ''
        AND os_version = 'Android 13'
        GROUP BY segment;

-- Step 21: Depth 1 (within os_version=Android 13) — rank segments for dimension 'category'
SELECT
            category AS segment,
            countIf(event_date BETWEEN '2026-06-24' AND '2026-06-24') AS requests_b,
            sumIf(is_filled, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS fills_b,
            sumIf(is_impression, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS impressions_b,
            sumIf(is_click, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS clicks_b,
            sumIf(revenue, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS revenue_b,
            countIf(event_date BETWEEN '2026-07-01' AND '2026-07-01') AS requests_c,
            sumIf(is_filled, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS fills_c,
            sumIf(is_impression, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS impressions_c,
            sumIf(is_click, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS clicks_c,
            sumIf(revenue, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS revenue_c
        FROM fact_events
        WHERE event_date BETWEEN '2026-06-24' AND '2026-07-01'
        -- vertical/campaign_type are '' on unfilled requests (no advertiser assigned,
        -- per metrics_glossary.md); that bucket isn't a real segment value and its
        -- rate is trivially fixed at 0 for any fill-dependent factor, which otherwise
        -- shows up as a phantom high-lift "segment".
        AND category != ''
        AND os_version = 'Android 13'
        GROUP BY segment;

-- Step 22: Depth 1 (within os_version=Android 13) — rank segments for dimension 'publisher_tier'
SELECT
            publisher_tier AS segment,
            countIf(event_date BETWEEN '2026-06-24' AND '2026-06-24') AS requests_b,
            sumIf(is_filled, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS fills_b,
            sumIf(is_impression, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS impressions_b,
            sumIf(is_click, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS clicks_b,
            sumIf(revenue, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS revenue_b,
            countIf(event_date BETWEEN '2026-07-01' AND '2026-07-01') AS requests_c,
            sumIf(is_filled, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS fills_c,
            sumIf(is_impression, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS impressions_c,
            sumIf(is_click, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS clicks_c,
            sumIf(revenue, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS revenue_c
        FROM fact_events
        WHERE event_date BETWEEN '2026-06-24' AND '2026-07-01'
        -- vertical/campaign_type are '' on unfilled requests (no advertiser assigned,
        -- per metrics_glossary.md); that bucket isn't a real segment value and its
        -- rate is trivially fixed at 0 for any fill-dependent factor, which otherwise
        -- shows up as a phantom high-lift "segment".
        AND publisher_tier != ''
        AND os_version = 'Android 13'
        GROUP BY segment;

-- Step 23: Depth 1 (within os_version=Android 13) — rank segments for dimension 'vertical'
SELECT
            vertical AS segment,
            countIf(event_date BETWEEN '2026-06-24' AND '2026-06-24') AS requests_b,
            sumIf(is_filled, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS fills_b,
            sumIf(is_impression, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS impressions_b,
            sumIf(is_click, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS clicks_b,
            sumIf(revenue, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS revenue_b,
            countIf(event_date BETWEEN '2026-07-01' AND '2026-07-01') AS requests_c,
            sumIf(is_filled, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS fills_c,
            sumIf(is_impression, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS impressions_c,
            sumIf(is_click, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS clicks_c,
            sumIf(revenue, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS revenue_c
        FROM fact_events
        WHERE event_date BETWEEN '2026-06-24' AND '2026-07-01'
        -- vertical/campaign_type are '' on unfilled requests (no advertiser assigned,
        -- per metrics_glossary.md); that bucket isn't a real segment value and its
        -- rate is trivially fixed at 0 for any fill-dependent factor, which otherwise
        -- shows up as a phantom high-lift "segment".
        AND vertical != ''
        AND os_version = 'Android 13'
        GROUP BY segment;

-- Step 24: Depth 1 (within os_version=Android 13) — rank segments for dimension 'campaign_type'
SELECT
            campaign_type AS segment,
            countIf(event_date BETWEEN '2026-06-24' AND '2026-06-24') AS requests_b,
            sumIf(is_filled, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS fills_b,
            sumIf(is_impression, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS impressions_b,
            sumIf(is_click, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS clicks_b,
            sumIf(revenue, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS revenue_b,
            countIf(event_date BETWEEN '2026-07-01' AND '2026-07-01') AS requests_c,
            sumIf(is_filled, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS fills_c,
            sumIf(is_impression, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS impressions_c,
            sumIf(is_click, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS clicks_c,
            sumIf(revenue, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS revenue_c
        FROM fact_events
        WHERE event_date BETWEEN '2026-06-24' AND '2026-07-01'
        -- vertical/campaign_type are '' on unfilled requests (no advertiser assigned,
        -- per metrics_glossary.md); that bucket isn't a real segment value and its
        -- rate is trivially fixed at 0 for any fill-dependent factor, which otherwise
        -- shows up as a phantom high-lift "segment".
        AND campaign_type != ''
        AND os_version = 'Android 13'
        GROUP BY segment;

-- Step 25: Depth 1 (within os_version=Android 13) — rank segments for dimension 'region'
SELECT
            region AS segment,
            countIf(event_date BETWEEN '2026-06-24' AND '2026-06-24') AS requests_b,
            sumIf(is_filled, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS fills_b,
            sumIf(is_impression, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS impressions_b,
            sumIf(is_click, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS clicks_b,
            sumIf(revenue, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS revenue_b,
            countIf(event_date BETWEEN '2026-07-01' AND '2026-07-01') AS requests_c,
            sumIf(is_filled, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS fills_c,
            sumIf(is_impression, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS impressions_c,
            sumIf(is_click, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS clicks_c,
            sumIf(revenue, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS revenue_c
        FROM fact_events
        WHERE event_date BETWEEN '2026-06-24' AND '2026-07-01'
        -- vertical/campaign_type are '' on unfilled requests (no advertiser assigned,
        -- per metrics_glossary.md); that bucket isn't a real segment value and its
        -- rate is trivially fixed at 0 for any fill-dependent factor, which otherwise
        -- shows up as a phantom high-lift "segment".
        AND region != ''
        AND os_version = 'Android 13'
        GROUP BY segment;

-- Step 26: Depth 1 (within os_version=Android 13) — rank segments for dimension 'country'
SELECT
            country AS segment,
            countIf(event_date BETWEEN '2026-06-24' AND '2026-06-24') AS requests_b,
            sumIf(is_filled, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS fills_b,
            sumIf(is_impression, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS impressions_b,
            sumIf(is_click, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS clicks_b,
            sumIf(revenue, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS revenue_b,
            countIf(event_date BETWEEN '2026-07-01' AND '2026-07-01') AS requests_c,
            sumIf(is_filled, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS fills_c,
            sumIf(is_impression, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS impressions_c,
            sumIf(is_click, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS clicks_c,
            sumIf(revenue, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS revenue_c
        FROM fact_events
        WHERE event_date BETWEEN '2026-06-24' AND '2026-07-01'
        -- vertical/campaign_type are '' on unfilled requests (no advertiser assigned,
        -- per metrics_glossary.md); that bucket isn't a real segment value and its
        -- rate is trivially fixed at 0 for any fill-dependent factor, which otherwise
        -- shows up as a phantom high-lift "segment".
        AND country != ''
        AND os_version = 'Android 13'
        GROUP BY segment;

-- Step 27: Depth 1 (within os_version=Android 13) — rank segments for dimension 'device_model'
SELECT
            device_model AS segment,
            countIf(event_date BETWEEN '2026-06-24' AND '2026-06-24') AS requests_b,
            sumIf(is_filled, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS fills_b,
            sumIf(is_impression, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS impressions_b,
            sumIf(is_click, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS clicks_b,
            sumIf(revenue, event_date BETWEEN '2026-06-24' AND '2026-06-24') AS revenue_b,
            countIf(event_date BETWEEN '2026-07-01' AND '2026-07-01') AS requests_c,
            sumIf(is_filled, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS fills_c,
            sumIf(is_impression, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS impressions_c,
            sumIf(is_click, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS clicks_c,
            sumIf(revenue, event_date BETWEEN '2026-07-01' AND '2026-07-01') AS revenue_c
        FROM fact_events
        WHERE event_date BETWEEN '2026-06-24' AND '2026-07-01'
        -- vertical/campaign_type are '' on unfilled requests (no advertiser assigned,
        -- per metrics_glossary.md); that bucket isn't a real segment value and its
        -- rate is trivially fixed at 0 for any fill-dependent factor, which otherwise
        -- shows up as a phantom high-lift "segment".
        AND device_model != ''
        AND os_version = 'Android 13'
        GROUP BY segment;
