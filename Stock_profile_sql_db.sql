CREATE DATABASE IF NOT EXISTS stock_evaluation_db;
USE stock_evaluation_db;

CREATE TABLE IF NOT EXISTS company_profiles (
    symbol VARCHAR(10) PRIMARY KEY,
    company_name VARCHAR(255),
    price DECIMAL(15, 2),
    volume BIGINT,
    avg_volume BIGINT,
    market_cap BIGINT,
    industry VARCHAR(255),
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

SELECT *
FROM company_profiles;