
import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date, time

# Prisijungimas prie SQLite bazės
conn = sqlite3.connect('dispo.db', check_same_thread=False)
c = conn.cursor()

# Sukuriame lentelę su visais reikalingais laukais
c.execute("""
CREATE TABLE IF NOT EXISTS kroviniai (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pakrovimo_numeris TEXT UNIQUE,
    pakrovimo_data_laikas TEXT,
    iskrovimo_data_laikas TEXT,
    pakrovimo_vieta TEXT,
    iskrovimo_vieta TEXT,
    kilometrai INTEGER,
    frachtas REAL,
    svoris INTEGER,
    busena TEXT,
    atsakingas_vadybininkas TEXT
)
""")
conn.commit()

st.title("DISPO – Krovinių valdymas")

# Pavyzdiniai miestai ir šalys
salis_options = ["LT", "LV", "PL", "EE"]
miestai_options = ["Vilnius", "Kaunas", "Klaipeda", "Ryga", "Talinas", "Varšuva"]

busenos = ["suplanuotas", "kraunamas", "iškrautas", "neplanuotas"]

# Sesijos būsena
if 'leidimas_irasyti' not in st.session_state:
    st.session_state['leidimas_irasyti'] = False

with st.form("krovinio_forma", clear_on_submit=False):
    pakrovimo_numeris = st.text_input("Pakrovimo numeris", max_chars=20)

    pakrovimo_data = st.date_input("Pakrovimo data", value=date.today())
    pakrovimo_laikas = st.time_input("Pakrovimo laikas", value=datetime.now().time())
    iskrovimo_data = st.date_input("Iškrovimo data", value=date.today())
    iskrovimo_laikas = st.time_input("Iškrovimo laikas", value=datetime.now().time())

    pakrovimo_salis = st.selectbox("Pakrovimo šalis", salis_options, index=0)
    pakrovimo_miestas = st.selectbox("Pakrovimo miestas", miestai_options, index=0)
    iskrovimo_salis = st.selectbox("Iškrovimo šalis", salis_options, index=0)
    iskrovimo_miestas = st.selectbox("Iškrovimo miestas", miestai_options, index=1)

    pakrovimo_vieta = f"{pakrovimo_salis}{pakrovimo_miestas}"
    iskrovimo_vieta = f"{iskrovimo_salis}{iskrovimo_miestas}"

    kilometrai = st.number_input("Kilometrai", min_value=0)
    frachtas = st.number_input("Frachtas (€)", min_value=0.0, format="%.2f")
    svoris = st.number_input("Svoris (kg)", min_value=0)
    busena = st.selectbox("Būsena", busenos)

    # Automatinis vadybininkas (pvz., pagal miestą)
    atsakingas_vadybininkas = "vadybininkas_" + pakrovimo_miestas.lower()

    submit = st.form_submit_button("Įrašyti krovinį")

# Apdorojimas
if submit:
    pakrovimo_data_laikas = datetime.combine(pakrovimo_data, pakrovimo_laikas)
    iskrovimo_data_laikas = datetime.combine(iskrovimo_data, iskrovimo_laikas)

    # Tikrinam ar toks pakrovimo numeris jau egzistuoja
    c.execute("SELECT * FROM kroviniai WHERE pakrovimo_numeris = ?", (pakrovimo_numeris,))
    egzistuoja = c.fetchone()

    if egzistuoja and not st.session_state['leidimas_irasyti']:
        st.warning("Toks krovinys jau įvestas. Ar tikrai norite įrašyti dar kartą?")
        if st.button("Taip, įrašyti vistiek"):
            st.session_state['leidimas_irasyti'] = True
            st.rerun()
        elif st.button("Ne, atšaukti"):
            st.session_state['leidimas_irasyti'] = False
            st.success("Įrašymas atšauktas.")
    else:
        try:
            c.execute("""
                INSERT INTO kroviniai (
                    pakrovimo_numeris, pakrovimo_data_laikas, iskrovimo_data_laikas,
                    pakrovimo_vieta, iskrovimo_vieta, kilometrai, frachtas,
                    svoris, busena, atsakingas_vadybininkas
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pakrovimo_numeris, pakrovimo_data_laikas, iskrovimo_data_laikas,
                pakrovimo_vieta, iskrovimo_vieta, kilometrai, frachtas,
                svoris, busena, atsakingas_vadybininkas
            ))
            conn.commit()
            st.success("Krovinys įrašytas!")
            st.session_state['leidimas_irasyti'] = False
        except sqlite3.IntegrityError:
            st.error("Toks pakrovimo numeris jau egzistuoja ir įrašymas nebuvo patvirtintas.")

# Lentelės peržiūra
st.subheader("Krovinių sąrašas")
df = pd.read_sql_query("SELECT * FROM kroviniai", conn)
st.dataframe(df)
