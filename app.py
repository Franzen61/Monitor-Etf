import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# 1. Configurazione Estetica
st.set_page_config(page_title="Financial Terminal - LIVE", page_icon="📈", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1e2130; padding: 15px; border-radius: 10px; border: 1px solid #30363d; }
    </style>
    """, unsafe_allow_html=True)

# 2. Caricamento Dati (Semplice e Diretto)
@st.cache_data(ttl=300)
def load_data():
    sheet_id = "15Z2njJ4c8ztxE97JTgrbaWAmRExojNEpxkWdKIACu0Q"
    base_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet="
    
    # Carichiamo i fogli
    df_mon = pd.read_csv(base_url + "Monitor%20Etfs", skiprows=6 )
    df_set = pd.read_csv(base_url + "SETTORI", skiprows=18)
    df_mot = pd.read_csv(base_url + "Motore")
    
    # Pulizia rapida numeri (virgola -> punto)
    for df in [df_mon, df_set, df_mot]:
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].str.replace('.', '', regex=False).str.replace(',', '.', regex=False)
    
    return df_mon, df_set, df_mot

try:
    df_mon, df_set, df_mot = load_data()

    st.sidebar.title("📊 Terminale LIVE")
    menu = st.sidebar.radio("Navigazione", ["Monitor ETFs", "Analisi Settoriale", "Serie Storiche (Motore)"])

    if menu == "Monitor ETFs":
        st.title("🎯 Monitor ETFs - Segnali LIVE")
        # Selezioniamo le colonne giuste
        mon_display = df_mon.iloc[0:12, [0, 1, 8, 9, 10, 11, 12]].copy()
        mon_display.columns = ['Ticker', 'Rar Day', 'Coerenza Trend', 'Classifica', 'Delta-RS', 'Situazione', 'Operatività']
        
        def color_op(val):
            v = str(val).upper()
            if 'BUY' in v: return 'background-color: #004d00; color: white'
            if 'EVITA' in v: return 'background-color: #4d0000; color: white'
            if 'OSSERVA' in v: return 'background-color: #4d3300; color: white'
            if 'MANTIENI' in v: return 'background-color: #002b4d; color: white'
            return ''

        st.dataframe(mon_display.style.applymap(color_op, subset=['Operatività']), use_container_width=True, height=450)

    elif menu == "Analisi Settoriale":
        st.title("Sector Performance Analysis")
        df_s = df_set.iloc[0:11, 0:10].copy()
        df_s.columns = ['ticker', 'Nome', 'Prezzo', 'Giorno', 'Sett', 'Mese', 'Trim', 'Sem', 'Ytd', 'Ann']
        
        # Grafico Performance Giornaliera
        df_s['Giorno'] = pd.to_numeric(df_s['Giorno'], errors='coerce')
        fig = px.bar(df_s, x='ticker', y='Giorno', color='Giorno', color_continuous_scale='RdYlGn', template="plotly_dark", title="Performance Giornaliera (%)")
        st.plotly_chart(fig, use_container_width=True)

    elif menu == "Serie Storiche (Motore)":
        st.title("Motore - Analisi Comparativa (Base 100)")
        df_mot['Date'] = pd.to_datetime(df_mot['Date'], errors='coerce')
        df_mot = df_mot.dropna(subset=['Date']).sort_values('Date')
        
        tickers = [c for c in df_mot.columns if c not in ['Date', 'Close'] and not c.startswith('Unnamed')]
        sel = st.multiselect("Seleziona Settori", tickers, default=tickers[:3])
        
        if sel:
            fig_ts = go.Figure()
            for t in sel:
                # Convertiamo in numero e calcoliamo Base 100
                vals = pd.to_numeric(df_mot[t], errors='coerce').dropna()
                if not vals.empty:
                    norm = (vals / vals.iloc[0]) * 100
                    fig_ts.add_trace(go.Scatter(x=df_mot.loc[vals.index, 'Date'], y=norm, name=t, mode='lines'))
            
            fig_ts.update_layout(template="plotly_dark", hovermode="x unified", yaxis_title="Performance (Inizio = 100)")
            st.plotly_chart(fig_ts, use_container_width=True)

except Exception as e:
    st.error(f"Errore: {e}")
