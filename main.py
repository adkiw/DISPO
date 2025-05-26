import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date, time, timedelta

conn = sqlite3.connect('dispo_new.db', check_same_thread=False)
c = conn.cursor()

# Meniu pasirinkimas
modulis = st.sidebar.selectbox("📂 Pasirink modulį", ["Kroviniai", "Vilkikai", "Darbuotojai", "Priekabos"])

if modulis == "Kroviniai":
    # ... (visa tavo Kroviniai logika)
    pass

elif modulis == "Vilkikai":
    # ... (visa tavo Vilkikai logika)
    pass

elif modulis == "Darbuotojai":
    # ... (visa tavo Darbuotojai logika)
    pass

elif modulis == "Priekabos":
    st.title("DISPO – Priekabų valdymas")
    c.execute("""
    CREATE TABLE IF NOT EXISTS priekabos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numeris TEXT UNIQUE,
        marke TEXT,
        pagaminimo_metai INTEGER,
        tech_apziura DATE
    )
    """)
    conn.commit()

    with st.form("priekabu_forma", clear_on_submit=True):
        st.subheader("➕ Pridėti naują priekabą")
        col1, col2 = st.columns(2)
        numeris = col1.text_input("Valstybiniai numeriai")
        marke = col2.text_input("Markė")

        col3, col4 = st.columns(2)
        pagaminimo_metai = col3.text_input("Pagaminimo metai")
        tech_apziura = col4.date_input("Paskutinė techninė apžiūra")

        priekaba_submit = st.form_submit_button("💾 Įrašyti priekabą")

    if priekaba_submit:
        if not numeris or not pagaminimo_metai:
            st.warning("⚠️ Numeris ir pagaminimo metai yra privalomi.")
        else:
            try:
                c.execute("INSERT INTO priekabos (numeris, marke, pagaminimo_metai, tech_apziura) VALUES (?, ?, ?, ?)",
                        (numeris, marke, int(pagaminimo_metai), str(tech_apziura)))
                conn.commit()
                st.success("✅ Priekaba įrašyta sėkmingai!")
            except Exception as e:
                st.error(f"❌ Klaida įrašant: {e}")

    st.subheader("📋 Priekabų sąrašas")
    df_priekabos = pd.read_sql_query("SELECT * FROM priekabos", conn)
    today = pd.to_datetime(date.today())
    df_priekabos["tech_apziura"] = pd.to_datetime(df_priekabos["tech_apziura"])
    df_priekabos["🛠 TA liko (d.)"] = (df_priekabos["tech_apziura"] - today).dt.days
    df_priekabos["TA Įspėjimas"] = df_priekabos["🛠 TA liko (d.)"].apply(
        lambda x: "⚠️ Baigiasi" if x < 30 else "")
    st.dataframe(df_priekabos)
