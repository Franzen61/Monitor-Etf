import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta

# ------------------------
# CONFIG
# ------------------------
st.set_page_config(layout="wide", page_title="Financial Terminal")

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
    "ZPRV.DE", "SWDA.MI", "IQSA.MI"
]

FACTOR_COMPARISON = ["SWDA.MI", "IQSA.MI"]

# ------------------------
# DATA LOADER (ADJUSTED)
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

    if isinstance(data.columns, pd.MultiIndex):
        data = data["Close"]

    return data.dropna(how="all")

# ------------------------
# SAFE RETURNS
# ------------------------
def ret(data, days):
    if len(data) <= days:
        return np.nan
    return (data.iloc[-1] / data.iloc[-days-1] - 1) * 100

def ret_ytd(data):
    ytd = data[data.index.year == datetime.today().year]
    if len(ytd) < 2:
        return np.nan
    return (ytd.iloc[-1] / ytd.iloc[0] - 1) * 100

# ------------------------
# LOAD DATA
# ------------------------
prices = load_data(ALL_TICKERS)

# ------------------------
# UI
# ------------------------
tab1, tab2, tab3 = st.tabs([
    "📊 Dashboard Settoriale",
    "📈 Andamento Settoriale",
    "📊 Fattori"
])

# ========================
# TAB 3 — FATTORI
# ========================
with tab3:
    factor_prices = load_data(FACTOR_ETFS)

    df = pd.DataFrame(index=FACTOR_ETFS)

    df["Prezzo"] = factor_prices.iloc[-1].round(2)

    df["1D"]  = factor_prices.apply(lambda x: ret(x, 1))
    df["1W"]  = factor_prices.apply(lambda x: ret(x, 5))
    df["1M"]  = factor_prices.apply(lambda x: ret(x, 21))
    df["3M"]  = factor_prices.apply(lambda x: ret(x, 63))
    df["6M"]  = factor_prices.apply(lambda x: ret(x, 126))
    df["1A"]  = factor_prices.apply(lambda x: ret(x, 252))
    df["YTD"] = factor_prices.apply(ret_ytd)
    df["3A"]  = factor_prices.apply(lambda x: ret(x, 756))
    df["5A"]  = factor_prices.apply(lambda x: ret(x, 1260))

    df = df.round(2)

    def style(row):
        if row.name in FACTOR_COMPARISON:
            return ["background-color:#1e1e1e;color:#cccccc"] * len(row)
        return ["background-color:#000000;color:white"] * len(row)

    st.dataframe(
        df.style
        .apply(style, axis=1)
        .format({
            "Prezzo": "{:.2f}",
            **{c: "{:+.2f}%" for c in df.columns if c != "Prezzo"}
        }),
        use_container_width=True
    )
