-- ==========================================================================
-- validation_queries.sql
-- Luxury Housing Sales Analysis - Bengaluru
-- --------------------------------------------------------------------------
-- Post-load checks. sql_loader.py parses this file and runs every block, so
-- each block must be a single statement introduced by a "-- name:" label.
--
-- Blocks 1-3 are the three checks named explicitly in the project brief.
-- ==========================================================================


-- name: 1. Total record count
SELECT COUNT(*) AS total_records
FROM luxury_housing;


-- name: 2. Records grouped by booking status
SELECT
    booking_status,
    COUNT(*)                                              AS record_count,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM luxury_housing), 2) AS pct_of_total
FROM luxury_housing
GROUP BY booking_status
ORDER BY record_count DESC;


-- name: 3. Average ticket price per builder
SELECT
    developer_name                                        AS builder,
    COUNT(*)                                              AS properties,
    ROUND(AVG(ticket_price_cr), 2)                        AS avg_ticket_price_cr,
    ROUND(AVG(price_per_sqft), 0)                         AS avg_price_per_sqft
FROM luxury_housing
WHERE is_price_outlier = 0
GROUP BY developer_name
ORDER BY avg_ticket_price_cr DESC;


-- name: 4. Referential integrity - nulls in required columns
SELECT
    SUM(CASE WHEN property_id       IS NULL THEN 1 ELSE 0 END) AS null_property_id,
    SUM(CASE WHEN ticket_price_cr   IS NULL THEN 1 ELSE 0 END) AS null_price,
    SUM(CASE WHEN unit_size_sqft    IS NULL THEN 1 ELSE 0 END) AS null_size,
    SUM(CASE WHEN amenity_score     IS NULL THEN 1 ELSE 0 END) AS null_amenity,
    SUM(CASE WHEN micro_market      IS NULL THEN 1 ELSE 0 END) AS null_market,
    SUM(CASE WHEN purchase_date     IS NULL THEN 1 ELSE 0 END) AS null_date
FROM luxury_housing;


-- name: 5. Uniqueness of the primary key
SELECT
    COUNT(*)                        AS total_rows,
    COUNT(DISTINCT property_id)     AS distinct_property_ids,
    COUNT(*) - COUNT(DISTINCT property_id) AS duplicate_ids
FROM luxury_housing;


-- name: 6. Categorical cardinality after cleaning
SELECT
    COUNT(DISTINCT micro_market)      AS micro_markets,
    COUNT(DISTINCT developer_name)    AS builders,
    COUNT(DISTINCT configuration)     AS configurations,
    COUNT(DISTINCT possession_status) AS possession_statuses,
    COUNT(DISTINCT sales_channel)     AS sales_channels,
    COUNT(DISTINCT buyer_type)        AS buyer_types,
    COUNT(DISTINCT quarter_label)     AS quarters
FROM luxury_housing;


-- name: 7. Value ranges are plausible
SELECT
    ROUND(MIN(ticket_price_cr), 2)  AS min_price_cr,
    ROUND(MAX(ticket_price_cr), 2)  AS max_price_cr,
    ROUND(MIN(unit_size_sqft), 0)   AS min_sqft,
    ROUND(MAX(unit_size_sqft), 0)   AS max_sqft,
    ROUND(MIN(amenity_score), 2)    AS min_amenity,
    ROUND(MAX(amenity_score), 2)    AS max_amenity,
    MIN(purchase_date)              AS earliest_quarter,
    MAX(purchase_date)              AS latest_quarter
FROM luxury_housing;


-- name: 8. Top 10 micro-markets by booking conversion
SELECT
    micro_market,
    COUNT(*)                                              AS properties,
    SUM(booking_flag)                                     AS bookings,
    ROUND(100.0 * SUM(booking_flag) / COUNT(*), 2)        AS conversion_pct,
    ROUND(AVG(price_per_sqft), 0)                         AS avg_price_per_sqft
FROM luxury_housing
WHERE is_price_outlier = 0
GROUP BY micro_market
ORDER BY conversion_pct DESC
LIMIT 10;


-- name: 9. Amenity band vs booking conversion
SELECT
    amenity_band,
    COUNT(*)                                              AS properties,
    ROUND(AVG(amenity_score), 2)                          AS avg_amenity_score,
    ROUND(100.0 * SUM(booking_flag) / COUNT(*), 2)        AS conversion_pct
FROM luxury_housing
WHERE is_price_outlier = 0
GROUP BY amenity_band
ORDER BY avg_amenity_score;


-- name: 10. Quarter-over-quarter volume and pricing
SELECT
    quarter_label,
    COUNT(*)                                              AS properties,
    ROUND(AVG(ticket_price_cr), 2)                        AS avg_price_cr,
    ROUND(AVG(price_per_sqft), 0)                         AS avg_price_per_sqft,
    ROUND(100.0 * SUM(booking_flag) / COUNT(*), 2)        AS conversion_pct
FROM luxury_housing
WHERE is_price_outlier = 0
GROUP BY quarter_label
ORDER BY quarter_label;


-- name: 11. Buyer sentiment distribution
SELECT
    comment_sentiment,
    COUNT(*)                                              AS mentions,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM luxury_housing), 2) AS pct_of_total,
    ROUND(100.0 * SUM(booking_flag) / COUNT(*), 2)        AS conversion_pct
FROM luxury_housing
GROUP BY comment_sentiment
ORDER BY mentions DESC;


-- name: 12. Share of imputed values (cleaning transparency)
SELECT
    SUM(price_imputed)                                    AS imputed_prices,
    SUM(size_imputed)                                     AS imputed_sizes,
    SUM(amenity_imputed)                                  AS imputed_amenity_scores,
    SUM(is_price_outlier)                                 AS flagged_price_outliers,
    COUNT(*)                                              AS total_rows
FROM luxury_housing;
