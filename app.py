import streamlit as st
import pandas as pd

st.set_page_config(page_title="Diagnostica Dati", layout="wide")
sheet_id = "15Z2njJ4c8ztxE97JTgrbaWAmRExojNEpxkWdKIACu0Q"
base_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet="

st.title("🔍 Diagnostica Struttura Dati" )

try:
    df_set = pd.read_csv(base_url + "SETTORI")
    st.subheader("Foglio SETTORI")
    st.write("Colonne rilevate:", list(df_set.columns))
    st.write("Prime 3 righe:", df_set.head(3))
    
    df_mot = pd.read_csv(base_url + "Motore")
    st.subheader("Foglio Motore")
    st.write("Colonne rilevate:", list(df_mot.columns))
    st.write("Prime 3 righe:", df_mot.head(3))
except Exception as e:
    st.error(f"Errore: {e}")
