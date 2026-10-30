import requests

from .domain import Business

# Approximate boxes (south, west, north, east). Adjust or pass --bbox.
AREAS: dict[str, tuple[float, float, float, float]] = {
    "isola": (45.484, 9.185, 45.495, 9.198),
    "navigli": (45.445, 9.165, 45.456, 9.190),
    "nolo": (45.495, 9.205, 45.512, 9.235),
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


def fetch(
    bbox: tuple[float, float, float, float],
    url: str,
    user_agent: str,
    session: requests.Session | None = None,
) -> list[Business]:
    s = session or requests.Session()
    resp = s.post(
        url, data={"data": build_query(bbox)}, headers={"User-Agent": user_agent}, timeout=120
    )
    resp.raise_for_status()
    return parse(resp.json().get("elements", []))
