import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, time, timedelta

# ─── Duomenų bazės prisijungimas ───────────────────────────────────────────────
conn = sqlite3.connect('dispo_new.db', check_same_thread=False)
c = conn.cursor()

# ─── Lookup lentelė visoms dropdown reikšmėms ─────────────────────────────────
c.execute("""
CREATE TABLE IF NOT EXISTS lookup (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    modulis TEXT,
    kategorija TEXT,
    reiksme TEXT UNIQUE
)
""")
conn.commit()

# ─── Pagrindinių lentelių sukūrimas ────────────────────────────────────────────
tables = {
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
for ddl in tables.values():
    c.execute(ddl)
conn.commit()

# ─── Šoninė meniu juosta ──────────────────────────────────────────────────────
modules = [
    "Kroviniai", "Vilkikai", "Priekabos",
    "Grupės", "Vairuotojai", "Klientai",
    "Darbuotojai", "Nustatymai"
]
modulis = st.sidebar.selectbox("📂 Pasirink modulį", modules)

# ─── NUSTATYMAI ───────────────────────────────────────────────────────────────
if modulis == "Nustatymai":
    st.title("DISPO – Sąrašų valdymas")

    sel_mod = st.selectbox("Modulis", [m for m in modules if m != "Nustatymai"])
    cats = [r[0] for r in c.execute(
        "SELECT DISTINCT kategorija FROM lookup WHERE modulis=?", (sel_mod,)
    ).fetchall()]

    col1, col2 = st.columns(2)
    esama = col1.selectbox("Esama kategorija", [""] + cats)
    nauja = col2.text_input("Arba įvesk naują")
    kat = nauja.strip() if nauja else esama

    st.markdown("---")
    if not kat:
        st.info("Pasirink arba įvesk kategoriją, kad galėtum valdyti reikšmes.")
    else:
        st.subheader(f"{sel_mod} – {kat}")
        values = [r[0] for r in c.execute(
            "SELECT reiksme FROM lookup WHERE modulis=? AND kategorija=?", (sel_mod, kat)
        ).fetchall()]
        st.write(values or "_(nėra įrašų)_")

        # Pridėti
        with st.form("ns_add", clear_on_submit=True):
            nv = st.text_input("Nauja reikšmė")
            go = st.form_submit_button("➕ Pridėti")
        if go and nv:
            try:
                c.execute(
                    "INSERT INTO lookup (modulis,kategorija,reiksme) VALUES (?,?,?)",
                    (sel_mod, kat, nv)
                )
                conn.commit()
                st.success("✅ Pridėta")
                st.experimental_rerun()
            except sqlite3.IntegrityError:
                st.warning("⚠️ Toks įrašas jau egzistuoja.")

        st.markdown("---")
        # Ištrinti
        if values:
            with st.form("ns_del", clear_on_submit=True):
                dv = st.selectbox("Ištrinti reikšmę", [""] + values)
                gd = st.form_submit_button("🗑 Ištrinti")
            if gd and dv:
                c.execute(
                    "DELETE FROM lookup WHERE modulis=? AND kategorija=? AND reiksme=?",
                    (sel_mod, kat, dv)
                )
                conn.commit()
                st.success("✅ Ištrinta")
                st.experimental_rerun()

# ─── KROVINIAI ────────────────────────────────────────────────────────────────
elif modulis == "Kroviniai":
    st.title("DISPO – Krovinių valdymas")

    with st.form("kro_form", clear_on_submit=False):
        c0, c1 = st.columns(2)
        klientai = [f"{r[1]} ({r[4]})" for r in c.execute(
            "SELECT id,pavadinimas,regionas,vat_numeris,miestas FROM klientai"
        ).fetchall()]
        klientas = c0.selectbox("Klientas", [""] + klientai, key="K_cli")
        uzs_nr = c0.text_input("Užsakymo numeris", key="K_un")
        pak_nr = c1.text_input("Pakrovimo numeris", key="K_pn")

        c2, c3 = st.columns(2)
        pak_data = c2.date_input("Pakrovimo data", date.today(), key="K_pd")
        pak_nuo = c2.time_input("Laikas nuo (pakrov.)", time(8, 0), key="K_pnuo")
        pak_iki = c3.time_input("Laikas iki (pakrov.)", time(17, 0), key="K_piki")

        c4, c5 = st.columns(2)
        isk_data = c4.date_input("Iškrovimo data", pak_data + timedelta(days=1), key="K_id")
        isk_nuo = c4.time_input("Laikas nuo (iškrov.)", time(8, 0), key="K_inuo")
        isk_iki = c5.time_input("Laikas iki (iškrov.)", time(17, 0), key="K_iiki")

        c6, c7 = st.columns(2)
        pak_s = c6.text_input("Pakrovimo šalis", key="K_ps")
        pak_m = c6.text_input("Pakrovimo miestas", key="K_pm")
        isk_s = c7.text_input("Iškrovimo šalis", key="K_is")
        isk_m = c7.text_input("Iškrovimo miestas", key="K_im")

        vilk_list = [r[0] for r in c.execute("SELECT numeris FROM vilkikai").fetchall()]
        vilk = st.selectbox("Vilkikas", [""] + vilk_list, key="K_vilk")
        priek = ""
        if vilk:
            row = c.execute("SELECT priekaba FROM vilkikai WHERE numeris=?", (vilk,)).fetchone()
            priek = row[0] if row else ""
        st.text_input("Priekaba", value=priek, disabled=True)

        km = st.number_input("Kilometrai", 0, key="K_km")
        fr = st.number_input("Frachtas (€)", 0.0, key="K_fr")
        sv = st.number_input("Svoris (kg)", 0, key="K_sv")
        pd = st.number_input("Padėklų skaičius", 0, key="K_pdks")

        bs_list = [r[0] for r in c.execute(
            "SELECT reiksme FROM lookup WHERE modulis='Kroviniai' AND kategorija='busena'"
        ).fetchall()]
        bus = st.selectbox("Būsena", bs_list or ["suplanuotas","pakrautas","iškrautas"], key="K_bus")

        submit = st.form_submit_button("💾 Įrašyti krovinį")

    if submit:
        if not klientas or not uzs_nr:
            st.error("❌ Privalomi laukai: Klientas ir Užsakymo numeris.")
        else:
            # suffix logic
            base = uzs_nr
            exist = [r[0] for r in c.execute(
                "SELECT uzsakymo_numeris FROM kroviniai WHERE uzsakymo_numeris LIKE ?", (base + "%",)
            ).fetchall()]
            suf = f"-{len(exist)}" if exist else ""
            final_nr = base + suf

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
                klientas, final_nr, pak_nr,
                str(pak_data), str(pak_nuo), str(pak_iki),
                str(isk_data), str(isk_nuo), str(isk_iki),
                pak_s, pak_m, isk_s, isk_m,
                vilk, priek, "",
                km, fr, sv, pd, bus
            ))
            conn.commit()
            st.success(f"✅ Įrašyta kaip {final_nr}.")

    st.subheader("📋 Krovinių sąrašas")
    st.dataframe(pd.read_sql_query("SELECT * FROM kroviniai", conn), use_container_width=True)

# ─── VILKIKAI ────────────────────────────────────────────────────────────────
elif modulis == "Vilkikai":
    st.title("DISPO – Vilkikų valdymas")
    with st.form("vi_form", clear_on_submit=True):
        num = st.text_input("Numeris")
        mark_list = [r[0] for r in c.execute(
            "SELECT reiksme FROM lookup WHERE modulis='Vilkikai' AND kategorija='marke'"
        ).fetchall()]
        mr = st.selectbox("Markė", [""]+mark_list) if mark_list else st.text_input("Markė")
        pm = st.number_input("Pagaminimo metai", 1900, date.today().year)
        tp = st.date_input("Techninė apžiūra")
        vd = st.text_input("Vadybininkas")
        vr = st.text_input("Vairuotojai (kableliai)")
        pr = st.text_input("Priekaba")
        sb = st.form_submit_button("💾 Išsaugoti vilkiką")
    if sb and num:
        try:
            c.execute("""
                INSERT INTO vilkikai (numeris,marke,pagaminimo_metai,tech_apziura,vadybininkas,vairuotojai,priekaba)
                VALUES (?,?,?,?,?,?,?)
            """, (num, mr, pm, str(tp), vd, vr, pr))
            conn.commit()
            st.success("✅ Vilkikas įrašytas.")
        except Exception as e:
            st.error(f"❌ {e}")
    st.subheader("📋 Vilkikų sąrašas")
    st.dataframe(pd.read_sql_query("SELECT * FROM vilkikai", conn), use_container_width=True)

# ─── PRIEKABOS ───────────────────────────────────────────────────────────────
elif modulis == "Priekabos":
    st.title("DISPO – Priekabų valdymas")
    with st.form("pr_form", clear_on_submit=True):
        tip_list = [r[0] for r in c.execute(
            "SELECT reiksme FROM lookup WHERE modulis='Priekabos' AND kategorija='tipas'"
        ).fetchall()]
        tp = st.selectbox("Tipas", [""]+tip_list) if tip_list else st.text_input("Tipas")
        num = st.text_input("Numeris")
        mr = st.text_input("Markė")
        pm = st.number_input("Pagaminimo metai", 1900, date.today().year)
        tpz = st.date_input("Techninė apžiūra")
        pv = st.selectbox("Priskirtas vilkikas", [""]+[r[0] for r in c.execute("SELECT numeris FROM vilkikai")])
        sb = st.form_submit_button("💾 Išsaugoti priekabą")
    if sb and num:
        try:
            c.execute("""
                INSERT INTO priekabos (priekabu_tipas,numeris,marke,pagaminimo_metai,tech_apziura,priskirtas_vilkikas)
                VALUES (?,?,?,?,?,?)
            """, (tp, num, mr, pm, str(tpz), pv))
            conn.commit()
            st.success("✅ Priekaba įrašyta.")
        except Exception as e:
            st.error(f"❌ {e}")
    st.subheader("📋 Priekabų sąrašas")
    st.dataframe(pd.read_sql_query("SELECT * FROM priekabos", conn), use_container_width=True)

# ─── GRUPĖS ─────────────────────────────────────────────────────────────────
elif modulis == "Grupės":
    st.title("DISPO – Grupės valdymas")
    with st.form("gr_form", clear_on_submit=True):
        num = st.text_input("Numeris")
        pav = st.text_input("Pavadinimas")
        apr = st.text_area("Aprašymas")
        sb = st.form_submit_button("💾 Išsaugoti grupę")
    if sb and num and pav:
        try:
            c.execute("INSERT INTO grupes (numeris,pavadinimas,aprasymas) VALUES (?,?,?)", (num,pav,apr))
            conn.commit()
            st.success("✅ Grupė įrašyta.")
        except Exception as e:
            st.error(f"❌ {e}")
    st.subheader("📋 Grupės sąrašas")
    st.dataframe(pd.read_sql_query("SELECT * FROM grupes", conn), use_container_width=True)

# ─── VAIRUOTOJAI ─────────────────────────────────────────────────────────────
elif modulis == "Vairuotojai":
    st.title("DISPO – Vairuotojų valdymas")
    with st.form("va_form", clear_on_submit=True):
        v = st.text_input("Vardas")
        p = st.text_input("Pavardė")
        g = st.number_input("Gimimo metai", 1900, date.today().year)
        t = st.text_input("Tautybė")
        pv = st.selectbox("Priskirtas vilkikas", [""]+[r[0] for r in c.execute("SELECT numeris FROM vilkikai")])
        sb = st.form_submit_button("💾 Išsaugoti vairuotoją")
    if sb and v and p:
        try:
            c.execute("""
                INSERT INTO vairuotojai (vardas,pavarde,gimimo_metai,tautybe,priskirtas_vilkikas)
                VALUES (?,?,?,?,?)
            """, (v,p,g,t,pv))
            conn.commit()
            st.success("✅ Vairuotojas įrašytas.")
        except Exception as e:
            st.error(f"❌ {e}")
    st.subheader("📋 Vairuotojų sąrašas")
    st.dataframe(pd.read_sql_query("SELECT * FROM vairuotojai", conn), use_container_width=True)

# ─── KLIENTAI ────────────────────────────────────────────────────────────────
elif modulis == "Klientai":
    st.title("DISPO – Klientų valdymas")
    with st.form("kl_form", clear_on_submit=True):
        p = st.text_input("Įmonės pavadinimas")
        vat = st.text_input("PVM numeris")
        m, pc = st.columns(2)
        miest = m.text_input("Miestas")
        kod = pc.text_input("Pašto kodas")
        kont = st.text_input("Kontaktai (v/p, el, tel)")
        skl = st.text_input("Sąskaitų kontaktas (v/p, el, tel)")
        cof = st.number_input("COFACE limitas", 0.0)
        ats = st.selectbox("Atsiskaitymo būdas", ["originalūs dokumentai","platforma","skanuoti dokumentai"])
        term = st.text_input("Atsiskaitymo terminas")
        sb = st.form_submit_button("💾 Išsaugoti klientą")
    if sb and p and miest and kod:
        exists = c.execute("""
            SELECT 1 FROM klientai WHERE pavadinimas=? AND miestas=? AND regionas=?
        """, (p, miest, kod)).fetchone()
        if exists:
            st.error("❌ Toks klientas jau egzistuoja.")
        else:
            c.execute("""
                INSERT INTO klientai
                (pavadinimas,kontaktai,salis,miestas,regionas,vat_numeris)
                VALUES (?,?,?,?,?,?)
            """, (p,kont,"",miest,kod,vat))
            conn.commit()
            st.success("✅ Klientas įrašytas.")
    st.subheader("📋 Klientų sąrašas")
    st.dataframe(pd.read_sql_query("SELECT * FROM klientai", conn), use_container_width=True)

# ─── DARBUOTOJAI ─────────────────────────────────────────────────────────────
elif modulis == "Darbuotojai":
    st.title("DISPO – Darbuotojų valdymas")
    with st.form("da_form", clear_on_submit=True):
        v = st.text_input("Vardas")
        p = st.text_input("Pavardė")
        pr_list = [r[0] for r in c.execute(
            "SELECT reiksme FROM lookup WHERE modulis='Darbuotojai' AND kategorija='pareigybe'"
        ).fetchall()]
        pr = st.selectbox("Pareigybė", [""]+pr_list) if pr_list else st.text_input("Pareigybė")
        gr_list = [r[2] for r in c.execute("SELECT id,numeris,pavadinimas FROM grupes").fetchall()]
        gr = st.selectbox("Grupė", [""]+gr_list) if gr_list else st.text_input("Grupė")
        email = st.text_input("El. paštas")
        tel = st.text_input("Telefono numeris")
        sb = st.form_submit_button("💾 Išsaugoti darbuotoją")
    if sb and v and p:
        c.execute("""
            INSERT INTO darbuotojai
            (vardas,pavarde,pareigybe,el_pastas,telefonas,grupe)
            VALUES (?,?,?,?,?,?)
        """, (v,p,pr,email,tel,gr))
        conn.commit()
        st.success("✅ Darbuotojas įrašytas.")
    st.subheader("📋 Darbuotojų sąrašas")
    st.dataframe(pd.read_sql_query("SELECT * FROM darbuotojai", conn), use_container_width=True)
