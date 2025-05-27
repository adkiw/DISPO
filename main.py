import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, time, timedelta

# ─── 1. Prisijungimas prie DB ─────────────────────────────────────────────────
conn = sqlite3.connect('dispo_new.db', check_same_thread=False)
c = conn.cursor()

# ─── 2. Lentelių kūrimas ────────────────────────────────────────────────────────
# lookup
c.execute("""
CREATE TABLE IF NOT EXISTS lookup (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    modulis TEXT,
    kategorija TEXT,
    reiksme TEXT UNIQUE
)
""")
# klientai (išplėstinė struktūra pagal funkcionalumą)
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
# kroviniai
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
# pakrovimai (viena lentele pakrovimams ir iškrovimams)
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
# vilkikai
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
# priekabos
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
# grupes
c.execute("""
CREATE TABLE IF NOT EXISTS grupes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numeris TEXT UNIQUE,
    pavadinimas TEXT,
    aprasymas TEXT
)
""")
# vairuotojai
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
# darbuotojai
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

# ─── 3. Modulių pasirinkimas ───────────────────────────────────────────────────
moduliai = [
    "Kroviniai", "Klientai", "Vilkikai",
    "Priekabos", "Grupės", "Vairuotojai",
    "Darbuotojai", "Nustatymai"
]
modulis = st.sidebar.selectbox("📂 Pasirink modulį", moduliai)

# ─── 4. NUSTATYMAI ───────────────────────────────────────────────────────────────
if modulis == "Nustatymai":
    st.title("DISPO – Sąrašų valdymas")
    sel_mod = st.selectbox("Modulis", [m for m in moduliai if m != "Nustatymai"])
    # rodom tik to modulio įrašus
    cats = [r[0] for r in c.execute(
        "SELECT DISTINCT kategorija FROM lookup WHERE modulis = ?", (sel_mod,)
    ).fetchall()]
    esama = st.selectbox("Esama kategorija", [""] + cats)
    nauja = st.text_input("Arba įvesk naują kategoriją")
    kat = nauja.strip() if nauja else esama

    st.markdown("---")
    if kat:
        st.subheader(f"{sel_mod} – {kat}")
        vals = [r[0] for r in c.execute(
            "SELECT reiksme FROM lookup WHERE modulis = ? AND kategorija = ?", (sel_mod, kat)
        ).fetchall()]
        st.write(vals or "__Nėra reikšmių_")
        newv = st.text_input("Pridėti naują reikšmę")
        if st.button("➕ Pridėti"):
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
        todel = st.selectbox("Ištrinti reikšmę", [""] + vals)
        if st.button("🗑 Ištrinti"):
            if todel:
                c.execute(
                    "DELETE FROM lookup WHERE modulis=? AND kategorija=? AND reiksme=?",
                    (sel_mod, kat, todel)
                )
                conn.commit()
                st.success(f"✅ Ištrinta: {todel}")
                st.experimental_rerun()
    else:
        st.info("Pasirink modulį ir kategoriją arba įvesk naują.")

# ─── 5. KROVINIAI ────────────────────────────────────────────────────────────────
elif modulis == "Kroviniai":
    st.title("DISPO – Krovinių valdymas")

    # inits
    if "loads" not in st.session_state:
        st.session_state.loads = [
            {"data": date.today(), "nuo": time(8,0), "iki": time(17,0), "adresas": ""}
        ]
    if "unloads" not in st.session_state:
        st.session_state.unloads = [
            {"data": date.today()+timedelta(days=1), "nuo": time(8,0), "iki": time(17,0), "adresas": ""}
        ]

    # mygtukai prieš formą
    c1, c2 = st.columns(2)
    if c1.button("➕ Pridėti pakrovimą"):
        st.session_state.loads.append({"data": date.today(), "nuo": time(8,0), "iki": time(17,0), "adresas": ""})
    if c2.button("➕ Pridėti iškrovimą"):
        st.session_state.unloads.append({"data": date.today()+timedelta(days=1), "nuo": time(8,0), "iki": time(17,0), "adresas": ""})

    # form
    with st.form("krovinys_forma", clear_on_submit=False):
        # klientas
        cl = c.execute("SELECT id,pavadinimas,post_kodas,miestas FROM klientai").fetchall()
        kli_opts = {f"{r[1]} {r[2]} {r[3]}": r[0] for r in cl}
        if kli_opts:
            klientas_lbl = st.selectbox("Klientas", list(kli_opts.keys()))
            klientas_id = kli_opts[klientas_lbl]
        else:
            klientas_id = None
            st.text_input("Įvesk klientą (nėra duomenų)")

        uzs_nr = st.text_input("Užsakymo numeris")
        pak_num = st.text_input("Pakrovimo numeris")

        # datų laukai
        col1, col2 = st.columns(2)
        pak_data = col1.date_input("Pakrovimo data", date.today())
        pak_nuo = col1.time_input("Laikas nuo (pakrovimas)", time(8,0))
        pak_iki = col1.time_input("Laikas iki (pakrovimas)", time(17,0))
        isk_data = col2.date_input("Iškrovimo data", pak_data+timedelta(days=1))
        isk_nuo = col2.time_input("Laikas nuo (iškrovimas)", time(8,0))
        isk_iki = col2.time_input("Laikas iki (iškrovimas)", time(17,0))

        # šalys/miestai
        col3, col4 = st.columns(2)
        pak_sal = col3.text_input("Pakrovimo šalis")
        pak_mi  = col3.text_input("Pakrovimo miestas")
        isk_sal = col4.text_input("Iškrovimo šalis")
        isk_mi  = col4.text_input("Iškrovimo miestas")

        # vilkikas / priekaba
        vilk_map = dict(c.execute("SELECT numeris, priekaba FROM vilkikai").fetchall())
        if vilk_map:
            vilkikas = st.selectbox("Vilkikas", list(vilk_map.keys()))
            priekaba = vilk_map[vilkikas]
        else:
            vilkikas = st.text_input("Vilkikas")
            priekaba = ""
        st.text_input("Priekaba", value=priekaba, disabled=True)

        # kiti laukai
        km = st.text_input("Kilometrai")
        fr = st.text_input("Frachtas (€)")
        sv = st.text_input("Svoris (kg)")
        pal = st.text_input("Padėklų skaičius")

        # būsena
        bus_opts = [r[0] for r in c.execute(
            "SELECT reiksme FROM lookup WHERE modulis='Kroviniai' AND kategorija='busena'"
        ).fetchall()]
        if bus_opts:
            busena = st.selectbox("Būsena", bus_opts)
        else:
            busena = st.selectbox("Būsena", ["suplanuotas","nesuplanuotas","pakrautas","iškrautas"])

        submit = st.form_submit_button("💾 Įrašyti krovinį")

    # įrašymas
    if submit:
        if not klientas_id or not uzs_nr:
            st.error("Privalomi: Klientas ir Užsakymo numeris.")
        else:
            # business_id logika
            base = uzs_nr
            all_same = c.execute(
                "SELECT COUNT(*) FROM kroviniai WHERE uzsakymo_numeris = ?", (base,)
            ).fetchone()[0]
            bid = base if all_same == 0 else f"{base}-{all_same}"
            if all_same > 0:
                st.warning(f"Toks numeris egzistuoja → Business ID = {bid}")

            c.execute("""
                INSERT INTO kroviniai (
                    business_id, klientas_id, uzsakymo_numeris,
                    pakrovimo_numeris, vilkikas, priekaba, busena
                ) VALUES (?,?,?,?,?,?,?)
            """, (
                bid, klientas_id, uzs_nr,
                pak_num, vilkikas, priekaba, busena
            ))
            kid = c.lastrowid
            # pakrovimai
            for ld in st.session_state.loads:
                c.execute("""
                    INSERT INTO pakrovimai (
                        krovinys_id, tipas, data, laikas_nuo, laikas_iki, adresas
                    ) VALUES (?,?,?,?,?,?)
                """, (
                    kid, "load",
                    str(ld["data"]), str(ld["nuo"]), str(ld["iki"]), ld["adresas"]
                ))
            # iškrovimai
            for ul in st.session_state.unloads:
                c.execute("""
                    INSERT INTO pakrovimai (
                        krovinys_id, tipas, data, laikas_nuo, laikas_iki, adresas
                    ) VALUES (?,?,?,?,?,?)
                """, (
                    kid, "unload",
                    str(ul["data"]), str(ul["nuo"]), str(ul["iki"]), ul["adresas"]
                ))
            conn.commit()
            st.success("Krovinys įrašytas.")

    # santrauka
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
    st.title("DISPO – Klientai")
    with st.form("kl_form", clear_on_submit=True):
        pavad = st.text_input("Įmonės pavadinimas")
        vat = st.text_input("PVM numeris")
        miestas = st.text_input("Miestas")
        pk = st.text_input("Pašto kodas")
        st.markdown("**Kontaktas**")
        kv = st.text_input("Vardas")
        kp = st.text_input("Pavardė")
        ke = st.text_input("El. paštas")
        kt = st.text_input("Telefonas")
        st.markdown("**Kontaktas sąskaitoms**")
        sv = st.text_input("Vardas")
        sp = st.text_input("Pavardė")
        se = st.text_input("El. paštas")
        stl= st.text_input("Telefonas")
        coface = st.number_input("COFACE limitas", min_value=0.0)
        musu = round(coface/3,2)
        st.write(f"Mūsų limitas: {musu}")
        ab = st.selectbox("Atsiskaitymo būdas", ["originalūs dokumentai","platforma","skanuoti dokumentai"])
        at = st.text_input("Atsiskaitymo terminas")
        submit = st.form_submit_button("💾 Išsaugoti")
    if submit:
        dup = c.execute("""
            SELECT COUNT(*) FROM klientai
            WHERE pavadinimas=? AND miestas=? AND post_kodas=?
        """, (pavad, miestas, pk)).fetchone()[0]
        if dup:
            st.error("Toks klientas jau egzistuoja.")
        else:
            c.execute("""
                INSERT INTO klientai (
                    pavadinimas, vat_numeris, miestas, post_kodas,
                    kont_vardas, kont_pavarde, kont_email, kont_tel,
                    s_vardas, s_pavarde, s_email, s_tel,
                    coface_limitas, musu_limitas, ats_budas, ats_terminas
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                pavad, vat, miestas, pk,
                kv, kp, ke, kt,
                sv, sp, se, stl,
                coface, musu, ab, at
            ))
            conn.commit()
            st.success("Klientas įrašytas.")
    st.dataframe(pd.read_sql_query("SELECT * FROM klientai", conn))

# ─── 7. VILKIKAI ───────────────────────────────────────────────────────────────
elif modulis == "Vilkikai":
    st.title("DISPO – Vilkikų valdymas")
    marks = [r[0] for r in c.execute(
        "SELECT reiksme FROM lookup WHERE modulis='Vilkikai' AND kategorija='marke'"
    ).fetchall()]
    with st.form("vilk_form", clear_on_submit=True):
        nr = st.text_input("Numeris")
        if marks:
            mk = st.selectbox("Markė", marks)
        else:
            mk = st.text_input("Markė")
        pm = st.text_input("Pagaminimo metai")
        ta = st.date_input("Techninė apžiūra")
        vd = st.text_input("Vadybininkas")
        vv = st.text_input("Vairuotojai (kableliais)")
        pr = st.text_input("Priekaba")
        sub = st.form_submit_button("💾 Išsaugoti")
    if sub:
        if nr:
            c.execute("""
                INSERT INTO vilkikai (
                    numeris, marke, pagaminimo_metai,
                    tech_apziura, vadybininkas, vairuotojai, priekaba
                ) VALUES (?,?,?,?,?,?,?)
            """, (nr, mk, int(pm or 0), str(ta), vd, vv, pr))
            conn.commit()
            st.success("Vilkikas įrašytas.")
        else:
            st.warning("Numeris privalomas.")
    st.dataframe(pd.read_sql_query("SELECT * FROM vilkikai", conn))

# ─── 8. PRIEKABOS ───────────────────────────────────────────────────────────────
elif modulis == "Priekabos":
    st.title("DISPO – Priekabų valdymas")
    tips = [r[0] for r in c.execute(
        "SELECT reiksme FROM lookup WHERE modulis='Priekabos' AND kategorija='tipas'"
    ).fetchall()]
    with st.form("priek_form", clear_on_submit=True):
        if tips:
            tp = st.selectbox("Tipas", tips)
        else:
            tp = st.text_input("Tipas")
        num = st.text_input("Numeris")
        mr = st.text_input("Markė")
        pm = st.text_input("Pagaminimo metai")
        ta = st.date_input("Techninė apžiūra")
        pv = st.text_input("Priskirtas vilkikas")
        sb = st.form_submit_button("💾 Išsaugoti")
    if sb:
        if num:
            c.execute("""
                INSERT INTO priekabos (
                    priekabu_tipas, numeris, marke,
                    pagaminimo_metai, tech_apziura, priskIRTas_vilkikas
                ) VALUES (?,?,?,?,?,?)
            """, (tp, num, mr, int(pm or 0), str(ta), pv))
            conn.commit()
            st.success("Priekaba įrašyta.")
        else:
            st.warning("Numeris būtinas.")
    st.dataframe(pd.read_sql_query("SELECT * FROM priekabos", conn))

# ─── 9. GRUPĖS ─────────────────────────────────────────────────────────────────
elif modulis == "Grupės":
    st.title("DISPO – Darbo grupių valdymas")
    with st.form("grp_form", clear_on_submit=True):
        nr = st.text_input("Numeris")
        pv = st.text_input("Pavadinimas")
        ap = st.text_area("Aprašymas")
        sb = st.form_submit_button("💾 Išsaugoti")
    if sb:
        if nr and pv:
            c.execute("INSERT INTO grupes(numeris,pavadinimas,aprasymas) VALUES(?,?,?)", (nr,pv,ap))
            conn.commit(); st.success("Grupė įrašyta.")
        else:
            st.warning("Numeris ir pavadinimas būtini.")
    st.dataframe(pd.read_sql_query("SELECT * FROM grupes", conn))

# ─── 10. VAIRUOTOJAI ───────────────────────────────────────────────────────────
elif modulis == "Vairuotojai":
    st.title("DISPO – Vairuotojų valdymas")
    with st.form("drv_form", clear_on_submit=True):
        vd = st.text_input("Vardas")
        pv = st.text_input("Pavardė")
        gm = st.text_input("Gimimo metai")
        tt = st.text_input("Tautybė")
        vk = st.text_input("Priskirtas vilkikas")
        sb = st.form_submit_button("💾 Išsaugoti")
    if sb:
        if vd and pv:
            c.execute("""
                INSERT INTO vairuotojai (
                    vardas,pavarde,gimimo_metai,tautybe,priskirtas_vilkikas
                ) VALUES(?,?,?,?,?)
            """, (vd,pv,int(gm or 0),tt,vk))
            conn.commit(); st.success("Vairuotojas įrašytas.")
        else:
            st.warning("Vardas ir pavardė būtini.")
    st.dataframe(pd.read_sql_query("SELECT * FROM vairuotojai", conn))

# ─── 11. DARBUOTOJAI ───────────────────────────────────────────────────────────
elif modulis == "Darbuotojai":
    st.title("DISPO – Darbuotojų valdymas")
    pareig = [r[0] for r in c.execute(
        "SELECT reiksme FROM lookup WHERE modulis='Darbuotojai' AND kategorija='pareigybe'"
    ).fetchall()]
    grps = [r[2] for r in c.execute("SELECT id,numeris,pavadinimas FROM grupes").fetchall()]
    with st.form("emp_form", clear_on_submit=True):
        vd = st.text_input("Vardas")
        pv = st.text_input("Pavardė")
        pg = st.selectbox("Pareigybė", pareig) if pareig else st.text_input("Pareigybė")
        gr = st.selectbox("Grupė", grps) if grps else st.text_input("Grupė")
        em = st.text_input("El. paštas")
        ph = st.text_input("Telefonas")
        sb = st.form_submit_button("💾 Išsaugoti")
    if sb:
        if vd and pv:
            c.execute("""
                INSERT INTO darbuotojai (
                    vardas,pavarde,pareigybe,el_pastas,telefonas,grupe
                ) VALUES (?,?,?,?,?,?)
            """, (vd,pv,pg,em,ph,gr))
            conn.commit(); st.success("Darbuotojas įrašytas.")
        else:
            st.warning("Vardas ir pavardė būtini.")
    st.dataframe(pd.read_sql_query("SELECT * FROM darbuotojai", conn))
