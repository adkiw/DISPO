
import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date

# Prisijungimas prie SQLite bazės
conn = sqlite3.connect('dispo.db', check_same_thread=False)
c = conn.cursor()

# 1. Pirma sukurti lentelę, jei dar nėra
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

# 2. Tik tada tikrinti, ar yra papildomas stulpelis
c.execute("PRAGMA table_info(kroviniai)")
columns = [col[1] for col in c.fetchall()]
if "pakrovimo_numeris" not in columns:
    try:
        c.execute("ALTER TABLE kroviniai ADD COLUMN pakrovimo_numeris TEXT UNIQUE")
        conn.commit()
    except sqlite3.OperationalError:
        pass

st.title("DISPO – Krovinių valdymas")

# Sesijos būsena dublikato patvirtinimui
if 'leidimas_irasyti' not in st.session_state:
    st.session_state['leidimas_irasyti'] = False

with st.form("krovinio_forma", clear_on_submit=False):
    pakrovimo_numeris = st.text_input("Pakrovimo numeris", max_chars=20)
    pakrovimo_data = st.date_input("Pakrovimo data", value=date.today())
    pakrovimo_laikas = st.time_input("Pakrovimo laikas", value=datetime.now().time())
    iskrovimo_data = st.date_input("Iškrovimo data", value=date.today())
    iskrovimo_laikas = st.time_input("Iškrovimo laikas", value=datetime.now().time())
    pakrovimo_miestas = st.text_input("Pakrovimo miestas")
    iskrovimo_miestas = st.text_input("Iškrovimo miestas")
    kilometrai = st.number_input("Kilometrai", min_value=0)
    frachtas = st.number_input("Frachtas (€)", min_value=0.0, format="%.2f")
    submit = st.form_submit_button("Įrašyti krovinį")

# Apdorojimas
if submit:
    pakrovimo_data_laikas = f"{pakrovimo_data} {pakrovimo_laikas}"
    iskrovimo_data_laikas = f"{iskrovimo_data} {iskrovimo_laikas}"

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
                INSERT INTO kroviniai (pakrovimo_numeris, pakrovimo_data_laikas, iskrovimo_data_laikas,
                                       pakrovimo_miestas, iskrovimo_miestas, kilometrai, frachtas)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (pakrovimo_numeris, pakrovimo_data_laikas, iskrovimo_data_laikas,
                  pakrovimo_miestas, iskrovimo_miestas, kilometrai, frachtas))
            conn.commit()
            st.success("Krovinys įrašytas!")
            st.session_state['leidimas_irasyti'] = False
        except sqlite3.IntegrityError:
            st.error("Toks pakrovimo numeris jau egzistuoja ir įrašymas nebuvo patvirtintas.")

# Lentelės peržiūra
st.subheader("Krovinių sąrašas")
df = pd.read_sql_query("SELECT * FROM kroviniai", conn)
st.dataframe(df)
