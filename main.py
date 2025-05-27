import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, time, timedelta

# ─── Duomenų bazės ryšys ────────────────────────────────────────────────
conn = sqlite3.connect('dispo_new.db', check_same_thread=False)
c = conn.cursor()

# ─── Lookup lentelė visiems dropdown ―────────────────────────────────
c.execute("""
CREATE TABLE IF NOT EXISTS lookup (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    modulis TEXT,
    kategorija TEXT,
    reiksme TEXT UNIQUE
)
""")

# ─── Pagrindinės lentelės ─────────────────────────────────────────────
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
    kontaktai TEXT,
    salis TEXT,
    miestas TEXT,
    regionas TEXT,
    vat_numeris TEXT
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

# ─── Sidebar ―───────────────────────────────────────────────────────────
modules = [
    "Kroviniai", "Vilkikai", "Priekabos",
    "Grupės", "Vairuotojai", "Klientai",
    "Darbuotojai", "Nustatymai"
]
modulis = st.sidebar.radio("📂 Pasirink modulį", modules)

# ─── NUSTATYMAI: dinamiški dropdown reikšmės ──────────────────────────
if modulis == "Nustatymai":
    st.title("DISPO – Sąrašų valdymas")

    sel_mod = st.selectbox("Modulis", [m for m in modules if m != "Nustatymai"], key="ns_mod")

    # Išryškinam kategorijas šiam moduliui
    cats = [r[0] for r in c.execute(
        "SELECT DISTINCT kategorija FROM lookup WHERE modulis=?", (sel_mod,)
    ).fetchall()]

    col1, col2 = st.columns(2)
    esama = col1.selectbox("Esama kategorija", [""] + cats, key="ns_esama")
    nauja_kat = col2.text_input("Arba įveskite naują", key="ns_nauja")
    kategorija = nauja_kat.strip() if nauja_kat else esama

    st.markdown("---")
    if not kategorija:
        st.info("Pasirinkite arba įveskite naują kategoriją, kad galėtumėte valdyti reikšmes.")
    else:
        st.subheader(f"{sel_mod} – {kategorija}")

        # Esamos reikšmės
        values = [r[0] for r in c.execute(
            "SELECT reiksme FROM lookup WHERE modulis=? AND kategorija=?", (sel_mod, kategorija)
        ).fetchall()]
        st.write(values or "_(nėra įrašų)_")

        # Formos pridėjimui
        with st.form("ns_add_form", clear_on_submit=True):
            nv = st.text_input("Pridėti naują reikšmę", key="ns_add_val")
            add = st.form_submit_button("➕ Pridėti", key="ns_add_btn")
        if add and nv:
            try:
                c.execute(
                    "INSERT INTO lookup (modulis,kategorija,reiksme) VALUES (?,?,?)",
                    (sel_mod, kategorija, nv)
                )
                conn.commit()
                st.success(f"✅ Pridėta: {nv}")
                st.experimental_rerun()
            except sqlite3.IntegrityError:
                st.warning("⚠️ Toks įrašas jau egzistuoja.")

        st.markdown("---")

        # Formos trynimui
        if values:
            with st.form("ns_del_form", clear_on_submit=True):
                dv = st.selectbox("Ištrinti reikšmę", [""] + values, key="ns_del_val")
                delete = st.form_submit_button("🗑 Ištrinti", key="ns_del_btn")
            if delete and dv:
                c.execute(
                    "DELETE FROM lookup WHERE modulis=? AND kategorija=? AND reiksme=?",
                    (sel_mod, kategorija, dv)
                )
                conn.commit()
                st.success(f"✅ Ištrinta: {dv}")
                st.experimental_rerun()

# ─── KROVINIAI ―──────────────────────────────────────────────────────────
elif modulis == "Kroviniai":
    st.title("DISPO – Krovinių valdymas")

    with st.form("kro_form", clear_on_submit=False):
        # 1 eilutė
        c0, c1 = st.columns(2)
        clients = c.execute("SELECT id,pavadinimas,regionas,miestas FROM klientai").fetchall()
        klientai = [f"{r[1]} {r[2]} {r[3]}" for r in clients]
        klientas = c0.selectbox("Klientas", [""] + klientai, key="kro_kl")
        uzs_nr = c0.text_input("Užsakymo numeris", key="kro_un")
        pak_nr = c1.text_input("Pakrovimo numeris", key="kro_pn")

        # 2 eilutė: datos/laikai
        c2, c3 = st.columns(2)
        pak_data = c2.date_input("Pakrovimo data", date.today(), key="kro_pd")
        pak_nuo = c2.time_input("Laikas nuo (pakrovimas)", time(8,0), key="kro_pnu")
        pak_iki = c3.time_input("Laikas iki (pakrovimas)", time(17,0), key="kro_pik")

        # 3 eilutė: iškrovimo datos/laikai
        c4, c5 = st.columns(2)
        isk_data = c4.date_input("Iškrovimo data", pak_data + timedelta(days=1), key="kro_id")
        isk_nuo = c4.time_input("Laikas nuo (iškrovimas)", time(8,0), key="kro_inu")
        isk_iki = c5.time_input("Laikas iki (iškrovimas)", time(17,0), key="kro_iki")

        # 4 eilutė: šalys / miestai
        c6, c7 = st.columns(2)
        pak_s = c6.text_input("Pakrovimo šalis", key="kro_ps")
        pak_m = c6.text_input("Pakrovimo miestas", key="kro_pm")
        isk_s = c7.text_input("Iškrovimo šalis", key="kro_is")
        isk_m = c7.text_input("Iškrovimo miestas", key="kro_im")

        # 5 eilutė: vilkikas / priekaba
        vilk_list = [r[0] for r in c.execute("SELECT numeris FROM vilkikai").fetchall()]
        vilk = st.selectbox("Vilkikas", [""] + vilk_list, key="kro_vilk")
        priek = ""
        if vilk:
            row = c.execute("SELECT priekaba FROM vilkikai WHERE numeris=?", (vilk,)).fetchone()
            priek = row[0] if row else ""
        st.text_input("Priekaba", value=priek, disabled=True, key="kro_prk")

        # 6 eilutė: skaičiai
        km = st.number_input("Kilometrai", min_value=0, key="kro_km")
        fr = st.number_input("Frachtas (€)", min_value=0.0, key="kro_fr")
        sv = st.number_input("Svoris (kg)", min_value=0, key="kro_sv")
        pdks = st.number_input("Padėklų skaičius", min_value=0, key="kro_pdks")

        # 7 eilutė: būsena iš lookup
        bus_list = [r[0] for r in c.execute(
            "SELECT reiksme FROM lookup WHERE modulis='Kroviniai' AND kategorija='busena'"
        ).fetchall()]
        bus = st.selectbox("Būsena", bus_list or ["suplanuotas","pakrautas","iškrautas"], key="kro_bus")

        submit = st.form_submit_button("💾 Įrašyti krovinį", key="kro_submit")

    if submit:
        if not klientas or not uzs_nr:
            st.error("❌ Privalomi laukai: Klientas ir Užsakymo numeris.")
        else:
            # Jeigu toks pat uzsakymo numeris, pridedam sufiksą "-n"
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
                km, fr, sv, pdks, bus
            ))
            conn.commit()
            st.success(f"✅ Įrašyta su numeriu: {final_nr}")

    st.subheader("📋 Krovinių sąrašas")
    df = pd.read_sql_query("SELECT * FROM kroviniai", conn)
    st.dataframe(df)

# ─── VILKIKAI ―──────────────────────────────────────────────────────────
elif modulis == "Vilkikai":
    st.title("DISPO – Vilkikų valdymas")

    with st.form("vilk_form", clear_on_submit=True):
        numeris = st.text_input("Vilkiko numeris", key="vl_num")
        marke_list = [r[0] for r in c.execute(
            "SELECT reiksme FROM lookup WHERE modulis='Vilkikai' AND kategorija='marke'"
        ).fetchall()]
        if marke_list:
            marke = st.selectbox("Markė", [""] + marke_list, key="vl_marke")
        else:
            marke = st.text_input("Markė", key="vl_marke")
        pag_metai = st.number_input(
            "Pagaminimo metai", min_value=1900,
            max_value=date.today().year, key="vl_pag"
        )
        tech_apz = st.date_input("Techninė apžiūra", key="vl_tech")
        vadybininkas = st.text_input("Priskirtas vadybininkas", key="vl_vad")
        vairuotojai = st.text_input("Vairuotojai (kableliais)", key="vl_vair")
        priekaba = st.text_input("Priekaba", key="vl_prk")
        save_v = st.form_submit_button("💾 Išsaugoti vilkiką", key="vl_submit")

    if save_v:
        if not numeris:
            st.warning("⚠️ Įveskite vilkiko numerį.")
        else:
            try:
                c.execute("""
                    INSERT INTO vilkikai (
                        numeris, marke, pagaminimo_metai, tech_apziura,
                        vadybininkas, vairuotojai, priekaba
                    ) VALUES (?,?,?,?,?,?,?)
                """, (
                    numeris, marke, pag_metai, str(tech_apz),
                    vadybininkas, vairuotojai, priekaba
                ))
                conn.commit()
                st.success("✅ Vilkikas įrašytas.")
            except Exception as e:
                st.error(f"❌ Klaida: {e}")

    df_v = pd.read_sql_query("SELECT * FROM vilkikai", conn)
    st.subheader("📋 Vilkikų sąrašas")
    st.dataframe(df_v)

# ─── PRIEKABOS ―─────────────────────────────────────────────────────────
elif modulis == "Priekabos":
    st.title("DISPO – Priekabų valdymas")

    with st.form("prk_form", clear_on_submit=True):
        tip_list = [r[0] for r in c.execute(
            "SELECT reiksme FROM lookup WHERE modulis='Priekabos' AND kategorija='priekabu_tipas'"
        ).fetchall()]
        if tip_list:
            priekabu_tipas = st.selectbox("Priekabos tipas", [""] + tip_list, key="prk_tip")
        else:
            priekabu_tipas = st.text_input("Priekabos tipas", key="prk_tip")
        numeris = st.text_input("Numeris", key="prk_num")
        marke = st.text_input("Markė", key="prk_mark")
        pag_metai = st.number_input(
            "Pagaminimo metai", min_value=1900,
            max_value=date.today().year, key="prk_pag"
        )
        tech_apz = st.date_input("Techninė apžiūra", key="prk_tech")
        prisk_vilk = st.text_input("Priskirtas vilkikas", key="prk_prv")
        save_p = st.form_submit_button("💾 Išsaugoti priekabą", key="prk_submit")

    if save_p:
        if not numeris:
            st.warning("⚠️ Įveskite priekabos numerį.")
        else:
            try:
                c.execute("""
                    INSERT INTO priekabos (
                        priekabu_tipas, numeris, marke, pagaminimo_metai,
                        tech_apziura, priskirtas_vilkikas
                    ) VALUES (?,?,?,?,?,?)
                """, (
                    priekabu_tipas, numeris, marke, pag_metai,
                    str(tech_apz), prisk_vilk
                ))
                conn.commit()
                st.success("✅ Priekaba įrašyta.")
            except Exception as e:
                st.error(f"❌ Klaida: {e}")

    df_p = pd.read_sql_query("SELECT * FROM priekabos", conn)
    st.subheader("📋 Priekabų sąrašas")
    st.dataframe(df_p)

# ─── GRUPĖS ―────────────────────────────────────────────────────────────
elif modulis == "Grupės":
    st.title("DISPO – Grupės valdymas")

    with st.form("grup_form", clear_on_submit=True):
        numeris = st.text_input("Grupės numeris", key="gr_num")
        pavadinimas = st.text_input("Pavadinimas", key="gr_pav")
        aprasymas = st.text_area("Aprašymas", key="gr_apr")
        save_g = st.form_submit_button("💾 Išsaugoti grupę", key="gr_submit")

    if save_g:
        if not numeris or not pavadinimas:
            st.warning("⚠️ Įveskite numerį ir pavadinimą.")
        else:
            try:
                c.execute("""
                    INSERT INTO grupes (numeris,pavadinimas,aprasymas)
                    VALUES (?,?,?)
                """, (numeris, pavadinimas, aprasymas))
                conn.commit()
                st.success("✅ Grupė įrašyta.")
            except Exception as e:
                st.error(f"❌ Klaida: {e}")

    df_g = pd.read_sql_query("SELECT * FROM grupes", conn)
    st.subheader("📋 Grupės sąrašas")
    st.dataframe(df_g)

# ─── VAIRUOTOJAI ―───────────────────────────────────────────────────────
elif modulis == "Vairuotojai":
    st.title("DISPO – Vairuotojų valdymas")

    with st.form("vtd_form", clear_on_submit=True):
        vardas = st.text_input("Vardas", key="vtd_va")
        pavarde = st.text_input("Pavardė", key="vtd_pa")
        gim_metai = st.number_input(
            "Gimimo metai", min_value=1900,
            max_value=date.today().year, key="vtd_gm"
        )
        tautybe = st.text_input("Tautybė", key="vtd_ta")
        vilk_list2 = [r[0] for r in c.execute("SELECT numeris FROM vilkikai").fetchall()]
        prisk_vilk = st.selectbox("Priskirtas vilkikas", [""] + vilk_list2, key="vtd_pr")
        save_vtd = st.form_submit_button("💾 Išsaugoti vairuotoją", key="vtd_submit")

    if save_vtd:
        if not vardas or not pavarde:
            st.warning("⚠️ Įveskite vardą ir pavardę.")
        else:
            try:
                c.execute("""
                    INSERT INTO vairuotojai (
                        vardas,pavarde,gimimo_metai,tautybe,priskirtas_vilkikas
                    ) VALUES (?,?,?,?,?)
                """, (vardas, pavarde, gim_metai, tautybe, prisk_vilk))
                conn.commit()
                st.success("✅ Vairuotojas įrašytas.")
            except Exception as e:
                st.error(f"❌ Klaida: {e}")

    df_vtd = pd.read_sql_query("SELECT * FROM vairuotojai", conn)
    st.subheader("📋 Vairuotojų sąrašas")
    st.dataframe(df_vtd)

# ─── KLIENTAI ―──────────────────────────────────────────────────────────
elif modulis == "Klientai":
    st.title("DISPO – Klientų valdymas")

    with st.form("kl_form", clear_on_submit=True):
        pavadinimas = st.text_input("Įmonės pavadinimas", key="kl_pav")
        vat = st.text_input("PVM (VAT) numeris", key="kl_vat")
        salis = st.text_input("Šalis", key="kl_salis")
        miestas = st.text_input("Miestas", key="kl_miest")
        regionas = st.text_input("Post kodas / regionas", key="kl_reg")
        # Kontaktai
        cont_name = st.text_input("Kontaktas – Vardas Pavardė", key="kl_cn")
        cont_email = st.text_input("Kontaktas – El. paštas", key="kl_ce")
        cont_tel = st.text_input("Kontaktas – Telefonas", key="kl_ct")
        # Sąskaitų kontaktai
        inv_name = st.text_input("Sąskaitų kontaktas – Vardas Pavardė", key="kl_in")
        inv_email = st.text_input("Sąskaitų kontaktas – El. paštas", key="kl_ie")
        inv_tel = st.text_input("Sąskaitų kontaktas – Telefonas", key="kl_it")
        # Limitai
        cof_limit = st.number_input("COFACE limitas", min_value=0.0, key="kl_cof")
        st.write(f"Mūsų limitas: {cof_limit/3:.2f}")
        st.write(f"LIKES limitas: (tuščia kol formulė)")
        # Atsiskaitymas
        as_budas = st.selectbox(
            "Atsiskaitymo būdas",
            ["originalūs dokumentai", "platforma", "skanuoti dokumentai"],
            key="kl_ab"
        )
        as_term = st.text_input("Atsiskaitymo terminas", key="kl_at")
        as_naud = st.text_input("Atsiskaitymo naudingumas", key="kl_an")

        save_kl = st.form_submit_button("💾 Išsaugoti klientą", key="kl_submit")

    if save_kl:
        if not pavadinimas or not miestas or not regionas:
            st.warning("⚠️ Įveskite pavadinimą, miestą ir post kodą.")
        else:
            exists = c.execute("""
                SELECT 1 FROM klientai
                WHERE pavadinimas=? AND miestas=? AND regionas=?
            """, (pavadinimas, miestas, regionas)).fetchone()
            if exists:
                st.error("❌ Toks klientas jau egzistuoja.")
            else:
                c.execute("""
                    INSERT INTO klientai (
                        pavadinimas,kontaktai,salis,miestas,regionas,vat_numeris
                    ) VALUES (?,?,?,?,?,?)
                """, (
                    pavadinimas,
                    f"{cont_name};{cont_email};{cont_tel}",
                    salis, miestas, regionas, vat
                ))
                conn.commit()
                st.success("✅ Klientas įrašytas.")

    df_kl = pd.read_sql_query("SELECT * FROM klientai", conn)
    st.subheader("📋 Klientų sąrašas")
    st.dataframe(df_kl)

# ─── DARBUOTOJAI ―───────────────────────────────────────────────────────
elif modulis == "Darbuotojai":
    st.title("DISPO – Darbuotojų valdymas")

    # Dinaminės pareigybės
    pareigybe_list = [r[0] for r in c.execute(
        "SELECT reiksme FROM lookup WHERE modulis='Darbuotojai' AND kategorija='pareigybe'"
    ).fetchall()]
    # Dinaminės grupės
    group_list = [r[2] for r in c.execute("SELECT id,numeris,pavadinimas FROM grupes").fetchall()]

    with st.form("da_form", clear_on_submit=True):
        vardas = st.text_input("Vardas", key="da_va")
        pavarde = st.text_input("Pavardė", key="da_pa")
        if pareigybe_list:
            pareigybe = st.selectbox("Pareigybė", pareigybe_list, key="da_pr")
        else:
            pareigybe = st.text_input("Pareigybė", key="da_pr")
        if group_list:
            grupe = st.selectbox("Grupė", group_list, key="da_gr")
        else:
            grupe = st.text_input("Grupė", key="da_gr")
        el_pastas = st.text_input("El. paštas", key="da_em")
        telefonas = st.text_input("Telefono numeris", key="da_tel")
        save_da = st.form_submit_button("💾 Išsaugoti darbuotoją", key="da_submit")

    if save_da:
        if not vardas or not pavarde:
            st.warning("⚠️ Įveskite vardą ir pavardę.")
        else:
            try:
                c.execute("""
                    INSERT INTO darbuotojai (
                        vardas,pavarde,pareigybe,el_pastas,telefonas,grupe
                    ) VALUES (?,?,?,?,?,?)
                """, (vardas, pavarde, pareigybe, el_pastas, telefonas, grupe))
                conn.commit()
                st.success("✅ Darbuotojas įrašytas.")
            except Exception as e:
                st.error(f"❌ Klaida: {e}")

    df_da = pd.read_sql_query("SELECT * FROM darbuotojai", conn)
    st.subheader("📋 Darbuotojų sąrašas")
    st.dataframe(df_da)
