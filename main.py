import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, time, timedelta

# ─── Duomenų bazės prisijungimas ───────────────────────────────────────────────
conn = sqlite3.connect('dispo_new.db', check_same_thread=False)
c = conn.cursor()

# ─── Universali lookup lentelė dropdown reikšmėms ─────────────────────────────
c.execute("""
CREATE TABLE IF NOT EXISTS lookup (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kategorija TEXT,
    reiksme TEXT UNIQUE
)
""")
conn.commit()

# ─── Svarbiausių lentelių užtikrinimas ────────────────────────────────────────
# (kuriame tik tuščias struktūras; duomenų pildymas jau vyksta moduliai)
tables = {
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

for ddl in tables.values():
    c.execute(ddl)
conn.commit()

# ─── Šoninė meniu juosta ──────────────────────────────────────────────────────
modulis = st.sidebar.selectbox("📂 Pasirink modulį", [
    "Kroviniai", "Vilkikai", "Priekabos",
    "Grupės", "Vairuotojai", "Klientai",
    "Darbuotojai", "Nustatymai"
])

# ─── NUSTATYMAI: visiškai dinamiškas dropdown valdymas ────────────────────────
if modulis == "Nustatymai":
    st.title("DISPO – Sąrašų valdymas")

    # 1) Užkraunam visas esamas kategorijas
    kategorijos = [r[0] for r in c.execute(
        "SELECT DISTINCT kategorija FROM lookup"
    ).fetchall()]

    # 2) Galim pasirinkti esamą arba įvesti naują
    col1, col2 = st.columns(2)
    esama = col1.selectbox("Pasirink esamą kategoriją", [""] + kategorijos)
    nauja_kat = col2.text_input("Arba įveskite naują kategoriją")
    kategorija = nauja_kat.strip() if nauja_kat else esama

    st.markdown("---")

    if kategorija:
        st.subheader(f"Reikšmės kategorijoje: **{kategorija}**")

        # 3a) Rodom esamas reikšmes
        values = [r[0] for r in c.execute(
            "SELECT reiksme FROM lookup WHERE kategorija = ?", (kategorija,)
        ).fetchall()]
        st.write(values or "_(kol kas nėra įrašų)_")

        # 3b) Pridėti naują reikšmę
        nauja = st.text_input("Pridėti naują reikšmę šiai kategorijai")
        if st.button("➕ Pridėti reikšmę"):
            if nauja:
                try:
                    c.execute(
                        "INSERT INTO lookup (kategorija, reiksme) VALUES (?, ?)",
                        (kategorija, nauja)
                    )
                    conn.commit()
                    st.success(f"✅ Pridėta: {nauja}")
                except sqlite3.IntegrityError:
                    st.warning("⚠️ Toks įrašas jau egzistuoja.")

        # 3c) Ištrinti pažymėtą reikšmę
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
        st.info("Įveskite naują kategoriją arba išsirinkite esamą, kad galėtumėte valdyti reikšmes.")

# ─── KROVINIAI ────────────────────────────────────────────────────────────────
elif modulis == "Kroviniai":
    st.title("DISPO – Krovinių valdymas")

    with st.form("forma", clear_on_submit=False):
        col0a, col0b = st.columns(2)
        klientas = col0a.text_input("Klientas")
        uzsakymo_numeris = col0b.text_input("Užsakymo numeris")
        pakrovimo_numeris = st.text_input("Pakrovimo numeris")

        col1, col2 = st.columns(2)
        pakrovimo_data = col1.date_input("Pakrovimo data", date.today())
        pakrovimo_laikas_nuo = col1.time_input("Laikas nuo (pakrovimo)", time(8,0))
        iskrovimo_data = col2.date_input("Iškrovimo data", pakrovimo_data + timedelta(days=1))
        iskrovimo_laikas_nuo = col2.time_input("Laikas nuo (iškrovimo)", time(8,0))

        col3, col4 = st.columns(2)
        pakrovimo_laikas_iki = col3.time_input("Laikas iki (pakrovimo)", time(17,0))
        iskrovimo_laikas_iki = col4.time_input("Laikas iki (iškrovimo)", time(17,0))

        col5, col6 = st.columns(2)
        pakrovimo_salis = col5.text_input("Pakrovimo šalis")
        pakrovimo_miestas = col5.text_input("Pakrovimo miestas")
        iskrovimo_salis = col6.text_input("Iškrovimo šalis")
        iskrovimo_miestas = col6.text_input("Iškrovimo miestas")

        col7, col8 = st.columns(2)
        vilkikai_sarasas = [r[0] for r in c.execute("SELECT numeris FROM vilkikai").fetchall()]
        vilkikas = col7.selectbox("Vilkikas", vilkikai_sarasas) if vilkikai_sarasas else col7.text_input("Vilkikas")
        priekaba = "PR" + vilkikas[-3:] if vilkikas and len(vilkikas)>=3 else ""
        atsakingas_vadybininkas = "vadyb_" + vilkikas.lower() if vilkikas else ""
        col8.text_input("Priekaba", value=priekaba, disabled=True)

        col9, col10, col11 = st.columns(3)
        kilometrai_raw = col9.text_input("Kilometrai")
        frachtas_raw = col10.text_input("Frachtas (€)")
        svoris_raw = col11.text_input("Svoris (kg)")

        paleciu_raw = st.text_input("Padėklų skaičius")

        # Dinaminė 'busena' iš lookup
        busena_list = [r[0] for r in c.execute(
            "SELECT reiksme FROM lookup WHERE kategorija = ?", ("busena",)
        ).fetchall()]
        busena = st.selectbox("Būsena", busena_list) if busena_list else st.selectbox(
            "Būsena", ["suplanuotas","nesuplanuotas","pakrautas","iškrautas"]
        )

        submit = st.form_submit_button("💾 Įrašyti krovinį")

    if submit:
        if pakrovimo_data > iskrovimo_data:
            st.error("❌ Pakrovimo data negali būti vėlesnė už iškrovimo datą.")
        elif not klientas or not uzsakymo_numeris:
            st.error("❌ Privalomi laukai: Klientas ir Užsakymo numeris.")
        else:
            try:
                km = int(kilometrai_raw or 0)
                fr = float(frachtas_raw or 0)
                sv = int(svoris_raw or 0)
                pal = int(paleciu_raw or 0)
                c.execute("""
                    INSERT INTO kroviniai (
                        klientas, uzsakymo_numeris, pakrovimo_numeris,
                        pakrovimo_data, pakrovimo_laikas_nuo, pakrovimo_laikas_iki,
                        iskrovimo_data, iskrovimo_laikas_nuo, iskrovimo_laikas_iki,
                        pakrovimo_salis, pakrovimo_miestas, iskrovimo_salis, iskrovimo_miestas,
                        vilkikas, priekaba, atsakingas_vadybininkas,
                        kilometrai, frachtas, svoris, paleciu_skaicius, busena
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    klientas, uzsakymo_numeris, pakrovimo_numeris,
                    str(pakrovimo_data), str(pakrovimo_laikas_nuo), str(pakrovimo_laikas_iki),
                    str(iskrovimo_data), str(iskrovimo_laikas_nuo), str(iskrovimo_laikas_iki),
                    pakrovimo_salis, pakrovimo_miestas, iskrovimo_salis, iskrovimo_miestas,
                    vilkikas, priekaba, atsakingas_vadybininkas,
                    km, fr, sv, pal, busena
                ))
                conn.commit()
                st.success("✅ Įrašyta sėkmingai.")
            except Exception as e:
                st.error(f"❌ Klaida: {e}")

    st.subheader("📋 Krovinių sąrašas")
    df = pd.read_sql_query("SELECT * FROM kroviniai", conn)
    st.dataframe(df)

# ─── VILKIKAI ────────────────────────────────────────────────────────────────
elif modulis == "Vilkikai":
    st.title("DISPO – Vilkikų valdymas")

    with st.form("vilkikai_forma", clear_on_submit=True):
        col1, col2 = st.columns(2)
        numeris = col1.text_input("Vilkiko numeris")

        # Dinaminė markė iš lookup
        marke_list = [r[0] for r in c.execute(
            "SELECT reiksme FROM lookup WHERE kategorija = ?", ("vilkiku_marke",)
        ).fetchall()]
        marke = col2.selectbox("Markė", marke_list) if marke_list else col2.text_input("Markė")

        col3, col4 = st.columns(2)
        pag_metai = col3.text_input("Pagaminimo metai")
        tech_apziura = col4.date_input("Techninė apžiūra")

        vadybininkas = st.text_input("Priskirtas vadybininkas")
        vairuotojai = st.text_input("Vairuotojai (atskirti kableliais)")
        priekaba = st.text_input("Priekaba")

        submit = st.form_submit_button("💾 Įrašyti vilkiką")

    if submit:
        if not numeris:
            st.warning("⚠️ Numeris privalomas.")
        else:
            try:
                c.execute("""
                    INSERT INTO vilkikai (
                        numeris, marke, pagaminimo_metai, tech_apziura,
                        vadybininkas, vairuotojai, priekaba
                    ) VALUES (?,?,?,?,?,?,?)
                """, (
                    numeris, marke, int(pag_metai), str(tech_apziura),
                    vadybininkas, vairuotojai, priekaba
                ))
                conn.commit()
                st.success("✅ Vilkikas įrašytas.")
            except Exception as e:
                st.error(f"❌ Klaida: {e}")

    df = pd.read_sql_query("SELECT * FROM vilkikai", conn)
    st.subheader("📋 Vilkikų sąrašas")
    st.dataframe(df)

# ─── PRIEKABOS ───────────────────────────────────────────────────────────────
elif modulis == "Priekabos":
    st.title("DISPO – Priekabų valdymas")

    with st.form("priekabos_forma", clear_on_submit=True):
        col1, col2 = st.columns(2)
        # Dinaminis priekabų tipas
        tipai = [r[0] for r in c.execute(
            "SELECT reiksme FROM lookup WHERE kategorija = ?", ("priekabu_tipas",)
        ).fetchall()]
        priekabu_tipas = col1.selectbox("Priekabos tipas", tipai) if tipai else col1.text_input("Priekabos tipas")

        numeris = col2.text_input("Priekabos numeris")

        col3, col4 = st.columns(2)
        marke = col3.text_input("Markė")
        pag_metai = col4.text_input("Pagaminimo metai")
        tech_apziura = col4.date_input("Techninė apžiūra")

        priskirtas_vilkikas = st.text_input("Priskirtas vilkikas")

        submit = st.form_submit_button("💾 Įrašyti priekabą")

    if submit:
        if not numeris:
            st.warning("⚠️ Priekabos numeris būtinas.")
        else:
            try:
                c.execute("""
                    INSERT INTO priekabos (
                        priekabu_tipas, numeris, marke, pagaminimo_metai,
                        tech_apziura, priskirtas_vilkikas
                    ) VALUES (?,?,?,?,?,?)
                """, (
                    priekabu_tipas, numeris, marke, int(pag_metai),
                    str(tech_apziura), priskirtas_vilkikas
                ))
                conn.commit()
                st.success("✅ Priekaba įrašyta.")
            except Exception as e:
                st.error(f"❌ Klaida: {e}")

    df = pd.read_sql_query("SELECT * FROM priekabos", conn)
    st.subheader("📋 Priekabų sąrašas")
    st.dataframe(df)

# ─── GRUPĖS ─────────────────────────────────────────────────────────────────
elif modulis == "Grupės":
    st.title("DISPO – Darbo grupių valdymas")

    with st.form("grupes_forma", clear_on_submit=True):
        col1, col2 = st.columns(2)
        numeris = col1.text_input("Grupės numeris")
        pavadinimas = col2.text_input("Pavadinimas")
        aprasymas = st.text_area("Aprašymas")
        submit = st.form_submit_button("💾 Įrašyti grupę")

    if submit:
        if not numeris or not pavadinimas:
            st.warning("⚠️ Numeris ir pavadinimas būtini.")
        else:
            try:
                c.execute("""
                    INSERT INTO grupes (numeris, pavadinimas, aprasymas)
                    VALUES (?,?,?)
                """, (numeris, pavadinimas, aprasymas))
                conn.commit()
                st.success("✅ Grupė įrašyta.")
            except Exception as e:
                st.error(f"❌ Klaida: {e}")

    df = pd.read_sql_query("SELECT * FROM grupes", conn)
    st.subheader("📋 Grupės sąrašas")
    st.dataframe(df)

# ─── VAIRUOTOJAI ─────────────────────────────────────────────────────────────
elif modulis == "Vairuotojai":
    st.title("DISPO – Vairuotojų valdymas")

    with st.form("vairuotojo_forma", clear_on_submit=True):
        col1, col2 = st.columns(2)
        vardas = col1.text_input("Vardas")
        pavarde = col2.text_input("Pavardė")

        col3, col4 = st.columns(2)
        gimimo_metai = col3.text_input("Gimimo metai")
        tautybe = col4.text_input("Tautybė")

        priskirtas_vilkikas = st.text_input("Priskirtas vilkikas")

        submit = st.form_submit_button("💾 Įrašyti vairuotoją")

    if submit:
        if not vardas or not pavarde:
            st.warning("⚠️ Vardas ir pavardė būtini.")
        else:
            try:
                c.execute("""
                    INSERT INTO vairuotojai (
                        vardas, pavarde, gimimo_metai, tautybe, priskirtas_vilkikas
                    ) VALUES (?,?,?,?,?)
                """, (
                    vardas, pavarde, int(gimimo_metai or 0), tautybe, priskirtas_vilkikas
                ))
                conn.commit()
                st.success("✅ Vairuotojas įrašytas.")
            except Exception as e:
                st.error(f"❌ Klaida: {e}")

    df = pd.read_sql_query("SELECT * FROM vairuotojai", conn)
    st.subheader("📋 Vairuotojų sąrašas")
    st.dataframe(df)

# ─── KLIENTAI ────────────────────────────────────────────────────────────────
elif modulis == "Klientai":
    st.title("DISPO – Klientų valdymas")

    with st.form("klientu_forma", clear_on_submit=True):
        col1, col2 = st.columns(2)
        pavadinimas = col1.text_input("Įmonės pavadinimas")
        kontaktai = col2.text_input("Kontaktai")
        col3, col4, col5 = st.columns(3)
        salis = col3.text_input("Šalis")
        miestas = col4.text_input("Miestas")
        regionas = col5.text_input("Regionas")
        vat_numeris = st.text_input("PVM (VAT) numeris")
        submit = st.form_submit_button("💾 Įrašyti klientą")

    if submit:
        if not pavadinimas:
            st.warning("⚠️ Pavadinimas būtinas.")
        else:
            try:
                c.execute("""
                    INSERT INTO klientai (
                        pavadinimas, kontaktai, salis, miestas, regionas, vat_numeris
                    ) VALUES (?,?,?,?,?,?)
                """, (
                    pavadinimas, kontaktai, salis, miestas, regionas, vat_numeris
                ))
                conn.commit()
                st.success("✅ Klientas įrašytas.")
            except Exception as e:
                st.error(f"❌ Klaida: {e}")

    df = pd.read_sql_query("SELECT * FROM klientai", conn)
    st.subheader("📋 Klientų sąrašas")
    st.dataframe(df)

# ─── DARBUOTOJAI ─────────────────────────────────────────────────────────────
elif modulis == "Darbuotojai":
    st.title("DISPO – Darbuotojų valdymas")

    # Dinaminės pareigybės iš lookup
    pareigybe_list = [r[0] for r in c.execute(
        "SELECT reiksme FROM lookup WHERE kategorija = ?", ("pareigybe",)
    ).fetchall()]

    # Dinaminės grupės iš grupes lentelės
    group_list = [r[2] for r in c.execute(
        "SELECT id, numeris, pavadinimas FROM grupes"
    ).fetchall()]

    with st.form("darbuotojo_forma", clear_on_submit=True):
        col1, col2 = st.columns(2)
        vardas = col1.text_input("Vardas")
        pavarde = col2.text_input("Pavardė")

        col3, col4 = st.columns(2)
        if pareigybe_list:
            pareigybe = col3.selectbox("Pareigybė", pareigybe_list)
        else:
            pareigybe = col3.text_input("Pareigybė")

        if group_list:
            grupe = col4.selectbox("Priskirta grupė", group_list)
        else:
            grupe = col4.text_input("Priskirta grupė")

        col5, col6 = st.columns(2)
        el_pastas = col5.text_input("El. paštas")
        telefonas = col6.text_input("Telefono numeris")

        submit = st.form_submit_button("💾 Įrašyti darbuotoją")

    if submit:
        if not vardas or not pavarde:
            st.warning("⚠️ Privaloma įvesti vardą ir pavardę.")
        else:
            try:
                c.execute("""
                    INSERT INTO darbuotojai (
                        vardas, pavarde, pareigybe, el_pastas, telefonas, grupe
                    ) VALUES (?,?,?,?,?,?)
                """, (
                    vardas, pavarde, pareigybe, el_pastas, telefonas, grupe
                ))
                conn.commit()
                st.success("✅ Darbuotojas įrašytas.")
            except Exception as e:
                st.error(f"❌ Klaida: {e}")

    df = pd.read_sql_query("SELECT * FROM darbuotojai", conn)
    st.subheader("📋 Darbuotojų sąrašas")
    st.dataframe(df)
