import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, time, timedelta

# ─── 1. Prisijungimas prie DB ────────────────────────────────────────────────────
conn = sqlite3.connect('dispo_new.db', check_same_thread=False)
c = conn.cursor()

# ─── 2. Lentelių kūrimas ─────────────────────────────────────────────────────────
# Universalūs lookup sąrašams
c.execute("""
CREATE TABLE IF NOT EXISTS lookup (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    modulis TEXT,
    kategorija TEXT,
    reiksme TEXT UNIQUE
)
""")

# Pagrindinės lentelės
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
    sask_vardas TEXT,
    sask_pavarde TEXT,
    sask_email TEXT,
    sask_tel TEXT,
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

# ─── 3. Šoninis meniu ────────────────────────────────────────────────────────────
moduliai = [
    "Kroviniai", "Klientai", "Vilkikai",
    "Priekabos", "Grupės", "Vairuotojai",
    "Darbuotojai", "Nustatymai"
]
modulis = st.sidebar.selectbox("📂 Pasirink modulį", moduliai)

# ─── 4. NUSTATYMAI ───────────────────────────────────────────────────────────────
if modulis == "Nustatymai":
    st.title("DISPO – Sąrašų valdymas")

    sel_mod = st.selectbox("Modulis", [m for m in moduliai if m != "Nustatymai"], key="ns_mod")
    cats = [r[0] for r in c.execute(
        "SELECT DISTINCT kategorija FROM lookup WHERE modulis=?", (sel_mod,)
    ).fetchall()]
    esama = st.selectbox("Esama kategorija", [""] + cats, key="ns_esama")
    nauja = st.text_input("Arba įvesk naują kategoriją", key="ns_nauja")
    kat = nauja.strip() if nauja else esama

    st.markdown("---")
    if kat:
        st.subheader(f"{sel_mod} – {kat}")
        values = [r[0] for r in c.execute(
            "SELECT reiksme FROM lookup WHERE modulis=? AND kategorija=?", (sel_mod, kat)
        ).fetchall()]
        st.write(values or "_Nėra reikšmių_")

        newv = st.text_input("Pridėti naują reikšmę", key="ns_newv")
        if st.button("➕ Pridėti reikšmę", key="ns_add"):
            if newv:
                try:
                    c.execute(
                        "INSERT INTO lookup (modulis,kategorija,reiksme) VALUES (?,?,?)",
                        (sel_mod, kat, newv)
                    )
                    conn.commit()
                    st.success(f"✅ Pridėta: {newv}")
                    st.experimental_rerun()
                except sqlite3.IntegrityError:
                    st.warning("⚠️ Toks įrašas jau egzistuoja.")

        istr = st.selectbox("Ištrinti reikšmę", [""] + values, key="ns_del_sel")
        if st.button("🗑 Ištrinti reikšmę", key="ns_del"):
            if istr:
                c.execute(
                    "DELETE FROM lookup WHERE modulis=? AND kategorija=? AND reiksme=?",
                    (sel_mod, kat, istr)
                )
                conn.commit()
                st.success(f"✅ Ištrinta: {istr}")
                st.experimental_rerun()
    else:
        st.info("Pasirink arba įvesk kategoriją, kad galėtum valdyti reikšmes.")

# ─── 5. KROVINIAI ────────────────────────────────────────────────────────────────
elif modulis == "Kroviniai":
    st.title("DISPO – Krovinių valdymas")

    # inicijuojam session_state sąrašus
    if "loads" not in st.session_state:
        st.session_state.loads = [{"data": date.today(), "nuo": time(8,0), "iki": time(17,0), "adresas": ""}]
    if "unloads" not in st.session_state:
        st.session_state.unloads = [{"data": date.today()+timedelta(days=1), "nuo": time(8,0), "iki": time(17,0), "adresas": ""}]

    c1, c2 = st.columns(2)
    if c1.button("➕ Pridėti pakrovimą", key="add_load"):
        st.session_state.loads.append({"data": date.today(), "nuo": time(8,0), "iki": time(17,0), "adresas": ""})
    if c2.button("➕ Pridėti iškrovimą", key="add_unload"):
        st.session_state.unloads.append({"data": date.today()+timedelta(days=1), "nuo": time(8,0), "iki": time(17,0), "adresas": ""})

    with st.form("form_krovinys", clear_on_submit=False):
        # Klientas iš dropdown
        klientai = c.execute("SELECT id,pavadinimas,post_kodas,miestas FROM klientai").fetchall()
        kl_map = {f"{r[1]} {r[2]} {r[3]}": r[0] for r in klientai}
        if kl_map:
            kl_sel = st.selectbox("Klientas", list(kl_map.keys()), key="kro_kl")
            klientas_id = kl_map[kl_sel]
        else:
            klientas_id = None
            st.text_input("Klientas (įvesk klientų modulyje)", key="kro_kl_txt")

        uzs_nr = st.text_input("Užsakymo numeris", key="kro_uzs")
        pak_nr = st.text_input("Pakrovimo numeris", key="kro_pnr")

        col1, col2 = st.columns(2)
        pak_dat   = col1.date_input("Pakrovimo data", date.today(), key="kro_pdat")
        pak_nuo   = col1.time_input("Laikas nuo (pakrovimas)", time(8,0), key="kro_pnuo")
        pak_iki   = col1.time_input("Laikas iki (pakrovimas)", time(17,0), key="kro_piki")
        isk_dat   = col2.date_input("Iškrovimo data", pak_dat+timedelta(days=1), key="kro_idat")
        isk_nuo   = col2.time_input("Laikas nuo (iškrovimas)", time(8,0), key="kro_inuo")
        isk_iki   = col2.time_input("Laikas iki (iškrovimas)", time(17,0), key="kro_iiki")

        col3, col4 = st.columns(2)
        pak_salis = col3.text_input("Pakrovimo šalis", key="kro_psal")
        pak_mi     = col3.text_input("Pakrovimo miestas", key="kro_pmi")
        isk_salis = col4.text_input("Iškrovimo šalis", key="kro_isal")
        isk_mi     = col4.text_input("Iškrovimo miestas", key="kro_ismi")

        # Vilkikas → priekaba auto
        vilk_map = dict(c.execute("SELECT numeris,priekaba FROM vilkikai").fetchall())
        if vilk_map:
            vilk = st.selectbox("Vilkikas", list(vilk_map.keys()), key="kro_vilk")
            priek = vilk_map[vilk]
        else:
            vilk = st.text_input("Vilkikas", key="kro_vtxt")
            priek = ""
        st.text_input("Priekaba", value=priek, disabled=True, key="kro_prk")

        km = st.text_input("Kilometrai", key="kro_km")
        fr = st.text_input("Frachtas (€)", key="kro_fr")
        sv = st.text_input("Svoris (kg)", key="kro_sv")
        pl = st.text_input("Padėklų skaičius", key="kro_pl")

        # Būsena iš lookup
        bus_opts = [r[0] for r in c.execute(
            "SELECT reiksme FROM lookup WHERE modulis='Kroviniai' AND kategorija='busena'"
        ).fetchall()]
        if bus_opts:
            bus = st.selectbox("Būsena", bus_opts, key="kro_bus")
        else:
            bus = st.selectbox("Būsena", ["suplanuotas","nesuplanuotas","pakrautas","iškrautas"], key="kro_bus2")

        submit = st.form_submit_button("💾 Išsaugoti krovinį", key="kro_submit")

    if submit:
        if not klientas_id or not uzs_nr:
            st.error("❌ Privalomi laukai: Klientas ir Užsakymo numeris.")
        else:
            cnt = c.execute("SELECT COUNT(*) FROM kroviniai WHERE uzsakymo_numeris=?", (uzs_nr,)).fetchone()[0]
            bid = uzs_nr if cnt == 0 else f"{uzs_nr}-{cnt}"
            if cnt>0:
                st.warning(f"Dublikatui pritaikytas Business ID: {bid}")
            c.execute("""
                INSERT INTO kroviniai (
                    business_id, klientas_id, uzsakymo_numeris,
                    pakrovimo_numeris, vilkikas, priekaba, busena
                ) VALUES (?,?,?,?,?,?,?)
            """, (bid, klientas_id, uzs_nr, pak_nr, vilk, priek, bus))
            kid = c.lastrowid
            # pakrovimai
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
            st.success("✅ Krovinys įrašytas.")

    st.subheader("📋 Krovinių sąrašas")
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

    with st.form("form_klientai", clear_on_submit=True):
        pavad  = st.text_input("Įmonės pavadinimas", key="kl_pav")
        vat    = st.text_input("PVM (VAT) numeris", key="kl_vat")
        st.subheader("Adresas")
        mi     = st.text_input("Miestas", key="kl_mi")
        pkod   = st.text_input("Pašto kodas", key="kl_pk")
        st.subheader("Kontaktas")
        kv     = st.text_input("Vardas", key="kl_kv")
        kp     = st.text_input("Pavardė", key="kl_kp")
        ke     = st.text_input("El. paštas", key="kl_ke")
        kt     = st.text_input("Telefonas", key="kl_kt")
        st.subheader("Kontaktas dėl sąskaitų")
        sv     = st.text_input("Vardas", key="kl_sv")
        sp     = st.text_input("Pavardė", key="kl_sp")
        se     = st.text_input("El. paštas", key="kl_se")
        stel   = st.text_input("Telefonas", key="kl_st")
        cof    = st.number_input("COFACE limitas", min_value=0.0, key="kl_cof")
        musu   = round(cof/3,2)
        st.write(f"Mūsų limitas: {musu}")
        ab     = st.selectbox("Atsiskaitymo būdas", ["originalūs dokumentai","platforma","skanuoti dokumentai"], key="kl_ab")
        at     = st.text_input("Atsiskaitymo terminas", key="kl_at")
        subk   = st.form_submit_button("💾 Išsaugoti klientą", key="kl_submit")

    if subk:
        dup = c.execute("""
            SELECT COUNT(*) FROM klientai
            WHERE pavadinimas=? AND miestas=? AND post_kodas=?
        """, (pavad, mi, pkod)).fetchone()[0]
        if dup:
            st.error("❌ Toks klientas jau egzistuoja.")
        else:
            c.execute("""
                INSERT INTO klientai (
                    pavadinimas, vat_numeris, miestas, post_kodas,
                    kont_vardas, kont_pavarde, kont_email, kont_tel,
                    sask_vardas, sask_pavarde, sask_email, sask_tel,
                    coface_limitas, musu_limitas, ats_budas, ats_terminas
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                pavad, vat, mi, pkod,
                kv, kp, ke, kt,
                sv, sp, se, stel,
                cof, musu, ab, at
            ))
            conn.commit()
            st.success("✅ Klientas įrašytas.")

    st.subheader("📋 Klientų sąrašas")
    st.dataframe(pd.read_sql_query("SELECT * FROM klientai", conn), use_container_width=True)

# ─── 7. VILKIKAI ───────────────────────────────────────────────────────────────
elif modulis == "Vilkikai":
    st.title("DISPO – Vilkikų valdymas")

    marks = [r[0] for r in c.execute(
        "SELECT reiksme FROM lookup WHERE modulis='Vilkikai' AND kategorija='marke'"
    ).fetchall()]

    with st.form("form_vilkikai", clear_on_submit=True):
        nr   = st.text_input("Numeris", key="vl_nr")
        if marks:
            mk = st.selectbox("Markė", marks, key="vl_mk")
        else:
            mk = st.text_input("Markė", key="vl_mk_txt")
        pm   = st.text_input("Pagaminimo metai", key="vl_pm")
        ta   = st.date_input("Techninė apžiūra", key="vl_ta")
        vd   = st.text_input("Vadybininkas", key="vl_vd")
        vv   = st.text_input("Vairuotojai (kableliais)", key="vl_vv")
        pr   = st.text_input("Priekaba", key="vl_pr")
        subv= st.form_submit_button("💾 Išsaugoti vilkiką", key="vl_submit")

    if subv:
        if not nr:
            st.warning("⚠️ Numeris privalomas.")
        else:
            c.execute("""
                INSERT INTO vilkikai (
                    numeris,marke,pagaminimo_metai,
                    tech_apziura,vadybininkas,vairuotojai,priekaba
                ) VALUES (?,?,?,?,?,?,?)
            """, (nr, mk, int(pm or 0), str(ta), vd, vv, pr))
            conn.commit()
            st.success("✅ Vilkikas įrašytas.")

    st.subheader("📋 Vilkikų sąrašas")
    st.dataframe(pd.read_sql_query("SELECT * FROM vilkikai", conn), use_container_width=True)

# ─── 8. PRIEKABOS ───────────────────────────────────────────────────────────────
elif modulis == "Priekabos":
    st.title("DISPO – Priekabų valdymas")

    types = [r[0] for r in c.execute(
        "SELECT reiksme FROM lookup WHERE modulis='Priekabos' AND kategorija='tipas'"
    ).fetchall()]

    with st.form("form_priekabos", clear_on_submit=True):
        if types:
            tp = st.selectbox("Tipas", types, key="pr_tp")
        else:
            tp = st.text_input("Tipas", key="pr_tp_txt")
        num = st.text_input("Numeris", key="pr_num")
        mr  = st.text_input("Markė", key="pr_mr")
        pm2 = st.text_input("Pagaminimo metai", key="pr_pm2")
        ta2 = st.date_input("Techninė apžiūra", key="pr_ta2")
        pv2 = st.text_input("Priskirtas vilkikas", key="pr_pv2")
        subp= st.form_submit_button("💾 Išsaugoti priekabą", key="pr_submit")

    if subp:
        if not num:
            st.warning("⚠️ Numeris būtinas.")
        else:
            c.execute("""
                INSERT INTO priekabos (
                    priekabu_tipas,numeris,marke,
                    pagaminimo_metai,tech_apziura,priskirtas_vilkikas
                ) VALUES (?,?,?,?,?,?)
            """, (tp, num, mr, int(pm2 or 0), str(ta2), pv2))
            conn.commit()
            st.success("✅ Priekaba įrašyta.")

    st.subheader("📋 Priekabų sąrašas")
    st.dataframe(pd.read_sql_query("SELECT * FROM priekabos", conn), use_container_width=True)

# ─── 9. GRUPĖS ─────────────────────────────────────────────────────────────────
elif modulis == "Grupės":
    st.title("DISPO – Darbo grupių valdymas")

    with st.form("form_grupes", clear_on_submit=True):
        nr2 = st.text_input("Numeris", key="gr_nr2")
        pv2 = st.text_input("Pavadinimas", key="gr_pv2")
        ap2 = st.text_area("Aprašymas", key="gr_ap2")
        subg= st.form_submit_button("💾 Išsaugoti grupę", key="gr_submit")

    if subg:
        if not nr2 or not pv2:
            st.warning("⚠️ Numeris ir pavadinimas būtini.")
        else:
            c.execute("INSERT INTO grupes (numeris,pavadinimas,aprasymas) VALUES (?,?,?)", (nr2,pv2,ap2))
            conn.commit()
            st.success("✅ Grupė įrašyta.")

    st.subheader("📋 Grupės sąrašas")
    st.dataframe(pd.read_sql_query("SELECT * FROM grupes", conn), use_container_width=True)

# ─── 10. VAIRUOTOJAI ───────────────────────────────────────────────────────────
elif modulis == "Vairuotojai":
    st.title("DISPO – Vairuotojų valdymas")

    with st.form("form_vairuotojai", clear_on_submit=True):
        vd2 = st.text_input("Vardas", key="v2_vd")
        pv2 = st.text_input("Pavardė", key="v2_pv")
        gm2 = st.text_input("Gimimo metai", key="v2_gm")
        tt2 = st.text_input("Tautybė", key="v2_tt")
        vk2 = st.text_input("Priskirtas vilkikas", key="v2_vk")
        subd= st.form_submit_button("💾 Išsaugoti vairuotoją", key="v2_submit")

    if subd:
        if not vd2 or not pv2:
            st.warning("⚠️ Vardas ir pavardė būtini.")
        else:
            c.execute("""
                INSERT INTO vairuotojai (
                    vardas,pavarde,gimimo_metai,tautybe,priskirtas_vilkikas
                ) VALUES (?,?,?,?,?)
            """, (vd2,pv2,int(gm2 or 0),tt2,vk2))
            conn.commit()
            st.success("✅ Vairuotojas įrašytas.")

    st.subheader("📋 Vairuotojų sąrašas")
    st.dataframe(pd.read_sql_query("SELECT * FROM vairuotojai", conn), use_container_width=True)

# ─── 11. DARBUOTOJAI ───────────────────────────────────────────────────────────
elif modulis == "Darbuotojai":
    st.title("DISPO – Darbuotojų valdymas")

    pareig = [r[0] for r in c.execute(
        "SELECT reiksme FROM lookup WHERE modulis='Darbuotojai' AND kategorija='pareigybe'"
    ).fetchall()]
    grps   = [r[2] for r in c.execute("SELECT id,numeris,pavadinimas FROM grupes").fetchall()]

    with st.form("form_darbuotojai", clear_on_submit=True):
        vd3 = st.text_input("Vardas", key="d_vd")
        pv3 = st.text_input("Pavardė", key="d_pv")
        if pareig:
            pg3 = st.selectbox("Pareigybė", pareig, key="d_pg")
        else:
            pg3 = st.text_input("Pareigybė", key="d_pg_txt")
        if grps:
            gr3 = st.selectbox("Grupė", grps, key="d_gr")
        else:
            gr3 = st.text_input("Grupė", key="d_gr_txt")
        em3 = st.text_input("El. paštas", key="d_em")
        ph3 = st.text_input("Telefono numeris", key="d_ph")
        sube = st.form_submit_button("💾 Išsaugoti darbuotoją", key="d_submit")

    if sube:
        if not vd3 or not pv3:
            st.warning("⚠️ Vardas ir pavardė būtini.")
        else:
            c.execute("""
                INSERT INTO darbuotojai (
                    vardas,pavarde,pareigybe,el_pastas,telefonas,grupe
                ) VALUES (?,?,?,?,?,?)
            """, (vd3,pv3,pg3,em3,ph3,gr3))
            conn.commit()
            st.success("✅ Darbuotojas įrašytas.")

    st.subheader("📋 Darbuotojų sąrašas")
    st.dataframe(pd.read_sql_query("SELECT * FROM darbuotojai", conn), use_container_width=True)
