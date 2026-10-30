from collections import Counter

import typer

from . import export, overpass, pipeline, storage
from .config import Settings
from .garden import cli as garden_cli
from .google_places import BudgetExceeded

app = typer.Typer(no_args_is_help=True, help="Aziende senza sito: OSM + verifica Google.")

app.add_typer(garden_cli.app, name="garden")


def _bbox(area: str, bbox: str | None) -> tuple[float, float, float, float]:
    if bbox:
        s, w, n, e = (float(x) for x in bbox.split(","))
        return s, w, n, e
    if area not in overpass.AREAS:
        raise typer.BadParameter(f"area sconosciuta: {area}. Usa {', '.join(overpass.AREAS)}")
    return overpass.AREAS[area]


@app.command()
def fetch(
    area: str = typer.Option("isola", help="isola | navigli | nolo"),
    bbox: str = typer.Option(None, help="south,west,north,east (sovrascrive --area)"),
) -> None:
    """1. Scarica le attività da OpenStreetMap (gratis)."""
    cfg = Settings()
    box = _bbox(area, bbox)
    items = overpass.fetch(box, cfg.overpass_url, cfg.user_agent)
    con = storage.connect(cfg.db_path)
    new = storage.upsert(con, items, area if not bbox else "custom")
    typer.echo(f"{len(items)} attività trovate, {new} nuove.")


@app.command()
def classify() -> None:
    """2. Classifica dai dati OSM + controllo dei siti (gratis, nessuna chiamata Google)."""
    con = storage.connect(Settings().db_path)
    typer.echo(f"{pipeline.classify_all(con)} attività classificate.")


@app.command()
def verify(
    limit: int = typer.Option(50, help="Massimo di attività da verificare in questa run"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Mostra le chiamate previste e basta"),
) -> None:
    """3. Verifica su Google i candidati, entro il tetto mensile di chiamate."""
    cfg = Settings()
    con = storage.connect(cfg.db_path)
    used = storage.google_calls_this_month(con)
    todo = min(limit, len(storage.pending(con, "candidate")))
    typer.echo(f"Candidati da verificare: {todo}. Chiamate Google questo mese: "
               f"{used}/{cfg.google_monthly_call_cap}.")
    if dry_run:
        return
    if not cfg.google_places_api_key:
        raise typer.BadParameter("manca GOOGLE_PLACES_API_KEY nel .env")
    try:
        checked, left = pipeline.verify(con, cfg.google_places_api_key,
                                        cfg.google_monthly_call_cap, limit)
    except BudgetExceeded as e:
        typer.echo(f"Stop: {e}.")
        raise typer.Exit(1) from e
    typer.echo(f"Verificate {checked}; restano {left} candidati.")


@app.command()
def export_xlsx(path: str = typer.Argument("leads.xlsx", help="File Excel di output")) -> None:
    """4. Esporta in Excel con le statistiche della run."""
    counts = export.write(storage.connect(Settings().db_path), path)
    typer.echo(f"Scritto {path}: {dict(counts)}")


@app.command()
def stats() -> None:
    """Conteggi per esito."""
    con = storage.connect(Settings().db_path)
    counts = Counter(r["verdict"] or "non classificato" for r in storage.all_rows(con))
    for k, v in counts.items():
        typer.echo(f"{k}: {v}")
