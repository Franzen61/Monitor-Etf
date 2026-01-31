import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ------------------------
# CONFIG
# ------------------------
st.set_page_config(layout="wide", page_title="S&P500 Sector Relative Strength")

SECTORS = [
    "XLK", "XLY", "XLF", "XLC", "XLV",
    "XLP", "XLI", "XLE", "XLB", "XLU", "XLRE"
]
BENCHMARK = "SPY"
ALL_TICKERS = SECTORS + [BENCHMARK]

WEIGHTS = {
    "1Y": 0.15,
    "6M": 0.25,
    "3M": 0.30,
    "1M": 0.20,
    "1W": 0.10
}

# ------------------------
# DATA DOWNLOAD
# ------------------------
@st.cache_data
def load_data():
    end = datetime.today()
    start = end - timedelta(days=5 * 365)

    raw = yf.download(
        ALL_TICKERS,
        start=start,
        end=end,
        auto_adjust=False,
        progress=False
    )

    # Caso MultiIndex (più ticker)
    if isinstance(raw.columns, pd.MultiIndex):
        prices = raw["Adj Close"]
    else:
        prices = raw

    return prices.dropna()


prices = load_data()

# ------------------------
# RETURNS
# ------------------------
def pct_change(days):
    return prices.pct_change(days).iloc[-1] * 100

returns = pd.DataFrame({
    "1D": pct_change(1),
    "1W": pct_change(5),
    "1M": pct_change(21),
    "3M": pct_change(63),
    "6M": pct_change(126),
    "1Y": pct_change(252),
    "3Y": pct_change(756),
    "5Y": pct_change(1260),
})

# ------------------------
# RAR CALCULATION
# ------------------------
rar = returns.sub(returns.loc[BENCHMARK])

# ------------------------
# COERENZA TREND (PESATA)
# ------------------------
def coerenza_pesata(row):
    score = 0
    score += 1 if row["1D"] > 0 else 0
    score += 1 if row["1W"] > 0 else 0
    score += 1 if row["1M"] > 0 else 0
    score += 1 if row["3M"] > 0 else 0
    score += 1 if row["6M"] > 0 else 0
    return max(score, 1)

# ------------------------
# DATAFRAME
# ------------------------
df = rar.copy()
df["Ra_momentum"] = (
    rar["1Y"] * WEIGHTS["1Y"] +
    rar["6M"] * WEIGHTS["6M"] +
    rar["3M"] * WEIGHTS["3M"] +
    rar["1M"] * WEIGHTS["1M"] +
    rar["1W"] * WEIGHTS["1W"]
)

df["Coerenza_Trend"] = rar.apply(coerenza_pesata, axis=1)
df["Delta_RS_5D"] = rar["1W"]

df = df.loc[SECTORS]
df = df.sort_values("Ra_momentum", ascending=False)
df["Classifica"] = range(1, len(df) + 1)

def situazione(row):
    if row["Ra_momentum"] > 0:
        return "LEADER" if row["Coerenza_Trend"] >= 4 else "IN RECUPERO"
    return "DEBOLE"

df["Situazione"] = df.apply(situazione, axis=1)

def operativita(row):
    if row["Delta_RS_5D"] > 0.02 and row["Situazione"] == "IN RECUPERO":
        return "🔭 ALERT BUY"
    if row["Classifica"] <= 3 and row["Coerenza_Trend"] >= 4 and row["Delta_RS_5D"] > 0:
        return "🔥 ACCUMULA"
    if row["Classifica"] <= 3 and row["Coerenza_Trend"] >= 4:
        return "📈 MANTIENI"
    if row["Classifica"] > 3 and row["Coerenza_Trend"] >= 4:
        return "👀 OSSERVA"
    return "❌ EVITA"

df["Operatività"] = df.apply(operativita, axis=1)

# ------------------------
# UI
# ------------------------
tab1, tab2 = st.tabs(["📊 Dashboard Settoriale", "📈 Andamento Settoriale"])

# ========================
# TAB 1
# ========================
with tab1:
    col_left, col_right = st.columns([1.3, 1])

    # ---- BAR CHART DAILY ----
    with col_left:
        daily = returns.loc[ALL_TICKERS, "1D"]

        fig_bar = go.Figure()
        for t in ALL_TICKERS:
            fig_bar.add_bar(name=t, x=[t], y=[daily[t]])

        fig_bar.update_layout(
            height=300,
            title="Variazione % Giornaliera",
            showlegend=False
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    # ---- LEADER MONITORS ----
    with col_right:
        leaders = df.head(3)
        for _, row in leaders.iterrows():
            st.markdown(
                f"""
                <div style="padding:15px;border-radius:12px;
                background:linear-gradient(135deg,#111,#222);
                color:white;margin-bottom:10px">
                <h3>{row.name}</h3>
                <p>Ra Momentum: {row.Ra_momentum:.2f}</p>
                <p>{row.Operatività}</p>
                </div>
                """,
                unsafe_allow_html=True
            )

    st.dataframe(df, use_container_width=True)

# ========================
# TAB 2
# ========================
with tab2:
    st.subheader("Andamento Settoriale")

    selected = st.multiselect(
        "Seleziona ETF",
        SECTORS,
        default=SECTORS
    )

    tf = st.selectbox("Timeframe", ["1W", "1M", "3M", "6M", "1Y", "3Y", "5Y"])

    days_map = {
        "1W": 5,
        "1M": 21,
        "3M": 63,
        "6M": 126,
        "1Y": 252,
        "3Y": 756,
        "5Y": 1260
    }

    norm = prices.iloc[-days_map[tf]:]
    norm = norm / norm.iloc[0] * 100

    fig = go.Figure()

    for etf in selected:
        fig.add_trace(go.Scatter(
            x=norm.index,
            y=norm[etf],
            name=etf,
            line=dict(width=2)
        ))

    fig.add_trace(go.Scatter(
        x=norm.index,
        y=norm[BENCHMARK],
        name="SPY",
        line=dict(width=4, color="black")
    ))

    fig.update_layout(height=600)
    st.plotly_chart(fig, use_container_width=True)
