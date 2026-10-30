from dataclasses import dataclass

# Verdicts, in the order they are reached by the pipeline.
HAS_SITE = "has_site"  # a working, non-social website
ONLY_SOCIAL = "only_social"  # only a Facebook/Instagram-style page
DEAD_SITE = "dead_site"  # a website is listed but does not answer
CANDIDATE = "candidate"  # no site in OSM: needs Google verification
GUESSED_SITE = "guessed_site"  # no site listed, but a likely domain answers
NO_SITE = "no_site"  # Google confirms there is no website


@dataclass(frozen=True)
class Business:
    osm_id: str
    name: str
    category: str
    address: str
    lat: float
    lon: float
    website: str
    phone: str
