import pandas as pd
import yfinance as yf
import numpy as np
import pymysql
import os
import requests
from io import StringIO
from dotenv import load_dotenv
import concurrent.futures  # ⬅️ ADDED: Required for Parallel Processing Engine

# -------------------------------------------------------------------
# 1. Environment & Database Configuration
# -------------------------------------------------------------------
load_dotenv()
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

# -------------------------------------------------------------------
# 2. Dynamic Top 1000 Market-Cap Sourcing (S&P 500 + S&P 400)
# -------------------------------------------------------------------
def fetch_top_market_cap_tickers():
    """
    Scrapes both S&P 500 (Large-Cap) and S&P 400 (Mid-Cap) from Wikipedia.
    Combines them to cover the Top ~900-1000 equities in the US market.
    """
    print("🌐 [PIPELINE STEP 1] Scraping S&P 500 & S&P 400 lists from Wikipedia...")
    
    urls = [
        'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies',
        'https://en.wikipedia.org/wiki/List_of_S%26P_400_companies'
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }
    
    combined_tickers = []
    
    for url in urls:
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status() 
            
            html_data = StringIO(response.text)
            tables = pd.read_html(html_data)
            
            sp_df = tables[0]
            col_name = 'Symbol' if 'Symbol' in sp_df.columns else 'Ticker symbol'
            sp_df[col_name] = sp_df[col_name].astype(str).str.replace('.', '-', regex=False)
            
            combined_tickers.extend(sp_df[col_name].tolist())
            
        except Exception as e:
            print(f"⚠️ Warning scraping {url[:40]}: {str(e)[:100]}")
            
    unique_tickers = list(dict.fromkeys(combined_tickers))
    print(f"✅ Successfully extracted {len(unique_tickers)} Top Market-Cap equities.")
    
    return unique_tickers[:1000]

# -------------------------------------------------------------------
# 3. Parallel Data Fetching Worker Function
# -------------------------------------------------------------------
def fetch_single_ticker_data(ticker):
    """
    Worker function to fetch data for a single ticker.
    Designed to be executed concurrently in a thread pool.
    """
    try:
        info = yf.Ticker(ticker).info
        industry = info.get("industry")
        
        if not industry or industry == "Unknown":
            return None
            
        return {
            "Ticker": ticker,
            "Industry": industry,
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
    except Exception:
        return None

# -------------------------------------------------------------------
# 4. Main Execution Pipeline (With Asynchronous Engine)
# -------------------------------------------------------------------
def run_bulk_data_pipeline():
    target_tickers = fetch_top_market_cap_tickers()
    
    if not target_tickers:
        print("🚨 Pipeline aborted: Ticker list is empty.")
        return

    print(f"🚀 [PIPELINE STEP 2] Fetching financial data using PARALLEL ENGINE (Target: {len(target_tickers)} equities)...")
    
    raw_data = []
    
    # Set max threads to 20 to balance speed without triggering Yahoo's IP ban
    MAX_THREADS = 20 
    
    # Execute the worker function concurrently using ThreadPoolExecutor
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        future_to_ticker = {executor.submit(fetch_single_ticker_data, ticker): ticker for ticker in target_tickers}
        
        completed_count = 0
        for future in concurrent.futures.as_completed(future_to_ticker):
            completed_count += 1
            ticker = future_to_ticker[future]
            
            try:
                data = future.result()
                if data:
                    raw_data.append(data)
                
                # Print progress every 50 tickers to keep the terminal clean
                if completed_count % 50 == 0 or completed_count == len(target_tickers):
                    print(f"   ⚡ Processed {completed_count}/{len(target_tickers)} tickers...")
                    
            except Exception as e:
                print(f"   ⚠️ Exception generated for {ticker}: {e}")
    
    # ---------------------------------------------------------
    # 5. Statistical Aggregation & DB Upsert
    # ---------------------------------------------------------
    print("📊 [PIPELINE STEP 3] Grouping dynamically and calculating statistics...")
    df = pd.DataFrame(raw_data)
    
    if df.empty:
        print("🚨 Pipeline aborted: No data collected.")
        return
        
    numeric_cols = df.columns.drop(["Ticker", "Industry"])
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    
    grouped = df.groupby("Industry")
    
    connection = pymysql.connect(**db_config)
    total_industries_updated = 0
    
    try:
        with connection.cursor() as cursor:
            for industry_name, group_df in grouped:
                if len(group_df) < 2:
                    continue
                    
                mean_series = group_df.mean(numeric_only=True)
                std_series = group_df.std(numeric_only=True)
                
                for metric in numeric_cols:
                    mean_val = mean_series.get(metric)
                    std_val = std_series.get(metric)
                    
                    if pd.isna(mean_val):
                        continue
                        
                    std_val = 1.0 if (pd.isna(std_val) or std_val == 0) else std_val
                    
                    sql = """
                        INSERT INTO industry_benchmarks (industry_name, metric_name, mean_value, std_value)
                        VALUES (%s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            mean_value = VALUES(mean_value),
                            std_value = VALUES(std_value),
                            updated_at = CURRENT_TIMESTAMP;
                    """
                    cursor.execute(sql, (industry_name, metric, float(mean_val), float(std_val)))
                
                total_industries_updated += 1
                
        connection.commit()
        print(f"🏆 [BACKGROUND JOB] Complete! Updated {total_industries_updated} industries at lightning speed.")
        
    except Exception as e:
        print(f"❌ [BACKGROUND JOB] Critical Database Error: {e}")
    finally:
        connection.close()

if __name__ == "__main__":
    run_bulk_data_pipeline()