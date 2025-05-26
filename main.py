import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date, time, timedelta

conn = sqlite3.connect('dispo_new.db', check_same_thread=False)
c = conn.cursor()

# Meniu pasirinkimas
modulis = st.sidebar.selectbox("📂 Pasirink modulį", ["Kroviniai", "Vilkikai"])

# --- Duomenų bazių kūrimas ---
# Vilkikai
c.execute("""
CREATE TABLE IF NOT EXISTS vilkikai (

# Patikrinam ar vilkikai lentelėje yra stulpeliai priekaba ir vadybininkas
try:
    c.execute("ALTER TABLE vilkikai ADD COLUMN priekaba TEXT")
except:
    pass
try:
    c.execute("ALTER TABLE vilkikai ADD COLUMN vadybininkas TEXT")
except:
    pass
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numeris TEXT UNIQUE,
    marke TEXT,
    pagaminimo_metai INTEGER,
    tech_apziura DATE,
    priekaba TEXT,
    vadybininkas TEXT
)
""")

# Priekabos
c.execute("""
CREATE TABLE IF NOT EXISTS priekabos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numeris TEXT UNIQUE,
    marke TEXT,
    pagaminimo_metai INTEGER,
    tech_apziura DATE
)
""")

# Darbuotojai
c.execute("""
CREATE TABLE IF NOT EXISTS darbuotojai (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vardas TEXT,
    pavarde TEXT,
    pareigybe TEXT,
    el_pastas TEXT,
    telefonas TEXT
)
""")

conn.commit()

# --- KROVINIAI ---
if modulis == "Kroviniai":
    st.title("DISPO – Krovinių valdymas")

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
        vilkikai_sarasas = [row[0] for row in c.execute("SELECT numeris FROM vilkikai").fetchall()]
        if vilkikai_sarasas:
            vilkikas = col7.selectbox("Vilkikas", vilkikai_sarasas)
        else:
            vilkikas = col7.text_input("Vilkikas (nėra įrašų, įveskite ranka)")
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
            try:
                c.execute("SELECT COUNT(*) FROM kroviniai WHERE uzsakymo_numeris = ?", (uzsakymo_numeris,))
                if c.fetchone()[0] > 0:
                    st.warning("⚠️ Toks užsakymo numeris jau yra!")
                kilometrai = int(kilometrai_raw) if kilometrai_raw else 0
                frachtas = float(frachtas_raw) if frachtas_raw else 0.0
                svoris = int(svoris_raw) if svoris_raw else 0
                paleciu_skaicius = int(paleciu_raw) if paleciu_raw else 0

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
                st.success("✅ Krovinys įrašytas sėkmingai!")
            except Exception as e:
                st.error(f"❌ Klaida įrašant: {e}")

    st.subheader("📦 Krovinių sąrašas")
    df = pd.read_sql_query("SELECT * FROM kroviniai", conn)
    df["Krovinio ID"] = df["id"].astype(str) + "-" + (df.groupby("uzsakymo_numeris").cumcount() + 1).astype(str)
    df["EUR/km"] = df.apply(lambda row: round(row["frachtas"] / row["kilometrai"], 2) if row["kilometrai"] > 0 else 0, axis=1)
    df["Padėklų sk."] = df["paleciu_skaicius"]
    st.dataframe(df)

# --- VILKIKAI ---
elif modulis == "Vilkikai":
    st.title("DISPO – Vilkikų valdymas")

    with st.form("vilkiku_forma", clear_on_submit=True):
        st.subheader("➕ Pridėti naują vilkiką")
        col1, col2 = st.columns(2)
        numeris = col1.text_input("Valstybiniai numeriai")
        marke = col2.text_input("Markė")

        col3, col4 = st.columns(2)
        pagaminimo_metai = col3.text_input("Pagaminimo metai (pvz. 2016)")
        tech_apziura_raw = col4.text_input("Techninės apžiūros data (YYYY-MM-DD)")

        col5, col6 = st.columns(2)
        priekabos_sarasas = [row[0] for row in c.execute("SELECT numeris FROM priekabos").fetchall()]
        priekaba = col5.selectbox("Priekaba", priekabos_sarasas) if priekabos_sarasas else ""

        vadybininkai = [f"{row[0]} {row[1]}" for row in c.execute("SELECT vardas, pavarde FROM darbuotojai WHERE pareigybe = 'transporto vadybininkas'")]
        vadybininkas = col6.selectbox("Transporto vadybininkas", vadybininkai) if vadybininkai else ""

        vilkikas_submit = st.form_submit_button("💾 Įrašyti vilkiką")

    if vilkikas_submit:
        if not numeris or not pagaminimo_metai:
            st.warning("⚠️ Numeris ir pagaminimo metai yra privalomi.")
        else:
            try:
                tech_apziura = tech_apziura_raw if tech_apziura_raw else None
                c.execute("INSERT INTO vilkikai (numeris, marke, pagaminimo_metai, tech_apziura, priekaba, vadybininkas) VALUES (?, ?, ?, ?, ?, ?)",
                        (numeris, marke, int(pagaminimo_metai), tech_apziura, priekaba, vadybininkas))
                conn.commit()
                st.success("✅ Vilkikas įrašytas sėkmingai!")
            except Exception as e:
                st.error(f"❌ Klaida įrašant: {e}")

    st.subheader("📋 Vilkikų sąrašas")
    df_vilkikai = pd.read_sql_query("SELECT * FROM vilkikai", conn)
    if not df_vilkikai.empty:
        today = pd.to_datetime(date.today())
        df_vilkikai["tech_apziura"] = pd.to_datetime(df_vilkikai["tech_apziura"], errors='coerce')
        df_vilkikai["🛠 TA liko (d.)"] = (df_vilkikai["tech_apziura"] - today).dt.days
        df_vilkikai["TA Įspėjimas"] = df_vilkikai["🛠 TA liko (d.)"].apply(lambda x: "⚠️ Baigiasi" if pd.notnull(x) and x < 30 else "")
    st.dataframe(df_vilkikai)
