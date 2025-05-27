import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, time, timedelta

# ─── 1. Prisijungimas prie DB ─────────────────────────────────────────────────
conn = sqlite3.connect('dispo_new.db', check_same_thread=False)
c = conn.cursor()

# ─── 2. Lentelių kūrimas ────────────────────────────────────────────────────────
c.execute("""
CREATE TABLE IF NOT EXISTS lookup (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    modulis TEXT,
    kategorija TEXT,
    reiksme TEXT UNIQUE
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
    s_vardas_email TEXT,
    s_vardas_tel TEXT,
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
CREATE TABLE IF NOT EXISTS kroviniai (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id TEXT UNIQUE,
    klientas_id INTEGER,
    uzsakymo_numeris TEXT,
    pakrovimo_numeris TEXT,
    vilkikas TEXT,
    priekaba TEXT,
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

# ─── 3. Modulių meniu ───────────────────────────────────────────────────────────
moduliai = [
    "Kroviniai", "Klientai", "Vilkikai",
    "Priekabos", "Grupės", "Vairuotojai",
    "Darbuotojai", "Nustatymai"
]
modulis = st.sidebar.selectbox("📂 Pasirink modulį", moduliai)

# ─── 4. NUSTATYMAI ───────────────────────────────────────────────────────────────
if modulis == "Nustatymai":
    st.title("DISPO – Sąrašų valdymas")
    sel_mod = st.selectbox("Modulis", [m for m in moduliai if m != "Nustatymai"], key="nu_mod")
    cats = [r[0] for r in c.execute(
        "SELECT DISTINCT kategorija FROM lookup WHERE modulis = ?", (sel_mod,)
    ).fetchall()]
    esama = st.selectbox("Esama kategorija", [""] + cats, key="nu_esama")
    nauja = st.text_input("Arba įvesk naują kategoriją", key="nu_nauja")
    kat = nauja.strip() if nauja else esama

    st.markdown("---")
    if kat:
        st.subheader(f"{sel_mod} – {kat}")
        vals = [r[0] for r in c.execute(
            "SELECT reiksme FROM lookup WHERE modulis = ? AND kategorija = ?", (sel_mod, kat)
        ).fetchall()]
        st.write(vals or "_Nėra reikšmių_")
        newv = st.text_input("Pridėti naują reikšmę", key="nu_newv")
        if st.button("➕ Pridėti reikšmę", key="nu_add"):
            if newv:
                try:
                    c.execute(
                        "INSERT INTO lookup(modulis,kategorija,reiksme) VALUES(?,?,?)",
                        (sel_mod, kat, newv)
                    )
                    conn.commit()
                    st.success(f"✅ Pridėta: {newv}")
                    st.experimental_rerun()
                except sqlite3.IntegrityError:
                    st.warning("⚠️ Toks įrašas jau egzistuoja.")
        istr = st.selectbox("Ištrinti reikšmę", [""] + vals, key="nu_istr")
        if st.button("🗑 Ištrinti", key="nu_del"):
            if istr:
                c.execute(
                    "DELETE FROM lookup WHERE modulis=? AND kategorija=? AND reiksme=?",
                    (sel_mod, kat, istr)
                )
                conn.commit()
                st.success(f"✅ Ištrinta: {istr}")
                st.experimental_rerun()
    else:
        st.info("Pasirink modulį ir kategoriją arba įvesk naują.")

# ─── 5. KROVINIAI ────────────────────────────────────────────────────────────────
elif modulis == "Kroviniai":
    st.title("DISPO – Krovinių valdymas")

    # init load/unload lists
    if "loads"   not in st.session_state:
        st.session_state.loads   = [{"data": date.today(), "nuo": time(8,0), "iki": time(17,0), "adresas": ""}]
    if "unloads" not in st.session_state:
        st.session_state.unloads = [{"data": date.today()+timedelta(days=1), "nuo": time(8,0), "iki": time(17,0), "adresas": ""}]

    # buttons before form
    c1, c2 = st.columns(2)
    if c1.button("➕ Pridėti pakrovimą", key="add_load"):
        st.session_state.loads.append({"data": date.today(), "nuo": time(8,0), "iki": time(17,0), "adresas": ""})
    if c2.button("➕ Pridėti iškrovimą", key="add_unload"):
        st.session_state.unloads.append({"data": date.today()+timedelta(days=1), "nuo": time(8,0), "iki": time(17,0), "adresas": ""})

    with st.form("kro_form", clear_on_submit=False):
        # klientas
        kli = c.execute("SELECT id,pavadinimas,post_kodas,miestas FROM klientai").fetchall()
        kli_opts = {f"{r[1]} {r[2]} {r[3]}": r[0] for r in kli}
        if kli_opts:
            kl_lbl = st.selectbox("Klientas", list(kli_opts.keys()), key="kli_sel")
            klientas_id = kli_opts[kl_lbl]
        else:
            klientas_id = None
            st.text_input("Klientas (nėra įrašų)", key="kli_txt")

        uzs_nr = st.text_input("Užsakymo numeris", key="kro_u_nr")
        pak_nr = st.text_input("Pakrovimo numeris", key="kro_p_nr")

        col1, col2 = st.columns(2)
        pak_data = col1.date_input("Pakrovimo data", date.today(), key="kro_pd")
        pak_nuo  = col1.time_input("Laikas nuo (pakrovimas)", time(8,0), key="kro_pnuo")
        pak_iki  = col1.time_input("Laikas iki (pakrovimas)", time(17,0), key="kro_piki")
        isk_data = col2.date_input("Iškrovimo data", pak_data+timedelta(days=1), key="kro_id")
        isk_nuo  = col2.time_input("Laikas nuo (iškrovimas)", time(8,0), key="kro_inuo")
        isk_iki  = col2.time_input("Laikas iki (iškrovimas)", time(17,0), key="kro_iiki")

        col3, col4 = st.columns(2)
        pak_sal = col3.text_input("Pakrovimo šalis", key="kro_psal")
        pak_mi  = col3.text_input("Pakrovimo miestas", key="kro_pmi")
        isk_sal = col4.text_input("Iškrovimo šalis", key="kro_isal")
        isk_mi  = col4.text_input("Iškrovimo miestas", key="kro_ismi")

        vilk_map = dict(c.execute("SELECT numeris,priekaba FROM vilkikai").fetchall())
        if vilk_map:
            vilk = st.selectbox("Vilkikas", list(vilk_map.keys()), key="kro_vilk")
            priek = vilk_map[vilk]
        else:
            vilk = st.text_input("Vilkikas", key="kro_vtxt")
            priek = ""
        st.text_input("Priekaba", value=priek, disabled=True, key="kro_priek")

        km = st.text_input("Kilometrai", key="kro_km")
        fr = st.text_input("Frachtas (€)", key="kro_fr")
        sv = st.text_input("Svoris (kg)", key="kro_sv")
        pal= st.text_input("Padėklų skaičius", key="kro_pal")

        bus_opts = [r[0] for r in c.execute(
            "SELECT reiksme FROM lookup WHERE modulis='Kroviniai' AND kategorija='busena'"
        ).fetchall()]
        if bus_opts:
            bus = st.selectbox("Būsena", bus_opts, key="kro_bus")
        else:
            bus = st.selectbox("Būsena", ["suplanuotas","nesuplanuotas","pakrautas","iškrautas"], key="kro_bus2")

        submit = st.form_submit_button("💾 Išsaugoti krovinį", key="kro_sub")

    if submit:
        if not klientas_id or not uzs_nr:
            st.error("Privalomi laukai: Klientas ir Užsakymo numeris.")
        else:
            cnt = c.execute(
                "SELECT COUNT(*) FROM kroviniai WHERE uzsakymo_numeris = ?", (uzs_nr,)
            ).fetchone()[0]
            bid = uzs_nr if cnt == 0 else f"{uzs_nr}-{cnt}"
            if cnt > 0:
                st.warning(f"Dublikatas → Business ID = {bid}")
            c.execute("""
                INSERT INTO kroviniai (
                    business_id, klientas_id, uzsakymo_numeris,
                    pakrovimo_numeris, vilkikas, priekaba, busena
                ) VALUES (?,?,?,?,?,?,?)
            """, (bid, klientas_id, uzs_nr, pak_nr, vilk, priek, bus))
            kid = c.lastrowid
            for ld in st.session_state.loads:
                c.execute("""
                    INSERT INTO pakrovimai (
                        krovinys_id, tipas, data, laikas_nuo, laikas_iki, adresas
                    ) VALUES (?,?,?,?,?,?)
                """, (kid, "load", str(ld["data"]), str(ld["nuo"]), str(ld["iki"]), ld["adresas"]))
            for ul in st.session_state.unloads:
                c.execute("""
                    INSERT INTO pakrovimai (
                        krovinys_id, tipas, data, laikas_nuo, laikas_iki, adresas
                    ) VALUES (?,?,?,?,?,?)
                """, (kid, "unload", str(ul["data"]), str(ul["nuo"]), str(ul["iki"]), ul["adresas"]))
            conn.commit()
            st.success("Krovinys įrašytas.")

    st.subheader("Krovinių sąrašas")
    df = pd.read_sql_query("""
        SELECT k.business_id, kl.pavadinimas AS klientas,
               k.uzsakymo_numeris, k.vilkikas, k.priekaba, k.busena
        FROM kroviniai k
        LEFT JOIN klientai kl ON k.klientas_id = kl.id
    """, conn)
    st.dataframe(df, use_container_width=True)

# ─── 6. KLIENTAI ───────────────────────────────────────────────────────────────
elif modulis == "Klientai":
    st.title("DISPO – Klientų valdymas")
    with st.form("kl_form", clear_on_submit=True):
        pavad   = st.text_input("Įmonės pavadinimas", key="kl_pav")
        vat     = st.text_input("PVM (VAT) numeris", key="kl_vat")
        st.subheader("Adresas")
        miestas = st.text_input("Miestas", key="kl_mi")
        p_kodas = st.text_input("Pašto kodas", key="kl_pk")

        st.subheader("Kontaktas")
        kont_v   = st.text_input("Kontaktas – Vardas", key="kl_kv")
        kont_p   = st.text_input("Kontaktas – Pavardė", key="kl_kp")
        kont_e   = st.text_input("Kontaktas – El. paštas", key="kl_ke")
        kont_t   = st.text_input("Kontaktas – Telefonas", key="kl_kt")

        st.subheader("Kontaktas dėl sąskaitų")
        sask_v   = st.text_input("Sąskaitų kontaktas – Vardas", key="kl_sv")
        sask_p   = st.text_input("Sąskaitų kontaktas – Pavardė", key="kl_sp")
        sask_e   = st.text_input("Sąskaitų kontaktas – El. paštas", key="kl_se")
        sask_t   = st.text_input("Sąskaitų kontaktas – Telefonas", key="kl_st")

        coface   = st.number_input("COFACE limitas", min_value=0.0, key="kl_cof")
        musu     = round(coface/3, 2)
        st.write(f"Mūsų limitas: {musu}")
        ats_b    = st.selectbox("Atsiskaitymo būdas", ["originalūs dokumentai","platforma","skanuoti dokumentai"], key="kl_ab")
        ats_t    = st.text_input("Atsiskaitymo terminas", key="kl_at")

        submit_k = st.form_submit_button("💾 Išsaugoti klientą", key="kl_sub")

    if submit_k:
        dup = c.execute("""
            SELECT COUNT(*) FROM klientai
            WHERE pavadinimas=? AND miestas=? AND post_kodas=?
        """, (pavad, miestas, p_kodas)).fetchone()[0]
        if dup:
            st.error("❌ Toks klientas jau egzistuoja.")
        else:
            c.execute("""
                INSERT INTO klientai (
                    pavadinimas, vat_numeris, miestas, post_kodas,
                    kont_vardas, kont_pavarde, kont_email, kont_tel,
                    s_vardas, s_pavarde, s_email, s_tel,
                    coface_limitas, musu_limitas, ats_budas, ats_terminas
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                pavad, vat, miestas, p_kodas,
                kont_v, kont_p, kont_e, kont_t,
                sask_v, sask_p, sask_e, sask_t,
                coface, musu, ats_b, ats_t
            ))
            conn.commit()
            st.success("Klientas įrašytas.")

    st.subheader("Klientų sąrašas")
    st.dataframe(pd.read_sql_query("SELECT * FROM klientai", conn), use_container_width=True)

# ─── 7. VILKIKAI ───────────────────────────────────────────────────────────────
elif modulis == "Vilkikai":
    st.title("DISPO – Vilkikų valdymas")
    marks = [r[0] for r in c.execute(
        "SELECT reiksme FROM lookup WHERE modulis='Vilkikai' AND kategorija='marke'"
    ).fetchall()]
    with st.form("vi_form", clear_on_submit=True):
        nr = st.text_input("Numeris", key="vi_nr")
        if marks:
            mk = st.selectbox("Markė", marks, key="vi_mk")
        else:
            mk = st.text_input("Markė", key="vi_mkt")
        pm = st.text_input("Pagaminimo metai", key="vi_pm")
        ta = st.date_input("Techninė apžiūra", key="vi_ta")
        vd = st.text_input("Vadybininkas", key="vi_vd")
        vv = st.text_input("Vairuotojai (kableliais)", key="vi_vv")
        pr = st.text_input("Priekaba", key="vi_pr")
        sub = st.form_submit_button("💾 Išsaugoti vilkiką", key="vi_sub")
    if sub:
        if not nr:
            st.warning("⚠️ Numeris privalomas.")
        else:
            c.execute("""
                INSERT INTO vilkikai (
                    numeris, marke, pagaminimo_metai,
                    tech_apziura, vadybininkas, vairuotojai, priekaba
                ) VALUES (?,?,?,?,?,?,?)
            """, (nr, mk, int(pm or 0), str(ta), vd, vv, pr))
            conn.commit()
            st.success("Vilkikas įrašytas.")
    st.subheader("Vilkikų sąrašas")
    st.dataframe(pd.read_sql_query("SELECT * FROM vilkikai", conn), use_container_width=True)

# ─── 8. PRIEKABOS ───────────────────────────────────────────────────────────────
elif modulis == "Priekabos":
    st.title("DISPO – Priekabų valdymas")
    tips = [r[0] for r in c.execute(
        "SELECT reiksme FROM lookup WHERE modulis='Priekabos' AND kategorija='tipas'"
    ).fetchall()]
    with st.form("pr_form", clear_on_submit=True):
        if tips:
            tp = st.selectbox("Tipas", tips, key="pr_tp")
        else:
            tp = st.text_input("Tipas", key="pr_tpt")
        num = st.text_input("Numeris", key="pr_num")
        mr = st.text_input("Markė", key="pr_mr")
        pm = st.text_input("Pagaminimo metai", key="pr_pm")
        ta = st.date_input("Techninė apžiūra", key="pr_ta")
        pv = st.text_input("Priskirtas vilkikas", key="pr_pv")
        sb = st.form_submit_button("💾 Išsaugoti priekabą", key="pr_sub")
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
            st.success("Priekaba įrašyta.")
    st.subheader("Priekabų sąrašas")
    st.dataframe(pd.read_sql_query("SELECT * FROM priekabos", conn), use_container_width=True)

# ─── 9. GRUPĖS ─────────────────────────────────────────────────────────────────
elif modulis == "Grupės":
    st.title("DISPO – Darbo grupių valdymas")
    with st.form("gr_form", clear_on_submit=True):
        nr = st.text_input("Numeris", key="gr_nr")
        pv = st.text_input("Pavadinimas", key="gr_pv")
        ap = st.text_area("Aprašymas", key="gr_ap")
        sb = st.form_submit_button("💾 Išsaugoti grupę", key="gr_sb")
    if sb:
        if not nr or not pv:
            st.warning("⚠️ Numeris ir pavadinimas būtini.")
        else:
            c.execute("INSERT INTO grupes(numeris,pavadinimas,aprasymas) VALUES(?,?,?)", (nr,pv,ap))
            conn.commit()
            st.success("Grupė įrašyta.")
    st.subheader("Grupių sąrašas")
    st.dataframe(pd.read_sql_query("SELECT * FROM grupes", conn), use_container_width=True)

# ─── 10. VAIRUOTOJAI ───────────────────────────────────────────────────────────
elif modulis == "Vairuotojai":
    st.title("DISPO – Vairuotojų valdymas")
    with st.form("va_form", clear_on_submit=True):
        vd = st.text_input("Vardas", key="va_vd")
        pv = st.text_input("Pavardė", key="va_pv")
        gm = st.text_input("Gimimo metai", key="va_gm")
        tt = st.text_input("Tautybė", key="va_tt")
        vk = st.text_input("Priskirtas vilkikas", key="va_vk")
        sb = st.form_submit_button("💾 Išsaugoti vairuotoją", key="va_sb")
    if sb:
        if not vd or not pv:
            st.warning("⚠️ Vardas ir pavardė būtini.")
        else:
            c.execute("""
                INSERT INTO vairuotojai (
                    vardas,pavarde,gimimo_metai,tautybe,priskirtas_vilkikas
                ) VALUES(?,?,?,?,?)
            """, (vd,pv,int(gm or 0),tt,vk))
            conn.commit()
            st.success("Vairuotojas įrašytas.")
    st.subheader("Vairuotojų sąrašas")
    st.dataframe(pd.read_sql_query("SELECT * FROM vairuotojai", conn), use_container_width=True)

# ─── 11. DARBUOTOJAI ───────────────────────────────────────────────────────────
elif modulis == "Darbuotojai":
    st.title("DISPO – Darbuotojų valdymas")
    pareig = [r[0] for r in c.execute(
        "SELECT reiksme FROM lookup WHERE modulis='Darbuotojai' AND kategorija='pareigybe'"
    ).fetchall()]
    grps = [r[2] for r in c.execute("SELECT id,numeris,pavadinimas FROM grupes").fetchall()]
    with st.form("da_form", clear_on_submit=True):
        vd = st.text_input("Vardas", key="da_vd")
        pv = st.text_input("Pavardė", key="da_pv")
        if pareig:
            pg = st.selectbox("Pareigybė", pareig, key="da_pg")
        else:
            pg = st.text_input("Pareigybė", key="da_pg2")
        if grps:
            gr = st.selectbox("Grupė", grps, key="da_gr")
        else:
            gr = st.text_input("Grupė", key="da_gr2")
        em = st.text_input("El. paštas", key="da_em")
        ph = st.text_input("Telefono numeris", key="da_ph")
        sb = st.form_submit_button("💾 Išsaugoti darbuotoją", key="da_sb")
    if sb:
        if not vd or not pv:
            st.warning("⚠️ Vardas ir pavardė būtini.")
        else:
            c.execute("""
                INSERT INTO darbuotojai (
                    vardas,pavarde,pareigybe,el_pastas,telefonas,grupe
                ) VALUES (?,?,?,?,?,?)
            """, (vd,pv,pg,em,ph,gr))
            conn.commit()
            st.success("Darbuotojas įrašytas.")
    st.subheader("Darbuotojų sąrašas")
    st.dataframe(pd.read_sql_query("SELECT * FROM darbuotojai", conn), use_container_width=True)
