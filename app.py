"""
Maniago TLR - Esploratore curve di carico (DOMANDA)
=====================================================
Avvio: streamlit run app.py
Richiede nella stessa cartella:
  - maniago_domanda_edifici.csv
  - maniago_domanda_oraria_8760h_HDD_reale.csv
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(page_title="Maniago TLR - Curve di carico", layout="wide")


@st.cache_data
def load_data():
    buildings = pd.read_csv("maniago_domanda_edifici.csv")
    hourly = pd.read_csv("maniago_domanda_oraria_8760h_HDD_reale.csv", parse_dates=["datetime"])
    return buildings, hourly


buildings, hourly = load_data()

# ---------------------------------------------------------------------------
# Sidebar - filtri
# ---------------------------------------------------------------------------
st.sidebar.title("Filtri")
st.sidebar.caption("Domanda termica - profilo orario, anno tipo")

clusters = sorted(buildings["cluster"].unique())
st.sidebar.subheader("Cluster di rete")
selected_clusters = [c for c in clusters if st.sidebar.checkbox(c, value=True, key=f"cl_{c}")]

st.sidebar.subheader("Tipologia di utenza")
tipologie = sorted(buildings["tipologia"].unique())
select_all_tip = st.sidebar.checkbox("Seleziona tutte le tipologie", value=True)
selected_tip = st.sidebar.multiselect(
    "Filtra per tipologia (opzionale)",
    tipologie,
    default=tipologie if select_all_tip else [],
)

st.sidebar.subheader("Periodo")
month_names = ["Gen","Feb","Mar","Apr","Mag","Giu","Lug","Ago","Set","Ott","Nov","Dic"]
month_range = st.sidebar.select_slider(
    "Mesi da visualizzare", options=list(range(1,13)),
    value=(1,12), format_func=lambda m: month_names[m-1]
)

# ---------------------------------------------------------------------------
# Filtraggio dati
# ---------------------------------------------------------------------------
mask_building = buildings["cluster"].isin(selected_clusters) & buildings["tipologia"].isin(selected_tip)
selected_buildings = buildings.loc[mask_building, "edificio"].tolist()

df = hourly[hourly["edificio"].isin(selected_buildings)].copy()
df["month"] = df["datetime"].dt.month
df = df[(df["month"] >= month_range[0]) & (df["month"] <= month_range[1])]

if df.empty:
    st.warning("Nessun edificio selezionato: spunta almeno un cluster e una tipologia nella barra laterale.")
    st.stop()

agg_total = df.groupby("datetime")["MWh"].sum().reset_index()
agg_cluster = df.groupby(["datetime", "cluster"])["MWh"].sum().reset_index()

# ---------------------------------------------------------------------------
# KPI
# ---------------------------------------------------------------------------
st.title("Maniago TLR — Curve di carico della domanda")
st.caption(
    "Anno tipo (calendario 2024) · temperatura calibrata su dati reali stazione "
    "Vivaro (anno 2011, corretto verso i 2.850 GG ufficiali di Maniago)"
)

energia_tot = agg_total["MWh"].sum()
picco = agg_total["MWh"].max()
ore_anno = len(agg_total)
load_factor = energia_tot / (picco * ore_anno) if picco > 0 else 0
ora_picco = agg_total.loc[agg_total["MWh"].idxmax(), "datetime"]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Energia nel periodo", f"{energia_tot:,.0f} MWh".replace(",", "."))
c2.metric("Picco orario", f"{picco:.3f} MW", help=f"il {ora_picco.strftime('%d/%m alle %H:00')}")
c3.metric("Edifici selezionati", f"{len(selected_buildings)} / {len(buildings)}")
c4.metric("Fattore di carico", f"{load_factor*100:.1f}%",
          help="Energia reale / (potenza di picco × ore) — quanto è 'piatto' il carico")

st.divider()

# ---------------------------------------------------------------------------
# Grafico curva di carico oraria (per cluster, sovrapponibile)
# ---------------------------------------------------------------------------
st.subheader("Curva di carico oraria")
show_by_cluster = st.toggle("Scomponi per cluster", value=True)

fig = go.Figure()
if show_by_cluster:
    for cl in selected_clusters:
        sub = agg_cluster[agg_cluster["cluster"] == cl]
        fig.add_trace(go.Scatter(x=sub["datetime"], y=sub["MWh"], mode="lines",
                                  name=cl, stackgroup="one", line=dict(width=0.5)))
else:
    fig.add_trace(go.Scatter(x=agg_total["datetime"], y=agg_total["MWh"], mode="lines",
                              name="Totale selezione", line=dict(width=1)))
fig.update_layout(height=450, xaxis_title="", yaxis_title="MWh/h (≈ MW)",
                   legend=dict(orientation="h", yanchor="bottom", y=1.02))
st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# Curva di durata (load duration curve)
# ---------------------------------------------------------------------------
st.subheader("Curva di durata del carico")
st.caption("Potenza richiesta ordinata dalla più alta alla più bassa: indica per quante ore/anno serve ciascun livello di potenza — utile per dimensionare la base load vs i picchi.")
durata = agg_total.sort_values("MWh", ascending=False).reset_index(drop=True)
durata["ore"] = durata.index + 1
fig_durata = px.area(durata, x="ore", y="MWh", labels={"ore": "Ore/anno", "MWh": "MW"})
fig_durata.update_layout(height=350)
st.plotly_chart(fig_durata, use_container_width=True)

# ---------------------------------------------------------------------------
# Domanda mensile
# ---------------------------------------------------------------------------
st.subheader("Domanda mensile per cluster")
monthly = df.copy()
monthly["mese"] = monthly["datetime"].dt.month.map(lambda m: month_names[m-1])
monthly_agg = monthly.groupby(["mese", "cluster"])["MWh"].sum().reset_index()
monthly_agg["mese"] = pd.Categorical(monthly_agg["mese"], categories=month_names, ordered=True)
monthly_agg = monthly_agg.sort_values("mese")
fig_month = px.bar(monthly_agg, x="mese", y="MWh", color="cluster", barmode="stack")
fig_month.update_layout(height=350, xaxis_title="", yaxis_title="MWh")
st.plotly_chart(fig_month, use_container_width=True)

# ---------------------------------------------------------------------------
# Dettaglio per edificio (tabella)
# ---------------------------------------------------------------------------
with st.expander("Dettaglio per edificio"):
    detail = df.groupby(["edificio", "cluster", "tipologia"])["MWh"].sum().reset_index()
    detail = detail.sort_values("MWh", ascending=False).rename(columns={"MWh": "Energia periodo (MWh)"})
    st.dataframe(detail, use_container_width=True, hide_index=True)

st.caption(
    "Fonti: Google Sheet 'Utenze TLR Maniago' (De Blasio Associati / APE FVG), "
    "TRL_utenze_bioman.xlsx, stazione meteo Vivaro (ARPA FVG OSMER). "
    "Profili orari infra-giornalieri per tipologia sono assunzioni di partenza "
    "da calibrare con dati di misura reali quando disponibili."
)
