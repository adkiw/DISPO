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
    kategorija TEXT,
    reiksme TEXT,
    UNIQUE(kategorija, reiksme)
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

# ─── Pagrindinės lentelės ─────────────────────────────────────────────────────
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

# ─── Dinaminis laukas: selectbox jei turi reiksmių, kitaip text_input ────────
def dynamic_field(table, column, label, default=""):
    cfg = c.execute(
        "SELECT lookup_category FROM field_config WHERE table_name=? AND column_name=?",
        (table, column)
    ).fetchone()
    if cfg and cfg[0]:
        opts = [r[0] for r in c.execute(
            "SELECT reiksme FROM lookup WHERE kategorija=?", (cfg[0],)
        ).fetchall()]
        if opts:
            return st.selectbox(label, opts, index=opts.index(default) if default in opts else 0)
    # fallback
    return st.text_input(label, value=default)

# ─── Šoninis meniu ────────────────────────────────────────────────────────────
moduliai = [
    "Kroviniai", "Vilkikai", "Priekabos",
    "Grupės", "Vairuotojai", "Klientai",
    "Darbuotojai", "Nustatymai"
]
modulis = st.sidebar.radio("📂 Pasirink modulį", moduliai)

# ─── NUSTATYMAI: lookup + field_config (tik tekstiniai įrašai) ────────────────
if modulis == "Nustatymai":
    st.title("DISPO – Nustatymai")

    # 1) lookup pridėjimas
    st.subheader("🔧 Lookup kategorijų ir reikšmių valdymas")
    esamos = [r[0] for r in c.execute("SELECT DISTINCT kategorija FROM lookup").fetchall()]
    col1, col2 = st.columns([2,3])
    sel = col1.selectbox("Esama kategorija", [""] + esamos)
    new = col2.text_input("Įvesk reikšmę → kuriama/mokomasi kategorija")
    if st.button("➕ Pridėti į lookup"):
        kat = sel or new.strip()
        val = new.strip() or sel
        if kat and val:
            c.execute("INSERT OR IGNORE INTO lookup(kategorija,reiksme) VALUES(?,?)", (kat, val))
            conn.commit()
            st.success(f"✅ lookup: {kat} → {val}")
            st.experimental_rerun()
        else:
            st.warning("Pasirink arba įvesk reikšmę.")

    st.markdown("---")

    # 2) laukų konfigūracija (field_config) – tik text_input
    st.subheader("⚙️ Laukų priskyrimas moduliais")
    for table in table_ddls.keys():
        with st.expander(f"Modulis: {table}"):
            cols = [info[1] for info in c.execute(f"PRAGMA table_info({table})").fetchall()]
            for col in cols:
                cur = c.execute(
                    "SELECT lookup_category FROM field_config WHERE table_name=? AND column_name=?",
                    (table, col)
                ).fetchone()
                cur_cat = cur[0] if cur else ""
                txt = st.text_input(f"{col}: įvesk lookup kategoriją", value=cur_cat, key=f"cfg_{table}_{col}")
                if st.button(f"Išsaugoti {table}.{col}", key=f"btn_{table}_{col}"):
                    if txt.strip():
                        if cur:
                            c.execute("""
                                UPDATE field_config
                                SET lookup_category=?
                                WHERE table_name=? AND column_name=?
                            """, (txt.strip(), table, col))
                        else:
                            c.execute("""
                                INSERT INTO field_config(table_name,column_name,lookup_category)
                                VALUES(?,?,?)
                            """, (table, col, txt.strip()))
                        conn.commit()
                        st.success(f"✅ {table}.{col} → '{txt.strip()}'")
                    else:
                        c.execute("""
                            DELETE FROM field_config
                            WHERE table_name=? AND column_name=?
                        """, (table, col))
                        conn.commit()
                        st.info(f"ℹ️ Ištrinta konfiguracija {table}.{col}")

# ─── KROVINIAI ────────────────────────────────────────────────────────────────
elif modulis == "Kroviniai":
    st.title("DISPO – Krovinių valdymas")
    with st.form("frm_kroviniai", clear_on_submit=False):
        klientas = dynamic_field("kroviniai","klientas","Klientas")
        uznr     = dynamic_field("kroviniai","uzsakymo_numeris","Užsakymo numeris")
        paknr    = dynamic_field("kroviniai","pakrovimo_numeris","Pakrovimo numeris")
        c1,c2    = st.columns(2)
        pd1      = c1.date_input("Pakrovimo data", date.today())
        pfrom    = c1.time_input("Laikas nuo (pakrov.)", time(8,0))
        pto      = c1.time_input("Laikas iki (pakrov.)", time(17,0))
        id1      = c2.date_input("Iškrovimo data", pd1+timedelta(days=1))
        ifrom    = c2.time_input("Laikas nuo (iškrov.)", time(8,0))
        ito      = c2.time_input("Laikas iki (iškrov.)", time(17,0))
        ps       = dynamic_field("kroviniai","pakrovimo_salis","Pakrovimo šalis")
        pm       = dynamic_field("kroviniai","pakrovimo_miestas","Pakrovimo miestas")
        is       = dynamic_field("kroviniai","iskrovimo_salis","Iškrovimo šalis")
        im       = dynamic_field("kroviniai","iskrovimo_miestas","Iškrovimo miestas")
        vlk      = dynamic_field("kroviniai","vilkikas","Vilkikas")
        prk      = dynamic_field("kroviniai","priekaba","Priekaba")
        km       = dynamic_field("kroviniai","kilometrai","Kilometrai")
        fr       = dynamic_field("kroviniai","frachtas","Frachtas (€)")
        sv       = dynamic_field("kroviniai","svoris","Svoris (kg)")
        pads     = dynamic_field("kroviniai","paleciu_skaicius","Padėklų skaičius")
        bus      = dynamic_field("kroviniai","busena","Būsena","suplanuotas")
        sub      = st.form_submit_button("💾 Išsaugoti")
    if sub:
        if pd1 > id1:
            st.error("❌ Pakrovimo data vėlesnė už iškrovimo.")
        elif not klientas or not uznr:
            st.error("❌ Privalomi laukai: klientas ir Nr.")
        else:
            base = uznr
            ex = [r[0] for r in c.execute(
                "SELECT uzsakymo_numeris FROM kroviniai WHERE uzsakymo_numeris LIKE ?", (f"{base}%",)
            ).fetchall()]
            if base in ex:
                suf = sum(1 for x in ex if x.startswith(base))
                uznr = f"{base}-{suf}"
                st.warning(f"Pervadinta: {uznr}")
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
                klientas, uznr, paknr,
                str(pd1), str(pfrom), str(pto),
                str(id1), str(ifrom), str(ito),
                ps, pm, is, im,
                vlk, prk, f"vadyb_{vlk.lower()}",
                int(km or 0), float(fr or 0), int(sv or 0), int(pads or 0), bus
            ))
            conn.commit()
            st.success("✅ Išsaugojau krovinį.")
    st.subheader("Visi kroviniai")
    st.dataframe(pd.read_sql("SELECT * FROM kroviniai", conn))

# ─── KITI MODULIAI (tą pačią dynamic_field logiką pritaikyk atitinkamai) ──────
elif modulis == "Vilkikai":
    st.title("DISPO – Vilkikų valdymas")
    with st.form("frm_vilkikai", clear_on_submit=True):
        nr = dynamic_field("vilkikai","numeris","Numeris")
        mk = dynamic_field("vilkikai","marke","Markė")
        pm = dynamic_field("vilkikai","pagaminimo_metai","Pagaminimo metai")
        ta = st.date_input("Tech. apžiūra")
        vd = dynamic_field("vilkikai","vadybininkas","Vadybininkas")
        vr = dynamic_field("vilkikai","vairuotojai","Vairuotojai")
        pk = dynamic_field("vilkikai","priekaba","Priekaba")
        sb = st.form_submit_button("💾 Išsaugoti")
    if sb:
        if not nr:
            st.warning("Numeris būtinas.")
        else:
            c.execute("""
                INSERT OR REPLACE INTO vilkikai
                (numeris,marke,pagaminimo_metai,tech_apziura,vadybininkas,vairuotojai,priekaba)
                VALUES (?,?,?,?,?,?,?)
            """, (nr, mk, int(pm or 0), str(ta), vd, vr, pk))
            conn.commit(); st.success("✅ Išsaugojau.")
    st.dataframe(pd.read_sql("SELECT * FROM vilkikai", conn))

elif modulis == "Priekabos":
    st.title("DISPO – Priekabų valdymas")
    with st.form("frm_priekabos", clear_on_submit=True):
        tp = dynamic_field("priekabos","priekabu_tipas","Tipas")
        nr = dynamic_field("priekabos","numeris","Numeris")
        mk = dynamic_field("priekabos","marke","Markė")
        pm = dynamic_field("priekabos","pagaminimo_metai","Pagaminimo metai")
        ta = st.date_input("Tech. apžiūra")
        pv = dynamic_field("priekabos","priskirtas_vilkikas","Priskirtas vilkikas")
        sb = st.form_submit_button("💾 Išsaugoti")
    if sb:
        if not nr:
            st.warning("Numeris būtinas.")
        else:
            c.execute("""
                INSERT OR REPLACE INTO priekabos
                (priekabu_tipas,numeris,marke,pagaminimo_metai,tech_apziura,priskirtas_vilkikas)
                VALUES (?,?,?,?,?,?)
            """, (tp,nr,mk,int(pm or 0), str(ta), pv))
            conn.commit(); st.success("✅ Išsaugojau.")
    st.dataframe(pd.read_sql("SELECT * FROM priekabos", conn))

elif modulis == "Grupės":
    st.title("DISPO – Grupės")
    with st.form("frm_grupes", clear_on_submit=True):
        nr = dynamic_field("grupes","numeris","Numeris")
        pv = dynamic_field("grupes","pavadinimas","Pavadinimas")
        ap = st.text_area("Aprašymas")
        sb = st.form_submit_button("💾 Išsaugoti")
    if sb:
        if not nr or not pv:
            st.warning("Numeris ir pavadinimas būtini.")
        else:
            c.execute("""
                INSERT OR REPLACE INTO grupes(numeris,pavadinimas,aprasymas)
                VALUES (?,?,?)
            """, (nr,pv,ap))
            conn.commit(); st.success("✅ Išsaugojau.")
    st.dataframe(pd.read_sql("SELECT * FROM grupes", conn))

elif modulis == "Vairuotojai":
    st.title("DISPO – Vairuotojai")
    with st.form("frm_vairuotojai", clear_on_submit=True):
        vd = dynamic_field("vairuotojai","vardas","Vardas")
        pv = dynamic_field("vairuotojai","pavarde","Pavardė")
        gm = dynamic_field("vairuotojai","gimimo_metai","Gimimo metai")
        tt = dynamic_field("vairuotojai","tautybe","Tautybė")
        pvk= dynamic_field("vairuotojai","priskirtas_vilkikas","Priskirtas vilkikas")
        sb = st.form_submit_button("💾 Išsaugoti")
    if sb:
        if not vd or not pv:
            st.warning("Vardas ir pavardė būtini.")
        else:
            c.execute("""
                INSERT OR REPLACE INTO vairuotojai
                (vardas,pavarde,gimimo_metai,tautybe,priskirtas_vilkikas)
                VALUES (?,?,?,?,?)
            """, (vd,pv,int(gm or 0), tt, pvk))
            conn.commit(); st.success("✅ Išsaugojau.")
    st.dataframe(pd.read_sql("SELECT * FROM vairuotojai", conn))

elif modulis == "Klientai":
    st.title("DISPO – Klientai")
    with st.form("frm_klientai", clear_on_submit=True):
        nm = dynamic_field("klientai","pavadinimas","Pavadinimas")
        kt = dynamic_field("klientai","kontaktai","Kontaktai")
        sl = dynamic_field("klientai","salis","Šalis")
        ms = dynamic_field("klientai","miestas","Miestas")
        rg = dynamic_field("klientai","regionas","Regionas")
        vat= dynamic_field("klientai","vat_numeris","PVM numeris")
        sb = st.form_submit_button("💾 Išsaugojau")
    if sb:
        if not nm:
            st.warning("Pavadinimas būtinas.")
        else:
            c.execute("""
                INSERT OR REPLACE INTO klientai
                (pavadinimas,kontaktai,salis,miestas,regionas,vat_numeris)
                VALUES (?,?,?,?,?,?)
            """, (nm,kt,sl,ms,rg,vat))
            conn.commit(); st.success("✅ Išsaugojau.")
    st.dataframe(pd.read_sql("SELECT * FROM klientai", conn))

elif modulis == "Darbuotojai":
    st.title("DISPO – Darbuotojai")
    with st.form("frm_darbuotojai", clear_on_submit=True):
        vd = dynamic_field("darbuotojai","vardas","Vardas")
        pv = dynamic_field("darbuotojai","pavarde","Pavardė")
        pg = dynamic_field("darbuotojai","pareigybe","Pareigybė")
        em = dynamic_field("darbuotojai","el_pastas","El. paštas")
        ph = dynamic_field("darbuotojai","telefonas","Telefonas")
        gr = dynamic_field("darbuotojai","grupe","Grupė")
        sb = st.form_submit_button("💾 Išsaugojau")
    if sb:
        if not vd or not pv:
            st.warning("Vardas ir pavardė būtini.")
        else:
            c.execute("""
                INSERT OR REPLACE INTO darbuotojai
                (vardas,pavarde,pareigybe,el_pastas,telefonas,grupe)
                VALUES (?,?,?,?,?,?)
            """, (vd,pv,pg,em,ph,gr))
            conn.commit(); st.success("✅ Išsaugojau.")
    st.dataframe(pd.read_sql("SELECT * FROM darbuotojai", conn))
