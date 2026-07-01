import numpy as np
import pandas as pd

ANNO = 2024  # Allineato all'anno tipo della domanda
PORTATA_M3H = 160.0  # m3/h costanti reali da sopralluogo ZML
T_MANDATA_PICCO = 65.0  # Temperatura picco fusione (°C)
T_RITORNO_TLR = 40.0  # Ipotizzata ritorno rete TLR (°C)

# Calcolo Potenza di picco termica recuperabile (~4.65 MW)
CP_ACQUA = 4.186 / 3600  # MWh/(kg*K)
DELTA_T_MAX = T_MANDATA_PICCO - T_RITORNO_TLR
P_PICCO_MW = PORTATA_M3H * 1000 * CP_ACQUA * DELTA_T_MAX

# Generazione range orario 8760h
hours = pd.date_range(
    start=f"{ANNO}-01-01 00:00:00", end=f"{ANNO}-12-31 23:00:00", freq="h"
)
df_off = pd.DataFrame({"datetime": hours})
df_off["mese"] = df_off["datetime"].dt.month
df_off["giorno_sett"] = df_off["datetime"].dt.weekday  # 0=Lun, 6=Dom
df_off["ora"] = df_off["datetime"].dt.hour


# Applicazione regole del calendario industriale ZML
def calcola_potenza(row):
    if row["giorno_sett"] >= 5:
        return 0.0  # Spento weekend
    if row["mese"] == 8:
        return 0.0  # Chiuso ad Agosto
    if (row["mese"] == 1 and row["datetime"].day <= 6) or (
        row["mese"] == 12 and row["datetime"].day >= 22
    ):
        return 0.0  # 2 settimane stop Natale

    # Turno fusione: dalle 06:00 alle 22:00 (16 ore)
    if 6 <= row["ora"] < 22:
        # Oscillazione ciclica delle cariche batch delle due batterie (tra 35% e 100% del picco)
        frequenza_ciclo = 2 * np.pi / 3
        fattore = 0.675 + 0.325 * np.sin(row["ora"] * frequenza_ciclo)
        return P_PICCO_MW * fattore
    return 0.0


df_off["MWh_termici"] = df_off.apply(calcola_potenza, axis=1)
df_off["fonte"] = "ZML (Forni fusori)"
df_off["tipologia_offerta"] = "Cascame Industriale"

# Salvataggio del CSV richiesto dall'app
df_off[["datetime", "fonte", "tipologia_offerta", "MWh_termici"]].to_csv(
    "maniago_offerta_oraria_zml.csv", index=False
)
print("File 'maniago_offerta_oraria_zml.csv' generato con successo!")
