from dataclasses import dataclass

VILLA, CONDO, OTHER = "villa", "condominio", "altro"


@dataclass(frozen=True)
class KindCfg:
    villa_max_buildings: int = 2
    villa_max_footprint_m2: float = 400.0
    villa_max_parcel_m2: float = 3000.0
    condo_min_footprint_m2: float = 600.0
    condo_min_levels: int = 4


DEFAULT_KIND = KindCfg()


def kind(n_buildings: int, footprint_m2: float, parcel_m2: float, levels: float | None,
         cfg: KindCfg = DEFAULT_KIND) -> str:
    """Villa/villino (giardino privato) contro condominio (verde condiviso)."""
    if footprint_m2 >= cfg.condo_min_footprint_m2 or (levels or 0) >= cfg.condo_min_levels:
        return CONDO
    if (n_buildings <= cfg.villa_max_buildings and footprint_m2 <= cfg.villa_max_footprint_m2
            and parcel_m2 <= cfg.villa_max_parcel_m2):
        return VILLA
    return OTHER


def potential(green_m2: float, green_share: float, lot_kind: str) -> int:
    """Punteggio grezzo 0-100, da calibrare sul pilota: m² di verde, quota, tipologia."""
    base = 60 * min(green_m2 / 200, 1) + 25 * min(green_share, 1)
    return round(base + (15 if lot_kind == VILLA else 0))
