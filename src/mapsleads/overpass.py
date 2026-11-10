import time
from collections.abc import Callable

import requests

from .domain import Business

# Approximate boxes (south, west, north, east). Adjust or pass --bbox.
AREAS: dict[str, tuple[float, float, float, float]] = {
    "isola": (45.484, 9.185, 45.495, 9.198),
    "navigli": (45.445, 9.165, 45.456, 9.190),
    "nolo": (45.495, 9.205, 45.512, 9.235),
    "affori": (45.508, 9.150, 45.528, 9.182),
}

# Categories worth contacting; anything else tagged amenity/shop (benches, ATMs…) is skipped.
AMENITIES = {
    "restaurant", "cafe", "bar", "pub", "fast_food", "ice_cream", "dentist", "doctors",
    "pharmacy", "veterinary", "driving_school", "car_wash", "car_rental", "bicycle_rental",
}
KEYS = ("shop", "craft", "office", "amenity")


def build_query(bbox: tuple[float, float, float, float]) -> str:
    s, w, n, e = bbox
    box = f"{s},{w},{n},{e}"
    parts = "".join(f'nwr["{k}"]["name"]({box});' for k in KEYS)
    return f"[out:json][timeout:90];({parts});out center tags;"


def _address(tags: dict[str, str]) -> str:
    street = " ".join(x for x in (tags.get("addr:street"), tags.get("addr:housenumber")) if x)
    city = " ".join(x for x in (tags.get("addr:postcode"), tags.get("addr:city")) if x)
    return ", ".join(x for x in (street, city) if x)


def parse(elements: list[dict]) -> list[Business]:
    out: list[Business] = []
    for el in elements:
        tags = el.get("tags", {})
        name = tags.get("name")
        if not name:
            continue
        category = next((f"{k}={tags[k]}" for k in KEYS if k in tags), "")
        if category.startswith("amenity=") and tags["amenity"] not in AMENITIES:
            continue
        pos = el if "lat" in el else el.get("center")
        if not pos:
            continue
        website = tags.get("website") or tags.get("contact:website") or tags.get("url") or ""
        if not website:
            website = tags.get("contact:facebook") or tags.get("contact:instagram") or ""
        out.append(
            Business(
                osm_id=f"{el['type']}/{el['id']}",
                name=name,
                category=category,
                address=_address(tags),
                lat=float(pos["lat"]),
                lon=float(pos["lon"]),
                website=website,
                phone=tags.get("phone") or tags.get("contact:phone") or "",
            )
        )
    return out


# Public mirrors tried after the configured URL when a server is overloaded.
MIRRORS = (
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
)
RETRY_STATUS = {429, 502, 503, 504}


class OverpassUnavailable(Exception):
    pass


def fetch(
    bbox: tuple[float, float, float, float],
    url: str,
    user_agent: str,
    session: requests.Session | None = None,
    rounds: int = 3,
    sleep: Callable[[float], None] = time.sleep,
) -> list[Business]:
    """POST the query, retrying overloaded servers (429/5xx) and falling back to mirrors."""
    s = session or requests.Session()
    urls = [url, *(m for m in MIRRORS if m != url)]
    data = {"data": build_query(bbox)}
    last = ""
    for attempt in range(rounds):
        for u in urls:
            try:
                resp = s.post(u, data=data, headers={"User-Agent": user_agent}, timeout=120)
            except (requests.ConnectionError, requests.Timeout) as e:
                last = f"{u}: {e.__class__.__name__}"
                continue
            if resp.status_code in RETRY_STATUS:
                last = f"{u}: HTTP {resp.status_code}"
                continue
            resp.raise_for_status()
            return parse(resp.json().get("elements", []))
        if attempt < rounds - 1:
            sleep(10 * (attempt + 1))
    raise OverpassUnavailable(f"tutti i server Overpass sono occupati, riprova tra poco ({last})")
