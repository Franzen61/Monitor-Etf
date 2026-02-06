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
.rotation-box {
    text-align:center;
    padding:40px;
    border-radius:12px;
    font-size:32px;
    font-weight:bold;
}
</style>
""", unsafe_allow_html=True)

# ========================
# TICKERS
# ========================
SECTORS = ["XLK","XLY","XLF","XLC","XLV","XLP","XLI","XLE","XLB","XLU","XLRE"]
BENCHMARK = "SPY"
ALL_TICKERS = SECTORS + [BENCHMARK]

CYCLICAL = ["XLK","XLY","XLF","XLI","XLB","XLE"]
DEFENSIVE = ["XLV","XLP","XLU","XLRE"]

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

def rsr(asset_ret, benchmark_ret):
    return ((1 + asset_ret/100) / (1 + benchmark_ret/100) - 1) * 100

# ========================
# ROTATION SCORE SERIES
# ========================
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

rsr_df = pd.DataFrame(index=returns.index, columns=returns.columns)
for col in returns.columns:
    rsr_df[col] = rsr(returns[col], returns.loc[BENCHMARK, col])

df = rsr_df.loc[SECTORS].copy()

df["Ra_momentum"] = (
    df["1M"]*WEIGHTS["1M"] +
    df["3M"]*WEIGHTS["3M"] +
    df["6M"]*WEIGHTS["6M"]
)

df["Coerenza_Trend"] = df[["1D","1W","1M","3M","6M"]].gt(0).sum(axis=1)
df["Delta_RS_5D"] = df["1W"]
df = df.sort_values("Ra_momentum", ascending=False)
df["Classifica"] = range(1, len(df)+1)

def situazione(row):
    if row.Ra_momentum > 0:
        return "LEADER" if row.Coerenza_Trend >= 4 else "IN RECUPERO"
    return "DEBOLE"

df["Situazione"] = df.apply(situazione, axis=1)

def operativita(row):
    if row["Delta_RS_5D"] > 0.02 and row["Situazione"] == "NEUTRAL":
        return "ALERT"
    if row["Classifica"] <= 3 and row["Coerenza_Trend"] >= 4 and row["Delta_RS_5D"] > 0:
        return "BOUGHT"
    if row["Classifica"] <= 3 and row["Coerenza_Trend"] >= 4:
        return "HOLD"
    if row["Classifica"] > 3 and row["Coerenza_Trend"] >= 4:
        return "OSSERVA"
    return "EVITA"

df["Operatività"] = df.apply(operativita, axis=1)

# ========================
# TAB 4 — ROTAZIONE SETTORIALE
# ========================
with st.tab("🔄 Rotazione Settoriale"):

    CYCLICALS = ["XLK","XLY","XLF","XLI","XLE","XLB"]
    DEFENSIVES = ["XLP","XLV","XLU","XLRE"]

    rar_focus = rsr_df[["1M","3M","6M"]].mean(axis=1)

    cyc_score = rar_focus.loc[CYCLICALS]
    def_score = rar_focus.loc[DEFENSIVES]

    cyc_breadth = (cyc_score > 0).sum()
    def_breadth = (def_score > 0).sum()

    cyc_pct = cyc_breadth / len(CYCLICALS) * 100
    def_pct = def_breadth / len(DEFENSIVES) * 100

    rotation_score = cyc_score.mean() - def_score.mean()

    if rotation_score > 1.5 and cyc_pct >= 65:
        regime = "ROTATION: RISK ON"
        bg = "#003300"
        comment = "Risk On maturo, non euforico"
    elif rotation_score < -1.5 and def_pct >= 65:
        regime = "ROTATION: RISK OFF"
        bg = "#330000"
        comment = "Fase difensiva dominante"
    else:
        regime = "ROTATION: NEUTRAL"
        bg = "#333300"
        comment = "Rotazione poco direzionale / transizione"

    st.markdown(f"""
    <div style="background:{bg};padding:20px 40px;border-radius:12px;text-align:center;">
        <h2>{regime}</h2>
        <h3>Rotation Score: {rotation_score:.2f}</h3>
    </div>
    """, unsafe_allow_html=True)

    # ---------- BLOCCO SPIEGAZIONE ----------
    st.markdown("""
    <h3 style="color:#ff9900;">Come si Calcola il Rotation Score</h3>
    Il Rotation Score misura la forza relativa tra settori Ciclici e Difensivi rispetto allo SPY.
    """, unsafe_allow_html=True)

    # ---------- SITUAZIONE ATTUALE ----------
    st.markdown(f"""
    <h3 style="color:#ff9900;">Situazione Attuale</h3>

    <div style="background:#1a1a1a;padding:15px;border-radius:8px;">
    <b>Rotation Score:</b> {rotation_score:.2f} → <b>{comment}</b><br><br>

    Cyclicals leadership: <b>{cyc_breadth}/{len(CYCLICALS)}</b> ({cyc_pct:.0f}%)<br>
    Defensives leadership: <b>{def_breadth}/{len(DEFENSIVES)}</b> ({def_pct:.0f}%)
    </div>
    """, unsafe_allow_html=True)
