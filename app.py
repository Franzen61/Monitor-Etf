import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# Configurazione Pagina
st.set_page_config(page_title="Financial Terminal - LIVE", page_icon="📈", layout="wide")

# Stile Custom
st.markdown("<style>.main { background-color: #0e1117; } .stMetric { background-color: #1e2130; padding: 15px; border-radius: 10px; border: 1px solid #30363d; }</style>", unsafe_allow_html=True)

@st.cache_data(ttl=300)
def load_data_from_gsheets():
    sheet_id = "15Z2njJ4c8ztxE97JTgrbaWAmRExojNEpxkWdKIACu0Q"
    base_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet="
    
    # Funzione di pulizia numeri
    def clean_num(df, columns ):
        for col in columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace('.', '').str.replace(',', '.').str.replace('%', ''), errors='coerce')
        return df

    # Caricamento Fogli
    df_monitor = pd.read_csv(base_url + "Monitor%20Etfs", skiprows=6)
    df_settori = pd.read_csv(base_url + "SETTORI", skiprows=18)
    df_motore = pd.read_csv(base_url + "Motore")
    
    # Pulizia Settori
    if not df_settori.empty:
        df_settori.columns = ['ticker', 'Nome', 'Prezzo', 'Var_Giorno', 'Var_Sett', 'Var_Mese', 'Var_Trim', 'Var_Sem', 'Var_Ytd', 'Var_Ann', 'Var_2y', 'Var_3y', 'Var_5y', 'Var_10y'] + list(df_settori.columns[14:])
        df_settori = clean_num(df_settori, ['Var_Giorno', 'Var_Ytd'])

    # Pulizia Motore
    df_motore['Date'] = pd.to_datetime(df_motore['Date'], errors='coerce')
    df_motore = df_motore.dropna(subset=['Date']).sort_values('Date')
    for col in df_motore.columns:
        if col != 'Date':
            df_motore[col] = pd.to_numeric(df_motore[col].astype(str).str.replace('.', '').str.replace(',', '.'), errors='coerce')
            
    return df_monitor, df_settori, df_motore

try:
    df_monitor, df_settori, df_motore = load_data_from_gsheets()

    st.sidebar.title("📊 Terminale LIVE")
    menu = st.sidebar.radio("Navigazione", ["Monitor ETFs", "Analisi Settoriale", "Serie Storiche (Motore)"])

    if menu == "Monitor ETFs":
        st.title("🎯 Monitor ETFs - Segnali LIVE")
        monitor_display = df_monitor.iloc[0:12, [0, 1, 8, 9, 10, 11, 12]].copy()
        monitor_display.columns = ['Ticker', 'Rar Day', 'Coerenza Trend', 'Classifica', 'Delta-RS', 'Situazione', 'Operatività']
        
        def color_operativita(val):
            v = str(val).upper()
            if 'BUY' in v: return 'background-color: #004d00; color: white'
            if 'EVITA' in v: return 'background-color: #4d0000; color: white'
            if 'OSSERVA' in v: return 'background-color: #4d3300; color: white'
            if 'MANTIENI' in v: return 'background-color: #002b4d; color: white'
            return ''

        st.dataframe(monitor_display.style.applymap(color_operativita, subset=['Operatività']), use_container_width=True)

    elif menu == "Analisi Settoriale":
        st.title("Sector Performance Analysis")
        df_s = df_settori.iloc[0:11].copy()
        st.plotly_chart(px.bar(df_s, x='ticker', y='Var_Giorno', color='Var_Giorno', color_continuous_scale='RdYlGn', template="plotly_dark"), use_container_width=True)
        st.plotly_chart(px.bar(df_s, x='ticker', y='Var_Ytd', title="Performance YTD (%)", template="plotly_dark"), use_container_width=True)

    elif menu == "Serie Storiche (Motore)":
        st.title("Motore - Analisi Comparativa (Base 100)")
        exclude = ['Date', 'Close']
        tickers = [c for c in df_motore.columns if c not in exclude and not c.startswith('Unnamed') and df_motore[c].notna().any()]
        selected_tickers = st.multiselect("Seleziona Settori", tickers, default=tickers[:3] if len(tickers)>3 else tickers)
        
        if selected_tickers:
            fig_ts = go.Figure()
            for t in selected_tickers:
                series = df_motore[t].dropna()
                if not series.empty:
                    first_price = series.iloc[0]
                    normalized = (df_motore[t] / first_price) * 100
                    fig_ts.add_trace(go.Scatter(x=df_motore['Date'], y=normalized, name=t, mode='lines'))
            fig_ts.update_layout(template="plotly_dark", hovermode="x unified", yaxis_title="Base 100")
            st.plotly_chart(fig_ts, use_container_width=True)

except Exception as e:
    st.error(f"Errore: {e}")
