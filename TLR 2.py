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
import json
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
COLOR_HP = "#22C3DD"  # ciano → HP alta T (alias di COLOR_HP_ALTA)
COLOR_CALDAIA = "#B0413E"
COLOR_EX_BIOMAN = "#E63946"  # rosso acceso dedicato, sempre e solo per la zona ex Bioman

# --- Palette DISPATCH/COPERTURA: colori vivaci e ben distinti (per tema scuro) ---
COLOR_ALTA_T   = "#FF4B4B"  # rosso vivo   → scarto ≥ mandata, diretto in linea (caldo diretto)
COLOR_HP_ALTA  = COLOR_HP    # ciano        → HP alta T (intermedio → mandata)
COLOR_HP_BASSA = "#B57EDC"  # viola        → HP bassa T (freddo/ground → intermedio, interno)
COLOR_SOLARE   = "#F5C518"  # ambra        → solare termico
COLOR_BACKUP   = "#FF9F1C"  # arancio      → caldaia gas/biomassa (supporto a combustibile)
COLOR_NONCOP   = "#9AA0A6"  # grigio       → domanda non coperta
COLOR_DOMANDA  = "#FFFFFF"  # bianco       → linea della domanda (visibile su sfondo scuro)


ZONE_NOMI = {
    1: "Zona 1 - Comune NE",
    2: "Zona 2 - Ex Bioman",
    3: "Zona 3 - Sud",
    4: "Zona 4 - Centro",
    5: "Zona 5 - Ovest",
}
ZONE_DEFAULT = ["Zona 1 - Comune NE", "Zona 2 - Ex Bioman"]      # zone attive di default
ZONA_COLORI = {
    "Zona 1 - Comune NE": "#2D7DC0",   # blu
    "Zona 2 - Ex Bioman": "#E63946",   # rosso
    "Zona 3 - Sud":       "#E9C46A",   # giallo
    "Zona 4 - Centro":    "#9B5DE5",   # viola
    "Zona 5 - Ovest":     "#3FA34D",   # verde
}
# la frazione di Campagna (a est di questa longitudine) è ESCLUSA dall'analisi:
# troppo lontana e isolata (~2,4 km dalla centrale, densità lineare ~0,04 MWh/(m·a))
CAMPAGNA_LON_MIN = 12.73


def _anelli_zona(geom):
    """Anelli esterni di un (Multi)Polygon → lista di array Nx2 [lon, lat]."""
    polys = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]
    return [np.asarray(p[0], dtype=float) for p in polys]


@st.cache_data
def carica_zone_confini(path="TLR_zones_borders.geojson"):
    """Poligoni dei confini di zona: {id_zona: [anelli]}. {} se il file manca."""
    try:
        gj = json.load(open(path, encoding="utf-8"))
    except Exception:
        return {}
    return {ft["properties"]["id"]: _anelli_zona(ft["geometry"]) for ft in gj["features"]}


def _punto_in_anello(lon, lat, ring):
    x, y = ring[:, 0], ring[:, 1]
    n = len(x); dentro = False; j = n - 1
    for i in range(n):
        if ((y[i] > lat) != (y[j] > lat)) and \
           (lon < (x[j] - x[i]) * (lat - y[i]) / (y[j] - y[i] + 1e-15) + x[i]):
            dentro = not dentro
        j = i
    return dentro


def zona_da_coordinate(lat, lon, zone_poly):
    """Nome della zona che contiene il punto, altrimenti None."""
    if lat is None or lon is None or (isinstance(lat, float) and np.isnan(lat)):
        return None
    if lon is not None and lon > CAMPAGNA_LON_MIN:      # frazione di Campagna: esclusa
        return "__ESCLUSO__"
    for zid, anelli in zone_poly.items():
        for r in anelli:
            if _punto_in_anello(lon, lat, r):
                return ZONE_NOMI.get(zid)
    return None


AZIENDE_COORD = {
    "ZML":         (46.1478, 12.7139),
    "Pietro Rosa": (46.1432, 12.7215),
    "Pandolfo":    (46.1485, 12.7160),
    "Inossman":    (46.1501, 12.7145),
}
# sottocentrale: baricentro ottimo tra ZML e Pandolfo (min. metri di tubo pesati)
CENTRALE_LAT, CENTRALE_LON = 46.1479, 12.7151


def mst_archi(lat, lon, radice=None):
    """Albero di connessione minimo (Prim) sui punti dati; se 'radice' è (lat,lon) parte da lì.
    Ritorna (archi, lunghezza_totale_m): archi = lista di ((lat1,lon1),(lat2,lon2),dist_m)."""
    lat = np.asarray(lat, dtype=float); lon = np.asarray(lon, dtype=float)
    ok = np.isfinite(lat) & np.isfinite(lon)
    lat, lon = lat[ok], lon[ok]
    if radice is not None:
        lat = np.insert(lat, 0, radice[0]); lon = np.insert(lon, 0, radice[1])
    n = len(lat)
    if n < 2:
        return [], 0.0
    R = 6371000.0
    la = np.radians(lat); lo = np.radians(lon)
    x = R * lo * np.cos(la.mean()); y = R * la
    dentro = np.zeros(n, dtype=bool); dentro[0] = True
    dist = np.hypot(x - x[0], y - y[0])
    padre = np.zeros(n, dtype=int)
    archi = []; tot = 0.0
    for _ in range(n - 1):
        d2 = np.where(dentro, np.inf, dist)
        j = int(np.argmin(d2))
        if not np.isfinite(d2[j]):
            break
        p = int(padre[j]); tot += float(dist[j]); dentro[j] = True
        archi.append(((lat[p], lon[p]), (lat[j], lon[j]), float(dist[j])))
        nd = np.hypot(x - x[j], y - y[j])
        agg = nd < dist
        padre[agg] = j; dist = np.minimum(dist, nd)
    return archi, tot


def stima_lunghezza_rete(lat, lon, fattore_tortuosita=1.35):
    """Lunghezza indicativa della rete (m) che collega i punti dati, come albero di
    connessione minimo (MST, algoritmo di Prim) sulle distanze in piano locale.
    Il fattore di tortuosità tiene conto che le tubazioni seguono le strade, non le rette."""
    lat = np.asarray(lat, dtype=float); lon = np.asarray(lon, dtype=float)
    ok = np.isfinite(lat) & np.isfinite(lon)
    lat, lon = lat[ok], lon[ok]
    n = len(lat)
    if n < 2:
        return 0.0
    R = 6371000.0
    la = np.radians(lat); lo = np.radians(lon)
    x = R * lo * np.cos(la.mean()); y = R * la
    in_albero = np.zeros(n, dtype=bool); in_albero[0] = True
    dist = np.hypot(x - x[0], y - y[0]); tot = 0.0
    for _ in range(n - 1):
        dist[in_albero] = np.inf
        j = int(np.argmin(dist)); tot += float(dist[j]); in_albero[j] = True
        dist = np.minimum(dist, np.hypot(x - x[j], y - y[j]))
    return tot * fattore_tortuosita


def build_cluster_color_map(clusters_list):
    """Colore fisso per zona di rete (vedi ZONA_COLORI)."""
    return {cl: ZONA_COLORI.get(cl, "#888888") for cl in clusters_list}


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
MWH_PER_UNITA = 9.0   # consumo termico di riferimento per unità abitativa (MWh/a), scalabile dall'UI
HOURS_2024 = pd.date_range('2024-01-01', '2024-12-31 23:00', freq='h')
DAYS_2024 = pd.date_range('2024-01-01', '2024-12-31', freq='D')


def soil_temp_monthly(pvgis_df, depth_m=1.5, alpha=0.6e-6):
    """Temperatura del terreno (°C) per mese alla profondità data (transitorio sinusoidale
    smorzato applicato alla T aria oraria PVGIS T2m). A ~1.5 m la variazione diurna è
    annullata → un valore per mese. Ritorna array di 12 valori (Gen..Dic)."""
    T = pvgis_df["T2m"].astype(float).values
    doy = pvgis_df["datetime"].dt.dayofyear.values.astype(float)
    w = 2 * np.pi / 365.25
    X = np.column_stack([np.ones_like(doy), np.cos(w * doy), np.sin(w * doy)])
    coef, *_ = np.linalg.lstsq(X, T, rcond=None)
    Tm = float(coef[0]); A = float(np.hypot(coef[1], coef[2]))
    t_peak = float((np.arctan2(coef[2], coef[1]) / w) % 365.25)
    P = 365.25 * 86400.0
    d = np.sqrt(alpha * P / np.pi)          # profondità di smorzamento
    damp = np.exp(-depth_m / d); lag = (depth_m / d) / w   # ritardo (giorni)
    return np.array([Tm + A * damp * np.cos(w * (pd.Timestamp(2024, m, 15).dayofyear - t_peak - lag))
                     for m in range(1, 13)])


def cop_singola(T_src, T_mand, eta):
    """COP di una HP a stadio singolo (Carnot × η). Funziona anche su array numpy."""
    Tc = np.asarray(T_src, dtype=float) + 273.15
    Th = float(T_mand) + 273.15
    return eta * Th / np.maximum(Th - Tc, 1.0)

def routing_flussi(off_df, idx_h, mandata, T_int):
    """Instrada ogni flusso-ora per temperatura (ordine di merito):
      T_disp ≥ mandata            → accumulo CALDO (diretto in linea)
      T_int  ≤ T_disp < mandata   → accumulo INTERMEDIO (scambiatore diretto)
      T_disp < T_int              → accumulo BASSO (sorgente della HP bassa T)
    Ritorna: q_hot, q_int, q_low (MWh, orari) e la STRATIFICAZIONE dell'accumulo basso:
    q_low_bins [ore × fasce] = energia dei flussi freddi per fascia di temperatura (5°C),
    bin_T [fasce] = temperatura rappresentativa di ogni fascia. Così la HP bassa può pescare
    dallo strato più caldo disponibile (COP migliore) invece che dalla media miscelata."""
    o = off_df[off_df["MWh"] > 0].copy()
    o["T"] = o["T_disponibile"]
    hot = o[o["T"] >= mandata].groupby("datetime")["MWh"].sum().reindex(idx_h, fill_value=0.0)
    intm = o[(o["T"] >= T_int) & (o["T"] < mandata)].groupby("datetime")["MWh"].sum().reindex(idx_h, fill_value=0.0)
    low = o[o["T"] < T_int].copy()
    q_low = low.groupby("datetime")["MWh"].sum().reindex(idx_h, fill_value=0.0)
    edges = np.arange(0.0, T_int + 5.0, 5.0)              # fasce da 5°C: 0-5, ..., fino a T_int
    bin_T = (edges[:-1] + edges[1:]) / 2.0                # temp rappresentativa di ogni fascia
    K = len(bin_T)
    if low.empty:
        q_low_bins = np.zeros((len(idx_h), K))
    else:
        low = low.copy()
        low["bin"] = np.clip(np.digitize(low["T"].values, edges) - 1, 0, K - 1)
        piv = low.pivot_table(index="datetime", columns="bin", values="MWh", aggfunc="sum", observed=False)
        piv = piv.reindex(index=idx_h, columns=range(K), fill_value=0.0).fillna(0.0)
        q_low_bins = piv.values
    return hot.values, intm.values, q_low.values, q_low_bins, bin_T

def cop_singola(T_src, T_mand, eta, lift_min_K=8.0, cop_max=6.5):
    """COP Carnot × η con lift minimo (mai < lift_min_K) e cap a cop_max.
    lift_min_K rappresenta il ΔT effettivo minimo del compressore reale
    (perdite meccaniche, surriscaldamento, sottoraffreddamento).
    cop_max è la fascia superiore realistica per HP industriali con lift moderato
    (IEA DHC F6/F10: HP su excess heat 25 °C, lift ~25-40 K, COP 3-5)."""
    Tc = np.asarray(T_src, dtype=float) + 273.15
    Th = float(T_mand) + 273.15
    lift = np.maximum(Th - Tc, lift_min_K)
    cop = eta * Th / lift
    return np.minimum(cop, cop_max)


def dispatch_cascata(dom_arr, q_hot_arr, q_int_arr, q_low_bins, bin_T, soil_arr,
                     mandata, ritorno, T_int, dT_evap, eta_hp,
                     V_hot, V_int, V_low,
                     P_hp_alta_kw, P_hp_bassa_kw,
                     parallelo="HP bassa T", P_backup_kw=0.0, backup_cop=None,
                     antigelo=0.0, perdita_sett_pct=1.0):
    """
    Dispatch orario dello schema a cascata con 3 accumuli stratificati.

    CORE (sempre): scarto ≥ mandata → accumulo CALDO → linea; scarto [T_int,mandata) →
    accumulo INTERMEDIO; la HP ALTA T solleva l'intermedio → mandata (salto fisso, COP alto).

    PARALLELO (scelta, stessa funzione = coprire il gap):
      - "HP bassa T": recupera i flussi freddi (<T_int) e, quando manca lo scarto, il GROUND
        LOOP (profilo suolo, con floor antigelo), sollevandoli all'intermedio → poi HP alta T.
      - "gas"/"biomassa": una caldaia copre il gap direttamente a mandata; i flussi freddi
        NON vengono usati (una caldaia non può sollevarli).

    Ritorna dict con energie annue e serie orarie.
    """
    n = len(dom_arr)
    swing = max(mandata - ritorno, 1.0)
    C_hot = V_hot * RHO_CP * swing / 1000.0
    C_int = V_int * RHO_CP * swing / 1000.0
    C_low = V_low * RHO_CP * swing / 1000.0
    perdita_ora = (perdita_sett_pct / 100.0) / 168.0 if perdita_sett_pct > 0 else 0.0
    is_hp = (parallelo == "HP bassa T")

    P_alta = P_hp_alta_kw / 1000.0
    P_bassa = P_hp_bassa_kw / 1000.0
    P_bk = P_backup_kw / 1000.0

    q_hot_direct = np.zeros(n); q_alta = np.zeros(n); q_bassa = np.zeros(n)
    q_backup = np.zeros(n); el_alta = np.zeros(n); el_bassa = np.zeros(n)
    q_ground = np.zeros(n)
    non_cop = np.zeros(n); scarto_perso = np.zeros(n)
    cop_alta_s = np.zeros(n); cop_bassa_s = np.full(n, np.nan)
    ore_ground = 0

    soc_hot = soc_int = 0.0
    soc_low_bins = np.zeros(len(bin_T))
    for i in range(n):
        if perdita_ora > 0:
            soc_hot -= soc_hot * perdita_ora; soc_int -= soc_int * perdita_ora
            soc_low_bins *= (1.0 - perdita_ora)

        # --- carica accumuli con lo scarto ---
        ch = min(q_hot_arr[i], C_hot - soc_hot); soc_hot += ch
        scarto_perso[i] += max(q_hot_arr[i] - ch, 0.0)
        ci = min(q_int_arr[i], C_int - soc_int); soc_int += ci
        scarto_perso[i] += max(q_int_arr[i] - ci, 0.0)
        q_low_h = q_low_bins[i]                       # energia freddi per fascia, quest'ora
        if is_hp:
            soc_low_bins = soc_low_bins + q_low_h
            over = soc_low_bins.sum() - C_low
            if over > 1e-12:                          # capacità piena: scarta dalle fasce più FREDDE
                scarto_perso[i] += over
                for k in range(len(soc_low_bins)):
                    drop = min(soc_low_bins[k], over)
                    soc_low_bins[k] -= drop; over -= drop
                    if over <= 1e-12:
                        break
        else:
            scarto_perso[i] += float(q_low_h.sum())   # flussi freddi non sfruttati (gas/biomassa)

        dom = dom_arr[i]
        # --- accumulo caldo copre diretto in linea ---
        d_hot = min(dom, soc_hot); soc_hot -= d_hot; q_hot_direct[i] = d_hot
        residuo = dom - d_hot

        # --- HP alta T: intermedio → mandata ---
        cop_a = cop_singola(T_int - dT_evap, mandata, eta_hp)
        cop_alta_s[i] = cop_a
        if residuo > 1e-9 and P_alta > 0 and cop_a > 1:
            q_a_want = min(residuo, P_alta)
            E_a_want = q_a_want * (1.0 - 1.0 / cop_a)          # calore all'evaporatore alta T
            # l'intermedio può fornire: energia stoccata + (se HP) ciò che la bassa T aggiunge ora
            extra_bassa = P_bassa if is_hp else 0.0
            E_a = min(E_a_want, soc_int + extra_bassa)
            q_a = E_a / (1.0 - 1.0 / cop_a)
            # da dove viene E_a: prima dall'intermedio stoccato, poi dalla HP bassa T
            from_int = min(E_a, soc_int); soc_int -= from_int
            from_bassa = E_a - from_int
            if from_bassa > 1e-12 and is_hp and P_bassa > 0:
                # sorgente HP bassa: pesca dallo STRATO PIÙ CALDO dell'accumulo basso; se esaurito, dal suolo
                soc_tot = soc_low_bins.sum()
                g_T = max(soil_arr[i], antigelo)
                if soc_tot > 1e-9:
                    need = from_bassa; e_acc = 0.0; wt = 0.0
                    for k in range(len(bin_T) - 1, -1, -1):     # dal più caldo
                        take = min(soc_low_bins[k], need)
                        e_acc += take; wt += take * bin_T[k]; need -= take
                        if need <= 1e-12:
                            break
                    if need > 1e-12:                            # il resto lo darà il suolo
                        wt += need * g_T; e_acc += need
                    src_T = wt / e_acc if e_acc > 0 else g_T
                    src_is_ground = False
                else:
                    src_T = g_T; src_is_ground = True
                cop_b = cop_singola(src_T - dT_evap, T_int, eta_hp)
                cop_bassa_s[i] = cop_b
                q_b = from_bassa                                  # calore reso all'intermedio
                E_b = q_b * (1.0 - 1.0 / cop_b) if cop_b > 1 else q_b
                need = E_b                                        # preleva E_b dalle fasce più calde
                for k in range(len(soc_low_bins) - 1, -1, -1):
                    take = min(soc_low_bins[k], need)
                    soc_low_bins[k] -= take; need -= take
                    if need <= 1e-12:
                        break
                q_ground[i] = max(need, 0.0)                      # residuo preso dal suolo
                if src_is_ground or q_ground[i] > 1e-9:
                    ore_ground += 1
                q_bassa[i] = q_b
                el_bassa[i] = q_b / cop_b if cop_b > 0 else 0.0
            el_alta[i] = q_a / cop_a
            q_alta[i] = q_a
            residuo -= q_a

        # --- parallelo a combustibile: copre il residuo a mandata ---
        if not is_hp and residuo > 1e-9 and P_bk > 0:
            q_k = min(residuo, P_bk)
            q_backup[i] = q_k
            if backup_cop is not None and backup_cop > 0:
                el_bassa[i] = q_k / backup_cop        # (caso improbabile: backup elettrico)
            residuo -= q_k
        non_cop[i] = max(residuo, 0.0)

    E_hot = float(q_hot_direct.sum()); E_alta = float(q_alta.sum())
    E_bassa = float(q_bassa.sum()); E_bk = float(q_backup.sum())
    E_el_alta = float(el_alta.sum()); E_el_bassa = float(el_bassa.sum())
    cop_alta_medio = E_alta / E_el_alta if E_el_alta > 1e-9 else 0.0
    cop_bassa_medio = E_bassa / E_el_bassa if E_el_bassa > 1e-9 else 0.0
    return {
        "q_hot_direct": q_hot_direct, "q_alta": q_alta, "q_bassa": q_bassa, "q_backup": q_backup,
        "q_ground": q_ground, "E_ground": float(q_ground.sum()),
        "el_alta": el_alta, "el_bassa": el_bassa, "non_cop": non_cop,
        "cop_alta_s": cop_alta_s, "cop_bassa_s": cop_bassa_s,
        "E_hot_diretto": E_hot, "E_hp_alta": E_alta, "E_hp_bassa": E_bassa, "E_backup": E_bk,
        "E_el_alta": E_el_alta, "E_el_bassa": E_el_bassa, "E_el_tot": E_el_alta + E_el_bassa,
        "E_non_coperta": float(non_cop.sum()), "E_scarto_perso": float(scarto_perso.sum()),
        "cop_alta_medio": cop_alta_medio, "cop_bassa_medio": cop_bassa_medio,
        "ore_non_coperte": int((non_cop > 1e-6).sum()), "ore_ground": ore_ground,
    }


# =============================================================================
# MOTORE OFFERTA (generico, da tabella aziende) — funzioni pure, nessuna UI qui
# =============================================================================


def ottimizza_cascata(dom_arr, q_hot_arr, q_int_arr, q_low_bins, bin_T, soil_arr,
                      mandata, ritorno, T_int, dT_evap, eta_hp, parallelo,
                      capex_hp_func, capex_backup_kw, opex_backup_mwh, backup_cop,
                      prezzo_el, costo_m3, capex_solare_fisso, fattore_crf, perdita_func, antigelo):
    """
    Dimensiona P_hp_alta, P_hp_bassa, V_hot, V_int, V_low a LCOH minimo (costo annuo/domanda),
    copertura 100% e capacità FIRM (copre il picco anche con zero scarto).
    Le potenze sono fissate per firmness (la HP alta copre il picco; la bassa/caldaia alimenta
    ciò che serve al picco senza scarto); la griglia ottimizza i tre volumi.
    """
    dom_tot = float(dom_arr.sum())
    if dom_tot <= 0:
        return None
    picco_kw = float(dom_arr.max()) * 1000.0
    is_hp = (parallelo == "HP bassa T")
    cop_a_ref = float(cop_singola(T_int - dT_evap, mandata, eta_hp))
    frac_a = max(1.0 - 1.0 / cop_a_ref, 0.0)

    # potenze FIRM
    P_alta = picco_kw                              # la HP alta deve poter coprire il picco
    if is_hp:
        P_bassa = picco_kw * frac_a * 1.1          # alimenta l'intermedio al picco (via ground), +10% margine
        P_bk = 0.0
    else:
        P_bassa = 0.0
        P_bk = picco_kw                            # caldaia firm al picco

    ha_hot = float(q_hot_arr.sum()) > 1e-6
    v_hot_cands = [0.0, 300.0, 800.0] if ha_hot else [0.0]
    v_int_cands = [0.0, 400.0, 800.0, 1500.0]
    v_low_cands = [0.0, 400.0, 800.0] if is_hp else [0.0]

    def _valuta(v_hot, v_int, v_low):
        r = dispatch_cascata(dom_arr, q_hot_arr, q_int_arr, q_low_bins, bin_T, soil_arr,
                             mandata, ritorno, T_int, dT_evap, eta_hp,
                             v_hot, v_int, v_low, P_alta, P_bassa,
                             parallelo=parallelo, P_backup_kw=P_bk, backup_cop=backup_cop,
                             antigelo=antigelo, perdita_sett_pct=perdita_func(max(v_int, v_low, v_hot)))
        capex = (P_alta * capex_hp_func(P_alta)
                 + (P_bassa * capex_hp_func(P_bassa) if is_hp else P_bk * capex_backup_kw)
                 + (v_hot + v_int + v_low) * costo_m3 + capex_solare_fisso)
        opex = r["E_el_tot"] * prezzo_el + r["E_backup"] * opex_backup_mwh
        lcoh = (capex * fattore_crf + opex) / dom_tot
        # consegnato in rete = caldo diretto + HP alta + backup (E_hp_bassa è interno all'intermedio).
        # rinnovabile = caldo diretto + HP alta (include il recupero via HP bassa) + biomassa.
        E_fer = r["E_hot_diretto"] + r["E_hp_alta"] + (r["E_backup"] if parallelo == "biomassa" else 0.0)
        fer = E_fer / dom_tot * 100
        return {"v_hot": v_hot, "v_int": v_int, "v_low": v_low, "P_alta": P_alta, "P_bassa": P_bassa,
                "P_bk": P_bk, "lcoh": lcoh, "quota_fer": fer,
                "E_hot": r["E_hot_diretto"], "E_alta": r["E_hp_alta"], "E_bassa": r["E_hp_bassa"],
                "E_backup": r["E_backup"], "E_el": r["E_el_tot"], "ore_scoperte": r["ore_non_coperte"],
                "cop_alta": r["cop_alta_medio"], "cop_bassa": r["cop_bassa_medio"], "capex": capex}

    best = None
    for vh in v_hot_cands:
        for vi in v_int_cands:
            for vl in v_low_cands:
                r = _valuta(vh, vi, vl)
                if r["ore_scoperte"] == 0 and (best is None or r["lcoh"] < best["lcoh"]):
                    best = r
    if best is None:   # se nessuna combinazione copre il 100%, prendi la meno peggio
        for vh in v_hot_cands:
            for vi in v_int_cands:
                for vl in v_low_cands:
                    r = _valuta(vh, vi, vl)
                    if best is None or r["ore_scoperte"] < best.get("ore_scoperte", 1e9) or \
                       (r["ore_scoperte"] == best["ore_scoperte"] and r["lcoh"] < best["lcoh"]):
                        best = r
    return best


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
    try:
        _coord = pd.read_csv("edifici_pubblici_coordinate.csv")[["edificio", "lat", "lon", "indirizzo"]]
        buildings = buildings.merge(_coord, on="edificio", how="left")
    except Exception:
        buildings["lat"] = np.nan; buildings["lon"] = np.nan; buildings["indirizzo"] = ""
    domanda = pd.read_csv("maniago_domanda_oraria_8760h_HDD_reale.csv", parse_dates=["datetime"])
    domanda = domanda.merge(buildings[["edificio", "cluster", "tipologia", "tipo_utenza"]], on="edificio", how="left")
  # guardia contro il mismatch calendario domanda vs offerta
    assert len(HOURS_2024) == 8784, f"HOURS_2024 dovrebbe avere 8784 ore (2024 bisestile), ne ha {len(HOURS_2024)}"
    if not domanda["datetime"].isin(HOURS_2024).all():
      n_orfani = (~domanda["datetime"].isin(HOURS_2024)).sum()
      st.warning(f"⚠️ {n_orfani} timestamp della domanda non trovano riscontro in HOURS_2024: "
                 f"verranno silenziosamente esclusi dai bilanci. "
                 f"Rigenerare maniago_domanda_oraria_8760h_HDD_reale.csv su 2024 (8784 ore).")
    flussi = pd.read_csv("maniago_flussi_offerta.csv")
    flussi["id_flusso"] = flussi["azienda"] + " · " + flussi["flusso"]
    pvgis = pd.read_csv("pvgis_maniago_pulito.csv", parse_dates=["datetime"])
    # zona geografica dai confini disegnati.
    # NB: le righe "Residenziale Zona ..." sono vecchie stime aggregate dei privati, ora sostituite
    # dai footprint GeoJSON: le escludiamo per non contare due volte la domanda.
    buildings = buildings[~buildings["edificio"].str.startswith("Residenziale Zona")].copy()
    _zp = carica_zone_confini()
    if not _zp:
        st.error("⚠️ File **TLR_zones_borders.geojson** non trovato nella cartella dell'app: "
                 "le zone restano quelle vecchie e i filtri appariranno vuoti. "
                 "Copia i file .geojson e maniago_privati_edifici.csv accanto a provaTLRManiago.py.")
    if _zp:
        _centri = {ZONE_NOMI[z]: (np.mean([r[:, 1].mean() for r in a]), np.mean([r[:, 0].mean() for r in a]))
                   for z, a in _zp.items()}
        _out = []
        for r in buildings.itertuples():
            z = zona_da_coordinate(r.lat, r.lon, _zp)
            if z is None and not (r.lat is None or (isinstance(r.lat, float) and np.isnan(r.lat))):
                # fuori dai poligoni ma con coordinate → zona con centro più vicino
                z = min(_centri, key=lambda k: (_centri[k][0] - r.lat) ** 2 + (_centri[k][1] - r.lon) ** 2)
            _out.append(z if z else "Zona 4 - Centro")
        buildings["cluster"] = _out
        # frazione di Campagna: fuori analisi (isolata, non allacciabile in modo sensato)
        _esclusi = buildings["cluster"] == "__ESCLUSO__"
        if _esclusi.any():
            buildings = buildings[~_esclusi].copy()
    else:
        # senza confini: mappo comunque i vecchi nomi sui nuovi, così i default restano validi
        buildings["cluster"] = buildings["cluster"].replace({
            "NE-Centro": "Zona 1 - Comune NE", "Ex Bioman": "Zona 2 - Ex Bioman",
            "Campagna": "Zona 3 - Sud", "Ovest": "Zona 5 - Ovest"})
    domanda = domanda[domanda["edificio"].isin(buildings["edificio"])].copy()
    domanda = domanda.drop(columns=["cluster"], errors="ignore").merge(
        buildings[["edificio", "cluster"]], on="edificio", how="left")

    # --- PRIVATI (footprint GeoJSON): singoli edifici per la mappa, domanda oraria aggregata
    #     per zona × livello di estensione (2941 × 8760 sarebbe troppo pesante).
    try:
        priv = pd.read_csv("maniago_privati_edifici.csv")
    except Exception:
        priv = pd.DataFrame(columns=["edificio", "cluster", "anello", "lat", "lon",
                                     "MWh_SH", "MWh_ACS", "consumo_annuo_MWh", "tipo_utenza"])
    if not priv.empty:
        # profilo orario RESIDENZIALE: la forma delle utenze occupate 24h (RSA) è molto più
        # vicina a un'abitazione rispetto alla media dei pubblici (scuole/uffici, vuoti di notte).
        _res = domanda[domanda["tipologia"].astype(str).str.contains("RSA", na=False)]
        _base = _res if not _res.empty else domanda
        _p = _base.groupby("datetime")[["MWh_riscaldamento", "MWh_ACS"]].sum()
        _p = _p.reindex(domanda["datetime"].drop_duplicates().sort_values(), fill_value=0.0)
        _f_sh = (_p["MWh_riscaldamento"] / _p["MWh_riscaldamento"].sum()).values
        _f_acs_src = domanda.groupby("datetime")["MWh_ACS"].sum()
        _f_acs = (_f_acs_src / _f_acs_src.sum()).values
        _idx = _p.index
        _agg = priv.groupby(["cluster", "anello"])[["MWh_SH", "MWh_ACS"]].sum().reset_index()
        _righe = []
        for r in _agg.itertuples():
            _nome = f"Privati {r.cluster} · est.{int(r.anello)}"
            _righe.append(pd.DataFrame({
                "datetime": _idx, "edificio": _nome,
                "MWh_riscaldamento": _f_sh * r.MWh_SH, "MWh_ACS": _f_acs * r.MWh_ACS,
                "cluster": r.cluster, "tipologia": "Residenziale privato",
                "tipo_utenza": "Privato (potenziale)"}))
            buildings = pd.concat([buildings, pd.DataFrame([{
                "edificio": _nome, "cluster": r.cluster, "tipologia": "Residenziale privato",
                "consumo_annuo_MWh": r.MWh_SH + r.MWh_ACS, "tipo_utenza": "Privato (potenziale)",
                "anello": int(r.anello), "lat": np.nan, "lon": np.nan}])], ignore_index=True)
        domanda = pd.concat([domanda] + _righe, ignore_index=True)
    # --- CONDOMINI censiti dal Comune (anagrafica reale: unità, amministratore)
    try:
        cond = pd.read_csv("maniago_condomini.csv")
    except Exception:
        cond = pd.DataFrame(columns=["cluster", "unita"])
    if not cond.empty and not priv.empty:
        _pubb = domanda[domanda["tipo_utenza"] == "Pubblico"]
        _res2 = _pubb[_pubb["tipologia"].astype(str).str.contains("RSA", na=False)]
        _b2 = _res2 if not _res2.empty else _pubb
        _p = _b2.groupby("datetime")[["MWh_riscaldamento", "MWh_ACS"]].sum()
        _idx = _p.index
        _f_sh = (_p["MWh_riscaldamento"] / _p["MWh_riscaldamento"].sum()).values
        _acs_src = _pubb.groupby("datetime")["MWh_ACS"].sum().reindex(_idx, fill_value=0.0)
        _f_acs = (_acs_src / _acs_src.sum()).values
        _righe_c = []
        for _z, _g in cond.groupby("cluster"):
            _u = float(_g["unita"].sum())
            _e = _u * MWH_PER_UNITA          # baseline: scalabile dall'interfaccia
            _nome = f"Condomini {_z}"
            _righe_c.append(pd.DataFrame({
                "datetime": _idx, "edificio": _nome,
                "MWh_riscaldamento": _f_sh * _e * 0.85, "MWh_ACS": _f_acs * _e * 0.15,
                "cluster": _z, "tipologia": "Condominio censito", "tipo_utenza": "Condominio"}))
            buildings = pd.concat([buildings, pd.DataFrame([{
                "edificio": _nome, "cluster": _z, "tipologia": "Condominio censito",
                "consumo_annuo_MWh": _e, "tipo_utenza": "Condominio", "anello": 0,
                "unita": _u, "lat": np.nan, "lon": np.nan}])], ignore_index=True)
        domanda = pd.concat([domanda] + _righe_c, ignore_index=True)
    buildings["anello"] = buildings.get("anello", pd.Series(index=buildings.index, dtype=float)).fillna(0).astype(int)
    return buildings, domanda, flussi, pvgis, priv, cond


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

def crf(rate, anni):
    """Capital Recovery Factor: quota annua di ammortamento del CAPEX a tasso r su n anni."""
    if anni <= 0:
        return 1.0
    if rate <= 0:
        return 1.0 / anni
    return rate / (1.0 - (1.0 + rate) ** (-anni))

buildings, domanda, flussi, pvgis, privati, condomini = load_data()

st.title("🔥 Maniago TLR — Domanda, Offerta, Dimensionamento")
st.caption(
    "Anno tipo (calendario 2024) · Domanda: temperatura calibrata su dati reali stazione Vivaro "
    "(anno 2011, corretto verso i 2.850 GG ufficiali di Maniago) · Tutto calcolato live, un solo file."
)

tab_domanda, tab_offerta, tab_dimensionamento, tab_confronto, tab_economia = st.tabs(
    ["🏠 Domanda", "♻️ Offerta", "🧮 Dimensionamento", "📊 Confronto scenari", "💶 Analisi economica"]
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

        st.markdown("#### Zone e utenze")
        clusters = sorted(buildings["cluster"].unique())
        CLUSTER_COLORS = build_cluster_color_map(clusters)
        selected_clusters, sel_priv_zone, sel_cond_zone = [], [], []
        for c in clusters:
            on = st.checkbox(c, value=(c in ZONE_DEFAULT), key=f"dom_cl_{c}")
            if not on:
                continue
            selected_clusters.append(c)
            _ha_p = (not privati.empty) and bool((privati["cluster"] == c).any())
            _ha_c = (not condomini.empty) and bool((condomini["cluster"] == c).any())
            cc1, cc2 = st.columns(2)
            if _ha_p and cc1.checkbox("privati", key=f"dom_p_{c}",
                                      help="Tutti i residenziali da footprint GIS in questa zona"):
                sel_priv_zone.append(c)
            if _ha_c and cc2.checkbox("condomini", key=f"dom_c_{c}",
                                      help="Solo i condomini censiti dal Comune (n. unità reale)"):
                sel_cond_zone.append(c)
        # i condomini censiti sono un sottoinsieme dei privati GIS: evito il doppio conteggio
        _conf = sorted(set(sel_priv_zone) & set(sel_cond_zone))
        if _conf:
            sel_cond_zone = [z for z in sel_cond_zone if z not in _conf]
            st.caption("⚠️ In " + ", ".join(z.split(" - ")[0] for z in _conf) +
                       " i condomini sono già dentro i privati GIS: conto solo i privati.")

        st.markdown("**Utenza pubblica**")
        pub_on = st.checkbox("Includi edifici pubblici", value=True, key="dom_tu_pub")

        fattore_correzione = 100
        if sel_priv_zone:
            fattore_correzione = st.slider(
                "Tasso di allacciamento privati (%)", 10, 100, 60, step=5, key="dom_priv_fattore",
                help="Quota di privati che si allaccia davvero: la domanda GIS è un potenziale tecnico "
                     "e tende a sovrastimare.")
        mwh_unita = MWH_PER_UNITA
        tasso_cond = 100
        if sel_cond_zone:
            mwh_unita = st.slider("Consumo per unità abitativa (MWh/a)", 5.0, 15.0, MWH_PER_UNITA, step=0.5,
                                  key="dom_mwh_unita", help="Appartamento tipo esistente in FVG: 7-11 MWh/a.")
            tasso_cond = st.slider("Tasso di adesione condomini (%)", 10, 100, 80, step=5,
                                   key="dom_cond_tasso",
                                   help="I condomini censiti sono i candidati più realistici e concentrati.")

        selected_privati = []
        if sel_priv_zone:
            selected_privati += buildings.loc[(buildings["tipo_utenza"] == "Privato (potenziale)")
                                              & (buildings["cluster"].isin(sel_priv_zone)), "edificio"].tolist()
        if sel_cond_zone:
            selected_privati += buildings.loc[(buildings["tipo_utenza"] == "Condominio")
                                              & (buildings["cluster"].isin(sel_cond_zone)), "edificio"].tolist()
        liv_est = 6 if sel_priv_zone else 0

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
                     & (((buildings["tipo_utenza"] == "Pubblico") & pub_on
                         & buildings["tipologia"].isin(selected_tip))
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
    # condomini: scalo per consumo/unità scelto e tasso di adesione
    is_cond = dom["tipo_utenza"] == "Condominio"
    fatt_c = (mwh_unita / MWH_PER_UNITA) * (tasso_cond / 100.0)
    dom.loc[is_cond, "MWh_riscaldamento"] = dom.loc[is_cond, "MWh_riscaldamento"] * fatt_c
    dom.loc[is_cond, "MWh_ACS"] = dom.loc[is_cond, "MWh_ACS"] * fatt_c

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

            # --- Mappa degli edifici serviti ---
            bsel = buildings[buildings["edificio"].isin(selected_buildings)].copy()
            bsel_all = buildings[buildings["tipo_utenza"] == "Pubblico"].copy()
            bmap = bsel.dropna(subset=["lat", "lon"]) if "lat" in bsel.columns else bsel.iloc[0:0]
            if not bmap.empty:
                st.markdown("##### 🗺️ Mappa degli edifici serviti")
                fig_map = go.Figure()
                # confini delle zone (contorni colorati, sotto ai punti)
                for _zid, _anelli in carica_zone_confini().items():
                    _nome = ZONE_NOMI.get(_zid, f"Zona {_zid}")
                    _att = _nome in selected_clusters
                    for _r in _anelli:
                        fig_map.add_trace(go.Scattermapbox(
                            lat=list(_r[:, 1]) + [_r[0, 1]], lon=list(_r[:, 0]) + [_r[0, 0]],
                            mode="lines", name=f"confine {_nome}", legendgroup=f"z{_zid}",
                            showlegend=False, hoverinfo="skip",
                            line=dict(width=2.5 if _att else 1,
                                      color=ZONA_COLORI.get(_nome, "#888888")),
                            opacity=0.95 if _att else 0.35))
                for cl in selected_clusters:
                    sub = bmap[bmap["cluster"] == cl]
                    if sub.empty:
                        continue
                    fig_map.add_trace(go.Scattermapbox(
                        lat=sub["lat"], lon=sub["lon"], mode="markers", name=cl,
                        marker=dict(size=(sub["consumo_annuo_MWh"].clip(lower=1) ** 0.5) * 2.5 + 7,
                                    color=CLUSTER_COLORS.get(cl, "#888888")),
                        text=(sub["edificio"] + "<br>" + sub["indirizzo"].fillna("").astype(str)
                              + "<br>" + sub["consumo_annuo_MWh"].round(0).astype(int).astype(str) + " MWh/a"),
                        hoverinfo="text"))
                # privati delle sole zone in cui sono stati spuntati
                if sel_priv_zone and not privati.empty:
                    _pv = privati[privati["cluster"].isin(sel_priv_zone)]
                    if not _pv.empty:
                        fig_map.add_trace(go.Scattermapbox(
                            lat=_pv["lat"], lon=_pv["lon"], mode="markers",
                            name=f"Privati: {len(_pv)}",
                            marker=dict(size=6, color="#B57EDC", opacity=0.75),
                            text=(_pv["nome"].fillna("").astype(str) + "<br>" + _pv["via"].fillna("").astype(str)
                                  + "<br>est." + _pv["anello"].astype(str) + " · "
                                  + _pv["consumo_annuo_MWh"].round(1).astype(str) + " MWh/a"),
                            hoverinfo="text"))
                fig_map.update_layout(
                    mapbox=dict(style="open-street-map",
                                center=dict(lat=float(bmap["lat"].mean()), lon=float(bmap["lon"].mean())), zoom=13),
                    height=430, margin=dict(t=10, b=0, l=0, r=0),
                    legend=dict(orientation="h", yanchor="bottom", y=1.01))
                st.plotly_chart(fig_map, use_container_width=True)
                _senza = bsel.shape[0] - bmap.shape[0]
                if _senza > 0:
                    st.caption(f"{_senza} edifici senza coordinate non mostrati.")

                # --- Mappa di densità della domanda termica ---
                st.markdown("##### 🔥 Densità della domanda termica")
                dc1, dc2 = st.columns([2, 1])
                vista_dens = dc1.radio("Cosa mostrare",
                                       ["Potenziale totale (tutti gli edifici)", "Solo selezionati"],
                                       horizontal=True, key="dom_dens_vista",
                                       help="Il potenziale totale serve a decidere DOVE conviene estendere: "
                                            "mostra la densità a prescindere da cosa hai spuntato.")
                cella_m = dc2.select_slider("Cella (m)", options=[100, 150, 200], value=150, key="dom_dens_cella")
                _pts = []
                if vista_dens.startswith("Potenziale"):
                    if not privati.empty:
                        _pts.append(privati[["lat", "lon", "consumo_annuo_MWh"]])
                    _pts.append(bsel_all[["lat", "lon", "consumo_annuo_MWh"]].dropna(subset=["lat", "lon"]))
                else:
                    _pts.append(bmap[["lat", "lon", "consumo_annuo_MWh"]])
                    if sel_priv_zone and not privati.empty:
                        _q = privati[privati["cluster"].isin(sel_priv_zone)].copy()
                        _q["consumo_annuo_MWh"] = _q["consumo_annuo_MWh"] * fattore_correzione / 100.0
                        _pts.append(_q[["lat", "lon", "consumo_annuo_MWh"]])
                _pts = pd.concat(_pts, ignore_index=True).dropna(subset=["lat", "lon"])
                if _pts.empty:
                    st.info("Nessun edificio georeferenziato da mostrare.")
                else:
                    _la0 = float(_pts["lat"].mean())
                    _dy = cella_m / 111320.0
                    _dx = cella_m / (111320.0 * np.cos(np.radians(_la0)))
                    _gi = ((_pts["lat"] - _pts["lat"].min()) / _dy).astype(int)
                    _gj = ((_pts["lon"] - _pts["lon"].min()) / _dx).astype(int)
                    _grid = (_pts.assign(gi=_gi, gj=_gj)
                             .groupby(["gi", "gj"])
                             .agg(MWh=("consumo_annuo_MWh", "sum"), lat=("lat", "mean"), lon=("lon", "mean"))
                             .reset_index())
                    _ha = (cella_m / 100.0) ** 2
                    _grid["dens"] = _grid["MWh"] / _ha
                    fig_dens = go.Figure(go.Densitymapbox(
                        lat=_grid["lat"], lon=_grid["lon"], z=_grid["dens"],
                        radius=max(18, int(cella_m / 6)), colorscale="Turbo", opacity=0.75,
                        colorbar=dict(title="MWh/(ha·a)"),
                        hovertemplate="%{z:.0f} MWh/(ha·a)<extra></extra>"))
                    for _zid, _anelli in carica_zone_confini().items():
                        _nm = ZONE_NOMI.get(_zid, "")
                        for _r in _anelli:
                            fig_dens.add_trace(go.Scattermapbox(
                                lat=list(_r[:, 1]) + [_r[0, 1]], lon=list(_r[:, 0]) + [_r[0, 0]],
                                mode="lines", showlegend=False, hoverinfo="skip",
                                line=dict(width=1.5, color=ZONA_COLORI.get(_nm, "#888")), opacity=0.8))
                    fig_dens.update_layout(
                        mapbox=dict(style="carto-darkmatter",
                                    center=dict(lat=_la0, lon=float(_pts["lon"].mean())), zoom=12.6),
                        height=460, margin=dict(t=10, b=0, l=0, r=0))
                    st.plotly_chart(fig_dens, use_container_width=True)
                    _q90 = _grid["dens"].quantile(0.9)
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Densità mediana", f"{_grid['dens'].median():.0f} MWh/(ha·a)")
                    m2.metric("Celle sopra 300", f"{(_grid['dens'] > 300).mean()*100:.0f}%",
                              help="Sopra ~300 MWh/(ha·a) il TLR è generalmente favorevole; 100-300 media; sotto 100 rada")
                    m3.metric("Energia nelle celle dense", f"{_grid.loc[_grid['dens'] > 300, 'MWh'].sum()/_grid['MWh'].sum()*100:.0f}%",
                              help="Quota di domanda concentrata nelle celle sopra 300 MWh/(ha·a)")
                    st.caption(f"Griglia da {cella_m} m ({_ha:.2f} ha per cella). Le aree calde sono quelle dove il "
                               f"TLR rende di più: è lì che conviene tracciare la dorsale.")


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
        st.divider()
        # --- Densità termica lineare per zona ed estensione ---
        if not privati.empty:
            st.markdown("##### 📏 Densità termica lineare (quanto rende il tubo)")
            st.caption("Per ogni zona e livello di estensione: lunghezza indicativa della rete "
                       "(albero minimo tra gli edifici × tortuosità 1,35) e **densità lineare** = "
                       "MWh/anno per metro di rete. È l'indicatore chiave di fattibilità del TLR: "
                       "sotto ~1,2 MWh/(m·a) la rete fatica a ripagarsi, sopra ~2 è buona.")
            cD1, cD2 = st.columns(2)
            costo_m_rete = cD1.slider("Costo rete (€/m di trincea)", 200, 1500, 600, step=50,
                                      key="dom_costo_rete",
                                      help="Posa di tubazione preisolata in trincea, valore tipico per centro urbano.")
            righe_d = []
            for _z in (sel_priv_zone or selected_clusters):
                _pz2 = privati[privati["cluster"] == _z]
                if _pz2.empty:
                    continue
                for _l in [a for a in range(1, 7) if (_pz2["anello"] <= a).any()]:
                    _s = _pz2[_pz2["anello"] <= _l]
                    if _s.empty:
                        continue
                    _L = stima_lunghezza_rete(_s["lat"].values, _s["lon"].values)
                    _E = _s["consumo_annuo_MWh"].sum() * (fattore_correzione / 100.0)
                    if _L < 1:
                        continue
                    righe_d.append({"Zona": _z, "Livello": _l, "Edifici": len(_s),
                                    "Domanda (MWh/a)": round(_E), "Rete (m)": round(_L),
                                    "Densità (MWh/m·a)": round(_E / _L, 2),
                                    "CAPEX rete (€)": round(_L * costo_m_rete)})
            if righe_d:
                df_d = pd.DataFrame(righe_d)
                fig_d = go.Figure()
                for _z in df_d["Zona"].unique():
                    _sub = df_d[df_d["Zona"] == _z]
                    fig_d.add_trace(go.Scatter(x=_sub["Livello"], y=_sub["Densità (MWh/m·a)"],
                                               mode="lines+markers", name=_z,
                                               line=dict(color=CLUSTER_COLORS.get(_z, "#888"), width=2.5),
                                               marker=dict(size=9)))
                fig_d.add_hline(y=2.0, line_dash="dot", line_color="#3FA34D",
                                annotation_text="buona (2,0)", annotation_position="top left")
                fig_d.add_hline(y=1.2, line_dash="dot", line_color="#E63946",
                                annotation_text="soglia critica (1,2)", annotation_position="bottom left")
                fig_d.update_layout(height=350, xaxis_title="Livello di estensione",
                                    yaxis_title="Densità lineare (MWh per metro di rete, anno)",
                                    legend=dict(orientation="h", yanchor="bottom", y=1.02),
                                    margin=dict(t=30, b=10))
                st.plotly_chart(fig_d, use_container_width=True)
                st.dataframe(df_d, use_container_width=True, hide_index=True)
                _tot_L = df_d[df_d["Livello"] == max(liv_est, 1)]["Rete (m)"].sum()
                if liv_est > 0 and _tot_L > 0:
                    st.caption(f"Al livello **{liv_est}** nelle zone attive: rete ≈ **{_tot_L:,.0f} m**, "
                               f"CAPEX rete ≈ **{_tot_L*costo_m_rete:,.0f} €** "
                               f"(non incluso nel LCOH di produzione della scheda Dimensionamento).".replace(",", "."))

        # --- Elenco dei condomini selezionati ---
        if sel_cond_zone and not condomini.empty:
            st.divider()
            st.markdown("##### 🏢 Condomini censiti nelle zone selezionate")
            _cs = condomini[condomini["cluster"].isin(sel_cond_zone)].copy()
            _cs["MWh/a stimati"] = (_cs["unita"] * mwh_unita * tasso_cond / 100.0).round(1)
            cq1, cq2, cq3 = st.columns(3)
            cq1.metric("Condomini", f"{len(_cs)}")
            cq2.metric("Unità abitative", f"{_cs['unita'].sum():,.0f}".replace(",", "."))
            cq3.metric("Domanda stimata", f"{_cs['MWh/a stimati'].sum():,.0f} MWh/a".replace(",", "."),
                       help=f"{mwh_unita} MWh per unità · adesione {tasso_cond}%")
            _tab = _cs[["cluster", "via", "civico", "denominazione", "amministratore", "unita", "MWh/a stimati"]]
            _tab = _tab.rename(columns={"cluster": "Zona", "via": "Via", "civico": "Civico",
                                        "denominazione": "Denominazione", "amministratore": "Amministratore",
                                        "unita": "Unità"}).sort_values(["Zona", "Unità"], ascending=[True, False])
            st.dataframe(_tab, use_container_width=True, hide_index=True)

        # --- Ipotesi di tracciato della rete dalla sottocentrale ---
        st.divider()
        st.markdown("##### 🛤️ Ipotesi di tracciato della rete")
        st.caption(f"Rete ad albero minimo che parte dalla **sottocentrale** "
                   f"({CENTRALE_LAT:.4f}, {CENTRALE_LON:.4f}, area industriale presso ZML/Pandolfo) e "
                   f"raggiunge le utenze selezionate. È un'ipotesi di ordine di grandezza: il tracciato "
                   f"reale segue le strade, qui le lunghezze sono maggiorate del fattore di tortuosità.")
        _tr = []
        if not bmap.empty:
            _tr.append(bmap[["lat", "lon", "consumo_annuo_MWh"]])
        if sel_priv_zone and not privati.empty:
            _tr.append(privati[privati["cluster"].isin(sel_priv_zone)][["lat", "lon", "consumo_annuo_MWh"]])
        _tr = pd.concat(_tr, ignore_index=True).dropna(subset=["lat", "lon"]) if _tr else pd.DataFrame()
        if _tr.empty:
            st.info("Seleziona almeno un'utenza georeferenziata per vedere il tracciato.")
        else:
            tc1, tc2 = st.columns(2)
            tort = tc1.slider("Fattore di tortuosità", 1.0, 2.0, 1.35, step=0.05, key="dom_tort",
                              help="I tubi seguono le strade: 1,35 è un valore tipico urbano.")
            costo_m_tr = tc2.slider("Costo rete (€/m)", 200, 1500, 600, step=50, key="dom_costo_tr")
            _archi, _len = mst_archi(_tr["lat"].values, _tr["lon"].values,
                                     radice=(CENTRALE_LAT, CENTRALE_LON))
            _len_t = _len * tort
            _lat_l, _lon_l = [], []
            for (a, b, _d) in _archi:
                _lat_l += [a[0], b[0], None]; _lon_l += [a[1], b[1], None]
            fig_tr = go.Figure()
            fig_tr.add_trace(go.Scattermapbox(lat=_lat_l, lon=_lon_l, mode="lines",
                                              line=dict(width=2, color="#FF4B4B"),
                                              name="Tracciato ipotizzato", hoverinfo="skip"))
            fig_tr.add_trace(go.Scattermapbox(
                lat=_tr["lat"], lon=_tr["lon"], mode="markers", name="Utenze",
                marker=dict(size=5, color="#22C3DD", opacity=0.7),
                text=_tr["consumo_annuo_MWh"].round(1).astype(str) + " MWh/a", hoverinfo="text"))
            for _n, (_la, _lo) in AZIENDE_COORD.items():
                fig_tr.add_trace(go.Scattermapbox(lat=[_la], lon=[_lo], mode="markers",
                                                  name=_n, marker=dict(size=9, color="#F5C518"),
                                                  text=_n, hoverinfo="text", showlegend=False))
            fig_tr.add_trace(go.Scattermapbox(
                lat=[CENTRALE_LAT], lon=[CENTRALE_LON], mode="markers+text", name="Sottocentrale",
                marker=dict(size=18, color="#FF9F1C"), text=["CENTRALE"], textposition="top right",
                textfont=dict(size=13, color="#FF9F1C")))
            _clat = (float(_tr["lat"].mean()) + CENTRALE_LAT) / 2
            _clon = (float(_tr["lon"].mean()) + CENTRALE_LON) / 2
            fig_tr.update_layout(mapbox=dict(style="open-street-map",
                                             center=dict(lat=_clat, lon=_clon), zoom=12.2),
                                 height=560, margin=dict(t=10, b=0, l=0, r=0),
                                 legend=dict(orientation="h", yanchor="bottom", y=1.01))
            st.plotly_chart(fig_tr, use_container_width=True)
            _dom_tr = float(_tr["consumo_annuo_MWh"].sum())
            t1, t2, t3, t4 = st.columns(4)
            t1.metric("Lunghezza rete", f"{_len_t/1000:.1f} km", help=f"{_len_t:,.0f} m con tortuosità {tort}".replace(",", "."))
            t2.metric("Utenze collegate", f"{len(_tr):,}".replace(",", "."))
            t3.metric("CAPEX rete", f"{_len_t*costo_m_tr/1e6:.1f} M€")
            t4.metric("Densità lineare", f"{_dom_tr/_len_t:.2f} MWh/(m·a)",
                      help="sotto ~1,2 la rete fatica a ripagarsi; sopra ~2 è buona")
            st.session_state["_rete_info"] = {
                "lunghezza_m": float(_len_t), "capex_rete": float(_len_t * costo_m_tr),
                "densita": float(_dom_tr / _len_t), "n_utenze": int(len(_tr)),
                "costo_m": int(costo_m_tr), "traccia_lat": _lat_l, "traccia_lon": _lon_l,
                "pt_lat": _tr["lat"].tolist(), "pt_lon": _tr["lon"].tolist(),
            }


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
        st.markdown("#### 🏭 Sorgenti di scarto e sottocentrale")
        st.caption(f"La **sottocentrale** (HP + accumuli) è ipotizzata in area industriale presso "
                   f"ZML/Pandolfo: è lì che conviene, perché il calore di scarto a bassa temperatura "
                   f"richiede portate elevate e va sollevato subito prima di essere trasportato in città.")
        _sel_az = sorted(set(a for a in AZIENDE_COORD if not off.empty
                             and off["azienda"].astype(str).str.startswith(a).any())) if not off.empty else []
        _pw = (off.groupby("azienda")["MWh"].sum() if not off.empty else pd.Series(dtype=float))
        fig_src = go.Figure()
        for _n, (_la, _lo) in AZIENDE_COORD.items():
            _match = [k for k in _pw.index if str(k).startswith(_n)]
            _e = float(_pw[_match].sum()) if _match else 0.0
            _att = _e > 0
            fig_src.add_trace(go.Scattermapbox(
                lat=[_la, CENTRALE_LAT], lon=[_lo, CENTRALE_LON], mode="lines",
                line=dict(width=(2 + 6 * min(_e / max(_pw.sum(), 1), 1)) if _att else 1,
                          color=COLOR_OFFERTA if _att else "#666666"),
                showlegend=False, hoverinfo="skip", opacity=0.9 if _att else 0.35))
            fig_src.add_trace(go.Scattermapbox(
                lat=[_la], lon=[_lo], mode="markers+text",
                marker=dict(size=(12 + 22 * min(_e / max(_pw.sum(), 1), 1)) if _att else 10,
                            color=COLOR_OFFERTA if _att else "#777777"),
                text=[_n], textposition="top right", textfont=dict(size=12, color="#DDDDDD"),
                name=_n, hovertext=[f"{_n}<br>{_e:,.0f} MWh/a nel periodo".replace(",", ".")
                                    if _att else f"{_n}<br>nessun flusso selezionato"],
                hoverinfo="text", showlegend=False))
        fig_src.add_trace(go.Scattermapbox(
            lat=[CENTRALE_LAT], lon=[CENTRALE_LON], mode="markers+text",
            marker=dict(size=20, color="#FF9F1C"), text=["SOTTOCENTRALE"], textposition="bottom center",
            textfont=dict(size=13, color="#FF9F1C"), name="Sottocentrale",
            hovertext=[f"Sottocentrale<br>{CENTRALE_LAT:.4f}, {CENTRALE_LON:.4f}"], hoverinfo="text",
            showlegend=False))
        fig_src.update_layout(
            mapbox=dict(style="open-street-map",
                        center=dict(lat=np.mean([v[0] for v in AZIENDE_COORD.values()] + [CENTRALE_LAT]),
                                    lon=np.mean([v[1] for v in AZIENDE_COORD.values()] + [CENTRALE_LON])),
                        zoom=14.2),
            height=430, margin=dict(t=10, b=0, l=0, r=0))
        st.plotly_chart(fig_src, use_container_width=True)
        if not off.empty:
            _R = 6371000.0
            _dist = {n: _R * np.hypot(np.radians(v[0] - CENTRALE_LAT),
                                      np.radians(v[1] - CENTRALE_LON) * np.cos(np.radians(46.15)))
                     for n, v in AZIENDE_COORD.items()}
            _rows = []
            for _n in AZIENDE_COORD:
                _m = [k for k in _pw.index if str(k).startswith(_n)]
                if not _m:
                    continue
                _rows.append({"Azienda": _n, "Energia periodo (MWh)": round(float(_pw[_m].sum())),
                              "Distanza dalla centrale (m)": round(_dist[_n])})
            if _rows:
                st.dataframe(pd.DataFrame(_rows).sort_values("Energia periodo (MWh)", ascending=False),
                             use_container_width=True, hide_index=True)
        st.divider()

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

    st.divider()
    st.markdown("#### 🌡️ Temperatura oraria della sorgente (per l'accumulo basso / HP)")
    st.caption("Per ogni ora, la **T media** (pesata sull'energia dei flussi disponibili) e la **T max** "
               "dello scarto: è la sorgente che carica l'accumulo basso e alimenta la HP bassa T. "
               "Curva di durata (ore ordinate dalla T più alta).")
    off_t = off[off["T_disponibile"].notna() & (off["MWh"] > 0)].copy()
    if off_t.empty:
        st.info("Nessun flusso con temperatura disponibile nel periodo.")
    else:
        off_t["Tw"] = off_t["T_disponibile"] * off_t["MWh"]
        g = off_t.groupby("datetime")
        T_media = g["Tw"].sum() / g["MWh"].sum()      # per ora: media pesata sull'energia
        T_max = g["T_disponibile"].max()               # per ora: massima
        kt1, kt2, kt3 = st.columns(3)
        kt1.metric("T media oraria", f"{T_media.mean():.0f}°C",
                   help="media nel tempo della T pesata sull'energia di ogni ora (≤ T max, ora coerente)")
        kt2.metric("T max media oraria", f"{T_max.mean():.0f}°C", help=f"picco {T_max.max():.0f}°C")
        kt3.metric("Ore con scarto", f"{len(T_media):,}".replace(",", "."))
        dur = pd.DataFrame({"media": np.sort(T_media.values)[::-1], "max": np.sort(T_max.values)[::-1]})
        dur["ore"] = np.arange(1, len(dur) + 1)
        fig_ts = go.Figure()
        fig_ts.add_trace(go.Scatter(x=dur["ore"], y=dur["max"], mode="lines", name="T max oraria",
                                    line=dict(color=COLOR_ALTA_T, width=2)))
        fig_ts.add_trace(go.Scatter(x=dur["ore"], y=dur["media"], mode="lines", name="T media oraria",
                                    line=dict(color=COLOR_HP, width=2)))
        fig_ts.add_hline(y=T_mandata_ideale, line_dash="dot", line_color="#BBBBBB",
                         annotation_text=f"mandata {T_mandata_ideale}°C", annotation_position="top left")
        fig_ts.update_layout(height=420, xaxis_title="Ore/anno (ordinate per T decrescente)",
                             yaxis_title="Temperatura sorgente (°C)",
                             legend=dict(orientation="h", yanchor="bottom", y=1.02), margin=dict(t=30, b=10))
        st.plotly_chart(fig_ts, use_container_width=True)


# =============================================================================
# TAB 3 - DIMENSIONAMENTO (schema a cascata: 3 accumuli + 2 HP)
# =============================================================================
with tab_dimensionamento:
    st.markdown("### Dimensionamento — schema a cascata (3 accumuli + 2 HP)")

    # --- eredita domanda + flussi (solo calcolo) ---
    edifici_dim = st.session_state.get("_dom_edifici") or \
        buildings.loc[buildings["tipo_utenza"] == "Pubblico", "edificio"].tolist()
    flussi_dim = st.session_state.get("_off_flussi") or flussi["id_flusso"].tolist()
    eredita_ok = bool(st.session_state.get("_dom_edifici")) and bool(st.session_state.get("_off_flussi"))
    zone_dim = st.session_state.get("_dom_zone", [])
    fattore_priv = st.session_state.get("_dom_fattore_privato", 1.0)
    dom_dim = domanda[domanda["edificio"].isin(edifici_dim)].copy()
    is_priv = dom_dim["tipo_utenza"] == "Privato (potenziale)"
    dom_dim.loc[is_priv, "MWh_riscaldamento"] *= fattore_priv
    dom_dim.loc[is_priv, "MWh_ACS"] *= fattore_priv
    dom_dim_series = dom_dim.groupby("datetime")[["MWh_riscaldamento", "MWh_ACS"]].sum().sum(axis=1)
    idx_h = dom_dim_series.index
    dom_arr = dom_dim_series.values
    dom_tot = float(dom_arr.sum())
    picco_kw = float(dom_arr.max()) * 1000.0
    pinch_dim = st.session_state.get("_off_pinch", 5.0)
    off_all = genera_offerta_flussi(flussi, pinch_dim)
    off_all = off_all[off_all["id_flusso"].isin(flussi_dim)].copy()
    soil_temp_arr = soil_temp_monthly(pvgis)[idx_h.month.values - 1]

    def capex_hp_kw(pot_kw):
        p = max(pot_kw / 1000.0, 0.1); pts = [(1, 340), (3, 300), (10, 220)]
        if p <= 1: return 340
        if p >= 10: return 220
        for (p0, c0), (p1, c1) in zip(pts, pts[1:]):
            if p0 <= p <= p1:
                return c0 + (np.log(p) - np.log(p0)) / (np.log(p1) - np.log(p0)) * (c1 - c0)
        return 220
    perdita_func = (lambda v: float(np.interp(np.log(np.clip(v, 500, 5000)), [np.log(500), np.log(5000)], [2.0, 1.0])) if v > 0 else 0.0)
    _maxp = int(picco_kw) + 1000

    col_ctrl, col_res = st.columns([1, 3])

    # =========================== CONTROLLI (sinistra) ===========================
    with col_ctrl:
        st.markdown("#### ⚙️ Parametri")
        T_int = st.slider("Anello intermedio (°C)", 40, 60, 50, key="dim_tint",
                          help="La HP alta T solleva sempre da qui a mandata. ~45-50°C è l'ottimo tipico.")
        st.markdown("**Supporto (parallelo)**")
        backup_tipo = st.radio("Copre il gap con:", ["HP bassa T", "gas", "biomassa"],
                               key="dim_backup_tipo",
                               help="Stessa funzione. Solo la HP bassa T recupera i flussi freddi e il ground loop.")
        is_hp_par = (backup_tipo == "HP bassa T")
        eta_hp = st.slider("η 2° principio HP (%)", 30, 60, 50, key="dim_eta") / 100.0
        prezzo_el = st.slider("Prezzo elettricità (€/MWh)", 80, 350, 180, step=10, key="dim_prezzo_el")
        antigelo = st.slider("Floor antigelo ground loop (°C)", -5, 10, 0, key="dim_antigelo",
                             help="L'evaporatore sul suolo non scende sotto questa soglia.")
        if backup_tipo == "gas":
            rend_gas = st.slider("Rendimento caldaia (%)", 85, 98, 92, key="dim_rend_gas") / 100.0
            prezzo_gas = st.slider("Prezzo gas (€/MWh)", 40, 160, 90, key="dim_prezzo_gas")
            capex_kw_bk = st.slider("CAPEX caldaia (€/kW)", 60, 300, 120, step=10, key="dim_capex_gas")
            opex_bk_mwh = prezzo_gas / rend_gas
        elif backup_tipo == "biomassa":
            rend_bio = st.slider("Rendimento caldaia (%)", 75, 92, 85, key="dim_rend_bio") / 100.0
            costo_cip = st.slider("Costo cippato (€/MWh)", 20, 60, 35, key="dim_costo_bio")
            capex_kw_bk = st.slider("CAPEX caldaia (€/kW)", 300, 900, 550, step=25, key="dim_capex_bio")
            opex_bk_mwh = costo_cip / rend_bio
        else:
            capex_kw_bk = 700.0; opex_bk_mwh = 0.0
        backup_cop = None
        costo_m3 = st.slider("CAPEX accumuli (€/m³)", 80, 1500, 1000, step=20, key="dim_costo_m3",
                             help="IEA DHC F1 Tab.3 (Sud Europa, <5000 m³ ≈ 1000 €/m³).")

        solare_on = st.checkbox("☀️ Solare nell'accumulo basso", value=False, key="dim_solare_on")
        solar_low = np.zeros(len(dom_arr)); capex_solare = 0.0; area_sol = 0
        if solare_on:
            acs = dom_dim.groupby("datetime")["MWh_ACS"].sum().reindex(idx_h, fill_value=0)
            est = idx_h.month.isin([6, 7, 8]); acs_est = float(acs[est].sum())
            pref = genera_offerta_solare(pvgis, 1000.0, 0.30).groupby("datetime")["MWh"].sum().reindex(idx_h, fill_value=0)
            pref_est = float(pref[est].sum()); area_base = (acs_est / pref_est * 1000.0) if pref_est > 1e-6 else 2000.0
            quota = st.slider("Quota solare (% ACS estiva)", 0, 300, 100, step=10, key="dim_quota_sol")
            eff = st.slider("Efficienza collettori (%)", 15, 50, 30, key="dim_eff_sol") / 100.0
            capex_mq = st.slider("CAPEX solare (€/m²)", 200, 900, 450, step=20, key="dim_capex_sol")
            area_sol = int(round(area_base * quota / 100.0 * (0.30 / max(eff, 0.01))))
            solar_low = genera_offerta_solare(pvgis, area_sol, eff).groupby("datetime")["MWh"].sum().reindex(idx_h, fill_value=0).values
            capex_solare = area_sol * capex_mq
            if solare_on and not is_hp_par:
              st.warning(
                  "⚠️ Solare attivo con supporto a combustibile: il calore solare finisce "
                  "nella fascia più calda dell'accumulo basso, ma senza HP bassa T resta "
                  "inutilizzato. Considera se aggiungere HP bassa T o instradare il solare "
                  "come preriscaldo del ritorno rete (non ancora implementato)."
              )
                        st.caption(f"Campo ~{area_sol:,} m²".replace(",", "."))

        # routing (serve all'ottimizzatore qui sotto)
        q_hot_arr, q_int_arr, q_low_arr, q_low_bins, bin_T = routing_flussi(off_all, idx_h, T_mandata_ideale, T_int)
        q_low_bins_eff = q_low_bins.copy()
        if solare_on:
            q_low_bins_eff[:, -1] = q_low_bins_eff[:, -1] + solar_low   # solare → fascia più calda dell'accumulo basso

        st.markdown("#### 🔎 Ottimizzazione")
        if st.button("Ottimizza scenario", key="dim_btn_opt", use_container_width=True):
            with st.spinner("LCOH minimo, copertura 100%..."):
                best = ottimizza_cascata(dom_arr, q_hot_arr, q_int_arr, q_low_bins_eff, bin_T, soil_temp_arr,
                                         float(T_mandata_ideale), float(T_ritorno_ideale), float(T_int), 5, eta_hp,
                                         backup_tipo, capex_hp_kw, capex_kw_bk, opex_bk_mwh, backup_cop,
                                         prezzo_el, costo_m3, capex_solare, crf(0.04, 20), perdita_func, float(antigelo))
            if best:
                st.session_state["dim_p_alta"] = int(round(best["P_alta"] / 100) * 100)
                st.session_state["dim_p_bassa"] = int(round(best["P_bassa"] / 100) * 100)
                st.session_state["dim_p_bk"] = int(round(best["P_bk"] / 100) * 100)
                st.session_state["dim_v_hot"] = int(round(best["v_hot"] / 50) * 50)
                st.session_state["dim_v_int"] = int(round(best["v_int"] / 50) * 50)
                st.session_state["dim_v_low"] = int(round(best["v_low"] / 50) * 50)
                st.session_state["_opt_casc"] = best
                st.rerun()

        st.markdown("**Taglie** (dall'ottimo, ritoccabili)")
        for k, dv in [("dim_p_alta", int(picco_kw)), ("dim_p_bassa", int(picco_kw * 0.8)), ("dim_p_bk", int(picco_kw))]:
            st.session_state[k] = max(0, min(int(st.session_state.get(k, dv)), _maxp))
        for k, dv in [("dim_v_hot", 0), ("dim_v_int", 800), ("dim_v_low", 400)]:
            st.session_state[k] = max(0, min(int(st.session_state.get(k, dv)), 4000))
        P_alta = st.slider("HP alta T (kW)", 0, _maxp, step=100, key="dim_p_alta")
        if is_hp_par:
            P_bassa = st.slider("HP bassa T (kW)", 0, _maxp, step=100, key="dim_p_bassa"); P_bk = 0
        else:
            P_bassa = 0
            P_bk = st.slider(f"Caldaia {backup_tipo} (kW)", 0, _maxp, step=100, key="dim_p_bk")
        V_hot = st.slider("Accumulo CALDO (m³)", 0, 4000, step=50, key="dim_v_hot")
        V_int = st.slider("Accumulo INTERMEDIO (m³)", 0, 4000, step=50, key="dim_v_int")
        V_low = st.slider("Accumulo BASSO (m³)", 0, 4000, step=50, key="dim_v_low")

    # =========================== CALCOLO ===========================
    perd = perdita_func(max(V_hot, V_int, V_low))
    sim = dispatch_cascata(dom_arr, q_hot_arr, q_int_arr, q_low_bins_eff, bin_T, soil_temp_arr,
                           float(T_mandata_ideale), float(T_ritorno_ideale), float(T_int), 5, eta_hp,
                           V_hot, V_int, V_low, P_alta, P_bassa,
                           parallelo=backup_tipo, P_backup_kw=P_bk, backup_cop=backup_cop,
                           antigelo=float(antigelo), perdita_sett_pct=perd)
    E_hot, E_alta, E_bassa = sim["E_hot_diretto"], sim["E_hp_alta"], sim["E_hp_bassa"]
    E_bk, E_nc = sim["E_backup"], sim["E_non_coperta"]
    E_fer = E_hot + E_alta + (E_bk if backup_tipo == "biomassa" else 0.0)
    quota_fer = E_fer / dom_tot * 100 if dom_tot > 0 else 0
    fattore_crf = crf(0.04, 20)
    capex_alta = P_alta * capex_hp_kw(P_alta)
    capex_bassa = P_bassa * capex_hp_kw(P_bassa) if is_hp_par else 0.0
    capex_bk = P_bk * capex_kw_bk if not is_hp_par else 0.0
    capex_acc = (V_hot + V_int + V_low) * costo_m3
    capex_sistema = capex_alta + capex_bassa + capex_bk + capex_acc + capex_solare
    opex = sim["E_el_tot"] * prezzo_el + E_bk * opex_bk_mwh
    costo_annuo = capex_sistema * fattore_crf + opex
    lcoh = costo_annuo / dom_tot if dom_tot > 0 else np.nan

    # =========================== RISULTATI (destra) ===========================
    with col_res:
        if eredita_ok:
            st.caption(f"**{len(edifici_dim)} edifici** (zone: {', '.join(zone_dim) if zone_dim else '—'}) · "
                       f"**{len(flussi_dim)} flussi** · mandata/ritorno **{T_mandata_ideale}/{T_ritorno_ideale}°C** "
                       f"· anello intermedio **{T_int}°C**.")
        else:
            st.info(f"Valori predefiniti ({len(edifici_dim)} edifici pubblici, {len(flussi_dim)} flussi). "
                    f"Personalizza in Domanda/Offerta.")

        # --- taglie ottime, in evidenza ---
        ores = st.session_state.get("_opt_casc")
        if ores:
            st.markdown("#### ✅ Scenario ottimizzato")
            o1, o2, o3, o4, o5 = st.columns(5)
            o1.metric("HP alta T", f"{ores['P_alta']:.0f} kW")
            o2.metric("HP bassa T" if is_hp_par else "Caldaia",
                      f"{(ores['P_bassa'] if is_hp_par else ores['P_bk']):.0f} kW")
            o3.metric("LCOH", f"{ores['lcoh']:.1f} €/MWh")
            o4.metric("Quota FER", f"{ores['quota_fer']:.0f}%")
            o5.metric("COP HP alta", f"{ores['cop_alta']:.1f}")
            va1, va2, va3 = st.columns(3)
            va1.metric("Accumulo CALDO", f"{ores['v_hot']:.0f} m³")
            va2.metric("Accumulo INTERMEDIO", f"{ores['v_int']:.0f} m³")
            va3.metric("Accumulo BASSO", f"{ores['v_low']:.0f} m³")
            st.caption("Backup **firm** (potenza al picco): copre il 100% anche a zero scarto. "
                       "Cambi supporto/solare/fonti? Rilancia l'ottimizzazione.")
        else:
            st.info("Premi **Ottimizza scenario** (a sinistra) per dimensionare HP e accumuli a LCOH minimo.")

        st.divider()
        st.markdown("#### Instradamento dello scarto per temperatura")
        cA1, cA2, cA3, cA4 = st.columns(4)
        cA1.metric("Domanda annua", f"{dom_tot:,.0f} MWh".replace(",", "."), help=f"picco {picco_kw:.0f} kW")
        cA2.metric("🔴 → caldo", f"{q_hot_arr.sum():,.0f} MWh".replace(",", "."),
                   help=f"scarto ≥ mandata ({T_mandata_ideale}°C): diretto in linea")
        cA3.metric("🟠 → intermedio", f"{q_int_arr.sum():,.0f} MWh".replace(",", "."),
                   help=f"tra {T_int} e {T_mandata_ideale}°C: sorgente HP alta T")
        cA4.metric("🔵 → basso", f"{q_low_arr.sum():,.0f} MWh".replace(",", "."),
                   help=f"< {T_int}°C: sollevato dalla HP bassa T (solo se attiva)")
        if q_hot_arr.sum() < 1e-6:
            st.caption("ℹ️ Accumulo **caldo a 0**: nessun flusso ≥ mandata. Diventa utile selezionando in "
                       "Offerta flussi fumi ad alta T (o abbassando la mandata sotto la T dei flussi).")

        # DECOMPOSIZIONE PER FONTE DI ENERGIA (quanta domanda arriva da: scarto / suolo / elettricità / supporto)
        el_hp = sim["el_alta"] + sim["el_bassa"]                       # lavoro dei compressori
        ground = sim["q_ground"]                                       # calore dal suolo (rinnovabile, NON scarto)
        scarto_via_hp = np.maximum(sim["q_alta"] - el_hp - ground, 0.0)  # scarto (caldo+freddo) risollevato dalle HP
        E_scarto_via_hp = float(scarto_via_hp.sum())
        E_ground = sim["E_ground"]; E_el = float(el_hp.sum())
        E_scarto_tot = E_hot + E_scarto_via_hp                        # scarto totale che PARTECIPA in energia
        C_GROUND = "#8C6D46"                                          # marrone (distinto dall'elettricità)

        st.markdown("##### 📉 Curva di durata: da dove arriva l'energia")
        st.caption("Ore ordinate per domanda decrescente (linea **bianca**). Sotto, le **fonti** che la coprono in "
                   "energia: **scarto** usato diretto (rosso) o risollevato dalle HP (verde) = la quota di calore di "
                   "scarto che partecipa; **suolo/ground** (marrone); **elettricità** dei compressori HP alta (ciano) "
                   "e HP bassa (viola); **supporto** a combustibile (arancio). Il vuoto fino alla linea resta scoperto.")
        order = np.argsort(dom_arr)[::-1]
        x = np.arange(1, len(dom_arr) + 1)
        fig_dur = go.Figure()
        bande = [("Scarto diretto", sim["q_hot_direct"], COLOR_ALTA_T),
                 ("Scarto risollevato dalle HP", scarto_via_hp, COLOR_OFFERTA),
                 ("Suolo / ground loop", ground, C_GROUND),
                 ("Elettricità HP alta", sim["el_alta"], COLOR_HP),
                 ("Elettricità HP bassa", sim["el_bassa"], COLOR_HP_BASSA),
                 (f"Supporto ({backup_tipo})", sim["q_backup"], COLOR_BACKUP)]
        for nome, arr, col in bande:
            if float(arr.sum()) < 1:
                continue
            fig_dur.add_trace(go.Scatter(x=x, y=arr[order], mode="lines", name=nome,
                                         stackgroup="c", line=dict(width=0), fillcolor=hex_to_rgba(col, 0.9)))
        fig_dur.add_trace(go.Scatter(x=x, y=dom_arr[order], mode="lines", name="Domanda",
                                     line=dict(color=COLOR_DOMANDA, width=2.4)))
        fig_dur.update_layout(height=440, xaxis_title="Ore/anno", yaxis_title="MW",
                              legend=dict(orientation="h", yanchor="bottom", y=1.02), margin=dict(t=30, b=10))
        st.plotly_chart(fig_dur, use_container_width=True)

        st.markdown("##### 🗺️ Heatmap: energia di scarto per mese e temperatura")
        _h = off_all[off_all["MWh"] > 0].copy()
        if _h.empty:
            st.info("Nessuno scarto disponibile.")
        else:
            _h["mese"] = _h["datetime"].dt.month
            bins = [0, 30, 40, 50, 60, 70, 80, 100, 150, 2000]
            labels = ["<30", "30-40", "40-50", "50-60", "60-70", "70-80", "80-100", "100-150", "≥150"]
            _h["fascia"] = pd.cut(_h["T_disponibile"], bins=bins, labels=labels, right=False)
            piv = (_h.pivot_table(index="fascia", columns="mese", values="MWh", aggfunc="sum", observed=False)
                   .reindex(index=labels).reindex(columns=range(1, 13)).fillna(0))
            fig_hm = go.Figure(go.Heatmap(z=piv.values, x=[MONTH_NAMES[m-1] for m in piv.columns], y=labels,
                                          colorscale="YlOrRd", colorbar=dict(title="MWh")))
            for _lv, _lab in [(T_int, f"intermedio {T_int}°C"), (T_mandata_ideale, f"mandata {T_mandata_ideale}°C")]:
                try:
                    _ib = next(i for i in range(len(labels)) if bins[i] <= _lv < bins[i+1])
                    fig_hm.add_hline(y=_ib - 0.5, line_color="#22C3DD", line_width=2,
                                     annotation_text=_lab, annotation_position="top left")
                except StopIteration:
                    pass
            fig_hm.update_layout(height=420, yaxis_title="Temperatura scarto (°C)", margin=dict(t=30, b=10))
            st.plotly_chart(fig_hm, use_container_width=True)

        st.divider()
        st.markdown("#### Copertura (simulazione oraria)")
        mets = [("Caldo diretto", E_hot, f"{E_hot/dom_tot*100:.0f}% della domanda"),
                ("HP alta T", E_alta, f"{E_alta/dom_tot*100:.0f}% consegnato · COP {sim['cop_alta_medio']:.2f}")]
        if is_hp_par:
            mets.append(("HP bassa T (interna)", E_bassa,
                         f"→ intermedio (interno) · COP {sim['cop_bassa_medio']:.2f} · ground {sim['ore_ground']} ore"))
        else:
            mets.append((f"Supporto: {backup_tipo}", E_bk, f"{E_bk/dom_tot*100:.0f}% della domanda"))
        cols_r = st.columns(len(mets) + 1)
        for i, (lab, val, hlp) in enumerate(mets):
            cols_r[i].metric(lab, f"{val:,.0f} MWh".replace(",", "."), help=hlp)
        cols_r[-1].metric("Quota FER", f"{quota_fer:.0f}%")
        if sim["ore_non_coperte"] > 0:
            st.error(f"⚠️ {sim['ore_non_coperte']} ore non coperte ({E_nc:,.0f} MWh): ottimizza o aumenta le taglie.".replace(",", "."))
        else:
            st.success("✅ Copertura 100% in tutte le ore.")

        st.markdown("**Da dove arriva l'energia** (fonti, sull'anno)")
        fig_mix = go.Figure()
        voci = [("Scarto diretto", E_hot, COLOR_ALTA_T),
                ("Scarto risollevato dalle HP", E_scarto_via_hp, COLOR_OFFERTA),
                ("Suolo / ground loop", E_ground, C_GROUND),
                ("Elettricità HP alta", float(sim["el_alta"].sum()), COLOR_HP),
                ("Elettricità HP bassa", float(sim["el_bassa"].sum()), COLOR_HP_BASSA),
                (f"Supporto ({backup_tipo})", E_bk, COLOR_BACKUP)]
        if E_nc > 1:
            voci.append(("Non coperto", E_nc, COLOR_NONCOP))
        voci = [(n, v, c) for n, v, c in voci if v > 1]
        tot_mix = sum(v for _, v, _ in voci) or 1.0
        for nome, val, col in voci:
            pct = val / tot_mix * 100
            fig_mix.add_trace(go.Bar(y=["Fonti"], x=[val], name=nome, orientation="h", marker_color=col,
                                     text=(f"{pct:.0f}%" if pct >= 6 else ""), textposition="inside",
                                     insidetextanchor="middle", textfont=dict(color="white", size=13), cliponaxis=False))
        fig_mix.update_layout(barmode="stack", height=220, xaxis_title="MWh/anno",
                              legend=dict(orientation="h", yanchor="top", y=-0.5), margin=dict(t=30, b=10))
        fig_mix.update_yaxes(showticklabels=False)
        st.plotly_chart(fig_mix, use_container_width=True)
        st.caption(f"**Scarto che partecipa** = rosso + verde = **{E_scarto_tot:,.0f} MWh/a** "
                   f"({E_scarto_tot/dom_tot*100:.0f}% della domanda). Il resto è elettricità dei compressori, "
                   f"suolo e (se scelto) combustibile di supporto.".replace(",", "."))

        # bilancio energetico sintetico (per confrontare gli scenari)
        st.markdown("**Bilancio energetico dello scenario**")
        _spf = (E_hot + E_alta) / E_el if E_el > 1e-6 else 0.0
        bb = st.columns(4)
        bb[0].metric("Scarto utilizzato", f"{E_scarto_tot:,.0f} MWh".replace(",", "."),
                     help=f"{E_scarto_tot/dom_tot*100:.0f}% della domanda (diretto + risollevato via HP)")
        bb[1].metric("Elettricità HP", f"{E_el:,.0f} MWh".replace(",", "."),
                     help=f"compressori (alta {sim['E_el_alta']:.0f} + bassa {sim['E_el_bassa']:.0f}) · SPF sistema {_spf:.1f}")
        bb[2].metric("Suolo / ground", f"{E_ground:,.0f} MWh".replace(",", "."), help=f"{sim['ore_ground']} ore su ground loop")
        bb[3].metric("Combustibile", f"{E_bk:,.0f} MWh".replace(",", "."),
                     help=(f"{backup_tipo}" if not is_hp_par else "nessuno (scenario elettrico)"))

        # curva di durata del COP delle due HP
        st.markdown("**📈 Curva di durata del COP delle pompe di calore**")
        st.caption("Per ogni HP, i COP orari ordinati dal più alto al più basso (solo ore in cui la macchina lavora).")
        fig_cop = go.Figure()
        _ca = sim["cop_alta_s"][(sim["q_alta"] > 1e-6) & np.isfinite(sim["cop_alta_s"])]
        if len(_ca):
            fig_cop.add_trace(go.Scatter(y=np.sort(_ca)[::-1], x=np.arange(1, len(_ca) + 1),
                                         mode="lines", name="COP HP alta T", line=dict(color=COLOR_HP, width=2)))
        _cb = sim["cop_bassa_s"][(sim["q_bassa"] > 1e-6) & np.isfinite(sim["cop_bassa_s"])]
        if len(_cb):
            fig_cop.add_trace(go.Scatter(y=np.sort(_cb)[::-1], x=np.arange(1, len(_cb) + 1),
                                         mode="lines", name="COP HP bassa T", line=dict(color=COLOR_HP_BASSA, width=2)))
        if len(_ca) or len(_cb):
            fig_cop.update_layout(height=320, xaxis_title="Ore di funzionamento (ordinate per COP decrescente)",
                                  yaxis_title="COP", legend=dict(orientation="h", yanchor="bottom", y=1.02),
                                  margin=dict(t=30, b=10))
            st.plotly_chart(fig_cop, use_container_width=True)
        else:
            st.info("Nessuna HP attiva in questo scenario.")

        st.divider()
        st.markdown("#### 💰 Costi e LCOH")
        righe = [
            {"Voce": f"HP alta T ({P_alta} kW)", "CAPEX (€)": round(capex_alta), "OPEX (€/a)": round(sim["E_el_alta"] * prezzo_el)},
            ({"Voce": f"HP bassa T ({P_bassa} kW)", "CAPEX (€)": round(capex_bassa), "OPEX (€/a)": round(sim["E_el_bassa"] * prezzo_el)} if is_hp_par else
             {"Voce": f"Caldaia {backup_tipo} ({P_bk} kW)", "CAPEX (€)": round(capex_bk), "OPEX (€/a)": round(E_bk * opex_bk_mwh)}),
            {"Voce": f"Accumuli ({V_hot}+{V_int}+{V_low} m³)", "CAPEX (€)": round(capex_acc), "OPEX (€/a)": 0},
        ]
        if solare_on:
            righe.append({"Voce": f"Solare ({area_sol} m²)", "CAPEX (€)": round(capex_solare), "OPEX (€/a)": 0})
        st.dataframe(pd.DataFrame(righe), use_container_width=True, hide_index=True)
        fig_co = go.Figure(go.Pie(labels=["CAPEX (annualizzato)", "OPEX (annuo)"],
                                  values=[capex_sistema * fattore_crf, opex], hole=0.5,
                                  marker=dict(colors=["#5B8DEF", "#F4A259"]), sort=False))
        fig_co.update_layout(title=f"Costo annuo · {costo_annuo:,.0f} €/a".replace(",", "."),
                             height=300, margin=dict(t=45, b=10), legend=dict(orientation="h", y=-0.1))
        st.plotly_chart(fig_co, use_container_width=True)
        df_c = pd.DataFrame(righe)
        _pal = [COLOR_HP, (COLOR_HP_BASSA if is_hp_par else COLOR_BACKUP), COLOR_ACCUMULO, COLOR_SOLARE]
        pc1, pc2 = st.columns(2)
        with pc1:
            fig_capex = go.Figure(go.Pie(labels=df_c["Voce"], values=df_c["CAPEX (€)"], hole=0.5,
                                         marker=dict(colors=_pal[:len(df_c)]), sort=False))
            fig_capex.update_layout(title=f"CAPEX totale · {capex_sistema:,.0f} €".replace(",", "."),
                                    height=330, margin=dict(t=45, b=10), legend=dict(orientation="h", y=-0.1))
            st.plotly_chart(fig_capex, use_container_width=True)
        with pc2:
            df_o = df_c[df_c["OPEX (€/a)"] > 0]
            fig_opex = go.Figure(go.Pie(labels=df_o["Voce"], values=df_o["OPEX (€/a)"], hole=0.5,
                                        marker=dict(colors=_pal[:len(df_o)]), sort=False))
            fig_opex.update_layout(title=f"OPEX annuo · {opex:,.0f} €/a".replace(",", "."),
                                   height=330, margin=dict(t=45, b=10), legend=dict(orientation="h", y=-0.1))
            st.plotly_chart(fig_opex, use_container_width=True)
        s1, s2, s3, s4 = st.columns(4)
        s1.metric("CAPEX di sistema", f"{capex_sistema:,.0f} €".replace(",", "."))
        s2.metric("Costo annuo", f"{costo_annuo:,.0f} €/a".replace(",", "."))
        s3.metric("LCOH di sistema", f"{lcoh:.1f} €/MWh" if not np.isnan(lcoh) else "n/d")
        s4.metric("Quota FER", f"{quota_fer:.0f}%")

    st.session_state["_dim_snapshot"] = {
        "utenza": f"{len(edifici_dim)} edifici",
        "T mandata/ritorno": f"{T_mandata_ideale}/{T_ritorno_ideale}°C",
        "carico_residuo_mwh": round(dom_tot),
        "tecnologie": f"HP alta {P_alta}kW + " + (f"HP bassa {P_bassa}kW" if is_hp_par else f"{backup_tipo} {P_bk}kW")
                      + (f" + solare {area_sol}m²" if solare_on else ""),
        "volume_accumulo": f"{V_hot}+{V_int}+{V_low}",
        "capex_sistema": round(capex_sistema),
        "costo_annuo_sistema": round(costo_annuo),
        "lcoh_sistema": round(float(lcoh), 1) if not np.isnan(lcoh) else None,
        "quota_fer_pct": round(quota_fer),
        "ore_non_coperte": sim["ore_non_coperte"],
        # dettaglio per l'analisi economica
        "capex_hp_alta": round(capex_alta), "capex_hp_bassa": round(capex_bassa),
        "capex_caldaia": round(capex_bk), "capex_accumuli": round(capex_acc),
        "capex_solare": round(capex_solare),
        "opex_elettrico": round(sim["E_el_tot"] * prezzo_el), "opex_combustibile": round(E_bk * opex_bk_mwh),
        "E_el_mwh": round(sim["E_el_tot"]), "E_comb_mwh": round(E_bk),
        "E_scarto_mwh": round(E_hot + max(sim["E_hp_alta"] - sim["E_el_tot"] - sim["E_ground"], 0)),
        "backup_tipo": backup_tipo, "cop_alta": round(sim["cop_alta_medio"], 2),
        "rete": st.session_state.get("_rete_info"),
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
            st.session_state.setdefault("scenari_full", {})[nome_scenario] = dict(snap)
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

# =============================================================================
# TAB 5 - ANALISI ECONOMICA
# =============================================================================
def van(flussi_cassa, tasso):
    """Valore Attuale Netto di una serie di flussi (anno 0 incluso)."""
    return float(sum(f / (1 + tasso) ** t for t, f in enumerate(flussi_cassa)))


def tir(flussi_cassa, lo=-0.9, hi=1.5):
    """Tasso Interno di Rendimento per bisezione; None se non esiste nell'intervallo."""
    f_lo, f_hi = van(flussi_cassa, lo), van(flussi_cassa, hi)
    if f_lo * f_hi > 0:
        return None
    for _ in range(200):
        mid = (lo + hi) / 2
        f_mid = van(flussi_cassa, mid)
        if abs(f_mid) < 1e-6:
            return mid
        if f_lo * f_mid < 0:
            hi, f_hi = mid, f_mid
        else:
            lo, f_lo = mid, f_mid
    return (lo + hi) / 2


with tab_economia:
    st.markdown("### Analisi economica degli scenari")
    _full = st.session_state.get("scenari_full", {})
    if not _full:
        st.info("Nessuno scenario salvato. Vai in **Dimensionamento**, imposta il sistema, poi in "
                "**Confronto scenari** premi *Salva scenario corrente*. Puoi salvarne quanti vuoi "
                "(es. gas / biomassa / HP bassa T, con e senza privati) e confrontarli qui.")
    else:
        col_par, col_ris = st.columns([1, 3])

        with col_par:
            st.markdown("#### ⚙️ Ipotesi economiche")
            scen_sel = st.multiselect("Scenari da analizzare", list(_full.keys()),
                                      default=list(_full.keys()), key="ec_scen")
            anni = st.slider("Orizzonte (anni)", 10, 40, 25, key="ec_anni")
            tasso = st.slider("Tasso di sconto (%)", 0.0, 12.0, 4.0, step=0.5, key="ec_tasso") / 100
            st.markdown("**Ricavi**")
            prezzo_vendita = st.slider("Prezzo di vendita calore (€/MWh)", 40, 200, 95, step=5,
                                       key="ec_prezzo_v",
                                       help="Tariffa al cliente finale, al netto di IVA.")
            allacc_una_tantum = st.slider("Contributo di allacciamento (€/utenza)", 0, 8000, 1500,
                                          step=100, key="ec_allacc",
                                          help="Una tantum incassato all'anno 0 per ogni utenza collegata.")
            st.markdown("**Costi**")
            om_pct = st.slider("O&M annuo (% del CAPEX)", 0.0, 5.0, 2.0, step=0.25, key="ec_om") / 100
            contributo = st.slider("Contributo a fondo perduto (% CAPEX)", 0, 80, 40, step=5,
                                   key="ec_contributo",
                                   help="Quota di CAPEX coperta da finanziamenti pubblici (PNRR, bandi regionali).")
            incl_rete = st.checkbox("Includi CAPEX rete", value=True, key="ec_incl_rete")
            st.markdown("**Confronto con gas metano**")
            prezzo_gas_ut = st.slider("Prezzo gas utente (€/MWh)", 40, 180, 95, step=5, key="ec_gas_p",
                                      help="Costo del metano per l'utente finale, comprensivo di oneri.")
            rend_cald = st.slider("Rendimento caldaie esistenti (%)", 70, 100, 88, key="ec_gas_r") / 100
            escalation = st.slider("Escalation prezzi energia (%/anno)", 0.0, 5.0, 2.0, step=0.5,
                                   key="ec_esc") / 100

        with col_ris:
            if not scen_sel:
                st.warning("Seleziona almeno uno scenario.")
            else:
                risultati = []
                for nome in scen_sel:
                    s = _full[nome]
                    rete = s.get("rete") or {}
                    capex_prod = float(s.get("capex_sistema") or 0)
                    capex_rete = float(rete.get("capex_rete") or 0) if incl_rete else 0.0
                    capex_tot = capex_prod + capex_rete
                    capex_netto = capex_tot * (1 - contributo / 100)
                    dom_mwh = float(s.get("carico_residuo_mwh") or 0)
                    n_ut = int(rete.get("n_utenze") or 0)
                    opex_en = float(s.get("opex_elettrico") or 0) + float(s.get("opex_combustibile") or 0)
                    opex_om = capex_tot * om_pct
                    ricavo_calore = dom_mwh * prezzo_vendita
                    costo_gas_oggi = dom_mwh / rend_cald * prezzo_gas_ut
                    # flussi di cassa (ottica del gestore)
                    cf = [-capex_netto + n_ut * allacc_una_tantum]
                    for t in range(1, anni + 1):
                        k = (1 + escalation) ** t
                        cf.append(ricavo_calore * k - (opex_en * k + opex_om))
                    v = van(cf, tasso)
                    r = tir(cf)
                    margine = ricavo_calore - opex_en - opex_om
                    payback = None
                    cum = cf[0]
                    for t in range(1, anni + 1):
                        cum += cf[t]
                        if cum >= 0:
                            payback = t
                            break
                    lcoh_tot = ((capex_netto * crf(tasso, anni)) + opex_en + opex_om) / dom_mwh if dom_mwh > 0 else np.nan
                    risultati.append({
                        "Scenario": nome, "Tecnologie": s.get("tecnologie", ""),
                        "Domanda (MWh/a)": round(dom_mwh), "Utenze": n_ut,
                        "CAPEX prod. (€)": round(capex_prod), "CAPEX rete (€)": round(capex_rete),
                        "CAPEX totale (€)": round(capex_tot), "CAPEX netto (€)": round(capex_netto),
                        "OPEX energia (€/a)": round(opex_en), "O&M (€/a)": round(opex_om),
                        "Ricavi (€/a)": round(ricavo_calore), "Margine (€/a)": round(margine),
                        "VAN (€)": round(v), "TIR (%)": (round(r * 100, 1) if r is not None else None),
                        "Payback (anni)": payback,
                        "LCOH completo (€/MWh)": round(float(lcoh_tot), 1) if dom_mwh > 0 else None,
                        "Costo gas oggi (€/a)": round(costo_gas_oggi),
                        "Risparmio vs gas (€/a)": round(costo_gas_oggi - (opex_en + opex_om)),
                        "Quota FER (%)": s.get("quota_fer_pct"),
                        "Densità (MWh/m·a)": round(float(rete.get("densita") or 0), 2),
                        "Rete (km)": round(float(rete.get("lunghezza_m") or 0) / 1000, 1),
                    })
                df_ec = pd.DataFrame(risultati)

                st.markdown("#### 📋 Risultati per scenario")
                for r in risultati:
                    with st.expander(f"**{r['Scenario']}** · VAN {r['VAN (€)']/1e6:.2f} M€ · "
                                     f"TIR {r['TIR (%)'] if r['TIR (%)'] is not None else 'n/d'}% · "
                                     f"LCOH {r['LCOH completo (€/MWh)']} €/MWh",
                                     expanded=(len(risultati) <= 2)):
                        st.caption(f"{r['Tecnologie']} · {r['Domanda (MWh/a)']:,} MWh/a · "
                                   f"{r['Utenze']} utenze · rete {r['Rete (km)']} km".replace(",", "."))
                        e1, e2, e3, e4 = st.columns(4)
                        e1.metric("VAN", f"{r['VAN (€)']/1e6:.2f} M€",
                                  help=f"a {anni} anni, tasso {tasso*100:.1f}%")
                        e2.metric("TIR", f"{r['TIR (%)']}%" if r["TIR (%)"] is not None else "n/d")
                        e3.metric("Payback", f"{r['Payback (anni)']} anni" if r["Payback (anni)"] else "oltre orizzonte")
                        e4.metric("LCOH completo", f"{r['LCOH completo (€/MWh)']} €/MWh",
                                  help="produzione + rete + O&M, CAPEX annualizzato")
                        f1, f2 = st.columns(2)
                        with f1:
                            _lab = ["HP alta T", "HP bassa T", "Caldaia", "Accumuli", "Solare", "Rete"]
                            _s = _full[r["Scenario"]]
                            _val = [_s.get("capex_hp_alta", 0), _s.get("capex_hp_bassa", 0),
                                    _s.get("capex_caldaia", 0), _s.get("capex_accumuli", 0),
                                    _s.get("capex_solare", 0), r["CAPEX rete (€)"]]
                            _c = [COLOR_HP, COLOR_HP_BASSA, COLOR_BACKUP, COLOR_ACCUMULO, COLOR_SOLARE, COLOR_ALTA_T]
                            _k = [(l, v, c) for l, v, c in zip(_lab, _val, _c) if v and v > 0]
                            fig_cx = go.Figure(go.Pie(labels=[k[0] for k in _k], values=[k[1] for k in _k],
                                                      hole=0.5, marker=dict(colors=[k[2] for k in _k]), sort=False))
                            fig_cx.update_layout(title=f"CAPEX · {r['CAPEX totale (€)']/1e6:.2f} M€",
                                                 height=300, margin=dict(t=45, b=10),
                                                 legend=dict(orientation="h", y=-0.1))
                            st.plotly_chart(fig_cx, use_container_width=True, key=f"ec_cx_{r['Scenario']}")
                        with f2:
                            _s = _full[r["Scenario"]]
                            _lo = [("Elettricità HP", _s.get("opex_elettrico", 0), COLOR_HP),
                                   ("Combustibile", _s.get("opex_combustibile", 0), COLOR_BACKUP),
                                   ("O&M", r["O&M (€/a)"], COLOR_ACCUMULO)]
                            _lo = [x for x in _lo if x[1] and x[1] > 0]
                            fig_ox = go.Figure(go.Pie(labels=[x[0] for x in _lo], values=[x[1] for x in _lo],
                                                      hole=0.5, marker=dict(colors=[x[2] for x in _lo]), sort=False))
                            fig_ox.update_layout(title=f"OPEX · {(r['OPEX energia (€/a)']+r['O&M (€/a)'])/1e3:.0f} k€/a",
                                                 height=300, margin=dict(t=45, b=10),
                                                 legend=dict(orientation="h", y=-0.1))
                            st.plotly_chart(fig_ox, use_container_width=True, key=f"ec_ox_{r['Scenario']}")
                        g1, g2, g3 = st.columns(3)
                        g1.metric("Costo con gas oggi", f"{r['Costo gas oggi (€/a)']/1e3:.0f} k€/a",
                                  help=f"{r['Domanda (MWh/a)']} MWh / rendimento {rend_cald*100:.0f}% × {prezzo_gas_ut} €/MWh")
                        g2.metric("Costo esercizio TLR", f"{(r['OPEX energia (€/a)']+r['O&M (€/a)'])/1e3:.0f} k€/a")
                        g3.metric("Risparmio vs gas", f"{r['Risparmio vs gas (€/a)']/1e3:.0f} k€/a",
                                  delta=f"{r['Risparmio vs gas (€/a)']/max(r['Costo gas oggi (€/a)'],1)*100:.0f}%")
                        # mappa del tracciato dello scenario
                        _rete = _full[r["Scenario"]].get("rete") or {}
                        if _rete.get("traccia_lat"):
                            fig_m = go.Figure()
                            fig_m.add_trace(go.Scattermapbox(lat=_rete["traccia_lat"], lon=_rete["traccia_lon"],
                                                             mode="lines", line=dict(width=2, color=COLOR_ALTA_T),
                                                             name="Tracciato", hoverinfo="skip"))
                            fig_m.add_trace(go.Scattermapbox(lat=_rete["pt_lat"], lon=_rete["pt_lon"],
                                                             mode="markers", marker=dict(size=5, color=COLOR_HP),
                                                             name="Utenze", hoverinfo="skip"))
                            fig_m.add_trace(go.Scattermapbox(lat=[CENTRALE_LAT], lon=[CENTRALE_LON],
                                                             mode="markers", marker=dict(size=16, color="#FF9F1C"),
                                                             name="Centrale", hoverinfo="skip"))
                            fig_m.update_layout(mapbox=dict(style="open-street-map",
                                                            center=dict(lat=(np.mean(_rete["pt_lat"]) + CENTRALE_LAT) / 2,
                                                                        lon=(np.mean(_rete["pt_lon"]) + CENTRALE_LON) / 2),
                                                            zoom=12),
                                                height=380, margin=dict(t=5, b=0, l=0, r=0),
                                                legend=dict(orientation="h", yanchor="bottom", y=1.01))
                            st.plotly_chart(fig_m, use_container_width=True, key=f"ec_map_{r['Scenario']}")

                st.divider()
                st.markdown("#### ⚖️ Confronto tra scenari")
                _metriche = {"VAN (€)": "VAN (€)", "TIR (%)": "TIR (%)",
                             "LCOH completo (€/MWh)": "LCOH completo (€/MWh)",
                             "CAPEX totale (€)": "CAPEX totale (€)",
                             "OPEX energia (€/a)": "OPEX energia (€/a)",
                             "Quota FER (%)": "Quota FER (%)",
                             "Densità (MWh/m·a)": "Densità (MWh/m·a)",
                             "Risparmio vs gas (€/a)": "Risparmio vs gas (€/a)"}
                scelte = st.multiselect("Parametri da confrontare", list(_metriche.keys()),
                                        default=["VAN (€)", "TIR (%)", "LCOH completo (€/MWh)", "Quota FER (%)"],
                                        key="ec_metriche")
                if scelte:
                    _n = len(scelte)
                    for i in range(0, _n, 2):
                        cc = st.columns(min(2, _n - i))
                        for j, m in enumerate(scelte[i:i + 2]):
                            _d = df_ec[["Scenario", m]].dropna()
                            if _d.empty:
                                continue
                            fig_b = go.Figure(go.Bar(x=_d["Scenario"], y=_d[m],
                                                     marker_color=[COLOR_HP, COLOR_BACKUP, COLOR_OFFERTA,
                                                                   COLOR_HP_BASSA, COLOR_SOLARE][:len(_d)],
                                                     text=_d[m].round(1), textposition="outside"))
                            fig_b.update_layout(title=m, height=300, margin=dict(t=45, b=10),
                                                yaxis=dict(zeroline=True, zerolinecolor="#888"))
                            cc[j].plotly_chart(fig_b, use_container_width=True, key=f"ec_bar_{m}")
                st.markdown("##### Tabella completa")
                st.dataframe(df_ec, use_container_width=True, hide_index=True)
                st.download_button("⬇️ Scarica confronto (CSV)", df_ec.to_csv(index=False).encode("utf-8"),
                                   "maniago_analisi_economica.csv", "text/csv")
                st.caption("**VAN** = valore attuale netto dei flussi di cassa del gestore (ricavi da vendita "
                           "calore + allacciamenti − CAPEX netto − OPEX − O&M). **TIR** = tasso che azzera il VAN. "
                           "**LCOH completo** include produzione, rete e O&M con CAPEX annualizzato. "
                           "Il confronto col gas è sui soli costi di esercizio, a parità di calore fornito.")
