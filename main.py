import streamlit as st
import sqlite3
import pandas as pd
import random
from datetime import date, time, timedelta

# ─── Duomenų bazės prisijungimas ───────────────────────────────────────────────
conn = sqlite3.connect('dispo_new.db', check_same_thread=False)
c = conn.cursor()

# ─── Universali lookup lentelė ────────────────────────────────────────────────
c.execute("""
CREATE TABLE IF NOT EXISTS lookup (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kategorija TEXT,
    reiksme TEXT UNIQUE
)
""")
conn.commit()

# ─── Kitos lentelės ───────────────────────────────────────────────────────────
table_ddls = {
    "kroviniai": """
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
            kontaktai TEXT,
            salis TEXT,
            miestas TEXT,
            regionas TEXT,
            vat_numeris TEXT
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

# ─── Modulių pasirinkimas ────────────────────────────────────────────────────
moduliai = [
    "DISPO", "Kroviniai", "Vilkikai", "Priekabos",
    "Grupės", "Vairuotojai", "Klientai",
    "Darbuotojai", "Nustatymai"
]
modulis = st.sidebar.radio("📂 Pasirink modulį", moduliai)

# ─── DISPO – Planavimo lentelė ────────────────────────────────────────────────
if modulis == "DISPO":
    st.title("DISPO – Planavimas (horizontalus)")

    # Bendri stulpeliai
    common = [
        "Transporto grupė", "Eksp. grupės nr.",
        "Vilkiko nr.", "Ekspeditorius", "Trans. vadybininkas",
        "Priekabos nr.", "Vair. sk.", "Savaitinė atstova"
    ]
    # Dienos operaciniai stulpeliai
    day_cols = [
        "Bendras darbo laikas", "Likęs darbo laikas atvykus", "Atvykimo laikas",
        "Laikas nuo", "Laikas iki", "Vieta", "Atsakingas",
        "Tušti km", "Krauti km", "Kelių išlaidos (EUR)", "Frachtas (EUR)"
    ]
    # Generuojame 10 dienų horizontaliai
    start = date.today()
    days = [start + timedelta(days=i) for i in range(10)]
    cols = common.copy()
    for d in days:
        ds = d.strftime("%Y-%m-%d")
        cols += [f"{ds} – {col}" for col in day_cols]

    # Pavyzdiniai vilkikai
    trucks = [
        ("ABC123", "Tomas Mickus", "Laura Juknevičienė", "PRK001", 2, 24, "TG1", "EG2"),
        ("XYZ789", "Greta Kairytė", "Jonas Petrauskas", "PRK009", 1, 45, "TG1", "EG3"),
        ("DEF456", "Rasa Mikalauskienė", "Tomas Mickus", "PRK123", 2, 24, "TG2", "EG1"),
        ("GHI321", "Jonas Petrauskas", "Greta Kairytė", "PRK456", 1, 45, "TG2", "EG2"),
        ("JKL654", "Laura Juknevičienė", "Rasa Mikalauskienė", "PRK789", 2, 24, "TG3", "EG1")
    ]
    data = []
    for t in trucks:
        # Iškrovimas
        row_un = list(t)
        for _ in days:
            row_un += [None, None, f"{random.randint(10,12)}:{random.choice(['00','30'])}", "", "", random.choice(["Riga","Poznan"]), None, None, None, None, None]
        data.append(row_un)
        # Pakrovimas
        row_ld = list(t)
        for _ in days:
            row_ld += [9, 6, f"{random.randint(7,9)}:{random.choice(['00','30'])}", "08:00", "16:00",
                       random.choice(["Vilnius","Kaunas"]), t[2],
                       random.randint(20,120), random.randint(400,900), 15.0, random.randint(900,2400)]
        data.append(row_ld)

    df_dispo = pd.DataFrame(data, columns=cols)
    st.dataframe(df_dispo)

# ─── KROVINIAI ────────────────────────────────────────────────────────────────
elif modulis == "Kroviniai":
    st.title("DISPO – Krovinių valdymas")
    with st.form("krovinio_forma", clear_on_submit=False):
        clienti = [r[0] for r in c.execute("SELECT pavadinimas FROM klientai").fetchall()]
        col1, col2 = st.columns(2)
        klientas = col1.selectbox("Klientas", clienti) if clienti else col1.text_input("Klientas")
        uzs_nr = col2.text_input("Užsakymo numeris")
        pak_nr = st.text_input("Pakrovimo numeris")
        dcol1, dcol2 = st.columns(2)
        pak_data = dcol1.date_input("Pakrovimo data", date.today())
        pak_nuo = dcol1.time_input("Laikas nuo (pakrovimas)", time(8,0))
        pak_iki = dcol1.time_input("Laikas iki (pakrovimas)", time(17,0))
        isk_data = dcol2.date_input("Iškrovimo data", pak_data + timedelta(days=1))
        isk_nuo = dcol2.time_input("Laikas nuo (iškrovimas)", time(8,0))
        isk_iki = dcol2.time_input("Laikas iki (iškrovimas)", time(17,0))
        vcol1, vcol2 = st.columns(2)
        sal_pak = vcol1.text_input("Pakrovimo šalis"); m_pak = vcol1.text_input("Pakrovimo miestas")
        sal_isk = vcol2.text_input("Iškrovimo šalis"); m_isk = vcol2.text_input("Iškrovimo miestą")
        vcol3, vcol4 = st.columns(2)
        vilks = [r[0] for r in c.execute("SELECT numeris FROM vilkikai").fetchall()]
        vilk = vcol3.selectbox("Vilkikas", vilks) if vilks else vcol3.text_input("Vilkikas")
        prk_val = c.execute("SELECT priekaba FROM vilkikai WHERE numeris = ?", (vilk,)).fetchone()
        prk = prk_val[0] if prk_val and prk_val[0] else ""
        vcol4.text_input("Priekaba", value=prk, disabled=True)
        km = st.text_input("Kilometrai"); fr = st.text_input("Frachtas (€)")
        sv = st.text_input("Svoris (kg)"); pal = st.text_input("Padėklų skaičius")
        bs_opt = [r[0] for r in c.execute("SELECT reiksme FROM lookup WHERE kategorija = ?", ("busena",)).fetchall()]
        bus = st.selectbox("Būsena", bs_opt or ["suplanuotas","nesuplanuotas","pakrautas","iškrautas"])
        if st.form_submit_button("💾 Įrašyti krovinį"):
            if pak_data > isk_data:
                st.error("❌ Pakrovimo data negali būti vėlesnė už iškrovimo.")
            else:
                uzs = uzs_nr
                ex = [r[0] for r in c.execute("SELECT uzsakymo_numeris FROM kroviniai WHERE uzsakymo_numeris LIKE ?", (f"{uzs}%",)).fetchall()]
                if uzs in ex:
                    suf = sum(1 for x in ex if x.startswith(uzs))
                    uzs = f"{uzs}-{suf}"
                    st.warning(f"🔔 Numeris pakeistas į {uzs}.")
                c.execute("""
                    INSERT INTO kroviniai (
                        klientas, uzsakymo_numeris, pakrovimo_numeris,
                        pakrovimo_data, pakrovimo_laikas_nuo, pakrovimo_laikas_iki,
                        iskrovimo_data, iskrovimo_laikas_nuo, iskrovimo_laikas_iki,
                        pakrovimo_salis, pakrovimo_miestas, iskrovimo_salis, iskrovimo_miestas,
                        vilkikas, priekaba, atsakingas_vadybininkas,
                        kilometrai, frachtas, svoris, paleciu_skaicius, busena
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    klientas, uzs, pak_nr,
                    str(pak_data), str(pak_nuo), str(pak_iki),
                    str(isk_data), str(isk_nuo), str(isk_iki),
                    sal_pak, m_pak, sal_isk, m_isk,
                    vilk, prk, f"vadyb_{vilk.lower()}",
                    int(km or 0), float(fr or 0), int(sv or 0), int(pal or 0), bus
                ))
                conn.commit(); st.success("✅ Išsaugojau krovinį.")
    st.subheader("📋 Krovinių sąrašas")
    st.dataframe(pd.read_sql_query("SELECT * FROM kroviniai", conn))

# ─── VILKIKAI ────────────────────────────────────────────────────────────────
elif modulis == "Vilkikai":
    st.title("DISPO – Vilkikų valdymas")
    with st.form("vilk_form", clear_on_submit=True):
        num = st.text_input("Numeris")
        marks = [r[0] for r in c.execute("SELECT reiksme FROM lookup WHERE kategorija = ?", ("vilkiku_marke",)).fetchall()]
        m = st.selectbox("Markė", marks) if marks else st.text_input("Markė")
        pm = st.text_input("Pagaminimo metai")
        ta = st.date_input("Tech. apžiūra")
        vd = st.text_input("Vadybininkas"); vr = st.text_input("Vairuotojai (csv)")
        pr = st.text_input("Priekaba")
        if st.form_submit_button("💾 Įrašyti vilkiką"):
            if not num: st.warning("⚠️ Numeris būtinas.")
            else:
                try:
                    c.execute("""
                        INSERT INTO vilkikai (
                            numeris, marke, pagaminimo_metai, tech_apziura,
                            vadybininkas, vairuotojai, priekaba
                        ) VALUES (?,?,?,?,?,?,?)
                    """, (num, m, int(pm or 0), str(ta), vd, vr, pr))
                    conn.commit(); st.success("✅ Išsaugojau.")
                except Exception as e:
                    st.error(f"❌ {e}")
    st.dataframe(pd.read_sql_query("SELECT * FROM vilkikai", conn))

# ─── PRIEKABOS ───────────────────────────────────────────────────────────────
elif modulis == "Priekabos":
    st.title("DISPO – Priekabų valdymas")
    with st.form("priek_form", clear_on_submit=True):
        types = [r[0] for r in c.execute("SELECT reiksme FROM lookup WHERE kategorija = ?", ("priekabu_tipas",)).fetchall()]
        t = st.selectbox("Tipas", types) if types else st.text_input("Tipas")
        num = st.text_input("Numeris"); mk = st.text_input("Markė")
        pm = st.text_input("Pagaminimo metai"); ta = st.date_input("Tech. apžiūra")
        pv = st.text_input("Priskirtas vilkikas")
        if st.form_submit_button("💾 Išsaugoti"):
            if not num: st.warning("⚠️ Numeris būtinas.")
            else:
                try:
                    c.execute("""
                        INSERT INTO priekabos (
                            priekabu_tipas, numeris, marke,
                            pagaminimo_metai, tech_apziura, priskirtas_vilkikas
                        ) VALUES (?,?,?,?,?,?)
                    """, (t, num, mk, int(pm or 0), str(ta), pv))
                    conn.commit(); st.success("✅ Išsaugojau.")
                except Exception as e:
                    st.error(f"❌ {e}")
    st.dataframe(pd.read_sql_query("SELECT * FROM priekabos", conn))

# ─── GRUPĖS ─────────────────────────────────────────────────────────────────
elif modulis == "Grupės":
    st.title("DISPO – Grupės")
    with st.form("grp_form", clear_on_submit=True):
        nr = st.text_input("Numeris"); pav = st.text_input("Pavadinimas")
        apr = st.text_area("Aprašymas")
        if st.form_submit_button("💾 Išsaugoti"):
            if not nr or not pav: st.warning("⚠️ Numeris ir pavadinimas būtini.")
            else:
                try:
                    c.execute("INSERT INTO grupes(numeris,pavadinimas,aprasymas) VALUES(?,?,?)", (nr, pav, apr))
                    conn.commit(); st.success("✅ Išsaugojau.")
                except Exception as e:
                    st.error(f"❌ {e}")
    st.dataframe(pd.read_sql_query("SELECT * FROM grupes", conn))

# ─── VAIRUOTOJAI ─────────────────────────────────────────────────────────────
elif modulis == "Vairuotojai":
    st.title("DISPO – Vairuotojai")
    with st.form("drv_form", clear_on_submit=True):
        vd = st.text_input("Vardas"); pv = st.text_input("Pavardė")
        gm = st.text_input("Gimimo metai"); tt = st.text_input("Tautybė")
        pvk = st.text_input("Priskirtas vilkikas")
        if st.form_submit_button("💾 Išsaugoti"):
            if not vd or not pv: st.warning("⚠️ Vardas ir pavardė būtini.")
            else:
                try:
                    c.execute("""
                        INSERT INTO vairuotojai (
                            vardas,pavarde,gimimo_metai,tautybe,priskirtas_vilkikas
                        ) VALUES(?,?,?,?,?)
                    """, (vd, pv, int(gm or 0), tt, pvk))
                    conn.commit(); st.success("✅ Išsaugojau.")
                except Exception as e:
                    st.error(f"❌ {e}")
    st.dataframe(pd.read_sql_query("SELECT * FROM vairuotojai", conn))

# ─── KLIENTAI ────────────────────────────────────────────────────────────────
elif modulis == "Klientai":
    st.title("DISPO – Klientai")
    with st.form("kl_form", clear_on_submit=True):
        iv = st.text_input("Įmonės pavadinimas"); kt = st.text_input("Kontaktai")
        sl = st.text_input("Šalis"); ms = st.text_input("Miestas")
        rg = st.text_input("Regionas"); pv = st.text_input("PVM numeris")
        if st.form_submit_button("💾 Išsaugoti"):
            if not iv: st.warning("⚠️ Pavadinimas būtinas.")
            else:
                try:
                    c.execute("""
                        INSERT INTO klientai (
                            pavadinimas,kontaktai,salis,miestas,regionas,vat_numeris
                        ) VALUES(?,?,?,?,?,?)
                    """, (iv, kt, sl, ms, rg, pv))
                    conn.commit(); st.success("✅ Išsaugojau.")
                except Exception as e:
                    st.error(f"❌ {e}")
    st.dataframe(pd.read_sql_query("SELECT * FROM klientai", conn))

# ─── DARBUOTOJAI ─────────────────────────────────────────────────────────────
elif modulis == "Darbuotojai":
    st.title("DISPO – Darbuotojai")
    p_list = [r[0] for r in c.execute("SELECT reiksme FROM lookup WHERE kategorija = ?", ("pareigybe",)).fetchall()]
    g_list = [r[2] for r in c.execute("SELECT id,numeris,pavadinimas FROM grupes").fetchall()]
    with st.form("emp_form", clear_on_submit=True):
        vd = st.text_input("Vardas"); pv = st.text_input("Pavardė")
        pg = st.selectbox("Pareigybė", p_list) if p_list else st.text_input("Pareigybė")
        gr = st.selectbox("Grupė", g_list) if g_list else st.text_input("Grupė")
        em = st.text_input("El. paštas"); ph = st.text_input("Telefonas")
        if st.form_submit_button("💾 Išsaugoti"):
            if not vd or not pv: st.warning("⚠️ Vardas ir pavardė būtini.")
            else:
                try:
                    c.execute("""
                        INSERT INTO darbuotojai (
                            vardas,pavarde,pareigybe,el_pastas,telefonas,grupe
                        ) VALUES(?,?,?,?,?,?)
                    """, (vd, pv, pg, em, ph, gr))
                    conn.commit(); st.success("✅ Išsaugojau.")
                except Exception as e:
                    st.error(f"❌ {e}")
    st.dataframe(pd.read_sql_query("SELECT * FROM darbuotojai", conn))

# ─── NUSTATYMAI ───────────────────────────────────────────────────────────────
elif modulis == "Nustatymai":
    st.title("DISPO – Sąrašų valdymas")
    kategorijos = [row[0] for row in c.execute("SELECT DISTINCT kategorija FROM lookup").fetchall()]
    col1, col2 = st.columns(2)
    esama = col1.selectbox("Esama kategorija", [""] + kategorijos)
    nauja_kat = col2.text_input("Arba nauja kategorija")
    kat = nauja_kat.strip() if nauja_kat else esama
    st.markdown("---")
    if kat:
        st.subheader(f"Kategorija: **{kat}**")
        values = [r[0] for r in c.execute("SELECT reiksme FROM lookup WHERE kategorija = ?", (kat,)).fetchall()]
        st.write(values or "_(nerasta reikšmių)_")
        new_val = st.text_input("Pridėti naują reikšmę")
        if st.button("➕ Pridėti reikšmę"):
            if new_val:
                try:
                    c.execute("INSERT INTO lookup(kategorija, reiksme) VALUES(?,?)", (kat, new_val))
                    conn.commit(); st.success(f"✅ Pridėta: {new_val}")
                except sqlite3.IntegrityError:
                    st.warning("⚠️ Toks elementas jau egzistuoja.")
        to_del = st.selectbox("Ištrinti reikšmę", [""] + values)
        if st.button("🗑 Ištrinti reikšmę"):
            if to_del:
                c.execute("DELETE FROM lookup WHERE kategorija = ? AND reiksme = ?", (kat, to_del))
                conn.commit(); st.success(f"✅ Ištrinta: {to_del}")
    else:
        st.info("Pasirink arba sukurk kategoriją, kad valdytum reikšmes.")
