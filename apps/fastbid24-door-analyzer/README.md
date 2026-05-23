# FastBid24 Door Analyzer

Static browser app for FastBid24-style door, hardware, risk, and RFI analysis. This app is isolated in the monorepo under `apps/fastbid24-door-analyzer`.

```text
C:\Users\muzaf\Downloads\FastBid24 Door Analyzer (1).zip
```

## Notes

- `app.jsx` contains the React app and current client-side extraction flow.
- `prompts/` documents the staged extraction pipeline:
  - door schedule extraction
  - hardware set extraction
  - door-to-hardware mapping
  - optional RFI / estimator review
- The UI layer has been refactored for a denser estimator workbench pattern while preserving extraction logic, features, and prompt content.

The main entry point is `index.html`, which loads the refactored `app.jsx` and `styles.css` in the browser.

## Clean Folder Contents

- `index.html` - browser entry point.
- `config.js` - frontend API/auth configuration.
- `app.jsx` - React app source and extraction pipeline logic.
- `styles.css` - workbench UI styling.
- `prompts/` - pipeline prompt documentation and metadata references.
- `backend/` - Flask API for login, roles, Postgres run history, logs, and S3 PDF storage.
- `serve.ps1` - local static server launcher.

## Backend Setup

The backend uses the repo `.env` for `DATABASE_URL` and S3 credentials. It derives a FastBid-specific database from `FASTBID24_DATABASE_NAME` or defaults to `fastbid24_door_analyzer`.

```powershell
& "c:\Users\muzaf\my_lab\computervision\Scripts\python.exe" apps\fastbid24-door-analyzer\backend\scripts\init_backend.py
.\apps\fastbid24-door-analyzer\backend\run.ps1
```

Then use the first-time setup link on the login page to create the first admin account.

## Deployment

See the production runbook:

```text
docs/FASTBID24_DEPLOYMENT.md
```

The backend is Docker-ready for Coolify via:

```text
apps/fastbid24-door-analyzer/compose.coolify.yml
```

## Run

From the repo root:

```powershell
.\apps\fastbid24-door-analyzer\serve.ps1
```

Then open:

```text
http://127.0.0.1:8503/
```

The app uses browser CDN dependencies for React, Babel, pdf.js, and XLSX, so the browser needs internet access unless those dependencies are vendored locally later.
