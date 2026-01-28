import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# 1. Configurazione Pagina e Stile Bloomberg
st.set_page_config(page_title="Financial Terminal - LIVE", page_icon="📈", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1e2130; padding: 15px; border-radius: 10px; border: 1px solid #30363d; }
    .highlight-green { color: #00ff00; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=300)
def load_live_data():
    sheet_id = "15Z2njJ4c8ztxE97JTgrbaWAmRExojNEpxkWdKIACu0Q"
    base_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet="
    
    def clean_val(val ):
        if pd.isna(val): return 0.0
        s = str(val).replace('.', '').replace(',', '.').replace('%', '').strip()
        try: return float(s)
        except: return 0.0

    try:
        # Caricamento Fogli
        df_set = pd.read_csv(base_url + "SETTORI")
        df_mot = pd.read_csv(base_url + "Motore")
        df_fat = pd.read_csv(base_url + "Fattori")
        return df_set, df_mot, df_fat
    except Exception as e:
        st.error(f"Errore caricamento: {e}")
        return None, None, None

df_set, df_mot, df_fat = load_live_data()

if df_set is not None:
    st.sidebar.title("📊 Terminale LIVE")
    menu = st.sidebar.radio("Navigazione", ["Monitor Settori", "Analisi Fattori", "Serie Storiche (Motore)"])

    # --- MONITOR SETTORI ---
    if menu == "Monitor Settori":
        st.title("🎯 Monitor Settori - Bloomberg Style")
        
        # Selezione intervallo A1:M12 (Ticker A, Momentum H, Situazione K, Operatività L)
        df_m = df_set.iloc[0:12].copy()
        # Pulizia nomi colonne per sicurezza
        df_m.columns = [f"Col_{i}" for i in range(len(df_m.columns))]
        
        # Identifichiamo le colonne basandoci sulle tue indicazioni (A=0, H=7, K=10, L=11)
        df_display = df_m[[df_m.columns[0], df_m.columns[7], df_m.columns[8], df_m.columns[9], df_m.columns[10], df_m.columns[11]]].copy()
        df_display.columns = ['Ticker', 'Momentum', 'Rar Week', 'Rar Month', 'Situazione', 'Operatività']
        
        # Convertiamo Momentum in numerico per la classifica
        df_display['Momentum_Num'] = df_display['Momentum'].apply(clean_val)
        top_3 = df_display.sort_values('Momentum_Num', ascending=False).head(3)

        # Monitor in alto (Top 3 Momentum)
        cols = st.columns(3)
        for i, (idx, row) in enumerate(top_3.iterrows()):
            with cols[i]:
                st.metric(f"Leader {i+1}", row['Ticker'], f"Mom: {row['Momentum']}")

        # Tabella Monitor
        def style_op(val):
            v = str(val).upper()
            if 'BUY' in v: return 'color: #00ff00; font-weight: bold'
            if 'EVITA' in v: return 'color: #ff4b4b; font-weight: bold'
            return ''

        st.subheader("Dashboard Operativa")
        st.dataframe(df_display.drop(columns=['Momentum_Num']).style.applymap(style_op, subset=['Operatività']), use_container_width=True)

    # --- ANALISI FATTORI ---
    elif menu == "Analisi Fattori":
        st.title("Factor Analysis - Performance Highlights")
        df_f = df_fat.iloc[:10].copy()
        
        # Funzione per evidenziare il massimo in verde
        def highlight_max(s):
            if s.dtype == object: return [''] * len(s)
            is_max = s == s.max()
            return ['background-color: #004d00; color: #00ff00; font-weight: bold' if v else '' for v in is_max]

        # Pulizia numerica per le colonne di variazione
        for col in df_f.columns[2:]:
            df_f[col] = df_f[col].apply(clean_val)

        st.dataframe(df_f.style.apply(highlight_max, subset=df_f.columns[2:]), use_container_width=True)

    # --- SERIE STORICHE (MOTORE) ---
    elif menu == "Serie Storiche (Motore)":
        st.title("Motore - Analisi Comparativa (Base 100)")
        
        # Correzione SPY e Date
        df_mot.columns = ['Date', 'SPY'] + list(df_mot.columns[2:])
        df_mot['Date'] = pd.to_datetime(df_mot['Date'], errors='coerce')
        # Filtriamo solo dal 2025
        df_mot = df_mot[df_mot['Date'] >= '2025-01-01'].sort_values('Date')
        
        tickers = [c for c in df_mot.columns if c != 'Date' and not c.startswith('Unnamed')]
        sel = st.multiselect("Seleziona Asset", tickers, default=['SPY'])
        
        if sel:
            fig_ts = go.Figure()
            for t in sel:
                series = df_mot[t].apply(clean_val)
                series = series[series > 0] # Evitiamo zeri
                if not series.empty:
                    norm = (series / series.iloc[0]) * 100
                    fig_ts.add_trace(go.Scatter(x=df_mot.loc[series.index, 'Date'], y=norm, name=t, mode='lines'))
            
            fig_ts.update_layout(template="plotly_dark", hovermode="x unified", yaxis_title="Base 100 (Start = 100)")
            st.plotly_chart(fig_ts, use_container_width=True)

except Exception as e:
    st.error(f"Errore: {e}")
