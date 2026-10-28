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
 P22 Riorganizzazione del solare fra le schede:
     - Offerta decide soltanto se considerare un campo di COLLETTORI TERMICI;
     - Dimensionamento ne stabilisce superficie, temperatura e costo;
     - i MODULI IBRIDI passano alla scheda Carico elettrico, dove elettricita'
       e calore si valutano insieme, e il loro contributo termico rientra nel
       dispatch con un trasferimento esplicito;
     - il FOTOVOLTAICO resta solo nella scheda elettrica.
     La scheda elettrica sostituisce la "copertura obiettivo" con una
     OTTIMIZZAZIONE DI SISTEMA che cerca la combinazione di ibridi,
     fotovoltaico e accumulo a costo di approvvigionamento minimo.
     Nota metodologica: con l'eccedenza valorizzata al prezzo di mercato
     l'ottimo non esiste (il fotovoltaico produce a ~56 EUR/MWh e l'energia
     immessa ne vale ~105, quindi conviene sempre ingrandire). Valutando
     l'impianto come approvvigionamento, con l'eccedenza a valore nullo,
     l'ottimo torna interno e ben definito. Il cursore permette comunque di
     valorizzarla, avvisando che in quel caso il vincolo diventa la superficie
     o la potenza di connessione.
     Nel bilancio dell'ibrido si conta anche il calore prodotto, valorizzato
     come costo evitato alle pompe: senza di esso l'ibrido non risulterebbe
     mai conveniente rispetto al fotovoltaico.
 P21 Parametro n_griglia nell'ottimizzatore: regola la finezza della ricerca
     sui volumi di accumulo, che si riflette al cubo sul tempo di calcolo.
     Serve allo script scenari_maniago.py, che percorre in batch l'intero
     ventaglio di configurazioni e produce la tabella di confronto.
 P20 Solare riorganizzato: in Offerta solo la scelta se considerarlo, in
     Dimensionamento la tecnologia (collettori termici o moduli ibridi) e la
     taglia, nella scheda elettrica il fotovoltaico a valle. Quest'ultima
     mostra la copertura attuale, dimensiona il fotovoltaico per taglia o per
     copertura obiettivo entro il limite di superficie disponibile, e confronta
     la configurazione a miglior ritorno economico con quella a massima
     autonomia dalla rete.
     CORREZIONE: la conversione da irraggiamento a produzione fotovoltaica
     applicava il rendimento del modulo una seconda volta, sottostimando la
     resa di circa 5,6 volte (214 invece di ~1.190 kWh/kWp). Un kWp e' per
     definizione la potenza a 1.000 W/m2 in condizioni standard: il rendimento
     e' gia' nella definizione e va tolto solo il BOS.
 P19 Scomposizione energetica per origine (calore di scarto, solare, loop
     geotermico, HP alta temperatura, fonte di backup) con quote che sommano
     esattamente alla domanda; costo della rete differenziato per diametro,
     con lo scavo separato dalla fornitura; sottostazioni d'utenza in analisi
     economica; diagnostica del contributo, del prezzo o del calore aggiuntivo
     necessari quando il progetto non rientra.
 P18 Catalogo di moduli ibridi PVT selezionabile (Abora aH72 vetrato e isolato,
     Fototherm FT320AS e FT265CS non isolati), con i parametri certificati
     EN ISO 9806 delle rispettive schede tecniche e i limiti di temperatura
     di circuito dichiarati dai costruttori.
 P17 Solare dimensionabile anche per quota della domanda coperta; PV
     dimensionabile per copertura del consumo elettrico; volumi di prelievo
     idrico nel caso di acqua di falda; struttura finanziaria completa in
     analisi economica (debito con piano di ammortamento, ammortamenti
     fiscali, imposte sul reddito imponibile, DSCR, TIR di progetto e per
     l'azionista, prezzo di equilibrio).
 P16 Sorgente fredda della HP bassa T dimensionata davvero (sonde verticali,
     serpentine orizzontali o acqua di falda) con superficie, numero di pozzi
     e costo; nuova scheda "Carico elettrico" con autoconsumo, accumulo e
     valorizzazione ai prezzi zonali orari; solare governabile da superficie
     o da potenza richiesta; soglia di densita' azzerabile per includere
     tutti gli edifici.
 P15 Profili orari rivisti: i privati e i condomini hanno una forma
     residenziale propria (due punte giornaliere, distinzione feriale/festivo)
     invece di ereditare quella degli edifici pubblici; le fermate degli
     impianti industriali seguono il calendario reale invece di essere
     estratte a sorte; l'anno solare conserva la sequenza reale dei giorni,
     quindi le sequenze di giornate coperte che dimensionano l'accumulo.
     La potenza dei flussi e' limitata allo scambiatore quotato dove noto.
 P14 Stratificazione dell'accumulo intermedio: strati da 5 K, la pompa alta T
     preleva dal piu' caldo disponibile. La temperatura utile e' la media fra
     quella dello strato e quella di base dell'anello, perche' il fluido cede
     calore raffreddandosi. Disattivabile per tornare al mescolamento perfetto.
 P13 Flusso guidato in 4 passi nel dimensionamento, distinzione fra
     "dimensiona" (ricerca automatica) e "calcola" (taglie imposte),
     tetto ai volumi di accumulo, schema di massima dell'impianto in SVG
     e scheda PDF di confronto degli scenari.
 P12 Pannelli solari ibridi PVT (Abora aH72 M2): resa termica ed elettrica
     calcolata ora per ora dai parametri certificati EN ISO 9806 (eta0, a1, a2)
     e dal modello NOCT, con la temperatura del fluido come variabile. L'energia
     elettrica prodotta si porta in detrazione dei consumi delle pompe di calore.
 P11 Routing su strade reali OSM (Overpass API) con Dijkstra (networkx):
     ogni edificio "snappa" al nodo stradale piu vicino, il tratto obbligato
     e un albero di Steiner approssimato lungo le strade, gli stub dei privati
     sono anch'essi calcolati su strada. Cache locale in maniago_strade_cache.json.
     Dipendenze: networkx, scipy, requests (fallback silenzioso a MST se assenti).

 Requisiti: streamlit >= 1.45, plotly >= 5.24 (mappe MapLibre supportate anche
 nelle versioni precedenti tramite il ripiego di compatibilita' in testa al file),
 pandas, numpy, networkx, scipy, requests.

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

# -----------------------------------------------------------------------------
# COMPATIBILITA' PLOTLY - MAPPE
# Plotly ha migrato da Mapbox a MapLibre: le tracce Scattermapbox/Densitymapbox
# e la chiave di layout "mapbox" sono state rimosse a favore di Scattermap,
# Densitymap e "map". Il codice usa la nuova API; qui viene fornito un ripiego
# per le versioni precedenti, cosi' l'app gira su entrambe.
# -----------------------------------------------------------------------------
if hasattr(go, "Scattermap"):
    MAP_NUOVA_API = True
else:
    MAP_NUOVA_API = False
    go.Scattermap = go.Scattermapbox
    go.Densitymap = go.Densitymapbox

# Nomi degli stili base: cambiano tra le due generazioni di API.
_STILI_MAPPA = {
    "chiaro": "basic" if MAP_NUOVA_API else "open-street-map",
    "scuro": "dark" if MAP_NUOVA_API else "carto-darkmatter",
}


def layout_mappa(center_lat, center_lon, zoom, stile="chiaro"):
    """Blocco di layout per le mappe, con la chiave giusta per la versione
    di Plotly installata ("map" sulla nuova API, "mapbox" sulla precedente)."""
    cfg = dict(style=_STILI_MAPPA.get(stile, _STILI_MAPPA["chiaro"]),
               center=dict(lat=center_lat, lon=center_lon), zoom=zoom)
    return {"map": cfg} if MAP_NUOVA_API else {"mapbox": cfg}

# scipy in cima al modulo per evitare problemi di import dentro cache_data
try:
    from scipy.spatial import cKDTree
    _HAS_SCIPY = True
except Exception:
    _HAS_SCIPY = False

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
# -----------------------------------------------------------------------------
# SCENARI PERSISTENTI
# Gli scenari salvati vivevano solo nella sessione del browser: ricaricando la
# pagina o riaprendo l'app sparivano. Ora vengono scritti anche in un file JSON
# accanto allo script e riletti all'avvio di ogni sessione. Su Streamlit Cloud
# il disco si azzera quando l'app viene riavviata o ridistribuita (per esempio
# dopo un commit su GitHub): per conservarli in modo definitivo si usa
# l'esportazione/importazione JSON della scheda Confronto scenari.
# -----------------------------------------------------------------------------
FILE_SCENARI = "scenari_salvati.json"


def _json_default(o):
    """Converte numpy e tipi non standard in valori serializzabili."""
    if hasattr(o, "item"):
        try:
            return o.item()
        except Exception:
            pass
    if isinstance(o, (set, tuple)):
        return list(o)
    return str(o)


def _firma_el(r):
    """Impronta del risultato del passo Carico elettrico usata dal dimensionamento."""
    if not r:
        return None
    return tuple(round(float(r.get(k, 0) or 0), 1) for k in
                 ("consumo_mwh", "acquisto_eur", "ricavo_eur", "capex_eur", "copertura_pct"))


def carica_scenari_file(percorso=FILE_SCENARI):
    try:
        with open(percorso, "r", encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def salva_scenari_file(scenari, percorso=FILE_SCENARI):
    """Scrive gli scenari su disco. Ritorna True se riuscito."""
    try:
        _tmp = percorso + ".tmp"
        with open(_tmp, "w", encoding="utf-8") as f:
            json.dump(scenari, f, ensure_ascii=False, indent=1, default=_json_default)
        os.replace(_tmp, percorso)
        return True
    except Exception:
        return False


if "_scenari" not in st.session_state:
    st.session_state["_scenari"] = carica_scenari_file()

# -----------------------------------------------------------------------------
# REGISTRO DELLE IPOTESI
# Per riportare nella scheda PDF TUTTE le ipotesi di uno scenario serve sapere,
# per ogni comando, l'etichetta che l'utente vede. I comandi di input vengono
# avvolti una sola volta per processo: ogni chiamata con una `key` registra
# l'etichetta nella sessione. Il valore si legge poi da st.session_state.
# -----------------------------------------------------------------------------
_WIDGET_IPOTESI = ("slider", "select_slider", "number_input", "checkbox", "radio",
                   "selectbox", "multiselect", "text_input", "toggle")


def _registra_etichetta(label, kwargs):
    try:
        _k = kwargs.get("key")
        if _k:
            _reg = st.session_state.setdefault("_etichette_widget", {})
            _reg[str(_k)] = str(label)
            # comandi effettivamente mostrati in questa esecuzione: servono a non
            # riportare valori rimasti in memoria di comandi oggi nascosti
            st.session_state.setdefault("_widget_cur", set()).add(str(_k))
    except Exception:
        pass


def _avvolgi_widget():
    try:
        from streamlit.delta_generator import DeltaGenerator as _DG
    except Exception:
        _DG = None
    for _n in _WIDGET_IPOTESI:
        if _DG is not None and hasattr(_DG, _n):
            _orig = getattr(_DG, _n)
            if not getattr(_orig, "_tlr_avvolto", False):
                def _mk_m(orig):
                    def _w(self, label, *a, **k):
                        _registra_etichetta(label, k)
                        return orig(self, label, *a, **k)
                    _w._tlr_avvolto = True
                    return _w
                setattr(_DG, _n, _mk_m(_orig))
        if hasattr(st, _n):
            _orig_f = getattr(st, _n)
            if not getattr(_orig_f, "_tlr_avvolto", False):
                def _mk_f(orig):
                    def _w(label, *a, **k):
                        _registra_etichetta(label, k)
                        return orig(label, *a, **k)
                    _w._tlr_avvolto = True
                    return _w
                setattr(st, _n, _mk_f(_orig_f))


_avvolgi_widget()
# ad ogni esecuzione si ricorda quali comandi erano visibili in quella precedente
st.session_state["_widget_prev"] = set(st.session_state.get("_widget_cur", set()))
st.session_state["_widget_cur"] = set()

# prefisso della chiave -> scheda in cui si trova il comando
_SCHEDE_IPOTESI = [("dom_", "Domanda"), ("off_", "Offerta"), ("dim_", "Dimensionamento"),
                   ("el_", "Dimensionamento · carico elettrico"), ("eco_", "Analisi economica")]
# chiavi da non riportare singolarmente: le selezioni per edificio e per flusso
# vengono riassunte negli elenchi, i pulsanti e i caricamenti non sono ipotesi
_ESCLUSE_IPOTESI = ("dom_ed_", "dom_cl_", "dom_p_", "dom_c_", "off_az_", "off_fl_",
                    "dim_btn", "dim_nome_scen", "dom_osm_upload", "del_scen",
                    "dom_retry", "off_retry", "dim_rimuovi", "dom_dens_vista",
                    "dom_dens_cella", "dom_mostra_strade", "eco_dl", "conf_",
                    "dim_dl", "dom_all_tip", "dom_view")


def raccogli_ipotesi():
    """Fotografa tutte le ipotesi correnti: valore di ogni comando con la sua
    etichetta e la scheda, piu' gli elenchi di zone, edifici e flussi."""
    _reg = st.session_state.get("_etichette_widget", {})
    _visibili = (set(st.session_state.get("_widget_prev", set()))
                 | set(st.session_state.get("_widget_cur", set())))
    righe = []
    for _k in sorted(st.session_state.keys()):
        _k = str(_k)
        _sch = next((s for p, s in _SCHEDE_IPOTESI if _k.startswith(p)), None)
        if _sch is None or _k.startswith(_ESCLUSE_IPOTESI) or _k not in _visibili:
            continue
        _v = st.session_state.get(_k)
        if isinstance(_v, (bytes, bytearray)) or callable(_v) or _v is None:
            continue
        if hasattr(_v, "item"):
            _v = _v.item()
        if isinstance(_v, tuple):
            _v = list(_v)
        if not isinstance(_v, (int, float, str, bool, list)):
            continue
        _lab = _reg.get(_k, _k)
        _lab = _lab.replace("**", "").strip()
        righe.append({"scheda": _sch, "chiave": _k, "ipotesi": _lab, "valore": _v})
    _ordine = {s: i for i, (_, s) in enumerate(_SCHEDE_IPOTESI)}
    righe.sort(key=lambda r: (_ordine.get(r["scheda"], 9), r["ipotesi"].lower()))
    elenchi = {
        "Zone selezionate": list(st.session_state.get("_dom_zone", []) or []),
        "Edifici selezionati": list(st.session_state.get("_dom_edifici", []) or []),
        "Edifici serviti dal tracciato": list(st.session_state.get("_dom_edifici_serviti", []) or []),
        "Esclusi dal tracciato": list(st.session_state.get("_dom_esclusi_rete", []) or []),
        "Flussi di calore di scarto": list(st.session_state.get("_off_flussi", []) or []),
        "Prezzo del calore di scarto (€/MWh)": {
            str(a): v for a, v in (st.session_state.get("_off_prezzi_scarto", {}) or {}).items()},
    }
    return {"parametri": righe, "elenchi": elenchi}

# -----------------------------------------------------------------------------
# PALETTE
# -----------------------------------------------------------------------------
COLOR_RISCALDAMENTO = "#C0522D"
COLOR_ACS = "#2D7DC0"
COLOR_OFFERTA = "#3FA34D"
COLOR_ACCUMULO = "#8E5FC2"
COLOR_HP = "#22C3DD"
COLOR_CALDAIA = "#B0413E"
COLOR_MANIAGO_SUD = "#E63946"
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
    2: "Zona 2 - Caserme",
    3: "Zona 3 - Sud",
    4: "Zona 4 - Centro",
    5: "Zona 5 - Ovest",
}
ZONE_DEFAULT = ["Zona 1 - Comune NE", "Zona 2 - Caserme"]
ZONA_COLORI = {
    "Zona 1 - Comune NE": "#2D7DC0",
    "Zona 2 - Caserme": "#E63946",
    "Zona 3 - Sud": "#E9C46A",
    "Zona 4 - Centro": "#9B5DE5",
    "Zona 5 - Ovest": "#3FA34D",
}
CAMPAGNA_LON_MIN = 12.73
# edifici pubblici non spuntati all'avvio (si possono comunque selezionare)
PUBBLICI_NON_SPUNTATI = {"Centro sociale Dandolo", "Magazzino comunale"}

MONTH_NAMES = ["Gen", "Feb", "Mar", "Apr", "Mag", "Giu", "Lug", "Ago", "Set", "Ott", "Nov", "Dic"]
RHO_CP = 1.163          # kWh/(m3*K)
MWH_PER_UNITA = 9.0
HOURS_2024 = pd.date_range("2024-01-01", "2024-12-31 23:00", freq="h")
DAYS_2024 = pd.date_range("2024-01-01", "2024-12-31", freq="D")

AZIENDE_COORD = {
    # Coordinate GPS reali degli stabilimenti (fornite da APE FVG, formato DMS convertito).
    "Inossman":    (46.154511, 12.722867),  # Via dell'Industria 4, Molino di Campagna
    "Pietro Rosa": (46.150386, 12.719578),  # Via Ponte Giulio 76, Maniago
    "ZML":         (46.148400, 12.727597),  # Via dell'Industria 10, Maniago
    "Pandolfo":    (46.146761, 12.719458),  # Via Ponte Giulio 45, Maniago
}
# Sottocentrale: punto intermedio tra il baricentro delle aziende sorgente e
# il baricentro degli edifici pubblici serviti. E' un compromesso tra la
# vicinanza alle fonti di calore e la distribuzione all'utenza.
# Il valore hardcoded qui e' un fallback quando gli edifici non sono ancora
# stati caricati; nel tab Domanda viene ricalcolato dinamicamente.
_LAT_BAR_AZIENDE = sum(v[0] for v in AZIENDE_COORD.values()) / len(AZIENDE_COORD)
_LON_BAR_AZIENDE = sum(v[1] for v in AZIENDE_COORD.values()) / len(AZIENDE_COORD)
CENTRALE_LAT, CENTRALE_LON = 46.149000, 46.149000  # placeholder, ricalcolato

# Distanza massima ammessa tra un edificio e il nodo stradale piu vicino del
# grafo OSM. Oltre questa soglia l'edificio non viene considerato agganciabile:
# senza il limite, edifici in zone con copertura stradale rada producevano
# allacci rettilinei lunghi centinaia di metri che tagliavano l'abitato.
MAX_SNAP_M = 120.0

# Centro attorno a cui si scarica la rete stradale. E' volutamente FISSO e
# indipendente dalla posizione della sottocentrale, che invece si sposta con
# le selezioni dell'utente: se cambiasse, ogni spostamento farebbe ripartire
# un download da Overpass, con il rischio di incappare nel limite di richieste.
# Il raggio e' ampio abbastanza da coprire sia il centro urbano sia la zona
# industriale in qualunque configurazione.
GRAFO_CENTRO_LAT = 46.1495
GRAFO_CENTRO_LON = 12.7175
GRAFO_RAGGIO_KM = 3.0
# Riquadro (sud, ovest, nord, est) effettivamente scaricato: e' ritagliato
# sull'area di studio (edifici pubblici, condomini, privati e aziende, con
# ~300 m di margine) invece che su un quadrato attorno al centro. E' piu'
# piccolo del quadrato da 3 km ma copre anche Fratta, la Biblioteca e i
# privati piu' a nord e a ovest, che il quadrato lasciava fuori. Un riquadro
# piu' grande (raggio 3,6 km) faceva scadere Overpass e superare all'API
# ufficiale il limite di 50.000 nodi per richiesta (HTTP 400).
GRAFO_BBOX = (46.1440, 12.6730, 46.1840, 12.7510)

def calcola_sottocentrale(bmap_df):
    """Calcola la sottocentrale come punto intermedio tra il baricentro
    delle 4 aziende sorgente e il baricentro degli edifici pubblici passati.

    Se bmap_df e' vuoto, ritorna il baricentro delle aziende (nessun utente
    da servire -> la centrale sta comunque dove sono le fonti).
    """
    if bmap_df is None or bmap_df.empty:
        return _LAT_BAR_AZIENDE, _LON_BAR_AZIENDE
    _lat_pub = float(bmap_df["lat"].mean())
    _lon_pub = float(bmap_df["lon"].mean())
    return ((_LAT_BAR_AZIENDE + _lat_pub) / 2,
            (_LON_BAR_AZIENDE + _lon_pub) / 2)

# Valori di default globali (usati prima che il tab Domanda ne calcoli di aggiornati)
CENTRALE_LAT, CENTRALE_LON = _LAT_BAR_AZIENDE, _LON_BAR_AZIENDE


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


# Origine della proiezione locale metrica. Tenerla FISSA e' essenziale: se il
# fattore di scala dipendesse dalla media delle latitudini passate di volta in
# volta, due proiezioni fatte su insiemi diversi non sarebbero confrontabili.
# Con x,y assoluti dell'ordine di 10^6 m bastava uno scarto di 0.03% sul coseno
# per generare errori di 200 m sulle distanze (bug osservato sugli snap OSM).
_PROJ_LAT0 = 46.150
_PROJ_LON0 = 12.720


def _latlon_a_xy(lat, lon):
    """Proiezione equirettangolare locale (metri) con origine fissa su Maniago.

    Ritorna coordinate piccole (ordine dei km) riferite a (_PROJ_LAT0, _PROJ_LON0),
    coerenti tra chiamate diverse.
    """
    lat = np.asarray(lat, dtype=float)
    lon = np.asarray(lon, dtype=float)
    R = 6371000.0
    cos0 = np.cos(np.radians(_PROJ_LAT0))
    x = R * np.radians(lon - _PROJ_LON0) * cos0
    y = R * np.radians(lat - _PROJ_LAT0)
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
# Tipi di viabilita' utili al tracciato di una rete di teleriscaldamento.
# Il filtro viene applicato in Python e non nella query: un'espressione
# regolare lunga rallenta Overpass e in certi casi fa scadere il timeout,
# restituendo una risposta vuota.
STRADE_UTILI = {
    "motorway", "trunk", "primary", "secondary", "tertiary", "unclassified",
    "residential", "service", "living_street", "pedestrian", "road", "track",
    "motorway_link", "trunk_link", "primary_link", "secondary_link",
    "tertiary_link",
}


def _bbox(centro_lat, centro_lon, raggio_km):
    """Riquadro (sud, ovest, nord, est) attorno al centro.

    Il grado di longitudine vale 111 km solo all'equatore: a 46 N sono ~77 km,
    quindi senza il coseno il riquadro risulterebbe schiacciato in est-ovest.
    """
    d_lat = raggio_km / 111.0
    d_lon = raggio_km / (111.0 * np.cos(np.radians(centro_lat)))
    return (centro_lat - d_lat, centro_lon - d_lon,
            centro_lat + d_lat, centro_lon + d_lon)


def _osm_da_overpass(bb, timeout=60):
    """Scarica da Overpass. Ritorna (dict, None) oppure (None, errore)."""
    import requests
    # Query volutamente semplice: si chiedono tutte le highway del riquadro e
    # si filtra dopo. Le espressioni regolari lunghe appesantiscono il server.
    q = (f"[out:json][timeout:{timeout}];"
         f'(way["highway"]({bb[0]:.5f},{bb[1]:.5f},{bb[2]:.5f},{bb[3]:.5f}););'
         f"out body;>;out skel qt;")
    endpoints = [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
        "https://overpass.osm.ch/api/interpreter",
        "https://overpass.private.coffee/api/interpreter",
    ]
    ultimo = None
    for url in endpoints:
        try:
            r = requests.post(url, data={"data": q}, timeout=timeout + 30,
                              headers={"User-Agent": "TLR-Maniago/1.0"})
            if r.status_code != 200:
                ultimo = f"{url.split('//')[1].split('/')[0]}: HTTP {r.status_code}"
                continue
            js = r.json()
            if sum(1 for e in js.get("elements", []) if e.get("type") == "node") > 0:
                return js, None
            ultimo = f"{url.split('//')[1].split('/')[0]}: risposta senza nodi"
        except Exception as e:
            ultimo = f"{url.split('//')[1].split('/')[0]}: {type(e).__name__}"
    return None, ultimo


def _osm_da_api_ufficiale(bb, timeout=90):
    """Scarica dall'API ufficiale OpenStreetMap (XML).

    E' il canale piu' affidabile quando Overpass e' sovraccarico: restituisce
    tutti gli elementi del riquadro, senza filtri. Il limite di 0,25 gradi
    quadrati e' ampiamente rispettato dall'area di Maniago (~0,004).
    Il risultato viene convertito nella stessa struttura di Overpass.
    """
    import requests
    import xml.etree.ElementTree as ET
    url = (f"https://api.openstreetmap.org/api/0.6/map?"
           f"bbox={bb[1]:.5f},{bb[0]:.5f},{bb[3]:.5f},{bb[2]:.5f}")
    try:
        r = requests.get(url, timeout=timeout,
                         headers={"User-Agent": "TLR-Maniago/1.0"})
        if r.status_code != 200:
            return None, f"api.openstreetmap.org: HTTP {r.status_code}"
        root = ET.fromstring(r.content)
    except Exception as e:
        return None, f"api.openstreetmap.org: {type(e).__name__}: {str(e)[:80]}"

    elementi = []
    for nd in root.findall("node"):
        elementi.append({"type": "node", "id": int(nd.get("id")),
                         "lat": float(nd.get("lat")), "lon": float(nd.get("lon"))})
    for w in root.findall("way"):
        tags = {t.get("k"): t.get("v") for t in w.findall("tag")}
        if "highway" not in tags:
            continue
        elementi.append({"type": "way", "id": int(w.get("id")),
                         "nodes": [int(n.get("ref")) for n in w.findall("nd")],
                         "tags": tags})
    if not any(e["type"] == "way" for e in elementi):
        return None, "api.openstreetmap.org: nessuna strada nel riquadro"
    return {"elements": elementi}, None


def _tasselli(bb, n):
    """Divide il riquadro (s, o, n, e) in n x n tasselli."""
    s_, o_, n_, e_ = bb
    dl, dg = (n_ - s_) / n, (e_ - o_) / n
    return [(s_ + i * dl, o_ + j * dg, s_ + (i + 1) * dl, o_ + (j + 1) * dg)
            for i in range(n) for j in range(n)]


def _unisci_osm(parti):
    """Unisce le risposte di piu' tasselli eliminando nodi e strade doppi."""
    visti, el = set(), []
    for d in parti:
        for e in d.get("elements", []):
            k = (e.get("type"), e.get("id"))
            if k in visti:
                continue
            visti.add(k)
            el.append(e)
    return {"elements": el}


def _osm_download_strade(bb, timeout=120):
    """Rete stradale del riquadro bb = (sud, ovest, nord, est).

    Ordine dei tentativi:
      1. Overpass sull'intero riquadro;
      2. Overpass a tasselli 2 x 2 (richieste piu' leggere, meno timeout);
      3. API ufficiale OSM a tasselli 3 x 3: l'API rifiuta con HTTP 400 le
         richieste oltre 50.000 nodi, e l'area di Maniago intera li supera.
    Ritorna (dict, None) se va a buon fine, (None, messaggio) altrimenti.
    """
    try:
        import requests  # noqa: F401
    except ImportError:
        return None, "modulo 'requests' non installato (pip install requests)"
    data, err1 = _osm_da_overpass(bb, timeout)
    if data is not None:
        return data, None
    parti, err2 = [], None
    for t in _tasselli(bb, 2):
        d, e = _osm_da_overpass(t, 90)
        if d is None:
            err2 = e
            break
        parti.append(d)
    if err2 is None and parti:
        return _unisci_osm(parti), None
    parti, err3 = [], None
    for t in _tasselli(bb, 3):
        d, e = _osm_da_api_ufficiale(t)
        if d is None:
            err3 = e
            break
        parti.append(d)
    if err3 is None and parti:
        return _unisci_osm(parti), None
    return None, f"Overpass ({err1}); Overpass a tasselli ({err2}); API OSM a tasselli ({err3})"


@st.cache_data(show_spinner="Scarico la rete stradale di Maniago (una volta sola)...")
def carica_grafo_strade(centro_lat=CENTRALE_LAT, centro_lon=CENTRALE_LON,
                        raggio_km=1.5, cache_file="maniago_strade_cache.json"):
    """Carica il grafo stradale OSM. Usa cache locale su file se presente.

    Ritorna (grafo_dict, None) se ok oppure (None, messaggio_errore).
    """
    if not _HAS_SCIPY:
        return None, "scipy non disponibile in questo processo streamlit"

    def _conta_nodi(d):
        if not isinstance(d, dict):
            return 0
        return sum(1 for e in d.get("elements", []) if e.get("type") == "node")

    # La cache viene riletta solo se contiene davvero dei nodi: se un tentativo
    # precedente ha salvato una risposta vuota (Overpass sovraccarico, limite di
    # richieste raggiunto), il file resterebbe corrotto e ogni avvio successivo
    # fallirebbe allo stesso modo. In quel caso si riscarica.
    # La cache registra il riquadro scaricato. Una cache senza riquadro, o con
    # un riquadro che non copre quello richiesto, viene da una versione
    # precedente (centro mobile, raggio 1,5 km): usarla lasciava fuori dal
    # grafo interi quartieri, i cui edifici risultavano irraggiungibili e
    # venivano collegati con lunghi tratti in linea d'aria.
    bb_rich = GRAFO_BBOX

    def _copre(c):
        _b = c.get("_bbox") if isinstance(c, dict) else None
        if not _b or len(_b) != 4:
            return False
        return (_b[0] <= bb_rich[0] + 1e-6 and _b[1] <= bb_rich[1] + 1e-6
                and _b[2] >= bb_rich[2] - 1e-6 and _b[3] >= bb_rich[3] - 1e-6)

    data = None
    err = None
    _vecchia = None
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                _c = json.load(f)
            if _conta_nodi(_c) > 0 and _copre(_c):
                data = _c
            elif _conta_nodi(_c) > 0:
                _vecchia = _c          # tenuta come ripiego se il download fallisce
            else:
                os.remove(cache_file)
        except Exception:
            try:
                os.remove(cache_file)
            except Exception:
                pass
            data = None

    if data is None:
        data, err = _osm_download_strade(bb_rich)
        if data is None or _conta_nodi(data) == 0:
            if _vecchia is not None:
                data = _vecchia        # meglio una mappa parziale che nessuna
            elif data is None:
                return None, err
            else:
                return None, ("Overpass ha risposto senza dati: di solito è un limite "
                              "di richieste temporaneo. Riprova fra qualche minuto.")
        else:
            data["_bbox"] = list(bb_rich)
            # si salva solo una risposta valida
            try:
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump(data, f)
            except Exception:
                pass

    # parse: nodi + strade. Il filtro sui tipi di viabilita' si applica qui e
    # non nella query, perche' un'espressione regolare lunga rallenta Overpass
    # fino a farlo scadere restituendo una risposta vuota.
    nodi = {}
    strade = []
    for el in data.get("elements", []):
        if el.get("type") == "node":
            nodi[el["id"]] = (el["lat"], el["lon"])
        elif el.get("type") == "way":
            _tags = el.get("tags") or {}
            _hw = _tags.get("highway")
            # se il tag non e' disponibile (Overpass con "out skel") si tiene
            # la strada: meglio qualche sentiero in piu' che un buco nel grafo
            if _hw is None or _hw in STRADE_UTILI:
                strade.append(el.get("nodes", []))
    if not nodi:
        return None, "risposta senza nodi: riquadro vuoto o filtro troppo stretto"
    if not strade:
        return None, "nessuna strada utile nel riquadro"

    # ------------------------------------------------------------------
    # DENSIFICAZIONE DEL GRAFO
    # OSM inserisce un nodo solo dove la geometria cambia direzione: una via
    # rettilinea di 300 m puo' avere due soli nodi. Un edificio a meta' via
    # risulterebbe a 150 m dal nodo piu vicino pur essendo a pochi metri dalla
    # carreggiata. Spezzo quindi ogni tratto lungo in segmenti da PASSO_M,
    # inserendo nodi virtuali con id negativi (non collidono con quelli OSM).
    # ------------------------------------------------------------------
    PASSO_M = 25.0
    _next_vid = -1
    strade_dense = []
    for way in strade:
        if len(way) < 2:
            continue
        nuova = [way[0]]
        for a, b in zip(way[:-1], way[1:]):
            if a not in nodi or b not in nodi:
                nuova.append(b)
                continue
            la1, lo1 = nodi[a]
            la2, lo2 = nodi[b]
            _x, _y = _latlon_a_xy(np.array([la1, la2]), np.array([lo1, lo2]))
            dist = float(np.hypot(_x[1] - _x[0], _y[1] - _y[0]))
            n_split = int(dist // PASSO_M)
            if n_split >= 1:
                for k in range(1, n_split + 1):
                    t = k / (n_split + 1.0)
                    nodi[_next_vid] = (la1 + t * (la2 - la1), lo1 + t * (lo2 - lo1))
                    nuova.append(_next_vid)
                    _next_vid -= 1
            nuova.append(b)
        strade_dense.append(nuova)
    strade = strade_dense

    # ------------------------------------------------------------------
    # COMPONENTE CONNESSA PRINCIPALE
    # Il grafo OSM contiene frammenti isolati: viabilita' interna di cortili e
    # parcheggi, strade private collegate solo da sentieri (esclusi dal filtro),
    # tratti tagliati al bordo del riquadro. Se un edificio "aggancia" il nodo
    # piu' vicino e questo sta su un frammento, il percorso verso la centrale
    # non esiste. Lo snap si fa quindi solo sui nodi della componente piu'
    # grande, che e' la rete stradale vera e propria.
    # ------------------------------------------------------------------
    _padre = {}

    def _trova(x):
        while _padre.get(x, x) != x:
            _padre[x] = _padre.get(_padre[x], _padre[x])
            x = _padre[x]
        return x

    for way in strade:
        _w = [n for n in way if n in nodi]
        for a, b in zip(_w[:-1], _w[1:]):
            ra, rb = _trova(a), _trova(b)
            if ra != rb:
                _padre[ra] = rb
    _comp = {}
    for way in strade:
        for n in way:
            if n in nodi:
                _comp.setdefault(_trova(n), set()).add(n)
    _principale = max(_comp.values(), key=len) if _comp else set(nodi.keys())
    n_frammenti = max(len(_comp) - 1, 0)

    node_ids = [i for i in nodi.keys() if i in _principale]
    _lat_nodi = np.array([nodi[i][0] for i in node_ids], dtype=float)
    _lon_nodi = np.array([nodi[i][1] for i in node_ids], dtype=float)
    _x_nodi, _y_nodi = _latlon_a_xy(_lat_nodi, _lon_nodi)
    pts = np.column_stack([_x_nodi, _y_nodi])
    kd = cKDTree(pts)
    return {"nodi": nodi, "strade": strade, "kd": kd,
            "node_ids": node_ids, "pts_xy": pts,
            "n_frammenti": n_frammenti,
            "bbox": data.get("_bbox"),
            "copre_richiesta": _copre(data)}, None


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


def steiner_con_potatura_densita(G, nodi_target, radice_nodo, mwh_per_target,
                                  soglia_mwh_per_m=1.0):
    """Costruisce l'albero di Steiner e POTA i rami la cui densita' cumulativa
    (MWh totali dei target nel sotto-ramo / metri totali del sotto-ramo) e' sotto soglia.

    Il criterio e' cumulativo: un ramo con 3 edifici piccoli oltre 200 m puo' essere
    tenuto se in totale porta abbastanza calore; un ramo con 1 solo edificio piccolo
    a 300 m e' quasi sempre potato.

    Args:
        G: grafo networkx (nodi = punti stradali, pesi = metri)
        nodi_target: lista di id nodi da servire
        radice_nodo: id nodo della sottocentrale
        mwh_per_target: dict {id_nodo: MWh/a portati da quel target}
        soglia_mwh_per_m: densita' lineare minima accettabile (default 1.0)

    Ritorna:
        archi_finali: lista (id_a, id_b, dist_m) dopo potatura
        lun_totale: metri totali dopo potatura
        target_serviti: set di id nodi che sono rimasti nell'albero
        target_esclusi: set di id nodi potati
    """
    import networkx as nx
    # 1) albero completo
    archi_full, _, _ = albero_steiner_su_strade(G, nodi_target, radice_nodo)
    # target_esclusi contiene SOLO i target potati per densita'. Quelli che il
    # grafo non riesce a raggiungere non compaiono ne' fra i serviti ne' fra gli
    # esclusi: e' il chiamante a decidere come collegarli.
    if not archi_full:
        _serv0 = {radice_nodo} & set(nodi_target)
        return [], 0.0, _serv0, set(), {}

    # 2) costruisco l'albero come grafo diretto radicato in 'radice_nodo'
    #    (BFS/DFS dalla radice sull'albero non orientato per orientarlo)
    T = nx.Graph()
    for a, b, w in archi_full:
        T.add_edge(a, b, weight=w)
    if radice_nodo not in T:
        # la radice non e' entrata: nessun target raggiungibile sul grafo
        return [], 0.0, set(), set(), {}

    parent = {radice_nodo: None}
    order = []
    stack = [radice_nodo]
    visited = {radice_nodo}
    while stack:
        u = stack.pop()
        order.append(u)
        for v in T.neighbors(u):
            if v not in visited:
                visited.add(v)
                parent[v] = u
                stack.append(v)

    target_set = set(nodi_target)

    # 3) per ogni nodo, calcolo (in ordine BFS inverso = foglie prima) il
    #    sotto-albero cumulativo: MWh totali dei target sotto di lui + lunghezza
    #    totale degli archi sotto di lui (compreso l'arco che lo collega al padre).
    sub_mwh = {u: (mwh_per_target.get(u, 0.0) if u in target_set else 0.0) for u in order}
    sub_len = {u: 0.0 for u in order}  # lunghezza rami DENTRO il sotto-albero
    children = {u: [] for u in order}
    for u in order:
        if parent[u] is not None:
            children[parent[u]].append(u)
    for u in reversed(order):
        p = parent[u]
        if p is not None:
            w_edge = T[u][p]["weight"]
            sub_mwh[p] = sub_mwh[p] + sub_mwh[u]
            sub_len[p] = sub_len[p] + sub_len[u] + w_edge

    # 4) potatura iterativa dal basso: poto sotto-alberi di foglie/rami con densita' < soglia.
    #    Ripeto finche' non ci sono piu' rami da potare (la potatura di un ramo
    #    puo' cambiare la densita' del ramo padre, che diventa piu' compatto).
    esclusi = set()
    # per ogni target escluso, il ramo che lo ha fatto escludere: lunghezza,
    # calore portato, densita' e altri target potati insieme
    info_potatura = {}
    nodi_vivi = set(order)  # nodi ancora nell'albero

    def _sub_da_zero(u):
        """ricalcola sub_mwh e sub_len su nodi_vivi partendo da u"""
        if u not in nodi_vivi:
            return 0.0, 0.0
        m = mwh_per_target.get(u, 0.0) if u in target_set else 0.0
        L = 0.0
        for c in children[u]:
            if c in nodi_vivi:
                m_c, L_c = _sub_da_zero(c)
                m += m_c
                arc = T[u][c]["weight"]
                L += L_c + arc
        return m, L

    while True:
        potati = False
        # ordina i sotto-rami dai piu' interni (foglie) verso l'alto
        for u in reversed(order):
            if u == radice_nodo or u not in nodi_vivi:
                continue
            p = parent[u]
            if p is None or p not in nodi_vivi:
                continue
            m_u, L_u = _sub_da_zero(u)
            arc_up = T[u][p]["weight"]
            L_tot = L_u + arc_up
            if L_tot < 10.0:  # rami micro: tieni
                continue
            dens = m_u / L_tot if L_tot > 0 else 0.0
            if dens < soglia_mwh_per_m:
                # poto: rimuovo u e tutto il sotto-albero
                stack = [u]
                _nel_ramo = []
                while stack:
                    x = stack.pop()
                    if x in target_set:
                        esclusi.add(x)
                        _nel_ramo.append(x)
                    nodi_vivi.discard(x)
                    stack.extend([c for c in children[x] if c in nodi_vivi])
                for x in _nel_ramo:
                    info_potatura[x] = {"lunghezza_m": float(L_tot), "mwh": float(m_u),
                                        "densita": float(dens), "nodi_ramo": list(_nel_ramo)}
                potati = True
                break  # ripeto il ciclo dall'inizio
        if not potati:
            break

    keep = nodi_vivi

    # 5) ricostruisco gli archi finali: solo quelli tra nodi tenuti
    archi_finali = []
    for u in order:
        if u == radice_nodo:
            continue
        if u in keep:
            p = parent[u]
            if p in keep:
                w = T[u][p]["weight"]
                archi_finali.append((p, u, w))

    lun_tot = float(sum(w for _, _, w in archi_finali))
    target_serviti = (target_set & keep)
    return archi_finali, lun_tot, target_serviti, esclusi, info_potatura


def archi_a_coords(archi_nodi, strade_data):
    """Converte lista di archi (id_a, id_b, dist) in ((lat1,lon1),(lat2,lon2),dist)."""
    nodi = strade_data["nodi"]
    out = []
    for a, b, d in archi_nodi:
        if a in nodi and b in nodi:
            out.append(((nodi[a][0], nodi[a][1]), (nodi[b][0], nodi[b][1]), d))
    return out


def buffer_su_rete(G, nodi_tubo, nodi_snap, dist_snap, raggio_m):
    """Lunghezza di allaccio di ciascun edificio misurata LUNGO LE STRADE.

    Il buffer geometrico (distanza in linea d'aria dalla polilinea del tubo)
    sbaglia dove il tracciato compie salti rettilinei su aree non mappate:
    quella retta attraversa campi e cortili, quindi esclude gli edifici che
    stanno lungo la strada vera e includerebbe case irraggiungibili.
    Qui invece si misura il tubo che servirebbe davvero:

        allaccio = tratto edificio->strada  +  percorso stradale fino al tubo

    Un solo Dijkstra multi-sorgente dal tubo verso tutta la rete, quindi il
    costo non cresce col numero di edifici.

    Args:
        G: grafo stradale (pesi in metri)
        nodi_tubo: insieme dei nodi gia' attraversati dalla condotta
        nodi_snap: per ogni edificio, il nodo stradale su cui e' agganciato
        dist_snap: per ogni edificio, i metri tra edificio e quel nodo
        raggio_m: soglia di allaccio

    Ritorna: array con la lunghezza di allaccio (inf se irraggiungibile).
    """
    import networkx as nx
    if not nodi_tubo or len(nodi_snap) == 0:
        return np.full(len(nodi_snap), np.inf)
    sorgenti = set(n for n in nodi_tubo if n in G)
    if not sorgenti:
        return np.full(len(nodi_snap), np.inf)
    dist_da_tubo = nx.multi_source_dijkstra_path_length(
        G, sources=sorgenti, cutoff=float(raggio_m), weight="weight")
    out = np.full(len(nodi_snap), np.inf)
    for i, (n, d_s) in enumerate(zip(nodi_snap, dist_snap)):
        d_rete = dist_da_tubo.get(n)
        if d_rete is not None:
            out[i] = float(d_s) + float(d_rete)
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


# =============================================================================
# DIMENSIONAMENTO IDRAULICO DELLE CONDOTTE
# =============================================================================
# Serie DN commerciale per tubazioni preisolate di teleriscaldamento, con
# diametro interno indicativo (mm) del tubo di servizio in acciaio.
SERIE_DN = [
    (20, 21.7), (25, 28.5), (32, 37.2), (40, 43.1), (50, 54.5),
    (65, 70.3), (80, 82.5), (100, 107.1), (125, 132.5), (150, 159.3),
    (200, 210.1), (250, 263.0), (300, 312.7), (350, 344.4), (400, 393.8),
    (450, 444.6), (500, 495.4), (600, 595.8),
]
CP_ACQUA_KJ_KG_K = 4.186
RHO_ACQUA_KG_M3 = 977.0        # ~70 C, valore medio mandata/ritorno


def dimensiona_dn(potenza_kw, dT_K, v_max_m_s=1.5):
    """Diametro nominale della condotta a partire dalla potenza trasportata.

    Q = m_punto * cp * dT  ->  portata massica
    A = V_punto / v        ->  sezione, quindi diametro

    Args:
        potenza_kw: potenza termica di picco che attraversa il tratto (kW)
        dT_K: salto termico mandata-ritorno (K)
        v_max_m_s: velocita' massima ammessa. Riferimenti QM/Verenum:
                   0,5-1,0 allacci d'utenza; 1,0-2,0 distribuzione;
                   2,0-3,0 dorsali di trasporto.

    Ritorna: (DN, diametro_interno_mm, velocita_effettiva_m_s, portata_m3_h)
    Se la potenza e' nulla ritorna (0, 0, 0, 0).
    """
    if potenza_kw <= 0 or dT_K <= 0:
        return 0, 0.0, 0.0, 0.0
    m_punto = potenza_kw / (CP_ACQUA_KJ_KG_K * dT_K)          # kg/s
    v_punto = m_punto / RHO_ACQUA_KG_M3                        # m3/s
    area_min = v_punto / v_max_m_s                             # m2
    d_min_mm = np.sqrt(4.0 * area_min / np.pi) * 1000.0
    for dn, d_int in SERIE_DN:
        if d_int >= d_min_mm:
            area_reale = np.pi * (d_int / 1000.0) ** 2 / 4.0
            return dn, d_int, v_punto / area_reale, v_punto * 3600.0
    dn, d_int = SERIE_DN[-1]
    area_reale = np.pi * (d_int / 1000.0) ** 2 / 4.0
    return dn, d_int, v_punto / area_reale, v_punto * 3600.0


# =============================================================================
# SCHEMA DI MASSIMA DELL'IMPIANTO
# =============================================================================
def schema_impianto_svg(cfg):
    """Schema a blocchi dell'impianto dimensionato, in SVG.

    Riproduce l'architettura a cascata: collettore dei flussi di scarto,
    tre accumuli ai rispettivi livelli termici, le due pompe di calore con
    evaporatore e condensatore, l'eventuale caldaia di supporto e la
    mandata/ritorno verso la rete. Le taglie riportate sono quelle
    effettivamente impostate nel dimensionamento.

    cfg: dizionario con le chiavi usate sotto (tutte opzionali salvo le
    temperature). Ritorna una stringa SVG.
    """
    T_mand = cfg.get("T_mandata", 80)
    T_rit = cfg.get("T_ritorno", 50)
    T_int = cfg.get("T_int", 50)
    P_alta = cfg.get("P_alta_kw", 0)
    P_bassa = cfg.get("P_bassa_kw", 0)
    P_bk = cfg.get("P_backup_kw", 0)
    tipo_bk = cfg.get("backup_tipo", "gas")
    V_hot = cfg.get("V_hot", 0)
    V_int = cfg.get("V_int", 0)
    V_low = cfg.get("V_low", 0)
    E_hot = cfg.get("E_hot", 0.0)
    E_alta = cfg.get("E_alta", 0.0)
    E_bassa = cfg.get("E_bassa", 0.0)
    E_bk = cfg.get("E_backup", 0.0)
    E_ground = cfg.get("E_ground", 0.0)
    cop_a = cfg.get("cop_alta", 0.0)
    cop_b = cfg.get("cop_bassa", 0.0)
    dn = cfg.get("dn_dorsale", 0)
    flussi_caldo = cfg.get("flussi_caldo", [])
    flussi_int = cfg.get("flussi_int", [])
    flussi_basso = cfg.get("flussi_basso", [])
    solare_on = cfg.get("solare_on", False)
    is_hp = (P_bassa > 0)

    C_ACC = "#2D7DC0"
    C_CALDO = "#C0522D"
    C_HP = "#22C3DD"
    C_HPB = "#B57EDC"
    C_BK = "#FF9F1C"
    C_TXT = "#E8E8E8"
    C_LIN = "#9AA0A6"
    C_SOL = "#F5C518"

    p = []
    a = p.append
    a('<svg viewBox="0 0 1180 520" xmlns="http://www.w3.org/2000/svg" '
      'style="background:#111418;font-family:system-ui,sans-serif">')
    a('<defs><marker id="fr" markerWidth="9" markerHeight="7" refX="8" refY="3.5" '
      f'orient="auto"><polygon points="0 0, 9 3.5, 0 7" fill="{C_LIN}"/></marker>'
      '<marker id="frc" markerWidth="9" markerHeight="7" refX="8" refY="3.5" '
      f'orient="auto"><polygon points="0 0, 9 3.5, 0 7" fill="{C_CALDO}"/></marker>'
      '</defs>')

    def txt(x, y, s, size=11, col=C_TXT, anchor="middle", weight="normal"):
        s = (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
        a(f'<text x="{x}" y="{y}" font-size="{size}" fill="{col}" '
          f'text-anchor="{anchor}" font-weight="{weight}">{s}</text>')

    def cilindro(x, y, w, h, col, titolo, sotto1="", sotto2=""):
        """Accumulo disegnato come serbatoio cilindrico."""
        ry = 11
        a(f'<path d="M{x} {y+ry} a{w/2} {ry} 0 0 1 {w} 0 v{h} a{w/2} {ry} 0 0 1 -{w} 0 z" '
          f'fill="{col}" fill-opacity="0.30" stroke="{col}" stroke-width="2"/>')
        a(f'<ellipse cx="{x+w/2}" cy="{y+ry}" rx="{w/2}" ry="{ry}" '
          f'fill="{col}" fill-opacity="0.55" stroke="{col}" stroke-width="2"/>')
        txt(x + w / 2, y + ry + 26, titolo, 12, "#FFFFFF", weight="bold")
        if sotto1:
            txt(x + w / 2, y + ry + 45, sotto1, 11)
        if sotto2:
            txt(x + w / 2, y + ry + 62, sotto2, 10, C_LIN)

    def blocco(x, y, w, h, col, t1, t2="", t3=""):
        a(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" '
          f'fill="{col}" fill-opacity="0.22" stroke="{col}" stroke-width="2"/>')
        txt(x + w / 2, y + 20, t1, 12, "#FFFFFF", weight="bold")
        if t2:
            txt(x + w / 2, y + 38, t2, 11)
        if t3:
            txt(x + w / 2, y + 54, t3, 10, C_LIN)

    def linea(x1, y1, x2, y2, col=C_LIN, w=2, tratteggio=None, freccia=True):
        # la freccia segue sempre il verso x1->x2, cosi' il flusso disegnato
        # coincide con quello fisico anche nei tratti da destra a sinistra
        d = f' stroke-dasharray="{tratteggio}"' if tratteggio else ""
        m = ' marker-end="url(#fr)"' if freccia and col == C_LIN else (
            ' marker-end="url(#frc)"' if freccia else "")
        a(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{col}" '
          f'stroke-width="{w}"{d}{m}/>')

    # ---- intestazione
    txt(590, 26, "Schema di massima dell'impianto", 16, "#FFFFFF", weight="bold")
    txt(590, 46, f"mandata {T_mand} °C · ritorno {T_rit} °C · anello intermedio {T_int} °C",
        11, C_LIN)

    # ---- colonna sinistra: flussi in ingresso, allineati a sinistra
    #      con un riquadro di sfondo per staccarli dalla mappa dei blocchi
    _x0 = 16
    a(f'<rect x="{_x0 - 6}" y="66" width="200" height="250" rx="6" '
      f'fill="#1A1F26" stroke="#333B45" stroke-width="1"/>')
    txt(_x0, 86, "FLUSSI DI SCARTO", 11, "#FFFFFF", anchor="start", weight="bold")
    _y = 108
    for _lbl, _lst, _col in [("uso diretto", flussi_caldo[:3], C_CALDO),
                             ("anello intermedio", flussi_int[:4], C_HP),
                             ("anello basso", flussi_basso[:4], C_HPB)]:
        if not _lst:
            continue
        txt(_x0, _y, _lbl, 9, _col, anchor="start", weight="bold")
        _y += 15
        for nome, temp in _lst:
            a(f'<circle cx="{_x0 + 4}" cy="{_y - 4}" r="3" fill="{_col}"/>')
            txt(_x0 + 13, _y, f"{nome[:22]}", 9.5, C_TXT, anchor="start")
            txt(188, _y, f"{temp:.0f}°C", 9.5, _col, anchor="end")
            _y += 15
        _y += 6
    if solare_on:
        a(f'<circle cx="{_x0 + 4}" cy="{_y - 4}" r="3" fill="{C_SOL}"/>')
        txt(_x0 + 13, _y, "solare termico", 9.5, C_SOL, anchor="start")

    # ---- accumulo BASSO
    cilindro(150, 300, 130, 90, C_HPB, "Accumulo BASSO",
             f"{V_low:.0f} m³" if V_low else "assente",
             f"< {T_int} °C")
    linea(200, 345, 146, 345)

    # ---- ground loop
    if is_hp:
        a(f'<rect x="150" y="440" width="130" height="46" rx="6" fill="#8C6D46" '
          f'fill-opacity="0.22" stroke="#8C6D46" stroke-width="2"/>')
        txt(215, 460, "Ground loop", 11, "#FFFFFF", weight="bold")
        txt(215, 477, f"{E_ground:,.0f} MWh/a".replace(",", "."), 10, C_LIN)
        linea(215, 438, 215, 400, "#8C6D46")

    # ---- HP bassa T
    if is_hp:
        blocco(330, 310, 118, 70, C_HPB, "HP bassa T",
               f"{P_bassa:.0f} kW",
               f"COP {cop_b:.1f} · {E_bassa:,.0f} MWh/a".replace(",", "."))
        linea(282, 345, 328, 345)
        a(f'<path d="M448 345 H 500 V 300" stroke="{C_LIN}" stroke-width="2" '
          f'fill="none" marker-end="url(#fr)"/>')
    else:
        txt(389, 340, "HP bassa T", 11, C_LIN)
        txt(389, 357, "non prevista", 10, C_LIN)
        a(f'<line x1="282" y1="345" x2="470" y2="345" stroke="{C_LIN}" '
          f'stroke-width="1.5" stroke-dasharray="4 4" opacity="0.4"/>')

    # ---- accumulo INTERMEDIO
    cilindro(500, 190, 140, 100, C_ACC, "Accumulo INTERMEDIO",
             f"{V_int:.0f} m³" if V_int else "assente",
             f"{T_int} °C")
    linea(200, 232, 498, 232)
    txt(300, 224, "flussi tra " + f"{T_int} e {T_mand} °C", 10, C_HP, anchor="middle")

    # ---- HP alta T
    blocco(700, 200, 118, 74, C_HP, "HP alta T",
           f"{P_alta:.0f} kW",
           f"COP {cop_a:.1f} · {E_alta:,.0f} MWh/a".replace(",", "."))
    linea(642, 237, 698, 237)
    txt(670, 229, "evap.", 9, C_LIN)
    linea(818, 237, 880, 237)
    txt(850, 229, "cond.", 9, C_LIN)

    # ---- caldaia di supporto
    if not is_hp and P_bk > 0:
        blocco(700, 330, 118, 74, C_BK, f"Caldaia {tipo_bk}",
               f"{P_bk:.0f} kW",
               f"{E_bk:,.0f} MWh/a".replace(",", "."))
        linea(818, 367, 940, 367)
        linea(940, 367, 940, 300)

    # ---- accumulo CALDO
    cilindro(880, 150, 140, 110, C_CALDO, "Accumulo CALDO",
             f"{V_hot:.0f} m³" if V_hot else "assente",
             f"{T_mand} °C")
    # uso diretto dello scarto sopra mandata
    if E_hot > 0:
        a(f'<path d="M200 96 H 950 V 148" stroke="{C_CALDO}" stroke-width="2.5" '
          f'fill="none" marker-end="url(#frc)"/>')
        txt(560, 88, f"uso diretto: scarto ≥ {T_mand} °C  ·  "
                      f"{E_hot:,.0f} MWh/a".replace(",", "."), 11, C_CALDO)

    # ---- mandata e ritorno rete
    a(f'<path d="M1020 215 H 1128" stroke="{C_CALDO}" stroke-width="5" '
      f'fill="none" marker-end="url(#frc)"/>')
    txt(1074, 200, f"mandata {T_mand} °C", 10, C_CALDO)
    if dn:
        txt(1074, 240, f"DN {dn}", 12, "#FFFFFF", weight="bold")
    # il ritorno rientra sull'accumulo intermedio (recupero del residuo termico)
    a(f'<path d="M1125 445 H 570 V 302" stroke="#2D7DC0" stroke-width="4" fill="none" '
      f'marker-end="url(#fr)"/>')
    txt(850, 437, f"ritorno dalla rete {T_rit} °C", 10, "#2D7DC0")

    a('</svg>')
    return "\n".join(p)


# =============================================================================
# CIRCUITO GEOTERMICO / SORGENTE DELLA POMPA A BASSA TEMPERATURA
# =============================================================================
# Il terreno non e' una sorgente illimitata: ogni kW estratto richiede una
# quantita' precisa di scambio, e a potenze da teleriscaldamento le opere
# diventano rilevanti quanto la centrale. 1.500 kW estratti significano
# 300-400 pozzi da 100 m su circa due ettari, oppure sei ettari di terreno
# libero con le serpentine.
SORGENTI_BASSA_T = {
    "sonde verticali": {
        "unita": "m di perforazione",
        "resa_min": 30.0, "resa_tip": 45.0, "resa_max": 60.0,   # W per metro
        "costo_min": 35.0, "costo_tip": 60.0, "costo_max": 90.0,  # EUR/m
        "prof_sonda_m": 100.0,
        "passo_m": 7.0,          # interasse tipico fra le sonde
        "note": ("Resa 30-60 W/m secondo la conducibilita' del terreno e la falda. "
                 "Nell'alta pianura friulana, con ghiaie sature, si sta nella parte "
                 "alta della forchetta. Richiede indagine geognostica e, sopra i "
                 "certi volumi, autorizzazione allo scarico termico."),
    },
    "serpentine orizzontali": {
        "unita": "m² di terreno",
        "resa_min": 15.0, "resa_tip": 25.0, "resa_max": 35.0,   # W per m2
        "costo_min": 12.0, "costo_tip": 22.0, "costo_max": 35.0,  # EUR/m2
        "prof_posa_m": 1.5,
        "note": ("Posa a 1,5 m di profondita'. Il terreno sopra le serpentine resta "
                 "libero solo per prato o coltivazioni superficiali: niente edifici "
                 "ne' alberi. La resa cala molto in terreni asciutti."),
    },
    "acqua di falda": {
        "unita": "l/s di portata",
        "dt_k": 4.0,             # salto termico ammesso sul prelievo
        # il costo si conta a pozzo, non a portata: un pozzo attrezzato in
        # alta pianura rende 30-80 l/s e costa fra 40 e 120 mila euro fra
        # perforazione, colonna, elettropompa, filtri e opere di resa
        "costo_min": 40000.0, "costo_tip": 75000.0, "costo_max": 130000.0,
        "resa_min": 25.0, "resa_tip": 50.0, "resa_max": 80.0,   # l/s per pozzo
        "note": ("Soluzione piu' compatta ed efficiente dove la falda e' ricca, come "
                 "nell'alta pianura pordenonese. Richiede concessione di derivazione "
                 "e pozzo di resa: il vincolo non e' la superficie ma il salto "
                 "termico ammesso allo scarico e la disponibilita' idrica."),
    },
}


def dimensiona_sorgente_bassa_t(potenza_kw, tipo="sonde verticali", resa=None,
                                costo_unitario=None):
    """Opere necessarie per estrarre una data potenza dalla sorgente fredda.

    Ritorna un dizionario con la grandezza dimensionante (metri di perforazione,
    superficie o portata), il numero di pozzi dove ha senso, la superficie
    complessivamente impegnata e il costo.
    """
    p = SORGENTI_BASSA_T.get(tipo, SORGENTI_BASSA_T["sonde verticali"])
    out = {"tipo": tipo, "potenza_kw": float(potenza_kw), "note": p["note"]}
    if potenza_kw <= 0:
        return {**out, "quantita": 0.0, "unita": p["unita"], "n_pozzi": 0,
                "superficie_m2": 0.0, "costo": 0.0, "costo_unitario": 0.0}
    W = float(potenza_kw) * 1000.0

    if tipo == "acqua di falda":
        # Q = m_punto * cp * dT  ->  portata necessaria al prelievo
        dt = p["dt_k"]
        cu = float(costo_unitario if costo_unitario is not None else p["costo_tip"])
        resa_pozzo = float(resa if resa is not None else p["resa_tip"])   # l/s
        m_punto = float(potenza_kw) / (CP_ACQUA_KJ_KG_K * dt)             # kg/s
        portata_ls = m_punto / 1000.0 * 1000.0                            # l/s
        n_pozzi = int(np.ceil(portata_ls / max(resa_pozzo, 1e-6)))
        # ai pozzi di presa si aggiunge sempre almeno un pozzo di resa
        n_tot = n_pozzi + max(1, n_pozzi // 2)
        return {**out, "quantita": portata_ls, "unita": p["unita"],
                "n_pozzi": n_tot, "superficie_m2": n_tot * 150.0,
                "costo": n_tot * cu, "costo_unitario": cu, "dt_k": dt,
                "resa": resa_pozzo,
                "portata_m3h": portata_ls * 3.6}

    r = float(resa if resa is not None else p["resa_tip"])
    cu = float(costo_unitario if costo_unitario is not None else p["costo_tip"])
    q = W / r                      # metri di sonda oppure m2 di terreno
    if tipo == "sonde verticali":
        n_pozzi = int(np.ceil(q / p["prof_sonda_m"]))
        sup = n_pozzi * p["passo_m"] ** 2
    else:
        n_pozzi = 0
        sup = q
    return {**out, "quantita": q, "unita": p["unita"], "n_pozzi": n_pozzi,
            "superficie_m2": sup, "costo": q * cu, "costo_unitario": cu, "resa": r}


def costo_condotta_eur_m(dn, costo_scavo=150.0, fattore=1.0):
    """Costo al metro di condotta preisolata posata, per diametro nominale.

    La relazione col diametro non e' proporzionale: una quota rilevante del
    costo e' scavo, letto di posa, rinterro e ripristino, che dipendono poco
    dal tubo. Sui piccoli diametri lo scavo arriva a pesare oltre l'80 %,
    quindi un ramo DN40 non costa un quarto di una dorsale DN150 ma circa la
    meta'. Usare un costo unico per tutta la rete sovrastima quindi i rami
    secondari e sottostima le dorsali.

    Args:
        dn: diametro nominale
        costo_scavo: quota indipendente dal diametro (EUR/m)
        fattore: moltiplicatore sulla sola quota di fornitura, per adeguare
            i prezzi al contesto o al momento di mercato

    Riferimento: prezzari regionali per reti di teleriscaldamento preisolate
    in area urbana, da verificare con offerte reali in fase di progetto.
    """
    # quota di sola fornitura e montaggio della tubazione preisolata
    _dn_rif = [20, 25, 32, 40, 50, 65, 80, 100, 125, 150, 200, 250, 300, 400, 500]
    _forn = [25, 30, 50, 75, 105, 150, 195, 260, 340, 430, 610, 800, 1000, 1450, 1950]
    d = float(dn) if dn else 20.0
    forn = float(np.interp(d, _dn_rif, _forn))
    return float(costo_scavo) + forn * float(fattore)


def potenza_da_energia(mwh_anno, ore_equivalenti=1900.0, f_contemporaneita=1.0):
    """Potenza di picco stimata (kW) da energia annua (MWh).

    ore_equivalenti: ore di funzionamento a pieno carico. Per il riscaldamento
    residenziale in clima alpino/prealpino 1.700-2.200 h/a e' il campo tipico.
    """
    if ore_equivalenti <= 0:
        return 0.0
    return mwh_anno * 1000.0 / ore_equivalenti * f_contemporaneita


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

    # --- STRATIFICAZIONE DELL'ANELLO INTERMEDIO ---
    # Un serbatoio reale non mescola: l'acqua piu' calda galleggia e viene
    # prelevata per prima. Suddividendo anche il livello intermedio in strati
    # da 5 K, l'evaporatore della HP alta T pesca dallo strato piu' caldo
    # disponibile invece che da una media, con un COP piu' realistico.
    edges_i = np.arange(float(T_int), float(mandata) + 5.0, 5.0)
    if len(edges_i) < 2:
        edges_i = np.array([float(T_int), float(mandata)])
    bin_T_int = (edges_i[:-1] + edges_i[1:]) / 2.0
    Ki = len(bin_T_int)
    im = o[(o["T"] >= T_int) & (o["T"] < mandata)].copy()
    if im.empty:
        q_int_bins = np.zeros((len(idx_h), Ki))
    else:
        im["bin"] = np.clip(np.digitize(im["T"].values, edges_i) - 1, 0, Ki - 1)
        pv = im.pivot_table(index="datetime", columns="bin", values="MWh",
                            aggfunc="sum", observed=False)
        pv = pv.reindex(index=idx_h, columns=range(Ki), fill_value=0.0).fillna(0.0)
        q_int_bins = pv.values

    return (hot.values, intm.values, q_low.values, q_low_bins, bin_T,
            q_int_bins, bin_T_int)


# =============================================================================
# P7 - DISPATCH A CASCATA CON MERIT ORDER
# =============================================================================
def utilizzo_per_azienda(off_df, idx_h, mandata, T_int, sim, dom_arr):
    """Quanto del calore offerto da ciascuna azienda viene davvero valorizzato.

    Il dispatch aggrega i flussi per livello termico e non distingue piu' la
    provenienza: dentro un livello il calore e' indistinguibile. La quota persa
    su ogni livello viene quindi ripartita fra le aziende in proporzione al loro
    contributo su quel livello IN QUELLA ORA, il che rende l'attribuzione esatta
    e non una media annua.

    Ritorna un DataFrame per azienda con: energia offerta, utilizzata, scartata,
    quota di utilizzo, ore in cui il flusso e' disponibile e ore in cui serve
    davvero. Un flusso disponibile solo quando la domanda e' bassa vale poco,
    per quanto grande sia sulla carta.
    """
    o = off_df[off_df["MWh"] > 0].copy()
    if o.empty:
        return pd.DataFrame(columns=["azienda", "offerta_mwh", "utilizzata_mwh",
                                     "scartata_mwh", "quota_utilizzo_pct",
                                     "ore_disponibile", "ore_utile", "livello"])
    o["T"] = o["T_disponibile"]
    o["livello"] = np.where(o["T"] >= mandata, "caldo",
                            np.where(o["T"] >= T_int, "intermedio", "basso"))

    perso = {"caldo": np.asarray(sim.get("perso_hot", np.zeros(len(idx_h)))),
             "intermedio": np.asarray(sim.get("perso_int", np.zeros(len(idx_h)))),
             "basso": np.asarray(sim.get("perso_low", np.zeros(len(idx_h))))}
    dom_pos = np.asarray(dom_arr) > 1e-9

    righe = []
    for az, g_az in o.groupby("azienda"):
        off_tot = float(g_az["MWh"].sum())
        scartata = 0.0
        for liv, g_liv in g_az.groupby("livello"):
            # serie oraria dell'azienda su questo livello
            s_az = g_liv.groupby("datetime")["MWh"].sum().reindex(idx_h, fill_value=0.0).values
            # totale offerto sul livello da TUTTE le aziende, ora per ora
            s_tot = (o[o["livello"] == liv].groupby("datetime")["MWh"].sum()
                     .reindex(idx_h, fill_value=0.0).values)
            with np.errstate(divide="ignore", invalid="ignore"):
                quota = np.where(s_tot > 1e-12, s_az / s_tot, 0.0)
            scartata += float((perso[liv] * quota).sum())
        scartata = min(scartata, off_tot)
        utilizzata = off_tot - scartata
        s_az_tot = g_az.groupby("datetime")["MWh"].sum().reindex(idx_h, fill_value=0.0).values
        disponibile = s_az_tot > 1e-9
        righe.append({
            "azienda": az,
            "offerta_mwh": round(off_tot, 1),
            "utilizzata_mwh": round(utilizzata, 1),
            "scartata_mwh": round(scartata, 1),
            "quota_utilizzo_pct": round(utilizzata / off_tot * 100, 1) if off_tot > 0 else 0.0,
            "ore_disponibile": int(disponibile.sum()),
            "ore_utile": int((disponibile & dom_pos).sum()),
            "livello": ", ".join(sorted(g_az["livello"].unique())),
        })
    return pd.DataFrame(righe).sort_values("utilizzata_mwh", ascending=False)


# -----------------------------------------------------------------------------
# PREZZO DEL CALORE DI SCARTO CON LA SCALA EXERGETICA
# -----------------------------------------------------------------------------
# PSV medio mensile (EUR/Smc, da gennaio a dicembre): media del PSV day ahead
# pubblicata da ARERA per la componente materia prima dei clienti vulnerabili
# (raccolta su billding.it; gen-apr 2024 verificati con la Camera di Commercio
# di Genova). Conversione con il PCS convenzionale 0,03852 GJ/Smc = 10,70 kWh/Smc.
# "Ultimi 12 mesi" = ott-dic 2025 + gen-set 2026, rimessi in ordine di calendario.
PCS_MWH_PER_SMC = 0.010700
PSV_SERIE_EUR_SMC = {
    "2024": [0.334, 0.298, 0.307, 0.326, 0.353, 0.386,
             0.379, 0.434, 0.415, 0.437, 0.483, 0.509],
    "2025": [0.534, 0.566, 0.455, 0.402, 0.403, 0.419,
             0.392, 0.381, 0.373, 0.354, 0.349, 0.328],
    "Ultimi 12 mesi (ott 2025 - set 2026)": [0.404, 0.377, 0.558, 0.492, 0.502, 0.505,
                                             0.607, 0.686, 0.843, 0.354, 0.349, 0.328],
}
PSV_SERIE_EUR_MWH = {k: np.array(v) / PCS_MWH_PER_SMC for k, v in PSV_SERIE_EUR_SMC.items()}
# Fattore di emissione del gas naturale riferito al PCS, coerente con il PSV in
# EUR/MWh: 1,96 kg CO2/Smc / 10,70 kWh/Smc = 0,183 t CO2/MWh. Serve a tradurre il
# prezzo ETS2 (edifici, operativo dal 2028) in EUR per MWh di gas.
EF_GAS_T_MWH_PCS = 0.00196 / PCS_MWH_PER_SMC


def formula_scarto_da_sessione():
    """(a, b) in frazione se in Offerta e' scelta la formula su PSV, altrimenti None."""
    if str(st.session_state.get("off_metodo_prezzo", "")).startswith("Formula"):
        return (float(st.session_state.get("off_formula_a", 20.0)) / 100.0,
                float(st.session_state.get("off_formula_b", 15.0)) / 100.0)
    return None


def exergia_scala(T_c, T0_c):
    """Exergia (per unita' di massa e di c_p, in K) per portare il fluido da T0 a T.

    ex = (T - T0) - T0 ln(T / T0): e' l'area fra la curva T-s del fluido e la
    retta T0. Sotto T0 vale zero (un calore piu' freddo dell'ambiente non ha
    qualita' utile per riscaldare).
    """
    T = np.asarray(T_c, dtype=float) + 273.15
    T0 = np.asarray(T0_c, dtype=float) + 273.15
    T = np.maximum(T, T0)
    return (T - T0) - T0 * np.log(T / T0)


def prezzo_scarto_exergetico(off_df, idx_h, sim, T0_h, prezzo_el_h, mandata, T_int,
                             psv_mese, spread, eta_caldaia, sconto, quota_fissa,
                             hp_bassa_attiva, ets2=0.0, caldaia_evitata=0.0,
                             formula_psv=None):
    """Prezzo del calore di scarto per azienda con la scala exergetica T0 -> mandata.

    Regola (concordata):
      - la scala T0 -> T_mandata serve SOLO a dividere il valore. Lo scarto che
        arriva a T_k "porta" il fluido da T0 a T_k: il suo peso e'
        w = ex(T0->T_k) / ex(T0->T_mandata), al massimo 1, con T0 orario;
      - le QUANTITA' vere (MWh ceduti, elettricita', COP) vengono dal dispatch;
      - il valore attribuito allo scarto si divide per i MWh realmente ceduti.

    Valore di riferimento: costo del calore a gas per l'utente,
    C_gas = (PSV mensile + spread + ETS2 x fattore di emissione) / rendimento
    caldaia + costi evitati della caldaia (manutenzione e sostituzione),
    scontato del target:
    P_target = (1 - sconto) * C_gas.

    Valore attribuito allo scarto:
      - uso diretto (scarto >= mandata): P_target * q_diretto (peso 1), ora per ora;
      - via pompe di calore, mese per mese: P_target * q_alta * sum(ceduto * w) /
        calore gratuito entrato negli evaporatori (scarto, terreno, solare). Il
        peso w e' orario (dipende da T0), ma il rapporto si chiude sul mese perche'
        gli accumuli spostano il calore da un'ora all'altra.

    Chiusura mensile: i pesi sono orari, ma gli accumuli spostano il calore nel
    tempo, quindi il valore di ogni mese si ripartisce fra le aziende in
    proporzione a sum(MWh ceduti * w) del mese. Al valore si aggiunge la quota
    fissa (EUR/MWh ceduto). Tetto (netback): nel mese lo scarto non puo' costare
    piu' di P_target * calore prodotto - costo dell'elettricita' delle pompe,
    altrimenti il target per l'utente non e' rispettabile.
    """
    n = len(idx_h)
    mesi = np.asarray(idx_h.month.values)
    C_gas = ((np.asarray(psv_mese)[mesi - 1] + spread + ets2 * EF_GAS_T_MWH_PCS) / eta_caldaia
             + caldaia_evitata)
    P_t = (1.0 - sconto) * C_gas
    T0_h = np.asarray(T0_h, dtype=float)
    p_el = np.asarray(prezzo_el_h, dtype=float)
    g_mand = exergia_scala(mandata, T0_h)

    q_dir = np.asarray(sim["q_hot_direct"])
    q_alta = np.asarray(sim["q_alta"])
    W = np.asarray(sim["el_alta"]) + (np.asarray(sim["el_bassa"]) if hp_bassa_attiva else 0.0)
    q_ground = np.asarray(sim.get("q_ground", np.zeros(n)))
    q_sol = np.asarray(sim.get("q_da_solare", np.zeros(n)))
    u_hp = np.maximum(q_alta - W - q_ground - q_sol, 0.0)
    gratuito = u_hp + q_ground + q_sol
    with np.errstate(divide="ignore", invalid="ignore"):
        s_w = np.where(gratuito > 1e-12, u_hp / gratuito, 0.0)

    vuoto = (pd.DataFrame(), pd.DataFrame(), {})
    o = off_df[off_df["MWh"] > 0].copy()
    if o.empty:
        return vuoto
    o["T"] = o["T_disponibile"].astype(float)
    o["livello"] = np.where(o["T"] >= mandata, "caldo",
                            np.where(o["T"] >= T_int, "intermedio", "basso"))
    o["percorso"] = np.where(o["livello"] == "caldo", "diretto", "hp")
    o["MWhT"] = o["MWh"] * o["T"]
    perso = {"caldo": np.asarray(sim.get("perso_hot", np.zeros(n))),
             "intermedio": np.asarray(sim.get("perso_int", np.zeros(n))),
             "basso": np.asarray(sim.get("perso_low", np.zeros(n)))}

    # MWh ceduti e peso orario, per azienda e livello
    serie = []
    for liv, g_liv in o.groupby("livello"):
        tot = g_liv.groupby("datetime")["MWh"].sum().reindex(idx_h, fill_value=0.0).values
        for az, g in g_liv.groupby("azienda"):
            agg = g.groupby("datetime")[["MWh", "MWhT"]].sum().reindex(idx_h, fill_value=0.0)
            s = agg["MWh"].values
            with np.errstate(divide="ignore", invalid="ignore"):
                T_k = np.where(s > 1e-12, agg["MWhT"].values / s, np.nan)
                quota = np.where(tot > 1e-12, s / tot, 0.0)
                w = np.where(g_mand > 1e-12,
                             exergia_scala(np.nan_to_num(T_k, nan=-273.0), T0_h) / g_mand, 0.0)
            ceduto = np.maximum(s - perso[liv] * quota, 0.0)
            serie.append({"azienda": az, "percorso": "diretto" if liv == "caldo" else "hp",
                          "ceduto": ceduto, "w": np.clip(w, 0.0, 1.0)})
    if not serie:
        return vuoto

    # valore orario attribuibile allo scarto per percorso
    num_hp = sum(x["ceduto"] * x["w"] for x in serie if x["percorso"] == "hp") \
        if any(x["percorso"] == "hp" for x in serie) else np.zeros(n)
    den_hp = sum(x["ceduto"] for x in serie if x["percorso"] == "hp") \
        if any(x["percorso"] == "hp" for x in serie) else np.zeros(n)
    with np.errstate(divide="ignore", invalid="ignore"):
        w_hp = np.where(den_hp > 1e-12, num_hp / den_hp, np.nan)
    # ore senza cessione (si lavora dall'accumulo): peso medio del mese
    w_hp_s = pd.Series(w_hp)
    w_mese = pd.Series(num_hp).groupby(mesi).sum() / pd.Series(den_hp).groupby(mesi).sum().replace(0, np.nan)
    w_hp = np.where(np.isnan(w_hp), w_mese.reindex(mesi).fillna(0.0).values, w_hp_s.values)
    V = {"diretto": P_t * q_dir, "hp": P_t * q_alta * s_w * w_hp}
    margine = P_t * (q_dir + q_alta) - p_el * W

    if formula_psv is not None:
        # Prezzo per formula: EUR/MWh ceduto = PSV del mese x (a + b x w), con w
        # orario (T0 e temperatura del flusso). Nessun riparto di valore.
        _a, _b = float(formula_psv[0]), float(formula_psv[1])
        _psv_h = np.asarray(psv_mese)[mesi - 1]
        righe = []
        for m in range(1, 13):
            sel = mesi == m
            if not sel.any():
                continue
            agg = {}
            for x in serie:
                c = float(x["ceduto"][sel].sum())
                cw = float((x["ceduto"][sel] * x["w"][sel]).sum())
                costo = float((x["ceduto"][sel] * _psv_h[sel] * (_a + _b * x["w"][sel])).sum())
                r = agg.setdefault(x["azienda"], [0.0, 0.0, 0.0])
                r[0] += c
                r[1] += cw
                r[2] += costo
            for az, (c, cw, costo) in agg.items():
                righe.append({"azienda": az, "mese": m, "MWh_ceduti": c,
                              "w_medio": cw / c if c > 1e-9 else 0.0, "costo_eur": costo,
                              "eur_mwh": costo / c if c > 1e-9 else 0.0,
                              "tetto_attivo": False, "P_target": float(P_t[sel].mean())})
        return _riassumi_prezzi_scarto(righe, C_gas, P_t, p_el, W, margine)

    righe = []
    for m in range(1, 13):
        sel = mesi == m
        if not sel.any():
            continue
        quote = {}
        for perc in ("diretto", "hp"):
            den = sum(float((x["ceduto"][sel] * x["w"][sel]).sum())
                      for x in serie if x["percorso"] == perc)
            for x in serie:
                if x["percorso"] != perc:
                    continue
                c = float(x["ceduto"][sel].sum())
                cw = float((x["ceduto"][sel] * x["w"][sel]).sum())
                if perc == "hp":
                    # Valore del mese sul percorso pompe: target x calore prodotto,
                    # per la quota di exergia che lo scarto porta nel mese
                    # = sum(ceduto x w) / calore gratuito entrato negli evaporatori.
                    # Pesare ora per ora (versione precedente) era sbagliato con gli
                    # accumuli: il calore di ZML immagazzinato e usato nel weekend
                    # prendeva il peso del calore ceduto in quell'ora (Pietro Rosa a
                    # 25 °C, quasi zero), e ZML risultava pagato il 40 % in meno.
                    _grat_m = float(gratuito[sel].sum())
                    _quota_ex = min(den / _grat_m, 1.0) if _grat_m > 1e-12 else 0.0
                    V_m = float((P_t[sel] * q_alta[sel]).sum()) * _quota_ex
                else:
                    V_m = float(V[perc][sel].sum())
                v = V_m * (cw / den) if den > 1e-12 else 0.0
                r = quote.setdefault(x["azienda"], {"ceduto": 0.0, "cw": 0.0, "var": 0.0})
                r["ceduto"] += c
                r["cw"] += cw
                r["var"] += v
        tot_m = sum(r["var"] + quota_fissa * r["ceduto"] for r in quote.values())
        marg_m = max(float(margine[sel].sum()), 0.0)
        fatt = min(1.0, marg_m / tot_m) if tot_m > 1e-9 else 1.0
        for az, r in quote.items():
            costo = (r["var"] + quota_fissa * r["ceduto"]) * fatt
            righe.append({"azienda": az, "mese": m, "MWh_ceduti": r["ceduto"],
                          "w_medio": r["cw"] / r["ceduto"] if r["ceduto"] > 1e-9 else 0.0,
                          "costo_eur": costo,
                          "eur_mwh": costo / r["ceduto"] if r["ceduto"] > 1e-9 else 0.0,
                          "tetto_attivo": fatt < 0.999,
                          "P_target": float(P_t[sel].mean())})
    return _riassumi_prezzi_scarto(righe, C_gas, P_t, p_el, W, margine)


def _riassumi_prezzi_scarto(righe, C_gas, P_t, p_el, W, margine):
    """Tabelle mensile e annua per azienda a partire dalle righe mensili."""
    df_m = pd.DataFrame(righe)
    if df_m.empty:
        return pd.DataFrame(), pd.DataFrame(), {}
    df_a = (df_m.groupby("azienda")
            .agg(MWh_ceduti=("MWh_ceduti", "sum"), costo_eur=("costo_eur", "sum"),
                 mesi_tetto=("tetto_attivo", "sum"))
            .reset_index())
    _cw = df_m.assign(cw=df_m["MWh_ceduti"] * df_m["w_medio"]).groupby("azienda")["cw"].sum()
    df_a["w_medio"] = df_a["azienda"].map(_cw) / df_a["MWh_ceduti"].replace(0, np.nan)
    df_a["eur_mwh"] = df_a["costo_eur"] / df_a["MWh_ceduti"].replace(0, np.nan)
    df_a = df_a.sort_values("MWh_ceduti", ascending=False)
    info = {"C_gas_h": C_gas, "P_target_h": P_t,
            "costo_el": float((p_el * W).sum()),
            "margine": float(margine.sum())}
    return df_m, df_a, info


def valuta_combinazioni_aziende(off_all, idx_h, dom_arr, soil_arr, mandata, ritorno, T_int,
                                eta_hp, V_hot, V_int, V_low, P_alta, P_bassa, backup_tipo,
                                P_bk, backup_cop, antigelo, perd, strat_on, solar_low,
                                tipo_sorgente, resa_sorgente, costo_sorgente,
                                T0_h, prezzo_el_h, psv, spread, eta_cald, sconto, quota_fissa,
                                ets2=0.0, caldaia_evitata=0.0, formula_psv=None):
    """Ripete il dispatch annuale per ogni combinazione di aziende allacciate.

    Taglie di macchine e accumuli restano quelle dello scenario: cambia solo
    da dove arriva il calore. Per ogni combinazione si raccolgono le grandezze
    che dipendono dalle aziende allacciate: elettricita' delle pompe,
    combustibile di backup, picco e costo della sorgente fredda (il terreno
    supplisce allo scarto che manca), costo del calore di scarto con la scala
    exergetica, energia non coperta.
    """
    from itertools import combinations
    aziende = sorted(off_all["azienda"].unique())
    is_hp = backup_tipo == "HP bassa T"
    out = []
    for k in range(0, len(aziende) + 1):
        for comb in combinations(aziende, k):
            o = off_all[off_all["azienda"].isin(comb)]
            (q_hot, q_int, _ql, q_low_b, bin_T, q_int_b, bin_T_int) = routing_flussi(
                o, idx_h, mandata, T_int)
            q_low_eff = q_low_b.copy()
            if solar_low is not None:
                q_low_eff[:, -1] = q_low_eff[:, -1] + solar_low
            s = dispatch_cascata(dom_arr, q_hot, q_int, q_low_eff, bin_T, soil_arr,
                                 mandata, ritorno, T_int, 5, eta_hp,
                                 V_hot, V_int, V_low, P_alta, P_bassa,
                                 parallelo=backup_tipo, P_backup_kw=P_bk,
                                 backup_cop=backup_cop, antigelo=antigelo,
                                 perdita_sett_pct=perd, q_int_bins=q_int_b,
                                 bin_T_int=bin_T_int, stratificato=strat_on,
                                 solare_low=solar_low)
            pk_g = float(s["q_ground"].max()) * 1000.0 if is_hp else 0.0
            capex_g = (float(dimensiona_sorgente_bassa_t(pk_g, tipo_sorgente, resa_sorgente,
                                                         costo_sorgente)["costo"])
                       if is_hp and pk_g > 0 else 0.0)
            costo_sc = 0.0
            per_az = {}
            if comb:
                _m, _a, _i = prezzo_scarto_exergetico(
                    o, idx_h, s, T0_h, prezzo_el_h, mandata, T_int, psv, spread,
                    eta_cald, sconto, quota_fissa, is_hp, ets2, caldaia_evitata,
                    formula_psv)
                if not _a.empty:
                    costo_sc = float(_a["costo_eur"].sum())
                    per_az = dict(zip(_a["azienda"], _a["MWh_ceduti"]))
            out.append({"aziende": tuple(comb), "E_el": float(s["E_el_tot"]),
                        "costo_el": float((np.asarray(prezzo_el_h)
                                           * (s["el_alta"] + s["el_bassa"])).sum()),
                        "E_backup": float(s["E_backup"]), "E_non_cop": float(s["E_non_coperta"]),
                        "ore_non_cop": int(s["ore_non_coperte"]),
                        "E_ground": float(s["E_ground"]), "capex_sorgente": capex_g,
                        "costo_scarto": costo_sc, "MWh_ceduti": per_az})
    return out


def lunghezza_adduzioni(aziende, lung_radiale, schema="dorsale"):
    """Metri di condotta per allacciare un gruppo di aziende alla sottocentrale.

    radiale: una condotta per azienda fino alla sottocentrale (lunghezze del
             tracciato calcolato in Offerta).
    dorsale: albero di collegamento minimo fra sottocentrale e aziende. Dalla
             sottocentrale si usa il tracciato calcolato; fra un'azienda e
             l'altra la distanza in linea d'aria x 1,35 (tortuosita' stradale).
             Prudente: il diametro della dorsale si paga come quello degli stacchi.
    """
    az = [a for a in aziende if a in lung_radiale]
    if not az:
        return 0.0
    if schema == "radiale":
        return float(sum(lung_radiale[a] for a in az))
    # Prim: si parte dalla sottocentrale
    collegati, tot = [], 0.0
    restanti = list(az)
    while restanti:
        best = None
        for a in restanti:
            d = lung_radiale[a]
            for c in collegati:
                la, lo = AZIENDE_COORD[a]
                lc, lc2 = AZIENDE_COORD[c]
                x, y = _latlon_a_xy(np.array([la, lc]), np.array([lo, lc2]))
                d = min(d, float(np.hypot(x[1] - x[0], y[1] - y[0])) * 1.35)
            if best is None or d < best[1]:
                best = (a, d)
        collegati.append(best[0])
        restanti.remove(best[0])
        tot += best[1]
    return tot


def dispatch_cascata(dom_arr, q_hot_arr, q_int_arr, q_low_bins, bin_T, soil_arr,
                     mandata, ritorno, T_int, dT_evap, eta_hp,
                     V_hot, V_int, V_low,
                     P_hp_alta_kw, P_hp_bassa_kw,
                     parallelo="HP bassa T", P_backup_kw=0.0, backup_cop=None,
                     antigelo=0.0, perdita_sett_pct=1.0,
                     q_int_bins=None, bin_T_int=None, stratificato=True,
                     solare_low=None):
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
    # scarto perso distinto per livello: consente di attribuire a ciascuna
    # azienda la quota di calore realmente valorizzata (vedi utilizzo_per_azienda)
    perso_hot = np.zeros(n)
    perso_int = np.zeros(n)
    perso_low = np.zeros(n)
    cop_alta_s = np.full(n, np.nan)
    cop_bassa_s = np.full(n, np.nan)
    ore_ground = 0

    soc_hot = 0.0
    soc_int = 0.0
    soc_low_bins = np.zeros(len(bin_T))

    # ------------------------------------------------------------------
    # PRECALCOLO: tutto cio' che non dipende dallo stato degli accumuli esce
    # dal ciclo orario. Il COP della HP alta T, in particolare, dipende solo
    # da T_int, mandata e rendimento: e' costante su tutte le 8.784 ore.
    # ------------------------------------------------------------------
    # --- accumulo intermedio: stratificato oppure a mescolamento ---
    # Con la stratificazione l'evaporatore della HP alta T preleva dallo strato
    # piu' caldo disponibile, quindi il COP varia ora per ora invece di essere
    # fisso sulla temperatura nominale dell'anello. Senza flussi di scarto a
    # temperature diverse la differenza si annulla da se'.
    strat = bool(stratificato) and (q_int_bins is not None) and (bin_T_int is not None)
    if strat:
        q_int_b = np.asarray(q_int_bins, dtype=float)
        bT_int = np.asarray(bin_T_int, dtype=float)
        n_bin_int = len(bT_int)
        idx_int_desc = list(range(n_bin_int - 1, -1, -1))   # dal piu' caldo
        # COP per strato. Un flusso non cede calore restando alla propria
        # temperatura: entra allo strato k e si raffredda scendendo verso la
        # base dell'anello. La temperatura utile all'evaporatore e' quindi la
        # media fra quella dello strato e quella di base, non quella d'ingresso:
        # usare quest'ultima sovrastimerebbe il COP anche quando tutti i flussi
        # arrivano alla stessa temperatura.
        T_utile = (bT_int + float(T_int)) / 2.0
        cop_strato = np.array([float(cop_singola(t - dT_evap, mandata, eta_hp))
                               for t in T_utile])
    else:
        q_int_b = None
        bT_int = None
        n_bin_int = 0
        idx_int_desc = []
        cop_strato = None

    soc_int_bins = np.zeros(n_bin_int) if strat else None

    # Quota solare dell'anello basso. Il calore solare entra nello stesso
    # accumulo dello scarto a bassa temperatura e diventa indistinguibile:
    # per attribuirne la parte utilizzata si tiene la proporzione fra le due
    # sorgenti ora per ora, che e' l'unica attribuzione corretta.
    sol_low = (np.asarray(solare_low, dtype=float)
               if solare_low is not None else np.zeros(n))
    if len(sol_low) != n:
        sol_low = np.zeros(n)
    q_da_solare = np.zeros(n)

    cop_a = float(cop_singola(T_int - dT_evap, mandata, eta_hp))
    hp_alta_attiva = (P_alta > 0) and (cop_a > 1.0)
    frac_evap = 1.0 - 1.0 / cop_a if cop_a > 1.0 else 0.0
    inv_cop_a = 1.0 / cop_a if cop_a > 0 else 0.0
    fatt_perdita = 1.0 - perdita_ora
    ha_perdite = perdita_ora > 0
    extra_bassa = P_bassa if is_hp else 0.0
    # temperatura della sorgente geotermica gia' vincolata al floor antigelo
    soil_eff = np.maximum(soil_arr, antigelo)
    n_bin = len(bin_T)
    bin_T_desc = list(range(n_bin - 1, -1, -1))   # ordine di prelievo: dal piu caldo

    for i in range(n):
        # --- dispersioni degli accumuli ---
        if ha_perdite:
            soc_hot *= fatt_perdita
            soc_int *= fatt_perdita
            soc_low_bins *= fatt_perdita
            if strat:
                soc_int_bins *= fatt_perdita

        # --- pool disponibili nell'ora: stock + flusso in ingresso (P7) ---
        pool_hot = soc_hot + q_hot_arr[i]
        if strat:
            pool_int_bins = soc_int_bins + q_int_b[i]
            pool_int = float(pool_int_bins.sum())
        else:
            pool_int = soc_int + q_int_arr[i]
        pool_low_bins = soc_low_bins + q_low_bins[i]
        if not is_hp:
            # senza HP bassa T il livello basso non ha utilizzatori
            _pl = float(pool_low_bins.sum())
            scarto_perso[i] += _pl
            perso_low[i] += _pl
            pool_low_bins = np.zeros_like(pool_low_bins)

        dom = dom_arr[i]

        # --- MERIT 1: scarto >= mandata, uso diretto ---
        d_hot = dom if dom < pool_hot else pool_hot
        pool_hot -= d_hot
        q_hot_direct[i] = d_hot
        residuo = dom - d_hot

        # --- MERIT 2: HP alta T (precede SEMPRE il combustibile) ---
        if residuo > 1e-9 and hp_alta_attiva:
            q_a_want = residuo if residuo < P_alta else P_alta

            if strat:
                # Prelievo dallo strato piu' caldo verso il basso. Ogni strato
                # ha il proprio COP, quindi il calore reso e l'energia sottratta
                # all'evaporatore vanno accumulati strato per strato: usare una
                # temperatura media sottostimerebbe la resa della macchina.
                q_a = 0.0
                el_a = 0.0
                from_int = 0.0
                residuo_pot = q_a_want
                for k in idx_int_desc:
                    if residuo_pot <= 1e-12:
                        break
                    disp = pool_int_bins[k]
                    if disp <= 1e-12:
                        continue
                    cop_k = cop_strato[k]
                    if cop_k <= 1.0:
                        continue
                    fe_k = 1.0 - 1.0 / cop_k          # quota presa all'evaporatore
                    # calore producibile con l'energia di questo strato
                    q_k = disp / fe_k
                    if q_k > residuo_pot:
                        q_k = residuo_pot
                    e_k = q_k * fe_k
                    pool_int_bins[k] -= e_k
                    from_int += e_k
                    q_a += q_k
                    el_a += q_k / cop_k
                    residuo_pot -= q_k
                pool_int = float(pool_int_bins.sum())

                # se lo stratificato non basta, la HP bassa ricarica in tempo
                # reale: quel contributo entra alla temperatura nominale T_int
                from_bassa = 0.0
                if residuo_pot > 1e-12 and extra_bassa > 0 and frac_evap > 0:
                    e_want = residuo_pot * frac_evap
                    from_bassa = e_want if e_want < extra_bassa else extra_bassa
                    q_extra = from_bassa / frac_evap
                    q_a += q_extra
                    el_a += q_extra * inv_cop_a
                E_a = from_int + from_bassa
                cop_alta_s[i] = (q_a / el_a) if el_a > 1e-12 else np.nan
            else:
                cop_alta_s[i] = cop_a
                E_a_want = q_a_want * frac_evap
                # energia disponibile all'evaporatore: livello intermedio +
                # eventuale ricarica in tempo reale dalla HP bassa T
                E_a = min(E_a_want, pool_int + extra_bassa)
                q_a = E_a / frac_evap if E_a > 1e-12 else 0.0
                el_a = q_a * inv_cop_a
                from_int = min(E_a, pool_int)
                pool_int -= from_int
                from_bassa = E_a - from_int

            if E_a > 1e-12:

                # --- MERIT 3: HP bassa T, ricarica il livello intermedio ---
                if from_bassa > 1e-12 and is_hp and P_bassa > 0:
                    g_T = soil_eff[i]
                    soc_tot = float(pool_low_bins.sum())
                    if soc_tot > 1e-9:
                        need = from_bassa
                        e_acc = 0.0
                        wt = 0.0
                        for k in bin_T_desc:
                            take = pool_low_bins[k]
                            if take > need:
                                take = need
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
                    for k in bin_T_desc:
                        take = pool_low_bins[k]
                        if take > need:
                            take = need
                        pool_low_bins[k] -= take
                        need -= take
                        if need <= 1e-12:
                            break
                    q_ground[i] = need if need > 0.0 else 0.0
                    # attribuzione della quota solare: il prelievo effettivo
                    # dall'anello basso e' E_b meno cio' che e' arrivato dal
                    # terreno, e si ripartisce in proporzione agli ingressi
                    _pres_low = max(E_b - q_ground[i], 0.0)
                    if _pres_low > 1e-12:
                        _in_low = float(q_low_bins[i].sum()) + sol_low[i]
                        if _in_low > 1e-12:
                            q_da_solare[i] = _pres_low * sol_low[i] / _in_low
                    if src_is_ground or q_ground[i] > 1e-9:
                        ore_ground += 1
                    q_bassa[i] = q_b
                    el_bassa[i] = q_b / cop_b if cop_b > 0 else 0.0

                el_alta[i] = el_a
                q_alta[i] = q_a
                residuo -= q_a

        # --- MERIT 4: combustibile, solo sul residuo ---
        if (not is_hp) and residuo > 1e-9 and P_bk > 0:
            q_k = residuo if residuo < P_bk else P_bk
            q_backup[i] = q_k
            if backup_cop is not None and backup_cop > 0:
                el_bassa[i] += q_k / backup_cop
            residuo -= q_k

        non_cop[i] = residuo if residuo > 0.0 else 0.0

        # --- fine ora: quel che avanza va in accumulo, il resto e perso ---
        if pool_hot > C_hot:
            scarto_perso[i] += pool_hot - C_hot
            perso_hot[i] += pool_hot - C_hot
            soc_hot = C_hot
        else:
            soc_hot = pool_hot
        if strat:
            tot_i = float(pool_int_bins.sum())
            if tot_i > C_int:
                over_i = tot_i - C_int
                scarto_perso[i] += over_i
                perso_int[i] += over_i
                # trabocca dallo strato piu' freddo: e' quello meno pregiato
                for k in range(n_bin_int):
                    drop = pool_int_bins[k]
                    if drop > over_i:
                        drop = over_i
                    pool_int_bins[k] -= drop
                    over_i -= drop
                    if over_i <= 1e-12:
                        break
            soc_int_bins = pool_int_bins
            soc_int = float(soc_int_bins.sum())
        elif pool_int > C_int:
            scarto_perso[i] += pool_int - C_int
            perso_int[i] += pool_int - C_int
            soc_int = C_int
        else:
            soc_int = pool_int
        if is_hp:
            tot_low = float(pool_low_bins.sum())
            if tot_low > C_low:
                over = tot_low - C_low
                scarto_perso[i] += over
                perso_low[i] += over
                for k in range(n_bin):
                    drop = pool_low_bins[k]
                    if drop > over:
                        drop = over
                    pool_low_bins[k] -= drop
                    over -= drop
                    if over <= 1e-12:
                        break
            soc_low_bins = pool_low_bins
        else:
            soc_low_bins = np.zeros(n_bin)

    # traccia oraria dello scarto perso per livello: serve ad attribuire a
    # ciascuna azienda la quota di calore effettivamente valorizzata
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
        "q_da_solare": q_da_solare, "E_da_solare": float(q_da_solare.sum()),
        "el_alta": el_alta, "el_bassa": el_bassa, "non_cop": non_cop,
        "cop_alta_s": cop_alta_s, "cop_bassa_s": cop_bassa_s,
        "E_hot_diretto": E_hot, "E_hp_alta": E_alta, "E_hp_bassa": E_bassa, "E_backup": E_bk,
        "E_el_alta": E_el_alta, "E_el_bassa": E_el_bassa, "E_el_tot": E_el_alta + E_el_bassa,
        "E_non_coperta": float(non_cop.sum()), "E_scarto_perso": float(scarto_perso.sum()),
        "perso_hot": perso_hot, "perso_int": perso_int, "perso_low": perso_low,
        "cop_alta_medio": cop_alta_medio, "cop_bassa_medio": cop_bassa_medio,
        "ore_non_coperte": int((non_cop > 1e-6).sum()), "ore_ground": ore_ground,
    }


def ottimizza_cascata(dom_arr, q_hot_arr, q_int_arr, q_low_bins, bin_T, soil_arr,
                      mandata, ritorno, T_int, dT_evap, eta_hp, parallelo,
                      capex_hp_func, capex_backup_kw, opex_backup_mwh, backup_cop,
                      prezzo_el, costo_m3, capex_solare_fisso, fattore_crf,
                      perdita_func, antigelo, q_int_bins=None, bin_T_int=None,
                      stratificato=True, n_griglia=6, **kwargs):
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

    # Tetto ai volumi: oltre una certa taglia un serbatoio non e' piu' un
    # componente di centrale ma un'opera civile a se', con costi e ingombri
    # di altra natura. Il limite e' impostabile dall'utente.
    v_max = float(kwargs.get("v_max_m3", 2000.0))

    def _griglia(vmax, n=None):
        """Volumi candidati fino a vmax, piu' fitti sui valori piccoli.

        Il numero di valori si riflette al cubo sul tempo di calcolo, perche'
        i tre accumuli vengono combinati fra loro: con la pompa a bassa
        temperatura, dove tutti e tre sono in gioco, scendere da 6 a 4 valori
        riduce le combinazioni da oltre trecento a una sessantina.
        """
        n = int(n_griglia if n is None else n)
        if vmax <= 0:
            return [0.0]
        passi = np.unique(np.round(np.geomspace(50.0, max(vmax, 100.0), n) / 50.0) * 50.0)
        return [0.0] + [float(v) for v in passi if v <= vmax]

    ha_hot = float(q_hot_arr.sum()) > 1e-6
    v_hot_cands = _griglia(v_max) if ha_hot else [0.0]
    v_int_cands = _griglia(v_max)
    v_low_cands = _griglia(v_max) if is_hp else [0.0]

    def _valuta(v_hot, v_int, v_low):
        r = dispatch_cascata(dom_arr, q_hot_arr, q_int_arr, q_low_bins, bin_T, soil_arr,
                             mandata, ritorno, T_int, dT_evap, eta_hp,
                             v_hot, v_int, v_low, P_alta, P_bassa,
                             parallelo=parallelo, P_backup_kw=P_bk, backup_cop=backup_cop,
                             antigelo=antigelo,
                             perdita_sett_pct=perdita_func(max(v_int, v_low, v_hot)),
                             q_int_bins=q_int_bins, bin_T_int=bin_T_int,
                             stratificato=stratificato)
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


def ottimizza_economico(dom_arr, q_hot_arr, q_int_arr, q_low_bins, bin_T, soil_arr,
                        mandata, ritorno, T_int, dT_evap, eta_hp, parallelo,
                        capex_hp_func, capex_backup_kw, opex_backup_mwh, backup_cop,
                        prezzo_el, costo_m3, capex_solare_fisso, perdita_func, antigelo,
                        picco_kw, v_max, sorgente, economia, costo_scarto_func,
                        q_int_bins=None, bin_T_int=None, stratificato=True,
                        solare_low=None, n_griglia=5):
    """Dimensionamento con lo stesso obiettivo dell'Analisi economica.

    Minimizza il costo annuo delle voci di centrale che dipendono dalle taglie:
      investimento (pompe, caldaia, accumuli, sorgente fredda, solare) al netto
      del contributo, annualizzato al WACC sull'orizzonte dell'Analisi economica
      + manutenzione di centrale in % del CAPEX
      + elettricita' delle pompe al prezzo effettivo
      + combustibile di backup
      + acquisto del calore di scarto (scala exergetica o prezzi fissi).
    Rete, sottostazioni, allacciamenti e ricavi non dipendono dalle taglie, quindi
    a parita' di domanda minimizzare questo costo massimizza il VAN.

    Diversamente dal dimensionamento a LCOH, cerca anche le POTENZE:
      - con HP bassa T: HP alta sul picco (non c'e' backup), HP bassa variabile;
      - con caldaia: caldaia sul picco come riserva, HP alta variabile, cosi' la
        pompa lavora in base e il combustibile copre solo le punte.
    Ricerca a coordinate: volumi alla potenza di riferimento, poi potenza con i
    volumi trovati, poi di nuovo i volumi alla potenza scelta.

    sorgente: dict(tipo, resa, costo) per la sorgente fredda della HP bassa T.
    economia: dict(wacc, anni, contributo_pct, om_pct).
    costo_scarto_func(sim) -> EUR/a di calore di scarto acquistato.
    """
    dom_tot = float(np.sum(dom_arr))
    if dom_tot <= 0:
        return None
    is_hp = (parallelo == "HP bassa T")
    cop_a_ref = float(cop_singola(T_int - dT_evap, mandata, eta_hp))
    frac_a = max(1.0 - 1.0 / cop_a_ref, 0.0)
    fattore = crf(economia["wacc"], economia["anni"]) * (1.0 - economia["contributo_pct"] / 100.0)
    om = economia["om_pct"] / 100.0

    def _griglia(vmax, n=n_griglia):
        if vmax <= 0:
            return [0.0]
        passi = np.unique(np.round(np.geomspace(50.0, max(vmax, 100.0), n) / 50.0) * 50.0)
        return [0.0] + [float(v) for v in passi if v <= vmax]

    ha_hot = float(np.sum(q_hot_arr)) > 1e-6
    v_hot_c = _griglia(v_max) if ha_hot else [0.0]
    v_int_c = _griglia(v_max)
    v_low_c = _griglia(v_max) if is_hp else [0.0]
    if is_hp:
        P_ref = picco_kw * frac_a * 1.1
        p_cands = [round(P_ref * f / 100.0) * 100.0 for f in (0.25, 0.35, 0.5, 0.65, 0.8, 1.0)]
    else:
        P_ref = picco_kw
        p_cands = [round(picco_kw * f / 100.0) * 100.0 for f in (0.25, 0.35, 0.5, 0.65, 0.8, 1.0)]
    cache = {}

    def _valuta(P_var, vh, vi, vl):
        chiave = (P_var, vh, vi, vl)
        if chiave in cache:
            return cache[chiave]
        if is_hp:
            P_alta, P_bassa, P_bk = picco_kw, P_var, 0.0
        else:
            P_alta, P_bassa, P_bk = P_var, 0.0, picco_kw
        r = dispatch_cascata(dom_arr, q_hot_arr, q_int_arr, q_low_bins, bin_T, soil_arr,
                             mandata, ritorno, T_int, dT_evap, eta_hp,
                             vh, vi, vl, P_alta, P_bassa,
                             parallelo=parallelo, P_backup_kw=P_bk, backup_cop=backup_cop,
                             antigelo=antigelo,
                             perdita_sett_pct=perdita_func(max(vi, vl, vh)),
                             q_int_bins=q_int_bins, bin_T_int=bin_T_int,
                             stratificato=stratificato, solare_low=solare_low)
        capex_g = 0.0
        if is_hp:
            pk_g = float(r["q_ground"].max()) * 1000.0
            if pk_g > 0:
                capex_g = float(dimensiona_sorgente_bassa_t(
                    pk_g, sorgente["tipo"], sorgente["resa"], sorgente["costo"])["costo"])
        capex = (P_alta * capex_hp_func(P_alta)
                 + (P_bassa * capex_hp_func(P_bassa) if is_hp and P_bassa > 0 else 0.0)
                 + (P_bk * capex_backup_kw if not is_hp else 0.0)
                 + (vh + vi + vl) * costo_m3 + capex_solare_fisso + capex_g)
        c_scarto = float(costo_scarto_func(r))
        opex = r["E_el_tot"] * prezzo_el + r["E_backup"] * opex_backup_mwh
        costo = capex * fattore + capex * om + opex + c_scarto
        E_fer = (r["E_hot_diretto"] + r["E_hp_alta"]
                 + (r["E_backup"] if parallelo == "biomassa" else 0.0))
        out = {"v_hot": vh, "v_int": vi, "v_low": vl, "P_alta": P_alta, "P_bassa": P_bassa,
               "P_bk": P_bk, "costo_annuo": costo, "lcoh": costo / dom_tot,
               "quota_fer": E_fer / dom_tot * 100, "capex": capex, "capex_sorgente": capex_g,
               "costo_scarto": c_scarto, "E_hot": r["E_hot_diretto"], "E_alta": r["E_hp_alta"],
               "E_bassa": r["E_hp_bassa"], "E_backup": r["E_backup"], "E_el": r["E_el_tot"],
               "ore_scoperte": r["ore_non_coperte"], "cop_alta": r["cop_alta_medio"],
               "cop_bassa": r["cop_bassa_medio"], "obiettivo": "economico"}
        cache[chiave] = out
        return out

    def _migliore(cands):
        cands = list(cands)
        min_sc = min(c["ore_scoperte"] for c in cands)
        ok = [c for c in cands if c["ore_scoperte"] <= min_sc]
        return min(ok, key=lambda c: c["costo_annuo"])

    def _volumi(P_var):
        return _migliore(_valuta(P_var, vh, vi, vl)
                         for vh in v_hot_c for vi in v_int_c for vl in v_low_c)

    # copertura di riferimento: la migliore ottenibile alla potenza piena
    ref = _volumi(p_cands[-1])
    soglia = ref["ore_scoperte"]
    best = ref
    for _giro in range(2):
        prove = [_valuta(P, best["v_hot"], best["v_int"], best["v_low"]) for P in p_cands]
        prove = [c for c in prove if c["ore_scoperte"] <= soglia]
        if prove:
            cand = min(prove, key=lambda c: c["costo_annuo"])
            P_sel = cand["P_bassa"] if is_hp else cand["P_alta"]
            vol = _volumi(P_sel)
            nuovo = vol if vol["ore_scoperte"] <= soglia else cand
            if nuovo["costo_annuo"] < best["costo_annuo"] - 1e-6:
                best = nuovo
                continue
        break
    return best


# =============================================================================
# GENERAZIONE PROFILI DI OFFERTA
# =============================================================================
# =============================================================================
# PROFILI DI CARICO RESIDENZIALE
# =============================================================================
# Un'abitazione non consuma come un edificio pubblico: ha due picchi (mattino
# e sera) e nelle ore centrali e' spesso vuota, mentre una scuola o un ufficio
# scaldano in modo continuo durante l'orario di apertura e una RSA 24 ore su 24.
# Usare il profilo dei pubblici per i privati falsa la forma del picco, che e'
# proprio la grandezza su cui si dimensionano macchine e accumuli.
#
# Coefficienti orari (media = 1.0) da profili di carico residenziale italiani
# per riscaldamento con caldaia autonoma e per acqua calda sanitaria.
PROFILO_SH_RESIDENZIALE = np.array([
    0.55, 0.45, 0.40, 0.40, 0.45, 0.75,   # 00-05  notte, attenuazione
    1.35, 1.60, 1.45, 1.10, 0.95, 0.90,   # 06-11  punta del mattino
    0.95, 0.90, 0.85, 0.90, 1.10, 1.40,   # 12-17  ripresa pomeridiana
    1.55, 1.45, 1.25, 1.05, 0.85, 0.65,   # 18-23  punta della sera
])
PROFILO_ACS_RESIDENZIALE = np.array([
    0.25, 0.15, 0.10, 0.10, 0.15, 0.45,   # 00-05
    1.30, 1.95, 1.75, 1.15, 0.85, 0.80,   # 06-11  docce del mattino
    0.95, 0.85, 0.65, 0.60, 0.75, 1.15,   # 12-17
    1.70, 1.90, 1.60, 1.20, 0.75, 0.40,   # 18-23  docce della sera
])
# Nel fine settimana la punta del mattino si sposta piu' tardi e si attenua.
PROFILO_SH_WEEKEND = np.roll(PROFILO_SH_RESIDENZIALE, 2) * 0.5 + PROFILO_SH_RESIDENZIALE * 0.5
PROFILO_ACS_WEEKEND = np.roll(PROFILO_ACS_RESIDENZIALE, 2) * 0.6 + PROFILO_ACS_RESIDENZIALE * 0.4


def profilo_residenziale(idx_h, energia_annua_mwh, hdd_orari=None, quota_acs=0.0):
    """Serie oraria di una utenza residenziale.

    Combina due componenti:
      - la stagionalita', presa dai gradi giorno orari se disponibili (cosi' il
        riscaldamento segue il clima reale e si spegne d'estate);
      - la forma giornaliera tipica dell'abitazione, con le due punte.

    Args:
        idx_h: indice orario
        energia_annua_mwh: energia da distribuire
        hdd_orari: peso stagionale per ora (tipicamente il fabbisogno orario
            aggregato degli edifici gia' noti). Se assente si usa un andamento
            sinusoidale con stagione di riscaldamento 15/10 - 15/04.
        quota_acs: se > 0, la serie e' ACS e non segue la stagionalita' del
            riscaldamento ma resta pressoche' costante nell'anno.

    Ritorna un array di MWh orari la cui somma e' esattamente energia_annua_mwh.
    """
    ore = idx_h.hour.values
    festivo = idx_h.dayofweek.values >= 5
    if quota_acs > 0:
        forma = np.where(festivo, PROFILO_ACS_WEEKEND[ore], PROFILO_ACS_RESIDENZIALE[ore])
        # l'ACS ha una lieve stagionalita': in inverno l'acqua di rete e' piu'
        # fredda e serve piu' calore per portarla in temperatura
        doy = idx_h.dayofyear.values
        stag = 1.0 + 0.15 * np.cos(2 * np.pi * (doy - 15) / 365.25)
        peso = forma * stag
    else:
        forma = np.where(festivo, PROFILO_SH_WEEKEND[ore], PROFILO_SH_RESIDENZIALE[ore])
        if hdd_orari is not None and float(np.nansum(hdd_orari)) > 0:
            stag = np.asarray(hdd_orari, dtype=float)
            stag = np.where(np.isfinite(stag), stag, 0.0)
        else:
            doy = idx_h.dayofyear.values
            stag = np.clip(np.cos(2 * np.pi * (doy - 15) / 365.25), 0.0, None)
        peso = forma * stag
    tot = float(peso.sum())
    if tot <= 0:
        return np.zeros(len(idx_h))
    return peso / tot * float(energia_annua_mwh)


# Festivita' civili e religiose infrasettimanali del calendario 2024, piu' il
# patrono di Maniago (San Mauro, 15 gennaio). Sono i giorni in cui gli impianti
# industriali si fermano al di fuori delle ferie programmate.
FESTIVITA_2024 = [
    "2024-01-01",  # Capodanno
    "2024-01-06",  # Epifania
    "2024-01-15",  # San Mauro, patrono di Maniago
    "2024-04-01",  # Lunedi dell'Angelo
    "2024-04-25",  # Liberazione
    "2024-05-01",  # Festa del lavoro
    "2024-06-02",  # Festa della Repubblica
    "2024-08-15",  # Ferragosto
    "2024-11-01",  # Ognissanti
    "2024-12-08",  # Immacolata
    "2024-12-25",  # Natale
    "2024-12-26",  # Santo Stefano
]


def _giorni_chiusura_set(giorni_chiusura_annui, seed=0, natale_acceso=False):
    """Giorni di fermata dell'impianto, su calendario reale.

    Le fermate non sono distribuite a caso: seguono l'ordine con cui si fermano
    davvero gli stabilimenti, cioe' ferie estive centrali di agosto, chiusura
    fra Natale e l'Epifania, festivita' infrasettimanali. Solo un eventuale
    residuo viene collocato nei venerdi, giorno tipico di manutenzione.

    natale_acceso: per gli impianti a ciclo continuo che non si spengono a
    Natale (e' il caso dei forni di Pietro Rosa).
    """
    if not giorni_chiusura_annui or giorni_chiusura_annui <= 0:
        return set()
    n = int(giorni_chiusura_annui)
    chiusi = []

    # 1) ferie estive: due settimane centrali di agosto, il blocco piu' lungo
    agosto = list(pd.date_range("2024-08-05", "2024-08-18"))
    chiusi += agosto[:min(n, len(agosto))]

    # 2) chiusura invernale, salvo impianti a ciclo continuo
    if len(chiusi) < n and not natale_acceso:
        natale = list(pd.date_range("2024-12-24", "2024-12-31"))
        chiusi += natale[:n - len(chiusi)]

    # 3) festivita' infrasettimanali
    if len(chiusi) < n:
        fest = [pd.Timestamp(d) for d in FESTIVITA_2024]
        fest = [d for d in fest if d not in chiusi and d.weekday() < 5]
        if natale_acceso:
            fest = [d for d in fest if not (d.month == 12 and d.day in (25, 26))]
        chiusi += fest[:n - len(chiusi)]

    # 4) residuo: manutenzioni programmate, tipicamente di venerdi
    if len(chiusi) < n:
        ven = [d for d in DAYS_2024 if d.weekday() == 4 and d not in chiusi]
        passo = max(len(ven) // max(n - len(chiusi), 1), 1)
        chiusi += ven[::passo][:n - len(chiusi)]

    return set(pd.Timestamp(d).normalize() for d in chiusi[:n])


def genera_flusso(row, pinch=5.0, seed=0):
    rng = np.random.default_rng(seed)
    P_nom = row["P_kW"] / 1000.0
    T_disp = row["T_alta_C"] - pinch
    profilo = row["profilo"]
    giorni_sett = int(row["giorni_sett"]) if not pd.isna(row.get("giorni_sett")) else 7
    # alcuni impianti a ciclo continuo non si fermano a Natale: si dichiara
    # con la colonna facoltativa natale_acceso del CSV dei flussi
    _nat = str(row.get("natale_acceso", "")).strip().lower() in ("1", "si", "sì", "true", "x")
    chiusi = _giorni_chiusura_set(row.get("chiusura_gg", 0), seed, natale_acceso=_nat)

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
        # Abbinamento per nome normalizzato (maiuscole e spazi ignorati): una
        # differenza di sola grafia faceva perdere le coordinate all'edificio,
        # che restava nei consumi ma spariva dal tracciato della rete.
        def _norm_nome(x):
            return " ".join(str(x).casefold().split())
        _coord["_k"] = _coord["edificio"].map(_norm_nome)
        _coord = _coord.drop_duplicates("_k").drop(columns=["edificio"])
        buildings["_k"] = buildings["edificio"].map(_norm_nome)
        buildings = buildings.merge(_coord, on="_k", how="left").drop(columns=["_k"])
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

    # POTENZA EFFETTIVA DEL FLUSSO
    # P_kW e' il calore teoricamente presente nel flusso, ma il recupero e'
    # limitato dallo scambiatore che si installa davvero. Dove esiste una
    # quotazione (P_scambiatore_kW) si usa quella: e' il collo di bottiglia
    # reale. Es. Pandolfo 4.187 kW recuperabili su 5.931 disponibili.
    flussi["P_disponibile_kW"] = pd.to_numeric(flussi["P_kW"], errors="coerce").fillna(0.0)
    if "P_scambiatore_kW" in flussi.columns:
        _phe = pd.to_numeric(flussi["P_scambiatore_kW"], errors="coerce")
        flussi["P_kW"] = np.where(_phe.notna() & (_phe > 0), _phe,
                                  flussi["P_disponibile_kW"])
        flussi["limitato_da_HE"] = (_phe.notna() & (_phe > 0)).values
    else:
        flussi["P_scambiatore_kW"] = np.nan
        flussi["limitato_da_HE"] = False
    for _c in ("costo_allacciamento_eur", "modello_HE", "note"):
        if _c not in flussi.columns:
            flussi[_c] = np.nan
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
        # compatibilita' con i vecchi nomi usati nei CSV: "Ex Bioman" e "Maniago
        # Sud" sono la stessa zona 2, ora chiamata "Caserme"
        buildings["cluster"] = buildings["cluster"].replace({
            "NE-Centro": "Zona 1 - Comune NE",
            "Caserme": "Zona 2 - Caserme",
            "Ex Bioman": "Zona 2 - Caserme",
            "Maniago Sud": "Zona 2 - Caserme",
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
        # I privati NON ereditano piu' il profilo dei pubblici: usano una forma
        # residenziale propria, con le due punte giornaliere. La stagionalita'
        # resta quella reale, ricavata dal fabbisogno orario aggregato degli
        # edifici gia' noti (che incorpora i gradi giorno di Maniago).
        _p = domanda.groupby("datetime")[["MWh_riscaldamento", "MWh_ACS"]].sum()
        _p = _p.reindex(domanda["datetime"].drop_duplicates().sort_values(), fill_value=0.0)
        _idx = _p.index
        _hdd_h = _p["MWh_riscaldamento"].values
        _agg = priv.groupby(["cluster", "anello"])[["MWh_SH", "MWh_ACS"]].sum().reset_index()
        _righe = []
        for r in _agg.itertuples():
            _nome = f"Privati {r.cluster} · est.{int(r.anello)}"
            _righe.append(pd.DataFrame({
                "datetime": _idx, "edificio": _nome,
                "MWh_riscaldamento": profilo_residenziale(_idx, r.MWh_SH, _hdd_h),
                "MWh_ACS": profilo_residenziale(_idx, r.MWh_ACS, quota_acs=1.0),
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
        # Anche i condomini seguono la forma residenziale. Rispetto alle case
        # singole la punta e' un po' piu' smussata perche' le utenze interne
        # sono gia' molte: se ne tiene conto con la contemporaneita' QM, che
        # agisce a valle sul picco di dimensionamento.
        _pubb = domanda[domanda["tipo_utenza"] == "Pubblico"]
        _p = _pubb.groupby("datetime")[["MWh_riscaldamento", "MWh_ACS"]].sum()
        _idx = _p.index
        _hdd_h = _p["MWh_riscaldamento"].values
        _righe_c = []
        for _z, _g in cond.groupby("cluster"):
            _u = float(_g["unita"].sum())
            _e = _u * MWH_PER_UNITA
            _nome = f"Condomini {_z}"
            _righe_c.append(pd.DataFrame({
                "datetime": _idx, "edificio": _nome,
                "MWh_riscaldamento": profilo_residenziale(_idx, _e * 0.85, _hdd_h),
                "MWh_ACS": profilo_residenziale(_idx, _e * 0.15, quota_acs=1.0),
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


# =============================================================================
# PANNELLI SOLARI IBRIDI (PVT)
# =============================================================================
# Dati di targa Abora aH72 M2 (scheda tecnica FICHATECNICA_241809_V1_IT).
# Certificazioni: DIN EN 12975-1, DIN EN ISO 9806, SolarKeymark, IEC 61215/61730.
#
# Nota sulla scheda tecnica: le voci "1.316 W/anno" (termico) e "1.800 W/anno"
# (elettrico) hanno unita' incoerenti e non sono utilizzabili come rese annue.
# Il modello usa invece i parametri fisici certificati (eta0, a1, a2 per il
# termico; Pmpp e coefficiente di temperatura per l'elettrico), che consentono
# di calcolare la resa ora per ora nelle condizioni reali di Maniago.
# Catalogo dei moduli ibridi considerati. I parametri termici sono quelli
# certificati EN ISO 9806 riportati nelle schede tecniche dei costruttori.
#
# Differenza sostanziale fra le due famiglie: l'Abora e' un modulo isolato e
# vetrato, con temperatura di stagnazione dichiarata a 126 C; i Fototherm sono
# moduli non isolati, con perdite maggiori e stagnazione intorno ai 68 C. Sopra
# i 60 C di esercizio i Fototherm rendono quindi pochissimo calore, mentre
# restano competitivi sul lato elettrico. Il manuale della serie AS fissa
# inoltre a 80 C la temperatura massima ammessa nel circuito solare.
CATALOGO_PVT = {
    "Abora aH72 M2 (vetrato e isolato)": {
        "nome": "Abora aH72 M2",
        "area_lorda_m2": 1.96, "area_apertura_m2": 1.88,
        "eta0": 0.70, "a1": 5.98, "a2": 0.00,
        "p_picco_w": 350.0, "eta_pv_stc": 0.178, "coeff_pmpp_pct_k": -0.36,
        "noct_c": 45.0, "t_ristagno_c": 126.0, "t_max_circuito_c": 100.0,
        "portata_l_h": 60.0, "peso_kg": 50.0,
        "note": ("Modulo vetrato e coibentato: perdite contenute (a1 = 5,98) e "
                 "quindi buona resa anche a temperature elevate. E' il piu' "
                 "adatto quando si vuole alimentare direttamente un anello caldo."),
    },
    "Fototherm FT320AS (non isolato)": {
        "nome": "Fototherm FT320AS",
        "area_lorda_m2": 1.63, "area_apertura_m2": 1.63,
        "eta0": 0.472, "a1": 7.96, "a2": 0.00,
        "p_picco_w": 320.0, "eta_pv_stc": 0.1967, "coeff_pmpp_pct_k": -0.38,
        "noct_c": 45.0, "t_ristagno_c": 67.0, "t_max_circuito_c": 80.0,
        "portata_l_h": 120.0, "peso_kg": 30.0,
        "note": ("Rendimento elettrico elevato (19,7 %) ma modulo non isolato: "
                 "stagnazione a circa 67 C e resa termica che crolla oltre i "
                 "50 C. Il manuale fissa a 80 C la massima temperatura di "
                 "circuito. Adatto a precaricare l'anello basso. Nota: la "
                 "potenza termica nominale dichiarata (827 W) implicherebbe "
                 "un'area di riferimento di 1,75 m2 contro i 1,63 m2 di area "
                 "lorda; qui si adotta l'ipotesi conservativa dell'area lorda."),
    },
    "Fototherm FT265CS (non isolato)": {
        "nome": "Fototherm FT265CS",
        "area_lorda_m2": 1.61, "area_apertura_m2": 1.59,
        "eta0": 0.56, "a1": 9.12, "a2": 0.00,
        "p_picco_w": 265.0, "eta_pv_stc": 0.165, "coeff_pmpp_pct_k": -0.41,
        "noct_c": 45.0, "t_ristagno_c": 69.0, "t_max_circuito_c": 80.0,
        "portata_l_h": 120.0, "peso_kg": 27.0,
        "note": ("Celle policristalline, rendimento elettrico inferiore (16,5 %) "
                 "ma rendimento ottico termico piu' alto della serie AS. Anche "
                 "questo non isolato: perdite elevate (a1 = 9,12) e stagnazione "
                 "intorno ai 69 C."),
    },
}


PVT_ABORA = {
    "nome": "Abora aH72 M2",
    "area_lorda_m2": 1.96,       # 1970 x 995 mm
    "area_apertura_m2": 1.88,
    "eta0": 0.70,                # efficienza ottica (rendimento a Tm = Ta)
    "a1": 5.98,                  # W/(m2*K)  perdite lineari
    "a2": 0.00,                  # W/(m2*K2) perdite quadratiche
    "p_picco_w": 350.0,          # potenza nominale STC
    "eta_pv_stc": 0.178,         # rendimento elettrico STC
    "coeff_pmpp_pct_k": -0.36,   # %/K sulla potenza
    "noct_c": 45.0,
    "t_ristagno_c": 126.0,
    "portata_l_h": 60.0,
    "peso_kg": 50.0,
}


def resa_pvt_oraria(G_wm2, T_amb_c, T_fluido_c, pvt=None,
                    perdite_bos=0.10, perdite_circuito=0.05):
    """Resa termica ed elettrica oraria di un campo PVT, per m2 di area lorda.

    Termico (EN ISO 9806):  eta = eta0 - a1*x - a2*G*x^2,  x = (Tm - Ta)/G
    Il rendimento scende al crescere della temperatura richiesta: alimentare
    l'anello caldo a 80 C rende molto meno che precaricare l'anello basso.

    Elettrico: P = Pmpp * (G/1000) * [1 + coeff*(T_cella - 25)], con la
    temperatura di cella stimata dal modello NOCT. Nel PVT il fluido raffredda
    il laminato, quindi la cella lavora piu' fredda e rende di piu' che nel
    fotovoltaico tradizionale: l'effetto e' incluso legando T_cella a T_fluido.

    Ritorna: (kWh_termici_per_m2, kWh_elettrici_per_m2) per l'ora considerata.
    """
    p = pvt or PVT_ABORA
    G = np.asarray(G_wm2, dtype=float)
    Ta = np.asarray(T_amb_c, dtype=float)
    Tm = np.asarray(T_fluido_c, dtype=float)

    # --- termico ---
    attivo = G > 20.0
    with np.errstate(divide="ignore", invalid="ignore"):
        x = np.where(attivo, (Tm - Ta) / np.maximum(G, 1e-6), 0.0)
    eta_th = p["eta0"] - p["a1"] * x - p["a2"] * G * x * x
    eta_th = np.clip(np.where(attivo, eta_th, 0.0), 0.0, p["eta0"])
    # riferito all'area di apertura, riportato all'area lorda
    q_th = eta_th * G * (p["area_apertura_m2"] / p["area_lorda_m2"])
    q_th = q_th / 1000.0 * (1.0 - perdite_circuito)      # kWh/(m2*h)

    # --- elettrico ---
    # T_cella: modello NOCT, corretto verso T_fluido per l'effetto di
    # raffreddamento attivo tipico del PVT.
    t_cella_pv = Ta + (p["noct_c"] - 20.0) / 800.0 * G
    t_cella = np.where(G > 20.0, 0.5 * t_cella_pv + 0.5 * (Tm + 5.0), Ta)
    fatt_t = 1.0 + p["coeff_pmpp_pct_k"] / 100.0 * (t_cella - 25.0)
    p_el_wp_m2 = p["p_picco_w"] / p["area_lorda_m2"]
    q_el = p_el_wp_m2 * (G / 1000.0) * fatt_t * (1.0 - perdite_bos)
    q_el = np.clip(q_el, 0.0, None) / 1000.0            # kWh/(m2*h)

    return q_th, q_el


@st.cache_data
def genera_offerta_pvt(pvgis_df, n_pannelli, T_fluido_c, pvt_nome=None):
    """Serie oraria annua di un campo PVT: calore utile ed elettricita'.

    T_fluido_c: temperatura media del fluido nei collettori. Coincide col
    livello termico che il campo deve alimentare (anello basso, intermedio
    o caldo): piu' e' alta, minore e' la resa termica.
    """
    p = CATALOGO_PVT.get(pvt_nome, PVT_ABORA) if pvt_nome else PVT_ABORA
    area = n_pannelli * p["area_lorda_m2"]
    # anno meteorologico con la variabilita' giorno per giorno conservata
    out = serie_meteo_annua(pvgis_df).copy()
    q_th, q_el = resa_pvt_oraria(out["G_totale"].values, out["T2m"].values,
                                 T_fluido_c, pvt=p)
    out["MWh_term"] = q_th * area / 1000.0
    out["MWh_el"] = q_el * area / 1000.0
    out["MWh"] = out["MWh_term"]          # per compatibilita' col dispatch
    out["P_kW"] = out["MWh_term"] * 1000.0
    out["fonte"] = "Solare ibrido PVT"
    out["T_disponibile"] = np.nan
    return out[["datetime", "fonte", "MWh", "MWh_term", "MWh_el", "P_kW", "T_disponibile"]]


@st.cache_data
def serie_meteo_annua(pvgis_df):
    """Anno meteorologico orario che conserva la sequenza reale dei giorni.

    La media per mese e ora produce un giorno tipo che si ripete uguale per
    tutto il mese: sparisce l'alternanza fra giornate serene e coperte, e con
    essa le sequenze di piu' giorni nuvolosi consecutivi. Ma sono proprio
    quelle a dimensionare l'accumulo: con un giorno tipo l'accumulo risulta
    sempre sufficiente e la taglia viene sottostimata.

    Qui si sceglie invece, per ciascun mese, un mese reale della serie storica:
    quello con irraggiamento piu' vicino alla media di lungo periodo (criterio
    del Typical Meteorological Year). La variabilita' giorno per giorno resta
    intatta, mentre i totali mensili restano rappresentativi.

    Ritorna un DataFrame sul calendario di HOURS_2024 con G_totale e T2m.
    """
    df = pvgis_df.copy()
    df["month"] = df["datetime"].dt.month
    df["anno"] = df["datetime"].dt.year
    df["day"] = df["datetime"].dt.day
    df["hour"] = df["datetime"].dt.hour

    anni = sorted(df["anno"].unique())
    if len(anni) <= 1:
        # una sola annata disponibile: la si usa cosi' com'e'
        scelta = {m: anni[0] for m in range(1, 13)}
    else:
        scelta = {}
        for m in range(1, 13):
            gm = df[df["month"] == m]
            if gm.empty:
                scelta[m] = anni[0]
                continue
            somme = gm.groupby("anno")["G_totale"].sum()
            # scarto gli anni incompleti, che falserebbero il confronto. Il
            # criterio e' il numero di ore registrate, non l'irraggiamento: con
            # la soglia sull'irraggiamento (80 % del mese piu' soleggiato) i mesi
            # invernali nuvolosi venivano scartati e la mediana dei rimanenti
            # gonfiava l'anno tipo del 13 % (1.907 invece di 1.681 kWh/m2).
            ore = gm.groupby("anno")["G_totale"].count()
            completi = ore[ore >= ore.max() * 0.9].index
            somme = somme.loc[completi] if len(completi) else somme
            scelta[m] = int((somme - somme.median()).abs().idxmin())

    pezzi = []
    for m in range(1, 13):
        gm = df[(df["month"] == m) & (df["anno"] == scelta[m])]
        pezzi.append(gm[["month", "day", "hour", "G_totale", "T2m"]])
    tipo = pd.concat(pezzi, ignore_index=True).drop_duplicates(
        subset=["month", "day", "hour"])

    out = pd.DataFrame({"datetime": HOURS_2024})
    out["month"] = out["datetime"].dt.month
    out["day"] = out["datetime"].dt.day
    out["hour"] = out["datetime"].dt.hour
    out = out.merge(tipo, on=["month", "day", "hour"], how="left")

    # 29 febbraio e altri buchi: ricopio il giorno precedente disponibile
    if out["G_totale"].isna().any():
        media_mh = tipo.groupby(["month", "hour"])[["G_totale", "T2m"]].mean()
        for col in ("G_totale", "T2m"):
            mask = out[col].isna()
            if mask.any():
                out.loc[mask, col] = [
                    media_mh.loc[(m, h), col] if (m, h) in media_mh.index else 0.0
                    for m, h in zip(out.loc[mask, "month"], out.loc[mask, "hour"])]
    return out[["datetime", "month", "hour", "G_totale", "T2m"]]


@st.cache_data
def genera_offerta_solare(pvgis_df, area_m2, efficienza):
    """Serie oraria di un campo solare termico tradizionale.

    Usa l'anno meteorologico con la variabilita' giorno per giorno conservata:
    una sequenza di giornate coperte produce davvero un buco di piu' giorni,
    che e' cio' che mette alla prova l'accumulo.
    """
    meteo = serie_meteo_annua(pvgis_df)
    df_h = meteo[["datetime"]].copy()
    df_h["P_kW"] = meteo["G_totale"].values * area_m2 * efficienza / 1000.0
    df_h["MWh"] = df_h["P_kW"] / 1000.0
    df_h["fonte"] = "Solare termico"
    df_h["T_disponibile"] = np.nan
    return df_h[["datetime", "fonte", "MWh", "P_kW", "T_disponibile"]]


# =============================================================================
# ECONOMIA
# =============================================================================
# =============================================================================
# SCHEDA PDF DI CONFRONTO SCENARI
# =============================================================================
def genera_pdf_scenari(scenari, titolo="Confronto scenari"):
    """Scheda PDF sinottica degli scenari salvati.

    Ritorna i byte del PDF, oppure None se reportlab non e' disponibile.
    Il formato e' orizzontale per far stare piu' scenari affiancati.
    """
    try:
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib import colors
        from reportlab.lib.units import mm
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import (SimpleDocTemplate, Table, TableStyle,
                                        Paragraph, Spacer)
    except ImportError:
        return None
    import io
    from datetime import date

    if not scenari:
        return None

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4),
                            leftMargin=14 * mm, rightMargin=14 * mm,
                            topMargin=12 * mm, bottomMargin=12 * mm,
                            title=titolo, author="APE FVG - Interreg HEAT 35")
    ss = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=ss["Title"], fontSize=16, spaceAfter=2)
    sub = ParagraphStyle("sub", parent=ss["Normal"], fontSize=8,
                         textColor=colors.HexColor("#666666"))
    sez = ParagraphStyle("sez", parent=ss["Normal"], fontSize=9,
                         textColor=colors.HexColor("#1B4F72"), spaceBefore=6)
    note = ParagraphStyle("note", parent=ss["Normal"], fontSize=7,
                          textColor=colors.HexColor("#666666"), leading=9)

    el = [Paragraph("Maniago · rete di teleriscaldamento", h1),
          Paragraph(f"{titolo} — {len(scenari)} scenari a confronto · "
                    f"elaborato il {date.today():%d/%m/%Y} · "
                    f"progetto Interreg HEAT 35, APE FVG", sub),
          Spacer(1, 6)]

    nomi = list(scenari.keys())

    # Le righe sono raggruppate per tema: cosi' la scheda si legge per blocchi
    # invece che come un elenco piatto di numeri.
    gruppi = [
        ("Utenza e rete", [
            ("carico_utenze_mwh", "Calore venduto", "MWh/a", 0),
            ("carico_centrale_mwh", "Calore prodotto in centrale", "MWh/a", 0),
            ("perdite_rete_pct", "Perdite di rete", "%", 1),
            ("lunghezza_rete_m", "Lunghezza rete", "m", 0),
            ("densita_lineare", "Densità lineare", "MWh/(m·a)", 2),
            ("picco_dim_kw", "Picco di dimensionamento", "kW", 0),
            ("dn_dorsale", "Diametro dorsale", "DN", 0),
        ]),
        ("Impianto", [
            ("tecnologie", "Assetto", "", None),
            ("P_alta_kw", "HP alta temperatura", "kW", 0),
            ("P_bassa_kw", "HP bassa temperatura", "kW", 0),
            ("P_backup_kw", "Caldaia di supporto", "kW", 0),
            ("V_hot", "Accumulo caldo", "mc", 0),
            ("V_int", "Accumulo intermedio", "mc", 0),
            ("V_low", "Accumulo basso", "mc", 0),
        ]),
        ("Bilancio energetico", [
            ("E_hot_diretto", "Scarto usato direttamente", "MWh/a", 0),
            ("E_hp_alta", "Consegnato da HP alta T", "MWh/a", 0),
            ("E_backup", "Da combustibile", "MWh/a", 0),
            ("E_elettrica", "Elettricità assorbita", "MWh/a", 0),
            ("cop_alta", "COP medio HP alta T", "", 2),
            ("spf_sistema", "SPF di sistema", "", 2),
            ("ore_non_coperte", "Ore non coperte", "h", 0),
        ]),
        ("Sostenibilità", [
            ("quota_fer_pct", "Quota FER", "%", 1),
            ("pct_scarto_su_domanda", "Scarto utilizzato / domanda", "%", 1),
            ("pct_rinnovabile", "Rinnovabile / fornito", "%", 1),
            ("co2_evitata_t", "CO2 evitata", "t/a", 0),
        ]),
        ("Economia", [
            ("capex_sistema", "CAPEX centrale", "€", 0),
            ("capex_rete", "CAPEX rete", "€", 0),
            ("costo_calore_acquistato", "Acquisto calore di scarto", "€/a", 0),
            ("opex_annuo", "OPEX", "€/a", 0),
            ("lcoh", "LCOH di sistema", "€/MWh", 1),
        ]),
    ]

    def fmt(v, dec):
        if v is None or v == "—":
            return "—"
        if dec is None or isinstance(v, str):
            # i testi lunghi vengono spezzati per non sbordare dalla colonna
            t = str(v)
            return t if len(t) <= 22 else t.replace(" + ", "\n+ ")
        try:
            f = float(v)
        except (TypeError, ValueError):
            return str(v)[:38]
        s = f"{f:,.{dec}f}"
        return s.replace(",", "@").replace(".", ",").replace("@", ".")

    dati = [["Indicatore"] + nomi]
    stile = [
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7.5),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1B4F72")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CCCCCC")),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]
    r = 1
    for nome_gr, campi in gruppi:
        dati.append([nome_gr] + [""] * len(nomi))
        stile += [("BACKGROUND", (0, r), (-1, r), colors.HexColor("#D6EAF8")),
                  ("FONTNAME", (0, r), (-1, r), "Helvetica-Bold"),
                  ("SPAN", (0, r), (-1, r))]
        r += 1
        for chiave, etichetta, unita, dec in campi:
            eti = f"{etichetta} ({unita})" if unita else etichetta
            dati.append([eti] + [fmt(scenari[n].get(chiave), dec) for n in nomi])
            if r % 2 == 0:
                stile.append(("BACKGROUND", (0, r), (-1, r), colors.HexColor("#FAFAFA")))
            r += 1

    # --- tutti gli altri risultati salvati nello scenario, senza perderne nessuno ---
    _gia = {c for _, campi in gruppi for c, *_ in campi} | {"ipotesi", "salvato_il"}
    _altri = sorted({k for n in nomi for k in scenari[n].keys()} - _gia)
    if _altri:
        dati.append(["Altri risultati salvati"] + [""] * len(nomi))
        stile += [("BACKGROUND", (0, r), (-1, r), colors.HexColor("#D6EAF8")),
                  ("FONTNAME", (0, r), (-1, r), "Helvetica-Bold"),
                  ("SPAN", (0, r), (-1, r))]
        r += 1
        for chiave in _altri:
            _vals = [scenari[n].get(chiave) for n in nomi]
            _dec = 2 if any(isinstance(v, float) for v in _vals) else 0
            dati.append([chiave.replace("_", " ")] + [fmt(v, _dec) for v in _vals])
            if r % 2 == 0:
                stile.append(("BACKGROUND", (0, r), (-1, r), colors.HexColor("#FAFAFA")))
            r += 1

    larg = [72 * mm] + [(196 - 72) / max(len(nomi), 1) * mm] * len(nomi)
    t = Table(dati, colWidths=larg, repeatRows=1)
    t.setStyle(TableStyle(stile))
    el.append(t)

    # --- IPOTESI E DATI INSERITI: tutti i comandi impostati al salvataggio ---
    from reportlab.platypus import PageBreak
    cella = ParagraphStyle("cella", parent=ss["Normal"], fontSize=6.5, leading=8)
    cella_b = ParagraphStyle("cella_b", parent=cella, fontName="Helvetica-Bold")

    def _txt(v):
        if v is None or v == "":
            return "—"
        if isinstance(v, bool):
            return "sì" if v else "no"
        if isinstance(v, dict):
            return "; ".join(f"{k}: {_txt(x)}" for k, x in v.items()) or "—"
        if isinstance(v, list):
            return ", ".join(_txt(x) for x in v) or "—"
        if isinstance(v, float):
            s_ = f"{v:,.3f}".rstrip("0").rstrip(".")
            return s_.replace(",", "@").replace(".", ",").replace("@", ".")
        if isinstance(v, int):
            return f"{v:,}".replace(",", ".")
        return str(v)

    def _esc(t_):
        # i font standard del PDF non hanno emoji ne' apici/pedici: si
        # sostituiscono i simboli comuni e si tolgono gli altri
        t_ = str(t_)
        for a_, b_ in (("³", "3"), ("²", "2"), ("₂", "2"), ("η", "eta"), ("Δ", "delta"),
                       ("→", "->"), ("·", "·"), ("×", "x")):
            t_ = t_.replace(a_, b_)
        t_ = "".join(c for c in t_ if ord(c) <= 0xFF or c == "€").strip()
        return t_.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    _ip = {n: (scenari[n].get("ipotesi") or {}) for n in nomi}
    if any(_ip.values()):
        el.append(PageBreak())
        el.append(Paragraph("Ipotesi e dati inseriti", h1))
        el.append(Paragraph(
            "Valori di tutti i comandi delle schede Domanda, Offerta, Dimensionamento, "
            "Carico elettrico e Analisi economica al momento del salvataggio di ciascuno "
            "scenario. Le righe in cui gli scenari differiscono sono evidenziate.", sub))
        el.append(Spacer(1, 4))
        _salv = [scenari[n].get("salvato_il", "—") for n in nomi]
        dati_i = [[Paragraph("<b>Ipotesi</b>", cella)]
                  + [Paragraph(f"<b>{_esc(n)}</b><br/>salvato il {_esc(s_)}", cella)
                     for n, s_ in zip(nomi, _salv)]]
        stile_i = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D6EAF8")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CCCCCC")),
            ("TOPPADDING", (0, 0), (-1, -1), 1.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
            ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ]
        ri = 1
        # elenchi (zone, edifici, flussi, prezzi)
        _nomi_el = []
        for n in nomi:
            for k in (_ip[n].get("elenchi") or {}):
                if k not in _nomi_el:
                    _nomi_el.append(k)
        if _nomi_el:
            dati_i.append([Paragraph("Selezioni", cella_b)] + [""] * len(nomi))
            stile_i += [("SPAN", (0, ri), (-1, ri)),
                        ("BACKGROUND", (0, ri), (-1, ri), colors.HexColor("#EAF2F8"))]
            ri += 1
            for k in _nomi_el:
                _vals = [(_ip[n].get("elenchi") or {}).get(k) for n in nomi]
                dati_i.append([Paragraph(_esc(k), cella)]
                              + [Paragraph(_esc(_txt(v)), cella) for v in _vals])
                if len({_txt(v) for v in _vals}) > 1:
                    stile_i.append(("BACKGROUND", (1, ri), (-1, ri), colors.HexColor("#FFF4D6")))
                ri += 1
        # parametri, raggruppati per scheda nell'ordine dell'app
        _par = {}
        _ord = []
        for n in nomi:
            for p_ in (_ip[n].get("parametri") or []):
                _ch = p_.get("chiave")
                if _ch not in _par:
                    _par[_ch] = (p_.get("scheda", ""), p_.get("ipotesi", _ch))
                    _ord.append(_ch)
        _rank = {s_: i for i, (_, s_) in enumerate(_SCHEDE_IPOTESI)}
        _ord.sort(key=lambda c: (_rank.get(_par[c][0], 9), _par[c][1].lower()))
        _sch_corr = None
        for _ch in _ord:
            _sch, _lab = _par[_ch]
            if _sch != _sch_corr:
                dati_i.append([Paragraph(_esc(_sch), cella_b)] + [""] * len(nomi))
                stile_i += [("SPAN", (0, ri), (-1, ri)),
                            ("BACKGROUND", (0, ri), (-1, ri), colors.HexColor("#EAF2F8"))]
                ri += 1
                _sch_corr = _sch
            _vals = []
            for n in nomi:
                _m = next((p_ for p_ in (_ip[n].get("parametri") or [])
                           if p_.get("chiave") == _ch), None)
                _vals.append(_m.get("valore") if _m else None)
            dati_i.append([Paragraph(_esc(_lab), cella)]
                          + [Paragraph(_esc(_txt(v)), cella) for v in _vals])
            if len({_txt(v) for v in _vals}) > 1:
                stile_i.append(("BACKGROUND", (1, ri), (-1, ri), colors.HexColor("#FFF4D6")))
            ri += 1
        _li = [80 * mm] + [(269 - 80) / max(len(nomi), 1) * mm] * len(nomi)
        t_i = Table(dati_i, colWidths=_li, repeatRows=1)
        t_i.setStyle(TableStyle(stile_i))
        el.append(t_i)
        _senza = [n for n in nomi if not _ip[n]]
        if _senza:
            el.append(Spacer(1, 4))
            el.append(Paragraph(
                "Scenari salvati con una versione precedente dell'app, senza la "
                "fotografia delle ipotesi: " + _esc(", ".join(_senza)) + ".", note))

    el.append(Spacer(1, 8))
    el.append(Paragraph(
        "Metodologia: QM Holzheizwerke Planning Handbook (perdite di rete Fig. 12.3, "
        "contemporaneità Fig. 12.2), Verenum Planungshandbuch Fernwärme, IEA DHC Annex TS5 "
        "(COP e CAPEX delle pompe di calore, accumuli termici). "
        "La CO2 evitata e' calcolata rispetto a caldaie a gas individuali "
        "(0,20 t/MWh, rendimento 90 %) al netto delle emissioni del mix elettrico. "
        "Il LCOH riportato è quello di sistema (sola centrale, riferito al calore prodotto): "
        "non coincide con il LCOH completo della scheda di analisi economica, che include "
        "rete, O&amp;M e personale ed è riferito al calore venduto.", note))
    el.append(Spacer(1, 4))
    el.append(Paragraph(
        "Documento di supporto allo studio di fattibilità: i risultati dipendono dalla "
        "qualità dei dati di ingresso e dalle ipotesi selezionate, e non sostituiscono "
        "un progetto esecutivo.", note))

    doc.build(el)
    return buf.getvalue()


# =============================================================================
# COPERTURA DEL CARICO ELETTRICO
# =============================================================================
def dispatch_elettrico(produzione, consumo, batteria_mwh=0.0, p_batt_mw=None,
                       eff_batt=0.90, soc_iniziale=0.2):
    """Bilancio elettrico orario fra produzione rinnovabile e consumo.

    Ordine di merito, come nel toolkit H2Ready: la produzione copre prima il
    consumo istantaneo, l'eccedenza carica la batteria, cio' che resta viene
    immesso in rete; il deficit viene coperto dalla batteria e infine prelevato
    dalla rete.

    Il rendimento di ciclo si applica meta' in carica e meta' in scarica
    (radice quadrata), cosi' il rendimento complessivo di andata e ritorno
    coincide con quello dichiarato.

    Args:
        produzione: serie oraria di generazione (MWh)
        consumo: serie oraria di assorbimento (MWh)
        batteria_mwh: capacita' utile dell'accumulo
        p_batt_mw: potenza massima in carica e scarica; se assente si assume
            una taglia da un'ora (C-rate 1)
        eff_batt: rendimento di ciclo completo

    Ritorna un dizionario con le serie orarie e gli aggregati annui.
    """
    prod = np.asarray(produzione, dtype=float)
    cons = np.asarray(consumo, dtype=float)
    n = len(cons)
    if len(prod) != n:
        prod = np.resize(prod, n)

    autoc_diretto = np.minimum(prod, cons)
    surplus = prod - autoc_diretto
    deficit = cons - autoc_diretto

    carica = np.zeros(n)
    scarica = np.zeros(n)
    soc_serie = np.zeros(n)

    if batteria_mwh > 0:
        p_max = float(p_batt_mw) if p_batt_mw else float(batteria_mwh)
        se = np.sqrt(eff_batt)
        soc = batteria_mwh * soc_iniziale
        for t in range(n):
            if surplus[t] > 0:
                c = min(surplus[t], (batteria_mwh - soc) / se, p_max)
                if c > 0:
                    soc += c * se
                    carica[t] = c
                    surplus[t] -= c
            elif deficit[t] > 0:
                d = min(deficit[t], soc * se, p_max)
                if d > 0:
                    soc -= d / se
                    scarica[t] = d
                    deficit[t] -= d
            soc_serie[t] = soc

    immesso = surplus
    prelevato = deficit
    autoconsumo = autoc_diretto + scarica

    tot_cons = float(cons.sum())
    tot_prod = float(prod.sum())
    return {
        "autoconsumo_diretto": autoc_diretto, "carica": carica, "scarica": scarica,
        "immesso": immesso, "prelevato": prelevato, "soc": soc_serie,
        "autoconsumo": autoconsumo,
        "E_consumo": tot_cons, "E_produzione": tot_prod,
        "E_autoconsumo": float(autoconsumo.sum()),
        "E_immesso": float(immesso.sum()), "E_prelevato": float(prelevato.sum()),
        "E_carica": float(carica.sum()), "E_scarica": float(scarica.sum()),
        # quota del consumo coperta da produzione propria
        "copertura_pct": float(autoconsumo.sum()) / tot_cons * 100 if tot_cons > 0 else 0.0,
        # quota della produzione consumata sul posto invece che immessa
        "autoconsumo_pct": float(autoconsumo.sum()) / tot_prod * 100 if tot_prod > 0 else 0.0,
        "ore_autosufficienti": int((prelevato < 1e-9).sum()),
    }


@st.cache_data
def carica_prezzi_elettrici(percorso="prezzi_elettrici.csv"):
    """Serie oraria dei prezzi zonali.

    Usa il file esterno se presente, altrimenti un profilo di riserva ricavato
    dai prezzi zona Nord 2025 (media 116 €/MWh). Il profilo di riserva conserva
    l'andamento giornaliero, che e' cio' che conta per l'autoconsumo: l'energia
    solare vale meno perche' arriva quando il prezzo e' depresso.
    """
    if os.path.exists(percorso):
        try:
            df = pd.read_csv(percorso, parse_dates=["datetime"])
            s = df.set_index("datetime")["prezzo"].reindex(HOURS_2024)
            if s.notna().sum() > 8000:
                return s.interpolate().bfill().ffill().values, "file esterno"
        except Exception:
            pass
    # profilo di riserva: fattori orari applicati alla media mensile
    fattori_ora = np.array([0.97, 0.93, 0.89, 0.89, 0.92, 1.00,
                            1.08, 1.10, 1.06, 0.97, 0.88, 0.81,
                            0.81, 0.83, 0.86, 0.90, 1.02, 1.18,
                            1.18, 1.14, 1.09, 1.05, 1.02, 0.99])
    medie_mese = np.array([137, 128, 108, 96, 84, 92,
                           108, 112, 108, 118, 128, 124], dtype=float)
    m = HOURS_2024.month.values - 1
    h = HOURS_2024.hour.values
    return medie_mese[m] * fattori_ora[h], "profilo interno (zona Nord 2025)"


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


# =============================================================================
# STRUTTURA FINANZIARIA
# =============================================================================
def piano_ammortamento_debito(capitale, tasso_annuo, anni, rate_per_anno=2):
    """Piano di ammortamento francese, aggregato per anno.

    Il calcolo procede per rata (semestrale per impostazione predefinita, come
    nella prassi del project financing) e viene poi sommato per anno, perche'
    aggregare direttamente su base annua sottostima gli interessi.

    Ritorna un DataFrame con quota interessi, quota capitale, rata e debito
    residuo per ciascun anno.
    """
    if capitale <= 0 or anni <= 0:
        return pd.DataFrame(columns=["anno", "rata", "interessi", "capitale", "residuo"])
    i_per = (1.0 + tasso_annuo) ** (1.0 / rate_per_anno) - 1.0
    n_rate = int(anni * rate_per_anno)
    if i_per <= 0:
        rata = capitale / n_rate
    else:
        rata = capitale * (i_per * (1 + i_per) ** n_rate) / ((1 + i_per) ** n_rate - 1)
    saldo = float(capitale)
    righe = []
    for k in range(n_rate):
        interesse = saldo * i_per
        quota_cap = rata - interesse
        saldo -= quota_cap
        righe.append({"periodo": k + 1, "rata": rata, "interessi": interesse,
                      "capitale": quota_cap, "residuo": max(saldo, 0.0)})
    df = pd.DataFrame(righe)
    df["anno"] = ((df["periodo"] - 1) // rate_per_anno) + 1
    out = df.groupby("anno").agg(rata=("rata", "sum"),
                                 interessi=("interessi", "sum"),
                                 capitale=("capitale", "sum"),
                                 residuo=("residuo", "last")).reset_index()
    return out


def conto_economico(anni, ricavi_0, costi_op_0, capex_lordo, contributo,
                    quota_debito, tasso_debito, anni_debito,
                    aliquota_imposte=0.24, anni_ammortamento=20,
                    esc_ricavi=0.02, esc_costi=0.03, rate_per_anno=2):
    """Conto economico e flussi di cassa del progetto, anno per anno.

    Distingue il flusso disponibile per il servizio del debito da quello per
    l'azionista, e calcola le imposte sul reddito imponibile (quindi al netto
    di ammortamenti e interessi passivi, che sono deducibili): trascurarli
    sovrastima il carico fiscale e con esso il costo del calore.

    Ritorna un DataFrame con una riga per anno e un dizionario di sintesi.
    """
    capex_netto = capex_lordo - contributo
    debito = capex_netto * quota_debito
    equity = capex_netto - debito
    piano = piano_ammortamento_debito(debito, tasso_debito, anni_debito, rate_per_anno)
    amm_annuo = (capex_lordo - contributo) / max(anni_ammortamento, 1)

    righe = []
    for t in range(1, anni + 1):
        ric = ricavi_0 * (1 + esc_ricavi) ** (t - 1)
        cos = costi_op_0 * (1 + esc_costi) ** (t - 1)
        ebitda = ric - cos
        amm = amm_annuo if t <= anni_ammortamento else 0.0
        ebit = ebitda - amm
        _r = piano[piano["anno"] == t]
        interessi = float(_r["interessi"].iloc[0]) if len(_r) else 0.0
        quota_cap = float(_r["capitale"].iloc[0]) if len(_r) else 0.0
        residuo = float(_r["residuo"].iloc[0]) if len(_r) else 0.0
        ebt = ebit - interessi
        imposte = max(ebt, 0.0) * aliquota_imposte
        utile = ebt - imposte
        # il flusso operativo riprende l'ammortamento, che non e' un'uscita
        fcf_progetto = ebitda - imposte
        fcf_equity = fcf_progetto - interessi - quota_cap
        dscr = (fcf_progetto / (interessi + quota_cap)
                if (interessi + quota_cap) > 1e-9 else np.nan)
        righe.append({
            "anno": t, "ricavi": ric, "costi_operativi": cos, "ebitda": ebitda,
            "ammortamenti": amm, "ebit": ebit, "interessi": interessi,
            "ebt": ebt, "imposte": imposte, "utile_netto": utile,
            "quota_capitale": quota_cap, "debito_residuo": residuo,
            "fcf_progetto": fcf_progetto, "fcf_equity": fcf_equity, "dscr": dscr,
        })
    df = pd.DataFrame(righe)

    flussi_progetto = [-capex_netto] + df["fcf_progetto"].tolist()
    flussi_equity = [-equity] + df["fcf_equity"].tolist()
    dscr_validi = df["dscr"].replace([np.inf, -np.inf], np.nan).dropna()
    return df, {
        "capex_lordo": capex_lordo, "contributo": contributo,
        "capex_netto": capex_netto, "debito": debito, "equity": equity,
        "flussi_progetto": flussi_progetto, "flussi_equity": flussi_equity,
        "interessi_totali": float(df["interessi"].sum()),
        "imposte_totali": float(df["imposte"].sum()),
        "dscr_min": float(dscr_validi.min()) if len(dscr_validi) else np.nan,
        "dscr_medio": float(dscr_validi.mean()) if len(dscr_validi) else np.nan,
    }


def prezzo_di_equilibrio(energia_venduta, quota_fissa_tot, anni, costi_op_0,
                         capex_lordo, contributo, quota_debito, tasso_debito,
                         anni_debito, tasso_van, **kw):
    """Prezzo di vendita del calore che annulla il valore attuale netto.

    E' il costo minimo a cui il progetto sta in piedi: sotto questa soglia
    l'investimento distrugge valore. Si cerca per bisezione, sfruttando il
    fatto che il VAN cresce in modo monotono col prezzo.
    """
    if energia_venduta <= 0:
        return None

    def _van_a(prezzo):
        ric = energia_venduta * prezzo + quota_fissa_tot
        _, s = conto_economico(anni, ric, costi_op_0, capex_lordo, contributo,
                               quota_debito, tasso_debito, anni_debito, **kw)
        return van(s["flussi_progetto"], tasso_van)

    lo, hi = 0.0, 1000.0
    if _van_a(hi) < 0:
        return None
    for _ in range(60):
        mid = (lo + hi) / 2.0
        if _van_a(mid) < 0:
            lo = mid
        else:
            hi = mid
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

# Il carico elettrico non e' piu' una scheda a se': e' il passo 4 del
# Dimensionamento, fra "Taglie e accumuli" e "Risultati".
(tab_domanda, tab_offerta, tab_dimensionamento,
 tab_confronto, tab_economia) = st.tabs(
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
        # Si contano le utenze che si ALLACCIANO davvero: i privati in base al
        # tasso di allacciamento, i condomini in base al tasso di adesione.
        # Contare tutti i potenziali sovrastimava la contemporaneita' (e quindi
        # sottostimava il picco di dimensionamento).
        _n_priv_reale = 0
        _fatt_all_qm = (fattore_correzione / 100.0) if sel_priv_zone else 1.0
        if sel_priv_zone and not privati.empty:
            _n_priv_reale += int(round(len(privati[privati["cluster"].isin(sel_priv_zone)])
                                       * _fatt_all_qm))
        _n_cond_uni = 0
        if sel_cond_zone and not condomini.empty:
            _n_cond_uni = int(round(condomini[condomini["cluster"].isin(sel_cond_zone)]["unita"].sum()
                                    * tasso_cond / 100.0))
            _n_priv_reale += _n_cond_uni
        # Se un buffer sul tracciato ha ristretto i privati agganciabili, correggo
        # anche il conteggio utenze per la contemporaneita QM.
        _buff_records_qm = st.session_state.get("_dom_priv_in_buffer", None)
        if _buff_records_qm is not None and sel_priv_zone and not privati.empty:
            _n_priv_zone_tot = int(len(privati[privati["cluster"].isin(sel_priv_zone)]))
            if _n_priv_zone_tot > 0:
                # scalo la parte "privati" (non i condomini) alla quota buffer
                _n_priv_reale = int(round(len(_buff_records_qm) * _fatt_all_qm)) + _n_cond_uni
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

    # ------------------------------------------------------------------
    # Selezione per SINGOLO edificio pubblico.
    # Le checkbox vere sono disegnate piu sotto (area centrale), qui leggo
    # il loro stato da session_state: al primo giro non esiste ancora e il
    # default e' "tutti attivi".
    # ------------------------------------------------------------------
    _pub_candidati = buildings[(buildings["tipo_utenza"] == "Pubblico")
                               & buildings["cluster"].isin(selected_clusters)
                               & buildings["tipologia"].isin(selected_tip)].copy()
    _pub_candidati = _pub_candidati.sort_values("consumo_annuo_MWh", ascending=False)
    _pub_scelti = [e for e in _pub_candidati["edificio"]
                   if st.session_state.get(f"dom_ed_{e}", e not in PUBBLICI_NON_SPUNTATI)]
    st.session_state["_dom_pub_scelti"] = _pub_scelti

    mask_building = (buildings["cluster"].isin(selected_clusters)
                     & (((buildings["tipo_utenza"] == "Pubblico") & pub_on
                         & buildings["edificio"].isin(_pub_scelti))
                        | buildings["edificio"].isin(selected_privati)))
    selected_buildings = buildings.loc[mask_building, "edificio"].tolist()

    # Se il buffer sul tracciato ha ristretto i privati agganciabili, correggo
    # il fattore di allacciamento in modo che rappresenti la quota realmente
    # servita rispetto al totale della zona. Aggregando su zona/anello questo
    # e l'unico modo di rispettare il vincolo geometrico senza cambiare i dati.
    # La quota si calcola sull'ENERGIA e non sul numero di edifici: i privati
    # lungo il tubo sono in media piu' grandi di quelli della zona, quindi la
    # quota per conteggio sottostimava la domanda rispetto a quella che la rete
    # dichiara di servire (es. 1.893 contro 2.146 MWh/a).
    _buff_records = st.session_state.get("_dom_priv_in_buffer", None)
    _priv_zone_totali = 0.0
    _priv_zone_buffer = 0.0
    if sel_priv_zone and not privati.empty:
        _priv_zone_totali = float(privati.loc[privati["cluster"].isin(sel_priv_zone),
                                              "consumo_annuo_MWh"].sum())
    if _buff_records is not None:
        _priv_zone_buffer = float(sum(float(r.get("consumo_annuo_MWh", 0.0) or 0.0)
                                      for r in _buff_records))
    quota_buffer = (min(_priv_zone_buffer / _priv_zone_totali, 1.0)
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

    # Edifici effettivamente SERVITI dalla rete. Valore iniziale = selezionati;
    # la sezione del tracciato, piu' sotto, lo restringe togliendo i pubblici
    # potati o privi di coordinate. Dimensionamento e Analisi economica leggono
    # questo elenco, cosi' ricavi e taglie si riferiscono al calore che la rete
    # tracciata consegna davvero e non a quello solo selezionato.
    st.session_state["_dom_edifici_serviti"] = list(selected_buildings)
    st.session_state["_dom_fattore_condomini"] = fatt_c
    st.session_state["_dom_esclusi_rete"] = []

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
                        fig_map.add_trace(go.Scattermap(
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
                    fig_map.add_trace(go.Scattermap(
                        lat=sub["lat"], lon=sub["lon"], mode="markers", name=cl,
                        marker=dict(size=(sub["consumo_annuo_MWh"].clip(lower=1) ** 0.5) * 2.5 + 7,
                                    color=CLUSTER_COLORS.get(cl, "#888888")),
                        text=(sub["edificio"] + "<br>" + sub["indirizzo"].fillna("").astype(str)
                              + "<br>" + sub["consumo_annuo_MWh"].round(0).astype(int).astype(str) + " MWh/a"),
                        hoverinfo="text"))
                if sel_priv_zone and not privati.empty:
                    _pv = privati[privati["cluster"].isin(sel_priv_zone)]
                    if not _pv.empty:
                        fig_map.add_trace(go.Scattermap(
                            lat=_pv["lat"], lon=_pv["lon"], mode="markers",
                            name=f"Privati: {len(_pv)}",
                            marker=dict(size=6, color="#B57EDC", opacity=0.75),
                            text=(_pv["nome"].fillna("").astype(str) + "<br>"
                                  + _pv["via"].fillna("").astype(str)
                                  + "<br>est." + _pv["anello"].astype(str) + " · "
                                  + _pv["consumo_annuo_MWh"].round(1).astype(str) + " MWh/a"),
                            hoverinfo="text"))
                fig_map.update_layout(
                    **layout_mappa(float(bmap["lat"].mean()), float(bmap["lon"].mean()), 13),
                    height=430, margin=dict(t=10, b=0, l=0, r=0),
                    legend=dict(orientation="h", yanchor="bottom", y=1.01))
                st.plotly_chart(fig_map, width="stretch")
                _pub_senza = bsel[(bsel["tipo_utenza"] == "Pubblico")
                                  & (bsel["lat"].isna() | bsel["lon"].isna())]
                if not _pub_senza.empty:
                    st.warning(
                        f"⚠️ {len(_pub_senza)} edifici pubblici selezionati non hanno "
                        f"coordinate in `edifici_pubblici_coordinate.csv` (controlla che "
                        f"il nome coincida con quello del file della domanda): "
                        + ", ".join(f"**{e}**" for e in _pub_senza["edificio"])
                        + ". Non possono essere collegati al tracciato e restano esclusi "
                          "da dimensionamento e analisi economica ("
                        + f"{_pub_senza['consumo_annuo_MWh'].sum():,.0f}".replace(",", ".")
                        + " MWh/a).")

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
                    fig_dens = go.Figure(go.Densitymap(
                        lat=_grid["lat"], lon=_grid["lon"], z=_grid["dens"],
                        radius=max(18, int(cella_m / 6)), colorscale="Turbo", opacity=0.75,
                        colorbar=dict(title="MWh/(ha·a)"),
                        hovertemplate="%{z:.0f} MWh/(ha·a)<extra></extra>"))
                    for _zid, _anelli in carica_zone_confini().items():
                        _nm = ZONE_NOMI.get(_zid, "")
                        for _r in _anelli:
                            fig_dens.add_trace(go.Scattermap(
                                lat=list(_r[:, 1]) + [_r[0, 1]], lon=list(_r[:, 0]) + [_r[0, 0]],
                                mode="lines", showlegend=False, hoverinfo="skip",
                                line=dict(width=1.5, color=ZONA_COLORI.get(_nm, "#888")), opacity=0.8))
                    fig_dens.update_layout(
                        **layout_mappa(_la0, float(_pts["lon"].mean()), 12.6, stile="scuro"),
                        height=460, margin=dict(t=10, b=0, l=0, r=0))
                    st.plotly_chart(fig_dens, width="stretch")
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
            st.plotly_chart(fig, width="stretch")

            view_mode = st.radio("Bilancio mensile per:", ["Cluster di rete", "Componente (risc./ACS)"],
                                 horizontal=True, key="dom_view")

            st.markdown("**Curva di durata**")
            durata = agg_total.sort_values("MWh_sel", ascending=False).reset_index(drop=True)
            durata["ore"] = durata.index + 1
            fig_d = px.area(durata, x="ore", y="MWh_sel", labels={"ore": "Ore/anno", "MWh_sel": "MW"})
            fig_d.update_traces(line_color=COLOR_RISCALDAMENTO)
            fig_d.update_layout(height=420)
            st.plotly_chart(fig_d, width="stretch")

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
            st.plotly_chart(fig_m, width="stretch")

            with st.expander("Dettaglio per edificio (zone, tipologia, ACS separata)"):
                detail = dom.groupby(["edificio", "cluster", "tipologia"])[["MWh_riscaldamento", "MWh_ACS"]].sum()
                detail["Totale MWh"] = detail["MWh_riscaldamento"] + detail["MWh_ACS"]
                detail = detail.rename(columns={"MWh_riscaldamento": "Riscaldamento MWh", "MWh_ACS": "ACS MWh"})
                detail = detail.sort_values("Totale MWh", ascending=False).reset_index()
                st.dataframe(detail, width="stretch", hide_index=True)

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
            costo_m_rete = cD1.slider("Costo rete (\u20ac/m di trincea)", 200, 1500, 350, step=50,
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
                st.plotly_chart(fig_dl, width="stretch")
                st.dataframe(df_d, width="stretch", hide_index=True)
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
            st.dataframe(_tab, width="stretch", hide_index=True)

        st.divider()
        st.markdown("##### \U0001F3DB\ufe0f Edifici pubblici della dorsale")
        st.caption("Spunta gli edifici che la **dorsale principale** deve raggiungere. "
                   "Il tracciato viene ricostruito su questa selezione; condomini e privati "
                   "si agganciano poi come rami secondari.")

        if _pub_candidati.empty:
            st.info("Nessun edificio pubblico nelle zone selezionate.")
        else:
            _bs1, _bs2, _bs3 = st.columns([1, 1, 3])
            if _bs1.button("Seleziona tutti", key="dom_ed_all", width="stretch"):
                for _e in _pub_candidati["edificio"]:
                    st.session_state[f"dom_ed_{_e}"] = True
                st.rerun()
            if _bs2.button("Deseleziona tutti", key="dom_ed_none", width="stretch"):
                for _e in _pub_candidati["edificio"]:
                    st.session_state[f"dom_ed_{_e}"] = False
                st.rerun()
            _mwh_sel = float(_pub_candidati[_pub_candidati["edificio"].isin(_pub_scelti)]
                             ["consumo_annuo_MWh"].sum())
            _bs3.caption(f"**{len(_pub_scelti)}** di {len(_pub_candidati)} edifici selezionati "
                         f"· **{_mwh_sel:,.0f} MWh/a**".replace(",", "."))

            # griglia di checkbox, ordinate per consumo decrescente
            _ncol = 3
            _cols_ed = st.columns(_ncol)
            for _i, _r in enumerate(_pub_candidati.itertuples()):
                _c = _cols_ed[_i % _ncol]
                _zona_breve = str(_r.cluster).split(" - ")[0] if _r.cluster else ""
                _c.checkbox(
                    f"{_r.edificio} · {_r.consumo_annuo_MWh:,.0f} MWh".replace(",", "."),
                    value=st.session_state.get(f"dom_ed_{_r.edificio}",
                                               _r.edificio not in PUBBLICI_NON_SPUNTATI),
                    key=f"dom_ed_{_r.edificio}",
                    help=f"{_r.tipologia} · {_zona_breve}")

        st.divider()
        st.markdown("##### \U0001F6E4\ufe0f Ipotesi di tracciato della rete")

        # SOTTOCENTRALE: ricalcolo dinamico come punto intermedio tra baricentro
        # aziende e baricentro pubblici selezionati (override delle costanti
        # globali di modulo, valide solo dentro questa sezione).
        CENTRALE_LAT, CENTRALE_LON = calcola_sottocentrale(bmap)

        st.caption(f"Rete progettata in **2 tempi**: prima il tratto *obbligato* che collega la "
                   f"**sottocentrale** ({CENTRALE_LAT:.4f}, {CENTRALE_LON:.4f}) agli **edifici pubblici** "
                   f"e ai **condomini censiti** selezionati; poi i **privati** vengono agganciati "
                   f"solo se cadono entro un raggio dal tubo pubblico. "
                   f"**Zone senza pubblici** (es. Zona 3) possono essere agganciate in modo "
                   f"opportunistico se il tubo di altre zone ci passa vicino.")
        st.caption(f"\U0001F4CD **Posizione sottocentrale**: punto intermedio tra il baricentro "
                   f"delle 4 aziende sorgente ({_LAT_BAR_AZIENDE:.4f}, {_LON_BAR_AZIENDE:.4f}) "
                   f"e il baricentro degli edifici pubblici serviti. Si sposta dinamicamente al "
                   f"variare della selezione. Va confermata in fase di progetto in base agli "
                   f"spazi disponibili, all'antigelo del ground loop e ai vincoli urbanistici.")

        # --- 1. Tratto obbligato: pubblici + condomini censiti (opzione B) ---
        _pts_obb = []
        if not bmap.empty:
            _p_pub = bmap[["lat", "lon", "consumo_annuo_MWh", "edificio"]].copy()
            _p_pub["tipo"] = "pubblico"
            _pts_obb.append(_p_pub)
        if sel_cond_zone and not condomini.empty:
            _cond_z = condomini[condomini["cluster"].isin(sel_cond_zone)].copy()
            _cond_z["MWh_stimato"] = _cond_z["unita"] * mwh_unita * tasso_cond / 100.0
            _cond_z = _cond_z.dropna(subset=["lat", "lon"])
            if not _cond_z.empty:
                _p_cond = _cond_z[["lat", "lon", "MWh_stimato"]].rename(
                    columns={"MWh_stimato": "consumo_annuo_MWh"})
                _p_cond["edificio"] = _cond_z["denominazione"].fillna("Condominio").astype(str).values
                _p_cond["tipo"] = "condominio"
                _pts_obb.append(_p_cond)
        _obb = (pd.concat(_pts_obb, ignore_index=True).dropna(subset=["lat", "lon"])
                if _pts_obb else pd.DataFrame())

        if _obb.empty:
            st.info("Seleziona almeno un edificio pubblico o un condominio "
                    "georeferenziato per vedere il tracciato.")
        else:
            tc1, tc2, tc3, tc4 = st.columns(4)
            tort = tc1.slider("Fattore di tortuosità", 1.0, 2.0, 1.35, step=0.05, key="dom_tort")
            costo_m_tr = tc2.slider("Costo dello scavo (€/m)", 60, 500, 150, step=10,
                                    key="dom_costo_tr",
                                    help="Scavo, letto di posa, rinterro e ripristino: "
                                         "dipendono poco dal diametro. Alla dorsale e "
                                         "ai rami viene poi sommato il costo della "
                                         "tubazione, che invece cresce col diametro.")
            buffer_m = tc3.slider("Lunghezza max allaccio privati (m)", 20, 200, 50, step=5,
                                  key="dom_buffer",
                                  help="Metri di tubo che si e disposti a posare per allacciare "
                                       "un privato, misurati LUNGO LE STRADE: tratto "
                                       "edificio→strada più percorso stradale fino alla condotta "
                                       "già posata. Non è una distanza in linea d'aria, quindi "
                                       "un edificio dall'altra parte di un fiume o di una ferrovia "
                                       "non viene agganciato solo perché è vicino sulla mappa.")
            soglia_dens = tc4.slider("Soglia densità ramo (MWh/(m·a))", 0.0, 3.0, 1.0, step=0.1,
                                     key="dom_soglia_dens",
                                     help="QM: se un ramo del tratto pubblico porta meno di questa "
                                          "densità (MWh/anno diviso metri del ramo, cumulativo dal "
                                          "punto di diramazione in avanti), viene POTATO e gli edifici "
                                          "sotto vengono esclusi dal TLR (andrebbero serviti "
                                          "localmente). 1.0 = soglia critica QM standard; "
                                          "**0 = nessuna esclusione**, tutti gli edifici "
                                          "selezionati vengono collegati anche se il ramo "
                                          "non è conveniente, utile per vedere il "
                                          "potenziale massimo della rete.")
            if soglia_dens <= 0.001:
                st.info("🔓 Soglia disattivata: vengono collegati **tutti** gli edifici "
                        "selezionati, anche quelli che non rispettano i criteri QM di "
                        "densità lineare. Il tracciato mostra il potenziale massimo, "
                        "non la configurazione conveniente.")

            # Scelta metodo: OSM (Dijkstra su strade) con fallback MST + tortuosita
            _cb1, _cb2 = st.columns(2)
            usa_strade = _cb1.checkbox(
                "\U0001F6E3\ufe0f Tracciato sulle strade reali (OSM)", value=True, key="dom_usa_osm",
                help="Al primo avvio scarica la rete stradale di Maniago da OpenStreetMap "
                     "(qualche decina di secondi). Poi la cache resta locale in "
                     "`maniago_strade_cache.json`. Se disattivato o se il download fallisce, "
                     "si usa l'MST in linea d'aria con tortuosita.")
            mostra_strade = _cb2.checkbox(
                "\U0001F441\ufe0f Mostra la viabilità nota al grafo", value=False,
                key="dom_mostra_strade",
                help="Disegna in azzurro tutte le strade presenti nel grafo OSM. "
                     "Serve a capire dove la mappa è completa e dove invece il tracciato "
                     "è costretto a procedere in linea retta per mancanza di dati.")

            _strade_res = carica_grafo_strade(GRAFO_CENTRO_LAT, GRAFO_CENTRO_LON,
                                              raggio_km=GRAFO_RAGGIO_KM) if usa_strade else (None, None)
            _strade, _osm_err = _strade_res if isinstance(_strade_res, tuple) else (_strade_res, None)
            _uso_osm = _strade is not None
            if _uso_osm and not _strade.get("copre_richiesta", True):
                st.warning("⚠️ La mappa stradale in uso è una copia salvata che non copre "
                           "tutta l'area di studio (il nuovo download non è riuscito). "
                           "Gli edifici fuori dal riquadro risultano collegati in linea "
                           "d'aria: riprova il download o riavvia l'app.")
            if usa_strade and not _uso_osm:
                _msg_err = f" — causa: `{_osm_err}`" if _osm_err else ""
                st.warning(f"⚠️ Rete stradale non disponibile{_msg_err}. "
                           f"Il tracciato è calcolato in linea d'aria con tortuosità, "
                           f"quindi le condotte appaiono come segmenti rettilinei.")
                _w1, _w2 = st.columns([1, 3])
                if _w1.button("🔄 Riprova il download", key="dom_retry_osm",
                              width="stretch"):
                    try:
                        if os.path.exists("maniago_strade_cache.json"):
                            os.remove("maniago_strade_cache.json")
                    except Exception:
                        pass
                    try:
                        carica_grafo_strade.clear()
                    except Exception:
                        pass
                    st.rerun()
                _w2.caption("Il programma prova prima Overpass su quattro server, poi "
                            "l'API ufficiale di OpenStreetMap. Se falliscono entrambi si "
                            "tratta quasi sempre di un sovraccarico temporaneo o di un "
                            "proxy aziendale che blocca la richiesta.")
                with st.expander("Scaricare la mappa manualmente"):
                    _bbm = GRAFO_BBOX
                    # l'export di Overpass non ha il limite di 50.000 nodi dell'API
                    # ufficiale, che sull'intera area di Maniago risponde HTTP 400
                    _url_m = (f"https://overpass-api.de/api/map?"
                              f"bbox={_bbm[1]:.4f},{_bbm[0]:.4f},{_bbm[3]:.4f},{_bbm[2]:.4f}")
                    st.markdown(
                        f"Da una rete senza restrizioni, apri [questo indirizzo]({_url_m}) "
                        f"(export di OpenStreetMap tramite Overpass, qualche decina di MB) "
                        f"e salva il file `.osm` che viene restituito, poi caricalo qui "
                        f"sotto: viene convertito e messo in cache, e da quel momento il "
                        f"tracciato segue le strade senza bisogno di connessione.")
                    _up = st.file_uploader("File .osm o .xml", type=["osm", "xml"],
                                           key="dom_osm_upload")
                    if _up is not None:
                        try:
                            import xml.etree.ElementTree as _ET
                            _root = _ET.fromstring(_up.getvalue())
                            _els = []
                            for _nd in _root.findall("node"):
                                _els.append({"type": "node", "id": int(_nd.get("id")),
                                             "lat": float(_nd.get("lat")),
                                             "lon": float(_nd.get("lon"))})
                            for _w in _root.findall("way"):
                                _tg = {t.get("k"): t.get("v") for t in _w.findall("tag")}
                                if "highway" not in _tg:
                                    continue
                                _els.append({"type": "way", "id": int(_w.get("id")),
                                             "nodes": [int(x.get("ref"))
                                                       for x in _w.findall("nd")],
                                             "tags": _tg})
                            _n_way = sum(1 for e in _els if e["type"] == "way")
                            if _n_way == 0:
                                st.error("Nel file non ci sono strade.")
                            else:
                                with open("maniago_strade_cache.json", "w",
                                          encoding="utf-8") as _f:
                                    json.dump({"elements": _els,
                                               "_bbox": list(_bbm)}, _f)
                                try:
                                    carica_grafo_strade.clear()
                                except Exception:
                                    pass
                                st.success(f"Mappa caricata: {_n_way} strade. "
                                           f"Ricarico la pagina.")
                                st.rerun()
                        except Exception as _e:
                            st.error(f"File non leggibile: {type(_e).__name__}")
            if _uso_osm and build_grafo_stradale(_strade) is None:
                st.warning("⚠️ modulo `networkx` non installato "
                           "(pip install networkx). Uso il tracciato in linea d'aria.")
                _uso_osm = False

            if _uso_osm:
                # --- ROUTING SU STRADE: Steiner con potatura per densita' lineare ---
                _G = build_grafo_stradale(_strade)
                # snap centrale + edifici del tratto obbligato
                _lat_obb = np.concatenate([[CENTRALE_LAT], _obb["lat"].values])
                _lon_obb = np.concatenate([[CENTRALE_LON], _obb["lon"].values])
                _nodi_obb, _dsnap_obb = snap_a_strade(_lat_obb, _lon_obb, _strade)
                _rad_nodo = _nodi_obb[0]

                # Tutti gli edifici scelti dall'utente entrano nella dorsale:
                # nessuna esclusione per motivi cartografici. Se un edificio
                # risulta lontano dal nodo stradale piu vicino, l'ultimo tratto
                # viene tracciato in linea retta e la cosa viene segnalata, ma
                # l'edificio resta servito.
                _target_nodi = list(_nodi_obb[1:])
                _snap_lunghi = []
                for i in range(len(_obb)):
                    _d = float(_dsnap_obb[i + 1])
                    if _d > MAX_SNAP_M:
                        _snap_lunghi.append({
                            "edificio": _obb["edificio"].iloc[i] if "edificio" in _obb.columns else f"edif {i}",
                            "dist. da strada mappata (m)": round(_d),
                        })

                # mappa nodo_stradale -> MWh dell'edificio agganciato (per la potatura).
                # Se piu edifici snappano sullo stesso nodo, sommo i loro MWh.
                _mwh_per_target = {}
                _label_per_target = {}
                for i in range(len(_obb)):
                    _n = _nodi_obb[i + 1]
                    _mwh = float(_obb["consumo_annuo_MWh"].iloc[i]) if "consumo_annuo_MWh" in _obb.columns else 0.0
                    _mwh_per_target[_n] = _mwh_per_target.get(_n, 0.0) + _mwh
                    _lab = _obb["edificio"].iloc[i] if "edificio" in _obb.columns else f"edif {i}"
                    _label_per_target.setdefault(_n, []).append(str(_lab))

                _archi_G, _len_pub_osm, _target_servi, _target_escl, _info_pot = \
                    steiner_con_potatura_densita(_G, _target_nodi, _rad_nodo,
                                                  _mwh_per_target,
                                                  soglia_mwh_per_m=soglia_dens)
                _nodi_tubo = set()
                for a, b, _ in _archi_G:
                    _nodi_tubo.add(a)
                    _nodi_tubo.add(b)
                _archi_pub = archi_a_coords(_archi_G, _strade)

                # linee "ultimo metro" solo per gli edifici EFFETTIVAMENTE serviti
                # e comunque entro il limite di snap.
                _um_lat, _um_lon = [], []
                _len_ultimi = 0.0
                _len_linea_aria = 0.0
                _obb_servi_mask = []
                _obb_esclusi_info = []
                _non_raggiunti = []
                # Nodi a cui si puo' agganciare un edificio non raggiungibile sul
                # grafo: quelli del tubo gia' posato, piu' la sottocentrale.
                _nodi_aggancio = list(_nodi_tubo | {_rad_nodo})
                _xy_aggancio = _latlon_a_xy(
                    np.array([_strade["nodi"][k][0] for k in _nodi_aggancio]),
                    np.array([_strade["nodi"][k][1] for k in _nodi_aggancio]))
                for i in range(len(_obb)):
                    _n = _nodi_obb[i + 1]
                    _d_snap = float(_dsnap_obb[i + 1])
                    _lat_ed = float(_obb["lat"].iloc[i])
                    _lon_ed = float(_obb["lon"].iloc[i])
                    _lab = _obb["edificio"].iloc[i] if "edificio" in _obb.columns else f"edif {i}"
                    _mwh = float(_obb["consumo_annuo_MWh"].iloc[i]) if "consumo_annuo_MWh" in _obb.columns else 0.0
                    _tipo = _obb["tipo"].iloc[i] if "tipo" in _obb.columns else "?"
                    if _n in _target_servi:
                        _lat_n, _lon_n = _strade["nodi"][_n]
                        _um_lat += [_lat_ed, _lat_n, None]
                        _um_lon += [_lon_ed, _lon_n, None]
                        _len_ultimi += _d_snap
                        _obb_servi_mask.append(True)
                    elif _n in _target_escl:
                        # potato davvero dalla soglia di densita' lineare del ramo
                        _ip = _info_pot.get(_n, {})
                        _L_r = float(_ip.get("lunghezza_m", 0.0))
                        _m_r = float(_ip.get("mwh", _mwh))
                        _d_r = float(_ip.get("densita", 0.0))
                        # costo indicativo del solo ramo: diametro sulla potenza
                        # che porta, scavo + tubazione come nel resto della rete
                        _dT_e = max(T_mandata_ideale - T_ritorno_ideale, 1)
                        _dn_r = dimensiona_dn(potenza_da_energia(_m_r, 1900.0), _dT_e, 1.0)[0]
                        _c_r = _L_r * costo_condotta_eur_m(_dn_r, costo_m_tr)
                        _crf_r = crf(float(st.session_state.get("eco_wacc", 4.0)) / 100.0,
                                     int(st.session_state.get("eco_anni", 25)))
                        _eur_mwh_r = _c_r * _crf_r / _m_r if _m_r > 0 else float("nan")
                        _altri = sorted({_l for _nn in _ip.get("nodi_ramo", [])
                                         for _l in _label_per_target.get(_nn, [])} - {str(_lab)})
                        def _it(x, d=0):
                            return (f"{x:,.{d}f}".replace(",", "@").replace(".", ",")
                                    .replace("@", "."))
                        _motivo = (
                            f"Per raggiungerlo servono {_it(_L_r)} m di ramo che portano "
                            f"{_it(_m_r)} MWh/a: {_it(_d_r, 2)} MWh/(m·a), sotto la soglia "
                            f"di {_it(soglia_dens, 1)}. Il ramo (DN{_dn_r}) costerebbe circa "
                            f"{_it(_c_r / 1000)} k€, cioè {_it(_eur_mwh_r)} €/MWh "
                            f"di solo tubo sul calore che porta.")
                        if _altri:
                            _motivo += " Ramo condiviso con: " + ", ".join(_altri) + "."
                        _obb_servi_mask.append(False)
                        _obb_esclusi_info.append({"edificio": _lab,
                                                  "tipo": _tipo,
                                                  "MWh/a": round(_mwh, 1),
                                                  "Ramo (m)": round(_L_r),
                                                  "Calore del ramo (MWh/a)": round(_m_r, 1),
                                                  "Densità ramo (MWh/(m·a))": round(_d_r, 2),
                                                  "Costo ramo (k€)": round(_c_r / 1000),
                                                  "Solo tubo (€/MWh)": (round(_eur_mwh_r)
                                                                        if _m_r > 0 else None),
                                                  "motivo": _motivo,
                                                  "lat": _lat_ed, "lon": _lon_ed})
                    else:
                        # NON raggiungibile sul grafo stradale (componente OSM
                        # isolata, strade private o interne non mappate). In
                        # precedenza finiva fra gli "esclusi per densita'" anche
                        # con soglia zero, pur restando nei consumi. Coerentemente
                        # con la regola "nessuna esclusione per motivi
                        # cartografici", si collega in linea d'aria al punto piu'
                        # vicino del tubo, con la tortuosita' impostata.
                        _xe, _ye = _latlon_a_xy(np.array([_lat_ed]), np.array([_lon_ed]))
                        _dd = np.hypot(_xy_aggancio[0] - _xe[0], _xy_aggancio[1] - _ye[0])
                        _k = int(np.argmin(_dd))
                        _nk = _nodi_aggancio[_k]
                        _lat_k, _lon_k = _strade["nodi"][_nk]
                        _l_aria = float(_dd[_k]) * tort
                        _len_linea_aria += _l_aria
                        _archi_pub.append(((_lat_k, _lon_k), (_lat_ed, _lon_ed), _l_aria))
                        _obb_servi_mask.append(True)
                        _non_raggiunti.append({"edificio": _lab, "tipo": _tipo,
                                               "MWh/a": round(_mwh, 1),
                                               "allaccio in linea d'aria (m)": round(_l_aria)})
                _len_pub_t = _len_pub_osm + _len_ultimi + _len_linea_aria
            else:
                # --- FALLBACK: MST + tortuosita (nessuna potatura per densita') ---
                _archi_pub, _len_pub = mst_archi(_obb["lat"].values, _obb["lon"].values,
                                                 radice=(CENTRALE_LAT, CENTRALE_LON))
                _len_pub_t = _len_pub * tort
                _um_lat, _um_lon = [], []
                _nodi_tubo = set()
                _obb_servi_mask = [True] * len(_obb)
                _obb_esclusi_info = []
                _snap_lunghi = []
                _non_raggiunti = []

            # --- 2. Buffer privati: aggancio via strade se disponibili ---
            _priv_in = pd.DataFrame()
            _len_stub_t = 0.0
            _stub_lat_l, _stub_lon_l = [], []
            _fatt_priv = fattore_correzione / 100.0
            if sel_priv_zone and not privati.empty and _archi_pub:
                _pv = privati[privati["cluster"].isin(sel_priv_zone)].dropna(subset=["lat", "lon"]).copy()
                if not _pv.empty:
                    if _uso_osm:
                        # Buffer misurato LUNGO LE STRADE: allaccio = tratto
                        # edificio->strada + percorso stradale fino al tubo.
                        # Evita l'errore del buffer in linea d'aria dove il
                        # tracciato compie salti rettilinei su aree non mappate.
                        _nodi_pv_all, _dsnap_pv_all = snap_a_strade(
                            _pv["lat"].values, _pv["lon"].values, _strade)
                        _dmin = buffer_su_rete(_G, _nodi_tubo, _nodi_pv_all,
                                               _dsnap_pv_all, buffer_m)
                    else:
                        _dmin, _idx_arco, _lat_tubo, _lon_tubo = buffer_tracciato(
                            _archi_pub, _pv["lat"].values, _pv["lon"].values, raggio_m=buffer_m)
                    _pv["dist_tubo_m"] = _dmin
                    _in_buffer = _dmin <= buffer_m
                    _priv_in = _pv[_in_buffer].copy()
                    if not _priv_in.empty:
                        if _uso_osm:
                            _lat_pv = _priv_in["lat"].values
                            _lon_pv = _priv_in["lon"].values
                            _nodi_pv = [n for n, ok in zip(_nodi_pv_all, _in_buffer) if ok]
                            _dsnap_pv = _dsnap_pv_all[_in_buffer]
                            _lat_stub_flat, _lon_stub_flat = [], []
                            _len_stub_m = 0.0
                            _n_priv_snap_lungo = 0
                            for i in range(len(_priv_in)):
                                _d_sn = float(_dsnap_pv[i])
                                if _d_sn > MAX_SNAP_M:
                                    _n_priv_snap_lungo += 1
                                # ultimo metro edificio -> nodo stradale
                                _n = _nodi_pv[i]
                                _lat_n, _lon_n = _strade["nodi"][_n]
                                _lat_stub_flat += [float(_lat_pv[i]), _lat_n, None]
                                _lon_stub_flat += [float(_lon_pv[i]), _lon_n, None]
                                _len_stub_m += _d_sn
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
            # sfondo opzionale: la viabilita' effettivamente presente nel grafo.
            # Serve a capire dove OSM e' completo e dove invece il tracciato e'
            # costretto a procedere in linea retta.
            if _uso_osm and mostra_strade:
                _sl_lat, _sl_lon = [], []
                for _w in _strade["strade"]:
                    for _a, _b in zip(_w[:-1], _w[1:]):
                        if _a in _strade["nodi"] and _b in _strade["nodi"]:
                            _sl_lat += [_strade["nodi"][_a][0], _strade["nodi"][_b][0], None]
                            _sl_lon += [_strade["nodi"][_a][1], _strade["nodi"][_b][1], None]
                fig_tr.add_trace(go.Scattermap(
                    lat=_sl_lat, lon=_sl_lon, mode="lines",
                    line=dict(width=1, color="#7FB3D5"),
                    name="Viabilità nota al grafo", opacity=0.45, hoverinfo="skip"))
            # tracciato pubblico (rosso, spesso)
            _label_pub = (f"Tratto obbligato (strade OSM): {_len_pub_t / 1000:.2f} km" if _uso_osm
                          else f"Tratto obbligato (MST x{tort}): {_len_pub_t / 1000:.2f} km")
            fig_tr.add_trace(go.Scattermap(lat=_lat_l, lon=_lon_l, mode="lines",
                                              line=dict(width=3, color="#FF4B4B"),
                                              name=_label_pub,
                                              hoverinfo="skip"))
            # ultimi metri edificio->strada (rosa tratteggiato)
            if _uso_osm and _um_lat:
                fig_tr.add_trace(go.Scattermap(lat=_um_lat, lon=_um_lon, mode="lines",
                                                  line=dict(width=1.2, color="#FF9AA0"),
                                                  name="Ultimi metri edificio→strada",
                                                  hoverinfo="skip"))
            # stub privati (giallo, sottile)
            if _stub_lat_l:
                fig_tr.add_trace(go.Scattermap(lat=_stub_lat_l, lon=_stub_lon_l, mode="lines",
                                                  line=dict(width=1.5, color="#F5C518"),
                                                  name=f"Allacci privati: {_len_stub_t / 1000:.1f} km",
                                                  hoverinfo="skip"))
            # pubblici/condomini SERVITI (blu) vs ESCLUSI (grigi con X)
            if not bmap.empty:
                # tra gli edifici di _obb, quelli con maschera True sono serviti.
                # bmap contiene solo i pubblici; abbina per nome.
                _bmap_edifici = bmap["edificio"].tolist()
                _obb_edifici = _obb["edificio"].tolist() if "edificio" in _obb.columns else []
                _mappa_servi = {e: s for e, s in zip(_obb_edifici, _obb_servi_mask)}
                _serviti_ok = [_mappa_servi.get(e, True) for e in _bmap_edifici]
                _bmap_srv = bmap[pd.Series(_serviti_ok, index=bmap.index)]
                _bmap_esc = bmap[~pd.Series(_serviti_ok, index=bmap.index)]
                if not _bmap_srv.empty:
                    fig_tr.add_trace(go.Scattermap(
                        lat=_bmap_srv["lat"], lon=_bmap_srv["lon"], mode="markers",
                        name=f"🟢 Pubblici serviti ({len(_bmap_srv)})",
                        marker=dict(size=13, color="#1FA34A"),
                        text=(_bmap_srv["edificio"] + "<br>"
                              + _bmap_srv["consumo_annuo_MWh"].round(0).astype(int).astype(str) + " MWh/a"),
                        hoverinfo="text"))
                if not _bmap_esc.empty:
                    fig_tr.add_trace(go.Scattermap(
                        lat=_bmap_esc["lat"], lon=_bmap_esc["lon"], mode="markers",
                        name=f"❌ Pubblici esclusi ({len(_bmap_esc)})",
                        marker=dict(size=15, color="#E53935", opacity=0.95, symbol="cross"),
                        text=(_bmap_esc["edificio"] + "<br>"
                              + _bmap_esc["consumo_annuo_MWh"].round(0).astype(int).astype(str)
                              + " MWh/a - fuori soglia densità"),
                        hoverinfo="text"))
            # condomini (viola per serviti, grigio per esclusi)
            if sel_cond_zone and not condomini.empty:
                _c_geo = condomini[condomini["cluster"].isin(sel_cond_zone)].dropna(subset=["lat", "lon"])
                if not _c_geo.empty:
                    _c_geo = _c_geo.copy()
                    _c_geo["MWh_stimato"] = (_c_geo["unita"] * mwh_unita * tasso_cond / 100.0).round(1)
                    # marca condomini esclusi (chiavi in _obb_esclusi_info)
                    _nomi_escl_obb = set()
                    for _r in _obb_esclusi_info:
                        _nomi_escl_obb.add(_r["edificio"])
                    _c_geo["_servi"] = ~_c_geo["denominazione"].fillna("").astype(str).isin(_nomi_escl_obb)
                    _cs = _c_geo[_c_geo["_servi"]]
                    _ce = _c_geo[~_c_geo["_servi"]]
                    if not _cs.empty:
                        fig_tr.add_trace(go.Scattermap(
                            lat=_cs["lat"], lon=_cs["lon"], mode="markers",
                            name=f"Condomini serviti ({len(_cs)})",
                            marker=dict(size=9, color="#9B5DE5"),
                            text=(_cs["denominazione"].fillna("Condominio").astype(str) + "<br>"
                                  + _cs["unita"].astype(str) + " unità · "
                                  + _cs["MWh_stimato"].astype(str) + " MWh/a"),
                            hoverinfo="text"))
                    if not _ce.empty:
                        fig_tr.add_trace(go.Scattermap(
                            lat=_ce["lat"], lon=_ce["lon"], mode="markers",
                            name=f"⛔ Condomini esclusi ({len(_ce)})",
                            marker=dict(size=13, color="#E53935", opacity=0.9, symbol="cross"),
                            text=(_ce["denominazione"].fillna("Condominio").astype(str)
                                  + " · fuori soglia densità"),
                            hoverinfo="text"))
            # privati DENTRO il buffer (verde)
            if not _priv_in.empty:
                fig_tr.add_trace(go.Scattermap(
                    lat=_priv_in["lat"], lon=_priv_in["lon"], mode="markers",
                    name=f"Privati agganciati ({len(_priv_in)})",
                    marker=dict(size=5, color="#5DADE2", opacity=0.85),
                    text=(_priv_in.get("nome", pd.Series([""] * len(_priv_in))).fillna("").astype(str)
                          + "<br>allaccio: " + _priv_in["dist_tubo_m"].round(0).astype(int).astype(str)
                          + " m di tubo · " + _priv_in["consumo_annuo_MWh"].round(1).astype(str) + " MWh/a"),
                    hoverinfo="text"))
            # privati FUORI dal buffer (grigi trasparenti, per contesto)
            if sel_priv_zone and not privati.empty:
                _pv_all = privati[privati["cluster"].isin(sel_priv_zone)].dropna(subset=["lat", "lon"])
                if not _priv_in.empty:
                    _pv_out = _pv_all[~_pv_all.index.isin(_priv_in.index)]
                else:
                    _pv_out = _pv_all
                if not _pv_out.empty:
                    fig_tr.add_trace(go.Scattermap(
                        lat=_pv_out["lat"], lon=_pv_out["lon"], mode="markers",
                        name=f"Privati fuori buffer ({len(_pv_out)})",
                        marker=dict(size=3, color="#666666", opacity=0.35),
                        hoverinfo="skip"))
            # aziende
            for _n, (_la, _lo) in AZIENDE_COORD.items():
                fig_tr.add_trace(go.Scattermap(lat=[_la], lon=[_lo], mode="markers",
                                                  name=_n, marker=dict(size=9, color="#E9C46A"),
                                                  text=_n, hoverinfo="text", showlegend=False))
            # sottocentrale
            fig_tr.add_trace(go.Scattermap(
                lat=[CENTRALE_LAT], lon=[CENTRALE_LON], mode="markers+text", name="Sottocentrale",
                marker=dict(size=18, color="#FF9F1C"), text=["CENTRALE"], textposition="top right",
                textfont=dict(size=13, color="#FF9F1C")))
            # Centraggio mappa: includo la sottocentrale, gli edifici obbligati
            # e le 4 aziende sorgente (che stanno nella zona industriale, spesso
            # a est del centro urbano). Zoom out sufficiente per vederli tutti.
            _lat_all = list(_obb["lat"].values) + [CENTRALE_LAT]
            _lon_all = list(_obb["lon"].values) + [CENTRALE_LON]
            for _la, _lo in AZIENDE_COORD.values():
                _lat_all.append(_la)
                _lon_all.append(_lo)
            _clat = (min(_lat_all) + max(_lat_all)) / 2
            _clon = (min(_lon_all) + max(_lon_all)) / 2
            # zoom in base all'estensione spaziale
            _span_lat = max(_lat_all) - min(_lat_all)
            _span_lon = max(_lon_all) - min(_lon_all)
            _span = max(_span_lat, _span_lon)
            if _span > 0.025:
                _zoom = 12.5
            elif _span > 0.015:
                _zoom = 13.0
            else:
                _zoom = 13.5
            fig_tr.update_layout(**layout_mappa(_clat, _clon, _zoom),
                                 height=580, margin=dict(t=10, b=0, l=0, r=0),
                                 legend=dict(orientation="h", yanchor="bottom", y=1.01))
            st.plotly_chart(fig_tr, width="stretch")

            # --- edifici esclusi: SOLO per convenienza economica del ramo ---
            if _uso_osm and _obb_esclusi_info:
                _tot_mwh_escl = sum(r["MWh/a"] for r in _obb_esclusi_info)
                st.warning(
                    f"⛔ **{len(_obb_esclusi_info)} edifici esclusi** perché il ramo per "
                    f"servirli ha densità < {soglia_dens:.1f} MWh/(m·a): costerebbe più metri "
                    f"di tubo di quanto rendono. Potenziale non allacciato: "
                    f"**{_tot_mwh_escl:.0f} MWh/a**. Abbassa la soglia per includerli."
                )
                with st.expander(f"📋 Dettaglio {len(_obb_esclusi_info)} edifici esclusi"):
                    _df_esc = pd.DataFrame(_obb_esclusi_info)
                    _cols = [c for c in ["edificio", "tipo", "MWh/a", "Ramo (m)",
                                         "Calore del ramo (MWh/a)", "Densità ramo (MWh/(m·a))",
                                         "Costo ramo (k€)", "Solo tubo (€/MWh)", "motivo"]
                             if c in _df_esc.columns]
                    st.dataframe(_df_esc[_cols].rename(columns={
                        "edificio": "Edificio", "tipo": "Tipo",
                        "MWh/a": "Domanda (MWh/a)", "motivo": "Perché è escluso"}),
                        width="stretch", hide_index=True)
                    st.caption(
                        "Il ramo è il tratto di tubo che servirebbe solo per quell'edificio "
                        "(e per gli altri potati con lui), misurato dal punto in cui si "
                        "stacca dalla rete. Il criterio è quello QM: se il ramo porta meno "
                        "calore per metro della soglia, il tubo non si ripaga con la vendita "
                        "del calore. 'Solo tubo' è il costo del ramo annualizzato (tasso e "
                        "anni dell'Analisi economica) diviso il calore che porta: va "
                        "confrontato col prezzo di vendita. Gli edifici esclusi non entrano "
                        "né nella domanda del dimensionamento né nei ricavi, e la rete non "
                        "si estende fin lì.")

            # --- nota tecnica: allacci lontani dalla viabilita' mappata ---
            if _uso_osm and _non_raggiunti:
                _mwh_nr = sum(r["MWh/a"] for r in _non_raggiunti)
                _m_nr = sum(r["allaccio in linea d'aria (m)"] for r in _non_raggiunti)
                _mwh_nr_s = f"{_mwh_nr:,.0f}".replace(",", ".")
                _m_nr_s = f"{_m_nr:,.0f}".replace(",", ".")
                st.info(
                    f"🧭 **{len(_non_raggiunti)} edifici non raggiungibili sul grafo "
                    f"stradale** ({_mwh_nr_s} MWh/a): la mappa OSM non li collega al "
                    f"resto della rete (strade interne o private non mappate, tratti "
                    f"isolati). Restano serviti con un allaccio in linea d'aria × "
                    f"tortuosità, per {_m_nr_s} m complessivi già compresi nella "
                    f"lunghezza e nel costo della rete. Verifica il percorso reale sul "
                    f"posto.")
                with st.expander(f"📋 Dettaglio {len(_non_raggiunti)} edifici collegati in linea d'aria"):
                    st.dataframe(pd.DataFrame(_non_raggiunti), width="stretch",
                                 hide_index=True)

            if _uso_osm and _snap_lunghi:
                with st.expander(f"ℹ️ {len(_snap_lunghi)} edifici distanti dalla viabilità mappata "
                                 f"(sono comunque collegati)"):
                    st.caption(
                        f"Per questi edifici il nodo stradale OSM più vicino supera "
                        f"{MAX_SNAP_M:.0f} m, quindi l'ultimo tratto è tracciato in linea retta "
                        f"e la lunghezza potrebbe essere sovrastimata. Cause tipiche: coordinate "
                        f"imprecise nel CSV, oppure viabilità interna non mappata in OSM "
                        f"(cortili, aree industriali, strade private). **Gli edifici restano "
                        f"serviti**: è solo un avviso sulla precisione del tracciato.")
                    st.dataframe(pd.DataFrame(_snap_lunghi), width="stretch",
                                 hide_index=True)

            # --- energia servita ---
            # Energia SERVITA: escludo gli edifici potati dalla soglia densita'.
            _nomi_pub_serviti = set()
            _nomi_pub_tutti = bmap["edificio"].tolist() if not bmap.empty else []
            _nomi_pub_esclusi = set(r["edificio"] for r in _obb_esclusi_info) if _uso_osm else set()
            _bmap_srv_e = bmap[~bmap["edificio"].isin(_nomi_pub_esclusi)] if not bmap.empty else bmap
            _E_pub = float(_bmap_srv_e["consumo_annuo_MWh"].sum()) if not _bmap_srv_e.empty else 0.0
            _E_cond = 0.0
            _E_cond_tutti = 0.0
            _n_cond_serviti = 0
            _n_cond_unita_all = 0
            if sel_cond_zone and not condomini.empty:
                _cond_sel = condomini[condomini["cluster"].isin(sel_cond_zone)]
                _E_cond_tutti = float(_cond_sel["unita"].sum()) * mwh_unita * tasso_cond / 100.0
                if _uso_osm and _nomi_pub_esclusi:
                    _cond_sel = _cond_sel[~_cond_sel["denominazione"].fillna("").astype(str).isin(_nomi_pub_esclusi)]
                _E_cond = float(_cond_sel["unita"].sum()) * mwh_unita * tasso_cond / 100.0
                _n_cond_serviti = len(_cond_sel)
                _n_cond_unita_all = int(round(float(_cond_sel["unita"].sum()) * tasso_cond / 100.0))
            _E_priv = float(_priv_in["consumo_annuo_MWh"].sum()) * _fatt_priv if not _priv_in.empty else 0.0
            _E_tot = _E_pub + _E_cond + _E_priv
            # Privati che si allacciano davvero: il tasso di allacciamento riduce
            # l'energia, e deve ridurre allo stesso modo il numero di utenze (e
            # quindi sottostazioni, quote fisse e contributi di allacciamento).
            _n_priv_buffer = len(_priv_in) if not _priv_in.empty else 0
            _n_priv_allacciati = int(round(_n_priv_buffer * _fatt_priv))
            _n_utenze_tot = len(_bmap_srv_e) + _n_cond_serviti + _n_priv_allacciati

            # --- elenco degli edifici SERVITI, per Dimensionamento ed Economia ---
            _pub_serviti_set = set(_bmap_srv_e["edificio"]) if not _bmap_srv_e.empty else set()
            _tipo_di = buildings.set_index("edificio")["tipo_utenza"].to_dict()
            st.session_state["_dom_edifici_serviti"] = [
                e for e in selected_buildings
                if _tipo_di.get(e) != "Pubblico" or e in _pub_serviti_set]
            _esclusi_rete = [e for e in selected_buildings
                             if _tipo_di.get(e) == "Pubblico" and e not in _pub_serviti_set]
            st.session_state["_dom_esclusi_rete"] = _esclusi_rete
            # condomini: la domanda e' aggregata per zona, quindi i condomini
            # esclusi si tolgono scalando il fattore sulla quota di energia servita
            st.session_state["_dom_fattore_condomini"] = (
                fatt_c * (_E_cond / _E_cond_tutti) if _E_cond_tutti > 0 else fatt_c)

            def _picco_rete_kw(ore_eq):
                """Picco alla partenza della dorsale. La contemporaneita' QM
                si applica solo alle utenze private e condominiali, come nel
                Dimensionamento: applicarla anche ai grandi edifici pubblici
                faceva CALARE il picco aggiungendo utenze."""
                _n_res = _n_priv_allacciati + _n_cond_unita_all
                _f_res = coeff_simultaneita_QM(_n_res) if _n_res > 1 else 1.0
                return (potenza_da_energia(_E_pub, ore_eq, 1.0)
                        + potenza_da_energia(_E_cond + _E_priv, ore_eq, _f_res)), _f_res

            # ---- CAPEX della rete, differenziato per diametro ----
            # La dorsale porta l'intera potenza, i rami di allaccio solo quella
            # delle utenze che servono: applicare a tutta la rete il costo della
            # dorsale sovrastimerebbe sensibilmente gli allacci.
            _dT_r = max(T_mandata_ideale - T_ritorno_ideale, 1)
            _P_dors, _f_sim_r = _picco_rete_kw(1900.0)
            _dn_d0, _, _, _ = dimensiona_dn(_P_dors, _dT_r, 1.5)
            _c_dors = costo_condotta_eur_m(_dn_d0, costo_m_tr)
            # ramo tipo: potenza di una singola utenza, con la sua contemporaneita'
            _P_ramo = potenza_da_energia(_E_tot / max(_n_utenze_tot, 1), 1900.0, 1.0)
            _dn_r0, _, _, _ = dimensiona_dn(_P_ramo, _dT_r, 1.0)
            _c_ramo = costo_condotta_eur_m(_dn_r0, costo_m_tr)
            _capex_rete_tot = _len_pub_t * _c_dors + _len_stub_t * _c_ramo

            t1, t2, t3, t4 = st.columns(4)
            t1.metric("Lunghezza totale rete", f"{_len_totale / 1000:.2f} km",
                      help=f"Dorsale {_len_pub_t / 1000:.2f} km + allacci "
                           f"{_len_stub_t / 1000:.2f} km (tortuosità {tort})")
            t2.metric("Utenze totali servite",
                      f"{_n_utenze_tot}",
                      help=f"pubblici + condomini + {_n_priv_allacciati} privati allacciati "
                           f"({_n_priv_buffer} nel buffer × tasso di allacciamento)")
            t3.metric("CAPEX rete", f"{_capex_rete_tot / 1e6:.2f} M€",
                      help=f"dorsale DN{_dn_d0} a {_c_dors:.0f} €/m · "
                           f"allacci DN{_dn_r0} a {_c_ramo:.0f} €/m")
            _dens = _E_tot / _len_totale if _len_totale > 0 else 0.0
            t4.metric("Densità lineare", f"{_dens:.2f} MWh/(m·a)",
                      help=f"soglia potatura: {soglia_dens:.1f} · sotto ~1,2 la rete fatica a ripagarsi; "
                           f"sopra ~2,0 e buona (QM)")

            with st.expander("💰 Come si compone il costo della rete"):
                _rc = pd.DataFrame([
                    {"Tratto": "Dorsale", "Lunghezza (m)": round(_len_pub_t),
                     "DN": _dn_d0, "€/m": round(_c_dors),
                     "di cui scavo": round(costo_m_tr),
                     "Costo (k€)": round(_len_pub_t * _c_dors / 1000)},
                    {"Tratto": "Allacci d'utenza", "Lunghezza (m)": round(_len_stub_t),
                     "DN": _dn_r0, "€/m": round(_c_ramo),
                     "di cui scavo": round(costo_m_tr),
                     "Costo (k€)": round(_len_stub_t * _c_ramo / 1000)},
                ])
                st.dataframe(_rc, width="stretch", hide_index=True)
                _c_medio = _capex_rete_tot / max(_len_totale, 1)
                st.caption(
                    f"Costo medio della rete **{_c_medio:.0f} €/m**. Il diametro degli "
                    f"allacci è calcolato sulla potenza di una singola utenza, quello "
                    f"della dorsale sulla potenza complessiva, con la contemporaneità QM "
                    f"({_f_sim_r:.2f}) applicata alle sole utenze private e condominiali. Sui piccoli diametri lo scavo pesa per la maggior "
                    f"parte del costo, quindi un allaccio DN{_dn_r0} non costa una "
                    f"frazione della dorsale ma circa "
                    f"{_c_ramo / max(_c_dors, 1) * 100:.0f} %.")

            # --- breakdown ---
            b1, b2, b3 = st.columns(3)
            b1.metric("da pubblici", f"{_E_pub:,.0f} MWh/a".replace(",", "."),
                      help=f"{len(_bmap_srv_e)} edifici serviti"
                           + (f" ({len(_nomi_pub_esclusi)} esclusi)" if _nomi_pub_esclusi else ""))
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

            # --- tabella degli edifici serviti e della loro domanda ---
            # Un edificio per riga per i pubblici (anche quelli che sulla mappa
            # stanno sotto lo stesso pallino perche' hanno le stesse coordinate),
            # una riga aggregata per privati e una per condomini.
            _righe_srv = []
            if not _bmap_srv_e.empty:
                for _r in _bmap_srv_e.sort_values("consumo_annuo_MWh", ascending=False).itertuples():
                    _righe_srv.append({
                        "Edificio": _r.edificio,
                        "Tipo": getattr(_r, "tipologia", "Pubblico"),
                        "Zona": str(_r.cluster).split(" - ")[0],
                        "Domanda (MWh/a)": round(float(_r.consumo_annuo_MWh), 1)})
            if _E_priv > 0:
                _righe_srv.append({
                    "Edificio": (f"Privati agganciati ({_n_priv_buffer} edifici nel buffer × "
                                 f"{fattore_correzione}% allacciamento ≈ {_n_priv_allacciati} utenze)"),
                    "Tipo": "Residenziale privato (aggregato)",
                    "Zona": ", ".join(sorted(str(z).split(" - ")[0]
                                             for z in _priv_in["cluster"].unique())),
                    "Domanda (MWh/a)": round(_E_priv, 1)})
            if _E_cond > 0:
                _righe_srv.append({
                    "Edificio": (f"Condomini ({_n_cond_serviti} edifici, adesione "
                                 f"{tasso_cond}% ≈ {_n_cond_unita_all} unità)"),
                    "Tipo": "Condominio (aggregato)",
                    "Zona": ", ".join(sorted(str(z).split(" - ")[0]
                                             for z in _cond_sel["cluster"].unique())),
                    "Domanda (MWh/a)": round(_E_cond, 1)})
            if _righe_srv:
                _df_srv = pd.DataFrame(_righe_srv)
                _df_srv["Quota (%)"] = (_df_srv["Domanda (MWh/a)"]
                                        / max(_E_tot, 1e-9) * 100).round(1)
                _df_srv = pd.concat([_df_srv, pd.DataFrame([{
                    "Edificio": "TOTALE", "Tipo": "", "Zona": "",
                    "Domanda (MWh/a)": round(_E_tot, 1), "Quota (%)": 100.0}])],
                    ignore_index=True)
                st.markdown("##### 🏢 Edifici serviti e domanda")
                st.dataframe(_df_srv, width="stretch", hide_index=True)
                st.caption("Domanda annua alle utenze, prima delle perdite di rete. Gli "
                           "edifici con le stesse coordinate compaiono qui su righe "
                           "distinte anche se sulla mappa si sovrappongono.")

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

            # ----------------------------------------------------------
            # DIMENSIONAMENTO DI MASSIMA DELLE CONDOTTE
            # ----------------------------------------------------------
            st.markdown("##### \U0001F527 Dimensionamento di massima delle condotte")
            _dc1, _dc2, _dc3 = st.columns(3)
            _ore_eq = _dc1.slider("Ore equivalenti a pieno carico (h/a)", 1200, 2600, 1900,
                                  step=50, key="dom_ore_eq",
                                  help="Serve a convertire l'energia annua in potenza di picco. "
                                       "Clima prealpino: 1.700-2.200 h/a tipiche.")
            _v_max = _dc2.slider("Velocità max acqua (m/s)", 0.5, 3.0, 1.5, step=0.1,
                                 key="dom_vmax",
                                 help="QM/Verenum: 0,5-1,0 negli allacci d'utenza; "
                                      "1,0-2,0 in distribuzione; 2,0-3,0 sulle dorsali.")
            _dT_rete = max(T_mandata_ideale - T_ritorno_ideale, 1)
            _dc3.metric("Salto termico rete", f"{_dT_rete} K",
                        help=f"mandata {T_mandata_ideale}°C - ritorno {T_ritorno_ideale}°C "
                             f"(impostati in alto a sinistra)")

            # potenza di picco alla partenza della dorsale, con contemporaneita QM
            _P_dorsale, _f_sim_rete = _picco_rete_kw(_ore_eq)
            _dn_d, _dint_d, _v_d, _q_d = dimensiona_dn(_P_dorsale, _dT_rete, _v_max)

            _pd1, _pd2, _pd3, _pd4 = st.columns(4)
            _pd1.metric("Potenza di picco dorsale", f"{_P_dorsale:,.0f} kW".replace(",", "."),
                        help=f"{_E_tot:,.0f} MWh/a su {_ore_eq} h · contemporaneità {_f_sim_rete:.2f} sulle sole utenze private e condominiali".replace(",", "."))
            _pd2.metric("Diametro dorsale", f"DN {_dn_d}",
                        help=f"diametro interno {_dint_d:.1f} mm")
            _pd3.metric("Velocità effettiva", f"{_v_d:.2f} m/s")
            _pd4.metric("Portata", f"{_q_d:,.0f} m³/h".replace(",", "."))

            # tabella per fasce di potenza: utile per capire i rami
            with st.expander("📐 Diametri per fascia di potenza (stesso ΔT e velocità)"):
                _righe_dn = []
                for _quota in [1.0, 0.75, 0.5, 0.25, 0.1]:
                    _p = _P_dorsale * _quota
                    _dn, _di, _v, _q = dimensiona_dn(_p, _dT_rete, _v_max)
                    _righe_dn.append({
                        "Tratto": f"{_quota*100:.0f}% del carico",
                        "Potenza (kW)": round(_p),
                        "DN": _dn,
                        "D interno (mm)": round(_di, 1),
                        "Velocità (m/s)": round(_v, 2),
                        "Portata (m³/h)": round(_q, 1),
                    })
                st.dataframe(pd.DataFrame(_righe_dn), width="stretch", hide_index=True)
                st.caption("Dimensionamento indicativo sulla sola velocità. In progetto va "
                           "verificato anche il gradiente di perdita di carico (QM: indicativamente "
                           "≤ 100-250 Pa/m) e il bilanciamento idraulico dei rami.")

            st.session_state["_rete_info"] = {
                "lunghezza_m": float(_len_totale),
                "lunghezza_pubblico_m": float(_len_pub_t),
                "lunghezza_stub_m": float(_len_stub_t),
                "capex_rete": float(_capex_rete_tot),
                "dn_allaccio": int(_dn_r0),
                "costo_m_dorsale": float(_c_dors),
                "costo_m_allaccio": float(_c_ramo),
                "densita": float(_dens),
                "n_utenze": int(_n_utenze_tot),
                "n_privati_agganciati": int(_n_priv_dentro),
                "n_privati_allacciati": int(_n_priv_allacciati),
                "buffer_m": int(buffer_m),
                "costo_m": int(costo_m_tr),
                "traccia_lat": _lat_l, "traccia_lon": _lon_l,
                "stub_lat": _stub_lat_l, "stub_lon": _stub_lon_l,
                "E_pubblico": float(_E_pub),
                "E_condomini": float(_E_cond),
                "E_privati": float(_E_priv),
                "E_totale": float(_E_tot),
                "P_dorsale_kw": float(_P_dorsale),
                "dn_dorsale": int(_dn_d),
                "velocita_m_s": float(_v_d),
                "portata_m3h": float(_q_d),
                "ore_equivalenti": int(_ore_eq),
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
        _metodo_scarto = st.radio(
            "Metodo di prezzo", ["Formula su PSV: PSV \u00d7 (a + b\u00b7w)",
                                 "Scala exergetica (riferimento gas)",
                                 "Prezzi fissi per azienda"],
            key="off_metodo_prezzo",
            help="Scala exergetica: quota del valore del calore venduto, in base alla "
                 "qualita' (parametri in Dimensionamento, passo 5 · Risultati). Formula su PSV: "
                 "\u20ac/MWh ceduto = PSV del mese \u00d7 (a + b\u00b7w), con w peso exergetico "
                 "orario del flusso. Prezzi fissi: \u20ac/MWh costanti.")
        _psv_sel_off = st.selectbox(
            "Serie PSV mensile", list(PSV_SERIE_EUR_MWH.keys()),
            index=len(PSV_SERIE_EUR_MWH) - 1, key="ex_psv_serie",
            help="Medie mensili ARERA del PSV day ahead (\u20ac/Smc convertiti con 10,70 "
                 "kWh/Smc). Serve alla formula, alla scala exergetica e al prezzo di vendita "
                 "agli utenti (gas \u2212 sconto).")
        _psv_off = PSV_SERIE_EUR_MWH[_psv_sel_off]
        st.caption("PSV (\u20ac/MWh): " + " · ".join(
            f"{MONTH_NAMES[i]} {v:.0f}" for i, v in enumerate(_psv_off))
            + f" · media {float(np.mean(_psv_off)):.1f}")
        if _metodo_scarto.startswith("Formula"):
            _fa1, _fa2 = st.columns(2)
            _fa1.number_input("a: quota fissa (% del PSV)", 0.0, 100.0, 20.0, step=0.5,
                              key="off_formula_a")
            _fa2.number_input("b: quota legata alla qualit\u00e0 (% del PSV)", 0.0, 200.0, 15.0,
                              step=0.5, key="off_formula_b")
            st.caption("Esempio: con PSV 50 \u20ac/MWh, a = 20 % e b = 15 %, un flusso con "
                       "w = 0,5 costa 50 \u00d7 (0,20 + 0,15 \u00d7 0,5) = 13,75 \u20ac/MWh.")
        _prezzi_scarto = {}
        if _metodo_scarto == "Prezzi fissi per azienda":
            for az in selected_fonti:
                _prezzi_scarto[az] = st.slider(
                    f"{az} (\u20ac/MWh)", 0, 60, 10, step=1, key=f"off_prezzo_{az}",
                    help="0 = calore ceduto gratuitamente; valori tipici 5-20 \u20ac/MWh.")
        st.session_state["_off_prezzi_scarto"] = _prezzi_scarto

    with st.expander("\u2139\ufe0f Come sono costruiti i profili orari"):
        st.markdown("""
**Domanda**

| utenza | profilo orario |
|---|---|
| Edifici pubblici | dato reale dal CSV, edificio per edificio, riscaldamento e ACS separati, calibrato sui gradi giorno di Maniago |
| Privati | forma **residenziale** propria, con le due punte giornaliere (mattino e sera); la stagionalità segue il fabbisogno reale degli edifici noti |
| Condomini | stessa forma residenziale, ripartizione 85 % riscaldamento / 15 % ACS |

Il profilo residenziale distingue giorni feriali e festivi (nel fine settimana
la punta del mattino si sposta più tardi e si attenua). L'ACS ha una punta
serale marcata e una lieve stagionalità, perché d'inverno l'acqua di rete è più
fredda. La contemporaneità QM agisce a valle sul picco di dimensionamento.

**Calore di scarto** — dalle colonne del CSV dei flussi:

| profilo | comportamento |
|---|---|
| `continuo` | potenza costante nelle ore attive |
| `notturno_18_08` | attivo dalle 18 alle 8 |
| `ore_giorno_N` | N ore consecutive dalle 6 del mattino |
| `cf_random` | ore accese estratte a caso, con probabilità pari al fattore di carico |
| `ciclico_colate` | rampa da `T_alta_C` a `T_out_C` ripetuta n volte al giorno |

La **potenza** utilizzata è quella dello scambiatore quotato (`P_scambiatore_kW`)
dove disponibile, altrimenti quella teorica del flusso: è lo scambiatore a
determinare quanto calore si recupera davvero.

Le **fermate** seguono il calendario reale: ferie centrali di agosto, chiusura
fra Natale e l'Epifania, festività infrasettimanali (compreso San Mauro,
patrono di Maniago), e solo per il residuo i venerdì di manutenzione. Gli
impianti a ciclo continuo che non si fermano a Natale si dichiarano con la
colonna `natale_acceso`.

Resta una semplificazione: la **temperatura è costante** in tutti i profili
tranne `ciclico_colate`, mentre un camino industriale oscilla col carico. E
`cf_random` distribuisce le ore a caso, quindi quel flusso risulta scorrelato
dalla domanda.

**Solare** — l'anno meteorologico conserva la **sequenza reale dei giorni**: per
ogni mese si sceglie, fra le annate della serie PVGIS, quella con irraggiamento
più vicino alla mediana. Restano così le alternanze fra giornate serene e
coperte e le sequenze di più giorni nuvolosi consecutivi, che sono proprio
quelle che mettono alla prova l'accumulo. Con la media mensile, che produce un
giorno tipo sempre uguale, l'accumulo risulterebbe sempre sufficiente e la
taglia verrebbe sottostimata.
""")

    with st.expander("\U0001F4CB Dettaglio flussi da CSV (dati grezzi)"):
        st.dataframe(flussi[["azienda", "flusso", "destinazione", "fluido", "T_alta_C",
                             "T_out_C", "P_kW", "profilo"]],
                     width="stretch", hide_index=True)

    # =========================================================================
    # SOLARE
    # Qui si decide soltanto SE considerare un campo solare fra le fonti di
    # calore. Tecnologia, superficie e temperatura di esercizio si impostano
    # nella scheda Dimensionamento, insieme alle altre scelte di impianto,
    # perche' e' li' che se ne vede l'effetto sul dispatch.
    # =========================================================================
    st.divider()
    st.markdown("#### \u2600\ufe0f Solare termico")
    _sol_on = st.checkbox(
        "Considera un campo di collettori solari termici", value=False,
        key="off_sol_on",
        help="Attivandolo, nella scheda **Dimensionamento** compaiono superficie, "
             "temperatura di esercizio e costo del campo. Qui si decide soltanto se "
             "il solare termico rientra fra le fonti di calore.")
    if _sol_on:
        st.info("☀️ Solare termico attivo. Vai in **Dimensionamento**, passo "
                "*2 · Tecnologie*, per dimensionare il campo.")
        _dim_sol = st.session_state.get("_dim_solare_conf", {}) or {}
        if _dim_sol.get("area_m2"):
            _s1, _s2, _s3 = st.columns(3)
            _s1.metric("Configurazione", _dim_sol.get("tipo", "—"))
            _s2.metric("Superficie", f"{_dim_sol['area_m2']:,} m²".replace(",", "."))
            _s3.metric("Calore prodotto",
                       f"{_dim_sol.get('termico_mwh', 0):,.0f} MWh/a".replace(",", "."))
    else:
        st.caption("Nessun campo solare termico: le fonti di calore sono i soli flussi "
                   "di scarto selezionati sopra.")

    st.caption("I **moduli ibridi** non si impostano qui: producendo elettricità oltre "
               "al calore, si dimensionano nel passo **4 · Carico elettrico** del Dimensionamento, dove i due "
               "prodotti si valutano insieme. Il calore che producono rientra poi nel "
               "bilancio termico con un trasferimento esplicito. Il **fotovoltaico** "
               "puro, che non produce calore, sta solo in quella scheda.")

    st.session_state["_off_solare_attivo"] = bool(_sol_on)


    off = offerta[offerta["id_flusso"].isin(selected_flussi)].copy()
    off["month"] = off["datetime"].dt.month
    off = off[(off["month"] >= month_range_o[0]) & (off["month"] <= month_range_o[1])]

    with col_contenuto2:
        st.markdown("#### \U0001F3ED Sorgenti di scarto e sottocentrale")
        _pw = (off.groupby("azienda")["MWh"].sum() if not off.empty else pd.Series(dtype=float))
        _tot_pw = float(_pw.sum()) if len(_pw) else 0.0

        # Percorso delle condotte di adduzione dalle aziende alla sottocentrale,
        # calcolato sulle strade reali come nella scheda Domanda. In mancanza
        # del grafo OSM si ripiega sul collegamento diretto.
        _str_res = carica_grafo_strade(GRAFO_CENTRO_LAT, GRAFO_CENTRO_LON,
                                       raggio_km=GRAFO_RAGGIO_KM)
        _str_off, _ = _str_res if isinstance(_str_res, tuple) else (_str_res, None)
        _G_off = build_grafo_stradale(_str_off) if _str_off is not None else None

        fig_src = go.Figure()
        _len_add = {}
        for _n, (_la, _lo) in AZIENDE_COORD.items():
            _match = [k for k in _pw.index if str(k).startswith(_n)]
            _e = float(_pw[_match].sum()) if _match else 0.0
            _att = _e > 0
            _w = (2.5 + 6 * min(_e / max(_tot_pw, 1), 1)) if _att else 1.2
            _col = COLOR_OFFERTA if _att else "#666666"
            _tracciato = None
            if _G_off is not None:
                try:
                    _nodi_ad, _dsn = snap_a_strade([_la, CENTRALE_LAT],
                                                   [_lo, CENTRALE_LON], _str_off)
                    import networkx as _nx
                    _path = _nx.dijkstra_path(_G_off, _nodi_ad[0], _nodi_ad[1],
                                              weight="weight")
                    _lt = [_la] + [_str_off["nodi"][k][0] for k in _path] + [CENTRALE_LAT]
                    _ln = [_lo] + [_str_off["nodi"][k][1] for k in _path] + [CENTRALE_LON]
                    _lung = _nx.dijkstra_path_length(_G_off, _nodi_ad[0], _nodi_ad[1],
                                                     weight="weight") + float(_dsn.sum())
                    _tracciato = (_lt, _ln, _lung)
                except Exception:
                    _tracciato = None
            if _tracciato is None:
                _x, _y = _latlon_a_xy(np.array([_la, CENTRALE_LAT]),
                                      np.array([_lo, CENTRALE_LON]))
                _tracciato = ([_la, CENTRALE_LAT], [_lo, CENTRALE_LON],
                              float(np.hypot(_x[1] - _x[0], _y[1] - _y[0])) * 1.35)
            _lt, _ln, _lung = _tracciato
            _len_add[_n] = _lung
            fig_src.add_trace(go.Scattermap(
                lat=_lt, lon=_ln, mode="lines",
                line=dict(width=_w, color=_col),
                showlegend=False, opacity=0.9 if _att else 0.35,
                hovertext=f"{_n} → sottocentrale: {_lung:,.0f} m".replace(",", "."),
                hoverinfo="text"))
            fig_src.add_trace(go.Scattermap(
                lat=[_la], lon=[_lo], mode="markers+text",
                marker=dict(size=(13 + 20 * min(_e / max(_tot_pw, 1), 1)) if _att else 10,
                            color=_col),
                text=[_n], textposition="top right", textfont=dict(size=12, color="#DDDDDD"),
                name=_n,
                hovertext=[f"{_n}<br>{_e:,.0f} MWh/a nel periodo<br>"
                           f"adduzione {_lung:,.0f} m".replace(",", ".")
                           if _att else f"{_n}<br>nessun flusso selezionato"],
                hoverinfo="text", showlegend=False))
        fig_src.add_trace(go.Scattermap(
            lat=[CENTRALE_LAT], lon=[CENTRALE_LON], mode="markers+text",
            marker=dict(size=20, color="#FF9F1C"), text=["SOTTOCENTRALE"],
            textposition="bottom center",
            textfont=dict(size=13, color="#FF9F1C"), name="Sottocentrale",
            hovertext=[f"Sottocentrale<br>{CENTRALE_LAT:.4f}, {CENTRALE_LON:.4f}"],
            hoverinfo="text", showlegend=False))
        _lat_tutte = [v[0] for v in AZIENDE_COORD.values()] + [CENTRALE_LAT]
        _lon_tutte = [v[1] for v in AZIENDE_COORD.values()] + [CENTRALE_LON]
        fig_src.update_layout(
            **layout_mappa((min(_lat_tutte) + max(_lat_tutte)) / 2,
                           (min(_lon_tutte) + max(_lon_tutte)) / 2, 13.6),
            height=470, margin=dict(t=10, b=0, l=0, r=0))
        st.plotly_chart(fig_src, width="stretch")
        # Lunghezze delle adduzioni salvate SEMPRE, anche senza grafo stradale:
        # prima, senza OSM, la scheda Analisi economica le contava come zero e
        # l'allacciamento alle aziende risultava gratuito.
        _att_len = {k: v for k, v in _len_add.items()
                    if any(str(x).startswith(k) for x in _pw.index)}
        st.session_state["_off_lunghezze_adduzione"] = _att_len
        st.session_state["_off_adduzione_stimata"] = _G_off is None
        if _G_off is not None:
            if _att_len:
                st.caption("Condotte di adduzione lungo le strade: "
                           + " · ".join(f"**{k}** {v:,.0f} m".replace(",", ".")
                                        for k, v in sorted(_att_len.items(),
                                                           key=lambda x: x[1]))
                           + f" — in totale **{sum(_att_len.values()):,.0f} m**".replace(",", "."))
        else:
            st.warning("⚠️ Rete stradale non disponibile: i collegamenti sono mostrati "
                       "in linea d'aria con tortuosità 1,35, quindi come segmenti "
                       "rettilinei. Le lunghezze delle adduzioni sono approssimate.")
            if st.button("🔄 Riprova a scaricare la rete stradale", key="off_retry_osm"):
                try:
                    if os.path.exists("maniago_strade_cache.json"):
                        os.remove("maniago_strade_cache.json")
                except Exception:
                    pass
                try:
                    carica_grafo_strade.clear()
                except Exception:
                    pass
                st.rerun()
        st.divider()


        # =====================================================================
        # QUANTO SCARTO VIENE DAVVERO VALORIZZATO, AZIENDA PER AZIENDA
        # Non conta quanto calore c'e': conta quanto ne serve. Un flusso
        # disponibile solo quando la domanda e' bassa, o su un livello termico
        # che l'impianto non riesce a sfruttare, vale poco per quanto sia grande.
        # =====================================================================
        st.markdown("#### \U0001F4CA Utilizzo effettivo del calore di scarto")
        _utz = st.session_state.get("_off_utilizzo_aziende")
        if _utz is None or (hasattr(_utz, "empty") and _utz.empty):
            st.info("Apri la scheda **Dimensionamento** e configura un assetto: "
                    "qui comparirà quanto del calore offerto da ciascuna azienda "
                    "viene effettivamente valorizzato dall'impianto.")
        else:
            _u = _utz.copy()
            _tot_off = float(_u["offerta_mwh"].sum())
            _tot_uso = float(_u["utilizzata_mwh"].sum())
            _q1, _q2, _q3 = st.columns(3)
            _q1.metric("Offerto dalle aziende", f"{_tot_off:,.0f} MWh/a".replace(",", "."))
            _q2.metric("Effettivamente utilizzato", f"{_tot_uso:,.0f} MWh/a".replace(",", "."),
                       delta=f"{_tot_uso / _tot_off * 100:.0f}% dell'offerto" if _tot_off > 0 else None,
                       delta_color="off")
            _q3.metric("Scartato", f"{_tot_off - _tot_uso:,.0f} MWh/a".replace(",", "."),
                       help="Calore disponibile ma non utilizzabile: accumulo pieno, "
                            "domanda già soddisfatta, o livello termico senza utilizzatori.")

            _fu = go.Figure()
            _fu.add_trace(go.Bar(y=_u["azienda"], x=_u["utilizzata_mwh"], orientation="h",
                                 name="Utilizzato", marker_color=COLOR_OFFERTA,
                                 text=_u["quota_utilizzo_pct"].map(lambda v: f"{v:.0f}%"),
                                 textposition="inside", insidetextanchor="middle"))
            _fu.add_trace(go.Bar(y=_u["azienda"], x=_u["scartata_mwh"], orientation="h",
                                 name="Scartato", marker_color=COLOR_NONCOP))
            _fu.update_layout(barmode="stack", height=max(220, 60 * len(_u)),
                              xaxis_title="MWh/anno",
                              legend=dict(orientation="h", yanchor="bottom", y=1.02),
                              margin=dict(t=30, b=10))
            st.plotly_chart(_fu, width="stretch")

            # costo di modifica in situ per azienda, sui SOLI flussi selezionati
            # (prima si sommavano tutti i flussi dell'azienda: Pietro Rosa
            # risultava a 44.000 EUR, il costo della torre, anche con il solo
            # maglio attivo). I flussi senza quotazione si stimano a potenza con
            # lo stesso EUR/kW dell'Analisi economica, cosi' le due schede danno
            # lo stesso numero.
            _fl_sel_c = flussi[flussi["id_flusso"].isin(selected_flussi)]
            _cq_sel = pd.to_numeric(_fl_sel_c["costo_allacciamento_eur"], errors="coerce")
            _he_stima = float(st.session_state.get("eco_costo_he", 60))
            _cost_az = (_fl_sel_c.assign(
                _c=_cq_sel.fillna(pd.to_numeric(_fl_sel_c["P_kW"], errors="coerce")
                                  .fillna(0.0) * _he_stima))
                .groupby("azienda")["_c"].sum())
            _u["costo_modifica_eur"] = _u["azienda"].map(_cost_az).fillna(0.0)
            _u["eur_per_mwh_utile"] = np.where(
                _u["utilizzata_mwh"] > 1e-9,
                _u["costo_modifica_eur"] * crf(0.04, 20) / _u["utilizzata_mwh"], np.nan)

            _tab_u = _u.rename(columns={
                "azienda": "Azienda", "offerta_mwh": "Offerto (MWh/a)",
                "utilizzata_mwh": "Utilizzato (MWh/a)", "scartata_mwh": "Scartato (MWh/a)",
                "quota_utilizzo_pct": "Utilizzo (%)", "ore_disponibile": "Ore disponibile",
                "ore_utile": "Ore con domanda", "livello": "Livello termico",
                "costo_modifica_eur": "Costo modifica (€)",
                "eur_per_mwh_utile": "Incidenza (€/MWh)"})
            _tab_u["Incidenza (€/MWh)"] = _tab_u["Incidenza (€/MWh)"].round(1)
            st.dataframe(_tab_u, width="stretch", hide_index=True)
            if _u["costo_modifica_eur"].sum() > 0:
                st.caption("Il *costo di modifica* è quello dichiarato nel CSV dei flussi "
                           "(scambiatore e opere in situ). L'*incidenza* lo annualizza a "
                           "20 anni e lo divide per il calore effettivamente valorizzato: "
                           "si somma al prezzo pagato all'azienda e va confrontata con il "
                           "costo delle alternative. Le condotte di adduzione sono "
                           "conteggiate a parte nella scheda *Analisi economica*.")

            _scarse = _u[_u["quota_utilizzo_pct"] < 40]
            if not _scarse.empty:
                _nomi = ", ".join(f"**{r.azienda}** ({r.quota_utilizzo_pct:.0f}%)"
                                  for r in _scarse.itertuples())
                st.warning(
                    f"⚠️ Utilizzo sotto il 40 % per: {_nomi}. Il costo dell'allacciamento "
                    f"si ripartisce su poco calore: verifica nella scheda *Analisi economica* "
                    f"se l'investimento su questi flussi si giustifica, oppure valuta un "
                    f"accumulo maggiore per assorbire i picchi di disponibilità.")
            _buone = _u[_u["quota_utilizzo_pct"] >= 80]
            if not _buone.empty:
                st.success(
                    f"✅ Utilizzo sopra l'80 % per {len(_buone)} "
                    f"{'azienda' if len(_buone) == 1 else 'aziende'}: "
                    + ", ".join(_buone["azienda"]) + ".")
            st.caption("La quota scartata di ogni azienda è calcolata ora per ora, "
                       "ripartendo il calore in eccesso su ciascun livello termico in "
                       "proporzione a quanto ogni azienda vi contribuisce in quel momento. "
                       "La colonna *Ore con domanda* indica quante ore il flusso è "
                       "disponibile mentre la rete ha effettivamente bisogno di calore.")

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
            st.plotly_chart(fig_o, width="stretch")

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
        st.plotly_chart(fig_comp, width="stretch")

        if righe_riep:
            riepilogo = pd.DataFrame(righe_riep).sort_values(
                f"Utilizzabile a T≥{T_mandata_ideale}°C (MWh/a)", ascending=False)
            st.dataframe(riepilogo, width="stretch", hide_index=True)
    else:
        st.info("Nessun flusso selezionato con dati di temperatura in questo periodo.")


# =============================================================================
# TAB 3 - DIMENSIONAMENTO
# =============================================================================
with tab_dimensionamento:
    st.markdown("### Dimensionamento — schema a cascata (3 accumuli + 2 HP)")

    # Si dimensiona sugli edifici effettivamente SERVITI dal tracciato, non su
    # tutti quelli selezionati: i pubblici potati o senza coordinate non hanno
    # un tubo che li raggiunga, quindi non generano ne' domanda ne' ricavi.
    edifici_dim = (st.session_state.get("_dom_edifici_serviti")
                   or st.session_state.get("_dom_edifici")
                   or buildings.loc[buildings["tipo_utenza"] == "Pubblico", "edificio"].tolist())
    _esclusi_dim = st.session_state.get("_dom_esclusi_rete") or []
    flussi_dim = st.session_state.get("_off_flussi") or flussi["id_flusso"].tolist()
    eredita_ok = bool(st.session_state.get("_dom_edifici")) and bool(st.session_state.get("_off_flussi"))
    zone_dim = st.session_state.get("_dom_zone", [])
    fattore_priv = st.session_state.get("_dom_fattore_privato", 1.0)
    fattore_cond = st.session_state.get("_dom_fattore_condomini", 1.0)

    dom_dim = domanda[domanda["edificio"].isin(edifici_dim)].copy()
    is_priv = dom_dim["tipo_utenza"] == "Privato (potenziale)"
    dom_dim.loc[is_priv, "MWh_riscaldamento"] *= fattore_priv
    dom_dim.loc[is_priv, "MWh_ACS"] *= fattore_priv
    # i condomini prima entravano al 100 % a 9 MWh/unita', ignorando consumo per
    # unita' e tasso di adesione impostati nella scheda Domanda
    is_cond_d = dom_dim["tipo_utenza"] == "Condominio"
    dom_dim.loc[is_cond_d, "MWh_riscaldamento"] *= fattore_cond
    dom_dim.loc[is_cond_d, "MWh_ACS"] *= fattore_cond
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

    # =========================================================================
    # FLUSSO GUIDATO IN 4 PASSI
    # 1 livelli termici -> 2 tecnologie -> 3 taglie -> 4 risultati
    # Ogni passo mostra subito l'effetto della scelta, cosi' si procede
    # sapendo cosa si sta decidendo invece di riempire moduli.
    # =========================================================================
    # step_el: passo 4 "Carico elettrico" (ex scheda separata); step4 resta il
    # contenitore dei Risultati, che ora e' il passo 5
    step1, step2, step3, step_el, step4 = st.tabs([
        "1 · Livelli termici",
        "2 · Tecnologie",
        "3 · Taglie e accumuli",
        "4 · Carico elettrico",
        "5 · Risultati",
    ])

    # ---------------------------------------------------------------- PASSO 1
    with step1:
        st.markdown("#### Livelli termici della rete")
        st.caption("Sono la decisione che condiziona tutto il resto: stabiliscono "
                   "quanto calore di scarto e' utilizzabile direttamente e quanto "
                   "va risollevato dalle pompe di calore.")
        _t1, _t2 = st.columns([1, 2])
        with _t1:
            st.metric("Mandata", f"{T_mandata_ideale} °C")
            st.metric("Ritorno", f"{T_ritorno_ideale} °C")
            st.caption("Mandata e ritorno si impostano nella scheda **Domanda**, "
                       "in alto a sinistra: valgono per tutto lo studio.")
            T_int = st.slider("Anello intermedio (°C)", 40, 60, 45, key="dim_tint",
                              help="Livello da cui la HP alta T solleva fino alla mandata. "
                                   "Piu' e' alto, meno lavora la pompa ma meno scarto "
                                   "risulta utilizzabile. 45-50 °C e' l'ottimo tipico.")
        with _t2:
            _qh, _qi, _ql, _qlb, _bT, _qib, _bTi = routing_flussi(
                off_all, idx_h, T_mandata_ideale, T_int)
            _tot_scarto = float(_qh.sum() + _qi.sum() + _ql.sum())
            st.markdown("**Dove finisce il calore di scarto disponibile**")
            _r1, _r2, _r3 = st.columns(3)
            _r1.metric("🔴 Uso diretto", f"{_qh.sum():,.0f} MWh".replace(",", "."),
                       help=f"scarto già sopra la mandata di {T_mandata_ideale} °C: "
                            f"non serve alcuna pompa di calore")
            _r2.metric("🟠 Anello intermedio", f"{_qi.sum():,.0f} MWh".replace(",", "."),
                       help=f"tra {T_int} e {T_mandata_ideale} °C: alimenta "
                            f"l'evaporatore della HP alta T")
            _r3.metric("🔵 Anello basso", f"{_ql.sum():,.0f} MWh".replace(",", "."),
                       help=f"sotto {T_int} °C: utilizzabile solo con una seconda "
                            f"pompa di calore")
            if _tot_scarto > 0:
                _fig_liv = go.Figure()
                for _nm, _v, _cl in [("Uso diretto", float(_qh.sum()), COLOR_ALTA_T),
                                     ("Anello intermedio", float(_qi.sum()), COLOR_OFFERTA),
                                     ("Anello basso", float(_ql.sum()), COLOR_HP_BASSA)]:
                    if _v > 1:
                        _fig_liv.add_trace(go.Bar(
                            y=["scarto"], x=[_v], name=_nm, orientation="h",
                            marker_color=_cl,
                            text=f"{_v / _tot_scarto * 100:.0f}%",
                            textposition="inside", insidetextanchor="middle"))
                _fig_liv.update_layout(barmode="stack", height=140,
                                       xaxis_title="MWh/anno", showlegend=True,
                                       legend=dict(orientation="h", yanchor="top", y=-0.3),
                                       margin=dict(t=10, b=10))
                _fig_liv.update_yaxes(showticklabels=False)
                st.plotly_chart(_fig_liv, width="stretch")
                st.caption(f"Domanda annua alla centrale: **{dom_tot:,.0f} MWh** · "
                           f"scarto disponibile: **{_tot_scarto:,.0f} MWh** "
                           f"({_tot_scarto / dom_tot * 100:.0f}% della domanda)".replace(",", "."))
            else:
                st.warning("Nessun flusso di scarto selezionato: scegli le fonti "
                           "nella scheda **Offerta**.")

    # ---------------------------------------------------------------- PASSO 2
    with step2:
        st.markdown("#### Tecnologie di generazione")
        _c1, _c2 = st.columns(2)
        with _c1:
            st.markdown("**Pompa di calore alta temperatura**")
            st.caption(f"Solleva il calore da {T_int} °C alla mandata di "
                       f"{T_mandata_ideale} °C. E' la macchina di base del sistema.")
            eta_hp = st.slider("η 2° principio (%)", 30, 60, 50, key="dim_eta",
                               help="Rendimento rispetto al ciclo di Carnot. "
                                    "Macchine industriali: 45-55 %.") / 100.0
            _cop_prev = float(cop_singola(T_int - 5, T_mandata_ideale, eta_hp))
            st.metric("COP atteso", f"{_cop_prev:.2f}",
                      help=f"da {T_int - 5} °C all'evaporatore a {T_mandata_ideale} °C")
            prezzo_el = st.slider("Prezzo elettricità (€/MWh)", 80, 350, 180, step=10,
                                  key="dim_prezzo_el",
                                  help="Prezzo medio di acquisto, oneri inclusi. "
                                       "Zona Nord 2025: ~116 €/MWh di sola energia.")
        with _c2:
            st.markdown("**Supporto per il residuo**")
            backup_tipo = st.radio("Copre il gap con:", ["HP bassa T", "gas", "biomassa"],
                                   key="dim_backup_tipo")
            is_hp_par = (backup_tipo == "HP bassa T")
            if is_hp_par:
                st.caption("Una seconda pompa di calore recupera il calore sotto "
                           f"{T_int} °C e il calore del terreno, ricaricando l'anello "
                           "intermedio.")
                antigelo = st.slider("Floor antigelo sorgente fredda (°C)", -5, 10, 0,
                                     key="dim_antigelo",
                                     help="Temperatura minima ammessa al circuito, "
                                          "per non congelare il terreno.")
                tipo_sorgente = st.selectbox(
                    "Sorgente fredda", list(SORGENTI_BASSA_T.keys()),
                    index=2, key="dim_tipo_sorg",
                    help="Da dove la pompa a bassa temperatura preleva il calore "
                         "quando il calore di scarto non basta. La scelta pesa "
                         "molto su costi e ingombri: le opere sono confrontate "
                         "nel passo 5 · Risultati, a valle del calcolo.")
                _sp = SORGENTI_BASSA_T[tipo_sorgente]
                if tipo_sorgente == "acqua di falda":
                    resa_sorgente = st.slider("Resa per pozzo (l/s)",
                                              float(_sp["resa_min"]), float(_sp["resa_max"]),
                                              float(_sp["resa_tip"]), step=5.0,
                                              key="dim_resa_sorg")
                    costo_sorgente = st.slider("Costo per pozzo (€)",
                                               float(_sp["costo_min"]), float(_sp["costo_max"]),
                                               float(_sp["costo_tip"]), step=5000.0,
                                               key="dim_costo_sorg")
                else:
                    resa_sorgente = st.slider(
                        f"Resa specifica (W per {_sp['unita'].split()[1] if tipo_sorgente=='sonde verticali' else 'm²'})",
                        float(_sp["resa_min"]), float(_sp["resa_max"]),
                        float(_sp["resa_tip"]), step=1.0, key="dim_resa_sorg",
                        help="Dipende dalla conducibilità del terreno e dalla presenza "
                             "di falda. Nelle ghiaie sature dell'alta pianura friulana "
                             "ci si colloca nella parte alta della forchetta.")
                    costo_sorgente = st.slider(
                        f"Costo unitario (€ per {_sp['unita'].split()[0]})",
                        float(_sp["costo_min"]), float(_sp["costo_max"]),
                        float(_sp["costo_tip"]), step=1.0, key="dim_costo_sorg")
                st.caption(_sp["note"])
                capex_kw_bk = 700.0
                opex_bk_mwh = 0.0
            else:
                antigelo = 0
                tipo_sorgente = None
                resa_sorgente = None
                costo_sorgente = None
                st.caption(f"**Merit order**: la HP alta T lavora sempre per prima; "
                           f"il {backup_tipo} interviene solo sul residuo che la pompa "
                           f"non riesce a coprire.")
                if backup_tipo == "gas":
                    rend_gas = st.slider("Rendimento caldaia (%)", 85, 98, 92,
                                         key="dim_rend_gas") / 100.0
                    prezzo_gas = st.slider("Prezzo gas (€/MWh)", 40, 160, 90,
                                           key="dim_prezzo_gas")
                    capex_kw_bk = st.slider("CAPEX caldaia (€/kW)", 60, 300, 120, step=10,
                                            key="dim_capex_gas")
                    # ETS2 anche sul gas della centrale (impianto sotto i 20 MW,
                    # fuori dall'ETS1): stesso prezzo impostato per il riferimento utente
                    _ets2_bk = float(st.session_state.get("ex_ets2", 85))
                    opex_bk_mwh = (prezzo_gas + _ets2_bk * EF_GAS_T_MWH_PCS) / rend_gas
                    st.caption(f"Comprende l'ETS2 a {_ets2_bk:.0f} €/t "
                               f"(+{_ets2_bk * EF_GAS_T_MWH_PCS:.1f} €/MWh di gas), impostato "
                               f"nel riquadro della scala exergetica al passo 5.")
                else:
                    rend_bio = st.slider("Rendimento caldaia (%)", 75, 92, 85,
                                         key="dim_rend_bio") / 100.0
                    costo_cip = st.slider("Costo cippato (€/MWh)", 20, 60, 35,
                                          key="dim_costo_bio")
                    capex_kw_bk = st.slider("CAPEX caldaia (€/kW)", 300, 900, 550, step=25,
                                            key="dim_capex_bio")
                    opex_bk_mwh = costo_cip / rend_bio
                    st.caption("⚠️ Nota QM: il Handbook suggerisce l'opposto — biomassa "
                               "in base con molte ore equivalenti e fossile in punta. "
                               "Come supporto avrà poche ore/anno a fronte di un CAPEX alto.")
                st.metric("Costo del calore di supporto", f"{opex_bk_mwh:.0f} €/MWh")
        backup_cop = None
        st.divider()
        _a1, _a2 = st.columns(2)
        with _a1:
            costo_m3 = st.slider("CAPEX accumuli (€/m³)", 80, 1500, 500, step=20,
                                 key="dim_costo_m3",
                             help="IEA DHC F1 Tab.3: 110-200 €/m³ sopra i 2.000 m³; "
                                      "1.000 €/m³ è conservativo per serbatoi in acciaio piccoli.")
        with _a2:
            strat_on = st.checkbox("Accumulo intermedio stratificato", value=True,
                                   key="dim_strat",
                                   help="Un serbatoio ben progettato non mescola: l'acqua "
                                        "più calda resta in alto e viene prelevata per prima, "
                                        "così l'evaporatore della pompa alta T lavora sullo "
                                        "strato migliore invece che su una media. Conta solo "
                                        "quando arrivano flussi di scarto a temperature "
                                        "diverse; a parità di temperatura non cambia nulla. "
                                        "Disattivalo per simulare un accumulo a mescolamento.")
            if strat_on:
                st.caption("Strati da 5 K tra l'anello intermedio e la mandata. "
                           "Il calore in eccesso trabocca dallo strato più freddo, "
                           "che è il meno pregiato.")
            else:
                st.caption("⚠️ Modello a mescolamento perfetto: il COP della pompa alta T "
                           "viene calcolato sulla temperatura nominale dell'anello. "
                           "È l'ipotesi conservativa.")


        # ------------------------------------------------------------------
        # SOLARE TERMICO
        # Si attiva nella scheda Offerta, dove si decide se considerarlo fra le
        # fonti di calore; qui se ne sceglie la taglia, perche' e' in questa
        # scheda che se ne vede l'effetto sul dispatch.
        # Qui compaiono i soli collettori termici. I moduli ibridi producono
        # anche elettricita' e vanno quindi dimensionati nella scheda Carico
        # elettrico, dove i due prodotti si valutano insieme; il calore che
        # producono rientra qui attraverso il trasferimento esplicito.
        # ------------------------------------------------------------------
        st.divider()
        st.markdown("**☀️ Solare termico**")
        solare_on = bool(st.session_state.get("_off_solare_attivo", False))
        solar_low = np.zeros(len(dom_arr))
        capex_solare = 0.0
        area_sol = 0
        n_pvt = 0
        pvt_el_mwh = 0.0
        ricavo_pvt_el = 0.0
        tipo_solare = "assente"
        _serie_el_dim = np.zeros(len(HOURS_2024))
        _tf_in = 45

        if not solare_on:
            st.caption("Disattivato. Per considerarlo, spunta *Considera un campo solare "
                       "fra le fonti di calore* nella scheda **Offerta**.")
        else:
            _ds1, _ds2, _ds3 = st.columns(3)
            _area_in = _ds1.number_input("Superficie del campo (m²)", min_value=0,
                                         max_value=50000, value=2000, step=100,
                                         key="dim_area_sol")
            _tf_in = _ds2.slider("Temperatura di esercizio (°C)", 25, 100, 45, step=5,
                                 key="dim_tf_sol",
                                 help="Più è bassa, più rende il campo: a 70 °C si "
                                      "ottiene circa la metà del calore che si avrebbe "
                                      "a 45 °C, a parità di superficie. Deve però essere "
                                      "compatibile con l'anello che alimenta.")
            _cap_mq = _ds3.slider("Costo del campo (€/m²)", 100, 1200, 450, step=10,
                                  key="dim_capex_sol_mq",
                                  help="Collettori, strutture di supporto, circuito "
                                       "idraulico e regolazione. Un campo di grande "
                                       "taglia sta sui 300-500 €/m²; su coperture "
                                       "esistenti si può superare gli 800.")
            area_sol = int(_area_in)
            tipo_solare = "Collettori termici"
            _st_ = genera_offerta_solare(pvgis, area_sol, 0.45).set_index("datetime")
            solar_low = _st_["MWh"].reindex(idx_h, fill_value=0).values
            capex_solare = area_sol * _cap_mq

            _mm1, _mm2, _mm3 = st.columns(3)
            _mm1.metric("Calore", f"{solar_low.sum():,.0f} MWh/a".replace(",", "."))
            _mm2.metric("CAPEX", f"{capex_solare / 1000:,.0f} k€".replace(",", "."))
            _p_pk_s = (solar_low.max() * 1000.0) if len(solar_low) else 0.0
            _mm3.metric("Costo specifico",
                        f"{capex_solare / max(_p_pk_s, 1):,.0f} €/kW".replace(",", "."),
                        help=f"riferito ai {_p_pk_s:,.0f} kW di picco raggiunti "
                             f"nell'anno simulato".replace(",", "."))
            if not is_hp_par:
                st.warning("⚠️ Il calore solare alimenta l'anello basso, che senza pompa "
                           "a bassa temperatura non ha utilizzatori: verrebbe scartato "
                           "mentre il CAPEX resta a bilancio.")

        # --- calore dei moduli ibridi trasferito dalla scheda elettrica ---
        # I moduli ibridi si dimensionano di la', dove elettricita' e calore si
        # valutano insieme; qui ne arriva il contributo termico, che alleggerisce
        # il carico delle pompe di calore.
        _ibr = st.session_state.get("_el_ibrido_da_elettrico") or {}
        if _ibr.get("attivo") and _ibr.get("area_m2", 0) > 0:
            _s_ibr = np.asarray(_ibr.get("serie_termica", np.zeros(len(dom_arr))),
                                dtype=float)
            if _s_ibr.size == len(dom_arr):
                solar_low = solar_low + _s_ibr
                capex_solare += _ibr["area_m2"] * (_ibr["costo_pannello"]
                                                   / CATALOGO_PVT[_ibr["modello"]]["area_lorda_m2"])
                area_sol += int(_ibr["area_m2"])
                n_pvt = int(_ibr["area_m2"] / CATALOGO_PVT[_ibr["modello"]]["area_lorda_m2"])
                _serie_el_dim = np.asarray(_ibr.get("serie_elettrica",
                                                    np.zeros(len(HOURS_2024))), dtype=float)
                pvt_el_mwh = float(_serie_el_dim.sum())
                tipo_solare = (f"{tipo_solare} + ibridi" if solare_on
                               else f"Ibridi {CATALOGO_PVT[_ibr['modello']]['nome']}")
                solare_on = True
                _c1i, _c2i, _c3i = st.columns(3)
                _c1i.metric("Moduli ibridi (dalla scheda elettrica)",
                            f"{_ibr['area_m2']:,.0f} m²".replace(",", "."))
                _c2i.metric("Calore che portano",
                            f"{_s_ibr.sum():,.0f} MWh/a".replace(",", "."))
                _c3i.metric("Elettricità",
                            f"{pvt_el_mwh:,.0f} MWh/a".replace(",", "."))
                st.caption(f"Dimensionati nel passo **4 · Carico elettrico** "
                           f"({CATALOGO_PVT[_ibr['modello']]['nome']}, "
                           f"{_ibr['T_esercizio']:.0f} °C) e trasferiti qui. "
                           f"Se li modifichi là, ritrasferiscili e rilancia il "
                           f"dimensionamento.")
                if st.button("Rimuovi i moduli ibridi dal bilancio termico",
                             key="dim_rimuovi_ibr"):
                    st.session_state.pop("_el_ibrido_da_elettrico", None)
                    st.rerun()

        st.session_state["_dim_solare_conf"] = {
            "attivo": solare_on, "tipo": tipo_solare, "area_m2": area_sol,
            "n_pannelli": n_pvt, "capex": capex_solare,
            "termico_mwh": float(solar_low.sum()), "elettrico_mwh": pvt_el_mwh,
            "T_esercizio": _tf_in,
        }
        st.session_state["_dim_serie_el_solare"] = _serie_el_dim
        st.session_state["_dim_serie_el_solare_term"] = (
            np.asarray(_ibr.get("serie_termica", np.zeros(len(dom_arr))), dtype=float)
            if _ibr.get("attivo") else np.zeros(len(dom_arr)))

        # ------------------------------------------------------------------
        # AUTOPRODUZIONE ELETTRICA -> passo 4
        # La scelta si fa in testa al passo 4 "Carico elettrico", dove si vede
        # subito cosa comporta; il codice resta qui perche' il valore serve gia'
        # all'ottimizzazione del passo 3.
        # ------------------------------------------------------------------
        with step_el:
            st.markdown("#### ⚡ Carico elettrico delle pompe di calore")
            if pvt_el_mwh > 0:
                st.caption(f"Il dimensionamento include moduli ibridi che producono "
                           f"**{pvt_el_mwh:,.0f} MWh/a** elettrici.".replace(",", "."))
            considera_el = st.checkbox(
                "Includi l'autoproduzione elettrica (fotovoltaico, ibridi, batterie) "
                "nel dimensionamento",
                value=False, key="dim_considera_el",
                help="Acceso: il costo dell'elettricità delle pompe di calore nei "
                     "Risultati, nel costo del calore e nell'Analisi economica è quello "
                     "che risulta da questo passo (acquisti dalla rete meno vendita "
                     "dell'eccedenza) e l'investimento negli impianti si aggiunge al "
                     "CAPEX. Spento: l'elettricità si paga tutta al prezzo del passo 2 "
                     "e gli scenari restano confrontabili sulla sola parte termica.")
            if considera_el:
                st.success("✅ **Incluso.** Il risultato di questo passo entra nei "
                           "Risultati (passo 5), negli scenari salvati e nell'Analisi "
                           "economica. Le taglie termiche del passo 3 non cambiano: "
                           "l'autoproduzione si dimensiona sui consumi delle pompe che "
                           "ne risultano e si ricalcola da sola quando quei consumi "
                           "cambiano.")
            else:
                st.info("**Non incluso.** Le pompe di calore comprano tutta "
                        "l'elettricità dalla rete al prezzo del passo 2. Spunta la "
                        "casella per dimensionare fotovoltaico, ibridi e batterie.")
        st.session_state["_dim_considera_el"] = considera_el
        st.session_state["_dim_serie_el_solare"] = _serie_el_dim

        (q_hot_arr, q_int_arr, q_low_arr, q_low_bins, bin_T,
         q_int_bins, bin_T_int) = routing_flussi(off_all, idx_h, T_mandata_ideale, T_int)
        q_low_bins_eff = q_low_bins.copy()
        if solare_on:
            q_low_bins_eff[:, -1] = q_low_bins_eff[:, -1] + solar_low

    # ---------------------------------------------------------------- PASSO 3
    with step3:
        st.markdown("#### Taglie delle macchine e volumi di accumulo")
        st.caption("Prima si lascia che il programma cerchi la configurazione migliore, "
                   "poi si può ritoccarla. I risultati nel passo 5 si aggiornano a ogni "
                   "modifica, senza premere nulla.")

        _d1, _d2 = st.columns([1, 1])
        with _d1:
            v_max_acc = st.slider("Volume massimo per accumulo (m³)", 100, 5000, 1500,
                                  step=100, key="dim_v_max",
                                  help="Tetto imposto alla ricerca. Oltre qualche migliaio "
                                       "di metri cubi un serbatoio non è più un componente "
                                       "di centrale ma un'opera civile a sé, con costi e "
                                       "ingombri di altra natura.")
        with _d2:
            st.metric("Picco da coprire", f"{picco_kw:,.0f} kW".replace(",", "."),
                      help=f"contemporaneità QM applicata: {_f_sim:.2f}")

        if st.button("⚙️ Dimensiona a costo minimo (obiettivo dell'Analisi economica)",
                     key="dim_btn_opt", width="stretch", type="primary",
                     help="Cerca potenze e volumi che rendono minimo il costo annuo di "
                          "centrale con gli stessi parametri dell'Analisi economica: WACC, "
                          "orizzonte, contributo, manutenzione e acquisto del calore di "
                          "scarto. L'elettricita' si valuta al prezzo di rete del passo 2: "
                          "l'autoproduzione (passo 4) si aggiunge dopo e non cambia le "
                          "taglie termiche."):
            with st.spinner("Ricerca della configurazione a costo minimo..."):
                # parametri economici: quelli impostati nell'Analisi economica
                _eco_par = {"wacc": float(st.session_state.get("eco_wacc", 4.0)) / 100.0,
                            "anni": int(st.session_state.get("eco_anni", 25)),
                            "contributo_pct": float(st.session_state.get("eco_contributo", 40)),
                            "om_pct": float(st.session_state.get("eco_om", 2.0))}
                # Le taglie termiche si cercano SEMPRE con il prezzo di rete del
                # passo 2: il dimensionamento termico non dipende dall'autoproduzione.
                # Prima, con l'autoproduzione inclusa, si usava il prezzo effettivo,
                # che a sua volta dipende dai consumi delle pompe: le due
                # ottimizzazioni si rincorrevano.
                _pel_opt = float(prezzo_el)
                # costo del calore di scarto, con il metodo scelto in Offerta
                _met_o = serie_meteo_annua(pvgis)
                _T0_o = (pd.Series(_met_o["T2m"].values, index=pd.to_datetime(_met_o["datetime"]))
                         .reindex(idx_h).interpolate().bfill().ffill().values)
                _pz_o, _ = carica_prezzi_elettrici()
                _pz_o = pd.Series(_pz_o, index=HOURS_2024).reindex(idx_h).ffill().bfill().values
                _pz_o = _pz_o * (_pel_opt / max(float(np.mean(_pz_o)), 1e-9))
                _ss = st.session_state
                _psv_o = PSV_SERIE_EUR_MWH.get(_ss.get("ex_psv_serie"),
                                               list(PSV_SERIE_EUR_MWH.values())[-1])
                _exergetico = str(_ss.get("off_metodo_prezzo",
                                          "Scala exergetica")).startswith(("Scala", "Formula"))
                _prezzi_fissi = _ss.get("_off_prezzi_scarto", {}) or {}

                def _costo_scarto_opt(r):
                    if _exergetico:
                        _m, _a, _i = prezzo_scarto_exergetico(
                            off_all, idx_h, r, _T0_o, _pz_o, float(T_mandata_ideale),
                            float(T_int), _psv_o, float(_ss.get("ex_spread", 50)),
                            float(_ss.get("ex_eta", 0.90)),
                            float(_ss.get("ex_sconto", 15)) / 100.0,
                            float(_ss.get("ex_fisso", 0)), is_hp_par,
                            float(_ss.get("ex_ets2", 85)), float(_ss.get("ex_caldaia", 0)),
                            formula_scarto_da_sessione())
                        return float(_a["costo_eur"].sum()) if not _a.empty else 0.0
                    _u = utilizzo_per_azienda(off_all, idx_h, float(T_mandata_ideale),
                                              float(T_int), r, dom_arr)
                    if _u is None or _u.empty:
                        return 0.0
                    return float(sum(float(_prezzi_fissi.get(a, 0)) * float(e)
                                     for a, e in zip(_u["azienda"], _u["utilizzata_mwh"])))

                best = ottimizza_economico(
                    dom_arr, q_hot_arr, q_int_arr, q_low_bins_eff, bin_T, soil_temp_arr,
                    float(T_mandata_ideale), float(T_ritorno_ideale), float(T_int), 5, eta_hp,
                    backup_tipo, capex_hp_kw, capex_kw_bk, opex_bk_mwh, backup_cop,
                    _pel_opt, costo_m3, capex_solare, perdita_func, float(antigelo),
                    float(picco_kw), float(v_max_acc),
                    {"tipo": tipo_sorgente, "resa": resa_sorgente, "costo": costo_sorgente},
                    _eco_par, _costo_scarto_opt,
                    q_int_bins=q_int_bins, bin_T_int=bin_T_int, stratificato=strat_on,
                    solare_low=(solar_low if solare_on else None))
            if best:
                # arrotondamento per ECCESSO: al centinaio piu' vicino la taglia
                # poteva restare qualche kW sotto il picco, lasciando scoperta
                # l'ora di punta e facendo comparire un allarme fuorviante
                st.session_state["dim_p_alta"] = int(np.ceil(best["P_alta"] / 100) * 100)
                st.session_state["dim_p_bassa"] = int(np.ceil(best["P_bassa"] / 100) * 100)
                st.session_state["dim_p_bk"] = int(np.ceil(best["P_bk"] / 100) * 100)
                st.session_state["dim_v_hot"] = int(round(best["v_hot"] / 50) * 50)
                st.session_state["dim_v_int"] = int(round(best["v_int"] / 50) * 50)
                st.session_state["dim_v_low"] = int(round(best["v_low"] / 50) * 50)
                st.session_state["_opt_casc"] = best
                st.rerun()

        _ores = st.session_state.get("_opt_casc")
        if _ores:
            _sg = [f"HP alta **{_ores['P_alta']:.0f} kW**"]
            _sg.append(f"HP bassa **{_ores['P_bassa']:.0f} kW**" if is_hp_par
                       else f"caldaia **{_ores['P_bk']:.0f} kW**")
            _sg.append(f"accumuli **{_ores['v_hot']:.0f}+{_ores['v_int']:.0f}"
                       f"+{_ores['v_low']:.0f} m³**")
            if _ores.get("obiettivo") == "economico":
                st.success(f"Configurazione a costo minimo · costo annuo di centrale "
                           f"**{_ores['costo_annuo'] / 1000:,.0f} k€/a** "
                           f"({_ores['lcoh']:.1f} €/MWh prodotto, comprende scarto e "
                           f"manutenzione) · quota FER **{_ores['quota_fer']:.0f}%** — ".replace(",", ".")
                           + " · ".join(_sg))
            else:
                st.success(f"Configurazione a costo minimo · LCOH **{_ores['lcoh']:.1f} €/MWh** "
                           f"· quota FER **{_ores['quota_fer']:.0f}%** — " + " · ".join(_sg))
        else:
            st.info("Non ancora dimensionato: i valori qui sotto sono di primo tentativo. "
                    "Premi **Dimensiona** per la configurazione a costo minimo.")

        st.divider()
        st.markdown("##### Ritocca le taglie")
        _lim_v = int(st.session_state.get("dim_v_max", 1500))
        for k, dv in [("dim_p_alta", int(picco_kw)), ("dim_p_bassa", int(picco_kw * 0.8)),
                      ("dim_p_bk", int(picco_kw))]:
            st.session_state[k] = max(0, min(int(st.session_state.get(k, dv)), _maxp))
        for k, dv in [("dim_v_hot", 0), ("dim_v_int", min(800, _lim_v)),
                      ("dim_v_low", min(400, _lim_v))]:
            st.session_state[k] = max(0, min(int(st.session_state.get(k, dv)), _lim_v))

        _p1, _p2 = st.columns(2)
        with _p1:
            st.markdown("**Potenze installate**")
            P_alta = st.slider("HP alta T (kW)", 0, _maxp, step=100, key="dim_p_alta",
                               help="Macchina di base: solleva il calore dall'anello "
                                    "intermedio alla mandata. Dimensionata sul picco "
                                    "copre da sola tutta la domanda quando c'è scarto.")
            if is_hp_par:
                P_bassa = st.slider("HP bassa T (kW)", 0, _maxp, step=100, key="dim_p_bassa",
                                    help="Recupera il calore sotto l'anello intermedio e "
                                         "quello del terreno. Serve solo la frazione di "
                                         "potenza che alimenta l'evaporatore della HP alta.")
                P_bk = 0
            else:
                P_bassa = 0
                P_bk = st.slider(f"Caldaia {backup_tipo} (kW)", 0, _maxp, step=100,
                                 key="dim_p_bk",
                                 help="Interviene solo sul residuo che la pompa di calore "
                                      "non copre. Va comunque dimensionata sul picco per "
                                      "garantire il servizio a scarto nullo.")
        with _p2:
            st.markdown(f"**Volumi di accumulo** (max {_lim_v:,} m³)".replace(",", "."))
            V_hot = st.slider("Caldo (m³)", 0, _lim_v, step=50, key="dim_v_hot",
                              help=f"a {T_mandata_ideale} °C. Serve solo se ci sono flussi "
                                   f"di scarto già sopra la mandata.")
            V_int = st.slider("Intermedio (m³)", 0, _lim_v, step=50, key="dim_v_int",
                              help=f"a {T_int} °C, alimenta l'evaporatore della HP alta T. "
                                   f"È di norma il più utile: disaccoppia la disponibilità "
                                   f"dello scarto dalla domanda.")
            V_low = st.slider("Basso (m³)", 0, _lim_v, step=50, key="dim_v_low",
                              help="sorgente della HP bassa T e del solare")
            _cap_tot = (V_hot + V_int + V_low) * RHO_CP * max(
                T_mandata_ideale - T_ritorno_ideale, 1) / 1000.0
            _ore_aut = _cap_tot / (dom_tot / 8784) if dom_tot > 0 else 0
            st.caption(f"Capacità termica **{_cap_tot:.1f} MWh** — circa "
                       f"**{_ore_aut:.1f} ore** di domanda media · CAPEX "
                       f"**{(V_hot + V_int + V_low) * costo_m3:,.0f} €**".replace(",", "."))


    # ============================== CALCOLO ==============================
    perd = perdita_func(max(V_hot, V_int, V_low))
    sim = dispatch_cascata(dom_arr, q_hot_arr, q_int_arr, q_low_bins_eff, bin_T, soil_temp_arr,
                           float(T_mandata_ideale), float(T_ritorno_ideale), float(T_int), 5, eta_hp,
                           V_hot, V_int, V_low, P_alta, P_bassa,
                           parallelo=backup_tipo, P_backup_kw=P_bk, backup_cop=backup_cop,
                           antigelo=float(antigelo), perdita_sett_pct=perd,
                           q_int_bins=q_int_bins, bin_T_int=bin_T_int,
                           stratificato=strat_on,
                           solare_low=(solar_low if solare_on else None))
    # serie orarie che alimentano la scheda del carico elettrico: si tengono
    # separate dal dimensionamento termico, che non deve dipenderne
    st.session_state["_dim_serie_elettriche"] = {
        "consumo_hp": (sim["el_alta"] + sim["el_bassa"]),
        "el_alta": sim["el_alta"],
        "el_bassa": sim["el_bassa"],
    }

    # attribuzione alle aziende del calore realmente valorizzato: il risultato
    # viene mostrato nella scheda Offerta, dove si decide quali flussi allacciare
    try:
        st.session_state["_off_utilizzo_aziende"] = utilizzo_per_azienda(
            off_all, idx_h, float(T_mandata_ideale), float(T_int), sim, dom_arr)
    except Exception:
        st.session_state["_off_utilizzo_aziende"] = None

    E_hot, E_alta, E_bassa = sim["E_hot_diretto"], sim["E_hp_alta"], sim["E_hp_bassa"]
    E_bk, E_nc = sim["E_backup"], sim["E_non_coperta"]
    E_fer = E_hot + E_alta + (E_bk if backup_tipo == "biomassa" else 0.0)
    quota_fer = E_fer / dom_tot * 100 if dom_tot > 0 else 0

    fattore_crf = crf(0.04, 20)
    capex_alta = P_alta * capex_hp_kw(P_alta)
    capex_bassa = P_bassa * capex_hp_kw(P_bassa) if is_hp_par else 0.0
    capex_bk = P_bk * capex_kw_bk if not is_hp_par else 0.0
    capex_acc = (V_hot + V_int + V_low) * costo_m3
    # Opere per la sorgente fredda: dimensionate sul picco di prelievo dal
    # terreno, che si conosce solo dopo aver simulato l'anno. E' una voce che
    # negli scenari a sole pompe di calore puo' pesare quanto le macchine.
    capex_sorgente = 0.0
    _pk_ground_kw = float(sim["q_ground"].max()) * 1000.0 if is_hp_par else 0.0
    if is_hp_par and _pk_ground_kw > 0:
        capex_sorgente = float(dimensiona_sorgente_bassa_t(
            _pk_ground_kw, tipo_sorgente, resa_sorgente, costo_sorgente)["costo"])
    capex_sistema = (capex_alta + capex_bassa + capex_bk + capex_acc
                     + capex_solare + capex_sorgente)
    # L'elettricita' prodotta dai pannelli ibridi alimenta le pompe di calore
    # (o viene venduta) e si porta in detrazione dei costi operativi.
    # Prezzo effettivo dell'elettricita': se si tiene conto dell'autoproduzione,
    # la quota autoconsumata non viene acquistata e il costo medio scende.
    prezzo_el_eff = prezzo_el
    quota_autocons = 0.0
    capex_autoproduzione = 0.0
    # firma del risultato elettrico usato in questo calcolo: il passo 4 viene
    # eseguito dopo, e se il suo risultato cambia la pagina si ricalcola subito,
    # cosi' i Risultati non restano indietro di un'interazione
    st.session_state["_el_usato"] = (_firma_el(st.session_state.get("_el_risultato"))
                                     if considera_el else None)
    if considera_el:
        _rel = st.session_state.get("_el_risultato") or {}
        quota_autocons = float(_rel.get("copertura_pct", 0.0)) / 100.0
        if "acquisto_eur" in _rel and float(_rel.get("consumo_mwh", 0)) > 0:
            # costo di esercizio = acquisti dalla rete - ricavo dell'eccedenza,
            # ai prezzi della scheda Carico elettrico; l'investimento in
            # fotovoltaico, ibridi e batterie entra nel CAPEX dell'Analisi economica
            prezzo_el_eff = ((float(_rel["acquisto_eur"]) - float(_rel.get("ricavo_eur", 0)))
                             / float(_rel["consumo_mwh"]))
            capex_autoproduzione = float(_rel.get("capex_eur", 0.0))
        else:
            prezzo_el_eff = prezzo_el * (1.0 - quota_autocons)
    opex_lordo = sim["E_el_tot"] * prezzo_el_eff + E_bk * opex_bk_mwh
    opex = opex_lordo - ricavo_pvt_el
    # l'investimento in autoproduzione si annualizza insieme alla centrale: il
    # risparmio sull'elettricita' e' gia' nell'opex, senza l'investimento il LCOH
    # degli scenari con fotovoltaico risultava troppo basso. Solo indicatore: i
    # flussi di cassa dell'Analisi economica lo contavano gia'.
    costo_annuo = (capex_sistema + capex_autoproduzione) * fattore_crf + opex
    lcoh = costo_annuo / dom_tot if dom_tot > 0 else np.nan
    # taglie dell'autoproduzione e verifica che l'ottimizzazione elettrica sia
    # stata fatta su questa configurazione (consumo delle pompe uguale)
    _rel_s = (st.session_state.get("_el_risultato") or {}) if considera_el else {}
    kwp_autoprod = float(_rel_s.get("kwp_pv", 0.0))
    batt_autoprod = float(_rel_s.get("batteria_mwh", 0.0))
    ibr_autoprod = float(_rel_s.get("ibrido_m2", 0.0))
    _cons_ott = float(_rel_s.get("consumo_mwh", 0.0))
    _cons_ora = float(sim["E_el_tot"])
    autoprod_da_rifare = bool(considera_el) and (
        not _rel_s or abs(_cons_ott - _cons_ora) > max(0.01 * _cons_ora, 1.0))

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
    # Calore consegnato alla rete. La HP bassa T NON va sommata: il suo calore
    # entra nell'anello intermedio ed e' gia' contenuto in quello che la HP alta
    # T consegna in mandata. Contarlo due volte abbassava la quota (58 % invece
    # di ~77 % nello scenario dei pubblici).
    E_fornito = E_hot + E_alta + E_bk
    E_rinnovabile = (E_scarto_tot + E_ground
                     + (E_bk if backup_tipo == "biomassa" else 0.0))
    pct_rinnovabile = E_rinnovabile / E_fornito * 100 if E_fornito > 0 else 0.0

    with step4:
        if eredita_ok:
            st.caption(f"**{len(edifici_dim)} edifici** (zone: {', '.join(zone_dim) if zone_dim else '—'}) "
                       f"· **{len(flussi_dim)} flussi** · mandata/ritorno "
                       f"**{T_mandata_ideale}/{T_ritorno_ideale}°C** · anello intermedio "
                       f"**{T_int}°C**.")
        else:
            st.info(f"Valori predefiniti ({len(edifici_dim)} edifici pubblici, {len(flussi_dim)} flussi).")
        if _esclusi_dim:
            _mwh_escl_dim = float(buildings.loc[buildings["edificio"].isin(_esclusi_dim),
                                                "consumo_annuo_MWh"].sum())
            st.warning(
                f"⚠️ {len(_esclusi_dim)} edifici pubblici selezionati non sono serviti dal "
                f"tracciato (potati dalla soglia di densità o privi di coordinate) e sono "
                f"esclusi dal dimensionamento: "
                f"{_mwh_escl_dim:,.0f}".replace(",", ".") + " MWh/a. "
                f"Dettaglio nella scheda **Domanda**.")

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
                f"Cade nel buffer del tubo pubblico il **{_quota_buf * 100:.0f} %** della "
                f"domanda privata delle zone attive ({_n_priv_agg} edifici): solo quella, "
                f"ridotta dal tasso di allacciamento, entra nel dimensionamento. "
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

        # ------------------------------------------------------------------
        # SCOMPOSIZIONE DELL'ENERGIA PER ORIGINE
        # Le voci sono le sorgenti primarie da cui il calore entra nel sistema,
        # non i componenti che lo erogano: cosi' le quote sommano esattamente
        # alla domanda e nessun contributo viene contato due volte.
        # La pompa a bassa temperatura non compare come voce a se': cio' che
        # preleva dal terreno sta in "loop geotermico", l'elettricita' che
        # assorbe sta nella voce del supporto.
        # ------------------------------------------------------------------
        _q_sol = sim.get("q_da_solare", np.zeros(len(dom_arr)))
        # calore di scarto valorizzato: quello usato direttamente piu' quello
        # risollevato, al netto di elettricita', terreno e solare
        _scarto_h = np.maximum(
            sim["q_hot_direct"] + sim["q_alta"]
            - sim["el_alta"] - sim["el_bassa"] - ground - _q_sol, 0.0)
        _el_hp_alta = sim["el_alta"]
        _el_backup = sim["el_bassa"]

        _bande = [
            ("Calore di scarto", _scarto_h, COLOR_ALTA_T),
            ("Calore solare", _q_sol, COLOR_SOLARE),
            ("Loop geotermico", ground, COLOR_GROUND),
            ("HP alta temperatura", _el_hp_alta, COLOR_HP),
            (f"Fonte di backup ({backup_tipo})",
             _el_backup + sim["q_backup"], COLOR_BACKUP),
        ]

        st.markdown("##### \U0001F4C9 Curva di durata: da dove arriva l'energia")
        order = np.argsort(dom_arr)[::-1]
        x = np.arange(1, len(dom_arr) + 1)
        fig_dur = go.Figure()
        for nome, arr, col in _bande:
            if float(np.asarray(arr).sum()) < 1:
                continue
            fig_dur.add_trace(go.Scatter(x=x, y=np.asarray(arr)[order], mode="lines",
                                         name=nome, stackgroup="c", line=dict(width=0),
                                         fillcolor=hex_to_rgba(col, 0.9)))
        if E_nc > 1:
            fig_dur.add_trace(go.Scatter(x=x, y=sim["non_cop"][order], mode="lines",
                                         name="Non coperto", stackgroup="c",
                                         line=dict(width=0),
                                         fillcolor=hex_to_rgba(COLOR_NONCOP, 0.9)))
        fig_dur.add_trace(go.Scatter(x=x, y=dom_arr[order], mode="lines", name="Domanda",
                                     line=dict(color=COLOR_DOMANDA, width=2.4)))
        fig_dur.update_layout(height=440, xaxis_title="Ore/anno", yaxis_title="MW",
                              legend=dict(orientation="h", yanchor="bottom", y=1.02),
                              margin=dict(t=30, b=10))
        st.plotly_chart(fig_dur, width="stretch")
        st.caption("Le voci sono le sorgenti da cui il calore entra nel sistema: "
                   "**HP alta temperatura** è l'energia elettrica che la pompa aggiunge "
                   "al calore che risolleva, non il totale che consegna. Sommate danno "
                   "esattamente la domanda alla centrale.")


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
            st.plotly_chart(fig_hm, width="stretch")

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
        _quota_nc = E_nc / dom_tot * 100 if dom_tot > 0 else 0.0
        if sim["ore_non_coperte"] == 0:
            st.success("✅ Copertura 100 % in tutte le ore.")
        elif _quota_nc < 0.01:
            st.info(f"✅ Copertura sostanzialmente completa: restano scoperte "
                    f"{sim['ore_non_coperte']} ore per un totale di "
                    f"**{E_nc * 1000:.0f} kWh**, meno di un centesimo di punto "
                    f"della domanda annua. È un residuo di arrotondamento delle "
                    f"taglie, non un deficit di dimensionamento.")
        else:
            st.error(f"⚠️ {sim['ore_non_coperte']} ore non coperte per "
                     f"{E_nc:,.0f} MWh ({_quota_nc:.2f} % della domanda): "
                     f"rilancia il dimensionamento o aumenta le taglie."
                     .replace(",", "."))

        # ---- schema di massima dell'impianto dimensionato ----
        if considera_el and quota_autocons > 0:
            st.info(f"⚡ Il costo dell'elettricità tiene conto dell'autoproduzione: "
                    f"copertura **{quota_autocons * 100:.0f}%** dal passo *4 · Carico "
                    f"elettrico*, prezzo effettivo **{prezzo_el_eff:.0f} €/MWh** invece "
                    f"di {prezzo_el:.0f}. Per confrontare gli scenari su basi omogenee "
                    f"conviene disattivare l'opzione nel passo 2.")
        elif considera_el:
            st.warning("⚡ Autoproduzione attiva ma nessun risultato disponibile: "
                       "apri il passo **4 · Carico elettrico** e configura la generazione.")

        # ---- dimensionamento della sorgente fredda ----
        if is_hp_par and E_ground > 1:
            st.markdown("##### \U0001F573\ufe0f Sorgente fredda della pompa a bassa temperatura")
            _pk_ground = float(sim["q_ground"].max()) * 1000.0
            _ore_gr = int(sim["ore_ground"])
            _gs1, _gs2, _gs3 = st.columns(3)
            _gs1.metric("Potenza di picco richiesta", f"{_pk_ground:,.0f} kW".replace(",", "."),
                        help="Massimo prelievo orario dalla sorgente nel corso dell'anno: "
                             "è questo a dimensionare le opere, non l'energia.")
            _gs2.metric("Energia annua estratta", f"{E_ground:,.0f} MWh".replace(",", "."),
                        help=f"in {_ore_gr} ore di funzionamento")
            _gs3.metric("Ore equivalenti", f"{E_ground * 1000 / max(_pk_ground, 1):,.0f} h".replace(",", "."),
                        help="Poche ore equivalenti significano opere costose usate "
                             "per poco tempo: conviene ridurre la potenza della "
                             "pompa a bassa temperatura e lasciare il resto al supporto.")

            _dg = dimensiona_sorgente_bassa_t(_pk_ground, tipo_sorgente,
                                              resa_sorgente, costo_sorgente)
            _o1, _o2, _o3, _o4 = st.columns(4)
            _o1.metric("Opere", f"{_dg['quantita']:,.0f}".replace(",", ".") + f" {_dg['unita'].split()[0]}")
            _volumi_acqua = None
            if tipo_sorgente == "acqua di falda":
                # portata di prelievo e volumi movimentati: sono i numeri che
                # servono per la domanda di concessione di derivazione
                _q_ls = _dg["quantita"]
                _q_m3h = _dg.get("portata_m3h", _q_ls * 3.6)
                _ore_pren = int((sim["q_ground"] > 1e-9).sum())
                _vol_anno = _q_m3h * _ore_pren
                # volume effettivo, pesato sul prelievo orario reale
                _vol_eff = float((sim["q_ground"] * 1000.0
                                  / (CP_ACQUA_KJ_KG_K * _dg["dt_k"])   # kg/s per MWh/h
                                  ).sum()) * 3600.0 / 1000.0
                _volumi_acqua = {"l_s": _q_ls, "m3_h": _q_m3h,
                                 "m3_anno": _vol_eff, "ore": _ore_pren,
                                 "dt_k": _dg["dt_k"]}
            if _dg["n_pozzi"]:
                _o2.metric("Pozzi", f"{_dg['n_pozzi']}")
            else:
                _o2.metric("Pozzi", "—")
            _sup = _dg["superficie_m2"]
            _o3.metric("Superficie impegnata",
                       f"{_sup / 10000:.2f} ha" if _sup >= 5000 else f"{_sup:,.0f} m²".replace(",", "."))
            _o4.metric("Costo", f"{_dg['costo'] / 1000:,.0f} k€".replace(",", "."),
                       help=f"{_dg['costo'] / max(_pk_ground, 1):,.0f} €/kW estratto".replace(",", "."))

            if _volumi_acqua:
                st.markdown("**Prelievo idrico**")
                _w1, _w2, _w3, _w4 = st.columns(4)
                _w1.metric("Portata di punta", f"{_volumi_acqua['l_s']:,.0f} l/s".replace(",", "."),
                           help=f"pari a {_volumi_acqua['m3_h']:,.0f} m³/h, con un salto "
                                f"termico di {_volumi_acqua['dt_k']:.0f} K sul prelievo".replace(",", "."))
                _w2.metric("Volume annuo", f"{_volumi_acqua['m3_anno'] / 1000:,.0f} migliaia di m³".replace(",", "."),
                           help="Calcolato ora per ora sul prelievo effettivo, non sulla "
                                "portata di punta: è il dato da riportare nella domanda "
                                "di concessione di derivazione.")
                _w3.metric("Ore di prelievo", f"{_volumi_acqua['ore']:,} h/a".replace(",", "."))
                _w4.metric("Portata media", 
                           f"{_volumi_acqua['m3_anno'] / max(_volumi_acqua['ore'], 1):,.0f} m³/h".replace(",", "."),
                           help="Il rapporto fra portata di punta e portata media indica "
                                "quanto il pozzo lavori a carico parziale.")
                st.caption("L'acqua prelevata viene restituita in falda a temperatura "
                           "inferiore: il bilancio idrico è nullo, quello termico no. "
                           "La concessione di derivazione e l'autorizzazione allo scarico "
                           "termico vanno verificate con la Regione, insieme "
                           "all'interferenza con altri pozzi nell'intorno.")

            # confronto fra le tre tecnologie a parità di potenza
            with st.expander("Confronto fra le sorgenti possibili"):
                _rg = []
                for _t in SORGENTI_BASSA_T:
                    _d = dimensiona_sorgente_bassa_t(_pk_ground, _t)
                    _s = _d["superficie_m2"]
                    _rg.append({
                        "Sorgente": _t,
                        "Dimensione": f"{_d['quantita']:,.0f} {_d['unita']}".replace(",", "."),
                        "Pozzi": str(_d["n_pozzi"]) if _d["n_pozzi"] else "—",
                        "Superficie": (f"{_s / 10000:.2f} ha" if _s >= 5000
                                       else f"{_s:,.0f} m²".replace(",", ".")),
                        "Costo (k€)": round(_d["costo"] / 1000),
                        "€/kW": round(_d["costo"] / max(_pk_ground, 1)),
                    })
                st.dataframe(pd.DataFrame(_rg), width="stretch", hide_index=True)
                st.caption(SORGENTI_BASSA_T[tipo_sorgente]["note"])

            if _sup > 20000:
                st.warning(
                    f"⚠️ La sorgente scelta richiede **{_sup / 10000:.1f} ettari**. "
                    f"È una superficie che va reperita e vincolata: sopra le serpentine "
                    f"non si può costruire né piantare alberi. Valuta l'acqua di falda, "
                    f"oppure riduci la potenza della pompa a bassa temperatura lasciando "
                    f"il picco a un supporto a combustibile.")
            elif _dg["costo"] > capex_sistema * 0.4:
                st.warning(
                    f"⚠️ Le opere per la sorgente fredda costano "
                    f"**{_dg['costo'] / 1000:,.0f} k€**, oltre il 40 % del CAPEX di "
                    f"centrale. Con {E_ground * 1000 / max(_pk_ground, 1):,.0f} ore "
                    f"equivalenti l'investimento si ripartisce su poca energia."
                    .replace(",", "."))
            st.session_state["_dim_sorgente"] = _dg
            st.divider()

        st.markdown("##### \U0001F5A5\ufe0f Schema di massima dell'impianto")
        _fl_caldo, _fl_int, _fl_basso = [], [], []
        if not off_all.empty:
            _agg_fl = (off_all[off_all["MWh"] > 0]
                       .groupby("flusso")
                       .agg(T=("T_disponibile", "mean"), E=("MWh", "sum"))
                       .sort_values("E", ascending=False))
            for _nm, _r in _agg_fl.iterrows():
                _voce = (str(_nm)[:26], float(_r["T"]))
                if _r["T"] >= T_mandata_ideale:
                    _fl_caldo.append(_voce)
                elif _r["T"] >= T_int:
                    _fl_int.append(_voce)
                else:
                    _fl_basso.append(_voce)
        _svg = schema_impianto_svg({
            "T_mandata": T_mandata_ideale, "T_ritorno": T_ritorno_ideale, "T_int": T_int,
            "P_alta_kw": P_alta, "P_bassa_kw": P_bassa, "P_backup_kw": P_bk,
            "backup_tipo": backup_tipo,
            "V_hot": V_hot, "V_int": V_int, "V_low": V_low,
            "E_hot": E_hot, "E_alta": E_alta, "E_bassa": E_bassa,
            "E_backup": E_bk, "E_ground": E_ground,
            "cop_alta": sim["cop_alta_medio"], "cop_bassa": sim["cop_bassa_medio"],
            "dn_dorsale": int((st.session_state.get("_rete_info", {}) or {}).get("dn_dorsale", 0)),
            "flussi_caldo": _fl_caldo, "flussi_int": _fl_int, "flussi_basso": _fl_basso,
            "solare_on": solare_on,
        })
        st.image(_svg, width="stretch")
        st.download_button("⬇️ Scarica lo schema (SVG)", data=_svg,
                           file_name="maniago_schema_impianto.svg",
                           mime="image/svg+xml", key="dim_dl_schema")
        st.caption("Schema a blocchi indicativo: riporta le taglie dimensionate e i "
                   "livelli termici, non sostituisce uno schema funzionale di progetto "
                   "(mancano valvole, circolatori, sicurezze, vaso di espansione, "
                   "strumentazione).")
        st.divider()

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
        # stessa scomposizione per origine usata nella curva di durata
        voci = [("Calore di scarto", float(_scarto_h.sum()), COLOR_ALTA_T),
                ("Calore solare", float(np.asarray(_q_sol).sum()), COLOR_SOLARE),
                ("Loop geotermico", E_ground, COLOR_GROUND),
                ("HP alta temperatura", float(sim["el_alta"].sum()), COLOR_HP),
                (f"Fonte di backup ({backup_tipo})",
                 float(sim["el_bassa"].sum()) + E_bk, COLOR_BACKUP)]
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
        st.plotly_chart(fig_mix, width="stretch")
        st.caption("**Calore di scarto** è quello industriale effettivamente valorizzato, "
                   "al netto dell'energia spesa per risollevarlo. **HP alta temperatura** "
                   "è l'elettricità che la pompa aggiunge. **Fonte di backup** comprende "
                   "l'elettricità della pompa a bassa temperatura oppure il combustibile, "
                   "secondo l'assetto scelto.")

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

        if strat_on and q_int_bins is not None and float(q_int_bins.sum()) > 1:
            with st.expander("\U0001F321\ufe0f Stratificazione dell'accumulo intermedio"):
                _e_str = q_int_bins.sum(axis=0)
                _T_ut = (np.asarray(bin_T_int) + float(T_int)) / 2.0
                _cop_str = [float(cop_singola(t - 5, T_mandata_ideale, eta_hp)) for t in _T_ut]
                _df_str = pd.DataFrame({
                    "Strato (°C)": [f"{t - 2.5:.0f}–{t + 2.5:.0f}" for t in bin_T_int],
                    "Energia in ingresso (MWh/a)": np.round(_e_str, 1),
                    "T utile all'evaporatore (°C)": np.round(_T_ut, 1),
                    "COP dello strato": np.round(_cop_str, 2)})
                _df_str = _df_str[_df_str["Energia in ingresso (MWh/a)"] > 0.5]
                st.dataframe(_df_str, width="stretch", hide_index=True)
                _cop_nom = float(cop_singola(T_int - 5, T_mandata_ideale, eta_hp))
                st.caption(
                    f"La pompa alta T preleva dallo strato più caldo disponibile. "
                    f"Con l'accumulo a mescolamento perfetto lavorerebbe sempre a "
                    f"COP {_cop_nom:.2f}; qui il COP medio effettivo risulta "
                    f"**{sim['cop_alta_medio']:.2f}**. La temperatura utile è la media "
                    f"fra quella dello strato e quella di base dell'anello, perché il "
                    f"fluido cede calore raffreddandosi.")

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
            st.plotly_chart(fig_cop, width="stretch")
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
        if capex_sorgente > 0:
            _dgs = dimensiona_sorgente_bassa_t(_pk_ground_kw, tipo_sorgente,
                                               resa_sorgente, costo_sorgente)
            righe.append({"Voce": f"Sorgente fredda: {tipo_sorgente} "
                                  f"({_dgs['quantita']:,.0f} {_dgs['unita'].split()[0]})".replace(",", "."),
                          "CAPEX (\u20ac)": round(capex_sorgente),
                          "OPEX (\u20ac/a)": 0})
        if solare_on:
            if tipo_solare.startswith("Ibrido"):
                righe.append({"Voce": f"Solare ibrido PVT ({n_pvt} pann., {area_sol} m²)",
                              "CAPEX (\u20ac)": round(capex_solare),
                              "OPEX (\u20ac/a)": -round(ricavo_pvt_el)})
            else:
                righe.append({"Voce": f"Solare termico ({area_sol} m²)",
                              "CAPEX (\u20ac)": round(capex_solare),
                              "OPEX (\u20ac/a)": 0})
        st.dataframe(pd.DataFrame(righe), width="stretch", hide_index=True)
        if solare_on and tipo_solare.startswith("Ibrido") and ricavo_pvt_el > 0:
            st.caption(f"L'OPEX negativo del PVT è il valore dell'energia elettrica prodotta "
                       f"({pvt_el_mwh:,.0f} MWh/a), che si porta in detrazione dei consumi "
                       f"delle pompe di calore.".replace(",", "."))

        # --- scomposizione del costo del calore ---
        # Il grafico a torta dice solo quanto pesa una voce sul totale; qui
        # invece ogni voce e' espressa in euro per MWh prodotto, cioe' nella
        # stessa unita' del prezzo di vendita: si legge subito quanto incide
        # ciascun componente sul costo finale del calore.
        df_c = pd.DataFrame(righe)
        _voci_lcoh = []
        for _r in righe:
            _cap_ann = float(_r["CAPEX (\u20ac)"]) * fattore_crf
            _op = float(_r["OPEX (\u20ac/a)"])
            if abs(_cap_ann) > 1:
                _voci_lcoh.append((f"{_r['Voce']} · capitale", _cap_ann / dom_tot, "#5B8DEF"))
            if abs(_op) > 1:
                _voci_lcoh.append((f"{_r['Voce']} · esercizio", _op / dom_tot, "#F4A259"))
        if _voci_lcoh:
            _fig_l = go.Figure()
            _nomi_l = [v[0] for v in _voci_lcoh]
            _val_l = [v[1] for v in _voci_lcoh]
            _col_l = [v[2] for v in _voci_lcoh]
            _fig_l.add_trace(go.Bar(
                y=_nomi_l, x=_val_l, orientation="h", marker_color=_col_l,
                text=[f"{v:+.1f}" if v < 0 else f"{v:.1f}" for v in _val_l],
                textposition="outside"))
            _fig_l.update_layout(
                height=max(200, 42 * len(_voci_lcoh) + 90),
                xaxis_title="€ per MWh di calore prodotto",
                margin=dict(t=36, b=10, l=10, r=40), showlegend=False,
                title=f"Come si compone il costo del calore · totale {lcoh:.1f} €/MWh")
            _fig_l.update_yaxes(autorange="reversed")
            st.plotly_chart(_fig_l, width="stretch")
            st.caption("In blu il capitale annualizzato (CAPEX × CRF), in arancio i costi "
                       "di esercizio. Le voci negative sono ricavi che si portano in "
                       "detrazione. Il totale coincide con il LCOH di sistema.")

        s1, s2, s3, s4 = st.columns(4)
        s1.metric("CAPEX di sistema", f"{capex_sistema:,.0f} \u20ac".replace(",", "."))
        s2.metric("Costo annuo", f"{costo_annuo:,.0f} \u20ac/a".replace(",", "."),
                  help=(f"capitale {(capex_sistema + capex_autoproduzione) * fattore_crf:,.0f}"
                        + (f" (di cui autoproduzione {capex_autoproduzione * fattore_crf:,.0f})"
                           if capex_autoproduzione > 0 else "")
                        + f" + esercizio {opex:,.0f}").replace(",", "."))
        s3.metric("LCOH di sistema", f"{lcoh:.1f} \u20ac/MWh" if not np.isnan(lcoh) else "n/d",
                  help="Costo del calore alla centrale, compreso l'investimento in "
                       "autoproduzione elettrica se attiva. Non comprende rete, O&M e "
                       "personale: quelli sono nella scheda Analisi economica.")
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

    # ---------------------------------------------------------------------
    # PREZZO DEL CALORE DI SCARTO CON LA SCALA EXERGETICA (riferimento gas)
    # ---------------------------------------------------------------------
    with step4:
        with st.expander("\U0001F321\ufe0f Prezzo del calore di scarto con la scala exergetica"):
            st.caption(
                "Il valore di riferimento e' il costo del calore a gas per l'utente, "
                "(PSV medio mensile + spread) / rendimento caldaia, scontato del target. "
                "La scala T0 \u2192 mandata (T0 = temperatura esterna oraria) divide il valore: "
                "lo scarto a T_k pesa ex(T0\u2192T_k) / ex(T0\u2192mandata). Le quantita' "
                "(MWh ceduti, elettricita') vengono dal dispatch; il valore si divide per i "
                "MWh realmente ceduti. Chiusura mensile per tener conto degli accumuli; tetto "
                "pari al margine dopo l'elettricita' delle pompe.")
            # la serie PSV si sceglie in Offerta, accanto al metodo di prezzo
            _psv_sel = st.session_state.get("ex_psv_serie", list(PSV_SERIE_EUR_MWH.keys())[-1])
            if _psv_sel not in PSV_SERIE_EUR_MWH:
                _psv_sel = list(PSV_SERIE_EUR_MWH.keys())[-1]
            _psv_ex = PSV_SERIE_EUR_MWH[_psv_sel]
            st.caption(f"Serie PSV **{_psv_sel}** (si cambia in Offerta) · €/MWh: " + " · ".join(
                f"{MONTH_NAMES[i]} {v:.0f}" for i, v in enumerate(_psv_ex)))
            _x1, _x2, _x3, _x4 = st.columns(4)
            _sconto_ex = _x1.slider("Sconto sul gas (%)", 0, 40, 15, key="ex_sconto") / 100.0
            _spread_ex = _x2.slider("Spread sul PSV (\u20ac/MWh)", 0, 120, 50, step=5,
                                    key="ex_spread",
                                    help="Trasporto, oneri, accise, IVA e margine del venditore "
                                         "che l'utente paga oltre al PSV.")
            _eta_ex = _x3.slider("Rendimento caldaia utente", 0.70, 1.05, 0.90, step=0.01,
                                 key="ex_eta")
            _fisso_ex = _x4.slider("Quota fissa (\u20ac/MWh ceduto)", 0, 30, 0, key="ex_fisso")
            _y1, _y2 = st.columns(2)
            _ets2_ex = _y1.slider("Prezzo ETS2 sul gas per edifici (\u20ac/tCO\u2082)", 0, 150, 85,
                                  step=5, key="ex_ets2",
                                  help="ETS2 operativo dal 2028 (rinviato dal 2027). Nei primi "
                                       "anni la riserva di stabilita' interviene sopra 45 "
                                       "\u20ac/t a prezzi 2020. 45 \u20ac/t valgono circa "
                                       f"{45 * EF_GAS_T_MWH_PCS:.1f} \u20ac/MWh di gas.")
            _cald_ex = _y2.slider("Costi evitati della caldaia (\u20ac/MWh di calore)", 0, 40, 0,
                                  key="ex_caldaia",
                                  help="Manutenzione, terzo responsabile e quota di "
                                       "sostituzione della caldaia che l'utente non paga piu' "
                                       "allacciandosi. Tipicamente 10-20 \u20ac/MWh per edifici "
                                       "pubblici medi.")

            _met_ex = serie_meteo_annua(pvgis)
            _T0_ex = (pd.Series(_met_ex["T2m"].values, index=pd.to_datetime(_met_ex["datetime"]))
                      .reindex(idx_h).interpolate().bfill().ffill().values)
            _pz_ex, _ = carica_prezzi_elettrici()
            _pz_ex = (pd.Series(_pz_ex, index=HOURS_2024).reindex(idx_h).ffill().bfill().values)
            # forma oraria dei prezzi zonali, livello medio = prezzo effettivo del dimensionamento
            _pz_ex = _pz_ex * (prezzo_el_eff / max(float(np.mean(_pz_ex)), 1e-9))

            _df_m_ex, _df_a_ex, _info_ex = prezzo_scarto_exergetico(
                off_all, idx_h, sim, _T0_ex, _pz_ex, float(T_mandata_ideale), float(T_int),
                _psv_ex, float(_spread_ex), float(_eta_ex),
                float(_sconto_ex), float(_fisso_ex), backup_tipo == "HP bassa T",
                float(_ets2_ex), float(_cald_ex), formula_scarto_da_sessione())

            _costo_scarto_ex = 0.0
            # prezzo di vendita coerente con il target: media pesata sulla domanda
            # oraria delle utenze del (PSV mensile + spread) / rendimento x (1 - sconto)
            _ut_h_all = dom_arr / _fatt_lordo
            _C_gas_h_all = ((_psv_ex[np.asarray(idx_h.month.values) - 1] + float(_spread_ex)
                             + float(_ets2_ex) * EF_GAS_T_MWH_PCS) / float(_eta_ex)
                            + float(_cald_ex))
            _den_ut = max(float(_ut_h_all.sum()), 1e-9)
            _costo_gas_mwh = float((_ut_h_all * _C_gas_h_all).sum()) / _den_ut
            _prezzo_target_mwh = _costo_gas_mwh * (1.0 - float(_sconto_ex))
            if _df_a_ex.empty:
                st.info("Nessun calore di scarto ceduto con la configurazione attuale.")
            else:
                _ut_h = dom_arr / _fatt_lordo
                _costo_gas_ut = float((_ut_h * _info_ex["C_gas_h"]).sum())
                _target_ut = float((_ut_h * _info_ex["P_target_h"]).sum())
                _costo_scarto_ex = float(_df_a_ex["costo_eur"].sum())
                _costo_var_tlr = _costo_scarto_ex + _info_ex["costo_el"] + E_bk * opex_bk_mwh
                _k1, _k2, _k3, _k4 = st.columns(4)
                _k1.metric("Costo a gas per le utenze", f"{_costo_gas_ut:,.0f} \u20ac/a".replace(",", "."),
                           help=f"{_costo_gas_ut / max(_ut_h.sum(), 1e-9):.1f} \u20ac/MWh medi")
                _k2.metric(f"Target (\u2212{_sconto_ex * 100:.0f} %)",
                           f"{_target_ut:,.0f} \u20ac/a".replace(",", "."))
                _k3.metric("Calore di scarto (scala exergetica)",
                           f"{_costo_scarto_ex:,.0f} \u20ac/a".replace(",", "."),
                           help="Va nei flussi di cassa dell'Analisi economica se in "
                                "Offerta e' scelto il metodo a scala exergetica.")
                _k4.metric("Costo variabile TLR", f"{_costo_var_tlr:,.0f} \u20ac/a".replace(",", "."),
                           help="Scarto + elettricita' delle pompe + combustibile di backup. "
                                "Non comprende CAPEX, rete e O&M.")

                _tab_ex = _df_a_ex.rename(columns={
                    "azienda": "Azienda", "MWh_ceduti": "MWh ceduti", "w_medio": "Peso w medio",
                    "eur_mwh": "\u20ac/MWh ceduto", "costo_eur": "\u20ac/a",
                    "mesi_tetto": "Mesi col tetto"})
                st.dataframe(
                    _tab_ex[["Azienda", "MWh ceduti", "Peso w medio", "\u20ac/MWh ceduto",
                             "\u20ac/a", "Mesi col tetto"]].round(
                        {"MWh ceduti": 0, "Peso w medio": 2, "\u20ac/MWh ceduto": 1, "\u20ac/a": 0}),
                    hide_index=True, width="stretch")

                _fig_ex = go.Figure()
                _pt_m = _df_m_ex.groupby("mese")["P_target"].first()
                _fig_ex.add_trace(go.Scatter(
                    x=[MONTH_NAMES[m - 1] for m in _pt_m.index], y=_pt_m.values,
                    name="Target calore utente", line=dict(color="#888780", dash="dash")))
                for _az, _g in _df_m_ex.groupby("azienda"):
                    _g = _g[_g["MWh_ceduti"] > 1e-6]
                    _fig_ex.add_trace(go.Scatter(
                        x=[MONTH_NAMES[m - 1] for m in _g["mese"]], y=_g["eur_mwh"],
                        name=_az, mode="lines+markers"))
                _fig_ex.update_layout(height=340, margin=dict(l=10, r=10, t=30, b=10),
                                      yaxis_title="\u20ac/MWh",
                                      title="Prezzo mensile del calore ceduto")
                st.plotly_chart(_fig_ex, width="stretch")
                if int(_df_a_ex["mesi_tetto"].sum()) > 0:
                    st.warning("In alcuni mesi il valore della scala supera il margine dopo "
                               "l'elettricita' delle pompe: il prezzo e' stato ridotto al "
                               "margine (colonna *Mesi col tetto*).")

    # il costo che entra nello snapshot (e quindi nell'Analisi economica)
    # segue il metodo scelto in Offerta
    _metodo_scarto_dim = st.session_state.get("off_metodo_prezzo",
                                              "Scala exergetica (riferimento gas)")
    if _metodo_scarto_dim.startswith(("Scala exergetica", "Formula")):
        costo_calore_acq = _costo_scarto_ex

    # ---------------------------------------------------------------------
    # CALORE DI SCARTO NEI RISULTATI: PREZZO PAGATO E CONVENIENZA PER AZIENDA
    # Per ogni azienda si confronta lo scenario attuale con lo stesso scenario
    # senza quell'azienda (stesse macchine e accumuli, dispatch rifatto): la
    # differenza di costo annuo dice se il suo calore, al prezzo pagato, fa
    # risparmiare o no. Le simulazioni sono le stesse dell'Analisi economica e
    # vengono condivise con la sua cache (stessa firma).
    # ---------------------------------------------------------------------
    _metodo_fisso = not _metodo_scarto_dim.startswith(("Scala exergetica", "Formula"))
    _ss_r = st.session_state
    _lung_add_r = _ss_r.get("_off_lunghezze_adduzione", {}) or {}
    _schema_add_r = _ss_r.get("eco_schema_add", "dorsale")
    _costo_m_add_r = float(_ss_r.get("eco_costo_add", 700))
    _costo_he_r = float(_ss_r.get("eco_costo_he", 60))
    _wacc_r = float(_ss_r.get("eco_wacc", 4.0)) / 100.0
    _anni_r = int(_ss_r.get("eco_anni", 25))
    _contr_r = float(_ss_r.get("eco_contributo", 40))
    _om_rete_r = float(_ss_r.get("eco_om_rete", 0.75))
    _om_r = float(_ss_r.get("eco_om", 2.0))
    _fl_sel_r = _ss_r.get("_off_flussi", []) or []
    _q_r = flussi[flussi["id_flusso"].isin(_fl_sel_r)]
    _cq_r = pd.to_numeric(_q_r.get("costo_allacciamento_eur"), errors="coerce")
    _he_per_az_r = (_q_r.assign(_he=_cq_r.fillna(
        pd.to_numeric(_q_r["P_kW"], errors="coerce").fillna(0) * _costo_he_r))
        .groupby("azienda")["_he"].sum().to_dict()) if not _q_r.empty else {}
    _firma_c = (tuple(sorted(map(str, _fl_sel_r))), float(T_mandata_ideale),
                float(T_ritorno_ideale), float(T_int), float(eta_hp),
                float(V_hot), float(V_int), float(V_low), float(P_alta),
                float(P_bassa), str(backup_tipo), float(P_bk), str(backup_cop),
                float(antigelo), float(perd), bool(strat_on), bool(solare_on),
                round(float(np.sum(solar_low)) if solare_on else 0.0, 3),
                str(tipo_sorgente), str(resa_sorgente), str(costo_sorgente),
                str(_psv_sel), float(_spread_ex), float(_eta_ex), float(_sconto_ex),
                float(_fisso_ex), float(prezzo_el_eff), float(_ets2_ex), float(_cald_ex),
                str(formula_scarto_da_sessione()),
                round(float(np.sum(dom_arr)), 3), len(dom_arr))
    _combs_r = []
    if not off_all.empty and off_all["azienda"].nunique() <= 5:
        _cache_r = _ss_r.get("_eco_combinazioni")
        try:
            if _cache_r and _cache_r[0] == _firma_c:
                _combs_r = _cache_r[1]
            else:
                with st.spinner("Valuto il contributo di ciascuna azienda…"):
                    _combs_r = valuta_combinazioni_aziende(
                        off_all, idx_h, dom_arr, soil_temp_arr, float(T_mandata_ideale),
                        float(T_ritorno_ideale), float(T_int), eta_hp, V_hot, V_int, V_low,
                        P_alta, P_bassa, backup_tipo, P_bk, backup_cop, float(antigelo),
                        perd, strat_on, (solar_low if solare_on else None),
                        tipo_sorgente, resa_sorgente, costo_sorgente,
                        _T0_ex, _pz_ex, _psv_ex, float(_spread_ex), float(_eta_ex),
                        float(_sconto_ex), float(_fisso_ex), float(_ets2_ex), float(_cald_ex),
                        formula_scarto_da_sessione())
                _ss_r["_eco_combinazioni"] = (_firma_c, _combs_r)
        except Exception:
            _combs_r = []

    def _pagato_combo(c):
        """Calore di scarto pagato in una combinazione, col metodo scelto in Offerta."""
        if _metodo_fisso:
            return sum(float(m) * float(_prezzi_scarto.get(a, 0.0))
                       for a, m in (c.get("MWh_ceduti") or {}).items())
        return float(c["costo_scarto"])

    def _voci_combo(c):
        _az = list(c["aziende"])
        _cap_all = (sum(_he_per_az_r.get(a, 0.0) for a in _az)
                    + lunghezza_adduzioni(_az, _lung_add_r, _schema_add_r) * _costo_m_add_r)
        _f_n = (1.0 - _contr_r / 100.0) * crf(_wacc_r, _anni_r)
        return {
            "energia": (c["costo_el"] + c["E_backup"] * opex_bk_mwh
                        + c["capex_sorgente"] * (_f_n + _om_r / 100.0)),
            "allaccio": _cap_all * (_f_n + _om_rete_r / 100.0),
            "cap_allaccio": _cap_all,
            "pagato": _pagato_combo(c),
            "ore_nc": int(c["ore_non_cop"]),
        }

    _righe_conv = []
    _set_att = frozenset(off_all["azienda"].unique()) if not off_all.empty else frozenset()
    _c_att = next((c for c in _combs_r if frozenset(c["aziende"]) == _set_att), None)
    if _c_att is not None:
        _v_att = _voci_combo(_c_att)
        for _a in sorted(_set_att):
            _c_senza = next((c for c in _combs_r
                             if frozenset(c["aziende"]) == _set_att - {_a}), None)
            if _c_senza is None:
                continue
            _v_s = _voci_combo(_c_senza)
            _mwh_a = float((_c_att.get("MWh_ceduti") or {}).get(_a, 0.0))
            _pag_a = (_mwh_a * float(_prezzi_scarto.get(_a, 0.0)) if _metodo_fisso
                      else float(_df_a_ex.loc[_df_a_ex["azienda"] == _a, "costo_eur"].sum())
                      if not _df_a_ex.empty else 0.0)
            _risp = _v_s["energia"] - _v_att["energia"]          # cosa fa risparmiare
            _all_a = _v_att["allaccio"] - _v_s["allaccio"]        # quanto costa allacciarla
            _dpag = _v_att["pagato"] - _v_s["pagato"]             # quanto si paga in piu'
            _saldo = _risp - _all_a - _dpag
            _p_max = ((_risp - _all_a - (_dpag - _pag_a)) / _mwh_a) if _mwh_a > 1e-6 else None
            _ore_in_piu = _v_s["ore_nc"] - _v_att["ore_nc"]
            if _ore_in_piu > 0:
                _verd = f"indispensabile: senza, {_ore_in_piu} ore scoperte"
            elif _saldo >= 0:
                _verd = "conviene"
            else:
                _verd = "non conviene"
            _righe_conv.append({
                "Azienda": _a,
                "Calore ceduto (MWh/a)": round(_mwh_a),
                "Prezzo pagato (€/MWh)": round(_pag_a / _mwh_a, 1) if _mwh_a > 1e-6 else None,
                "Pagato (k€/a)": round(_pag_a / 1000, 1),
                "Allacciamento (k€)": round((_v_att["cap_allaccio"] - _v_s["cap_allaccio"]) / 1000),
                "Allacciamento annuo (k€/a)": round(_all_a / 1000, 1),
                "Risparmio su elettricità e sorgente (k€/a)": round(_risp / 1000, 1),
                "Saldo per il TLR (k€/a)": round(_saldo / 1000, 1),
                "Prezzo massimo sostenibile (€/MWh)": (round(_p_max, 1)
                                                       if _p_max is not None else None),
                "Esito": _verd})

    with step4:
        st.divider()
        st.markdown("#### 🏭 Calore di scarto: prezzo pagato alle aziende e convenienza")
        _met_lab = ("prezzo fisso per azienda (Offerta)" if _metodo_fisso
                    else _metodo_scarto_dim)
        st.caption(f"Metodo di prezzo: **{_met_lab}**. Per ogni azienda lo scenario viene "
                   f"rifatto senza di lei, con le stesse macchine e gli stessi accumuli: la "
                   f"differenza dice quanto il suo calore fa risparmiare su elettricità delle "
                   f"pompe, combustibile e sorgente fredda, e lo si confronta con quanto costa "
                   f"allacciarla e con quanto le si paga il calore.")
        if not _righe_conv:
            st.info("Nessuna azienda allacciata, oppure analisi non disponibile per questa "
                    "configurazione.")
        else:
            _df_conv = pd.DataFrame(_righe_conv)
            st.dataframe(_df_conv, width="stretch", hide_index=True)
            _non = [r["Azienda"] for r in _righe_conv if r["Esito"] == "non conviene"]
            _frasi = []
            for r in _righe_conv:
                _pm = r["Prezzo massimo sostenibile (€/MWh)"]
                _pp = r["Prezzo pagato (€/MWh)"]
                if _pm is None or _pp is None:
                    continue
                if _pm <= 0:
                    _frasi.append(f"**{r['Azienda']}**: anche gratis il suo calore non "
                                  f"ripaga l'allacciamento ({_pm:.0f} €/MWh)")
                else:
                    _frasi.append(f"**{r['Azienda']}**: si può pagare fino a "
                                  f"**{_pm:.0f} €/MWh** (oggi {_pp:.0f})")
            if _frasi:
                st.markdown("Prezzo massimo che il TLR può pagare a ciascuna azienda "
                            "restando in pari: " + " · ".join(_frasi) + ".")
            if _non:
                st.warning("Al prezzo attuale non conviene allacciare: **"
                           + ", ".join(_non) + "**. Deseleziona i suoi flussi in Offerta, "
                           "rinegozia il prezzo sotto il massimo sostenibile o riduci il "
                           "costo dell'allacciamento.")
            else:
                st.success("Tutte le aziende allacciate convengono al prezzo attuale.")
            st.caption(
                "Prezzo massimo sostenibile = (risparmio − costo annuo dell'allacciamento) / "
                "MWh ceduti: è il prezzo a cui il saldo si azzera. Il costo dell'allacciamento "
                "comprende scambiatori, opere e quota di adduzione (schema, €/m e "
                "contributo dall'Analisi economica), annualizzato e con la manutenzione. "
                "Togliere un'azienda cambia anche il prezzo delle altre (la scala exergetica "
                "ripartisce il valore fra chi cede), e il saldo ne tiene conto.")

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
        "accumulo_stratificato": "sì" if strat_on else "no",
        "autoproduzione_el": ("sì" if considera_el else "no"),
        "prezzo_el_effettivo": round(prezzo_el_eff),
        "capex_autoproduzione": round(capex_autoproduzione),
        "kwp_autoproduzione": round(kwp_autoprod),
        "batteria_autoproduzione_mwh": round(batt_autoprod, 1),
        "ibridi_autoproduzione_m2": round(ibr_autoprod),
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
        "tipo_solare": (tipo_solare if solare_on else "assente"),
        "n_pannelli_pvt": int(n_pvt),
        "pvt_elettrico_mwh": round(pvt_el_mwh, 1),
        "pvt_ricavo_el": round(ricavo_pvt_el),
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
        "dn_dorsale": int(_rete_info.get("dn_dorsale", 0)),
        "P_dorsale_kw": round(float(_rete_info.get("P_dorsale_kw", 0.0))),
        "n_privati_agganciati": int(_rete_info.get("n_privati_agganciati", 0)),
        "densita_lineare": round(_dens_lin, 2),
        "opex_annuo": round(opex),
        "costo_annuo": round(costo_annuo),
        "lcoh": round(float(lcoh), 2) if not np.isnan(lcoh) else None,
        "prezzo_el": int(prezzo_el),
        "costo_gas_utente_mwh": round(_costo_gas_mwh, 2),
        "prezzo_target_mwh": round(_prezzo_target_mwh, 2),
        "sconto_target_pct": round(float(_sconto_ex) * 100),
        "opex_backup_mwh": round(float(opex_bk_mwh), 1),
    }

    # --- salvataggio scenario (P9: rimovibili singolarmente) ---
    st.divider()
    if autoprod_da_rifare:
        st.warning("⚡ L'autoproduzione elettrica è stata ottimizzata per un'altra "
                   "configurazione (consumo delle pompe diverso da quello attuale) o non "
                   "è ancora stata calcolata. Rilancia **Trova la configurazione ottima** "
                   "nel passo *4 · Carico elettrico* prima di salvare lo scenario.")
    sc1, sc2 = st.columns([3, 1])
    _nome_def = f"{backup_tipo} · {T_mandata_ideale}/{T_ritorno_ideale}°C"
    nome_scen = sc1.text_input("Nome dello scenario da salvare", value=_nome_def, key="dim_nome_scen")
    if sc2.button("\U0001F4BE Salva scenario", width="stretch", key="dim_btn_salva"):
        if nome_scen.strip():
            from datetime import datetime as _dt
            _snap_s = dict(st.session_state["_dim_snapshot"])
            # fotografia completa delle ipotesi, per la scheda PDF di confronto
            _snap_s["ipotesi"] = raccogli_ipotesi()
            _snap_s["salvato_il"] = _dt.now().strftime("%d/%m/%Y %H:%M")
            st.session_state["_scenari"][nome_scen.strip()] = _snap_s
            _ok_f = salva_scenari_file(st.session_state["_scenari"])
            st.success(f"Scenario **{nome_scen.strip()}** salvato "
                       f"({len(st.session_state['_scenari'])} in memoria)"
                       + ("." if _ok_f else ": non è stato possibile scriverlo su disco, "
                          "esportalo dalla scheda Confronto scenari."))
        else:
            st.warning("Dai un nome allo scenario prima di salvarlo.")


# =============================================================================
# TAB 4 - COPERTURA DEL CARICO ELETTRICO
# Volutamente separata dal dimensionamento termico: le scelte elettriche non
# devono condizionare il dispatch del calore, che risponde a vincoli propri.
# =============================================================================
with step_el:
    _snap_el = st.session_state.get("_dim_snapshot")
    _attiva_el = bool(st.session_state.get("_dim_considera_el", False))
    if not _snap_el:
        st.info("Completa prima i passi 1-3: da lì arrivano i consumi elettrici "
                "delle pompe di calore.")
    elif not _attiva_el:
        pass
    else:
        _serie_el = st.session_state.get("_dim_serie_elettriche", {}) or {}
        _cons_h = np.asarray(_serie_el.get("consumo_hp", []), dtype=float)
        if _cons_h.size == 0:
            _cons_h = np.full(len(HOURS_2024),
                              float(_snap_el.get("E_elettrica", 0)) / len(HOURS_2024))
        _prezzi_h, _fonte_pr = carica_prezzi_elettrici()
        _mt_el = serie_meteo_annua(pvgis)
        _cop_rif = float(_snap_el.get("cop_alta", 4.5)) or 4.5

        # =================================================================
        # 1. SITUAZIONE DI PARTENZA
        # =================================================================
        st.markdown("#### Punto di partenza")
        _p1, _p2, _p3 = st.columns(3)
        _p1.metric("Consumo delle pompe di calore",
                   f"{_cons_h.sum():,.0f} MWh/a".replace(",", "."),
                   help=f"dal dispatch termico · {_snap_el.get('tecnologie', '')}")
        _p2.metric("Oggi coperto da", "rete elettrica",
                   help="Senza impianti di generazione propri tutto il fabbisogno "
                        "viene acquistato.")
        _p3.metric("Prezzi zonali", f"{_prezzi_h.mean():.0f} €/MWh medi",
                   help=f"da {_fonte_pr} · ore 10-16 "
                        f"{_prezzi_h[HOURS_2024.hour.isin(range(10, 17))].mean():.0f} · "
                        f"ore 18-21 "
                        f"{_prezzi_h[HOURS_2024.hour.isin(range(18, 22))].mean():.0f}")

        # =================================================================
        # 2. PARAMETRI DEGLI IMPIANTI
        # =================================================================
        st.divider()
        st.markdown("#### Impianti considerati")
        st.caption("Si impostano qui i costi e le caratteristiche; le taglie le trova "
                   "l'ottimizzazione più sotto.")

        _i1, _i2, _i3 = st.columns(3)
        with _i1:
            st.markdown("**☀️ Solare ibrido**")
            _usa_ibr = st.checkbox("Considera moduli ibridi", value=False,
                                   key="el_usa_ibrido",
                                   help="I moduli ibridi producono elettricità e calore "
                                        "con la stessa superficie. Il calore alimenta "
                                        "l'anello basso della rete, quindi entra anche "
                                        "nel bilancio termico.")
            if _usa_ibr:
                _mod_ibr = st.selectbox("Modello", list(CATALOGO_PVT.keys()), index=0,
                                        key="el_modello_ibr")
                _mp_el = CATALOGO_PVT[_mod_ibr]
                _tf_ibr = st.slider("Temperatura di esercizio (°C)", 25, 80, 40, step=5,
                                    key="el_tf_ibrido",
                                    help="Il calore prodotto va all'anello basso, quindi "
                                         "conviene una temperatura bassa: la resa termica "
                                         "sale e quella elettrica non ne risente quasi.")
                _costo_ibr = st.slider("Costo per modulo (€)", 200, 2000,
                                       900 if "Abora" in _mp_el["nome"] else 500,
                                       step=25, key="el_costo_ibrido")
                if _tf_ibr > _mp_el.get("t_max_circuito_c", 100):
                    st.error(f"Oltre il limite di circuito del modulo "
                             f"({_mp_el['t_max_circuito_c']:.0f} °C).")
            else:
                _mod_ibr = list(CATALOGO_PVT.keys())[0]
                _mp_el = CATALOGO_PVT[_mod_ibr]
                _tf_ibr, _costo_ibr = 40, 900

        with _i2:
            st.markdown("**\U0001F50B Fotovoltaico e accumulo**")
            _usa_pv = st.checkbox("Considera fotovoltaico", value=True, key="el_usa_pv")
            _costo_kwp = st.slider("Costo del fotovoltaico (€/kWp)", 400, 2000, 850,
                                   step=50, key="el_costo_kwp",
                                   help="Chiavi in mano. Impianti sopra i 500 kWp su "
                                        "copertura esistente stanno di norma fra 700 "
                                        "e 1.100 €/kWp.")
            _usa_batt = st.checkbox("Considera l'accumulo elettrochimico", value=True,
                                    key="el_usa_batt")
            _costo_kwh_b = st.slider("Costo della batteria (€/kWh)", 100, 800, 300,
                                     step=25, key="el_costo_batt")
            _bos_pv = st.slider("Perdite di sistema (%)", 5, 25, 14, step=1,
                                key="el_bos_pv",
                                help="Inverter, cablaggi, sporcamento, temperatura di "
                                     "cella. Un impianto ben progettato sta fra il 12 "
                                     "e il 15 %.")

        with _i3:
            st.markdown("**\U0001F4B6 Valorizzazione**")
            _oneri = st.slider("Oneri e imposte sul prelievo (€/MWh)", 0, 200, 110,
                               step=5, key="el_oneri",
                               help="Si sommano al prezzo zonale sull'energia "
                                    "acquistata e ne determinano la forma oraria. Il "
                                    "livello medio del prezzo d'acquisto è quello "
                                    "impostato nel Dimensionamento, così le due schede "
                                    "usano la stessa tariffa.")
            # prezzo d'acquisto: forma oraria (zonale + oneri), livello medio pari al
            # prezzo dell'elettricita' del Dimensionamento (oneri inclusi)
            _forma_acq = _prezzi_h + _oneri
            _prezzo_acq_h = _forma_acq * (float(prezzo_el) / max(float(np.mean(_forma_acq)), 1e-9))
            st.caption(f"Prezzo d'acquisto medio **{float(np.mean(_prezzo_acq_h)):.0f} €/MWh** "
                       f"(dal Dimensionamento).")
            _val_imm = st.slider("Valore dell'energia immessa (% del prezzo zonale)",
                                 0, 100, 0, step=5, key="el_val_imm",
                                 help="A zero l'impianto è valutato come puro "
                                      "approvvigionamento: l'eccedenza non vale nulla "
                                      "e l'ottimizzazione trova una taglia finita. "
                                      "Alzandolo si tratta l'impianto anche come "
                                      "vendita, e la taglia ottima cresce.")
            _val_cal_el = st.slider("Valore del calore da moduli ibridi (€/MWh)",
                                    0, 200,
                                    int(round(float(st.session_state.get(
                                        "dim_prezzo_el", 180)) / _cop_rif)), step=5,
                                    key="el_val_calore",
                                    help="Costo che si evita producendo quel calore con "
                                         "le pompe di calore invece che con i moduli. "
                                         "Il valore proposto è il prezzo dell'elettricità "
                                         f"diviso il COP di sistema ({_cop_rif:.1f}).")
            _anni_el = st.slider("Vita utile per l'annualizzazione (anni)", 10, 30, 20,
                                 key="el_anni")

        if _val_imm == 0:
            st.caption("Con l'eccedenza a valore nullo l'ottimizzazione cerca la "
                       "configurazione che **minimizza il costo di approvvigionamento**: "
                       "oltre una certa taglia si produrrebbe solo surplus inutile, "
                       "quindi l'ottimo esiste ed è interno. È la lettura più prudente.")
        else:
            st.caption(f"Valorizzando l'eccedenza al {_val_imm} % del prezzo zonale "
                       f"l'impianto è trattato anche come vendita: la taglia ottima "
                       f"cresce, e può arrivare al limite della ricerca. In quel caso "
                       f"il vincolo non è più energetico ma di superficie o di "
                       f"potenza di connessione, da verificare a parte.")

        # --- serie unitarie: si calcolano una volta e si scalano, perche' la
        #     resa e' proporzionale alla taglia a parita' di temperatura ---
        _pv_unit = (_mt_el["G_totale"].values / 1000.0
                    * (1.0 - _bos_pv / 100.0) / 1000.0)        # MWh/h per kWp
        _resa_kwp = float(_pv_unit.sum()) * 1000.0
        _AREA_RIF = 1000.0
        _n_rif = max(int(_AREA_RIF / _mp_el["area_lorda_m2"]), 1)
        _s_rif = genera_offerta_pvt(pvgis, _n_rif, float(_tf_ibr), _mod_ibr).set_index("datetime")
        _ibr_el_u = (_s_rif["MWh_el"].reindex(HOURS_2024, fill_value=0).values
                     / _AREA_RIF)                               # MWh/h per m2
        _ibr_th_u = (_s_rif["MWh_term"].reindex(HOURS_2024, fill_value=0).values
                     / _AREA_RIF)
        _costo_ibr_m2 = _costo_ibr / _mp_el["area_lorda_m2"]

        # =================================================================
        # 3. OTTIMIZZAZIONE DI SISTEMA
        # =================================================================
        st.divider()
        st.markdown("#### \U0001F3AF Ottimizzazione di sistema")
        st.caption("Cerca la combinazione di moduli ibridi, fotovoltaico e accumulo che "
                   "rende minimo il costo complessivo di approvvigionamento elettrico: "
                   "investimento annualizzato più energia acquistata, al netto di quanto "
                   "si ricava dall'eccedenza e del calore che gli ibridi risparmiano "
                   "alle pompe.")

        _crf_el = crf(0.04, int(_anni_el))
        _costo_base = float((_cons_h * _prezzo_acq_h).sum())

        def _valuta_sistema(area_ibr, kwp, batt):
            """Costo annuo di approvvigionamento per una data configurazione.

            Comprende l'investimento annualizzato, l'energia acquistata, il
            ricavo dall'eccedenza e il calore che i moduli ibridi sottraggono
            alle pompe di calore: senza quest'ultimo l'ibrido risulterebbe
            sempre perdente rispetto al fotovoltaico, perche' rende meno
            elettricita' a parita' di superficie.
            """
            prod = _ibr_el_u * area_ibr + _pv_unit * kwp
            r = dispatch_elettrico(prod, _cons_h, batteria_mwh=batt,
                                   p_batt_mw=batt * 0.5, eff_batt=0.90)
            acquisto = float((r["prelevato"] * _prezzo_acq_h).sum())
            ricavo = float((r["immesso"] * _prezzi_h).sum()) * (_val_imm / 100.0)
            calore = float((_ibr_th_u * area_ibr).sum())
            capex = (area_ibr * _costo_ibr_m2 + kwp * _costo_kwp
                     + batt * 1000.0 * _costo_kwh_b)
            costo = capex * _crf_el + acquisto - ricavo - calore * _val_cal_el
            return {"area_ibr": area_ibr, "kwp": kwp, "batt": batt, "res": r,
                    "capex": capex, "acquisto": acquisto, "ricavo": ricavo,
                    "calore_mwh": calore, "costo": costo,
                    "risparmio": _costo_base - costo}

        _col_o1, _col_o2 = st.columns([1, 2])
        with _col_o1:
            _lim_kwp = st.number_input("Limite superiore della ricerca (kWp)",
                                       min_value=100, max_value=50000, value=3000,
                                       step=100, key="el_lim_kwp",
                                       help="Serve solo a delimitare la ricerca. Se "
                                            "l'ottimo lo tocca significa che con "
                                            "questi prezzi converrebbe un impianto "
                                            "ancora più grande.")
            _lancia = st.button("\U0001F3AF Trova la configurazione ottima",
                                key="el_btn_opt", width="stretch", type="primary")
        with _col_o2:
            st.caption(f"Senza alcun impianto l'energia costa "
                       f"**{_costo_base / 1000:,.0f} k€/a** "
                       f"({_costo_base / max(_cons_h.sum(), 1e-9):.0f} €/MWh medi). "
                       f"È il riferimento da battere.".replace(",", "."))
            st.caption(f"Resa attesa del fotovoltaico **{_resa_kwp:.0f} kWh/kWp**; "
                       f"dei moduli ibridi "
                       f"**{_ibr_el_u.sum() * 1000:.0f} kWh/m² elettrici** e "
                       f"**{_ibr_th_u.sum() * 1000:.0f} kWh/m² termici** a {_tf_ibr} °C.")

        # Firma di cio' da cui dipende l'ottimo elettrico: consumi orari delle
        # pompe e impostazioni di questo passo. Se cambia (nuove taglie termiche,
        # nuovi costi del fotovoltaico...) l'ottimizzazione si rifa' da sola, cosi'
        # il risultato non resta mai riferito a un dimensionamento precedente.
        _firma_prove = (round(float(_cons_h.sum()), 1), int(len(_cons_h)),
                        tuple(sorted((str(k), str(st.session_state.get(k)))
                                     for k in st.session_state.keys()
                                     if str(k).startswith("el_")
                                     and not str(k).startswith("el_btn"))))
        _da_rifare = (st.session_state.get("_el_prove") is not None
                      and st.session_state.get("_el_prove_firma") != _firma_prove)
        if _lancia or _da_rifare or st.session_state.get("_el_prove") is None:
            with st.spinner("Esploro le combinazioni..."):
                _g_ibr = [0.0]
                if _usa_ibr:
                    _g_ibr = [0.0, 500.0, 1000.0, 2000.0, 4000.0, 8000.0]
                _g_kwp = [0.0]
                if _usa_pv:
                    _g_kwp = [0.0] + list(np.unique(np.round(
                        np.geomspace(50, float(_lim_kwp), 12) / 10) * 10))
                _g_batt = [0.0]
                if _usa_batt:
                    _g_batt = [0.0, 0.5, 1.0, 2.0, 4.0, 8.0, 15.0]
                _prove = [_valuta_sistema(a, k, b)
                          for a in _g_ibr for k in _g_kwp for b in _g_batt]
            st.session_state["_el_prove"] = _prove
            st.session_state["_el_prove_firma"] = _firma_prove

        _prove = st.session_state.get("_el_prove")
        if not _prove:
            st.info("Premi **Trova la configurazione ottima** per esplorare le "
                    "combinazioni di taglie.")
        else:
            _best = min(_prove, key=lambda r: r["costo"])
            _senza = _valuta_sistema(0.0, 0.0, 0.0)

            st.success(
                f"Configurazione a costo minimo: "
                + (f"**{_best['area_ibr']:,.0f} m²** di moduli ibridi · ".replace(",", ".")
                   if _best["area_ibr"] else "")
                + (f"**{_best['kwp']:,.0f} kWp** di fotovoltaico".replace(",", ".")
                   if _best["kwp"] else "nessun fotovoltaico")
                + (f" · **{_best['batt']:.1f} MWh** di accumulo"
                   if _best["batt"] else " · senza accumulo"))

            _r1, _r2, _r3, _r4 = st.columns(4)
            _r1.metric("Costo dell'energia",
                       f"{_best['costo'] / 1000:,.0f} k€/a".replace(",", "."),
                       delta=f"{(_best['costo'] - _costo_base) / 1000:+,.0f} k€/a"
                             .replace(",", "."),
                       delta_color="inverse",
                       help="Investimento annualizzato più acquisti, al netto di "
                            "eccedenza e calore risparmiato.")
            _r2.metric("Investimento", f"{_best['capex'] / 1e6:.2f} M€")
            _r3.metric("Copertura del consumo",
                       f"{_best['res']['copertura_pct']:.0f} %")
            _r4.metric("Autoconsumo della produzione",
                       f"{_best['res']['autoconsumo_pct']:.0f} %",
                       help="Quota della produzione usata sul posto. Con l'eccedenza "
                            "a valore nullo l'ottimizzazione tende a tenerla alta.")

            if _best["kwp"] >= float(_lim_kwp) * 0.95:
                st.warning(
                    f"L'ottimo tocca il limite di ricerca ({_lim_kwp:,.0f} kWp): con "
                    f"questi prezzi converrebbe un impianto ancora più grande. Alza il "
                    f"limite, oppure verifica quale sia il vero vincolo — superficie "
                    f"disponibile o potenza di connessione in immissione."
                    .replace(",", "."))
            if _best["area_ibr"] > 0:
                st.caption(
                    f"I moduli ibridi contribuiscono con "
                    f"**{(_ibr_el_u * _best['area_ibr']).sum():,.0f} MWh/a elettrici** e "
                    f"**{_best['calore_mwh']:,.0f} MWh/a termici**, questi ultimi "
                    f"valorizzati {_val_cal_el} €/MWh come calore che le pompe non "
                    f"devono più produrre. Senza contare il calore l'ibrido non "
                    f"risulterebbe mai conveniente rispetto al fotovoltaico."
                    .replace(",", "."))

            # --- confronto delle configurazioni esplorate ---
            _df_p = pd.DataFrame([{
                "Ibridi (m²)": r["area_ibr"], "FV (kWp)": r["kwp"],
                "Accumulo (MWh)": r["batt"],
                "Copertura (%)": round(r["res"]["copertura_pct"], 1),
                "Autoconsumo (%)": round(r["res"]["autoconsumo_pct"], 1),
                "Investimento (k€)": round(r["capex"] / 1000),
                "Costo energia (k€/a)": round(r["costo"] / 1000),
                "Risparmio (k€/a)": round(r["risparmio"] / 1000),
            } for r in _prove]).sort_values("Costo energia (k€/a)")

            _fig_o = go.Figure()
            for _b in sorted({r["batt"] for r in _prove}):
                _sel = sorted([r for r in _prove if r["batt"] == _b],
                              key=lambda r: r["res"]["copertura_pct"])
                _fig_o.add_trace(go.Scatter(
                    x=[r["res"]["copertura_pct"] for r in _sel],
                    y=[r["costo"] / 1000 for r in _sel], mode="lines+markers",
                    name=(f"{_b:.1f} MWh" if _b else "senza accumulo"),
                    hovertemplate="copertura %{x:.0f}%%<br>%{y:.0f} k€/a<extra></extra>"))
            _fig_o.add_hline(y=_costo_base / 1000, line_dash="dot", line_color="#888",
                             annotation_text="solo rete", annotation_position="right")
            _fig_o.add_trace(go.Scatter(
                x=[_best["res"]["copertura_pct"]], y=[_best["costo"] / 1000],
                mode="markers", name="ottimo",
                marker=dict(size=16, color=COLOR_OFFERTA, symbol="star")))
            _fig_o.update_layout(height=400, xaxis_title="Copertura del consumo (%)",
                                 yaxis_title="Costo dell'energia (k€/anno)",
                                 legend=dict(orientation="h", yanchor="bottom", y=1.02),
                                 margin=dict(t=30, b=10))
            st.plotly_chart(_fig_o, width="stretch")
            st.caption("Ogni punto è una configurazione. La linea tratteggiata è il "
                       "costo senza alcun impianto: tutto ciò che sta sotto conviene. "
                       "La curva ha un minimo perché oltre una certa taglia si produce "
                       "solo eccedenza, che qui non è valorizzata.")

            with st.expander("Tutte le configurazioni esplorate"):
                st.dataframe(_df_p, width="stretch", hide_index=True)
                st.download_button("⬇️ Scarica (CSV)",
                                   data=_df_p.to_csv(index=False).encode("utf-8"),
                                   file_name="maniago_ottimizzazione_elettrica.csv",
                                   mime="text/csv", key="el_dl_opt")

            # =============================================================
            # 4. RIALLINEAMENTO DEL BILANCIO TERMICO
            # =============================================================
            _th_ott = float((_ibr_th_u * _best["area_ibr"]).sum())
            _th_attuale = float(np.asarray(
                st.session_state.get("_dim_serie_el_solare_term",
                                     np.zeros(len(HOURS_2024)))).sum())
            if _best["area_ibr"] > 0:
                st.divider()
                st.markdown("#### \U0001F504 Riallineamento del bilancio termico")
                _scarto_th = abs(_th_ott - _th_attuale)
                if _scarto_th > max(_th_ott * 0.02, 1.0):
                    st.warning(
                        f"I moduli ibridi trovati qui produrrebbero "
                        f"**{_th_ott:,.0f} MWh/a** di calore, mentre il dimensionamento "
                        f"termico ne sta considerando {_th_attuale:,.0f}. I due conti "
                        f"sono disallineati: le pompe di calore risultano più grandi "
                        f"del necessario e il costo del calore è sovrastimato."
                        .replace(",", "."))
                    if st.button("Trasferisci al dimensionamento termico",
                                 key="el_btn_allinea", type="primary"):
                        st.session_state["_el_ibrido_da_elettrico"] = {
                            "attivo": True, "area_m2": float(_best["area_ibr"]),
                            "modello": _mod_ibr, "T_esercizio": float(_tf_ibr),
                            "costo_pannello": float(_costo_ibr),
                            "serie_termica": _ibr_th_u * _best["area_ibr"],
                            "serie_elettrica": _ibr_el_u * _best["area_ibr"],
                            "termico_mwh": _th_ott,
                        }
                        st.success("Trasferito. Rilancia il dimensionamento nel passo "
                                   "3 · Taglie e accumuli: il calore degli "
                                   "ibridi è ora incluso.")
                        st.rerun()
                    st.caption("Il calore degli ibridi alleggerisce il carico delle "
                               "pompe, che a loro volta determinano il consumo "
                               "elettrico calcolato qui: i due conti vanno chiusi "
                               "insieme. Trasferendo e rilanciando il dimensionamento "
                               "una volta si arriva quasi sempre a convergenza.")
                else:
                    st.success("✅ Bilancio termico allineato: il dimensionamento sta "
                               "già considerando il calore di questi moduli ibridi.")

            # =============================================================
            # 5. ANDAMENTO NELL'ANNO
            # =============================================================
            _res_el = _best["res"]
            st.divider()
            st.markdown("#### Come si distribuisce nell'anno")
            _mese = HOURS_2024.month.values
            _dfm = pd.DataFrame({
                "mese": [MONTH_NAMES[m - 1] for m in range(1, 13)],
                "consumo": [float(_cons_h[_mese == m].sum()) for m in range(1, 13)],
                "autoconsumo": [float(_res_el["autoconsumo"][_mese == m].sum())
                                for m in range(1, 13)],
                "immesso": [float(_res_el["immesso"][_mese == m].sum())
                            for m in range(1, 13)],
            })
            _fm = go.Figure()
            _fm.add_trace(go.Bar(x=_dfm["mese"], y=_dfm["autoconsumo"],
                                 name="coperto da produzione propria",
                                 marker_color=COLOR_OFFERTA))
            _fm.add_trace(go.Bar(x=_dfm["mese"], y=_dfm["consumo"] - _dfm["autoconsumo"],
                                 name="prelevato dalla rete", marker_color=COLOR_NONCOP))
            _fm.add_trace(go.Scatter(x=_dfm["mese"], y=_dfm["immesso"],
                                     name="immesso in rete", mode="lines+markers",
                                     line=dict(color=COLOR_SOLARE, width=2.5)))
            _fm.update_layout(barmode="stack", height=340, yaxis_title="MWh",
                              legend=dict(orientation="h", yanchor="bottom", y=1.02),
                              margin=dict(t=30, b=10))
            st.plotly_chart(_fm, width="stretch")
            st.caption("Le pompe di calore consumano d'inverno, il solare produce "
                       "d'estate: è questo sfasamento a limitare l'autoconsumo, molto "
                       "più della taglia dell'accumulo.")

            st.session_state["_el_risultato"] = {
                "consumo_mwh": round(_res_el["E_consumo"], 1),
                "produzione_mwh": round(_res_el["E_produzione"], 1),
                "autoconsumo_mwh": round(_res_el["E_autoconsumo"], 1),
                "immesso_mwh": round(_res_el["E_immesso"], 1),
                "prelevato_mwh": round(_res_el["E_prelevato"], 1),
                "copertura_pct": round(_res_el["copertura_pct"], 1),
                "kwp_pv": float(_best["kwp"]), "batteria_mwh": float(_best["batt"]),
                "ibrido_m2": float(_best["area_ibr"]),
                "costo_energia_eur": round(_best["costo"]),
                "capex_eur": round(_best["capex"]),
                # per il costo di esercizio del teleriscaldamento: energia comprata
                # dalla rete meno il ricavo dell'eccedenza (l'investimento va a parte)
                "acquisto_eur": round(_best["acquisto"]),
                "ricavo_eur": round(_best["ricavo"]),
            }
            # il dimensionamento (gia' eseguito in questo giro) ha usato un
            # risultato diverso: si ricalcola una volta per allinearlo
            if (_firma_el(st.session_state["_el_risultato"])
                    != st.session_state.get("_el_usato")):
                st.rerun()



# =============================================================================
# TAB 5 - CONFRONTO SCENARI (P9: rimozione selettiva)
# =============================================================================
with tab_confronto:
    st.markdown("### \U0001F4CA Confronto tra scenari salvati")
    _scen = st.session_state.get("_scenari", {})

    # --- conservazione degli scenari fra una sessione e l'altra ---
    with st.expander("💾 Esporta / importa gli scenari (copia permanente)",
                     expanded=not _scen):
        st.caption("Gli scenari salvati restano anche se ricarichi la pagina o la riapri "
                   "più tardi, perché vengono scritti in un file sul server dell'app. Quel "
                   "file però si cancella quando l'app viene riavviata o aggiornata (per "
                   "esempio dopo un commit su GitHub): per conservarli davvero scarica il "
                   "file JSON e ricaricalo quando serve.")
        _x1, _x2 = st.columns(2)
        if _scen:
            _x1.download_button(
                "⬇️ Scarica gli scenari (JSON)",
                data=json.dumps(_scen, ensure_ascii=False, indent=1,
                                default=_json_default).encode("utf-8"),
                file_name="maniago_tlr_scenari.json", mime="application/json",
                width="stretch", key="conf_dl_json")
        _up_sc = _x2.file_uploader("Carica scenari da file JSON", type=["json"],
                                   key="conf_up_json")
        if _up_sc is not None:
            _sig = (_up_sc.name, _up_sc.size)
            if st.session_state.get("_conf_ultimo_import") != _sig:
                try:
                    _imp = json.loads(_up_sc.getvalue().decode("utf-8"))
                    if not isinstance(_imp, dict):
                        raise ValueError("formato non valido")
                    st.session_state["_scenari"].update(_imp)
                    salva_scenari_file(st.session_state["_scenari"])
                    st.session_state["_conf_ultimo_import"] = _sig
                    st.success(f"Importati {len(_imp)} scenari.")
                    st.rerun()
                except Exception as _e:
                    st.error(f"File non leggibile: {_e}")

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
                    salva_scenari_file(st.session_state["_scenari"])
                    st.rerun()
            st.divider()
            gz1, gz2 = st.columns([1, 4])
            if gz1.button("\U0001F5D1\ufe0f Svuota tutto", key="del_scen_all"):
                st.session_state["_scenari"] = {}
                salva_scenari_file({})
                st.rerun()
            gz2.caption("Attenzione: *Svuota tutto* cancella l'intera lista senza conferma.")

        _scen = st.session_state.get("_scenari", {})
        if not _scen:
            st.stop()

        _misti = {s.get("autoproduzione_el", "no") for s in _scen.values()}
        if len(_misti) > 1:
            st.warning(
                "⚠️ Fra gli scenari salvati alcuni calcolano il LCOH al netto "
                "dell'autoproduzione elettrica e altri no: i costi non sono "
                "confrontabili fra loro. Per un confronto omogeneo disattiva "
                "l'opzione nel passo 2 del dimensionamento e risalva gli scenari.")

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
            ("dn_dorsale", "DN dorsale"),
            ("P_dorsale_kw", "Potenza dorsale (kW)"),
            ("n_privati_agganciati", "Privati agganciati"),
            ("tecnologie", "Assetto impianto"),
            ("P_alta_kw", "HP alta T (kW)"),
            ("P_bassa_kw", "HP bassa T (kW)"),
            ("P_backup_kw", "Caldaia di supporto (kW)"),
            ("V_hot", "Accumulo caldo (m³)"),
            ("V_int", "Accumulo intermedio (m³)"),
            ("V_low", "Accumulo basso (m³)"),
            ("accumulo_stratificato", "Accumulo stratificato"),
            ("autoproduzione_el", "LCOH al netto dell'autoproduzione"),
            ("E_hot_diretto", "Scarto diretto (MWh/a)"),
            ("E_hp_alta", "Consegnato da HP alta T (MWh/a)"),
            ("E_backup", "Da combustibile (MWh/a)"),
            ("E_elettrica", "Elettricità HP (MWh/a)"),
            ("E_scarto_utilizzato", "Scarto utilizzato (MWh/a)"),
            ("cop_alta", "COP medio HP alta T"),
            ("spf_sistema", "SPF di sistema"),
            ("quota_fer_pct", "Quota FER (%)"),
            ("tipo_solare", "Tecnologia solare"),
            ("n_pannelli_pvt", "Pannelli ibridi PVT"),
            ("pvt_elettrico_mwh", "Elettricità da PVT (MWh/a)"),
            ("pct_scarto_su_domanda", "Scarto utilizzato / domanda (%)"),
            ("pct_rinnovabile", "Rinnovabile / fornito (%)"),
            ("co2_evitata_t", "CO\u2082 evitata (t/a)"),
            ("co2_sistema_t", "CO\u2082 residua sistema (t/a)"),
            ("ore_non_coperte", "Ore non coperte"),
            ("capex_sistema", "CAPEX centrale, senza autoproduzione (\u20ac)"),
            ("capex_rete", "CAPEX rete (\u20ac)"),
            ("capex_autoproduzione", "CAPEX autoproduzione elettrica (\u20ac)"),
            ("kwp_autoproduzione", "Fotovoltaico (kWp)"),
            ("batteria_autoproduzione_mwh", "Batteria (MWh)"),
            ("ibridi_autoproduzione_m2", "Moduli ibridi da scheda elettrica (m²)"),
            ("prezzo_el_effettivo", "Prezzo effettivo elettricità (\u20ac/MWh)"),
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
        st.dataframe(df_cf, width="stretch", hide_index=True)

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
            st.plotly_chart(fig_l, width="stretch")
        with gg2:
            st.markdown("**Quota FER**")
            _v = [_scen[n].get("quota_fer_pct", 0) for n in nomi]
            fig_f = go.Figure(go.Bar(x=nomi, y=_v, marker_color=COLOR_OFFERTA,
                                     text=[f"{x:.0f}%" for x in _v], textposition="outside"))
            fig_f.update_layout(height=340, yaxis_title="%", margin=dict(t=20, b=10),
                                xaxis_tickangle=-20, yaxis_range=[0, 105])
            st.plotly_chart(fig_f, width="stretch")

        gg3, gg4 = st.columns(2)
        with gg3:
            st.markdown("**CO\u2082 evitata rispetto al gas**")
            _v = [_scen[n].get("co2_evitata_t", 0) for n in nomi]
            fig_co2 = go.Figure(go.Bar(x=nomi, y=_v, marker_color="#2E7D32",
                                       text=[f"{x:,.0f}".replace(",", ".") for x in _v],
                                       textposition="outside"))
            fig_co2.update_layout(height=340, yaxis_title="t CO\u2082 / anno",
                                  margin=dict(t=20, b=10), xaxis_tickangle=-20)
            st.plotly_chart(fig_co2, width="stretch")
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
            st.plotly_chart(fig_pct, width="stretch")

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
        st.plotly_chart(fig_mixs, width="stretch")

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
        st.plotly_chart(fig_cx, width="stretch")

        st.divider()
        st.markdown("#### \U0001F4C4 Esporta il confronto")
        _e1, _e2 = st.columns(2)
        _e1.download_button(
            "\u2B07\ufe0f Scarica il confronto (CSV)",
            data=df_cf.to_csv(index=False).encode("utf-8"),
            file_name="maniago_tlr_confronto_scenari.csv", mime="text/csv",
            width="stretch")
        _pdf = None
        try:
            _pdf = genera_pdf_scenari(_scen)
        except Exception as _e:
            st.caption(f"Scheda PDF non disponibile: {type(_e).__name__}")
        if _pdf:
            _e2.download_button(
                "\U0001F4C4 Scarica la scheda di confronto (PDF)",
                data=_pdf, file_name="maniago_tlr_confronto_scenari.pdf",
                mime="application/pdf", width="stretch", type="primary")
        else:
            _e2.caption("Per la scheda PDF serve la libreria `reportlab`: "
                        "aggiungila a `requirements.txt`.")
        st.caption("La scheda PDF riporta gli scenari affiancati, raggruppati per "
                   "utenza e rete, impianto, bilancio energetico, sostenibilità ed "
                   "economia, con le note metodologiche in calce.")


# =============================================================================
# TAB 6 - ANALISI ECONOMICA
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
            _pt_snap = _snap.get("prezzo_target_mwh")
            _origine_prezzo = st.radio(
                "Prezzo di vendita", ["Target: gas scontato", "Manuale"],
                horizontal=True, key="eco_origine_prezzo",
                help="Target: costo del calore a gas per l'utente, (PSV mensile + spread) / "
                     "rendimento caldaia, meno lo sconto; parametri in Dimensionamento, "
                     "passo 5, riquadro della scala exergetica.")
            if _origine_prezzo == "Target: gas scontato" and _pt_snap:
                prezzo_calore = round(float(_pt_snap), 1)
                st.caption(f"Costo del calore a gas per l'utente "
                           f"**{_snap.get('costo_gas_utente_mwh', 0):.1f} \u20ac/MWh** "
                           f"\u2212 {_snap.get('sconto_target_pct', 15)} % \u2192 prezzo di vendita "
                           f"**{prezzo_calore:.1f} \u20ac/MWh** (media pesata sulla domanda; "
                           f"varia mese per mese con il PSV).")
            elif _unita_prezzo == "\u20ac/MWh":
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
            _metodo_eco = st.session_state.get("off_metodo_prezzo",
                                               "Scala exergetica (riferimento gas)")
            _orig_eco = ("scala exergetica, parametri in *Dimensionamento* passo 5"
                         if _metodo_eco.startswith("Scala")
                         else ("formula PSV \u00d7 (a + b\u00b7w) impostata in *Offerta*"
                               if _metodo_eco.startswith("Formula")
                               else "prezzi fissi impostati in *Offerta*"))
            st.caption(f"Calore di scarto acquistato dalle aziende ({_orig_eco}): "
                       + f"**{_costo_scarto_base:,.0f} \u20ac/a**".replace(",", "."))
            _scarto_mult = st.slider("Correttivo sul costo del calore di scarto (\u00d7)",
                                     0.0, 3.0, 1.0, step=0.1, key="eco_scarto_mult",
                                     help="Moltiplicatore rapido per testare scenari di prezzo "
                                          "del cascame senza tornare in Offerta. 1.0 = prezzi "
                                          "impostati per azienda.")
            costo_scarto = _costo_scarto_base * _scarto_mult
            om_pct = st.slider("O&M centrale in % del suo CAPEX (\u20ac/a)", 0.5, 5.0, 2.0,
                               step=0.25, key="eco_om",
                               help="Pompe di calore, accumuli, sorgente fredda, solare.")
            om_autoprod_pct = st.slider("O&M fotovoltaico, ibridi e batterie in % del CAPEX (\u20ac/a)",
                                        0.25, 3.0, 1.0, step=0.25, key="eco_om_autoprod")
            om_rete_pct = st.slider("O&M rete, adduzioni e sottostazioni in % del CAPEX (\u20ac/a)",
                                    0.25, 3.0, 0.75, step=0.25, key="eco_om_rete",
                                    help="Tubazioni preisolate e scambiatori richiedono poca "
                                         "manutenzione: di norma 0,5-1 % l'anno.")
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
            esc_costi = st.slider("Escalation costi energia (%/a)", 0.0, 8.0, 2.0, step=0.25,
                                  key="eco_esc_cos") / 100.0
            esc_om = st.slider("Escalation O&M (%/a)", 0.0, 6.0, 2.0, step=0.25,
                               key="eco_esc_om") / 100.0

        # ---------------------------------------------------------------------
        capex_centrale = (float(_snap["capex_sistema"])
                          + float(_snap.get("capex_autoproduzione", 0.0)))
        capex_rete = float(_snap["capex_rete"])
        # fattore di annualizzazione provvisorio, per l'incidenza degli allacci
        _crf_pre = crf(float(st.session_state.get("eco_wacc", 4.0)) / 100.0,
                       int(st.session_state.get("eco_anni", 25)))

        # --- CAPEX di allacciamento delle aziende cedenti ---
        # Comprende scambiatore, opere in situ e condotta di adduzione fino
        # alla sottocentrale. Le quotazioni note arrivano dal CSV dei flussi,
        # le lunghezze delle adduzioni dal routing stradale della scheda Offerta.
        _fl_sel = st.session_state.get("_off_flussi", []) or []
        _q_all = flussi[flussi["id_flusso"].isin(_fl_sel)].copy()
        _cq = pd.to_numeric(_q_all.get("costo_allacciamento_eur"), errors="coerce")
        _costo_he_noto = float(_cq.fillna(0).sum())
        _n_senza = int(_cq.isna().sum())
        _lung_add = st.session_state.get("_off_lunghezze_adduzione", {}) or {}
        _m_add = float(sum(_lung_add.values()))

        with st.expander(f"🔌 Allacciamento delle aziende cedenti "
                         f"({len(_q_all)} flussi, {len(_lung_add)} stabilimenti)"):
            _schema_add = st.radio(
                "Schema delle adduzioni", ["dorsale", "radiale"], horizontal=True,
                key="eco_schema_add",
                format_func=lambda v: ("A dorsale: le aziende vicine condividono la condotta"
                                       if v == "dorsale" else
                                       "Radiale: una condotta per azienda fino alla sottocentrale"),
                help="A dorsale si collega la sottocentrale all'azienda piu' vicina e le altre "
                     "in cascata (albero di collegamento minimo). Le aziende di Maniago sono "
                     "a poche centinaia di metri l'una dall'altra: tre condotte separate fino "
                     "alla sottocentrale ripetono quasi tutto il percorso.")
            _m_add = lunghezza_adduzioni(sorted(_lung_add.keys()), _lung_add, _schema_add)
            _ac1, _ac2 = st.columns(2)
            _costo_m_add = _ac1.slider("Costo condotta di adduzione (€/m)", 200, 1500, 700,
                                       step=50, key="eco_costo_add",
                                       help="Comprende scavo, tubazione preisolata e "
                                            "ripristini. Le adduzioni industriali sono "
                                            "di norma più costose della distribuzione "
                                            "perché a diametro maggiore.")
            _costo_he_stima = _ac2.slider("Scambiatore, dove non quotato (€/kW)", 10, 200, 60,
                                          step=5, key="eco_costo_he",
                                          help=f"{_n_senza} flussi non hanno ancora una "
                                               f"quotazione: si stimano a potenza.")
            _p_senza = float(pd.to_numeric(_q_all.loc[_cq.isna(), "P_kW"],
                                           errors="coerce").fillna(0).sum())
            _costo_he_tot = _costo_he_noto + _p_senza * _costo_he_stima
            _costo_add_tot = _m_add * _costo_m_add
            capex_allacci = _costo_he_tot + _costo_add_tot
            _r1, _r2, _r3 = st.columns(3)
            _r1.metric("Scambiatori e opere", f"{_costo_he_tot / 1000:,.0f} k€".replace(",", "."),
                       help=f"quotati {_costo_he_noto:,.0f} € · stimati "
                            f"{_p_senza * _costo_he_stima:,.0f} € su {_p_senza:,.0f} kW".replace(",", "."))
            _add_stim = bool(st.session_state.get("_off_adduzione_stimata", False))
            _r2.metric("Condotte di adduzione", f"{_costo_add_tot / 1000:,.0f} k€".replace(",", "."),
                       help=(f"{_m_add:,.0f} m, schema {_schema_add}"
                             + (" (rete stradale non disponibile: tratti verso la "
                                "sottocentrale in linea d'aria × 1,35)" if _add_stim else ""))
                       .replace(",", "."))
            _r3.metric("Totale allacciamenti", f"{capex_allacci / 1e6:.2f} M€")
            if not _q_all.empty:
                _tb = _q_all[["azienda", "flusso", "P_kW", "costo_allacciamento_eur",
                              "modello_HE"]].copy()
                _tb["costo_allacciamento_eur"] = _cq.fillna(
                    pd.to_numeric(_q_all["P_kW"], errors="coerce") * _costo_he_stima).round(0)
                _tb.columns = ["Azienda", "Flusso", "Potenza (kW)", "Scambiatore (€)", "Modello"]
                st.dataframe(_tb, width="stretch", hide_index=True)
            _utz_ec = st.session_state.get("_off_utilizzo_aziende")
            if _utz_ec is not None and not _utz_ec.empty and capex_allacci > 0:
                _u2 = _utz_ec.copy()
                _u2["quota"] = _u2["utilizzata_mwh"] / max(_u2["utilizzata_mwh"].sum(), 1e-9)
                _u2["capex_att"] = _u2["quota"] * capex_allacci
                _u2["eur_per_mwh"] = np.where(
                    _u2["utilizzata_mwh"] > 1e-9,
                    _u2["capex_att"] * _crf_pre / _u2["utilizzata_mwh"], np.nan)
                _tb2 = _u2[["azienda", "utilizzata_mwh", "capex_att", "eur_per_mwh"]].copy()
                _tb2.columns = ["Azienda", "Calore utilizzato (MWh/a)",
                                "CAPEX attribuito (€)", "Incidenza allacciamento (€/MWh)"]
                _tb2 = _tb2.round(1)
                st.markdown("**Quanto costa il calore di ciascuna azienda**")
                st.dataframe(_tb2, width="stretch", hide_index=True)
                st.caption("Il CAPEX è ripartito in proporzione al calore effettivamente "
                           "valorizzato e annualizzato al tasso indicato. L'incidenza in "
                           "€/MWh si somma al prezzo pagato all'azienda: se supera il costo "
                           "delle alternative, quell'allacciamento non conviene.")

        # ------------------------------------------------------------------
        # CONVIENE ALLACCIARE CIASCUNA AZIENDA?
        # Per ogni combinazione di aziende si ripete il dispatch annuale con le
        # stesse macchine e si confronta il costo annuo delle sole voci che
        # cambiano: allacciamento (scambiatori + adduzioni), sorgente fredda,
        # elettricita' delle pompe, backup, acquisto del calore di scarto.
        # ------------------------------------------------------------------
        with st.expander("⚖️ Conviene allacciare ciascuna azienda?"):
            _he_per_az = (_q_all.assign(_he=_cq.fillna(
                pd.to_numeric(_q_all["P_kW"], errors="coerce").fillna(0) * _costo_he_stima))
                .groupby("azienda")["_he"].sum().to_dict()) if not _q_all.empty else {}
            # cache manuale: si ricalcola solo se cambiano gli ingressi del dispatch
            _firma_c = (tuple(sorted(map(str, _fl_sel))), float(T_mandata_ideale),
                        float(T_ritorno_ideale), float(T_int), float(eta_hp),
                        float(V_hot), float(V_int), float(V_low), float(P_alta),
                        float(P_bassa), str(backup_tipo), float(P_bk), str(backup_cop),
                        float(antigelo), float(perd), bool(strat_on), bool(solare_on),
                        round(float(np.sum(solar_low)) if solare_on else 0.0, 3),
                        str(tipo_sorgente), str(resa_sorgente), str(costo_sorgente),
                        str(_psv_sel), float(_spread_ex), float(_eta_ex), float(_sconto_ex),
                        float(_fisso_ex), float(prezzo_el_eff), float(_ets2_ex), float(_cald_ex),
                        str(formula_scarto_da_sessione()),
                        round(float(np.sum(dom_arr)), 3), len(dom_arr))
            _cache_c = st.session_state.get("_eco_combinazioni")
            try:
                if _cache_c and _cache_c[0] == _firma_c:
                    _combs = _cache_c[1]
                else:
                    with st.spinner("Simulo le combinazioni di aziende allacciate…"):
                        _combs = valuta_combinazioni_aziende(
                            off_all, idx_h, dom_arr, soil_temp_arr, float(T_mandata_ideale),
                            float(T_ritorno_ideale), float(T_int), eta_hp, V_hot, V_int, V_low,
                            P_alta, P_bassa, backup_tipo, P_bk, backup_cop, float(antigelo),
                            perd, strat_on, (solar_low if solare_on else None),
                            tipo_sorgente, resa_sorgente, costo_sorgente,
                            _T0_ex, _pz_ex, _psv_ex, float(_spread_ex), float(_eta_ex),
                            float(_sconto_ex), float(_fisso_ex), float(_ets2_ex), float(_cald_ex),
                            formula_scarto_da_sessione())
                    st.session_state["_eco_combinazioni"] = (_firma_c, _combs)
            except Exception as _e_comb:
                _combs = []
                st.caption(f"Analisi non disponibile: {type(_e_comb).__name__}")
            if _combs:
                _crf_c = crf(wacc, orizzonte)
                _fatt_netto = 1.0 - contributo_pct / 100.0
                _righe_c = []
                for _c in _combs:
                    _az = list(_c["aziende"])
                    _capex_all = (sum(_he_per_az.get(a, 0.0) for a in _az)
                                  + lunghezza_adduzioni(_az, _lung_add, _schema_add) * _costo_m_add)
                    _capex_g = _c["capex_sorgente"]
                    _annuo = ((_capex_all + _capex_g) * _fatt_netto * _crf_c
                              + _capex_all * om_rete_pct / 100.0
                              + _capex_g * om_pct / 100.0
                              + _c["costo_el"] + _c["E_backup"] * opex_bk_mwh
                              + _c["costo_scarto"])
                    _righe_c.append({
                        "Aziende allacciate": " + ".join(_az) if _az else "nessuna (solo terreno)",
                        "_n": len(_az), "_set": frozenset(_az),
                        "Calore ceduto (MWh/a)": sum(_c["MWh_ceduti"].values()),
                        "Allacciamento (k€)": _capex_all / 1000,
                        "Sorgente fredda (k€)": _capex_g / 1000,
                        "Elettricità (MWh/a)": _c["E_el"],
                        "Calore di scarto (k€/a)": _c["costo_scarto"] / 1000,
                        "Costo annuo (k€/a)": _annuo / 1000,
                        "Ore non coperte": _c["ore_non_cop"]})
                _dfc = pd.DataFrame(_righe_c)
                # ammesse le combinazioni che non peggiorano la copertura rispetto alla migliore
                _ok = _dfc[_dfc["Ore non coperte"] <= _dfc["Ore non coperte"].min()]
                _best = (_ok if not _ok.empty else _dfc).sort_values("Costo annuo (k€/a)").iloc[0]
                _attuale = _dfc[_dfc["_set"] == frozenset(off_all["azienda"].unique())]
                _cA, _cB = st.columns(2)
                _cA.metric("Combinazione più conveniente", _best["Aziende allacciate"],
                           help="Costo annuo minimo fra le combinazioni con la copertura migliore.")
                if not _attuale.empty:
                    _risp = float(_attuale.iloc[0]["Costo annuo (k€/a)"]
                                  - _best["Costo annuo (k€/a)"])
                    _cB.metric("Risparmio rispetto agli allacci attuali",
                               f"{_risp:,.0f} k€/a".replace(",", "."))
                st.dataframe(
                    _dfc.drop(columns=["_n", "_set"]).sort_values("Costo annuo (k€/a)")
                    .round(0), hide_index=True, width="stretch")
                # contributo marginale di ciascuna azienda alla configurazione attuale
                if not _attuale.empty:
                    _set_att = _attuale.iloc[0]["_set"]
                    _c_att = float(_attuale.iloc[0]["Costo annuo (k€/a)"])
                    _marg = []
                    for _a in sorted(_set_att):
                        _senza = _dfc[_dfc["_set"] == _set_att - {_a}]
                        if not _senza.empty:
                            _d = float(_senza.iloc[0]["Costo annuo (k€/a)"]) - _c_att
                            _marg.append(f"**{_a}** {'conviene' if _d > 0 else 'non conviene'} "
                                         f"({'risparmio' if _d > 0 else 'maggior costo'} di "
                                         f"{abs(_d):,.0f} k€/a)".replace(",", "."))
                    if _marg:
                        st.markdown("Contributo di ciascuna azienda, a parità delle altre: "
                                    + " · ".join(_marg) + ". Un'azienda conviene se il "
                                    "risparmio sull'energia supera il costo annuo del suo "
                                    "allacciamento.")
                st.caption(
                    "Macchine e accumuli restano quelli dello scenario; cambiano solo le voci "
                    "che dipendono dalle aziende allacciate. Senza un'azienda la pompa bassa T "
                    "preleva di più dal terreno, quindi cresce la sorgente fredda. Il costo "
                    "annuo comprende l'investimento annualizzato al netto del contributo, la "
                    "manutenzione, l'elettricità, il backup e il calore acquistato. Per "
                    "applicare la combinazione scelta, deseleziona le aziende nella scheda "
                    "Offerta.")

        # ------------------------------------------------------------------
        # SOTTOSTAZIONI D'UTENZA
        # Ogni edificio allacciato richiede uno scambiatore, il contatore di
        # calore, la regolazione e le opere murarie nel locale tecnico. E' una
        # voce che nelle reti reali pesa quanto un tratto di dorsale, e va
        # tenuta distinta dal costo della condotta.
        # ------------------------------------------------------------------
        _ri = st.session_state.get("_rete_info", {}) or {}
        _n_priv_ut = int(_ri.get("n_privati_allacciati", _ri.get("n_privati_agganciati", 0)))
        _n_pub_ut = int(_ri.get("n_utenze", 0)) - _n_priv_ut
        _e_pub_ut = float(_ri.get("E_pubblico", 0.0)) + float(_ri.get("E_condomini", 0.0))
        _e_priv_ut = float(_ri.get("E_privati", 0.0))

        with st.expander(f"🏠 Sottostazioni d'utenza "
                         f"({_n_pub_ut} fra pubblici e condomini, {_n_priv_ut} privati)"):
            st.caption("Scambiatore, contatore di calore, valvole, regolazione e opere "
                       "nel locale tecnico dell'utente. Il costo dipende soprattutto "
                       "dalla taglia: una scuola richiede una sottostazione molto più "
                       "grande di una villetta.")
            _u1, _u2, _u3 = st.columns(3)
            _cost_ut_grande = _u1.slider("Sottostazione grande (€ cad.)", 3000, 40000,
                                         12000, step=500, key="eco_sub_grande",
                                         help="Edifici pubblici e condomini: taglie "
                                              "da qualche decina a qualche centinaio di kW.")
            _cost_ut_piccola = _u2.slider("Sottostazione piccola (€ cad.)", 1500, 15000,
                                          4500, step=250, key="eco_sub_piccola",
                                          help="Utenze private singole, tipicamente "
                                               "sotto i 30 kW.")
            _quota_utente = _u3.slider("Quota a carico dell'utente (%)", 0, 100, 0,
                                       step=5, key="eco_quota_utente",
                                       help="Parte del costo di sottostazione pagata "
                                            "dall'utente all'atto dell'allacciamento. "
                                            "Riduce l'investimento del gestore ma è "
                                            "già compresa nel contributo di "
                                            "allacciamento impostato sopra: attenzione "
                                            "a non contarla due volte.")
            capex_sottostazioni = (_n_pub_ut * _cost_ut_grande
                                   + _n_priv_ut * _cost_ut_piccola)
            capex_sottostazioni *= (1.0 - _quota_utente / 100.0)
            _v1, _v2, _v3 = st.columns(3)
            _v1.metric("Pubblici e condomini",
                       f"{_n_pub_ut * _cost_ut_grande / 1000:,.0f} k€".replace(",", "."),
                       help=f"{_n_pub_ut} sottostazioni")
            _v2.metric("Privati",
                       f"{_n_priv_ut * _cost_ut_piccola / 1000:,.0f} k€".replace(",", "."),
                       help=f"{_n_priv_ut} sottostazioni")
            _v3.metric("A carico del gestore",
                       f"{capex_sottostazioni / 1e6:.2f} M€")
            if _e_pub_ut + _e_priv_ut > 0:
                _inc_sub = capex_sottostazioni * _crf_pre / (_e_pub_ut + _e_priv_ut)
                st.caption(f"Incidenza sul calore venduto: **{_inc_sub:.1f} €/MWh**. "
                           f"Se le sottostazioni pesano molto, conviene concentrare la "
                           f"rete sulle utenze grandi: una sottostazione costa quasi "
                           f"uguale a prescindere dai MWh che serve.")

        capex_tot = (capex_centrale + capex_rete + capex_allacci
                     + capex_sottostazioni)
        contributo = capex_tot * contributo_pct / 100.0
        capex_netto = capex_tot - contributo

        E_venduto = float(_snap["carico_utenze_mwh"])
        E_prodotto = float(_snap["carico_centrale_mwh"])
        # la domanda che la centrale non copre non si vende: senza questa
        # correzione uno scenario sottodimensionato risultava il piu' redditizio
        _E_nc = float(_snap.get("E_non_coperta", 0.0) or 0.0)
        if _E_nc > 1e-6 and E_prodotto > 0:
            _q_nc = min(_E_nc / E_prodotto, 1.0)
            E_venduto = E_venduto * (1.0 - _q_nc)
            if _q_nc > 0.005:
                st.error(f"La centrale non copre {_E_nc:,.0f} MWh/a "
                         f"({_q_nc * 100:.1f} % della domanda): i ricavi sono calcolati solo "
                         f"sul calore effettivamente fornito. Controlla le taglie nel "
                         f"Dimensionamento.".replace(",", "."))

        ricavo_calore_0 = E_venduto * prezzo_calore
        ricavo_fisso_0 = n_utenze_eco * quota_fissa
        ricavi_0 = ricavo_calore_0 + ricavo_fisso_0
        incasso_allacci = n_utenze_eco * allacci_eur

        opex_energia_0 = float(_snap["opex_annuo"])
        costo_pompaggio_0 = E_prodotto * pompaggio_kwh_mwh / 1000.0 * float(_snap["prezzo_el"])
        _capex_autoprod = float(_snap.get("capex_autoproduzione", 0.0))
        om_0 = ((capex_centrale - _capex_autoprod) * om_pct / 100.0
                + _capex_autoprod * om_autoprod_pct / 100.0
                + (capex_rete + capex_allacci + capex_sottostazioni) * om_rete_pct / 100.0)
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
        # il margine comprende anche l'acquisto del calore di scarto, che nei
        # flussi di cassa c'e' gia': escluderlo qui lo faceva sembrare positivo
        # anche quando la gestione era in pareggio
        margine_0 = (ricavi_0 - opex_energia_0 - costo_pompaggio_0 - costo_scarto_0
                     - om_0 - costi_fissi_0)

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
        m4.metric("Margine anno 1", f"{margine_0 / 1000:.0f} k\u20ac/a",
                  help="Ricavi meno tutti i costi di esercizio dell'anno 1: energia, "
                       "pompaggio, acquisto del calore di scarto, O&M, personale e "
                       "varie. Non comprende il rientro dell'investimento.")

        n1, n2, n3, n4 = st.columns(4)
        n1.metric("CAPEX totale", f"{capex_tot / 1e6:.2f} M\u20ac",
                  help=f"centrale {capex_centrale / 1e6:.2f} (di cui autoproduzione "
                       f"{float(_snap.get('capex_autoproduzione', 0)) / 1e6:.2f}) "
                       f"+ rete {capex_rete / 1e6:.2f} "
                       f"+ allacci aziende {capex_allacci / 1e6:.2f} "
                       f"+ sottostazioni {capex_sottostazioni / 1e6:.2f} M€")
        n2.metric("Contributo pubblico", f"{contributo / 1e6:.2f} M\u20ac",
                  help=f"{contributo_pct}% del CAPEX")
        n3.metric("Investimento netto", f"{capex_netto / 1e6:.2f} M\u20ac")
        n4.metric("LCOH completo", f"{lcoh_completo:.1f} \u20ac/MWh",
                  help="Include rete, O&M, pompaggio, personale. Riferito al calore VENDUTO. "
                       "Il 'LCOH di sistema' della scheda Dimensionamento e piu ristretto "
                       "(sola centrale, riferito al calore prodotto): non sono confrontabili "
                       "direttamente.")

        # ------------------------------------------------------------------
        # INCENTIVO NECESSARIO: quanto serve per portare il VAN a zero, in
        # conto capitale (una tantum all'anno 0) oppure in conto esercizio
        # (EUR per MWh venduto, costante, per un numero di anni dato).
        # Il VAN e' lineare in entrambe le leve, quindi le soglie sono esatte.
        # ------------------------------------------------------------------
        st.markdown("#### \U0001F3AF Incentivo necessario per VAN = 0")
        _gap_van = max(-_van, 0.0)
        _i1, _i2, _i3 = st.columns([1, 1, 1])
        _durata_inc = _i3.slider("Durata dell'incentivo in conto esercizio (anni)", 1,
                                 int(orizzonte), int(orizzonte), key="eco_durata_inc")
        _af_inc = sum(1.0 / (1.0 + wacc) ** _t for _t in range(1, _durata_inc + 1))
        _contr_nec = contributo + _gap_van
        if _gap_van <= 0:
            _i1.metric("Contributo in conto capitale", f"{contributo / 1e6:.2f} M€",
                       help="Il progetto ha gia' VAN positivo con il contributo impostato.")
            _i2.metric("Incentivo in conto esercizio", "0 €/MWh")
        else:
            if _contr_nec <= capex_tot:
                _i1.metric("Contributo in conto capitale necessario",
                           f"{_contr_nec / 1e6:.2f} M€",
                           delta=f"{_contr_nec / capex_tot * 100:.0f} % del CAPEX",
                           delta_color="off",
                           help=f"Oggi ipotizzati {contributo / 1e6:.2f} M€ "
                                f"({contributo_pct} %). Senza incentivi in conto esercizio.")
            else:
                _i1.metric("Contributo in conto capitale necessario", "oltre il CAPEX",
                           delta=f"{_contr_nec / 1e6:.2f} M€", delta_color="off",
                           help="Anche finanziando il 100 % dell'investimento il VAN resta "
                                "negativo: la gestione corrente e' in perdita e va sostenuta "
                                "con un incentivo in conto esercizio o con il prezzo.")
            _inc_nec = _gap_van / (E_venduto * _af_inc) if E_venduto > 0 else float("nan")
            _i2.metric("Incentivo in conto esercizio necessario",
                       f"{_inc_nec:.1f} €/MWh",
                       delta=f"{_inc_nec * E_venduto / 1000:,.0f} k€/a".replace(",", "."),
                       delta_color="off",
                       help=f"Per MWh venduto, costante per {_durata_inc} anni, con il "
                            f"contributo in conto capitale attuale ({contributo_pct} %).")
        # combinazioni: per ogni quota di contributo, l'incentivo che serve ancora
        _righe_inc = []
        for _q in (0, 20, 40, 60, 80, 100):
            _gap_q = max(_gap_van - capex_tot * (_q - contributo_pct) / 100.0, 0.0)
            _righe_inc.append({
                "Contributo in conto capitale": f"{_q} % ({capex_tot * _q / 100 / 1e6:.2f} M€)",
                "Incentivo in conto esercizio (€/MWh)":
                    round(_gap_q / (E_venduto * _af_inc), 1) if E_venduto > 0 else None,
                "Incentivo (k€/a)":
                    round(_gap_q / _af_inc / 1000) if _af_inc > 0 else None})
        st.dataframe(pd.DataFrame(_righe_inc), hide_index=True, width="stretch")
        st.caption("Ogni riga e' una combinazione che porta il VAN a zero: con quella quota "
                   "di contributo sull'investimento, l'incentivo in conto esercizio indicato "
                   "sul calore venduto. Valori prima delle imposte, attualizzati al WACC.")

        # ------------------------------------------------------------------
        # QUANTO SERVIREBBE PERCHE' IL PROGETTO STIA IN PIEDI
        # Quando il tempo di ritorno supera l'orizzonte, dire soltanto "non
        # rientra" non aiuta: serve sapere di quanto manca e su quale leva
        # agire. Qui si calcolano tre soglie alternative, ciascuna agendo su
        # una sola variabile per volta.
        # ------------------------------------------------------------------
        if _pb is None or _van < 0:
            st.divider()
            st.markdown("#### \U0001F9ED Cosa servirebbe perché il progetto stia in piedi")
            _margine_unit = margine_0 / E_venduto if E_venduto > 0 else 0.0
            _costi_tot_0 = (opex_energia_0 + costo_pompaggio_0 + costo_scarto_0
                            + om_0 + costi_fissi_0)
            _crf_x = crf(wacc, orizzonte)

            if margine_0 <= 0:
                st.error(
                    f"**Il margine di gestione è negativo** "
                    f"({margine_0 / 1000:,.0f} k€/a): i ricavi non coprono nemmeno i "
                    f"costi di esercizio. Nessun contributo in conto capitale può "
                    f"risolverlo, perché il problema non è l'investimento iniziale ma "
                    f"la gestione corrente. Occorre alzare il prezzo di vendita, "
                    f"ridurre i costi operativi o aumentare il calore venduto."
                    .replace(",", "."))
            else:
                _c1, _c2, _c3 = st.columns(3)

                def _van_con_contributo(q_pct):
                    _cn = capex_tot * (1.0 - q_pct / 100.0)
                    _fc = [-_cn + incasso_allacci]
                    for _t in range(1, orizzonte + 1):
                        _fc.append(
                            ricavi_0 * (1 + esc_ricavi) ** (_t - 1)
                            - (opex_energia_0 + costo_pompaggio_0 + costo_scarto_0)
                            * (1 + esc_costi) ** (_t - 1)
                            - (om_0 + costi_fissi_0) * (1 + esc_om) ** (_t - 1))
                    return van(_fc, wacc)

                _q_nec = None
                if _van_con_contributo(100.0) > 0:
                    _lo, _hi = float(contributo_pct), 100.0
                    for _ in range(50):
                        _m = (_lo + _hi) / 2.0
                        if _van_con_contributo(_m) < 0:
                            _lo = _m
                        else:
                            _hi = _m
                    _q_nec = _hi
                if _q_nec is not None:
                    _c1.metric("Contributo necessario", f"{_q_nec:.0f} %",
                               delta=f"{_q_nec - contributo_pct:+.0f} punti",
                               delta_color="inverse",
                               help=f"{capex_tot * _q_nec / 100 / 1e6:.2f} M€ contro i "
                                    f"{contributo / 1e6:.2f} M€ attualmente ipotizzati")
                else:
                    _c1.metric("Contributo necessario", "non sufficiente",
                               help="Nemmeno un contributo del 100 % rende positivo il "
                                    "valore attuale netto: il margine di gestione è "
                                    "troppo esiguo per sostenere i costi ricorrenti.")

                _prezzo_nec = (((capex_netto - incasso_allacci) * _crf_x + _costi_tot_0
                                - ricavo_fisso_0) / E_venduto) if E_venduto > 0 else None
                if _prezzo_nec:
                    _c2.metric("Prezzo di vendita necessario", f"{_prezzo_nec:.0f} €/MWh",
                               delta=f"{_prezzo_nec - prezzo_calore:+.0f}",
                               delta_color="inverse",
                               help=f"A parità di contributo e di costi. Oggi impostato "
                                    f"a {prezzo_calore:.0f} €/MWh. Va confrontato con "
                                    f"quanto l'utente spende oggi col proprio impianto.")

                _mancante = max(-_van, 0.0)
                _extra = (_mancante * _crf_x / _margine_unit) if _margine_unit > 0 else None
                if _extra is not None and _extra < E_venduto * 3:
                    _c3.metric("Calore da vendere in più",
                               f"+{_extra / E_venduto * 100:.0f} %",
                               help=f"{_extra:,.0f} MWh/a in più a parità di rete e di "
                                    f"costi fissi, cioè allacciando altre utenze lungo "
                                    f"il tracciato già posato.".replace(",", "."))
                else:
                    _c3.metric("Calore da vendere in più", "oltre il triplo",
                               help="Il divario non si colma densificando la rete attuale.")

                st.caption(
                    "Le tre soglie sono alternative, non cumulative: ciascuna porta a "
                    "zero il valore attuale netto agendo su una sola variabile e "
                    "lasciando ferme le altre. Nella pratica si combinano, e conviene "
                    "verificare quale sia davvero disponibile: il contributo dipende "
                    "dai bandi aperti, il prezzo di vendita dal confronto con il costo "
                    "del gas per l'utente finale, le utenze aggiuntive dalla densità "
                    "edilizia lungo il tracciato.")

                with st.expander("Strumenti di finanziamento da verificare"):
                    st.markdown(
                        "Canali che di norma finanziano reti di teleriscaldamento da "
                        "recupero di calore. Le finestre e le percentuali cambiano nel "
                        "tempo, quindi vanno verificate al momento della domanda.\n\n"
                        "- **Conto Termico** (GSE), per la quota di impianto a fonte "
                        "rinnovabile e per gli interventi sugli edifici pubblici allacciati\n"
                        "- **Fondi europei a gestione regionale** (FESR) e programmi di "
                        "cooperazione territoriale come **Interreg**, che è il canale "
                        "del progetto HEAT 35 stesso\n"
                        "- **Fondo nazionale per l'efficienza energetica** e strumenti "
                        "della **BEI** per la quota a debito, spesso a condizioni "
                        "migliori del mercato\n"
                        "- **Certificati bianchi** per il risparmio di energia primaria: "
                        "sono però un ricavo in conto esercizio e non riducono "
                        "l'investimento iniziale\n\n"
                        "Il modello tratta il contributo come una percentuale unica del "
                        "CAPEX. Per una valutazione puntuale occorre verificare quali "
                        "voci siano ammissibili in ciascuno strumento, perché spesso "
                        "rete, sottostazioni e centrale hanno aliquote diverse.")

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
        st.plotly_chart(fig_cf, width="stretch")

        st.markdown("#### Struttura dei costi annui (anno 1)")
        _voci_c = [("Energia (elettricità HP + combustibile)", opex_energia_0, COLOR_HP),
                   ("Acquisto calore di scarto", costo_scarto_0, COLOR_OFFERTA),
                   ("Pompaggio di rete", costo_pompaggio_0, "#4C6EF5"),
                   ("O&M impianti e rete", om_0, COLOR_ACCUMULO),
                   ("Personale e gestione", personale, "#F4A259"),
                   ("Assicurazioni e varie", assicuraz, "#9AA0A6"),
                   ("CAPEX annualizzato", capex_netto * _crf_eco, "#5B8DEF")]
        # nota: il CAPEX comprende centrale, rete e allacciamenti industriali
        _voci_c = [(n, v, c) for n, v, c in _voci_c if v > 0]
        # A barre e non a torta: ogni voce e' espressa anche in euro per MWh
        # venduto, cioe' nella stessa unita' del prezzo di vendita, cosi' si
        # legge subito quanto incide sul costo finale del calore.
        _fig_str = go.Figure()
        _nm = [n for n, _, _ in _voci_c]
        _vl = [v for _, v, _ in _voci_c]
        _cl = [c for _, _, c in _voci_c]
        _inc = [v / E_venduto if E_venduto > 0 else 0 for v in _vl]
        _fig_str.add_trace(go.Bar(
            y=_nm, x=_vl, orientation="h", marker_color=_cl,
            text=[f"{v/1000:,.0f} k€  ({i:.1f} €/MWh)".replace(",", ".")
                  for v, i in zip(_vl, _inc)],
            textposition="outside",
            hovertemplate="%{y}<br>%{x:,.0f} €/a<extra></extra>"))
        _fig_str.update_layout(
            height=max(240, 44 * len(_voci_c) + 90),
            xaxis_title="€/anno",
            title=f"Costo annuo completo · {costo_annuo_completo:,.0f} €/a "
                  f"· {lcoh_completo:.1f} €/MWh".replace(",", "."),
            margin=dict(t=44, b=10, l=10, r=150), showlegend=False)
        _fig_str.update_yaxes(autorange="reversed")
        st.plotly_chart(_fig_str, width="stretch")
        st.caption("Fra parentesi l'incidenza di ciascuna voce sul calore venduto: "
                   "sommate danno il costo pieno del calore, confrontabile "
                   "direttamente col prezzo di vendita.")

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
        st.plotly_chart(fig_sens, width="stretch")

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
            st.plotly_chart(fig_sens2, width="stretch")

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
                    help="Valore sociale della CO\u2082 evitata, solo indicativo. L'ETS2 che "
                         "l'utente pagherebbe sul gas e' gia' nel prezzo di vendita (riquadro "
                         "della scala exergetica in Dimensionamento): non va sommato di nuovo.")

        # ------------------------------------------------------------------
        # STRUTTURA FINANZIARIA
        # Il calcolo sopra tratta l'investimento come se fosse pagato per
        # intero e subito. Nella realta' un'opera di questa dimensione viene
        # finanziata: qui si aggiungono debito, ammortamenti e imposte, che
        # cambiano sensibilmente il quadro perche' gli interessi e gli
        # ammortamenti sono deducibili.
        # ------------------------------------------------------------------
        st.divider()
        st.markdown("#### \U0001F3E6 Struttura finanziaria")
        _usa_pf = st.checkbox("Considera debito, ammortamenti e imposte",
                              value=False, key="eco_usa_pf",
                              help="Senza questa opzione il progetto è valutato come "
                                   "se fosse interamente autofinanziato e non soggetto "
                                   "a imposte: è il conto più semplice, ma trascura la "
                                   "leva finanziaria e la deducibilità di interessi e "
                                   "ammortamenti.")
        if _usa_pf:
            _f1, _f2, _f3 = st.columns(3)
            with _f1:
                _q_deb = st.slider("Quota coperta da debito (%)", 0, 90, 70, step=5,
                                   key="eco_q_deb",
                                   help="Percentuale dell'investimento netto, cioè al "
                                        "netto del contributo pubblico.") / 100.0
                _t_deb = st.slider("Tasso sul debito (%)", 0.5, 10.0, 4.5, step=0.25,
                                   key="eco_t_deb") / 100.0
            with _f2:
                _anni_deb = st.slider("Durata del debito (anni)", 5, 30, 15,
                                      key="eco_anni_deb")
                _rate_anno = st.selectbox("Rate all'anno", [1, 2, 4, 12], index=1,
                                          key="eco_rate_anno",
                                          help="Il piano si calcola per rata e si "
                                               "aggrega per anno: sommare direttamente "
                                               "su base annua sottostimerebbe gli interessi.")
            with _f3:
                _aliq = st.slider("Aliquota sul reddito (%)", 0, 45, 24, step=1,
                                  key="eco_aliq",
                                  help="IRES 24 %. Aggiungere l'IRAP se rilevante "
                                       "per la forma societaria scelta.")
                _anni_amm = st.slider("Anni di ammortamento fiscale", 5, 40, 20,
                                      key="eco_anni_amm")

            _costi_op_pf = (opex_energia_0 + costo_pompaggio_0 + costo_scarto_0
                            + om_0 + costi_fissi_0)
            _df_ce, _sint = conto_economico(
                anni=orizzonte, ricavi_0=ricavi_0, costi_op_0=_costi_op_pf,
                capex_lordo=capex_tot, contributo=contributo,
                quota_debito=_q_deb, tasso_debito=_t_deb, anni_debito=_anni_deb,
                aliquota_imposte=_aliq / 100.0, anni_ammortamento=_anni_amm,
                esc_ricavi=esc_ricavi, esc_costi=esc_costi,
                rate_per_anno=int(_rate_anno))

            _van_p = van(_sint["flussi_progetto"], wacc)
            _van_e = van(_sint["flussi_equity"], wacc)
            _tir_p = tir(_sint["flussi_progetto"])
            _tir_e = tir(_sint["flussi_equity"])

            _s1, _s2, _s3, _s4 = st.columns(4)
            _s1.metric("Debito", f"{_sint['debito'] / 1e6:.2f} M€",
                       help=f"su {_sint['capex_netto'] / 1e6:.2f} M€ di investimento netto")
            _s2.metric("Capitale proprio", f"{_sint['equity'] / 1e6:.2f} M€")
            _s3.metric("Interessi totali", f"{_sint['interessi_totali'] / 1e6:.2f} M€")
            _s4.metric("Imposte totali", f"{_sint['imposte_totali'] / 1e6:.2f} M€")

            _r1, _r2, _r3, _r4 = st.columns(4)
            _r1.metric("VAN di progetto", f"{_van_p / 1e6:.2f} M€",
                       help="Flussi disponibili prima del servizio del debito, "
                            "attualizzati al WACC.")
            _r2.metric("VAN per l'azionista", f"{_van_e / 1e6:.2f} M€",
                       help="Flussi che restano dopo aver pagato rate e interessi.")
            _r3.metric("TIR di progetto",
                       f"{_tir_p * 100:.1f}%" if _tir_p is not None else "n/d")
            _r4.metric("TIR per l'azionista",
                       f"{_tir_e * 100:.1f}%" if _tir_e is not None else "n/d",
                       help="Se supera il TIR di progetto, la leva finanziaria sta "
                            "creando valore: il debito costa meno del rendimento "
                            "dell'investimento.")

            _d1, _d2 = st.columns(2)
            _dscr_min = _sint["dscr_min"]
            _d1.metric("DSCR minimo", f"{_dscr_min:.2f}" if np.isfinite(_dscr_min) else "n/d",
                       help="Rapporto fra flusso di cassa e servizio del debito nell'anno "
                            "peggiore. Le banche chiedono di norma almeno 1,20-1,30.")
            _d2.metric("DSCR medio", f"{_sint['dscr_medio']:.2f}"
                       if np.isfinite(_sint["dscr_medio"]) else "n/d")
            if np.isfinite(_dscr_min):
                if _dscr_min < 1.0:
                    st.error(f"⚠️ Con un DSCR minimo di {_dscr_min:.2f} il progetto non "
                             f"genera cassa sufficiente a pagare le rate: va ridotta la "
                             f"quota di debito, allungata la durata o aumentato il "
                             f"contributo pubblico.")
                elif _dscr_min < 1.2:
                    st.warning(f"⚠️ DSCR minimo {_dscr_min:.2f}: sotto la soglia di 1,20 "
                               f"normalmente richiesta dagli istituti di credito. "
                               f"Il margine di sicurezza è esiguo.")
                else:
                    st.success(f"✅ DSCR minimo {_dscr_min:.2f}: il flusso di cassa copre "
                               f"il servizio del debito con margine adeguato.")

            _pe = prezzo_di_equilibrio(
                E_venduto, ricavo_fisso_0, orizzonte, _costi_op_pf, capex_tot,
                contributo, _q_deb, _t_deb, _anni_deb, wacc,
                aliquota_imposte=_aliq / 100.0, anni_ammortamento=_anni_amm,
                esc_ricavi=esc_ricavi, esc_costi=esc_costi,
                rate_per_anno=int(_rate_anno))
            if _pe is not None:
                _scarto = prezzo_calore - _pe
                st.metric("Prezzo di equilibrio del calore", f"{_pe:.1f} €/MWh",
                          delta=f"{_scarto:+.1f} rispetto al prezzo impostato",
                          delta_color="normal" if _scarto >= 0 else "inverse",
                          help="Prezzo che annulla il valore attuale netto: è il minimo "
                               "a cui il progetto sta in piedi.")
                if _scarto < 0:
                    st.warning(f"Al prezzo di {prezzo_calore:.0f} €/MWh il progetto "
                               f"distrugge valore: servirebbero almeno {_pe:.0f} €/MWh, "
                               f"oppure un contributo più alto.")

            _fg = go.Figure()
            _fg.add_trace(go.Bar(x=_df_ce["anno"], y=_df_ce["ebitda"], name="EBITDA",
                                 marker_color=COLOR_OFFERTA))
            _fg.add_trace(go.Bar(x=_df_ce["anno"], y=-_df_ce["interessi"],
                                 name="interessi", marker_color=COLOR_CALDAIA))
            _fg.add_trace(go.Bar(x=_df_ce["anno"], y=-_df_ce["quota_capitale"],
                                 name="quota capitale", marker_color="#8E5FC2"))
            _fg.add_trace(go.Bar(x=_df_ce["anno"], y=-_df_ce["imposte"],
                                 name="imposte", marker_color="#9AA0A6"))
            _fg.add_trace(go.Scatter(x=_df_ce["anno"], y=_df_ce["fcf_equity"],
                                     name="flusso per l'azionista", mode="lines+markers",
                                     line=dict(color=COLOR_DOMANDA, width=2.5)))
            _fg.update_layout(barmode="relative", height=400, yaxis_title="€/anno",
                              xaxis_title="anno",
                              legend=dict(orientation="h", yanchor="bottom", y=1.02),
                              margin=dict(t=30, b=10))
            st.plotly_chart(_fg, width="stretch")

            with st.expander("📄 Conto economico e flussi, anno per anno"):
                _vis = _df_ce.copy()
                _vis.columns = ["Anno", "Ricavi", "Costi operativi", "EBITDA",
                                "Ammortamenti", "EBIT", "Interessi", "EBT", "Imposte",
                                "Utile netto", "Quota capitale", "Debito residuo",
                                "Flusso di progetto", "Flusso per l'azionista", "DSCR"]
                st.dataframe(_vis.round(0), width="stretch", hide_index=True)
                st.download_button("⬇️ Scarica il conto economico (CSV)",
                                   data=_vis.to_csv(index=False).encode("utf-8"),
                                   file_name="maniago_tlr_conto_economico.csv",
                                   mime="text/csv", key="eco_dl_ce")
            st.caption("Le imposte gravano sul reddito imponibile, quindi al netto di "
                       "ammortamenti e interessi passivi che sono deducibili. Il flusso "
                       "di progetto è quello disponibile prima del servizio del debito, "
                       "quello per l'azionista è ciò che resta dopo. Non sono considerati "
                       "l'IVA, il credito d'imposta e gli eventuali incentivi in conto "
                       "esercizio, che vanno valutati caso per caso.")

        with st.expander("\U0001F4C4 Dettaglio dei flussi di cassa anno per anno"):
            df_det = pd.DataFrame(dettaglio)
            df_det["Cumulato (\u20ac)"] = df_det["Flusso netto (\u20ac)"].cumsum() + flussi_cassa[0]
            st.dataframe(df_det, width="stretch", hide_index=True)
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
