import difflib
import math
from dataclasses import dataclass

import requests

from .domain import Business

URL = "https://places.googleapis.com/v1/places:searchText"
FIELD_MASK = "places.id,places.displayName,places.websiteUri,places.location"


class BudgetExceeded(Exception):
    pass


@dataclass(frozen=True)
class GoogleMatch:
    place_id: str
    website: str


def _distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    dy = (lat2 - lat1) * 111_320
    dx = (lon2 - lon1) * 111_320 * math.cos(math.radians((lat1 + lat2) / 2))
    return math.hypot(dx, dy)


def pick_match(biz: Business, places: list[dict]) -> GoogleMatch | None:
    """Same business = similar name and within 150 m of the OSM point."""
    best: tuple[float, dict] | None = None
    for p in places:
        loc = p.get("location", {})
        name = p.get("displayName", {}).get("text", "")
        ratio = difflib.SequenceMatcher(None, biz.name.lower(), name.lower()).ratio()
        dist = _distance_m(biz.lat, biz.lon, loc.get("latitude", 0), loc.get("longitude", 0))
        close = dist <= 150
        if ratio >= 0.6 and close and (best is None or ratio > best[0]):
            best = (ratio, p)
    if best is None:
        return None
    return GoogleMatch(place_id=best[1]["id"], website=best[1].get("websiteUri", ""))


def lookup(
    biz: Business, api_key: str, session: requests.Session | None = None
) -> GoogleMatch | None:
    """One Text Search call (Enterprise tier because websiteUri is requested)."""
    s = session or requests.Session()
    body = {
        "textQuery": f"{biz.name} {biz.address}".strip(),
        "pageSize": 5,
        "locationBias": {
            "circle": {"center": {"latitude": biz.lat, "longitude": biz.lon}, "radius": 150.0}
        },
    }
    r = s.post(
        URL,
        json=body,
        headers={"X-Goog-Api-Key": api_key, "X-Goog-FieldMask": FIELD_MASK},
        timeout=30,
    )
    r.raise_for_status()
    return pick_match(biz, r.json().get("places", []))
