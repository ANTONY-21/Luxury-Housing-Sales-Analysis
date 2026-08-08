-- ==========================================================================
-- analytics_views.sql
-- Luxury Housing Sales Analysis - Bengaluru
-- --------------------------------------------------------------------------
-- Pre-aggregated views, one per business use case in the brief. Power BI can
-- import these directly instead of pushing the aggregation into DAX, which
-- keeps the model small and the report fast.
--
-- DROP + CREATE is used rather than CREATE OR REPLACE because SQLite has no
-- CREATE OR REPLACE VIEW and MySQL has no CREATE VIEW IF NOT EXISTS.
-- ==========================================================================


-- --------------------------------------------------------------------------
-- 0. Flat base view for Power BI.
--    Exposes developer_name under the brief's name ("builder") and hides the
--    injected price outliers, which otherwise drag every average upward.
-- --------------------------------------------------------------------------
DROP VIEW IF EXISTS vw_dashboard_base;
CREATE VIEW vw_dashboard_base AS
SELECT
    property_id,
    project_name,
    developer_name          AS builder,
    micro_market,
    latitude,
    longitude,
    map_location,
    configuration,
    unit_size_sqft,
    size_category,
    ticket_price_cr,
    price_per_sqft,
    price_segment,
    transaction_type,
    booking_flag,
    booking_status,
    possession_status,
    sales_channel,
    buyer_type,
    nri_buyer,
    buyer_comments,
    comment_sentiment,
    amenity_score,
    amenity_band,
    connectivity_score,
    locality_infra_score,
    avg_traffic_time_min,
    purchase_date,
    purchase_year,
    quarter_number,
    quarter_label,
    fiscal_year
FROM luxury_housing
WHERE is_price_outlier = 0;


-- --------------------------------------------------------------------------
-- 1. Market Intelligence - builder-wise performance.
-- --------------------------------------------------------------------------
DROP VIEW IF EXISTS vw_builder_performance;
CREATE VIEW vw_builder_performance AS
SELECT
    developer_name                                        AS builder,
    COUNT(*)                                              AS total_properties,
    ROUND(AVG(ticket_price_cr), 2)                        AS avg_ticket_price_cr,
    ROUND(SUM(ticket_price_cr), 2)                        AS total_pipeline_value_cr,
    ROUND(AVG(price_per_sqft), 0)                         AS avg_price_per_sqft,
    ROUND(AVG(unit_size_sqft), 0)                         AS avg_unit_size_sqft,
    SUM(booking_flag)                                     AS total_bookings,
    ROUND(100.0 * SUM(booking_flag) / COUNT(*), 2)        AS booking_conversion_pct,
    ROUND(AVG(amenity_score), 2)                          AS avg_amenity_score,
    COUNT(DISTINCT micro_market)                          AS markets_present
FROM luxury_housing
WHERE is_price_outlier = 0
GROUP BY developer_name;


-- --------------------------------------------------------------------------
-- 2. Market Intelligence - micro-market performance.
-- --------------------------------------------------------------------------
DROP VIEW IF EXISTS vw_micro_market_summary;
CREATE VIEW vw_micro_market_summary AS
SELECT
    micro_market,
    MIN(latitude)                                         AS latitude,
    MIN(longitude)                                        AS longitude,
    MIN(map_location)                                     AS map_location,
    COUNT(*)                                              AS total_properties,
    ROUND(AVG(ticket_price_cr), 2)                        AS avg_ticket_price_cr,
    ROUND(AVG(price_per_sqft), 0)                         AS avg_price_per_sqft,
    SUM(booking_flag)                                     AS total_bookings,
    ROUND(100.0 * SUM(booking_flag) / COUNT(*), 2)        AS booking_conversion_pct,
    ROUND(AVG(amenity_score), 2)                          AS avg_amenity_score,
    ROUND(AVG(connectivity_score), 2)                     AS avg_connectivity_score,
    ROUND(AVG(locality_infra_score), 2)                   AS avg_infra_score,
    ROUND(AVG(avg_traffic_time_min), 1)                   AS avg_traffic_time_min,
    COUNT(DISTINCT developer_name)                        AS competing_builders
FROM luxury_housing
WHERE is_price_outlier = 0
GROUP BY micro_market;


-- --------------------------------------------------------------------------
-- 3. Quarterly Trend Tracking.
-- --------------------------------------------------------------------------
DROP VIEW IF EXISTS vw_quarterly_trends;
CREATE VIEW vw_quarterly_trends AS
SELECT
    quarter_label,
    fiscal_year,
    purchase_year,
    quarter_number,
    COUNT(*)                                              AS total_properties,
    ROUND(AVG(ticket_price_cr), 2)                        AS avg_ticket_price_cr,
    ROUND(SUM(ticket_price_cr), 2)                        AS total_value_cr,
    ROUND(AVG(price_per_sqft), 0)                         AS avg_price_per_sqft,
    SUM(booking_flag)                                     AS total_bookings,
    ROUND(100.0 * SUM(booking_flag) / COUNT(*), 2)        AS booking_conversion_pct
FROM luxury_housing
WHERE is_price_outlier = 0
GROUP BY quarter_label, fiscal_year, purchase_year, quarter_number;


-- --------------------------------------------------------------------------
-- 4. Market Intelligence - configuration demand shift.
-- --------------------------------------------------------------------------
DROP VIEW IF EXISTS vw_configuration_demand;
CREATE VIEW vw_configuration_demand AS
SELECT
    configuration,
    quarter_label,
    COUNT(*)                                              AS total_properties,
    ROUND(AVG(ticket_price_cr), 2)                        AS avg_ticket_price_cr,
    ROUND(AVG(price_per_sqft), 0)                         AS avg_price_per_sqft,
    SUM(booking_flag)                                     AS total_bookings,
    ROUND(100.0 * SUM(booking_flag) / COUNT(*), 2)        AS booking_conversion_pct
FROM luxury_housing
WHERE is_price_outlier = 0
GROUP BY configuration, quarter_label;


-- --------------------------------------------------------------------------
-- 5. Sales Optimization - channel drop-off.
-- --------------------------------------------------------------------------
DROP VIEW IF EXISTS vw_sales_channel_performance;
CREATE VIEW vw_sales_channel_performance AS
SELECT
    sales_channel,
    possession_status,
    COUNT(*)                                              AS total_properties,
    SUM(booking_flag)                                     AS total_bookings,
    COUNT(*) - SUM(booking_flag)                          AS drop_offs,
    ROUND(100.0 * SUM(booking_flag) / COUNT(*), 2)        AS booking_conversion_pct,
    ROUND(AVG(ticket_price_cr), 2)                        AS avg_ticket_price_cr
FROM luxury_housing
WHERE is_price_outlier = 0
GROUP BY sales_channel, possession_status;


-- --------------------------------------------------------------------------
-- 6. Buyer Persona Building.
-- --------------------------------------------------------------------------
DROP VIEW IF EXISTS vw_buyer_persona;
CREATE VIEW vw_buyer_persona AS
SELECT
    buyer_type,
    nri_buyer,
    COUNT(*)                                              AS total_properties,
    ROUND(AVG(ticket_price_cr), 2)                        AS avg_ticket_price_cr,
    ROUND(AVG(unit_size_sqft), 0)                         AS avg_unit_size_sqft,
    ROUND(100.0 * SUM(booking_flag) / COUNT(*), 2)        AS booking_conversion_pct,
    SUM(CASE WHEN comment_sentiment = 'Positive' THEN 1 ELSE 0 END)  AS positive_comments,
    SUM(CASE WHEN comment_sentiment = 'Negative' THEN 1 ELSE 0 END)  AS negative_comments,
    ROUND(AVG(amenity_score), 2)                          AS avg_amenity_score
FROM luxury_housing
WHERE is_price_outlier = 0
GROUP BY buyer_type, nri_buyer;


-- --------------------------------------------------------------------------
-- 7. Amenity Score & Conversion.
-- --------------------------------------------------------------------------
DROP VIEW IF EXISTS vw_amenity_conversion;
CREATE VIEW vw_amenity_conversion AS
SELECT
    amenity_band,
    COUNT(*)                                              AS total_properties,
    ROUND(AVG(amenity_score), 2)                          AS avg_amenity_score,
    SUM(booking_flag)                                     AS total_bookings,
    ROUND(100.0 * SUM(booking_flag) / COUNT(*), 2)        AS booking_conversion_pct,
    ROUND(AVG(ticket_price_cr), 2)                        AS avg_ticket_price_cr,
    ROUND(AVG(price_per_sqft), 0)                         AS avg_price_per_sqft
FROM luxury_housing
WHERE is_price_outlier = 0
GROUP BY amenity_band;


-- --------------------------------------------------------------------------
-- 8. Buyer sentiment breakdown, used by the Power BI comment insight cards.
-- --------------------------------------------------------------------------
DROP VIEW IF EXISTS vw_sentiment_summary;
CREATE VIEW vw_sentiment_summary AS
SELECT
    comment_sentiment,
    buyer_comments,
    COUNT(*)                                              AS mention_count,
    ROUND(100.0 * SUM(booking_flag) / COUNT(*), 2)        AS booking_conversion_pct,
    ROUND(AVG(ticket_price_cr), 2)                        AS avg_ticket_price_cr,
    ROUND(AVG(amenity_score), 2)                          AS avg_amenity_score
FROM luxury_housing
WHERE is_price_outlier = 0
GROUP BY comment_sentiment, buyer_comments;


-- --------------------------------------------------------------------------
-- 8a. Visualization question 1 - quarterly bookings per micro-market.
--     Feeds the line chart: Quarter on X, booking count on Y, one line
--     per micro-market.
-- --------------------------------------------------------------------------
DROP VIEW IF EXISTS vw_market_quarterly_bookings;
CREATE VIEW vw_market_quarterly_bookings AS
SELECT
    micro_market,
    quarter_label,
    purchase_year,
    quarter_number,
    COUNT(*)                                              AS total_properties,
    SUM(booking_flag)                                     AS booking_count,
    ROUND(100.0 * SUM(booking_flag) / COUNT(*), 2)        AS booking_conversion_pct,
    ROUND(AVG(ticket_price_cr), 2)                        AS avg_ticket_price_cr
FROM luxury_housing
WHERE is_price_outlier = 0
GROUP BY micro_market, quarter_label, purchase_year, quarter_number;


-- --------------------------------------------------------------------------
-- 8b. Visualization question 7 - builder revenue by quarter.
--     Feeds the matrix: rows = builder, columns = quarter, values = revenue.
-- --------------------------------------------------------------------------
DROP VIEW IF EXISTS vw_builder_quarter_revenue;
CREATE VIEW vw_builder_quarter_revenue AS
SELECT
    developer_name                                        AS builder,
    quarter_label,
    COUNT(*)                                              AS total_properties,
    ROUND(SUM(ticket_price_cr), 2)                        AS total_revenue_cr,
    ROUND(AVG(ticket_price_cr), 2)                        AS avg_ticket_price_cr,
    SUM(booking_flag)                                     AS booking_count
FROM luxury_housing
WHERE is_price_outlier = 0
GROUP BY developer_name, quarter_label;


-- --------------------------------------------------------------------------
-- 8c. Visualization question 8 - possession status vs booking, by buyer type.
-- --------------------------------------------------------------------------
DROP VIEW IF EXISTS vw_possession_buyer_matrix;
CREATE VIEW vw_possession_buyer_matrix AS
SELECT
    possession_status,
    buyer_type,
    booking_status,
    COUNT(*)                                              AS total_properties,
    ROUND(AVG(ticket_price_cr), 2)                        AS avg_ticket_price_cr
FROM luxury_housing
WHERE is_price_outlier = 0
GROUP BY possession_status, buyer_type, booking_status;


-- --------------------------------------------------------------------------
-- 8d. Visualization question 10 - top builders by revenue and bookings.
--     Ordered by revenue; take the first five rows for the KPI cards.
-- --------------------------------------------------------------------------
DROP VIEW IF EXISTS vw_top_builders;
CREATE VIEW vw_top_builders AS
SELECT
    developer_name                                        AS builder,
    COUNT(*)                                              AS total_properties,
    ROUND(SUM(ticket_price_cr), 2)                        AS total_revenue_cr,
    ROUND(AVG(ticket_price_cr), 2)                        AS avg_ticket_price_cr,
    SUM(booking_flag)                                     AS booking_count,
    ROUND(100.0 * SUM(booking_flag) / COUNT(*), 2)        AS booking_conversion_pct,
    ROUND(AVG(price_per_sqft), 0)                         AS avg_price_per_sqft
FROM luxury_housing
WHERE is_price_outlier = 0
GROUP BY developer_name
ORDER BY total_revenue_cr DESC;


-- --------------------------------------------------------------------------
-- 9. Competitive Pricing - builder position inside each micro-market.
-- --------------------------------------------------------------------------
DROP VIEW IF EXISTS vw_competitive_pricing;
CREATE VIEW vw_competitive_pricing AS
SELECT
    m.micro_market,
    m.developer_name                                      AS builder,
    m.total_properties,
    m.avg_price_per_sqft,
    k.market_avg_price_per_sqft,
    ROUND(m.avg_price_per_sqft - k.market_avg_price_per_sqft, 0)              AS premium_vs_market,
    ROUND(100.0 * (m.avg_price_per_sqft - k.market_avg_price_per_sqft)
          / k.market_avg_price_per_sqft, 2)                                   AS premium_vs_market_pct,
    m.booking_conversion_pct
FROM (
    SELECT
        micro_market,
        developer_name,
        COUNT(*)                                       AS total_properties,
        ROUND(AVG(price_per_sqft), 0)                  AS avg_price_per_sqft,
        ROUND(100.0 * SUM(booking_flag) / COUNT(*), 2) AS booking_conversion_pct
    FROM luxury_housing
    WHERE is_price_outlier = 0
    GROUP BY micro_market, developer_name
) m
JOIN (
    SELECT
        micro_market,
        ROUND(AVG(price_per_sqft), 0)                  AS market_avg_price_per_sqft
    FROM luxury_housing
    WHERE is_price_outlier = 0
    GROUP BY micro_market
) k ON m.micro_market = k.micro_market;
