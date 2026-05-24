import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from sqlalchemy.engine import make_url


BACKEND_ROOT = Path(__file__).resolve().parent
APP_ROOT = BACKEND_ROOT.parent
REPO_ROOT = APP_ROOT.parent.parent


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def load_env() -> None:
    _load_env_file(REPO_ROOT / ".env")
    _load_env_file(APP_ROOT / ".env")


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _derive_database_url(base_url: str | None, database_name: str | None) -> str | None:
    if not base_url or not database_name:
        return base_url
    if os.environ.get("FASTBID24_DATABASE_URL"):
        return base_url
    try:
        return make_url(base_url).set(database=database_name).render_as_string(hide_password=False)
    except Exception:
        return base_url


def _derived_bucket_name() -> str:
    explicit = os.environ.get("FASTBID24_S3_BUCKET_NAME")
    if explicit:
        return explicit
    base = os.environ.get("S3_BUCKET_NAME")
    if base:
        suffix = "-fastbid24"
        return base if base.endswith(suffix) else f"{base}{suffix}"
    return "fastbid24-door-analyzer-runs"


@dataclass(frozen=True)
class Settings:
    database_url: str | None
    database_name: str
    aws_access_key_id: str | None
    aws_secret_access_key: str | None
    aws_region: str
    s3_bucket_name: str
    s3_endpoint_url: str | None
    s3_key_prefix: str
    cors_origins: tuple[str, ...]
    session_days: int
    host: str
    port: int
    max_upload_mb: int
    openai_api_key: str | None
    openai_model: str
    allow_global_analysis_key: bool
    secret_key: str | None
    extraction_rate_limit_per_hour: int

    @property
    def database_configured(self) -> bool:
        return bool(self.database_url)

    @property
    def s3_configured(self) -> bool:
        return bool(self.aws_access_key_id and self.aws_secret_access_key and self.s3_bucket_name)

    @property
    def analysis_fallback_configured(self) -> bool:
        return bool(self.allow_global_analysis_key and self.openai_api_key)

    @property
    def secret_configured(self) -> bool:
        return bool(self.secret_key)


def get_settings() -> Settings:
    load_env()
    database_name = os.environ.get("FASTBID24_DATABASE_NAME", "fastbid24_door_analyzer")
    base_database_url = os.environ.get("FASTBID24_DATABASE_URL") or os.environ.get("DATABASE_URL")
    database_url = _derive_database_url(base_database_url, database_name)
    origins = _split_csv(
        os.environ.get(
            "FASTBID24_CORS_ORIGINS",
            "http://127.0.0.1:8503,http://localhost:8503,http://127.0.0.1:5500,http://localhost:5500",
        )
    )
    return Settings(
        database_url=database_url,
        database_name=database_name,
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
        aws_region=os.environ.get("AWS_REGION", "us-east-1"),
        s3_bucket_name=_derived_bucket_name(),
        s3_endpoint_url=os.environ.get("S3_ENDPOINT_URL") or None,
        s3_key_prefix=os.environ.get("FASTBID24_S3_KEY_PREFIX", "fastbid24/door-analyzer"),
        cors_origins=tuple(origins),
        session_days=int(os.environ.get("FASTBID24_SESSION_DAYS", "14")),
        host=os.environ.get("FASTBID24_API_HOST", "127.0.0.1"),
        port=int(os.environ.get("FASTBID24_API_PORT", "8765")),
        max_upload_mb=int(os.environ.get("FASTBID24_MAX_UPLOAD_MB", "100")),
        openai_api_key=os.environ.get("FASTBID24_OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY"),
        openai_model=os.environ.get("FASTBID24_OPENAI_MODEL", "gpt-5.5"),
        allow_global_analysis_key=_env_bool("FASTBID24_ALLOW_GLOBAL_ANALYSIS_KEY", False),
        secret_key=os.environ.get("FASTBID24_SECRET_KEY") or os.environ.get("SECRET_KEY"),
        extraction_rate_limit_per_hour=int(os.environ.get("FASTBID24_EXTRACTION_RATE_LIMIT_PER_HOUR", "12")),
    )


settings = get_settings()


def sanitized_url(url: str | None) -> str:
    if not url:
        return ""
    parsed = make_url(url)
    return str(parsed.set(password="***")) if parsed.password else str(parsed)


def allowed_origin(origin: str | None, configured: Iterable[str] | None = None) -> str | None:
    if not origin:
        return None
    origins = tuple(configured or settings.cors_origins)
    if "*" in origins:
        return origin
    return origin if origin in origins else None
