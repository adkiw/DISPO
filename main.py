import streamlit as st
import sqlite3
import pandas as pd
import json
from datetime import date, time, timedelta

# ─── Database setup ────────────────────────────────────────────────────────────
conn = sqlite3.connect('dispo_new.db', check_same_thread=False)
c = conn.cursor()

# Lookup table with module scoping
c.execute("""
CREATE TABLE IF NOT EXISTS lookup (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    module TEXT,
    kategorija TEXT,
    reiksme TEXT UNIQUE
)
""")

# Full schema updates
c.execute("""
CREATE TABLE IF NOT EXISTS klientai (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pavadinimas TEXT,
    pasto_kodas TEXT,
    miestas TEXT,
    regionas TEXT,
    salis TEXT,
    vat_numeris TEXT,
    contact1_name TEXT,
    contact1_surname TEXT,
    contact1_email TEXT,
    contact1_phone TEXT,
    contact2_name TEXT,
    contact2_surname TEXT,
    contact2_email TEXT,
    contact2_phone TEXT,
    coface_limit REAL,
    musu_limit REAL,
    likes_limit REAL,
    payment_method TEXT,
    payment_term INTEGER,
    payment_utility REAL,
    UNIQUE(pavadinimas, miestas, pasto_kodas)
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS kroviniai (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id TEXT,
    klientas TEXT,
    uzsakymo_numeris TEXT,
    pakrovimai TEXT,       -- JSON array of {data, nuo, iki, adresas}
    iskrovimai TEXT,       -- JSON array of {data, nuo, iki, adresas}
    vilkikas TEXT,
    priekaba TEXT,
    busena TEXT
)
""")

# Other tables left unchanged...
# (vilkikai, priekabos, grupes, vairuotojai, darbuotojai)
# ────────────────────────────────────────────────────────────────────────────────

conn.commit()

# ─── Sidebar module selector ────────────────────────────────────────────────────
modules = [
    "Kroviniai", "Vilkikai", "Priekabos",
    "Grupės", "Vairuotojai", "Klientai",
    "Darbuotojai", "Nustatymai"
]
modulis = st.sidebar.radio("📂 Pasirink modulį", modules)

# Initialize dynamic counts for load/unload
if 'n_pak' not in st.session_state:
    st.session_state.n_pak = 1
if 'n_isk' not in st.session_state:
    st.session_state.n_isk = 1

def add_pak():
    st.session_state.n_pak += 1

def add_isk():
    st.session_state.n_isk += 1

# ─── SETTINGS ─────────────────────────────────────────────────────────────────
if modulis == "Nustatymai":
    st.title("DISPO – Nustatymai")
    # Choose module (exclude Nustatymai)
    sel_module = st.selectbox("Modulis", [m for m in modules if m != "Nustatymai"])
    # Load categories for that module
    cats = [r[0] for r in c.execute(
        "SELECT DISTINCT kategorija FROM lookup WHERE module = ?", (sel_module,)
    ).fetchall()]
    col1, col2 = st.columns(2)
    existing = col1.selectbox("Esama kategorija", [""] + cats)
    new_cat = col2.text_input("Arba nauja kategorija")
    kategori = new_cat.strip() if new_cat else existing

    if kategori:
        st.markdown("---")
        st.subheader(f"{sel_module} – kategorija **{kategori}**")
        vals = [r[0] for r in c.execute(
            "SELECT reiksme FROM lookup WHERE module = ? AND kategorija = ?",
            (sel_module, kategori)
        ).fetchall()]
        st.write(vals or "_(nerasta reikšmių)_")
        v_new = st.text_input("Pridėti naują reikšmę")
        if st.button("➕ Pridėti reikšmę"):
            if v_new:
                try:
                    c.execute(
                        "INSERT INTO lookup(module,kategorija,reiksme) VALUES(?,?,?)",
                        (sel_module, kategori, v_new)
                    )
                    conn.commit()
                    st.success(f"✅ Pridėta: {v_new}")
                except sqlite3.IntegrityError:
                    st.warning("⚠️ Toks elementas jau egzistuoja.")
        to_del = st.selectbox("Ištrinti reikšmę", [""] + vals)
        if st.button("🗑 Ištrinti reikšmę"):
            if to_del:
                c.execute(
                    "DELETE FROM lookup WHERE module = ? AND kategorija = ? AND reiksme = ?",
                    (sel_module, kategori, to_del)
                )
                conn.commit()
                st.success(f"✅ Ištrinta: {to_del}")
    else:
        st.info("Pasirinkite modulį ir kategoriją")

# ─── CARGOS ────────────────────────────────────────────────────────────────────
elif modulis == "Kroviniai":
    st.title("DISPO – Krovinių valdymas")

    with st.form("krovinio_forma", clear_on_submit=False):
        # 1) Klientas dropdown with template
        kli = c.execute("SELECT pavadinimas, pasto_kodas, miestas FROM klientai").fetchall()
        opts = [f"{p[0]} {p[1]} {p[2]}" for p in kli]
        if opts:
            klientas = st.selectbox("Klientas", opts)
        else:
            klientas = st.text_input("Klientas (nėra įvestų)")

        uzs_nr = st.text_input("Užsakymo numeris")

        # Dynamic loading/unloading
        st.button("➕ Pridėti pakrovimą", on_click=add_pak)
        pakrovimai = []
        for i in range(st.session_state.n_pak):
            st.markdown(f"**Pakrovimas #{i+1}**")
            d = st.date_input(f"Data {i+1}", key=f"p_data_{i}", value=date.today())
            nuo = st.time_input(f"Nuo {i+1}", key=f"p_nuo_{i}", value=time(8,0))
            iki = st.time_input(f"Iki {i+1}", key=f"p_iki_{i}", value=time(17,0))
            adres = st.text_input(f"Adresas {i+1}", key=f"p_addr_{i}")
            pakrovimai.append({
                "data": str(d), "nuo": str(nuo),
                "iki": str(iki), "adresas": adres
            })

        st.button("➕ Pridėti iškrovimą", on_click=add_isk)
        iskrovimai = []
        for i in range(st.session_state.n_isk):
            st.markdown(f"**Iškrovimas #{i+1}**")
            d2 = st.date_input(f"Data {i+1}", key=f"i_data_{i}", value=date.today())
            nuo2 = st.time_input(f"Nuo {i+1}", key=f"i_nuo_{i}", value=time(8,0))
            iki2 = st.time_input(f"Iki {i+1}", key=f"i_iki_{i}", value=time(17,0))
            addr2 = st.text_input(f"Adresas {i+1}", key=f"i_addr_{i}")
            iskrovimai.append({
                "data": str(d2), "nuo": str(nuo2),
                "iki": str(iki2), "adresas": addr2
            })

        # Truck & trailer
        trucks = [r[0] for r in c.execute("SELECT numeris FROM vilkikai").fetchall()]
        if trucks:
            vilkikas = st.selectbox("Vilkikas", trucks)
            priek = c.execute(
                "SELECT priekaba FROM vilkikai WHERE numeris = ?", (vilkikas,)
            ).fetchone()[0] or ""
        else:
            vilkikas = st.text_input("Vilkikas")
            priek = ""
        st.text_input("Priekaba", value=priek, disabled=True)

        # Status from lookup or default
        bus_opts = [r[0] for r in c.execute(
            "SELECT reiksme FROM lookup WHERE module = 'Kroviniai' AND kategorija = 'busena'"
        ).fetchall()]
        busena = st.selectbox("Būsena",
                              bus_opts if bus_opts else ["suplanuotas","nesuplanuotas","pakrautas","iškrautas"])

        submit = st.form_submit_button("💾 Įrašyti krovinį")

    if submit:
        # Basic validation
        if not klientas or not uzs_nr:
            st.error("❌ Privalomi laukai: Klientas ir Užsakymo numeris.")
        else:
            # Insert placeholder to get new PK
            c.execute("""
                INSERT INTO kroviniai (
                    business_id, klientas, uzsakymo_numeris,
                    pakrovimai, iskrovimai, vilkikas, priekaba, busena
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "", klientas, uzs_nr,
                json.dumps(pakrovimai),
                json.dumps(iskrovimai),
                vilkikas, priek, busena
            ))
            conn.commit()
            new_id = c.lastrowid

            # Determine base PK for this order
            base = uzs_nr
            base_id = c.execute(
                "SELECT id FROM kroviniai WHERE uzsakymo_numeris = ? ORDER BY id ASC LIMIT 1",
                (base,)
            ).fetchone()[0]

            if base_id == new_id:
                bid = str(base_id)
            else:
                cnt = c.execute(
                    "SELECT COUNT(*) FROM kroviniai WHERE uzsakymo_numeris = ? AND id < ?",
                    (base, new_id)
                ).fetchone()[0]
                bid = f"{base_id}-{cnt}"

            # Update business_id
            c.execute("UPDATE kroviniai SET business_id = ? WHERE id = ?", (bid, new_id))
            conn.commit()
            st.success(f"✅ Krovinį išsaugojau su business_id `{bid}`.")

    # Summary table
    df = pd.read_sql_query("SELECT * FROM kroviniai ORDER BY id DESC", conn)
    summary = []
    for _, row in df.iterrows():
        p = json.loads(row["pakrovimai"] or "[]")
        i = json.loads(row["iskrovimai"] or "[]")
        first_p = p[0] if p else {}
        last_i = i[-1] if i else {}
        ps = f"{first_p.get('data','')} {first_p.get('nuo','')}-{first_p.get('iki','')} {first_p.get('adresas','')}"
        is_ = f"{last_i.get('data','')} {last_i.get('nuo','')}-{last_i.get('iki','')} {last_i.get('adresas','')}"
        summary.append({
            "business_id": row["business_id"],
            "Klientas": row["klientas"],
            "Užsakymo nr.": row["uzsakymo_numeris"],
            "Pakrovimas": ps,
            "Iškrovimas": is_,
            "Vilkikas": row["vilkikas"],
            "Priekaba": row["priekaba"],
            "Būsena": row["busena"]
        })
    st.subheader("📋 Krovinių sąrašas")
    st.dataframe(pd.DataFrame(summary))

# ─── CLIENTS ──────────────────────────────────────────────────────────────────
elif modulis == "Klientai":
    st.title("DISPO – Klientai")

    with st.form("kl_form", clear_on_submit=True):
        iv = st.text_input("Įmonės pavadinimas")
        pk = st.text_input("Pašto kodas")
        ms = st.text_input("Miestas")
        rg = st.text_input("Regionas")
        sl = st.text_input("Šalis")
        vat = st.text_input("PVM numeris")

        st.markdown("**Pagrindinis kontaktas**")
        c1n = st.text_input("Vardas (kontaktas #1)")
        c1s = st.text_input("Pavardė")
        c1e = st.text_input("El. paštas")
        c1p = st.text_input("Telefonas")

        st.markdown("**Kontaktas dėl sąskaitų**")
        c2n = st.text_input("Vardas (kontaktas #2)")
        c2s = st.text_input("Pavardė")
        c2e = st.text_input("El. paštas")
        c2p = st.text_input("Telefonas")

        coface = st.number_input("COFACE limitas", min_value=0.0, step=1.0)
        musu = coface / 3
        st.text_input("Mūsų limitas", value=f"{musu:.2f}", disabled=True)
        likes = st.number_input("Likes limitas", min_value=0.0, step=1.0)

        pay_methods = ["originalūs dokumentai","platforma","skanuoti dokumentai"]
        pay_m = st.selectbox("Atsiskaitymo būdas", pay_methods)
        term = st.number_input("Atsiskaitymo terminas (dienomis)", min_value=0, step=1)
        util = st.number_input("Atsiskaitymo naudingumas", min_value=0.0, step=0.1)

        sb = st.form_submit_button("💾 Išsaugoti klientą")

    if sb:
        if not iv or not pk or not ms:
            st.error("❌ Pavadinimas, pašto kodas ir miestas privalomi.")
        else:
            # Uniqueness check
            exists = c.execute(
                "SELECT COUNT(*) FROM klientai WHERE pavadinimas = ? AND miestas = ? AND pasto_kodas = ?",
                (iv, ms, pk)
            ).fetchone()[0]
            if exists:
                st.error("❌ Toks klientas jau egzistuoja.")
            else:
                c.execute("""
                    INSERT INTO klientai (
                        pavadinimas, pasto_kodas, miestas, regionas, salis, vat_numeris,
                        contact1_name, contact1_surname, contact1_email, contact1_phone,
                        contact2_name, contact2_surname, contact2_email, contact2_phone,
                        coface_limit, musu_limit, likes_limit,
                        payment_method, payment_term, payment_utility
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    iv, pk, ms, rg, sl, vat,
                    c1n, c1s, c1e, c1p,
                    c2n, c2s, c2e, c2p,
                    coface, musu, likes,
                    pay_m, term, util
                ))
                conn.commit()
                st.success("✅ Klientas įrašytas.")

    st.subheader("📋 Klientų sąrašas")
    st.dataframe(pd.read_sql_query("SELECT * FROM klientai ORDER BY id DESC", conn))

# ─── Other modules (Vilkikai, Priekabos, Grupės, Vairuotojai, Darbuotojai) ─────
# (You can keep your existing implementations, they remain compatible.)

