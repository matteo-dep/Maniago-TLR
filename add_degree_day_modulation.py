"""
Modulazione su gradi-giorno (HDD) - Maniago TLR
=================================================
AGGIORNAMENTO: usa ora la serie di temperatura REALE della stazione di Vivaro
(stazione di riferimento ufficiale per Maniago, confermato dal PAES comunale),
anno 2011 (anno meteorologicamente piu' rappresentativo tra il 2007-2025,
GG piu' vicino alla media pluriennale, tra gli anni completi senza buchi).

La serie e' corretta con un fattore "delta" (scala moltiplicativa sullo scarto
rispetto a 20°C) per allinearla ai 2.850 GG ufficiali di Maniago (Vivaro e'
strutturalmente piu' mite: 2.649 GG medi 2007-2025 contro 2.850 di Maniago,
coerente con la sua posizione in pianura aperta rispetto alla pedemontana).

Questo sostituisce il precedente modello sintetico (rumore autoregressivo):
ora la variabilita' giorno-per-giorno, le ondate di freddo e la loro
autocorrelazione sono REALI (misure ARPA FVG OSMER), non piu' simulate.
"""
import pandas as pd
import numpy as np

# ---------------------------------------------------------------------------
# 1. Temperatura giornaliera REALE (Vivaro 2011, corretta verso Maniago 2850 GG)
# ---------------------------------------------------------------------------
temp_real = pd.read_csv('maniago_temperatura_giornaliera_REALE_2011.csv', parse_dates=['date'])
# rimappo l'anno 2011 (reale) sul calendario 2024 usato nel resto della pipeline,
# allineando mese/giorno (29 feb 2011 non esiste: la gestiamo duplicando il 28 feb)
days_2024 = pd.date_range('2024-01-01', '2024-12-31', freq='D')
temp_real = temp_real.set_index(temp_real['date'].dt.strftime('%m-%d'))
lookup = temp_real['Tmed_maniago'].to_dict()
T_daily = np.array([lookup.get(d.strftime('%m-%d'), lookup.get('02-28')) for d in days_2024])

days = days_2024
month_of_day = days.month
T_BASE_GG = 20.0

temp_df = pd.DataFrame({'date': days, 'T_mean': T_daily, 'month': month_of_day})
temp_df['HDD'] = (T_BASE_GG - temp_df['T_mean']).clip(lower=0)
print(f"GG anno tipo (calendario 2024, dati reali Vivaro 2011 corretti): {temp_df['HDD'].sum():.0f}")
print(f"Temperatura minima: {T_daily.min():.1f}°C il {days[T_daily.argmin()].strftime('%d/%m')}")

temp_df.to_csv('maniago_temperatura_giornaliera_tipo.csv', index=False)

# ---------------------------------------------------------------------------
# 2. Split base/heating load per edificio dai dati mensili gia' costruiti
# ---------------------------------------------------------------------------
monthly_all = pd.read_csv('maniago_domanda_mensile_MWh_TUTTI_edifici.csv', index_col=0)
monthly_all.index = list(range(1, 13))  # 1..12

SUMMER_MONTHS = [6, 7, 8]
base_load = {}
heating_load = pd.DataFrame(index=monthly_all.index, columns=monthly_all.columns, dtype=float)
for b in monthly_all.columns:
    summer_avg = monthly_all.loc[SUMMER_MONTHS, b].mean()
    base_load[b] = summer_avg  # stesso valore ogni mese
    heating_load[b] = (monthly_all[b] - summer_avg).clip(lower=0)
    # ridistribuisco l'eventuale scarto (mesi estivi sotto la media, o differenza
    # di arrotondamento) mantenendo il totale annuo invariato
    residual = monthly_all[b].sum() - (base_load[b]*12 + heating_load[b].sum())
    heating_load[b] += residual / 12  # piccola correzione uniforme

print("\nBase load (non termodipendente, MWh/mese) - alcuni esempi:")
for b in ['Piscina','Caserme','ISIS + IPSIA Torricelli','Municipio/Comune']:
    print(f"  {b}: {base_load[b]:.2f} MWh/mese ({base_load[b]*12/monthly_all[b].sum()*100:.0f}% del totale annuo)")

# ---------------------------------------------------------------------------
# 3. Forme orarie (riprese identiche dalla fase precedente)
# ---------------------------------------------------------------------------
def make_shape(weekday_hint, weekend_hint):
    wd = np.array(weekday_hint, dtype=float); wd /= wd.sum()
    we = np.array(weekend_hint, dtype=float); we /= we.sum()
    return wd, we

HOURLY_SHAPES = {
    'scuola': make_shape(
        [0.3,0.3,0.3,0.3,0.3,0.5,1.5,3.5,4.5,4.5,4.3,4.0,3.0,3.8,4.0,3.5,2.0,0.8,0.5,0.4,0.3,0.3,0.3,0.3],
        [0.6]*24),
    'uffici': make_shape(
        [0.3,0.3,0.3,0.3,0.3,0.4,1.0,2.5,4.0,4.3,4.3,4.0,3.5,4.0,4.3,4.0,3.5,2.0,1.0,0.5,0.4,0.3,0.3,0.3],
        [0.6]*24),
    'caserma': make_shape(
        [3.0,2.8,2.7,2.7,2.8,3.2,4.0,4.5,4.5,4.3,4.2,4.2,4.2,4.2,4.2,4.2,4.3,4.5,4.5,4.2,3.8,3.5,3.2,3.0],
        [3.2,3.0,2.9,2.9,3.0,3.3,3.8,4.2,4.3,4.3,4.3,4.3,4.3,4.3,4.3,4.3,4.3,4.3,4.3,4.2,4.0,3.7,3.5,3.3]),
    'sportivo': make_shape(
        [1.0,1.0,1.0,1.0,1.0,1.0,1.5,1.5,1.5,1.5,1.5,2.0,2.0,1.5,1.5,2.0,3.0,5.5,6.5,6.0,4.5,2.5,1.5,1.0],
        [1.5,1.5,1.5,1.5,1.5,1.5,2.0,2.5,3.5,4.5,5.0,5.5,5.5,5.0,4.5,4.5,4.5,4.5,4.0,3.5,2.5,2.0,1.5,1.5]),
    'piscina': make_shape(
        [2.5,2.5,2.5,2.5,2.5,3.0,4.0,4.5,4.5,4.5,4.5,4.5,4.5,4.5,4.5,4.5,4.5,5.0,5.0,4.5,3.5,3.0,2.5,2.5],
        [2.5,2.5,2.5,2.5,2.5,3.0,4.0,4.5,5.0,5.0,5.0,5.0,4.8,4.8,4.8,4.8,4.8,4.8,4.5,4.0,3.5,3.0,2.5,2.5]),
}

buildings = pd.read_csv('maniago_domanda_edifici.csv').set_index('edificio')
TYPOLOGY_TO_HOURLY_CAT = {
    'Scuola': 'scuola', 'Scuola infanzia': 'scuola', 'Scuola superiore': 'scuola',
    'Uffici pubblici': 'uffici', 'Cultura': 'uffici', 'Cultura/Uffici pubblici': 'uffici',
    'Deposito/magazzino': 'uffici', 'Sociale/assistenziale': 'uffici',
    'Sociale/assistenziale (RSA)': 'caserma', 'Caserma': 'caserma', 'Sportivo': 'sportivo',
}
PISCINA_NAME = 'Piscina'

# ---------------------------------------------------------------------------
# 4. Ricostruzione oraria (8760h) con energia giornaliera VARIABILE (HDD-based)
# ---------------------------------------------------------------------------
hours_2024 = pd.date_range('2024-01-01', '2024-12-31 23:00', freq='h')
temp_df_idx = temp_df.set_index('date')

records = []
for name in monthly_all.columns:
    tipologia = buildings.loc[name, 'tipologia']
    cluster = buildings.loc[name, 'cluster']
    cat = 'piscina' if name == PISCINA_NAME else TYPOLOGY_TO_HOURLY_CAT.get(tipologia, 'uffici')
    wd_shape, we_shape = HOURLY_SHAPES[cat]

    # energia giornaliera per l'edificio, mese per mese
    daily_energy = pd.Series(index=days, dtype=float)
    for m in range(1, 13):
        mask = temp_df_idx['month'] == m if False else (temp_df['month'] == m).values
        hdd_month = temp_df.loc[mask, 'HDD']
        hdd_sum = hdd_month.sum()
        n_days_month = mask.sum()
        base_daily = base_load[name] / n_days_month
        if hdd_sum > 0:
            heat_daily = heating_load.loc[m, name] * (hdd_month.values / hdd_sum)
        else:
            heat_daily = np.zeros(n_days_month)
        daily_energy.iloc[np.where(mask)[0]] = base_daily + heat_daily

    df_h = pd.DataFrame({'datetime': hours_2024})
    df_h['date'] = df_h['datetime'].dt.floor('D')
    df_h['hour'] = df_h['datetime'].dt.hour
    df_h['is_weekend'] = df_h['datetime'].dt.weekday >= 5
    df_h['E_day'] = df_h['date'].map(daily_energy)

    shape_lookup_wd = {h: wd_shape[h] for h in range(24)}
    shape_lookup_we = {h: we_shape[h] for h in range(24)}
    frac = np.where(df_h['is_weekend'], df_h['hour'].map(shape_lookup_we), df_h['hour'].map(shape_lookup_wd))
    df_h['MWh'] = df_h['E_day'].values * frac

    df_h['edificio'] = name
    df_h['cluster'] = cluster
    df_h['tipologia'] = tipologia
    records.append(df_h[['datetime','edificio','cluster','tipologia','MWh']])

hourly_all = pd.concat(records, ignore_index=True)
hourly_all.to_csv('maniago_domanda_oraria_8760h_HDD_reale.csv', index=False)

check2 = hourly_all.groupby('edificio')['MWh'].sum().round(1)
target = buildings['consumo_annuo_MWh'].round(1)
diff = (check2 - target).abs()
print("\nMax scostamento vs consumo annuo dichiarato (MWh):", diff.max())

cluster_hourly = hourly_all.groupby(['datetime','cluster'])['MWh'].sum().unstack()
cluster_hourly.to_csv('maniago_domanda_oraria_per_cluster_HDD_reale.csv')

print("\nTotale annuo per cluster (MWh):")
print(cluster_hourly.sum().round(1))
print("\nPicco orario per cluster (MW) - CON modulazione HDD:")
print(cluster_hourly.max().round(3))
print("\nOra di picco per Ex Bioman:", cluster_hourly['Ex Bioman'].idxmax())
