import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, time, timedelta

# ─── 1. Prisijungimas prie DB ────────────────────────────────────────────────
conn = sqlite3.connect('dispo_new.db', check_same_thread=False)
c    = conn.cursor()

# ─── 2. Lentelių kūrimas ─────────────────────────────────────────────────────
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
CREATE TABLE IF NOT EXISTS pakrovimai (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    krovinys_id INTEGER,
    tipas TEXT,
    data TEXT,
    laikas_nuo TEXT,
    laikas_iki TEXT,
    adresas TEXT
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

# ─── 3. Moduliai ─────────────────────────────────────────────────────────────
modules = [
    "Kroviniai", "Vilkikai", "Priekabos",
    "Grupės", "Vairuotojai", "Klientai",
    "Darbuotojai", "Nustatymai"
]
modulis = st.sidebar.selectbox("📂 Pasirink modulį", modules)

# ─── 4. NUSTATYMAI ────────────────────────────────────────────────────────────
if modulis == "Nustatymai":
    st.title("DISPO – Sąrašų valdymas")

    # Įkeliame esamas kategorijas
    kategorijos = [r[0] for r in c.execute("SELECT DISTINCT kategorija FROM lookup").fetchall()]

    # Pasirenkame arba įvedame
    col1, col2 = st.columns(2)
    esama     = col1.selectbox("Pasirink esamą kategoriją", [""] + kategorijos, key="nm_esama")
    naujaKat  = col2.text_input("Arba įvesk naują kategoriją", key="nm_nauja")
    kategorija= naujaKat.strip() if naujaKat else esama

    st.markdown("---")
    if kategorija:
        st.subheader(f"Reikšmės kategorijoje: **{kategorija}**")

        # Rodome ir valdome reikšmes
        values = [r[0] for r in c.execute(
            "SELECT reiksme FROM lookup WHERE kategorija = ?", (kategorija,)
        ).fetchall()]
        st.write(values or "_(nerasta)_")

        naujaReiksme = st.text_input("Pridėti naują reikšmę", key="nm_new")
        if st.button("➕ Pridėti reikšmę", key="nm_add"):
            if naujaReiksme:
                try:
                    c.execute("INSERT INTO lookup (kategorija,reiksme) VALUES (?,?)",
                              (kategorija, naujaReiksme))
                    conn.commit()
                    st.experimental_rerun()
                except sqlite3.IntegrityError:
                    st.warning("⚠️ Toks elementas jau egzistuoja.")

        istr = st.selectbox("Ištrinti reikšmę", [""] + values, key="nm_del_sel")
        if st.button("🗑 Ištrinti reikšmę", key="nm_del"):
            if istr:
                c.execute("DELETE FROM lookup WHERE kategorija=? AND reiksme=?",
                          (kategorija, istr))
                conn.commit()
                st.experimental_rerun()
    else:
        st.info("Pasirink arba įvesk kategoriją, kad valdytum reikšmes.")

# ─── 5. KROVINIAI ──────────────────────────────────────────────────────────────
elif modulis == "Kroviniai":
    st.title("DISPO – Krovinių valdymas")

    # Paruošiame adresų list'us
    if "loads" not in st.session_state:
        st.session_state.loads = [{"data":date.today(),"nuo":time(8,0),"iki":time(17,0),"adresas":""}]
    if "unloads" not in st.session_state:
        st.session_state.unloads = [{"data":date.today()+timedelta(days=1),"nuo":time(8,0),"iki":time(17,0),"adresas":""}]

    c1, c2 = st.columns(2)
    if c1.button("➕ Pridėti pakrovimą"):
        st.session_state.loads.append({"data":date.today(),"nuo":time(8,0),"iki":time(17,0),"adresas":""})
    if c2.button("➕ Pridėti iškrovimą"):
        st.session_state.unloads.append({"data":date.today()+timedelta(days=1),"nuo":time(8,0),"iki":time(17,0),"adresas":""})

    # Klientas viršuje
    klientai = c.execute("SELECT id,pavadinimas,post_kodas,miestas FROM klientai").fetchall()
    opts      = {f"{r[1]} {r[2]} {r[3]}":r[0] for r in klientai}
    if opts:
        klientas = st.selectbox("Klientas", list(opts.keys()), key="kr_kli")
    else:
        klientas = st.text_input("Klientas", key="kr_kli_txt")

    # Forma
    with st.form("kroviniai_forma", clear_on_submit=False):
        uzs_nr   = st.text_input("Užsakymo numeris", key="kr_uzs")
        pak_num  = st.text_input("Pakrovimo numeris", key="kr_pak_num")

        pak_data = st.date_input("Pakrovimo data", date.today(), key="kr_pak_data")
        pak_nuo  = st.time_input("Laikas nuo (pakrovimo)", time(8,0), key="kr_pak_nuo")
        pak_iki  = st.time_input("Laikas iki (pakrovimo)", time(17,0), key="kr_pak_iki")

        isk_data = st.date_input("Iškrovimo data", pak_data+timedelta(days=1), key="kr_isk_data")
        isk_nuo  = st.time_input("Laikas nuo (iškrovimo)", time(8,0), key="kr_isk_nuo")
        isk_iki  = st.time_input("Laikas iki (iškrovimo)", time(17,0), key="kr_isk_iki")

        pak_sal  = st.text_input("Pakrovimo šalis", key="kr_pak_sal")
        pak_mi   = st.text_input("Pakrovimo miestas", key="kr_pak_mi")
        isk_sal  = st.text_input("Iškrovimo šalis", key="kr_isk_sal")
        isk_mi   = st.text_input("Iškrovimo miestas", key="kr_isk_mi")

        vilk_list = [r[0] for r in c.execute("SELECT numeris,priekaba FROM vilkikai").fetchall()]
        if vilk_list:
            vilk     = st.selectbox("Vilkikas", vilk_list, key="kr_vilk")
        else:
            vilk     = st.text_input("Vilkikas", key="kr_vilk_txt")
        priek     = f"PR{vilk[-3:]}" if len(vilk)>=3 else ""
        st.text_input("Priekaba", value=priek, disabled=True, key="kr_priek")

        vadyb     = f"vadyb_{vilk.lower()}" if vilk else ""
        st.text_input("Ats. vadybininkas", value=vadyb, disabled=True, key="kr_vadyb")

        km        = st.text_input("Kilometrai", key="kr_km")
        fr        = st.text_input("Frachtas (€)", key="kr_fr")
        sv        = st.text_input("Svoris (kg)", key="kr_sv")
        pal       = st.text_input("Padėklų skaičius", key="kr_pal")

        bus_opts  = [r[0] for r in c.execute("SELECT reiksme FROM lookup WHERE kategorija='busena'").fetchall()]
        if bus_opts:
            bus    = st.selectbox("Būsena", bus_opts, key="kr_bus")
        else:
            bus    = st.selectbox("Būsena", ["suplanuotas","pakrautas","iškrautas"], key="kr_bus_def")

        submit = st.form_submit_button("💾 Įrašyti krovinį")

    # Įrašymas
    if submit:
        if pak_data > isk_data:
            st.error("❌ Pakrovimo data negali būti vėlesnė už iškrovimo datą.")
        elif not klientas or not uzs_nr:
            st.error("❌ Privalomi laukai: Klientas ir užsakymo numeris.")
        else:
            cnt = c.execute("SELECT COUNT(*) FROM kroviniai WHERE uzsakymo_numeris=?", (uzs_nr,)).fetchone()[0]
            if cnt:
                st.warning("🔔 Toks numeris jau yra – ID bus naujas, numerį palieku.")

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
                klientas, uzs_nr, pak_num,
                str(pak_data), str(pak_nuo), str(pak_iki),
                str(isk_data), str(isk_nuo), str(isk_iki),
                pak_sal, pak_mi,
                isk_sal, isk_mi,
                vilk, pr, vadyb,
                int(km or 0), float(fr or 0), int(sv or 0), int(pal or 0), bus
            ))
            conn.commit()
            st.success("✅ Krovinys įrašytas.")

    # Sąrašas + detali peržiūra
    st.subheader("📋 Krovinių sąrašas")
    df = pd.read_sql_query("""
        SELECT id, klientas, uzsakymo_numeris,
               pakrovimo_data, iskrovimo_data,
               vilkikas, priekaba, busena
        FROM kroviniai
    """, conn)
    st.dataframe(df, use_container_width=True)

    sel = st.selectbox(
        "Peržiūrėti krovinio detales",
        df.apply(lambda r: f"{r.id} – {r.uzsakymo_numeris}", axis=1),
        key="kr_det"
    )
    sel_id = int(sel.split(" – ")[0])

    det = c.execute("""
        SELECT klientas, uzsakymo_numeris, pakrovimo_numeris,
               pakrovimo_data, pakrovimo_laikas_nuo, pakrovimo_laikas_iki,
               iskrovimo_data, iskrovimo_laikas_nuo, iskrovimo_laikas_iki,
               pakrovimo_salis, pakrovimo_miestas,
               iskrovimo_salis, iskrovimo_miestas,
               vilkikas, priekaba, atsakingas_vadybininkas,
               kilometrai, frachtas, svoris, paleciu_skaicius, busena
        FROM kroviniai WHERE id = ?
    """, (sel_id,)).fetchone()
    cols = [c[0] for c in c.description]
    detail = dict(zip(cols, det))

    st.subheader("🔍 Krovinio detalės")
    st.json(detail)

# ─── 6. VILKIKAI ───────────────────────────────────────────────────────────────
elif modulis == "Vilkikai":
    st.title("DISPO – Vilkikų valdymas")
    with st.form("vilk_form", clear_on_submit=True):
        nr    = st.text_input("Numeris")
        marks = [r[0] for r in c.execute("SELECT reiksme FROM lookup WHERE kategorija='vilkiku_marke'").fetchall()]
        if marks:
            mk = st.selectbox("Markė", marks)
        else:
            mk = st.text_input("Markė")
        pm = st.text_input("Pagaminimo metai")
        ta = st.date_input("Tech. apžiūra")
        vd = st.text_input("Vadybininkas")
        vv = st.text_input("Vairuotojai (kableliais)")
        pr = st.text_input("Priekaba")
        sb = st.form_submit_button("💾 Įrašyti vilkiką")
    if sb:
        if not nr:
            st.warning("⚠️ Numeris būtinas.")
        else:
            c.execute("""
                INSERT INTO vilkikai (
                    numeris, marke, pagaminimo_metai,
                    tech_apziura, vadybininkas,
                    vairuotojai, priekaba
                ) VALUES (?,?,?,?,?,?,?)
            """, (nr, mk, int(pm or 0), str(ta), vd, vv, pr))
            conn.commit()
            st.success("✅ Vilkikas įrašytas.")
    st.dataframe(pd.read_sql_query("SELECT * FROM vilkikai", conn))

# ─── 7. PRIEKABOS ───────────────────────────────────────────────────────────────
elif modulis == "Priekabos":
    st.title("DISPO – Priekabų valdymas")
    with st.form("priek_form", clear_on_submit=True):
        tips = [r[0] for r in c.execute("SELECT reiksme FROM lookup WHERE kategorija='priekabu_tipas'").fetchall()]
        if tips:
            tp = st.selectbox("Tipas", tips)
        else:
            tp = st.text_input("Tipas")
        num = st.text_input("Numeris")
        mr  = st.text_input("Markė")
        pm  = st.text_input("Pagaminimo metai")
        ta  = st.date_input("Tech. apžiūra")
        pv  = st.text_input("Priskirtas vilkikas")
        sb  = st.form_submit_button("💾 Išsaugoti priekabą")
    if sb:
        if not num:
            st.warning("⚠️ Numeris būtinas.")
        else:
            c.execute("""
                INSERT INTO priekabos (
                    priekabu_tipas, numeris, marke,
                    pagaminimo_metai, tech_apziura, priskirtas_vilkikas
                ) VALUES (?,?,?,?,?,?)
            """, (tp, num, mr, int(pm or 0), str(ta), pv))
            conn.commit()
            st.success("✅ Priekaba įrašyta.")
    st.dataframe(pd.read_sql_query("SELECT * FROM priekabos", conn))

# ─── 8. GRUPĖS ─────────────────────────────────────────────────────────────────
elif modulis == "Grupės":
    st.title("DISPO – Darbo grupių valdymas")
    with st.form("grp_form", clear_on_submit=True):
        nr = st.text_input("Numeris")
        pv = st.text_input("Pavadinimas")
        ap = st.text_area("Aprašymas")
        sb = st.form_submit_button("💾 Išsaugoti grupę")
    if sb:
        if nr and pv:
            c.execute("INSERT INTO grupes(numeris,pavadinimas,aprasymas) VALUES(?,?,?)", (nr,pv,ap))
            conn.commit(); st.success("✅ Grupė įrašyta.")
        else:
            st.warning("⚠️ Numeris ir pavadinimas būtini.")
    st.dataframe(pd.read_sql_query("SELECT * FROM grupes", conn))

# ─── 9. VAIRUOTOJAI ─────────────────────────────────────────────────────────────
elif modulis == "Vairuotojai":
    st.title("DISPO – Vairuotojų valdymas")
    with st.form("drv_form", clear_on_submit=True):
        vd = st.text_input("Vardas")
        pv = st.text_input("Pavardė")
        gm = st.text_input("Gimimo metai")
        tt = st.text_input("Tautybė")
        vk = st.text_input("Priskirtas vilkikas")
        sb = st.form_submit_button("💾 Įrašyti vairuotoją")
    if sb:
        if vd and pv:
            c.execute("""
                INSERT INTO vairuotojai (
                    vardas,pavarde,gimimo_metai,tautybe,priskirtas_vilkikas
                ) VALUES(?,?,?,?,?)
            """, (vd,pv,int(gm or 0),tt,vk))
            conn.commit(); st.success("✅ Vairuotojas įrašytas.")
        else:
            st.warning("⚠️ Vardas ir pavardė būtini.")
    st.dataframe(pd.read_sql_query("SELECT * FROM vairuotojai", conn))

# ─── 10. KLIENTAI ───────────────────────────────────────────────────────────────
elif modulis == "Klientai":
    st.title("DISPO – Klientų valdymas")
    with st.form("kl_form", clear_on_submit=True):
        pavadinimas = st.text_input("Įmonės pavadinimas")
        vat         = st.text_input("PVM (VAT) numeris")
        c1, c2      = st.columns(2)
        miestas     = c1.text_input("Miestas")
        post_kodas  = c2.text_input("Pašto kodas")
        st.markdown("**Kontaktas**")
        c3, c4      = st.columns(2)
        kv          = c3.text_input("Vardas")
        kp          = c4.text_input("Pavardė")
        c5, c6      = st.columns(2)
        ke          = c5.text_input("El. paštas")
        kt          = c6.text_input("Telefonas")
        st.markdown("**Kontaktas sąskaitoms**")
        c7, c8      = st.columns(2)
        sv          = c7.text_input("Vardas")
        sp          = c8.text_input("Pavardė")
        c9, c10     = st.columns(2)
        se          = c9.text_input("El. paštas")
        stl         = c10.text_input("Telefonas")
        coface      = st.number_input("COFACE limitas", min_value=0.0, step=0.01)
        musu        = round(coface/3,2); st.write(f"Mūsų limitas: {musu}")
        ats_budas    = st.selectbox("Atsiskaitymo būdas", ["originalūs dokumentai","platforma","skanuoti dokumentai"])
        ats_terminas = st.text_input("Atsiskaitymo terminas")
        sb           = st.form_submit_button("💾 Išsaugoti klientą")
    if sb:
        d = c.execute("""
            SELECT COUNT(*) FROM klientai WHERE pavadinimas=? AND miestas=? AND post_kodas=?
        """, (pavadinimas, miestas, post_kodas)).fetchone()[0]
        if d:
            st.error("❌ Toks klientas jau yra.")
        else:
            c.execute("""
                INSERT INTO klientai (
                    pavadinimas,vat_numeris,miestas,post_kodas,
                    kont_vardas,kont_pavarde,kont_email,kont_tel,
                    s_vardas,s_pavarde,s_email,s_tel,
                    coface_limitas,musu_limitas,ats_budas,ats_terminas
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                pavadinimas,vat,miestas,post_kodas,
                kv,kp,ke,kt,
                sv,sp,se,stl,
                coface,musu,ats_budas,ats_terminas
            ))
            conn.commit()
            st.success("✅ Klientas įrašytas.")
    st.dataframe(pd.read_sql_query("SELECT * FROM klientai", conn))

# ─── 11. DARBUOTOJAI ───────────────────────────────────────────────────────────
elif modulis == "Darbuotojai":
    st.title("DISPO – Darbuotojų valdymas")
    p_list = [r[0] for r in c.execute("SELECT reiksme FROM lookup WHERE kategorija='pareigybe'").fetchall()]
    g_list = [r[2] for r in c.execute("SELECT id,numeris,pavadinimas FROM grupes").fetchall()]
    with st.form("emp_form", clear_on_submit=True):
        vd = st.text_input("Vardas")
        pv = st.text_input("Pavardė")
        pg = st.selectbox("Pareigybė", p_list) if p_list else st.text_input("Pareigybė")
        gr = st.selectbox("Grupė", g_list)   if g_list else st.text_input("Grupė")
        em = st.text_input("El. paštas")
        ph = st.text_input("Telefonas")
        sb = st.form_submit_button("💾 Išsaugoti darbuotoją")
    if sb:
        if vd and pv:
            c.execute("""
                INSERT INTO darbuotojai (
                    vardas,pavarde,pareigybe,el_pastas,telefonas,grupe
                ) VALUES (?,?,?,?,?,?)
            """, (vd,pv,pg,em,ph,gr))
            conn.commit(); st.success("✅ Darbuotojas įrašytas.")
        else:
            st.warning("⚠️ Vardas ir pavardė būtini.")
    st.dataframe(pd.read_sql_query("SELECT * FROM darbuotojai", conn))
