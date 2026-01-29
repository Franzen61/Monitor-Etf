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

def clean_num(val):
    if pd.isna(val) or str(val).strip().upper() in ['NONE', 'NAN', '', 'NONE.']: return 0.0
    s = str(val).replace('.', '').replace(',', '.').replace('%', '').strip()
    try: return float(s)
    except: return 0.0

@st.cache_data(ttl=300)
def load_live_data():
    sheet_id = "15Z2njJ4c8ztxE97JTgrbaWAmRExojNEpxkWdKIACu0Q"
    base_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet="
    try:
        # Caricamento e pulizia immediata dei nomi colonne
        df_set = pd.read_csv(base_url + "SETTORI" )
        df_set.columns = [str(c).strip() for c in df_set.columns]
        
        df_mot = pd.read_csv(base_url + "Motore")
        df_mot.columns = [str(c).strip() for c in df_mot.columns]
        
        df_fat = pd.read_csv(base_url + "Fattori")
        df_fat.columns = [str(c).strip() for c in df_fat.columns]
        
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
        # Usiamo i nomi esatti dalla diagnostica
        cols_target = ["Ticker", "Ra/momentum", "Coerenza trend", "Classifica", "Δ_RS (5d)", "Situazione", "Operatività"]
        # Verifichiamo quali esistono effettivamente
        available_cols = [c for c in cols_target if c in df_set.columns]
        df_display = df_set[available_cols].iloc[0:12].copy()
        
        # Pulizia "NONE" visiva
        for col in df_display.columns:
            df_display[col] = df_display[col].apply(lambda x: "" if str(x).strip().upper() in ["NONE", "NAN"] else x)
        
        # Monitor in alto
        if "Ra/momentum" in df_display.columns:
            df_display['Mom_Num'] = df_display['Ra/momentum'].apply(clean_num)
            top_3 = df_display.sort_values('Mom_Num', ascending=False).head(3)
            cols = st.columns(3)
            for i, (idx, row) in enumerate(top_3.iterrows()):
                with cols[i]:
                    st.metric(f"Leader {i+1}", row['Ticker'], f"Mom: {row['Ra/momentum']}")

        def style_op(val):
            v = str(val).upper()
            if 'BUY' in v: return 'color: #00ff00; font-weight: bold'
            if 'EVITA' in v: return 'color: #ff4b4b; font-weight: bold'
            return ''

        st.subheader("Dashboard Operativa")
        st.dataframe(df_display.style.applymap(style_op, subset=['Operatività'] if 'Operatività' in df_display.columns else []), use_container_width=True)

    # --- ANALISI FATTORI ---
    elif menu == "Analisi Fattori":
        st.title("Factor Analysis - Performance Highlights")
        df_f = df_fat.iloc[:10].copy()
        perf_cols = [c for c in df_f.columns if c not in [df_f.columns[0], df_f.columns[1], df_f.columns[2]]]
        
        def highlight_max(s):
            nums = s.apply(clean_num)
            is_max = (nums == nums.max()) & (nums != 0)
            return ['background-color: #004d00; color: #00ff00; font-weight: bold' if v else '' for v in is_max]

        st.dataframe(df_f.style.apply(highlight_max, subset=perf_cols), use_container_width=True)

    # --- SERIE STORICHE (MOTORE) ---
    elif menu == "Serie Storiche (Motore)":
        st.title("Motore - Analisi Comparativa (Base 100)")
        # Rinomina Close in SPY
        df_mot = df_mot.rename(columns={'Close': 'SPY'})
        
        # Gestione Date: proviamo diversi formati
        df_mot['Date'] = pd.to_datetime(df_mot['Date'], errors='coerce')
        df_mot = df_mot.dropna(subset=['Date']).sort_values('Date')
        
        # Filtro 2025
        df_mot = df_mot[df_mot['Date'] >= '2025-01-01']
        
        # Tickers validi (Intervallo A:M -> indici 1 a 12)
        all_cols = list(df_mot.columns)
        tickers = [c for c in all_cols[1:13] if not "Unnamed" in c]
        
        sel = st.multiselect("Seleziona Asset", tickers, default=['SPY'] if 'SPY' in tickers else tickers[:1])
        
        if sel:
            fig_ts = go.Figure()
            for t in sel:
                # Pulizia numerica forzata
                y_vals = df_mot[t].apply(clean_num)
                if not y_vals.empty and y_vals.iloc[0] != 0:
                    norm = (y_vals / y_vals.iloc[0]) * 100
                    fig_ts.add_trace(go.Scatter(x=df_mot['Date'], y=norm, name=t, mode='lines'))
            
            fig_ts.update_layout(template="plotly_dark", hovermode="x unified", yaxis_title="Base 100")
            st.plotly_chart(fig_ts, use_container_width=True)
else:
    st.info("Connessione in corso...")
