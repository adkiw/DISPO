import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, time, timedelta

# ─── Duomenų bazės prisijungimas ───────────────────────────────────────────────
conn = sqlite3.connect('dispo_new.db', check_same_thread=False)
c = conn.cursor()

# ─── Universali lookup lentelė ────────────────────────────────────────────────
c.execute("""
CREATE TABLE IF NOT EXISTS lookup (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kategorija TEXT UNIQUE,
    reiksme TEXT UNIQUE
)
""")
conn.commit()

# ─── Laukų konfigūracija ───────────────────────────────────────────────────────
c.execute("""
CREATE TABLE IF NOT EXISTS field_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    table_name TEXT,
    column_name TEXT,
    lookup_category TEXT
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
    "Kroviniai", "Vilkikai", "Priekabos",
    "Grupės", "Vairuotojai", "Klientai",
    "Darbuotojai", "Nustatymai"
]
modulis = st.sidebar.radio("📂 Pasirink modulį", moduliai)

# ─── NUSTATYMAI: Laukų ir kategorijų priskyrimas ─────────────────────────────
if modulis == "Nustatymai":
    st.title("DISPO – Nustatymai")

    # 1) Valdyk lookup kategorijas
    st.subheader("🔧 Lookup kategorijos")
    existing_cats = [r[0] for r in c.execute("SELECT DISTINCT kategorija FROM lookup").fetchall()]
    col1, col2 = st.columns([2,3])
    chosen_cat = col1.selectbox("Pasirink kategoriją", [""] + existing_cats)
    new_cat = col2.text_input("Arba įvesk naują kategoriją")
    if st.button("➕ Pridėti / Atnaujinti kategoriją"):
        cat_to_add = new_cat.strip() if new_cat.strip() else chosen_cat
        if cat_to_add:
            c.execute("INSERT OR IGNORE INTO lookup(kategorija,reiksme) VALUES(?,?)",
                      (cat_to_add, cat_to_add))
            conn.commit()
            st.success(f"Kategorija '{cat_to_add}' įtraukta į lookup.")
            st.experimental_rerun()
        else:
            st.warning("Pasirink arba įvesk naują kategoriją.")

    st.markdown("---")

    # 2) Priskirk laukams kategorijas
    st.subheader("⚙️ Laukų priskyrimas moduliais")
    lookup_cats = [r[0] for r in c.execute("SELECT DISTINCT kategorija FROM lookup").fetchall()]
    for table in table_ddls.keys():
        with st.expander(f"Modulis: {table}"):
            cols = [info[1] for info in c.execute(f"PRAGMA table_info({table})").fetchall()]
            for col in cols:
                # dabartinė konfigūracija
                cur = c.execute(
                    "SELECT lookup_category FROM field_config WHERE table_name=? AND column_name=?",
                    (table, col)
                ).fetchone()
                cur_cat = cur[0] if cur else ""
                # rodyk select ir po apačia input
                sel = st.selectbox(
                    f"{col}: pasirink kateg.", [""] + lookup_cats,
                    index=(lookup_cats.index(cur_cat)+1) if cur_cat in lookup_cats else 0,
                    key=f"sel_{table}_{col}"
                )
                inp = st.text_input(
                    f"{col}: arba įvesk naują kateg.", key=f"inp_{table}_{col}"
                )
                if st.button(f"💾 Priskirti {table}.{col}", key=f"btn_{table}_{col}"):
                    chosen = inp.strip() if inp.strip() else sel
                    if chosen:
                        # įsitikink, kad lookup turi
                        c.execute("INSERT OR IGNORE INTO lookup(kategorija,reiksme) VALUES(?,?)",
                                  (chosen, chosen))
                        # priskirk laukui
                        if cur:
                            c.execute("""
                                UPDATE field_config
                                SET lookup_category=?
                                WHERE table_name=? AND column_name=?
                            """, (chosen, table, col))
                        else:
                            c.execute("""
                                INSERT INTO field_config(table_name,column_name,lookup_category)
                                VALUES(?,?,?)
                            """, (table, col, chosen))
                        conn.commit()
                        st.success(f"{table}.{col} → '{chosen}'")
                        st.experimental_rerun()
                    else:
                        # jeigu abu tušti, trinam konfigūraciją
                        c.execute("""
                            DELETE FROM field_config
                            WHERE table_name=? AND column_name=?
                        """, (table, col))
                        conn.commit()
                        st.info(f"Išvalyta priskyrimo konfigūracija {table}.{col}")
                        st.experimental_rerun()

# ─── KROVINIAI ────────────────────────────────────────────────────────────────
elif modulis == "Kroviniai":
    st.title("DISPO – Krovinių valdymas")
    with st.form("krovinio_forma", clear_on_submit=False):
        # klientas + užsakymo numeris
        klientai = [r[0] for r in c.execute("SELECT pavadinimas FROM klientai").fetchall()]
        col1, col2 = st.columns(2)
        if klientai:
            klientas = col1.selectbox("Klientas", klientai)
        else:
            klientas = col1.text_input("Klientas (nėra įvestų)")
        uzs_nr = col2.text_input("Užsakymo numeris")

        pakrt_nr = st.text_input("Pakrovimo numeris")

        # datos / laikai
        c1, c2 = st.columns(2)
        pd1 = c1.date_input("Pakrovimo data", date.today())
        ptime_from = c1.time_input("Laikas nuo (pakrov.)", time(8,0))
        ptime_to   = c1.time_input("Laikas iki (pakrov.)", time(17,0))
        idate = c2.date_input("Iškrovimo data", pd1 + timedelta(days=1))
        itime_from = c2.time_input("Laikas nuo (iškrov.)", time(8,0))
        itime_to   = c2.time_input("Laikas iki (iškrov.)", time(17,0))

        # vietos
        v1, v2 = st.columns(2)
        pk_s = v1.text_input("Pakrovimo šalis"); pk_m = v1.text_input("Pakrovimo miestas")
        ik_s = v2.text_input("Iškrovimo šalis"); ik_m = v2.text_input("Iškrovimo miestas")

        # vilkikas + priekaba
        vcol1, vcol2 = st.columns(2)
        vilk_list = [r[0] for r in c.execute("SELECT numeris FROM vilkikai").fetchall()]
        if vilk_list:
            vlk = vcol1.selectbox("Vilkikas", vilk_list)
            pr_val = c.execute("SELECT priekaba FROM vilkikai WHERE numeris=?", (vlk,)).fetchone()
            prk = pr_val[0] if pr_val and pr_val[0] else ""
        else:
            vlk = vcol1.text_input("Vilkikas (tuščias)"); prk = ""
        vcol2.text_input("Priekaba", value=prk, disabled=True)

        # km, frachtas, svoris, padėklai
        k1,k2,k3,k4 = st.columns(4)
        km    = k1.text_input("Kilometrai")
        fr    = k2.text_input("Frachtas (€)")
        sv    = k3.text_input("Svoris (kg)")
        pads  = k4.text_input("Padėklų skaičius")

        # būsena pagal field_config
        cfg = c.execute(
            "SELECT lookup_category FROM field_config WHERE table_name='kroviniai' AND column_name='busena'"
        ).fetchone()
        if cfg:
            opts = [r[0] for r in c.execute("SELECT reiksme FROM lookup WHERE kategorija=?", (cfg[0],)).fetchall()]
            bus = st.selectbox("Būsena", opts)
        else:
            bus = st.selectbox("Būsena", ["suplanuotas","nesuplanuotas","pakrautas","iškrautas"])

        submit = st.form_submit_button("💾 Išsaugoti krovinį")

    if submit:
        if pd1 > idate:
            st.error("❌ Pakrovimo data negali būti vėlesnė už iškrovimo datą.")
        elif not klientas or not uzs_nr:
            st.error("❌ Privalomi: klientas ir užsakymo numeris.")
        else:
            base = uzs_nr
            existing = [r[0] for r in c.execute(
                "SELECT uzsakymo_numeris FROM kroviniai WHERE uzsakymo_numeris LIKE ?", (f"{base}%",)
            ).fetchall()]
            if base in existing:
                suf = sum(1 for x in existing if x.startswith(base))
                uzs_nr = f"{base}-{suf}"
                st.warning(f"Pervardinta į {uzs_nr}.")
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
                klientas, uzs_nr, pakrt_nr,
                str(pd1), str(ptime_from), str(ptime_to),
                str(idate), str(itime_from), str(itime_to),
                pk_s, pk_m, ik_s, ik_m,
                vlk, prk, f"vadyb_{vlk.lower()}",
                int(km or 0), float(fr or 0), int(sv or 0), int(pads or 0), bus
            ))
            conn.commit()
            st.success("✅ Krovinį įrašiau.")

    st.subheader("📋 Visų krovinių sąrašas")
    st.dataframe(pd.read_sql_query("SELECT * FROM kroviniai", conn))

# ─── VILKIKAI, PRIEKABOS, GRUPĖS, VAIRUOTOJAI, KLIENTAI, DARBUOTOJAI ─────────
# (analoginė struktūra: formos, validation, INSERT, dataframe)

elif modulis == "Vilkikai":
    # ... (kaip anksčiau, tik taikant field_config selectų logiką markei)
    pass

elif modulis == "Priekabos":
    pass

elif modulis == "Grupės":
    pass

elif modulis == "Vairuotojai":
    pass

elif modulis == "Klientai":
    pass

elif modulis == "Darbuotojai":
    pass
