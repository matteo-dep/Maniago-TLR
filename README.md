# Maniago TLR — app di dimensionamento rete di teleriscaldamento

App Streamlit unica per domanda, offerta di calore di scarto, dimensionamento
(accumulo + pompa di calore + backup) e confronto scenari del pilota di Maniago.

## Come si avvia

```bash
pip install -r requirements.txt
streamlit run "TLR 2.py"
```

Su **Streamlit Cloud**: nelle impostazioni dell'app (Manage app → Settings) il
*Main file path* deve puntare a `TLR 2.py`. Se prima era impostato su
`app.py`, cambialo qui — era questa la causa dell'app che eseguiva codice vecchio.

## Cosa contiene la root (i soli file che l'app legge)

| File | A cosa serve |
|------|--------------|
| `TLR 2.py` | l'applicazione (unico script, tutto calcolato live) |
| `requirements.txt` | dipendenze |
| `maniago_domanda_edifici.csv` | anagrafica edifici: zona, tipologia, tipo utenza (pubblico/privato) |
| `maniago_domanda_oraria_8760h_HDD_reale.csv` | domanda oraria per edificio, separata riscaldamento/ACS |
| `maniago_flussi_offerta.csv` | flussi di calore di scarto per azienda (T, potenza, profilo) |
| `pvgis_maniago_pulito.csv` | irraggiamento solare orario (per il solare termico) |
| `edifici_pubblici_coordinate.csv` | coordinate per l'ottimizzazione della densità lineare |

Sono **7 file in tutto**. L'app non ne legge altri: verificato leggendo ogni
`read_csv` nel codice.

## Perché questa fusione (main + prova → uno solo)

Lo script `provaTLRManiago.py` era **identico** nei due branch (stesso hash). La
differenza stava solo nei dati, e nessuno dei due branch da solo aveva tutti i
file necessari — ecco perché l'app non partiva mai:

- **`maniago_domanda_edifici.csv`**: la versione di *main* non aveva la colonna
  `tipo_utenza` → era la causa del `KeyError` all'avvio. Tenuta la versione di
  *prova* (ha `tipo_utenza` e 27 edifici invece di 23).
- **`maniago_domanda_oraria_8760h_HDD_reale.csv`**: *main* aveva una sola colonna
  `MWh`; il codice invece usa `MWh_riscaldamento` e `MWh_ACS` separate → tenuta la
  versione di *prova*.
- **`maniago_flussi_offerta.csv`**: presente **solo in main** → preso da lì.
- **`pvgis_maniago_pulito.csv`** e **`edifici_pubblici_coordinate.csv`**: presenti
  **solo in prova** → presi da lì.

Collaudo eseguito: `load_data()` gira senza errori, il merge zona/tipo_utenza è
completo su tutti gli edifici, i 4 cluster (Campagna, Ex Bioman, NE-Centro, Ovest)
sono presenti, tutti i profili dei flussi sono gestiti dal motore.

## Cartella `_archivio/` (niente è stato buttato)

File dei vecchi branch che l'app **non usa**, tenuti per sicurezza:

- `script_generazione_dati/` — gli script con cui erano stati generati i CSV
  (offerta ZML, modulazione gradi-giorno). Utili se un domani rigeneri i dati.
- `dati_sorgente_non_letti_dall_app/` — dati grezzi di provenienza (dettaglio ZML
  a 5 min, condomìni, mappa utenze, temperature sorgente…). L'app non li apre, ma
  documentano da dove vengono i numeri.
- `versioni_superate/` — le versioni "sbagliate" dei file duplicati (la domanda
  edifici senza `tipo_utenza`, la domanda oraria con struttura diversa, la vecchia
  `maniago_aziende_offerta.csv` del motore precedente).

Puoi committare anche `_archivio/` senza problemi: l'app legge i file per nome
nella root, quindi la sottocartella non interferisce. Se preferisci un repo
minimale, cancella pure `_archivio/` — l'app continua a funzionare con i 7 file.

## Passare a un branch unico su GitHub

Se vuoi un solo branch pulito:

1. Sostituisci il contenuto della root del repo con questi file.
2. Committa su `main`.
3. Su Streamlit Cloud verifica che il *Main file* sia `provaTLRManiago.py`.
4. Se non ti serve più `prova`, cancellalo (Settings → Branches, o
   `git push origin --delete prova`).

## Correzioni del 13/10/2026

1. **Edifici "esclusi per densità < 0.0"**: gli edifici che il grafo stradale OSM
   non raggiunge non vengono più etichettati come potati dalla soglia. Restano
   serviti con un allaccio in linea d'aria × tortuosità (incluso in lunghezza e
   CAPEX della rete) e sono elencati in un avviso dedicato.
2. **Coordinate mancanti**: corretti in `edifici_pubblici_coordinate.csv` i nomi
   di "Asilo Nido / Scuola materna (via Campagna 50)" e "Sede Agenzia delle
   Entrate e Centro per l'impiego"; l'abbinamento ora ignora maiuscole e spazi e
   gli edifici pubblici ancora senza coordinate sono segnalati per nome.
3. **Dimensionamento ed Economia sugli edifici SERVITI**: i pubblici potati o
   senza coordinate non entrano più in domanda, taglie e ricavi. I condomini
   applicano consumo per unità e tasso di adesione anche nel dimensionamento.
4. **Privati coerenti fra rete e dimensionamento**: la quota nel buffer si calcola
   sull'energia (non sul numero di edifici); sottostazioni, utenze, quote fisse e
   contemporaneità contano i privati che si allacciano davvero (buffer × tasso).
5. **Margine anno 1** comprende l'acquisto del calore di scarto.
6. **Calore rinnovabile / totale fornito**: il calore della HP bassa T non è più
   contato due volte al denominatore.
7. **Picco della dorsale**: la contemporaneità QM si applica alle sole utenze
   private e condominiali (prima il picco calava aggiungendo utenze).
8. **Adduzioni senza OSM**: le lunghezze stimate (linea d'aria × 1,35) entrano
   comunque nell'analisi economica, segnalate come stima (prima valevano zero).
10. **Mappa stradale incompleta**: la copia salvata della mappa OSM
   (`maniago_strade_cache.json`) ora registra il riquadro scaricato e viene
   riscaricata se non copre l'area di studio (le versioni vecchie, con raggio
   1,5 km, lasciavano fuori il centro). Il raggio passa a 3,6 km per includere
   Fratta, la Biblioteca e tutti i privati. Gli edifici si agganciano solo alla
   rete stradale principale, non a frammenti isolati (cortili, parcheggi).
9. Colonna "Pozzi" del confronto sorgenti resa omogenea (errore Arrow).
