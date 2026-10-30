import pytest

pytest.importorskip("geopandas")
pytest.importorskip("rasterio")

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.transform import from_origin
from shapely.geometry import box
from typer.testing import CliRunner

from mapsleads.cli import app
from mapsleads.garden import classify, lots, pipeline, vegetation

X0, Y0 = 500000.0, 5035000.0  # in UTM 32N, zona di Milano


def _gdf(geoms, **cols):
    return gpd.GeoDataFrame(cols, geometry=geoms, crs=lots.METRIC_CRS)


@pytest.fixture
def data(tmp_path):
    # Lotto A: villino 10x10 in 30x30, tutto il resto verde. Lotto B: condominio 40x20 in 50x30.
    parcels = _gdf([box(X0, Y0, X0 + 30, Y0 + 30), box(X0 + 40, Y0, X0 + 90, Y0 + 30)])
    blds = _gdf([box(X0 + 10, Y0 + 10, X0 + 20, Y0 + 20), box(X0 + 45, Y0 + 5, X0 + 85, Y0 + 25)])
    park = _gdf([box(X0 + 40, Y0, X0 + 90, Y0 + 5)])  # striscia di verde pubblico nel lotto B
    # Ortofoto 1 m/pixel, 4 bande R,G,B,NIR: verde ovunque tranne il lotto B oltre y>5 (asfalto)
    h, w = 40, 100
    arr = np.zeros((4, h, w), dtype="uint8")
    arr[0], arr[3] = 40, 200  # rosso basso, NIR alto => NDVI ~0.67
    path = tmp_path / "ortho.tif"
    with rasterio.open(path, "w", driver="GTiff", height=h, width=w, count=4, dtype="uint8",
                       crs=lots.METRIC_CRS, transform=from_origin(X0, Y0 + h, 1, 1)) as dst:
        dst.write(arr)
    for name, g in (("parcels", parcels), ("blds", blds), ("park", park)):
        g.to_file(tmp_path / f"{name}.gpkg", driver="GPKG")
    return tmp_path


def test_ndvi_and_kinds():
    assert vegetation.ndvi(np.array([40]), np.array([200]))[0] == pytest.approx(0.667, abs=1e-2)
    assert classify.kind(1, 100, 900, None) == classify.VILLA
    assert classify.kind(1, 800, 900, None) == classify.CONDO
    assert classify.kind(1, 100, 900, 5) == classify.CONDO
    assert classify.kind(4, 300, 900, None) == classify.OTHER
    assert classify.potential(200, 1.0, classify.VILLA) == 100


def test_open_area_excludes_buildings_and_public_green(data):
    found = lots.build_lots(
        lots.load(str(data / "parcels.gpkg")),
        lots.load(str(data / "blds.gpkg")),
        lots.load(str(data / "park.gpkg")),
    )
    a, b = found.sort_values("parcel_id").itertuples()
    assert a.open_m2 == pytest.approx(900 - 100)
    assert b.open_m2 == pytest.approx(1500 - 800 - 250)  # meno edificio e verde pubblico


def test_pipeline_ranks_villa_first(data):
    found = pipeline.run(str(data / "parcels.gpkg"), str(data / "blds.gpkg"),
                         str(data / "ortho.tif"), str(data / "park.gpkg"))
    assert list(found["kind"]) == ["villa", "condominio"]
    assert found.loc[0, "green_m2"] == pytest.approx(800, abs=5)
    assert found.loc[0, "score"] > found.loc[1, "score"]
    assert 45.0 < found.loc[0, "lat"] < 45.9


def test_cli_writes_outputs(data):
    out = data / "o"
    out.mkdir()
    res = CliRunner().invoke(app, [
        "garden", "analyze", "--parcels", str(data / "parcels.gpkg"),
        "--buildings", str(data / "blds.gpkg"), "--ortho", str(data / "ortho.tif"),
        "--gpkg", str(out / "g.gpkg"), "--xlsx", str(out / "g.xlsx")])
    assert res.exit_code == 0, res.output
    assert (out / "g.gpkg").exists() and (out / "g.xlsx").exists()
