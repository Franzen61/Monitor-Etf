import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# 1. Configurazione Iniziale
st.set_page_config(page_title="Financial Terminal - LIVE", page_icon="📈", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1e2130; padding: 15px; border-radius: 10px; border: 1px solid #30363d; }
    </style>
    """, unsafe_allow_html=True)

# 2. Funzione di Caricamento Dati Robusta
@st.cache_data(ttl=300)
def load_live_data():
    sheet_id = "15Z2njJ4c8ztxE97JTgrbaWAmRExojNEpxkWdKIACu0Q"
    base_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet="
    
    def clean_val(val ):
        """Pulisce i numeri in formato italiano (es. 1.234,56)"""
        if pd.isna(val): return 0.0
        s = str(val).replace('.', '').replace(',', '.').replace('%', '').strip()
        try: return float(s)
        except: return 0.0

    try:
        # Caricamento Monitor
        df_mon = pd.read_csv(base_url + "Monitor%20Etfs", skiprows=6)
        # Caricamento Settori
        df_set = pd.read_csv(base_url + "SETTORI", skiprows=18)
        # Caricamento Motore
        df_mot = pd.read_csv(base_url + "Motore")
        
        return df_mon, df_set, df_mot
    except Exception as e:
        st.error(f"Errore nel recupero dati da Google Sheets: {e}")
        return None, None, None

# 3. Esecuzione App
df_mon, df_set, df_mot = load_live_data()

if df_mon is not None:
    st.sidebar.title("📊 Terminale LIVE")
    menu = st.sidebar.radio("Navigazione", ["Monitor ETFs", "Analisi Settoriale", "Serie Storiche (Motore)"])

    # --- MONITOR ETFs ---
    if menu == "Monitor ETFs":
        st.title("🎯 Monitor ETFs - Segnali LIVE")
        try:
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
        except:
            st.warning("Struttura del foglio 'Monitor Etfs' non riconosciuta.")

    # --- ANALISI SETTORIALE ---
    elif menu == "Analisi Settoriale":
        st.title("Sector Performance Analysis")
        try:
            # Assegnazione nomi colonne basata sulla posizione
            cols = ['ticker', 'Nome', 'Prezzo', 'Var_Giorno', 'Var_Sett', 'Var_Mese', 'Var_Trim', 'Var_Sem', 'Var_Ytd']
            df_s = df_set.iloc[0:11, 0:9].copy()
            df_s.columns = cols
            
            # Pulizia numerica
            df_s['Var_Giorno_Num'] = df_s['Var_Giorno'].apply(lambda x: str(x).replace(',', '.').replace('%', '')).astype(float, errors='ignore')
            
            fig = px.bar(df_s, x='ticker', y='Var_Giorno', color='ticker', title="Performance Giornaliera", template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Errore visualizzazione settori: {e}")

    # --- SERIE STORICHE (MOTORE) ---
    elif menu == "Serie Storiche (Motore)":
        st.title("Motore - Analisi Comparativa (Base 100)")
        try:
            # Pulizia Date
            df_mot['Date'] = pd.to_datetime(df_mot['Date'], errors='coerce')
            df_mot = df_mot.dropna(subset=['Date']).sort_values('Date')
            
            # Identificazione Ticker (escludiamo colonne di servizio)
            exclude = ['Date', 'Close', 'Unnamed']
            tickers = [c for c in df_mot.columns if not any(x in c for x in exclude)]
            
            sel_tickers = st.multiselect("Seleziona Settori", tickers, default=tickers[:3] if len(tickers)>3 else tickers)
            
            if sel_tickers:
                fig_ts = go.Figure()
                for t in sel_tickers:
                    # Pulizia e conversione numerica della serie
                    series = df_mot[t].astype(str).str.replace('.', '').str.replace(',', '.').astype(float, errors='coerce').dropna()
                    if not series.empty:
                        base_val = series.iloc[0]
                        normalized = (series / base_val) * 100
                        fig_ts.add_trace(go.Scatter(x=df_mot.loc[series.index, 'Date'], y=normalized, name=t, mode='lines'))
                
                fig_ts.update_layout(title="Performance Normalizzata (Base 100)", template="plotly_dark", hovermode="x unified", yaxis_title="Valore (Inizio = 100)")
                st.plotly_chart(fig_ts, use_container_width=True)
        except Exception as e:
            st.error(f"Errore nel grafico storico: {e}")

else:
    st.info("In attesa di connessione con Google Sheets...")
