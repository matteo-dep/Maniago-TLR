"""
Maniago TLR - Domanda, Offerta, Dimensionamento e Confronto Scenari
========================================================================
Avvio: streamlit run provaTLRManiago.py

File richiesti nella stessa cartella (DATI GREZZI, stabili):
  - maniago_domanda_edifici.csv                  anagrafica edifici pubblici + zone private
  - maniago_domanda_oraria_8760h_HDD_reale.csv   domanda oraria (MWh_riscaldamento, MWh_ACS)
  - maniago_aziende_offerta.csv                  tabella generica aziende (potenza/T/portata/profilo)
  - pvgis_maniago_pulito.csv                     irraggiamento solare reale orario (PVGIS 2005-2023)
  - maniago_temperatura_giornaliera_tipo.csv     T_mean/HDD per giorno (anno tipo)
  - maniago_mappa_utenze.csv                     coordinate edifici/condomini/aziende per la mappa
  - maniago_condomini_con_domanda.csv            dettaglio condomini (via, zona, domanda stimata)
  - maniago_densita_lineare_per_cluster.csv      risultato calcolo densità lineare

Tutto il resto (offerta aziende/solare, accumulo, HP, caldaia, scenari, costi) è
CALCOLATO LIVE in questo unico file — nessun altro script o CSV di scenario.
Per aggiungere una nuova azienda: aggiungi una riga a maniago_aziende_offerta.csv.
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(page_title="Maniago TLR", layout="wide", page_icon="🔥")

# --- default degli slider forzati al primo avvio (evita che la cache di sessione
#     mantenga valori vecchi quando cambiano i default nel codice) ---
DEFAULTS_SLIDER = {
    "dom_t_mandata": 80,      # T mandata rete
    "dom_t_ritorno": 50,      # T ritorno rete
    "dim_volume": 800,        # volume accumulo tiepido
    "dim_vol_alta": 500,      # volume accumulo caldo (alta T)
    "dim_tmin_acc": 25,       # T minima utile evaporatore
}
def applica_default_slider(force=False):
    for k, v in DEFAULTS_SLIDER.items():
        if force or k not in st.session_state:
            st.session_state[k] = v
if "_init_done" not in st.session_state:
    applica_default_slider(force=True)
    st.session_state["_init_done"] = True

COLOR_RISCALDAMENTO = "#C0522D"
COLOR_ACS = "#2D7DC0"
COLOR_OFFERTA = "#3FA34D"
COLOR_ACCUMULO = "#8E5FC2"
COLOR_HP = "#2DA3A3"
COLOR_CALDAIA = "#B0413E"
COLOR_EX_BIOMAN = "#E63946"  # rosso acceso dedicato, sempre e solo per la zona ex Bioman

# --- Palette DISPATCH/COPERTURA: colori ben distinti tra loro (hue + luminosità) ---
COLOR_ALTA_T  = "#D62728"  # rosso      → scarto alta T usato diretto in rete
COLOR_SOLARE  = "#F2A900"  # ambra      → solare termico
# HP alta T usa COLOR_HP (#2DA3A3, teal)
COLOR_BACKUP  = "#3D5A80"  # blu navy   → tecnologia di supporto (gas/biomassa/HP bassa T)
COLOR_NONCOP  = "#B5B5B5"  # grigio     → domanda non coperta


def build_cluster_color_map(clusters_list):
    """Un solo colore solido per zona di rete: la zona 'ex Bioman' è sempre rossa,
    le altre pescano (senza ripetizioni) da una palette qualitativa ad alto contrasto."""
    palette = [c for c in (px.colors.qualitative.Set2 + px.colors.qualitative.Dark2)
               if c.lower() != COLOR_EX_BIOMAN.lower()]
    color_map, i = {}, 0
    for cl in clusters_list:
        if "bioman" in str(cl).lower():
            color_map[cl] = COLOR_EX_BIOMAN
        else:
            color_map[cl] = palette[i % len(palette)]
            i += 1
    return color_map


def hex_to_rgba(color, alpha=0.85):
    """Converte un colore hex (o rgb(...) plotly) in rgba con opacità fissa,
    per aree piene e leggibili invece che sfumate/anti-aliasate."""
    color = color.strip()
    if color.startswith("rgb"):
        nums = color[color.find("(") + 1: color.find(")")].split(",")
        r, g, b = (int(float(n)) for n in nums[:3])
    else:
        h = color.lstrip("#")
        r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


MONTH_NAMES = ["Gen","Feb","Mar","Apr","Mag","Giu","Lug","Ago","Set","Ott","Nov","Dic"]
RHO_CP = 1.163  # kWh/(m3*K)
HOURS_2024 = pd.date_range('2024-01-01', '2024-12-31 23:00', freq='h')
DAYS_2024 = pd.date_range('2024-01-01', '2024-12-31', freq='D')

# =============================================================================
# MOTORE OFFERTA (generico, da tabella aziende) — funzioni pure, nessuna UI qui
# =============================================================================


# =============================================================================
# MOTORE OFFERTA — una riga per FLUSSO (da maniago_flussi_offerta.csv)
# =============================================================================

def _giorni_chiusura_set(giorni_chiusura_annui, seed):
    """N giorni di chiusura nell'anno, concentrati a Natale/agosto (deterministico per seed)."""
    if not giorni_chiusura_annui or giorni_chiusura_annui <= 0:
        return set()
    rng = np.random.default_rng(seed)
    n = int(giorni_chiusura_annui)
    natale = pd.date_range('2024-12-20', '2024-12-31')
    agosto = pd.date_range('2024-08-05', '2024-08-25')
    n_natale = min(n // 2, len(natale))
    n_agosto = min(n - n_natale, len(agosto))
    chiusi = list(natale[:n_natale]) + list(agosto[:n_agosto])
    resto = n - len(chiusi)
    if resto > 0:
        altri = [d for d in DAYS_2024 if d not in chiusi]
        scelti = rng.choice(len(altri), size=min(resto, len(altri)), replace=False)
        chiusi += [altri[i] for i in scelti]
    return set(pd.Timestamp(d).normalize() for d in chiusi)


def genera_flusso(row, pinch=5.0, seed=0):
    """
    Profilo orario (MWh/h, T_disponibile °C) di un singolo flusso di scarto.
    P_kW è il picco nominale; il pattern temporale (profilo) lo modula ora per ora.
    """
    rng = np.random.default_rng(seed)
    P_nom = row['P_kW'] / 1000.0
    T_disp = row['T_alta_C'] - pinch
    profilo = row['profilo']
    giorni_sett = int(row['giorni_sett']) if not pd.isna(row.get('giorni_sett')) else 7
    chiusi = _giorni_chiusura_set(row.get('chiusura_gg', 0), seed)

    P = np.zeros(len(HOURS_2024))
    Td = np.full(len(HOURS_2024), np.nan)
    giorno_di = HOURS_2024.normalize()
    ora_di = HOURS_2024.hour

    for d in DAYS_2024:
        if d.weekday() >= giorni_sett or d in chiusi:
            continue
        mg = (giorno_di == d)

        if profilo == 'continuo':
            P[mg] = P_nom; Td[mg] = T_disp
        elif profilo == 'notturno_18_08':
            notte = mg & ((ora_di >= 18) | (ora_di < 8))
            P[notte] = P_nom; Td[notte] = T_disp
        elif profilo.startswith('ore_giorno_'):
            n_ore = int(profilo.split('_')[-1]); start = 6
            fascia = mg & (ora_di >= start) & (ora_di < start + n_ore)
            P[fascia] = P_nom; Td[fascia] = T_disp
        elif profilo == 'cf_random':
            cf = float(row['cf']) if not pd.isna(row.get('cf')) else 0.3
            idx_g = np.where(mg)[0]
            attive = rng.random(len(idx_g)) < cf
            P[idx_g[attive]] = P_nom; Td[idx_g[attive]] = T_disp
        elif profilo == 'ciclico_colate':
            n_cicli = int(rng.integers(int(row['cicli_min']), int(row['cicli_max']) + 1))
            idx_g = np.where(mg)[0]
            if len(idx_g) == 0:
                continue
            ore_op, start = 20, 2
            per_ciclo = ore_op / max(n_cicli, 1)
            for h_local in range(min(24, len(idx_g))):
                if h_local < start or h_local >= start + ore_op:
                    continue
                gi = idx_g[h_local]
                fase = ((h_local - start) % per_ciclo) / per_ciclo
                T_ist = row['T_alta_C'] - fase * (row['T_alta_C'] - row['T_out_C'])
                dT_ist = max(T_ist - row['T_out_C'], 0)
                dT_max = max(row['T_alta_C'] - row['T_out_C'], 1)
                P[gi] = P_nom * (dT_ist / dT_max)
                Td[gi] = T_ist - pinch
        else:
            P[mg] = P_nom; Td[mg] = T_disp

    return pd.DataFrame({'datetime': HOURS_2024, 'MWh': P, 'P_kW': P * 1000, 'T_disponibile': Td})


@st.cache_data
def load_data():
    buildings = pd.read_csv("maniago_domanda_edifici.csv")
    domanda = pd.read_csv("maniago_domanda_oraria_8760h_HDD_reale.csv", parse_dates=["datetime"])
    domanda = domanda.merge(buildings[["edificio", "cluster", "tipologia", "tipo_utenza"]], on="edificio", how="left")
    flussi = pd.read_csv("maniago_flussi_offerta.csv")
    flussi["id_flusso"] = flussi["azienda"] + " · " + flussi["flusso"]
    pvgis = pd.read_csv("pvgis_maniago_pulito.csv", parse_dates=["datetime"])
    return buildings, domanda, flussi, pvgis


@st.cache_data
def genera_offerta_flussi(flussi_df, pinch):
    """Genera i profili orari di tutti i flussi. Ritorna un df lungo con id_flusso, azienda, destinazione."""
    frames = []
    for i, row in flussi_df.iterrows():
        prof = genera_flusso(row, pinch=pinch, seed=i * 13 + 1)
        prof["id_flusso"] = row["id_flusso"]
        prof["azienda"] = row["azienda"]
        prof["flusso"] = row["flusso"]
        prof["destinazione"] = row["destinazione"]
        prof["fonte"] = row["azienda"]  # compatibilità con codice esistente che usa 'fonte'
        frames.append(prof[["datetime", "id_flusso", "azienda", "flusso", "destinazione", "fonte", "MWh", "P_kW", "T_disponibile"]])
    return pd.concat(frames, ignore_index=True)



@st.cache_data
def genera_offerta_solare(pvgis_df, area_m2, efficienza):
    pvgis_df = pvgis_df.copy()
    pvgis_df["hour"] = pvgis_df["datetime"].dt.hour
    profilo_tipo = pvgis_df.groupby(["month", "hour"])["G_totale"].mean().reset_index()
    profilo_tipo["P_kW"] = profilo_tipo["G_totale"] * area_m2 * efficienza / 1000
    df_h = pd.DataFrame({"datetime": HOURS_2024})
    df_h["month"] = df_h["datetime"].dt.month
    df_h["hour"] = df_h["datetime"].dt.hour
    df_h = df_h.merge(profilo_tipo[["month", "hour", "P_kW"]], on=["month", "hour"], how="left")
    df_h["MWh"] = df_h["P_kW"] / 1000
    df_h["fonte"] = "Solare termico"
    df_h["T_disponibile"] = np.nan  # il solare preriscalda il ritorno, non ha una "T disponibile" standalone
    return df_h[["datetime", "fonte", "MWh", "P_kW", "T_disponibile"]]


def simula_copertura(dom_s, off_s, capacity_mwh):
    """Dispatch greedy orario: offerta diretta + carica/scarica accumulo. Ritorna (coperta, sprecata)."""
    soc, covered, wasted = 0.0, 0.0, 0.0
    for o, d in zip(off_s.values, dom_s.values):
        direct = min(o, d)
        covered += direct
        d_res, o_res = d - direct, o - direct
        charge = min(o_res, capacity_mwh - soc)
        soc += charge
        wasted += (o_res - charge)
        discharge = min(d_res, soc)
        soc -= discharge
        covered += discharge
    return covered, wasted


def crf(rate, anni):
    """Capital Recovery Factor: quota annua di ammortamento del CAPEX a tasso r su n anni."""
    if anni <= 0:
        return 1.0
    if rate <= 0:
        return 1.0 / anni
    return rate / (1.0 - (1.0 + rate) ** (-anni))


def dispatch_orario(dom_arr, solare_arr, cap_accumulo_mwh, tecno_disp, potenze_kw):
    """
    Dispatch orario con merit order fisso su ciò che resta DOPO lo scarto industriale.
      dom_arr:    domanda residua oraria (MWh/h) da coprire — già al netto dello scarto utilizzabile
      solare_arr: produzione solare oraria (MWh/h), non dispacciabile (0 se solare non attivo)
      cap_accumulo_mwh: capacità accumulo
      tecno_disp: lista ordinata di tecnologie dispacciabili attive, es. ["Biomassa","Pompa di calore","Gas"]
      potenze_kw: dict {tecnologia: potenza installata kW}  (None/assente = illimitata)
    Ritorna: dict con energia annua per tecnologia, ore non coperte, energia non coperta,
             solare sprecato, e la serie oraria di produzione per ciascuna (per curve di durata).
    """
    n = len(dom_arr)
    soc = 0.0
    prod = {t: np.zeros(n) for t in (["Solare", "Accumulo"] + tecno_disp)}
    non_coperta = np.zeros(n)
    solare_sprecato = 0.0
    for i in range(n):
        residuo = dom_arr[i]
        # 1) solare (non dispacciabile): copre direttamente, surplus carica accumulo
        sol = solare_arr[i]
        uso_sol = min(sol, residuo)
        prod["Solare"][i] = uso_sol
        residuo -= uso_sol
        surplus_sol = sol - uso_sol
        carica = min(surplus_sol, cap_accumulo_mwh - soc)
        soc += carica
        solare_sprecato += (surplus_sol - carica)
        # 2) accumulo scarica
        scarica = min(residuo, soc)
        soc -= scarica
        prod["Accumulo"][i] = scarica
        residuo -= scarica
        # 3) dispacciabili in merit order (costo marginale crescente), con limite di potenza
        for t in tecno_disp:
            if residuo <= 0:
                break
            pmax = potenze_kw.get(t)
            erogabile = residuo if pmax is None else min(residuo, pmax / 1000.0)
            prod[t][i] = erogabile
            residuo -= erogabile
        non_coperta[i] = max(residuo, 0)
    return {
        "prod": prod,
        "energia": {t: prod[t].sum() for t in prod},
        "non_coperta_mwh": non_coperta.sum(),
        "ore_non_coperte": int((non_coperta > 1e-6).sum()),
        "solare_sprecato_mwh": solare_sprecato,
        "serie_non_coperta": non_coperta,
    }


def simula_accumulo_tiepido(dom_arr, scarto_pot_arr, scarto_T_arr, volume_m3,
                            T_min_acc, T_max_acc, dT_evaporatore,
                            P_hp_kw, cop_reale, P_gas_kw,
                            architettura="diretta",
                            backup_cop=None, backup_arr_max=None,
                            perdita_sett_pct=0.0, T_amb_acc=15.0,
                            cop_dinamico=False, T_mandata_cop=None, eta_hp_cop=None,
                            cop_min=2.0, cop_max=8.0, T_ritorno_rete=None):
    """
    Simulazione oraria dell'accumulo termico che disaccoppia scarto e HP.

    Due architetture (parametro `architettura`):
      - "diretta": accumulo TIEPIDO lato sorgente. La HP pesca dall'accumulo e manda
        DIRETTAMENTE in rete, seguendo la domanda ora per ora. L'accumulo assorbe la
        variabilità dello SCARTO. La HP deve avere potenza per seguire la domanda.
      - "carica_accumulo": la HP lavora VERSO l'accumulo caldo (a T mandata) a potenza
        piatta finché c'è scarto e capienza; la RETE scarica dall'accumulo. L'accumulo
        assorbe la variabilità della DOMANDA → la HP lavora più costante.

    Backup (parametro generico):
      - se backup_cop è None → backup termico puro (gas/biomassa): rende q_backup con
        potenza P_gas_kw, consumo combustibile = q/rendimento (gestito fuori nei costi)
      - se backup_cop è un numero → backup elettrico (2ª HP su ambiente): rende q_backup
        con COP=backup_cop, elettricità = q/backup_cop
      - backup_arr_max: profilo orario di potenza max backup (MWh/h) per fonti non
        dispacciabili come il solare; se None il backup è dispacciabile a P_gas_kw

    Ritorna dict con serie orarie ed energie annue aggregate. La chiave 'q_gas' /
    'E_gas' contiene sempre l'energia del BACKUP (qualunque tecnologia sia).
    """
    n = len(dom_arr)
    C_MWh_per_K = volume_m3 * RHO_CP / 1000.0
    T_acc = np.zeros(n)
    q_hp = np.zeros(n)
    q_gas = np.zeros(n)          # energia del backup (nome storico mantenuto)
    q_scarto_in = np.zeros(n)
    non_coperta = np.zeros(n)
    el_hp = np.zeros(n)
    el_backup = np.zeros(n)      # elettricità backup se è una 2ª HP
    scarto_perso = np.zeros(n)

    T = T_min_acc
    P_hp_mwh = P_hp_kw / 1000.0
    P_gas_mwh = P_gas_kw / 1000.0
    frac_da_sorgente = max(1.0 - 1.0 / cop_reale, 0.0) if cop_reale > 0 else 0.0
    # perdita oraria come frazione dell'energia stoccata (sopra T_amb): da %/settimana a /ora
    perdita_ora_frac = (perdita_sett_pct / 100.0) / 168.0 if perdita_sett_pct > 0 else 0.0
    perdite_acc = np.zeros(n)
    cop_serie = np.zeros(n)  # COP effettivo usato ogni ora
    Tmand_K = (T_mandata_cop + 273.15) if (cop_dinamico and T_mandata_cop is not None) else None

    for i in range(n):
        Ts = scarto_T_arr[i]
        scarto_disp = scarto_pot_arr[i]
        dom = dom_arr[i]
        # perdite di standby all'inizio dell'ora: raffreddano l'accumulo verso T_amb
        if perdita_ora_frac > 0 and C_MWh_per_K > 0 and T > T_amb_acc:
            persa = perdita_ora_frac * (T - T_amb_acc) * C_MWh_per_K
            T -= persa / C_MWh_per_K
            perdite_acc[i] = persa

        # Sorgente HP e COP dell'ora
        # Schema B (T_ritorno_rete valorizzato): la sorgente è il MIX tra ritorno rete e accumulo.
        #   Il ritorno rete è sempre disponibile (portata ~ domanda), l'accumulo aggiunge lo scarto.
        #   Peso: quota accumulo vs quota ritorno, in base a massa accumulo ed energia richiesta.
        if T_ritorno_rete is not None and (T_ritorno_rete > 0):
            # peso del ritorno cresce con la domanda dell'ora, quello dell'accumulo con la sua capacità
            w_ret = min(dom, P_hp_mwh) if P_hp_mwh > 0 else dom
            w_acc = max((T - T_min_acc) * C_MWh_per_K, 0.0) if C_MWh_per_K > 0 else 0.0
            wtot = w_ret + w_acc
            if wtot > 1e-9:
                T_sorg_base = (T_ritorno_rete * w_ret + T * w_acc) / wtot
            else:
                T_sorg_base = T_ritorno_rete
            # la sorgente non scende comunque sotto il ritorno rete (pavimento garantito)
            T_sorg_base = max(T_sorg_base, T_ritorno_rete)
        else:
            T_sorg_base = T  # schema A: sorgente = solo accumulo

        if cop_dinamico and Tmand_K is not None and eta_hp_cop is not None:
            T_sorg_i = T_sorg_base - dT_evaporatore
            cop_i = (Tmand_K / max(Tmand_K - (T_sorg_i + 273.15), 1.0)) * eta_hp_cop
            cop_i = min(max(cop_i, cop_min), cop_max)
        else:
            cop_i = cop_reale
        frac_i = max(1.0 - 1.0 / cop_i, 0.0) if cop_i > 0 else 0.0
        cop_serie[i] = cop_i

        if architettura == "carica_accumulo":
            # 1) la HP carica l'accumulo caldo usando lo scarto come sorgente, a potenza piatta
            #    finché c'è scarto disponibile e capienza nell'accumulo
            entrato = 0.0
            q_hp_i = 0.0
            if scarto_disp > 0 and not np.isnan(Ts) and P_hp_mwh > 0 and C_MWh_per_K > 0:
                capienza = max((T_max_acc - T) * C_MWh_per_K, 0.0)
                # la HP rende fino a P_hp; l'energia dalla sorgente è q*frac, limitata dallo scarto
                q_max_da_scarto = scarto_disp / frac_i if frac_i > 0 else np.inf
                q_hp_i = min(P_hp_mwh, capienza, q_max_da_scarto)
                entrato = q_hp_i * frac_i
                T += q_hp_i / C_MWh_per_K if C_MWh_per_K > 0 else 0.0  # tutto il calore reso va in accumulo
            q_scarto_in[i] = entrato
            scarto_perso[i] = max(scarto_disp - entrato, 0.0)
            q_hp[i] = q_hp_i
            el_hp[i] = q_hp_i / cop_i if cop_i > 0 else 0.0

            # 2) la RETE scarica dall'accumulo per coprire la domanda
            scaricabile = max((T - T_min_acc) * C_MWh_per_K, 0.0)
            da_accumulo = min(dom, scaricabile)
            T -= da_accumulo / C_MWh_per_K if C_MWh_per_K > 0 else 0.0
            residuo = dom - da_accumulo
        else:
            # architettura "diretta": accumulo tiepido lato sorgente
            entrato = 0.0
            if scarto_disp > 0 and not np.isnan(Ts) and Ts > T and C_MWh_per_K > 0:
                capienza = max((T_max_acc - T) * C_MWh_per_K, 0.0)
                entrato = min(scarto_disp, capienza)
                T += entrato / C_MWh_per_K
            q_scarto_in[i] = entrato
            scarto_perso[i] = max(scarto_disp - entrato, 0.0)

            q_hp_i = 0.0
            if dom > 0 and P_hp_mwh > 0 and cop_i > 0 and C_MWh_per_K > 0:
                if T_ritorno_rete is not None and T_ritorno_rete > 0:
                    # Schema B: il ritorno rete è sorgente sempre disponibile -> HP limitata solo dalla potenza.
                    # L'accumulo contribuisce con lo scarto captato; la HP attinge prima all'accumulo (se caldo),
                    # poi al ritorno rete per il resto.
                    q_hp_i = min(dom, P_hp_mwh)
                    # energia estratta dalla sorgente = q_hp_i * frac_i, prelevata prima dall'accumulo
                    q_evap_tot = q_hp_i * frac_i
                    da_accumulo = min(q_evap_tot, max((T - T_min_acc) * C_MWh_per_K, 0.0))
                    T -= da_accumulo / C_MWh_per_K if C_MWh_per_K > 0 else 0.0
                    # il resto (q_evap_tot - da_accumulo) viene dal ritorno rete, non tocca l'accumulo
                else:
                    # Schema A: sorgente = solo accumulo
                    estraibile = max((T - T_min_acc) * C_MWh_per_K, 0.0)
                    q_cond_max = estraibile / frac_i if frac_i > 0 else np.inf
                    q_hp_i = min(dom, P_hp_mwh, q_cond_max)
                    T -= q_hp_i * frac_i / C_MWh_per_K if C_MWh_per_K > 0 else 0.0
            q_hp[i] = q_hp_i
            el_hp[i] = q_hp_i / cop_i if cop_i > 0 else 0.0
            residuo = dom - q_hp_i

        # 3) BACKUP copre il residuo, fino alla sua potenza (o al profilo max se non dispacciabile)
        p_backup = P_gas_mwh
        if backup_arr_max is not None:
            p_backup = min(P_gas_mwh, backup_arr_max[i]) if P_gas_mwh > 0 else backup_arr_max[i]
        q_backup_i = min(max(residuo, 0.0), p_backup) if p_backup > 0 else 0.0
        q_gas[i] = q_backup_i
        if backup_cop is not None and backup_cop > 0:
            el_backup[i] = q_backup_i / backup_cop
        non_coperta[i] = max(residuo - q_backup_i, 0.0)
        T_acc[i] = T

    # COP medio pesato sull'energia termica resa dalla HP (SCOP di sistema)
    cop_medio = (q_hp.sum() / el_hp.sum()) if el_hp.sum() > 1e-9 else 0.0
    return {
        "T_acc": T_acc, "q_hp": q_hp, "q_gas": q_gas, "q_scarto_in": q_scarto_in,
        "el_hp": el_hp, "el_backup": el_backup, "non_coperta": non_coperta,
        "scarto_perso": scarto_perso, "cop_serie": cop_serie, "cop_medio": cop_medio,
        "E_hp": q_hp.sum(), "E_gas": q_gas.sum(), "E_scarto_captato": q_scarto_in.sum(),
        "E_el_hp": el_hp.sum(), "E_el_backup": el_backup.sum(),
        "E_non_coperta": non_coperta.sum(), "E_scarto_perso": scarto_perso.sum(),
        "E_perdite_acc": perdite_acc.sum(),
        "ore_non_coperte": int((non_coperta > 1e-6).sum()),
        "ore_hp_attiva": int((q_hp > 1e-6).sum()),
        "ore_gas_attivo": int((q_gas > 1e-6).sum()),
    }


def simula_accumulo_alta_T(dom_arr, scarto_alta_arr, volume_m3, T_mandata, T_ritorno,
                           perdita_sett_pct=1.0):
    """
    Accumulo caldo alimentato dai fumi ad alta T (già a T mandata via scambiatore).
    Copre la domanda DIRETTAMENTE (no HP). Ritorna quanto copre e la domanda residua.
    Capacità termica = volume × cp × (T_mandata − T_ritorno).
    """
    n = len(dom_arr)
    C_MWh_per_K = volume_m3 * RHO_CP / 1000.0 if volume_m3 > 0 else 0.0
    cap_max = C_MWh_per_K * max(T_mandata - T_ritorno, 1) if volume_m3 > 0 else 0.0
    perdita_ora = (perdita_sett_pct/100.0)/168.0 if perdita_sett_pct > 0 else 0.0

    carica = 0.0  # stato di carica (MWh sopra il livello di ritorno)
    q_diretta = np.zeros(n)   # calore dell'alta T che copre la domanda
    dom_residua = np.zeros(n)
    for i in range(n):
        if perdita_ora > 0 and carica > 0:
            carica -= perdita_ora * carica
        carica = min(carica + scarto_alta_arr[i], cap_max) if cap_max > 0 else scarto_alta_arr[i]
        # copre la domanda con quello che c'è (accumulo + flusso istantaneo se no accumulo)
        disponibile = carica if cap_max > 0 else scarto_alta_arr[i]
        coperto = min(dom_arr[i], disponibile)
        q_diretta[i] = coperto
        if cap_max > 0:
            carica -= coperto
        dom_residua[i] = dom_arr[i] - coperto
    return q_diretta, dom_residua


def ottimizza_scenario(dom_arr, scarto_tiep_arr, scartoT_arr, scarto_alta_arr, solar_avail,
                       T_mandata, T_ritorno, T_min_acc, dT_evap, eta_hp, prezzo_el,
                       capex_hp_func, capex_backup_kw, opex_backup_mwh, backup_cop,
                       costo_m3, capex_solare_fisso, fattore_crf, perdita_func):
    """
    Trova P_hp, potenza backup, V_accumulo_tiepido e V_accumulo_altaT che MINIMIZZANO
    il LCOH di sistema (costo annuo totale / domanda annua), garantendo copertura 100%.

    Strategia: la potenza di backup non è una variabile di griglia — per ogni (P_hp, V_tiepido,
    V_alta) si simula con backup ILLIMITATO (copertura sempre 100%) e si legge la punta oraria
    che il backup deve realmente coprire: quella è la potenza di backup minima. Così il vincolo
    di copertura 100% è sempre soddisfatto e P_backup è il minimo necessario.
    Ricerca coarse-to-fine; l'accumulo alta T entra solo se c'è scarto alta T.
    """
    dom_tot = float(dom_arr.sum())
    if dom_tot <= 0:
        return None
    picco_kw = float(dom_arr.max() * 1000.0)
    has_alta = float(scarto_alta_arr.sum()) > 1e-6

    # cache dello stadio alta T (dipende solo da V_alta): dom residua dopo alta T + solare
    _alta_cache = {}
    def _stadio_alta(v_alta):
        if v_alta not in _alta_cache:
            q_alta, dom_res = simula_accumulo_alta_T(dom_arr, scarto_alta_arr, v_alta,
                                                     T_mandata, T_ritorno, perdita_sett_pct=perdita_func(v_alta))
            q_sol = np.minimum(dom_res, solar_avail)
            _alta_cache[v_alta] = (float(q_alta.sum()), dom_res - q_sol, float(q_sol.sum()))
        return _alta_cache[v_alta]

    def _valuta(p_hp, v_tiep, v_alta):
        E_alta, dom_after, E_sol = _stadio_alta(v_alta)
        s = simula_accumulo_tiepido(
            dom_after, scarto_tiep_arr, scartoT_arr, v_tiep, T_min_acc, T_mandata, dT_evap,
            p_hp, 4.0, 1e9, architettura="diretta", backup_cop=backup_cop,
            perdita_sett_pct=perdita_func(v_tiep), cop_dinamico=True,
            T_mandata_cop=T_mandata, eta_hp_cop=eta_hp, T_ritorno_rete=T_ritorno)
        p_bk = float(s["q_gas"].max() * 1000.0)   # punta backup necessaria -> kW
        capex = (p_hp * capex_hp_func(p_hp) + p_bk * capex_backup_kw
                 + v_tiep * costo_m3 + v_alta * costo_m3 + capex_solare_fisso)
        opex = s["E_el_hp"] * prezzo_el + s["E_gas"] * opex_backup_mwh
        lcoh = (capex * fattore_crf + opex) / dom_tot
        return {"p_hp_kw": p_hp, "p_bk_kw": p_bk, "v_tiep": v_tiep, "v_alta": v_alta,
                "lcoh": lcoh, "E_alta": E_alta, "E_sol": E_sol, "E_hp": s["E_hp"], "E_gas": s["E_gas"],
                "cop_medio": s["cop_medio"],
                "quota_fer": (E_alta + E_sol + s["E_hp"]) / dom_tot * 100}

    v_alta_cands = [0.0, 500.0, 1000.0, 2000.0] if has_alta else [0.0]
    p_hp_cands = list(np.linspace(0.2, 1.0, 5) * picco_kw)
    v_tiep_cands = [0.0, 400.0, 800.0, 1500.0, 2500.0]

    best = None
    for v_alta in v_alta_cands:
        for p_hp in p_hp_cands:
            for v_tiep in v_tiep_cands:
                r = _valuta(p_hp, v_tiep, v_alta)
                if best is None or r["lcoh"] < best["lcoh"]:
                    best = r
    if best is None:
        return None
    # raffino P_hp e V_tiepido intorno al migliore (V_alta tenuto al valore ottimo grezzo)
    va = best["v_alta"]
    dph = 0.1 * picco_kw
    for p_hp in [best["p_hp_kw"] + d for d in (-2*dph, -dph, 0, dph, 2*dph)]:
        if p_hp <= 0:
            continue
        for v_tiep in [best["v_tiep"] + d for d in (-500, -250, 0, 250, 500)]:
            if v_tiep < 0:
                continue
            r = _valuta(p_hp, v_tiep, va)
            if r["lcoh"] < best["lcoh"]:
                best = r
    return best


buildings, domanda, flussi, pvgis = load_data()

st.title("🔥 Maniago TLR — Domanda, Offerta, Dimensionamento")
st.caption(
    "Anno tipo (calendario 2024) · Domanda: temperatura calibrata su dati reali stazione Vivaro "
    "(anno 2011, corretto verso i 2.850 GG ufficiali di Maniago) · Tutto calcolato live, un solo file."
)

tab_domanda, tab_offerta, tab_dimensionamento, tab_confronto = st.tabs(
    ["🏠 Domanda", "♻️ Offerta", "🧮 Dimensionamento", "📊 Confronto scenari"]
)

# =============================================================================
# TAB 1 - DOMANDA
# =============================================================================
with tab_domanda:
    col_filtri, col_contenuto = st.columns([1, 3])

    with col_filtri:
        st.markdown("#### 🌡️ Linea ideale di rete")
        T_mandata_ideale = st.slider("Mandata (°C)", 35, 95, key="dom_t_mandata",
                                      help="Temperatura obiettivo di mandata alla rete — influenza la scelta bassa/alta T")
        T_ritorno_ideale = st.slider("Ritorno (°C)", 20, 60, key="dom_t_ritorno",
                                      help="Temperatura di ritorno rete — è la sorgente co-primaria della HP (schema co-sorgente) e serve al calcolo pinch in Offerta")
        st.caption("Questi due valori guidano anche i calcoli in Offerta e Dimensionamento.")
        if st.button("↺ Ripristina default", key="btn_reset_default",
                     help="Riporta mandata/ritorno, volume accumulo e T minima ai valori predefiniti "
                          "(utile se la sessione ha memorizzato valori vecchi)"):
            applica_default_slider(force=True)
            st.rerun()

        st.markdown("#### Filtri")
        clusters = sorted(buildings["cluster"].unique())
        CLUSTER_COLORS = build_cluster_color_map(clusters)
        selected_clusters = [c for c in clusters if st.checkbox(c, value=True, key=f"dom_cl_{c}")]

        st.markdown("**Utenza**")
        pub_on = st.checkbox("Pubblico", value=True, key="dom_tu_pub")
        st.caption("Privato (potenziale tecnico, per zona):")
        zone_private = sorted(buildings.loc[buildings["tipo_utenza"] == "Privato (potenziale)", "edificio"].unique())
        selected_privati = [z for z in zone_private if st.checkbox(z.replace("Residenziale ", ""), value=False, key=f"dom_priv_{z}")]

        fattore_correzione = 100
        if selected_privati:
            fattore_correzione = st.slider(
                "Fattore di correzione privato (%)", 10, 100, 100, step=5, key="dom_priv_fattore",
                help="Il potenziale privato viene da un coefficiente GIS uniforme (~150 kWh/m²/anno, "
                     "vicino allo standard 'vecchio/non ristrutturato') che probabilmente sovrastima "
                     "il reale. Usa questo slider per testare scenari più prudenti."
            )

        st.markdown("**Componente**")
        show_risc = st.checkbox("Riscaldamento ambienti", value=True, key="dom_risc")
        show_acs = st.checkbox("Acqua calda sanitaria (ACS)", value=True, key="dom_acs")

        with st.expander("Tipologia edificio"):
            tipologie = sorted(buildings["tipologia"].unique())
            select_all_tip = st.checkbox("Tutte", value=True, key="dom_all_tip")
            selected_tip = st.multiselect("Filtra", tipologie, default=tipologie if select_all_tip else [],
                                           key="dom_tip", label_visibility="collapsed")

        month_range = st.select_slider(
            "Mesi", options=list(range(1, 13)), value=(1, 12),
            format_func=lambda m: MONTH_NAMES[m-1], key="dom_mesi"
        )

    mask_building = (buildings["cluster"].isin(selected_clusters)
                     & buildings["tipologia"].isin(selected_tip)
                     & (((buildings["tipo_utenza"] == "Pubblico") & pub_on)
                        | buildings["edificio"].isin(selected_privati)))
    selected_buildings = buildings.loc[mask_building, "edificio"].tolist()

    # salvo per la catena di ereditarietà (scheda Dimensionamento)
    st.session_state["_dom_edifici"] = selected_buildings
    st.session_state["_dom_zone"] = selected_clusters
    st.session_state["_dom_fattore_privato"] = fattore_correzione / 100.0
    st.session_state["_dom_ha_privati"] = len(selected_privati) > 0

    dom = domanda[domanda["edificio"].isin(selected_buildings)].copy()
    dom["month"] = dom["datetime"].dt.month
    dom = dom[(dom["month"] >= month_range[0]) & (dom["month"] <= month_range[1])]

    is_privato = dom["tipo_utenza"] == "Privato (potenziale)"
    fattore = fattore_correzione / 100.0
    dom.loc[is_privato, "MWh_riscaldamento"] = dom.loc[is_privato, "MWh_riscaldamento"] * fattore
    dom.loc[is_privato, "MWh_ACS"] = dom.loc[is_privato, "MWh_ACS"] * fattore

    with col_contenuto:
        if dom.empty or not (show_risc or show_acs):
            st.warning("Nessun dato da mostrare: controlla i filtri a sinistra.")
        else:
            dom["MWh_sel"] = 0.0
            if show_risc:
                dom["MWh_sel"] += dom["MWh_riscaldamento"]
            if show_acs:
                dom["MWh_sel"] += dom["MWh_ACS"]

            agg_total = dom.groupby("datetime")["MWh_sel"].sum().reset_index()
            agg_cluster = dom.groupby(["datetime", "cluster"])["MWh_sel"].sum().reset_index()
            agg_componente = dom.groupby("datetime")[["MWh_riscaldamento", "MWh_ACS"]].sum().reset_index()

            tot = agg_total["MWh_sel"].sum()
            picco = agg_total["MWh_sel"].max()
            ora_picco = agg_total.loc[agg_total["MWh_sel"].idxmax(), "datetime"]
            load_factor = tot / (picco * len(agg_total)) if picco > 0 else 0
            acs_tot = dom["MWh_ACS"].sum() if show_acs else 0.0

            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Energia nel periodo", f"{tot:,.0f} MWh".replace(",", "."))
            k2.metric("Picco orario", f"{picco:.3f} MW", help=f"il {ora_picco.strftime('%d/%m alle %H:00')}")
            k3.metric("Quota ACS", f"{(acs_tot/tot*100 if tot else 0):.0f}%",
                      help=f"{acs_tot:,.0f} MWh ACS su {tot:,.0f} MWh totali".replace(",", "."))
            k4.metric("Fattore di carico", f"{load_factor*100:.1f}%")

            fig = go.Figure()
            cluster_nel_grafico = [c for c in selected_clusters if c in agg_cluster["cluster"].unique()]
            for cl in cluster_nel_grafico:
                sub = agg_cluster[agg_cluster["cluster"] == cl]
                colore = CLUSTER_COLORS.get(cl, "#888888")
                fig.add_trace(go.Scatter(x=sub["datetime"], y=sub["MWh_sel"], mode="lines",
                                          name=cl, stackgroup="one",
                                          line=dict(width=0.6, color=colore),
                                          fillcolor=hex_to_rgba(colore, 0.85)))
            fig.update_layout(height=420, yaxis_title="MWh/h (≈ MW)", xaxis_title="",
                               legend=dict(orientation="h", yanchor="bottom", y=1.02))
            st.plotly_chart(fig, use_container_width=True)
            st.caption("Un solo colore per zona di rete (la zona ex Bioman è sempre in rosso). "
                       "Per il dettaglio riscaldamento/ACS vedi il bilancio mensile sotto.")

            view_mode = st.radio("Bilancio mensile per:", ["Cluster di rete", "Componente (risc./ACS)"],
                                  horizontal=True, key="dom_view")

            st.markdown("**Curva di durata**")
            durata = agg_total.sort_values("MWh_sel", ascending=False).reset_index(drop=True)
            durata["ore"] = durata.index + 1
            fig_d = px.area(durata, x="ore", y="MWh_sel", labels={"ore": "Ore/anno", "MWh_sel": "MW"})
            fig_d.update_traces(line_color=COLOR_RISCALDAMENTO)
            fig_d.update_layout(height=420)
            st.plotly_chart(fig_d, use_container_width=True)

            st.markdown("**Bilancio mensile**")
            monthly_dom = dom.copy()
            monthly_dom["mese"] = monthly_dom["datetime"].dt.month.map(lambda m: MONTH_NAMES[m-1])
            fig_m = go.Figure()
            if view_mode == "Cluster di rete":
                monthly_cl = monthly_dom.groupby(["mese", "cluster"])["MWh_sel"].sum().reset_index()
                monthly_cl["mese"] = pd.Categorical(monthly_cl["mese"], categories=MONTH_NAMES, ordered=True)
                monthly_cl = monthly_cl.sort_values("mese")
                for cl in selected_clusters:
                    sub = monthly_cl[monthly_cl["cluster"] == cl]
                    fig_m.add_trace(go.Bar(x=sub["mese"], y=sub["MWh_sel"], name=cl,
                                            marker_color=CLUSTER_COLORS[cl]))
            else:
                monthly_agg = monthly_dom.groupby("mese")[["MWh_riscaldamento", "MWh_ACS"]].sum().reset_index()
                monthly_agg["mese"] = pd.Categorical(monthly_agg["mese"], categories=MONTH_NAMES, ordered=True)
                monthly_agg = monthly_agg.sort_values("mese")
                if show_risc:
                    fig_m.add_trace(go.Bar(x=monthly_agg["mese"], y=monthly_agg["MWh_riscaldamento"],
                                            name="Riscaldamento", marker_color=COLOR_RISCALDAMENTO))
                if show_acs:
                    fig_m.add_trace(go.Bar(x=monthly_agg["mese"], y=monthly_agg["MWh_ACS"],
                                            name="ACS", marker_color=COLOR_ACS))
            fig_m.update_layout(barmode="stack", height=320, yaxis_title="MWh", xaxis_title="")
            st.plotly_chart(fig_m, use_container_width=True)

            with st.expander("Dettaglio per edificio (zone, tipologia, ACS separata)"):
                detail = dom.groupby(["edificio", "cluster", "tipologia"])[["MWh_riscaldamento", "MWh_ACS"]].sum()
                detail["Totale MWh"] = detail["MWh_riscaldamento"] + detail["MWh_ACS"]
                detail = detail.rename(columns={"MWh_riscaldamento": "Riscaldamento MWh", "MWh_ACS": "ACS MWh"})
                detail = detail.sort_values("Totale MWh", ascending=False).reset_index()
                st.dataframe(detail, use_container_width=True, hide_index=True)


# =============================================================================
# TAB 2 - OFFERTA
# =============================================================================
with tab_offerta:
    col_filtri2, col_contenuto2 = st.columns([1, 3])
    with col_filtri2:
        st.markdown("#### Parametri scambio")
        st.caption(f"T ritorno rete: **{T_ritorno_ideale}°C** (impostata in scheda Domanda)")
        pinch = st.slider("Pinch scambiatore (°C)", 2, 10, 5, key="off_pinch")

        st.markdown("#### Fonti — selezione per flusso")
        st.caption("Da `maniago_flussi_offerta.csv`. Di **default sono spuntati solo i flussi più "
                   "certi** — le torri evaporative di Pandolfo, ZML e Pietro Rosa. Attiva le altre "
                   "fonti/flussi quando vuoi valutarli. 🔴 = fumi alta T (rete diretta) · 🔵 = tiepido (via HP).")
        offerta = genera_offerta_flussi(flussi, pinch)

        # fonti "certe" spuntate all'avvio: torri evaporative di Pandolfo, ZML e Pietro Rosa
        FONTI_CERTE = {"Pandolfo", "ZML", "Pietro Rosa"}
        def _flusso_e_certo(azienda, flusso):
            return (azienda in FONTI_CERTE) and ("torr" in str(flusso).lower())

        selected_flussi = []
        for az in sorted(flussi["azienda"].unique()):
            flussi_az = flussi[flussi["azienda"] == az]
            az_ha_certi = any(_flusso_e_certo(az, fr["flusso"]) for _, fr in flussi_az.iterrows())
            az_on = st.checkbox(f"**{az}**", value=az_ha_certi, key=f"off_az_{az}")
            for _, fr in flussi_az.iterrows():
                icona = "🔴" if fr["destinazione"] == "alta_T" else "🔵"
                label = f"{icona} {fr['flusso']} ({fr['P_kW']/1000:.1f} MW, {fr['T_alta_C']:.0f}°C)"
                # il flusso è selezionabile solo se l'azienda è attiva; spuntato di default solo se "certo"
                fl_on = st.checkbox(label, value=_flusso_e_certo(az, fr["flusso"]),
                                    key=f"off_fl_{fr['id_flusso']}", disabled=not az_on)
                if az_on and fl_on:
                    selected_flussi.append(fr["id_flusso"])

        # 'fonti' selezionate = aziende che hanno almeno un flusso attivo (per compatibilità a valle)
        selected_fonti = sorted(set(
            flussi.loc[flussi["id_flusso"].isin(selected_flussi), "azienda"]
        ))
        st.session_state["_off_flussi"] = selected_flussi
        st.session_state["_off_fonti"] = selected_fonti
        st.session_state["_off_pinch"] = pinch
        month_range_o = st.select_slider(
            "Mesi", options=list(range(1, 13)), value=(1, 12),
            format_func=lambda m: MONTH_NAMES[m-1], key="off_mesi"
        )

    with st.expander("📋 Dettaglio flussi (dati grezzi)"):
        st.dataframe(flussi[["azienda", "flusso", "destinazione", "fluido", "T_alta_C",
                             "T_out_C", "P_kW", "profilo"]],
                     use_container_width=True, hide_index=True)
        st.caption(
            "Ogni riga è un flusso di scarto asportabile. **destinazione**: `alta_T` = fumi caldi "
            "(≥260°C) che via scambiatore caricano l'accumulo caldo e servono la rete direttamente, "
            "senza pompa di calore; `tiepido` = scarti a bassa T (acqua torri, compressori) che vanno "
            "all'accumulo tiepido e alla HP. La calcinazione sabbia (24 MW nominali, CF 30%) domina "
            "l'alta T: prova a deselezionarla per vedere il sistema senza di essa."
        )

    off = offerta[offerta["id_flusso"].isin(selected_flussi)].copy()
    off["month"] = off["datetime"].dt.month
    off = off[(off["month"] >= month_range_o[0]) & (off["month"] <= month_range_o[1])]

    with col_contenuto2:
        if off.empty:
            st.warning("Nessuna fonte selezionata.")
        else:
            agg_off_tot = off.groupby("datetime")["MWh"].sum().reset_index()
            agg_off_fonte = off.groupby(["datetime", "fonte"])["MWh"].sum().reset_index()

            tot_o = agg_off_tot["MWh"].sum()
            picco_o = agg_off_tot["MWh"].max()
            ore_disp = (agg_off_tot["MWh"] > 0).sum()

            k1, k2, k3 = st.columns(3)
            k1.metric("Energia disponibile nel periodo", f"{tot_o:,.0f} MWh".replace(",", "."))
            k2.metric("Picco orario (media)", f"{picco_o:.3f} MW")
            k3.metric("Ore/anno con disponibilità", f"{ore_disp:,}".replace(",", "."))

            fig_o = go.Figure()
            for f in selected_fonti:
                sub = agg_off_fonte[agg_off_fonte["fonte"] == f]
                fig_o.add_trace(go.Scatter(x=sub["datetime"], y=sub["MWh"], mode="lines",
                                            name=f, stackgroup="one", line=dict(width=0.5)))
            fig_o.update_layout(height=420, yaxis_title="MWh/h (≈ MW)", xaxis_title="",
                                 legend=dict(orientation="h", yanchor="bottom", y=1.02))
            st.plotly_chart(fig_o, use_container_width=True)

            with st.expander("Dettaglio per fonte"):
                detail_o = off.groupby("fonte")["MWh"].sum().reset_index().rename(columns={"MWh": "Energia periodo (MWh)"})
                st.dataframe(detail_o.sort_values("Energia periodo (MWh)", ascending=False),
                             use_container_width=True, hide_index=True)

    st.divider()
    st.markdown("#### 🌡️ Curva composita: energia disponibile per soglia di temperatura, per azienda")
    st.caption(
        f"Per ogni azienda le ore vengono ordinate dalla T più alta alla più bassa e l'energia viene "
        f"accumulata. Leggendo il grafico all'altezza della T richiesta ({T_mandata_ideale}°C, linea "
        f"rossa tratteggiata), l'ascissa indica **quanta energia annua puoi ottenere da quell'azienda "
        f"accettando solo temperature pari o superiori alla soglia** — l'energia oltre il punto in cui "
        f"la curva scende sotto la soglia richiede comunque un ausilio (HP/caldaia) per completare la "
        f"salita di temperatura."
    )
    off_temp = off[off["T_disponibile"].notna() & (off["P_kW"] > 0)]
    if not off_temp.empty:
        fig_comp = go.Figure()
        righe_riep = []
        for fid in selected_flussi:
            sub = off_temp[off_temp["id_flusso"] == fid].sort_values("T_disponibile", ascending=False)
            if sub.empty:
                continue
            cum_mwh = sub["MWh"].cumsum().values
            T_vals = sub["T_disponibile"].values
            dest = sub["destinazione"].iloc[0]
            nome = sub["flusso"].iloc[0]
            fig_comp.add_trace(go.Scatter(x=cum_mwh, y=T_vals, mode="lines",
                                           name=f"{'🔴' if dest=='alta_T' else '🔵'} {nome[:22]}",
                                           line=dict(width=2.0, shape="hv")))
            sopra = (sub["T_disponibile"] >= T_mandata_ideale)
            righe_riep.append({
                "Flusso": fid, "Destinazione": dest,
                f"Utilizzabile a T≥{T_mandata_ideale}°C (MWh/a)": round(sub.loc[sopra, "MWh"].sum()),
                "Fornita sotto soglia (MWh/a)": round(sub.loc[~sopra, "MWh"].sum()),
            })
        fig_comp.add_hline(y=T_mandata_ideale, line_dash="dot", line_color="red",
                            annotation_text=f"T mandata ideale ({T_mandata_ideale}°C)",
                            annotation_position="top left")
        fig_comp.update_layout(height=680, xaxis_title="Energia cumulata disponibile (MWh/anno)",
                                yaxis_title="Temperatura disponibile (°C)",
                                font=dict(size=14),
                                legend=dict(orientation="h", yanchor="bottom", y=1.02))
        st.plotly_chart(fig_comp, use_container_width=True)

        if righe_riep:
            riepilogo = pd.DataFrame(righe_riep).sort_values(
                f"Utilizzabile a T≥{T_mandata_ideale}°C (MWh/a)", ascending=False)
            st.dataframe(riepilogo, use_container_width=True, hide_index=True)
        st.caption(
            f"Sopra i {T_mandata_ideale}°C lo scarto è utilizzabile direttamente in rete (tipico dei flussi "
            f"🔴 alta T); sotto soglia serve la pompa di calore per alzarne la temperatura (flussi 🔵 tiepidi). "
            f"Il dispatch dei due accumuli è calcolato ora per ora nella scheda Dimensionamento."
        )
    else:
        st.info("Nessun flusso selezionato con dati di temperatura in questo periodo.")


# =============================================================================
# TAB 3 - DIMENSIONAMENTO (accumulo tiepido + HP + gas, simulazione oraria)
# =============================================================================
with tab_dimensionamento:
    st.markdown("### Dimensionamento: accumulo tiepido + pompa di calore + backup")
    st.caption(
        "Schema modellato: lo **scarto industriale** carica un **accumulo tiepido** (~40-45°C); la "
        "**pompa di calore** pesca da lì (sorgente calda e stabile → COP alto) e porta a T di mandata; "
        "il **gas** interviene solo quando l'accumulo è scarico. Simulazione oraria della temperatura "
        "dell'accumulo sulla domanda impostata nella scheda Domanda."
    )

    # -------------------------------------------------------------------------
    # A) Domanda e scarto disponibile — EREDITATI da Domanda e Offerta
    # -------------------------------------------------------------------------
    st.markdown("#### A) Domanda da coprire e scarto disponibile")

    # eredita da Domanda/Offerta se disponibili, altrimenti default sensati (non bloccare mai)
    edifici_dim = st.session_state.get("_dom_edifici")
    if not edifici_dim:
        edifici_dim = buildings.loc[buildings["tipo_utenza"] == "Pubblico", "edificio"].tolist()
    flussi_dim = st.session_state.get("_off_flussi")
    if not flussi_dim:
        flussi_dim = flussi["id_flusso"].tolist()

    eredita_ok = bool(st.session_state.get("_dom_edifici")) and bool(st.session_state.get("_off_flussi"))
    zone_dim = st.session_state.get("_dom_zone", [])
    if eredita_ok:
        st.caption(
            f"Sto usando **{len(edifici_dim)} edifici** dalle zone selezionate in Domanda "
            f"({', '.join(zone_dim) if zone_dim else '—'}) e **{len(flussi_dim)} flussi** "
            f"selezionati in Offerta, con mandata/ritorno **{T_mandata_ideale}/{T_ritorno_ideale}°C**. "
            f"Cambia le selezioni in quelle schede e questa si aggiorna di conseguenza."
        )
    else:
        st.info(
            f"Sto usando i **valori predefiniti** ({len(edifici_dim)} edifici pubblici, tutti i "
            f"{len(flussi_dim)} flussi). Apri le schede **Domanda** e **Offerta** per personalizzare."
        )

    # domanda: stessi edifici della Domanda, con il fattore di correzione privato applicato
    fattore_priv = st.session_state.get("_dom_fattore_privato", 1.0)
    dom_dim = domanda[domanda["edificio"].isin(edifici_dim)].copy()
    is_priv = dom_dim["tipo_utenza"] == "Privato (potenziale)"
    dom_dim.loc[is_priv, "MWh_riscaldamento"] *= fattore_priv
    dom_dim.loc[is_priv, "MWh_ACS"] *= fattore_priv
    dom_dim_series = dom_dim.groupby("datetime")[["MWh_riscaldamento", "MWh_ACS"]].sum().sum(axis=1)
    idx_h = dom_dim_series.index

    # scarto dai flussi selezionati, SEPARATO per destinazione (due accumuli)
    pinch_dim = st.session_state.get("_off_pinch", 5.0)
    offerta_dim = genera_offerta_flussi(flussi, pinch_dim)
    off_all = offerta_dim[offerta_dim["id_flusso"].isin(flussi_dim)].copy()

    # ALTA T: fumi caldi -> accumulo caldo -> rete diretta (nessuna HP)
    off_alta = off_all[off_all["destinazione"] == "alta_T"]
    scarto_alta = off_alta.groupby("datetime")["MWh"].sum().reindex(idx_h, fill_value=0)

    # TIEPIDO: scarti bassa T -> accumulo tiepido -> HP
    off_tiep = off_all[off_all["destinazione"] == "tiepido"]
    scarto_tiep = off_tiep.groupby("datetime")["MWh"].sum().reindex(idx_h, fill_value=0)
    off_tv = off_tiep[off_tiep["T_disponibile"].notna() & (off_tiep["MWh"] > 0)].copy()
    off_tv["Tw"] = off_tv["T_disponibile"] * off_tv["MWh"]
    num = off_tv.groupby("datetime")["Tw"].sum().reindex(idx_h)
    den = off_tv.groupby("datetime")["MWh"].sum().reindex(idx_h)
    scarto_T = num / den

    scarto_arr = scarto_tiep.values          # alimenta la HP (accumulo tiepido)
    scartoT_arr = scarto_T.values
    scarto_alta_arr = scarto_alta.values     # copre la domanda direttamente (accumulo caldo)
    dom_arr = dom_dim_series.values

    cA1, cA2, cA3, cA4 = st.columns(4)
    cA1.metric("Domanda annua", f"{dom_dim_series.sum():,.0f} MWh".replace(",", "."))
    cA2.metric("🔴 Scarto alta T (rete diretta)", f"{scarto_alta.sum():,.0f} MWh".replace(",", "."),
               help="Fumi caldi via scambiatore: coprono la domanda senza HP né gas")
    cA3.metric("🔵 Scarto tiepido (→ HP)", f"{scarto_tiep.sum():,.0f} MWh".replace(",", "."),
               help="Scarti a bassa T: la pompa di calore li solleva a mandata")
    cA4.metric("Picco domanda", f"{dom_dim_series.max():.2f} MW")
    st.caption(
        "I due flussi vanno in **due accumuli separati** (per non degradare l'exergia dei fumi caldi "
        "mescolandoli col tiepido): l'alta T copre la domanda direttamente, il tiepido passa dalla HP. "
        "Il gas interviene solo quando entrambi sono scarichi."
    )

    # -------------------------------------------------------------------------
    # A-ter) FOTO INIZIALE: copertura dello scarto sulla domanda, con le temperature
    # -------------------------------------------------------------------------
    st.markdown("##### 🌡️ Copertura dello scarto sulla domanda (con le temperature)")

    # split orario dello scarto per adeguatezza di temperatura rispetto alla mandata
    _oh = off_all.copy()
    dir_h = (_oh.loc[_oh["T_disponibile"] >= T_mandata_ideale]
             .groupby("datetime")["MWh"].sum().reindex(idx_h, fill_value=0))
    src_hp_h = (_oh.loc[_oh["T_disponibile"].notna() & (_oh["T_disponibile"] < T_mandata_ideale)]
                .groupby("datetime")["MWh"].sum().reindex(idx_h, fill_value=0))

    # COP nominale (solo per questa foto): converte lo scarto tiepido-sorgente in calore reso in rete
    T_src_med = float(np.nanmedian(scartoT_arr[np.isfinite(scartoT_arr)])) if np.isfinite(scartoT_arr).any() else float(T_ritorno_ideale)
    lift_diag = max(T_mandata_ideale - T_src_med, 1.0)
    cop_diag = float(np.clip((T_mandata_ideale + 273.15) / lift_diag * 0.5, 2.5, 7.0))
    reso_hp_h = src_hp_h / (1.0 - 1.0 / cop_diag)   # calore reso in rete dalla HP

    tab_dur, tab_heat = st.tabs(["📉 Curva di durata", "🗺️ Heatmap T × tempo"])

    with tab_dur:
        st.caption(
            f"Ore ordinate dalla domanda più alta alla più bassa. Sotto la curva della domanda, quanto lo "
            f"**scarto** riesce a coprire: in **verde** ciò che è già a T≥mandata ({T_mandata_ideale}°C) e va "
            f"diretto in rete, in **teal** ciò che la **HP** solleva (COP nominale {cop_diag:.1f}). Il vuoto tra "
            f"le aree e la linea nera è la **punta** che resta a backup/accumulo."
        )
        order = np.argsort(dom_arr)[::-1]
        dem_s = dom_arr[order]
        dir_cov = np.minimum(dem_s, dir_h.values[order])
        hp_cov = np.minimum(dem_s - dir_cov, reso_hp_h.values[order])
        x = np.arange(1, len(dem_s) + 1)
        fig_dur = go.Figure()
        fig_dur.add_trace(go.Scatter(x=x, y=dir_cov, mode="lines", name="Scarto diretto (T≥mandata)",
                                     stackgroup="cov", line=dict(width=0, color=COLOR_OFFERTA),
                                     fillcolor=hex_to_rgba(COLOR_OFFERTA, 0.85)))
        fig_dur.add_trace(go.Scatter(x=x, y=hp_cov, mode="lines", name="Scarto via HP (T<mandata)",
                                     stackgroup="cov", line=dict(width=0, color=COLOR_HP),
                                     fillcolor=hex_to_rgba(COLOR_HP, 0.8)))
        fig_dur.add_trace(go.Scatter(x=x, y=dem_s, mode="lines", name="Domanda",
                                     line=dict(color="black", width=1.6)))
        fig_dur.update_layout(height=430, xaxis_title="Ore/anno (ordinate per domanda decrescente)",
                              yaxis_title="MW", legend=dict(orientation="h", yanchor="bottom", y=1.02),
                              margin=dict(t=30, b=10))
        st.plotly_chart(fig_dur, use_container_width=True)
        E_dir = float(dir_cov.sum()); E_hp_pot = float(hp_cov.sum()); E_dom = float(dem_s.sum()) or 1.0
        E_unc = max(E_dom - E_dir - E_hp_pot, 0)
        cS1, cS2, cS3 = st.columns(3)
        cS1.metric("Coperto diretto", f"{E_dir/E_dom*100:.0f}%",
                   help=f"{E_dir:,.0f} MWh a T≥mandata".replace(",", "."))
        cS2.metric("Coperto via HP", f"{E_hp_pot/E_dom*100:.0f}%",
                   help=f"{E_hp_pot:,.0f} MWh sollevati dalla HP".replace(",", "."))
        cS3.metric("Resta alla punta", f"{E_unc/E_dom*100:.0f}%",
                   help=f"{E_unc:,.0f} MWh da backup/accumulo".replace(",", "."))
        st.caption("È un tetto **teorico** (HP a potenza illimitata, nessun accumulo): il dimensionamento "
                   "reale, con potenze e accumuli finiti, è nei blocchi sotto.")

    with tab_heat:
        st.caption(
            f"Energia di scarto (MWh) disponibile per mese e per temperatura. La riga rossa è la **mandata "
            f"({T_mandata_ideale}°C)**: sopra, lo scarto è usabile **diretto**; sotto, serve la **HP**. "
            f"Mostra *quando* e *a che T* arriva il calore rispetto a quando serve."
        )
        _h = off_all[off_all["MWh"] > 0].copy()
        if _h.empty:
            st.info("Nessuno scarto disponibile con le fonti selezionate.")
        else:
            _h["mese"] = _h["datetime"].dt.month
            bins = [0, 30, 40, 50, 60, 70, 80, 100, 150, 2000]
            labels = ["<30", "30-40", "40-50", "50-60", "60-70", "70-80", "80-100", "100-150", "≥150"]
            _h["fascia"] = pd.cut(_h["T_disponibile"], bins=bins, labels=labels, right=False)
            piv = (_h.pivot_table(index="fascia", columns="mese", values="MWh", aggfunc="sum", observed=False)
                   .reindex(index=labels).reindex(columns=range(1, 13)).fillna(0))
            fig_hm = go.Figure(go.Heatmap(
                z=piv.values, x=[MONTH_NAMES[m-1] for m in piv.columns], y=labels,
                colorscale="YlOrRd", colorbar=dict(title="MWh"),
                hovertemplate="%{x} · %{y}°C: %{z:.0f} MWh<extra></extra>"))
            try:
                idx_band = next(i for i in range(len(labels)) if bins[i] <= T_mandata_ideale < bins[i+1])
                fig_hm.add_hline(y=idx_band - 0.5, line_color="red", line_width=2,
                                 annotation_text=f"mandata {T_mandata_ideale}°C", annotation_position="top left")
            except StopIteration:
                pass
            fig_hm.update_layout(height=430, xaxis_title="", yaxis_title="Temperatura scarto (°C)",
                                 margin=dict(t=30, b=10))
            st.plotly_chart(fig_hm, use_container_width=True)

    # -------------------------------------------------------------------------
    # A-bis) OTTIMIZZAZIONE AUTOMATICA dello scenario (HP + supporto + 2 accumuli)
    # -------------------------------------------------------------------------
    st.markdown("##### ⚙️ Ottimizzazione automatica dello scenario")
    st.caption(
        "A **fonti fissate** (quelle scelte in Offerta), cerca la configurazione a **LCOH minimo** che "
        "copre il **100% della domanda**: dimensiona la **HP primaria** sullo scarto, la **potenza di "
        "supporto** (la tecnologia scelta nel blocco D), e **entrambi gli accumuli** (tiepido e alta T). "
        "Il solare è incluso se spuntato nel blocco D. Le taglie trovate diventano il punto di partenza "
        "degli slider sotto — che puoi comunque ritoccare."
    )
    picco_dim_kw = float(dom_dim_series.max() * 1000)

    # CAPEX HP e costo accumulo coerenti col contesto scelto nelle schede (default Sud Europa/Italia)
    _hp_ctx = st.session_state.get("dim_hp_contesto", "Sud Europa / Italia")
    _hp_pts = {"Sud Europa / Italia": [(1, 340), (3, 300), (10, 220)],
               "Nord Europa": [(1, 1240), (3, 860), (10, 670)]}.get(_hp_ctx, [(1, 340), (3, 300), (10, 220)])

    def _capex_hp_opt(pot_kw):
        p_mw = max(pot_kw / 1000.0, 0.1)
        if p_mw <= _hp_pts[0][0]: return _hp_pts[0][1]
        if p_mw >= _hp_pts[-1][0]: return _hp_pts[-1][1]
        for (p0, c0), (p1, c1) in zip(_hp_pts, _hp_pts[1:]):
            if p0 <= p_mw <= p1:
                return c0 + (np.log(p_mw) - np.log(p0)) / (np.log(p1) - np.log(p0)) * (c1 - c0)
        return _hp_pts[-1][1]

    # costo accumulo €/m³: Sud Europa/Italia ~1000 (F1 Tab.3, <5000 m³), Nord Europa ~150 (F1 Tab.2)
    _acc_ctx = st.session_state.get("dim_contesto_acc", "Sud Europa / Italia (più alto)")
    _costo_m3_opt = 150.0 if "Nord" in _acc_ctx else 1000.0

    # tecnologia di supporto e solare: presi da quanto scelto nel blocco D (rerun precedente)
    _tech = st.session_state.get("dim_backup_tipo", "Caldaia (gas)")
    _sol_on = st.session_state.get("dim_solare_on", True)
    if _tech == "Caldaia (gas)":
        _bk_capex, _bk_opex, _bk_cop = 120.0, 90.0 / 0.92, None
    elif _tech == "HP bassa T (aria/ambiente)":
        _bk_cop = (T_mandata_ideale + 273.15) / max(T_mandata_ideale - 10, 1) * 0.40
        _bk_capex, _bk_opex = 700.0, 180.0 / _bk_cop
    else:  # Biomassa (cippato)
        _bk_capex, _bk_opex, _bk_cop = 550.0, 35.0 / 0.85, None

    # solare (baseline = ACS estiva) se spuntato in D
    _solar_avail = np.zeros(len(dom_arr)); _capex_solare = 0.0; _area_sol_opt = 0
    if _sol_on:
        _acs = dom_dim.groupby("datetime")["MWh_ACS"].sum().reindex(idx_h, fill_value=0)
        _est = idx_h.month.isin([6, 7, 8])
        _acs_est = float(_acs[_est].sum())
        _pref = genera_offerta_solare(pvgis, 1000.0, 0.30).groupby("datetime")["MWh"].sum().reindex(idx_h, fill_value=0)
        _pref_est = float(_pref[_est].sum())
        _area_base = (_acs_est / _pref_est * 1000.0) if _pref_est > 1e-6 else 2000.0
        _quota = st.session_state.get("dim_quota_sol", 100)
        _eff = st.session_state.get("dim_eff_sol", 30) / 100.0
        _area_sol_opt = int(round(_area_base * (_quota / 100.0) * (0.30 / max(_eff, 0.01))))
        _solar_avail = genera_offerta_solare(pvgis, _area_sol_opt, _eff).groupby("datetime")["MWh"].sum().reindex(idx_h, fill_value=0).values
        _capex_solare = _area_sol_opt * st.session_state.get("dim_capex_sol", 450)

    _perdita_opt = (lambda v: float(np.interp(np.log(np.clip(v, 500, 5000)),
                    [np.log(500), np.log(5000)], [2.0, 1.0])) if v > 0 else 0.0)

    colopt1, colopt2 = st.columns([1, 2])
    colopt1.caption(f"Supporto: **{_tech}** · Solare: **{'sì' if _sol_on else 'no'}**"
                    + (f" ({_area_sol_opt} m²)" if _sol_on else ""))
    if colopt1.button("🔎 Ottimizza scenario", key="dim_btn_ottimizza"):
        with st.spinner("Ricerca della configurazione a LCOH minimo (copertura 100%)..."):
            best = ottimizza_scenario(
                dom_arr, scarto_arr, scartoT_arr, scarto_alta_arr, _solar_avail,
                float(T_mandata_ideale), float(T_ritorno_ideale), 25, 5, 0.5, 180,
                _capex_hp_opt, _bk_capex, _bk_opex, _bk_cop,
                _costo_m3_opt, _capex_solare, crf(0.04, 20), _perdita_opt)
        if best:
            hp_opt = int(round(best["p_hp_kw"] / 100) * 100)
            bk_opt = int(round(best["p_bk_kw"] / 100) * 100)
            vt_opt = int(round(best["v_tiep"] / 100) * 100)
            va_opt = int(round(best["v_alta"] / 100) * 100)
            st.session_state["_opt_hp_kw"] = hp_opt
            st.session_state["_opt_gas_kw"] = bk_opt
            st.session_state["dim_pot_hp"] = hp_opt
            _key_bk = {"Caldaia (gas)": "dim_pot_gas", "HP bassa T (aria/ambiente)": "dim_pot_hp2",
                       "Biomassa (cippato)": "dim_pot_bio"}.get(_tech, "dim_pot_gas")
            st.session_state[_key_bk] = bk_opt
            st.session_state["dim_volume"] = vt_opt
            st.session_state["dim_vol_alta"] = va_opt
            st.session_state["_opt_result"] = best
            st.rerun()
        else:
            st.session_state["_opt_result"] = None
            st.warning("Ottimizzazione non riuscita: verifica che ci siano domanda e scarto selezionati.")

    opt_res = st.session_state.get("_opt_result")
    if opt_res:
        with colopt2:
            o1, o2, o3, o4 = st.columns(4)
            o1.metric("HP primaria", f"{opt_res['p_hp_kw']:.0f} kW",
                      help=f"{opt_res['p_hp_kw']/picco_dim_kw*100:.0f}% del picco domanda")
            o2.metric("Supporto", f"{opt_res['p_bk_kw']:.0f} kW",
                      help="potenza minima per coprire la punta residua")
            o3.metric("Acc. tiepido", f"{opt_res['v_tiep']:.0f} m³")
            o4.metric("Acc. alta T", f"{opt_res['v_alta']:.0f} m³",
                      help="0 se non ci sono flussi alta T selezionati")
        oo1, oo2, oo3 = colopt2.columns(3)
        oo1.metric("LCOH minimo", f"{opt_res['lcoh']:.1f} €/MWh")
        oo2.metric("Quota FER", f"{opt_res['quota_fer']:.0f}%", help=f"COP medio HP {opt_res['cop_medio']:.2f}")
        oo3.metric("HP su energia", f"{opt_res['E_hp']/(opt_res['E_hp']+opt_res['E_gas']+opt_res['E_alta']+opt_res['E_sol'])*100:.0f}%")
        colopt2.caption("✅ Configurazione impostata negli slider sotto (100% coperto). "
                        "Se cambi fonti, tecnologia di supporto o solare, rilancia l'ottimizzazione.")

    st.divider()
    st.markdown("#### B) Accumuli termici (due: caldo per l'alta T, tiepido per la HP)")
    st.caption(
        f"Mandata/ritorno **{T_mandata_ideale}/{T_ritorno_ideale}°C**. **Accumulo caldo** (a T mandata): "
        f"caricato dai fumi 🔴, serve la rete diretta. **Accumulo tiepido** (~{T_ritorno_ideale}°C): "
        f"caricato dagli scarti 🔵, la HP lo solleva a mandata. Tenerli separati evita di degradare "
        f"l'exergia dei fumi caldi mescolandoli col tiepido (IEA DHC F1: serbatoi in serie idraulica)."
    )
    architettura = "diretta"
    T_max_acc = float(T_mandata_ideale)  # accumulo tiepido: cima vincolata alla mandata

    cB1, cB2, cB3 = st.columns(3)
    volume_alta_T = cB1.slider("🔴 Volume accumulo CALDO (m³)", 0, 4000, step=100, key="dim_vol_alta",
                               help="Immagazzina i fumi caldi per disaccoppiarli dalla domanda. "
                                    "0 = i fumi coprono solo la domanda istantanea, senza buffer.")
    volume_accumulo = cB2.slider("🔵 Volume accumulo TIEPIDO (m³)", 0, 4000, step=100, key="dim_volume",
                                 help="Buffer per lo scarto tiepido che alimenta la HP")
    T_min_acc = cB3.slider("T minima utile evaporatore (°C)", 10, int(T_max_acc)-5,
                           key="dim_tmin_acc",
                           help="Soglia FISICA dell'evaporatore HP, NON la T di ritorno rete. È la temperatura "
                                "minima della sorgente sotto cui la HP non riesce più a estrarre calore utile "
                                "dall'accumulo e subentra il backup. Tipicamente 20-30°C.")
    dT_evap = st.slider("ΔT evaporatore HP (°C)", 3, 10, 5, key="dim_dt_evap",
                        help="Salto che la HP sottrae al fluido dell'accumulo a ogni passaggio")
    st.caption(
        f"⚠️ **T minima utile ({T_min_acc}°C) ≠ T ritorno rete ({T_ritorno_ideale}°C)**: sono grandezze "
        f"diverse. La T minima è il limite dell'evaporatore della HP; il ritorno rete è dove torna l'acqua "
        f"dagli edifici. **Schema attivo (co-sorgente)**: la HP pesca da un mix tra il ritorno rete "
        f"({T_ritorno_ideale}°C, sempre disponibile) e l'accumulo caricato dallo scarto. Così la HP non si "
        f"ferma mai per accumulo scarico e il COP resta sostenuto. **Conseguenza**: lo scarto più freddo del "
        f"ritorno ({T_ritorno_ideale}°C) viene recuperato poco — se hai fonti a bassa T (es. 30-40°C), "
        f"abbassare il ritorno rete le renderebbe più utili."
    )

    # numero indicativo di serbatoi in serie (taglio pratico ~2000 m³/serbatoio per TTES)
    VOL_MAX_SERBATOIO = 2000
    if volume_accumulo > VOL_MAX_SERBATOIO:
        n_serbatoi = int(np.ceil(volume_accumulo / VOL_MAX_SERBATOIO))
        st.caption(f"➜ {volume_accumulo} m³ ≈ **{n_serbatoi} serbatoi in serie** da ~{volume_accumulo//n_serbatoi} m³ ciascuno "
                   f"(un singolo TTES supera raramente ~2000 m³).")

    cAC1, cAC2 = st.columns(2)
    contesto_costo = cAC1.radio("Contesto costi accumulo", ["Nord Europa (100-200 €/m³)", "Sud Europa / Italia (più alto)"],
                                key="dim_contesto_acc", horizontal=False, index=1,
                                help="IEA DHC F1: TTES >2000 m³ costa 100-200 €/m³ in Nord Europa (Tab.2); nel Sud "
                                     "Europa (Tab.3) il factsheet indica ~1000 €/m³ per serbatoi <5000 m³. "
                                     "Maniago è in Italia → default Sud Europa.")
    default_costo_acc = 150 if "Nord" in contesto_costo else 1000
    max_costo_acc = 400 if "Nord" in contesto_costo else 1500
    costo_m3_accumulo = cAC2.slider("CAPEX accumulo (€/m³)", 80, max_costo_acc, default_costo_acc, step=20,
                                    key="dim_costo_accumulo",
                                    help="Serbatoio acqua isolato (IEA DHC F1 Tab.3, Sud Europa <5000 m³ ≈ 1000 €/m³) "
                                         "— DA VALIDARE con fornitore")

    # perdite accumulo dai valori IEA DHC F1: ~2%/settimana a 500 m³, ~1%/settimana a 5000 m³
    if volume_accumulo > 0:
        v = np.clip(volume_accumulo, 500, 5000)
        perdita_sett_pct = np.interp(np.log(v), [np.log(500), np.log(5000)], [2.0, 1.0])
    else:
        perdita_sett_pct = 0.0
    st.caption(
        f"Perdite di standby stimate (IEA DHC F1): **~{perdita_sett_pct:.1f}%/settimana** per {volume_accumulo} m³ "
        f"(2%/sett a 500 m³ → 1%/sett a 5000 m³). Già considerate nel dispatch orario."
    )

    # -------------------------------------------------------------------------
    # C) Pompa di calore
    # -------------------------------------------------------------------------
    st.divider()
    st.markdown("#### C) Pompa di calore")
    cC1, cC2, cC3 = st.columns(3)
    _max_hp = int(dom_dim_series.max() * 1000) + 500
    if "dim_pot_hp" not in st.session_state:
        st.session_state["dim_pot_hp"] = min(int(st.session_state.get("_opt_hp_kw", 1000)), _max_hp)
    pot_hp_kw = cC1.slider("Potenza termica HP (kW)", 0, _max_hp, step=100, key="dim_pot_hp",
                           help="Dimensionala perché lavori il più costante possibile: guarda 'ore HP attiva' sotto. "
                                "Rif. IEA DHC F6: le grandi HP si dimensionano spesso a ~50% del picco e coprono ~80% dell'energia. "
                                "Se hai usato l'ottimizzazione automatica, parte dal valore ottimo.")
    eta_hp = cC2.slider("Efficienza di 2° principio η (%)", 30, 60, 50, key="dim_hp_eta",
                        help="η di Lorentz. IEA DHC F6 e QM Handbook: valori reali 40-60% per HP industriali di qualità.") / 100
    prezzo_el = cC3.slider("Prezzo elettricità (€/MWh)", 80, 350, 180, step=10, key="dim_prezzo_el")

    # CAPEX HP dai factsheet IEA DHC F6: due contesti.
    #   Nord Europa (Tab.1, excess heat @25°C): 1 MW->1240, 3->860, 10->670 €/kW
    #   Sud Europa/Italia (Tab.2, excess heat/low-lift waste heat, dati UNIPD/POLIMI/Turboden):
    #       ~340 (1 MW) -> ~300 (3 MW) -> ~220 (10 MW) €/kW  (nettamente più bassi)
    _HP_PTS = {"Sud Europa / Italia": [(1, 340), (3, 300), (10, 220)],
               "Nord Europa": [(1, 1240), (3, 860), (10, 670)]}

    def capex_hp_factsheet(pot_kw, contesto="Sud Europa / Italia"):
        p_mw = max(pot_kw / 1000.0, 0.1)
        pts = _HP_PTS.get(contesto, _HP_PTS["Sud Europa / Italia"])
        if p_mw <= pts[0][0]:
            return pts[0][1]
        if p_mw >= pts[-1][0]:
            return pts[-1][1]
        for (p0, c0), (p1, c1) in zip(pts, pts[1:]):
            if p0 <= p_mw <= p1:
                f = (np.log(p_mw) - np.log(p0)) / (np.log(p1) - np.log(p0))
                return c0 + f * (c1 - c0)
        return pts[-1][1]

    hp_contesto = st.radio("Contesto costi HP", list(_HP_PTS.keys()), key="dim_hp_contesto",
                           horizontal=True,
                           help="IEA DHC F6: la Tab.2 Sud Europa (dati italiani UNIPD/POLIMI/Turboden per "
                                "HP su calore di scarto) riporta CAPEX ~2-3× più bassi del Nord Europa. "
                                "Maniago è in Italia → default Sud Europa.")
    cHP1, cHP2 = st.columns([1, 2])
    usa_default_fs = cHP1.checkbox("CAPEX da factsheet (per taglia)", value=True, key="dim_hp_capex_fs",
                                   help="Usa i valori IEA DHC F6 interpolati sulla potenza scelta")
    default_capex_hp = int(round(capex_hp_factsheet(pot_hp_kw, hp_contesto)))
    if usa_default_fs:
        capex_kw_hp = default_capex_hp
        cHP2.metric("CAPEX HP (€/kW termico)", f"{capex_kw_hp} €/kW",
                    help=f"Da IEA DHC F6 ({hp_contesto}) per ~{pot_hp_kw/1000:.1f} MW su calore di scarto.")
    else:
        capex_kw_hp = cHP2.slider("CAPEX HP (€/kW termico)", 150, 1400, default_capex_hp, step=50,
                                  key="dim_capex_hp", help="Regolabile manualmente")

    # COP: sorgente = T media accumulo, target = T mandata rete
    T_sorgente_hp = (T_min_acc + T_max_acc) / 2.0
    T_target_hp = T_mandata_ideale
    cop_carnot = (T_target_hp + 273.15) / max((T_target_hp - T_sorgente_hp), 1)
    cop_reale = cop_carnot * eta_hp  # valore "medio nominale" (sulla T media accumulo)
    lift = T_target_hp - T_sorgente_hp
    # riferimento QM Handbook: lift 30K->6.5, 40K->4.5, 60K->3.5
    if lift <= 30:
        cop_rif = 6.5
    elif lift <= 40:
        cop_rif = 6.5 + (lift - 30) / 10 * (4.5 - 6.5)
    elif lift <= 60:
        cop_rif = 4.5 + (lift - 40) / 20 * (3.5 - 4.5)
    else:
        cop_rif = 3.5

    cop_dinamico = st.checkbox(
        "COP dinamico orario", value=True, key="dim_cop_dinamico",
        help="Se attivo, il COP è ricalcolato ogni ora sulla temperatura reale dell'accumulo in quell'istante "
             "(più alto quando l'accumulo è caldo, più basso quando è quasi scarico). Dà un consumo elettrico "
             "e un LCOH più accurati. Se spento, usa un COP fisso sulla T media dell'accumulo."
    )

    cCOP1, cCOP2, cCOP3 = st.columns(3)
    if cop_dinamico:
        cCOP1.metric("COP nominale (T media)", f"{cop_reale:.2f}",
                     help="Riferimento sulla T media accumulo. Quello effettivo varia ora per ora — vedi COP medio nei risultati.")
    else:
        cCOP1.metric("COP reale (fisso)", f"{cop_reale:.2f}", help=f"Carnot {cop_carnot:.1f} × η {eta_hp:.0%}")
    cCOP2.metric("Salita di temperatura (lift medio)", f"{T_sorgente_hp:.0f}→{T_target_hp:.0f}°C ({lift:.0f}K)",
                 help="Sul valore medio dell'accumulo; con COP dinamico il lift reale oscilla ora per ora")
    cCOP3.metric("COP di riferimento (QM Handbook)", f"~{cop_rif:.1f}",
                 help=f"Per un lift di {lift:.0f}K, macchine reali di qualità danno ~{cop_rif:.1f} "
                      f"(QM Handbook: 30K→6-7, 40K→4-5, 60K→3-4).")
    st.caption(
        f"Sorgente = accumulo (media {T_sorgente_hp:.0f}°C, oscilla tra {T_min_acc}-{T_max_acc}°C) → mandata {T_target_hp}°C. "
        + ("**COP dinamico attivo**: ricalcolato ogni ora sulla T dell'accumulo, il COP medio effettivo comparirà nei risultati. "
           if cop_dinamico else "**COP fisso** sulla T media. ")
        + "⚠️ Questo è un COP **istantaneo/nominale**: i fattori di prestazione **stagionali** (SPF) di grandi HP su "
          "calore di scarto sono più bassi (AGFW 2021 / Exergy Pass: ~2,9 a 90°C di mandata, ~4,3 a 65°C, con ausiliari "
          "e perdite). Per l'energia/OPEX annui conviene un η prudente (~45%)."
    )

    # -------------------------------------------------------------------------
    # D) Backup e integrazione — HP alta T è primaria; qui scegli chi la affianca
    #    + integrazione solare termico ADDITIVA (sopra qualunque combinazione)
    # -------------------------------------------------------------------------
    st.divider()
    st.markdown("#### D) Backup e integrazione")
    st.caption(
        "La **HP alta T** (scheda C) è la tecnologia primaria in tutti gli scenari. Qui scegli la "
        "tecnologia che la **affianca sul residuo** (quando accumulo + HP non bastano) e, in modo "
        "indipendente, quanta **integrazione solare termico** aggiungere. Cambia una cosa alla volta e "
        "salva gli scenari nella scheda Confronto per metterli a paragone."
    )

    backup_tipo = st.radio(
        "Combinazione:  HP alta T +",
        ["Caldaia (gas)", "HP bassa T (aria/ambiente)", "Biomassa (cippato)"],
        key="dim_backup_tipo", horizontal=True,
        help="La HP alta T resta primaria in tutti i casi; cambia solo la tecnologia di supporto sul picco."
    )

    backup_cop = None          # None = backup termico; numero = backup elettrico (HP bassa T)
    opex_backup_unitario = 0.0 # €/MWh di calore reso dal backup
    capex_backup = 0.0

    if backup_tipo == "Caldaia (gas)":
        cD1, cD2, cD3 = st.columns(3)
        _max_gas = int(dom_dim_series.max()*1000)+1000
        if "dim_pot_gas" not in st.session_state:
            st.session_state["dim_pot_gas"] = min(int(st.session_state.get("_opt_gas_kw", 2000)), _max_gas)
        pot_gas_kw = cD1.slider("Potenza caldaia (kW)", 0, _max_gas, step=100, key="dim_pot_gas",
                                help="Se hai usato l'ottimizzazione automatica, parte dal valore ottimo.")
        rend_gas = cD2.slider("Rendimento (%)", 85, 98, 92, key="dim_rend_gas") / 100
        prezzo_gas = cD3.slider("Prezzo gas (€/MWh termico)", 40, 160, 90, key="dim_prezzo_gas")
        capex_kw_gas = st.slider("CAPEX (€/kW)", 60, 300, 120, step=10, key="dim_capex_gas")
        capex_backup = pot_gas_kw * capex_kw_gas
        opex_backup_unitario = prezzo_gas / rend_gas if rend_gas > 0 else 0
        pot_backup_kw = pot_gas_kw
        backup_label = f"Caldaia gas {pot_gas_kw} kW"

    elif backup_tipo == "HP bassa T (aria/ambiente)":
        cD1, cD2, cD3 = st.columns(3)
        pot_backup_kw = cD1.slider("Potenza termica (kW)", 0, int(dom_dim_series.max()*1000)+1000, 2000,
                                   step=100, key="dim_pot_hp2")
        T_amb = cD2.slider("T sorgente ambiente (°C)", 0, 20, 10, key="dim_hp2_tamb")
        eta_hp2 = cD3.slider("η 2° principio (%)", 30, 60, 40, key="dim_hp2_eta") / 100
        cop_hp2_carnot = (T_mandata_ideale+273.15)/max(T_mandata_ideale-T_amb,1)
        backup_cop = cop_hp2_carnot * eta_hp2
        prezzo_el2 = st.slider("Prezzo elettricità HP bassa T (€/MWh)", 80, 350, 180, step=10, key="dim_prezzo_el2")
        capex_kw_hp2 = st.slider("CAPEX (€/kW termico)", 300, 1200, 700, step=50, key="dim_capex_hp2")
        capex_backup = pot_backup_kw * capex_kw_hp2
        opex_backup_unitario = prezzo_el2 / backup_cop if backup_cop > 0 else 0
        st.caption(f"COP HP bassa T ≈ **{backup_cop:.2f}** (sorgente ambiente {T_amb}°C → {T_mandata_ideale}°C). "
                   f"Più basso della HP alta T perché parte dall'ambiente, non dallo scarto industriale.")
        backup_label = f"HP bassa T {pot_backup_kw} kW (COP {backup_cop:.1f})"

    else:  # Biomassa (cippato)
        cD1, cD2, cD3 = st.columns(3)
        pot_backup_kw = cD1.slider("Potenza caldaia (kW)", 0, int(dom_dim_series.max()*1000)+1000, 2000,
                                   step=100, key="dim_pot_bio")
        rend_bio = cD2.slider("Rendimento (%)", 75, 92, 85, key="dim_rend_bio") / 100
        costo_cippato = cD3.slider("Costo cippato (€/MWh termico)", 20, 60, 35, key="dim_costo_bio")
        capex_kw_bio = st.slider("CAPEX (€/kW)", 300, 900, 550, step=25, key="dim_capex_bio")
        capex_backup = pot_backup_kw * capex_kw_bio
        opex_backup_unitario = costo_cippato / rend_bio if rend_bio > 0 else 0
        st.caption("⚠️ La biomassa come backup lavora a basso capacity factor: CAPEX alto spalmato su "
                   "poche ore → LCOH tipicamente elevato. Il confronto lo mostra coi numeri.")
        backup_label = f"Biomassa {pot_backup_kw} kW"

    pot_backup_kw_sim = pot_backup_kw

    # --- Integrazione SOLARE TERMICO (additiva, sopra qualunque combinazione) ---
    st.markdown("##### ☀️ Integrazione solare termico")
    st.caption(
        "Il solare è **additivo**: copre parte della domanda quando c'è sole — soprattutto l'ACS estiva, "
        "quando HP e backup lavorano poco — riducendone il carico. Il default dimensiona il campo perché "
        "la **produzione solare estiva eguagli il fabbisogno ACS estivo** (giu-ago); da lì puoi spingere "
        "la quota su o giù."
    )
    solare_on = st.checkbox("Aggiungi solare termico", value=True, key="dim_solare_on")

    E_solar = 0.0
    solar_avail = np.zeros(len(dom_arr))
    capex_solare = 0.0
    area_sol = 0
    if solare_on:
        # fabbisogno ACS estivo (giu-lug-ago) sugli edifici selezionati
        acs_series = dom_dim.groupby("datetime")["MWh_ACS"].sum().reindex(idx_h, fill_value=0)
        mesi_estivi = idx_h.month.isin([6, 7, 8])
        acs_estiva = float(acs_series[mesi_estivi].sum())
        # produzione solare estiva per campo di riferimento (1000 m² @ 30%) → area baseline
        EFF_REF = 0.30
        off_ref = genera_offerta_solare(pvgis, 1000.0, EFF_REF)
        prod_ref = off_ref.groupby("datetime")["MWh"].sum().reindex(idx_h, fill_value=0)
        prod_ref_estiva = float(prod_ref[mesi_estivi].sum())
        area_baseline = (acs_estiva / prod_ref_estiva * 1000.0) if prod_ref_estiva > 1e-6 else 2000.0

        cS0, cS1, cS2 = st.columns(3)
        cS0.metric("Fabbisogno ACS estivo (giu-ago)", f"{acs_estiva:,.0f} MWh".replace(",", "."),
                   help="È il target base del solare: al 100% il campo è dimensionato per coprirlo in estate.")
        quota_sol = cS1.slider("Quota solare (% dell'ACS estiva)", 0, 300, 100, step=10, key="dim_quota_sol",
                               help="100% = produzione solare estiva ≈ ACS estiva. Sopra il 100% il solare "
                                    "spinge oltre l'ACS, ma il surplus estivo va sprecato senza accumulo stagionale.")
        eff_sol = cS2.slider("Efficienza netta collettori (%)", 15, 50, 30, key="dim_eff_sol") / 100
        # l'area compensa un'efficienza diversa da quella di riferimento per tenere fermo il target energetico
        area_sol = int(round(area_baseline * (quota_sol / 100.0) * (EFF_REF / eff_sol)))
        capex_mq_sol = st.slider("CAPEX solare (€/m²)", 200, 900, 450, step=20, key="dim_capex_sol")

        offerta_sol = genera_offerta_solare(pvgis, area_sol, eff_sol)
        solar_avail = offerta_sol.groupby("datetime")["MWh"].sum().reindex(idx_h, fill_value=0).values
        capex_solare = area_sol * capex_mq_sol

        cSa, cSb, cSc = st.columns(3)
        cSa.metric("Superficie collettori", f"{area_sol:,} m²".replace(",", "."))
        cSb.metric("Produzione solare potenziale", f"{solar_avail.sum():,.0f} MWh/a".replace(",", "."),
                   help="Energia teorica del campo; quanta ne finisce utile dipende dalla domanda ora per ora.")
        cSc.metric("CAPEX solare", f"{capex_solare:,.0f} €".replace(",", "."))

    # -------------------------------------------------------------------------
    # E) Parametri economici + simulazione
    # -------------------------------------------------------------------------
    st.divider()
    st.markdown("#### Parametri economici (LCOH)")
    cE1, cE2 = st.columns(2)
    vita_utile = cE1.slider("Vita utile impianti (anni)", 10, 30, 20, key="dim_vita")
    tasso_sconto = cE2.slider("Tasso di sconto (%)", 1, 10, 4, key="dim_tasso") / 100
    fattore_crf = crf(tasso_sconto, vita_utile)

    # PRIMO STADIO: l'alta T (fumi caldi) copre la domanda direttamente
    q_alta_diretta, dom_residua_arr = simula_accumulo_alta_T(
        dom_arr, scarto_alta_arr, volume_alta_T, T_mandata_ideale, T_ritorno_ideale,
        perdita_sett_pct=perdita_sett_pct
    )
    E_alta_diretta = float(q_alta_diretta.sum())

    # STADIO SOLARE: il solare termico (must-take) copre parte della domanda residua
    q_solar_arr = np.minimum(dom_residua_arr, solar_avail)
    E_solar = float(q_solar_arr.sum())
    E_solar_sprecato = float((solar_avail - q_solar_arr).sum())
    dom_dopo_solare = dom_residua_arr - q_solar_arr

    # SECONDO STADIO: la HP alta T (accumulo tiepido) copre il residuo, backup a valle
    sim = simula_accumulo_tiepido(
        dom_dopo_solare, scarto_arr, scartoT_arr, volume_accumulo,
        T_min_acc, T_max_acc, dT_evap, pot_hp_kw, cop_reale, pot_backup_kw_sim,
        architettura=architettura, backup_cop=backup_cop, backup_arr_max=None,
        perdita_sett_pct=perdita_sett_pct,
        cop_dinamico=cop_dinamico, T_mandata_cop=T_mandata_ideale, eta_hp_cop=eta_hp,
        T_ritorno_rete=T_ritorno_ideale
    )

    # -------------------------------------------------------------------------
    # RISULTATI
    # -------------------------------------------------------------------------
    st.divider()
    st.markdown("#### Risultato della simulazione oraria")

    # mix di copertura: alta T diretta + solare + HP + backup
    E_hp, E_gas, E_nc = sim["E_hp"], sim["E_gas"], sim["E_non_coperta"]
    dom_tot = dom_dim_series.sum()
    cols_r = st.columns(5 if solare_on else 4)
    ci = 0
    cols_r[ci].metric("🔴 Alta T diretta", f"{E_alta_diretta:,.0f} MWh".replace(",", "."),
              help=f"{E_alta_diretta/dom_tot*100:.0f}% della domanda dai fumi caldi, senza HP né backup "
                   f"(calore quasi gratuito)"); ci += 1
    if solare_on:
        cols_r[ci].metric("☀️ Solare", f"{E_solar:,.0f} MWh".replace(",", "."),
              help=f"{E_solar/dom_tot*100:.0f}% della domanda dal solare termico · "
                   f"{E_solar_sprecato:,.0f} MWh estivi in surplus (sprecati senza accumulo stagionale)".replace(",", ".")); ci += 1
    cols_r[ci].metric("🔵 HP alta T", f"{E_hp:,.0f} MWh".replace(",", "."),
              help=f"{E_hp/dom_tot*100:.0f}% della domanda · COP medio {sim['cop_medio']:.1f} · "
                   f"{sim['ore_hp_attiva']:,} ore attiva".replace(",", ".")); ci += 1
    cols_r[ci].metric("Backup", f"{E_gas:,.0f} MWh".replace(",", "."),
              help=f"{backup_label} · {E_gas/dom_tot*100:.0f}% della domanda · {sim['ore_gas_attivo']:,} ore attivo".replace(",", ".")); ci += 1
    quota_rinnovabile = (E_alta_diretta + E_solar + E_hp) / dom_tot * 100 if dom_tot > 0 else 0
    cols_r[ci].metric("Quota rinnovabile", f"{quota_rinnovabile:.0f}%",
              help=f"Alta T + solare + HP sul totale domanda (il backup conta a parte se rinnovabile). "
                   f"Elettricità HP {sim['E_el_hp']:,.0f} MWh".replace(",", "."))

    if sim["ore_non_coperte"] > 0:
        st.error(
            f"⚠️ **{sim['ore_non_coperte']} ore/anno non coperte** ({E_nc:,.0f} MWh): alta T, HP e backup "
            f"insieme non bastano. Aumenta le potenze o i volumi di accumulo.".replace(",", ".")
        )
    else:
        st.success("✅ Il sistema copre il 100% della domanda in tutte le ore.")

    # grafico mix — "chi copre la domanda"
    fig_mix = go.Figure()
    voci_mix = [("🔴 Scarto alta T diretto", E_alta_diretta, COLOR_ALTA_T)]
    if solare_on and E_solar > 1:
        voci_mix.append(("☀️ Solare termico", E_solar, COLOR_SOLARE))
    voci_mix += [("🔵 HP alta T", E_hp, COLOR_HP), (f"⚙️ {backup_label}", E_gas, COLOR_BACKUP)]
    if E_nc > 1:
        voci_mix.append(("Non coperto", E_nc, COLOR_NONCOP))
    tot_mix = sum(v for _, v, _ in voci_mix) or 1.0
    for nome, val, col in voci_mix:
        pct = val / tot_mix * 100
        fig_mix.add_trace(go.Bar(
            y=["Copertura"], x=[val], name=nome, orientation="h", marker_color=col,
            text=(f"{pct:.0f}%" if pct >= 6 else ""), textposition="inside",
            insidetextanchor="middle", textfont=dict(color="white", size=13),
            cliponaxis=False,
            hovertemplate=f"{nome}: %{{x:,.0f}} MWh ({pct:.1f}%)<extra></extra>"))
    fig_mix.update_layout(barmode="stack", height=240, xaxis_title="MWh/anno",
                          legend=dict(orientation="h", yanchor="top", y=-0.35, x=0),
                          margin=dict(t=40, b=20), title="Chi copre la domanda")
    fig_mix.update_yaxes(showticklabels=False)
    st.plotly_chart(fig_mix, use_container_width=True)

    # curva oraria temperatura accumulo (settimana tipo invernale + estiva) e distribuzione
    st.markdown("##### 🌡️ Comportamento dell'accumulo")
    T_acc_series = pd.Series(sim["T_acc"], index=idx_h)
    q_hp_series = pd.Series(sim["q_hp"], index=idx_h)
    q_gas_series = pd.Series(sim["q_gas"], index=idx_h)
    cop_series = pd.Series(sim["cop_serie"], index=idx_h)
    # stato di carica: 0% a T_min, 100% a T_max
    soc_series = ((T_acc_series - T_min_acc) / max(T_max_acc - T_min_acc, 1) * 100).clip(0, 100)

    sett = st.radio("Periodo da visualizzare", ["Settimana invernale (gen)", "Settimana estiva (lug)", "Anno intero"],
                    horizontal=True, key="dim_periodo_tacc")
    if sett == "Settimana invernale (gen)":
        mask_t = (idx_h >= "2024-01-15") & (idx_h < "2024-01-22")
    elif sett == "Settimana estiva (lug)":
        mask_t = (idx_h >= "2024-07-15") & (idx_h < "2024-07-22")
    else:
        mask_t = np.ones(len(idx_h), dtype=bool)

    # metriche di sintesi sull'accumulo
    ore_pieno = int((soc_series >= 95).sum())
    ore_scarico = int((soc_series <= 5).sum())
    mA1, mA2, mA3 = st.columns(3)
    mA1.metric("T media accumulo (anno)", f"{T_acc_series.mean():.0f}°C",
               help=f"Oscilla tra {T_acc_series.min():.0f} e {T_acc_series.max():.0f}°C")
    mA2.metric("Ore/anno ~pieno (SOC≥95%)", f"{ore_pieno:,}".replace(",", "."),
               help="Accumulo carico: scarto abbondante, HP a COP alto")
    mA3.metric("Ore/anno ~scarico (SOC≤5%)", f"{ore_scarico:,}".replace(",", "."),
               help="Accumulo vuoto: subentra il backup")

    # grafico 1: T accumulo + COP orario (doppio asse) nel periodo scelto
    fig_tacc = go.Figure()
    fig_tacc.add_trace(go.Scatter(x=idx_h[mask_t], y=T_acc_series[mask_t], mode="lines",
                                  name="T accumulo", line=dict(color=COLOR_ACCUMULO, width=1.8), yaxis="y1"))
    fig_tacc.add_trace(go.Scatter(x=idx_h[mask_t], y=cop_series[mask_t], mode="lines",
                                  name="COP orario", line=dict(color=COLOR_HP, width=1.2, dash="dot"), yaxis="y2"))
    fig_tacc.add_hline(y=T_max_acc, line_dash="dot", line_color="gray", annotation_text="T max = mandata")
    fig_tacc.add_hline(y=T_min_acc, line_dash="dot", line_color="red", annotation_text="T min (subentra backup)")
    fig_tacc.update_layout(height=320, xaxis_title="",
                           yaxis=dict(title="T accumulo (°C)", side="left"),
                           yaxis2=dict(title="COP orario", overlaying="y", side="right", showgrid=False),
                           legend=dict(orientation="h", yanchor="bottom", y=1.02),
                           title="Temperatura accumulo e COP istantaneo (si muovono insieme)")
    st.plotly_chart(fig_tacc, use_container_width=True)
    st.caption(
        "Il COP (linea tratteggiata) sale quando l'accumulo è caldo e scende quando si svuota: "
        "è la ragione per cui il COP dinamico è più realistico del valore fisso. Quando la T tocca "
        "la linea rossa, l'accumulo è scarico e subentra il backup."
    )

    # grafico 2: istogramma ore per fascia di temperatura accumulo (sempre su anno intero)
    bins = np.arange(int(T_min_acc//5*5), int(T_max_acc//5*5)+10, 5)
    hist, edges = np.histogram(T_acc_series.values, bins=bins)
    centri = [f"{int(edges[i])}-{int(edges[i+1])}°C" for i in range(len(edges)-1)]
    fig_hist = go.Figure(go.Bar(x=centri, y=hist, marker_color=COLOR_ACCUMULO))
    fig_hist.update_layout(height=260, xaxis_title="Fascia di temperatura accumulo",
                           yaxis_title="Ore/anno", margin=dict(t=30, b=10),
                           title="Quante ore l'accumulo passa in ciascuna fascia di temperatura")
    st.plotly_chart(fig_hist, use_container_width=True)

    # grafico 3: HP vs backup nel periodo
    fig_disp = go.Figure()
    fig_disp.add_trace(go.Scatter(x=idx_h[mask_t], y=q_hp_series[mask_t], mode="lines", name="HP alta T",
                                  stackgroup="one", line=dict(width=0.5, color=COLOR_HP),
                                  fillcolor=hex_to_rgba(COLOR_HP, 0.75)))
    fig_disp.add_trace(go.Scatter(x=idx_h[mask_t], y=q_gas_series[mask_t], mode="lines", name=backup_label,
                                  stackgroup="one", line=dict(width=0.5, color=COLOR_BACKUP),
                                  fillcolor=hex_to_rgba(COLOR_BACKUP, 0.75)))
    fig_disp.add_trace(go.Scatter(x=idx_h[mask_t], y=dom_dim_series[mask_t], mode="lines", name="Domanda",
                                  line=dict(color="black", width=1, dash="dot")))
    fig_disp.update_layout(height=300, yaxis_title="MWh/h (≈ MW)", xaxis_title="",
                           legend=dict(orientation="h", yanchor="bottom", y=1.02),
                           title="Ripartizione oraria HP / backup rispetto alla domanda")
    st.plotly_chart(fig_disp, use_container_width=True)

    # -------------------------------------------------------------------------
    # COSTI e LCOH
    # -------------------------------------------------------------------------
    st.divider()
    st.markdown("#### 💰 Costi e LCOH")
    capex_hp = pot_hp_kw * capex_kw_hp
    capex_acc = volume_accumulo * costo_m3_accumulo
    opex_hp = sim["E_el_hp"] * prezzo_el
    # OPEX del backup: opex_backup_unitario è sempre in €/MWh di calore reso dal backup
    opex_gas = E_gas * opex_backup_unitario

    righe = [
        {"Voce": f"HP alta T ({pot_hp_kw} kW)", "CAPEX (€)": round(capex_hp),
         "CAPEX annuo (€/a)": round(capex_hp*fattore_crf), "OPEX (€/a)": round(opex_hp),
         "Energia (MWh/a)": round(E_hp),
         "Costo annuo (€/a)": round(capex_hp*fattore_crf + opex_hp),
         "LCOH (€/MWh)": round((capex_hp*fattore_crf + opex_hp)/E_hp, 1) if E_hp > 1e-6 else None},
        {"Voce": f"Backup: {backup_label}", "CAPEX (€)": round(capex_backup),
         "CAPEX annuo (€/a)": round(capex_backup*fattore_crf), "OPEX (€/a)": round(opex_gas),
         "Energia (MWh/a)": round(E_gas),
         "Costo annuo (€/a)": round(capex_backup*fattore_crf + opex_gas),
         "LCOH (€/MWh)": round((capex_backup*fattore_crf + opex_gas)/E_gas, 1) if E_gas > 1e-6 else None},
    ]
    if solare_on and E_solar > 1e-6:
        righe.append(
            {"Voce": f"Solare termico ({area_sol} m²)", "CAPEX (€)": round(capex_solare),
             "CAPEX annuo (€/a)": round(capex_solare*fattore_crf), "OPEX (€/a)": 0,
             "Energia (MWh/a)": round(E_solar),
             "Costo annuo (€/a)": round(capex_solare*fattore_crf),
             "LCOH (€/MWh)": round(capex_solare*fattore_crf/E_solar, 1) if E_solar > 1e-6 else None})
    righe.append(
        {"Voce": f"Accumulo ({volume_accumulo} m³)", "CAPEX (€)": round(capex_acc),
         "CAPEX annuo (€/a)": round(capex_acc*fattore_crf), "OPEX (€/a)": 0,
         "Energia (MWh/a)": None, "Costo annuo (€/a)": round(capex_acc*fattore_crf),
         "LCOH (€/MWh)": None})
    df_tec = pd.DataFrame(righe)
    st.dataframe(df_tec, use_container_width=True, hide_index=True)

    def _colore_voce(v):
        if v.startswith("HP alta T"): return COLOR_HP
        if v.startswith("Solare"): return COLOR_SOLARE
        return COLOR_BACKUP
    df_lcoh = df_tec.dropna(subset=["LCOH (€/MWh)"]).sort_values("LCOH (€/MWh)")
    if not df_lcoh.empty:
        fig_lcoh = go.Figure(go.Bar(
            x=df_lcoh["LCOH (€/MWh)"], y=df_lcoh["Voce"], orientation="h",
            marker_color=[_colore_voce(v) for v in df_lcoh["Voce"]],
            text=df_lcoh["LCOH (€/MWh)"].map(lambda v: f"{v:.0f} €/MWh"), textposition="outside"))
        fig_lcoh.update_layout(height=220, xaxis_title="LCOH (€/MWh)", yaxis_title="",
                               margin=dict(t=10, b=10),
                               title="Costo del calore per fonte (più basso = più conveniente)")
        st.plotly_chart(fig_lcoh, use_container_width=True)

    capex_sistema = capex_hp + capex_backup + capex_acc + capex_solare
    costo_annuo_sistema = capex_sistema*fattore_crf + opex_hp + opex_gas
    energia_fornita = E_hp + E_gas + E_solar
    lcoh_sistema = costo_annuo_sistema / energia_fornita if energia_fornita > 1e-6 else np.nan
    # quota rinnovabile: HP e solare sempre FER; il backup conta come FER se NON è la caldaia a gas
    backup_is_fer = backup_tipo != "Caldaia (gas)"
    E_fer = E_hp + E_solar + (E_gas if backup_is_fer else 0)
    quota_fer_pct = E_fer / energia_fornita * 100 if energia_fornita > 1e-6 else 0

    s1, s2, s3, s4 = st.columns(4)
    s1.metric("CAPEX di sistema", f"{capex_sistema:,.0f} €".replace(",", "."))
    s2.metric("Costo annuo di sistema", f"{costo_annuo_sistema:,.0f} €/a".replace(",", "."))
    s3.metric("LCOH di sistema", f"{lcoh_sistema:.1f} €/MWh" if not np.isnan(lcoh_sistema) else "n/d",
              help="Solo produzione di calore: escluse rete, centrale, allacciamenti")
    s4.metric("Quota rinnovabile", f"{quota_fer_pct:.0f}%",
              help="HP (recupero scarto) + backup se rinnovabile. Con backup a gas solo la HP conta come FER.")

    # sweep volume accumulo
    with st.expander("🔍 Sweep accumulo: come cambia il sistema al variare del volume"):
        st.caption("Rifà la simulazione oraria per diversi volumi, tenendo fisse HP e backup. "
                   "Mostra quanto scarto recuperato, quota HP e LCOH migliorano con l'accumulo.")
        volumi = list(range(0, 4001, 500))
        rows = []
        for vol in volumi:
            s = simula_accumulo_tiepido(dom_dopo_solare, scarto_arr, scartoT_arr, vol,
                                        T_min_acc, T_max_acc, dT_evap, pot_hp_kw, cop_reale, pot_backup_kw_sim,
                                        architettura=architettura, backup_cop=backup_cop, backup_arr_max=None,
                                        perdita_sett_pct=np.interp(np.log(np.clip(vol,500,5000)), [np.log(500),np.log(5000)], [2.0,1.0]) if vol>0 else 0.0,
                                        cop_dinamico=cop_dinamico, T_mandata_cop=T_mandata_ideale, eta_hp_cop=eta_hp,
                                        T_ritorno_rete=T_ritorno_ideale)
            cx = capex_hp + capex_backup + vol*costo_m3_accumulo
            ca = cx*fattore_crf + s["E_el_hp"]*prezzo_el + s["E_gas"]*opex_backup_unitario
            ef = s["E_hp"] + s["E_gas"]
            rows.append({"Volume (m³)": vol,
                         "Quota HP (%)": s["E_hp"]/ef*100 if ef else 0,
                         "Scarto recuperato (MWh)": round(s["E_scarto_captato"]),
                         "Backup (MWh)": round(s["E_gas"]),
                         "LCOH (€/MWh)": ca/ef if ef else np.nan,
                         "Ore non coperte": s["ore_non_coperte"]})
        df_sw = pd.DataFrame(rows)
        fig_sw = go.Figure()
        fig_sw.add_trace(go.Scatter(x=df_sw["Volume (m³)"], y=df_sw["Quota HP (%)"],
                                    name="Quota HP (%)", yaxis="y1", line=dict(color=COLOR_HP)))
        fig_sw.add_trace(go.Scatter(x=df_sw["Volume (m³)"], y=df_sw["LCOH (€/MWh)"],
                                    name="LCOH (€/MWh)", yaxis="y2", line=dict(color=COLOR_CALDAIA)))
        fig_sw.update_layout(height=340, xaxis_title="Volume accumulo (m³)",
                             yaxis=dict(title="Quota HP (%)", side="left"),
                             yaxis2=dict(title="LCOH (€/MWh)", overlaying="y", side="right"),
                             legend=dict(orientation="h", yanchor="bottom", y=1.02),
                             title="Effetto del volume di accumulo")
        st.plotly_chart(fig_sw, use_container_width=True)
        st.dataframe(df_sw.round(1), use_container_width=True, hide_index=True)

    # snapshot per confronto scenari
    st.session_state["_dim_snapshot"] = {
        "utenza": f"{len(edifici_dim)} edifici (da Domanda)",
        "T mandata/ritorno": f"{T_mandata_ideale}/{T_ritorno_ideale}°C",
        "carico_residuo_mwh": round(float(dom_tot)),
        "tecnologie": (f"HP alta T {pot_hp_kw}kW (COP {sim['cop_medio']:.1f}{'din' if cop_dinamico else 'fisso'}) + {backup_label}"
                       + (f" + Solare {area_sol}m²" if (solare_on and E_solar > 1) else "")),
        "volume_accumulo": volume_accumulo,
        "capex_sistema": round(float(capex_sistema)),
        "costo_annuo_sistema": round(float(costo_annuo_sistema)),
        "lcoh_sistema": round(float(lcoh_sistema), 1) if not np.isnan(lcoh_sistema) else None,
        "quota_fer_pct": round(float(quota_fer_pct)),
        "ore_non_coperte": sim["ore_non_coperte"],
    }

# =============================================================================
# TAB 4 - CONFRONTO SCENARI
# =============================================================================
with tab_confronto:
    st.markdown("### Confronto scenari")
    st.caption(
        "Salva la configurazione corrente della scheda Dimensionamento (mix tecnologico + accumulo) "
        "per confrontarla con altre — es. **100% rinnovabile** vs **rinnovabile + quota gas**. "
        "Imposta le tecnologie in Dimensionamento, torna qui e salva; poi cambia il mix e salva di nuovo."
    )

    if "scenari_salvati" not in st.session_state:
        st.session_state.scenari_salvati = []

    snap = st.session_state.get("_dim_snapshot")
    if snap is None:
        st.info("Apri prima la scheda Dimensionamento e imposta un mix di tecnologie.")
    else:
        cprev1, cprev2, cprev3, cprev4 = st.columns(4)
        cprev1.metric("Carico residuo", f"{snap['carico_residuo_mwh']:,.0f} MWh".replace(",", "."))
        cprev2.metric("LCOH di sistema", f"{snap['lcoh_sistema']:.1f} €/MWh" if snap['lcoh_sistema'] else "n/d")
        cprev3.metric("Quota FER", f"{snap['quota_fer_pct']:.0f}%")
        cprev4.metric("Ore non coperte", f"{snap['ore_non_coperte']}" if snap['ore_non_coperte'] is not None else "n/d")
        st.caption(f"Mix corrente: **{snap['tecnologie']}** · accumulo {snap['volume_accumulo']} m³")

        nome_scenario = st.text_input("Nome scenario",
                                      value=f"Scenario {len(st.session_state.scenari_salvati)+1}", key="conf_nome")
        if st.button("💾 Salva scenario corrente"):
            st.session_state.scenari_salvati.append({
                "Nome": nome_scenario,
                "Utenza": snap["utenza"],
                "T mand./rit.": snap["T mandata/ritorno"],
                "Tecnologie": snap["tecnologie"],
                "Carico residuo (MWh)": snap["carico_residuo_mwh"],
                "Accumulo (m³)": snap["volume_accumulo"],
                "Quota FER (%)": snap["quota_fer_pct"],
                "CAPEX (€)": snap["capex_sistema"],
                "Costo annuo (€/a)": snap["costo_annuo_sistema"],
                "LCOH (€/MWh)": snap["lcoh_sistema"],
                "Ore non coperte": snap["ore_non_coperte"],
            })
            st.success(f"Scenario '{nome_scenario}' salvato.")

    if st.session_state.scenari_salvati:
        df_scenari = pd.DataFrame(st.session_state.scenari_salvati)
        st.dataframe(df_scenari, use_container_width=True, hide_index=True)

        c1, c2 = st.columns(2)
        with c1:
            fig_lcoh_conf = go.Figure(go.Bar(
                x=df_scenari["Nome"], y=df_scenari["LCOH (€/MWh)"], marker_color=COLOR_CALDAIA,
                text=df_scenari["LCOH (€/MWh)"].map(lambda v: f"{v:.0f}" if pd.notna(v) else "n/d"),
                textposition="outside"))
            fig_lcoh_conf.update_layout(height=340, yaxis_title="LCOH (€/MWh)",
                                        title="LCOH di sistema per scenario (più basso = più conveniente)")
            st.plotly_chart(fig_lcoh_conf, use_container_width=True)
        with c2:
            fig_fer_conf = go.Figure(go.Bar(
                x=df_scenari["Nome"], y=df_scenari["Quota FER (%)"], marker_color=COLOR_OFFERTA,
                text=df_scenari["Quota FER (%)"].map(lambda v: f"{v:.0f}%"), textposition="outside"))
            fig_fer_conf.update_layout(height=340, yaxis_title="Quota FER (%)", yaxis_range=[0, 105],
                                       title="Quota rinnovabile per scenario")
            st.plotly_chart(fig_fer_conf, use_container_width=True)

        fig_costo = go.Figure()
        fig_costo.add_trace(go.Bar(x=df_scenari["Nome"], y=df_scenari["CAPEX (€)"],
                                   name="CAPEX (€)", marker_color=COLOR_ACCUMULO))
        fig_costo.add_trace(go.Bar(x=df_scenari["Nome"], y=df_scenari["Costo annuo (€/a)"],
                                   name="Costo annuo (€/a)", marker_color=COLOR_HP))
        fig_costo.update_layout(height=340, barmode="group", yaxis_title="€",
                                title="CAPEX totale vs costo annuo, per scenario",
                                legend=dict(orientation="h", yanchor="bottom", y=1.02))
        st.plotly_chart(fig_costo, use_container_width=True)
        st.caption(
            "Lettura tipica: lo scenario **100% FER** ha CAPEX più alto (HP/biomassa sovradimensionate "
            "per il picco) ma OPEX più basso; lo scenario **FER + gas** ha CAPEX più basso (il gas copre "
            "il picco con poca spesa d'impianto) ma OPEX più alto e quota FER inferiore. Il LCOH dice "
            "quale delle due, nel complesso, produce calore a minor costo."
        )

        if st.button("🗑️ Cancella tutti gli scenari salvati"):
            st.session_state.scenari_salvati = []
            st.rerun()
    else:
        st.info("Nessuno scenario salvato ancora. Imposta la scheda Dimensionamento e premi 'Salva scenario corrente'.")

st.divider()
st.caption(
    "Fonti: Google Sheet 'Utenze TLR Maniago' (De Blasio Associati / APE FVG), TRL_utenze_bioman.xlsx, "
    "stazione meteo Vivaro (ARPA FVG OSMER), interviste aziende + foto monitoraggio. "
    "ACS stimata da base load estivo reale dove disponibile, altrimenti da % tipologica (QM Handbook). "
    "Profili aziende: motore generico per tipo_profilo, parametri da validare con log dati reali. "
    "Simulazione accumulo: dispatch greedy orario, nessun limite di potenza carica/scarico."
)
