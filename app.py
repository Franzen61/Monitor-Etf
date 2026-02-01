import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ========================
# CONFIG & STYLE
# ========================
st.set_page_config(layout="wide", page_title="Financial Terminal")

st.markdown("""
<style>
.main { background-color: #000000; color: #ffffff; }
.leader-box {
    background: linear-gradient(135deg, #1a1a1a 0%, #0a0a0a 100%);
    border: 1px solid #333;
    border-radius: 8px;
    padding: 15px;
    margin-bottom: 12px;
}
.leader-ticker { color: #ff9900; font-size: 1.4em; font-weight: bold; }
.leader-mom { color: #00ff00; font-family: monospace; }
</style>
""", unsafe_allow_html=True)

# ========================
# TICKERS
# ========================
SECTORS = ["XLK","XLY","XLF","XLC","XLV","XLP","XLI","XLE","XLB","XLU","XLRE"]
BENCHMARK = "SPY"
ALL_TICKERS = SECTORS + [BENCHMARK]

FACTOR_ETFS = [
    "MVOL.MI","IWQU.MI","IWMO.MI","IWVL.MI",
    "ZPRV.DE","SWDA.MI","IQSA.MI"
]
FACTOR_COMPARISON = ["SWDA.MI","IQSA.MI"]

WEIGHTS = {"1Y":0.15,"6M":0.25,"3M":0.30,"1M":0.20,"1W":0.10}

# ========================
# DATA LOADER (ADJUSTED)
# ========================
@st.cache_data
def load_prices(tickers):
    end = datetime.today()
    start = end - timedelta(days=6*365)

    data = yf.download(
        tickers,
        start=start,
        end=end,
        auto_adjust=True,
        progress=False
    )

    if isinstance(data.columns, pd.MultiIndex):
        data = data["Close"]

    return data.dropna(how="all")

# ========================
# RETURN FUNCTIONS
# ========================
def ret(data, days):
    if len(data) <= days:
        return np.nan
    return (data.iloc[-1] / data.iloc[-days-1] - 1) * 100

def ret_ytd(data):
    ytd = data[data.index.year == datetime.today().year]
    if len(ytd) < 2:
        return np.nan
    return (ytd.iloc[-1] / ytd.iloc[0] - 1) * 100

# ========================
# LOAD DATA
# ========================
prices = load_prices(ALL_TICKERS)

returns = pd.DataFrame({
    "1D": prices.apply(lambda x: ret(x,1)),
    "1W": prices.apply(lambda x: ret(x,5)),
    "1M": prices.apply(lambda x: ret(x,21)),
    "3M": prices.apply(lambda x: ret(x,63)),
    "6M": prices.apply(lambda x: ret(x,126)),
    "1Y": prices.apply(lambda x: ret(x,252)),
})

rar = returns.sub(returns.loc[BENCHMARK])
df = rar.loc[SECTORS].copy()

df["Ra_momentum"] = (
    rar["1Y"]*WEIGHTS["1Y"] +
    rar["6M"]*WEIGHTS["6M"] +
    rar["3M"]*WEIGHTS["3M"] +
    rar["1M"]*WEIGHTS["1M"] +
    rar["1W"]*WEIGHTS["1W"]
)

df["Coerenza_Trend"] = df[["1D","1W","1M","3M","6M"]].gt(0).sum(axis=1)
df["Delta_RS_5D"] = df["]()
