import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Settings:
    app_name: str = os.getenv("APP_NAME", "bridge-ai-interface")
    app_env: str = os.getenv("APP_ENV", "development")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    sfdc_client_id: str | None = os.getenv("SFDC_CLIENT_ID")
    sfdc_client_secret: str | None = os.getenv("SFDC_CLIENT_SECRET")
    sfdc_username: str | None = os.getenv("SFDC_USERNAME")
    sfdc_password: str | None = os.getenv("SFDC_PASSWORD")
    sfdc_token: str | None = os.getenv("SFDC_TOKEN")
    sfdc_instance_url: str | None = os.getenv("SFDC_INSTANCE_URL")

    sansan_api_base_url: str | None = os.getenv("SANSAN_API_BASE_URL")
    sansan_api_key: str | None = os.getenv("SANSAN_API_KEY")

    internal_api_base_url: str | None = os.getenv("INTERNAL_API_BASE_URL")
    internal_api_key: str | None = os.getenv("INTERNAL_API_KEY")


settings = Settings()
