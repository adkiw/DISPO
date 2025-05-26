
import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date, time, timedelta

conn = sqlite3.connect('dispo_new.db', check_same_thread=False)
c = conn.cursor()

# Lentelių kūrimas
c.execute("""
CREATE TABLE IF NOT EXISTS kroviniai (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    klientas TEXT,
    uzsakymo_numeris TEXT,
    pakrovimo_numeris TEXT,
    pakrovimo_data TEXT,
    pakrovimo_laikas_nuo TEXT,
    pakrovimo_laikas_iki TEXT,
    iskrovimo_data TEXT,
    iskrovimo_laikas_nuo TEXT,
    iskrovimo_laikas_iki TEXT,
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
    paleciu_skaicius INTEGER,
    busena TEXT
)
""")
c.execute("""
CREATE TABLE IF NOT EXISTS vilkikai (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numeris TEXT UNIQUE,
    marke TEXT,
    pagaminimo_metai INTEGER,
    tech_apziura DATE
)
""")
c.execute("""
CREATE TABLE IF NOT EXISTS darbuotojai (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vardas TEXT,
    pavarde TEXT,
    el_pastas TEXT,
    telefonas TEXT,
    pareigybe TEXT,
    grupe TEXT
)
""")
conn.commit()

# Meniu pasirinkimas
modulis = st.sidebar.selectbox("📂 Pasirink modulį", ["Kroviniai", "Vilkikai", "Darbuotojai"])

# Esami moduliai (Kroviniai, Vilkikai) – čia trumpiname, nes neredaguojame

if modulis == "Darbuotojai":
    st.title("DISPO – Darbuotojų valdymas")

    with st.form("darbuotojo_forma", clear_on_submit=True):
        col1, col2 = st.columns(2)
        vardas = col1.text_input("Vardas")
        pavarde = col2.text_input("Pavardė")

        col3, col4 = st.columns(2)
        el_pastas = col3.text_input("El. paštas")
        telefonas = col4.text_input("Telefono numeris")

        pareigybe = st.selectbox("Pareigybė", ["Ekspeditorius", "Transporto vadybininkas", "Vadovas", "Kita"])
        grupe = st.text_input("Grupė")

        darbuotojas_submit = st.form_submit_button("💾 Įrašyti darbuotoją")

    if darbuotojas_submit:
        try:
            c.execute("""
                INSERT INTO darbuotojai (vardas, pavarde, el_pastas, telefonas, pareigybe, grupe)
                VALUES (?, ?, ?, ?, ?, ?)""",
                (vardas, pavarde, el_pastas, telefonas, pareigybe, grupe)
            )
            conn.commit()
            st.success("✅ Darbuotojas įrašytas sėkmingai!")
        except Exception as e:
            st.error(f"❌ Klaida įrašant: {e}")

    st.subheader("📋 Darbuotojų sąrašas")
    df_darbuotojai = pd.read_sql_query("SELECT * FROM darbuotojai", conn)
    st.dataframe(df_darbuotojai)
