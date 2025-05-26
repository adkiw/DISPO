import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date, time, timedelta

# Prisijungimas prie DB
conn = sqlite3.connect('dispo_new.db', check_same_thread=False)
c = conn.cursor()

# Lentelių inicializavimas
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

# Meniu pasirinkimas
modulis = st.sidebar.selectbox("📂 Pasirink modulį", ["Kroviniai", "Vilkikai", "Darbuotojai", "Priekabos"])

# … (visas likęs kodas lieka nepakeistas)
# Nuo “if modulis == 'Kroviniai':” toliau, iki galo
# Nereikia keisti likusios logikos, nes struktūra teisinga
