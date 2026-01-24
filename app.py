import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# Configurazione interfaccia
st.set_page_config(page_title="ETF Sector Monitor", layout="wide")

st.title("📊 Monitor Settoriale Strategico")
st.markdown("---")

# 1. Connessione al foglio Google (usando l'URL che hai fornito)
url = "https://docs.google.com/spreadsheets/d/15Z2njJ4c8ztxE97JTgrbaWAmRExojNEpxkWdKIACu0Q/edit?gid=42115566#gid=42115566"

conn = st.connection("gsheets", type=GSheetsConnection)

try:
    # Lettura dati (specificando il foglio se necessario)
    df = conn.read(spreadsheet=url)

    # 2. Pulizia Dati
    # Selezioniamo solo le colonne che contano davvero per il monitor
    # Nota: Assicurati che i nomi corrispondano esattamente a quelli del foglio
    colonne_visibili = ['Ticker', 'Situazione', 'Δ-RS (5d)', 'Operatività'] 
    
    # Filtriamo il dataframe per righe che hanno un Ticker (evitiamo righe vuote)
    df_monitor = df[df['Ticker'].notna()][colonne_visibili].copy()

    # 3. Funzione per i Colori dell'Operatività
    def color_operativita(val):
        if 'ACCUMULA' in str(val):
            color = '#2ecc71' # Verde
        elif 'ALERT BUY' in str(val):
            color = '#3498db' # Blu
        elif 'EVITA' in str(val):
            color = '#e74c3c' # Rosso
        elif 'OSSERVA' in str(val):
            color = '#f1c40f' # Giallo
        else:
            color = 'transparent'
        return f'background-color: {color}; color: black; font-weight: bold'

    # 4. Visualizzazione Tabella
    st.subheader("Segnali Operativi Real-Time")
    
    # Applichiamo lo stile e mostriamo la tabella a tutta larghezza
    st.dataframe(
        df_monitor.style.applymap(color_operativita, subset=['Operatività']),
        use_container_width=True,
        hide_index=True,
        height=500
    )

    st.info("💡 Il monitor si aggiorna automaticamente ogni volta che modifichi il foglio Google.")

except Exception as e:
    st.error(f"Errore nel collegamento: {e}")
    st.warning("Verifica che il foglio Google abbia l'accesso 'Chiunque abbia il link può visualizzare' o che le credenziali siano corrette.")
