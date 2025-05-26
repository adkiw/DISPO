
import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date, time, timedelta

st.markdown("<h1 style='text-align: center; color: #4CAF50;'>DISPO – Krovinių valdymas</h1>", unsafe_allow_html=True)

st.markdown("""
    <style>
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        font-size: 18px;
        padding: 10px 24px;
        border: none;
        border-radius: 5px;
    }
    .stTextInput>div>div>input {
        padding: 8px;
        font-size: 16px;
    }
    .stSelectbox>div>div {
        padding: 4px;
        font-size: 16px;
    }
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    </style>
""", unsafe_allow_html=True)

conn = sqlite3.connect('dispo_cleanest2.db', check_same_thread=False)
c = conn.cursor()

c.execute("DROP TABLE IF EXISTS kroviniai_cleanest")
c.execute("""
CREATE TABLE kroviniai_cleanest (
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
    paleciai INTEGER,
    busena TEXT
)
""")
conn.commit()

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

    col9, col10, col11, col12 = st.columns(4)
    kilometrai_raw = col9.text_input("Kilometrai")
    frachtas_raw = col10.text_input("Frachtas (€)")
    svoris_raw = col11.text_input("Svoris (kg)")
    paleciai_raw = col12.text_input("Padėčių skaičius")

    busena = st.selectbox("Būsena", ["suplanuotas", "nesuplanuotas", "pakrautas", "iškrautas"])
    submit = st.form_submit_button("Įrašyti krovinį")

if submit:
    if iskrovimo_data < pakrovimo_data:
        st.error("❌ Klaida: iškrovimo data negali būti ankstesnė nei pakrovimo data.")
    else:
        try:
            kilometrai = int(kilometrai_raw)
            frachtas = float(frachtas_raw)
            svoris = int(svoris_raw)
            paleciai = int(paleciai_raw)

            c.execute("SELECT COUNT(*) FROM kroviniai_cleanest WHERE uzsakymo_numeris = ?", (uzsakymo_numeris,))
            if c.fetchone()[0] > 0:
                st.warning("⚠️ Toks užsakymo numeris jau yra. Vis tiek įrašoma.")

            c.execute("INSERT INTO kroviniai_cleanest (klientas, uzsakymo_numeris, pakrovimo_numeris, pakrovimo_data, pakrovimo_laikas_nuo, pakrovimo_laikas_iki, iskrovimo_data, iskrovimo_laikas_nuo, iskrovimo_laikas_iki, pakrovimo_salis, pakrovimo_miestas, iskrovimo_salis, iskrovimo_miestas, vilkikas, priekaba, atsakingas_vadybininkas, kilometrai, frachtas, svoris, paleciai, busena) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (
                klientas, uzsakymo_numeris, pakrovimo_numeris,
                str(pakrovimo_data), str(pakrovimo_laikas_nuo), str(pakrovimo_laikas_iki),
                str(iskrovimo_data), str(iskrovimo_laikas_nuo), str(iskrovimo_laikas_iki),
                pakrovimo_salis, pakrovimo_miestas, iskrovimo_salis, iskrovimo_miestas,
                vilkikas, priekaba, atsakingas_vadybininkas,
                kilometrai, frachtas, svoris, paleciai, busena
            ))
            conn.commit()
            st.success("✅ Krovinys įrašytas!")
        except Exception as e:
            st.error(f"Klaida įrašant: {e}")

st.subheader("Krovinių sąrašas")
df = pd.read_sql_query("SELECT * FROM kroviniai_cleanest", conn)
df["Krovinio ID"] = df["id"]
df["EUR/km"] = df.apply(lambda row: round(row["frachtas"] / row["kilometrai"], 2) if row["kilometrai"] > 0 else 0, axis=1)
st.dataframe(df)
