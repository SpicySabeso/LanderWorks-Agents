from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

SESSION_TTL_HOURS = 12


class Settings(BaseSettings):
    OPENAI_API_KEY: str = Field(default="")
    MODEL: str = "gpt-4o-mini"
    EMBED_MODEL: str = "text-embedding-3-small"

    DB_PATH: str = Field(default="backend/data/leads.db")

    # opcional: si validas requests de Twilio
    TWILIO_AUTH_TOKEN: str = Field(default="")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
