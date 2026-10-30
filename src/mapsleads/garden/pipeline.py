import geopandas as gpd
import rasterio

from . import classify, lots, vegetation


def run(
    parcels_path: str,
    buildings_path: str,
    ortho_path: str,
    public_green_path: str | None = None,
    chm_path: str | None = None,
    levels_col: str | None = None,
    use_col: str | None = None,
    use_values: list[str] | None = None,
    min_green_m2: float = 30.0,
    green_cfg: vegetation.GreenCfg | None = None,
) -> gpd.GeoDataFrame:
    green_cfg = green_cfg or vegetation.GreenCfg()
    buildings = lots.load(buildings_path)
    if use_col and use_values:
        buildings = buildings[buildings[use_col].isin(use_values)]
    public = lots.load(public_green_path) if public_green_path else None
    found = lots.build_lots(lots.load(parcels_path), buildings, public)
    if levels_col:
        levels = buildings.loc[:, [levels_col, "geometry"]].copy()
        levels["geometry"] = levels.geometry.representative_point()
        top = (gpd.sjoin(levels, found[["parcel_id", "geometry"]], predicate="within")
               .groupby("parcel_id")[levels_col].max())
        found["levels"] = found["parcel_id"].map(top)
    else:
        found["levels"] = None

    with rasterio.open(ortho_path) as ortho:
        chm = rasterio.open(chm_path) if chm_path else None
        try:
            open_geom = found["open_geom"].set_crs(lots.METRIC_CRS).to_crs(ortho.crs)
            stats = [vegetation.green_stats(g, ortho, green_cfg, chm) for g in open_geom]
        finally:
            if chm:
                chm.close()
    found["green_m2"] = [s[0] for s in stats]
    found["tree_m2"] = [s[1] for s in stats]
    found["green_share"] = found["green_m2"] / found["open_m2"]
    found["kind"] = [
        classify.kind(r.n_buildings, r.footprint_m2, r.parcel_m2, r.levels)
        for r in found.itertuples()
    ]
    found["score"] = [
        classify.potential(r.green_m2, r.green_share, r.kind) for r in found.itertuples()
    ]
    found = found[found["green_m2"] >= min_green_m2]
    centre = found.geometry.centroid.to_crs("EPSG:4326")
    found["lat"], found["lon"] = centre.y, centre.x
    return found.sort_values("score", ascending=False).reset_index(drop=True)
