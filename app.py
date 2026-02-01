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
# TICKERS
# ------------------------
SECTORS = [
    "XLK", "XLY", "XLF", "XLC", "XLV",
    "XLP", "XLI", "XLE", "XLB", "XLU", "XLRE"
]
BENCHMARK = "SPY"
ALL_TICKERS = SECTORS + [BENCHMARK]

# ETF FATTORIALI
FACTOR_ETFS = [
    "MVOL.MI",
    "IWQU.MI",
    "IWMO.MI",
    "IWVL.MI",
    "ZPRV.DE",
    "SWDA",
    "IQSA"
]
FACTOR_BENCHMARKS = ["SWDA", "IQSA"]

WEIGHTS = {
    "1Y": 0.15,
    "6M": 0.25,
    "3M": 0.30,
    "1M": 0.20,
    "1W": 0.10
}

# ------------------------
# DATA DOWNLOAD (ROBUSTO)
# ------------------------
@st.cache_data
def load_data(tickers):
    end = datetime.today()
    start = end - timedelta(days=5 * 365)

    raw = yf.download(
        tickers,
        start=start,
        end=end,
        progress=False,
        auto_adjust=False
    )

    if isinstance(raw.columns, pd.MultiIndex):
        if "Adj Close" in raw.columns.levels[0]:
            prices = raw["Adj Close"]
        elif "Close" in raw.columns.levels[0]:
            prices = raw["Close"]
        else:
            raise ValueError("Né 'Adj Close' né 'Close' trovati nei dati Yahoo")
    else:
        prices = raw

    return prices.dropna()

prices = load_data(ALL_TICKERS)
factor_prices = load_data(FACTOR_ETFS)

# ------------------------
# RETURNS SETTORI
# ------------------------
def pct_change(data, days):
    return data.pct_change(days).iloc[-1] * 100

returns = pd.DataFrame({
    "1D": pct_change(prices, 1),
    "1W": pct_change(prices, 5),
    "1M": pct_change(prices, 21),
    "3M": pct_change(prices, 63),
    "6M": pct_change(prices, 126),
    "1Y": pct_change(prices, 252),
    "3Y": pct_change(prices, 756),
    "5Y": pct_change(prices, 1260),
})

# ------------------------
# RAR
# ------------------------
rar = returns.sub(returns.loc[BENCHMARK])

# ------------------------
# COERENZA TREND
# ------------------------
def coerenza_trend(row):
    score = sum([
        row["1D"] > 0,
        row["1W"] > 0,
        row["1M"] > 0,
        row["3M"] > 0,
        row["6M"] > 0
    ])
    return max(score, 1)

df = rar.loc[SECTORS].copy()

df["Ra_momentum"] = (
    rar["1Y"] * WEIGHTS["1Y"] +
    rar["6M"] * WEIGHTS["6M"] +
    rar["3M"] * WEIGHTS["3M"] +
    rar["1M"] * WEIGHTS["1M"] +
    rar["1W"] * WEIGHTS["1W"]
)

df["Coerenza_Trend"] = rar.apply(coerenza_trend, axis=1).loc[SECTORS]
df["Delta_RS_5D"] = rar["1W"].loc[SECTORS]

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
# UI TABS
# ------------------------
tab1, tab2, tab3 = st.tabs([
    "📊 Dashboard Settoriale",
    "📈 Andamento Settoriale",
    "📐 Fattori"
])

# ========================
# TAB 1
# ========================
with tab1:
    col_left, col_right = st.columns([1.3, 1])

    with col_left:
        daily = returns.loc[ALL_TICKERS, "1D"]
        fig_bar = go.Figure()
        for t in ALL_TICKERS:
            fig_bar.add_bar(x=[t], y=[daily[t]])
        fig_bar.update_layout(
            height=300,
            title="Variazione % Giornaliera",
            paper_bgcolor="#000000",
            plot_bgcolor="#000000",
            font_color="white",
            showlegend=False
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_right:
        for ticker, row in df.head(3).iterrows():
            st.markdown(f"""
            <div class="leader-box">
                <div class="leader-ticker">{ticker}</div>
                <div class="leader-mom">Ra Momentum: {row.Ra_momentum:.2f}</div>
                <div class="leader-op">{row.Operatività}</div>
            </div>
            """, unsafe_allow_html=True)

    st.dataframe(df, use_container_width=True)

# ========================
# TAB 2
# ========================
with tab2:
    st.subheader("Andamento Settoriale")

    selected = st.multiselect("Seleziona ETF", SECTORS, default=SECTORS)
    tf = st.selectbox("Timeframe", ["1W", "1M", "3M", "6M", "1Y", "3Y", "5Y"])

    days_map = {
        "1W": 5, "1M": 21, "3M": 63,
        "6M": 126, "1Y": 252, "3Y": 756, "5Y": 1260
    }

    slice_ = prices.iloc[-days_map[tf]:]
    norm = (slice_ / slice_.iloc[0] - 1) * 100

    fig = go.Figure()
    for etf in selected:
        fig.add_trace(go.Scatter(x=norm.index, y=norm[etf], name=etf, line=dict(width=2.5)))

    fig.add_trace(go.Scatter(
        x=norm.index,
        y=norm[BENCHMARK],
        name="SPY",
        line=dict(width=5, color="#00FF00")
    ))

    fig.update_layout(
        height=600,
        paper_bgcolor="#000000",
        plot_bgcolor="#000000",
        font_color="white",
        yaxis_title="Variazione %"
    )

    st.plotly_chart(fig, use_container_width=True)

# ========================
# TAB 3 — FATTORI
# ========================
with tab3:
    st.subheader("Performance ETF Fattoriali")

    factor_df = pd.DataFrame({
        "1D": pct_change(factor_prices, 1),
        "1W": pct_change(factor_prices, 5),
        "1M": pct_change(factor_prices, 21),
        "3M": pct_change(factor_prices, 63),
        "6M": pct_change(factor_prices, 126),
        "1Y": pct_change(factor_prices, 252),
        "YTD": (factor_prices.iloc[-1] /
                factor_prices[factor_prices.index.year == datetime.today().year].iloc[0] - 1) * 100,
        "3Y": pct_change(factor_prices, 756),
        "5Y": pct_change(factor_prices, 1260),
    }).round(2)

    def highlight_rows(row):
        if row.name in FACTOR_BENCHMARKS:
            return ["background-color: #1f1f1f"] * len(row)
        return [""] * len(row)

    styled = (
        factor_df
        .style
        .apply(highlight_rows, axis=1)
        .set_properties(**{
            "color": "white",
            "background-color": "#000000",
            "border-color": "#333"
        })
    )

    st.dataframe(styled, use_container_width=True)
