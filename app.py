import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# Configurazione interfaccia
st.set_page_config(page_title="ETF Sector Monitor", layout="wide")

st.title("📊 Monitor Settoriale Strategico")
st.markdown("---")

# URL del tuo foglio
url = "https://docs.google.com/spreadsheets/d/15Z2njJ4c8ztxE97JTgrbaWAmRExojNEpxkWdKIACu0Q/edit?gid=42115566#gid=42115566"

conn = st.connection("gsheets", type=GSheetsConnection)

try:
    # 1. Carichiamo tutto il foglio senza intestazioni predefinite
    df_raw = conn.read(spreadsheet=url, header=None)

    # 2. Troviamo la riga dove si trova la parola "Ticker"
    # Cerchiamo la riga che contiene i nomi delle colonne
    header_row = 0
    for i, row in df_raw.iterrows():
        if "Ticker" in row.values:
            header_row = i
            break
    
    # Reimpostiamo il dataframe partendo dalla riga corretta
    df = df_raw.iloc[header_row:].copy()
    df.columns = df.iloc[0] # Imposta la riga trovata come intestazione
    df = df[1:] # Rimuove la riga dell'intestazione dai dati

    # 3. Pulizia e selezione colonne (Sostituisci i nomi se diversi sul foglio)
    # Usiamo nomi parziali per evitare errori di spazi o caratteri speciali
    cols = df.columns.tolist()
    
    # Cerchiamo le colonne che ci servono basandoci su parole chiave
    col_ticker = [c for c in cols if 'Ticker' in str(c)][0]
    col_situa = [c for c in cols if 'Situazione' in str(c)][0]
    col_delta = [c for c in cols if 'Δ-RS' in str(c) or 'Delta' in str(c)][0]
    col_op = [c for c in cols if 'Operatività' in str(c)][0]

    df_monitor = df[[col_ticker, col_situa, col_delta, col_op]].dropna(subset=[col_ticker])

    # 4. Funzione Colori
    def color_operativita(val):
        v = str(val).upper()
        if 'ACCUMULA' in v: color = '#2ecc71'
        elif 'ALERT BUY' in v: color = '#3498db'
        elif 'EVITA' in v: color = '#e74c3c'
        elif 'OSSERVA' in v: color = '#f1c40f'
        else: color = 'transparent'
        return f'background-color: {color}; color: black; font-weight: bold'

    # 5. Visualizzazione
    st.subheader("Segnali Operativi Real-Time")
    st.dataframe(
        df_monitor.style.applymap(color_operativita, subset=[col_op]),
        use_container_width=True,
        hide_index=True,
        height=600
    )

except Exception as e:
    st.error(f"Errore durante l'elaborazione dei dati: {e}")
    st.info("Nota: Assicurati che nel foglio Google la colonna si chiami esattamente 'Ticker'.")
