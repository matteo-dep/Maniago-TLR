"""
OFFERTA - ZML: profilo orario di calore di scarto disponibile
================================================================
Fonti: intervista ZML (note testuali) + foto schermo monitoraggio reale
(curva "T acqua a valle batterie", confermato ciclico, ~9-10 picchi/16h
di lavoro) + chiarimenti utente su orari reali di lavoro.

Assunzioni esplicite (da validare/affinare con dati di log reali quando
disponibili):
- Finestra operativa: 16h/giorno (2 turni), inizio variabile tra le 01:00
  e le 04:00 (modellato come uniforme in questo intervallo, per giorno)
- 9 o 10 cicli di fusione per finestra operativa (equiprobabili) ->
  periodo di ciclo ~1.6-1.8h
- Forma del ciclo: onda TRIANGOLARE tra Tmin=40°C e Tmax=65°C lato
  primario (ZML, "a valle batterie") - approssimazione di partenza,
  la forma vera (dal grafico) non e' simmetrica ma senza dati di log
  esportati non e' possibile digitalizzarla con precisione da una foto
- Scambio termico primario/secondario: pinch (Delta t di approccio) = 5°C
  costante -> T_mandata_rete(t) = T_primario(t) - 5
- T_ritorno rete fissata a 30°C (ampio margine di fattibilita' rispetto
  al Tmin del primario)
- Portata secondaria COSTANTE, dimensionata per eguagliare la potenza di
  picco del primario nel punto di massima resa (quando T_primario=65,
  T_mandata_rete=60): vedi calcolo sotto
- Giorni operativi: lun-ven, agosto ridotto (~50%), 2 settimane ferme a
  Natale (23/12 - 05/01)
- Fuori dalla finestra operativa: potenza disponibile = 0
"""
import pandas as pd
import numpy as np

np.random.seed(7)

RHO_CP = 1.163  # kWh/(m3*K) per acqua

# ---------------------------------------------------------------------------
# 1. Parametri primario (ZML)
# ---------------------------------------------------------------------------
T_MAX_PRIMARIO = 65.0
T_MIN_PRIMARIO = 40.0
FLOW_PRIMARIO = 170.0  # m3/h (media 160-180 dalle note ZML)
P_PEAK_PRIMARIO = FLOW_PRIMARIO * RHO_CP * (T_MAX_PRIMARIO - T_MIN_PRIMARIO)
print(f"Potenza di picco primario (ZML, Tmax-Tmin): {P_PEAK_PRIMARIO:.0f} kW")

# ---------------------------------------------------------------------------
# 2. Parametri secondario (rete)
# ---------------------------------------------------------------------------
PINCH = 5.0
T_RITORNO_RETE = 30.0
T_MANDATA_RETE_PICCO = T_MAX_PRIMARIO - PINCH  # 60°C
# portata secondaria dimensionata per uguagliare la potenza di picco del
# primario nel punto di massima resa
FLOW_SECONDARIO = P_PEAK_PRIMARIO / (RHO_CP * (T_MANDATA_RETE_PICCO - T_RITORNO_RETE))
print(f"Portata secondaria (assunzione, calibrata sul picco): {FLOW_SECONDARIO:.1f} m3/h")
print(f"Potenza minima teorica (Tmin primario, mandata rete {T_MIN_PRIMARIO-PINCH:.0f}°C): "
      f"{FLOW_SECONDARIO*RHO_CP*max(T_MIN_PRIMARIO-PINCH-T_RITORNO_RETE,0):.0f} kW")

# ---------------------------------------------------------------------------
# 3. Calendario operativo (anno tipo 2024, stesso calendario del lato domanda)
# ---------------------------------------------------------------------------
days_2024 = pd.date_range('2024-01-01', '2024-12-31', freq='D')

def is_operating_day(d):
    if d.weekday() >= 5:  # weekend
        return False
    # 2 settimane ferme a Natale: 23/12 - 05/01
    if (d.month == 12 and d.day >= 23) or (d.month == 1 and d.day <= 5):
        return False
    return True

# ---------------------------------------------------------------------------
# 4. Simulazione ad alta risoluzione (1 minuto) poi aggregazione oraria
# ---------------------------------------------------------------------------
minutes = pd.date_range('2024-01-01', '2025-01-01', freq='min', inclusive='left')
T_primario = np.zeros(len(minutes))
minute_of_day = (minutes.hour * 60 + minutes.minute).values
day_index = minutes.normalize()

# precalcolo per ogni giorno: e' operativo? a che ora inizia? quanti cicli?
unique_days = pd.date_range('2024-01-01', '2024-12-31', freq='D')
day_params = {}
for d in unique_days:
    if not is_operating_day(d):
        day_params[d] = None
        continue
    start_hour = np.random.uniform(1.0, 4.0)  # inizio tra le 01:00 e le 04:00
    duration_h = 16.0
    if d.month == 8:  # agosto ridotto
        duration_h *= 0.5
    n_cicli = np.random.choice([9, 10])
    period_h = duration_h / n_cicli
    day_params[d] = (start_hour, duration_h, period_h)

# costruzione onda triangolare minuto per minuto
df_min = pd.DataFrame({'datetime': minutes})
df_min['day'] = df_min['datetime'].dt.normalize()
df_min['hour_frac'] = df_min['datetime'].dt.hour + df_min['datetime'].dt.minute/60.0

T_arr = np.full(len(df_min), np.nan)
for d, params in day_params.items():
    if params is None:
        continue
    start_h, dur_h, period_h = params
    mask = (df_min['day'] == d).values
    hrs = df_min.loc[mask, 'hour_frac'].values
    # gestisco eventuale finestra che passa la mezzanotte (start 1-4, dur 16h -> fine 17-20, niente overflow)
    in_window = (hrs >= start_h) & (hrs < start_h + dur_h)
    phase = ((hrs - start_h) % period_h) / period_h  # 0..1 dentro il ciclo
    # onda triangolare: sale da Tmin a Tmax in meta' ciclo, poi scende
    tri = np.where(phase < 0.5,
                    T_MIN_PRIMARIO + (T_MAX_PRIMARIO - T_MIN_PRIMARIO) * (phase / 0.5),
                    T_MAX_PRIMARIO - (T_MAX_PRIMARIO - T_MIN_PRIMARIO) * ((phase - 0.5) / 0.5))
    vals = np.where(in_window, tri, 0.0)
    idx = np.where(mask)[0]
    T_arr[idx] = vals

df_min['T_primario'] = T_arr
df_min['operativo'] = df_min['T_primario'] > 0

df_min['T_mandata_rete'] = np.where(df_min['operativo'], df_min['T_primario'] - PINCH, np.nan)
df_min['P_kW'] = np.where(
    df_min['operativo'],
    FLOW_SECONDARIO * RHO_CP * np.clip(df_min['T_mandata_rete'] - T_RITORNO_RETE, 0, None),
    0.0
)

# ---------------------------------------------------------------------------
# 5. Aggregazione oraria
# ---------------------------------------------------------------------------
df_min['hour'] = df_min['datetime'].dt.floor('h')
hourly = df_min.groupby('hour').agg(
    P_media_kW=('P_kW', 'mean'),
    P_picco_kW=('P_kW', 'max'),
    T_mandata_media=('T_mandata_rete', 'mean'),
).reset_index().rename(columns={'hour': 'datetime'})
hourly['MWh'] = hourly['P_media_kW'] / 1000.0

hourly.to_csv('maniago_offerta_ZML_oraria.csv', index=False)
df_min.iloc[::5].to_csv('maniago_offerta_ZML_5min_dettaglio.csv', index=False)  # campione ogni 5 min per ispezione

print(f"\nEnergia annua disponibile (ZML, con questo modello): {hourly['MWh'].sum():.0f} MWh")
print(f"Potenza media oraria di picco: {hourly['P_media_kW'].max():.0f} kW")
print(f"Potenza istantanea di picco (risoluzione 1 min): {df_min['P_kW'].max():.0f} kW")
print(f"Ore/anno con disponibilita' > 0: {(hourly['P_media_kW']>0).sum()}")
print(f"\nConfronto con la stima flat precedente (9.449 MWh, 12h/giorno, DeltaT 35.3°C): "
      f"{hourly['MWh'].sum()/9449*100:.0f}% di quella")
