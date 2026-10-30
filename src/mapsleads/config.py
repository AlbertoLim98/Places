from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    google_places_api_key: str = ""
    google_monthly_call_cap: int = 900
    db_path: str = "mapsleads.db"
    overpass_url: str = "https://overpass-api.de/api/interpreter"
    user_agent: str = "mapsleads-prototype/0.1"
