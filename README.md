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
