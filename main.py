elif modulis == "Kroviniai":
    st.title("DISPO – Krovinių valdymas")

    # 1) Dinaminiai adresų laukai pakrovimams/iškrovimams
    if "loads" not in st.session_state:
        st.session_state.loads = [{"data": date.today(), "nuo": time(8,0), "iki": time(17,0), "adresas": ""}]
    if "unloads" not in st.session_state:
        st.session_state.unloads = [{"data": date.today()+timedelta(days=1), "nuo": time(8,0), "iki": time(17,0), "adresas": ""}]

    col1, col2 = st.columns(2)
    if col1.button("➕ Pridėti pakrovimą"):
        st.session_state.loads.append({"data": date.today(), "nuo": time(8,0), "iki": time(17,0), "adresas": ""})
    if col2.button("➕ Pridėti iškrovimą"):
        st.session_state.unloads.append({"data": date.today()+timedelta(days=1), "nuo": time(8,0), "iki": time(17,0), "adresas": ""})

    # 2) Duomenų įvedimo forma
    with st.form("kroviniai_forma", clear_on_submit=False):
        # 2.1 Klientas VIRŠUJE – tik iš klientų lentelės
        klientai = c.execute("SELECT id, pavadinimas, post_kodas, miestas FROM klientai").fetchall()
        opts = {f"{r[1]} {r[2]} {r[3]}": r[0] for r in klientai}
        if opts:
            klientas_lbl = st.selectbox("Klientas", list(opts.keys()), key="kr_kli")
            klientas_id  = opts[klientas_lbl]
        else:
            klientas_lbl = st.text_input("Klientas", key="kr_kli_txt")
            klientas_id  = None

        # 2.2 Užsakymo numeris (leidžiame dublikatus – ID visada skirtingas)
        uzs_nr = st.text_input("Užsakymo numeris", key="kr_uzs")

        # 2.3 Vilkikas + automatinė priekaba
        vilkikai = c.execute("SELECT numeris, priekaba FROM vilkikai").fetchall()
        vopts    = {r[0]: r[1] for r in vilkikai}
        if vopts:
            vilk = st.selectbox("Vilkikas", list(vopts.keys()), key="kr_vilk")
            priek = vopts[vilk]
        else:
            vilk = st.text_input("Vilkikas", key="kr_vilk_txt")
            priek = ""
        st.text_input("Priekaba", value=priek, disabled=True, key="kr_priek")

        # 2.4 Būsena (iš lookup jei yra, kitaip tekstas)
        bus_vals = [r[0] for r in c.execute(
            "SELECT reiksme FROM lookup WHERE kategorija='busena'"
        ).fetchall()]
        if bus_vals:
            bus = st.selectbox("Būsena", bus_vals, key="kr_bus")
        else:
            bus = st.text_input("Būsena", key="kr_bus_txt")

        # 2.5 Pakrovimai su adresais
        st.markdown("**Pakrovimai (įrašyk adresą)**")
        for i, ld in enumerate(st.session_state.loads):
            with st.expander(f"Pakrovimas #{i+1}", expanded=True):
                d  = st.date_input("Data", ld["data"], key=f"kr_pak_{i}_d")
                n  = st.time_input("Nuo", ld["nuo"], key=f"kr_pak_{i}_n")
                ik = st.time_input("Iki", ld["iki"], key=f"kr_pak_{i}_i")
                ad = st.text_input("Adresas", ld["adresas"], key=f"kr_pak_{i}_ad")
                st.session_state.loads[i] = {"data":d, "nuo":n, "iki":ik, "adresas":ad}

        # 2.6 Iškrovimai su adresais
        st.markdown("**Iškrovimai (įrašyk adresą)**")
        for i, ul in enumerate(st.session_state.unloads):
            with st.expander(f"Iškrovimas #{i+1}", expanded=True):
                d  = st.date_input("Data", ul["data"], key=f"kr_isk_{i}_d")
                n  = st.time_input("Nuo", ul["nuo"], key=f"kr_isk_{i}_n")
                ik = st.time_input("Iki", ul["iki"], key=f"kr_isk_{i}_i")
                ad = st.text_input("Adresas", ul["adresas"], key=f"kr_isk_{i}_ad")
                st.session_state.unloads[i] = {"data":d, "nuo":n, "iki":ik, "adresas":ad}

        submit = st.form_submit_button("💾 Įrašyti krovinį")

    # 3) Po pateikimo – įrašome į DB
    if submit:
        # 3.1 Įspėjame jei tas pats numeris jau egzistuoja (ID vis tiek unikalus)
        cnt = c.execute("SELECT COUNT(*) FROM kroviniai WHERE uzsakymo_numeris=?", (uzs_nr,)).fetchone()[0]
        if cnt:
            st.warning("🔔 Toks užsakymo numeris jau egzistuoja – numerį palieku, tačiau įrašas gaus naują ID.")

        c.execute("""
            INSERT INTO kroviniai (
                klientas, uzsakymo_numeris,
                vilkikas, priekaba, busena
            ) VALUES (?,?,?,?,?)
        """, (klientas_lbl, uzs_nr, vilk, priek, bus))
        kid = c.lastrowid

        # 3.2 Įrašome visus pakrovimus
        for ld in st.session_state.loads:
            c.execute("""
                INSERT INTO pakrovimai (
                    krovinys_id, tipas, data,
                    laikas_nuo, laikas_iki, adresas
                ) VALUES (?,?,?,?,?,?)
            """, (kid, "load", str(ld["data"]), str(ld["nuo"]), str(ld["iki"]), ld["adresas"]))

        # 3.3 Įrašome visus iškrovimus
        for ul in st.session_state.unloads:
            c.execute("""
                INSERT INTO pakrovimai (
                    krovinys_id, tipas, data,
                    laikas_nuo, laikas_iki, adresas
                ) VALUES (?,?,?,?,?,?)
            """, (kid, "unload", str(ul["data"]), str(ul["nuo"]), str(ul["iki"]), ul["adresas"]))

        conn.commit()
        st.success(f"✅ Krovinys įrašytas (ID {kid}).")

    # 4) Detalių peržiūra – tik paspaudus iš sąrašo
    st.subheader("Peržiūrėti krovinį")
    df_ids = pd.read_sql_query("SELECT id, uzsakymo_numeris FROM kroviniai", conn)
    sel = st.selectbox(
        "Pasirink pagal ID – užsakymo numerį",
        df_ids.apply(lambda r: f"{r.id} – {r.uzsakymo_numeris}", axis=1),
        key="kr_sel"
    )
    sel_id = int(sel.split(" – ")[0])

    # 4.1 Bendra informacija
    det = c.execute("SELECT klientas, uzsakymo_numeris, vilkikas, priekaba, busena FROM kroviniai WHERE id=?", (sel_id,)).fetchone()
    st.markdown("**Bendra informacija:**")
    st.write({
        "Klientas": det[0],
        "Užsakymo numeris": det[1],
        "Vilkikas": det[2],
        "Priekaba": det[3],
        "Būsena": det[4]
    })

    # 4.2 Visos pakrovimų/iškrovimų detalės su adresais
    pak = c.execute("SELECT tipas, data, laikas_nuo, laikas_iki, adresas FROM pakrovimai WHERE krovinys_id=?", (sel_id,)).fetchall()
    st.markdown("**Visi pakrovimai ir iškrovimai:**")
    st.table(pd.DataFrame(pak, columns=["Tipas","Data","Nuo","Iki","Adresas"]))
