
import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date

# Prisijungimas prie SQLite
conn = sqlite3.connect('dispo.db', check_same_thread=False)
c = conn.cursor()

# Lentelė
c.execute("""
CREATE TABLE IF NOT EXISTS kroviniai (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pakrovimo_numeris TEXT,
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

if 'leidimas_irasyti' not in st.session_state:
    st.session_state['leidimas_irasyti'] = False
    st.session_state['pakrovimo_numeris_temp'] = ""

with st.form("krovinio_forma", clear_on_submit=False):
    pakrovimo_numeris = st.text_input("Pakrovimo numeris", max_chars=20)

    col1, col2 = st.columns(2)
    with col1:
        pakrovimo_data = st.date_input("Pakrovimo data", value=date.today())
    with col2:
        pakrovimo_laikas = st.time_input("Pakrovimo laikas")

    col3, col4 = st.columns(2)
    with col3:
        iskrovimo_data = st.date_input("Iškrovimo data", value=date.today())
    with col4:
        iskrovimo_laikas = st.time_input("Iškrovimo laikas")

    col5, col6 = st.columns(2)
    with col5:
        pakrovimo_salis = st.text_input("Pakrovimo šalis")
    with col6:
        pakrovimo_miestas = st.text_input("Pakrovimo miestas")

    col7, col8 = st.columns(2)
    with col7:
        iskrovimo_salis = st.text_input("Iškrovimo šalis")
    with col8:
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
    pakrovimo_data_laikas = datetime.combine(pakrovimo_data, pakrovimo_laikas)
    iskrovimo_data_laikas = datetime.combine(iskrovimo_data, iskrovimo_laikas)

    pakrovimo_data_laikas_str = pakrovimo_data_laikas.strftime("%Y-%m-%d %H:%M")
    iskrovimo_data_laikas_str = iskrovimo_data_laikas.strftime("%Y-%m-%d %H:%M")

    if pakrovimo_data_laikas > iskrovimo_data_laikas:
        st.error("Pakrovimo data negali būti vėlesnė nei iškrovimo.")
    else:
        c.execute("SELECT COUNT(*) FROM kroviniai WHERE pakrovimo_numeris = ?", (pakrovimo_numeris,))
        count = c.fetchone()[0]

        if count > 0 and not (st.session_state['leidimas_irasyti'] and st.session_state['pakrovimo_numeris_temp'] == pakrovimo_numeris):
            st.warning("Toks pakrovimo numeris jau yra. Ar tikrai norite įrašyti dar kartą?")
            if st.button("Taip, įrašyti vistiek"):
                st.session_state['leidimas_irasyti'] = True
                st.session_state['pakrovimo_numeris_temp'] = pakrovimo_numeris
                st.rerun()
            elif st.button("Ne, atšaukti"):
                st.success("Krovinio įrašymas atšauktas.")
                st.session_state['leidimas_irasyti'] = False
        else:
            c.execute("INSERT INTO kroviniai (pakrovimo_numeris, pakrovimo_data_laikas, iskrovimo_data_laikas, pakrovimo_salis, pakrovimo_miestas, iskrovimo_salis, iskrovimo_miestas, vilkikas, priekaba, atsakingas_vadybininkas, kilometrai, frachtas, svoris, busena) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (
                pakrovimo_numeris, pakrovimo_data_laikas_str, iskrovimo_data_laikas_str,
                pakrovimo_salis, pakrovimo_miestas, iskrovimo_salis, iskrovimo_miestas,
                vilkikas, priekaba, atsakingas_vadybininkas, kilometrai, frachtas, svoris, busena
            ))
            conn.commit()
            st.success("Krovinys įrašytas!")
            st.session_state['leidimas_irasyti'] = False
            st.session_state['pakrovimo_numeris_temp'] = ""

# Lentelės peržiūra su rodomu ID + sufiksu
st.subheader("Krovinių sąrašas")

df = pd.read_sql_query("SELECT * FROM kroviniai", conn)

# Pridedam "rodyti_id" su -1, -2 ir eur/km
id_counts = {}
display_ids = []

for index, row in df.iterrows():
    base_id = str(row["id"])
    pakr_numeris = row["pakrovimo_numeris"]
    if pakr_numeris not in id_counts:
        id_counts[pakr_numeris] = 0
        display_ids.append(base_id)
    else:
        id_counts[pakr_numeris] += 1
        display_ids.append(f"{base_id}-{id_counts[pakr_numeris]}")

df.insert(0, "Krovinio ID", display_ids)
df["EUR/km"] = df.apply(lambda row: round(row["frachtas"] / row["kilometrai"], 2) if row["kilometrai"] > 0 else 0, axis=1)

st.dataframe(df)
