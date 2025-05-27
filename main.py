import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, time, timedelta

# ─── DATABASE CONNECTION ──────────────────────────────────────────────────────
conn = sqlite3.connect('dispo_new.db', check_same_thread=False)
c = conn.cursor()

# ─── LOOKUP TABLE ─────────────────────────────────────────────────────────────
c.execute("""
CREATE TABLE IF NOT EXISTS lookup (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kategorija TEXT,
    reiksme TEXT UNIQUE
)
""")
conn.commit()

# ─── CORE TABLES ──────────────────────────────────────────────────────────────
# Kroviniai
c.execute("""
CREATE TABLE IF NOT EXISTS kroviniai (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    klientas_id INTEGER,
    uzsakymo_numeris TEXT UNIQUE,
    pakrovimo_numeris TEXT,
    iskrovimo_numeris TEXT,
    vilkikas TEXT,
    priekaba TEXT,
    atsakingas_vadybininkas TEXT,
    kilometrai INTEGER,
    frachtas REAL,
    svoris INTEGER,
    paleciu_skaicius INTEGER,
    busena TEXT,
    FOREIGN KEY(klientas_id) REFERENCES klientai(id)
)
""")

# Pakrovimai & Iškrovimai (new, many-to-one)
c.execute("""
CREATE TABLE IF NOT EXISTS pakrovimai (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    krovinys_id INTEGER,
    data TEXT, laikas_nuo TEXT, laikas_iki TEXT,
    salis TEXT, miestas TEXT, adresas TEXT,
    FOREIGN KEY(krovinys_id) REFERENCES kroviniai(id)
)
""")
c.execute("""
CREATE TABLE IF NOT EXISTS iskrovimai (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    krovinys_id INTEGER,
    data TEXT, laikas_nuo TEXT, laikas_iki TEXT,
    salis TEXT, miestas TEXT, adresas TEXT,
    FOREIGN KEY(krovinys_id) REFERENCES kroviniai(id)
)
""")

# Vilkikai
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

# Priekabos
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

# Grupės
c.execute("""
CREATE TABLE IF NOT EXISTS grupes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numeris TEXT UNIQUE,
    pavadinimas TEXT,
    aprasymas TEXT
)
""")

# Vairuotojai
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

# Darbuotojai
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

# Klientai (extended)
c.execute("""
CREATE TABLE IF NOT EXISTS klientai (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pavadinimas TEXT,
    post_kodas TEXT,
    salis TEXT,
    miestas TEXT,
    regionas TEXT,
    vat_numeris TEXT,
    kontaktas_vardas TEXT,
    kontaktas_pavarde TEXT,
    kontaktas_el TEXT,
    kontaktas_tel TEXT,
    inv_kont_vardas TEXT,
    inv_kont_pavarde TEXT,
    inv_kont_el TEXT,
    inv_kont_tel TEXT,
    coface_limitas REAL,
    our_limitas REAL,
    likes_limitas REAL,
    apm_metodai TEXT,
    apm_terminas TEXT,
    apm_naudingumas TEXT
)
""")
conn.commit()

# ─── MODULE NAVIGATION ────────────────────────────────────────────────────────
st.sidebar.title("DISPO")
moduliai = [
    "Kroviniai", "Vilkikai", "Priekabos",
    "Grupės", "Vairuotojai", "Klientai",
    "Darbuotojai", "Nustatymai"
]
modulis = st.sidebar.radio("📂 Pasirink modulį", moduliai)

# ─── NUSTATYMAI ───────────────────────────────────────────────────────────────
if modulis == "Nustatymai":
    st.title("DISPO – Sąrašų valdymas")
    kategorijos = [row[0] for row in c.execute(
        "SELECT DISTINCT kategorija FROM lookup"
    ).fetchall()]
    col1, col2 = st.columns(2)
    esama = col1.selectbox("Esama kategorija", [""] + kategorijos)
    nauja_kat = col2.text_input("Arba nauja kategorija")
    kategorija = nauja_kat.strip() if nauja_kat else esama
    st.markdown("---")
    if kategorija:
        st.subheader(f"Kategorija: **{kategorija}**")
        values = [r[0] for r in c.execute(
            "SELECT reiksme FROM lookup WHERE kategorija = ?", (kategorija,)
        ).fetchall()]
        st.write(values or "_(nerasta reikšmių)_")
        nauja_reiksme = st.text_input("Pridėti naują reikšmę")
        if st.button("➕ Pridėti reikšmę"):
            if nauja_reiksme:
                try:
                    c.execute(
                        "INSERT INTO lookup(kategorija, reiksme) VALUES(?, ?)",
                        (kategorija, nauja_reiksme)
                    )
                    conn.commit()
                    st.success(f"✅ Pridėta: {nauja_reiksme}")
                except sqlite3.IntegrityError:
                    st.warning("⚠️ Toks elementas jau egzistuoja.")
        istr = st.selectbox("Ištrinti reikšmę", [""] + values)
        if st.button("🗑 Ištrinti reikšmę"):
            if istr:
                c.execute(
                    "DELETE FROM lookup WHERE kategorija = ? AND reiksme = ?",
                    (kategorija, istr)
                )
                conn.commit()
                st.success(f"✅ Ištrinta: {istr}")
    else:
        st.info("Pasirink arba sukurk kategoriją, kad valdytum reikšmes.")

# ─── KROVINIAI ────────────────────────────────────────────────────────────────
elif modulis == "Kroviniai":
    st.title("DISPO – Krovinių valdymas")

    # — Edit or New? —
    kroviniai_df = pd.read_sql_query("SELECT id, uzsakymo_numeris FROM kroviniai", conn)
    edit_choice = st.selectbox(
        "🔍 Redaguoti esamą krovinį",
        [""] + [f"{row.id} – {row.uzsakymo_numeris}" for row in kroviniai_df.itertuples()]
    )
    edit_id = None
    existing = {}
    pak_list = []
    isk_list = []
    if edit_choice:
        edit_id = int(edit_choice.split(" – ")[0])
        rec = c.execute("SELECT * FROM kroviniai WHERE id = ?", (edit_id,)).fetchone()
        cols = [d[0] for d in c.description]
        existing = dict(zip(cols, rec))
        # load existing pakrovimai/iskrovimai
        pak_list = c.execute(
            "SELECT data,laikas_nuo,laikas_iki,salis,miestas,adresas FROM pakrovimai WHERE krovinys_id = ? ORDER BY data",
            (edit_id,)
        ).fetchall()
        isk_list = c.execute(
            "SELECT data,laikas_nuo,laikas_iki,salis,miestas,adresas FROM iskrovimai WHERE krovinys_id = ? ORDER BY data",
            (edit_id,)
        ).fetchall()

    # — session_state for dynamic lists —
    if 'n_pak' not in st.session_state:
        st.session_state.n_pak = max(1, len(pak_list) or 1)
    if 'n_isk' not in st.session_state:
        st.session_state.n_isk = max(1, len(isk_list) or 1)

    with st.form("krovinio_forma", clear_on_submit=False):
        # 1) Client selector first
        kl_df = pd.read_sql_query("SELECT id,pavadinimas,post_kodas,miestas FROM klientai", conn)
        kl_opts = {f"{row.pavadinimas} {row.post_kodas} {row.miestas}": row.id for row in kl_df.itertuples()}
        if kl_opts:
            sel = st.selectbox("Klientas", [""] + list(kl_opts.keys()), index=0 if not existing else list(kl_opts.keys()).index(
                next(k for k,v in kl_opts.items() if v==existing.get('klientas_id'))
            ))
            klientas_id = kl_opts.get(sel, None)
        else:
            sel = st.text_input("Klientas (nėra įvestų)")
            klientas_id = None

        uzsakymo_numeris = st.text_input(
            "Užsakymo numeris",
            value=existing.get('uzsakymo_numeris','') if existing else ''
        )
        pakrovimo_numeris = st.text_input(
            "Pakrovimo numeris",
            value=existing.get('pakrovimo_numeris','') if existing else ''
        )
        iskrovimo_numeris = st.text_input(
            "Iškrovimo numeris",
            value=existing.get('iskrovimo_numeris','') if existing else ''
        )

        # 2) Pakrovimai dynamic
        st.markdown("**Pakrovimai**")
        if st.button("➕ Pridėti pakrovimą"):
            st.session_state.n_pak += 1
        pak_inputs = []
        for i in range(st.session_state.n_pak):
            cols = st.columns(6)
            d = cols[0].date_input(f"Data #{i+1}", value=date.fromisoformat(pak_list[i][0]) if i<len(pak_list) else date.today(), key=f"pd{i}")
            ln = cols[1].time_input("Laikas nuo", value=time(8,0), key=f"pn{i}")
            li = cols[2].time_input("Laikas iki", value=time(17,0), key=f"pi{i}")
            sal = cols[3].text_input("Šalis", key=f"ps{i}", value=pak_list[i][3] if i<len(pak_list) else "")
            mie = cols[4].text_input("Miestas", key=f"pm{i}", value=pak_list[i][4] if i<len(pak_list) else "")
            adr = cols[5].text_input("Adresas", key=f"pa{i}", value=pak_list[i][5] if i<len(pak_list) else "")
            pak_inputs.append((d,ln,li,sal,mie,adr))

        # 3) Iškrovimai dynamic
        st.markdown("**Iškrovimai**")
        if st.button("➕ Pridėti iškrovimą"):
            st.session_state.n_isk += 1
        isk_inputs = []
        for i in range(st.session_state.n_isk):
            cols = st.columns(6)
            d = cols[0].date_input(f"Data #{i+1}", value=date.fromisoformat(isk_list[i][0]) if i<len(isk_list) else date.today(), key=f"id{i}")
            ln = cols[1].time_input("Laikas nuo", value=time(8,0), key=f"in{i}")
            li = cols[2].time_input("Laikas iki", value=time(17,0), key=f"ii{i}")
            sal = cols[3].text_input("Šalis", key=f"is{i}", value=isk_list[i][3] if i<len(isk_list) else "")
            mie = cols[4].text_input("Miestas", key=f"im{i}", value=isk_list[i][4] if i<len(isk_list) else "")
            adr = cols[5].text_input("Adresas", key=f"ia{i}", value=isk_list[i][5] if i<len(isk_list) else "")
            isk_inputs.append((d,ln,li,sal,mie,adr))

        # 4) Vilkikas / Priekaba / etc.
        vilkikai = [r[0] for r in c.execute("SELECT numeris FROM vilkikai").fetchall()]
        if vilkikai:
            vilkikas = st.selectbox("Vilkikas", vilkikai,
                                     index=vilkikai.index(existing.get('vilkikas','')) if existing else 0)
            priekaba = c.execute(
                "SELECT priekaba FROM vilkikai WHERE numeris = ?", (vilkikas,)
            ).fetchone()[0] or ""
        else:
            vilkikas = st.text_input("Vilkikas (nėra įvestų)")
            priekaba = ""
        st.text_input("Priekaba", value=priekaba, disabled=True)

        col7, col8, col9 = st.columns(3)
        kilometrai = col7.number_input("Kilometrai", value=existing.get('kilometrai',0) if existing else 0, step=1)
        frachtas = col8.number_input("Frachtas (€)", value=existing.get('frachtas',0.0) if existing else 0.0, step=0.1)
        svoris = col9.number_input("Svoris (kg)", value=existing.get('svoris',0) if existing else 0, step=1)
        paleciu = st.number_input("Padėklų skaičius", value=existing.get('paleciu_skaicius',0) if existing else 0, step=1)

        busena_opt = [r[0] for r in c.execute(
            "SELECT reiksme FROM lookup WHERE kategorija = ?", ("busena",)
        ).fetchall()]
        busena = st.selectbox("Būsena", busena_opt) if busena_opt else st.selectbox(
            "Būsena", ["suplanuotas","nesuplanuotas","pakrautas","iškrautas"]
        )

        submit = st.form_submit_button("💾 Išsaugoti krovinį")

    if submit:
        if not klientas_id or not uzsakymo_numeris:
            st.error("❌ Privalomi laukai: Klientas ir Užsakymo numeris.")
        else:
            # INSERT vs UPDATE
            if edit_id:
                # update
                c.execute("""
                    UPDATE kroviniai SET
                        klientas_id=?, pakrovimo_numeris=?, iskrovimo_numeris=?,
                        vilkikas=?, priekaba=?, atsakingas_vadybininkas=?,
                        kilometrai=?, frachtas=?, svoris=?, paleciu_skaicius=?, busena=?
                    WHERE id=?
                """, (
                    klientas_id, pakrovimo_numeris, iskrovimo_numeris,
                    vilkikas, priekaba, f"vadyb_{vilkikas.lower()}",
                    kilometrai, frachtas, svoris, paleciu, busena,
                    edit_id
                ))
                krovinys_id = edit_id
                st.success("✅ Krovinį atnaujinau.")
                # clear old many-to-one
                c.execute("DELETE FROM pakrovimai WHERE krovinys_id=?", (krovinys_id,))
                c.execute("DELETE FROM iskrovimai WHERE krovinys_id=?", (krovinys_id,))
            else:
                # new
                c.execute("""
                    INSERT INTO kroviniai (
                        klientas_id, uzsakymo_numeris, pakrovimo_numeris, iskrovimo_numeris,
                        vilkikas, priekaba, atsakingas_vadybininkas,
                        kilometrai, frachtas, svoris, paleciu_skaicius, busena
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    klientas_id, uzsakymo_numeris, pakrovimo_numeris, iskrovimo_numeris,
                    vilkikas, priekaba, f"vadyb_{vilkikas.lower()}",
                    kilometrai, frachtas, svoris, paleciu, busena
                ))
                krovinys_id = c.lastrowid
                st.success("✅ Krovinį išsaugojau.")
            # insert many-to-one
            for d,ln,li,sal,mie,adr in pak_inputs:
                c.execute("""
                    INSERT INTO pakrovimai(krovinys_id,data,laikas_nuo,laikas_iki,salis,miestas,adresas)
                    VALUES(?,?,?,?,?,?,?)
                """, (krovinys_id,str(d),str(ln),str(li),sal,mie,adr))
            for d,ln,li,sal,mie,adr in isk_inputs:
                c.execute("""
                    INSERT INTO iskrovimai(krovinys_id,data,laikas_nuo,laikas_iki,salis,miestas,adresas)
                    VALUES(?,?,?,?,?,?,?)
                """, (krovinys_id,str(d),str(ln),str(li),sal,mie,adr))
            conn.commit()

    # — Summary table: show only first pakrovimas & last iskrovimas
    st.subheader("📋 Krovinių sąrašas")
    summary = []
    for row in c.execute("""
        SELECT k.id, k.uzsakymo_numeris, cl.pavadinimas,
               k.vilkikas, k.frachtas, k.busena
        FROM kroviniai k
        LEFT JOIN klientai cl ON cl.id = k.klientas_id
    """):
        kid, uz, kpav, vilk, fra, bus = row
        # first pak
        first_p = c.execute("""
            SELECT data||' '||laikas_nuo FROM pakrovimai
            WHERE krovinys_id=? ORDER BY data,laikas_nuo LIMIT 1
        """, (kid,)).fetchone()
        last_i = c.execute("""
            SELECT data||' '||laikas_iki FROM iskrovimai
            WHERE krovinys_id=? ORDER BY data DESC,laikas_iki DESC LIMIT 1
        """, (kid,)).fetchone()
        summary.append({
            "ID": kid,
            "Užsakymas": uz,
            "Klientas": kpav,
            "Vilkikas": vilk,
            "Pirmas pak.:": first_p[0] if first_p else "",
            "Pask. isk.:": last_i[0] if last_i else "",
            "Frachtas": fra,
            "Būsena": bus
        })
    st.dataframe(pd.DataFrame(summary))

# ─── VILKIKAI ────────────────────────────────────────────────────────────────
elif modulis == "Vilkikai":
    st.title("DISPO – Vilkikų valdymas")
    with st.form("vilkikai_forma", clear_on_submit=True):
        numeris = st.text_input("Numeris")
        marks = [r[0] for r in c.execute(
            "SELECT reiksme FROM lookup WHERE kategorija = ?", ("vilkiku_marke",)
        ).fetchall()]
        marke = st.selectbox("Markė", marks) if marks else st.text_input("Markė")
        pag_metai = st.number_input("Pagaminimo metai", step=1)
        tech_apz = st.date_input("Tech. apžiūra")
        vadyb = st.text_input("Vadybininkas")
        vair = st.text_input("Vairuotojai (kableliai)")
        priek = st.text_input("Priekaba")
        sub = st.form_submit_button("💾 Įrašyti vilkiką")
    if sub:
        if not numeris:
            st.warning("⚠️ Įveskite numerį.")
        else:
            try:
                c.execute("""
                    INSERT INTO vilkikai (
                        numeris, marke, pagaminimo_metai, tech_apziura,
                        vadybininkas, vairuotojai, priekaba
                    ) VALUES (?,?,?,?,?,?,?)
                """, (numeris, marke, pag_metai, str(tech_apz),
                      vadyb, vair, priek))
                conn.commit(); st.success("✅ Išsaugojau.")
            except Exception as e:
                st.error(f"❌ Klaida: {e}")
    st.dataframe(pd.read_sql_query("SELECT * FROM vilkikai", conn))

# ─── PRIEKABOS ───────────────────────────────────────────────────────────────
elif modulis == "Priekabos":
    st.title("DISPO – Priekabų valdymas")
    with st.form("priek_form", clear_on_submit=True):
        tipai = [r[0] for r in c.execute(
            "SELECT reiksme FROM lookup WHERE kategorija = ?", ("priekabu_tipas",)
        ).fetchall()]
        pr_tipas = st.selectbox("Tipas", tipai) if tipai else st.text_input("Tipas")
        num = st.text_input("Numeris")
        mr = st.text_input("Markė")
        pm = st.number_input("Pagaminimo metai", step=1)
        ta = st.date_input("Tech. apžiūra")
        pv = st.text_input("Priskirtas vilkikas")
        sb = st.form_submit_button("💾 Išsaugoti")
    if sb:
        if not num:
            st.warning("⚠️ Įveskite numerį.")
        else:
            try:
                c.execute("""
                    INSERT INTO priekabos (
                        priekabu_tipas, numeris, marke,
                        pagaminimo_metai, tech_apziura, priskirtas_vilkikas
                    ) VALUES (?,?,?,?,?,?)
                """, (pr_tipas, num, mr, pm, str(ta), pv))
                conn.commit(); st.success("✅ Išsaugojau.")
            except Exception as e:
                st.error(f"❌ Klaida: {e}")
    st.dataframe(pd.read_sql_query("SELECT * FROM priekabos", conn))

# ─── GRUPĖS ─────────────────────────────────────────────────────────────────
elif modulis == "Grupės":
    st.title("DISPO – Grupės")
    with st.form("grp_form", clear_on_submit=True):
        nr = st.text_input("Numeris")
        pav = st.text_input("Pavadinimas")
        apr = st.text_area("Aprašymas")
        sb = st.form_submit_button("💾 Išsaugoti")
    if sb:
        if not nr or not pav:
            st.warning("⚠️ Numeris ir pavadinimas būtini.")
        else:
            try:
                c.execute(
                    "INSERT INTO grupes(numeris,pavadinimas,aprasymas) VALUES(?,?,?)",
                    (nr,pav,apr)
                )
                conn.commit(); st.success("✅ Išsaugojau.")
            except Exception as e:
                st.error(f"❌ Klaida: {e}")
    st.dataframe(pd.read_sql_query("SELECT * FROM grupes", conn))

# ─── VAIRUOTOJAI ─────────────────────────────────────────────────────────────
elif modulis == "Vairuotojai":
    st.title("DISPO – Vairuotojai")
    with st.form("drv_form", clear_on_submit=True):
        vd = st.text_input("Vardas"); pv = st.text_input("Pavardė")
        gm = st.number_input("Gimimo metai", step=1); tt = st.text_input("Tautybė")
        pvk = st.text_input("Priskirtas vilkikas")
        sb = st.form_submit_button("💾 Išsaugoti")
    if sb:
        if not vd or not pv:
            st.warning("⚠️ Reikia vardo ir pavardės.")
        else:
            try:
                c.execute("""
                    INSERT INTO vairuotojai (
                        vardas,pavarde,gimimo_metai,tautybe,priskirtas_vilkikas
                    ) VALUES(?,?,?,?,?)
                """, (vd,pv,gm,tt,pvk))
                conn.commit(); st.success("✅ Išsaugojau.")
            except Exception as e:
                st.error(f"❌ Klaida: {e}")
    st.dataframe(pd.read_sql_query("SELECT * FROM vairuotojai", conn))

# ─── KLIENTAI ────────────────────────────────────────────────────────────────
elif modulis == "Klientai":
    st.title("DISPO – Klientai")
    with st.form("kl_form", clear_on_submit=True):
        iv = st.text_input("Įmonės pavadinimas")
        pk = st.text_input("Pašto kodas")
        sl = st.text_input("Šalis"); ms = st.text_input("Miestas")
        rg = st.text_input("Regionas"); pv = st.text_input("PVM numeris")
        st.markdown("**Kontaktas (bendras)**")
        kv = st.text_input("Vardas"); kp = st.text_input("Pavardė")
        ke = st.text_input("El. paštas"); kt = st.text_input("Telefonas")
        st.markdown("**Kontaktas dėl sąskaitų**")
        ivv = st.text_input("Vardas"); ivp = st.text_input("Pavardė")
        ive = st.text_input("El. paštas"); ivt = st.text_input("Telefonas")
        co = st.number_input("Coface limitas (€)", value=0.0, step=0.1)
        # our_limit = coface / 3, likes_limit arbitrary example: coface * 0.5
        ol = co / 3 if co else 0
        ll = co * 0.5 if co else 0
        st.write(f"Mūsų limitas: {ol:.2f} €, Likes limitas: {ll:.2f} €")
        apm = st.multiselect("Atsiskaitymo būdas", ["Originalus dokumentai","Platforma","Skanuoti dokumentai"])
        apt = st.text_input("Atsiskaitymo terminas")
        apn = st.text_input("Atsiskaitymo naudingumas")
        sb = st.form_submit_button("💾 Išsaugoti")
    if sb:
        # uniqueness check
        exists = c.execute("""
            SELECT COUNT(*) FROM klientai
            WHERE pavadinimas=? AND miestas=? AND post_kodas=?
        """, (iv,ms,pk)).fetchone()[0]
        if exists:
            st.error("❌ Toks klientas jau egzistuoja.")
        elif not iv:
            st.warning("⚠️ Pavadinimas būtinas.")
        else:
            try:
                c.execute("""
                    INSERT INTO klientai (
                        pavadinimas,post_kodas,salis,miestas,regionas,vat_numeris,
                        kontaktas_vardas,kontaktas_pavarde,kontaktas_el,kontaktas_tel,
                        inv_kont_vardas,inv_kont_pavarde,inv_kont_el,inv_kont_tel,
                        coface_limitas,our_limitas,likes_limitas,
                        apm_metodai,apm_terminas,apm_naudingumas
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    iv,pk,sl,ms,rg,pv,
                    kv,kp,ke,kt,
                    ivv,ivp,ive,ivt,
                    co,ol,ll,
                    ",".join(apm),apt,apn
                ))
                conn.commit(); st.success("✅ Išsaugojau.")
            except Exception as e:
                st.error(f"❌ Klaida: {e}")
    st.dataframe(pd.read_sql_query("SELECT * FROM klientai", conn))

# ─── DARBUOTOJAI ─────────────────────────────────────────────────────────────
elif modulis == "Darbuotojai":
    st.title("DISPO – Darbuotojai")
    p_list = [r[0] for r in c.execute(
        "SELECT reiksme FROM lookup WHERE kategorija = ?", ("pareigybe",)
    ).fetchall()]
    g_list = [r[2] for r in c.execute("SELECT id,numeris,pavadinimas FROM grupes").fetchall()]
    with st.form("emp_form", clear_on_submit=True):
        vd = st.text_input("Vardas"); pv = st.text_input("Pavardė")
        pg = st.selectbox("Pareigybė", p_list) if p_list else st.text_input("Pareigybė")
        gr = st.selectbox("Grupė", g_list) if g_list else st.text_input("Grupė")
        em = st.text_input("El. paštas"); ph = st.text_input("Telefonas")
        sb = st.form_submit_button("💾 Išsaugoti")
    if sb:
        if not vd or not pv:
            st.warning("⚠️ Vardas ir pavardė būtini.")
        else:
            try:
                c.execute("""
                    INSERT INTO darbuotojai (
                        vardas,pavarde,pareigybe,el_pastas,telefonas,grupe
                    ) VALUES(?,?,?,?,?,?)
                """, (vd,pv,pg,em,ph,gr))
                conn.commit(); st.success("✅ Išsaugojau.")
            except Exception as e:
                st.error(f"❌ Klaida: {e}")
    st.dataframe(pd.read_sql_query("SELECT * FROM darbuotojai", conn))
