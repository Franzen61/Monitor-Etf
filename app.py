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

# ========================
# RELATIVE STRENGTH RETURN (RSR)
# ========================
def rsr(asset_ret, benchmark_ret):
    return ((1 + asset_ret/100) / (1 + benchmark_ret/100) - 1) * 100


# ========================
# FUNZIONE PER SPARKLINE ROTATION SCORE
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

# ========================
# COSTRUZIONE RSR
# ========================
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
        st.plotly_chart(fig, width='stretch')

    with col2:
        for t,row in df.head(3).iterrows():
            st.markdown(f"""
            <div class="leader-box">
                <div class="leader-ticker">{t}</div>
                <div class="leader-mom">Ra Momentum: {row.Ra_momentum:.2f}</div>
                <div>Operatività: {row.Operatività}</div>
                <div>{row.Situazione}</div>
            </div>
            """, unsafe_allow_html=True)

    st.dataframe(df.round(2), width='stretch')

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
        fig.add_trace(go.Scatter(x=norm.index, y=norm[t], name=t))
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
    st.plotly_chart(fig, width='stretch')

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
    
    # INTERVENTO 1: Aggiungi funzione highlight_max
    def highlight_max(s):
        max_val = s.max()
        return [
            "background-color:#003300;color:#00FF00;font-weight:bold"
            if v == max_val else ""
            for v in s
        ]
    
    # INTERVENTO 1: Modifica il blocco finale
    st.dataframe(
        f.round(2)
        .style
        .apply(style, axis=1)
        .apply(highlight_max, subset=[c for c in f.columns if c != "Prezzo"])
        .format({"Prezzo":"{:.2f}", **{c:"{:+.2f}%" for c in f.columns if c!="Prezzo"}}),
        width='stretch'
    )

# ========================
# TAB 4 — ROTAZIONE SETTORIALE
# ========================
with tab4:

    CYCLICALS = ["XLK","XLY","XLF","XLI","XLE","XLB"]
    DEFENSIVES = ["XLP","XLV","XLU","XLRE"]

    # --- RAR medio su timeframe guida ---
    rar_focus = rar[["1M","3M","6M"]].mean(axis=1)

    cyc_score = rar_focus.loc[CYCLICALS]
    def_score = rar_focus.loc[DEFENSIVES]

    # --- Breadth ---
    cyc_breadth = (cyc_score > 0).sum()
    def_breadth = (def_score > 0).sum()

    cyc_pct = cyc_breadth / len(CYCLICALS) * 100
    def_pct = def_breadth / len(DEFENSIVES) * 100

    # --- Rotation Score ---
    rotation_score = cyc_score.mean() - def_score.mean()

    # ========================
    # REGIME LOGIC
    # ========================
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

    # ========================
    # MAIN BOX
    # ========================
    st.markdown(f"""
    <div style="
        background:{bg};
        padding:40px;
        border-radius:12px;
        text-align:center;
        margin-bottom:25px;
    ">
        <h1>{regime}</h1>
        <h2>Rotation Score: {rotation_score:.2f}</h2>
    </div>
    """, unsafe_allow_html=True)

    # ========================
    # ROTATION SCORE — SPARKLINE 12 MESI (INTERVENTO 2)
    # ========================
    rotation_series = compute_rotation_score_series(prices)
    
    # CORREZIONE: sostituzione del metodo deprecato .last("365D")
    if not rotation_series.empty:
        cutoff_date = rotation_series.index.max() - pd.Timedelta(days=365)
        rotation_12m = rotation_series[rotation_series.index >= cutoff_date]
    else:
        rotation_12m = rotation_series

    fig_rs = go.Figure()

    fig_rs.add_trace(go.Scatter(
        x=rotation_12m.index,
        y=rotation_12m,
        mode="lines",
        line=dict(color="#DDDDDD", width=2),
        name="Rotation Score"
    ))

    fig_rs.add_hline(y=1.5, line_dash="dot", line_color="#006600")
    fig_rs.add_hline(y=0.0, line_dash="dot", line_color="#666666")
    fig_rs.add_hline(y=-1.5, line_dash="dot", line_color="#660000")

    fig_rs.update_layout(
        height=140,
        margin=dict(l=20, r=20, t=10, b=10),
        paper_bgcolor="#000000",
        plot_bgcolor="#000000",
        font_color="white",
        showlegend=False,
        yaxis_title="",
        xaxis_title=""
    )

    st.plotly_chart(fig_rs, width='stretch')

    # ========================
    # DIDASCALIA DINAMICA
    # ========================
    st.markdown(f"""
    <div style="
        background:#0d0d0d;
        padding:25px;
        border-radius:10px;
        font-size:1.05em;
        line-height:1.6;
    ">

    <b>Motivo della rotazione</b><br>
    La leadership relativa tra settori ciclici e difensivi su timeframe
    1M–3M–6M definisce il regime di rischio corrente.

    <br><br>

    <b>Breadth settoriale</b><br>
    Cyclicals in leadership: <b>{cyc_breadth} / {len(CYCLICALS)}</b> ({cyc_pct:.0f}%)<br>
    Defensives in leadership: <b>{def_breadth} / {len(DEFENSIVES)}</b> ({def_pct:.0f}%)

    <br><br>
 
    <b>Lettura del Rotation Score</b><br>
    {rotation_score:.2f} → <b>{comment}</b>

    </div>
    """, unsafe_allow_html=True)    
