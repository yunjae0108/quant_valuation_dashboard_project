-- Select the database
USE stock_evaluation_db;

-- Add new columns for calculated valuation metrics
ALTER TABLE company_profiles
ADD COLUMN per DECIMAL(10, 2),
ADD COLUMN pb_ratio DECIMAL(10, 2),
ADD COLUMN enterprise_value BIGINT,
ADD COLUMN ev_ebitda DECIMAL(10, 2);