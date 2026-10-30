# mapsleads — prototipo

Trova attività senza sito web con un approccio ibrido: OpenStreetMap (gratis) per l'elenco,
controlli web gratuiti, Google Places solo per verificare i candidati rimasti, con tetto mensile.

```bash
uv sync
cp .env.example .env            # aggiungi GOOGLE_PLACES_API_KEY solo per `verify`
uv run mapsleads fetch --area isola
uv run mapsleads classify
uv run mapsleads verify --dry-run
uv run mapsleads verify --limit 50
uv run mapsleads export-xlsx leads.xlsx
```

Esiti: `has_site`, `only_social`, `dead_site`, `guessed_site` (dominio probabile, da controllare),
`candidate` (nessun sito in OSM, da verificare su Google), `no_site` (confermato da Google).
Un candidato senza corrispondenza affidabile su Google resta `candidate`, non diventa `no_site`.

Prima di usarlo per contattare: termini d'uso di Google (non conservare i dati oltre il
consentito) e regole GDPR/marketing diretto.

## Studio 2: giardini privati (Milano)

Mappa di potenziale per il giardinaggio da dati aperti. **Niente immagini Google Maps** (i termini
vietano di estrarne dati). Nessun nome o contatto di proprietari: l'output sono particelle e
indirizzi/coordinate.

```bash
uv sync --extra geo
uv run mapsleads garden analyze \
  --parcels particelle.gpkg --buildings edifici.gpkg --ortho ortofoto_rgbi.tif \
  --public-green verde_pubblico.gpkg --chm chioma.tif
```

Per ogni particella con edifici: parte scoperta (lotto − edifici − verde pubblico), NDVI
dall'ortofoto con infrarosso (Sentinel-2, a 10 m, è troppo grossolano per i lotti), tipo
(`villa` = giardino privato, `condominio` = verde condiviso), punteggio 0-100 da calibrare.

Dati da scaricare per il pilota (Lambrate), tutti aperti e senza dati personali:

| Dato | Fonte |
|---|---|
| Particelle (solo geometrie) | Agenzia delle Entrate, cartografia catastale INSPIRE |
| Edifici | DBT Regione Lombardia / Comune di Milano |
| Ortofoto RGB + infrarosso | Regione Lombardia (AGEA) |
| Altezze (DSM/DTM) | Regione Lombardia, LiDAR |
| Verde pubblico | Comune di Milano, open data |

Contatto: solo volantini non indirizzati ("Al residente") evitano il trattamento di dati
personali; posta nominativa o ricerca dei nomi richiede una valutazione GDPR prima di partire.
