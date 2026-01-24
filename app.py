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

# Stile Custom
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

@st.cache_data(ttl=300)
def load_data_from_gsheets():
    sheet_id = "15Z2njJ4c8ztxE97JTgrbaWAmRExojNEpxkWdKIACu0Q"
    base_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet="
    
    # Caricamento Monitor
    df_monitor = pd.read_csv(base_url + "Monitor%20Etfs", skiprows=6 )
    
    # Caricamento Settori - Usiamo i nomi delle colonne basandoci sulla posizione per evitare errori
    df_settori = pd.read_csv(base_url + "SETTORI", skiprows=18)
    if not df_settori.empty:
        df_settori.columns = ['ticker', 'Nome', 'Prezzo', 'Var_Giorno', 'Var_Sett', 'Var_Mese', 'Var_Trim', 'Var_Sem', 'Var_Ytd', 'Var_Ann', 'Var_2y', 'Var_3y', 'Var_5y', 'Var_10y'] + list(df_settori.columns[14:])
    
    # Caricamento Motore
    df_motore = pd.read_csv(base_url + "Motore")
    df_motore['Date'] = pd.to_datetime(df_motore['Date'], errors='coerce')
    df_motore = df_motore.dropna(subset=['Date']).sort_values('Date')
    
    # Convertiamo tutte le colonne dei prezzi in numeri (gestendo la virgola italiana)
    for col in df_motore.columns:
        if col != 'Date':
            df_motore[col] = pd.to_numeric(df_motore[col].astype(str).str.replace(',', '.'), errors='coerce')
            
    return df_monitor, df_settori, df_motore

try:
    df_monitor, df_settori, df_motore = load_data_from_gsheets()

    # Sidebar
    st.sidebar.title("📊 Terminale LIVE")
    st.sidebar.success("Connesso a Google Sheets")
    
    menu = st.sidebar.radio("Navigazione", ["Monitor ETFs", "Analisi Settoriale", "Serie Storiche (Motore)"])

    if menu == "Monitor ETFs":
        st.title("🎯 Monitor ETFs - Segnali LIVE")
        monitor_display = df_monitor.iloc[0:12, [0, 1, 8, 9, 10, 11, 12]].copy()
        monitor_display.columns = ['Ticker', 'Rar Day', 'Coerenza Trend', 'Classifica', 'Delta-RS', 'Situazione', 'Operatività']
        
        for col in ['Rar Day', 'Delta-RS']:
            monitor_display[col] = pd.to_numeric(monitor_display[col].astype(str).str.replace(',', '.'), errors='coerce')

        col1, col2, col3, col4 = st.columns(4)
        with col1: st.metric("Market Sentiment", "Rally Sano", "Bullish")
        with col2: st.metric("Top Sector", "XLE", "+0.53%")
        with col3: st.metric("Leader", "Energy", "XLE")
        with col4: st.metric("Laggard", "Utilities", "XLU")

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
            use_container_width=True, height=450
        )

    elif menu == "Analisi Settoriale":
        st.title("Sector Performance Analysis")
        df_s = df_settori.iloc[0:11].copy()
        # Pulizia dati numerici per i grafici
        df_s['Var_Giorno'] = pd.to_numeric(df_s['Var_Giorno'].astype(str).str.replace(',', '.').str.replace('%', ''), errors='coerce')
        df_s['Var_Ytd'] = pd.to_numeric(df_s['Var_Ytd'].astype(str).str.replace(',', '.').str.replace('%', ''), errors='coerce')
        
        fig = px.bar(df_s, x='ticker', y='Var_Giorno', 
                     title="Performance Giornaliera (%)",
                     color='Var_Giorno', color_continuous_scale='RdYlGn', template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)
        
        fig_ytd = px.bar(df_s, x='ticker', y='Var_Ytd', title="Performance YTD (%)", template="plotly_dark")
        st.plotly_chart(fig_ytd, use_container_width=True)

    elif menu == "Serie Storiche (Motore)":
        st.title("Motore - Analisi Comparativa (Base 100)")
        st.write("I prezzi sono normalizzati a 100 alla data di partenza per confrontare la performance reale.")
        
        exclude = ['Date', 'Close']
        tickers = [c for c in df_motore.columns if c not in exclude and not c.startswith('Unnamed')]
        selected_tickers = st.multiselect("Seleziona Settori", tickers, default=['XLK', 'XLE', 'XLF'])
        
        if selected_tickers:
            fig_ts = go.Figure()
            for t in selected_tickers:
                # Normalizzazione: (Prezzo / Primo Prezzo Disponibile) * 100
                first_price = df_motore[t].dropna().iloc[0]
                normalized_series = (df_motore[t] / first_price) * 100
                
                fig_ts.add_trace(go.Scatter(x=df_motore['Date'], y=normalized_series, name=t, mode='lines'))
            
            fig_ts.update_layout(
                title="Andamento Relativo (Base 100)",
                template="plotly_dark",
                xaxis_title="Data",
                yaxis_title="Performance Normalizzata",
                hovermode="x unified"
            )
            st.plotly_chart(fig_ts, use_container_width=True)

except Exception as e:
    st.error(f"Errore: {e}")
