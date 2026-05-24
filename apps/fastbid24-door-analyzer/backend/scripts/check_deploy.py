import sys
from pathlib import Path

from sqlalchemy import text

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

from config import settings
from db import get_engine
from storage import ensure_bucket


def main() -> int:
    print("Checking FastBid24 backend deployment...")
    print(f"Database configured: {settings.database_configured}")
    print(f"S3 configured: {settings.s3_configured}")
    print(f"Secret encryption configured: {settings.secret_configured}")
    print(f"S3 bucket: {settings.s3_bucket_name}")

    with get_engine().connect() as conn:
        current = conn.execute(text("select current_database(), current_user")).fetchone()
        print(f"Postgres connected: database={current[0]} user={current[1]}")

    bucket = ensure_bucket()
    print(f"S3 bucket reachable: {bucket}")
    print("Deploy check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
