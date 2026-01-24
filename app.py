import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# ======================
# CONFIGURAZIONE PAGINA
# ======================
st.set_page_config(
    page_title="Market Monitor",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
.main { background-color: #0e1117; }
.stDataFrame { font-size: 13px; }
</style>
""", unsafe_allow_html=True)

# ======================
# LOAD DATI GOOGLE SHEETS
# ======================
@st.cache_data(ttl=300)
def load_data():
    sheet_id = "15Z2njJ4c8ztxE97JTgrbaWAmRExojNEpxkWdKIACu0Q"
    base = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet="

    df_settori = pd.read_csv(base + "SETTORI")
    df_monitor = pd.read_csv(base + "Monitor")
    df_motore = pd.read_csv(base + "Motore")

    # Motore: Close = SPY
    if 'Close' in df_motore.columns:
        df_motore = df_motore.rename(columns={'Close': 'SPY'})

    return df_settori, df_monitor, df_motore


df_settori, df_monitor, df_motore = load_data()

# ======================
# SIDEBAR
# ======================
st.sidebar.title("📊 Market Monitor")
st.sidebar.caption(f"Aggiornato: {datetime.now().strftime('%H:%M:%S')}")

sezione = st.sidebar.radio(
    "Sezione",
    ["Andamento Settori", "Monitor ETF", "Confronto Storico"]
)

# ======================
# SEZIONE 1 — ANDAMENTO SETTORI
# ======================
if sezione == "Andamento Settori":
    st.title("📊 Andamento Settori")

    # Selezione area dati (come da foglio)
    df = df_settori.iloc[13:26].copy()
    df.columns = [c.strip() for c in df.columns]

    df = df.set_index('ticker')

    def color_scale(val):
        try:
            v = float(val)
            if v > 0:
                return 'background-color: #004d00; color: white'
            elif v < 0:
                return 'background-color: #4d0000; color: white'
        except:
            pass
        return ''

    st.dataframe(
        df.style.applymap(color_scale),
        use_container_width=True,
        height=520
    )

# ======================
# SEZIONE 2 — MONITOR ETF
# ======================
elif sezione == "Monitor ETF":
    st.title("🎯 Monitor ETF")

    df = df_monitor.iloc[0:12].copy()

    cols = df.columns[7:13]  # H → M
    monitor = df[['Ticker'] + list(cols)]

    def color_operativita(val):
        val = str(val).upper()
        if 'BUY' in val:
            return 'background-color: #006400; color: white'
        if 'EVITA' in val:
            return 'background-color: #8B0000; color: white'
        if 'OSSERVA' in val:
            return 'background-color: #8B6508; color: white'
        return ''

    st.dataframe(
        monitor.style.applymap(color_operativita, subset=['Operatività']),
        use_container_width=True,
        height=480
    )

# ======================
# SEZIONE 3 — CONFRONTO STORICO
# ======================
elif sezione == "Confronto Storico":
    st.title("📈 Confronto Storico Settori")

    df = df_motore.copy()
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.set_index('Date')

    tickers = df.columns.tolist()
    selected = st.multiselect(
        "Seleziona ETF",
        tickers,
        default=tickers
    )

    # Normalizzazione base 100
    df_norm = df[selected] / df[selected].iloc[0] * 100

    fig = go.Figure()
    for t in selected:
        fig.add_trace(go.Scatter(
            x=df_norm.index,
            y=df_norm[t],
            name=t,
            mode='lines'
        ))

    fig.update_layout(
        template="plotly_dark",
        title="Performance Normalizzata (Base 100)",
        xaxis_title="Data",
        yaxis_title="Indice",
        legend_title="ETF"
    )

    st.plotly_chart(fig, use_container_width=True)
