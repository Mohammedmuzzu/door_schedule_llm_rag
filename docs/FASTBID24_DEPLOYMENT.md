# FastBid24 Deployment Runbook

Recommended stack:

- Frontend: Cloudflare Pages
- Backend: Coolify on an Oracle Cloud Always Free VM
- Database: Supabase Postgres
- PDF storage: current S3 bucket or Cloudflare R2 later

## 1. Prepare Backend Environment

Use the same values that already work locally, but set them in Coolify as environment variables.

Required:

```text
DATABASE_URL=postgresql://...
FASTBID24_DATABASE_NAME=fastbid24_door_analyzer
FASTBID24_SECRET_KEY=<long random secret used to encrypt assigned user keys>
FASTBID24_ALLOW_GLOBAL_ANALYSIS_KEY=false
FASTBID24_OPENAI_API_KEY=<optional server fallback analysis key>
FASTBID24_OPENAI_MODEL=gpt-5.5
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=...
S3_BUCKET_NAME=door-schedules-fastbid24
FASTBID24_S3_BUCKET_NAME=door-schedules-fastbid24
FASTBID24_CORS_ORIGINS=https://your-cloudflare-pages-domain.pages.dev,https://your-custom-domain.com
FASTBID24_EXTRACTION_RATE_LIMIT_PER_HOUR=12
```

After you know the final API domain, set:

```text
FASTBID24_CORS_ORIGINS=https://your-frontend-domain.com
```

## 2. Create Oracle Always Free VM

Create an Ubuntu VM in Oracle Cloud. Prefer Ampere A1 if available.

Open inbound ports:

```text
22    SSH
80    HTTP
443   HTTPS
8000  Coolify dashboard during setup only
```

Oracle Always Free can provide up to 4 ARM OCPUs and 24 GB RAM within Always Free limits, depending on regional capacity.

## 3. Install Coolify

SSH into the VM, then run the official installer:

```bash
curl -fsSL https://cdn.coollabs.io/coolify/install.sh | sudo bash
```

Open the Coolify URL shown by the installer and immediately create the Coolify admin account.

## 4. Deploy Backend In Coolify

In Coolify:

1. Create a new project.
2. Add a new resource from GitHub.
3. Select this repository.
4. Choose Docker Compose deployment.
5. Compose file path:

```text
apps/fastbid24-door-analyzer/compose.coolify.yml
```

6. Set the environment variables from step 1.
7. Set exposed port/container port to:

```text
8765
```

8. Assign a domain like:

```text
https://api.your-domain.com
```

9. Deploy.

Check:

```text
https://api.your-domain.com/api/v1/health
```

Expected:

```json
{"ok": true}
```

## 5. Initialize Database And S3 On The Server

In Coolify, open a terminal for the backend container and run:

```bash
python scripts/init_backend.py
python scripts/check_deploy.py
```

This creates/updates the Postgres schema and confirms S3 access.

## 6. Configure Frontend API URL

Before deploying the frontend, edit:

```text
apps/fastbid24-door-analyzer/config.js
```

Change:

```text
https://api.your-domain.com/api/v1
```

to your real backend API domain.

## 7. Deploy Frontend To Cloudflare Pages

In Cloudflare Pages:

1. Create a new Pages project from GitHub.
2. Select this repository.
3. Set:

```text
Build command: empty
Build output directory: apps/fastbid24-door-analyzer
Root directory: empty or repository root
```

4. Deploy.
5. Open the Pages URL.
6. Use First-time setup to create the first FastBid24 admin account.

## 8. Production Checklist

- Backend health URL returns `ok: true`.
- Backend health reports `secret_configured: true`.
- Frontend `config.js` points to the real backend API URL.
- `FASTBID24_CORS_ORIGINS` contains only the frontend domain.
- Cloud Pages frontend does not contain provider keys, direct provider calls, or prompt bodies.
- First admin account is created.
- Test normal user creation from Admin.
- Assign an analysis key to the normal user from Admin.
- Test one PDF run from a normal user.
- Confirm the PDF appears in S3.
- Confirm the run appears in Admin.
- Confirm normal user can only see their own runs.

## Render Backend Alternative

Render is easier than managing an Oracle VM. It is not open-source/self-hosted, but it is a good first public deployment for this Flask API.

Render supports Docker services from a repository Dockerfile. A Render web service must bind its public HTTP server to `0.0.0.0` and the `PORT` environment variable. This repo includes a Dockerfile that does that.

Manual Render setup:

1. Push the repo to GitHub.
2. Open Render Dashboard.
3. Click **New** > **Web Service**.
4. Connect the GitHub repo.
5. Use these settings:

```text
Name: fastbid24-door-analyzer-api
Language/runtime: Docker
Root directory: apps/fastbid24-door-analyzer/backend
Dockerfile path: Dockerfile
Health check path: /api/v1/health
Plan: Free for testing, Starter for serious usage
```

6. Add environment variables:

```text
PORT=10000
FASTBID24_API_HOST=0.0.0.0
FASTBID24_API_PORT=10000
FASTBID24_DATABASE_NAME=fastbid24_door_analyzer
FASTBID24_SECRET_KEY=<long random secret used to encrypt assigned user keys>
FASTBID24_ALLOW_GLOBAL_ANALYSIS_KEY=false
FASTBID24_OPENAI_API_KEY=<optional server fallback analysis key>
FASTBID24_OPENAI_MODEL=gpt-5.5
FASTBID24_MAX_UPLOAD_MB=100
FASTBID24_SESSION_DAYS=14
FASTBID24_EXTRACTION_RATE_LIMIT_PER_HOUR=12
DATABASE_URL=...
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=...
S3_BUCKET_NAME=door-schedules-fastbid24
FASTBID24_S3_BUCKET_NAME=door-schedules-fastbid24
FASTBID24_CORS_ORIGINS=https://your-cloudflare-pages-domain.pages.dev
```

7. Deploy.
8. Open:

```text
https://your-render-service.onrender.com/api/v1/health
```

9. In Render Shell, run:

```bash
python scripts/init_backend.py --skip-create-database
python scripts/check_deploy.py
```

Use `--skip-create-database` because the Supabase database has already been created locally.

Blueprint setup:

The repo also has `render.yaml` at the root. In Render, choose **New** > **Blueprint**, select the repo, and Render will prompt for the `sync: false` secrets.

## Capacity Notes

This architecture is suitable for an MVP with 1000+ registered users if active usage is moderate. For 1000 users at the exact same time, plan paid infrastructure:

- Supabase Pro or larger Postgres compute
- Multiple backend replicas
- R2/S3 lifecycle rules
- Backups and monitoring
