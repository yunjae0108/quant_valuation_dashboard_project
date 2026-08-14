import pymysql
import os
from dotenv import load_dotenv

# 1. Load Environment Variables
load_dotenv()

# 2. Updated Database configuration for Aiven Cloud MySQL
db_config = {
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT", 16078)),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
    "ssl": {"ssl_mode": "REQUIRED"}
}

def create_tables():
    print("🚀 Connecting to Aiven Cloud Database...")
    connection = pymysql.connect(**db_config)
    
    try:
        with connection.cursor() as cursor:
            # 3. Create the benchmark statistics table
            print("📦 Creating 'industry_benchmarks' table...")
            sql_benchmarks = """
            CREATE TABLE IF NOT EXISTS industry_benchmarks (
                id INT AUTO_INCREMENT PRIMARY KEY,
                industry_name VARCHAR(100) NOT NULL,
                metric_name VARCHAR(50) NOT NULL,
                mean_value FLOAT,
                std_value FLOAT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY idx_industry_metric (industry_name, metric_name)
            );
            """
            cursor.execute(sql_benchmarks)
            
            # 4. Create the company profiles table for dashboard caching
            print("📦 Creating 'company_profiles' table...")
            sql_profiles = """
            CREATE TABLE IF NOT EXISTS company_profiles (
                symbol VARCHAR(10) PRIMARY KEY,
                company_name VARCHAR(255),
                price FLOAT,
                volume BIGINT,
                avg_volume BIGINT,
                market_cap BIGINT,
                industry VARCHAR(100),
                description TEXT,
                per FLOAT,
                pb_ratio FLOAT,
                enterprise_value BIGINT,
                ev_ebitda FLOAT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            );
            """
            cursor.execute(sql_profiles)
            
        connection.commit()
        print("✅ All tables created successfully in the Cloud!")
        
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
    finally:
        connection.close()

# 5. Execute table creation directly from the terminal
if __name__ == "__main__":
    create_tables()