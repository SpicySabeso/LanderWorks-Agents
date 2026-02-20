from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

SESSION_TTL_HOURS = 12


class Settings(BaseSettings):
    OPENAI_API_KEY: str = Field(default="")
    MODEL: str = "gpt-4o-mini"
    EMBED_MODEL: str = "text-embedding-3-small"

    SHEETS_WEBHOOK_URL: str = Field(default="")
    SHEETS_WEBHOOK_SECRET: str = Field(default="")

    DB_PATH: str = Field(default="backend/data/leads.db")

    # opcional: si validas requests de Twilio
    TWILIO_AUTH_TOKEN: str = Field(default="")
    TWILIO_VALIDATE_SIGNATURE: bool = Field(default=True)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    NOTIFY_EMAIL_TO: str = Field(default="")
    NOTIFY_EMAIL_SUBJECT: str = Field(default="[Dental Agent] Nuevo Lead")

    # Email via HTTP (Resend)
    RESEND_API_KEY: str = Field(default="")
    EMAIL_FROM: str = Field(default="")  # ej: "Dental Agent <onboarding@resend.dev>"


settings = Settings()
