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
    # 1. Carichiamo i dati saltando le prime 3 righe (l'intestazione vera è alla riga 4)
    # Usiamo il foglio specifico (gid=42115566 è solitamente il primo, ma leggiamo tutto)
    df = conn.read(spreadsheet=url, header=3) 

    # 2. Selezioniamo solo le righe dei settori (da A5 a A16 nel foglio diventano 0:12 qui)
    # Prendiamo le colonne basandoci sulla loro posizione numerica se i nomi variano
    # Colonna 0 = Ticker (A), Colonna 15 = Situazione (P), Colonna 17 = Delta (R), Colonna 19 = Operatività (T)
    # Nota: Gli indici in Python partono da 0 (A=0, B=1...)
    
    # Per sicurezza, proviamo a mappare le colonne per nome basandoci sulla tua struttura
    df_monitor = df.iloc[0:12].copy() # Prende i 12 settori
    
    # Rinominiamo le colonne per essere sicuri della gestione successiva
    # Mapping basato sulla struttura del tuo foglio:
    # A=0, P=15, R=17, T=19
    df_final = pd.DataFrame({
        'ETF': df_monitor.iloc[:, 0],
        'Situazione': df_monitor.iloc[:, 15],
        'Δ-RS (5d)': df_monitor.iloc[:, 17],
        'Operatività': df_monitor.iloc[:, 19]
    })

    # 3. Funzione Colori per l'operatività
    def color_operativita(val):
        v = str(val).upper()
        if 'ACCUMULA' in v: color = '#2ecc71' # Verde
        elif 'ALERT BUY' in v: color = '#3498db' # Blu
        elif 'EVITA' in v: color = '#e74c3c' # Rosso
        elif 'OSSERVA' in v: color = '#f1c40f' # Giallo
        else: color = 'transparent'
        return f'background-color: {color}; color: black; font-weight: bold'

    # 4. Visualizzazione
    st.subheader("Segnali Operativi Settori")
    
    # Formattiamo il Delta come percentuale
    df_final['Δ-RS (5d)'] = df_final['Δ-RS (5d)'].apply(lambda x: f"{x:.2%}" if isinstance(x, (int, float)) else x)

    st.dataframe(
        df_final.style.applymap(color_operativita, subset=['Operatività']),
        use_container_width=True,
        hide_index=True,
        height=455 # Altezza ottimizzata per 12 righe
    )

    st.caption("Dati sincronizzati in tempo reale dal Financial Terminal")

except Exception as e:
    st.error(f"Errore: {e}")
    st.info("Verifica che il foglio Google non abbia subito spostamenti di colonne (A, P, R, T).")
