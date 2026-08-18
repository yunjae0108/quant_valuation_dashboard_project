import pymysql
import os
from dotenv import load_dotenv

# 1. Load Environment Variables
load_dotenv()

# 2. Database configuration for Aiven Cloud MySQL
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
            
            # Drop old table to cleanly apply the dual z-score schema update
            print("📦 Recreating 'company_rankings' table with Dual Context Z-Scores...")
            cursor.execute("DROP TABLE IF EXISTS company_rankings;")
            
            sql_rankings = """
            CREATE TABLE company_rankings (
                symbol VARCHAR(10) PRIMARY KEY,
                company_name VARCHAR(255),
                industry VARCHAR(100) NOT NULL,
                industry_z_score FLOAT,
                market_z_score FLOAT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            );
            """
            cursor.execute(sql_rankings)
            
        connection.commit()
        print("✅ All tables created successfully in the Cloud!")
        
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
    finally:
        connection.close()

if __name__ == "__main__":
    create_tables()