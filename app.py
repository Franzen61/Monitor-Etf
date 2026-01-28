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

# 2. Funzione di Caricamento Dati (Ottimizzata per fogli puliti)
@st.cache_data(ttl=300)
def load_live_data():
    sheet_id = "15Z2njJ4c8ztxE97JTgrbaWAmRExojNEpxkWdKIACu0Q"
    base_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet="
    
    def clean_df(df ):
        # Converte virgole in punti e pulisce i numeri
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].str.replace('.', '', regex=False).str.replace(',', '.', regex=False).str.replace('%', '', regex=False)
                df[col] = pd.to_numeric(df[col], errors='ignore')
        return df

    try:
        # Carichiamo i fogli (senza saltare righe se ora sono puliti dall'inizio)
        df_set = clean_df(pd.read_csv(base_url + "SETTORI"))
        df_mot = clean_df(pd.read_csv(base_url + "Motore"))
        df_fat = clean_df(pd.read_csv(base_url + "Fattori"))
        
        return df_set, df_mot, df_fat
    except Exception as e:
        st.error(f"Errore caricamento: {e}")
        return None, None, None

df_set, df_mot, df_fat = load_live_data()

if df_set is not None:
    st.sidebar.title("📊 Terminale LIVE")
    menu = st.sidebar.radio("Navigazione", ["Analisi Settoriale", "Analisi Fattori", "Serie Storiche (Motore)"])

    # --- ANALISI SETTORIALE ---
    if menu == "Analisi Settoriale":
        st.title("Sector Performance Analysis")
        # Supponendo che la colonna 0 sia il ticker e la 3 la variazione giornaliera
        df_s = df_set.iloc[:11].copy()
        ticker_col = df_s.columns[0]
        var_col = df_s.columns[3]
        
        fig = px.bar(df_s, x=ticker_col, y=var_col, color=var_col, 
                     color_continuous_scale='RdYlGn', template="plotly_dark", title="Performance Giornaliera (%)")
        st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("Dati Dettagliati Settori")
        st.dataframe(df_s, use_container_width=True)

    # --- ANALISI FATTORI ---
    elif menu == "Analisi Fattori":
        st.title("Factor Analysis")
        df_f = df_fat.iloc[:10].copy()
        st.dataframe(df_f, use_container_width=True)
        
        if len(df_f.columns) >= 4:
            fig_f = px.bar(df_f, x=df_f.columns[1], y=df_f.columns[3], title="Performance Fattori", template="plotly_dark")
            st.plotly_chart(fig_f, use_container_width=True)

    # --- SERIE STORICHE (MOTORE) ---
    elif menu == "Serie Storiche (Motore)":
        st.title("Motore - Analisi Comparativa (Base 100)")
        # Cerchiamo la colonna data
        date_col = df_mot.columns[0]
        df_mot[date_col] = pd.to_datetime(df_mot[date_col], errors='coerce')
        df_mot = df_mot.dropna(subset=[date_col]).sort_values(date_col)
        
        tickers = [c for c in df_mot.columns if c != date_col and not c.startswith('Unnamed')]
        sel = st.multiselect("Seleziona Asset", tickers, default=tickers[:3] if len(tickers)>3 else tickers)
        
        if sel:
            fig_ts = go.Figure()
            for t in sel:
                series = pd.to_numeric(df_mot[t], errors='coerce').dropna()
                if not series.empty:
                    norm = (series / series.iloc[0]) * 100
                    fig_ts.add_trace(go.Scatter(x=df_mot.loc[series.index, date_col], y=norm, name=t, mode='lines'))
            
            fig_ts.update_layout(template="plotly_dark", hovermode="x unified", yaxis_title="Performance (Inizio = 100)")
            st.plotly_chart(fig_ts, use_container_width=True)

else:
    st.info("Connessione in corso...")
