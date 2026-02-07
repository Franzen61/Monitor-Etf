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
    if row["Delta_RS_5D"] > 0.02 and row["Situazione"] == "NEUTRAL":
        return "🔭 ALERT"
    if row["Classifica"] <= 3 and row["Coerenza_Trend"] >= 4 and row["Delta_RS_5D"] > 0:
        return "🔥 BOUGHT"
    if row["Classifica"] <= 3 and row["Coerenza_Trend"] >= 4:
        return "📈 HOLD"
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
        # Palette colori professionale per 11 settori + SPY
        colors = [
            '#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', 
            '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E2',
            '#F8B739', '#52B788', '#E76F51', '#00FF00'
        ]
        
        # Prepara dati
        tickers_list = ALL_TICKERS
        values = [returns.loc[t, "1D"] for t in tickers_list]
        bar_colors = [colors[i] for i in range(len(tickers_list))]
        
        # Crea grafico con UN SOLO trace (nessuna legenda multipla)
        fig = go.Figure(data=[
            go.Bar(
                x=tickers_list,
                y=values,
                marker=dict(
                    color=bar_colors,
                    line=dict(color='#333', width=1)
                ),
                width=0.7,
                showlegend=False
            )
        ])
        
        # Layout pulito
        fig.update_layout(
            height=300,
            paper_bgcolor="#000",
            plot_bgcolor="#000",
            font=dict(color="white", size=12),
            title=dict(
                text="Variazione % Giornaliera",
                font=dict(size=16, color="#ff9900")
            ),
            xaxis=dict(
                tickangle=0,
                gridcolor="#1a1a1a"
            ),
            yaxis=dict(
                title="",
                gridcolor="#1a1a1a",
                zeroline=True,
                zerolinecolor="#444",
                zerolinewidth=2
            ),
            margin=dict(l=40, r=20, t=50, b=40),
            bargap=0.15
        )
        
        st.plotly_chart(fig, use_container_width=True)

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
    
    # DEBUG: verifica se i dati sono stati scaricati
    if factor_prices.empty or factor_prices.isna().all().all():
        st.error("⚠️ Impossibile scaricare i dati degli ETF fattoriali da Yahoo Finance. Riprova tra qualche minuto.")
        st.info("Ticker richiesti: " + ", ".join(FACTOR_ETFS))
    else:
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
        
        def highlight_max(s):
            max_val = s.max()
            return [
                "background-color:#003300;color:#00FF00;font-weight:bold"
                if v == max_val else ""
                for v in s
            ]
        
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
    rar_focus = rsr_df[["1M","3M","6M"]].mean(axis=1)

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
    # MAIN BOX - PIÙ COMPATTO
    # ========================
    st.markdown(f"""
    <div style="
        background:{bg};
        padding:20px 40px;
        border-radius:12px;
        text-align:center;
        margin-bottom:15px;
    ">
        <h2 style="margin:0 0 8px 0;">{regime}</h2>
        <h3 style="margin:0; font-weight:normal;">Rotation Score: {rotation_score:.2f}</h3>
    </div>
    """, unsafe_allow_html=True)

    # ========================
    # ROTATION SCORE — SPARKLINE PIÙ GRANDE
    # ========================
    rotation_series = compute_rotation_score_series(prices)
    
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
        name="Rotation Score",
        fill='tozeroy',
        fillcolor='rgba(100,100,100,0.2)'
    ))

    # Linee di riferimento
    fig_rs.add_hline(y=1.5, line_dash="dot", line_color="#00AA00", 
                     annotation_text="Risk On", annotation_position="right")
    fig_rs.add_hline(y=0.0, line_dash="solid", line_color="#666666")
    fig_rs.add_hline(y=-1.5, line_dash="dot", line_color="#AA0000",
                     annotation_text="Risk Off", annotation_position="right")

    fig_rs.update_layout(
        height=280,
        margin=dict(l=40, r=40, t=20, b=40),
        paper_bgcolor="#000000",
        plot_bgcolor="#000000",
        font_color="white",
        showlegend=False,
        yaxis_title="Rotation Score",
        xaxis_title="",
        yaxis=dict(gridcolor="#222222")
    )

    st.plotly_chart(fig_rs, use_container_width=True)

    # ========================
    # DIDASCALIA ARRICCHITA
    # ========================
    st.markdown(f"""
    <div style="
        background:#0d0d0d;
        padding:25px;
        border-radius:10px;
        font-size:1.05em;
        line-height:1.7;
    ">

    <h3 style="color:#ff9900; margin-top:0;">📊 Come si Calcola il Rotation Score</h3>

    Il <b>Rotation Score</b> misura la forza relativa tra settori
    <b>Ciclici</b> e <b>Difensivi</b> rispetto al benchmark SPY.

    <ol style="margin:15px 0;">
        <li><b>Calcolo RSR medio</b>: media dei rendimenti relativi su 1M, 3M e 6M</li>
        <li><b>Performance Ciclici</b>: XLK, XLY, XLF, XLI, XLE, XLB</li>
        <li><b>Performance Difensivi</b>: XLP, XLV, XLU, XLRE</li>
        <li><b>Rotation Score</b> = Ciclici - Difensivi</li>
    </ol>

    <h3 style="color:#ff9900; margin-top:25px;">📈 Come Interpretare il Grafico</h3>

    <table style="width:100%; border-collapse:collapse; margin:15px 0;">
        <tr style="background:#1a1a1a;">
            <td style="padding:10px; border:1px solid #333;"><b>Zona</b></td>
            <td style="padding:10px; border:1px solid #333;"><b>Range</b></td>
            <td style="padding:10px; border:1px solid #333;"><b>Significato</b></td>
        </tr>
        <tr>
            <td style="padding:10px; border:1px solid #333; color:#00ff00;">🟢 RISK ON</td>
            <td style="padding:10px; border:1px solid #333;">&gt; +1.5</td>
            <td style="padding:10px; border:1px solid #333;">Ciclici dominanti</td>
        </tr>
        <tr style="background:#0a0a0a;">
            <td style="padding:10px; border:1px solid #333; color:#ffff00;">🟡 NEUTRAL</td>
            <td style="padding:10px; border:1px solid #333;">-1.5 a +1.5</td>
            <td style="padding:10px; border:1px solid #333;">Fase di transizione</td>
        </tr>
        <tr>
            <td style="padding:10px; border:1px solid #333; color:#ff0000;">🔴 RISK OFF</td>
            <td style="padding:10px; border:1px solid #333;">&lt; -1.5</td>
            <td style="padding:10px; border:1px solid #333;">Difensivi dominanti</td>
        </tr>
    </table>

    <h3 style="color:#ff9900; margin-top:25px;">🎯 Situazione Attuale</h3>
    
    st.markdown(f"""
    <div style="background:#1a1a1a; padding:15px; border-radius:8px; margin:15px 0;">
        <b>Rotation Score:</b> {rotation_score:.2f} → <b>{comment}</b><br><br>

        <b>Breadth Settoriale (conferma del regime):</b><br>
        • Cyclicals in leadership: <b>{cyc_breadth}/{len(CYCLICALS)}</b>
        ({cyc_pct:.0f}%)
        {'✅' if cyc_pct >= 65 else '⚠️'}<br>

        • Defensives in leadership: <b>{def_breadth}/{len(DEFENSIVES)}</b>
        ({def_pct:.0f}%)
        {'✅' if def_pct >= 65 else '⚠️'}
    </div>

    <h3 style="color:#ff9900; margin-top:25px;">💡 Come Usare Questo Indicatore</h3>

    <ul>
        <li>Linea in salita → rotazione Risk On</li>
        <li>Linea in discesa → rotazione Risk Off</li>
        <li>Breadth &gt;65% → regime confermato</li>
        <li>Breadth basso + score estremo → possibile inversione</li>
    </ul>

    </div>
    """, unsafe_allow_html=True)
