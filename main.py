
import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date

# Prisijungimas prie SQLite bazės
conn = sqlite3.connect('dispo.db', check_same_thread=False)
c = conn.cursor()

# Sukuriam lentelę jei dar nėra
c.execute("""
CREATE TABLE IF NOT EXISTS kroviniai (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pakrovimo_data_laikas TEXT,
    iskrovimo_data_laikas TEXT,
    pakrovimo_miestas TEXT,
    iskrovimo_miestas TEXT,
    kilometrai INTEGER,
    frachtas REAL
)
""")
conn.commit()

st.title("DISPO – Krovinių valdymas")

# Įvedimo forma
with st.form("krovinio_forma"):
    pakrovimo_data = st.date_input("Pakrovimo data", value=date.today())
    pakrovimo_laikas = st.time_input("Pakrovimo laikas", value=datetime.now().time())
    iskrovimo_data = st.date_input("Iškrovimo data", value=date.today())
    iskrovimo_laikas = st.time_input("Iškrovimo laikas", value=datetime.now().time())
    pakrovimo_miestas = st.text_input("Pakrovimo miestas")
    iskrovimo_miestas = st.text_input("Iškrovimo miestas")
    kilometrai = st.number_input("Kilometrai", min_value=0)
    frachtas = st.number_input("Frachtas (€)", min_value=0.0, format="%.2f")
    submit = st.form_submit_button("Įrašyti krovinį")

if submit:
    pakrovimo_data_laikas = f"{pakrovimo_data} {pakrovimo_laikas}"
    iskrovimo_data_laikas = f"{iskrovimo_data} {iskrovimo_laikas}"
    c.execute("INSERT INTO kroviniai (pakrovimo_data_laikas, iskrovimo_data_laikas, pakrovimo_miestas, iskrovimo_miestas, kilometrai, frachtas) VALUES (?, ?, ?, ?, ?, ?)",
              (pakrovimo_data_laikas, iskrovimo_data_laikas, pakrovimo_miestas, iskrovimo_miestas, kilometrai, frachtas))
    conn.commit()
    st.success("Krovinys įrašytas!")

# Lentelės peržiūra
st.subheader("Krovinių sąrašas")
df = pd.read_sql_query("SELECT * FROM kroviniai", conn)
st.dataframe(df)
