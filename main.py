import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, time, timedelta

# ─── Duomenų bazės prisijungimas ───────────────────────────────────────────────
conn = sqlite3.connect('dispo_new.db', check_same_thread=False)
c = conn.cursor()

# ─── Universali lookup lentelė su moduliu ──────────────────────────────────────
c.execute("""
CREATE TABLE IF NOT EXISTS lookup (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    modulis TEXT,
    kategorija TEXT,
    reiksme TEXT,
    UNIQUE(modulis, kategorija, reiksme)
)
""")
conn.commit()

# ─── Kitos lentelės ───────────────────────────────────────────────────────────
table_ddls = {
    "kroviniai": """
        CREATE TABLE IF NOT EXISTS kroviniai (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            business_id TEXT,
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
            pasto_kodas TEXT,
            miestas TEXT,
            regionas TEXT,
            vat_numeris TEXT,
            contact1_vardas TEXT,
            contact1_pavarde TEXT,
            contact1_email TEXT,
            contact1_telefonas TEXT,
            contact2_vardas TEXT,
            contact2_pavarde TEXT,
            contact2_email TEXT,
            contact2_telefonas TEXT,
            coface_limitas REAL,
            musu_limitas REAL,
            likes_limitas REAL,
            atsiskaitymo_budas TEXT,
            atsiskaitymo_terminas TEXT,
            atsiskaitymo_naudingumas REAL,
            UNIQUE(pavadinimas, pasto_kodas, miestas)
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

# ─── Moduliai pasirinkimui ──────────────────────────────────────────────────
moduliai = [
    "Kroviniai", "Vilkikai", "Priekabos",
    "Grupės", "Vairuotojai", "Klientai",
    "Darbuotojai", "Nustatymai"
]
modulis = st.sidebar.radio("📂 Pasirink modulį", moduliai)

# ─── NUSTATYMAI: lookup valdymas pagal modulį ────────────────────────────────
if modulis == "Nustatymai":
    st.title("DISPO – Sąrašų valdymas")
    # 1) Pasirinkti moduli
    settings_moduliai = [m for m in moduliai if m != "Nustatymai"]
    sel_modulis = st.selectbox("Modulis", settings_moduliai)
    # 2) Kategorijų sąrašas pagal moduli
    kategorijos = [r[0] for r in c.execute(
        "SELECT DISTINCT kategorija FROM lookup WHERE modulis = ?", (sel_modulis,)
    ).fetchall()]
    col1, col2 = st.columns(2)
    esama = col1.selectbox("Esama kategorija", [""] + kategorijos)
    nauja_kat = col2.text_input("Arba nauja kategorija")
    kategorija = nauja_kat.strip() if nauja_kat else esama

    st.markdown("---")
    if kategorija:
        st.subheader(f"Modulis: {sel_modulis} | Kategorija: **{kategorija}**")
        # 3a) Esamos reikšmės
        values = [r[0] for r in c.execute(
            "SELECT reiksme FROM lookup WHERE modulis = ? AND kategorija = ?",
            (sel_modulis, kategorija)
        ).fetchall()]
        st.write(values or "_(nerasta reikšmių)_")
        # 3b) Pridėti
        nauja_reiksme = st.text_input("Pridėti naują reikšmę")
        if st.button("➕ Pridėti reikšmę"):
            if nauja_reiksme:
                try:
                    c.execute(
                        "INSERT INTO lookup(modulis, kategorija, reiksme) VALUES(?,?,?)",
                        (sel_modulis, kategorija, nauja_reiksme)
                    )
                    conn.commit()
                    st.success(f"✅ Pridėta: {nauja_reiksme}")
                except sqlite3.IntegrityError:
                    st.warning("⚠️ Toks elementas jau egzistuoja.")
        # 3c) Trinti
        istr = st.selectbox("Ištrinti reikšmę", [""] + values)
        if st.button("🗑 Ištrinti reikšmę"):
            if istr:
                c.execute(
                    "DELETE FROM lookup WHERE modulis = ? AND kategorija = ? AND reiksme = ?",
                    (sel_modulis, kategorija, istr)
                )
                conn.commit()
                st.success(f"✅ Ištrinta: {istr}")
    else:
        st.info("Pasirink arba sukurk kategoriją, kad valdytum reikšmes.")

# ─── KROVINIAI ────────────────────────────────────────────────────────────────
elif modulis == "Kroviniai":
    st.title("DISPO – Krovinių valdymas")
    with st.form("krovinio_forma", clear_on_submit=False):
        # 1) Klientas dropdown formatuotas
        klientai = [f"{row[0]} {row[1]} {row[2]}" for row in c.execute(
            "SELECT pavadinimas, pasto_kodas, miestas FROM klientai"
        ).fetchall()]
        if klientai:
            klientas = st.selectbox("Klientas", klientai)
        else:
            klientas = st.text_input("Klientas (nėra įvestų)")

        uzsakymo_numeris = st.text_input("Užsakymo numeris")
        pakrovimo_numeris = st.text_input("Pakrovimo numeris")

        col1, col2 = st.columns(2)
        pakrovimo_data = col1.date_input("Pakrovimo data", date.today())
        pakrovimo_laikas_nuo = col1.time_input("Laikas nuo (pakrovimas)", time(8,0))
        pakrovimo_laikas_iki = col1.time_input("Laikas iki (pakrovimas)", time(17,0))
        col3, col4 = st.columns(2)
        iskrovimo_data = col3.date_input("Iškrovimo data", pakrovimo_data + timedelta(days=1))
        iskrovimo_laikas_nuo = col3.time_input("Laikas nuo (iškrovimas)", time(8,0))
        iskrovimo_laikas_iki = col4.time_input("Laikas iki (iškrovimas)", time(17,0))

        col5, col6 = st.columns(2)
        pakrovimo_salis = col5.text_input("Pakrovimo šalis")
        pakrovimo_miestas = col5.text_input("Pakrovimo miestas")
        iskrovimo_salis = col6.text_input("Iškrovimo šalis")
        iskrovimo_miestas = col6.text_input("Iškrovimo miestą")

        # 2) Vilkikas ir priekaba
        vilkikai = [r[0] for r in c.execute("SELECT numeris FROM vilkikai").fetchall()]
        if vilkikai:
            vilkikas = st.selectbox("Vilkikas", vilkikai)
            priekaba = c.execute(
                "SELECT priekaba FROM vilkikai WHERE numeris = ?",
                (vilkikas,)
            ).fetchone()
            priekaba = priekaba[0] if priekaba else ""
        else:
            vilkikas = st.text_input("Vilkikas (nėra įvestų)")
            priekaba = ""
        st.text_input("Priekaba", value=priekaba, disabled=True)

        col7, col8, col9 = st.columns(3)
        kilometrai = col7.text_input("Kilometrai")
        frachtas = col8.text_input("Frachtas (€)")
        svoris = col9.text_input("Svoris (kg)")
        paleciu = st.text_input("Padėklų skaičius")

        # 3) Būsena iš lookup pagal modulį
        busena_opt = [r[0] for r in c.execute(
            "SELECT reiksme FROM lookup WHERE modulis = ? AND kategorija = ?",
            (modulis, "busena")
        ).fetchall()]
        busena = st.selectbox("Būsena", busena_opt) if busena_opt else st.selectbox(
            "Būsena", ["suplanuotas","nesuplanuotas","pakrautas","iškrautas"]
        )

        submit = st.form_submit_button("💾 Įrašyti krovinį")

    if submit:
        # validacija
        if pakrovimo_data > iskrovimo_data:
            st.error("❌ Pakrovimo data negali būti vėlesnė už iškrovimo datą.")
        elif not klientas or not uzsakymo_numeris:
            st.error("❌ Privalomi laukai: Klientas ir Užsakymo numeris.")
        else:
            # įrašymas be business_id
            c.execute(
                "INSERT INTO kroviniai (business_id, klientas, uzsakymo_numeris, pakrovimo_numeris, pakrovimo_data, pakrovimo_laikas_nuo, pakrovimo_laikas_iki, iskrovimo_data, iskrovimo_laikas_nuo, iskrovimo_laikas_iki, pakrovimo_salis, pakrovimo_miestas, iskrovimo_salis, iskrovimo_miestas, vilkikas, priekaba, atsakingas_vadybininkas, kilometrai, frachtas, svoris, paleciu_skaicius, busena) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (None, klientas, uzsakymo_numeris, pakrovimo_numeris,
                 str(pakrovimo_data), str(pakrovimo_laikas_nuo), str(pakrovimo_laikas_iki),
                 str(iskrovimo_data), str(iskrovimo_laikas_nuo), str(iskrovimo_laikas_iki),
                 pakrovimo_salis, pakrovimo_miestas, iskrovimo_salis, iskrovimo_miestas,
                 vilkikas, priekaba, f"vadyb_{vilkikas.lower()}",
                 int(kilometrai or 0), float(frachtas or 0), int(svoris or 0), int(paleciu or 0), busena)
            )
            conn.commit()
            row_id = c.lastrowid
            # Business ID generavimas
            count = c.execute(
                "SELECT COUNT(*) FROM kroviniai WHERE uzsakymo_numeris = ?", (uzsakymo_numeris,)
            ).fetchone()[0]
            if count == 1:
                business_id = str(row_id)
            else:
                base_row = c.execute(
                    "SELECT id FROM kroviniai WHERE uzsakymo_numeris = ? ORDER BY id ASC LIMIT 1",
                    (uzsakymo_numeris,)
                ).fetchone()[0]
                business_id = f"{base_row}-{count-1}"
                st.warning(f"🔔 Toks numeris jau egzistuoja – verslo ID: {business_id}.")
            c.execute(
                "UPDATE kroviniai SET business_id = ? WHERE id = ?", (business_id, row_id)
            )
            conn.commit()
            st.success("✅ Krovinį išsaugojau.")

    # 📋 Santraukos lentelė
    df = pd.read_sql_query(
        """
        SELECT
            business_id AS 'Business ID',
            klientas AS 'Klientas',
            uzsakymo_numeris AS 'Užsakymo nr.',
            pakrovimo_data || ' ' || pakrovimo_laikas_nuo || '-' || pakrovimo_laikas_iki || ' ' || pakrovimo_salis || ' ' || pakrovimo_miestas AS 'Pakrovimas',
            iskrovimo_data || ' ' || iskrovimo_laikas_nuo || '-' || iskrovimo_laikas_iki || ' ' || iskrovimo_salis || ' ' || iskrovimo_miestas AS 'Iškrovimas',
            vilkikas AS 'Vilkikas', priekaba AS 'Priekaba', busena AS 'Būsena'
        FROM kroviniai
        ORDER BY id DESC
        """,
        conn
    )
    st.subheader("📋 Krovinių sąrašas")
    st.dataframe(df)

# ─── VILKIKAI ────────────────────────────────────────────────────────────────
elif modulis == "Vilkikai":
    st.title("DISPO – Vilkikų valdymas")
    with st.form("vilkikai_forma", clear_on_submit=True):
        numeris = st.text_input("Numeris")
        marks = [r[0] for r in c.execute(
            "SELECT reiksme FROM lookup WHERE modulis = ? AND kategorija = ?", (modulis, "vilkiku_marke")
        ).fetchall()]
        if marks:
            marke = st.selectbox("Markė", marks)
        else:
            marke = st.text_input("Markė")
        pag_metai = st.text_input("Pagaminimo metai")
        tech_apz = st.date_input("Tech. apžiūra")
        vadyb = st.text_input("Transporto vadybininkas")
        vair = st.text_input("Vairuotojai (kableliai)")
        priek = st.text_input("Priekaba")
        sub = st.form_submit_button("💾 Įrašyti vilkiką")
    if sub:
        if not numeris:
            st.warning("⚠️ Įveskite numerį.")
        else:
            try:
                c.execute(
                    "INSERT INTO vilkikai (numeris, marke, pagaminimo_metai, tech_apziura, vadybininkas, vairuotojai, priekaba) VALUES (?,?,?,?,?,?,?)",
                    (numeris, marke, int(pag_metai or 0), str(tech_apz), vadyb, vair, priek)
                )
                conn.commit(); st.success("✅ Išsaugojau.")
            except Exception as e:
                st.error(f"❌ Klaida: {e}")
    st.dataframe(pd.read_sql_query("SELECT * FROM vilkikai", conn))

# ─── PRIEKABOS ───────────────────────────────────────────────────────────────
elif modulis == "Priekabos":
    st.title("DISPO – Priekabų valdymas")
    with st.form("priek_form", clear_on_submit=True):
        tipai = [r[0] for r in c.execute(
            "SELECT reiksme FROM lookup WHERE modulis = ? AND kategorija = ?", (modulis, "priekabu_tipas")
        ).fetchall()]
        if tipai:
            pr_tipas = st.selectbox("Tipas", tipai)
        else:
            pr_tipas = st.text_input("Tipas")
        num = st.text_input("Numeris")
        mr = st.text_input("Markė")
        pm = st.text_input("Pagaminimo metai")
        ta = st.date_input("Tech. apžiūra")
        pv = st.text_input("Priskirtas vilkikas")
        sb = st.form_submit_button("💾 Išsaugoti")
    if sb:
        if not num: st.warning("⚠️ Įveskite numerį.")
        else:
            try:
                c.execute(
                    "INSERT INTO priekabos (priekabu_tipas, numeris, marke, pagaminimo_metai, tech_apziura, priskirtas_vilkikas) VALUES (?,?,?,?,?,?)",
                    (pr_tipas, num, mr, int(pm or 0), str(ta), pv)
                )
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
        if not nr or not pav: st.warning("⚠️ Numeris ir pavadinimas būtini.")
        else:
            try:
                c.execute(
                    "INSERT INTO grupes(numeris,pavadinimas,aprasymas) VALUES(?,?,?)",
                    (nr,pav,apr)
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
        if not vd or not pv: st.warning("⚠️ Reikia vardo ir pavardės.")
        else:
            try:
                c.execute(
                    "INSERT INTO vairuotojai (vardas,pavarde,gimimo_metai,tautybe,priskirtas_vilkikas) VALUES(?,?,?,?,?)",
                    (vd,pv,int(gm or 0),tt,pvk)
                )
                conn.commit(); st.success("✅ Išsaugojau.")
            except Exception as e:
                st.error(f"❌ Klaida: {e}")
    st.dataframe(pd.read_sql_query("SELECT * FROM vairuotojai", conn))

# ─── KLIENTAI ────────────────────────────────────────────────────────────────
elif modulis == "Klientai":
    st.title("DISPO – Klientai")
    with st.form("kl_form", clear_on_submit=True):
        iv = st.text_input("Įmonės pavadinimas")
        pk = st.text_input("Pašto kodas")
        ms = st.text_input("Miestas")
        rg = st.text_input("Regionas")
        pv = st.text_input("PVM numeris")
        st.markdown("**Kontaktas**")
        c1n = st.text_input("Kontaktas 1 – vardas")
        c1p = st.text_input("Kontaktas 1 – pavardė")
        c1e = st.text_input("Kontaktas 1 – el. paštas")
        c1t = st.text_input("Kontaktas 1 – telefonas")
        st.markdown("**Kontaktas dėl sąskaitų**")
        c2n = st.text_input("Kontaktas 2 – vardas")
        c2p = st.text_input("Kontaktas 2 – pavardė")
        c2e = st.text_input("Kontaktas 2 – el. paštas")
        c2t = st.text_input("Kontaktas 2 – telefonas")
        coface = st.number_input("COFACE limitas", min_value=0.0)
        likes = st.number_input("Likes limitas", min_value=0.0)
        ats_budas = st.selectbox("Atsiskaitymo būdas", ["originalūs dokumentai","platforma","skanuoti dokumentai"])
        ats_terminas = st.text_input("Atsiskaitymo terminas (dienomis)")
        sb = st.form_submit_button("💾 Išsaugoti")
    if sb:
        if not iv:
            st.warning("⚠️ Pavadinimas būtinas.")
        else:
            # unikalumas
            exists = c.execute(
                "SELECT 1 FROM klientai WHERE pavadinimas = ? AND pasto_kodas = ? AND miestas = ?",
                (iv, pk, ms)
            ).fetchone()
            if exists:
                st.error("❌ Toks klientas jau egzistuoja.")
            else:
                musu = coface / 3 if coface else 0
                try:
                    c.execute(
                        "INSERT INTO klientai (pavadinimas,pasto_kodas,miestas,regionas,vat_numeris,contact1_vardas,contact1_pavarde,contact1_email,contact1_telefonas,contact2_vardas,contact2_pavarde,contact2_email,contact2_telefonas,coface_limitas,musu_limitas,likes_limitas,atsiskaitymo_budas,atsiskaitymo_terminas) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (iv, pk, ms, rg, pv, c1n, c1p, c1e, c1t, c2n, c2p, c2e, c2t, coface, musu, likes, ats_budas, ats_terminas)
                    )
                    conn.commit(); st.success("✅ Išsaugojau.")
                except Exception as e:
                    st.error(f"❌ Klaida: {e}")
    st.dataframe(pd.read_sql_query("SELECT * FROM klientai", conn))

# ─── DARBUOTOJAI ─────────────────────────────────────────────────────────────
elif modulis == "Darbuotojai":
    st.title("DISPO – Darbuotojai")
    p_list = [r[0] for r in c.execute(
        "SELECT reiksme FROM lookup WHERE modulis = ? AND kategorija = ?", (modulis, "pareigybe")
    ).fetchall()]
    g_list = [r[2] for r in c.execute("SELECT id,numeris,pavadinimas FROM grupes").fetchall()]
    with st.form("emp_form", clear_on_submit=True):
        vd = st.text_input("Vardas"); pv = st.text_input("Pavardė")
        if p_list: pg = st.selectbox("Pareigybė", p_list)
        else: pg = st.text_input("Pareigybė")
        if g_list: gr = st.selectbox("Grupė", g_list)
        else: gr = st.text_input("Grupė")
        em = st.text_input("El. paštas"); ph = st.text_input("Telefonas")
        sb = st.form_submit_button("💾 Išsaugoti")
    if sb:
        if not vd or not pv: st.warning("⚠️ Vardas ir pavardė būtini.")
        else:
            try:
                c.execute(
                    "INSERT INTO darbuotojai (vardas,pavarde,pareigybe,el_pastas,telefonas,grupe) VALUES(?,?,?,?,?,?)",
                    (vd,pv,pg,em,ph,gr)
                )
                conn.commit(); st.success("✅ Išsaugojau.")
            except Exception as e:
                st.error(f"❌ Klaida: {e}")
    st.dataframe(pd.read_sql_query("SELECT * FROM darbuotojai", conn))
