import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go

st.set_page_config(page_title="S&P 500 Sector RS", layout="wide")

# =====================
# CONFIG
# =====================
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

# =====================
# DATA
# =====================
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

# =====================
# RETURNS
# =====================
returns = {
    tf: prices.pct_change(days).iloc[-1]
    for tf, days in TF_DAYS.items()
}
returns_df = pd.DataFrame(returns)

# =====================
# RAR
# =====================
rar_df = pd.DataFrame(index=SECTORS)

for tf in RAR_TFS:
    rar_df[f"RAR_{tf}"] = (
        returns_df.loc[SECTORS, tf] -
        returns_df.loc[BENCHMARK, tf]
    )

# =====================
# RA / MOMENTUM
# =====================
rar_df["Ra_Momentum"] = sum(
    rar_df[f"RAR_{tf}"] * w
    for tf, w in RA_WEIGHTS.items()
)

# =====================
# COERENZA TREND PESATA
# =====================
def weighted_coherence(row):
    score = sum(
        CT_WEIGHTS[tf] if row[f"RAR_{tf}"] > 0 else 0
        for tf in CT_WEIGHTS
    )
    return max(1, round(score * 5))

rar_df["Coerenza_Trend"] = rar_df.apply(weighted_coherence, axis=1)

# =====================
# CLASSIFICA
# =====================
rar_df["Classifica"] = (
    rar_df["Ra_Momentum"]
    .rank(ascending=False, method="first")
    .astype(int)
)

# =====================
# DELTA RS 5D
# =====================
rar_df["DELTA_RS_5D"] = (
    prices[SECTORS].pct_change(5).iloc[-1] -
    prices[BENCHMARK].pct_change(5).iloc[-1]
).values

# =====================
# SITUAZIONE
# =====================
def situazione(row):
    if row["Ra_Momentum"] > 0:
        return "LEADER" if row["Coerenza_Trend"] >= 4 else "IN RECUPERO"
    return "DEBOLE"

rar_df["Situazione"] = rar_df.apply(situazione, axis=1)

# =====================
# OPERATIVITÀ
# =====================
def operativita(row):
    if row["DELTA_RS_5D"] > 0.02 and row["Situazione"] == "IN RECUPERO":
        return "🔭 ALERT BUY"
    if row["Classifica"] <= 3 and row["Coerenza_Trend"] >= 4:
        return "🔥 ACCUMULA" if row["DELTA_RS_5D"] > 0 else "📈 MANTIENI"
    if row["Classifica"] > 3 and row["Coerenza_Trend"] >= 4:
        return "👀 OSSERVA"
    return "❌ EVITA"

rar_df["Operatività"] = rar_df.apply(operativita, axis=1)

# =====================
# REGIME FILTER
# =====================
spy_6m = returns_df.loc[BENCHMARK, "6M"]
breadth = (rar_df["Ra_Momentum"] > 0).mean()
quality = (rar_df["Coerenza_Trend"] >= 4).mean()

conditions = sum([spy_6m > 0, breadth >= 0.55, quality >= 0.40])

if conditions == 3:
    regime = "🟢 RISK ON"
elif conditions == 2:
    regime = "🟡 NEUTRAL"
else:
    regime = "🔴 RISK OFF"

def operativita_final(row):
    if regime == "🔴 RISK OFF" and row["Operatività"] in ["🔥 ACCUMULA", "🔭 ALERT BUY"]:
        return "⛔ BLOCCATO (RISK OFF)"
    return row["Operatività"]

rar_df["Operatività_Final"] = rar_df.apply(operativita_final, axis=1)

# =====================
# UI — TABS
# =====================
tab1, tab2 = st.tabs(["📊 Dashboard", "📈 Confronto Prezzi"])

# -------- TAB 1
with tab1:
    st.title("📊 S&P 500 – Sector Relative Strength")
    st.markdown(f"### Regime di Mercato: **{regime}**")

    top3 = rar_df.sort_values("Ra_Momentum", ascending=False).head(3)
    cols = st.columns(3)
    colors = ["#00c853", "#64dd17", "#aeea00"]

    for col, (etf, row), color in zip(cols, top3.iterrows(), colors):
        col.markdown(
            f"""
            <div style="background:{color};padding:20px;border-radius:12px;text-align:center;">
                <h2>{etf}</h2>
                <h4>{row['Situazione']}</h4>
                <h3>{row['Ra_Momentum']:.2%}</h3>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.subheader("Classifica Settoriale")

    st.dataframe(
        rar_df[
            ["Ra_Momentum", "Coerenza_Trend", "Classifica",
             "DELTA_RS_5D", "Situazione", "Operatività_Final"]
        ]
        .sort_values("Ra_Momentum", ascending=False)
        .style.format({
            "Ra_Momentum": "{:.2%}",
            "DELTA_RS_5D": "{:.2%}"
        }),
        use_container_width=True
    )

# -------- TAB 2
with tab2:
    st.title("📈 ETF Settoriali vs SPY (Normalizzati)")

    tf_map = {
        "1W": 5, "1M": 21, "3M": 63,
        "6M": 126, "1Y": 252, "3Y": 756, "5Y": 1260
    }

    tf = st.radio("Timeframe", list(tf_map.keys()), horizontal=True)
    days = tf_map[tf]

    data = prices[ALL_TICKERS].iloc[-days:]
    norm = data / data.iloc[0] * 100

    fig = go.Figure()

    for etf in SECTORS:
        fig.add_trace(go.Scatter(
            x=norm.index, y=norm[etf],
            mode="lines", name=etf, line=dict(width=1)
        ))

    fig.add_trace(go.Scatter(
        x=norm.index, y=norm["SPY"],
        mode="lines", name="SPY",
        line=dict(width=4, color="black")
    ))

    fig.update_layout(
        template="plotly_dark",
        yaxis_title="Indice Normalizzato (Base 100)",
        height=650
    )

    st.plotly_chart(fig, use_container_width=True)
