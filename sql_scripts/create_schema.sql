-- ==========================================================================
-- create_schema.sql
-- Luxury Housing Sales Analysis - Bengaluru
-- --------------------------------------------------------------------------
-- Warehouse table for the cleaned dataset produced by data_cleaning.py.
--
-- Written against the common subset of SQLite / PostgreSQL / MySQL so the same
-- file works on whichever backend config.DB_BACKEND points at.
--   * Identifiers are lower snake_case so PostgreSQL never needs quoting.
--   * SMALLINT stands in for BOOLEAN, which SQLite does not have.
--   * MySQL 8 does not accept IF NOT EXISTS on CREATE INDEX - drop the clause
--     from the index block if you target MySQL.
-- ==========================================================================

DROP TABLE IF EXISTS luxury_housing;

CREATE TABLE luxury_housing (
    -- Identity -------------------------------------------------------------
    property_id           VARCHAR(20)    NOT NULL,
    project_name          VARCHAR(100)   NOT NULL,
    developer_name        VARCHAR(100)   NOT NULL,   -- the brief calls this "Builder"
    micro_market          VARCHAR(100)   NOT NULL,

    -- Geography ------------------------------------------------------------
    -- Approximate locality centroids, so map visuals do not rely on geocoding.
    latitude              NUMERIC(9,6)   NOT NULL,
    longitude             NUMERIC(9,6)   NOT NULL,
    map_location          VARCHAR(160)   NOT NULL,   -- "<market>, Bengaluru, ..."

    -- Unit -----------------------------------------------------------------
    configuration         VARCHAR(10)    NOT NULL,   -- 3BHK / 4BHK / 5BHK+
    unit_size_sqft        NUMERIC(10,2)  NOT NULL,
    size_category         VARCHAR(30),

    -- Commercials ----------------------------------------------------------
    ticket_price_cr       NUMERIC(10,2)  NOT NULL,
    price_per_sqft        NUMERIC(12,2)  NOT NULL,
    price_segment         VARCHAR(30),
    is_price_outlier      SMALLINT       NOT NULL DEFAULT 0,

    -- Transaction ----------------------------------------------------------
    transaction_type      VARCHAR(20)    NOT NULL,   -- Primary / Secondary
    booking_flag          SMALLINT       NOT NULL DEFAULT 0,
    booking_status        VARCHAR(20)    NOT NULL,   -- Booked / Not Booked
    possession_status     VARCHAR(30)    NOT NULL,
    sales_channel         VARCHAR(30)    NOT NULL,

    -- Buyer ----------------------------------------------------------------
    buyer_type            VARCHAR(30)    NOT NULL,
    nri_buyer             VARCHAR(5)     NOT NULL,
    buyer_comments        VARCHAR(200),
    comment_sentiment     VARCHAR(20),

    -- Location quality -----------------------------------------------------
    amenity_score         NUMERIC(5,2),
    amenity_band          VARCHAR(10),
    connectivity_score    NUMERIC(5,2),
    locality_infra_score  NUMERIC(5,2),
    avg_traffic_time_min  INTEGER,

    -- Time -----------------------------------------------------------------
    purchase_date         DATE           NOT NULL,
    purchase_year         INTEGER        NOT NULL,
    quarter_number        INTEGER        NOT NULL,
    quarter_label         VARCHAR(10)    NOT NULL,   -- e.g. 2024-Q1
    fiscal_year           VARCHAR(12)    NOT NULL,   -- e.g. FY2023-24

    -- Cleaning audit flags -------------------------------------------------
    price_imputed         SMALLINT       NOT NULL DEFAULT 0,
    size_imputed          SMALLINT       NOT NULL DEFAULT 0,
    amenity_imputed       SMALLINT       NOT NULL DEFAULT 0,

    CONSTRAINT pk_luxury_housing PRIMARY KEY (property_id)
);

-- --------------------------------------------------------------------------
-- Indexes on every column the dashboard slices or groups by.
-- --------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_lh_developer     ON luxury_housing (developer_name);
CREATE INDEX IF NOT EXISTS idx_lh_market        ON luxury_housing (micro_market);
CREATE INDEX IF NOT EXISTS idx_lh_quarter       ON luxury_housing (quarter_label);
CREATE INDEX IF NOT EXISTS idx_lh_config        ON luxury_housing (configuration);
CREATE INDEX IF NOT EXISTS idx_lh_booking       ON luxury_housing (booking_flag);
CREATE INDEX IF NOT EXISTS idx_lh_possession    ON luxury_housing (possession_status);
CREATE INDEX IF NOT EXISTS idx_lh_channel       ON luxury_housing (sales_channel);
CREATE INDEX IF NOT EXISTS idx_lh_buyer_type    ON luxury_housing (buyer_type);
CREATE INDEX IF NOT EXISTS idx_lh_segment       ON luxury_housing (price_segment);
CREATE INDEX IF NOT EXISTS idx_lh_mkt_quarter   ON luxury_housing (micro_market, quarter_label);
