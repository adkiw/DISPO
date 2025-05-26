st.header("🚛 Vilkikų valdymas")

# Sukuriame lentelę vilkikai, jei jos dar nėra
c.execute("""
CREATE TABLE IF NOT EXISTS vilkikai (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numeris TEXT UNIQUE,
    marke TEXT,
    pagaminimo_metai INTEGER,
    tech_apziura DATE
)
""")
conn.commit()

with st.form("vilkiku_forma", clear_on_submit=True):
    st.subheader("➕ Pridėti naują vilkiką")
    col1, col2 = st.columns(2)
    numeris = col1.text_input("Valstybiniai numeriai")
    marke = col2.text_input("Markė")

    col3, col4 = st.columns(2)
    pagaminimo_metai = col3.text_input("Pagaminimo metai")
    tech_apziura = col4.date_input("Paskutinė techninė apžiūra")

    vilkikas_submit = st.form_submit_button("💾 Įrašyti vilkiką")

if vilkikas_submit:
    if not numeris or not pagaminimo_metai:
        st.warning("⚠️ Numeris ir pagaminimo metai yra privalomi.")
    else:
        try:
            c.execute("INSERT INTO vilkikai (numeris, marke, pagaminimo_metai, tech_apziura) VALUES (?, ?, ?, ?)",
                      (numeris, marke, int(pagaminimo_metai), str(tech_apziura)))
            conn.commit()
            st.success("✅ Vilkikas įrašytas sėkmingai!")
        except Exception as e:
            st.error(f"❌ Klaida įrašant: {e}")

# Rodyti vilkikų lentelę
st.subheader("📋 Vilkikų sąrašas")
df_vilkikai = pd.read_sql_query("SELECT * FROM vilkikai", conn)

# Įspėjimas dėl TA galiojimo
today = pd.to_datetime(date.today())
df_vilkikai["tech_apziura"] = pd.to_datetime(df_vilkikai["tech_apziura"])
df_vilkikai["🛠 TA liko (d.)"] = (df_vilkikai["tech_apziura"] - today).dt.days
df_vilkikai["TA Įspėjimas"] = df_vilkikai["🛠 TA liko (d.)"].apply(
    lambda x: "⚠️ Baigiasi" if x < 30 else "")

st.dataframe(df_vilkikai)
