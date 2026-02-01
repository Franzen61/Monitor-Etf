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
df["Delta_RS_5D"] = df["1W"]
df = df.sort_values("Ra_momentum", ascending=False)
df["Classifica"] = range(1, len(df)+1)

def situazione(row):
    if row.Ra_momentum > 0:
        return "LEADER" if row.Coerenza_Trend >= 4 else "IN RECUPERO"
    return "DEBOLE"

df["Situazione"] = df.apply(situazione, axis=1)

# FUNZIONE OPERATIVITÀ (AGGIUNTA)
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
                <div>Operatività: {row.Operatività}</div>
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
    
    # NUOVO GRAFICO A COLONNE PER I FATTORI
    st.divider()
    st.subheader("📊 Confronto Grafico Fattori")
    
    # Selettori per i ticker e timeframe
    col1, col2 = st.columns(2)
    with col1:
        selected_factors = st.multiselect(
            "Seleziona Fattori", 
            FACTOR_ETFS, 
            default=FACTOR_COMPARISON
        )
    
    with col2:
        selected_timeframes = st.multiselect(
            "Seleziona Timeframe",
            ["1W", "1M", "3M", "6M"],
            default=["1W", "1M", "3M", "6M"]
        )
    
    if selected_factors and selected_timeframes:
        # Crea dataframe per il grafico
        chart_data = f.loc[selected_factors, selected_timeframes].T
        
        # Crea il grafico a barre
        fig2 = go.Figure()
        
        # Colori per i ticker
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2']
        
        # Aggiungi barre per ogni ticker
        for i, ticker in enumerate(selected_factors):
            # Ottieni il colore (cicla se ci sono più ticker che colori)
            color_idx = i % len(colors)
            
            # Crea array di colori per questo ticker
            ticker_colors = []
            for timeframe in selected_timeframes:
                # Controlla se questo valore è il massimo per questo timeframe
                max_val = chart_data.loc[timeframe].max()
                current_val = chart_data.loc[timeframe, ticker]
                
                # Se è il massimo (entro una tolleranza piccola per floating point)
                if abs(current_val - max_val) < 0.0001:
                    ticker_colors.append('#00FF00')  # Verde fluo
                else:
                    ticker_colors.append(colors[color_idx])
            
            fig2.add_trace(go.Bar(
                name=ticker,
                x=selected_timeframes,
                y=chart_data[ticker].values,
                marker_color=ticker_colors,
                text=chart_data[ticker].round(2).astype(str) + '%',
                textposition='outside',
                textfont=dict(color='white')
            ))
        
        # Layout del grafico (versione semplificata e corretta)
        fig2.update_layout(
            title="Confronto Performance Fattori",
            xaxis_title="Timeframe",
            yaxis_title="Rendimento %",
            barmode='group',
            paper_bgcolor="#000",
            plot_bgcolor="#000",
            font_color="white",
            height=500,
            showlegend=True
        )
        
        # Impostazioni separate per gli assi
        fig2.update_xaxes(
            tickfont=dict(size=14),
            titlefont=dict(size=16)
        )
        
        fig2.update_yaxes(
            tickfont=dict(size=14),
            titlefont=dict(size=16),
            gridcolor='#333'
        )
        
        # Impostazioni separate per la legenda
        fig2.update_layout(legend=dict(font=dict(size=12)))
        
        st.plotly_chart(fig2, use_container_width=True)
        
        # Legenda colori
        st.markdown("""
        <div style="background-color: #1a1a1a; padding: 10px; border-radius: 5px; margin-top: 10px;">
        <small>
        <strong>Legenda:</strong><br>
        • <span style="color:#00FF00">Colonna verde fluo</span>: Valore massimo per quel timeframe<br>
        • Le barre mostrano il rendimento percentuale cumulativo per ogni timeframe
        </small>
        </div>
        """, unsafe_allow_html=True)
    elif not selected_factors:
        st.warning("Seleziona almeno un fattore per visualizzare il grafico.")
