import os
from fastapi import FastAPI, HTTPException, BackgroundTasks
import yfinance as yf
import pymysql
from dotenv import load_dotenv
import math
from update_benchmarks import run_bulk_data_pipeline

# 1. Load environment variables from the .env file
load_dotenv()

app = FastAPI()

# 2. Database configuration for Aiven Cloud MySQL
db_config = {
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT", 16078)),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
    "ssl": {"ssl_mode": "REQUIRED"},
    "connect_timeout": 30
}

# 3. Helper Function: Fetches real calculated statistics directly from MySQL database
def get_benchmark_averages(industry: str):
    benchmarks = {
        "Buffett_Indicator": {"market": {"mean": 1.85, "std": 0.2}},
        "Shiller_PE": {"market": {"mean": 34.0, "std": 5.0}},
        "Equity_Risk_Premium": {"market": {"mean": 0.045, "std": 0.01}},
        "Fed_Model_Ratio": {"market": {"mean": 1.2, "std": 0.3}},
    }
    
    polarities = {
        "PE_Ratio": True, "Forward_PE": True, "PEG_Ratio": True, "PB_Ratio": True,
        "PS_Ratio": True, "Price_to_FCF": True, "EV_EBITDA": True, "EV_Sales": True,
        "P_TBV": True, "Tobins_Q": True, "Debt_to_Equity": True, "Payout_Ratio": True,
        "ROE": False, "ROA": False, "Gross_Margin": False, "Operating_Margin": False,
        "Net_Margin": False, "Current_Ratio": False, "Quick_Ratio": False, 
        "Asset_Turnover": False, "Dividend_Yield": False
    }

    for metric, is_lower_better in polarities.items():
        benchmarks[metric] = {
            "lower_is_better": is_lower_better, 
            "industry": {"mean": None, "std": None}
        }

    connection = pymysql.connect(**db_config)
    try:
        with connection.cursor() as cursor:
            sql = """
                SELECT metric_name, mean_value, std_value 
                FROM industry_benchmarks 
                WHERE industry_name = %s
            """
            cursor.execute(sql, (industry,))
            results = cursor.fetchall()
            
            for row in results:
                metric_name = row['metric_name']
                if metric_name in benchmarks:
                    benchmarks[metric_name]["industry"] = {
                        "mean": row['mean_value'],
                        "std": row['std_value']
                    }
    except Exception as e:
        print(f"Error fetching benchmarks from DB: {e}")
    finally:
        connection.close()

    return benchmarks

# 4. Safe division utility to prevent division by zero or NoneType errors
def safe_div(num, den):
    if num is None or den is None or den == 0:
        return None
    return round(num / den, 4)

# 5. Manual Valuation Endpoint powered entirely by yfinance (No FMP paywall restrictions)
@app.get("/manual-valuation/{ticker}")
def get_manual_valuation(ticker: str):
    symbol = ticker.upper()
    
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        
        # Validate if ticker data exists
        if not info or ("currentPrice" not in info and "regularMarketPrice" not in info and "trailingPE" not in info):
            raise HTTPException(status_code=404, detail=f"Stock data for '{symbol}' not found via yfinance.")
            
        company_name = info.get("longName", info.get("shortName", symbol))
        price = info.get("currentPrice", info.get("regularMarketPrice", info.get("previousClose", 0)))
        industry = info.get("industry", "Unknown")
        
        # Extract valuation and financial metrics directly from yfinance info dictionary
        metrics = {
            "PE_Ratio": info.get("trailingPE"),
            "Forward_PE": info.get("forwardPE"),
            "PEG_Ratio": info.get("pegRatio"),
            "PB_Ratio": info.get("priceToBook"),
            "PS_Ratio": info.get("priceToSalesTrailing12Months"),
            "EV_EBITDA": info.get("enterpriseToEbitda"),
            "EV_Sales": info.get("enterpriseToRevenue"),
            "ROE": info.get("returnOnEquity"),
            "ROA": info.get("returnOnAssets"),
            "Gross_Margin": info.get("grossMargins"),
            "Operating_Margin": info.get("operatingMargins"),
            "Net_Margin": info.get("profitMargins"),
            "Debt_to_Equity": info.get("debtToEquity"),
            "Current_Ratio": info.get("currentRatio"),
            "Quick_Ratio": info.get("quickRatio"),
            "Dividend_Yield": info.get("dividendYield"),
            "Payout_Ratio": info.get("payoutRatio")
        }
        
        return {
            "symbol": symbol,
            "company_name": company_name,
            "price": price,
            "industry": industry,
            "metrics": metrics,
            "benchmarks": get_benchmark_averages(industry)
        }
        
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        import traceback
        print(f"🚨 ERROR in {symbol} processing:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal Processing Error: {str(e)}")

# 6. Home endpoint
@app.get("/")
def home():
    return {"message": "Welcome to the Stock Valuation API powered by yfinance."}

# 7. Background job trigger for bulk data pipeline
@app.post("/trigger-daily-update")
def trigger_daily_update(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_bulk_data_pipeline)
    return {"message": "Massive data pipeline triggered. Processing in background..."}