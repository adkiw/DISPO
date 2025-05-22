
import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date

# Prisijungimas prie SQLite
conn = sqlite3.connect('dispo.db', check_same_thread=False)
c = conn.cursor()

# Lentelės struktūra
c.execute("""
CREATE TABLE IF NOT EXISTS kroviniai (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pakrovimo_numeris TEXT UNIQUE,
    pakrovimo_data_laikas TEXT,
    iskrovimo_data_laikas TEXT,
    pakrovimo_salis TEXT,
    pakrovimo_miestas TEXT,
    iskrovimo_salis TEXT,
    iskrovimo_miestas TEXT,
    vilkikas TEXT,
    priekaba TEXT,
    atsakingas_vadybininkas TEXT,
    kilometrai INTEGER,
    frachtas REAL,
    svoris INTEGER,
    busena TEXT
)
""")
conn.commit()

st.title("DISPO – Krovinių valdymas")

busenos = ["suplanuotas", "nesuplanuotas", "pakrautas", "iškrautas"]

with st.form("krovinio_forma", clear_on_submit=False):
    pakrovimo_numeris_original = st.text_input("Pakrovimo numeris", max_chars=20)

    pakrovimo_data = st.date_input("Pakrovimo data", value=date.today())
    pakrovimo_val = st.time_input("Pakrovimo laikas")
    iskrovimo_data = st.date_input("Iškrovimo data", value=date.today())
    iskrovimo_val = st.time_input("Iškrovimo laikas")

    pakrovimo_salis = st.text_input("Pakrovimo šalis (pvz. FR12547)")
    pakrovimo_miestas = st.text_input("Pakrovimo miestas")
    iskrovimo_salis = st.text_input("Iškrovimo šalis (pvz. LT13254)")
    iskrovimo_miestas = st.text_input("Iškrovimo miestas")

    vilkikas = st.text_input("Vilkiko numeris")
    priekaba = "PR" + vilkikas[-3:] if vilkikas and len(vilkikas) >= 3 else ""
    atsakingas_vadybininkas = "vadyb_" + vilkikas.lower() if vilkikas else ""

    kilometrai = st.number_input("Kilometrai", min_value=0)
    frachtas = st.number_input("Frachtas (€)", min_value=0.0, format="%.2f")
    svoris = st.number_input("Svoris (kg)", min_value=0)
    busena = st.selectbox("Būsena", busenos)

    submit = st.form_submit_button("Įrašyti krovinį")

if submit:
    pakrovimo_data_laikas = datetime.combine(pakrovimo_data, pakrovimo_val)
    iskrovimo_data_laikas = datetime.combine(iskrovimo_data, iskrovimo_val)

    pakrovimo_data_laikas_str = pakrovimo_data_laikas.strftime("%Y-%m-%d %H:%M")
    iskrovimo_data_laikas_str = iskrovimo_data_laikas.strftime("%Y-%m-%d %H:%M")

    if pakrovimo_data_laikas > iskrovimo_data_laikas:
        st.error("Pakrovimo data ir laikas negali būti vėlesni nei iškrovimo. Patikrink datas!")
    else:
        # Automatinis skaitmeninis sufiksas: -1, -2, -3...
        pakrovimo_numeris = pakrovimo_numeris_original
        suffix = 1
        while True:
            try:
                c.execute("""
                    INSERT INTO kroviniai (
                        pakrovimo_numeris, pakrovimo_data_laikas, iskrovimo_data_laikas,
                        pakrovimo_salis, pakrovimo_miestas, iskrovimo_salis, iskrovimo_miestas,
                        vilkikas, priekaba, atsakingas_vadybininkas,
                        kilometrai, frachtas, svoris, busena
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    pakrovimo_numeris, pakrovimo_data_laikas_str, iskrovimo_data_laikas_str,
                    pakrovimo_salis, pakrovimo_miestas, iskrovimo_salis, iskrovimo_miestas,
                    vilkikas, priekaba, atsakingas_vadybininkas,
                    kilometrai, frachtas, svoris, busena
                ))
                conn.commit()
                st.success(f"Krovinys įrašytas kaip: {pakrovimo_numeris}")
                break
            except sqlite3.IntegrityError:
                pakrovimo_numeris = f"{pakrovimo_numeris_original}-{suffix}"
                suffix += 1
                if suffix > 99:
                    st.error("Pasiekta maksimali pakartojimų riba šiam numeriui.")
                    break

# Peržiūra
st.subheader("Krovinių sąrašas")
df = pd.read_sql_query("SELECT * FROM kroviniai", conn)
st.dataframe(df)
