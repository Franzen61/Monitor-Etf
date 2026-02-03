import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ------------------------
# CONFIG & STYLE (Bloomberg Dark)
# ------------------------
st.set_page_config(layout="wide", page_title="Financial Terminal - Bloomberg Style")

st.markdown("""
    <style>
    .main { background-color: #000000; color: #ffffff; }
    .leader-box {
        background: linear-gradient(135deg, #1a1a1a 0%, #0a0a0a 100%);
        border: 1px solid #333;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 12px;
        background-image: radial-gradient(#333 1px, transparent 1px);
        background-size: 10px 10px;
    }
    .leader-ticker { color: #ff9900; font-size: 1.4em; font-weight: bold; }
    .leader-mom { color: #00ff00; font-size: 1em; font-family: 'Courier New', Courier, monospace; }
    .leader-op { color: #ffffff; font-size: 1em; font-weight: bold; margin-top: 5px; }
    </style>
    """, unsafe_allow_html=True)

# ------------------------
# CONSTANTS & TICKERS
# ------------------------
SECTORS = ["XLK", "XLY", "XLF", "XLC", "XLV", "XLP", "XLI", "XLE", "XLB", "XLU", "XLRE"]
FACTORS = ["MTUM", "VLUE", "QUAL", "SIZE", "USMV", "DVY"]
BENCHMARK = "SPY"
CYCLICAL = ["XLK", "XLY", "XLF", "XLI", "XLB", "XLE"]
DEFENSIVE = ["XLV", "XLP", "XLU", "XLRE"]
ALL_TICKERS = list(set(SECTORS + FACTORS + [BENCHMARK]))

WEIGHTS = {"1Y": 0.15, "6M": 0.25, "3M": 0.30, "1M": 0.20, "1W": 0.10}

# ------------------------
# RETURN FUNCTIONS
# ------------------------
def compute_rotation_score_series(prices):
    ret_1m = prices.pct_change(21)
    ret_3m = prices.pct_change(63)
    ret_6m = prices.pct_change(126)
    
    rar_1m = ret_1m.sub(ret_1m[BENCHMARK], axis=0)
    rar_3m = ret_3m.sub(ret_3m[BENCHMARK], axis=0)
    rar_6m = ret_6m.sub(ret_6m[BENCHMARK], axis=0)
    
    rar_mean = (rar_1m + rar_3m + rar_6m) / 3
    
    cyc = rar_mean[CYCLICAL].mean(axis=1)
    def_ = rar_mean[DEFENSIVE].mean(axis=1)
    
    rotation_score = (cyc - def_) * 100
    return rotation_score.dropna()

# ------------------------
# DATA DOWNLOAD
# ------------------------
@st.cache_data(ttl=3600)
def load_data():
    end = datetime.today()
    start = end - timedelta(days=5 * 365)
    raw = yf.download(ALL_TICKERS, start=start, end=end, auto_adjust=False, progress=False)
    prices = raw["Adj Close"] if isinstance(raw.columns, pd.MultiIndex) else raw
    return prices.dropna()

prices = load_data()

# ------------------------
# CALCULATIONS
# ------------------------
def pct_change(days):
    return prices.pct_change(days).iloc[-1] * 100

returns = pd.DataFrame({
    "1D": pct_change(1), "1W": pct_change(5), "1M": pct_change(21),
    "3M": pct_change(63), "6M": pct_change(126), "1Y": pct_change(252)
})

rar = returns.sub(returns.loc[BENCHMARK])

def coerenza_pesata(row):
    score = sum([1 for tf in ["1D", "1W", "1M", "3M", "6M"] if row[tf] > 0])
    return max(score, 1)

# --- ELABORAZIONE SETTORI ---
df_sectors = rar.loc[SECTORS].copy()
df_sectors["Ra_momentum"] = (df_sectors["1Y"]*WEIGHTS["1Y"] + df_sectors["6M"]*WEIGHTS["6M"] + 
                             df_sectors["3M"]*WEIGHTS["3M"] + df_sectors["1M"]*WEIGHTS["1M"] + 
                             df_sectors["1W"]*WEIGHTS["1W"])
df_sectors["Coerenza_Trend"] = df_sectors.apply(coerenza_pesata, axis=1)
df_sectors["Delta_RS_5D"] = df_sectors["1W"]
df_sectors = df_sectors.sort_values("Ra_momentum", ascending=False)
df_sectors["Classifica"] = range(1, len(df_sectors) + 1)

def get_operativita(row):
    if row["Delta_RS_5D"] > 0.02 and row["Ra_momentum"] > 0: return "🔭 ALERT BUY"
    if row["Classifica"] <= 3 and row["Coerenza_Trend"] >= 4: return "🔥 ACCUMULA"
    if row["Coerenza_Trend"] >= 4: return "📈 MANTIENI"
    if row["Coerenza_Trend"] >= 3: return "👀 OSSERVA"
    return "❌ EVITA"

df_sectors["Operatività"] = df_sectors.apply(get_operativita, axis=1)

# --- ELABORAZIONE FATTORI ---
df_factors = rar.loc[FACTORS].copy()
df_factors["Prezzo"] = prices[FACTORS].iloc[-1]
df_factors["Ra_momentum"] = (df_factors["1Y"]*WEIGHTS["1Y"] + df_factors["6M"]*WEIGHTS["6M"] + 
                             df_factors["3M"]*WEIGHTS["3M"] + df_factors["1M"]*WEIGHTS["1M"] + 
                             df_factors["1W"]*WEIGHTS["1W"])
df_factors = df_factors.sort_values("Ra_momentum", ascending=False)

# ------------------------
# STYLING FUNCTIONS
# ------------------------
def style_factors(row):
    return ['color: #00ff00' if v > 0 else 'color: #ff4b4b' if v < 0 else '' for v in row]

def highlight_max(s):
    max_val = s.max()
    return ["background-color:#003300;color:#00FF00;font-weight:bold" if v == max_val else "" for v in s]

# ------------------------
# UI - DASHBOARD
# ------------------------
tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard Settoriale", "📈 Andamento Settoriale", "🧬 Analisi Fattori", "🔄 Market Rotation"])

with tab1:
    col_left, col_right = st.columns([1.3, 1])
    with col_left:
        daily = returns.loc[SECTORS + [BENCHMARK], "1D"].sort_values()
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(x=daily.index, y=daily.values, marker_color=['#ff4b4b' if x < 0 else '#00ff00' for x in daily.values]))
        fig_bar.update_layout(height=450, title="Variazione % Giornaliera", template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_bar, use_container_width=True)
    with col_right:
        st.markdown("### 🏆 Sector Leaders")
        leaders = df_sectors.head(3)
        for ticker, row in leaders.iterrows():
            st.markdown(f'<div class="leader-box"><div class="leader-ticker">{ticker}</div><div class="leader-mom">Momentum: {row.Ra_momentum:+.2f}</div><div class="leader-op">{row.Operatività}</div></div>', unsafe_allow_html=True)
    st.subheader("Dashboard Operativa Settori")
    st.dataframe(df_sectors.style.format("{:.2f}"), use_container_width=True)

with tab2:
    st.subheader("Andamento Settoriale (Variazione %)")
    selected = st.multiselect("Seleziona ETF", SECTORS, default=["XLK", "XLE", "XLF"])
    tf = st.selectbox("Timeframe", ["1W", "1M", "3M", "6M", "1Y"], index=2)
    days_map = {"1W": 5, "1M": 21, "3M": 63, "6M": 126, "1Y": 252}
    plot_data = (prices.iloc[-days_map[tf]:] / prices.iloc[-days_map[tf]] - 1) * 100
    fig = go.Figure()
    for etf in selected:
        fig.add_trace(go.Scatter(x=plot_data.index, y=plot_data[etf], name=etf, line=dict(width=2)))
    fig.add_trace(go.Scatter(x=plot_data.index, y=plot_data[BENCHMARK], name="SPY", line=dict(width=5, color="#CCFF00")))
    fig.update_layout(height=650, template="plotly_dark", yaxis_title="Variazione % (Base 0)", hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.title("🧬 Analisi Fattori")
    f = df_factors.copy()
    st.dataframe(
        f.round(2).style
        .apply(style_factors, axis=1, subset=[c for c in f.columns if c != "Prezzo"])
        .apply(highlight_max, subset=[c for c in f.columns if c != "Prezzo"])
        .format({"Prezzo":"{:.2f}", **{c:"{:+.2f}%" for c in f.columns if c!="Prezzo"}}),
        use_container_width=True
    )

with tab4:
    st.title("🔄 Market Rotation Score")
    rotation_series = compute_rotation_score_series(prices)
    current_score = rotation_series.iloc[-1]
    
    st.metric("Rotation Score Attuale", f"{current_score:+.2f}")
    
    # --- ROTATION SCORE SPARKLINE 12 MESI ---
    rotation_12m = rotation_series.last("365D")
    fig_rs = go.Figure()
    fig_rs.add_trace(go.Scatter(x=rotation_12m.index, y=rotation_12m, mode="lines", line=dict(color="#DDDDDD", width=2)))
    fig_rs.add_hline(y=1.5, line_dash="dot", line_color="#006600")
    fig_rs.add_hline(y=0.0, line_dash="dot", line_color="#666666")
    fig_rs.add_hline(y=-1.5, line_dash="dot", line_color="#660000")
    fig_rs.update_layout(height=140, margin=dict(l=20, r=20, t=10, b=10), paper_bgcolor="#000000", plot_bgcolor="#000000", font_color="white", showlegend=False)
    st.plotly_chart(fig_rs, use_container_width=True)
    
    if current_score > 1.5:
        st.success("🔥 Forte propensione al rischio (Ciclici dominanti)")
    elif current_score < -1.5:
        st.error("🛡️ Difensiva estrema (Risk-Off)")
    else:
        st.info("⚖️ Mercato in equilibrio")
