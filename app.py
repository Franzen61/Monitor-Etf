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

FACTOR_ETFS = [
    "MVOL.MI", "IWQU.MI", "IWMO.MI", "IWVL.MI",
    "ZPRV.DE", "SWDA", "IQSA"
]

FACTOR_COMPARISON = ["SWDA", "IQSA"]

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
    start = end - timedelta(days=6 * 365)

    data = yf.download(
        tickers,
        start=start,
        end=end,
        auto_adjust=True,
        progress=False
    )

    if isinstance(raw.columns, pd.MultiIndex):
        if "Adj Close" in raw.columns.levels[0]:
            prices = raw["Adj Close"]
        elif "Close" in raw.columns.levels[0]:
            prices = raw["Close"]
        else:
            raise ValueError("Né Adj Close né Close trovati")
    else:
        prices = raw

    return prices.dropna(how="all")

prices = load_data(ALL_TICKERS)

# ------------------------
# SAFE RETURNS
# ------------------------
def safe_pct_change(data, days):
    if len(data) <= days:
        return np.nan
    return (data.iloc[-1] / data.iloc[-days-1] - 1) * 100

def safe_ytd(data):
    if data.empty:
        return np.nan
    ytd = data[data.index.year == datetime.today().year]
    if len(ytd) < 2:
        return np.nan
    return (ytd.iloc[-1] / ytd.iloc[0] - 1) * 100

# ------------------------
# RETURNS TABLE
# ------------------------
returns = pd.DataFrame({
    "1D": prices.apply(lambda x: safe_pct_change(x, 1)),
    "1W": prices.apply(lambda x: safe_pct_change(x, 5)),
    "1M": prices.apply(lambda x: safe_pct_change(x, 21)),
    "3M": prices.apply(lambda x: safe_pct_change(x, 63)),
    "6M": prices.apply(lambda x: safe_pct_change(x, 126)),
    "1Y": prices.apply(lambda x: safe_pct_change(x, 252)),
    "3Y": prices.apply(lambda x: safe_pct_change(x, 756)),
    "5Y": prices.apply(lambda x: safe_pct_change(x, 1260)),
})

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

df["Situazione"] = df.apply(situazione, axis=1)
df["Operatività"] = df.apply(operativita, axis=1)

# ========================
# UI TABS
# ========================
tab1, tab2, tab3 = st.tabs([
    "📊 Dashboard Settoriale",
    "📈 Andamento Settoriale",
    "📊 Fattori"
])

# ========================
# TAB 1 — DASHBOARD
# ========================
with tab1:
    col1, col2 = st.columns([1.2,1])

    with col1:
        fig = go.Figure()
        for t in ALL_TICKERS:
            fig.add_bar(x=[t], y=[returns.loc[t,"1D"]])
        fig.update_layout(
            height=300,
            paper_bgcolor="#000",
            plot_bgcolor="#000",
            font_color="white",
            title="Variazione % Giornaliera"
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        for t,row in df.head(3).iterrows():
            st.markdown(f"""
            <div class="leader-box">
                <div class="leader-ticker">{t}</div>
                <div class="leader-mom">Ra Momentum: {row.Ra_momentum:.2f}</div>
                <div>{row.Situazione}</div>
            </div>
            """, unsafe_allow_html=True)

    st.dataframe(df.round(2), use_container_width=True)

# ========================
# TAB 2 — ANDAMENTO
# ========================
with tab2:
    selected = st.multiselect("ETF", SECTORS, default=SECTORS)
    tf = st.selectbox("Timeframe", ["1W","1M","3M","6M","1Y","3Y","5Y"])

    days = {"1W":5,"1M":21,"3M":63,"6M":126,"1Y":252,"3Y":756,"5Y":1260}[tf]
    slice_ = prices.iloc[-days:]
    norm = (slice_ / slice_.iloc[0] - 1) * 100

    fig = go.Figure()
    for t in selected:
        fig.add_trace(go.Scatter(x=norm.index, y=norm[t], name=t, line=dict(width=2)))
    fig.add_trace(go.Scatter(
        x=norm.index, y=norm[BENCHMARK],
        name="SPY", line=dict(width=4, color="#00FF00")
    ))

    fig.update_layout(
        paper_bgcolor="#000",
        plot_bgcolor="#000",
        font_color="white",
        yaxis_title="Variazione %"
    )
    st.plotly_chart(fig, use_container_width=True)

# ========================
# TAB 3 — FATTORI
# ========================
with tab3:
    factor_prices = load_prices(FACTOR_ETFS)
    f = pd.DataFrame(index=FACTOR_ETFS)

    f["Prezzo"] = factor_prices.iloc[-1].round(2)
    f["1D"]  = factor_prices.apply(lambda x: ret(x,1))
    f["1W"]  = factor_prices.apply(lambda x: ret(x,5))
    f["1M"]  = factor_prices.apply(lambda x: ret(x,21))
    f["3M"]  = factor_prices.apply(lambda x: ret(x,63))
    f["6M"]  = factor_prices.apply(lambda x: ret(x,126))
    f["1A"]  = factor_prices.apply(lambda x: ret(x,252))
    f["YTD"] = factor_prices.apply(ret_ytd)
    f["3A"]  = factor_prices.apply(lambda x: ret(x,756))
    f["5A"]  = factor_prices.apply(lambda x: ret(x,1260))

    def style(row):
        if row.name in FACTOR_COMPARISON:
            return ["background-color:#1e1e1e;color:#ccc"]*len(row)
        return ["background-color:#000;color:white"]*len(row)

    st.dataframe(
        f.round(2).style
        .apply(style, axis=1)
        .format({"Prezzo":"{:.2f}", **{c:"{:+.2f}%" for c in f.columns if c!="Prezzo"}}),
        use_container_width=True
    )
