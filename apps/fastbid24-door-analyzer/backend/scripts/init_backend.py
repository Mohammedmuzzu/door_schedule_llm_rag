import argparse
import re
import sys
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from config import sanitized_url, settings  # noqa: E402
from db import init_db  # noqa: E402
from storage import ensure_bucket  # noqa: E402


def _quote_identifier(name: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,62}", name):
        raise ValueError("FASTBID24_DATABASE_NAME must be a simple Postgres identifier.")
    return f'"{name}"'


def create_database_if_needed() -> None:
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL or FASTBID24_DATABASE_URL is required.")
    url = make_url(settings.database_url)
    database_name = url.database
    if not database_name:
        raise RuntimeError("Database URL must include a database name.")

    maintenance_database = "postgres" if database_name != "postgres" else "template1"
    maintenance_url = url.set(database=maintenance_database)
    engine = create_engine(maintenance_url.render_as_string(hide_password=False), isolation_level="AUTOCOMMIT", future=True)
    with engine.connect() as conn:
        exists = conn.execute(text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": database_name}).scalar()
        if exists:
            print(f"Database exists: {database_name}")
            return
        conn.execute(text(f"CREATE DATABASE {_quote_identifier(database_name)}"))
        print(f"Created database: {database_name}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize FastBid24 backend database and S3 bucket.")
    parser.add_argument(
        "--skip-create-database",
        action="store_true",
        help="Create tables in the configured database without trying CREATE DATABASE first.",
    )
    parser.add_argument("--skip-db", action="store_true", help="Skip all Postgres database work.")
    parser.add_argument("--skip-s3", action="store_true", help="Skip S3 bucket creation/check.")
    args = parser.parse_args()

    print(f"Database URL: {sanitized_url(settings.database_url)}")
    print(f"S3 bucket: {settings.s3_bucket_name}")

    if not args.skip_db:
        if not args.skip_create_database:
            create_database_if_needed()
        init_db()
        print("Database schema is ready.")

    if not args.skip_s3:
        bucket = ensure_bucket()
        print(f"S3 bucket is ready: {bucket}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
