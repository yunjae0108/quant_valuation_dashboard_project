import streamlit as st
import requests
import numpy as np
import plotly.graph_objects as go
import yfinance as yf
from datetime import datetime, timedelta
import math # Used for precise Percentile (CDF) calculations

# -------------------------------------------------------------------
# 1. Page Configuration & Modern Dark Mode CSS Injection
# -------------------------------------------------------------------
st.set_page_config(page_title="Quant Valuation Dashboard", layout="wide", page_icon="⚡")

st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] {
        background-color: #0E1117;
        color: #FAFAFA;
    }
    [data-testid="stHeader"] {
        background-color: transparent;
    }
    div[data-testid="metric-container"] {
        background-color: #1A1C24;
        border: 1px solid #2D3139;
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.5);
    }
    [data-testid="stMetricLabel"] {
        color: #9CA3AF !important; 
        font-weight: 500;
    }
    [data-testid="stMetricValue"] {
        color: #FFFFFF !important; 
        font-weight: 700;
    }
    .custom-subheader {
        color: #FFFFFF;
        font-size: 1.25rem;
        font-weight: 600;
        margin-bottom: 1rem;
        border-bottom: 1px solid #2D3139;
        padding-bottom: 0.5rem;
    }
    /* Sleek Expander Styling */
    .streamlit-expanderHeader {
        color: #9CA3AF !important;
        font-size: 14px;
    }
    </style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------------
# 2. Comprehensive Metric Definitions & LaTeX Formulas
# -------------------------------------------------------------------
METRIC_INFO = {
    "PE_Ratio": {"desc": "Price-to-Earnings measures a company's current share price relative to its EPS. A primary metric for valuation.", "formula": r"\frac{\text{Market Price}}{\text{Earnings Per Share (EPS)}}"},
    "Forward_PE": {"desc": "Forward P/E uses forecasted earnings to evaluate future valuation rather than trailing historical data.", "formula": r"\frac{\text{Market Price}}{\text{Estimated Future EPS}}"},
    "PEG_Ratio": {"desc": "The P/E ratio divided by the EPS growth rate. Helps normalize valuation for high-growth companies.", "formula": r"\frac{\text{P/E Ratio}}{\text{Earnings Growth Rate}}"},
    "PB_Ratio": {"desc": "Price-to-Book compares a firm's market capitalization to its accounting book value.", "formula": r"\frac{\text{Market Price}}{\text{Book Value Per Share}}"},
    "PS_Ratio": {"desc": "Price-to-Sales compares a company's stock price to its total revenues.", "formula": r"\frac{\text{Market Capitalization}}{\text{Total Revenue}}"},
    "EV_EBITDA": {"desc": "Enterprise Value to EBITDA measures the total overall value of a company relative to its operational cash flow/profitability.", "formula": r"\frac{\text{Enterprise Value (EV)}}{\text{EBITDA}}"},
    "EV_Sales": {"desc": "Enterprise Value to Sales. Useful for valuing companies with negative earnings.", "formula": r"\frac{\text{Enterprise Value (EV)}}{\text{Total Revenue}}"},
    "ROE": {"desc": "Return on Equity measures financial performance calculated by dividing net income by shareholders' equity.", "formula": r"\frac{\text{Net Income}}{\text{Shareholders' Equity}}"},
    "ROA": {"desc": "Return on Assets shows how profitable a company is relative to its total overall assets.", "formula": r"\frac{\text{Net Income}}{\text{Total Assets}}"},
    "Gross_Margin": {"desc": "The percent of total sales revenue retained after incurring the direct costs associated with producing goods.", "formula": r"\frac{\text{Revenue} - \text{COGS}}{\text{Revenue}}"},
    "Operating_Margin": {"desc": "Measures how much profit a company makes on a dollar of sales after paying for variable costs of production.", "formula": r"\frac{\text{Operating Income}}{\text{Revenue}}"},
    "Net_Margin": {"desc": "Measures how much net income is generated as a percentage of total revenue.", "formula": r"\frac{\text{Net Income}}{\text{Revenue}}"},
    "Debt_to_Equity": {"desc": "Calculated by dividing a company's total liabilities by its shareholder equity. Highlights leverage risk.", "formula": r"\frac{\text{Total Liabilities}}{\text{Shareholders' Equity}}"},
    "Current_Ratio": {"desc": "Measures a company's ability to pay short-term obligations due within one year.", "formula": r"\frac{\text{Current Assets}}{\text{Current Liabilities}}"},
    "Quick_Ratio": {"desc": "Measures a company's capacity to pay its current liabilities without needing to sell its inventory.", "formula": r"\frac{\text{Current Assets} - \text{Inventory}}{\text{Current Liabilities}}"},
    "Dividend_Yield": {"desc": "Shows how much a company pays out in dividends each year relative to its stock price.", "formula": r"\frac{\text{Annual Dividends}}{\text{Market Price}}"},
    "Payout_Ratio": {"desc": "The proportion of earnings paid out as dividends to shareholders.", "formula": r"\frac{\text{Dividends Paid}}{\text{Net Income}}"}
}

# -------------------------------------------------------------------
# 3. Header & Unified Search Interface
# -------------------------------------------------------------------
st.title("⚡ Advanced Quant Terminal")

selected_ticker = st.text_input(
    "Search Ticker", 
    placeholder="Enter a US ticker (e.g., AAPL, QQQ, SPCX) and press Enter...",
    label_visibility="collapsed"
).upper().strip()

st.markdown("<br>", unsafe_allow_html=True)

# -------------------------------------------------------------------
# 4. Main Analysis & Layout Rendering
# -------------------------------------------------------------------
if selected_ticker:
    with st.spinner(f"Aggregating institutional data for {selected_ticker}..."):
        try:
            res = requests.get(f"http://localhost:8000/manual-valuation/{selected_ticker}")
            
            if res.status_code == 200:
                data = res.json()
                company_name = data.get("company_name", selected_ticker)
                current_price = data.get("price", 0)
                metrics = data.get("metrics", {})
                benchmarks = data.get("benchmarks", {})
                
                st.markdown(f"<div class='custom-subheader'>🏢 {company_name} ({selected_ticker}) Overview</div>", unsafe_allow_html=True)
                
                # --- Top Row: KPI Cards ---
                col1, col2, col3, col4, col5 = st.columns(5)
                
                col1.metric("Live Price", f"${current_price:,.2f}")
                col2.metric("P/E Ratio", f"{metrics.get('PE_Ratio', 0):.2f}" if metrics.get('PE_Ratio') else "N/A")
                col3.metric("P/B Ratio", f"{metrics.get('PB_Ratio', 0):.2f}" if metrics.get('PB_Ratio') else "N/A")
                col4.metric("EV / EBITDA", f"{metrics.get('EV_EBITDA', 0):.2f}" if metrics.get('EV_EBITDA') else "N/A")
                col5.metric("ROE", f"{metrics.get('ROE', 0) * 100:.2f}%" if metrics.get('ROE') else "N/A")
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                # --- Middle Row: Historical Chart & Valuation Gauge ---
                chart_col, gauge_col = st.columns([2, 1])
                
                with chart_col:
                    col_title, col_selector = st.columns([1, 2])
                    with col_title:
                        st.markdown("<div class='custom-subheader' style='border:none; margin:0; padding:0;'>📈 Price Action</div>", unsafe_allow_html=True)
                    
                    with col_selector:
                        period_mapping = {
                            "1D": ("1d", "5m"), "1W": ("5d", "15m"), "1M": ("1mo", "1d"),
                            "3M": ("3mo", "1d"), "6M": ("6mo", "1d"), "1Y": ("1y", "1d"),
                            "5Y": ("5y", "1wk"), "ALL": ("max", "1mo")
                        }
                        selected_period = st.radio("Timeframe", options=list(period_mapping.keys()), horizontal=True, label_visibility="collapsed", index=4)
                    
                    st.markdown("<div style='border-bottom: 1px solid #2D3139; margin-bottom: 1rem;'></div>", unsafe_allow_html=True)
                    
                    yf_period, yf_interval = period_mapping[selected_period]
                    hist_data = yf.download(selected_ticker, period=yf_period, interval=yf_interval, progress=False)
                    
                    if not hist_data.empty:
                        close_prices = hist_data['Close'].squeeze()
                        start_price = float(close_prices.iloc[0])
                        end_price = float(close_prices.iloc[-1])
                        
                        min_price = close_prices.min()
                        max_price = close_prices.max()
                        price_range = max_price - min_price
                        if price_range == 0: price_range = min_price * 0.01 
                        
                        y_min = min_price - (price_range * 0.05)
                        y_max = max_price + (price_range * 0.05)
                        
                        pct_change = (((close_prices - start_price) / start_price) * 100).round(2)
                        trend_color = '#00C805' if end_price >= start_price else '#FF5000'
                        
                        fig_hist = go.Figure()
                        fig_hist.add_trace(go.Scatter(
                            x=hist_data.index, y=close_prices, customdata=pct_change,
                            mode='lines', line=dict(color=trend_color, width=2.5),
                            fill='tozeroy', fillcolor=f"rgba({ '0, 200, 5' if trend_color == '#00C805' else '255, 80, 0' }, 0.1)",
                            hovertemplate='%{x}<br><b>$%{y:.2f}</b> (%{customdata:+.2f}%)<extra></extra>'
                        ))
                        
                        fig_hist.update_layout(
                            hovermode='x unified', height=350, margin=dict(l=40, r=20, t=10, b=30), 
                            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                            xaxis=dict(showgrid=False, showticklabels=True, zeroline=False, showspikes=True, spikemode='across', spikesnap='cursor', showline=True, linecolor='#4B5563', spikedash='solid', spikethickness=1, spikecolor='gray'),
                            yaxis=dict(showgrid=True, gridcolor='rgba(128,128,128,0.2)', showticklabels=True, zeroline=False, tickprefix="$", range=[y_min, y_max])
                        )
                        st.plotly_chart(fig_hist, use_container_width=True, config={'displayModeBar': False})
                    else:
                        st.info(f"Price data unavailable for {selected_period}.")
                
                with gauge_col:
                    st.markdown("<div class='custom-subheader'>🧭 Valuation Verdict</div>", unsafe_allow_html=True)
                    
                    total_z = 0.0
                    valid_count = 0
                    for m_name, b_data in benchmarks.items():
                        if "industry" in b_data and b_data["industry"].get("mean") and metrics.get(m_name):
                            z = (metrics[m_name] - b_data["industry"]["mean"]) / (b_data["industry"]["std"] or 1)
                            total_z += -z if b_data.get("lower_is_better") else z
                            valid_count += 1
                            
                    avg_z = total_z / valid_count if valid_count > 0 else 0
                    
                    fig_gauge = go.Figure(go.Indicator(
                        mode="gauge+number",
                        value=avg_z,
                        domain={'x': [0, 1], 'y': [0, 1]},
                        number={'font': {'color': '#FFFFFF'}},
                        title={'text': "Composite Z-Score", 'font': {'size': 14, 'color': '#9CA3AF'}},
                        gauge={
                            'axis': {'range': [-3, 3], 'tickwidth': 1, 'tickcolor': "#4B5563"},
                            'bar': {'color': "#FFFFFF", 'thickness': 0.15},
                            'bgcolor': "#1A1C24",
                            'borderwidth': 0,
                            'steps': [
                                {'range': [-3, -0.5], 'color': "#FF5000"},
                                {'range': [-0.5, 0.5], 'color': "#FDBA74"},
                                {'range': [0.5, 3], 'color': "#00C805"}
                            ],
                        }
                    ))
                    fig_gauge.update_layout(height=250, margin=dict(l=20, r=20, t=30, b=0), paper_bgcolor='rgba(0,0,0,0)')
                    st.plotly_chart(fig_gauge, use_container_width=True, config={'displayModeBar': False})
                    
                    # ---------------------------------------------------------
                    # NEW: Expandable Analytics for the Composite Score
                    # ---------------------------------------------------------
                    with st.expander("ℹ️ How is this calculated?"):
                        st.markdown("**1. Calculation Methodology:**")
                        st.write("The Composite Z-Score is the arithmetic average of all individual metric Z-scores, mathematically adjusted for target polarity. It represents the aggregated standard deviation from the industry mean.")
                        
                        st.markdown("**2. Target Polarity:**")
                        st.write("📈 **Higher Score is Better.** A positive composite score indicates that the stock is fundamentally more attractive (undervalued or financially healthier) than its industry peers.")
                        
                        st.markdown("**3. Industry Percentile Ranking:**")
                        # CDF calculation using math.erf for standard normal distribution
                        cdf = (1.0 + math.erf(avg_z / math.sqrt(2.0))) / 2.0
                        percentile = cdf * 100
                        top_percent = 100 - percentile
                        
                        if top_percent < 50:
                            st.write(f"With a Z-Score of {avg_z:.2f}, this company ranks in the **Top {top_percent:.1f}%** of its industry basket in terms of overall fundamental attractiveness.")
                        else:
                            st.write(f"With a Z-Score of {avg_z:.2f}, this company ranks in the **Bottom {percentile:.1f}%** of its industry basket, indicating it may be overvalued or underperforming.")

                st.markdown("<br>", unsafe_allow_html=True)
                
                # --- Bottom Row: Z-Score Distribution Grids ---
                st.markdown("<div class='custom-subheader'>🔬 Fundamental Distribution Analysis</div>", unsafe_allow_html=True)
                
                grid_cols = st.columns(3)
                col_idx = 0
                
                for metric_name, benchmark_data in benchmarks.items():
                    if "industry" not in benchmark_data:
                        continue
                        
                    mean = benchmark_data["industry"].get("mean")
                    std = benchmark_data["industry"].get("std")
                    comp_val = metrics.get(metric_name)
                    
                    if comp_val is not None and mean is not None and std is not None and std > 0:
                        with grid_cols[col_idx % 3]:
                            with st.container(border=True):
                                st.markdown(f"<span style='color: #FFFFFF; font-weight: bold;'>{metric_name.replace('_', ' ')}</span>", unsafe_allow_html=True)
                                
                                fig_dist = go.Figure()
                                x_axis = np.linspace(mean - 4 * std, mean + 4 * std, 500)
                                y_axis = (1 / (std * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((x_axis - mean) / std) ** 2)
                                
                                fig_dist.add_trace(go.Scatter(
                                    x=x_axis, y=y_axis, mode='lines', 
                                    line=dict(color='#4A90E2', width=1.5),
                                    fill='tozeroy', fillcolor='rgba(74, 144, 226, 0.1)', hoverinfo='skip'
                                ))
                                
                                raw_z = (comp_val - mean) / std
                                is_lower_better = benchmark_data.get("lower_is_better")
                                is_good = (-raw_z if is_lower_better else raw_z) > 0
                                marker_color = '#00C805' if is_good else '#FF5000'
                                
                                fig_dist.add_vline(x=comp_val, line_width=2, line_color=marker_color)
                                fig_dist.add_vline(x=mean, line_dash="dot", line_width=1, line_color="gray")
                                
                                fig_dist.update_layout(
                                    height=130, margin=dict(l=0, r=0, t=5, b=0),
                                    plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                                    xaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
                                    yaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
                                    showlegend=False
                                )
                                # ---------------------------------------------------------
                                # FIX: staticPlot=True completely disables hover & interactivity
                                # ---------------------------------------------------------
                                st.plotly_chart(fig_dist, use_container_width=True, config={'staticPlot': True, 'displayModeBar': False})
                                st.caption(f"Val: {comp_val:.2f} | Ind. Mean: {mean:.2f}")
                                
                                # ---------------------------------------------------------
                                # NEW: Expandable Metric Deep Dive with Math & Percentiles
                                # ---------------------------------------------------------
                                with st.expander("📊 Metric Details & Rank"):
                                    info = METRIC_INFO.get(metric_name, {"desc": "Detailed description currently unavailable.", "formula": "N/A"})
                                    
                                    st.markdown("**1. Calculation Formula:**")
                                    if info["formula"] != "N/A":
                                        st.latex(info["formula"])
                                    
                                    st.markdown("**2. Financial Meaning:**")
                                    st.write(info["desc"])
                                    
                                    st.markdown("**3. Target Polarity:**")
                                    if is_lower_better:
                                        st.write("📉 **Lower is Better:** A smaller value relative to peers implies fundamental undervaluation or lower financial risk.")
                                    else:
                                        st.write("📈 **Higher is Better:** A larger value relative to peers implies greater operational profitability or efficiency.")
                                        
                                    st.markdown("**4. Industry Percentile Ranking:**")
                                    cdf_val = (1.0 + math.erf(raw_z / math.sqrt(2.0))) / 2.0
                                    raw_percentile = cdf_val * 100
                                    
                                    if is_lower_better:
                                        # For lower is better, being on the extreme left (low percentile) is attractive
                                        st.write(f"This company's raw value sits at the **{raw_percentile:.1f}th percentile** of the industry distribution. Because lower is better for this metric, this places the company in the **Top {raw_percentile:.1f}%** most attractive peers.")
                                    else:
                                        # For higher is better, being on the extreme right (high percentile) is attractive
                                        attractive_percent = 100 - raw_percentile
                                        st.write(f"This company's raw value sits at the **{raw_percentile:.1f}th percentile** of the industry distribution. Because higher is better for this metric, this places the company in the **Top {attractive_percent:.1f}%** most attractive peers.")

                        col_idx += 1

            else:
                try:
                    err_msg = res.json().get("detail", "Unknown backend error.")
                except:
                    err_msg = res.text
                st.error(f"⚠️ API Error [{res.status_code}]: {err_msg}")
                
        except requests.exceptions.ConnectionError:
            st.error("🚨 Connection Error: Unable to reach the FastAPI backend. Ensure it is running on port 8000.")