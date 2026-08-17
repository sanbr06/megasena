import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    app_env: str = os.getenv("APP_ENV", "development")
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "5000"))
    api_token: str = os.getenv("API_TOKEN", "")
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///data/lottery.db")
    request_timeout: int = int(os.getenv("REQUEST_TIMEOUT", "15"))


settings = Settings()
