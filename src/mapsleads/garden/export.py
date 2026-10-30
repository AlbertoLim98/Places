import geopandas as gpd
from openpyxl import Workbook

COLS = ["parcel_id", "kind", "score", "green_m2", "tree_m2", "green_share", "parcel_m2",
        "footprint_m2", "n_buildings", "lat", "lon"]
HEAD = ["Particella", "Tipo", "Punteggio", "Verde m²", "Chioma m²", "Quota verde",
        "Lotto m²", "Edifici m²", "N. edifici", "Mappa"]


def write_gpkg(found: gpd.GeoDataFrame, path: str) -> None:
    found[[*COLS, "geometry"]].to_file(path, layer="giardini", driver="GPKG")


def write_xlsx(found: gpd.GeoDataFrame, path: str) -> None:
    wb = Workbook()
    wb.remove(wb.active)
    for title, kinds in (("Ville", ("villa",)), ("Condomini e altro", ("condominio", "altro"))):
        ws = wb.create_sheet(title)
        ws.append(HEAD)
        for r in found[found["kind"].isin(kinds)].itertuples():
            maps = f"https://www.google.com/maps/search/?api=1&query={r.lat},{r.lon}"
            ws.append([r.parcel_id, r.kind, r.score, round(r.green_m2), round(r.tree_m2),
                       round(r.green_share, 2), round(r.parcel_m2), round(r.footprint_m2),
                       r.n_buildings, maps])
        ws.freeze_panes = "A2"
    wb.save(path)
