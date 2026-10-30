import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from mapsleads import export, google_places, overpass, pipeline, storage, webcheck
from mapsleads.domain import CANDIDATE, GUESSED_SITE, NO_SITE, ONLY_SOCIAL, Business

ELEMENTS = [
    {"type": "node", "id": 1, "lat": 45.49, "lon": 9.19,
     "tags": {"name": "Bar Rosa", "amenity": "bar", "addr:street": "Via Prova",
              "addr:housenumber": "3"}},
    {"type": "way", "id": 2, "center": {"lat": 45.49, "lon": 9.19},
     "tags": {"name": "Idraulico Verdi", "craft": "plumber", "website": "https://verdi.it"}},
    {"type": "node", "id": 3, "lat": 45.49, "lon": 9.19,
     "tags": {"name": "Panchina", "amenity": "bench"}},
    {"type": "node", "id": 4, "lat": 45.49, "lon": 9.19,
     "tags": {"name": "Salone Bella", "shop": "hairdresser",
              "contact:facebook": "https://facebook.com/salone"}},
]


def test_parse_filters_and_fields():
    items = overpass.parse(ELEMENTS)
    assert [b.name for b in items] == ["Bar Rosa", "Idraulico Verdi", "Salone Bella"]
    assert items[0].address == "Via Prova 3"
    assert items[1].osm_id == "way/2" and items[1].website == "https://verdi.it"
    assert webcheck.is_social(items[2].website)


def test_social_and_slug():
    assert webcheck.is_social("https://www.facebook.com/x")
    assert webcheck.is_social("instagram.com/x")
    assert not webcheck.is_social("https://facebook.com.evil.it")
    assert webcheck.slug("Caffè Dell'Angolo!") == "caffedellangolo"
    assert webcheck.guess_domains("Bar") == []


class FakeSession:
    def __init__(self, alive):
        self.alive = alive

    def get(self, url, **kw):
        status = 200 if any(a in url for a in self.alive) else 500
        return SimpleNamespace(status_code=status, close=lambda: None)


@pytest.fixture
def con():
    d = tempfile.mkdtemp()
    return storage.connect(str(Path(d) / "t.db"))


def test_classify_pipeline(con):
    storage.upsert(con, overpass.parse(ELEMENTS), "t")
    assert storage.upsert(con, overpass.parse(ELEMENTS), "t") == 0  # idempotent
    pipeline.classify_all(con, FakeSession(alive=["verdi.it", "salonebella.it"]))
    v = {r["name"]: r["verdict"] for r in storage.all_rows(con)}
    assert v["Idraulico Verdi"] == "has_site"
    assert v["Salone Bella"] == ONLY_SOCIAL
    assert v["Bar Rosa"] == CANDIDATE


def test_guess(con):
    storage.upsert(con, [Business("node/9", "Pizzeria Napoli", "amenity=restaurant", "", 45.4,
                                  9.1, "", "")], "t")
    pipeline.classify_all(con, FakeSession(alive=["pizzerianapoli.it"]))
    assert next(storage.all_rows(con))["verdict"] == GUESSED_SITE


def _place(name, lat, lon, site=""):
    p = {"id": "pid", "displayName": {"text": name},
         "location": {"latitude": lat, "longitude": lon}}
    if site:
        p["websiteUri"] = site
    return p


def test_pick_match():
    b = Business("node/1", "Bar Rosa", "", "", 45.49, 9.19, "", "")
    assert google_places.pick_match(b, [_place("Bar Rosa", 45.4901, 9.19, "http://x.it")]).website
    assert google_places.pick_match(b, [_place("Altro Locale", 45.49, 9.19)]) is None
    assert google_places.pick_match(b, [_place("Bar Rosa", 45.60, 9.19)]) is None  # too far


def test_verify_and_budget(con):
    storage.upsert(con, overpass.parse(ELEMENTS)[:1], "t")
    storage.upsert(con, [Business("node/7", "Altra Cosa", "", "", 45.4, 9.1, "", "")], "t")
    pipeline.classify_all(con, FakeSession(alive=[]))
    calls = []

    def fake(biz, key, session):
        calls.append(biz.name)
        return google_places.GoogleMatch("pid", "")

    checked, left = pipeline.verify(con, "k", monthly_cap=5, limit=10, lookup=fake)
    assert checked == 2 and left == 0
    assert {r["verdict"] for r in storage.all_rows(con)} == {NO_SITE}
    storage.upsert(con, [Business("node/8", "Terza Cosa", "", "", 45.4, 9.1, "", "")], "t")
    pipeline.classify_all(con, FakeSession(alive=[]))
    with pytest.raises(google_places.BudgetExceeded):
        pipeline.verify(con, "k", monthly_cap=2, limit=10, lookup=fake)


def test_export(con, tmp_path):
    storage.upsert(con, overpass.parse(ELEMENTS), "t")
    pipeline.classify_all(con, FakeSession(alive=["verdi.it"]))
    counts = export.write(con, str(tmp_path / "o.xlsx"))
    assert sum(counts.values()) == 3 and (tmp_path / "o.xlsx").exists()


def test_cli_export_takes_positional_path(tmp_path, monkeypatch):
    from typer.testing import CliRunner

    from mapsleads.cli import app

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DB_PATH", str(tmp_path / "t.db"))
    out = tmp_path / "x.xlsx"
    result = CliRunner().invoke(app, ["export-xlsx", str(out)])
    assert result.exit_code == 0, result.output
    assert out.exists()
