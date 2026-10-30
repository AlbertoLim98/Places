from dataclasses import dataclass

import numpy as np
import rasterio
from rasterio.mask import mask
from shapely.geometry import mapping

EPS = 1e-9


def ndvi(red: np.ndarray, nir: np.ndarray) -> np.ndarray:
    red = red.astype("float32")
    nir = nir.astype("float32")
    return (nir - red) / (nir + red + EPS)


@dataclass(frozen=True)
class GreenCfg:
    red_band: int = 1  # indici 1-based; l'ortofoto RGBI di solito è R,G,B,NIR
    nir_band: int = 4
    ndvi_min: float = 0.2
    tree_height_min: float = 3.0  # metri, solo se c'è un modello di altezza (CHM)


def _clip(src: rasterio.DatasetReader, geom, bands: list[int]):
    try:
        data, _ = mask(src, [mapping(geom)], crop=True, indexes=bands, filled=False)
    except ValueError:  # geometria fuori dal raster o più piccola di un pixel
        return None
    return data


def green_stats(
    geom, ortho: rasterio.DatasetReader, cfg: GreenCfg, chm=None
) -> tuple[float, float]:
    """(m² di verde, m² di chioma) dentro `geom`, che deve essere nel CRS del raster."""
    data = _clip(ortho, geom, [cfg.red_band, cfg.nir_band])
    if data is None:
        return 0.0, 0.0
    inside = ~np.ma.getmaskarray(data[0])
    green = (ndvi(data[0].filled(0), data[1].filled(0)) >= cfg.ndvi_min) & inside
    pixel_m2 = abs(ortho.transform.a * ortho.transform.e)
    tree_px = 0
    if chm is not None:
        height = _clip(chm, geom, [1])
        if height is not None and height.shape[1:] == green.shape:
            tree_px = int(((height[0].filled(0) >= cfg.tree_height_min) & green).sum())
    return float(green.sum() * pixel_m2), float(tree_px * pixel_m2)
