"""
=============================================================================
 MANIAGO TLR - Studio di fattibilita rete di teleriscaldamento
=============================================================================
 Sviluppato all'interno del progetto INTERREG HEAT 35
 https://www.interreg-central.eu/projects/heat-35/
 da Matteo De Piccoli - APE FVG
 www.linkedin.com/in/matteo-de-piccoli-2a17a5163
 matteo.depiccoli@ape.fvg.it | https://www.ape.fvg.it/
=============================================================================
 Avvio:  streamlit run "TLR 2.py"

 REVISIONE - patch applicate
 ---------------------------
 P1  Densita lineare: rimosso il doppio fattore di allacciamento
 P2  COP HP con lift minimo (8 K) e cap realistico (6.5) - IEA DHC F6/F10
 P3  Warning se solare attivo con supporto a combustibile
 P4  Guardia anno bisestile su HOURS_2024 (8784 h)
 P5  Contemporaneita QM (Fig. 12.2) applicata SOLO al picco di dimensionamento
 P6  Perdite di rete QM (Fig. 12.3 Verenum) sulla domanda alla centrale
 P7  MERIT ORDER: uso diretto dei flussi nell'ora corrente (l'accumulo non e
     piu un collo di bottiglia). La HP alta T ha SEMPRE precedenza sul
     combustibile: il gas/biomassa entra solo sul residuo.
 P8  Forni di forgiatura Pietro Rosa da misure Ecol Studio 14/07/2025
     (rapporti 25LF24167/168/169/170 - punti E1, E4, E5, E6)
 P9  Scenari salvati rimovibili singolarmente
 P10 Tracciato rete in 2 tempi: pubblici+condomini come obbligato + privati
     agganciati opportunisticamente entro un buffer dal tubo (default 50 m).
     Zone senza pubblici possono essere agganciate opportunisticamente se il
     tubo di altre zone ci passa vicino.
 P11 Routing su strade reali OSM (Overpass API) con Dijkstra (networkx):
     ogni edificio "snappa" al nodo stradale piu vicino, il tratto obbligato
     e un albero di Steiner approssimato lungo le strade, gli stub dei privati
     sono anch'essi calcolati su strada. Cache locale in maniago_strade_cache.json.
     Dipendenze: networkx, scipy, requests (fallback silenzioso a MST se assenti).

 File dati richiesti nella stessa cartella:
   maniago_domanda_edifici.csv
   maniago_domanda_oraria_8760h_HDD_reale.csv
   maniago_flussi_offerta.csv
   pvgis_maniago_pulito.csv
   maniago_mappa_utenze.csv          (opzionale)
   maniago_condomini.csv             (opzionale)
   maniago_privati_edifici.csv       (opzionale)
   edifici_pubblici_coordinate.csv   (opzionale)
   TLR_zones_borders.geojson
=============================================================================
"""
import streamlit as st
import pandas as pd
import json
import os
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(page_title="Maniago TLR | HEAT35 - APE FVG", layout="wide", page_icon="\U0001F525")

# -----------------------------------------------------------------------------
# RIFERIMENTI DI PROGETTO
# -----------------------------------------------------------------------------
PROGETTO_HTML = (
    "Sviluppato all'interno del progetto "
    "**[INTERREG HEAT 35](https://www.interreg-central.eu/projects/heat-35/)** "
    "da **[Matteo De Piccoli](https://www.linkedin.com/in/matteo-de-piccoli-2a17a5163)** "
    "— [APE FVG](https://www.ape.fvg.it/)"
)
FOOTER_HTML = (
    "\U0001F310 Progetto: [Interreg HEAT 35](https://www.interreg-central.eu/projects/heat-35/) "
    "&nbsp;|&nbsp; \U0001F3E0 Sito Ente: [APE FVG](https://www.ape.fvg.it/) "
    "&nbsp;|&nbsp; \U0001F4E7 Contatto: [matteo.depiccoli@ape.fvg.it](mailto:matteo.depiccoli@ape.fvg.it)"
)

# --- default degli slider forzati al primo avvio ---
DEFAULTS_SLIDER = {
    "dom_t_mandata": 80,
    "dom_t_ritorno": 50,
}


def applica_default_slider(force=False):
    for k, v in DEFAULTS_SLIDER.items():
        if force or k not in st.session_state:
            st.session_state[k] = v


if "_init_done" not in st.session_state:
    applica_default_slider(force=True)
    st.session_state["_init_done"] = True
if "_scenari" not in st.session_state:
    st.session_state["_scenari"] = {}

# -----------------------------------------------------------------------------
# PALETTE
# -----------------------------------------------------------------------------
COLOR_RISCALDAMENTO = "#C0522D"
COLOR_ACS = "#2D7DC0"
COLOR_OFFERTA = "#3FA34D"
COLOR_ACCUMULO = "#8E5FC2"
COLOR_HP = "#22C3DD"
COLOR_CALDAIA = "#B0413E"
COLOR_EX_BIOMAN = "#E63946"
COLOR_ALTA_T = "#FF4B4B"
COLOR_HP_ALTA = COLOR_HP
COLOR_HP_BASSA = "#B57EDC"
COLOR_SOLARE = "#F5C518"
COLOR_BACKUP = "#FF9F1C"
COLOR_NONCOP = "#9AA0A6"
COLOR_DOMANDA = "#FFFFFF"
COLOR_GROUND = "#8C6D46"

ZONE_NOMI = {
    1: "Zona 1 - Comune NE",
    2: "Zona 2 - Ex Bioman",
    3: "Zona 3 - Sud",
    4: "Zona 4 - Centro",
    5: "Zona 5 - Ovest",
}
ZONE_DEFAULT = ["Zona 1 - Comune NE", "Zona 2 - Ex Bioman"]
ZONA_COLORI = {
    "Zona 1 - Comune NE": "#2D7DC0",
    "Zona 2 - Ex Bioman": "#E63946",
    "Zona 3 - Sud": "#E9C46A",
    "Zona 4 - Centro": "#9B5DE5",
    "Zona 5 - Ovest": "#3FA34D",
}
CAMPAGNA_LON_MIN = 12.73

MONTH_NAMES = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu", "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]
RHO_CP = 1.163          # kWh/(m3*K)
MWH_PER_UNITA = 9.0
HOURS_2024 = pd.date_range("2024-01-01", "2024-12-31 23:00", freq="h")
DAYS_2024 = pd.date_range("2024-01-01", "2024-12-31", freq="D")

AZIENDE_COORD = {
    "ZML": (46.1478, 12.7139),
    "Pietro Rosa": (46.1432, 12.7215),
    "Pandolfo": (46.1485, 12.7160),
    "Inossman": (46.1501, 12.7145),
}
CENTRALE_LAT, CENTRALE_LON = 46.1479, 12.7151


# =============================================================================
# GEOMETRIE E ZONE
# =============================================================================
def _anelli_zona(geom):
    polys = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]
    return [np.asarray(p[0], dtype=float) for p in polys]


@st.cache_data
def carica_zone_confini(path="TLR_zones_borders.geojson"):
    try:
        gj = json.load(open(path, encoding="utf-8"))
    except Exception:
        return {}
    return {ft["properties"]["id"]: _anelli_zona(ft["geometry"]) for ft in gj["features"]}


def _punto_in_anello(lon, lat, ring):
    x, y = ring[:, 0], ring[:, 1]
    n = len(x)
    dentro = False
    j = n - 1
    for i in range(n):
        if ((y[i] > lat) != (y[j] > lat)) and \
           (lon < (x[j] - x[i]) * (lat - y[i]) / (y[j] - y[i] + 1e-15) + x[i]):
            dentro = not dentro
        j = i
    return dentro


def zona_da_coordinate(lat, lon, zone_poly):
    if lat is None or lon is None or (isinstance(lat, float) and np.isnan(lat)):
        return None
    if lon is not None and lon > CAMPAGNA_LON_MIN:
        return "__ESCLUSO__"
    for zid, anelli in zone_poly.items():
        for r in anelli:
            if _punto_in_anello(lon, lat, r):
                return ZONE_NOMI.get(zid)
    return None


def mst_archi(lat, lon, radice=None):
    lat = np.asarray(lat, dtype=float)
    lon = np.asarray(lon, dtype=float)
    ok = np.isfinite(lat) & np.isfinite(lon)
    lat, lon = lat[ok], lon[ok]
    if radice is not None:
        lat = np.insert(lat, 0, radice[0])
        lon = np.insert(lon, 0, radice[1])
    n = len(lat)
    if n < 2:
        return [], 0.0
    R = 6371000.0
    la = np.radians(lat)
    lo = np.radians(lon)
    x = R * lo * np.cos(la.mean())
    y = R * la
    dentro = np.zeros(n, dtype=bool)
    dentro[0] = True
    dist = np.hypot(x - x[0], y - y[0])
    padre = np.zeros(n, dtype=int)
    archi = []
    tot = 0.0
    for _ in range(n - 1):
        d2 = np.where(dentro, np.inf, dist)
        j = int(np.argmin(d2))
        if not np.isfinite(d2[j]):
            break
        p = int(padre[j])
        tot += float(dist[j])
        dentro[j] = True
        archi.append(((lat[p], lon[p]), (lat[j], lon[j]), float(dist[j])))
        nd = np.hypot(x - x[j], y - y[j])
        agg = nd < dist
        padre[agg] = j
        dist = np.minimum(dist, nd)
    return archi, tot


def stima_lunghezza_rete(lat, lon, fattore_tortuosita=1.35):
    lat = np.asarray(lat, dtype=float)
    lon = np.asarray(lon, dtype=float)
    ok = np.isfinite(lat) & np.isfinite(lon)
    lat, lon = lat[ok], lon[ok]
    n = len(lat)
    if n < 2:
        return 0.0
    R = 6371000.0
    la = np.radians(lat)
    lo = np.radians(lon)
    x = R * lo * np.cos(la.mean())
    y = R * la
    in_albero = np.zeros(n, dtype=bool)
    in_albero[0] = True
    dist = np.hypot(x - x[0], y - y[0])
    tot = 0.0
    for _ in range(n - 1):
        dist[in_albero] = np.inf
        j = int(np.argmin(dist))
        tot += float(dist[j])
        in_albero[j] = True
        dist = np.minimum(dist, np.hypot(x - x[j], y - y[j]))
    return tot * fattore_tortuosita


def _latlon_a_xy(lat, lon):
    """Proiezione locale metrica (equirettangolare centrata sulla media)."""
    lat = np.asarray(lat, dtype=float)
    lon = np.asarray(lon, dtype=float)
    R = 6371000.0
    la0 = np.radians(lat.mean()) if len(lat) else 0.0
    x = R * np.radians(lon) * np.cos(la0)
    y = R * np.radians(lat)
    return x, y


def dist_punto_segmento_m(px, py, ax, ay, bx, by):
    """Distanza (m) di ogni punto (px,py) dal segmento AB.
    px,py sono array; ax,ay,bx,by sono scalari. Ritorna array + parametro t in [0,1].
    """
    px = np.asarray(px, dtype=float); py = np.asarray(py, dtype=float)
    dx = bx - ax; dy = by - ay
    L2 = dx * dx + dy * dy
    if L2 < 1e-9:
        return np.hypot(px - ax, py - ay), np.zeros_like(px)
    t = np.clip(((px - ax) * dx + (py - ay) * dy) / L2, 0.0, 1.0)
    cx = ax + t * dx; cy = ay + t * dy
    return np.hypot(px - cx, py - cy), t


def buffer_tracciato(archi_pubblici, priv_lat, priv_lon, raggio_m=50.0):
    """Per ogni privato calcola la distanza minima dal tracciato pubblico.

    archi_pubblici: lista di ((lat1,lon1),(lat2,lon2),dist_m)
    Ritorna: dist_min (m), idx_arco_piu_vicino, (lat_pt,lon_pt) del punto sul tubo.
    """
    if not len(archi_pubblici) or not len(priv_lat):
        return np.array([]), np.array([]), np.array([]), np.array([])
    # proiezione comune: uso tutti i vertici degli archi + i privati
    all_lat = np.concatenate([[a[0][0] for a in archi_pubblici],
                              [a[1][0] for a in archi_pubblici],
                              np.asarray(priv_lat, dtype=float)])
    all_lon = np.concatenate([[a[0][1] for a in archi_pubblici],
                              [a[1][1] for a in archi_pubblici],
                              np.asarray(priv_lon, dtype=float)])
    xs, ys = _latlon_a_xy(all_lat, all_lon)
    N = len(archi_pubblici); M = len(priv_lat)
    ax = xs[:N]; ay = ys[:N]
    bx = xs[N:2 * N]; by = ys[N:2 * N]
    px = xs[2 * N:]; py = ys[2 * N:]
    dist_min = np.full(M, np.inf)
    idx_arco = np.zeros(M, dtype=int)
    t_best = np.zeros(M)
    for k in range(N):
        d, t = dist_punto_segmento_m(px, py, ax[k], ay[k], bx[k], by[k])
        migl = d < dist_min
        dist_min[migl] = d[migl]
        idx_arco[migl] = k
        t_best[migl] = t[migl]
    # coordinate del punto sul tubo piu vicino (per lo stub)
    lat_pt = np.array([archi_pubblici[idx_arco[i]][0][0]
                       + t_best[i] * (archi_pubblici[idx_arco[i]][1][0]
                                      - archi_pubblici[idx_arco[i]][0][0])
                       for i in range(M)])
    lon_pt = np.array([archi_pubblici[idx_arco[i]][0][1]
                       + t_best[i] * (archi_pubblici[idx_arco[i]][1][1]
                                      - archi_pubblici[idx_arco[i]][0][1])
                       for i in range(M)])
    return dist_min, idx_arco, lat_pt, lon_pt


# =============================================================================
# ROUTING SU RETE STRADALE OSM
# =============================================================================
def _osm_download_strade(centro_lat, centro_lon, raggio_km=1.5, timeout=90):
    """Scarica il grafo stradale attorno al centro tramite Overpass API.
    Ritorna (dict, None) se ok, (None, str_errore) se fallisce.
    """
    try:
        import requests
    except ImportError:
        return None, "modulo 'requests' non installato (pip install requests)"
    d = raggio_km / 111.0
    bbox = (centro_lat - d, centro_lon - d, centro_lat + d, centro_lon + d)
    q = f"""
[out:json][timeout:{timeout}];
(
  way["highway"~"^(primary|secondary|tertiary|unclassified|residential|service|living_street|pedestrian)$"]
    ({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});
);
out body;
>;
out skel qt;
"""
    # provo 3 endpoint Overpass in cascata
    endpoints = [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
        "https://overpass.osm.ch/api/interpreter",
    ]
    ultimo_errore = None
    for url in endpoints:
        try:
            r = requests.get(url, params={"data": q}, timeout=timeout + 30,
                             headers={"User-Agent": "TLR-Maniago/1.0"})
            r.raise_for_status()
            return r.json(), None
        except Exception as e:
            ultimo_errore = f"{url.split('//')[1].split('/')[0]}: {type(e).__name__}: {str(e)[:120]}"
            continue
    return None, ultimo_errore or "tutti gli endpoint Overpass hanno fallito"


@st.cache_data(show_spinner="Scarico la rete stradale di Maniago (una volta sola)...")
def carica_grafo_strade(centro_lat=CENTRALE_LAT, centro_lon=CENTRALE_LON,
                        raggio_km=1.5, cache_file="maniago_strade_cache.json"):
    """Carica il grafo stradale OSM. Usa cache locale su file se presente.

    Ritorna (grafo_dict, None) se ok oppure (None, messaggio_errore).
    """
    data = None
    err = None
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            err = f"cache locale illeggibile: {e}"
            data = None
    if data is None:
        data, err = _osm_download_strade(centro_lat, centro_lon, raggio_km)
        if data is None:
            return None, err
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except Exception as e:
            # non fatale
            pass
    # parse: nodi + strade
    nodi = {}
    strade = []
    for el in data.get("elements", []):
        if el["type"] == "node":
            nodi[el["id"]] = (el["lat"], el["lon"])
        elif el["type"] == "way":
            strade.append(el.get("nodes", []))
    if not nodi:
        return None, "risposta OSM senza nodi (bbox vuoto o filtro errato)"
    # KDTree sui nodi per snap
    try:
        from scipy.spatial import cKDTree
    except ImportError:
        return None, "modulo 'scipy' non installato (pip install scipy)"
    node_ids = list(nodi.keys())
    coords_xy = np.array([_latlon_a_xy(np.array([nodi[i][0]]),
                                       np.array([nodi[i][1]]))[0][0] for i in node_ids])
    ys = np.array([_latlon_a_xy(np.array([nodi[i][0]]),
                                np.array([nodi[i][1]]))[1][0] for i in node_ids])
    pts = np.column_stack([coords_xy, ys])
    kd = cKDTree(pts)
    return {"nodi": nodi, "strade": strade, "kd": kd,
            "node_ids": node_ids, "pts_xy": pts}, None


def build_grafo_stradale(strade_data):
    """Costruisce il grafo networkx dai dati OSM per Dijkstra."""
    try:
        import networkx as nx
    except ImportError:
        return None
    G = nx.Graph()
    nodi = strade_data["nodi"]
    for way in strade_data["strade"]:
        for a, b in zip(way[:-1], way[1:]):
            if a not in nodi or b not in nodi:
                continue
            lat1, lon1 = nodi[a]
            lat2, lon2 = nodi[b]
            x, y = _latlon_a_xy(np.array([lat1, lat2]), np.array([lon1, lon2]))
            d = float(np.hypot(x[1] - x[0], y[1] - y[0]))
            if G.has_edge(a, b):
                if d < G[a][b]["weight"]:
                    G[a][b]["weight"] = d
            else:
                G.add_edge(a, b, weight=d)
    return G


def snap_a_strade(lat_arr, lon_arr, strade_data):
    """Per ogni punto, id del nodo stradale piu vicino + distanza (m)."""
    lat_arr = np.asarray(lat_arr, dtype=float)
    lon_arr = np.asarray(lon_arr, dtype=float)
    kd = strade_data["kd"]
    node_ids = strade_data["node_ids"]
    x_pt, y_pt = _latlon_a_xy(lat_arr, lon_arr)
    d, idx = kd.query(np.column_stack([x_pt, y_pt]), k=1)
    return [node_ids[i] for i in idx], d


def albero_steiner_su_strade(G, nodi_target, radice_nodo):
    """Approssima l'albero di Steiner: parte dalla radice, aggiunge iterativamente
    ogni nodo target agganciandosi al percorso minimo verso il tratto gia esistente.
    Ritorna: lista di archi ((lat1,lon1),(lat2,lon2),d), lunghezza totale, set di nodi usati.
    """
    import networkx as nx
    targets = [t for t in nodi_target if t != radice_nodo and t in G]
    if radice_nodo not in G:
        return [], 0.0, set()
    usati = {radice_nodo}
    archi_res = []
    # dijkstra da radice
    dist_from_root, _ = nx.single_source_dijkstra(G, radice_nodo, weight="weight")
    # ordino i target per distanza dalla radice, dal piu vicino
    targets = sorted(targets, key=lambda t: dist_from_root.get(t, np.inf))
    for t in targets:
        if t in usati:
            continue
        # trovo il nodo gia usato piu vicino a t (dijkstra multi-source)
        try:
            # dijkstra da t verso set 'usati'
            dist_to_used, path = nx.multi_source_dijkstra(G, sources=usati, target=t, weight="weight")
        except nx.NetworkXNoPath:
            continue
        # path e la lista di nodi
        for a, b in zip(path[:-1], path[1:]):
            if b in usati and a in usati:
                continue
            # aggiungo l'arco
            w = G[a][b]["weight"]
            archi_res.append((a, b, w))
            usati.add(a)
            usati.add(b)
    lun_tot = float(sum(w for _, _, w in archi_res))
    return archi_res, lun_tot, usati


def archi_a_coords(archi_nodi, strade_data):
    """Converte lista di archi (id_a, id_b, dist) in ((lat1,lon1),(lat2,lon2),dist)."""
    nodi = strade_data["nodi"]
    out = []
    for a, b, d in archi_nodi:
        if a in nodi and b in nodi:
            out.append(((nodi[a][0], nodi[a][1]), (nodi[b][0], nodi[b][1]), d))
    return out


def dijkstra_stub_al_tubo(G, nodi_tubo, nodo_partenza):
    """Percorso minimo da nodo_partenza al set di nodi_tubo (l'arrivo e il tubo piu vicino).
    Ritorna: lista di archi, lunghezza totale, nodo di aggancio sul tubo.
    """
    import networkx as nx
    if nodo_partenza in nodi_tubo:
        return [], 0.0, nodo_partenza
    if nodo_partenza not in G:
        return [], 0.0, None
    try:
        lun, path = nx.multi_source_dijkstra(G, sources=nodi_tubo,
                                             target=nodo_partenza, weight="weight")
    except nx.NetworkXNoPath:
        return [], 0.0, None
    # il path va da qualche nodo in nodi_tubo a nodo_partenza
    archi = []
    for a, b in zip(path[:-1], path[1:]):
        archi.append((a, b, G[a][b]["weight"]))
    nodo_aggancio = path[0]
    return archi, float(lun), nodo_aggancio


def build_cluster_color_map(clusters_list):
    return {cl: ZONA_COLORI.get(cl, "#888888") for cl in clusters_list}


def hex_to_rgba(color, alpha=0.85):
    color = color.strip()
    if color.startswith("rgb"):
        nums = color[color.find("(") + 1: color.find(")")].split(",")
        r, g, b = (int(float(n)) for n in nums[:3])
    else:
        h = color.lstrip("#")
        r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def soil_temp_monthly(pvgis_df, depth_m=1.5, alpha=0.6e-6):
    """Temperatura del terreno (C) per mese alla profondita data."""
    T = pvgis_df["T2m"].astype(float).values
    doy = pvgis_df["datetime"].dt.dayofyear.values.astype(float)
    w = 2 * np.pi / 365.25
    X = np.column_stack([np.ones_like(doy), np.cos(w * doy), np.sin(w * doy)])
    coef, *_ = np.linalg.lstsq(X, T, rcond=None)
    Tm = float(coef[0])
    A = float(np.hypot(coef[1], coef[2]))
    t_peak = float((np.arctan2(coef[2], coef[1]) / w) % 365.25)
    P = 365.25 * 86400.0
    d = np.sqrt(alpha * P / np.pi)
    damp = np.exp(-depth_m / d)
    lag = (depth_m / d) / w
    return np.array([Tm + A * damp * np.cos(w * (pd.Timestamp(2024, m, 15).dayofyear - t_peak - lag))
                     for m in range(1, 13)])


# =============================================================================
# P2 - COP con vincoli fisici realistici (IEA DHC TS5 F6/F10)
# =============================================================================
def cop_singola(T_src, T_mand, eta, lift_min_K=8.0, cop_max=6.5):
    """COP a stadio singolo (Carnot x eta) con vincoli realistici.

    lift_min_K  delta T effettivo minimo del compressore reale (perdite
                meccaniche, surriscaldamento, sottoraffreddamento). Impedisce
                COP -> infinito quando la sorgente e quasi alla T di mandata.
    cop_max     tetto realistico per HP industriali (IEA DHC F6/F10:
                excess heat 25 C, lift 25-40 K -> COP 3-5).
    Funziona anche su array numpy.
    """
    Tc = np.asarray(T_src, dtype=float) + 273.15
    Th = float(T_mand) + 273.15
    lift = np.maximum(Th - Tc, lift_min_K)
    cop = eta * Th / lift
    return np.minimum(cop, cop_max)


def crf(rate, anni):
    """Capital Recovery Factor."""
    if anni <= 0:
        return 1.0
    if rate <= 0:
        return 1.0 / anni
    return rate / (1.0 - (1.0 + rate) ** (-anni))


# =============================================================================
# P5 - Contemporaneita QM (Handbook Fig. 12.2)
# =============================================================================
def coeff_simultaneita_QM(n_utenze):
    """Coefficiente di contemporaneita secondo QM Handbook Fig. 12.2.

    10-20 utenze -> ~0.95 ; oltre 100 utenze -> ~0.60. Interpolazione log.
    Si applica al PICCO di dimensionamento, non all'energia annua.
    """
    if n_utenze <= 1:
        return 1.0
    n = np.clip(n_utenze, 1, 500)
    return float(np.interp(np.log(n),
                           np.log([1, 10, 20, 100, 500]),
                           [1.0, 0.98, 0.95, 0.60, 0.55]))


# =============================================================================
# P6 - Perdite di rete QM (Handbook Fig. 12.3 / Verenum cap. 7.1 - 12.2.8)
# =============================================================================
def perdite_pct_QM(densita_MWh_m_a, T_media_rete_C=65, classe_isolante=2):
    """Perdite di distribuzione in % del calore venduto.

    Digitalizzata dal Verenum Planungshandbuch Fernwarme.
    Ancoraggio: densita 2.0 MWh/(m*a), T media 65 C, classe isolante 2 -> 10.5 %
    (benchmark QM: 1 MW connesso, 1 km di rete, target <= 10 %).
    La perdita specifica in W/m e circa costante: la percentuale scala come
    1/densita, mentre la vendita per metro cresce linearmente con la densita.
      classe_isolante  1 = minima, 2 = media (default), 3 = alta (target QM)
    """
    W_per_m_65 = 24.0
    fattore_classe = {1: 1.4, 2: 1.0, 3: 0.8}.get(classe_isolante, 1.0)
    T_terreno = 13.0
    fattore_T = (T_media_rete_C - T_terreno) / (65 - T_terreno)
    # perdita specifica annua per metro, in MWh/(m*a):
    #   W/m * 8760 h = Wh/(m*a); /1e6 -> MWh/(m*a)
    perdite_MWh_m_a = W_per_m_65 * fattore_classe * fattore_T * 8760 / 1e6
    return perdite_MWh_m_a / max(densita_MWh_m_a, 0.1) * 100


# =============================================================================
# ROUTING DEI FLUSSI PER TEMPERATURA
# =============================================================================
def routing_flussi(off_df, idx_h, mandata, T_int):
    """Instrada ogni flusso-ora sul livello termico corretto.

    >= mandata            -> anello CALDO (uso diretto, nessuna HP)
    tra T_int e mandata   -> anello INTERMEDIO (evaporatore della HP alta T)
    <  T_int              -> anello BASSO, suddiviso in bin da 5 K
    """
    o = off_df[off_df["MWh"] > 0].copy()
    o["T"] = o["T_disponibile"]
    hot = o[o["T"] >= mandata].groupby("datetime")["MWh"].sum().reindex(idx_h, fill_value=0.0)
    intm = o[(o["T"] >= T_int) & (o["T"] < mandata)].groupby("datetime")["MWh"].sum().reindex(idx_h, fill_value=0.0)
    low = o[o["T"] < T_int].copy()
    q_low = low.groupby("datetime")["MWh"].sum().reindex(idx_h, fill_value=0.0)
    edges = np.arange(0.0, T_int + 5.0, 5.0)
    bin_T = (edges[:-1] + edges[1:]) / 2.0
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


# =============================================================================
# P7 - DISPATCH A CASCATA CON MERIT ORDER
# =============================================================================
def dispatch_cascata(dom_arr, q_hot_arr, q_int_arr, q_low_bins, bin_T, soil_arr,
                     mandata, ritorno, T_int, dT_evap, eta_hp,
                     V_hot, V_int, V_low,
                     P_hp_alta_kw, P_hp_bassa_kw,
                     parallelo="HP bassa T", P_backup_kw=0.0, backup_cop=None,
                     antigelo=0.0, perdita_sett_pct=1.0):
    """Dispatch orario dello schema a cascata con 3 accumuli stratificati.

    MERIT ORDER (P7) - ordine di merito rigido, indipendente dai prezzi:
      1. calore di scarto >= mandata, usato DIRETTAMENTE
      2. HP alta T, che solleva dal livello intermedio alla mandata
      3. HP bassa T (se prevista), che ricarica il livello intermedio
      4. caldaia a combustibile, SOLO sul residuo non coperto dai punti 1-3

    Differenza chiave rispetto alla versione precedente: i flussi disponibili
    nell'ora corrente sono utilizzabili SUBITO, senza dover transitare per
    l'accumulo. In precedenza, con V_int = 0 la capacita era nulla e tutto il
    calore intermedio veniva scartato: la HP alta T non partiva mai e il gas
    copriva il 100 % della domanda. Gli accumuli ora servono solo a spostare
    energia nel tempo, come nella realta.
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

    q_hot_direct = np.zeros(n)
    q_alta = np.zeros(n)
    q_bassa = np.zeros(n)
    q_backup = np.zeros(n)
    el_alta = np.zeros(n)
    el_bassa = np.zeros(n)
    q_ground = np.zeros(n)
    non_cop = np.zeros(n)
    scarto_perso = np.zeros(n)
    cop_alta_s = np.full(n, np.nan)
    cop_bassa_s = np.full(n, np.nan)
    ore_ground = 0

    soc_hot = 0.0
    soc_int = 0.0
    soc_low_bins = np.zeros(len(bin_T))

    for i in range(n):
        # --- dispersioni degli accumuli ---
        if perdita_ora > 0:
            soc_hot -= soc_hot * perdita_ora
            soc_int -= soc_int * perdita_ora
            soc_low_bins = soc_low_bins * (1.0 - perdita_ora)

        # --- pool disponibili nell'ora: stock + flusso in ingresso (P7) ---
        pool_hot = soc_hot + q_hot_arr[i]
        pool_int = soc_int + q_int_arr[i]
        pool_low_bins = soc_low_bins + q_low_bins[i]
        if not is_hp:
            # senza HP bassa T il livello basso non ha utilizzatori
            scarto_perso[i] += float(pool_low_bins.sum())
            pool_low_bins = np.zeros_like(pool_low_bins)

        dom = dom_arr[i]

        # --- MERIT 1: scarto >= mandata, uso diretto ---
        d_hot = min(dom, pool_hot)
        pool_hot -= d_hot
        q_hot_direct[i] = d_hot
        residuo = dom - d_hot

        # --- MERIT 2: HP alta T (precede SEMPRE il combustibile) ---
        cop_a = float(cop_singola(T_int - dT_evap, mandata, eta_hp))
        if residuo > 1e-9 and P_alta > 0 and cop_a > 1:
            cop_alta_s[i] = cop_a
            q_a_want = min(residuo, P_alta)
            frac_evap = 1.0 - 1.0 / cop_a          # quota di calore presa all'evaporatore
            E_a_want = q_a_want * frac_evap
            # energia disponibile all'evaporatore: livello intermedio + eventuale
            # ricarica in tempo reale dalla HP bassa T
            extra_bassa = P_bassa if is_hp else 0.0
            E_a = min(E_a_want, pool_int + extra_bassa)
            if E_a > 1e-12:
                q_a = E_a / frac_evap
                from_int = min(E_a, pool_int)
                pool_int -= from_int
                from_bassa = E_a - from_int

                # --- MERIT 3: HP bassa T, ricarica il livello intermedio ---
                if from_bassa > 1e-12 and is_hp and P_bassa > 0:
                    g_T = max(soil_arr[i], antigelo)
                    soc_tot = float(pool_low_bins.sum())
                    if soc_tot > 1e-9:
                        need = from_bassa
                        e_acc = 0.0
                        wt = 0.0
                        for k in range(len(bin_T) - 1, -1, -1):
                            take = min(pool_low_bins[k], need)
                            e_acc += take
                            wt += take * bin_T[k]
                            need -= take
                            if need <= 1e-12:
                                break
                        if need > 1e-12:
                            wt += need * g_T
                            e_acc += need
                        src_T = wt / e_acc if e_acc > 0 else g_T
                        src_is_ground = False
                    else:
                        src_T = g_T
                        src_is_ground = True
                    cop_b = float(cop_singola(src_T - dT_evap, T_int, eta_hp))
                    cop_bassa_s[i] = cop_b
                    q_b = from_bassa
                    E_b = q_b * (1.0 - 1.0 / cop_b) if cop_b > 1 else q_b
                    need = E_b
                    for k in range(len(pool_low_bins) - 1, -1, -1):
                        take = min(pool_low_bins[k], need)
                        pool_low_bins[k] -= take
                        need -= take
                        if need <= 1e-12:
                            break
                    q_ground[i] = max(need, 0.0)
                    if src_is_ground or q_ground[i] > 1e-9:
                        ore_ground += 1
                    q_bassa[i] = q_b
                    el_bassa[i] = q_b / cop_b if cop_b > 0 else 0.0

                el_alta[i] = q_a / cop_a
                q_alta[i] = q_a
                residuo -= q_a

        # --- MERIT 4: combustibile, solo sul residuo ---
        if (not is_hp) and residuo > 1e-9 and P_bk > 0:
            q_k = min(residuo, P_bk)
            q_backup[i] = q_k
            if backup_cop is not None and backup_cop > 0:
                el_bassa[i] += q_k / backup_cop
            residuo -= q_k

        non_cop[i] = max(residuo, 0.0)

        # --- fine ora: quel che avanza va in accumulo, il resto e perso ---
        soc_hot = min(pool_hot, C_hot)
        scarto_perso[i] += max(pool_hot - C_hot, 0.0)
        soc_int = min(pool_int, C_int)
        scarto_perso[i] += max(pool_int - C_int, 0.0)
        if is_hp:
            tot_low = float(pool_low_bins.sum())
            if tot_low > C_low:
                over = tot_low - C_low
                scarto_perso[i] += over
                for k in range(len(pool_low_bins)):
                    drop = min(pool_low_bins[k], over)
                    pool_low_bins[k] -= drop
                    over -= drop
                    if over <= 1e-12:
                        break
            soc_low_bins = pool_low_bins
        else:
            soc_low_bins = np.zeros(len(bin_T))

    E_hot = float(q_hot_direct.sum())
    E_alta = float(q_alta.sum())
    E_bassa = float(q_bassa.sum())
    E_bk = float(q_backup.sum())
    E_el_alta = float(el_alta.sum())
    E_el_bassa = float(el_bassa.sum())
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


def ottimizza_cascata(dom_arr, q_hot_arr, q_int_arr, q_low_bins, bin_T, soil_arr,
                      mandata, ritorno, T_int, dT_evap, eta_hp, parallelo,
                      capex_hp_func, capex_backup_kw, opex_backup_mwh, backup_cop,
                      prezzo_el, costo_m3, capex_solare_fisso, fattore_crf,
                      perdita_func, antigelo, **kwargs):
    """Dimensiona P_hp_alta, P_hp_bassa, V_hot, V_int, V_low a LCOH minimo.

    Vincolo: copertura 100 % delle ore (backup firm sul picco).
    picco_kw_override: picco di dimensionamento gia corretto con la
    contemporaneita QM (P5).
    """
    dom_tot = float(dom_arr.sum())
    if dom_tot <= 0:
        return None
    picco_kw = kwargs.get("picco_kw_override") or float(dom_arr.max()) * 1000.0
    is_hp = (parallelo == "HP bassa T")
    cop_a_ref = float(cop_singola(T_int - dT_evap, mandata, eta_hp))
    frac_a = max(1.0 - 1.0 / cop_a_ref, 0.0)

    # La HP alta T e sempre dimensionata sul picco: e la macchina di base del
    # sistema (merit order), non un'opzione. Il combustibile resta firm come
    # ridondanza, ma nel dispatch entra solo sul residuo.
    P_alta = picco_kw
    if is_hp:
        P_bassa = picco_kw * frac_a * 1.1
        P_bk = 0.0
    else:
        P_bassa = 0.0
        P_bk = picco_kw

    ha_hot = float(q_hot_arr.sum()) > 1e-6
    v_hot_cands = [0.0, 300.0, 800.0] if ha_hot else [0.0]
    v_int_cands = [0.0, 400.0, 800.0, 1500.0]
    v_low_cands = [0.0, 400.0, 800.0] if is_hp else [0.0]

    def _valuta(v_hot, v_int, v_low):
        r = dispatch_cascata(dom_arr, q_hot_arr, q_int_arr, q_low_bins, bin_T, soil_arr,
                             mandata, ritorno, T_int, dT_evap, eta_hp,
                             v_hot, v_int, v_low, P_alta, P_bassa,
                             parallelo=parallelo, P_backup_kw=P_bk, backup_cop=backup_cop,
                             antigelo=antigelo,
                             perdita_sett_pct=perdita_func(max(v_int, v_low, v_hot)))
        capex = (P_alta * capex_hp_func(P_alta)
                 + (P_bassa * capex_hp_func(P_bassa) if is_hp else P_bk * capex_backup_kw)
                 + (v_hot + v_int + v_low) * costo_m3 + capex_solare_fisso)
        opex = r["E_el_tot"] * prezzo_el + r["E_backup"] * opex_backup_mwh
        lcoh = (capex * fattore_crf + opex) / dom_tot
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
    if best is None:
        for vh in v_hot_cands:
            for vi in v_int_cands:
                for vl in v_low_cands:
                    r = _valuta(vh, vi, vl)
                    if best is None or r["ore_scoperte"] < best.get("ore_scoperte", 1e9) or \
                       (r["ore_scoperte"] == best["ore_scoperte"] and r["lcoh"] < best["lcoh"]):
                        best = r
    return best


# =============================================================================
# GENERAZIONE PROFILI DI OFFERTA
# =============================================================================
def _giorni_chiusura_set(giorni_chiusura_annui, seed):
    if not giorni_chiusura_annui or giorni_chiusura_annui <= 0:
        return set()
    rng = np.random.default_rng(seed)
    n = int(giorni_chiusura_annui)
    natale = pd.date_range("2024-12-20", "2024-12-31")
    agosto = pd.date_range("2024-08-05", "2024-08-25")
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
    rng = np.random.default_rng(seed)
    P_nom = row["P_kW"] / 1000.0
    T_disp = row["T_alta_C"] - pinch
    profilo = row["profilo"]
    giorni_sett = int(row["giorni_sett"]) if not pd.isna(row.get("giorni_sett")) else 7
    chiusi = _giorni_chiusura_set(row.get("chiusura_gg", 0), seed)

    P = np.zeros(len(HOURS_2024))
    Td = np.full(len(HOURS_2024), np.nan)
    giorno_di = HOURS_2024.normalize()
    ora_di = HOURS_2024.hour

    for d in DAYS_2024:
        if d.weekday() >= giorni_sett or d in chiusi:
            continue
        mg = (giorno_di == d)

        if profilo == "continuo":
            P[mg] = P_nom
            Td[mg] = T_disp
        elif profilo == "notturno_18_08":
            notte = mg & ((ora_di >= 18) | (ora_di < 8))
            P[notte] = P_nom
            Td[notte] = T_disp
        elif profilo.startswith("ore_giorno_"):
            n_ore = int(profilo.split("_")[-1])
            start = 6
            fascia = mg & (ora_di >= start) & (ora_di < start + n_ore)
            P[fascia] = P_nom
            Td[fascia] = T_disp
        elif profilo == "cf_random":
            cf = float(row["cf"]) if not pd.isna(row.get("cf")) else 0.3
            idx_g = np.where(mg)[0]
            attive = rng.random(len(idx_g)) < cf
            P[idx_g[attive]] = P_nom
            Td[idx_g[attive]] = T_disp
        elif profilo == "ciclico_colate":
            n_cicli = int(rng.integers(int(row["cicli_min"]), int(row["cicli_max"]) + 1))
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
                T_ist = row["T_alta_C"] - fase * (row["T_alta_C"] - row["T_out_C"])
                dT_ist = max(T_ist - row["T_out_C"], 0)
                dT_max = max(row["T_alta_C"] - row["T_out_C"], 1)
                P[gi] = P_nom * (dT_ist / dT_max)
                Td[gi] = T_ist - pinch
        else:
            P[mg] = P_nom
            Td[mg] = T_disp

    return pd.DataFrame({"datetime": HOURS_2024, "MWh": P, "P_kW": P * 1000, "T_disponibile": Td})


@st.cache_data
def load_data():
    buildings = pd.read_csv("maniago_domanda_edifici.csv")
    try:
        _coord = pd.read_csv("edifici_pubblici_coordinate.csv")[["edificio", "lat", "lon", "indirizzo"]]
        buildings = buildings.merge(_coord, on="edificio", how="left")
    except Exception:
        buildings["lat"] = np.nan
        buildings["lon"] = np.nan
        buildings["indirizzo"] = ""
    domanda = pd.read_csv("maniago_domanda_oraria_8760h_HDD_reale.csv", parse_dates=["datetime"])

    # --- P4: guardia anno bisestile (2024 ha 8784 ore, non 8760) ---
    if not domanda["datetime"].isin(HOURS_2024).all():
        _n_orfani = int((~domanda["datetime"].isin(HOURS_2024)).sum())
        st.warning(
            f"\u26a0\ufe0f {_n_orfani} timestamp della domanda non trovano riscontro in HOURS_2024 "
            f"(il 2024 e bisestile: 8784 ore attese, non 8760). Queste ore vengono escluse "
            f"in silenzio da tutti i bilanci. Rigenera "
            f"`maniago_domanda_oraria_8760h_HDD_reale.csv` sul calendario 2024 completo."
        )

    domanda = domanda.merge(buildings[["edificio", "cluster", "tipologia", "tipo_utenza"]],
                            on="edificio", how="left")
    flussi = pd.read_csv("maniago_flussi_offerta.csv")
    flussi["id_flusso"] = flussi["azienda"] + " · " + flussi["flusso"]
    pvgis = pd.read_csv("pvgis_maniago_pulito.csv", parse_dates=["datetime"])
    buildings = buildings[~buildings["edificio"].str.startswith("Residenziale Zona")].copy()

    _zp = carica_zone_confini()
    if not _zp:
        st.error("\u26a0\ufe0f File **TLR_zones_borders.geojson** non trovato: le zone restano quelle vecchie.")
    if _zp:
        _centri = {ZONE_NOMI[z]: (np.mean([r[:, 1].mean() for r in a]), np.mean([r[:, 0].mean() for r in a]))
                   for z, a in _zp.items()}
        _out = []
        for r in buildings.itertuples():
            z = zona_da_coordinate(r.lat, r.lon, _zp)
            if z is None and not (r.lat is None or (isinstance(r.lat, float) and np.isnan(r.lat))):
                z = min(_centri, key=lambda k: (_centri[k][0] - r.lat) ** 2 + (_centri[k][1] - r.lon) ** 2)
            _out.append(z if z else "Zona 4 - Centro")
        buildings["cluster"] = _out
        _esclusi = buildings["cluster"] == "__ESCLUSO__"
        if _esclusi.any():
            buildings = buildings[~_esclusi].copy()
    else:
        buildings["cluster"] = buildings["cluster"].replace({
            "NE-Centro": "Zona 1 - Comune NE", "Ex Bioman": "Zona 2 - Ex Bioman",
            "Campagna": "Zona 3 - Sud", "Ovest": "Zona 5 - Ovest"})
    domanda = domanda[domanda["edificio"].isin(buildings["edificio"])].copy()
    domanda = domanda.drop(columns=["cluster"], errors="ignore").merge(
        buildings[["edificio", "cluster"]], on="edificio", how="left")

    try:
        priv = pd.read_csv("maniago_privati_edifici.csv")
    except Exception:
        priv = pd.DataFrame(columns=["edificio", "cluster", "anello", "lat", "lon",
                                     "MWh_SH", "MWh_ACS", "consumo_annuo_MWh", "tipo_utenza"])
    if not priv.empty:
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
            _e = _u * MWH_PER_UNITA
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
    frames = []
    for i, row in flussi_df.iterrows():
        prof = genera_flusso(row, pinch=pinch, seed=i * 13 + 1)
        prof["id_flusso"] = row["id_flusso"]
        prof["azienda"] = row["azienda"]
        prof["flusso"] = row["flusso"]
        prof["destinazione"] = row["destinazione"]
        prof["fonte"] = row["azienda"]
        frames.append(prof[["datetime", "id_flusso", "azienda", "flusso", "destinazione",
                            "fonte", "MWh", "P_kW", "T_disponibile"]])
    if not frames:
        return pd.DataFrame(columns=["datetime", "id_flusso", "azienda", "flusso", "destinazione",
                                     "fonte", "MWh", "P_kW", "T_disponibile"])
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
    df_h["T_disponibile"] = np.nan
    return df_h[["datetime", "fonte", "MWh", "P_kW", "T_disponibile"]]


# =============================================================================
# ECONOMIA
# =============================================================================
def van(flussi_cassa, tasso):
    """Valore Attuale Netto. flussi_cassa[0] e l'investimento (negativo)."""
    return float(sum(f / (1.0 + tasso) ** t for t, f in enumerate(flussi_cassa)))


def tir(flussi_cassa, lo=-0.95, hi=1.5, tol=1e-7, itmax=300):
    """Tasso Interno di Rendimento per bisezione. None se non esiste."""
    f_lo = van(flussi_cassa, lo)
    f_hi = van(flussi_cassa, hi)
    if f_lo * f_hi > 0:
        return None
    for _ in range(itmax):
        mid = (lo + hi) / 2.0
        f_mid = van(flussi_cassa, mid)
        if abs(f_mid) < tol:
            return mid
        if f_lo * f_mid < 0:
            hi = mid
        else:
            lo, f_lo = mid, f_mid
    return (lo + hi) / 2.0


def payback_semplice(flussi_cassa):
    """Tempo di ritorno semplice (non attualizzato), in anni. None se mai."""
    cum = 0.0
    for t, f in enumerate(flussi_cassa):
        prev = cum
        cum += f
        if t > 0 and prev < 0 <= cum:
            return t - 1 + (-prev / f if f != 0 else 0)
    return None


# =============================================================================
# CARICAMENTO
# =============================================================================
buildings, domanda, flussi, pvgis, privati, condomini = load_data()

st.title("\U0001F525 Maniago TLR — Domanda, Offerta, Dimensionamento")
st.markdown(PROGETTO_HTML)
st.caption(
    "Anno tipo (calendario 2024, 8784 ore) · Domanda: temperatura calibrata su dati reali "
    "stazione Vivaro (2011, corretta verso i 2.850 GG ufficiali di Maniago) · "
    "Offerta: flussi da CSV + camini forni Pietro Rosa da misure Ecol Studio 14/07/2025. "
    "Metodologia: **QM Holzheizwerke Planning Handbook** (perdite di rete Fig. 12.3, "
    "contemporaneità Fig. 12.2) e **IEA DHC TS5** (COP e CAPEX pompe di calore, accumuli)."
)

tab_domanda, tab_offerta, tab_dimensionamento, tab_confronto, tab_economia = st.tabs(
    ["\U0001F3E0 Domanda", "\u267B\ufe0f Offerta", "\U0001F9EE Dimensionamento",
     "\U0001F4CA Confronto scenari", "\U0001F4B6 Analisi economica"]
)


# =============================================================================
# TAB 1 - DOMANDA
# =============================================================================
with tab_domanda:
    col_filtri, col_contenuto = st.columns([1, 3])

    with col_filtri:
        st.markdown("#### \U0001F321\ufe0f Linea ideale di rete")
        T_mandata_ideale = st.slider("Mandata (°C)", 35, 95, key="dom_t_mandata",
                                     help="Temperatura obiettivo di mandata alla rete")
        T_ritorno_ideale = st.slider("Ritorno (°C)", 20, 60, key="dom_t_ritorno",
                                     help="Temperatura di ritorno rete")
        st.caption("Questi due valori guidano anche i calcoli in Offerta e Dimensionamento.")
        if st.button("\u21ba Ripristina default", key="btn_reset_default"):
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
            if _ha_p and cc1.checkbox("privati", key=f"dom_p_{c}"):
                sel_priv_zone.append(c)
            if _ha_c and cc2.checkbox("condomini", key=f"dom_c_{c}"):
                sel_cond_zone.append(c)
        _conf = sorted(set(sel_priv_zone) & set(sel_cond_zone))
        if _conf:
            sel_cond_zone = [z for z in sel_cond_zone if z not in _conf]
            st.caption("\u26a0\ufe0f In " + ", ".join(z.split(" - ")[0] for z in _conf) +
                       " i condomini sono già dentro i privati GIS: conto solo i privati.")

        st.markdown("**Utenza pubblica**")
        pub_on = st.checkbox("Includi edifici pubblici", value=True, key="dom_tu_pub")

        fattore_correzione = 100
        if sel_priv_zone:
            fattore_correzione = st.slider(
                "Tasso di allacciamento privati (%)", 10, 100, 60, step=5, key="dom_priv_fattore",
                help="Quota di privati che si allaccia davvero. QM: 50-80 % tipico.")
        mwh_unita = MWH_PER_UNITA
        tasso_cond = 100
        if sel_cond_zone:
            mwh_unita = st.slider("Consumo per unità abitativa (MWh/a)", 5.0, 15.0, MWH_PER_UNITA,
                                  step=0.5, key="dom_mwh_unita",
                                  help="Appartamento tipo esistente in FVG: 7-11 MWh/a.")
            tasso_cond = st.slider("Tasso di adesione condomini (%)", 10, 100, 80, step=5,
                                   key="dom_cond_tasso")

        selected_privati = []
        if sel_priv_zone:
            selected_privati += buildings.loc[(buildings["tipo_utenza"] == "Privato (potenziale)")
                                              & (buildings["cluster"].isin(sel_priv_zone)), "edificio"].tolist()
        if sel_cond_zone:
            selected_privati += buildings.loc[(buildings["tipo_utenza"] == "Condominio")
                                              & (buildings["cluster"].isin(sel_cond_zone)), "edificio"].tolist()
        liv_est = 6 if sel_priv_zone else 0

        # --- P5: conteggio utenze private/condominiali per la contemporaneita QM ---
        _n_priv_reale = 0
        if sel_priv_zone and not privati.empty:
            _n_priv_reale += int(len(privati[privati["cluster"].isin(sel_priv_zone)]))
        if sel_cond_zone and not condomini.empty:
            _n_priv_reale += int(condomini[condomini["cluster"].isin(sel_cond_zone)]["unita"].sum())
        # Se un buffer sul tracciato ha ristretto i privati agganciabili, correggo
        # anche il conteggio utenze per la contemporaneita QM.
        _buff_records_qm = st.session_state.get("_dom_priv_in_buffer", None)
        if _buff_records_qm is not None and sel_priv_zone and not privati.empty:
            _n_priv_zone_tot = int(len(privati[privati["cluster"].isin(sel_priv_zone)]))
            if _n_priv_zone_tot > 0:
                # scalo la parte "privati" (non i condomini) alla quota buffer
                _n_cond_uni = 0
                if sel_cond_zone and not condomini.empty:
                    _n_cond_uni = int(condomini[condomini["cluster"].isin(sel_cond_zone)]["unita"].sum())
                _n_priv_reale = int(round(len(_buff_records_qm))) + _n_cond_uni
        st.session_state["_dom_n_privati"] = _n_priv_reale
        if _n_priv_reale > 1:
            _f_sim_ui = coeff_simultaneita_QM(_n_priv_reale)
            st.caption(f"\U0001F465 Utenze private/condominiali: **{_n_priv_reale}** · "
                       f"contemporaneità QM: **{_f_sim_ui:.2f}** (agisce sul picco, "
                       f"non sull'energia annua)")

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
            format_func=lambda m: MONTH_NAMES[m - 1], key="dom_mesi")

    mask_building = (buildings["cluster"].isin(selected_clusters)
                     & (((buildings["tipo_utenza"] == "Pubblico") & pub_on
                         & buildings["tipologia"].isin(selected_tip))
                        | buildings["edificio"].isin(selected_privati)))
    selected_buildings = buildings.loc[mask_building, "edificio"].tolist()

    # Se il buffer sul tracciato ha ristretto i privati agganciabili, correggo
    # il fattore di allacciamento in modo che rappresenti la quota realmente
    # servita rispetto al totale della zona. Aggregando su zona/anello questo
    # e l'unico modo di rispettare il vincolo geometrico senza cambiare i dati.
    _buff_records = st.session_state.get("_dom_priv_in_buffer", None)
    _priv_zone_totali = 0
    _priv_zone_buffer = 0
    if sel_priv_zone and not privati.empty:
        _priv_zone_totali = int(len(privati[privati["cluster"].isin(sel_priv_zone)]))
    if _buff_records is not None:
        _priv_zone_buffer = int(len(_buff_records))
    quota_buffer = (_priv_zone_buffer / _priv_zone_totali
                    if _priv_zone_totali > 0 and _buff_records is not None else 1.0)
    fattore_effettivo = (fattore_correzione / 100.0) * quota_buffer

    st.session_state["_dom_edifici"] = selected_buildings
    st.session_state["_dom_zone"] = selected_clusters
    st.session_state["_dom_fattore_privato"] = fattore_effettivo
    st.session_state["_dom_ha_privati"] = len(selected_privati) > 0
    st.session_state["_dom_quota_buffer"] = quota_buffer

    dom = domanda[domanda["edificio"].isin(selected_buildings)].copy()
    dom["month"] = dom["datetime"].dt.month
    dom = dom[(dom["month"] >= month_range[0]) & (dom["month"] <= month_range[1])]

    is_privato = dom["tipo_utenza"] == "Privato (potenziale)"
    fattore = fattore_effettivo
    dom.loc[is_privato, "MWh_riscaldamento"] = dom.loc[is_privato, "MWh_riscaldamento"] * fattore
    dom.loc[is_privato, "MWh_ACS"] = dom.loc[is_privato, "MWh_ACS"] * fattore
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

            tot = agg_total["MWh_sel"].sum()
            picco = agg_total["MWh_sel"].max()
            ora_picco = agg_total.loc[agg_total["MWh_sel"].idxmax(), "datetime"]
            load_factor = tot / (picco * len(agg_total)) if picco > 0 else 0
            acs_tot = dom["MWh_ACS"].sum() if show_acs else 0.0

            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Energia nel periodo", f"{tot:,.0f} MWh".replace(",", "."))
            k2.metric("Picco orario", f"{picco:.3f} MW", help=f"il {ora_picco.strftime('%d/%m alle %H:00')}")
            k3.metric("Quota ACS", f"{(acs_tot / tot * 100 if tot else 0):.0f}%",
                      help=f"{acs_tot:,.0f} MWh ACS su {tot:,.0f} MWh totali".replace(",", "."))
            k4.metric("Fattore di carico", f"{load_factor * 100:.1f}%")

            bsel = buildings[buildings["edificio"].isin(selected_buildings)].copy()
            bsel_all = buildings[buildings["tipo_utenza"] == "Pubblico"].copy()
            bmap = bsel.dropna(subset=["lat", "lon"]) if "lat" in bsel.columns else bsel.iloc[0:0]

            if not bmap.empty:
                st.markdown("##### \U0001F5FA\ufe0f Mappa degli edifici serviti")
                fig_map = go.Figure()
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
                if sel_priv_zone and not privati.empty:
                    _pv = privati[privati["cluster"].isin(sel_priv_zone)]
                    if not _pv.empty:
                        fig_map.add_trace(go.Scattermapbox(
                            lat=_pv["lat"], lon=_pv["lon"], mode="markers",
                            name=f"Privati: {len(_pv)}",
                            marker=dict(size=6, color="#B57EDC", opacity=0.75),
                            text=(_pv["nome"].fillna("").astype(str) + "<br>"
                                  + _pv["via"].fillna("").astype(str)
                                  + "<br>est." + _pv["anello"].astype(str) + " · "
                                  + _pv["consumo_annuo_MWh"].round(1).astype(str) + " MWh/a"),
                            hoverinfo="text"))
                fig_map.update_layout(
                    mapbox=dict(style="open-street-map",
                                center=dict(lat=float(bmap["lat"].mean()), lon=float(bmap["lon"].mean())),
                                zoom=13),
                    height=430, margin=dict(t=10, b=0, l=0, r=0),
                    legend=dict(orientation="h", yanchor="bottom", y=1.01))
                st.plotly_chart(fig_map, use_container_width=True)
                _senza = bsel.shape[0] - bmap.shape[0]
                if _senza > 0:
                    st.caption(f"{_senza} edifici senza coordinate non mostrati.")

                st.markdown("##### \U0001F525 Densità della domanda termica")
                dc1, dc2 = st.columns([2, 1])
                vista_dens = dc1.radio("Cosa mostrare",
                                       ["Potenziale totale (tutti gli edifici)", "Solo selezionati"],
                                       horizontal=True, key="dom_dens_vista")
                cella_m = dc2.select_slider("Cella (m)", options=[100, 150, 200], value=150,
                                            key="dom_dens_cella")
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
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Densità mediana", f"{_grid['dens'].median():.0f} MWh/(ha·a)")
                    m2.metric("Celle sopra 300", f"{(_grid['dens'] > 300).mean() * 100:.0f}%",
                              help="Sopra ~300 MWh/(ha·a) il TLR e generalmente favorevole")
                    m3.metric("Energia nelle celle dense",
                              f"{_grid.loc[_grid['dens'] > 300, 'MWh'].sum() / _grid['MWh'].sum() * 100:.0f}%")
                    st.caption(f"Griglia da {cella_m} m ({_ha:.2f} ha per cella).")

            fig = go.Figure()
            cluster_nel_grafico = [c for c in selected_clusters if c in agg_cluster["cluster"].unique()]
            for cl in cluster_nel_grafico:
                sub = agg_cluster[agg_cluster["cluster"] == cl]
                colore = CLUSTER_COLORS.get(cl, "#888888")
                fig.add_trace(go.Scatter(x=sub["datetime"], y=sub["MWh_sel"], mode="lines",
                                         name=cl, stackgroup="one",
                                         line=dict(width=0.6, color=colore),
                                         fillcolor=hex_to_rgba(colore, 0.85)))
            fig.update_layout(height=420, yaxis_title="MWh/h (\u2248 MW)", xaxis_title="",
                              legend=dict(orientation="h", yanchor="bottom", y=1.02))
            st.plotly_chart(fig, use_container_width=True)

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
            monthly_dom["mese"] = monthly_dom["datetime"].dt.month.map(lambda m: MONTH_NAMES[m - 1])
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

        # ---------------------------------------------------------------------
        # P1 - Densita termica lineare (doppio fattore di allacciamento rimosso)
        # ---------------------------------------------------------------------
        if not privati.empty:
            st.markdown("##### \U0001F4CF Densità termica lineare per zona/livello (stima teorica)")
            st.caption("**Stima esplorativa** per capire dove la rete rende: per ogni zona e "
                       "livello di estensione, quanto sarebbe la densità lineare se si servissero "
                       "*tutti* i privati fino a quell'anello. Il valore realistico invece dipende "
                       "dal buffer sul tracciato pubblico (vedi *Ipotesi di tracciato* più sotto). "
                       "QM: sotto ~1,2 MWh/(m·a) la rete fatica a ripagarsi, sopra ~2,0 e buona.")
            cD1, cD2 = st.columns(2)
            costo_m_rete = cD1.slider("Costo rete (\u20ac/m di trincea)", 200, 1500, 600, step=50,
                                      key="dom_costo_rete")
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
                    # P1: il fattore di allacciamento si applica UNA SOLA VOLTA
                    _E = _s["consumo_annuo_MWh"].sum() * (fattore_correzione / 100.0)
                    if _L < 1:
                        continue
                    righe_d.append({"Zona": _z, "Livello": _l, "Edifici": len(_s),
                                    "Domanda (MWh/a)": round(_E), "Rete (m)": round(_L),
                                    "Densità (MWh/m·a)": round(_E / _L, 2),
                                    "CAPEX rete (\u20ac)": round(_L * costo_m_rete)})
            if righe_d:
                df_d = pd.DataFrame(righe_d)
                fig_dl = go.Figure()
                for _z in df_d["Zona"].unique():
                    _sub = df_d[df_d["Zona"] == _z]
                    fig_dl.add_trace(go.Scatter(x=_sub["Livello"], y=_sub["Densità (MWh/m·a)"],
                                                mode="lines+markers", name=_z,
                                                line=dict(color=CLUSTER_COLORS.get(_z, "#888"), width=2.5),
                                                marker=dict(size=9)))
                fig_dl.add_hline(y=2.0, line_dash="dot", line_color="#3FA34D",
                                 annotation_text="buona (2,0)", annotation_position="top left")
                fig_dl.add_hline(y=1.2, line_dash="dot", line_color="#E63946",
                                 annotation_text="soglia critica (1,2)", annotation_position="bottom left")
                fig_dl.update_layout(height=350, xaxis_title="Livello di estensione",
                                     yaxis_title="Densità lineare (MWh per metro di rete, anno)",
                                     legend=dict(orientation="h", yanchor="bottom", y=1.02),
                                     margin=dict(t=30, b=10))
                st.plotly_chart(fig_dl, use_container_width=True)
                st.dataframe(df_d, use_container_width=True, hide_index=True)
                _tot_L = df_d[df_d["Livello"] == max(liv_est, 1)]["Rete (m)"].sum()
                if liv_est > 0 and _tot_L > 0:
                    st.caption(f"Al livello **{liv_est}** nelle zone attive: rete \u2248 **{_tot_L:,.0f} m**, "
                               f"CAPEX rete \u2248 **{_tot_L * costo_m_rete:,.0f} \u20ac**.".replace(",", "."))

        if sel_cond_zone and not condomini.empty:
            st.divider()
            st.markdown("##### \U0001F3E2 Condomini censiti nelle zone selezionate")
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
                                        "unita": "Unità"}).sort_values(["Zona", "Unità"],
                                                                            ascending=[True, False])
            st.dataframe(_tab, use_container_width=True, hide_index=True)

        st.divider()
        st.markdown("##### \U0001F6E4\ufe0f Ipotesi di tracciato della rete")
        st.caption(f"Rete progettata in **2 tempi**: prima il tratto *obbligato* che collega la "
                   f"**sottocentrale** ({CENTRALE_LAT:.4f}, {CENTRALE_LON:.4f}) agli **edifici pubblici** "
                   f"e ai **condomini censiti** selezionati; poi i **privati** vengono agganciati "
                   f"solo se cadono entro un raggio dal tubo pubblico. "
                   f"**Zone senza pubblici** (es. Zona 3) possono essere agganciate in modo "
                   f"opportunistico se il tubo di altre zone ci passa vicino.")

        # --- 1. Tratto obbligato: pubblici + condomini censiti (opzione B) ---
        _pts_obb = []
        if not bmap.empty:
            _pts_obb.append(bmap[["lat", "lon", "consumo_annuo_MWh"]].assign(tipo="pubblico"))
        if sel_cond_zone and not condomini.empty:
            _cond_z = condomini[condomini["cluster"].isin(sel_cond_zone)].copy()
            _cond_z["MWh_stimato"] = _cond_z["unita"] * mwh_unita * tasso_cond / 100.0
            _cond_z = _cond_z.dropna(subset=["lat", "lon"])[["lat", "lon", "MWh_stimato"]]
            if not _cond_z.empty:
                _cond_z = _cond_z.rename(columns={"MWh_stimato": "consumo_annuo_MWh"})
                _pts_obb.append(_cond_z.assign(tipo="condominio"))
        _obb = (pd.concat(_pts_obb, ignore_index=True).dropna(subset=["lat", "lon"])
                if _pts_obb else pd.DataFrame())

        if _obb.empty:
            st.info("Seleziona almeno un edificio pubblico o un condominio "
                    "georeferenziato per vedere il tracciato.")
        else:
            tc1, tc2, tc3 = st.columns(3)
            tort = tc1.slider("Fattore di tortuosità", 1.0, 2.0, 1.35, step=0.05, key="dom_tort")
            costo_m_tr = tc2.slider("Costo rete (\u20ac/m)", 200, 1500, 600, step=50, key="dom_costo_tr")
            buffer_m = tc3.slider("Buffer privati dal tubo pubblico (m)", 20, 150, 50, step=5,
                                  key="dom_buffer",
                                  help="Un privato viene allacciato solo se si trova entro questa "
                                       "distanza dal tubo del tratto pubblico. Piu il buffer e "
                                       "piccolo, piu selettivo diventa (meno stub, densità lineare "
                                       "piu alta).")

            # Scelta metodo: OSM (Dijkstra su strade) con fallback MST + tortuosita
            usa_strade = st.checkbox(
                "\U0001F6E3\ufe0f Tracciato sulle strade reali (OSM)", value=True, key="dom_usa_osm",
                help="Al primo avvio scarica la rete stradale di Maniago da OpenStreetMap "
                     "(qualche decina di secondi). Poi la cache resta locale in "
                     "`maniago_strade_cache.json`. Se disattivato o se il download fallisce, "
                     "si usa l'MST in linea d'aria con tortuosita.")

            _strade_res = carica_grafo_strade(CENTRALE_LAT, CENTRALE_LON, raggio_km=1.8) if usa_strade else (None, None)
            _strade, _osm_err = _strade_res if isinstance(_strade_res, tuple) else (_strade_res, None)
            _uso_osm = _strade is not None
            if usa_strade and not _uso_osm:
                _msg_err = f" — causa: `{_osm_err}`" if _osm_err else ""
                st.warning(f"\u26a0\ufe0f Rete stradale OSM non disponibile{_msg_err}. "
                           f"Uso il metodo MST + tortuosita. "
                           f"**Suggerimenti**: (1) verifica connessione internet; "
                           f"(2) installa dipendenze con `pip install networkx scipy requests`; "
                           f"(3) se sei dietro proxy/VPN aziendale, disattivalo temporaneamente per "
                           f"scaricare la cache la prima volta.")
            if _uso_osm and build_grafo_stradale(_strade) is None:
                st.warning("\u26a0\ufe0f modulo `networkx` non installato "
                           "(pip install networkx). Uso il metodo MST.")
                _uso_osm = False

            if _uso_osm:
                # --- ROUTING SU STRADE: Steiner approssimato via Dijkstra ---
                _G = build_grafo_stradale(_strade)
                # snap centrale + edifici del tratto obbligato
                _lat_obb = np.concatenate([[CENTRALE_LAT], _obb["lat"].values])
                _lon_obb = np.concatenate([[CENTRALE_LON], _obb["lon"].values])
                _nodi_obb, _dsnap_obb = snap_a_strade(_lat_obb, _lon_obb, _strade)
                _rad_nodo = _nodi_obb[0]
                _target_nodi = _nodi_obb[1:]
                _archi_G, _len_pub_osm, _nodi_tubo = albero_steiner_su_strade(
                    _G, _target_nodi, _rad_nodo)
                _archi_pub = archi_a_coords(_archi_G, _strade)
                # linee "ultimo metro" dagli edifici al nodo stradale
                _ultimi_metri = []
                _len_ultimi = 0.0
                for i in range(len(_obb)):
                    _lat_ed = float(_obb["lat"].iloc[i])
                    _lon_ed = float(_obb["lon"].iloc[i])
                    _n = _nodi_obb[i + 1]
                    _lat_n, _lon_n = _strade["nodi"][_n]
                    _ultimi_metri += [_lat_ed, _lat_n, None]
                    _ultimi_metri += [_lon_ed, _lon_n, None]  # placeholder
                    _len_ultimi += float(_dsnap_obb[i + 1])
                # ricostruisco correttamente lat/lon separati
                _um_lat, _um_lon = [], []
                for i in range(len(_obb)):
                    _lat_ed = float(_obb["lat"].iloc[i])
                    _lon_ed = float(_obb["lon"].iloc[i])
                    _n = _nodi_obb[i + 1]
                    _lat_n, _lon_n = _strade["nodi"][_n]
                    _um_lat += [_lat_ed, _lat_n, None]
                    _um_lon += [_lon_ed, _lon_n, None]
                _len_pub_t = _len_pub_osm + _len_ultimi
            else:
                # --- FALLBACK: MST + tortuosita ---
                _archi_pub, _len_pub = mst_archi(_obb["lat"].values, _obb["lon"].values,
                                                 radice=(CENTRALE_LAT, CENTRALE_LON))
                _len_pub_t = _len_pub * tort
                _um_lat, _um_lon = [], []
                _nodi_tubo = set()

            # --- 2. Buffer privati: aggancio via strade se disponibili ---
            _priv_in = pd.DataFrame()
            _len_stub_t = 0.0
            _stub_lat_l, _stub_lon_l = [], []
            _fatt_priv = fattore_correzione / 100.0
            if sel_priv_zone and not privati.empty and _archi_pub:
                _pv = privati[privati["cluster"].isin(sel_priv_zone)].dropna(subset=["lat", "lon"]).copy()
                if not _pv.empty:
                    _dmin, _idx_arco, _lat_tubo, _lon_tubo = buffer_tracciato(
                        _archi_pub, _pv["lat"].values, _pv["lon"].values, raggio_m=buffer_m)
                    _pv["dist_tubo_m"] = _dmin
                    _in_buffer = _dmin <= buffer_m
                    _priv_in = _pv[_in_buffer].copy()
                    if not _priv_in.empty:
                        if _uso_osm:
                            # per ogni privato, dijkstra dal suo nodo strada al set dei nodi-tubo
                            _lat_pv = _priv_in["lat"].values
                            _lon_pv = _priv_in["lon"].values
                            _nodi_pv, _dsnap_pv = snap_a_strade(_lat_pv, _lon_pv, _strade)
                            _lat_stub_flat, _lon_stub_flat = [], []
                            _len_stub_m = 0.0
                            for i in range(len(_priv_in)):
                                # ultimo metro edificio -> nodo stradale
                                _n = _nodi_pv[i]
                                _lat_n, _lon_n = _strade["nodi"][_n]
                                _lat_stub_flat += [float(_lat_pv[i]), _lat_n, None]
                                _lon_stub_flat += [float(_lon_pv[i]), _lon_n, None]
                                _len_stub_m += float(_dsnap_pv[i])
                                # percorso stradale dal nodo al tubo
                                _stub_archi, _stub_len, _agg = dijkstra_stub_al_tubo(
                                    _G, _nodi_tubo, _n)
                                for a, b, w in _stub_archi:
                                    _la1, _lo1 = _strade["nodi"][a]
                                    _la2, _lo2 = _strade["nodi"][b]
                                    _lat_stub_flat += [_la1, _la2, None]
                                    _lon_stub_flat += [_lo1, _lo2, None]
                                _len_stub_m += _stub_len
                            _stub_lat_l = _lat_stub_flat
                            _stub_lon_l = _lon_stub_flat
                            _len_stub_t = _len_stub_m
                        else:
                            # MST classico: linea dritta al punto del tubo * tortuosita
                            _pt_tubo_lat = _lat_tubo[_in_buffer]
                            _pt_tubo_lon = _lon_tubo[_in_buffer]
                            _lat_stub_flat, _lon_stub_flat = [], []
                            _len_stub_m = 0.0
                            for i, (_, _r) in enumerate(_priv_in.iterrows()):
                                _lat_stub_flat += [float(_pt_tubo_lat[i]), float(_r["lat"]), None]
                                _lon_stub_flat += [float(_pt_tubo_lon[i]), float(_r["lon"]), None]
                                _len_stub_m += float(_r["dist_tubo_m"])
                            _stub_lat_l = _lat_stub_flat
                            _stub_lon_l = _lon_stub_flat
                            _len_stub_t = _len_stub_m * tort

            _len_totale = _len_pub_t + _len_stub_t

            # --- linee tracciato pubblico ---
            _lat_l, _lon_l = [], []
            for (a, b, _d) in _archi_pub:
                _lat_l += [a[0], b[0], None]
                _lon_l += [a[1], b[1], None]

            fig_tr = go.Figure()
            # tracciato pubblico (rosso, spesso)
            _label_pub = (f"Tratto obbligato (strade OSM): {_len_pub_t / 1000:.2f} km" if _uso_osm
                          else f"Tratto obbligato (MST x{tort}): {_len_pub_t / 1000:.2f} km")
            fig_tr.add_trace(go.Scattermapbox(lat=_lat_l, lon=_lon_l, mode="lines",
                                              line=dict(width=3, color="#FF4B4B"),
                                              name=_label_pub,
                                              hoverinfo="skip"))
            # ultimi metri edificio->strada (rosa tratteggiato)
            if _uso_osm and _um_lat:
                fig_tr.add_trace(go.Scattermapbox(lat=_um_lat, lon=_um_lon, mode="lines",
                                                  line=dict(width=1.2, color="#FF9AA0"),
                                                  name="Ultimi metri edificio→strada",
                                                  hoverinfo="skip"))
            # stub privati (giallo, sottile)
            if _stub_lat_l:
                fig_tr.add_trace(go.Scattermapbox(lat=_stub_lat_l, lon=_stub_lon_l, mode="lines",
                                                  line=dict(width=1.5, color="#F5C518"),
                                                  name=f"Allacci privati: {_len_stub_t / 1000:.1f} km",
                                                  hoverinfo="skip"))
            # pubblici (blu)
            if not bmap.empty:
                fig_tr.add_trace(go.Scattermapbox(
                    lat=bmap["lat"], lon=bmap["lon"], mode="markers", name="Pubblici",
                    marker=dict(size=10, color="#22C3DD"),
                    text=(bmap["edificio"] + "<br>"
                          + bmap["consumo_annuo_MWh"].round(0).astype(int).astype(str) + " MWh/a"),
                    hoverinfo="text"))
            # condomini (viola)
            if sel_cond_zone and not condomini.empty:
                _c_geo = condomini[condomini["cluster"].isin(sel_cond_zone)].dropna(subset=["lat", "lon"])
                if not _c_geo.empty:
                    _c_geo = _c_geo.copy()
                    _c_geo["MWh_stimato"] = (_c_geo["unita"] * mwh_unita * tasso_cond / 100.0).round(1)
                    fig_tr.add_trace(go.Scattermapbox(
                        lat=_c_geo["lat"], lon=_c_geo["lon"], mode="markers", name="Condomini",
                        marker=dict(size=9, color="#9B5DE5"),
                        text=(_c_geo["denominazione"].fillna("Condominio").astype(str) + "<br>"
                              + _c_geo["unita"].astype(str) + " unita\u0300 · "
                              + _c_geo["MWh_stimato"].astype(str) + " MWh/a"),
                        hoverinfo="text"))
            # privati DENTRO il buffer (verde)
            if not _priv_in.empty:
                fig_tr.add_trace(go.Scattermapbox(
                    lat=_priv_in["lat"], lon=_priv_in["lon"], mode="markers",
                    name=f"Privati agganciabili ({len(_priv_in)})",
                    marker=dict(size=5, color="#3FA34D", opacity=0.85),
                    text=(_priv_in.get("nome", pd.Series([""] * len(_priv_in))).fillna("").astype(str)
                          + "<br>dist. tubo: " + _priv_in["dist_tubo_m"].round(0).astype(int).astype(str)
                          + " m · " + _priv_in["consumo_annuo_MWh"].round(1).astype(str) + " MWh/a"),
                    hoverinfo="text"))
            # privati FUORI dal buffer (grigi trasparenti, per contesto)
            if sel_priv_zone and not privati.empty:
                _pv_all = privati[privati["cluster"].isin(sel_priv_zone)].dropna(subset=["lat", "lon"])
                if not _priv_in.empty:
                    _pv_out = _pv_all[~_pv_all.index.isin(_priv_in.index)]
                else:
                    _pv_out = _pv_all
                if not _pv_out.empty:
                    fig_tr.add_trace(go.Scattermapbox(
                        lat=_pv_out["lat"], lon=_pv_out["lon"], mode="markers",
                        name=f"Privati fuori buffer ({len(_pv_out)})",
                        marker=dict(size=3, color="#666666", opacity=0.35),
                        hoverinfo="skip"))
            # aziende
            for _n, (_la, _lo) in AZIENDE_COORD.items():
                fig_tr.add_trace(go.Scattermapbox(lat=[_la], lon=[_lo], mode="markers",
                                                  name=_n, marker=dict(size=9, color="#E9C46A"),
                                                  text=_n, hoverinfo="text", showlegend=False))
            # sottocentrale
            fig_tr.add_trace(go.Scattermapbox(
                lat=[CENTRALE_LAT], lon=[CENTRALE_LON], mode="markers+text", name="Sottocentrale",
                marker=dict(size=18, color="#FF9F1C"), text=["CENTRALE"], textposition="top right",
                textfont=dict(size=13, color="#FF9F1C")))
            _clat = (float(_obb["lat"].mean()) + CENTRALE_LAT) / 2
            _clon = (float(_obb["lon"].mean()) + CENTRALE_LON) / 2
            fig_tr.update_layout(mapbox=dict(style="open-street-map",
                                             center=dict(lat=_clat, lon=_clon), zoom=13.5),
                                 height=580, margin=dict(t=10, b=0, l=0, r=0),
                                 legend=dict(orientation="h", yanchor="bottom", y=1.01))
            st.plotly_chart(fig_tr, use_container_width=True)

            # --- energia servita ---
            _E_pub = float(bmap["consumo_annuo_MWh"].sum()) if not bmap.empty else 0.0
            _E_cond = 0.0
            if sel_cond_zone and not condomini.empty:
                _cond_sel = condomini[condomini["cluster"].isin(sel_cond_zone)]
                _E_cond = float(_cond_sel["unita"].sum()) * mwh_unita * tasso_cond / 100.0
            _E_priv = float(_priv_in["consumo_annuo_MWh"].sum()) * _fatt_priv if not _priv_in.empty else 0.0
            _E_tot = _E_pub + _E_cond + _E_priv
            _n_utenze_tot = (len(bmap) + (len(condomini[condomini['cluster'].isin(sel_cond_zone)])
                                          if sel_cond_zone and not condomini.empty else 0)
                             + len(_priv_in))

            t1, t2, t3, t4 = st.columns(4)
            t1.metric("Lunghezza totale rete", f"{_len_totale / 1000:.2f} km",
                      help=f"Obbligato {_len_pub_t / 1000:.2f} km + stub {_len_stub_t / 1000:.2f} km "
                           f"(tortuosità {tort})")
            t2.metric("Utenze totali",
                      f"{_n_utenze_tot}",
                      help=f"pubblici + condomini + {len(_priv_in) if not _priv_in.empty else 0} privati nel buffer")
            t3.metric("CAPEX rete", f"{_len_totale * costo_m_tr / 1e6:.2f} M\u20ac")
            _dens = _E_tot / _len_totale if _len_totale > 0 else 0.0
            t4.metric("Densità lineare", f"{_dens:.2f} MWh/(m·a)",
                      help="sotto ~1,2 la rete fatica a ripagarsi; sopra ~2,0 e buona (QM)")

            # --- breakdown ---
            b1, b2, b3 = st.columns(3)
            b1.metric("da pubblici", f"{_E_pub:,.0f} MWh/a".replace(",", "."),
                      help=f"{len(bmap)} edifici")
            b2.metric("da condomini", f"{_E_cond:,.0f} MWh/a".replace(",", "."),
                      help=f"adesione {tasso_cond}%")
            _n_priv_dentro = len(_priv_in) if not _priv_in.empty else 0
            _n_priv_totale = 0
            if sel_priv_zone and not privati.empty:
                _n_priv_totale = int(len(privati[privati["cluster"].isin(sel_priv_zone)]))
            _quota_bff = _n_priv_dentro / max(_n_priv_totale, 1) * 100
            b3.metric("da privati nel buffer",
                      f"{_E_priv:,.0f} MWh/a".replace(",", "."),
                      help=f"{_n_priv_dentro}/{_n_priv_totale} privati "
                           f"({_quota_bff:.0f}% delle zone attive) · "
                           f"buffer {buffer_m} m · allacciamento {fattore_correzione}%")

            # --- opportunistici: zone senza ancora (nessun pubblico né condominio) ---
            _zone_ancora = set()
            if not bmap.empty:
                _zone_ancora |= set(bmap["cluster"].unique())
            _zone_ancora |= set(sel_cond_zone)
            _zone_opportunistiche = [z for z in sel_priv_zone if z not in _zone_ancora]
            if _zone_opportunistiche and not _priv_in.empty:
                _priv_opp = _priv_in[_priv_in["cluster"].isin(_zone_opportunistiche)]
                if not _priv_opp.empty:
                    _E_opp = float(_priv_opp["consumo_annuo_MWh"].sum()) * _fatt_priv
                    _zn = ", ".join(z.split(" - ")[0] for z in _zone_opportunistiche)
                    st.info(f"\U0001F517 **Zone opportunistiche** ({_zn}): non hanno pubblici "
                            f"né condomini censiti, ma **{len(_priv_opp)} privati** "
                            f"cadono comunque nel buffer del tubo posato per le altre zone. "
                            f"Contribuiscono con **{_E_opp:,.0f} MWh/a**.".replace(",", "."))
                else:
                    _zn = ", ".join(z.split(" - ")[0] for z in _zone_opportunistiche)
                    st.warning(f"\U0001F4CD **Zone opportunistiche** ({_zn}): nessun privato "
                               f"cade nel buffer del tubo delle altre zone. Prova ad allargare "
                               f"il buffer, o dovrai valutare queste zone con un secondo tratto "
                               f"di rete dedicato.")

            if _dens < 1.2 and _len_totale > 100:
                st.warning(f"\u26a0\ufe0f Densità lineare {_dens:.2f} MWh/(m·a) sotto la soglia critica QM (1,2). "
                           f"Prova: buffer piu grande per pescare piu privati, oppure zone piu compatte.")
            elif _dens >= 2.0:
                st.success(f"\u2705 Densità lineare {_dens:.2f} MWh/(m·a): rete favorevole (QM ≥ 2,0).")

            st.session_state["_rete_info"] = {
                "lunghezza_m": float(_len_totale),
                "lunghezza_pubblico_m": float(_len_pub_t),
                "lunghezza_stub_m": float(_len_stub_t),
                "capex_rete": float(_len_totale * costo_m_tr),
                "densita": float(_dens),
                "n_utenze": int(_n_utenze_tot),
                "n_privati_agganciati": int(_n_priv_dentro),
                "buffer_m": int(buffer_m),
                "costo_m": int(costo_m_tr),
                "traccia_lat": _lat_l, "traccia_lon": _lon_l,
                "stub_lat": _stub_lat_l, "stub_lon": _stub_lon_l,
                "E_pubblico": float(_E_pub),
                "E_condomini": float(_E_cond),
                "E_privati": float(_E_priv),
                "E_totale": float(_E_tot),
            }

            # espongo l'elenco dei privati effettivamente agganciati, per Dimensionamento
            if not _priv_in.empty:
                st.session_state["_dom_priv_in_buffer"] = _priv_in[["cluster", "lat", "lon",
                                                                   "consumo_annuo_MWh"]].to_dict("records")
            else:
                st.session_state["_dom_priv_in_buffer"] = []


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
        st.caption("Da `maniago_flussi_offerta.csv`. Spunta le aziende e i singoli flussi "
                   "di calore di scarto da includere. Di default sono attivi i più certi.")

        offerta = genera_offerta_flussi(flussi, pinch)

        FONTI_CERTE = {"Pandolfo", "ZML", "Pietro Rosa"}

        def _flusso_e_certo(azienda, flusso):
            return (azienda in FONTI_CERTE) and ("torr" in str(flusso).lower())

        selected_flussi = []
        for az in sorted(flussi["azienda"].unique()):
            flussi_az = flussi[flussi["azienda"] == az]
            az_ha_certi = any(_flusso_e_certo(az, fr["flusso"]) for _, fr in flussi_az.iterrows())
            az_on = st.checkbox(f"**{az}**", value=az_ha_certi, key=f"off_az_{az}")
            for _, fr in flussi_az.iterrows():
                icona = "\U0001F534" if fr["destinazione"] == "alta_T" else "\U0001F535"
                label = f"{icona} {fr['flusso']} ({fr['P_kW'] / 1000:.2f} MW, {fr['T_alta_C']:.0f}°C)"
                fl_on = st.checkbox(label, value=_flusso_e_certo(az, fr["flusso"]),
                                    key=f"off_fl_{fr['id_flusso']}", disabled=not az_on)
                if az_on and fl_on:
                    selected_flussi.append(fr["id_flusso"])

        selected_fonti = sorted(set(
            offerta.loc[offerta["id_flusso"].isin(selected_flussi), "azienda"]))
        st.session_state["_off_flussi"] = selected_flussi
        st.session_state["_off_fonti"] = selected_fonti
        st.session_state["_off_pinch"] = pinch
        month_range_o = st.select_slider(
            "Mesi", options=list(range(1, 13)), value=(1, 12),
            format_func=lambda m: MONTH_NAMES[m - 1], key="off_mesi")

        # ---------------------------------------------------------------------
        # Prezzo di acquisto del calore di scarto, differenziato per azienda
        # ---------------------------------------------------------------------
        st.markdown("#### \U0001F4B6 Prezzo del calore di scarto")
        st.caption("Costo di acquisto del calore riconosciuto a ciascuna azienda "
                   "(\u20ac/MWh termico ceduto alla rete). Confluisce nei flussi di cassa "
                   "della scheda *Analisi economica*.")
        _prezzi_scarto = {}
        for az in selected_fonti:
            _prezzi_scarto[az] = st.slider(
                f"{az} (\u20ac/MWh)", 0, 60, 10, step=1, key=f"off_prezzo_{az}",
                help="0 = calore ceduto gratuitamente; valori tipici 5-20 \u20ac/MWh.")
        st.session_state["_off_prezzi_scarto"] = _prezzi_scarto

    with st.expander("\U0001F4CB Dettaglio flussi da CSV (dati grezzi)"):
        st.dataframe(flussi[["azienda", "flusso", "destinazione", "fluido", "T_alta_C",
                             "T_out_C", "P_kW", "profilo"]],
                     use_container_width=True, hide_index=True)

    off = offerta[offerta["id_flusso"].isin(selected_flussi)].copy()
    off["month"] = off["datetime"].dt.month
    off = off[(off["month"] >= month_range_o[0]) & (off["month"] <= month_range_o[1])]

    with col_contenuto2:
        st.markdown("#### \U0001F3ED Sorgenti di scarto e sottocentrale")
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
            k2.metric("Picco orario", f"{picco_o:.3f} MW")
            k3.metric("Ore/anno con disponibilità", f"{ore_disp:,}".replace(",", "."))

            fig_o = go.Figure()
            for f in sorted(agg_off_fonte["fonte"].unique()):
                sub = agg_off_fonte[agg_off_fonte["fonte"] == f]
                fig_o.add_trace(go.Scatter(x=sub["datetime"], y=sub["MWh"], mode="lines",
                                           name=f, stackgroup="one", line=dict(width=0.5)))
            fig_o.update_layout(height=420, yaxis_title="MWh/h (\u2248 MW)", xaxis_title="",
                                legend=dict(orientation="h", yanchor="bottom", y=1.02))
            st.plotly_chart(fig_o, use_container_width=True)

    st.divider()
    st.markdown("#### \U0001F321\ufe0f Curva composita: energia disponibile per soglia di temperatura")
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
            _ic = "\U0001F534" if dest == "alta_T" else "\U0001F535"
            fig_comp.add_trace(go.Scatter(
                x=cum_mwh, y=T_vals, mode="lines",
                name=f"{_ic} {nome[:26]}",
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
    else:
        st.info("Nessun flusso selezionato con dati di temperatura in questo periodo.")


# =============================================================================
# TAB 3 - DIMENSIONAMENTO
# =============================================================================
with tab_dimensionamento:
    st.markdown("### Dimensionamento — schema a cascata (3 accumuli + 2 HP)")

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
    dom_tot_utenze = float(dom_arr.sum())    # domanda ALLE UTENZE, prima delle perdite

    # -------------------------------------------------------------------------
    # P6 - Perdite di rete QM: la domanda ALLA CENTRALE include le perdite tubi
    # -------------------------------------------------------------------------
    _rete_info = st.session_state.get("_rete_info", {}) or {}
    _dens_lin = float(_rete_info.get("densita", 2.0))
    _T_media_rete = (T_mandata_ideale + T_ritorno_ideale) / 2.0
    _classe_iso = 2      # pre-isolate rigide PN16, classe media (baseline QM)
    _perd_pct = perdite_pct_QM(_dens_lin, _T_media_rete, _classe_iso)
    _fatt_lordo = 1.0 + _perd_pct / 100.0
    dom_arr = dom_arr * _fatt_lordo
    dom_tot = float(dom_arr.sum())

    # -------------------------------------------------------------------------
    # P5 - Contemporaneita QM: agisce SOLO sul picco di dimensionamento
    # -------------------------------------------------------------------------
    _mask_priv = dom_dim["tipo_utenza"].isin(["Privato (potenziale)", "Condominio"])
    _carico_priv = (dom_dim[_mask_priv].groupby("datetime")[["MWh_riscaldamento", "MWh_ACS"]]
                    .sum().sum(axis=1).reindex(idx_h, fill_value=0).values) * _fatt_lordo
    _carico_pub = dom_arr - _carico_priv
    _n_priv = int(st.session_state.get("_dom_n_privati", 0))
    _f_sim = coeff_simultaneita_QM(_n_priv) if _n_priv > 1 else 1.0
    picco_naive_kw = float(dom_arr.max()) * 1000.0
    picco_kw = float((_f_sim * _carico_priv + _carico_pub).max()) * 1000.0

    # -------------------------------------------------------------------------
    pinch_dim = st.session_state.get("_off_pinch", 5.0)
    off_all = genera_offerta_flussi(flussi, pinch_dim)
    off_all = off_all[off_all["id_flusso"].isin(flussi_dim)].copy()
    soil_temp_arr = soil_temp_monthly(pvgis)[idx_h.month.values - 1]

    def capex_hp_kw(pot_kw):
        """CAPEX specifico HP (\u20ac/kW). Curva conservativa 'sola macchina'.

        Nota: i fact sheet IEA DHC TS5 F6 Tab.4 (chiavi in mano, Europa
        occidentale) danno 0,67-1,24 M\u20ac/MW per HP su excess heat a 25 °C,
        cioe 670-1240 \u20ac/kW comprensivi di edificio, allaccio elettrico MT e
        sistema di regolazione. Usare lo slider CAPEX per la sensitivita.
        """
        p = max(pot_kw / 1000.0, 0.1)
        pts = [(1, 340), (3, 300), (10, 220)]
        if p <= 1:
            return 340
        if p >= 10:
            return 220
        for (p0, c0), (p1, c1) in zip(pts, pts[1:]):
            if p0 <= p <= p1:
                return c0 + (np.log(p) - np.log(p0)) / (np.log(p1) - np.log(p0)) * (c1 - c0)
        return 220

    perdita_func = (lambda v: float(np.interp(np.log(np.clip(v, 500, 5000)),
                                              [np.log(500), np.log(5000)], [2.0, 1.0])) if v > 0 else 0.0)
    _maxp = int(picco_kw) + 1000

    col_ctrl, col_res = st.columns([1, 3])

    with col_ctrl:
        st.markdown("#### \u2699\ufe0f Parametri")
        T_int = st.slider("Anello intermedio (°C)", 40, 60, 50, key="dim_tint",
                          help="La HP alta T solleva sempre da qui a mandata. "
                               "45-50 °C e l'ottimo tipico.")
        st.markdown("**Supporto (parallelo)**")
        backup_tipo = st.radio("Copre il gap con:", ["HP bassa T", "gas", "biomassa"],
                               key="dim_backup_tipo")
        is_hp_par = (backup_tipo == "HP bassa T")
        if not is_hp_par:
            st.caption("\u2139\ufe0f **Merit order**: la HP alta T lavora sempre per prima, "
                       "sollevando il calore dall'anello intermedio alla mandata. "
                       f"Il {backup_tipo} entra **solo sul residuo** che la HP non riesce a coprire.")
        eta_hp = st.slider("\u03b7 2° principio HP (%)", 30, 60, 50, key="dim_eta") / 100.0
        prezzo_el = st.slider("Prezzo elettricità (\u20ac/MWh)", 80, 350, 180, step=10, key="dim_prezzo_el")
        antigelo = st.slider("Floor antigelo ground loop (°C)", -5, 10, 0, key="dim_antigelo")

        if backup_tipo == "gas":
            rend_gas = st.slider("Rendimento caldaia (%)", 85, 98, 92, key="dim_rend_gas") / 100.0
            prezzo_gas = st.slider("Prezzo gas (\u20ac/MWh)", 40, 160, 90, key="dim_prezzo_gas")
            capex_kw_bk = st.slider("CAPEX caldaia (\u20ac/kW)", 60, 300, 120, step=10, key="dim_capex_gas")
            opex_bk_mwh = prezzo_gas / rend_gas
        elif backup_tipo == "biomassa":
            rend_bio = st.slider("Rendimento caldaia (%)", 75, 92, 85, key="dim_rend_bio") / 100.0
            costo_cip = st.slider("Costo cippato (\u20ac/MWh)", 20, 60, 35, key="dim_costo_bio")
            capex_kw_bk = st.slider("CAPEX caldaia (\u20ac/kW)", 300, 900, 550, step=25, key="dim_capex_bio")
            opex_bk_mwh = costo_cip / rend_bio
            st.caption("\u26a0\ufe0f Nota QM: la filosofia del Handbook e l'opposto — caldaia a "
                       "biomassa in **base** con molte ore equivalenti e fossile in punta. "
                       "Usata come supporto avrà poche ore/anno con CAPEX elevato.")
        else:
            capex_kw_bk = 700.0
            opex_bk_mwh = 0.0
        backup_cop = None

        costo_m3 = st.slider("CAPEX accumuli (\u20ac/m³)", 80, 1500, 1000, step=20, key="dim_costo_m3",
                             help="IEA DHC F1 Tab.3: TTES 110-200 \u20ac/m³ sopra i 2.000 m³; "
                                  "1.000 \u20ac/m³ e conservativo per serbatoi in acciaio piccoli.")

        solare_on = st.checkbox("\u2600\ufe0f Solare nell'accumulo basso", value=False, key="dim_solare_on")
        solar_low = np.zeros(len(dom_arr))
        capex_solare = 0.0
        area_sol = 0
        if solare_on:
            acs = dom_dim.groupby("datetime")["MWh_ACS"].sum().reindex(idx_h, fill_value=0)
            est = idx_h.month.isin([6, 7, 8])
            acs_est = float(acs[est].sum())
            pref = genera_offerta_solare(pvgis, 1000.0, 0.30).groupby("datetime")["MWh"].sum().reindex(idx_h, fill_value=0)
            pref_est = float(pref[est].sum())
            area_base = (acs_est / pref_est * 1000.0) if pref_est > 1e-6 else 2000.0
            quota = st.slider("Quota solare (% ACS estiva)", 0, 300, 100, step=10, key="dim_quota_sol")
            eff = st.slider("Efficienza collettori (%)", 15, 50, 30, key="dim_eff_sol") / 100.0
            capex_mq = st.slider("CAPEX solare (\u20ac/m²)", 200, 900, 450, step=20, key="dim_capex_sol")
            area_sol = int(round(area_base * quota / 100.0 * (0.30 / max(eff, 0.01))))
            solar_low = genera_offerta_solare(pvgis, area_sol, eff).groupby("datetime")["MWh"].sum().reindex(idx_h, fill_value=0).values
            capex_solare = area_sol * capex_mq
            st.caption(f"Campo ~{area_sol:,} m²".replace(",", "."))

            # --- P3: warning solare + supporto a combustibile ---
            if not is_hp_par:
                st.warning(
                    "\u26a0\ufe0f Solare attivo con supporto a **combustibile**: il calore solare "
                    "finisce nella fascia più calda dell'anello basso, ma senza HP bassa T non "
                    "ha alcun utilizzatore e viene scartato — mentre il CAPEX resta a bilancio. "
                    "Attiva 'HP bassa T' come supporto, oppure disattiva il solare."
                )

        q_hot_arr, q_int_arr, q_low_arr, q_low_bins, bin_T = routing_flussi(
            off_all, idx_h, T_mandata_ideale, T_int)
        q_low_bins_eff = q_low_bins.copy()
        if solare_on:
            q_low_bins_eff[:, -1] = q_low_bins_eff[:, -1] + solar_low

        st.markdown("#### \U0001F50E Ottimizzazione")
        if st.button("Ottimizza scenario", key="dim_btn_opt", use_container_width=True):
            with st.spinner("LCOH minimo, copertura 100%..."):
                best = ottimizza_cascata(
                    dom_arr, q_hot_arr, q_int_arr, q_low_bins_eff, bin_T, soil_temp_arr,
                    float(T_mandata_ideale), float(T_ritorno_ideale), float(T_int), 5, eta_hp,
                    backup_tipo, capex_hp_kw, capex_kw_bk, opex_bk_mwh, backup_cop,
                    prezzo_el, costo_m3, capex_solare, crf(0.04, 20), perdita_func, float(antigelo),
                    picco_kw_override=picco_kw)
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
        for k, dv in [("dim_p_alta", int(picco_kw)), ("dim_p_bassa", int(picco_kw * 0.8)),
                      ("dim_p_bk", int(picco_kw))]:
            st.session_state[k] = max(0, min(int(st.session_state.get(k, dv)), _maxp))
        for k, dv in [("dim_v_hot", 0), ("dim_v_int", 800), ("dim_v_low", 400)]:
            st.session_state[k] = max(0, min(int(st.session_state.get(k, dv)), 4000))
        P_alta = st.slider("HP alta T (kW)", 0, _maxp, step=100, key="dim_p_alta")
        if is_hp_par:
            P_bassa = st.slider("HP bassa T (kW)", 0, _maxp, step=100, key="dim_p_bassa")
            P_bk = 0
        else:
            P_bassa = 0
            P_bk = st.slider(f"Caldaia {backup_tipo} (kW)", 0, _maxp, step=100, key="dim_p_bk")
        V_hot = st.slider("Accumulo CALDO (m³)", 0, 4000, step=50, key="dim_v_hot")
        V_int = st.slider("Accumulo INTERMEDIO (m³)", 0, 4000, step=50, key="dim_v_int")
        V_low = st.slider("Accumulo BASSO (m³)", 0, 4000, step=50, key="dim_v_low")

    # ============================== CALCOLO ==============================
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

    el_hp = sim["el_alta"] + sim["el_bassa"]
    ground = sim["q_ground"]
    scarto_via_hp = np.maximum(sim["q_alta"] - el_hp - ground, 0.0)
    E_scarto_via_hp = float(scarto_via_hp.sum())
    E_ground = sim["E_ground"]
    E_el = float(el_hp.sum())
    E_scarto_tot = E_hot + E_scarto_via_hp

    # --- indicatori richiesti ---
    # % di calore di scarto industriale utilizzato rispetto alla domanda totale
    pct_scarto_su_domanda = E_scarto_tot / dom_tot * 100 if dom_tot > 0 else 0.0
    # % di calore rinnovabile/recuperato sul totale effettivamente fornito:
    #   scarto industriale recuperato + calore ambiente (suolo) + biomassa.
    #   NON conta l'elettricita di rete delle HP ne il gas fossile.
    E_fornito = E_hot + E_alta + E_bassa + E_bk
    E_rinnovabile = (E_scarto_tot + E_ground
                     + (E_bk if backup_tipo == "biomassa" else 0.0))
    pct_rinnovabile = E_rinnovabile / E_fornito * 100 if E_fornito > 0 else 0.0

    with col_res:
        if eredita_ok:
            st.caption(f"**{len(edifici_dim)} edifici** (zone: {', '.join(zone_dim) if zone_dim else '—'}) "
                       f"· **{len(flussi_dim)} flussi** · mandata/ritorno "
                       f"**{T_mandata_ideale}/{T_ritorno_ideale}°C** · anello intermedio "
                       f"**{T_int}°C**.")
        else:
            st.info(f"Valori predefiniti ({len(edifici_dim)} edifici pubblici, {len(flussi_dim)} flussi).")

        st.info(
            f"\U0001F4C9 **Perdite di rete QM (Fig. 12.3)**: {_perd_pct:.1f} % — densità "
            f"{_dens_lin:.2f} MWh/(m·a), T media rete {_T_media_rete:.0f} °C, classe "
            f"isolante {_classe_iso}. Domanda alle utenze **{dom_tot_utenze:,.0f} MWh/a** "
            f"→ alla centrale **{dom_tot:,.0f} MWh/a** (\u00d7{_fatt_lordo:.3f}).".replace(",", ".")
        )
        _quota_buf = st.session_state.get("_dom_quota_buffer", 1.0)
        _rete_info_dim = st.session_state.get("_rete_info", {}) or {}
        _buffer_m_dim = int(_rete_info_dim.get("buffer_m", 0))
        _n_priv_agg = int(_rete_info_dim.get("n_privati_agganciati", 0))
        if _quota_buf < 0.999 and _buffer_m_dim > 0:
            st.info(
                f"\U0001F6E4\ufe0f **Buffer di tracciato**: {_buffer_m_dim} m. "
                f"Dei privati delle zone attive, **{_quota_buf * 100:.0f} %** ({_n_priv_agg}) "
                f"cade nel buffer del tubo pubblico e viene servito; il resto e escluso. "
                f"Domanda dei privati e picco corretti di conseguenza."
            )
        if _n_priv > 1:
            st.info(
                f"\U0001F465 **Contemporaneità QM (Fig. 12.2)**: {_n_priv} utenze "
                f"private/condominiali → f = {_f_sim:.2f}. Picco per il dimensionamento "
                f"**{picco_kw:.0f} kW**, contro {picco_naive_kw:.0f} kW senza contemporaneità "
                f"(\u2212{(1 - picco_kw / max(picco_naive_kw, 1)) * 100:.0f} %). "
                f"L'energia annua non e toccata."
            )

        ores = st.session_state.get("_opt_casc")
        if ores:
            st.markdown("#### \u2705 Scenario ottimizzato")
            o1, o2, o3, o4, o5 = st.columns(5)
            o1.metric("HP alta T", f"{ores['P_alta']:.0f} kW")
            o2.metric("HP bassa T" if is_hp_par else "Caldaia",
                      f"{(ores['P_bassa'] if is_hp_par else ores['P_bk']):.0f} kW")
            o3.metric("LCOH", f"{ores['lcoh']:.1f} \u20ac/MWh")
            o4.metric("Quota FER", f"{ores['quota_fer']:.0f}%")
            o5.metric("COP HP alta", f"{ores['cop_alta']:.1f}")
            va1, va2, va3 = st.columns(3)
            va1.metric("Accumulo CALDO", f"{ores['v_hot']:.0f} m³")
            va2.metric("Accumulo INTERMEDIO", f"{ores['v_int']:.0f} m³")
            va3.metric("Accumulo BASSO", f"{ores['v_low']:.0f} m³")
            st.caption("Backup **firm** (potenza al picco): copre il 100 % anche a zero scarto. "
                       "La HP alta T e dimensionata anch'essa sul picco perche e la macchina di "
                       "base del sistema. Cambi supporto/solare/fonti? Rilancia l'ottimizzazione.")
        else:
            st.info("Premi **Ottimizza scenario** (a sinistra) per dimensionare HP e accumuli a LCOH minimo.")

        st.divider()
        st.markdown("#### Instradamento dello scarto per temperatura")
        cA1, cA2, cA3, cA4 = st.columns(4)
        cA1.metric("Domanda annua alla centrale", f"{dom_tot:,.0f} MWh".replace(",", "."),
                   help=f"picco di dimensionamento {picco_kw:.0f} kW (contemporaneità QM inclusa)")
        cA2.metric("\U0001F534 → caldo", f"{q_hot_arr.sum():,.0f} MWh".replace(",", "."),
                   help=f"scarto ≥ mandata ({T_mandata_ideale}°C), uso diretto")
        cA3.metric("\U0001F7E0 → intermedio", f"{q_int_arr.sum():,.0f} MWh".replace(",", "."),
                   help=f"tra {T_int} e {T_mandata_ideale}°C, evaporatore HP alta T")
        cA4.metric("\U0001F535 → basso", f"{q_low_arr.sum():,.0f} MWh".replace(",", "."),
                   help=f"< {T_int}°C, utilizzabile solo con HP bassa T")

        st.markdown("##### \U0001F4C9 Curva di durata: da dove arriva l'energia")
        order = np.argsort(dom_arr)[::-1]
        x = np.arange(1, len(dom_arr) + 1)
        fig_dur = go.Figure()
        bande = [("Scarto diretto", sim["q_hot_direct"], COLOR_ALTA_T),
                 ("Scarto risollevato dalle HP", scarto_via_hp, COLOR_OFFERTA),
                 ("Suolo / ground loop", ground, COLOR_GROUND),
                 ("Elettricità HP alta", sim["el_alta"], COLOR_HP),
                 ("Elettricità HP bassa", sim["el_bassa"], COLOR_HP_BASSA),
                 (f"Supporto ({backup_tipo})", sim["q_backup"], COLOR_BACKUP)]
        for nome, arr, col in bande:
            if float(arr.sum()) < 1:
                continue
            fig_dur.add_trace(go.Scatter(x=x, y=arr[order], mode="lines", name=nome,
                                         stackgroup="c", line=dict(width=0),
                                         fillcolor=hex_to_rgba(col, 0.9)))
        fig_dur.add_trace(go.Scatter(x=x, y=dom_arr[order], mode="lines", name="Domanda",
                                     line=dict(color=COLOR_DOMANDA, width=2.4)))
        fig_dur.update_layout(height=440, xaxis_title="Ore/anno", yaxis_title="MW",
                              legend=dict(orientation="h", yanchor="bottom", y=1.02),
                              margin=dict(t=30, b=10))
        st.plotly_chart(fig_dur, use_container_width=True)

        st.markdown("##### \U0001F5FA\ufe0f Heatmap: energia di scarto per mese e temperatura")
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
            fig_hm = go.Figure(go.Heatmap(z=piv.values, x=[MONTH_NAMES[m - 1] for m in piv.columns],
                                          y=labels, colorscale="YlOrRd", colorbar=dict(title="MWh")))
            for _lv, _lab in [(T_int, f"intermedio {T_int}°C"),
                              (T_mandata_ideale, f"mandata {T_mandata_ideale}°C")]:
                try:
                    _ib = next(i for i in range(len(labels)) if bins[i] <= _lv < bins[i + 1])
                    fig_hm.add_hline(y=_ib - 0.5, line_color="#22C3DD", line_width=2,
                                     annotation_text=_lab, annotation_position="top left")
                except StopIteration:
                    pass
            fig_hm.update_layout(height=420, yaxis_title="Temperatura scarto (°C)",
                                 margin=dict(t=30, b=10))
            st.plotly_chart(fig_hm, use_container_width=True)

        st.divider()
        st.markdown("#### Copertura (simulazione oraria)")
        mets = [("Caldo diretto", E_hot, f"{E_hot / dom_tot * 100:.0f}% della domanda"),
                ("HP alta T", E_alta, f"{E_alta / dom_tot * 100:.0f}% consegnato · COP {sim['cop_alta_medio']:.2f}")]
        if is_hp_par:
            mets.append(("HP bassa T (interna)", E_bassa,
                         f"→ intermedio · COP {sim['cop_bassa_medio']:.2f} · "
                         f"ground {sim['ore_ground']} ore"))
        else:
            mets.append((f"Supporto: {backup_tipo}", E_bk, f"{E_bk / dom_tot * 100:.0f}% della domanda"))
        cols_r = st.columns(len(mets) + 1)
        for i, (lab, val, hlp) in enumerate(mets):
            cols_r[i].metric(lab, f"{val:,.0f} MWh".replace(",", "."), help=hlp)
        cols_r[-1].metric("Quota FER", f"{quota_fer:.0f}%")
        if sim["ore_non_coperte"] > 0:
            st.error(f"\u26a0\ufe0f {sim['ore_non_coperte']} ore non coperte "
                     f"({E_nc:,.0f} MWh): ottimizza o aumenta le taglie.".replace(",", "."))
        else:
            st.success("\u2705 Copertura 100 % in tutte le ore.")

        # --- indicatori chiave richiesti ---
        st.markdown("##### \U0001F331 Indicatori chiave di sostenibilità")
        ind1, ind2, ind3 = st.columns(3)
        ind1.metric("Scarto industriale utilizzato / domanda",
                    f"{pct_scarto_su_domanda:.0f}%",
                    help="Quota della domanda alla centrale coperta con calore di scarto "
                         "recuperato dalle aziende (uso diretto + risollevato dalle HP), "
                         "al netto dell'elettricità dei compressori e del suolo.")
        ind2.metric("Calore rinnovabile / totale fornito",
                    f"{pct_rinnovabile:.0f}%",
                    help="Scarto recuperato + calore ambiente dal suolo + biomassa, sul totale "
                         "effettivamente fornito. Esclude l'elettricità di rete e il gas fossile.")
        ind3.metric("Quota FER (dimensionamento)", f"{quota_fer:.0f}%",
                    help="Definizione dello scenario (scarto diretto + HP alta T + biomassa).")

        st.markdown("**Da dove arriva l'energia** (fonti, sull'anno)")
        fig_mix = go.Figure()
        voci = [("Scarto diretto", E_hot, COLOR_ALTA_T),
                ("Scarto risollevato dalle HP", E_scarto_via_hp, COLOR_OFFERTA),
                ("Suolo / ground loop", E_ground, COLOR_GROUND),
                ("Elettricità HP alta", float(sim["el_alta"].sum()), COLOR_HP),
                ("Elettricità HP bassa", float(sim["el_bassa"].sum()), COLOR_HP_BASSA),
                (f"Supporto ({backup_tipo})", E_bk, COLOR_BACKUP)]
        if E_nc > 1:
            voci.append(("Non coperto", E_nc, COLOR_NONCOP))
        voci = [(n, v, c) for n, v, c in voci if v > 1]
        tot_mix = sum(v for _, v, _ in voci) or 1.0
        for nome, val, col in voci:
            pct = val / tot_mix * 100
            fig_mix.add_trace(go.Bar(y=["Fonti"], x=[val], name=nome, orientation="h",
                                     marker_color=col,
                                     text=(f"{pct:.0f}%" if pct >= 6 else ""), textposition="inside",
                                     insidetextanchor="middle",
                                     textfont=dict(color="white", size=13), cliponaxis=False))
        fig_mix.update_layout(barmode="stack", height=220, xaxis_title="MWh/anno",
                              legend=dict(orientation="h", yanchor="top", y=-0.5),
                              margin=dict(t=30, b=10))
        fig_mix.update_yaxes(showticklabels=False)
        st.plotly_chart(fig_mix, use_container_width=True)

        st.markdown("**Bilancio energetico dello scenario**")
        _spf = (E_hot + E_alta) / E_el if E_el > 1e-6 else 0.0
        bb = st.columns(4)
        bb[0].metric("Scarto utilizzato", f"{E_scarto_tot:,.0f} MWh".replace(",", "."),
                     help=f"{E_scarto_tot / dom_tot * 100:.0f}% della domanda")
        bb[1].metric("Elettricità HP", f"{E_el:,.0f} MWh".replace(",", "."),
                     help=f"compressori · SPF di sistema {_spf:.1f}")
        bb[2].metric("Suolo / ground", f"{E_ground:,.0f} MWh".replace(",", "."),
                     help=f"{sim['ore_ground']} ore")
        bb[3].metric("Combustibile", f"{E_bk:,.0f} MWh".replace(",", "."),
                     help=(f"{backup_tipo}" if not is_hp_par else "nessuno"))

        st.markdown("**\U0001F4C8 Curva di durata del COP delle pompe di calore**")
        st.caption("COP con vincoli realistici: lift minimo 8 K e tetto 6,5 (IEA DHC F6/F10).")
        fig_cop = go.Figure()
        _ca = sim["cop_alta_s"][(sim["q_alta"] > 1e-6) & np.isfinite(sim["cop_alta_s"])]
        if len(_ca):
            fig_cop.add_trace(go.Scatter(y=np.sort(_ca)[::-1], x=np.arange(1, len(_ca) + 1),
                                         mode="lines", name="COP HP alta T",
                                         line=dict(color=COLOR_HP, width=2)))
        _cb = sim["cop_bassa_s"][(sim["q_bassa"] > 1e-6) & np.isfinite(sim["cop_bassa_s"])]
        if len(_cb):
            fig_cop.add_trace(go.Scatter(y=np.sort(_cb)[::-1], x=np.arange(1, len(_cb) + 1),
                                         mode="lines", name="COP HP bassa T",
                                         line=dict(color=COLOR_HP_BASSA, width=2)))
        if len(_ca) or len(_cb):
            fig_cop.update_layout(height=320, xaxis_title="Ore di funzionamento", yaxis_title="COP",
                                  legend=dict(orientation="h", yanchor="bottom", y=1.02),
                                  margin=dict(t=30, b=10))
            st.plotly_chart(fig_cop, use_container_width=True)
        else:
            st.info("Nessuna HP attiva in questo scenario.")

        st.divider()
        st.markdown("#### \U0001F4B0 Costi e LCOH")
        righe = [
            {"Voce": f"HP alta T ({P_alta} kW)", "CAPEX (\u20ac)": round(capex_alta),
             "OPEX (\u20ac/a)": round(sim["E_el_alta"] * prezzo_el)},
            ({"Voce": f"HP bassa T ({P_bassa} kW)", "CAPEX (\u20ac)": round(capex_bassa),
              "OPEX (\u20ac/a)": round(sim["E_el_bassa"] * prezzo_el)} if is_hp_par else
             {"Voce": f"Caldaia {backup_tipo} ({P_bk} kW)", "CAPEX (\u20ac)": round(capex_bk),
              "OPEX (\u20ac/a)": round(E_bk * opex_bk_mwh)}),
            {"Voce": f"Accumuli ({V_hot}+{V_int}+{V_low} m³)", "CAPEX (\u20ac)": round(capex_acc),
             "OPEX (\u20ac/a)": 0},
        ]
        if solare_on:
            righe.append({"Voce": f"Solare ({area_sol} m²)", "CAPEX (\u20ac)": round(capex_solare),
                          "OPEX (\u20ac/a)": 0})
        st.dataframe(pd.DataFrame(righe), use_container_width=True, hide_index=True)

        fig_co = go.Figure(go.Pie(labels=["CAPEX (annualizzato)", "OPEX (annuo)"],
                                  values=[capex_sistema * fattore_crf, opex], hole=0.5,
                                  marker=dict(colors=["#5B8DEF", "#F4A259"]), sort=False))
        fig_co.update_layout(title=f"Costo annuo · {costo_annuo:,.0f} \u20ac/a".replace(",", "."),
                             height=300, margin=dict(t=45, b=10), legend=dict(orientation="h", y=-0.1))
        st.plotly_chart(fig_co, use_container_width=True)

        df_c = pd.DataFrame(righe)
        _pal = [COLOR_HP, (COLOR_HP_BASSA if is_hp_par else COLOR_BACKUP), COLOR_ACCUMULO, COLOR_SOLARE]
        pc1, pc2 = st.columns(2)
        with pc1:
            fig_capex = go.Figure(go.Pie(labels=df_c["Voce"], values=df_c["CAPEX (\u20ac)"], hole=0.5,
                                         marker=dict(colors=_pal[:len(df_c)]), sort=False))
            fig_capex.update_layout(title=f"CAPEX totale · {capex_sistema:,.0f} \u20ac".replace(",", "."),
                                    height=330, margin=dict(t=45, b=10),
                                    legend=dict(orientation="h", y=-0.1))
            st.plotly_chart(fig_capex, use_container_width=True)
        with pc2:
            df_o = df_c[df_c["OPEX (\u20ac/a)"] > 0]
            fig_opex = go.Figure(go.Pie(labels=df_o["Voce"], values=df_o["OPEX (\u20ac/a)"], hole=0.5,
                                        marker=dict(colors=_pal[:len(df_o)]), sort=False))
            fig_opex.update_layout(title=f"OPEX annuo · {opex:,.0f} \u20ac/a".replace(",", "."),
                                   height=330, margin=dict(t=45, b=10),
                                   legend=dict(orientation="h", y=-0.1))
            st.plotly_chart(fig_opex, use_container_width=True)

        s1, s2, s3, s4 = st.columns(4)
        s1.metric("CAPEX di sistema", f"{capex_sistema:,.0f} \u20ac".replace(",", "."))
        s2.metric("Costo annuo", f"{costo_annuo:,.0f} \u20ac/a".replace(",", "."))
        s3.metric("LCOH di sistema", f"{lcoh:.1f} \u20ac/MWh" if not np.isnan(lcoh) else "n/d")
        s4.metric("Quota FER", f"{quota_fer:.0f}%")

    # ---------------------------------------------------------------------
    # COSTO DEL CALORE DI SCARTO ACQUISTATO (per azienda) + CO2 EVITATA
    # ---------------------------------------------------------------------
    # Il calore di scarto realmente valorizzato e E_scarto_tot (diretto +
    # risollevato dalle HP). Lo ripartisco tra le aziende in proporzione
    # all'energia che ciascuna mette a disposizione tra i flussi selezionati.
    _prezzi_scarto = st.session_state.get("_off_prezzi_scarto", {})
    _en_per_azienda = (off_all.groupby("azienda")["MWh"].sum()
                       if not off_all.empty else pd.Series(dtype=float))
    _en_scarto_disp = float(_en_per_azienda.sum())
    costo_calore_acq = 0.0
    _righe_acq = []
    if _en_scarto_disp > 1e-6:
        for _az, _en in _en_per_azienda.items():
            _quota = _en / _en_scarto_disp
            _mwh_valorizzati = E_scarto_tot * _quota
            _pz = float(_prezzi_scarto.get(_az, 0))
            _costo = _mwh_valorizzati * _pz
            costo_calore_acq += _costo
            _righe_acq.append({"azienda": _az, "MWh valorizzati": round(_mwh_valorizzati),
                               "\u20ac/MWh": _pz, "costo (\u20ac/a)": round(_costo)})

    # CO2 evitata rispetto alla baseline gas.
    # Baseline: le utenze si scaldano da sole con caldaie a gas che producono
    # esattamente il calore VENDUTO alle utenze (E_venduto = dom_tot_utenze).
    # Il TLR invece produce E_fornito in centrale (= E_venduto + perdite rete)
    # e le sue emissioni sono elettricita HP (mix) + eventuale gas fossile.
    FATTORE_GAS_TCO2_MWH = 0.20   # t CO2 / MWh termico (gas naturale, ISPRA)
    RENDIMENTO_GAS_RIF = 0.90     # caldaia a gas di riferimento (baseline)
    FATTORE_EL_TCO2_MWH = 0.28    # mix elettrico IT ~2023-2024
    co2_baseline_gas = dom_tot_utenze / RENDIMENTO_GAS_RIF * FATTORE_GAS_TCO2_MWH
    E_da_gas = E_bk if backup_tipo == "gas" else 0.0
    co2_sistema = (E_el * FATTORE_EL_TCO2_MWH
                   + E_da_gas / RENDIMENTO_GAS_RIF * FATTORE_GAS_TCO2_MWH)
    co2_evitata = co2_baseline_gas - co2_sistema

    # ---------------------------------------------------------------------
    # SNAPSHOT PER CONFRONTO / ECONOMIA
    # ---------------------------------------------------------------------
    st.session_state["_dim_snapshot"] = {
        "utenza": f"{len(edifici_dim)} edifici",
        "zone": ", ".join(zone_dim) if zone_dim else "—",
        "T_mandata": int(T_mandata_ideale),
        "T_ritorno": int(T_ritorno_ideale),
        "T_int": int(T_int),
        "supporto": backup_tipo,
        "carico_utenze_mwh": round(dom_tot_utenze),
        "carico_centrale_mwh": round(dom_tot),
        "perdite_rete_pct": round(_perd_pct, 1),
        "contemporaneita": round(_f_sim, 2),
        "picco_naive_kw": round(picco_naive_kw),
        "picco_dim_kw": round(picco_kw),
        "P_alta_kw": int(P_alta),
        "P_bassa_kw": int(P_bassa),
        "P_backup_kw": int(P_bk),
        "V_hot": int(V_hot), "V_int": int(V_int), "V_low": int(V_low),
        "area_solare_m2": int(area_sol),
        "tecnologie": (f"HP alta {P_alta} kW + "
                       + (f"HP bassa {P_bassa} kW" if is_hp_par else f"{backup_tipo} {P_bk} kW")
                       + (f" + solare {area_sol} m²" if solare_on else "")),
        "E_hot_diretto": round(E_hot), "E_hp_alta": round(E_alta), "E_hp_bassa": round(E_bassa),
        "E_backup": round(E_bk), "E_elettrica": round(E_el), "E_ground": round(E_ground),
        "E_scarto_utilizzato": round(E_scarto_tot), "E_non_coperta": round(E_nc, 1),
        "ore_non_coperte": int(sim["ore_non_coperte"]),
        "cop_alta": round(sim["cop_alta_medio"], 2), "cop_bassa": round(sim["cop_bassa_medio"], 2),
        "spf_sistema": round(_spf, 2),
        "quota_fer_pct": round(quota_fer, 1),
        "pct_scarto_su_domanda": round(pct_scarto_su_domanda, 1),
        "pct_rinnovabile": round(pct_rinnovabile, 1),
        "co2_evitata_t": round(co2_evitata, 1),
        "co2_sistema_t": round(co2_sistema, 1),
        "costo_calore_acquistato": round(costo_calore_acq),
        "capex_sistema": round(capex_sistema),
        "capex_rete": round(float(_rete_info.get("capex_rete", 0.0))),
        "lunghezza_rete_m": round(float(_rete_info.get("lunghezza_m", 0.0))),
        "lunghezza_pubblico_m": round(float(_rete_info.get("lunghezza_pubblico_m", 0.0))),
        "lunghezza_stub_m": round(float(_rete_info.get("lunghezza_stub_m", 0.0))),
        "buffer_m": int(_rete_info.get("buffer_m", 0)),
        "n_privati_agganciati": int(_rete_info.get("n_privati_agganciati", 0)),
        "densita_lineare": round(_dens_lin, 2),
        "opex_annuo": round(opex),
        "costo_annuo": round(costo_annuo),
        "lcoh": round(float(lcoh), 2) if not np.isnan(lcoh) else None,
        "prezzo_el": int(prezzo_el),
        "opex_backup_mwh": round(float(opex_bk_mwh), 1),
    }

    # --- salvataggio scenario (P9: rimovibili singolarmente) ---
    st.divider()
    sc1, sc2 = st.columns([3, 1])
    _nome_def = f"{backup_tipo} · {T_mandata_ideale}/{T_ritorno_ideale}°C"
    nome_scen = sc1.text_input("Nome dello scenario da salvare", value=_nome_def, key="dim_nome_scen")
    if sc2.button("\U0001F4BE Salva scenario", use_container_width=True, key="dim_btn_salva"):
        if nome_scen.strip():
            st.session_state["_scenari"][nome_scen.strip()] = dict(st.session_state["_dim_snapshot"])
            st.success(f"Scenario **{nome_scen.strip()}** salvato "
                       f"({len(st.session_state['_scenari'])} in memoria).")
        else:
            st.warning("Dai un nome allo scenario prima di salvarlo.")


# =============================================================================
# TAB 4 - CONFRONTO SCENARI (P9: rimozione selettiva)
# =============================================================================
with tab_confronto:
    st.markdown("### \U0001F4CA Confronto tra scenari salvati")
    _scen = st.session_state.get("_scenari", {})

    if not _scen:
        st.info("Nessuno scenario salvato. Vai nella scheda **Dimensionamento**, configura un "
                "assetto e premi *Salva scenario*. Puoi salvarne quanti vuoi e confrontarli qui.")
    else:
        st.caption(f"**{len(_scen)}** scenari in memoria. Ogni scenario si rimuove singolarmente "
                   "con il pulsante \u274c sulla sua riga.")

        # --- gestione: rimozione selettiva + svuota tutto ---
        with st.expander("\U0001F5C2\ufe0f Gestione scenari", expanded=True):
            for _nome in list(_scen.keys()):
                _s = _scen[_nome]
                g1, g2, g3 = st.columns([5, 3, 1])
                g1.markdown(f"**{_nome}**")
                _lc = _s.get("lcoh")
                g2.caption(f"{_s.get('tecnologie', '')} · LCOH "
                           + (f"{_lc:.1f} \u20ac/MWh" if _lc is not None else "n/d")
                           + f" · FER {_s.get('quota_fer_pct', 0):.0f}%")
                if g3.button("\u274c", key=f"del_scen_{_nome}", help=f"Rimuovi '{_nome}'"):
                    del st.session_state["_scenari"][_nome]
                    st.rerun()
            st.divider()
            gz1, gz2 = st.columns([1, 4])
            if gz1.button("\U0001F5D1\ufe0f Svuota tutto", key="del_scen_all"):
                st.session_state["_scenari"] = {}
                st.rerun()
            gz2.caption("Attenzione: *Svuota tutto* cancella l'intera lista senza conferma.")

        _scen = st.session_state.get("_scenari", {})
        if not _scen:
            st.stop()

        # --- tabella di confronto ---
        _campi = [
            ("carico_utenze_mwh", "Calore venduto (MWh/a)"),
            ("carico_centrale_mwh", "Calore prodotto in centrale (MWh/a)"),
            ("perdite_rete_pct", "Perdite di rete (%)"),
            ("contemporaneita", "Contemporaneità QM"),
            ("picco_naive_kw", "Picco senza contemporaneità (kW)"),
            ("picco_dim_kw", "Picco di dimensionamento (kW)"),
            ("densita_lineare", "Densità lineare (MWh/m·a)"),
            ("lunghezza_rete_m", "Lunghezza rete totale (m)"),
            ("lunghezza_pubblico_m", "di cui tratto obbligato (m)"),
            ("lunghezza_stub_m", "di cui allacci privati (m)"),
            ("buffer_m", "Buffer privati (m)"),
            ("n_privati_agganciati", "Privati agganciati"),
            ("tecnologie", "Assetto impianto"),
            ("P_alta_kw", "HP alta T (kW)"),
            ("P_bassa_kw", "HP bassa T (kW)"),
            ("P_backup_kw", "Caldaia di supporto (kW)"),
            ("V_hot", "Accumulo caldo (m³)"),
            ("V_int", "Accumulo intermedio (m³)"),
            ("V_low", "Accumulo basso (m³)"),
            ("E_hot_diretto", "Scarto diretto (MWh/a)"),
            ("E_hp_alta", "Consegnato da HP alta T (MWh/a)"),
            ("E_backup", "Da combustibile (MWh/a)"),
            ("E_elettrica", "Elettricità HP (MWh/a)"),
            ("E_scarto_utilizzato", "Scarto utilizzato (MWh/a)"),
            ("cop_alta", "COP medio HP alta T"),
            ("spf_sistema", "SPF di sistema"),
            ("quota_fer_pct", "Quota FER (%)"),
            ("pct_scarto_su_domanda", "Scarto utilizzato / domanda (%)"),
            ("pct_rinnovabile", "Rinnovabile / fornito (%)"),
            ("co2_evitata_t", "CO\u2082 evitata (t/a)"),
            ("co2_sistema_t", "CO\u2082 residua sistema (t/a)"),
            ("ore_non_coperte", "Ore non coperte"),
            ("capex_sistema", "CAPEX centrale (\u20ac)"),
            ("capex_rete", "CAPEX rete (\u20ac)"),
            ("costo_calore_acquistato", "Acquisto calore scarto (\u20ac/a)"),
            ("opex_annuo", "OPEX (\u20ac/a)"),
            ("costo_annuo", "Costo annuo equivalente (\u20ac/a)"),
            ("lcoh", "LCOH di sistema (\u20ac/MWh)"),
        ]
        righe_cf = []
        for k, lab in _campi:
            r = {"Indicatore": lab}
            for nome, s in _scen.items():
                r[nome] = s.get(k, "—")
            righe_cf.append(r)
        df_cf = pd.DataFrame(righe_cf)
        st.dataframe(df_cf, use_container_width=True, hide_index=True)

        st.divider()

        # --- grafici di confronto ---
        nomi = list(_scen.keys())
        _pal_scen = px.colors.qualitative.Set2

        gg1, gg2 = st.columns(2)
        with gg1:
            st.markdown("**LCOH di sistema**")
            _v = [(_scen[n].get("lcoh") or 0) for n in nomi]
            fig_l = go.Figure(go.Bar(x=nomi, y=_v, marker_color=_pal_scen[:len(nomi)],
                                     text=[f"{x:.1f}" for x in _v], textposition="outside"))
            fig_l.update_layout(height=340, yaxis_title="\u20ac/MWh", margin=dict(t=20, b=10),
                                xaxis_tickangle=-20)
            st.plotly_chart(fig_l, use_container_width=True)
        with gg2:
            st.markdown("**Quota FER**")
            _v = [_scen[n].get("quota_fer_pct", 0) for n in nomi]
            fig_f = go.Figure(go.Bar(x=nomi, y=_v, marker_color=COLOR_OFFERTA,
                                     text=[f"{x:.0f}%" for x in _v], textposition="outside"))
            fig_f.update_layout(height=340, yaxis_title="%", margin=dict(t=20, b=10),
                                xaxis_tickangle=-20, yaxis_range=[0, 105])
            st.plotly_chart(fig_f, use_container_width=True)

        gg3, gg4 = st.columns(2)
        with gg3:
            st.markdown("**CO\u2082 evitata rispetto al gas**")
            _v = [_scen[n].get("co2_evitata_t", 0) for n in nomi]
            fig_co2 = go.Figure(go.Bar(x=nomi, y=_v, marker_color="#2E7D32",
                                       text=[f"{x:,.0f}".replace(",", ".") for x in _v],
                                       textposition="outside"))
            fig_co2.update_layout(height=340, yaxis_title="t CO\u2082 / anno",
                                  margin=dict(t=20, b=10), xaxis_tickangle=-20)
            st.plotly_chart(fig_co2, use_container_width=True)
        with gg4:
            st.markdown("**Scarto utilizzato e rinnovabile**")
            fig_pct = go.Figure()
            fig_pct.add_trace(go.Bar(x=nomi, y=[_scen[n].get("pct_scarto_su_domanda", 0) for n in nomi],
                                     name="Scarto / domanda", marker_color=COLOR_ALTA_T))
            fig_pct.add_trace(go.Bar(x=nomi, y=[_scen[n].get("pct_rinnovabile", 0) for n in nomi],
                                     name="Rinnovabile / fornito", marker_color=COLOR_OFFERTA))
            fig_pct.update_layout(barmode="group", height=340, yaxis_title="%",
                                  margin=dict(t=20, b=10), xaxis_tickangle=-20,
                                  legend=dict(orientation="h", yanchor="bottom", y=1.02),
                                  yaxis_range=[0, 105])
            st.plotly_chart(fig_pct, use_container_width=True)

        st.markdown("**Mix di produzione per scenario**")
        fig_mixs = go.Figure()
        _voci_mix = [("E_hot_diretto", "Scarto diretto", COLOR_ALTA_T),
                     ("E_hp_alta", "HP alta T", COLOR_HP),
                     ("E_backup", "Combustibile", COLOR_BACKUP)]
        for k, lab, col in _voci_mix:
            fig_mixs.add_trace(go.Bar(x=nomi, y=[_scen[n].get(k, 0) for n in nomi],
                                      name=lab, marker_color=col))
        fig_mixs.update_layout(barmode="stack", height=380, yaxis_title="MWh/a",
                               legend=dict(orientation="h", yanchor="bottom", y=1.02),
                               margin=dict(t=30, b=10), xaxis_tickangle=-20)
        st.plotly_chart(fig_mixs, use_container_width=True)

        st.markdown("**CAPEX centrale vs CAPEX rete vs OPEX annuo**")
        fig_cx = go.Figure()
        fig_cx.add_trace(go.Bar(x=nomi, y=[_scen[n].get("capex_sistema", 0) for n in nomi],
                                name="CAPEX centrale", marker_color="#5B8DEF"))
        fig_cx.add_trace(go.Bar(x=nomi, y=[_scen[n].get("capex_rete", 0) for n in nomi],
                                name="CAPEX rete", marker_color="#8E5FC2"))
        fig_cx.add_trace(go.Scatter(x=nomi, y=[_scen[n].get("opex_annuo", 0) for n in nomi],
                                    name="OPEX annuo", mode="markers+lines",
                                    marker=dict(size=12, color="#F4A259"), yaxis="y2"))
        fig_cx.update_layout(barmode="stack", height=400, yaxis_title="\u20ac (CAPEX)",
                             yaxis2=dict(title="\u20ac/a (OPEX)", overlaying="y", side="right"),
                             legend=dict(orientation="h", yanchor="bottom", y=1.02),
                             margin=dict(t=30, b=10), xaxis_tickangle=-20)
        st.plotly_chart(fig_cx, use_container_width=True)

        st.download_button(
            "\u2B07\ufe0f Scarica il confronto (CSV)",
            data=df_cf.to_csv(index=False).encode("utf-8"),
            file_name="maniago_tlr_confronto_scenari.csv", mime="text/csv")


# =============================================================================
# TAB 5 - ANALISI ECONOMICA
# =============================================================================
with tab_economia:
    st.markdown("### \U0001F4B6 Analisi economica del progetto")
    _snap = st.session_state.get("_dim_snapshot")

    if not _snap:
        st.info("Configura prima uno scenario nella scheda **Dimensionamento**: "
                "l'analisi economica ne eredita automaticamente i risultati.")
    else:
        st.caption(f"Scenario corrente: **{_snap['tecnologie']}** · "
                   f"calore venduto **{_snap['carico_utenze_mwh']:,} MWh/a** · "
                   f"prodotto in centrale **{_snap['carico_centrale_mwh']:,} MWh/a** "
                   f"(perdite di rete {_snap['perdite_rete_pct']:.1f} %)".replace(",", "."))

        ec1, ec2, ec3 = st.columns(3)
        with ec1:
            st.markdown("**Ricavi**")
            _unita_prezzo = st.radio("Unità del prezzo di vendita", ["\u20ac/MWh", "\u20ac/kWh"],
                                     horizontal=True, key="eco_unita_prezzo")
            if _unita_prezzo == "\u20ac/MWh":
                prezzo_calore = st.slider("Prezzo di vendita del calore (\u20ac/MWh)", 40, 180, 95,
                                          step=5, key="eco_prezzo",
                                          help="Si applica al calore VENDUTO alle utenze, non a "
                                               "quello prodotto in centrale: le perdite di rete "
                                               "sono a carico del gestore.")
            else:
                prezzo_calore = st.slider("Prezzo di vendita del calore (\u20ac/kWh)", 0.040, 0.180,
                                          0.095, step=0.005, format="%.3f", key="eco_prezzo_kwh",
                                          help="Si applica al calore VENDUTO alle utenze.") * 1000.0
            quota_fissa = st.slider("Quota fissa per utenza (\u20ac/a)", 0, 800, 250, step=25,
                                    key="eco_quotafissa")
            n_utenze_eco = st.number_input("Numero di utenze contrattualizzate", min_value=0,
                                           value=int(st.session_state.get("_rete_info", {}).get("n_utenze", 0)),
                                           step=1, key="eco_nutenze")
            allacci_eur = st.slider("Contributo di allacciamento una tantum (\u20ac/utenza)",
                                    0, 8000, 1500, step=250, key="eco_allacci")
        with ec2:
            st.markdown("**Costi**")
            st.caption(f"OPEX energia dallo scenario: **{_snap['opex_annuo']:,} \u20ac/a**".replace(",", "."))
            # costo di acquisto del calore di scarto dalle aziende (gia calcolato
            # in Dimensionamento a partire dai prezzi per-azienda impostati in Offerta)
            _costo_scarto_base = float(_snap.get("costo_calore_acquistato", 0))
            st.caption(f"Calore di scarto acquistato dalle aziende (dai prezzi impostati in "
                       f"*Offerta*): **{_costo_scarto_base:,.0f} \u20ac/a**".replace(",", "."))
            _scarto_mult = st.slider("Correttivo sul costo del calore di scarto (\u00d7)",
                                     0.0, 3.0, 1.0, step=0.1, key="eco_scarto_mult",
                                     help="Moltiplicatore rapido per testare scenari di prezzo "
                                          "del cascame senza tornare in Offerta. 1.0 = prezzi "
                                          "impostati per azienda.")
            costo_scarto = _costo_scarto_base * _scarto_mult
            om_pct = st.slider("O&M in % del CAPEX totale (\u20ac/a)", 0.5, 5.0, 2.0, step=0.25,
                               key="eco_om")
            pompaggio_kwh_mwh = st.slider("Elettricità di pompaggio (kWh el / MWh distribuito)",
                                          0, 40, 12, step=1, key="eco_pomp",
                                          help="QM: 8-20 kWh/MWh per reti ben progettate.")
            personale = st.slider("Personale e gestione (\u20ac/a)", 0, 200000, 45000, step=5000,
                                  key="eco_personale")
            assicuraz = st.slider("Assicurazioni, amministrazione, varie (\u20ac/a)",
                                  0, 100000, 15000, step=2500, key="eco_assic")
        with ec3:
            st.markdown("**Finanziario**")
            orizzonte = st.slider("Orizzonte di analisi (anni)", 10, 40, 25, key="eco_anni")
            wacc = st.slider("Tasso di attualizzazione WACC (%)", 1.0, 12.0, 4.0, step=0.5,
                             key="eco_wacc") / 100.0
            contributo_pct = st.slider("Contributo a fondo perduto (% del CAPEX)", 0, 80, 40, step=5,
                                       key="eco_contributo")
            esc_ricavi = st.slider("Escalation ricavi (%/a)", 0.0, 6.0, 2.0, step=0.25,
                                   key="eco_esc_ric") / 100.0
            esc_costi = st.slider("Escalation costi energia (%/a)", 0.0, 8.0, 3.0, step=0.25,
                                  key="eco_esc_cos") / 100.0
            esc_om = st.slider("Escalation O&M (%/a)", 0.0, 6.0, 2.0, step=0.25,
                               key="eco_esc_om") / 100.0

        # ---------------------------------------------------------------------
        capex_centrale = float(_snap["capex_sistema"])
        capex_rete = float(_snap["capex_rete"])
        capex_tot = capex_centrale + capex_rete
        contributo = capex_tot * contributo_pct / 100.0
        capex_netto = capex_tot - contributo

        E_venduto = float(_snap["carico_utenze_mwh"])
        E_prodotto = float(_snap["carico_centrale_mwh"])

        ricavo_calore_0 = E_venduto * prezzo_calore
        ricavo_fisso_0 = n_utenze_eco * quota_fissa
        ricavi_0 = ricavo_calore_0 + ricavo_fisso_0
        incasso_allacci = n_utenze_eco * allacci_eur

        opex_energia_0 = float(_snap["opex_annuo"])
        costo_pompaggio_0 = E_prodotto * pompaggio_kwh_mwh / 1000.0 * float(_snap["prezzo_el"])
        om_0 = capex_tot * om_pct / 100.0
        costi_fissi_0 = personale + assicuraz
        # il calore di scarto acquistato dalle aziende segue l'escalation energia
        costo_scarto_0 = float(costo_scarto)

        # --- flussi di cassa ---
        flussi_cassa = [-(capex_netto) + incasso_allacci]
        dettaglio = []
        for t in range(1, orizzonte + 1):
            ric = ricavi_0 * (1 + esc_ricavi) ** (t - 1)
            c_en = (opex_energia_0 + costo_pompaggio_0 + costo_scarto_0) * (1 + esc_costi) ** (t - 1)
            c_om = (om_0 + costi_fissi_0) * (1 + esc_om) ** (t - 1)
            netto = ric - c_en - c_om
            flussi_cassa.append(netto)
            dettaglio.append({"Anno": t, "Ricavi (\u20ac)": round(ric),
                              "Costi energia (\u20ac)": round(c_en),
                              "O&M e gestione (\u20ac)": round(c_om),
                              "Flusso netto (\u20ac)": round(netto)})

        _van = van(flussi_cassa, wacc)
        _tir = tir(flussi_cassa)
        _pb = payback_semplice(flussi_cassa)
        margine_0 = ricavi_0 - opex_energia_0 - costo_pompaggio_0 - om_0 - costi_fissi_0

        # LCOH completo: include rete, O&M, pompaggio; riferito al calore VENDUTO
        _crf_eco = crf(wacc, orizzonte)
        costo_annuo_completo = (capex_netto * _crf_eco + opex_energia_0 + costo_pompaggio_0
                                + costo_scarto_0 + om_0 + costi_fissi_0)
        lcoh_completo = costo_annuo_completo / E_venduto if E_venduto > 0 else np.nan

        st.divider()
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("VAN", f"{_van / 1e6:.2f} M\u20ac",
                  delta="positivo" if _van > 0 else "negativo",
                  delta_color="normal" if _van > 0 else "inverse")
        m2.metric("TIR", f"{_tir * 100:.1f}%" if _tir is not None else "n/d",
                  help="Non definito se i flussi non cambiano mai segno.")
        m3.metric("Payback semplice", f"{_pb:.1f} anni" if _pb is not None else "> orizzonte",
                  help="Non attualizzato.")
        m4.metric("Margine anno 1", f"{margine_0 / 1000:.0f} k\u20ac/a")

        n1, n2, n3, n4 = st.columns(4)
        n1.metric("CAPEX totale", f"{capex_tot / 1e6:.2f} M\u20ac",
                  help=f"centrale {capex_centrale / 1e6:.2f} M\u20ac + rete {capex_rete / 1e6:.2f} M\u20ac")
        n2.metric("Contributo pubblico", f"{contributo / 1e6:.2f} M\u20ac",
                  help=f"{contributo_pct}% del CAPEX")
        n3.metric("Investimento netto", f"{capex_netto / 1e6:.2f} M\u20ac")
        n4.metric("LCOH completo", f"{lcoh_completo:.1f} \u20ac/MWh",
                  help="Include rete, O&M, pompaggio, personale. Riferito al calore VENDUTO. "
                       "Il 'LCOH di sistema' della scheda Dimensionamento e piu ristretto "
                       "(sola centrale, riferito al calore prodotto): non sono confrontabili "
                       "direttamente.")

        if lcoh_completo > prezzo_calore:
            st.warning(f"\u26a0\ufe0f Il costo pieno del calore ({lcoh_completo:.1f} \u20ac/MWh) supera "
                       f"il prezzo di vendita ({prezzo_calore} \u20ac/MWh): il progetto non si "
                       f"sostiene senza ulteriore contributo o senza aumentare la densità di "
                       f"utenza.")
        else:
            st.success(f"\u2705 Il prezzo di vendita ({prezzo_calore} \u20ac/MWh) copre il costo pieno "
                       f"({lcoh_completo:.1f} \u20ac/MWh): margine unitario "
                       f"{prezzo_calore - lcoh_completo:.1f} \u20ac/MWh.")

        st.divider()
        st.markdown("#### Flussi di cassa cumulati")
        cum = np.cumsum(flussi_cassa)
        anni_x = list(range(0, orizzonte + 1))
        fig_cf = go.Figure()
        fig_cf.add_trace(go.Bar(x=anni_x, y=flussi_cassa, name="Flusso annuo",
                                marker_color=["#B0413E" if f < 0 else "#3FA34D" for f in flussi_cassa]))
        fig_cf.add_trace(go.Scatter(x=anni_x, y=cum, name="Cumulato", mode="lines+markers",
                                    line=dict(color="#22C3DD", width=3)))
        fig_cf.add_hline(y=0, line_dash="dot", line_color="#888")
        fig_cf.update_layout(height=420, xaxis_title="Anno", yaxis_title="\u20ac",
                             legend=dict(orientation="h", yanchor="bottom", y=1.02),
                             margin=dict(t=30, b=10))
        st.plotly_chart(fig_cf, use_container_width=True)

        st.markdown("#### Struttura dei costi annui (anno 1)")
        _voci_c = [("Energia (elettricità HP + combustibile)", opex_energia_0, COLOR_HP),
                   ("Acquisto calore di scarto", costo_scarto_0, COLOR_OFFERTA),
                   ("Pompaggio di rete", costo_pompaggio_0, "#4C6EF5"),
                   ("O&M impianti e rete", om_0, COLOR_ACCUMULO),
                   ("Personale e gestione", personale, "#F4A259"),
                   ("Assicurazioni e varie", assicuraz, "#9AA0A6"),
                   ("CAPEX annualizzato", capex_netto * _crf_eco, "#5B8DEF")]
        _voci_c = [(n, v, c) for n, v, c in _voci_c if v > 0]
        fig_str = go.Figure(go.Pie(labels=[n for n, _, _ in _voci_c],
                                   values=[v for _, v, _ in _voci_c], hole=0.5,
                                   marker=dict(colors=[c for _, _, c in _voci_c]), sort=False))
        fig_str.update_layout(title=f"Costo annuo completo · "
                                    f"{costo_annuo_completo:,.0f} \u20ac/a".replace(",", "."),
                              height=400, margin=dict(t=50, b=10),
                              legend=dict(orientation="h", y=-0.15))
        st.plotly_chart(fig_str, use_container_width=True)

        # --- sensitivita ---
        st.markdown("#### Sensitività del VAN")
        st.caption("Variazione del VAN al variare del prezzo di vendita del calore e della quota "
                   "di contributo pubblico, a parita di tutto il resto.")
        _prezzi = np.arange(max(prezzo_calore - 40, 30), prezzo_calore + 45, 10)
        _contrib = np.arange(0, 85, 10)
        Z = np.zeros((len(_contrib), len(_prezzi)))
        for i, cp in enumerate(_contrib):
            _cn = capex_tot * (1 - cp / 100.0)
            for j, pz in enumerate(_prezzi):
                _r0 = E_venduto * pz + ricavo_fisso_0
                _fc = [-_cn + incasso_allacci]
                for t in range(1, orizzonte + 1):
                    _fc.append(_r0 * (1 + esc_ricavi) ** (t - 1)
                               - (opex_energia_0 + costo_pompaggio_0 + costo_scarto_0) * (1 + esc_costi) ** (t - 1)
                               - (om_0 + costi_fissi_0) * (1 + esc_om) ** (t - 1))
                Z[i, j] = van(_fc, wacc) / 1e6
        fig_sens = go.Figure(go.Heatmap(
            z=Z, x=[f"{p:.0f}" for p in _prezzi], y=[f"{c:.0f}%" for c in _contrib],
            colorscale="RdYlGn", zmid=0, colorbar=dict(title="VAN (M\u20ac)"),
            hovertemplate="prezzo %{x} \u20ac/MWh<br>contributo %{y}<br>VAN %{z:.2f} M\u20ac<extra></extra>"))
        fig_sens.update_layout(height=400, xaxis_title="Prezzo di vendita (\u20ac/MWh)",
                               yaxis_title="Contributo a fondo perduto", margin=dict(t=30, b=10))
        st.plotly_chart(fig_sens, use_container_width=True)

        # --- sensitivita sul prezzo del calore di scarto acquistato ---
        if _costo_scarto_base > 0:
            st.markdown("#### Sensitività al prezzo del calore di scarto")
            st.caption("VAN al variare del correttivo sul costo del cascame acquistato dalle "
                       "aziende e del prezzo di vendita del calore, a parità del resto.")
            _mult_range = np.arange(0.0, 3.01, 0.5)
            _prezzi2 = np.arange(max(prezzo_calore - 40, 30), prezzo_calore + 45, 10)
            Z2 = np.zeros((len(_mult_range), len(_prezzi2)))
            for i, mu in enumerate(_mult_range):
                _cs = _costo_scarto_base * mu
                for j, pz in enumerate(_prezzi2):
                    _r0 = E_venduto * pz + ricavo_fisso_0
                    _fc = [-capex_netto + incasso_allacci]
                    for t in range(1, orizzonte + 1):
                        _fc.append(_r0 * (1 + esc_ricavi) ** (t - 1)
                                   - (opex_energia_0 + costo_pompaggio_0 + _cs) * (1 + esc_costi) ** (t - 1)
                                   - (om_0 + costi_fissi_0) * (1 + esc_om) ** (t - 1))
                    Z2[i, j] = van(_fc, wacc) / 1e6
            fig_sens2 = go.Figure(go.Heatmap(
                z=Z2, x=[f"{p:.0f}" for p in _prezzi2],
                y=[f"\u00d7{m:.1f}" for m in _mult_range],
                colorscale="RdYlGn", zmid=0, colorbar=dict(title="VAN (M\u20ac)"),
                hovertemplate="vendita %{x} \u20ac/MWh<br>scarto %{y}<br>VAN %{z:.2f} M\u20ac<extra></extra>"))
            fig_sens2.update_layout(height=360, xaxis_title="Prezzo di vendita (\u20ac/MWh)",
                                    yaxis_title="Correttivo costo scarto",
                                    margin=dict(t=30, b=10))
            st.plotly_chart(fig_sens2, use_container_width=True)

        # --- indicatori ambientali ---
        st.markdown("#### \U0001F30D Impatto ambientale")
        amb1, amb2, amb3 = st.columns(3)
        amb1.metric("CO\u2082 evitata / anno", f"{_snap.get('co2_evitata_t', 0):,.0f} t/a".replace(",", "."),
                    help="Rispetto a una caldaia a gas equivalente (0,20 tCO\u2082/MWh, rendimento "
                         "90 %), al netto delle emissioni residue del sistema.")
        amb2.metric("CO\u2082 evitata nell'orizzonte",
                    f"{_snap.get('co2_evitata_t', 0) * orizzonte / 1000:,.1f} kt".replace(",", "."),
                    help=f"su {orizzonte} anni")
        _val_co2 = st.slider("Valore della CO\u2082 (\u20ac/t) per stima ETS", 0, 200, 80, step=10,
                             key="eco_valco2")
        amb3.metric("Valore CO\u2082 evitata / anno",
                    f"{_snap.get('co2_evitata_t', 0) * _val_co2 / 1000:,.0f} k\u20ac/a".replace(",", "."),
                    help="Beneficio economico potenziale (non incluso nel VAN sopra).")

        with st.expander("\U0001F4C4 Dettaglio dei flussi di cassa anno per anno"):
            df_det = pd.DataFrame(dettaglio)
            df_det["Cumulato (\u20ac)"] = df_det["Flusso netto (\u20ac)"].cumsum() + flussi_cassa[0]
            st.dataframe(df_det, use_container_width=True, hide_index=True)
            st.download_button("\u2B07\ufe0f Scarica i flussi (CSV)",
                               data=df_det.to_csv(index=False).encode("utf-8"),
                               file_name="maniago_tlr_flussi_cassa.csv", mime="text/csv")

        st.caption(
            "**Nota metodologica.** I ricavi si applicano al calore *venduto* alle utenze, mentre "
            "i costi di produzione si riferiscono al calore *prodotto in centrale*: la differenza "
            "sono le perdite di rete (QM cap. 12.2.8), che restano a carico del gestore. "
            "Il payback e semplice, non attualizzato. L'O&M e stimato in percentuale del CAPEX "
            "totale (centrale + rete) e segue una propria escalation, distinta da quella dei "
            "prezzi dell'energia."
        )

# =============================================================================
# FOOTER
# =============================================================================
st.divider()
st.markdown(FOOTER_HTML)
st.caption(
    "Strumento di supporto allo studio di fattibilità. I risultati dipendono dalla qualità "
    "dei dati di ingresso e dalle ipotesi selezionate: non sostituiscono un progetto esecutivo. "
    "Metodologia di riferimento: QM Holzheizwerke Planning Handbook (3rd ed.), "
    "Verenum Planungshandbuch Fernw\u00e4rme, IEA DHC Annex TS5. "
    "Dati di emissione dei forni: Ecol Studio SpA, rapporti di prova 25LF24167-170 del 14/07/2025."
)
