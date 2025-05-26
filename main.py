import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, time, timedelta

# ─── 1. Duomenų bazės prisijungimas ────────────────────────────────────────────
conn = sqlite3.connect('dispo_new.db', check_same_thread=False)
c = conn.cursor()

# ─── 2. Lentelių kūrimas ───────────────────────────────────────────────────────
c.execute("""
CREATE TABLE IF NOT EXISTS lookup (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    modulis TEXT,
    kategorija TEXT,
    reiksme TEXT UNIQUE
)
""")
c.execute("""
CREATE TABLE IF NOT EXISTS kroviniai (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    klientas_id INTEGER,
    uzsakymo_numeris TEXT,
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
    pag_metai INTEGER,
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
    pag_metai INTEGER,
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
    gim_metai INTEGER,
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

# ─── 3. Modulių meniu ─────────────────────────────────────────────────────────
modules = [
    "Kroviniai", "Vilkikai", "Priekabos",
    "Grupės", "Vairuotojai", "Klientai",
    "Darbuotojai", "Nustatymai"
]
modulis = st.sidebar.radio("📂 Pasirink modulį", modules)

# ─── 4. NUSTATYMAI – modulis + kategorija ────────────────────────────────────
if modulis == "Nustatymai":
    st.title("DISPO – Sąrašų valdymas")
    mod_opts = [m for m in modules if m != "Nustatymai"]
    sel_mod = st.selectbox("Modulis", mod_opts, key="nm_mod")
    cats = [r[0] for r in c.execute(
        "SELECT DISTINCT kategorija FROM lookup WHERE modulis = ?", (sel_mod,)
    ).fetchall()]
    esama = st.selectbox("Esama kategorija", [""] + cats, key="nm_esama")
    nauja_kat = st.text_input("Arba nauja kategorija", key="nm_naujaKat")
    kat = nauja_kat.strip() if nauja_kat else esama

    st.markdown("---")
    if kat:
        st.subheader(f"**{sel_mod} – {kat}**")
        vals = [r[0] for r in c.execute(
            "SELECT reiksme FROM lookup WHERE modulis=? AND kategorija=?",
            (sel_mod, kat)
        ).fetchall()]
        st.write(vals or "_Nėra įrašų_")

        new_val = st.text_input("Pridėti naują reikšmę", key="nm_newVal")
        if st.button("➕ Pridėti reikšmę", key="nm_addVal"):
            if new_val:
                try:
                    c.execute(
                        "INSERT INTO lookup(modulis,kategorija,reiksme) VALUES(?,?,?)",
                        (sel_mod, kat, new_val)
                    )
                    conn.commit()
                    st.experimental_rerun()
                except sqlite3.IntegrityError:
                    st.warning("⚠️ Toks elementas jau egzistuoja.")

        to_del = st.selectbox("Ištrinti reikšmę", [""] + vals, key="nm_delVal")
        if st.button("🗑 Ištrinti reikšmę", key="nm_delBtn"):
            if to_del:
                c.execute(
                    "DELETE FROM lookup WHERE modulis=? AND kategorija=? AND reiksme=?",
                    (sel_mod, kat, to_del)
                )
                conn.commit()
                st.experimental_rerun()
    else:
        st.info("Pasirink arba įvesk kategoriją, kad valdytum reikšmes.")

# ─── 5. KROVINIAI ──────────────────────────────────────────────────────────────
elif modulis == "Kroviniai":
    st.title("DISPO – Krovinių valdymas")

    # Adresai pakrovimams / iškrovimams
    if "loads" not in st.session_state:
        st.session_state.loads = [{"data": date.today(), "nuo": time(8,0), "iki": time(17,0), "adresas": ""}]
    if "unloads" not in st.session_state:
        st.session_state.unloads = [{"data": date.today()+timedelta(days=1), "nuo": time(8,0), "iki": time(17,0), "adresas": ""}]

    col_add1, col_add2 = st.columns(2)
    if col_add1.button("➕ Pakrovimas"):
        st.session_state.loads.append({"data": date.today(), "nuo": time(8,0), "iki": time(17,0), "adresas": ""})
    if col_add2.button("➕ Iškrovimas"):
        st.session_state.unloads.append({"data": date.today()+timedelta(days=1), "nuo": time(8,0), "iki": time(17,0), "adresas": ""})

    with st.form("krov_forma", clear_on_submit=False):
        # Klientas viršuje
        klientai = c.execute("SELECT id,pavadinimas,post_kodas,miestas FROM klientai").fetchall()
        opts = {f"{r[1]} {r[2]} {r[3]}": r[0] for r in klientai}
        if opts:
            kli_label = st.selectbox("Klientas", list(opts.keys()), key="kr_kli")
            kli_id    = opts[kli_label]
        else:
            kli_label = st.text_input("Klientas", key="kr_kli_txt"); kli_id = None

        uzs_nr = st.text_input("Užsakymo numeris", key="kr_uzs")

        # Vilkikas + priekaba
        vilkikai = c.execute("SELECT numeris,priekaba FROM vilkikai").fetchall()
        vopts    = {r[0]:r[1] for r in vilkikai}
        if vopts:
            vilk = st.selectbox("Vilkikas", list(vopts.keys()), key="kr_vilk")
            priek = vopts[vilk]
        else:
            vilk = st.text_input("Vilkikas", key="kr_vilk_txt"); priek = ""
        st.text_input("Priekaba", value=priek, disabled=True, key="kr_priek")

        # Būsena
        bus_vals = [r[0] for r in c.execute(
            "SELECT reiksme FROM lookup WHERE modulis='Kroviniai' AND kategorija='Būsena'"
        ).fetchall()]
        if bus_vals:
            bus = st.selectbox("Būsena", bus_vals, key="kr_bus")
        else:
            bus = st.text_input("Būsena", key="kr_bus_txt")

        # Pakrovimai su adresais
        st.markdown("**Pakrovimai (įvesk adresą)**")
        for i, ld in enumerate(st.session_state.loads):
            with st.expander(f"Pakrovimas #{i+1}", expanded=True):
                d  = st.date_input("Data", ld["data"], key=f"kr_pak_{i}_d")
                n  = st.time_input("Nuo", ld["nuo"],    key=f"kr_pak_{i}_n")
                ik = st.time_input("Iki", ld["iki"],    key=f"kr_pak_{i}_i")
                ad = st.text_input("Adresas", ld["adresas"], key=f"kr_pak_{i}_ad")
                st.session_state.loads[i] = {"data":d, "nuo":n, "iki":ik, "adresas":ad}

        # Iškrovimai su adresais
        st.markdown("**Iškrovimai (įvesk adresą)**")
        for i, ul in enumerate(st.session_state.unloads):
            with st.expander(f"Iškrovimas #{i+1}", expanded=True):
                d  = st.date_input("Data", ul["data"], key=f"kr_isk_{i}_d")
                n  = st.time_input("Nuo", ul["nuo"],    key=f"kr_isk_{i}_n")
                ik = st.time_input("Iki", ul["iki"],    key=f"kr_isk_{i}_i")
                ad = st.text_input("Adresas", ul["adresas"], key=f"kr_isk_{i}_ad")
                st.session_state.unloads[i] = {"data":d, "nuo":n, "iki":ik, "adresas":ad}

        submit = st.form_submit_button("💾 Įrašyti krovinį")

    if submit:
        c.execute("""
            INSERT INTO kroviniai (
                klientas_id, uzsakymo_numeris,
                vilkikas, priekaba, busena
            ) VALUES (?,?,?,?,?)
        """, (kli_id, uzs_nr, vilk, priek, bus))
        kid = c.lastrowid

        for ld in st.session_state.loads:
            c.execute("""
                INSERT INTO pakrovimai (
                    krovinys_id, tipas, data,
                    laikas_nuo, laikas_iki, adresas
                ) VALUES (?,?,?,?,?,?)
            """, (kid, "load", str(ld["data"]), str(ld["nuo"]), str(ld["iki"]), ld["adresas"]))

        for ul in st.session_state.unloads:
            c.execute("""
                INSERT INTO pakrovimai (
                    krovinys_id, tipas, data,
                    laikas_nuo, laikas_iki, adresas
                ) VALUES (?,?,?,?,?,?)
            """, (kid, "unload", str(ul["data"]), str(ul["nuo"]), str(ul["iki"]), ul["adresas"]))

        conn.commit()
        st.success("✅ Krovinis įrašytas sėkmingai.")

    # Santrauka ir peržiūra
    df = pd.read_sql_query("SELECT id,uzsakymo_numeris FROM kroviniai", conn)
    choice = st.selectbox("Peržiūrėti krovinį pagal ID/užsakymo nr",
                          df.apply(lambda r: f'{r.id} – {r.uzsakymo_numeris}', axis=1),
                          key="kr_sel")
    sel_id = int(choice.split(" – ")[0])

    det = c.execute("SELECT klientas_id, uzsakymo_numeris, vilkikas, priekaba, busena FROM kroviniai WHERE id = ?", (sel_id,)).fetchone()
    kli_lbl = next((lbl for lbl,id_ in opts.items() if id_==det[0]), "")
    st.markdown("**Bendra informacija:**")
    st.write({
        "Klientas": kli_lbl,
        "Užsakymo nr": det[1],
        "Vilkikas": det[2],
        "Priekaba": det[3],
        "Būsena": det[4]
    })

    pak = c.execute("SELECT tipas,data,laikas_nuo,laikas_iki,adresas FROM pakrovimai WHERE krovinys_id = ?", (sel_id,)).fetchall()
    st.markdown("**Visi pakrovimai/iškrovimai:**")
    st.table(pd.DataFrame(pak, columns=["Tipas","Data","Nuo","Iki","Adresas"]))

# ─── 6. VILKIKAI ───────────────────────────────────────────────────────────────
elif modulis == "Vilkikai":
    st.title("DISPO – Vilkikų valdymas")
    with st.form("vilk_form", clear_on_submit=True):
        nr = st.text_input("Numeris", key="v_nr")
        marks = [r[0] for r in c.execute(
            "SELECT reiksme FROM lookup WHERE modulis='Vilkikai' AND kategorija='Markė'"
        ).fetchall()]
        if marks:
            mk = st.selectbox("Markė", marks, key="v_mk")
        else:
            mk = st.text_input("Markė", key="v_mk_txt")
        pm = st.text_input("Pagaminimo metai", key="v_pm")
        ta = st.date_input("Tech. apžiūra", key="v_ta")
        vd = st.text_input("Vadybininkas", key="v_vd")
        vv = st.text_input("Vairuotojai (kableliais)", key="v_vv")
        pr = st.text_input("Priekaba", key="v_pr")
        sb = st.form_submit_button("💾 Įrašyti vilkiką")
    if sb:
        if nr:
            c.execute("""
                INSERT INTO vilkikai (
                    numeris, marke, pag_metai,
                    tech_apziura, vadybininkas,
                    vairuotojai, priekaba
                ) VALUES (?,?,?,?,?,?,?)
            """, (nr, mk, int(pm or 0), str(ta), vd, vv, pr))
            conn.commit(); st.success("✅ Išsaugota.")
        else:
            st.warning("⚠️ Reikia įvesti numerį.")
    st.table(pd.read_sql_query("SELECT * FROM vilkikai", conn))

# ─── 7. PRIEKABOS ─────────────────────────────────────────────────────────────
elif modulis == "Priekabos":
    st.title("DISPO – Priekabų valdymas")
    with st.form("priek_form", clear_on_submit=True):
        tips = [r[0] for r in c.execute(
            "SELECT reiksme FROM lookup WHERE modulis='Priekabos' AND kategorija='Priekabų tipas'"
        ).fetchall()]
        if tips:
            tp = st.selectbox("Tipas", tips, key="p_tp")
        else:
            tp = st.text_input("Tipas", key="p_tp_txt")
        num = st.text_input("Numeris", key="p_num")
        mr = st.text_input("Markė", key="p_mr")
        pm = st.text_input("Pagaminimo metai", key="p_pm")
        ta = st.date_input("Tech. apžiūra", key="p_ta")
        pv = st.text_input("Priskirtas vilkikas", key="p_pv")
        sb = st.form_submit_button("💾 Išsaugoti")
    if sb:
        if num:
            c.execute("""
                INSERT INTO priekabos (
                    priekabu_tipas, numeris, marke,
                    pag_metai, tech_apziura, priskirtas_vilkikas
                ) VALUES (?,?,?,?,?,?)
            """, (tp, num, mr, int(pm or 0), str(ta), pv))
            conn.commit(); st.success("✅ Išsaugota.")
        else:
            st.warning("⚠️ Numeris būtinas.")
    st.table(pd.read_sql_query("SELECT * FROM priekabos", conn))

# ─── 8. GRUPĖS ─────────────────────────────────────────────────────────────────
elif modulis == "Grupės":
    st.title("DISPO – Darbo grupių valdymas")
    with st.form("grp_form", clear_on_submit=True):
        nr = st.text_input("Numeris", key="g_nr")
        pv = st.text_input("Pavadinimas", key="g_pv")
        ap = st.text_area("Aprašymas", key="g_ap")
        sb = st.form_submit_button("💾 Išsaugoti")
    if sb:
        if nr and pv:
            c.execute("INSERT INTO grupes(numeris,pavadinimas,aprasymas) VALUES(?,?,?)", (nr,pv,ap))
            conn.commit(); st.success("✅ Išsaugota.")
        else:
            st.warning("⚠️ Numeris ir pavadinimas būtini.")
    st.table(pd.read_sql_query("SELECT * FROM grupes", conn))

# ─── 9. VAIRUOTOJAI ─────────────────────────────────────────────────────────────
elif modulis == "Vairuotojai":
    st.title("DISPO – Vairuotojų valdymas")
    with st.form("drv_form", clear_on_submit=True):
        vd = st.text_input("Vardas", key="d_vd")
        pv = st.text_input("Pavardė", key="d_pv")
        gm = st.text_input("Gimimo metai", key="d_gm")
        tt = st.text_input("Tautybė", key="d_tt")
        vk = st.text_input("Priskirtas vilkikas", key="d_vk")
        sb = st.form_submit_button("💾 Išsaugoti")
    if sb:
        if vd and pv:
            c.execute("""
                INSERT INTO vairuotojai (
                    vardas,pavarde,gim_metai,tautybe,priskirtas_vilkikas
                ) VALUES(?,?,?,?,?)
            """, (vd,pv,int(gm or 0),tt,vk))
            conn.commit(); st.success("✅ Išsaugota.")
        else:
            st.warning("⚠️ Vardas ir pavardė būtini.")
    st.table(pd.read_sql_query("SELECT * FROM vairuotojai", conn))

# ─── 10. KLIENTAI ───────────────────────────────────────────────────────────────
elif modulis == "Klientai":
    st.title("DISPO – Klientų valdymas")
    with st.form("kl_form", clear_on_submit=True):
        pv = st.text_input("Įmonės pavadinimas", key="kl_pv")
        vat = st.text_input("PVM (VAT) numeris", key="kl_vat")
        c1,c2 = st.columns(2)
        ms = c1.text_input("Miestas", key="kl_ms"); pk = c2.text_input("Pašto kodas", key="kl_pk")
        st.markdown("**Kontaktas**")
        c3,c4 = st.columns(2)
        kv = c3.text_input("Vardas", key="kl_kv"); kp = c4.text_input("Pavardė", key="kl_kp")
        c5,c6 = st.columns(2)
        ke = c5.text_input("El. paštas", key="kl_ke"); kt = c6.text_input("Telefonas", key="kl_kt")
        st.markdown("**Kontaktas dėl sąskaitų**")
        c7,c8 = st.columns(2)
        sv = c7.text_input("Vardas", key="kl_sv"); sp = c8.text_input("Pavardė", key="kl_sp")
        c9,c10 = st.columns(2)
        se = c9.text_input("El. paštas", key="kl_se"); stl = c10.text_input("Telefonas", key="kl_stl")
        co = st.number_input("COFACE limitas", min_value=0.0, step=0.01, key="kl_co")
        mu = round(co/3,2); st.write(f"Mūsų limitas: {mu}")
        ab = st.selectbox("Atsiskaitymo būdas", ["originalūs dokumentai","platforma","skanuoti dokumentai"], key="kl_ab")
        at = st.text_input("Atsiskaitymo terminas", key="kl_at")
        sb = st.form_submit_button("💾 Išsaugoti")
    if sb:
        d = c.execute("""
            SELECT COUNT(*) FROM klientai
            WHERE pavadinimas=? AND miestas=? AND post_kodas=?
        """,(pv,ms,pk)).fetchone()[0]
        if d:
            st.error("❌ Toks klientas jau įvestas.")
        else:
            c.execute("""
                INSERT INTO klientai (
                    pavadinimas,vat_numeris,miestas,post_kodas,
                    kont_vardas,kont_pavarde,kont_email,kont_tel,
                    s_vardas,s_pavarde,s_email,s_tel,
                    coface_limitas,musu_limitas,ats_budas,ats_terminas
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (pv,vat,ms,pk,kv,kp,ke,kt,sv,sp,se,stl,co,mu,ab,at))
            conn.commit(); st.success("✅ Išsaugota.")
    st.table(pd.read_sql_query("SELECT * FROM klientai", conn))

# ─── 11. DARBUOTOJAI ───────────────────────────────────────────────────────────
elif modulis == "Darbuotojai":
    st.title("DISPO – Darbuotojų valdymas")
    p_list = [r[0] for r in c.execute(
        "SELECT reiksme FROM lookup WHERE modulis='Darbuotojai' AND kategorija='Pareigybė'"
    ).fetchall()]
    g_list = [r[2] for r in c.execute("SELECT id,numeris,pavadinimas FROM grupes").fetchall()]
    with st.form("emp_form", clear_on_submit=True):
        vd = st.text_input("Vardas", key="e_vd")
        pv = st.text_input("Pavardė", key="e_pv")
        if p_list:
            pg = st.selectbox("Pareigybė", p_list, key="e_pg")
        else:
            pg = st.text_input("Pareigybė", key="e_pg_txt")
        if g_list:
            gr = st.selectbox("Grupė", g_list, key="e_gr")
        else:
            gr = st.text_input("Grupė", key="e_gr_txt")
        em = st.text_input("El. paštas", key="e_em")
        ph = st.text_input("Telefonas", key="e_ph")
        sb = st.form_submit_button("💾 Išsaugoti")
    if sb:
        if vd and pv:
            c.execute("""
                INSERT INTO darbuotojai (
                    vardas,pavarde,pareigybe,el_pastas,telefonas,grupe
                ) VALUES(?,?,?,?,?,?)
            """, (vd,pv,pg,em,ph,gr))
            conn.commit(); st.success("✅ Išsaugota.")
        else:
            st.warning("⚠️ Vardas ir pavardė būtini.")
    st.table(pd.read_sql_query("SELECT * FROM darbuotojai", conn))
