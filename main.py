import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, time, timedelta
from io import BytesIO

# ─── Duomenų bazės prisijungimas ───────────────────────────────────────────────
conn = sqlite3.connect('dispo_new.db', check_same_thread=False)
c = conn.cursor()

# ─── Universali lookup lentelė ────────────────────────────────────────────────
c.execute("""
CREATE TABLE IF NOT EXISTS lookup (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kategorija TEXT,
    reiksme TEXT UNIQUE
)
""")
conn.commit()

# ─── Kitos lentelės ───────────────────────────────────────────────────────────
table_ddls = {
    "kroviniai": """
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
    """,
    "vilkikai": """
        CREATE TABLE IF NOT EXISTS vilkikai (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numeris TEXT UNIQUE,
            marke TEXT,
            pagaminimo_metai INTEGER,
            tech_apziura DATE,
            vadybininkas TEXT,
            vairuotojai TEXT,
            priekaba TEXT
        )
    """,
    "priekabos": """
        CREATE TABLE IF NOT EXISTS priekabos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            priekabu_tipas TEXT,
            numeris TEXT UNIQUE,
            marke TEXT,
            pagaminimo_metai INTEGER,
            tech_apziura DATE,
            priskirtas_vilkikas TEXT
        )
    """,
    "grupes": """
        CREATE TABLE IF NOT EXISTS grupes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            numeris TEXT UNIQUE,
            pavadinimas TEXT,
            aprasymas TEXT
        )
    """,
    "vairuotojai": """
        CREATE TABLE IF NOT EXISTS vairuotojai (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vardas TEXT,
            pavarde TEXT,
            gimimo_metai INTEGER,
            tautybe TEXT,
            priskirtas_vilkikas TEXT
        )
    """,
    "klientai": """
        CREATE TABLE IF NOT EXISTS klientai (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pavadinimas TEXT,
            kontaktai TEXT,
            salis TEXT,
            miestas TEXT,
            regionas TEXT,
            vat_numeris TEXT
        )
    """,
    "darbuotojai": """
        CREATE TABLE IF NOT EXISTS darbuotojai (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vardas TEXT,
            pavarde TEXT,
            pareigybe TEXT,
            el_pastas TEXT,
            telefonas TEXT,
            grupe TEXT
        )
    """
}
for ddl in table_ddls.values():
    c.execute(ddl)
conn.commit()

# ─── Modulių pasirinkimas (visada matomas sąrašas) ──────────────────────────
moduliai = [
    "DISPO", "Kroviniai", "Vilkikai", "Priekabos",
    "Grupės", "Vairuotojai", "Klientai",
    "Darbuotojai", "Nustatymai"
]
modulis = st.sidebar.radio("📂 Pasirink modulį", moduliai)

# ─── DISPO – Planavimo lentelė ───────────────────────────────────────────────
if modulis == "DISPO":
    st.title("DISPO – Planavimo lentelė")
    vilkikai = [r[0] for r in c.execute("SELECT numeris FROM vilkikai").fetchall()]
    selected_vilkikas = st.selectbox("Vilkikas", vilkikai)
    col1, col2 = st.columns(2)
    start_date = col1.date_input("Pradžios data", date.today())
    end_date = col2.date_input("Pabaigos data", start_date + timedelta(days=6))

    # Kroviniai pakrovimo laiku
    q_load = pd.read_sql_query(
        "SELECT id, pakrovimo_data AS date, 'PAKROVIMAS' AS type, pakrovimo_laikas_nuo AS from_time, "
        "pakrovimo_laikas_iki AS to_time, pakrovimo_salis || ', ' || pakrovimo_miestas AS location, "
        "kilometrai AS empty_km, frachtas AS freight, atsakingas_vadybininkas AS responsible "
        "FROM kroviniai WHERE vilkikas = ? AND pakrovimo_data BETWEEN ? AND ?",
        conn, params=(selected_vilkikas, str(start_date), str(end_date))
    )
    # Kroviniai iškrovimo laiku
    q_unload = pd.read_sql_query(
        "SELECT id, iskrovimo_data AS date, 'IŠKROVIMAS' AS type, iskrovimo_laikas_nuo AS from_time, "
        "iskrovimo_laikas_iki AS to_time, iskrovimo_salis || ', ' || iskrovimo_miestas AS location, "
        "0 AS empty_km, 0 AS freight, atsakingas_vadybininkas AS responsible "
        "FROM kroviniai WHERE vilkikas = ? AND iskrovimo_data BETWEEN ? AND ?",
        conn, params=(selected_vilkikas, str(start_date), str(end_date))
    )
    df_events = pd.concat([q_unload, q_load], ignore_index=True)
    df_events['date'] = pd.to_datetime(df_events['date']).dt.date
    table = df_events.pivot(
        index='type',
        columns='date',
        values=['from_time', 'to_time', 'location', 'empty_km', 'freight', 'responsible']
    )
    st.dataframe(table)

    # Eksporto mygtukai
    csv = table.to_csv(encoding='utf-8-sig')
    st.download_button("🔽 Atsisiųsti CSV", csv, file_name="dispo_plan.csv", mime="text/csv")

    with BytesIO() as b:
        writer = pd.ExcelWriter(b, engine="xlsxwriter")
        table.to_excel(writer, sheet_name="DISPO")
        writer.save()
        data = b.getvalue()
    st.download_button("🔽 Atsisiųsti Excel", data, file_name="dispo_plan.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ─── NUSTATYMAI: visiškai dinamiškas dropdown valdymas ────────────────────────
elif modulis == "Nustatymai":
    st.title("DISPO – Sąrašų valdymas")
    kategorijos = [row[0] for row in c.execute(
        "SELECT DISTINCT kategorija FROM lookup"
    ).fetchall()]
    col1, col2 = st.columns(2)
    esama = col1.selectbox("Esama kategorija", [""] + kategorijos)
    nauja_kat = col2.text_input("Arba nauja kategorija")
    kategorija = nauja_kat.strip() if nauja_kat else esama

    st.markdown("---")
    if kategorija:
        st.subheader(f"Kategorija: **{kategorija}**")
        values = [r[0] for r in c.execute(
            "SELECT reiksme FROM lookup WHERE kategorija = ?", (kategorija,)
        ).fetchall()]
        st.write(values or "_(nerasta reikšmių)_")
        nauja_reiksme = st.text_input("Pridėti naują reikšmę")
        if st.button("➕ Pridėti reikšmę"):
            if nauja_reiksme:
                try:
                    c.execute(
                        "INSERT INTO lookup(kategorija, reiksme) VALUES(?, ?)",
                        (kategorija, nauja_reiksme)
                    )
                    conn.commit()
                    st.success(f"✅ Pridėta: {nauja_reiksme}")
                except sqlite3.IntegrityError:
                    st.warning("⚠️ Toks elementas jau egzistuoja.")
        istr = st.selectbox("Ištrinti reikšmę", [""] + values)
        if st.button("🗑 Ištrinti reikšmę"):
            if istr:
                c.execute(
                    "DELETE FROM lookup WHERE kategorija = ? AND reiksme = ?",
                    (kategorija, istr)
                )
                conn.commit()
                st.success(f"✅ Ištrinta: {istr}")
    else:
        st.info("Pasirink arba sukurk kategoriją, kad valdytum reikšmes.")

# ─── KROVINIAI ────────────────────────────────────────────────────────────────
elif modulis == "Kroviniai":
    st.title("DISPO – Krovinių valdymas")
    with st.form("krovinio_forma", clear_on_submit=False):
        klientai = [r[0] for r in c.execute("SELECT pavadinimas FROM klientai").fetchall()]
        col1, col2 = st.columns(2)
        if klientai:
            klientas = col1.selectbox("Klientas", klientai)
        else:
            klientas = col1.text_input("Klientas (nėra įvestų)")
        uzsakymo_numeris = col2.text_input("Užsakymo numeris")
        pakrovimo_numeris = st.text_input("Pakrovimo numeris")

        col3, col4 = st.columns(2)
        pakrovimo_data = col3.date_input("Pakrovimo data", date.today())
        pakrovimo_laikas_nuo = col3.time_input("Laikas nuo (pakrovimas)", time(8, 0))
        pakrovimo_laikas_iki = col3.time_input("Laikas iki (pakrovimas)", time(17, 0))

        iskrovimo_data = col4.date_input("Iškrovimo data", pakrovimo_data + timedelta(days=1))
        iskrovimo_laikas_nuo = col4.time_input("Laikas nuo (iškrovimas)", time(8, 0))
        iskrovimo_laikas_iki = col4.time_input("Laikas iki (iškrovimas)", time(17, 0))

        col5, col6 = st.columns(2)
        pakrovimo_salis = col5.text_input("Pakrovimo šalis")
        pakrovimo_miestas = col5.text_input("Pakrovimo miestas")
        iskrovimo_salis = col6.text_input("Iškrovimo šalis")
        iskrovimo_miestas = col6.text_input("Iškrovimo miestą")

        col7, col8 = st.columns(2)
        vilkikai_list = [r[0] for r in c.execute("SELECT numeris FROM vilkikai").fetchall()]
        if vilkikai_list:
            vilkikas = col7.selectbox("Vilkikas", vilkikai_list)
            priekaba_val = c.execute("SELECT priekaba FROM vilkikai WHERE numeris = ?", (vilkikas,)).fetchone()
            priekaba = priekaba_val[0] if priekaba_val else ""
        else:
            vilkikas = col7.text_input("Vilkikas (nėra įvestų)")
            priekaba = ""
        col8.text_input("Priekaba", value=priekaba, disabled=True)

        col9, col10, col11, col12 = st.columns(4)
        kilometrai = col9.text_input("Kilometrai")
        frachtas = col10.text_input("Frachtas (€)")
        svoris = col11.text_input("Svoris (kg)")
        paleciu = col12.text_input("Padėklų skaičius")

        busena_opt = [r[0] for r in c.execute("SELECT reiksme FROM lookup WHERE kategorija = ?", ("busena",)).fetchall()]
        busena = st.selectbox("Būsena", busena_opt or ["suplanuotas","nesuplanuotas","pakrautas","iškrautas"])

        submit = st.form_submit_button("💾 Įrašyti krovinį")

    if submit:
        if pakrovimo_data > iskrovimo_data:
            st.error("❌ Pakrovimo data negali būti vėlesnė už iškrovimo datą.")
        elif not klientas or not uzsakymo_numeris:
            st.error("❌ Privalomi laukai: Klientas ir Užsakymo numeris.")
        else:
            base = uzsakymo_numeris
            egz = [r[0] for r in c.execute(
                "SELECT uzsakymo_numeris FROM kroviniai WHERE uzsakymo_numeris LIKE ?", (f"{base}%",)
            ).fetchall()]
            if base in egz:
                suffix = sum(1 for x in egz if x.startswith(base))
                uzsakymo_numeris = f"{base}-{suffix}"
                st.warning(f"🔔 Toks numeris jau egzistuoja – išsaugotas kaip {uzsakymo_numeris}.")
            c.execute("""
                INSERT INTO kroviniai (
                    klientas, uzsakymo_numeris, pakrovimo_numeris,
                    pakrovimo_data, pakrovimo_laikas_nuo, pakrovimo_laikas_iki,
                    iskrovimo_data, iskrovimo_laikas_nuo, iskrovimo_laikas_iki,
                    pakrovimo_salis, pakrovimo_miestas,
                    iskrovimo_salis, iskrovimo_miestas,
                    vilkikas, priekaba, atsakingas_vadybininkas,
                    kilometrai, frachtas, svoris, paleciu_skaicius, busena
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                klientas, uzsakymo_numeris, pakrovimo_numeris,
                str(pakrovimo_data), str(pakrovimo_laikas_nuo), str(pakrovimo_laikas_iki),
                str(iskrovimo_data), str(iskrovimo_laikas_nuo), str(iskrovimo_laikas_iki),
                pakrovimo_salis, pakrovimo_miestas, iskrovimo_salis, iskrovimo_miestas,
                vilkikas, priekaba, f"vadyb_{vilkikas.lower()}",
                int(kilometrai or 0), float(frachtas or 0),
                int(svoris or 0), int(paleciu or 0), busena
            ))
            conn.commit()
            st.success("✅ Krovinį išsaugojau.")

    st.subheader("📋 Krovinių sąrašas")
    st.dataframe(pd.read_sql_query("SELECT * FROM kroviniai", conn))

# ─── VILKIKAI ────────────────────────────────────────────────────────────────
elif modulis == "Vilkikai":
    st.title("DISPO – Vilkikų valdymas")
    with st.form("vilkikai_forma", clear_on_submit=True):
        numeris = st.text_input("Numeris")
        marks = [r[0] for r in c.execute("SELECT reiksme FROM lookup WHERE kategorija = ?", ("vilkiku_marke",)).fetchall()]
        marke = st.selectbox("Markė", marks) if marks else st.text_input("Markė")
        pag_metai = st.text_input("Pagaminimo metai")
        tech_apz = st.date_input("Tech. apžiūra")
        vadyb = st.text_input("Vadybininkas")
        vair = st.text_input("Vairuotojai (kableliai)")
        priek = st.text_input("Priekaba")
        sub = st.form_submit_button("💾 Įrašyti vilkiką")
    if sub:
        if not numeris:
            st.warning("⚠️ Įveskite numerį.")
        else:
            try:
                c.execute("""
                    INSERT INTO vilkikai (
                        numeris, marke, pagaminimo_metai, tech_apziura,
                        vadybininkas, vairuotojai, priekaba
                    ) VALUES (?,?,?,?,?,?,?)
                """, (numeris, marke, int(pag_metai or 0), str(tech_apz), vadyb, vair, priek))
                conn.commit(); st.success("✅ Išsaugojau.")
            except Exception as e:
                st.error(f"❌ Klaida: {e}")
    st.dataframe(pd.read_sql_query("SELECT * FROM vilkikai", conn))

# ─── PRIEKABOS ───────────────────────────────────────────────────────────────
elif modulis == "Priekabos":
    st.title("DISPO – Priekabų valdymas")
    with st.form("priek_form", clear_on_submit=True):
        tipai = [r[0] for r in c.execute("SELECT reiksme FROM lookup WHERE kategorija = ?", ("priekabu_tipas",)).fetchall()]
        pr_tipas = st.selectbox("Tipas", tipai) if tipai else st.text_input("Tipas")
        num = st.text_input("Numeris")
        mr = st.text_input("Markė")
        pm = st.text_input("Pagaminimo metai")
        ta = st.date_input("Tech. apžiūra")
        pv = st.text_input("Priskirtas vilkikas")
        sb = st.form_submit_button("💾 Išsaugoti")
    if sb:
        if not num:
            st.warning("⚠️ Įveskite numerį.")
        else:
            try:
                c.execute("""
                    INSERT INTO priekabos (
                        priekabu_tipas, numeris, marke,
                        pagaminimo_metai, tech_apziura, priskirtas_vilkikas
                    ) VALUES (?,?,?,?,?,?)
                """, (pr_tipas, num, mr, int(pm or 0), str(ta), pv))
                conn.commit(); st.success("✅ Išsaugojau.")
            except Exception as e:
                st.error(f"❌ Klaida: {e}")
    st.dataframe(pd.read_sql_query("SELECT * FROM priekabos", conn))

# ─── GRUPĖS ─────────────────────────────────────────────────────────────────
elif modulis == "Grupės":
    st.title("DISPO – Grupės")
    with st.form("grp_form", clear_on_submit=True):
        nr = st.text_input("Numeris")
        pav = st.text_input("Pavadinimas")
        apr = st.text_area("Aprašymas")
        sb = st.form_submit_button("💾 Išsaugoti")
    if sb:
        if not nr or not pav:
            st.warning("⚠️ Numeris ir pavadinimas būtini.")
        else:
            try:
                c.execute(
                    "INSERT INTO grupes(numeris,pavadinimas,aprasymas) VALUES(?,?,?)",
                    (nr, pav, apr)
                )
                conn.commit(); st.success("✅ Išsaugojau.")
            except Exception as e:
                st.error(f"❌ Klaida: {e}")
    st.dataframe(pd.read_sql_query("SELECT * FROM grupes", conn))

# ─── VAIRUOTOJAI ─────────────────────────────────────────────────────────────
elif modulis == "Vairuotojai":
    st.title("DISPO – Vairuotojai")
    with st.form("drv_form", clear_on_submit=True):
        vd = st.text_input("Vardas"); pv = st.text_input("Pavardė")
        gm = st.text_input("Gimimo metai"); tt = st.text_input("Tautybė")
        pvk = st.text_input("Priskirtas vilkikas")
        sb = st.form_submit_button("💾 Išsaugoti")
    if sb:
        if not vd or not pv:
            st.warning("⚠️ Reikia vardo ir pavardės.")
        else:
            try:
                c.execute("""
                    INSERT INTO vairuotojai (
                        vardas,pavarde,gimimo_metai,tautybe,priskirtas_vilkikas
                    ) VALUES(?,?,?,?,?)
                """, (vd, pv, int(gm or 0), tt, pvk))
                conn.commit(); st.success("✅ Išsaugojau.")
            except Exception as e:
                st.error(f"❌ Klaida: {e}")
    st.dataframe(pd.read_sql_query("SELECT * FROM vairuotojai", conn))

# ─── KLIENTAI ────────────────────────────────────────────────────────────────
elif modulis == "Klientai":
    st.title("DISPO – Klientai")
    with st.form("kl_form", clear_on_submit=True):
        iv = st.text_input("Įmonės pavadinimas"); kt = st.text_input("Kontaktai")
        sl = st.text_input("Šalis"); ms = st.text_input("Miestas")
        rg = st.text_input("Regionas"); pv = st.text_input("PVM numeris")
        sb = st.form_submit_button("💾 Išsaugoti")
    if sb:
        if not iv:
            st.warning("⚠️ Pavadinimas būtinas.")
        else:
            try:
                c.execute("""
                    INSERT INTO klientai (
                        pavadinimas,kontaktai,salis,miestas,regionas,vat_numeris
                    ) VALUES(?,?,?,?,?,?)
                """, (iv, kt, sl, ms, rg, pv))
                conn.commit(); st.success("✅ Išsaugojau.")
            except Exception as e:
                st.error(f"❌ Klaida: {e}")
    st.dataframe(pd.read_sql_query("SELECT * FROM klientai", conn))

# ─── DARBUOTOJAI ─────────────────────────────────────────────────────────────
elif modulis == "Darbuotojai":
    st.title("DISPO – Darbuotojai")
    p_list = [r[0] for r in c.execute("SELECT reiksme FROM lookup WHERE kategorija = ?", ("pareigybe",)).fetchall()]
    g_list = [r[2] for r in c.execute("SELECT id,numeris,pavadinimas FROM grupes").fetchall()]
    with st.form("emp_form", clear_on_submit=True):
        vd = st.text_input("Vardas"); pv = st.text_input("Pavardė")
        pg = st.selectbox("Pareigybė", p_list) if p_list else st.text_input("Pareigybė")
        gr = st.selectbox("Grupė", g_list) if g_list else st.text_input("Grupė")
        em = st.text_input("El. paštas"); ph = st.text_input("Telefonas")
        sb = st.form_submit_button("💾 Išsaugoti")
    if sb:
        if not vd or not pv:
            st.warning("⚠️ Vardas ir pavardė būtini.")
        else:
            try:
                c.execute("""
                    INSERT INTO darbuotojai (
                        vardas,pavarde,pareigybe,el_pastas,telefonas,grupe
                    ) VALUES(?,?,?,?,?,?)
                """, (vd, pv, pg, em, ph, gr))
                conn.commit(); st.success("✅ Išsaugojau.")
            except Exception as e:
                st.error(f"❌ Klaida: {e}")
    st.dataframe(pd.read_sql_query("SELECT * FROM darbuotojai", conn))
