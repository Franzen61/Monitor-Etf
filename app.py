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

CYCLICALS = ["XLK","XLY","XLF","XLI","XLB","XLE"]
DEFENSIVES = ["XLV","XLP","XLU","XLRE"]

FACTOR_ETFS = [
    "MVOL.MI","IWQU.MI","IWMO.MI","IWVL.MI",
    "IUSN.DE","SWDA.MI","IQSA.MI"
]
FACTOR_COMPARISON = ["SWDA.MI","IQSA.MI"]

WEIGHTS = {"1M":0.30,"3M":0.40,"6M":0.30}

# ========================
# DATA LOADER
# ========================
@st.cache_data(ttl=60*60)
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
# RSR FUNCTION (EXCEL-COMPATIBLE)
# ========================
def rsr(etf_ret, bm_ret):
    return ((1 + etf_ret/100) / (1 + bm_ret/100) - 1) * 100

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
})

# ========================
# RAR — per ranking
# ========================
rar = returns.sub(returns.loc[BENCHMARK])
df = rar.loc[SECTORS].copy()

df["Ra_momentum"] = (
    df["1M"]*WEIGHTS["1M"] +
    df["3M"]*WEIGHTS["3M"] +
    df["6M"]*WEIGHTS["6M"]
)

df["Coerenza_Trend"] = df[["1D","1W","1M","3M","6M"]].gt(0).sum(axis=1)

# 🔧 DELTA RS REALE (accelerazione)
rs_1w = rar["1W"]
rs_2w = prices.apply(lambda x: ret(x,10)).sub(returns.loc[BENCHMARK,"1W"])
df["Delta_RS_5D"] = rs_1w - rs_2w

df = df.sort_values("Ra_momentum", ascending=False)
df["Classifica"] = range(1, len(df)+1)

def situazione(row):
    if row.Ra_momentum > 0:
        return "LEADER" if row.Coerenza_Trend >= 4 else "IN RECUPERO"
    return "DEBOLE"

df["Situazione"] = df.apply(situazione, axis=1)

# ========================
# UI TABS
# ========================
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Dashboard Settoriale",
    "📈 Andamento Settoriale",
    "📊 Fattori",
    "🔄 Rotazione Settoriale"
])

# ========================
# TAB 4 — ROTAZIONE SETTORIALE (RSR)
# ========================
with tab4:

    # --- RSR per timeframe ---
    rsr_1m = rsr(returns["1M"], returns.loc[BENCHMARK,"1M"])
    rsr_3m = rsr(returns["3M"], returns.loc[BENCHMARK,"3M"])
    rsr_6m = rsr(returns["6M"], returns.loc[BENCHMARK,"6M"])

    rsr_focus = (rsr_1m + rsr_3m + rsr_6m) / 3

    cyc_score = rsr_focus.loc[CYCLICALS]
    def_score = rsr_focus.loc[DEFENSIVES]

    cyc_breadth = (cyc_score > 0).sum()
    def_breadth = (def_score > 0).sum()

    cyc_pct = cyc_breadth / len(CYCLICALS) * 100
    def_pct = def_breadth / len(DEFENSIVES) * 100

    rotation_score = cyc_score.mean() - def_score.mean()

    # --- Regime ---
    if rotation_score > 1.5 and cyc_pct >= 65:
        regime = "🟢 ROTATION: RISK ON"
        bg = "#003300"
        comment = "Risk On maturo, non euforico"
    elif rotation_score < -1.5 and def_pct >= 65:
        regime = "🔴 ROTATION: RISK OFF"
        bg = "#330000"
        comment = "Fase difensiva dominante"
    else:
        regime = "🟡 ROTATION: NEUTRAL"
        bg = "#333300"
        comment = "Rotazione poco direzionale / transizione"

    # --- Box principale ---
    st.markdown(f"""
    <div style="background:{bg};padding:40px;border-radius:12px;text-align:center;margin-bottom:20px;">
        <h1>{regime}</h1>
        <h2>Rotation Score: {rotation_score:.2f}</h2>
    </div>
    """, unsafe_allow_html=True)

    # ========================
    # SPARKLINE RSR 12 MESI
    # ========================
    rsr_series = (
        compute_rotation_score_series(prices)
        if "compute_rotation_score_series" in globals()
        else None
    )

    if rsr_series is not None and not rsr_series.empty:
        cutoff = rsr_series.index.max() - pd.Timedelta(days=365)
        rsr_12m = rsr_series[rsr_series.index >= cutoff]

        fig = go.Figure()

        # Linea RSR
        fig.add_trace(go.Scatter(
            x=rsr_12m.index,
            y=rsr_12m,
            mode="lines",
            line=dict(color="white", width=2),
            name="RSR"
        ))

        # --- Range colorati ---
        fig.add_hrect(ymin=1.5, ymax=10,
                      fillcolor="green", opacity=0.15, line_width=0)
        fig.add_hrect(ymin=-1.5, ymax=1.5,
                      fillcolor="yellow", opacity=0.12, line_width=0)
        fig.add_hrect(ymin=-10, ymax=-1.5,
                      fillcolor="red", opacity=0.15, line_width=0)

        # Linee soglia
        fig.add_hline(y=1.5, line_dash="dot", line_color="#00aa00")
        fig.add_hline(y=0.0, line_dash="dot", line_color="#888888")
        fig.add_hline(y=-1.5, line_dash="dot", line_color="#aa0000")

        fig.update_layout(
            height=160,
            margin=dict(l=20, r=20, t=10, b=10),
            paper_bgcolor="#000000",
            plot_bgcolor="#000000",
            font_color="white",
            showlegend=False,
            yaxis_title="",
            xaxis_title=""
        )

        st.plotly_chart(fig, width="stretch")

    # ========================
    # DIDASCALIA TECNICA
    # ========================
    st.markdown(f"""
    <div style="background:#0d0d0d;padding:25px;border-radius:10px;font-size:1.05em;line-height:1.6;">

    <b>Interpretazione quantitativa</b><br>
    Il Rotation Score misura, in punti percentuali, la differenza di performance relativa
    media tra settori ciclici e difensivi sui timeframe 1M–3M–6M.
    Valori &gt; +1.5 indicano sovraperformance dei ciclici (regime Risk On),
    valori &lt; −1.5 leadership difensiva (Risk Off),
    mentre l’area compresa tra −1.5 e +1.5 segnala una fase di rotazione neutrale o di transizione.

    <br><br>

    <b>Breadth settoriale</b><br>
    Cyclicals in leadership: <b>{cyc_breadth}/{len(CYCLICALS)}</b> ({cyc_pct:.0f}%)<br>
    Defensives in leadership: <b>{def_breadth}/{len(DEFENSIVES)}</b> ({def_pct:.0f}%)

    <br><br>

    <b>Lettura corrente</b><br>
    {rotation_score:.2f} → <b>{comment}</b><br>
    L’ampiezza del valore indica la forza della leadership,
    mentre la stabilità della linea nel tempo ne misura la persistenza.

    </div>
    """, unsafe_allow_html=True)
