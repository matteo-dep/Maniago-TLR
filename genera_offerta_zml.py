"""
Maniago TLR - Esploratore curve di carico (DOMANDA + OFFERTA)
=====================================================
Avvio locale: streamlit run app.py
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np

st.set_page_config(page_title="Maniago TLR - Curve di carico", layout="wide")

# ---------------------------------------------------------------------------
# CARICAMENTO DATI (Inclusa generazione dinamica Offerta ZML)
# ---------------------------------------------------------------------------
@st.cache_data
def load_data():
    # 1. Caricamento della DOMANDA
    buildings = pd.read_csv("maniago_domanda_edifici.csv")
    hourly = pd.read_csv("maniago_domanda_oraria_8760h_HDD_reale.csv", parse_dates=["datetime"])

    # 2. Generazione dinamica dell'OFFERTA (ZML)
    P_PICCO_MW = 160.0 * 1000 * (4.186 / 3600) * (65.0 - 40.0) # ~4.65 MW
    
    offerta_zml = pd.DataFrame({"datetime": hourly["datetime"].drop_duplicates()})
    offerta_zml["mese"] = offerta_zml["datetime"].dt.month
    offerta_zml["giorno_sett"] = offerta_zml["datetime"].dt.weekday
    offerta_zml["ora"] = offerta_zml["datetime"].dt.hour

    def calcola_potenza(row):
        # Spento weekend (5=Sabato, 6=Domenica) o agosto (8)
        if row["giorno_sett"] >= 5 or row["mese"] == 8:
            return 0.0
        # Spento a Natale (22 Dicembre - 6 Gennaio)
        if (row["mese"] == 1 and row["datetime"].day <= 6) or (row["mese"] == 12 and row["datetime"].day >= 22):
            return 0.0
        # Turno operativo 06:00 - 22:00
        if 6 <= row["ora"] < 22:
            frequenza_ciclo = 2 * np.pi / 3
            return P_PICCO_MW * (0.675 + 0.325 * np.sin(row["ora"] * frequenza_ciclo))
        return 0.0

    offerta_zml["MWh_termici"] = offerta_zml.apply(calcola_potenza, axis=1)

    return buildings, hourly, offerta_zml

buildings, hourly, offerta_zml = load_data()

# ---------------------------------------------------------------------------
# SIDEBAR - Filtri interattivi
# ---------------------------------------------------------------------------
st.sidebar.title("Filtri")
st.sidebar.caption("Analisi profili orari - Anno Tipo")

st.sidebar.subheader("Cluster di rete (Domanda)")
clusters = sorted(buildings["cluster"].unique())
selected_clusters = [c for c in clusters if st.sidebar.checkbox(c, value=True, key=f"cl_{c}")]

st.sidebar.subheader("Tipologia di utenza")
tipologie = sorted(buildings["tipologia"].unique())
select_all_tip = st.sidebar.checkbox("Seleziona tutte le tipologie", value=True)
if select_all_tip:
    selected_tip = tipologie
else:
    selected_tip = st.sidebar.multiselect("Scegli tipologie", tipologie, default=tipologie)

st.sidebar.subheader("Periodo di analisi")
min_date = hourly["datetime"].min().date()
max_date = hourly["datetime"].max().date()
date_range = st.sidebar.slider("Seleziona range", min_value=min_date, max_value=max_date, value=(min_date, max_date))

# ---------------------------------------------------------------------------
# FILTRAGGIO DATI DOMANDA
# ---------------------------------------------------------------------------
df = hourly[
    (hourly["cluster"].isin(selected_clusters)) & 
    (hourly["tipologia"].isin(selected_tip)) &
    (hourly["datetime"].dt.date >= date_range[0]) & 
    (hourly["datetime"].dt.date <= date_range[1])
]

# ---------------------------------------------------------------------------
# GRAFICO 1: BILANCIO TERMICO (Domanda vs Offerta ZML)
# ---------------------------------------------------------------------------
st.subheader("Bilancio Termico: Domanda Edifici vs Offerta Industriale ZML")

# Aggreghiamo la domanda totale
domanda_totale = df.groupby("datetime")["MWh"].sum().reset_index()
domanda_totale.rename(columns={"MWh": "Domanda Reti (MWh)"}, inplace=True)

# Filtriamo i giorni di ZML
mask_off = (offerta_zml["datetime"].dt.date >= date_range[0]) & (offerta_zml["datetime"].dt.date <= date_range[1])
off_filtered = offerta_zml[mask_off].copy()

# Uniamo le tabelle
bilancio = pd.merge(domanda_totale, off_filtered[["datetime", "MWh_termici"]], on="datetime", how="left")
bilancio.rename(columns={"MWh_termici": "Offerta ZML (MWh)"}, inplace=True)

# Plot
fig_bilancio = go.Figure()
fig_bilancio.add_trace(go.Scatter(
    x=bilancio["datetime"], y=bilancio["Domanda Reti (MWh)"], 
    fill='tozeroy', mode='lines', line=dict(color='rgba(215, 40, 40, 0.8)', width=1), 
    name='Domanda Termica (Cluster Selezionati)'
))
fig_bilancio.add_trace(go.Scatter(
    x=bilancio["datetime"], y=bilancio["Offerta ZML (MWh)"], 
    mode='lines', line=dict(color='rgba(40, 167, 69, 1)', width=2), 
    name='Disponibilità Calore ZML (Mandata 65°C)'
))

fig_bilancio.update_layout(
    height=400, xaxis_title="Data e Ora", yaxis_title="Potenza Termica (MW)", 
    hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)
st.plotly_chart(fig_bilancio, use_container_width=True)

# KPI Rapido
energia_domanda = bilancio["Domanda Reti (MWh)"].sum()
energia_offerta = bilancio["Offerta ZML (MWh)"].sum()
st.caption(f"Nel periodo visualizzato: **Fabbisogno reti = {energia_domanda:,.0f} MWh** | **Recupero teorico ZML = {energia_offerta:,.0f} MWh**")


# ---------------------------------------------------------------------------
# GRAFICO 2: DOMANDA MENSILE
# ---------------------------------------------------------------------------
st.markdown("---")
st.subheader("Domanda mensile per cluster")
month_names = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu", "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]
monthly = df.copy()
monthly["mese_num"] = monthly["datetime"].dt.month
monthly["mese"] = monthly["mese_num"].map(lambda m: month_names[m-1])

monthly_agg = monthly.groupby(["mese", "mese_num", "cluster"])["MWh"].sum().reset_index()
monthly_agg = monthly_agg.sort_values("mese_num")

fig_month = px.bar(monthly_agg, x="mese", y="MWh", color="cluster", barmode="stack")
fig_month.update_layout(height=350, xaxis_title="", yaxis_title="Energia (MWh)")
st.plotly_chart(fig_month, use_container_width=True)


# ---------------------------------------------------------------------------
# TABELLA: DETTAGLIO EDIFICI
# ---------------------------------------------------------------------------
with st.expander("Dettaglio per edificio (Domanda)"):
    detail = df.groupby(["edificio", "cluster", "tipologia"])["MWh"].sum().reset_index()
    detail = detail.sort_values("MWh", ascending=False).rename(columns={"MWh": "Energia periodo (MWh)"})
    st.dataframe(detail, use_container_width=True, hide_index=True)

st.caption("Fonti: Google Sheet 'Utenze TLR Maniago' (De Blasio Associati / APE FVG), stazione meteo Vivaro, Sopralluoghi Aziende.")
