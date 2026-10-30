import sqlite3
from collections.abc import Callable

import requests

from . import google_places, storage, webcheck
from .domain import CANDIDATE, GUESSED_SITE, NO_SITE, ONLY_SOCIAL, Business


def classify_all(con: sqlite3.Connection, session: requests.Session | None = None) -> int:
    """Free step: judge each business from what OSM lists, no Google calls."""
    rows = storage.pending(con, None)
    for r in rows:
        if r["website"]:
            storage.set_verdict(con, r["osm_id"], webcheck.classify_url(r["website"], session),
                                r["website"])
            continue
        guess = webcheck.guess_site(r["name"], session)
        if guess:
            storage.set_verdict(con, r["osm_id"], GUESSED_SITE, guess)
        else:
            storage.set_verdict(con, r["osm_id"], CANDIDATE)
    return len(rows)


def _business(r: sqlite3.Row) -> Business:
    return Business(r["osm_id"], r["name"], r["category"], r["address"], r["lat"], r["lon"],
                    r["website"], r["phone"])


def verify(
    con: sqlite3.Connection,
    api_key: str,
    monthly_cap: int,
    limit: int,
    lookup: Callable[..., google_places.GoogleMatch | None] = google_places.lookup,
    session: requests.Session | None = None,
) -> tuple[int, int]:
    """Google check of candidates, stopping at the monthly cap. Returns (checked, remaining)."""
    checked = 0
    for r in storage.pending(con, CANDIDATE, limit):
        if storage.google_calls_this_month(con) >= monthly_cap:
            raise google_places.BudgetExceeded(f"monthly cap of {monthly_cap} calls reached")
        match = lookup(_business(r), api_key, session)
        storage.count_google_call(con)
        checked += 1
        if match is None:
            continue  # no reliable match: leave as candidate, not confirmed
        if not match.website:
            storage.set_verdict(con, r["osm_id"], NO_SITE, "", match.place_id)
        elif webcheck.is_social(match.website):
            storage.set_verdict(con, r["osm_id"], ONLY_SOCIAL, match.website, match.place_id)
        else:
            verdict = webcheck.classify_url(match.website, session)
            storage.set_verdict(con, r["osm_id"], verdict, match.website, match.place_id)
    return checked, len(storage.pending(con, CANDIDATE))
