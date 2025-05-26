import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, time, timedelta

# ─── Duomenų bazės prisijungimas ───────────────────────────────────────────────
conn = sqlite3.connect('dispo_new.db', check_same_thread=False)
c = conn.cursor()

# ─── Lentelių kūrimas ─────────────────────────────────────────────────────────
c.execute("""
CREATE TABLE IF NOT EXISTS lookup (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kategorija TEXT,
    reiksme TEXT UNIQUE
)
""")

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
    tech_apziura DATE,
    vadybininkas TEXT,
    vairuotojai TEXT,
    priekaba TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS priekabos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    priekabu_tipas TEXT,
    numeris TEXT UNIQUE,
    marke TEXT,
    pagaminimo_metai INTEGER,
    tech_apziura DATE,
    priskirtas_vilkikas TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS grupes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numeris TEXT UNIQUE,
    pavadinimas TEXT,
    aprasymas TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS vairuotojai (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vardas TEXT,
    pavarde TEXT,
    gimimo_metai INTEGER,
    tautybe TEXT,
    priskirtas_vilkikas TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS klientai (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pavadinimas TEXT,
    vat_numeris TEXT,
    miestas TEXT,
    post_kodas TEXT,
    kont_vardas TEXT,
    kont_pavarde TEXT,
    kont_email TEXT,
    kont_tel TEXT,
    s_vardas TEXT,
    s_pavarde TEXT,
    s_email TEXT,
    s_tel TEXT,
    coface_limitas REAL,
    musu_limitas REAL,
    ats_budas TEXT,
    ats_terminas TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS darbuotojai (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vardas TEXT,
    pavarde TEXT,
    pareigybe TEXT,
    el_pastas TEXT,
    telefonas TEXT,
    grupe TEXT
)
""")

conn.commit()

# ─── Modulių sąrašas ─────────────────────────────────────────────────────────
moduliai = [
    "Kroviniai", "Vilkikai", "Priekabos",
    "Grupės", "Vairuotojai", "Klientai",
    "Darbuotojai", "Nustatymai"
]
modulis = st.sidebar.radio("📂 Pasirink modulį", moduliai)

# ─── NUSTATYMAI: dinamiškas lookup valdymas ─────────────────────────────────
if modulis == "Nustatymai":
    st.title("DISPO – Sąrašų valdymas")
    # 1) užkraunam kategorijas
    kategorijos = [row[0] for row in c.execute(
        "SELECT DISTINCT kategorija FROM lookup"
    ).fetchall()]
    # 2) renkamės arba kuriame naują
    col1, col2 = st.columns(2)
    esama = col1.selectbox("Esama kategorija", [""] + kategorijos)
    nauja_kat = col2.text_input("Arba nauja kategorija")
    kategorija = nauja_kat.strip() if nauja_kat else esama
    st.markdown("---")

    if kategorija:
        st.subheader(f"Kategorija: **{kategorija}**")
        # 3a) esamos reikšmės
        values = [r[0] for r in c.execute(
            "SELECT reiksme FROM lookup WHERE kategorija = ?", (kategorija,)
        ).fetchall()]
        st.write(values or "_(nerasta reikšmių)_")
        # 3b) pridėti naują
        nauja_reiksme = st.text_input("Pridėti naują reikšmę")
        if st.button("➕ Pridėti reikšmę"):
            if nauja_reiksme:
                try:
                    c.execute(
                        "INSERT INTO lookup(kategorija, reiksme) VALUES(?,?)",
                        (kategorija, nauja_reiksme)
                    )
                    conn.commit()
                    st.success(f"✅ Pridėta: {nauja_reiksme}")
                except sqlite3.IntegrityError:
                    st.warning("⚠️ Tokia reikšmė jau egzistuoja.")
        # 3c) trinti
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

    # Dinaminiai pakrovimai
    if "loads" not in st.session_state:
        st.session_state.loads = [{
            "data": date.today(),
            "laikas_nuo": time(8, 0),
            "laikas_iki": time(17, 0)
        }]
    st.markdown("### Pakrovimai")
    for i, load in enumerate(st.session_state.loads):
        with st.expander(f"Pakrovimas #{i+1}", expanded=True):
            d = st.date_input("Data", value=load["data"], key=f"load_date_{i}")
            nuo = st.time_input("Laikas nuo", value=load["laikas_nuo"], key=f"load_nuo_{i}")
            iki = st.time_input("Laikas iki", value=load["laikas_iki"], key=f"load_iki_{i}")
            st.session_state.loads[i] = {"data": d, "laikas_nuo": nuo, "laikas_iki": iki}
    if st.button("➕ Pridėti pakrovimą"):
        st.session_state.loads.append({
            "data": date.today(),
            "laikas_nuo": time(8, 0),
            "laikas_iki": time(17, 0)
        })

    # Dinaminiai iškrovimai
    if "unloads" not in st.session_state:
        st.session_state.unloads = [{
            "data": date.today() + timedelta(days=1),
            "laikas_nuo": time(8, 0),
            "laikas_iki": time(17, 0)
        }]
    st.markdown("### Iškrovimai")
    for i, ul in enumerate(st.session_state.unloads):
        with st.expander(f"Iškrovimas #{i+1}", expanded=True):
            d = st.date_input("Data", value=ul["data"], key=f"unload_date_{i}")
            nuo = st.time_input("Laikas nuo", value=ul["laikas_nuo"], key=f"unload_nuo_{i}")
            iki = st.time_input("Laikas iki", value=ul["laikas_iki"], key=f"unload_iki_{i}")
            st.session_state.unloads[i] = {"data": d, "laikas_nuo": nuo, "laikas_iki": iki}
    if st.button("➕ Pridėti iškrovimą"):
        st.session_state.unloads.append({
            "data": date.today() + timedelta(days=1),
            "laikas_nuo": time(8, 0),
            "laikas_iki": time(17, 0)
        })

    # Formos dalis
    with st.form("krovinio_forma", clear_on_submit=False):
        # Klientas iš Klientai
        klientai = c.execute(
            "SELECT id, pavadinimas, post_kodas, miestas FROM klientai"
        ).fetchall()
        opts = {f"{k[1]} {k[2]} {k[3]}": k[0] for k in klientai}
        if opts:
            klientas_label = st.selectbox("Klientas", list(opts.keys()))
        else:
            st.warning("⚠️ Nėra įvestų klientų.")
            klientas_label = ""
        uzs_raw = st.text_input("Užsakymo numeris")

        # Vilkikas + priekaba
        vilk = c.execute("SELECT numeris, priekaba FROM vilkikai").fetchall()
        vilk_opts = {v[0]: v[1] for v in vilk}
        if vilk_opts:
            vilkikas = st.selectbox("Vilkikas", list(vilk_opts.keys()))
            priekaba = vilk_opts[vilkikas]
        else:
            vilkikas = st.text_input("Vilkikas (nėra įvestų)")
            priekaba = ""
        st.text_input("Priekaba", value=priekaba, disabled=True)

        # Būsena
        bus = [r[0] for r in c.execute(
            "SELECT reiksme FROM lookup WHERE kategorija='busena'"
        ).fetchall()]
        busena = st.selectbox("Būsena", bus or ["suplanuotas","pakrautas","iškrautas"])

        submit = st.form_submit_button("💾 Įrašyti krovinį")

    if submit:
        # Unikalus užsakymo numeris
        egz = [r[0] for r in c.execute(
            "SELECT uzsakymo_numeris FROM kroviniai WHERE uzsakymo_numeris LIKE ?", (f"{uzs_raw}%",)
        ).fetchall()]
        numeris = uzs_raw
        if uzs_raw in egz:
            s = sum(1 for x in egz if x.startswith(uzs_raw))
            numeris = f"{uzs_raw}-{s}"
            st.warning(f"🔔 Numeris egzistuoja – išsaugotas kaip `{numeris}`.")

        # Pirmas pakrovimas ir paskutinis iškrovimas
        first = st.session_state.loads[0]
        last  = st.session_state.unloads[-1]

        # Įrašymas
        c.execute("""
            INSERT INTO kroviniai (
                klientas, uzsakymo_numeris,
                pakrovimo_data, pakrovimo_laikas_nuo, pakrovimo_laikas_iki,
                iskrovimo_data, iskrovimo_laikas_nuo, iskrovimo_laikas_iki,
                vilkikas, priekaba, busena
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (
            klientas_label, numeris,
            str(first["data"]), str(first["laikas_nuo"]), str(first["laikas_iki"]),
            str(last["data"]),  str(last["laikas_nuo"]),  str(last["laikas_iki"]),
            vilkikas, priekaba, busena
        ))
        conn.commit()
        st.success("✅ Krovinių užsakymas sėkmingai įrašytas.")

    # Rezultatų lentelė
    df = pd.read_sql_query("""
        SELECT klientas, uzsakymo_numeris,
               pakrovimo_data, pakrovimo_laikas_nuo,
               iskrovimo_data, iskrovimo_laikas_iki,
               vilkikas, priekaba, busena
        FROM kroviniai
    """, conn)
    st.dataframe(df)

# ─── VILKIKAI ────────────────────────────────────────────────────────────────
elif modulis == "Vilkikai":
    st.title("DISPO – Vilkikų valdymas")
    with st.form("vilkikai_forma", clear_on_submit=True):
        numeris = st.text_input("Numeris")
        marks = [r[0] for r in c.execute(
            "SELECT reiksme FROM lookup WHERE kategorija='vilkiku_marke'"
        ).fetchall()]
        if marks:
            marke = st.selectbox("Markė", marks)
        else:
            marke = st.text_input("Markė")
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
                """, (numeris, marke, int(pag_metai or 0), str(tech_apz),
                      vadyb, vair, priek))
                conn.commit()
                st.success("✅ Vilkikas įrašytas.")
            except Exception as e:
                st.error(f"❌ Klaida: {e}")
    st.dataframe(pd.read_sql_query("SELECT * FROM vilkikai", conn))

# ─── PRIEKABOS ───────────────────────────────────────────────────────────────
elif modulis == "Priekabos":
    st.title("DISPO – Priekabų valdymas")
    with st.form("priek_form", clear_on_submit=True):
        tipai = [r[0] for r in c.execute(
            "SELECT reiksme FROM lookup WHERE kategorija='priekabu_tipas'"
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
                conn.commit()
                st.success("✅ Priekaba įrašyta.")
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
                st.success("✅ Grupė įrašyta.")
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
            st.warning("⚠️ Vardas ir pavardė būtini.")
        else:
            try:
                c.execute("""
                    INSERT INTO vairuotojai (
                        vardas,pavarde,gimimo_metai,tautybe,priskirtas_vilkikas
                    ) VALUES (?,?,?,?,?)
                """, (vd, pv, int(gm or 0), tt, pvk))
                conn.commit()
                st.success("✅ Vairuotojas įrašytas.")
            except Exception as e:
                st.error(f"❌ Klaida: {e}")
    st.dataframe(pd.read_sql_query("SELECT * FROM vairuotojai", conn))

# ─── KLIENTAI ────────────────────────────────────────────────────────────────
elif modulis == "Klientai":
    st.title("DISPO – Klientų valdymas")
    with st.form("kl_form", clear_on_submit=True):
        pavadinimas = st.text_input("Įmonės pavadinimas")
        vat = st.text_input("PVM (VAT) numeris")
        col1, col2 = st.columns(2)
        miestas = col1.text_input("Miestas")
        post_kodas = col2.text_input("Pašto kodas")
        st.markdown("**Kontaktas**")
        col3, col4 = st.columns(2)
        kont_vardas = col3.text_input("Vardas")
        kont_pavarde = col4.text_input("Pavardė")
        col5, col6 = st.columns(2)
        kont_email = col5.text_input("El. paštas")
        kont_tel = col6.text_input("Telefonas")
        st.markdown("**Kontaktas dėl sąskaitų**")
        col7, col8 = st.columns(2)
        s_vardas = col7.text_input("Vardas (sąskaitos)")
        s_pavarde = col8.text_input("Pavardė (sąskaitos)")
        col9, col10 = st.columns(2)
        s_email = col9.text_input("El. paštas (sąskaitos)")
        s_tel = col10.text_input("Telefonas (sąskaitos)")
        st.markdown("**Limitai**")
        coface = st.number_input("COFACE limitas", min_value=0.0, step=0.01)
        musu = round(coface / 3, 2)
        st.write(f"Mūsų limitas (COFACE/3): {musu}")
        ats_budas = st.selectbox("Atsiskaitymo būdas", [
            "originalūs dokumentai", "platforma", "skanuoti dokumentai"
        ])
        ats_terminas = st.text_input("Atsiskaitymo terminas")
        submit = st.form_submit_button("💾 Įrašyti klientą")
    if submit:
        dub = c.execute("""
            SELECT COUNT(*) FROM klientai
            WHERE pavadinimas=? AND miestas=? AND post_kodas=?
        """, (pavadinimas, miestas, post_kodas)).fetchone()[0]
        if dub:
            st.error("❌ Toks klientas jau įvestas.")
        else:
            c.execute("""
                INSERT INTO klientai (
                    pavadinimas, vat_numeris,
                    miestas, post_kodas,
                    kont_vardas, kont_pavarde, kont_email, kont_tel,
                    s_vardas, s_pavarde, s_email, s_tel,
                    coface_limitas, musu_limitas,
                    ats_budas, ats_terminas
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                pavadinimas, vat,
                miestas, post_kodas,
                kont_vardas, kont_pavarde, kont_email, kont_tel,
                s_vardas, s_pavarde, s_email, s_tel,
                coface, musu,
                ats_budas, ats_terminas
            ))
            conn.commit()
            st.success("✅ Klientas įrašytas.")
    st.dataframe(pd.read_sql_query("SELECT * FROM klientai", conn))

# ─── DARBUOTOJAI ─────────────────────────────────────────────────────────────
elif modulis == "Darbuotojai":
    st.title("DISPO – Darbuotojai")
    # pareigybės iš lookup
    p_list = [r[0] for r in c.execute(
        "SELECT reiksme FROM lookup WHERE kategorija='pareigybe'"
    ).fetchall()]
    # grupės iš grupes
    g_list = [r[2] for r in c.execute("SELECT id,numeris,pavadinimas FROM grupes").fetchall()]
    with st.form("emp_form", clear_on_submit=True):
        vd = st.text_input("Vardas")
        pv = st.text_input("Pavardė")
        if p_list:
            pg = st.selectbox("Pareigybė", p_list)
        else:
            pg = st.text_input("Pareigybė")
        if g_list:
            gr = st.selectbox("Grupė", g_list)
        else:
            gr = st.text_input("Grupė")
        em = st.text_input("El. paštas")
        ph = st.text_input("Telefonas")
        sb = st.form_submit_button("💾 Išsaugoti")
    if sb:
        if not vd or not pv:
            st.warning("⚠️ Vardas ir pavardė būtini.")
        else:
            try:
                c.execute("""
                    INSERT INTO darbuotojai (
                        vardas,pavarde,pareigybe,el_pastas,telefonas,grupe
                    ) VALUES (?,?,?,?,?,?)
                """, (vd, pv, pg, em, ph, gr))
                conn.commit()
                st.success("✅ Darbuotojas įrašytas.")
            except Exception as e:
                st.error(f"❌ Klaida: {e}")
    st.dataframe(pd.read_sql_query("SELECT * FROM darbuotojai", conn))

