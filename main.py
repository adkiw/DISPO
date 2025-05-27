import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, time, timedelta

# ─── Duomenų bazės prisijungimas ───────────────────────────────────────────────
conn = sqlite3.connect('dispo_new.db', check_same_thread=False)
c = conn.cursor()

# ─── Lentelių kūrimas ──────────────────────────────────────────────────────────
table_ddls = {
    "lookup": """
        CREATE TABLE IF NOT EXISTS lookup (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kategorija TEXT,
            reiksme TEXT UNIQUE
        )
    """,
    "klientai": """
        CREATE TABLE IF NOT EXISTS klientai (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pavadinimas TEXT,
            vat_numeris TEXT,
            miestas TEXT,
            post_kodas TEXT,
            kontaktas_vardas TEXT,
            kontaktas_pavarde TEXT,
            kontaktas_email TEXT,
            kontaktas_telefonas TEXT,
            saskaita_vardas TEXT,
            saskaita_pavarde TEXT,
            saskaita_email TEXT,
            saskaita_telefonas TEXT,
            coface_limitas REAL,
            musu_limit REAL,
            likes_limit REAL,
            atsiskaitymo_budas TEXT,
            atsiskaitymo_terminas TEXT,
            atsiskaitymo_naudingumas REAL,
            UNIQUE(pavadinimas,miestas,post_kodas)
        )
    """,
    "kroviniai": """
        CREATE TABLE IF NOT EXISTS kroviniai (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            klientas_id INTEGER,
            uzsakymo_numeris TEXT,
            pakrovimo_numeris TEXT,
            vilkikas TEXT,
            priekaba TEXT,
            atsakingas_vadybininkas TEXT,
            kilometrai INTEGER,
            frachtas REAL,
            svoris INTEGER,
            paleciu_skaicius INTEGER,
            busena TEXT,
            FOREIGN KEY(klientas_id) REFERENCES klientai(id)
        )
    """,
    "pakrovimai": """
        CREATE TABLE IF NOT EXISTS pakrovimai (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            krovinys_id INTEGER,
            data TEXT,
            laikas_nuo TEXT,
            laikas_iki TEXT,
            salis TEXT,
            miestas TEXT,
            adresas TEXT,
            FOREIGN KEY(krovinys_id) REFERENCES kroviniai(id)
        )
    """,
    "iskrovimai": """
        CREATE TABLE IF NOT EXISTS iskrovimai (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            krovinys_id INTEGER,
            data TEXT,
            laikas_nuo TEXT,
            laikas_iki TEXT,
            salis TEXT,
            miestas TEXT,
            adresas TEXT,
            FOREIGN KEY(krovinys_id) REFERENCES kroviniai(id)
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

# ─── Moduliai ────────────────────────────────────────────────────────────────
moduliai = [
    "Kroviniai", "Vilkikai", "Priekabos",
    "Grupės", "Vairuotojai", "Klientai",
    "Darbuotojai", "Nustatymai"
]
modulis = st.sidebar.radio("📂 Pasirink modulį", moduliai)

# ─── Nustatymai ─────────────────────────────────────────────────────────────
if modulis == "Nustatymai":
    st.title("DISPO – Sąrašų valdymas")
    kategorijos = [r[0] for r in c.execute(
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
    # Klientų sąrašas formatai
    clients = c.execute("SELECT id, pavadinimas, miestas, post_kodas FROM klientai").fetchall()
    client_map = {f"{row[1]} {row[3]} {row[2]}": row[0] for row in clients}
    with st.form("krovinio_forma", clear_on_submit=False):
        st.subheader("🔹 Kliento pasirinkimas")
        if client_map:
            klientas_lbl = st.selectbox("Klientas", [""] + list(client_map.keys()))
            klientas_id = client_map.get(klientas_lbl)
        else:
            klientas_id = None
            st.warning("⚠️ Įveskite klientą Klientų modulyje.")
        st.markdown("---")
        st.subheader("🔹 Krovinio informacija")
        uzsakymo_numeris = st.text_input("Užsakymo numeris")
        pakrovimo_numeris = st.text_input("Pakrovimo numeris")
        col1, col2 = st.columns(2)
        pakrovimo_data = col1.date_input("Pakrovimo data", date.today())
        pakrovimo_laikas_nuo = col1.time_input("Laikas nuo (pakrovimas)", time(8,0))
        pakrovimo_laikas_iki = col1.time_input("Laikas iki (pakrovimas)", time(17,0))
        iskrovimo_data = col2.date_input("Iškrovimo data", pakrovimo_data + timedelta(days=1))
        iskrovimo_laikas_nuo = col2.time_input("Laikas nuo (iškrovimas)", time(8,0))
        iskrovimo_laikas_iki = col2.time_input("Laikas iki (iškrovimas)", time(17,0))
        col3, col4, col5 = st.columns(3)
        kol1 = col3
        kilometr
        ai = col3.text_input("Kilometrai")
        frachtas = col4.text_input("Frachtas (€)")
        svoris = col5.text_input("Svoris (kg)")
        paleciu = st.text_input("Padėklų skaičius")
        # Vilkikas ir būklė
        vilkikai = [r[0] for r in c.execute("SELECT numeris FROM vilkikai").fetchall()]
        if vilkikai:
            vilkikas = st.selectbox("Vilkikas", vilkikai)
            priekaba = c.execute(
                "SELECT priekaba FROM vilkikai WHERE numeris = ?", (vilkikas,)
            ).fetchone()
            priekaba = priekaba[0] if priekaba else ""
        else:
            vilkikas = st.text_input("Vilkikas (nėra įvestų)")
            priekaba = ""
        st.text_input("Priekaba", value=priekaba, disabled=True)
        # Būsena iš lookup
        busena_opt = [r[0] for r in c.execute(
            "SELECT reiksme FROM lookup WHERE kategorija = ?", ("busena",)
        ).fetchall()]
        busena = st.selectbox("Būsena", busena_opt) if busena_opt else st.text_input("Būsena")
        submit = st.form_submit_button("💾 Išsaugoti krovinį")
    if submit:
        if not klientas_id or not uzsakymo_numeris:
            st.error("❌ Privalomi laukai: Klientas ir Užsakymo numeris.")
        else:
            # Patikrinam, ar toks numeris egzistuoja
            existing = c.execute(
                "SELECT id FROM kroviniai WHERE uzsakymo_numeris = ?", (uzsakymo_numeris,)
            ).fetchone()
            km = int(ai or 0)
            fr = float(frachtas or 0)
            sv = int(svoris or 0)
            pal = int(paleciu or 0)
            if existing:
                krovinys_id = existing[0]
                c.execute("""
                    UPDATE kroviniai SET
                        klientas_id = ?, pakrovimo_numeris = ?, vilkikas = ?, priekaba = ?,
                        atsakingas_vadybininkas = ?, kilometrai = ?, frachtas = ?, svoris = ?,
                        paleciu_skaicius = ?, busena = ?
                    WHERE id = ?
                """, (
                    klientas_id, pakrovimo_numeris, vilkikas, priekaba,
                    f"vadyb_{vilkikas.lower()}", km, fr, sv, pal, busena, krovinys_id
                ))
                conn.commit()
                st.success("✅ Atnaujinau krovinį.")
            else:
                c.execute(
                    "INSERT INTO kroviniai (klientas_id, uzsakymo_numeris, pakrovimo_numeris, vilkikas, priekaba, atsakingas_vadybininkas, kilometrai, frachtas, svoris, paleciu_skaicius, busena) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        klientas_id, uzsakymo_numeris, pakrovimo_numeris,
                        vilkikas, priekaba, f"vadyb_{vilkikas.lower()}", km, fr, sv, pal, busena
                    )
                )
                conn.commit()
                st.success("✅ Krovinį išsaugojau.")
    # Santraukos lentelė: pirmas pakrovimas ir paskutinis iškrovimas
    df_summary = pd.read_sql_query("""
        SELECT k.id,
               (SELECT data FROM pakrovimai WHERE krovinys_id = k.id ORDER BY data ASC LIMIT 1) AS pirma_pakrovimo_data,
               (SELECT data FROM iskrovimai WHERE krovinys_id = k.id ORDER BY data DESC LIMIT 1) AS paskutine_iskrovimo_data,
               k.vilkikas, k.priekaba, k.busena
        FROM kroviniai k
    """, conn)
    st.subheader("📋 Krovinių santrauka")
    st.dataframe(df_summary)
    # Detalių peržiūra
    kroviniai_list = pd.read_sql_query("SELECT id, uzsakymo_numeris FROM kroviniai", conn)
    options = [f"{row.id}: {row.uzsakymo_numeris}" for row in kroviniai_list.itertuples()]
    sel = st.selectbox("Pasirinkite krovinį detaliai", [""] + options)
    if sel:
        sel_id = int(sel.split(":")[0])
        det = pd.read_sql_query("SELECT * FROM kroviniai WHERE id = ?", conn, params=(sel_id,))
        st.subheader("🔍 Krovinio detalės")
        st.write(det)
        # Pakrovimų valdymas
        with st.form("add_pakrovimas"):
            st.write("➕ Pridėti pakrovimą")
            pd_data = st.date_input("Data (pakrovimas)")
            pd_nuo = st.time_input("Nuo (pakrovimas)")
            pd_iki = st.time_input("Iki (pakrovimas)")
            pd_salis = st.text_input("Šalis (pakrovimas)")
            pd_miestas = st.text_input("Miestas (pakrovimas)")
            pd_adresas = st.text_input("Adresas (pakrovimas)")
            if st.form_submit_button("Pridėti pakrovimą"):
                c.execute(
                    "INSERT INTO pakrovimai (krovinys_id, data, laikas_nuo, laikas_iki, salis, miestas, adresas) VALUES (?,?,?,?,?,?,?)",
                    (sel_id, str(pd_data), str(pd_nuo), str(pd_iki), pd_salis, pd_miestas, pd_adresas)
                )
                conn.commit()
                st.success("✅ Pridėtas pakrovimas.")
        st.subheader("📦 Pakrovimai")
        st.dataframe(pd.read_sql_query("SELECT * FROM pakrovimai WHERE krovinys_id = ?", conn, params=(sel_id,)))
        # Iškrovimų valdymas
        with st.form("add_iskrovimas"):
            st.write("➕ Pridėti iškrovimą")
            id_data = st.date_input("Data (iškrovimas)")
            id_nuo = st.time_input("Nuo (iškrovimas)")
            id_iki = st.time_input("Iki (iškrovimas)")
            id_salis = st.text_input("Šalis (iškrovimas)")
            id_miestas = st.text_input("Miestas (iškrovimas)")
            id_adresas = st.text_input("Adresas (iškrovimas)")
            if st.form_submit_button("Pridėti iškrovimą"):
                c.execute(
                    "INSERT INTO iskrovimai (krovinys_id, data, laikas_nuo, laikas_iki, salis, miestas, adresas) VALUES (?,?,?,?,?,?,?)",
                    (sel_id, str(id_data), str(id_nuo), str(id_iki), id_salis, id_miestas, id_adresas)
                )
                conn.commit()
                st.success("✅ Pridėtas iškrovimas.")
        st.subheader("🚚 Iškrovimai")
        st.dataframe(pd.read_sql_query("SELECT * FROM iskrovimai WHERE krovinys_id = ?", conn, params=(sel_id,)))

# ─── VILKIKAI ────────────────────────────────────────────────────────────────
elif modulis == "Vilkikai":
    st.title("DISPO – Vilkikų valdymas")
    with st.form("vilkikai_forma", clear_on_submit=True):
        numeris = st.text_input("Numeris")
        marks = [r[0] for r in c.execute(
            "SELECT reiksme FROM lookup WHERE kategorija = ?", ("vilkiku_marke",)
        ).fetchall()]
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
                conn.commit()
                st.success("✅ Išsaugojau.")
            except Exception as e:
                st.error(f"❌ Klaida: {e}")
    st.dataframe(pd.read_sql_query("SELECT * FROM vilkikai", conn))

# ─── PRIEKABOS ───────────────────────────────────────────────────────────────
elif modulis == "Priekabos":
    st.title("DISPO – Priekabų valdymas")
    with st.form("priek_form", clear_on_submit=True):
        tipai = [r[0] for r in c.execute(
            "SELECT reiksme FROM lookup WHERE kategorija = ?", ("priekabu_tipas",)
        ).fetchall()]
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
                c.execute(
                    "INSERT INTO priekabos (priekabu_tipas, numeris, marke, pagaminimo_metai, tech_apziura, priskirtas_vilkikas) VALUES (?,?,?,?,?,?)",
                    (pr_tipas, num, mr, int(pm or 0), str(ta), pv)
                )
                conn.commit()
                st.success("✅ Išsaugojau.")
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
                conn.commit()
                st.success("✅ Išsaugojau.")
            except Exception as e:
                st.error(f"❌ Klaida: {e}")
    st.dataframe(pd.read_sql_query("SELECT * FROM grupes", conn))

# ─── VAIRUOTOJAI ─────────────────────────────────────────────────────────────
elif modulis == "Vairuotojai":
    st.title("DISPO – Vairuotojai")
    with st.form("drv_form", clear_on_submit=True):
        vd = st.text_input("Vardas")
        pv = st.text_input("Pavardė")
        gm = st.text_input("Gimimo metai")
        tt = st.text_input("Tautybė")
        pvk = st.text_input("Priskirtas vilkikas")
        sb = st.form_submit_button("💾 Išsaugoti")
    if sb:
        if not vd or not pv:
            st.warning("⚠️ Reikia vardo ir pavardės.")
        else:
            try:
                c.execute(
                    "INSERT INTO vairuotojai (vardas,pavarde,gimimo_metai,tautybe,priskirtas_vilkikas) VALUES(?,?,?,?,?)",
                    (vd, pv, int(gm or 0), tt, pvk)
                )
                conn.commit()
                st.success("✅ Išsaugojau.")
            except Exception as e:
                st.error(f"❌ Klaida: {e}")
    st.dataframe(pd.read_sql_query("SELECT * FROM vairuotojai", conn))

# ─── KLIENTAI ────────────────────────────────────────────────────────────────
elif modulis == "Klientai":
    st.title("DISPO – Klientai")
    with st.form("kl_form", clear_on_submit=True):
        pavadinimas = st.text_input("Įmonės pavadinimas")
        vat_numeris = st.text_input("VAT numeris")
        miestas = st.text_input("Miestas")
        post_kodas = st.text_input("Pašto kodas")
        kontaktas_vardas = st.text_input("Kontaktas - vardas")
        kontaktas_pavarde = st.text_input("Kontaktas - pavardė")
        kontaktas_email = st.text_input("Kontaktas - el. paštas")
        kontaktas_telefonas = st.text_input("Kontaktas - telefonas")
        saskaita_vardas = st.text_input("Sąskaita - vardas")
        saskaita_pavarde = st.text_input("Sąskaita - pavardė")
        saskaita_email = st.text_input("Sąskaita - el. paštas")
        saskaita_telefonas = st.text_input("Sąskaita - telefonas")
        coface_limitas = st.number_input("COFACE limitas", min_value=0.0)
        musu_limit = coface_limitas / 3 if coface_limitas else 0
        likes_limit = 0.0  # placeholder for future formula
        st.write(f"Mūsų limitas: {musu_limit}")
        st.write(f"Likes limitas: {likes_limit}")
        atsiskaitymo_budas = st.selectbox(
            "Atsiskaitymo būdas",
            ["Originalūs dokumentai", "Platforma", "Skanuoti dokumentai"]
        )
        atsiskaitymo_terminas = st.text_input("Atsiskaitymo terminas")
        atsiskaitymo_naudingumas = st.number_input("Atsiskaitymo naudingumas", value=0.0)
        sb = st.form_submit_button("💾 Išsaugoti")
    if sb:
        if not pavadinimas or not miestas or not post_kodas:
            st.warning("⚠️ Pavadinimas, miestas ir pašto kodas būtini.")
        else:
            exists = c.execute(
                "SELECT id FROM klientai WHERE pavadinimas = ? AND miestas = ? AND post_kodas = ?",
                (pavadinimas, miestas, post_kodas)
            ).fetchone()
            if exists:
                st.warning("⚠️ Toks klientas jau egzistuoja.")
            else:
                c.execute(
                    "INSERT INTO klientai (
                        pavadinimas, vat_numeris, miestas, post_kodas,
                        kontaktas_vardas, kontaktas_pavarde, kontaktas_email, kontaktas_telefonas,
                        saskaita_vardas, saskaita_pavarde, saskaita_email, saskaita_telefonas,
                        coface_limitas, musu_limit, likes_limit,
                        atsiskaitymo_budas, atsiskaitymo_terminas, atsiskaitymo_naudingumas
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        pavadinimas, vat_numeris, miestas, post_kodas,
                        kontaktas_vardas, kontaktas_pavarde, kontaktas_email, kontaktas_telefonas,
                        saskaita_vardas, saskaita_pavarde, saskaita_email, saskaita_telefonas,
                        coface_limitas, musu_limit, likes_limit,
                        atsiskaitymo_budas, atsiskaitymo_terminas, atsiskaitymo_naudingumas
                    )
                )
                conn.commit()
                st.success("✅ Išsaugojau klientą.")
    st.dataframe(pd.read_sql_query("SELECT * FROM klientai", conn))

# ─── DARBUOTOJAI ─────────────────────────────────────────────────────────────
elif modulis == "Darbuotojai":
    st.title("DISPO – Darbuotojai")
    p_list = [r[0] for r in c.execute(
        "SELECT reiksme FROM lookup WHERE kategorija = ?", ("pareigybe",)
    ).fetchall()]
    g_list = [r[2] for r in c.execute("SELECT id,numeris,pavadinimas FROM grupes").fetchall()]
    with st.form("emp_form", clear_on_submit=True):
        vd = st.text_input("Vardas")
        pv = st.text_input("Pavardė")
        pg = st.selectbox("Pareigybė", p_list) if p_list else st.text_input("Pareigybė")
        gr = st.selectbox("Grupė", g_list) if g_list else st.text_input("Grupė")
        em = st.text_input("El. paštas")
        ph = st.text_input("Telefonas")
        sb = st.form_submit_button("💾 Išsaugoti")
    if sb:
        if not vd or not pv:
            st.warning("⚠️ Vardas ir pavardė būtini.")
        else:
            try:
                c.execute(
                    "INSERT INTO darbuotojai (vardas,pavarde,pareigybe,el_pastas,telefonas,grupe) VALUES(?,?,?,?,?,?)",
                    (vd, pv, pg, em, ph, gr)
                )
                conn.commit()
                st.success("✅ Išsaugojau.")
            except Exception as e:
                st.error(f"❌ Klaida: {e}")
    st.dataframe(pd.read_sql_query("SELECT * FROM darbuotojai", conn))
