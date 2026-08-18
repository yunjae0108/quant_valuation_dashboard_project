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
    "ssl": {"ssl_mode": "REQUIRED"}
}

POLARITIES = {
    "PE_Ratio": True, "Forward_PE": True, "PEG_Ratio": True, "PB_Ratio": True,
    "PS_Ratio": True, "EV_EBITDA": True, "EV_Sales": True,
    "Debt_to_Equity": True, "Payout_Ratio": True,
    "ROE": False, "ROA": False, "Gross_Margin": False, "Operating_Margin": False,
    "Net_Margin": False, "Current_Ratio": False, "Quick_Ratio": False,
    "Dividend_Yield": False
}

def fetch_top_market_cap_tickers():
    print("🌐 [PIPELINE STEP 1] Scraping S&P 500 & S&P 400 lists from Wikipedia...")
    urls = [
        'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies',
        'https://en.wikipedia.org/wiki/List_of_S%26P_400_companies'
    ]
    headers = {"User-Agent": "Mozilla/5.0"}
    combined_tickers = []
    for url in urls:
        try:
            res = requests.get(url, headers=headers)
            res.raise_for_status() 
            tables = pd.read_html(StringIO(res.text))
            sp_df = tables[0]
            col_name = 'Symbol' if 'Symbol' in sp_df.columns else 'Ticker symbol'
            sp_df[col_name] = sp_df[col_name].astype(str).str.replace('.', '-', regex=False)
            combined_tickers.extend(sp_df[col_name].tolist())
        except:
            pass
    return list(dict.fromkeys(combined_tickers))[:1000]

def fetch_single_ticker_data(ticker):
    try:
        info = yf.Ticker(ticker).info
        if not info.get("industry") or info.get("industry") == "Unknown": return None
        return {
            "Ticker": ticker,
            "CompanyName": info.get("longName", info.get("shortName", ticker)),
            "Industry": info.get("industry"),
            "PE_Ratio": info.get("trailingPE"), "Forward_PE": info.get("forwardPE"),
            "PEG_Ratio": info.get("pegRatio"), "PB_Ratio": info.get("priceToBook"),
            "PS_Ratio": info.get("priceToSalesTrailing12Months"),
            "EV_EBITDA": info.get("enterpriseToEbitda"), "EV_Sales": info.get("enterpriseToRevenue"),
            "ROE": info.get("returnOnEquity"), "ROA": info.get("returnOnAssets"),
            "Gross_Margin": info.get("grossMargins"), "Operating_Margin": info.get("operatingMargins"),
            "Net_Margin": info.get("profitMargins"), "Debt_to_Equity": info.get("debtToEquity"),
            "Current_Ratio": info.get("currentRatio"), "Quick_Ratio": info.get("quickRatio"),
            "Dividend_Yield": info.get("dividendYield"), "Payout_Ratio": info.get("payoutRatio")
        }
    except: return None

def run_bulk_data_pipeline():
    target_tickers = fetch_top_market_cap_tickers()
    if not target_tickers: return

    print(f"🚀 [PIPELINE STEP 2] Fetching financial data (Target: {len(target_tickers)})...")
    raw_data = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        future_to_ticker = {executor.submit(fetch_single_ticker_data, t): t for t in target_tickers}
        for i, future in enumerate(concurrent.futures.as_completed(future_to_ticker), 1):
            data = future.result()
            if data: raw_data.append(data)
            if i % 50 == 0: print(f"   ⚡ Processed {i} tickers...")

    print("📊 [PIPELINE STEP 3] Applying 1% Winsorization and calculating robust statistics...")
    df = pd.DataFrame(raw_data)
    if df.empty: return
        
    numeric_cols = df.columns.drop(["Ticker", "CompanyName", "Industry"])
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    
    # 1% and 99% Winsorization
    for col in numeric_cols:
        lower, upper = df[col].quantile(0.01), df[col].quantile(0.99)
        df[col] = df[col].clip(lower=lower, upper=upper)
    
    # Pre-calculate Overall Market Stats
    market_stats = {"mean": df[numeric_cols].mean(numeric_only=True), "std": df[numeric_cols].std(numeric_only=True)}
    
    # Pre-calculate Industry Stats
    industry_stats = {}
    for ind, group in df.groupby("Industry"):
        if len(group) >= 2:
            industry_stats[ind] = {"mean": group.mean(numeric_only=True), "std": group.std(numeric_only=True)}
            
    connection = pymysql.connect(**db_config)
    try:
        with connection.cursor() as cursor:
            # Task A: Save Market Benchmarks
            for metric in numeric_cols:
                m_mean, m_std = market_stats["mean"].get(metric), market_stats["std"].get(metric)
                if pd.notna(m_mean):
                    m_std = 1.0 if pd.isna(m_std) or m_std == 0 else float(m_std)
                    cursor.execute("""
                        INSERT INTO industry_benchmarks (industry_name, metric_name, mean_value, std_value)
                        VALUES ('Market', %s, %s, %s) ON DUPLICATE KEY UPDATE mean_value=VALUES(mean_value), std_value=VALUES(std_value);
                    """, (metric, float(m_mean), m_std))

            # Task B: Save Industry Benchmarks
            for ind, stats in industry_stats.items():
                for metric in numeric_cols:
                    i_mean, i_std = stats["mean"].get(metric), stats["std"].get(metric)
                    if pd.notna(i_mean):
                        i_std = 1.0 if pd.isna(i_std) or i_std == 0 else float(i_std)
                        cursor.execute("""
                            INSERT INTO industry_benchmarks (industry_name, metric_name, mean_value, std_value)
                            VALUES (%s, %s, %s, %s) ON DUPLICATE KEY UPDATE mean_value=VALUES(mean_value), std_value=VALUES(std_value);
                        """, (ind, metric, float(i_mean), i_std))
            
            # Task C: Calculate Dual Z-Scores (Industry vs Market)
            print("📊 [PIPELINE STEP 4] Calculating Dual Composite Z-Scores...")
            for _, row in df.iterrows():
                ind = row["Industry"]
                if ind not in industry_stats: continue
                
                ind_z_total, mkt_z_total, ind_count, mkt_count = 0.0, 0.0, 0, 0
                
                for metric, is_lower_better in POLARITIES.items():
                    val = row.get(metric)
                    if pd.notna(val):
                        # Industry Z
                        i_mean, i_std = industry_stats[ind]["mean"].get(metric), industry_stats[ind]["std"].get(metric)
                        if pd.notna(i_mean) and pd.notna(i_std):
                            raw_ind_z = (val - i_mean) / (1.0 if i_std == 0 else i_std)
                            ind_z_total += -raw_ind_z if is_lower_better else raw_ind_z
                            ind_count += 1
                        
                        # Market Z
                        m_mean, m_std = market_stats["mean"].get(metric), market_stats["std"].get(metric)
                        if pd.notna(m_mean) and pd.notna(m_std):
                            raw_mkt_z = (val - m_mean) / (1.0 if m_std == 0 else m_std)
                            mkt_z_total += -raw_mkt_z if is_lower_better else raw_mkt_z
                            mkt_count += 1
                
                if ind_count > 0 and mkt_count > 0:
                    cursor.execute("""
                        INSERT INTO company_rankings (symbol, company_name, industry, industry_z_score, market_z_score)
                        VALUES (%s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE
                        company_name=VALUES(company_name), industry=VALUES(industry), 
                        industry_z_score=VALUES(industry_z_score), market_z_score=VALUES(market_z_score);
                    """, (row["Ticker"], row["CompanyName"], ind, float(ind_z_total/ind_count), float(mkt_z_total/mkt_count)))
                    
        connection.commit()
        print("🏆 [BACKGROUND JOB] Complete! Dual Z-Scores updated successfully.")
    except Exception as e:
        print(f"❌ [BACKGROUND JOB] Error: {e}")
    finally:
        connection.close()

if __name__ == "__main__":
    run_bulk_data_pipeline()