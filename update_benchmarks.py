import pandas as pd
import yfinance as yf
import numpy as np
import pymysql
import os
import requests
from io import StringIO
from dotenv import load_dotenv
import concurrent.futures

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

# Metric Polarity definition for Composite Z-Score calculation
POLARITIES = {
    "PE_Ratio": True, "Forward_PE": True, "PEG_Ratio": True, "PB_Ratio": True,
    "PS_Ratio": True, "EV_EBITDA": True, "EV_Sales": True,
    "Debt_to_Equity": True, "Payout_Ratio": True,
    "ROE": False, "ROA": False, "Gross_Margin": False, "Operating_Margin": False,
    "Net_Margin": False, "Current_Ratio": False, "Quick_Ratio": False,
    "Dividend_Yield": False
}

# -------------------------------------------------------------------
# 2. Dynamic Top 1000 Market-Cap Sourcing
# -------------------------------------------------------------------
def fetch_top_market_cap_tickers():
    print("🌐 [PIPELINE STEP 1] Scraping S&P 500 & S&P 400 lists from Wikipedia...")
    urls = [
        'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies',
        'https://en.wikipedia.org/wiki/List_of_S%26P_400_companies'
    ]
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/114.0.0.0 Safari/537.36"}
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
# 3. Parallel Data Fetching Worker Function (Includes Company Name)
# -------------------------------------------------------------------
def fetch_single_ticker_data(ticker):
    try:
        info = yf.Ticker(ticker).info
        industry = info.get("industry")
        if not industry or industry == "Unknown":
            return None
            
        company_name = info.get("longName", info.get("shortName", ticker))
            
        return {
            "Ticker": ticker,
            "CompanyName": company_name,
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
# 4. Main Execution Pipeline
# -------------------------------------------------------------------
def run_bulk_data_pipeline():
    target_tickers = fetch_top_market_cap_tickers()
    if not target_tickers:
        return

    print(f"🚀 [PIPELINE STEP 2] Fetching financial data using PARALLEL ENGINE (Target: {len(target_tickers)})...")
    raw_data = []
    MAX_THREADS = 20 
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        future_to_ticker = {executor.submit(fetch_single_ticker_data, ticker): ticker for ticker in target_tickers}
        completed_count = 0
        for future in concurrent.futures.as_completed(future_to_ticker):
            completed_count += 1
            try:
                data = future.result()
                if data:
                    raw_data.append(data)
                if completed_count % 50 == 0 or completed_count == len(target_tickers):
                    print(f"   ⚡ Processed {completed_count}/{len(target_tickers)} tickers...")
            except Exception:
                pass
    
    # ---------------------------------------------------------
    # 5. Statistical Aggregation, Winsorization & DB Upsert
    # ---------------------------------------------------------
    print("📊 [PIPELINE STEP 3] Applying 1% Winsorization and calculating robust statistics...")
    df = pd.DataFrame(raw_data)
    
    if df.empty:
        return
        
    numeric_cols = df.columns.drop(["Ticker", "CompanyName", "Industry"])
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    
    # 1% and 99% Winsorization
    for col in numeric_cols:
        lower_bound = df[col].quantile(0.01)
        upper_bound = df[col].quantile(0.99)
        df[col] = df[col].clip(lower=lower_bound, upper=upper_bound)
    
    grouped = df.groupby("Industry")
    
    industry_stats = {}
    for industry_name, group_df in grouped:
        if len(group_df) >= 2:
            industry_stats[industry_name] = {
                "mean": group_df.mean(numeric_only=True),
                "std": group_df.std(numeric_only=True)
            }
            
    connection = pymysql.connect(**db_config)
    total_industries_updated = 0
    total_ranked = 0
    
    try:
        with connection.cursor() as cursor:
            # Task A: Save Industry Benchmarks
            for industry_name, stats in industry_stats.items():
                for metric in numeric_cols:
                    mean_val = stats["mean"].get(metric)
                    std_val = stats["std"].get(metric)
                    if pd.isna(mean_val): continue
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
            
            # Task B: Calculate Individual Composite Z-Scores and Save Rankings with Company Name
            print("📊 [PIPELINE STEP 4] Calculating Composite Z-Scores for Rankings...")
            for index, row in df.iterrows():
                ind = row["Industry"]
                if ind not in industry_stats: continue
                
                total_z = 0.0
                valid_count = 0
                for metric, is_lower_better in POLARITIES.items():
                    val = row.get(metric)
                    if pd.notna(val):
                        mean_val = industry_stats[ind]["mean"].get(metric)
                        std_val = industry_stats[ind]["std"].get(metric)
                        if pd.notna(mean_val) and pd.notna(std_val):
                            std_val = 1.0 if std_val == 0 else std_val
                            raw_z = (val - mean_val) / std_val
                            adjusted_z = -raw_z if is_lower_better else raw_z
                            total_z += adjusted_z
                            valid_count += 1
                
                if valid_count > 0:
                    composite_z = float(total_z / valid_count)
                    sql_rank = """
                        INSERT INTO company_rankings (symbol, company_name, industry, composite_z_score)
                        VALUES (%s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            company_name = VALUES(company_name),
                            industry = VALUES(industry),
                            composite_z_score = VALUES(composite_z_score),
                            updated_at = CURRENT_TIMESTAMP;
                    """
                    cursor.execute(sql_rank, (row["Ticker"], row["CompanyName"], ind, composite_z))
                    total_ranked += 1
                    
        connection.commit()
        print(f"🏆 [BACKGROUND JOB] Complete! Updated {total_industries_updated} industries and ranked {total_ranked} companies.")
        
    except Exception as e:
        print(f"❌ [BACKGROUND JOB] Critical Database Error: {e}")
    finally:
        connection.close()

if __name__ == "__main__":
    run_bulk_data_pipeline()