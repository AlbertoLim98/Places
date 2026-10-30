import typer

app = typer.Typer(no_args_is_help=True, help="Studio 2: giardini privati da dati aperti.")


@app.command()
def analyze(
    parcels: str = typer.Option(..., help="Particelle catastali (senza nomi)"),
    buildings: str = typer.Option(..., help="Edifici (DBT Lombardia / Comune)"),
    ortho: str = typer.Option(..., help="Ortofoto con infrarosso (GeoTIFF RGBI)"),
    public_green: str = typer.Option(None, help="Verde pubblico da escludere"),
    chm: str = typer.Option(None, help="Modello altezza chioma (DSM-DTM) per separare gli alberi"),
    levels_col: str = typer.Option(None, help="Colonna piani/altezza negli edifici"),
    use_col: str = typer.Option(None, help="Colonna destinazione d'uso degli edifici"),
    use_values: str = typer.Option(None, help="Valori residenziali, separati da virgola"),
    red_band: int = typer.Option(1), nir_band: int = typer.Option(4),
    ndvi_min: float = typer.Option(0.2, help="Soglia NDVI per il verde"),
    min_green: float = typer.Option(30.0, help="m² minimi di verde per tenere il lotto"),
    gpkg: str = typer.Option("giardini.gpkg"),
    xlsx: str = typer.Option("giardini.xlsx"),
) -> None:
    """Calcola il verde nei lotti residenziali e scrive la mappa di potenziale."""
    from . import export, pipeline, vegetation

    found = pipeline.run(
        parcels, buildings, ortho, public_green, chm, levels_col, use_col,
        use_values.split(",") if use_values else None, min_green,
        vegetation.GreenCfg(red_band, nir_band, ndvi_min),
    )
    export.write_gpkg(found, gpkg)
    export.write_xlsx(found, xlsx)
    typer.echo(f"{len(found)} lotti ({(found['kind'] == 'villa').sum()} ville). "
               f"Scritti {gpkg} e {xlsx}.")
