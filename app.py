import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.set_page_config(page_title="Monitor Strategico", layout="wide")

# URL del tuo foglio
url = "https://docs.google.com/spreadsheets/d/15Z2njJ4c8ztxE97JTgrbaWAmRExojNEpxkWdKIACu0Q/edit?gid=42115566#gid=42115566"
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    # Leggiamo tutto il foglio come testo puro
    df = conn.read(spreadsheet=url, header=None).astype(str)

    # Lista dei tuoi Ticker target
    tickers_target = ["XLK", "XLY", "XLC", "XLV", "XLP", "XLE", "XLF", "XLI", "XLB", "XLRE", "XLU", "SPY"]
    
    # Cerchiamo le righe che contengono questi ticker nella prima colonna (A)
    mask = df[0].isin(tickers_target)
    filtered_df = df[mask].copy()

    # Selezioniamo le colonne basandoci sulla posizione standard (A, P, R, T)
    # Ma usiamo un filtro di sicurezza per evitare l'errore "out of bounds"
    available_cols = len(filtered_df.columns)
    
    # Creiamo il dataframe finale prendendo solo quello che esiste
    display_df = pd.DataFrame()
    display_df['ETF'] = filtered_df[0]
    if available_cols > 15: display_df['Situazione'] = filtered_df[15]
    if available_cols > 17: display_df['Delta RS'] = filtered_df[17]
    if available_cols > 19: display_df['Operatività'] = filtered_df[19]

    # Stile semplice
    st.table(display_df)

except Exception as e:
    st.error(f"Sistema in pausa. Errore: {e}")
