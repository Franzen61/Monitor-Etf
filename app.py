import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# Configurazione Pagina
st.set_page_config(
    page_title="Financial Terminal - LIVE",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Stile Custom per look Bloomberg/Reuters
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric {
        background-color: #1e2130;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #30363d;
    }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=300) # Aggiorna i dati ogni 5 minuti
def load_data_from_gsheets():
    # Link del tuo Google Sheets (formato export per pandas)
    sheet_id = "15Z2njJ4c8ztxE97JTgrbaWAmRExojNEpxkWdKIACu0Q"
    base_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet="
    
    # Caricamento fogli direttamente online
    df_monitor = pd.read_csv(base_url + "Monitor%20Etfs", skiprows=6 )
    df_settori = pd.read_csv(base_url + "SETTORI", skiprows=18)
    df_motore = pd.read_csv(base_url + "Motore")
    df_fattori = pd.read_csv(base_url + "Fattori", skiprows=12)
    
    return df_monitor, df_settori, df_motore, df_fattori

try:
    df_monitor, df_settori, df_motore, df_fattori = load_data_from_gsheets()

    # Sidebar
    st.sidebar.title("📊 Terminale LIVE")
    st.sidebar.success("Connesso a Google Sheets")
    st.sidebar.info(f"Ultimo check: {datetime.now().strftime('%H:%M:%S')}")
    
    menu = st.sidebar.radio("Navigazione", ["Monitor ETFs", "Analisi Settoriale", "Analisi Fattori", "Serie Storiche (Motore)"])

    if menu == "Monitor ETFs":
        st.title("🎯 Monitor ETFs - Segnali LIVE")
        
        # Pulizia dati Monitor (prendiamo le prime 12 righe e le colonne corrette)
        monitor_display = df_monitor.iloc[0:12, [0, 1, 8, 9, 10, 11, 12]].copy()
        monitor_display.columns = ['Ticker', 'Rar Day', 'Coerenza Trend', 'Classifica', 'Delta-RS', 'Situazione', 'Operatività']
        
        # Conversione numerica
        monitor_display['Rar Day'] = pd.to_numeric(monitor_display['Rar Day'], errors='coerce')
        monitor_display['Delta-RS'] = pd.to_numeric(monitor_display['Delta-RS'], errors='coerce')

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

        st.subheader("Classifica e Segnali in Tempo Reale")
        st.dataframe(
            monitor_display.style.applymap(color_operativita, subset=['Operatività'])
            .format({'Rar Day': '{:.2f}', 'Delta-RS': '{:.4f}'}, na_rep='-'),
            use_container_width=True,
            height=450
        )

    elif menu == "Analisi Settoriale":
        st.title("Sector Performance Analysis")
        df_s = df_settori.iloc[0:11, 0:14].copy()
        # Pulizia nomi colonne per sicurezza
        df_s.columns = [c.strip() for c in df_s.columns]
        
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
        df_f.columns = [c.strip() for c in df_f.columns]
        
        fig_f = px.line_polar(df_f, r='Variaz .%  YTD', theta='Fattori', line_close=True,
                              title="Radar Chart: Factor Performance YTD", template="plotly_dark")
        st.plotly_chart(fig_f, use_container_width=True)
        st.table(df_f[['Fattori', 'Prezzo corrente', 'Variaz .%  YTD', 'Var. % annuale']])

    elif menu == "Serie Storiche (Motore)":
        st.title("Motore - Analisi Serie Storiche")
        # Escludiamo colonne non necessarie
        exclude = ['Date', 'Close', 'Unnamed: 13', 'Unnamed: 25']
        tickers = [c for c in df_motore.columns if c not in exclude and not c.startswith('Unnamed')]
        
        selected_tickers = st.multiselect("Seleziona Settori da visualizzare", tickers, default=['XLK', 'XLE', 'XLF'])
        if selected_tickers:
            fig_ts = go.Figure()
            for t in selected_tickers:
                fig_ts.add_trace(go.Scatter(x=df_motore['Date'], y=df_motore[t], name=t, mode='lines'))
            fig_ts.update_layout(title="Andamento Storico Settori", template="plotly_dark", xaxis_title="Data")
            st.plotly_chart(fig_ts, use_container_width=True)

except Exception as e:
    st.error(f"Errore di connessione LIVE: {e}")
    st.info("Verifica che il link di Google Sheets sia impostato su 'Chiunque abbia il link può visualizzare'.")
