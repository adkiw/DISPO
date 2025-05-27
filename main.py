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
    # ... (kitos lentelės taip pat)
}
for ddl in table_ddls.values():
    c.execute(ddl)
conn.commit()

# ─── Dinaminis laukas: selectbox jei turi reikšmių, kitaip text_input ────────
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
    return st.text_input(label, value=default)

# ─── Šoninis meniu ────────────────────────────────────────────────────────────
moduliai = [
    "Kroviniai", "Vilkikai", "Priekabos",
    "Grupės", "Vairuotojai", "Klientai",
    "Darbuotojai", "Nustatymai"
]
modulis = st.sidebar.radio("📂 Pasirink modulį", moduliai)

# ─── NUSTATYMAI ───────────────────────────────────────────────────────────────
if modulis == "Nustatymai":
    st.title("DISPO – Nustatymai")

    # 1) lookup pridėjimas
    st.subheader("🔧 Lookup kategorijų ir reikšmių valdymas")
    esamos = [r[0] for r in c.execute("SELECT DISTINCT kategorija FROM lookup").fetchall()]
    col1, col2 = st.columns([2,3])
    sel = col1.selectbox("Esama kategorija", [""] + esamos)
    new = col2.text_input("Įvesk reikšmę (sukurti kategoriją/reikšmę)")
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

    # 2) laukų konfigūracija (tik text_input)
    st.subheader("⚙️ Laukų priskyrimas moduliais")
    for table in table_ddls.keys():
        with st.expander(f"Modulis: {table}"):
            cols = [info[1] for info in c.execute(f"PRAGMA table_info({table})").fetchall()]
            for col in cols:
                cur = c.execute(
                    "SELECT lookup_category FROM field_config WHERE table_name=? AND column_name=?",
                    (table, col)
                ).fetchone()
                current = cur[0] if cur else ""
                txt = st.text_input(f"{col}: įvesk kategoriją", value=current, key=f"cfg_{table}_{col}")
                if st.button(f"Išsaugoti {table}.{col}", key=f"btn_{table}_{col}"):
                    if txt.strip():
                        if cur:
                            c.execute(
                                "UPDATE field_config SET lookup_category=? WHERE table_name=? AND column_name=?",
                                (txt.strip(), table, col)
                            )
                        else:
                            c.execute(
                                "INSERT INTO field_config(table_name,column_name,lookup_category) VALUES(?,?,?)",
                                (table, col, txt.strip())
                            )
                        conn.commit()
                        st.success(f"✅ {table}.{col} → '{txt.strip()}'")
                    else:
                        c.execute(
                            "DELETE FROM field_config WHERE table_name=? AND column_name=?",
                            (table, col)
                        )
                        conn.commit()
                        st.info(f"ℹ️ Ištrinta konfigūracija {table}.{col}")

# ─── KROVINIAI ────────────────────────────────────────────────────────────────
elif modulis == "Kroviniai":
    st.title("DISPO – Krovinių valdymas")
    with st.form("frm_kroviniai", clear_on_submit=False):
        klientas = dynamic_field("kroviniai","klientas","Klientas")
        uznr     = dynamic_field("kroviniai","uzsakymo_numeris","Užsakymo numeris")
        paknr    = dynamic_field("kroviniai","pakrovimo_numeris","Pakrovimo numeris")

        c1, c2  = st.columns(2)
        pd1     = c1.date_input("Pakrovimo data", date.today())
        pfrom   = c1.time_input("Laikas nuo (pakrov.)", time(8,0))
        pto     = c1.time_input("Laikas iki (pakrov.)", time(17,0))

        id1     = c2.date_input("Iškrovimo data", pd1 + timedelta(days=1))
        ifrom   = c2.time_input("Laikas nuo (iškrov.)", time(8,0))
        ito     = c2.time_input("Laikas iki (iškrov.)", time(17,0))

        pak_s   = dynamic_field("kroviniai","pakrovimo_salis","Pakrovimo šalis")
        pak_m   = dynamic_field("kroviniai","pakrovimo_miestas","Pakrovimo miestas")

        isk_s   = dynamic_field("kroviniai","iskrovimo_salis","Iškrovimo šalis")
        isk_m   = dynamic_field("kroviniai","iskrovimo_miestas","Iškrovimo miestas")

        vlk     = dynamic_field("kroviniai","vilkikas","Vilkikas")
        prk     = dynamic_field("kroviniai","priekaba","Priekaba")

        km      = dynamic_field("kroviniai","kilometrai","Kilometrai")
        fr      = dynamic_field("kroviniai","frachtas","Frachtas (€)")
        sv      = dynamic_field("kroviniai","svoris","Svoris (kg)")
        pads    = dynamic_field("kroviniai","paleciu_skaicius","Padėklų skaičius")

        bus     = dynamic_field("kroviniai","busena","Būsena","suplanuotas")
        submit  = st.form_submit_button("💾 Išsaugoti")

    if submit:
        if pd1 > id1:
            st.error("❌ Pakrovimo data vėlesnė už iškrovimo.")
        elif not klientas or not uznr:
            st.error("❌ Privalomi laukai: klientas ir Nr.")
        else:
            base = uznr
            existing = [r[0] for r in c.execute(
                "SELECT uzsakymo_numeris FROM kroviniai WHERE uzsakymo_numeris LIKE ?", (f"{base}%",)
            ).fetchall()]
            if base in existing:
                suf = sum(1 for x in existing if x.startswith(base))
                uznr = f"{base}-{suf}"
                st.warning(f"Pervadinta į {uznr}")
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
                pak_s, pak_m, isk_s, isk_m,
                vlk, prk, f"vadyb_{vlk.lower()}",
                int(km or 0), float(fr or 0), int(sv or 0), int(pads or 0), bus
            ))
            conn.commit()
            st.success("✅ Krovinį išsaugojau.")

    st.subheader("Visi kroviniai")
    st.dataframe(pd.read_sql("SELECT * FROM kroviniai", conn))

# ─── Tolimesni moduliai (analoginė dynamic_field() logika) ────────────────────
elif modulis == "Vilkikai":
    # ... analogiškai pritaikyk dynamic_field moduliui Vilkikai
    pass

elif modulis == "Priekabos":
    pass

# ir t.t.
