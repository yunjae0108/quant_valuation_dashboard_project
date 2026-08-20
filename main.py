import os
from fastapi import FastAPI, HTTPException
import yfinance as yf
import pymysql
from dotenv import load_dotenv
import requests

load_dotenv()
app = FastAPI()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# (Keep your other existing imports here...)

app = FastAPI(title="Quant Engine API")

# -------------------------------------------------------------------
# 🚨 SECURITY: CORS Middleware Configuration (Crucial for Next.js)
# -------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Explicitly authorize Next.js frontend
    allow_credentials=True,
    allow_methods=["*"],                      # Allow all HTTP methods (GET, POST, OPTIONS, etc.)
    allow_headers=["*"],                      # Allow all headers
)

# (Keep all your existing routes like @app.get("/manual-valuation/{ticker}") down here...)

db_config = {
    "host": os.getenv("DB_HOST"), "port": int(os.getenv("DB_PORT", 16078)),
    "user": os.getenv("DB_USER"), "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"), "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor, "ssl": {"ssl_mode": "REQUIRED"}
}

def get_benchmark_averages(industry: str):
    polarities = {
        "PE_Ratio": True, "Forward_PE": True, "PEG_Ratio": True, "PB_Ratio": True,
        "PS_Ratio": True, "EV_EBITDA": True, "EV_Sales": True,
        "Debt_to_Equity": True, "Payout_Ratio": True,
        "ROE": False, "ROA": False, "Gross_Margin": False, "Operating_Margin": False,
        "Net_Margin": False, "Current_Ratio": False, "Quick_Ratio": False, 
        "Dividend_Yield": False
    }

    # Initialize dictionary to hold both Industry and Market data
    benchmarks = {}
    for metric, is_lower_better in polarities.items():
        benchmarks[metric] = {
            "lower_is_better": is_lower_better, 
            "industry": {"mean": None, "std": None},
            "market": {"mean": None, "std": None}
        }

    connection = pymysql.connect(**db_config)
    try:
        with connection.cursor() as cursor:
            # Fetch BOTH Industry and Market context
            cursor.execute("""
                SELECT industry_name, metric_name, mean_value, std_value 
                FROM industry_benchmarks 
                WHERE industry_name IN (%s, 'Market')
            """, (industry,))
            
            for row in cursor.fetchall():
                m_name = row['metric_name']
                i_name = row['industry_name']
                
                if m_name in benchmarks:
                    context_key = "market" if i_name == 'Market' else "industry"
                    benchmarks[m_name][context_key] = {"mean": row['mean_value'], "std": row['std_value']}
    except Exception as e: print(e)
    finally: connection.close()
    return benchmarks

@app.get("/manual-valuation/{ticker}")
def get_manual_valuation(ticker: str):
    symbol = ticker.upper()
    try:
        info = yf.Ticker(symbol).info
        company_name = info.get("longName", info.get("shortName", symbol))
        price = info.get("currentPrice", info.get("regularMarketPrice", 0))
        industry = info.get("industry", "Unknown")
        
        metrics = {
            "PE_Ratio": info.get("trailingPE"), "Forward_PE": info.get("forwardPE"),
            "PEG_Ratio": info.get("pegRatio"), "PB_Ratio": info.get("priceToBook"),
            "PS_Ratio": info.get("priceToSalesTrailing12Months"), "EV_EBITDA": info.get("enterpriseToEbitda"),
            "EV_Sales": info.get("enterpriseToRevenue"), "ROE": info.get("returnOnEquity"),
            "ROA": info.get("returnOnAssets"), "Gross_Margin": info.get("grossMargins"),
            "Operating_Margin": info.get("operatingMargins"), "Net_Margin": info.get("profitMargins"),
            "Debt_to_Equity": info.get("debtToEquity"), "Current_Ratio": info.get("currentRatio"),
            "Quick_Ratio": info.get("quickRatio"), "Dividend_Yield": info.get("dividendYield"),
            "Payout_Ratio": info.get("payoutRatio")
        }
        return {
            "symbol": symbol, "company_name": company_name, "price": price, 
            "industry": industry, "metrics": metrics, "benchmarks": get_benchmark_averages(industry)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/industries")
def get_industries():
    connection = pymysql.connect(**db_config)
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT DISTINCT industry FROM company_rankings ORDER BY industry ASC")
            return {"industries": [r['industry'] for r in cursor.fetchall()]}
    finally: connection.close()

@app.get("/rankings")
def get_rankings(industry: str = "All Industries", context: str = "Industry"):
    # Determine which Z-Score column to sort by based on frontend toggle
    sort_col = "market_z_score" if context == "Market" or industry == "All Industries" else "industry_z_score"
    
    connection = pymysql.connect(**db_config)
    try:
        with connection.cursor() as cursor:
            if industry == "All Industries":
                cursor.execute(f"SELECT symbol, company_name, industry, {sort_col} as z_score FROM company_rankings ORDER BY {sort_col} DESC LIMIT 10")
                top_10 = cursor.fetchall()
                cursor.execute(f"SELECT symbol, company_name, industry, {sort_col} as z_score FROM company_rankings ORDER BY {sort_col} ASC LIMIT 10")
                bottom_10 = cursor.fetchall()
            else:
                cursor.execute(f"SELECT symbol, company_name, industry, {sort_col} as z_score FROM company_rankings WHERE industry=%s ORDER BY {sort_col} DESC LIMIT 10", (industry,))
                top_10 = cursor.fetchall()
                cursor.execute(f"SELECT symbol, company_name, industry, {sort_col} as z_score FROM company_rankings WHERE industry=%s ORDER BY {sort_col} ASC LIMIT 10", (industry,))
                bottom_10 = cursor.fetchall()
            return {"top_10": top_10, "bottom_10": bottom_10}
    finally: connection.close()
    
@app.get("/history/{ticker}")
def get_stock_history(ticker: str, period: str = "6M"):
    try:
        # Map frontend timeframe to yfinance period & interval
        period_map = {
            "1D": ("1d", "5m"),
            "1W": ("5d", "15m"),
            "1M": ("1mo", "1d"),
            "3M": ("3mo", "1d"),
            "6M": ("6mo", "1d"),
            "1Y": ("1y", "1d"),
            "5Y": ("5y", "1wk"),
            "ALL": ("max", "1mo")
        }
        yf_period, yf_interval = period_map.get(period.upper(), ("6mo", "1d"))
        
        stock = yf.Ticker(ticker)
        hist = stock.history(period=yf_period, interval=yf_interval)
        
        if hist.empty:
            return {"history": [], "error": "No data returned from Yahoo Finance."}
            
        history_data = []
        for date, row in hist.iterrows():
            # Correctly parse intraday vs daily timestamps
            if 'm' in yf_interval or 'h' in yf_interval:
                date_str = date.strftime('%Y-%m-%d %H:%M')
            else:
                date_str = date.strftime('%Y-%m-%d')
                
            history_data.append({
                "date": date_str,
                "price": round(float(row['Close']), 2)
            })
            
        return {"history": history_data}
    except Exception as e:
        return {"history": [], "error": str(e)}

@app.get("/tickers")
def get_tickers():
    """
    Provides the frontend with the universe of available tickers.
    Replace Method 1 with Method 2 if you want to pull directly from your Aiven SQL DB.
    """
    try:
        # ---------------------------------------------------------
        # METHOD 1: Fetching all active US companies (Easy & Robust)
        # ---------------------------------------------------------
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        res = requests.get("https://www.sec.gov/files/company_tickers.json", headers=headers)
        res.raise_for_status()
        data = res.json()
        
        formatted_tickers = [{"symbol": item["ticker"], "title": item["title"]} for item in data.values()]
        return {"tickers": formatted_tickers}

        # ---------------------------------------------------------
        # METHOD 2: Direct Aiven SQL Database Query (The 900 Universe)
        # (Uncomment and modify this block to use exact 900 companies)
        # ---------------------------------------------------------
        # db_cursor = your_db_connection.cursor()
        # db_cursor.execute("SELECT DISTINCT ticker, company_name FROM your_valuation_table")
        # db_results = db_cursor.fetchall()
        # 
        # my_900_tickers = [{"symbol": row[0], "title": row[1]} for row in db_results]
        # return {"tickers": my_900_tickers}

    except Exception as e:
        print(f"Backend Error Fetching Tickers: {e}")
        return {"tickers": [], "error": str(e)}