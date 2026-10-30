import sqlite3
from collections.abc import Iterator
from datetime import UTC, datetime

from .domain import Business

SCHEMA = """
CREATE TABLE IF NOT EXISTS businesses (
    osm_id TEXT PRIMARY KEY, name TEXT, category TEXT, address TEXT,
    lat REAL, lon REAL, website TEXT, phone TEXT, area TEXT,
    verdict TEXT, detail TEXT, google_place_id TEXT, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS google_calls (month TEXT PRIMARY KEY, n INTEGER NOT NULL);
"""


def connect(path: str) -> sqlite3.Connection:
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def upsert(con: sqlite3.Connection, items: list[Business], area: str) -> int:
    """Insert new businesses; keep verdicts of rows already seen. Returns number of new rows."""
    new = 0
    for b in items:
        cur = con.execute(
            "INSERT OR IGNORE INTO businesses "
            "(osm_id,name,category,address,lat,lon,website,phone,area,updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (b.osm_id, b.name, b.category, b.address, b.lat, b.lon, b.website, b.phone, area,
             _now()),
        )
        new += cur.rowcount
    con.commit()
    return new


def pending(
    con: sqlite3.Connection, verdict: str | None, limit: int | None = None
) -> list[sqlite3.Row]:
    sql = "SELECT * FROM businesses WHERE verdict IS ? ORDER BY name"
    if limit:
        sql += f" LIMIT {int(limit)}"
    return con.execute(sql, (verdict,)).fetchall()


def set_verdict(
    con: sqlite3.Connection, osm_id: str, verdict: str, detail: str = "", place_id: str = ""
) -> None:
    con.execute(
        "UPDATE businesses SET verdict=?, detail=?, google_place_id=?, updated_at=? "
        "WHERE osm_id=?",
        (verdict, detail, place_id or None, _now(), osm_id),
    )
    con.commit()


def month_key() -> str:
    return datetime.now(UTC).strftime("%Y-%m")


def google_calls_this_month(con: sqlite3.Connection) -> int:
    row = con.execute("SELECT n FROM google_calls WHERE month=?", (month_key(),)).fetchone()
    return row["n"] if row else 0


def count_google_call(con: sqlite3.Connection) -> None:
    con.execute(
        "INSERT INTO google_calls(month,n) VALUES(?,1) "
        "ON CONFLICT(month) DO UPDATE SET n=n+1",
        (month_key(),),
    )
    con.commit()


def all_rows(con: sqlite3.Connection) -> Iterator[sqlite3.Row]:
    yield from con.execute("SELECT * FROM businesses ORDER BY name")
