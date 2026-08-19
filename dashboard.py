import streamlit as st
import pandas as pd
import requests
import numpy as np
import plotly.graph_objects as go
import yfinance as yf
import math

# -------------------------------------------------------------------
# 1. Page Configuration & Material Design 3 CSS Injection
# -------------------------------------------------------------------
st.set_page_config(page_title="Quant Valuation Dashboard", layout="wide", page_icon="⚡", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif !important;
    }

    /* M3 Dark Theme Surface Colors */
    [data-testid="stAppViewContainer"] { background-color: #0B0E14; color: #E2E2E2; }
    [data-testid="stHeader"] { background-color: transparent; }
    
    /* Sidebar Styling */
    [data-testid="stSidebar"] { background-color: #161A23 !important; border-right: 1px solid rgba(255, 255, 255, 0.05); }
    [data-testid="stSidebarNav"] { padding-top: 2rem; }
    
    /* =====================================================================
       🚨 ULTIMATE FIX: NUKE THE RADIO CIRCLES COMPLETELY
       ===================================================================== */
    [data-testid="stSidebar"] div[role="radiogroup"] { gap: 4px; }
    
    /* 1. Target and destroy the specific SVG circles Streamlit generates */
    [data-testid="stSidebar"] div[role="radiogroup"] label svg {
        display: none !important;
    }
    
    /* 2. Target and destroy the underlying HTML input element */
    [data-testid="stSidebar"] div[role="radiogroup"] label input {
        display: none !important;
    }
    
    /* 3. Target and destroy the wrapper div containing the circle */
    [data-testid="stSidebar"] div[role="radiogroup"] label > div:first-child {
        display: none !important;
        width: 0px !important;
        height: 0px !important;
        margin: 0px !important;
        padding: 0px !important;
        position: absolute !important;
    }
    
    /* 4. Base styling for all sidebar tabs - ensuring perfect alignment */
    [data-testid="stSidebar"] div[role="radiogroup"] label {
        padding: 12px 16px !important;
        border-radius: 12px !important;
        transition: all 0.2s ease-in-out !important;
        cursor: pointer !important;
        border-left: 4px solid transparent !important;
        margin-bottom: 6px !important;
        display: flex !important;
        align-items: center !important;
    }
    
    /* 5. Force text to take full width and align properly */
    [data-testid="stSidebar"] div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] {
        width: 100% !important;
        margin-left: 0 !important;
        padding-left: 0 !important;
    }
    
    /* 6. Typography for all tabs */
    [data-testid="stSidebar"] div[role="radiogroup"] label p {
        font-size: 1.05rem !important; 
        font-weight: 500 !important;
        color: #9CA3AF !important;
        margin: 0 !important;
    }
    
    /* Hover effect for unselected tabs */
    [data-testid="stSidebar"] div[role="radiogroup"] label:hover {
        background-color: rgba(255, 255, 255, 0.03) !important;
    }
    
    /* Distinct highlight for the SELECTED tab */
    [data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
        background-color: rgba(168, 199, 250, 0.1) !important;
        border-left: 4px solid #A8C7FA !important;
    }
    [data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) p {
        color: #FFFFFF !important;
        font-weight: 800 !important;
    }
    /* ===================================================================== */
    
    /* M3 Elevated Interactive Cards */
    div[data-testid="metric-container"] {
        background-color: #161A23; border: 1px solid rgba(255, 255, 255, 0.03); padding: 20px; 
        border-radius: 20px; transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1); box-shadow: 0 4px 6px rgba(0,0,0,0.2);
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-5px); background-color: #1D222E; box-shadow: 0 12px 20px rgba(0,0,0,0.4);
        border-color: rgba(168, 199, 250, 0.2);
    }
    
    /* Top Metrics Typography */
    [data-testid="stMetricValue"] { color: #FFFFFF !important; font-weight: 800 !important; font-size: 2.2rem !important; letter-spacing: -1px; }
    [data-testid="stMetricLabel"] { color: #A8C7FA !important; font-weight: 600 !important; font-size: 0.95rem !important; text-transform: uppercase; letter-spacing: 1px; }
    
    /* Custom Sleek Subheaders */
    .custom-subheader {
        color: #FFFFFF; font-size: 1.35rem; font-weight: 600; margin-bottom: 1.2rem; 
        border-bottom: 2px solid #1D222E; padding-bottom: 0.6rem; letter-spacing: -0.5px;
    }
    
    /* M3 Pill-shaped Context Toggle Container */
    .context-toggle { 
        background-color: #161A23; padding: 6px 20px; border-radius: 100px; margin-bottom: 20px; 
        display: inline-block; border: 1px solid rgba(255,255,255,0.05); box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    }
    
    /* Main Title Gradient */
    .main-title {
        font-size: 3rem; font-weight: 800; letter-spacing: -1.5px; margin-bottom: 1rem;
        background: linear-gradient(90deg, #FFFFFF 0%, #A8C7FA 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }
    
    /* Expander UI Upgrade */
    .streamlit-expanderHeader {
        background-color: #161A23 !important; border-radius: 12px !important; font-weight: 600 !important; 
        color: #A8C7FA !important; border: 1px solid rgba(255,255,255,0.03);
    }
    </style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------------
# 2. Comprehensive Metric Definitions
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
# 3. SEC Ticker Caching
# -------------------------------------------------------------------
@st.cache_data(ttl=86400)
def load_ticker_mapping():
    try:
        headers = {"User-Agent": "QuantDashboard/2.0 (Contact: admin@quantdashboard.com)"}
        res = requests.get("https://www.sec.gov/files/company_tickers.json", headers=headers)
        res.raise_for_status()
        df = pd.DataFrame.from_dict(res.json(), orient='index')
        return df
    except Exception as e:
        print(f"Error fetching SEC tickers: {e}")
        return pd.DataFrame()

# -------------------------------------------------------------------
# 4. Sidebar Navigation Module
# -------------------------------------------------------------------
st.sidebar.markdown("<div class='custom-subheader' style='border:none; font-size:1.8rem; color:#A8C7FA;'>Quant Engine</div>", unsafe_allow_html=True)
st.sidebar.markdown("<br>", unsafe_allow_html=True)

menu_selection = st.sidebar.radio(
    "Navigation Menu",
    [
        "🔍 Valuation Terminal", 
        "🏆 Market Rankings", 
        "📉 Options & Volatility", 
        "🤖 AI Predictive Modeling"
    ],
    label_visibility="collapsed"
)

# -------------------------------------------------------------------
# 5. Main Dashboard Rendering Logic
# -------------------------------------------------------------------
st.markdown("<div class='main-title'>⚡ Advanced Quant Terminal</div>", unsafe_allow_html=True)

if menu_selection == "🔍 Valuation Terminal":
    ticker_df = load_ticker_mapping()

    if 'search_name' not in st.session_state: st.session_state.search_name = None
    if 'search_ticker' not in st.session_state: st.session_state.search_ticker = None

    def clear_ticker(): st.session_state.search_ticker = None
    def clear_name(): st.session_state.search_name = None

    search_col1, search_col2 = st.columns(2)
    
    with search_col1:
        st.selectbox(
            "🔍 Search by Company Name", 
            options=ticker_df['title'].tolist() if not ticker_df.empty else [], 
            index=None, placeholder="Click and type Company Name (e.g., Amazon.com Inc.)",
            key="search_name", on_change=clear_ticker
        )
    with search_col2:
        st.selectbox(
            "🏷️ Search by Ticker", 
            options=ticker_df['ticker'].tolist() if not ticker_df.empty else [], 
            index=None, placeholder="Click and type Ticker (e.g., AMZN)",
            key="search_ticker", on_change=clear_name
        )

    st.markdown("<hr style='border: 1px solid rgba(255,255,255,0.05); margin: 2rem 0;'>", unsafe_allow_html=True)

    selected_ticker = None
    if st.session_state.search_name:
        selected_ticker = ticker_df[ticker_df['title'] == st.session_state.search_name]['ticker'].values[0]
    elif st.session_state.search_ticker:
        selected_ticker = st.session_state.search_ticker

    if selected_ticker:
        with st.spinner(f"Aggregating quantitative data for {selected_ticker}..."):
            try:
                res = requests.get(f"http://localhost:8000/manual-valuation/{selected_ticker}")
                if res.status_code == 200:
                    data = res.json()
                    metrics = data.get("metrics", {})
                    benchmarks = data.get("benchmarks", {})
                    
                    st.markdown(f"<div class='custom-subheader'>🏢 {data.get('company_name')} ({selected_ticker})</div>", unsafe_allow_html=True)
                    
                    st.markdown("<div class='context-toggle'>", unsafe_allow_html=True)
                    val_context = st.radio("Benchmark Context", ["Industry Context (Peers)", "Market Context (All Stocks)"], horizontal=True, label_visibility="collapsed")
                    st.markdown("</div>", unsafe_allow_html=True)
                    
                    b_key = "industry" if "Industry" in val_context else "market"
                    context_label = data.get("industry") if "Industry" in val_context else "Total Market"
                    
                    cols = st.columns(5)
                    cols[0].metric("Live Price", f"${data.get('price'):,.2f}")
                    cols[1].metric("P/E", f"{metrics.get('PE_Ratio', 0):.2f}" if metrics.get('PE_Ratio') else "N/A")
                    cols[2].metric("P/B", f"{metrics.get('PB_Ratio', 0):.2f}" if metrics.get('PB_Ratio') else "N/A")
                    cols[3].metric("EV/EBITDA", f"{metrics.get('EV_EBITDA', 0):.2f}" if metrics.get('EV_EBITDA') else "N/A")
                    cols[4].metric("ROE", f"{metrics.get('ROE', 0)*100:.2f}%" if metrics.get('ROE') else "N/A")
                    
                    chart_col, gauge_col = st.columns([2, 1])
                    
                    with chart_col:
                        col_title, col_selector = st.columns([1, 2])
                        with col_title:
                            st.markdown("<div class='custom-subheader' style='border:none; margin:0; padding:0;'>📈 Price Action</div>", unsafe_allow_html=True)
                        with col_selector:
                            period_mapping = {"1D": ("1d", "5m"), "1W": ("5d", "15m"), "1M": ("1mo", "1d"), "3M": ("3mo", "1d"), "6M": ("6mo", "1d"), "1Y": ("1y", "1d"), "5Y": ("5y", "1wk"), "ALL": ("max", "1mo")}
                            selected_period = st.radio("Timeframe", options=list(period_mapping.keys()), horizontal=True, label_visibility="collapsed", index=4)
                        
                        st.markdown("<div style='border-bottom: 1px solid #1D222E; margin-bottom: 1rem;'></div>", unsafe_allow_html=True)
                        
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
                            
                            abs_change = end_price - start_price
                            pct_change = (abs_change / start_price) * 100
                            trend_color = '#00C805' if abs_change >= 0 else '#FF5000'
                            sign = "+" if abs_change >= 0 else ""
                            
                            st.markdown(f"""
                                <div style='margin-bottom: 15px;'>
                                    <h1 style='color:#FFFFFF; font-size:2.8rem; font-weight:800; margin:0; padding:0; letter-spacing:-1px;'>${end_price:,.2f}</h1>
                                    <h3 style='color:{trend_color}; font-size:1.2rem; font-weight:600; margin:0; padding:0;'>{sign}${abs(abs_change):,.2f} ({sign}{pct_change:.2f}%)</h3>
                                </div>
                            """, unsafe_allow_html=True)
                            
                            fig_hist = go.Figure(go.Scatter(
                                x=hist_data.index, y=close_prices, mode='lines', line=dict(color=trend_color, width=2.5),
                                fill='tozeroy', fillcolor=f"rgba({ '0, 200, 5' if trend_color == '#00C805' else '255, 80, 0' }, 0.1)",
                                hovertemplate='%{x}<br><b>$%{y:.2f}</b><extra></extra>'
                            ))
                            fig_hist.update_layout(
                                hovermode='x unified', height=300, margin=dict(l=40, r=20, t=10, b=30), 
                                plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                                xaxis=dict(showgrid=False, showticklabels=True, zeroline=False, showspikes=True, spikemode='across', spikesnap='cursor', showline=True, linecolor='#333B4D', spikedash='solid', spikethickness=1, spikecolor='gray'),
                                yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', showticklabels=True, zeroline=False, tickprefix="$", range=[y_min, y_max])
                            )
                            st.plotly_chart(fig_hist, use_container_width=True, config={'displayModeBar': False})
                        else: st.info(f"Price data unavailable for {selected_period}.")
                            
                    with gauge_col:
                        st.markdown(f"<div class='custom-subheader'>🧭 Verdict vs {context_label}</div>", unsafe_allow_html=True)
                        total_z, valid_count = 0.0, 0
                        for m_name, b_data in benchmarks.items():
                            if b_key in b_data and b_data[b_key].get("mean") and metrics.get(m_name):
                                z = (metrics[m_name] - b_data[b_key]["mean"]) / (b_data[b_key]["std"] or 1)
                                total_z += -z if b_data.get("lower_is_better") else z
                                valid_count += 1
                        
                        avg_z = total_z / valid_count if valid_count > 0 else 0
                        z_font_color = "#A7F3D0" if avg_z >= 0 else "#FECDD3"
                        display_z = max(min(avg_z, 2.0), -2.0)
                        
                        fig_g = go.Figure(go.Indicator(
                            mode="gauge+number", value=avg_z, 
                            title={'text': f"Z-Score ({b_key.title()})", 'font': {'color': '#A8C7FA'}},
                            number={'font': {'color': z_font_color, 'weight': 'bold'}},
                            gauge={
                                'axis': {'range': [-2, 2], 'tickwidth': 1, 'tickcolor': "#333B4D"},
                                'bar': {'color': "rgba(0,0,0,0)", 'thickness': 0},
                                'threshold': {'line': {'color': "#FFFFFF", 'width': 4}, 'thickness': 0.75, 'value': display_z},
                                'steps': [{'range': [-2, -0.5], 'color': "#FF5000"}, {'range': [-0.5, 0.5], 'color': "#FDBA74"}, {'range': [0.5, 2], 'color': "#00C805"}]
                            }
                        ))
                        fig_g.update_layout(height=250, margin=dict(l=20,r=20,t=30,b=0), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font=dict(family='Outfit', color="white"))
                        st.plotly_chart(fig_g, use_container_width=True, config={'displayModeBar': False})
                    
                    st.markdown(f"<div class='custom-subheader'>🔬 Distribution vs {context_label}</div>", unsafe_allow_html=True)
                    grid = st.columns(3)
                    idx = 0
                    for m_name, b_data in benchmarks.items():
                        if b_key not in b_data: continue
                        mean, std, val = b_data[b_key].get("mean"), b_data[b_key].get("std"), metrics.get(m_name)
                        if val is not None and mean is not None and std is not None and std > 0:
                            with grid[idx % 3]:
                                st.markdown("<div data-testid='metric-container'>", unsafe_allow_html=True)
                                st.markdown(f"**{m_name.replace('_', ' ')}**")
                                fig_d = go.Figure()
                                x_axis = np.linspace(mean - 4*std, mean + 4*std, 100)
                                y_axis = (1/(std*np.sqrt(2*np.pi))) * np.exp(-0.5*((x_axis-mean)/std)**2)
                                fig_d.add_trace(go.Scatter(x=x_axis, y=y_axis, fill='tozeroy', marker=dict(color='#A8C7FA')))
                                
                                raw_z = (val - mean) / std
                                is_lower_better = b_data.get("lower_is_better")
                                is_good = (-raw_z if is_lower_better else raw_z) > 0
                                marker_color = '#00C805' if is_good else '#FF5000'
                                
                                fig_d.add_vline(x=val, line_color=marker_color, line_width=2)
                                fig_d.add_vline(x=mean, line_dash="dot", line_color="rgba(255,255,255,0.4)")
                                fig_d.update_layout(height=100, margin=dict(l=0,r=0,t=0,b=0), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', xaxis=dict(visible=False), yaxis=dict(visible=False), showlegend=False)
                                st.plotly_chart(fig_d, use_container_width=True, config={'displayModeBar': False})
                                st.caption(f"Val: {val:.2f} | Mean: {mean:.2f}")
                                
                                with st.expander("📊 Metric Details"):
                                    info = METRIC_INFO.get(m_name, {"desc": "Detailed description currently unavailable.", "formula": ""})
                                    st.markdown("**1. Calculation Formula:**")
                                    if info.get("formula"): st.latex(info["formula"])
                                    else: st.write("Formula unavailable.")
                                        
                                    st.markdown("**2. Financial Meaning:**")
                                    st.write(info["desc"])
                                    
                                    st.markdown("**3. Target Polarity:**")
                                    if is_lower_better: st.write("📉 **Lower is Better:** A smaller value implies fundamental undervaluation or lower financial risk.")
                                    else: st.write("📈 **Higher is Better:** A larger value implies greater operational profitability or efficiency.")
                                        
                                    st.markdown("**4. Percentile Ranking:**")
                                    cdf_val = (1.0 + math.erf(raw_z / math.sqrt(2.0))) / 2.0
                                    raw_percentile = cdf_val * 100
                                    
                                    if is_lower_better: st.write(f"Percentile Rank: **{raw_percentile:.1f}th**. Positioned in the **Top {raw_percentile:.1f}%** most attractive peers.")
                                    else: st.write(f"Percentile Rank: **{raw_percentile:.1f}th**. Positioned in the **Top {100 - raw_percentile:.1f}%** most attractive peers.")
                                st.markdown("</div>", unsafe_allow_html=True)
                            idx += 1
            except Exception as e: st.error(str(e))

elif menu_selection == "🏆 Market Rankings":
    st.markdown("<div class='custom-subheader'>📈 Top & Bottom 10 Rankings</div>", unsafe_allow_html=True)
    
    try:
        ind_res = requests.get("http://localhost:8000/industries")
        inds = ["All Industries"] + ind_res.json().get("industries", [])
        selected_ind = st.selectbox("Filter by Industry", options=inds)
        
        rank_res = requests.get(f"http://localhost:8000/rankings?industry={selected_ind}")
        if rank_res.status_code == 200:
            rank_data = rank_res.json()
            
            def fmt_df(d):
                if not d: return pd.DataFrame()
                df = pd.DataFrame(d).rename(columns={"symbol": "Symbol", "company_name": "Company Name", "industry": "Industry", "z_score": "Composite Z-Score"})
                if "Composite Z-Score" in df.columns: df["Composite Z-Score"] = df["Composite Z-Score"].round(2)
                df.insert(0, 'Rank', range(1, len(df) + 1))
                return df
                
            top_df = fmt_df(rank_data.get("top_10", []))
            bot_df = fmt_df(rank_data.get("bottom_10", []))

            def create_ranking_table(df):
                if df.empty: return go.Figure()
                z_colors = ['#A7F3D0' if z >= 0 else '#FECDD3' for z in df['Composite Z-Score']]
                cell_colors = []
                for col in df.columns:
                    if col == 'Composite Z-Score': cell_colors.append(z_colors)
                    elif col == 'Rank': cell_colors.append(['#9CA3AF'] * len(df))
                    elif col == 'Symbol': cell_colors.append(['#A8C7FA'] * len(df))
                    else: cell_colors.append(['#FAFAFA'] * len(df))
                        
                fig = go.Figure(data=[go.Table(
                    columnwidth=[0.8, 1.2, 3.5, 2.5, 1.5],
                    header=dict(values=[f"<b>{c}</b>" for c in df.columns], fill_color='#1D222E', font=dict(family='Outfit', color='#FFFFFF', size=14), align='center', height=45, line_color='#0B0E14'),
                    cells=dict(values=[df[c] for c in df.columns], fill_color='#161A23', font=dict(family='Outfit', color=cell_colors, size=13), align=['center', 'center', 'left', 'center', 'center'], height=40, line_color='#0B0E14')
                )])
                fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=450)
                return fig

            st.markdown("### 🏆 Top 10 (Undervalued / Healthy Fundamentals)")
            if not top_df.empty: st.plotly_chart(create_ranking_table(top_df), use_container_width=True, config={'displayModeBar': False})
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            st.markdown("### 🚨 Bottom 10 (Overvalued / Risky Fundamentals)")
            if not bot_df.empty: st.plotly_chart(create_ranking_table(bot_df), use_container_width=True, config={'displayModeBar': False})
            
    except Exception as e: st.warning(f"Backend error: Ensure FastAPI is running. Details: {e}")

else:
    st.markdown(f"<div class='custom-subheader'>🚧 {menu_selection}</div>", unsafe_allow_html=True)
    st.info("This module is currently under development. The engineering team is actively building the backend pipelines to integrate real-time institutional metrics.")