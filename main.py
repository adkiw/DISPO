
import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

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
    pakrovimo_data = st.datetime_input("Pakrovimo data ir laikas", value=datetime.now())
    iskrovimo_data = st.datetime_input("Iškrovimo data ir laikas", value=datetime.now())
    pakrovimo_miestas = st.text_input("Pakrovimo miestas")
    iskrovimo_miestas = st.text_input("Iškrovimo miestas")
    kilometrai = st.number_input("Kilometrai", min_value=0)
    frachtas = st.number_input("Frachtas (€)", min_value=0.0, format="%.2f")
    submit = st.form_submit_button("Įrašyti krovinį")

if submit:
    c.execute("INSERT INTO kroviniai (pakrovimo_data_laikas, iskrovimo_data_laikas, pakrovimo_miestas, iskrovimo_miestas, kilometrai, frachtas) VALUES (?, ?, ?, ?, ?, ?)",
              (pakrovimo_data, iskrovimo_data, pakrovimo_miestas, iskrovimo_miestas, kilometrai, frachtas))
    conn.commit()
    st.success("Krovinys įrašytas!")

# Lentelės peržiūra
st.subheader("Krovinių sąrašas")
df = pd.read_sql_query("SELECT * FROM kroviniai", conn)
st.dataframe(df)
