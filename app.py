import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# 1. Configurazione Pagina
st.set_page_config(page_title="Financial Terminal - LIVE", page_icon="📈", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1e2130; padding: 15px; border-radius: 10px; border: 1px solid #30363d; }
    </style>
    """, unsafe_allow_html=True)

# Funzione di pulizia universale
def to_num(val):
    if pd.isna(val): return 0.0
    s = str(val).replace('.', '').replace(',', '.').replace('%', '').strip().upper()
    if s in ['NONE', 'NAN', '', 'NONE.']: return 0.0
    try: return float(s)
    except: return 0.0

@st.cache_data(ttl=300)
def load_live_data():
    sheet_id = "15Z2njJ4c8ztxE97JTgrbaWAmRExojNEpxkWdKIACu0Q"
    base_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet="
    try:
        # Carichiamo i fogli senza intestazioni fisse per evitare errori di slittamento
        df_set = pd.read_csv(base_url + "SETTORI", header=None )
        df_mot = pd.read_csv(base_url + "Motore", header=None)
        df_fat = pd.read_csv(base_url + "Fattori", header=None)
        return df_set, df_mot, df_fat
    except Exception as e:
        st.error(f"Errore caricamento: {e}")
        return None, None, None

df_set_raw, df_mot_raw, df_fat_raw = load_live_data()

if df_set_raw is not None:
    st.sidebar.title("📊 Terminale LIVE")
    menu = st.sidebar.radio("Navigazione", ["Monitor Settori", "Analisi Fattori", "Serie Storiche (Motore)"])

    # --- MONITOR SETTORI ---
    if menu == "Monitor Settori":
        st.title("🎯 Monitor Settori - Bloomberg Style")
        # Estraiamo i dati basandoci sulla posizione fisica (A=0, H=7, I=8, J=9, K=10, L=11)
        # Saltiamo le prime righe se necessario (usiamo la riga 19 come intestazione se è lì che iniziano i dati)
        df_m = df_set_raw.iloc[18:30].copy() # Intervallo A19:M30 (che corrisponde a A1:M12 del tuo monitor)
        df_m.columns = ['Ticker', 'Rar Day', 'Rar Week', 'Rar Month', 'Rar Q', 'Rar 6M', 'Rar Y', 'Momentum', 'Coerenza', 'Classifica', 'Delta', 'Situazione', 'Operatività', 'Trend']
        
        df_display = df_m[['Ticker', 'Momentum', 'Coerenza', 'Classifica', 'Delta', 'Situazione', 'Operatività']].copy()
        
        # Pulizia NONE
        for col in df_display.columns:
            df_display[col] = df_display[col].apply(lambda x: "" if str(x).strip().upper() in ["NONE", "NAN", "NONE."] else x)
        
        # Monitor in alto
        df_display['Mom_Num'] = df_display['Momentum'].apply(to_num)
        top_3 = df_display.sort_values('Mom_Num', ascending=False).head(3)
        cols = st.columns(3)
        for i, (idx, row) in enumerate(top_3.iterrows()):
            with cols[i]:
                st.metric(f"Leader {i+1}", row['Ticker'], f"Mom: {row['Momentum']}")

        st.subheader("Dashboard Operativa")
        st.dataframe(df_display.drop(columns=['Mom_Num']), use_container_width=True)

    # --- ANALISI FATTORI ---
    elif menu == "Analisi Fattori":
        st.title("Factor Analysis")
        df_f = df_fat_raw.iloc[1:11].copy() # Saltiamo l'intestazione
        df_f.columns = ['ticker', 'Fattori', 'Prezzo', 'Giorno', 'Sett', 'Mese', 'Trim', 'Sem', 'YTD', 'Ann', '2y', '3y', '5y', '10y']
        
        perf_cols = ['Giorno', 'Sett', 'Mese', 'Trim', 'Sem', 'YTD', 'Ann', '2y', '3y', '5y', '10y']
        for col in perf_cols:
            df_f[col] = df_f[col].apply(to_num)

        def highlight_max(s):
            is_max = s == s.max()
            return ['background-color: #004d00; color: #00ff00; font-weight: bold' if v else '' for v in is_max]

        st.dataframe(df_f.style.apply(highlight_max, subset=perf_cols).format("{:.2f}%", subset=perf_cols), use_container_width=True)

    # --- SERIE STORICHE (MOTORE) ---
    elif menu == "Serie Storiche (Motore)":
        st.title("Motore - Analisi Comparativa (Base 100)")
        df_m = df_mot_raw.copy()
        df_m.columns = df_m.iloc[0] # Usiamo la prima riga come nomi colonne
        df_m = df_m.drop(0).rename(columns={'Close': 'SPY'})
        
        df_m['Date'] = pd.to_datetime(df_m['Date'], errors='coerce')
        df_m = df_m[df_m['Date'] >= '2025-01-01'].sort_values('Date')
        
        tickers = [c for c in df_m.columns if c != 'Date' and not str(c).startswith('Unnamed')]
        sel = st.multiselect("Seleziona Asset", tickers, default=['SPY'] if 'SPY' in tickers else tickers[:1])
        
        if sel:
            fig_ts = go.Figure()
            for t in sel:
                y_vals = df_m[t].apply(to_num)
                valid = y_vals[y_vals > 0]
                if not valid.empty:
                    norm = (valid / valid.iloc[0]) * 100
                    fig_ts.add_trace(go.Scatter(x=df_m.loc[valid.index, 'Date'], y=norm, name=t, mode='lines'))
            
            fig_ts.update_layout(template="plotly_dark", hovermode="x unified", yaxis_title="Base 100")
            st.plotly_chart(fig_ts, use_container_width=True)
else:
    st.info("Connessione in corso...")
