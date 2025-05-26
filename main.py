
import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date, time, timedelta

conn = sqlite3.connect('dispo_new.db', check_same_thread=False)
c = conn.cursor()

# Pridėti naują stulpelį, jei dar nėra
try:
    c.execute("ALTER TABLE kroviniai ADD COLUMN paleciu_skaicius INTEGER")
    conn.commit()
except:
    pass  # Jei jau pridėtas, ignoruojame klaidą

# Lentelė su tvarkinga stulpelių tvarka
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
conn.commit()

st.title("DISPO – Krovinių valdymas")

with st.form("forma", clear_on_submit=False):
    col0a, col0b = st.columns(2)
    klientas = col0a.text_input("Klientas")
    uzsakymo_numeris = col0b.text_input("Užsakymo numeris")

    pakrovimo_numeris = st.text_input("Pakrovimo numeris")

    col1, col2 = st.columns(2)
    pakrovimo_data = col1.date_input("Pakrovimo data", value=date.today())
    pakrovimo_laikas_nuo = col1.time_input("Laikas nuo (pakrovimo)", value=time(8, 0))
    iskrovimo_data = col2.date_input("Iškrovimo data", value=pakrovimo_data + timedelta(days=1))
    iskrovimo_laikas_nuo = col2.time_input("Laikas nuo (iškrovimo)", value=time(8, 0))

    col3, col4 = st.columns(2)
    pakrovimo_laikas_iki = col3.time_input("Laikas iki (pakrovimo)", value=time(17, 0))
    iskrovimo_laikas_iki = col4.time_input("Laikas iki (iškrovimo)", value=time(17, 0))

    col5, col6 = st.columns(2)
    pakrovimo_salis = col5.text_input("Pakrovimo šalis")
    pakrovimo_miestas = col5.text_input("Pakrovimo miestas")
    iskrovimo_salis = col6.text_input("Iškrovimo šalis")
    iskrovimo_miestas = col6.text_input("Iškrovimo miestas")

    col7, col8 = st.columns(2)
    vilkikas = col7.text_input("Vilkiko numeris")
    priekaba = "PR" + vilkikas[-3:] if vilkikas and len(vilkikas) >= 3 else ""
    atsakingas_vadybininkas = "vadyb_" + vilkikas.lower() if vilkikas else ""
    col8.text_input("Priekaba", value=priekaba, disabled=True)

    col9, col10, col11 = st.columns(3)
    kilometrai_raw = col9.text_input("Kilometrai")
    frachtas_raw = col10.text_input("Frachtas (€)")
    svoris_raw = col11.text_input("Svoris (kg)")

    col12 = st.columns(1)[0]
    paleciu_raw = col12.text_input("Padėklų skaičius")

    busena = st.selectbox("Būsena", ["suplanuotas", "nesuplanuotas", "pakrautas", "iškrautas"])
    submit = st.form_submit_button("Įrašyti krovinį")

if submit:
    if pakrovimo_data > iskrovimo_data:
        st.error("❌ Pakrovimo data negali būti vėlesnė už iškrovimo datą.")
    elif not klientas or not uzsakymo_numeris:
        st.error("❌ Privaloma užpildyti 'Klientas' ir 'Užsakymo numeris' laukus.")
    else:
        st.error("❌ Pakrovimo data negali būti vėlesnė už iškrovimo datą.")
        else:
        try:
        kilometrai = int(kilometrai_raw)
        frachtas = float(frachtas_raw)
        svoris = int(svoris_raw)
        paleciu_skaicius = int(paleciu_raw)

        # Perspėjimas dėl uzsakymo numerio dublio
        c.execute("SELECT COUNT(*) FROM kroviniai WHERE uzsakymo_numeris = ?", (uzsakymo_numeris,))
        if c.fetchone()[0] > 0:
        st.warning("⚠️ Toks užsakymo numeris jau yra. Vis tiek įrašoma.")

        c.execute("""INSERT INTO kroviniai (
        klientas, uzsakymo_numeris, pakrovimo_numeris,
        pakrovimo_data, pakrovimo_laikas_nuo, pakrovimo_laikas_iki,
        iskrovimo_data, iskrovimo_laikas_nuo, iskrovimo_laikas_iki,
        pakrovimo_salis, pakrovimo_miestas, iskrovimo_salis, iskrovimo_miestas,
        vilkikas, priekaba, atsakingas_vadybininkas,
        kilometrai, frachtas, svoris, paleciu_skaicius, busena
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (
        klientas, uzsakymo_numeris, pakrovimo_numeris,
        str(pakrovimo_data), str(pakrovimo_laikas_nuo), str(pakrovimo_laikas_iki),
        str(iskrovimo_data), str(iskrovimo_laikas_nuo), str(iskrovimo_laikas_iki),
        pakrovimo_salis, pakrovimo_miestas, iskrovimo_salis, iskrovimo_miestas,
        vilkikas, priekaba, atsakingas_vadybininkas,
        kilometrai, frachtas, svoris, paleciu_skaicius, busena
        ))
        conn.commit()
        st.success("Krovinys įrašytas!")
        except Exception as e:
        st.error(f"Klaida įrašant: {e}")

st.subheader("Krovinių sąrašas")
df = pd.read_sql_query("SELECT * FROM kroviniai", conn)
df["Krovinio ID"] = df["id"]
df["EUR/km"] = df.apply(lambda row: round(row["frachtas"] / row["kilometrai"], 2) if row["kilometrai"] > 0 else 0, axis=1)
df["Padėklų sk."] = df["paleciu_skaicius"]
st.dataframe(df)
