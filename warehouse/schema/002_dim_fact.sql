-- =============================================================================
-- 002_dim_fact.sql – Retail data-warehouse dimension and fact tables
-- Run after 001_init.sql.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- dim_date
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_date (
    date_key        INTEGER     PRIMARY KEY,   -- YYYYMMDD
    full_date       DATE        NOT NULL UNIQUE,
    day_of_week     SMALLINT    NOT NULL,      -- 0 = Sunday
    day_name        VARCHAR(10) NOT NULL,
    day_of_month    SMALLINT    NOT NULL,
    day_of_year     SMALLINT    NOT NULL,
    week_of_year    SMALLINT    NOT NULL,
    month_number    SMALLINT    NOT NULL,
    month_name      VARCHAR(10) NOT NULL,
    quarter         SMALLINT    NOT NULL,
    year            SMALLINT    NOT NULL,
    is_weekend      BOOLEAN     NOT NULL DEFAULT FALSE,
    is_holiday      BOOLEAN     NOT NULL DEFAULT FALSE
);

-- ---------------------------------------------------------------------------
-- dim_product
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_product (
    product_key     BIGSERIAL   PRIMARY KEY,
    product_id      VARCHAR(100) NOT NULL UNIQUE,
    product_name    VARCHAR(255),
    category        VARCHAR(100),
    sub_category    VARCHAR(100),
    brand           VARCHAR(100),
    unit_cost       NUMERIC(12, 4),
    unit_price      NUMERIC(12, 4),
    is_active       BOOLEAN     NOT NULL DEFAULT TRUE,
    valid_from      DATE        NOT NULL DEFAULT CURRENT_DATE,
    valid_to        DATE
);

CREATE INDEX IF NOT EXISTS idx_dim_product_product_id ON dim_product (product_id);

-- ---------------------------------------------------------------------------
-- dim_store
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS dim_store (
    store_key       BIGSERIAL   PRIMARY KEY,
    store_id        VARCHAR(100) NOT NULL UNIQUE,
    store_name      VARCHAR(255),
    region          VARCHAR(100),
    country         VARCHAR(100),
    city            VARCHAR(100),
    is_active       BOOLEAN     NOT NULL DEFAULT TRUE
);

-- ---------------------------------------------------------------------------
-- fact_sales
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS fact_sales (
    sale_key        BIGSERIAL   PRIMARY KEY,
    date_key        INTEGER     NOT NULL REFERENCES dim_date (date_key),
    product_key     BIGINT      NOT NULL REFERENCES dim_product (product_key),
    store_key       BIGINT      NOT NULL REFERENCES dim_store (store_key),
    job_id          UUID        NOT NULL REFERENCES etl_jobs (id),
    quantity        INTEGER     NOT NULL DEFAULT 0,
    unit_price      NUMERIC(12, 4),
    discount        NUMERIC(6, 4) DEFAULT 0,
    gross_sales     NUMERIC(14, 4),
    net_sales       NUMERIC(14, 4),
    cost_of_goods   NUMERIC(14, 4),
    gross_profit    NUMERIC(14, 4),
    loaded_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_fact_sales_date_key    ON fact_sales (date_key);
CREATE INDEX IF NOT EXISTS idx_fact_sales_product_key ON fact_sales (product_key);
CREATE INDEX IF NOT EXISTS idx_fact_sales_store_key   ON fact_sales (store_key);
CREATE INDEX IF NOT EXISTS idx_fact_sales_job_id      ON fact_sales (job_id);
