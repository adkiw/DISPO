
import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date, time, timedelta

# DB
conn = sqlite3.connect('dispo.db', check_same_thread=False)
c = conn.cursor()

# Lentelė
c.execute("""
CREATE TABLE IF NOT EXISTS kroviniai (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
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
    busena TEXT
)
""")
conn.commit()

st.title("DISPO – Krovinių valdymas")
busenos = ["suplanuotas", "nesuplanuotas", "pakrautas", "iškrautas"]
today = date.today()
dienos_pasirinkimui = [today + timedelta(days=i) for i in range(5)]

# Sesijos paruošimas
if 'leidimas_irasyti' not in st.session_state:
    st.session_state['leidimas_irasyti'] = False
    st.session_state['laikinai_irasyti_duomenys'] = {}

def form_input():
    with st.form("forma", clear_on_submit=False):
        pakrovimo_numeris = st.text_input("Pakrovimo numeris")
        col1, col2 = st.columns(2)
        with col1:
            pakrovimo_data = st.selectbox("Pakrovimo data", dienos_pasirinkimui)
            pakrovimo_laikas_nuo = st.time_input("Laikas nuo (pakrovimo)", value=time(8, 0))
        with col2:
            iskrovimo_data = st.selectbox("Iškrovimo data", dienos_pasirinkimui)
            iskrovimo_laikas_nuo = st.time_input("Laikas nuo (iškrovimo)", value=time(8, 0))
        col3, col4 = st.columns(2)
        with col3:
            pakrovimo_laikas_iki = st.time_input("Laikas iki (pakrovimo)", value=time(17, 0))
        with col4:
            iskrovimo_laikas_iki = st.time_input("Laikas iki (iškrovimo)", value=time(17, 0))
        col5, col6 = st.columns(2)
        with col5:
            pakrovimo_salis = st.text_input("Pakrovimo šalis")
            pakrovimo_miestas = st.text_input("Pakrovimo miestas")
        with col6:
            iskrovimo_salis = st.text_input("Iškrovimo šalis")
            iskrovimo_miestas = st.text_input("Iškrovimo miestas")
        vilkikas = st.text_input("Vilkiko numeris")
        priekaba = "PR" + vilkikas[-3:] if vilkikas and len(vilkikas) >= 3 else ""
        atsakingas_vadybininkas = "vadyb_" + vilkikas.lower() if vilkikas else ""
        st.text_input("Automatiškai priskirta priekaba", value=priekaba, disabled=True)
        col7, col8 = st.columns(2)
        with col7:
            kilometrai = st.number_input("Kilometrai", min_value=0)
        with col8:
            frachtas = st.number_input("Frachtas (€)", min_value=0.0, format="%.2f")
        svoris = st.number_input("Svoris (kg)", min_value=0)
        busena = st.selectbox("Būsena", busenos)
        submit = st.form_submit_button("Įrašyti krovinį")
    return submit, locals()

submit, data = form_input()

if submit or st.session_state['leidimas_irasyti']:
    pakrovimo_numeris = data['pakrovimo_numeris']
    pakrovimo_data = data['pakrovimo_data']
    iskrovimo_data = data['iskrovimo_data']

    if pakrovimo_data > iskrovimo_data:
        st.error("Pakrovimo data negali būti vėlesnė nei iškrovimo!")
    else:
        c.execute("SELECT COUNT(*) FROM kroviniai WHERE pakrovimo_numeris = ?", (pakrovimo_numeris,))
        count = c.fetchone()[0]

        if count > 0 and not st.session_state['leidimas_irasyti']:
            st.warning("Toks pakrovimo numeris jau yra. Ar tikrai norite įrašyti dar kartą?")
            st.session_state['laikinai_irasyti_duomenys'] = data
            if st.button("Taip, įrašyti vistiek"):
                st.session_state['leidimas_irasyti'] = True
                st.rerun()
            elif st.button("Ne, atšaukti"):
                st.success("Įrašymas atšauktas.")
        else:
            d = st.session_state['laikinai_irasyti_duomenys'] if st.session_state['leidimas_irasyti'] else data
            c.execute("INSERT INTO kroviniai (pakrovimo_numeris, pakrovimo_data, pakrovimo_laikas_nuo, pakrovimo_laikas_iki, iskrovimo_data, iskrovimo_laikas_nuo, iskrovimo_laikas_iki, pakrovimo_salis, pakrovimo_miestas, iskrovimo_salis, iskrovimo_miestas, vilkikas, priekaba, atsakingas_vadybininkas, kilometrai, frachtas, svoris, busena) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (
                d['pakrovimo_numeris'], str(d['pakrovimo_data']), str(d['pakrovimo_laikas_nuo']), str(d['pakrovimo_laikas_iki']),
                str(d['iskrovimo_data']), str(d['iskrovimo_laikas_nuo']), str(d['iskrovimo_laikas_iki']),
                d['pakrovimo_salis'], d['pakrovimo_miestas'], d['iskrovimo_salis'], d['iskrovimo_miestas'],
                d['vilkikas'], "PR" + d['vilkikas'][-3:] if d['vilkikas'] and len(d['vilkikas']) >= 3 else "",
                "vadyb_" + d['vilkikas'].lower() if d['vilkikas'] else "",
                d['kilometrai'], d['frachtas'], d['svoris'], d['busena']
            ))
            conn.commit()
            st.success("Krovinys įrašytas!")
            st.session_state['leidimas_irasyti'] = False
            st.session_state['laikinai_irasyti_duomenys'] = {}

# Rodymas
st.subheader("Krovinių sąrašas")
df = pd.read_sql_query("SELECT * FROM kroviniai", conn)

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
