import geopandas as gpd

METRIC_CRS = "EPSG:32632"  # UTM 32N: metri, copre Milano


def load(path: str, layer: str | None = None) -> gpd.GeoDataFrame:
    return gpd.read_file(path, layer=layer).to_crs(METRIC_CRS)


def build_lots(
    parcels: gpd.GeoDataFrame,
    buildings: gpd.GeoDataFrame,
    public_green: gpd.GeoDataFrame | None = None,
) -> gpd.GeoDataFrame:
    """Una riga per particella con almeno un edificio.

    `open_geom` è la parte scoperta: particella meno edifici meno verde pubblico.
    """
    parcels = parcels[["geometry"]].reset_index(drop=True).copy()
    parcels["parcel_id"] = parcels.index

    points = buildings.copy()
    points["geometry"] = points.geometry.representative_point()
    joined = points.sjoin(parcels, how="inner", predicate="within")
    footprints = buildings.geometry.area.loc[joined.index]
    stats = (
        joined.assign(footprint=footprints)
        .groupby("parcel_id")
        .agg(n_buildings=("footprint", "size"), footprint_m2=("footprint", "sum"))
    )
    built = gpd.GeoSeries(
        buildings.loc[joined.index, "geometry"].groupby(joined["parcel_id"]).apply(
            lambda s: s.union_all()
        ),
        crs=buildings.crs,
    )

    lots = parcels.merge(stats, left_on="parcel_id", right_index=True)
    lots["parcel_m2"] = lots.geometry.area
    built_per_lot = gpd.GeoSeries(lots["parcel_id"].map(built), crs=lots.crs)
    lots["open_geom"] = lots.geometry.difference(built_per_lot)
    if public_green is not None and len(public_green):
        lots["open_geom"] = lots["open_geom"].difference(public_green.union_all())
    lots["open_m2"] = lots["open_geom"].area
    return lots[lots["open_m2"] > 0].reset_index(drop=True)
