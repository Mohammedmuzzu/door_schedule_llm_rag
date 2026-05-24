# FastBid24 Door Analyzer Backend

Flask API for the FastBid24 browser app. It adds authentication, roles, Postgres-backed PDF run history, admin visibility, encrypted per-user analysis keys, and S3 PDF storage.

## Secure Extraction

- Admins assign analysis keys to user accounts from the Admin screen. Keys are encrypted at rest and are never returned to the browser after saving.
- `FASTBID24_OPENAI_API_KEY` or `OPENAI_API_KEY` can be enabled as a temporary server-side fallback only when `FASTBID24_ALLOW_GLOBAL_ANALYSIS_KEY=true`.
- The browser uploads PDFs to `POST /api/v1/extract` with a logged-in bearer token.
- Extraction prompts and provider calls run on Render, not in the Cloud Pages frontend.
- The backend stores completed analysis results and original PDFs after a run finishes.

## API Shape

- `POST /api/v1/auth/bootstrap` - create the first admin when no users exist.
- `POST /api/v1/auth/login` - login and receive a bearer token.
- `POST /api/v1/auth/logout` - revoke the current token.
- `GET /api/v1/me` - current user profile.
- `GET /api/v1/runs` - current user's PDF runs.
- `POST /api/v1/runs` - upload a completed PDF analysis, original PDF, and run logs.
- `GET /api/v1/runs/<id>` - run detail for the owner or an admin.
- `GET /api/v1/runs/<id>/logs` - run logs for the owner or an admin.
- `GET /api/v1/admin/users` - admin user list.
- `POST /api/v1/admin/users` - admin user creation.
- `PATCH /api/v1/admin/users/<id>` - admin user role/status updates.
- `GET /api/v1/admin/runs` - admin run list across users.
- `GET /api/v1/admin/logs` - admin log list across users/runs.

## Environment

The backend reads `.env` from the repo root first, then this app folder if present.

Required for production:

```text
DATABASE_URL=postgresql+psycopg2://...
FASTBID24_SECRET_KEY=<long random secret used to encrypt assigned keys>
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=...
S3_BUCKET_NAME=...
```

Optional FastBid-specific overrides:

```text
FASTBID24_DATABASE_NAME=fastbid24_door_analyzer
FASTBID24_DATABASE_URL=postgresql+psycopg2://...
FASTBID24_S3_BUCKET_NAME=your-fastbid24-bucket
FASTBID24_CORS_ORIGINS=http://127.0.0.1:8503,http://localhost:8503
FASTBID24_SESSION_DAYS=14
FASTBID24_ALLOW_GLOBAL_ANALYSIS_KEY=false
FASTBID24_OPENAI_API_KEY=<optional server fallback analysis key>
FASTBID24_OPENAI_MODEL=gpt-5.5
FASTBID24_EXTRACTION_RATE_LIMIT_PER_HOUR=12
```

If `FASTBID24_DATABASE_URL` is not set, the backend derives a new database URL from `DATABASE_URL` using `FASTBID24_DATABASE_NAME`.

## Initialize Database And S3

From the repo root:

```powershell
& "c:\Users\muzaf\my_lab\computervision\Scripts\python.exe" apps\fastbid24-door-analyzer\backend\scripts\init_backend.py
```

This creates the FastBid database if the Postgres account can create databases, creates/updates the schema, and ensures the configured S3 bucket exists.

## Run

```powershell
.\apps\fastbid24-door-analyzer\backend\run.ps1
```

The local API listens on:

```text
http://127.0.0.1:8765/api/v1
```
