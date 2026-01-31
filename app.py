import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime

st.set_page_config(page_title="S&P500 Sector Relative Strength", layout="wide")

# -------------------------
# CONFIG
# -------------------------
SECTORS = [
    "XLK", "XLY", "XLF", "XLC", "XLV", "XLP",
    "XLI", "XLE", "XLB", "XLU", "XLRE"
]
BENCHMARK = "SPY"
ALL_TICKERS = SECTORS + [BENCHMARK]

TF_DAYS = {
    "1D": 1,
    "1W": 5,
    "1M": 21,
    "3M": 63,
    "6M": 126,
    "1Y": 252,
    "3Y": 756,
    "5Y": 1260
}

RAR_TFS = ["1D", "1W", "1M", "3M", "6M", "1Y"]

CT_WEIGHTS = {
    "1D": 0.10,
    "1W": 0.15,
    "1M": 0.20,
    "3M": 0.25,
    "6M": 0.30
}

RA_WEIGHTS = {
    "1Y": 0.15,
    "6M": 0.25,
    "3M": 0.30,
    "1M": 0.20,
    "1W": 0.10
}

# -------------------------
# DATA DOWNLOAD
# -------------------------
@st.cache_data
def load_prices(tickers):
    data = yf.download(
        tickers,
        period="5y",
        auto_adjust=True,
        progress=False
    )["Close"]
    return data.dropna()

prices = load_prices(ALL_TICKERS)

# -------------------------
# RETURNS
# -------------------------
returns = {}

for tf, days in TF_DAYS.items():
    returns[tf] = prices.pct_change(days).iloc[-1]

returns_df = pd.DataFrame(returns)

# -------------------------
# RAR CALCULATION
# -------------------------
rar_df = pd.DataFrame(index=SECTORS)

for tf in RAR_TFS:
    rar_df[f"RAR_{tf}"] = (
        returns_df.loc[SECTORS, tf] - returns_df.loc[BENCHMARK, tf]
    )

# -------------------------
# RA / MOMENTUM
# -------------------------
ra_momentum = sum(
    rar_df[f"RAR_{tf}"] * weight
    for tf, weight in RA_WEIGHTS.items()
)

rar_df["Ra_Momentum"] = ra_momentum

# -------------------------
# COERENZA TREND PESATA
# -------------------------
def weighted_coherence(row):
    score = sum(
        CT_WEIGHTS[tf] if row[f"RAR_{tf}"] > 0 else 0
        for tf in CT_WEIGHTS
    )
    return max(1, round(score * 5))

rar_df["Coerenza_Trend"] = rar_df.apply(weighted_coherence, axis=1)

# -------------------------
# CLASSIFICA
# -------------------------
rar_df["Classifica"] = (
    rar_df["Ra_Momentum"]
    .rank(ascending=False, method="first")
    .astype(int)
)

# -------------------------
# DELTA RS 5D
# -------------------------
delta_rs = (
    prices[SECTORS].pct_change(5).iloc[-1]
    - prices[BENCHMARK].pct_change(5).iloc[-1]
)
rar_df["DELTA_RS_5D"] = delta_rs.values

# -------------------------
# SITUAZIONE
# -------------------------
def situazione(row):
    if row["Ra_Momentum"] > 0:
        return "LEADER" if row["Coerenza_Trend"] >= 4 else "IN RECUPERO"
    return "DEBOLE"

rar_df["Situazione"] = rar_df.apply(situazione, axis=1)

# -------------------------
# OPERATIVITÀ
# -------------------------
def operativita(row):
    if row["DELTA_RS_5D"] > 0.02 and row["Situazione"] == "IN RECUPERO":
        return "🔭 ALERT BUY"
    if row["Classifica"] <= 3 and row["Coerenza_Trend"] >= 4:
        if row["DELTA_RS_5D"] > 0:
            return "🔥 ACCUMULA"
        return "📈 MANTIENI"
    if row["Classifica"] > 3 and row["Coerenza_Trend"] >= 4:
        return "👀 OSSERVA"
    return "❌ EVITA"

rar_df["Operatività"] = rar_df.apply(operativita, axis=1)

# -------------------------
# REGIME FILTER
# -------------------------
spy_6m_return = returns_df.loc[BENCHMARK, "6M"]

breadth = (rar_df["Ra_Momentum"] > 0).mean()
quality = (rar_df["Coerenza_Trend"] >= 4).mean()

conditions = sum([
    spy_6m_return > 0,
    breadth >= 0.55,
    quality >= 0.40
])

if conditions == 3:
    regime = "🟢 RISK ON"
elif conditions == 2:
    regime = "🟡 NEUTRAL"
else:
    regime = "🔴 RISK OFF"

# -------------------------
# FINAL OPERATIVITY
# -------------------------
def operativita_final(row):
    if regime == "🔴 RISK OFF" and row["Operatività"] in ["🔥 ACCUMULA", "🔭 ALERT BUY"]:
        return "⛔ BLOCCATO (RISK OFF)"
    return row["Operatività"]

rar_df["Operatività_Final"] = rar_df.apply(operativita_final, axis=1)

# -------------------------
# STREAMLIT UI
# -------------------------
st.title("📊 S&P 500 – Sector Relative Strength Dashboard")

st.markdown(f"### Regime di Mercato: **{regime}**")

display_cols = [
    "Ra_Momentum", "Coerenza_Trend", "Classifica",
    "DELTA_RS_5D", "Situazione", "Operatività_Final"
]

st.dataframe(
    rar_df[display_cols]
    .sort_values("Classifica")
    .style.format({
        "Ra_Momentum": "{:.2%}",
        "DELTA_RS_5D": "{:.2%}"
    }),
    use_container_width=True
)
