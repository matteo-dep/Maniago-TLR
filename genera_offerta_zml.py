# ---------------------------------------------------------------------------
# CALCOLI BILANCIO E GRAFICO 1: PROFILO ORARIO
# ---------------------------------------------------------------------------
st.subheader("Bilancio Termico: Analisi Copertura e Sprechi")

# 1. Aggreghiamo domanda e filtriamo ZML
domanda_totale = df.groupby("datetime")["MWh"].sum().reset_index()
domanda_totale.rename(columns={"MWh": "Domanda Reti (MWh)"}, inplace=True)

mask_off = (offerta_zml["datetime"].dt.date >= date_range[0]) & (offerta_zml["datetime"].dt.date <= date_range[1])
off_filtered = offerta_zml[mask_off].copy()
bilancio = pd.merge(domanda_totale, off_filtered[["datetime", "MWh_termici"]], on="datetime", how="left")
bilancio.rename(columns={"MWh_termici": "Offerta ZML (MWh)"}, inplace=True)

# 2. Calcolo logico delle nuove curve
# Calore effettivamente scambiato (il minimo tra quello che serve e quello disponibile)
bilancio["Calore_Usato_ZML"] = np.minimum(bilancio["Domanda Reti (MWh)"], bilancio["Offerta ZML (MWh)"])
# Quota mancante da integrare con caldaie di back-up
bilancio["Integrazione_Caldaie"] = np.maximum(0, bilancio["Domanda Reti (MWh)"] - bilancio["Offerta ZML (MWh)"])
# Calore che ZML deve continuare a dissipare in torre (Spreco)
bilancio["Calore_Dissipato_ZML"] = np.maximum(0, bilancio["Offerta ZML (MWh)"] - bilancio["Domanda Reti (MWh)"])

# 3. Disegniamo il grafico (Stacked Area per la domanda + Linea per lo spreco)
fig_bilancio = go.Figure()

# Area Verde: Quota coperta da ZML
fig_bilancio.add_trace(go.Scatter(
    x=bilancio["datetime"], y=bilancio["Calore_Usato_ZML"], 
    fill='tozeroy', mode='none', fillcolor='rgba(40, 167, 69, 0.7)', 
    name='Copertura ZML', stackgroup='one'
))
# Area Rossa: Quota integrata dalle caldaie (Si impila sopra ZML formando la curva della domanda totale)
fig_bilancio.add_trace(go.Scatter(
    x=bilancio["datetime"], y=bilancio["Integrazione_Caldaie"], 
    fill='tonexty', mode='none', fillcolor='rgba(215, 40, 40, 0.7)', 
    name='Integrazione Caldaie (Mancante)', stackgroup='one'
))
# Linea Grigia tratteggiata: Calore dissipato in aria da ZML
fig_bilancio.add_trace(go.Scatter(
    x=bilancio["datetime"], y=bilancio["Calore_Dissipato_ZML"], 
    mode='lines', line=dict(color='rgba(150, 150, 150, 0.8)', width=1, dash='dot'), 
    name='Calore Dissipato in Torre (Spreco ZML)'
))

fig_bilancio.update_layout(
    height=400, xaxis_title="Timeline", yaxis_title="Potenza Termica (MW)", 
    hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)
st.plotly_chart(fig_bilancio, use_container_width=True)

# ---------------------------------------------------------------------------
# KPI NUMERICI DEL PERIODO SELEZIONATO
# ---------------------------------------------------------------------------
tot_domanda = bilancio["Domanda Reti (MWh)"].sum()
tot_usato_zml = bilancio["Calore_Usato_ZML"].sum()
tot_integrato = bilancio["Integrazione_Caldaie"].sum()
tot_dissipato = bilancio["Calore_Dissipato_ZML"].sum()

if tot_domanda > 0:
    perc_copertura = (tot_usato_zml / tot_domanda) * 100
else:
    perc_copertura = 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("Domanda Totale", f"{tot_domanda:,.0f} MWh")
col2.metric("Coperto da ZML", f"{tot_usato_zml:,.0f} MWh", f"{perc_copertura:.1f}% della domanda", delta_color="normal")
col3.metric("Integrazione necessaria", f"{tot_integrato:,.0f} MWh")
col4.metric("Dissipato in Torre (ZML)", f"{tot_dissipato:,.0f} MWh")

# ---------------------------------------------------------------------------
# GRAFICO 2: COPERTURA MENSILE % E DOMANDA
# ---------------------------------------------------------------------------
st.markdown("---")
st.subheader("Copertura ZML mese per mese")

bilancio["mese_num"] = bilancio["datetime"].dt.month
month_names = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu", "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]
bilancio["mese"] = bilancio["mese_num"].map(lambda m: month_names[m-1])

# Raggruppiamo i dati mensilmente
monthly_bil = bilancio.groupby(["mese", "mese_num"])[["Domanda Reti (MWh)", "Calore_Usato_ZML", "Integrazione_Caldaie"]].sum().reset_index()
monthly_bil = monthly_bil.sort_values("mese_num")
monthly_bil["% Copertura"] = (monthly_bil["Calore_Usato_ZML"] / monthly_bil["Domanda Reti (MWh)"] * 100).fillna(0)

# Grafico a barre impilate (ZML + Integrazione) e testo della percentuale
fig_month_bil = px.bar(
    monthly_bil, x="mese", y=["Calore_Usato_ZML", "Integrazione_Caldaie"], 
    title="Composizione Mensile dell'Energia",
    labels={"value": "Energia (MWh)", "variable": "Fonte"},
    color_discrete_map={"Calore_Usato_ZML": "#28a745", "Integrazione_Caldaie": "#dc3545"}
)

# Aggiungiamo le etichette di testo col % di copertura in cima ad ogni barra
fig_month_bil.add_trace(go.Scatter(
    x=monthly_bil["mese"], y=monthly_bil["Domanda Reti (MWh)"] + 50,
    text=monthly_bil["% Copertura"].apply(lambda x: f"{x:.1f}%"),
    mode='text', textposition='top center', showlegend=False
))

fig_month_bil.update_layout(height=400, xaxis_title="", yaxis_title="MWh", barmode='stack')
st.plotly_chart(fig_month_bil, use_container_width=True)
