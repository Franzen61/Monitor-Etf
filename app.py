import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="ETF Sector Monitor", layout="wide")

st.title("📊 Monitor Settoriale Strategico")
st.markdown("---")

url = "https://docs.google.com/spreadsheets/d/15Z2njJ4c8ztxE97JTgrbaWAmRExojNEpxkWdKIACu0Q/edit?gid=42115566#gid=42115566"

conn = st.connection("gsheets", type=GSheetsConnection)

try:
    # 1. Leggiamo il foglio senza intestazioni per avere il controllo totale
    df = conn.read(spreadsheet=url, header=None)

    # 2. Estraiamo i dati basandoci sulle coordinate esatte del tuo foglio:
    # Riga 5 a 16 (in Python indici 4 a 16)
    # Colonna A (0), Colonna P (15), Colonna R (17), Colonna T (19)
    
    subset = df.iloc[4:16, [0, 15, 17, 19]].copy()
    
    # Rinominiamo le colonne per chiarezza
    subset.columns = ['ETF', 'Situazione', 'Δ-RS (5d)', 'Operatività']

    # 3. Funzione Colori per l'operatività
    def color_operativita(val):
        v = str(val).upper()
        if 'ACCUMULA' in v: color = '#2ecc71' # Verde
        elif 'ALERT BUY' in v: color = '#3498db' # Blu
        elif 'EVITA' in v: color = '#e74c3c' # Rosso
        elif 'OSSERVA' in v: color = '#f1c40f' # Giallo
        else: color = 'transparent'
        return f'background-color: {color}; color: black; font-weight: bold'

    # 4. Pulizia dati (trasformiamo i valori numerici in percentuale se necessario)
    def format_delta(val):
        try:
            return f"{float(val):.2%}"
        except:
            return val

    subset['Δ-RS (5d)'] = subset['Δ-RS (5d)'].apply(format_delta)

    # 5. Visualizzazione
    st.subheader("Segnali Operativi Settori")
    
    st.dataframe(
        subset.style.applymap(color_operativita, subset=['Operatività']),
        use_container_width=True,
        hide_index=True,
        height=455
    )

    st.caption("Dati estratti dalle colonne A, P, R, T del Financial Terminal")

except Exception as e:
    st.error(f"Errore tecnico: {e}")
    st.info("💡 Consiglio: Assicurati che il foglio Google non abbia colonne nascoste o eliminate tra la A e la T.")
