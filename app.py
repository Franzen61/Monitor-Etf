import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import schedule
import time
from threading import Thread

# CONFIGURAZIONE
st.set_page_config(page_title="Monitor ETF", layout="wide")

# DEFINIZIONI
BENCHMARK = 'SWDA.MI'
ETF_LIST = {
    "SWDA.MI": "MSCI World",
    "EIMI.MI": "Emerging Markets",
    "IQQH.MI": "NASDAQ 100",
    "CAC40.PA": "Francia CAC40",
    "EXSA.MI": "Euro Stoxx 50",
    "QDVS.MI": "S&P500 Value",
    "QDVX.MI": "Euro Stoxx Value",
    "IUSN.MI": "MSCI World Small Cap",
    "SGLD.MI": "Oro Fisico",
    "FTSEMIB.MI": "Italia FTSE MIB",
}
FACTOR_LIST = {
    "QUALITY": ["QDVS.MI", "QDVX.MI", "IQQH.MI"],
    "VALUE": ["QDVS.MI", "QDVX.MI"],
    "MOMENTUM": ["IQQH.MI", "CAC40.PA"],
    "SIZE": ["IUSN.MI"],
    "VOLATILITY": ["SGLD.MI", "EIMI.MI"],
}
CYCLICAL = ["IQQH.MI", "CAC40.PA", "FTSEMIB.MI", "EIMI.MI"]
DEFENSIVE = ["SGLD.MI", "EXSA.MI", "QDVS.MI"]
ALL_ETF = list(ETF_LIST.keys())

# FUNZIONI DI CALCOLO
def fetch_prices(tickers, period="2y"):
    data = yf.download(tickers, period=period, progress=False)['Adj Close']
    return data

def calculate_returns(prices, periods):
    returns = {}
    for name, days in periods.items():
        returns[name] = prices.pct_change(days) * 100
    return returns

def calculate_rsi(prices, window=14):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_ema(prices, window=200):
    return prices.ewm(span=window, adjust=False).mean()

def compute_rotation_score_series(prices):
    """Calcola lo storico del Rotation Score"""
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

# LOAD DATA
@st.cache_data(ttl=3600)
def load_data():
    prices = fetch_prices(ALL_ETF)
    returns = calculate_returns(prices, {
        "1D": 1, "1W": 5, "1M": 21, "3M": 63, "6M": 126, "1Y": 252
    })
    rsi = calculate_rsi(prices)
    ema = calculate_ema(prices)
    return prices, returns, rsi, ema

prices, returns, rsi, ema = load_data()

# INTERFACCIA
st.title("📊 Monitor ETF - Dashboard")
st.markdown("---")

# TAB 1: PANORAMICA
tab1, tab2, tab3, tab4 = st.tabs(["📈 Panoramica", "📊 ETF Singoli", "🎯 Fattori", "🔄 Rotazione"])

with tab1:
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Andamento Premi/Ribassi")
        fig = go.Figure()
        for etf in ALL_ETF[:5]:
            fig.add_trace(go.Scatter(x=prices.index, y=prices[etf], name=ETF_LIST[etf],
                                    line=dict(width=2)))
        fig.update_layout(height=400, template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("RSI Attuale")
        latest_rsi = rsi.iloc[-1]
        for etf in ["IQQH.MI", "SWDA.MI", "EIMI.MI"]:
            val = latest_rsi[etf]
            color = "red" if val > 70 else "green" if val < 30 else "gray"
            st.metric(f"{ETF_LIST[etf]}", f"{val:.1f}", delta_color="off")

with tab2:
    selected_etf = st.selectbox("Seleziona ETF", list(ETF_LIST.keys()),
                               format_func=lambda x: f"{x} - {ETF_LIST[x]}")
    
    if selected_etf:
        col1, col2, col3 = st.columns(3)
        with col1:
            current_price = prices[selected_etf].iloc[-1]
            prev_price = prices[selected_etf].iloc[-2]
            change_pct = (current_price - prev_price) / prev_price * 100
            st.metric("Prezzo Attuale", f"€{current_price:.2f}",
                     f"{change_pct:+.2f}%")
        
        with col2:
            rsi_val = rsi[selected_etf].iloc[-1]
            st.metric("RSI (14)", f"{rsi_val:.1f}")
        
        with col3:
            ema_val = ema[selected_etf].iloc[-1]
            above_ema = current_price > ema_val
            st.metric("EMA 200", f"€{ema_val:.2f}",
                     "Sopra" if above_ema else "Sotto")
        
        # Grafico prezzo
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                           vertical_spacing=0.05, row_heights=[0.7, 0.3])
        
        fig.add_trace(go.Scatter(x=prices.index, y=prices[selected_etf],
                                name="Prezzo", line=dict(color="white")),
                     row=1, col=1)
        fig.add_trace(go.Scatter(x=ema.index, y=ema[selected_etf],
                                name="EMA 200", line=dict(color="orange", dash="dash")),
                     row=1, col=1)
        
        fig.add_trace(go.Scatter(x=rsi.index, y=rsi[selected_etf],
                                name="RSI", line=dict(color="cyan"),
                                fill="tozeroy"),
                     row=2, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
        
        fig.update_layout(height=600, template="plotly_dark", showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.subheader("Performance per Fattore")
    
    # Calcola performance medie per fattore
    factor_perf = {}
    for factor, etfs in FACTOR_LIST.items():
        perf = {}
        for tf in ["1D", "1W", "1M", "3M", "6M", "1Y"]:
            perf[tf] = returns[tf][etfs].mean(axis=1).iloc[-1]
        factor_perf[factor] = perf
    
    # Crea DataFrame
    f = pd.DataFrame(factor_perf).T
    f = f[["1D", "1W", "1M", "3M", "6M", "1Y"]]
    
    # Aggiungi benchmark
    bench_row = {}
    for tf in ["1D", "1W", "1M", "3M", "6M", "1Y"]:
        bench_row[tf] = returns[tf][BENCHMARK].iloc[-1]
    f.loc["BENCH"] = bench_row
    
    # Style function originale
    def style(row):
        colors = []
        for v in row:
            if v > 0:
                colors.append("color:#00FF00")
            elif v < 0:
                colors.append("color:#FF0000")
            else:
                colors.append("color:#FFFFFF")
        return colors
    
    # Funzione per evidenziare il massimo - INTERVENTO 1
    def highlight_max_column(series):
        """Evidenzia il valore massimo in ogni colonna"""
        is_max = series == series.max()
        return ['background-color: #003300; color: #00FF00; font-weight: bold' 
                if v else '' for v in is_max]
    
    # Applica gli stili
    styled_df = f.round(2).style
    
    # Applica il colore rosso/verde per i valori
    styled_df = styled_df.apply(style, axis=1)
    
    # Applica l'evidenziazione del massimo per ogni colonna
    for col in f.columns:
        styled_df = styled_df.apply(highlight_max_column, subset=[col])
    
    # Visualizza il dataframe
    st.dataframe(
        styled_df.format("{:+.2f}%"),
        use_container_width=True
    )

with tab4:
    st.subheader("Rotazione Ciclica/Defensiva")
    
    # Calcola Rotation Score corrente
    def compute_rotation_score(prices):
        ret_1m = prices.pct_change(21).iloc[-1]
        ret_3m = prices.pct_change(63).iloc[-1]
        ret_6m = prices.pct_change(126).iloc[-1]
        
        rar_1m = ret_1m - ret_1m[BENCHMARK]
        rar_3m = ret_3m - ret_3m[BENCHMARK]
        rar_6m = ret_6m - ret_6m[BENCHMARK]
        
        rar_mean = (rar_1m + rar_3m + rar_6m) / 3
        
        cyc = rar_mean[CYCLICAL].mean()
        def_ = rar_mean[DEFENSIVE].mean()
        
        rotation_score = (cyc - def_) * 100
        return rotation_score
    
    rotation = compute_rotation_score(prices)
    
    # Main box
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if rotation > 1.5:
            status = "🟢 RISK ON"
            color = "green"
        elif rotation < -1.5:
            status = "🔴 RISK OFF"
            color = "red"
        else:
            status = "⚪ NEUTRAL"
            color = "gray"
        
        st.markdown(f"""
        <div style='text-align:center; padding:20px; border:2px solid {color};
                    border-radius:10px; background-color:#000000;'>
            <h3 style='color:{color}; margin:0;'>Rotation Score: {rotation:.2f}</h3>
            <h2 style='color:{color}; margin:10px 0;'>{status}</h2>
        </div>
        """, unsafe_allow_html=True)
    
    # SPARKLINE STORICO - INTERVENTO 2
    st.markdown("---")
    st.subheader("Andamento Storico (12 mesi)")
    
    # Calcola lo storico del Rotation Score
    rotation_series = compute_rotation_score_series(prices)
    
    # Prendi gli ultimi 12 mesi
    rotation_12m = rotation_series.last("365D")
    
    if len(rotation_12m) > 0:
        # Crea il grafico sparkline
        fig_rs = go.Figure()
        
        # Aggiungi la linea principale
        fig_rs.add_trace(go.Scatter(
            x=rotation_12m.index,
            y=rotation_12m.values,
            mode='lines',
            line=dict(color='#DDDDDD', width=2),
            fill='tozeroy',
            fillcolor='rgba(221, 221, 221, 0.1)',
            name='Rotation Score'
        ))
        
        # Aggiungi le linee di soglia
        fig_rs.add_hline(y=1.5, line_dash="dot", line_color="#006600", 
                        annotation_text="Risk On", annotation_position="bottom right")
        fig_rs.add_hline(y=0, line_dash="dash", line_color="#666666",
                        annotation_text="Neutral", annotation_position="bottom right")
        fig_rs.add_hline(y=-1.5, line_dash="dot", line_color="#660000",
                        annotation_text="Risk Off", annotation_position="bottom right")
        
        # Layout minimalista
        fig_rs.update_layout(
            height=200,
            margin=dict(l=20, r=20, t=30, b=20),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(
                showgrid=False,
                showticklabels=True,
                tickformat="%b %Y"
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor='rgba(100,100,100,0.2)',
                zeroline=True,
                zerolinecolor='rgba(100,100,100,0.5)'
            ),
            showlegend=False,
            hovermode="x unified"
        )
        
        # Nascondi bordi e rendi minimal
        fig_rs.update_xaxes(showline=False, linewidth=0)
        fig_rs.update_yaxes(showline=False, linewidth=0)
        
        st.plotly_chart(fig_rs, use_container_width=True, config={'displayModeBar': False})
    else:
        st.info("Dati insufficienti per visualizzare lo storico 12 mesi")
    
    # Didascalia dinamica
    st.markdown("---")
    if rotation > 1.5:
        st.info("✅ **Cicliche in outperformance** - Considera aumento esposizione azionaria")
    elif rotation < -1.5:
        st.warning("⚠️ **Difensive in outperformance** - Considera aumento liquidità/obbligazioni")
    else:
        st.info("⚪ **Mercato in fase neutrale** - Mantieni asset allocation di base")

# SIDEBAR
with st.sidebar:
    st.header("Impostazioni")
    update_freq = st.selectbox("Frequenza aggiornamento", ["Ogni ora", "Ogni 2 ore", "Ogni 6 ore"])
    
    st.header("Ultimo aggiornamento")
    st.write(f"{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    if st.button("Aggiorna ora"):
        st.cache_data.clear()
        st.rerun()

# NOTIFICHE (solo backend)
def check_alerts():
    # Implementazione semplificata
    pass

# Footer
st.markdown("---")
st.markdown("*Dati da Yahoo Finance | Aggiornamento ogni ora*")
