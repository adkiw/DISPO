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
    # 4.1 Pasirenkame modulį (išskyrus patį „Nustatymai“)
    mod_opts = [m for m in modules if m != "Nustatymai"]
    sel_mod = st.selectbox("Modulis", mod_opts)

    # 4.2 Esamos kategorijos to modulio
    cats = [row[0] for row in c.execute(
        "SELECT DISTINCT kategorija FROM lookup WHERE modulis = ?", (sel_mod,)
    ).fetchall()]
    esama = st.selectbox("Esama kategorija", [""] + cats)
    nauja_kat = st.text_input("Arba nauja kategorija")
    kat = nauja_kat.strip() if nauja_kat else esama

    st.markdown("---")
    if kat:
        st.subheader(f"**{sel_mod} – {kat}**")
        # 4.3 Rodom esamas reikšmes
        vals = [r[0] for r in c.execute(
            "SELECT reiksme FROM lookup WHERE modulis = ? AND kategorija = ?",
            (sel_mod, kat)
        ).fetchall()]
        st.write(vals or "_Nėra įrašų_" )

        # 4.4 Pridėti naują reikšmę
        nauja_val = st.text_input("Pridėti naują reikšmę")
        if st.button("➕ Pridėti reikšmę"):
            if nauja_val:
                try:
                    c.execute(
                        "INSERT INTO lookup(modulis,kategorija,reiksme) VALUES(?,?,?)",
                        (sel_mod, kat, nauja_val)
                    )
                    conn.commit()
                    st.success("✅ Pridėta.")
                except sqlite3.IntegrityError:
                    st.warning("⚠️ Toks elementas jau egzistuoja.")

        # 4.5 Ištrinti reikšmę
        istr = st.selectbox("Ištrinti reikšmę", [""] + vals)
        if st.button("🗑 Ištrinti reikšmę"):
            if istr:
                c.execute(
                    "DELETE FROM lookup WHERE modulis = ? AND kategorija = ? AND reiksme = ?",
                    (sel_mod, kat, istr)
                )
                conn.commit()
                st.success("✅ Ištrinta.")
    else:
        st.info("Pasirink arba įvesk kategoriją, kad valdytum reikšmes.")

# ─── 5. KROVINIAI ──────────────────────────────────────────────────────────────
elif modulis == "Kroviniai":
    st.title("DISPO – Krovinių valdymas")

    # 5.1 Dinaminiai pakrovimai / iškrovimai laikomi session_state
    if "loads" not in st.session_state:
        st.session_state.loads = [{
            "data": date.today(),
            "nuo": time(8, 0),
            "iki": time(17, 0),
            "adresas": ""
        }]
    if "unloads" not in st.session_state:
        st.session_state.unloads = [{
            "data": date.today() + timedelta(days=1),
            "nuo": time(8, 0),
            "iki": time(17, 0),
            "adresas": ""
        }]

    # 5.2 Mygtukai pakrovimams / iškrovimams PRIEŠ formą
    col_add1, col_add2 = st.columns(2)
    if col_add1.button("➕ Pridėti pakrovimą"):
        st.session_state.loads.append({
            "data": date.today(),
            "nuo": time(8, 0),
            "iki": time(17, 0),
            "adresas": ""
        })
    if col_add2.button("➕ Pridėti iškrovimą"):
        st.session_state.unloads.append({
            "data": date.today() + timedelta(days=1),
            "nuo": time(8, 0),
            "iki": time(17, 0),
            "adresas": ""
        })

    # 5.3 Forma su klientu VIRŠUJE
    with st.form("krov_forma", clear_on_submit=False):
        # Klientas
        klientai = c.execute(
            "SELECT id, pavadinimas, post_kodas, miestas FROM klientai"
        ).fetchall()
        opts = {f"{r[1]} {r[2]} {r[3]}": r[0] for r in klientai}
        if opts:
            klient_label = st.selectbox("Klientas", list(opts.keys()))
            klient_id = opts[klient_label]
        else:
            klient_label = st.text_input("Klientas")
            klient_id = None

        # Užsakymo numeris (paliekam kaip įvestą – leidžiam dublikatams)
        uzs_nr = st.text_input("Užsakymo numeris")

        # Vilkikas + automatinė priekaba
        vilkikai = c.execute("SELECT numeris, priekaba FROM vilkikai").fetchall()
        vopts = {r[0]: r[1] for r in vilkikai}
        if vopts:
            vilk = st.selectbox("Vilkikas", list(vopts.keys()))
            priek = vopts[vilk]
        else:
            vilk = st.text_input("Vilkikas")
            priek = ""
        st.text_input("Priekaba", value=priek, disabled=True)

        # Būsena iš lookup (jei yra – dropdown, kitaip text)
        bus_vals = [r[0] for r in c.execute(
            "SELECT reiksme FROM lookup WHERE modulis = ? AND kategorija = ?",
            ("Kroviniai", "Būsena")
        ).fetchall()]
        if bus_vals:
            bus = st.selectbox("Būsena", bus_vals)
        else:
            bus = st.text_input("Būsena")

        # Submit
        submit = st.form_submit_button("💾 Įrašyti krovinį")

    # 5.4 Po Submit – įrašome į DB + pakrovimus/iškrovimus
    if submit:
        # 5.4.1 Įrašome pagrindinį įrašą
        c.execute("""
            INSERT INTO kroviniai (
                klientas_id, uzsakymo_numeris,
                vilkikas, priekaba, busena
            ) VALUES (?,?,?,?,?)
        """, (
            klient_id, uzs_nr,
            vilk, priek, bus
        ))
        krovinys_id = c.lastrowid

        # 5.4.2 Pakrovimai
        for ld in st.session_state.loads:
            c.execute("""
                INSERT INTO pakrovimai (
                    krovinys_id, tipas, data,
                    laikas_nuo, laikas_iki, adresas
                ) VALUES (?,?,?,?,?,?)
            """, (
                krovinys_id, "load",
                str(ld["data"]), str(ld["nuo"]),
                str(ld["iki"]), ld["adresas"]
            ))

        # 5.4.3 Iškrovimai
        for ul in st.session_state.unloads:
            c.execute("""
                INSERT INTO pakrovimai (
                    krovinys_id, tipas, data,
                    laikas_nuo, laikas_iki, adresas
                ) VALUES (?,?,?,?,?,?)
            """, (
                krovinys_id, "unload",
                str(ul["data"]), str(ul["nuo"]),
                str(ul["iki"]), ul["adresas"]
            ))

        conn.commit()
        st.success("✅ Krovinių užsakymas sėkmingai įrašytas.")

    # 5.5 Santrauka: tik pirmas pakrovimas + paskutinis iškrovimas
    all_kro = c.execute("""
        SELECT id, klientas_id, uzsakymo_numeris,
               vilkikas, priekaba, busena
        FROM kroviniai
    """).fetchall()
    summary = []
    for r in all_kro:
        kid, kli_id, nr, vk, pr, bs = r
        # pirma pakrovimo eilutė
        p = c.execute("""
            SELECT data, laikas_nuo, laikas_iki
            FROM pakrovimai
            WHERE krovinys_id = ? AND tipas = 'load'
            ORDER BY id
            LIMIT 1
        """, (kid,)).fetchone() or ("","","")
        # paskutinis iškrovimo
        u = c.execute("""
            SELECT data, laikas_nuo, laikas_iki
            FROM pakrovimai
            WHERE krovinys_id = ? AND tipas = 'unload'
            ORDER BY id DESC
            LIMIT 1
        """, (kid,)).fetchone() or ("","","")
        kli_lbl = next((x[0] for x in opts.items() if x[1]==kli_id), "")
        summary.append({
            "ID": kid,
            "Klientas": kli_lbl,
            "Užsak. nr.": nr,
            "Pakrovimo data": p[0],
            "Pak. nuo": p[1],
            "Pak. iki": p[2],
            "Iškrovimo data": u[0],
            "Išk. nuo": u[1],
            "Išk. iki": u[2],
            "Vilkikas": vk,
            "Priekaba": pr,
            "Būsena": bs
        })
    df_sum = pd.DataFrame(summary)

    # 5.6 Detalių peržiūra
    st.subheader("Peržiūrėti krovinį")
    sel = st.selectbox(
        "Pasirink pagal ID – Užsakymo numerį",
        df_sum.apply(lambda x: f"{x.ID} – {x['Užsak. nr.']}", axis=1)
    )
    sel_id = int(sel.split(" – ")[0])
    det = df_sum[df_sum.ID == sel_id].iloc[0]
    st.markdown("**Bendra informacija:**")
    st.write(det.drop(labels=["ID"]))

    # 5.7 Detalės: visi pakrovimai / iškrovimai su adresais
    st.markdown("**Visi pakrovimai ir iškrovimai:**")
    pak = c.execute("""
        SELECT tipas, data, laikas_nuo, laikas_iki, adresas
        FROM pakrovimai
        WHERE krovinys_id = ?
        ORDER BY id
    """, (sel_id,)).fetchall()
    df_pak = pd.DataFrame(pak, columns=["Tipas","Data","Nuo","Iki","Adresas"])
    st.table(df_pak)

    # 5.8 Galutinė santrauka
    st.subheader("Visi kroviniai – santrauka")
    st.table(df_sum)

# ─── 6. Likę moduliai (naudojasi lookup analogiškai) ─────────────────────────
elif modulis == "Vilkikai":
    st.title("DISPO – Vilkikų valdymas")
    with st.form("frm", clear_on_submit=True):
        nr  = st.text_input("Numeris")
        # dinaminė Markė iš lookup
        marks = [r[0] for r in c.execute(
            "SELECT reiksme FROM lookup WHERE modulis=? AND kategorija=?",
            ("Vilkikai","Markė")
        ).fetchall()]
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

elif modulis == "Priekabos":
    st.title("DISPO – Priekabų valdymas")
    with st.form("f", clear_on_submit=True):
        tips = [r[0] for r in c.execute(
            "SELECT reiksme FROM lookup WHERE modulis=? AND kategorija=?",
            ("Priekabos","Priekabų tipas")
        ).fetchall()]
        if tips:
            tp = st.selectbox("Tipas", tips)
        else:
            tp = st.text_input("Tipas")
        nr = st.text_input("Numeris")
        mk = st.text_input("Markė")
        pm = st.text_input("Pagaminimo metai")
        ta = st.date_input("Tech. apžiūra")
        pv = st.text_input("Priskirtas vilkikas")
        sb = st.form_submit_button("💾 Išsaugoti")
    if sb:
        if nr:
            c.execute("""
                INSERT INTO priekabos (
                    priekabu_tipas, numeris, marke,
                    pag_metai, tech_apziura, priskirtas_vilkikas
                ) VALUES (?,?,?,?,?,?)
            """, (tp, nr, mk, int(pm or 0), str(ta), pv))
            conn.commit(); st.success("✅ Išsaugota.")
        else:
            st.warning("⚠️ Numeris būtinas.")
    st.table(pd.read_sql_query("SELECT * FROM priekabos", conn))

elif modulis == "Grupės":
    st.title("DISPO – Darbo grupių valdymas")
    with st.form("f", clear_on_submit=True):
        nr = st.text_input("Numeris")
        pv = st.text_input("Pavadinimas")
        ap = st.text_area("Aprašymas")
        sb = st.form_submit_button("💾 Įrašyti")
    if sb:
        if nr and pv:
            c.execute("""
                INSERT INTO grupes(numeris,pavadinimas,aprasymas)
                VALUES(?,?,?)
            """, (nr,pv,ap))
            conn.commit(); st.success("✅ Išsaugota.")
        else:
            st.warning("⚠️ Numeris ir pavadinimas būtini.")
    st.table(pd.read_sql_query("SELECT * FROM grupes", conn))

elif modulis == "Vairuotojai":
    st.title("DISPO – Vairuotojų valdymas")
    with st.form("f", clear_on_submit=True):
        vd = st.text_input("Vardas")
        pv = st.text_input("Pavardė")
        gm = st.text_input("Gimimo metai")
        tt = st.text_input("Tautybė")
        vk = st.text_input("Priskirtas vilkikas")
        sb = st.form_submit_button("💾 Įrašyti")
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

elif modulis == "Klientai":
    st.title("DISPO – Klientų valdymas")
    with st.form("f", clear_on_submit=True):
        pv = st.text_input("Įmonės pavadinimas")
        vat = st.text_input("PVM (VAT) numeris")
        c1,c2 = st.columns(2)
        ms = c1.text_input("Miestas"); pk = c2.text_input("Pašto kodas")
        st.markdown("**Kontaktas**")
        c3,c4 = st.columns(2)
        kv = c3.text_input("Vardas"); kp = c4.text_input("Pavardė")
        c5,c6 = st.columns(2)
        ke = c5.text_input("El. paštas"); kt = c6.text_input("Telefonas")
        st.markdown("**Kontaktas dėl sąskaitų**")
        c7,c8 = st.columns(2)
        sv = c7.text_input("Vardas"); sp = c8.text_input("Pavardė")
        c9,c10 = st.columns(2)
        se = c9.text_input("El. paštas"); stl = c10.text_input("Telefonas")
        co = st.number_input("COFACE limitas",0.0,1e9,step=0.01)
        mu = round(co/3,2); st.write(f"Mūsų limitas: {mu}")
        ab = st.selectbox("Atsiskaitymo būdas", ["originalūs dokumentai","platforma","skanuoti dokumentai"])
        at = st.text_input("Atsiskaitymo terminas")
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
                    s_vardas,s_vardpavarde
                    ,s_email,s_tel,coface_limitas,musu_limitas,
                    ats_budas,ats_terminas
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                pv,vat,ms,pk,
                kv,kp,ke,kt,
                sv,sp,se,stl,
                co,mu,ab,at
            ))
            conn.commit(); st.success("✅ Išsaugota.")
    st.table(pd.read_sql_query("SELECT * FROM klientai", conn))

# ─── Pabaiga ─────────────────────────────────────────────────────────────────
