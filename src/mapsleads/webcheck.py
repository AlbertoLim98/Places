import re
import unicodedata
from urllib.parse import urlparse

import requests

from .domain import DEAD_SITE, HAS_SITE, ONLY_SOCIAL

SOCIAL_DOMAINS = (
    "facebook.com", "fb.com", "instagram.com", "linktr.ee", "tiktok.com", "twitter.com",
    "x.com", "linkedin.com", "youtube.com", "wa.me", "whatsapp.com", "google.com",
    "business.site", "paginegialle.it", "tripadvisor.it", "tripadvisor.com", "thefork.it",
)


def host(url: str) -> str:
    if "://" not in url:
        url = "http://" + url
    return (urlparse(url).hostname or "").lower().removeprefix("www.")


def is_social(url: str) -> bool:
    h = host(url)
    return any(h == d or h.endswith("." + d) for d in SOCIAL_DOMAINS)


def is_alive(url: str, session: requests.Session | None = None, timeout: float = 8.0) -> bool:
    s = session or requests.Session()
    if "://" not in url:
        url = "http://" + url
    try:
        r = s.get(url, timeout=timeout, allow_redirects=True, stream=True,
                  headers={"User-Agent": "Mozilla/5.0 (mapsleads prototype)"})
        r.close()
    except requests.RequestException:
        return False
    return r.status_code < 400 or r.status_code in (401, 403, 429)


def classify_url(url: str, session: requests.Session | None = None) -> str:
    """Verdict for a website listed on the business itself."""
    if is_social(url):
        return ONLY_SOCIAL
    return HAS_SITE if is_alive(url, session) else DEAD_SITE


def slug(name: str) -> str:
    text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]", "", text)


def guess_domains(name: str) -> list[str]:
    s = slug(name)
    if len(s) < 5:  # too short to be a meaningful domain guess
        return []
    return [f"{s}.it", f"{s}.com"]


def guess_site(name: str, session: requests.Session | None = None) -> str:
    """A likely own-domain that answers, or ''. Weak signal: reported as a guess only."""
    for d in guess_domains(name):
        if is_alive(d, session, timeout=5.0):
            return d
    return ""
