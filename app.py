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
        background-size: 10px 10px; /* Effetto griglia terminale */
    }
    .leader-ticker { color: #ff9900; font-size: 1.4em; font-weight: bold; }
    .leader-mom { color: #00ff00; font-size: 1em; font-family: 'Courier New', Courier, monospace; }
    .leader-op { color: #ffffff; font-size: 1em; font-weight: bold; margin-top: 5px; }
    </style>
    """, unsafe_allow_html=True)

SECTORS = ["XLK", "XLY", "XLF", "XLC", "XLV", "XLP", "XLI", "XLE", "XLB", "XLU", "XLRE"]
BENCHMARK = "SPY"
ALL_TICKERS = SECTORS + [BENCHMARK]

WEIGHTS = {"1Y": 0.15, "6M": 0.25, "3M": 0.30, "1M": 0.20, "1W": 0.10}

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

df = rar.copy()
df["Ra_momentum"] = (rar["1Y"]*WEIGHTS["1Y"] + rar["6M"]*WEIGHTS["6M"] + rar["3M"]*WEIGHTS["3M"] + rar["1M"]*WEIGHTS["1M"] + rar["1W"]*WEIGHTS["1W"])
df["Coerenza_Trend"] = rar.apply(coerenza_pesata, axis=1)
df["Delta_RS_5D"] = rar["1W"]
df = df.loc[SECTORS].sort_values("Ra_momentum", ascending=False)
df["Classifica"] = range(1, len(df) + 1)

def operativita(row):
    if row["Delta_RS_5D"] > 0.02 and row["Ra_momentum"] > 0: return "🔭 ALERT BUY"
    if row["Classifica"] <= 3 and row["Coerenza_Trend"] >= 4: return "🔥 ACCUMULA"
    if row["Coerenza_Trend"] >= 4: return "📈 MANTIENI"
    if row["Coerenza_Trend"] >= 3: return "👀 OSSERVA"
    return "❌ EVITA"

df["Operatività"] = df.apply(operativita, axis=1)

# ------------------------
# UI - DASHBOARD
# ------------------------
tab1, tab2 = st.tabs(["📊 Dashboard Settoriale", "📈 Andamento Settoriale"])

with tab1:
    col_left, col_right = st.columns([1.3, 1])

    with col_left:
        daily = returns.loc[ALL_TICKERS, "1D"].sort_values()
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            x=daily.index, y=daily.values,
            marker_color=['#ff4b4b' if x < 0 else '#00ff00' for x in daily.values]
        ))
        fig_bar.update_layout(
            height=450, title="Variazione % Giornaliera",
            template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            yaxis=dict(gridcolor='#333'), xaxis=dict(gridcolor='#333')
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_right:
        st.markdown("### 🏆 Sector Leaders")
        leaders = df.head(3)
        for ticker, row in leaders.iterrows():
            st.markdown(f"""
                <div class="leader-box">
                    <div class="leader-ticker">{ticker}</div>
                    <div class="leader-mom">Momentum: {row.Ra_momentum:+.2f}</div>
                    <div class="leader-op">{row.Operatività}</div>
                </div>
                """, unsafe_allow_html=True)

    st.dataframe(df.style.format("{:.2f}"), use_container_width=True)

# ------------------------
# UI - ANDAMENTO (BASE 0)
# ------------------------
with tab2:
    st.subheader("Andamento Settoriale (Variazione %)")
    selected = st.multiselect("Seleziona ETF", SECTORS, default=["XLK", "XLE", "XLF"])
    tf = st.selectbox("Timeframe", ["1W", "1M", "3M", "6M", "1Y"], index=2)
    
    days_map = {"1W": 5, "1M": 21, "3M": 63, "6M": 126, "1Y": 252}
    
    # Calcolo Base 0 (Variazione Percentuale Netta)
    plot_data = prices.iloc[-days_map[tf]:]
    plot_data = (plot_data / plot_data.iloc[0] - 1) * 100 
    
    fig = go.Figure()
    for etf in selected:
        fig.add_trace(go.Scatter(x=plot_data.index, y=plot_data[etf], name=etf, line=dict(width=2)))
    
    # SPY GIALLO FLUO E MOLTO SPESSO
    fig.add_trace(go.Scatter(
        x=plot_data.index, y=plot_data[BENCHMARK], 
        name="SPY (Benchmark)", line=dict(width=5, color="#CCFF00")
    ))
    
    fig.update_layout(
        height=650, template="plotly_dark",
        yaxis_title="Variazione % (Base 0)",
        hovermode="x unified",
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        yaxis=dict(gridcolor='#333', zerolinecolor='#666'), xaxis=dict(gridcolor='#333')
    )
    st.plotly_chart(fig, use_container_width=True)
