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

    # 1) Pasirinktas modulis (iš tų be pačių Nustatymų)
    sel_mod = st.selectbox("Modulis", [m for m in modules if m != "Nustatymai"], key="ns_mod")

    # 2) Gauname kategorijas to modulio
    cats = [r[0] for r in c.execute(
        "SELECT DISTINCT kategorija FROM lookup WHERE modulis=?", (sel_mod,)
    ).fetchall()]

    # 3) Esama arba nauja kategorija
    col1, col2 = st.columns(2)
    esama = col1.selectbox("Esama kategorija", [""] + cats, key="ns_esama")
    nauja = col2.text_input("Arba įrašyk naują", key="ns_nauja")
    kat = nauja.strip() if nauja else esama

    st.markdown("---")
    if not kat:
        st.info("Pasirink arba įrašyk kategoriją, kad galėtum valdyti reikšmes.")
    else:
        st.subheader(f"{sel_mod} – {kat}")
        # esamos reikšmės
        values = [r[0] for r in c.execute(
            "SELECT reiksme FROM lookup WHERE modulis=? AND kategorija=?", (sel_mod, kat)
        ).fetchall()]
        st.write(values or "_(nėra įrašų)_")

        # ––––– Pridėti naują –––––
        with st.form("ns_add_form", clear_on_submit=True):
            newv = st.text_input("Pridėti naują reikšmę", key="ns_newv")
            submit_add = st.form_submit_button("➕ Pridėti")
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

        st.markdown("---")

        # ––––– Ištrinti esamą –––––
        if values:
            with st.form("ns_del_form", clear_on_submit=True):
                istr = st.selectbox("Ištrinti reikšmę", [""] + values, key="ns_del_sel")
                submit_del = st.form_submit_button("🗑 Ištrinti")
            if submit_del and istr:
                c.execute(
                    "DELETE FROM lookup WHERE modulis=? AND kategorija=? AND reiksme=?",
                    (sel_mod, kat, istr)
                )
                conn.commit()
                st.success(f"✅ Ištrinta: {istr}")
                st.experimental_rerun()

# ─── KROVINIAI ────────────────────────────────────────────────────────────────
elif modulis == "Kroviniai":
    st.title("DISPO – Krovinių valdymas")

    with st.form("kro_form", clear_on_submit=False):
        c0, c1 = st.columns(2)
        klientai = [f"{r[1]} ({r[4]})" for r in c.execute(
            "SELECT id,pavadinimas,regionas,vat_numeris,miestas FROM klientai"
        ).fetchall()]
        klientas = c0.selectbox("Klientas", [""] + klientai, key="kro_cli")
        uzsakymo_numeris = c0.text_input("Užsakymo numeris", key="kro_un")
        pakrovimo_numeris = c1.text_input("Pakrovimo numeris", key="kro_pn")

        c2, c3 = st.columns(2)
        pakrovimo_data = c2.date_input("Pakrovimo data", date.today(), key="kro_pd")
        pak_nuo = c2.time_input("Laikas nuo (pakr.)", time(8,0), key="kro_pnuo")
        iskrovimo_data = c3.date_input("Iškrovimo data", pakrovimo_data+timedelta(days=1), key="kro_id")
        isk_nuo = c3.time_input("Laikas nuo (išk.)", time(8,0), key="kro_inuo")

        c4, c5 = st.columns(2)
        pak_iki = c4.time_input("Laikas iki (pakr.)", time(17,0), key="kro_piki")
        isk_iki = c5.time_input("Laikas iki (išk.)", time(17,0), key="kro_iiki")

        c6, c7 = st.columns(2)
        pak_salis = c6.text_input("Pakrovimo šalis", key="kro_ps")
        pak_miestas = c6.text_input("Pakrovimo miestas", key="kro_pm")
        isk_salis = c7.text_input("Iškrovimo šalis", key="kro_is")
        isk_miestas = c7.text_input("Iškrovimo miestas", key="kro_im")

        # vilkikas + priekaba
        vilkikai = [r[0] for r in c.execute("SELECT numeris FROM vilkikai").fetchall()]
        vilkikas = c2.selectbox("Vilkikas", [""]+vilkikai, key="kro_vilk")
        priekaba = ""
        if vilkikas:
            row = c.execute("SELECT priekaba FROM vilkikai WHERE numeris=?", (vilkikas,)).fetchone()
            priekaba = row[0] if row else ""
        c3.text_input("Priekaba", value=priekaba, disabled=True, key="kro_pr")

        km, fr, sv = c4.number_input("Kilometrai", 0, key="kro_km"), c5.number_input("Frachtas (€)", 0.0, key="kro_fr"), c6.number_input("Svoris (kg)", 0, key="kro_sv")
        pal = st.number_input("Padėklų skaičius", 0, key="kro_pl")

        bus_list = [r[0] for r in c.execute("SELECT reiksme FROM lookup WHERE modulis='Kroviniai' AND kategorija='busena'").fetchall()]
        busena = st.selectbox("Būsena", bus_list or ["suplanuotas","pakrautas","iškrautas"], key="kro_bs")

        submit = st.form_submit_button("💾 Įrašyti krovinį", key="kro_submit")

    if submit:
        if pakrovimo_data > iskrovimo_data:
            st.error("❌ Pakrovimo data vėlesnė už iškrovimo.")
        elif not klientas or not uzsakymo_numeris:
            st.error("❌ Pasirink klientą ir įvesk užsakymo numerį.")
        else:
            # unique uzsakymo numerio sufiksas
            base = uzsakymo_numeris
            existing = [r[0] for r in c.execute(
                "SELECT uzsakymo_numeris FROM kroviniai WHERE uzsakymo_numeris LIKE ?", (base+"%",)
            ).fetchall()]
            suffix = ""
            if existing:
                count = len(existing)
                suffix = f"-{count}"
            final_un = base + suffix

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
                klientas, final_un, pakrovimo_numeris,
                str(pakrovimo_data), str(pak_nuo), str(pak_iki),
                str(iskrovimo_data), str(isk_nuo), str(isk_iki),
                pak_salis, pak_miestas, isk_salis, isk_miestas,
                vilkikas, priekaba, "",
                km, fr, sv, pal, busena
            ))
            conn.commit()
            st.success(f"✅ Krovinys įrašytas kaip {final_un}.")

    st.subheader("📋 Krovinių sąrašas")
    df = pd.read_sql_query("SELECT * FROM kroviniai", conn)
    st.dataframe(df)

# ─── VILKIKAI ────────────────────────────────────────────────────────────────
elif modulis == "Vilkikai":
    st.title("DISPO – Vilkikų valdymas")
    with st.form("vi_form", clear_on_submit=True):
        numeris = st.text_input("Vilkiko numeris", key="vi_num")
        # dinaminė markė
        marke_list = [r[0] for r in c.execute(
            "SELECT reiksme FROM lookup WHERE modulis='Vilkikai' AND kategorija='marke'"
        ).fetchall()]
        marke = st.selectbox("Markė", [""]+marke_list, key="vi_marke") \
            if marke_list else st.text_input("Markė", key="vi_marke_txt")
        pag = st.number_input("Pagaminimo metai", 1900, date.today().year, key="vi_pag")
        tech = st.date_input("Techninė apžiūra", key="vi_tech")
        vadyb = st.text_input("Vadybininkas", key="vi_vadyb")
        vair = st.text_input("Vairuotojai (kableliai)", key="vi_vair")
        prie = st.text_input("Priekaba", key="vi_prie")

        submit = st.form_submit_button("💾 Įrašyti vilkiką", key="vi_submit")
    if submit and numeris:
        try:
            c.execute("""
                INSERT INTO vilkikai
                (numeris,marke,pagaminimo_metai,tech_apziura,vadybininkas,vairuotojai,priekaba)
                VALUES (?,?,?,?,?,?,?)
            """, (numeris, marke, pag, str(tech), vadyb, vair, prie))
            conn.commit()
            st.success("✅ Vilkikas įrašytas.")
        except Exception as e:
            st.error(f"❌ {e}")

    st.subheader("📋 Vilkikų sąrašas")
    st.dataframe(pd.read_sql_query("SELECT * FROM vilkikai", conn))

# ─── PRIEKABOS ───────────────────────────────────────────────────────────────
elif modulis == "Priekabos":
    st.title("DISPO – Priekabų valdymas")
    with st.form("pr_form", clear_on_submit=True):
        tip_list = [r[0] for r in c.execute(
            "SELECT reiksme FROM lookup WHERE modulis='Priekabos' AND kategorija='tipas'"
        ).fetchall()]
        tip = st.selectbox("Priekabos tipas", [""]+tip_list, key="pr_tip") \
            if tip_list else st.text_input("Priekabos tipas", key="pr_tip_txt")
        num = st.text_input("Numeris", key="pr_num")
        mar = st.text_input("Markė", key="pr_mar")
        pag = st.number_input("Pagaminimo metai", 1900, date.today().year, key="pr_pag")
        tech = st.date_input("Techninė apžiūra", key="pr_tech")
        asv = st.selectbox("Priskirtas vilkikas", [""] + [r[0] for r in c.execute("SELECT numeris FROM vilkikai")], key="pr_asv")

        submit = st.form_submit_button("💾 Išsaugoti priekabą", key="pr_submit")
    if submit and num:
        try:
            c.execute("""
                INSERT INTO priekabos
                (priekabu_tipas,numeris,marke,pagaminimo_metai,tech_apziura,priskirtas_vilkikas)
                VALUES (?,?,?,?,?,?)
            """, (tip, num, mar, pag, str(tech), asv))
            conn.commit()
            st.success("✅ Priekaba įrašyta.")
        except Exception as e:
            st.error(f"❌ {e}")

    st.subheader("📋 Priekabų sąrašas")
    st.dataframe(pd.read_sql_query("SELECT * FROM priekabos", conn))

# ─── GRUPĖS ─────────────────────────────────────────────────────────────────
elif modulis == "Grupės":
    st.title("DISPO – Darbo grupių valdymas")
    with st.form("gr_form", clear_on_submit=True):
        num = st.text_input("Grupės numeris", key="gr_num")
        pav = st.text_input("Pavadinimas", key="gr_pav")
        apr = st.text_area("Aprašymas", key="gr_apr")
        submit = st.form_submit_button("💾 Išsaugoti grupę", key="gr_submit")
    if submit and num and pav:
        try:
            c.execute("INSERT INTO grupes(numeris,pavadinimas,aprasymas) VALUES (?,?,?)", (num,pav,apr))
            conn.commit()
            st.success("✅ Grupė įrašyta.")
        except Exception as e:
            st.error(f"❌ {e}")

    st.subheader("📋 Grupės sąrašas")
    st.dataframe(pd.read_sql_query("SELECT * FROM grupes", conn))

# ─── VAIRUOTOJAI ─────────────────────────────────────────────────────────────
elif modulis == "Vairuotojai":
    st.title("DISPO – Vairuotojų valdymas")
    with st.form("va_form", clear_on_submit=True):
        v = st.text_input("Vardas", key="va_v")
        p = st.text_input("Pavardė", key="va_p")
        g = st.number_input("Gimimo metai", 1900, date.today().year, key="va_g")
        t = st.text_input("Tautybė", key="va_t")
        pv = st.selectbox("Priskirtas vilkikas", [""]+[r[0] for r in c.execute("SELECT numeris FROM vilkikai")], key="va_pr")
        submit = st.form_submit_button("💾 Išsaugoti vairuotoją", key="va_submit")
    if submit and v and p:
        try:
            c.execute("INSERT INTO vairuotojai(vardas,pavarde,gimimo_metai,tautybe,priskirtas_vilkikas) VALUES (?,?,?,?,?)",
                      (v,p,g,t,pv))
            conn.commit()
            st.success("✅ Vairuotojas įrašytas.")
        except Exception as e:
            st.error(f"❌ {e}")

    st.subheader("📋 Vairuotojų sąrašas")
    st.dataframe(pd.read_sql_query("SELECT * FROM vairuotojai", conn))

# ─── KLIENTAI ────────────────────────────────────────────────────────────────
elif modulis == "Klientai":
    st.title("DISPO – Klientų valdymas")
    with st.form("kl_form", clear_on_submit=True):
        p = st.text_input("Įmonės pavadinimas", key="kl_pav")
        vat = st.text_input("PVM numeris", key="kl_vat")
        m, pc = st.columns(2)
        miest = m.text_input("Miestas", key="kl_m")
        pd = pc.text_input("Pašto kodas", key="kl_pc")
        kont = st.text_input("Kontaktai (v/p, el, tel)", key="kl_k")
        skl = st.text_input("Sąskaitų kontaktas (v/p, el, tel)", key="kl_skl")
        cof = st.number_input("COFACE limitas", 0.0, key="kl_cof")
        atsisk = st.selectbox("Atsiskaitymo būdas", ["originalūs dokumentai","platforma","skanuoti dokumentai"], key="kl_atsb")
        term = st.text_input("Atsiskaitymo terminas", key="kl_term")
        submit = st.form_submit_button("💾 Išsaugoti klientą", key="kl_submit")
    if submit and p and miest and pd:
        # unikalumas pagal pavadinimą+miestą+pc
        exists = c.execute("""
            SELECT 1 FROM klientai WHERE pavadinimas=? AND miestas=? AND regionas=?
        """, (p, miest, pd)).fetchone()
        if exists:
            st.error("❌ Toks klientas jau egzistuoja.")
        else:
            try:
                c.execute("""
                    INSERT INTO klientai
                    (pavadinimas,kontaktai,salis,miestas,regionas,vat_numeris)
                    VALUES (?,?,?,?,?,?)
                """, (p,kont,"",miest,pd,vat))
                conn.commit()
                st.success("✅ Klientas įrašytas.")
            except Exception as e:
                st.error(f"❌ {e}")

    st.subheader("📋 Klientų sąrašas")
    st.dataframe(pd.read_sql_query("SELECT * FROM klientai", conn))

# ─── DARBUOTOJAI ─────────────────────────────────────────────────────────────
elif modulis == "Darbuotojai":
    st.title("DISPO – Darbuotojų valdymas")
    with st.form("da_form", clear_on_submit=True):
        v = st.text_input("Vardas", key="da_v")
        p = st.text_input("Pavardė", key="da_p")
        # pareigybės iš lookup
        pr_list = [r[0] for r in c.execute("SELECT reiksme FROM lookup WHERE modulis='Darbuotojai' AND kategorija='pareigybe'").fetchall()]
        pr = st.selectbox("Pareigybė", [""]+pr_list, key="da_pr") if pr_list else st.text_input("Pareigybė", key="da_pr_txt")
        # grupės iš grupes
        gr_list = [r[2] for r in c.execute("SELECT id,numeris,pavadinimas FROM grupes").fetchall()]
        gr = st.selectbox("Grupė", [""]+gr_list, key="da_gr") if gr_list else st.text_input("Grupė", key="da_gr_txt")
        email = st.text_input("El. paštas", key="da_em")
        tel = st.text_input("Telefono numeris", key="da_tel")
        submit = st.form_submit_button("💾 Išsaugoti darbuotoją", key="da_submit")
    if submit and v and p:
        try:
            c.execute("""
                INSERT INTO darbuotojai
                (vardas,pavarde,pareigybe,el_pastas,telefonas,grupe)
                VALUES (?,?,?,?,?,?)
            """, (v,p,pr,email,tel,gr))
            conn.commit()
            st.success("✅ Darbuotojas įrašytas.")
        except Exception as e:
            st.error(f"❌ {e}")

    st.subheader("📋 Darbuotojų sąrašas")
    st.dataframe(pd.read_sql_query("SELECT * FROM darbuotojai", conn))
