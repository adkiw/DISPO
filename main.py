import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, time, timedelta

# ─── 1. DB prisijungimas ────────────────────────────────────────────────────────
conn = sqlite3.connect('dispo_new.db', check_same_thread=False)
c = conn.cursor()

# ─── 2. Lentelių kūrimas ─────────────────────────────────────────────────────────
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
    business_id TEXT,
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
modules = [
    "Kroviniai", "Klientai", "Vilkikai",
    "Priekabos", "Grupės", "Vairuotojai",
    "Darbuotojai", "Nustatymai"
]
modulis = st.sidebar.selectbox("📂 Pasirink modulį", modules)

# ─── 4. NUSTATYMAI ───────────────────────────────────────────────────────────────
if modulis == "Nustatymai":
    st.title("DISPO – Sąrašų valdymas")

    sel_mod = st.selectbox("Modulis", [m for m in modules if m != "Nustatymai"], key="ns_mod")
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
        st.write(values or "_Nėra įrašų_")

        with st.form("ns_form", clear_on_submit=False):
            newv = st.text_input("Pridėti naują reikšmę", key="ns_newv")
            submit_add = st.form_submit_button("➕ Pridėti reikšmę", key="ns_add")
            istr = st.selectbox("Ištrinti reikšmę", [""] + values, key="ns_del_sel")
            submit_del = st.form_submit_button("🗑 Ištrinti reikšmę", key="ns_del")
        if submit_add and newv:
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
        if submit_del and istr:
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

    # inicijuojame sesijos kintamuosius pakrovimams/iškrovimams
    if "loads" not in st.session_state:
        st.session_state.loads = [{"data": date.today(), "nuo": time(8,0), "iki": time(17,0), "adresas": ""}]
    if "unloads" not in st.session_state:
        st.session_state.unloads = [{"data": date.today()+timedelta(days=1), "nuo": time(8,0), "iki": time(17,0), "adresas": ""}]

    colA, colB = st.columns(2)
    if colA.button("➕ Pridėti pakrovimą", key="add_load"):
        st.session_state.loads.append({"data": date.today(), "nuo": time(8,0), "iki": time(17,0), "adresas": ""})
    if colB.button("➕ Pridėti iškrovimą", key="add_unload"):
        st.session_state.unloads.append({"data": date.today()+timedelta(days=1), "nuo": time(8,0), "iki": time(17,0), "adresas": ""})

    with st.form("form_krovinys", clear_on_submit=False):
        # Klientas iš dropdown
        kl_rows = c.execute("SELECT id,pavadinimas,post_kodas,miestas FROM klientai").fetchall()
        kl_map = {f"{r[1]} {r[2]} {r[3]}": r[0] for r in kl_rows}
        if kl_map:
            kl_key = st.selectbox("Klientas", list(kl_map.keys()), key="kro_kl")
            klientas_id = kl_map[kl_key]
        else:
            klientas_id = None
            st.text_input("Klientas (pridėk klientą modulyje)", key="kro_kl_txt")

        uzs_nr = st.text_input("Užsakymo numeris", key="kro_uzs")
        pak_nr = st.text_input("Pakrovimo numeris", key="kro_pnr")

        c1, c2 = st.columns(2)
        pak_dat = c1.date_input("Pakrovimo data", date.today(), key="kro_pdat")
        pak_nuo = c1.time_input("Laikas nuo (pakrovimas)", time(8,0), key="kro_pnuo")
        pak_iki = c1.time_input("Laikas iki (pakrovimas)", time(17,0), key="kro_piki")
        isk_dat = c2.date_input("Iškrovimo data", pak_dat+timedelta(days=1), key="kro_idat")
        isk_nuo = c2.time_input("Laikas nuo (iškrovimas)", time(8,0), key="kro_inuo")
        isk_iki = c2.time_input("Laikas iki (iškrovimas)", time(17,0), key="kro_iiki")

        d1, d2 = st.columns(2)
        pak_salis   = d1.text_input("Pakrovimo šalis", key="kro_psal")
        pak_miestas = d1.text_input("Pakrovimo miestas", key="kro_pmi")
        isk_salis   = d2.text_input("Iškrovimo šalis", key="kro_isal")
        isk_miestas = d2.text_input("Iškrovimo miestą", key="kro_ismi")

        # Vilkikas→priekaba
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
            # Business ID su sufiksu
            cnt = c.execute("SELECT COUNT(*) FROM kroviniai WHERE uzsakymo_numeris=?", (uzs_nr,)).fetchone()[0]
            bid = uzs_nr if cnt == 0 else f"{uzs_nr}-{cnt}"
            if cnt > 0:
                st.warning(f"Dublikatui pritaikytas Business ID: {bid}")
            c.execute("""
                INSERT INTO kroviniai (
                    business_id, klientas_id, uzsakymo_numeris,
                    pakrovimo_numeris, vilkikas, priekaba, busena
                ) VALUES (?,?,?,?,?,?,?)
            """, (bid, klientas_id, uzs_nr, pak_nr, vilk, priek, bus))
            kid = c.lastrowid
            # įrašom pakrovimus
            for ld in st.session_state.loads:
                c.execute("""
                    INSERT INTO pakrovimai (
                        krovinys_id, tipas, data, laikas_nuo, laikas_iki, adresas
                    ) VALUES (?,?,?,?,?,?)
                """, (kid, "load", str(ld["data"]), str(ld["nuo"]), str(ld["iki"]), ld["adresas"]))
            # įrašom iškrovimus
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

# ─── 6. KLIENTAI ────────────────────────────────────────────────────────────────
elif modulis == "Klientai":
    st.title("DISPO – Klientų valdymas")

    with st.form("form_klientai", clear_on_submit=False):
        pavad = st.text_input("Įmonės pavadinimas", key="kl_pav")
        vat   = st.text_input("PVM (VAT) numeris", key="kl_vat")
        mi = st.text_input("Miestas", key="kl_mi")
        pc = st.text_input("Pašto kodas", key="kl_pc")

        # kontaktas
        st.markdown("**Kontaktas**")
        kv = st.text_input("Vardas", key="kl_kv_v")
        kp = st.text_input("Pavardė", key="kl_kv_p")
        ke = st.text_input("El. paštas", key="kl_kv_e")
        kt = st.text_input("Telefonas", key="kl_kv_t")

        # sąskaitų kontaktas
        st.markdown("**Kontaktas dėl sąskaitų**")
        sv = st.text_input("Vardas", key="kl_sv_v")
        sp = st.text_input("Pavardė", key="kl_sv_p")
        se = st.text_input("El. paštas", key="kl_sv_e")
        stt= st.text_input("Telefonas", key="kl_sv_t")

        # limitai
        co = st.number_input("COFACE limitas", value=0.0, key="kl_co")
        mu = co/3
        st.write(f"Mūsų limitas: {mu:.2f}")

        ats_b = st.selectbox(
            "Atsiskaitymo būdas",
            ["originalūs dokumentai","platforma","skenuoti dokumentai"],
            key="kl_ab"
        )
        ats_t = st.text_input("Atsiskaitymo terminas", key="kl_at")

        submit = st.form_submit_button("💾 Išsaugoti klientą", key="kl_submit")

    if submit:
        # unikumo patikra
        exists = c.execute("""
            SELECT 1 FROM klientai
            WHERE pavadinimas=? AND miestas=? AND post_kodas=?
        """, (pavad, mi, pc)).fetchone()
        if exists:
            st.error("❌ Toks klientas jau egzistuoja.")
        elif not pavad:
            st.error("❌ Įmonės pavadinimas privalomas.")
        else:
            c.execute("""
                INSERT INTO klientai (
                    pavadinimas, vat_numeris, miestas, post_kodas,
                    kont_vardas, kont_pavarde, kont_email, kont_tel,
                    sask_vardas, sask_pavarde, sask_email, sask_tel,
                    coface_limitas, musu_limitas, ats_budas, ats_terminas
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                pavad, vat, mi, pc,
                kv, kp, ke, kt,
                sv, sp, se, stt,
                co, mu, ats_b, ats_t
            ))
            conn.commit()
            st.success("✅ Klientas įrašytas.")

    st.subheader("📋 Klientų sąrašas")
    df = pd.read_sql_query("SELECT * FROM klientai", conn)
    st.dataframe(df, use_container_width=True)

# ─── 7. VILKIKAI ────────────────────────────────────────────────────────────────
elif modulis == "Vilkikai":
    st.title("DISPO – Vilkikų valdymas")

    with st.form("form_vilk", clear_on_submit=False):
        numer = st.text_input("Vilkiko numeris", key="vl_numer")
        # markės dropdown
        marks = [r[0] for r in c.execute(
            "SELECT reiksme FROM lookup WHERE modulis='Vilkikai' AND kategorija='marke'"
        ).fetchall()]
        marke = st.selectbox("Markė", marks, key="vl_marke") if marks else st.text_input("Markė", key="vl_marke_txt")
        pag = st.text_input("Pagaminimo metai", key="vl_pag")
        ta = st.date_input("Techninė apžiūra", date.today(), key="vl_ta")
        va = st.text_input("Vadybininkas", key="vl_va")
        vr = st.text_input("Vairuotojai (kableliais)", key="vl_vr")
        pr = st.text_input("Priekaba", key="vl_pr")
        submit = st.form_submit_button("💾 Išsaugoti vilkiką", key="vl_submit")

    if submit:
        if not numer:
            st.error("❌ Numeris privalomas.")
        else:
            try:
                c.execute("""
                    INSERT INTO vilkikai (
                        numeris, marke, pagaminimo_metai, tech_apziura,
                        vadybininkas, vairuotojai, priekaba
                    ) VALUES (?,?,?,?,?,?,?)
                """, (numer, marke, int(pag or 0), str(ta), va, vr, pr))
                conn.commit()
                st.success("✅ Vilkikas įrašytas.")
            except sqlite3.IntegrityError:
                st.error("❌ Toks vilkikas jau egzistuoja.")

    st.subheader("📋 Vilkikų sąrašas")
    df = pd.read_sql_query("SELECT * FROM vilkikai", conn)
    st.dataframe(df, use_container_width=True)

# ─── 8. PRIEKABOS ───────────────────────────────────────────────────────────────
elif modulis == "Priekabos":
    st.title("DISPO – Priekabų valdymas")

    with st.form("form_priek", clear_on_submit=False):
        types = [r[0] for r in c.execute(
            "SELECT reiksme FROM lookup WHERE modulis='Priekabos' AND kategorija='tipas'"
        ).fetchall()]
        tip = st.selectbox("Priekabos tipas", types, key="pr_tip") if types else st.text_input("Priekabos tipas", key="pr_tip_txt")
        num = st.text_input("Numeris", key="pr_num")
        ma = st.text_input("Markė", key="pr_ma")
        pa = st.text_input("Pagaminimo metai", key="pr_pa")
        ta = st.date_input("Techninė apžiūra", date.today(), key="pr_ta")
        pv = st.text_input("Priskirtas vilkikas", key="pr_pv")
        submit = st.form_submit_button("💾 Išsaugoti priekabą", key="pr_submit")

    if submit:
        if not num:
            st.error("❌ Numeris privalomas.")
        else:
            try:
                c.execute("""
                    INSERT INTO priekabos (
                        priekabu_tipas, numeris, marke, pagaminimo_metai,
                        tech_apziura, priskirtas_vilkikas
                    ) VALUES (?,?,?,?,?,?)
                """, (tip, num, ma, int(pa or 0), str(ta), pv))
                conn.commit()
                st.success("✅ Priekaba įrašyta.")
            except sqlite3.IntegrityError:
                st.error("❌ Tokia priekaba jau egzistuoja.")

    st.subheader("📋 Priekabų sąrašas")
    df = pd.read_sql_query("SELECT * FROM priekabos", conn)
    st.dataframe(df, use_container_width=True)

# ─── 9. GRUPĖS ─────────────────────────────────────────────────────────────────
elif modulis == "Grupės":
    st.title("DISPO – Darbo grupių valdymas")

    with st.form("form_grup", clear_on_submit=False):
        nr = st.text_input("Numeris", key="gr_nr")
        pav = st.text_input("Pavadinimas", key="gr_pav")
        apr = st.text_area("Aprašymas", key="gr_apr")
        submit = st.form_submit_button("💾 Išsaugoti grupę", key="gr_submit")

    if submit:
        if not nr or not pav:
            st.error("❌ Numeris ir pavadinimas privalomi.")
        else:
            try:
                c.execute("INSERT INTO grupes (numeris,pavadinimas,aprasymas) VALUES (?,?,?)", (nr,pav,apr))
                conn.commit()
                st.success("✅ Grupė įrašyta.")
            except sqlite3.IntegrityError:
                st.error("❌ Tokia grupė jau egzistuoja.")

    st.subheader("📋 Grupės sąrašas")
    df = pd.read_sql_query("SELECT * FROM grupes", conn)
    st.dataframe(df, use_container_width=True)

# ─── 10. VAIRUOTOJAI ────────────────────────────────────────────────────────────
elif modulis == "Vairuotojai":
    st.title("DISPO – Vairuotojų valdymas")

    with st.form("form_vair", clear_on_submit=False):
        v = st.text_input("Vardas", key="vai_v")
        p = st.text_input("Pavardė", key="vai_p")
        gm = st.text_input("Gimimo metai", key="vai_gm")
        ta = st.text_input("Tautybė", key="vai_ta")
        pv = st.text_input("Priskirtas vilkikas", key="vai_pv")
        submit = st.form_submit_button("💾 Išsaugoti vairuotoją", key="vai_submit")

    if submit:
        if not v or not p:
            st.error("❌ Vardas ir pavardė privalomi.")
        else:
            c.execute("""
                INSERT INTO vairuotojai (vardas,pavarde,gimimo_metai,tautybe,priskirtas_vilkikas)
                VALUES (?,?,?,?,?)
            """, (v,p,int(gm or 0),ta,pv))
            conn.commit()
            st.success("✅ Vairuotojas įrašytas.")

    st.subheader("📋 Vairuotojų sąrašas")
    df = pd.read_sql_query("SELECT * FROM vairuotojai", conn)
    st.dataframe(df, use_container_width=True)

# ─── 11. DARBUOTOJAI ────────────────────────────────────────────────────────────
elif modulis == "Darbuotojai":
    st.title("DISPO – Darbuotojų valdymas")

    # iš lookup pareigybės
    pareigybes = [r[0] for r in c.execute(
        "SELECT reiksme FROM lookup WHERE modulis='Darbuotojai' AND kategorija='pareigybe'"
    ).fetchall()]
    # iš grupių
    gr_list = [r[2] for r in c.execute("SELECT id,numeris,pavadinimas FROM grupes").fetchall()]

    with st.form("form_darb", clear_on_submit=False):
        vd = st.text_input("Vardas", key="da_v")
        pd_ = st.text_input("Pavardė", key="da_p")
        if pareigybes:
            pg = st.selectbox("Pareigybė", pareigybes, key="da_pg")
        else:
            pg = st.text_input("Pareigybė", key="da_pg_txt")
        if gr_list:
            gr = st.selectbox("Grupė", gr_list, key="da_gr")
        else:
            gr = st.text_input("Grupė", key="da_gr_txt")
        em = st.text_input("El. paštas", key="da_em")
        tp = st.text_input("Telefono numeris", key="da_tp")
        submit = st.form_submit_button("💾 Išsaugoti darbuotoją", key="da_submit")

    if submit:
        if not vd or not pd_:
            st.error("❌ Vardas ir pavardė privalomi.")
        else:
            c.execute("""
                INSERT INTO darbuotojai (
                    vardas,pavarde,pareigybe,el_pastas,telefonas,grupe
                ) VALUES (?,?,?,?,?,?)
            """, (vd,pd_,pg,em,tp,gr))
            conn.commit()
            st.success("✅ Darbuotojas įrašytas.")

    st.subheader("📋 Darbuotojų sąrašas")
    df = pd.read_sql_query("SELECT * FROM darbuotojai", conn)
    st.dataframe(df, use_container_width=True)
