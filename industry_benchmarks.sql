USE stock_evaluation_db;

CREATE TABLE IF NOT EXISTS industry_benchmarks (
    industry_name VARCHAR(100),
    metric_name VARCHAR(100),
    mean_value FLOAT,
    std_value FLOAT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (industry_name, metric_name)
);

SELECT * FROM industry_benchmarks