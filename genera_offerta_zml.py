"""
Maniago TLR - Esploratore curve di carico con Accumulo Termico
==============================================================
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np

st.set_page_config(page_title="Maniago TLR - Curve di carico", layout="wide")

# ===========================================================================
# 1. CARICAMENTO DATI E GENERAZIONE OFFERTA (Tutto in memoria)
# ===========================================================================
@st.cache_data
def load_data():
    buildings = pd.read_csv("maniago_domanda_edifici.csv")
    hourly = pd.read_csv("maniago_domanda_oraria_8760h_HDD_reale.csv", parse_dates=["datetime"])

    # Generazione Offerta ZML dinamica
    P_PICCO_MW = 160.0 * 1000 * (4.186 / 3600) * (65.0 - 40.0) # ~4.65 MW
    
    offerta_zml = pd.DataFrame({"datetime": hourly["datetime"].drop_duplicates()})
    offerta_zml["mese"] = offerta_zml["datetime"].dt.month
    offerta_zml["giorno_sett"] = offerta_zml["datetime"].dt.weekday
    offerta_zml["ora"] = offerta_zml["datetime"].dt.hour

    def calcola_potenza(row):
        # Spento weekend o agosto
        if row["giorno_sett"] >= 5 or row["mese"] == 8:
            return 0.0
        # Spento a Natale
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

# ===========================================================================
# 2. BARRA LATERALE E FILTRI INTERATTIVI
# ===========================================================================
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

min_date = hourly["datetime"].min().date()
max_date = hourly["datetime"].max().date()
date_range = st.sidebar.slider("Seleziona range", min_value=min_date, max_value=max_date, value=(min_date, max_date))

st.sidebar.markdown("---")
st.sidebar.subheader("Parametri Impianto")
# Slider in metri cubi d'acqua
volume_accumulo_m3 = st.sidebar.slider("Volume Accumulo (m³)", min_value=0, max_value=5000, value=1000, step=100)

# Conversione m3 -> MWh (Ipotizzando salto termico delta T = 40°C per l'accumulo)
DELTA_T_ACCUMULO = 40
# Formula: V * rho(1000) * cp(4.186/3600) * DT
CAPACITA_ACCUMULO_MWH = volume_accumulo_m3 * (4.186 / 3600) * DELTA_T_ACCUMULO

df = hourly[
    (hourly["cluster"].isin(selected_clusters)) & 
    (hourly["tipologia"].isin(selected_tip)) &
    (hourly["datetime"].dt.date >= date_range[0]) & 
    (hourly["datetime"].dt.date <= date_range[1])
]

# ===========================================================================
# 3. GRAFICO PRINCIPALE: BILANCIO E ACCUMULO TERMICO
# ===========================================================================
st.subheader("Bilancio Termico: Analisi Copertura, Accumulo e Sprechi")

domanda_totale = df.groupby("datetime")["MWh"].sum().reset_index()
domanda_totale.rename(columns={"MWh": "Domanda Reti (MWh)"}, inplace=True)

mask_off = (offerta_zml["datetime"].dt.date >= date_range[0]) & (offerta_zml["datetime"].dt.date <= date_range[1])
off_filtered = offerta_zml[mask_off].copy()
bilancio = pd.merge(domanda_totale, off_filtered[["datetime", "MWh_termici"]], on="datetime", how="left")
bilancio.rename(columns={"MWh_termici": "Offerta ZML (MWh)"}, inplace=True)

bilancio["Calore_Usato_ZML_Diretto"] = np.minimum(bilancio["Domanda Reti (MWh)"], bilancio["Offerta ZML (MWh)"])
bilancio["Esubero_ZML"] = np.maximum(0, bilancio["Offerta ZML (MWh)"] - bilancio["Domanda Reti (MWh)"])
bilancio["Deficit_Rete"] = np.maximum(0, bilancio["Domanda Reti (MWh)"] - bilancio["Offerta ZML (MWh)"])

# Simulazione logica dell'accumulo ora per ora
soc = np.zeros(len(bilancio))
scarica_accumulo = np.zeros(len(bilancio))
carica_accumulo = np.zeros(len(bilancio))
livello_attuale = 0.0

for i in range(len(bilancio)):
    esubero = bilancio["Esubero_ZML"].iloc[i]
    deficit = bilancio["Deficit_Rete"].iloc[i]
    
    # Se c'è esubero da ZML, carichiamo l'accumulo fino a capienza massima
    if esubero > 0 and livello_attuale < CAPACITA_ACCUMULO_MWH:
        energia_caricabile = min(esubero, CAPACITA_ACCUMULO_MWH - livello_attuale)
        livello_attuale += energia_caricabile
        carica_accumulo[i] = energia_caricabile
        
    # Se c'è deficit, scarichiamo l'accumulo se ha energia disponibile
    elif deficit > 0 and livello_attuale > 0:
        energia_scaricabile = min(deficit, livello_attuale)
        livello_attuale -= energia_scaricabile
        scarica_accumulo[i] = energia_scaricabile
        
    soc[i] = livello_attuale

bilancio["Scarica_Accumulo"] = scarica_accumulo
bilancio["Carica_Accumulo"] = carica_accumulo
bilancio["SoC_Accumulo"] = soc

# Calcolo grandezze finali
bilancio["Integrazione_Caldaie_Finale"] = bilancio["Deficit_Rete"] - bilancio["Scarica_Accumulo"]
bilancio["Calore_Dissipato_ZML_Finale"] = bilancio["Esubero_ZML"] - bilancio["Carica_Accumulo"]

# Plot
fig_bilancio = go.Figure()
fig_bilancio.add_trace(go.Scatter(x=bilancio["datetime"], y=bilancio["Calore_Usato_ZML_Diretto"], fill='tozeroy', mode='none', fillcolor='rgba(40, 167, 69, 0.7)', name='ZML (Uso Diretto)', stackgroup='one'))
fig_bilancio.add_trace(go.Scatter(x=bilancio["datetime"], y=bilancio["Scarica_Accumulo"], fill='tonexty', mode='none', fillcolor='rgba(23, 162, 184, 0.7)', name='Scarica Accumulo (TES)', stackgroup='one'))
fig_bilancio.add_trace(go.Scatter(x=bilancio["datetime"], y=bilancio["Integrazione_Caldaie_Finale"], fill='tonexty', mode='none', fillcolor='rgba(215, 40, 40, 0.7)', name='Integrazione Caldaie (Mancante)', stackgroup='one'))
fig_bilancio.add_trace(go.Scatter(x=bilancio["datetime"], y=bilancio["Calore_Dissipato_ZML_Finale"], mode='lines', line=dict(color='rgba(150, 150, 150, 0.8)', width=1, dash='dot'), name='Spreco ZML Finale (Torre)'))

fig_bilancio.update_layout(height=450, xaxis_title="Timeline", yaxis_title="Potenza Termica (MW)", hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
st.plotly_chart(fig_bilancio, use_container_width=True)

# ===========================================================================
# 4. KPI NUMERICI (AGGIORNATI)
# ===========================================================================
tot_domanda = bilancio["Domanda Reti (MWh)"].sum()
tot_zml_diretto = bilancio["Calore_Usato_ZML_Diretto"].sum()
tot_accumulo_usato = bilancio["Scarica_Accumulo"].sum()
tot_integrato_finale = bilancio["Integrazione_Caldaie_Finale"].sum()
tot_dissipato_finale = bilancio["Calore_Dissipato_ZML_Finale"].sum()

copertura_totale_zml = tot_zml_diretto + tot_accumulo_usato
perc_copertura = (copertura_totale_zml / tot_domanda) * 100 if tot_domanda > 0 else 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("Domanda Totale", f"{tot_domanda:,.0f} MWh")
col2.metric("Copertura (ZML + Accumulo)", f"{copertura_totale_zml:,.0f} MWh", f"{perc_copertura:.1f}% del totale", delta_color="normal")
col3.metric("Integrazione Caldaie", f"{tot_integrato_finale:,.0f} MWh")
col4.metric("Spreco ZML (In Torre)", f"{tot_dissipato_finale:,.0f} MWh")

# ===========================================================================
# 5. GRAFICO MENSILE: COPERTURA % E DOMANDA
# ===========================================================================
st.markdown("---")
st.subheader("Copertura ZML + Accumulo mese per mese")
bilancio["mese_num"] = bilancio["datetime"].dt.month
month_names = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu", "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]
bilancio["mese"] = bilancio["mese_num"].map(lambda m: month_names[m-1])

# Creiamo la metrica di copertura totale mensile (ZML diretto + Accumulo usato)
bilancio["Copertura_Totale_Mese"] = bilancio["Calore_Usato_ZML_Diretto"] + bilancio["Scarica_Accumulo"]

monthly_bil = bilancio.groupby(["mese", "mese_num"])[["Domanda Reti (MWh)", "Copertura_Totale_Mese", "Integrazione_Caldaie_Finale"]].sum().reset_index()
monthly_bil = monthly_bil.sort_values("mese_num")
monthly_bil["% Copertura"] = (monthly_bil["Copertura_Totale_Mese"] / monthly_bil["Domanda Reti (MWh)"] * 100).fillna(0)

fig_month_bil = px.bar(
    monthly_bil, x="mese", y=["Copertura_Totale_Mese", "Integrazione_Caldaie_Finale"], 
    title="Composizione Mensile dell'Energia",
    labels={"value": "Energia (MWh)", "variable": "Fonte"},
    color_discrete_map={"Copertura_Totale_Mese": "#28a745", "Integrazione_Caldaie_Finale": "#dc3545"}
)

fig_month_bil.add_trace(go.Scatter(
    x=monthly_bil["mese"], y=monthly_bil["Domanda Reti (MWh)"] + 50,
    text=monthly_bil["% Copertura"].apply(lambda x: f"{x:.1f}%"),
    mode='text', textposition='top center', showlegend=False
))
fig_month_bil.update_layout(height=400, xaxis_title="", yaxis_title="MWh", barmode='stack')
st.plotly_chart(fig_month_bil, use_container_width=True)

# ===========================================================================
# 6. TABELLA DETTAGLIO EDIFICI
# ===========================================================================
with st.expander("Dettaglio per edificio (Domanda)"):
    detail = df.groupby(["edificio", "cluster", "tipologia"])["MWh"].sum().reset_index()
    detail = detail.sort_values("MWh", ascending=False).rename(columns={"MWh": "Energia periodo (MWh)"})
    st.dataframe(detail, use_container_width=True, hide_index=True)
