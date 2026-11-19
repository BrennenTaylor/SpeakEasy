from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_", env_file=".env", extra="ignore")

    app_name: str = "Calorie Tracker API"
    environment: str = "development"
    database_url: str = "sqlite:///./data/app.db"
    sql_echo: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
