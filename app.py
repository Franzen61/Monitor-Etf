import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# Configurazione Pagina
st.set_page_config(
    page_title="Financial Terminal - ETF Monitor",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Stile Custom per look Bloomberg/Reuters
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
    }
    .stMetric {
        background-color: #1e2130;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #30363d;
    }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=600)
def load_data():
    # Carichiamo il file Excel che caricherai su GitHub
    file_path = 'Settori+Fattori & Mktcap (1).xlsx'
    
    # Caricamento fogli (usiamo i nomi esatti del tuo file)
    df_monitor = pd.read_excel(file_path, sheet_name='Monitor Etfs', skiprows=6)
    df_settori = pd.read_excel(file_path, sheet_name='SETTORI', skiprows=18)
    df_motore = pd.read_excel(file_path, sheet_name='Motore')
    df_fattori = pd.read_excel(file_path, sheet_name='Fattori', skiprows=12)
    
    return df_monitor, df_settori, df_motore, df_fattori

try:
    df_monitor, df_settori, df_motore, df_fattori = load_data()

    # Sidebar
    st.sidebar.title("📊 Terminale Finanziario")
    st.sidebar.info(f"Ultimo aggiornamento: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    
    menu = st.sidebar.radio("Navigazione", ["Monitor ETFs", "Analisi Settoriale", "Analisi Fattori", "Serie Storiche (Motore)"])

    if menu == "Monitor ETFs":
        st.title("🎯 Monitor ETFs - Segnali Operativi")
        
        # Pulizia dati Monitor
        monitor_display = df_monitor.iloc[0:12, [0, 1, 8, 9, 10, 11, 12]].copy()
        monitor_display.columns = ['Ticker', 'Rar Day', 'Coerenza Trend', 'Classifica', 'Delta-RS', 'Situazione', 'Operatività']
        
        # Metriche in alto
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Market Sentiment", "Rally Sano", "Bullish")
        with col2:
            st.metric("Top Sector", "XLE", "+0.53%")
        with col3:
            st.metric("Leader", "Energy", "XLE")
        with col4:
            st.metric("Laggard", "Utilities", "XLU")

        # Tabella con formattazione
        def color_operativita(val):
            val_str = str(val).upper()
            if 'BUY' in val_str: return 'background-color: #004d00; color: white'
            if 'EVITA' in val_str: return 'background-color: #4d0000; color: white'
            if 'OSSERVA' in val_str: return 'background-color: #4d3300; color: white'
            if 'MANTIENI' in val_str: return 'background-color: #002b4d; color: white'
            return ''

        st.subheader("Classifica e Segnali")
        st.dataframe(
            monitor_display.style.applymap(color_operativita, subset=['Operatività'])
            .format({'Rar Day': '{:.2f}', 'Delta-RS': '{:.4f}'}),
            use_container_width=True,
            height=450
        )

    elif menu == "Analisi Settoriale":
        st.title("Sector Performance Analysis")
        df_s = df_settori.iloc[0:11, 0:14].copy()
        fig = px.bar(df_s, x='ticker', y='Var. % giornaliera', 
                     title="Performance Giornaliera per Settore",
                     color='Var. % giornaliera',
                     color_continuous_scale='RdYlGn',
                     template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
        
        col1, col2 = st.columns(2)
        with col1:
            fig_ytd = px.bar(df_s, x='ticker', y='Var. % Ytd', title="Performance YTD", template="plotly_dark")
            st.plotly_chart(fig_ytd, use_container_width=True)
        with col2:
            fig_ann = px.bar(df_s, x='ticker', y='Var. % annuale', title="Performance Annuale", template="plotly_dark")
            st.plotly_chart(fig_ann, use_container_width=True)

    elif menu == "Analisi Fattori":
        st.title("Factor Analysis (World)")
        df_f = df_fattori.iloc[0:7, 1:10].copy()
        fig_f = px.line_polar(df_f, r='Variaz .%  YTD ', theta='Fattori ', line_close=True,
                              title="Radar Chart: Factor Performance YTD", template="plotly_dark")
        st.plotly_chart(fig_f, use_container_width=True)
        st.table(df_f[['Fattori ', 'Prezzo corrente', 'Variaz .%  YTD ', 'Var. % annuale']])

    elif menu == "Serie Storiche (Motore)":
        st.title("Motore - Analisi Serie Storiche")
        tickers = [c for c in df_motore.columns if c not in ['Date', 'Close', 'Unnamed: 13', 'Unnamed: 25']]
        selected_tickers = st.multiselect("Seleziona Settori da visualizzare", tickers, default=['XLK', 'XLE', 'XLF'])
        if selected_tickers:
            fig_ts = go.Figure()
            for t in selected_tickers:
                fig_ts.add_trace(go.Scatter(x=df_motore['Date'], y=df_motore[t], name=t, mode='lines'))
            fig_ts.update_layout(title="Andamento Storico Settori", template="plotly_dark")
            st.plotly_chart(fig_ts, use_container_width=True)

except Exception as e:
    st.error(f"Errore nel caricamento dei dati: {e}")
    st.info("Assicurati di aver caricato il file Excel 'Settori+Fattori&Mktcap(1).xlsx' nello stesso repository.")
