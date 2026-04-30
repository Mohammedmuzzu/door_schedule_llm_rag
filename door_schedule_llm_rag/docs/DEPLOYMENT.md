# 🚀 Deployment Guide — Supabase (Free Tier)

This guide sets up production-ready cloud infrastructure using **Supabase** (free, open-source) so your Streamlit app persists data globally.

## What You Get (All Free)

| Component | Local (dev) | Cloud (production) |
|---|---|---|
| **Database** | SQLite (`app.db`) | Supabase PostgreSQL |
| **File Storage** | Local `extracted_data/` | Supabase Storage (S3) |
| **RAG Vectors** | ChromaDB (local) | ChromaDB (auto-rebuilds on boot) |

---

## Step 1: Create a Free Supabase Account

1. Go to [https://supabase.com](https://supabase.com)
2. Click **Start your project** → Sign up with GitHub
3. Create a new project:
   - **Name**: `door-schedule-app`
   - **Database Password**: Pick a strong password (save it!)
   - **Region**: Choose closest to your users
4. Wait ~2 minutes for the project to provision

## Step 2: Get Your Database URL

1. In Supabase Dashboard → **Settings** → **Database**
2. Scroll to **Connection String** → Select **URI**
3. Copy the connection string. It looks like:
   ```
   postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
   ```
4. Replace `[password]` with the password you set in Step 1

## Step 3: Create a Storage Bucket

1. In Supabase Dashboard → **Storage**
2. Click **New Bucket**
   - Name: `door-schedules`
   - **Public**: No (private)
3. Go to **Settings** → **Storage** → **S3 Connection**
4. Note down:
   - `Access Key ID`
   - `Secret Access Key`
   - `Endpoint URL` (e.g., `https://[ref].supabase.co/storage/v1/s3`)

## Step 4: Configure Streamlit Secrets

### For Streamlit Community Cloud:
Go to your app dashboard → **Settings** → **Secrets** and paste:

```toml
DEPLOYMENT_ENV = "production"
LLM_PROVIDER = "openai"
OPENAI_API_KEY = "sk-your-openai-key"
OPENAI_MODEL = "gpt-4o-mini"

# Supabase Database
DATABASE_URL = "postgresql://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres"

# Supabase Storage
AWS_ACCESS_KEY_ID = "your-supabase-s3-access-key"
AWS_SECRET_ACCESS_KEY = "your-supabase-s3-secret-key"
S3_BUCKET_NAME = "door-schedules"
S3_ENDPOINT_URL = "https://[ref].supabase.co/storage/v1/s3"
```

### For local development:
Add the same values to your `.env` file (they're optional — the app falls back to SQLite + local files when missing).

## Step 5: Deploy to Streamlit Cloud

1. Push your code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Click **New app** → Select your repo
4. Set **Main file path**: `door_schedule_llm_rag/app.py`
5. Add your secrets from Step 4
6. Click **Deploy**

---

## How It Works

### Database
- `db.py` reads `DATABASE_URL` from environment/secrets
- If set → connects to Supabase PostgreSQL (global, persistent)
- If not set → falls back to local `app.db` (SQLite)
- **Zero code changes needed** — SQLAlchemy handles both transparently

### File Storage
- `cloud_storage.py` provides `upload_file_to_s3()` and `download_pdf_from_s3()`
- `pipeline.py` auto-uploads exports to S3 when configured
- If S3 is not configured → files stay local (no errors)

### RAG (ChromaDB)
- ChromaDB stores vectors in `rag_data/chroma/`
- On Streamlit Cloud restarts, this directory is wiped
- But `rag_store.ensure_seeded()` auto-rebuilds from `instructions/*.md` on boot
- Learned examples accumulate during the session and persist until next restart
- This is acceptable because the core extraction rules (99% of RAG value) are in git

---

## Cost

| Service | Free Tier Limit |
|---|---|
| Supabase Database | 500 MB, 50K monthly active users |
| Supabase Storage | 1 GB storage, 2 GB bandwidth/month |
| Supabase Auth | 50K monthly active users |
| Streamlit Cloud | Unlimited for public repos |
| **Total** | **$0/month** |
