# project/app/core/config.py
from pathlib import Path
from typing import Any, Dict
import json

from pydantic_settings import BaseSettings, SettingsConfigDict  # v2 style
from pydantic import Field


def _resolve_default_email_config() -> Path:
    """Resolve configs/email.json robustly regardless of where the process is started.
    Current file: project/app/core/config.py
    Repo root: .../vascular_api
    We expect: .../vascular_api/configs/email.json

    :return: Path to configs/email.json
    """
    here = Path(__file__).resolve()
    # parents:
    # 0 = .../project/app/core
    # 1 = .../project/app
    # 2 = .../project
    # 3 = .../vascular_api (repo root)
    repo_root = here.parents[3]
    candidate = repo_root / "configs" / "email.json"
    return candidate


class Settings(BaseSettings):
    SMTP_HOST: str = "mailhost"
    SMTP_PORT: int = 25
    SMTP_STARTTLS: bool = True
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: str | None = None
    EMAIL_FROM: str = ""
    JTDS_JAR_PATH: Path = Field(default_factory=lambda: Path("drivers/jtds-1.2.jar"))
    ISQL_BIN: str = "isql"

    # Use a robust default, but still overrideable by env or .env
    EMAIL_CONFIG_PATH: Path = Field(default_factory=_resolve_default_email_config)

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    # Compatibility: used by main, deps, logging, reports, etc.
    BASE_DIR: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[2])
    PROJECT_NAME: str = "Vascular Document Processing"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    LOG_LEVEL: str = "INFO"
    BACKEND_CORS_ORIGINS: list[str] = ["*"]
    SECRET_KEY: str = "your-super-secret-key-that-should-be-changed"
    ALGORITHM: str = "HS256"
    db_config: Dict[str, Any] = Field(default_factory=dict)
    email_config: Dict[str, Any] = Field(default_factory=dict)


def load_email_matrix(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(
            f"Email matrix not found at: {path}\n"
            "Tip: set EMAIL_CONFIG_PATH env var or fix default resolver,"
        )
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


settings = Settings()
