import json
import os
import re
import threading
import time
import uuid
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from functools import wraps

from flask import Flask, jsonify, request
from sqlalchemy import func
from werkzeug.exceptions import HTTPException

from config import allowed_origin, settings
from db import session_scope
from extraction import ExtractionError, extract_pdf_secure
from models import (
    AuditEvent,
    ExtractedDoor,
    HardwareItem,
    HardwareSet,
    Organization,
    PdfRun,
    PdfRunLog,
    RfiItem,
    User,
    UserAiCredential,
    UserSession,
)
from security import (
    SecretConfigurationError,
    SecretDecryptionError,
    decrypt_secret,
    encrypt_secret,
    hash_password,
    issue_token,
    normalize_email,
    secret_fingerprint,
    secret_hint,
    token_digest,
    verify_password,
)
from storage import StorageNotConfigured, upload_pdf


EXTRACTION_ATTEMPTS: dict[str, deque[float]] = defaultdict(deque)
EXTRACTION_JOBS: dict[str, dict] = {}
EXTRACTION_JOB_LOCK = threading.Lock()
EXTRACTION_EXECUTOR = ThreadPoolExecutor(max_workers=max(1, int(os.environ.get("FASTBID24_EXTRACTION_WORKERS", "1"))))
EXTRACTION_JOB_TTL_SECONDS = 6 * 60 * 60


def iso(value):
    return value.isoformat() if value else None


def api_error(status: int, code: str, message: str, details: dict | None = None):
    response = jsonify({"error": code, "message": message, "details": details or {}})
    response.status_code = status
    return response


def parse_json_field(name: str, default):
    raw = request.form.get(name)
    if raw in (None, ""):
        return default
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        raise ValueError(f"{name} must be valid JSON")


def serialize_user(user: User) -> dict:
    credential = getattr(user, "ai_credential", None)
    return {
        "id": str(user.id),
        "organization_id": str(user.organization_id),
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "status": user.status,
        "analysis_key_configured": bool(credential),
        "analysis_key_hint": credential.key_hint if credential else None,
        "analysis_key_updated_at": iso(credential.updated_at) if credential else None,
        "created_at": iso(user.created_at),
        "updated_at": iso(user.updated_at),
        "last_login_at": iso(user.last_login_at),
    }


def public_log_message(message: str) -> str:
    clean = str(message or "")
    clean = re.sub(r"\bOpenAI\b", "analysis service", clean, flags=re.I)
    clean = re.sub(r"\bgpt[-\w.]*\b", "analysis engine", clean, flags=re.I)
    clean = re.sub(r"\bCall\s+\d+\s*\([^)]+\)", "Analysis step", clean, flags=re.I)
    clean = re.sub(r"sending PDF/data to [^.]+", "processing document data", clean, flags=re.I)
    return clean


def public_log_payload(payload: dict | None) -> dict:
    if not isinstance(payload, dict):
        return {}
    return {key: payload[key] for key in ("kind", "level", "stage", "ts") if key in payload}


def clean_project_name(value: str | None) -> str | None:
    text = str(value or "").strip()
    if not text or re.fullmatch(r"untitled(?: project)?|project", text, flags=re.I):
        return None
    return text


def serialize_log(log: PdfRunLog) -> dict:
    return {
        "id": log.id,
        "run_id": str(log.run_id),
        "user_id": str(log.user_id),
        "level": log.level,
        "stage": log.stage,
        "message": public_log_message(log.message),
        "payload": public_log_payload(log.payload),
        "created_at": iso(log.created_at),
    }


def serialize_run(run: PdfRun, include_analysis: bool = False, include_logs: bool = False) -> dict:
    data = {
        "id": str(run.id),
        "organization_id": str(run.organization_id),
        "user_id": str(run.user_id),
        "user_email": run.user.email if run.user else None,
        "proposal_id": run.proposal_id,
        "status": run.status,
        "scope": run.scope,
        "source_filename": run.source_filename,
        "source_size": run.source_size,
        "source_sha256": run.source_sha256,
        "s3_bucket": run.s3_bucket,
        "s3_key": run.s3_key,
        "s3_url": run.s3_url,
        "project_name": run.project_name,
        "project_number": run.project_number,
        "architect": run.architect,
        "summary_json": run.summary_json or {},
        "metrics_json": run.metrics_json or {},
        "created_at": iso(run.created_at),
        "updated_at": iso(run.updated_at),
        "completed_at": iso(run.completed_at),
    }
    if include_analysis:
        data["analysis_json"] = run.analysis_json or {}
        data["project_json"] = run.project_json or {}
    if include_logs:
        data["logs"] = [serialize_log(log) for log in run.logs]
    return data


def public_extraction_result(result: dict) -> dict:
    qa = result.get("qa") if isinstance(result.get("qa"), dict) else {}
    return {
        "analysis": result.get("analysis") or {},
        "qa": {
            "extraction_complete": qa.get("extraction_complete", True),
            "extraction_failures": qa.get("extraction_failures") or [],
        },
    }


def public_job(job: dict) -> dict:
    data = {
        "id": job.get("id"),
        "status": job.get("status"),
        "filename": job.get("filename"),
        "scope": job.get("scope"),
        "message": job.get("message"),
        "created_at": job.get("created_at"),
        "updated_at": job.get("updated_at"),
        "started_at": job.get("started_at"),
        "completed_at": job.get("completed_at"),
    }
    if job.get("status") == "completed":
        data["result"] = job.get("result") or {}
    if job.get("status") == "failed":
        data["error"] = job.get("error") or "The analysis could not be completed. Please retry or contact your admin."
    return data


def cleanup_extraction_jobs() -> None:
    cutoff = time.time() - EXTRACTION_JOB_TTL_SECONDS
    with EXTRACTION_JOB_LOCK:
        stale = [
            job_id
            for job_id, job in EXTRACTION_JOBS.items()
            if job.get("status") in {"completed", "failed"} and float(job.get("finished_ts") or 0) < cutoff
        ]
        for job_id in stale:
            EXTRACTION_JOBS.pop(job_id, None)


def set_extraction_job(job_id: str, **updates) -> dict | None:
    with EXTRACTION_JOB_LOCK:
        job = EXTRACTION_JOBS.get(job_id)
        if not job:
            return None
        job.update(updates)
        job["updated_at"] = iso(datetime.now(timezone.utc))
        return dict(job)


def get_extraction_job(job_id: str) -> dict | None:
    with EXTRACTION_JOB_LOCK:
        job = EXTRACTION_JOBS.get(job_id)
        return dict(job) if job else None


def run_extraction_job(job_id: str, user_id: str, filename: str, file_bytes: bytes, scope: str, run_rfis: bool, analysis_key: str) -> None:
    now = datetime.now(timezone.utc)
    set_extraction_job(
        job_id,
        status="running",
        message="Analyzing document.",
        started_at=iso(now),
    )
    try:
        result = extract_pdf_secure(file_bytes, filename, scope, run_rfis=run_rfis, api_key=analysis_key)
        public_result = public_extraction_result(result)
        completed_at = datetime.now(timezone.utc)
        set_extraction_job(
            job_id,
            status="completed",
            message="Analysis ready for review.",
            result=public_result,
            completed_at=iso(completed_at),
            finished_ts=time.time(),
        )
        try:
            with session_scope() as db:
                user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()
                if user:
                    add_audit(
                        db,
                        user,
                        "extract.completed",
                        "pdf",
                        None,
                        {
                            "filename": filename,
                            "scope": scope,
                            "doors": len(public_result.get("analysis", {}).get("door_analysis") or []),
                            "hardware_sets": len(public_result.get("analysis", {}).get("hardware_set_review") or []),
                            "job_id": job_id,
                        },
                    )
        except Exception:
            pass
    except ExtractionError as exc:
        message = public_log_message(str(exc)) or "The analysis could not be completed. Please retry or contact your admin."
        set_extraction_job(
            job_id,
            status="failed",
            message="Analysis could not be completed.",
            error=message,
            completed_at=iso(datetime.now(timezone.utc)),
            finished_ts=time.time(),
        )
        try:
            with session_scope() as db:
                user = db.query(User).filter(User.id == uuid.UUID(user_id)).first()
                if user:
                    add_audit(db, user, "extract.failed", "pdf", None, {"filename": filename, "error": message, "job_id": job_id})
        except Exception:
            pass
    except Exception:
        set_extraction_job(
            job_id,
            status="failed",
            message="Analysis could not be completed.",
            error="The analysis could not be completed. Please retry or contact your admin.",
            completed_at=iso(datetime.now(timezone.utc)),
            finished_ts=time.time(),
        )


def get_bearer_token() -> str | None:
    header = request.headers.get("Authorization", "")
    if header.lower().startswith("bearer "):
        return header.split(" ", 1)[1].strip()
    return None


def current_session_user(db):
    token = get_bearer_token()
    if not token:
        return None
    session = (
        db.query(UserSession)
        .join(User)
        .filter(UserSession.token_hash == token_digest(token), UserSession.revoked_at.is_(None))
        .first()
    )
    if not session:
        return None
    now = datetime.now(timezone.utc)
    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= now:
        session.revoked_at = now
        return None
    if session.user.status != "active":
        return None
    session.last_seen_at = now
    return session.user


def require_user(handler):
    @wraps(handler)
    def wrapper(*args, **kwargs):
        with session_scope() as db:
            user = current_session_user(db)
            if not user:
                return api_error(401, "Unauthorized", "Login is required.")
            return handler(db, user, *args, **kwargs)

    return wrapper


def require_admin(handler):
    @wraps(handler)
    def wrapper(db, user, *args, **kwargs):
        if user.role != "admin":
            return api_error(403, "Forbidden", "Admin access is required.")
        return handler(db, user, *args, **kwargs)

    return wrapper


def paginate(query, page: int, page_size: int):
    page = max(1, page)
    page_size = min(max(1, page_size), 100)
    total = query.count()
    items = query.limit(page_size).offset((page - 1) * page_size).all()
    return items, {
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": (total + page_size - 1) // page_size,
    }


def add_audit(db, user: User | None, action: str, entity_type: str, entity_id: str | None, payload: dict | None = None):
    org_id = user.organization_id if user else None
    if not org_id:
        return
    db.add(
        AuditEvent(
            organization_id=org_id,
            user_id=user.id if user else None,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=payload or {},
        )
    )


def audit_safe_user_patch(body: dict) -> dict:
    hidden = {"password", "analysis_api_key"}
    payload = {key: value for key, value in body.items() if key not in hidden}
    if "password" in body:
        payload["password"] = "updated"
    if "analysis_api_key" in body:
        payload["analysis_key"] = "updated"
    return payload


def get_account_analysis_key(db, user: User) -> str | None:
    credential = (
        db.query(UserAiCredential)
        .filter(UserAiCredential.organization_id == user.organization_id, UserAiCredential.user_id == user.id)
        .first()
    )
    if credential:
        return decrypt_secret(credential.encrypted_api_key)
    if settings.allow_global_analysis_key:
        return settings.openai_api_key
    return None


def upsert_account_analysis_key(db, target: User, admin: User, raw_key: str) -> None:
    clean = (raw_key or "").strip()
    if not clean:
        raise ValueError("Analysis key cannot be empty.")
    if len(clean) > 4096:
        raise ValueError("Analysis key is too long.")
    credential = (
        db.query(UserAiCredential)
        .filter(UserAiCredential.organization_id == target.organization_id, UserAiCredential.user_id == target.id)
        .first()
    )
    if not credential:
        credential = UserAiCredential(
            organization_id=target.organization_id,
            user_id=target.id,
            provider="analysis",
        )
        db.add(credential)
    credential.encrypted_api_key = encrypt_secret(clean)
    credential.key_fingerprint = secret_fingerprint(clean)
    credential.key_hint = secret_hint(clean)
    credential.created_by_user_id = admin.id
    db.flush()


def clear_account_analysis_key(db, target: User) -> bool:
    credential = (
        db.query(UserAiCredential)
        .filter(UserAiCredential.organization_id == target.organization_id, UserAiCredential.user_id == target.id)
        .first()
    )
    if not credential:
        return False
    db.delete(credential)
    db.flush()
    return True


def rate_limit_extraction(user: User) -> tuple[bool, int]:
    limit = max(1, settings.extraction_rate_limit_per_hour)
    now = time.time()
    window_start = now - 3600
    key = str(user.id)
    attempts = EXTRACTION_ATTEMPTS[key]
    while attempts and attempts[0] < window_start:
        attempts.popleft()
    if len(attempts) >= limit:
        retry_after = int(max(1, 3600 - (now - attempts[0])))
        return False, retry_after
    attempts.append(now)
    return True, 0


def register_routes(app: Flask) -> None:
    @app.before_request
    def handle_options():
        if request.method == "OPTIONS":
            return "", 204
        return None

    @app.after_request
    def add_cors(response):
        origin = allowed_origin(request.headers.get("Origin"))
        if origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Vary"] = "Origin"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PATCH, DELETE, OPTIONS"
        return response

    @app.errorhandler(HTTPException)
    def handle_http_error(exc):
        return api_error(exc.code or 500, exc.name.replace(" ", ""), exc.description)

    @app.errorhandler(ValueError)
    def handle_value_error(exc):
        return api_error(400, "BadRequest", str(exc))

    @app.errorhandler(Exception)
    def handle_unexpected(exc):
        app.logger.exception("Unhandled API error")
        return api_error(500, "InternalServerError", "Unexpected backend error.")

    @app.get("/")
    def api_root():
        return jsonify(
            {
                "ok": True,
                "service": "FastBid24 Door Analyzer API",
                "message": "Backend is running. Use /api/v1/health for health checks.",
                "health": "/api/v1/health",
                "api_base": "/api/v1",
            }
        )

    @app.get("/api/v1")
    def api_index():
        return jsonify(
            {
                "ok": True,
                "service": "FastBid24 Door Analyzer API",
                "endpoints": {
                    "health": "/api/v1/health",
                    "login": "/api/v1/auth/login",
                    "runs": "/api/v1/runs",
                    "extract": "/api/v1/extract",
                    "admin_users": "/api/v1/admin/users",
                    "admin_runs": "/api/v1/admin/runs",
                },
            }
        )

    @app.get("/api/openapi.json")
    def openapi_spec():
        return jsonify(
            {
                "openapi": "3.0.3",
                "info": {
                    "title": "FastBid24 Door Analyzer API",
                    "version": "1.0.0",
                    "description": "Authentication, PDF run history, S3 PDF storage, and admin APIs for FastBid24.",
                },
                "servers": [{"url": "/api/v1"}],
                "components": {
                    "securitySchemes": {
                        "BearerAuth": {
                            "type": "http",
                            "scheme": "bearer",
                            "bearerFormat": "session-token",
                        }
                    }
                },
                "security": [{"BearerAuth": []}],
                "paths": {
                    "/health": {
                        "get": {
                            "summary": "Health check",
                            "security": [],
                            "responses": {"200": {"description": "Backend health status"}},
                        }
                    },
                    "/auth/bootstrap": {
                        "post": {
                            "summary": "Create the first admin user",
                            "security": [],
                            "requestBody": {
                                "required": True,
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "required": ["email", "password"],
                                            "properties": {
                                                "email": {"type": "string", "format": "email"},
                                                "password": {"type": "string", "minLength": 8},
                                                "name": {"type": "string"},
                                                "organization_name": {"type": "string"},
                                            },
                                        }
                                    }
                                },
                            },
                            "responses": {
                                "201": {"description": "Admin user created"},
                                "409": {"description": "Users already exist"},
                            },
                        }
                    },
                    "/auth/login": {
                        "post": {
                            "summary": "Login",
                            "security": [],
                            "requestBody": {
                                "required": True,
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "required": ["email", "password"],
                                            "properties": {
                                                "email": {"type": "string", "format": "email"},
                                                "password": {"type": "string"},
                                            },
                                        }
                                    }
                                },
                            },
                            "responses": {"200": {"description": "Bearer token and user profile"}},
                        }
                    },
                    "/auth/bootstrap/status": {
                        "get": {
                            "summary": "Check whether first-admin setup is still available",
                            "security": [],
                            "responses": {"200": {"description": "Bootstrap availability"}},
                        }
                    },
                    "/auth/logout": {
                        "post": {
                            "summary": "Logout current session",
                            "responses": {"204": {"description": "Logged out"}},
                        }
                    },
                    "/me": {
                        "get": {
                            "summary": "Current user profile",
                            "responses": {"200": {"description": "Current user"}},
                        }
                    },
                    "/runs": {
                        "get": {
                            "summary": "List current user's PDF runs",
                            "responses": {"200": {"description": "Paginated runs"}},
                        },
                        "post": {
                            "summary": "Store a completed PDF analysis",
                            "requestBody": {
                                "required": True,
                                "content": {
                                    "multipart/form-data": {
                                        "schema": {
                                            "type": "object",
                                            "required": ["pdf", "analysis_json"],
                                            "properties": {
                                                "pdf": {"type": "string", "format": "binary"},
                                                "analysis_json": {"type": "string"},
                                                "project_json": {"type": "string"},
                                                "logs_json": {"type": "string"},
                                                "metrics_json": {"type": "string"},
                                                "scope": {"type": "string"},
                                            },
                                        }
                                    }
                                },
                            },
                            "responses": {"201": {"description": "Run stored"}},
                        },
                    },
                    "/runs/{run_id}": {
                        "get": {
                            "summary": "Get one PDF run",
                            "parameters": [{"name": "run_id", "in": "path", "required": True, "schema": {"type": "string"}}],
                            "responses": {"200": {"description": "Run detail"}},
                        }
                    },
                    "/runs/{run_id}/logs": {
                        "get": {
                            "summary": "Get logs for one PDF run",
                            "parameters": [{"name": "run_id", "in": "path", "required": True, "schema": {"type": "string"}}],
                            "responses": {"200": {"description": "Run logs"}},
                        }
                    },
                    "/admin/users": {
                        "get": {
                            "summary": "Admin: list users",
                            "responses": {"200": {"description": "Users"}},
                        },
                        "post": {
                            "summary": "Admin: create user",
                            "requestBody": {
                                "required": True,
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "required": ["email", "password"],
                                            "properties": {
                                                "name": {"type": "string"},
                                                "email": {"type": "string", "format": "email"},
                                                "password": {"type": "string", "minLength": 8},
                                                "role": {"type": "string", "enum": ["admin", "user"]},
                                                "analysis_api_key": {"type": "string", "writeOnly": True},
                                            },
                                        }
                                    }
                                },
                            },
                            "responses": {"201": {"description": "User created"}},
                        },
                    },
                    "/admin/users/{user_id}": {
                        "patch": {
                            "summary": "Admin: update user",
                            "parameters": [{"name": "user_id", "in": "path", "required": True, "schema": {"type": "string"}}],
                            "requestBody": {
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "name": {"type": "string"},
                                                "role": {"type": "string", "enum": ["admin", "user"]},
                                                "status": {"type": "string", "enum": ["active", "inactive"]},
                                                "password": {"type": "string", "minLength": 8},
                                                "analysis_api_key": {"type": "string", "writeOnly": True},
                                                "clear_analysis_api_key": {"type": "boolean"},
                                            },
                                        }
                                    }
                                }
                            },
                            "responses": {"200": {"description": "User updated"}},
                        }
                    },
                    "/admin/runs": {
                        "get": {
                            "summary": "Admin: list all PDF runs",
                            "responses": {"200": {"description": "Runs"}},
                        }
                    },
                    "/admin/logs": {
                        "get": {
                            "summary": "Admin: list logs",
                            "parameters": [{"name": "run_id", "in": "query", "required": False, "schema": {"type": "string"}}],
                            "responses": {"200": {"description": "Logs"}},
                        }
                    },
                },
            }
        )

    @app.get("/api/docs")
    def swagger_docs():
        return """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>FastBid24 API Docs</title>
  <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
  <script>
    window.ui = SwaggerUIBundle({
      url: '/api/openapi.json',
      dom_id: '#swagger-ui',
      deepLinking: true,
      persistAuthorization: true
    });
  </script>
</body>
</html>
"""

    @app.get("/api/v1/health")
    def health():
        return jsonify(
            {
                "ok": True,
                "database_configured": settings.database_configured,
                "s3_configured": settings.s3_configured,
                "analysis_fallback_configured": settings.analysis_fallback_configured,
                "secret_configured": settings.secret_configured,
                "bucket": settings.s3_bucket_name,
            }
        )

    @app.post("/api/v1/auth/bootstrap")
    def bootstrap_admin():
        body = request.get_json(silent=True) or {}
        email = normalize_email(body.get("email", ""))
        password = body.get("password", "")
        name = (body.get("name") or "Admin").strip()
        org_name = (body.get("organization_name") or "FastBid24").strip()
        if not email or "@" not in email:
            return api_error(422, "ValidationError", "A valid email is required.")
        if len(password) < 8:
            return api_error(422, "ValidationError", "Password must be at least 8 characters.")
        with session_scope() as db:
            if db.query(User).count() > 0:
                return api_error(409, "AlreadyInitialized", "Bootstrap is only available before users exist.")
            org = Organization(name=org_name)
            db.add(org)
            db.flush()
            user = User(
                organization_id=org.id,
                email=email,
                name=name,
                role="admin",
                status="active",
                password_hash=hash_password(password),
            )
            db.add(user)
            db.flush()
            add_audit(db, user, "auth.bootstrap_admin", "user", str(user.id), {"email": email})
            return jsonify({"user": serialize_user(user)}), 201

    @app.get("/api/v1/auth/bootstrap/status")
    def bootstrap_status():
        with session_scope() as db:
            user_count = db.query(User).count()
            return jsonify({"bootstrap_available": user_count == 0, "user_count": user_count})

    @app.post("/api/v1/auth/login")
    def login():
        body = request.get_json(silent=True) or {}
        email = normalize_email(body.get("email", ""))
        password = body.get("password", "")
        with session_scope() as db:
            user = db.query(User).filter(User.email == email).first()
            if not user or user.status != "active" or not verify_password(user.password_hash, password):
                return api_error(401, "InvalidCredentials", "Email or password is incorrect.")
            token, digest, expires_at = issue_token()
            db.add(UserSession(user_id=user.id, token_hash=digest, expires_at=expires_at))
            user.last_login_at = datetime.now(timezone.utc)
            add_audit(db, user, "auth.login", "user", str(user.id), {})
            return jsonify({"token": token, "expires_at": iso(expires_at), "user": serialize_user(user)})

    @app.post("/api/v1/auth/logout")
    @require_user
    def logout(db, user):
        token = get_bearer_token()
        session = db.query(UserSession).filter(UserSession.token_hash == token_digest(token)).first()
        if session:
            session.revoked_at = datetime.now(timezone.utc)
        add_audit(db, user, "auth.logout", "user", str(user.id), {})
        return "", 204

    @app.get("/api/v1/me")
    @require_user
    def me(db, user):
        return jsonify({"user": serialize_user(user)})

    @app.post("/api/v1/extract/jobs")
    @require_user
    def start_extract_job(db, user):
        cleanup_extraction_jobs()
        allowed, retry_after = rate_limit_extraction(user)
        if not allowed:
            response = api_error(429, "RateLimited", "Extraction rate limit reached. Try again later.")
            response.headers["Retry-After"] = str(retry_after)
            return response
        try:
            analysis_key = get_account_analysis_key(db, user)
        except SecretConfigurationError:
            return api_error(503, "AnalysisKeyNotConfigured", "Secure analysis keys are not configured on the server.")
        except SecretDecryptionError:
            return api_error(503, "AnalysisKeyUnavailable", "This account's analysis key could not be read. Ask an admin to replace it.")
        if not analysis_key:
            return api_error(503, "AnalysisKeyNotConfigured", "Analysis service is not configured for this account.")

        pdf = request.files.get("pdf")
        if not pdf:
            return api_error(422, "ValidationError", "A PDF file is required.")
        filename = pdf.filename or "document.pdf"
        if not filename.lower().endswith(".pdf"):
            return api_error(422, "ValidationError", "Only PDF files are supported.")

        file_bytes = pdf.read()
        if not file_bytes:
            return api_error(422, "ValidationError", "Uploaded PDF is empty.")
        max_bytes = settings.max_upload_mb * 1024 * 1024
        if len(file_bytes) > max_bytes:
            return api_error(413, "PayloadTooLarge", f"PDF exceeds the {settings.max_upload_mb} MB upload limit.")

        scope = request.form.get("scope") or "Supply & Installation"
        if scope not in {"Supply Only", "Installation Only", "Supply & Installation"}:
            return api_error(422, "ValidationError", "Invalid project scope.")
        run_rfis = str(request.form.get("run_rfis", "true")).lower() not in {"0", "false", "no"}

        job_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        job = {
            "id": job_id,
            "organization_id": str(user.organization_id),
            "user_id": str(user.id),
            "status": "queued",
            "filename": filename,
            "scope": scope,
            "message": "Queued for analysis.",
            "created_at": iso(now),
            "updated_at": iso(now),
            "created_ts": time.time(),
        }
        with EXTRACTION_JOB_LOCK:
            EXTRACTION_JOBS[job_id] = job

        EXTRACTION_EXECUTOR.submit(run_extraction_job, job_id, str(user.id), filename, file_bytes, scope, run_rfis, analysis_key)
        add_audit(db, user, "extract.queued", "pdf", None, {"filename": filename, "scope": scope, "job_id": job_id})
        return jsonify({"job": public_job(job)}), 202

    @app.get("/api/v1/extract/jobs/<job_id>")
    @require_user
    def get_extract_job(db, user, job_id):
        job = get_extraction_job(job_id)
        if not job:
            return api_error(404, "NotFound", "Extraction job was not found. Please start a new analysis.")
        if job.get("organization_id") != str(user.organization_id):
            return api_error(404, "NotFound", "Extraction job was not found. Please start a new analysis.")
        if user.role != "admin" and job.get("user_id") != str(user.id):
            return api_error(403, "Forbidden", "You can only view your own extraction jobs.")
        return jsonify({"job": public_job(job)})

    @app.post("/api/v1/extract")
    @require_user
    def extract_pdf(db, user):
        allowed, retry_after = rate_limit_extraction(user)
        if not allowed:
            response = api_error(429, "RateLimited", "Extraction rate limit reached. Try again later.")
            response.headers["Retry-After"] = str(retry_after)
            return response
        try:
            analysis_key = get_account_analysis_key(db, user)
        except SecretConfigurationError:
            return api_error(503, "AnalysisKeyNotConfigured", "Secure analysis keys are not configured on the server.")
        except SecretDecryptionError:
            return api_error(503, "AnalysisKeyUnavailable", "This account's analysis key could not be read. Ask an admin to replace it.")
        if not analysis_key:
            return api_error(503, "AnalysisKeyNotConfigured", "Analysis service is not configured for this account.")

        pdf = request.files.get("pdf")
        if not pdf:
            return api_error(422, "ValidationError", "A PDF file is required.")
        filename = pdf.filename or "document.pdf"
        if not filename.lower().endswith(".pdf"):
            return api_error(422, "ValidationError", "Only PDF files are supported.")

        file_bytes = pdf.read()
        if not file_bytes:
            return api_error(422, "ValidationError", "Uploaded PDF is empty.")
        max_bytes = settings.max_upload_mb * 1024 * 1024
        if len(file_bytes) > max_bytes:
            return api_error(413, "PayloadTooLarge", f"PDF exceeds the {settings.max_upload_mb} MB upload limit.")

        scope = request.form.get("scope") or "Supply & Installation"
        if scope not in {"Supply Only", "Installation Only", "Supply & Installation"}:
            return api_error(422, "ValidationError", "Invalid project scope.")
        run_rfis = str(request.form.get("run_rfis", "true")).lower() not in {"0", "false", "no"}

        try:
            result = extract_pdf_secure(file_bytes, filename, scope, run_rfis=run_rfis, api_key=analysis_key)
        except ExtractionError as exc:
            add_audit(db, user, "extract.failed", "pdf", None, {"filename": filename, "error": str(exc)})
            return api_error(502, "ExtractionFailed", str(exc))

        add_audit(
            db,
            user,
            "extract.completed",
            "pdf",
            None,
            {
                "filename": filename,
                "scope": scope,
                "doors": len(result.get("analysis", {}).get("door_analysis") or []),
                "hardware_sets": len(result.get("analysis", {}).get("hardware_set_review") or []),
            },
        )
        return jsonify(public_extraction_result(result))

    @app.get("/api/v1/runs")
    @require_user
    def list_my_runs(db, user):
        page = int(request.args.get("page", "1"))
        page_size = int(request.args.get("page_size", "50"))
        query = (
            db.query(PdfRun)
            .filter(PdfRun.organization_id == user.organization_id, PdfRun.user_id == user.id)
            .order_by(PdfRun.created_at.desc())
        )
        items, meta = paginate(query, page, page_size)
        return jsonify({"items": [serialize_run(item) for item in items], "pagination": meta})

    @app.post("/api/v1/runs")
    @require_user
    def create_run(db, user):
        pdf = request.files.get("pdf")
        if not pdf:
            return api_error(422, "ValidationError", "A PDF file is required.")
        analysis = parse_json_field("analysis_json", {})
        project = parse_json_field("project_json", {})
        logs = parse_json_field("logs_json", [])
        metrics = parse_json_field("metrics_json", {})
        if not isinstance(analysis, dict):
            return api_error(422, "ValidationError", "analysis_json must be an object.")
        if not isinstance(project, dict):
            return api_error(422, "ValidationError", "project_json must be an object.")
        if not isinstance(logs, list):
            return api_error(422, "ValidationError", "logs_json must be an array.")

        run_id = uuid.uuid4()
        try:
            stored_pdf = upload_pdf(pdf, run_id, user.id)
        except StorageNotConfigured as exc:
            return api_error(503, "StorageNotConfigured", str(exc))

        ps = analysis.get("project_summary") or {}
        qa = analysis.get("qa") or {}
        project_name = clean_project_name(ps.get("project_name")) or clean_project_name(project.get("name"))
        status = "review_required" if analysis.get("status") == "REVIEW_REQUIRED" else "completed"
        run = PdfRun(
            id=run_id,
            organization_id=user.organization_id,
            user_id=user.id,
            proposal_id=project.get("proposalId"),
            status=status,
            scope=request.form.get("scope") or ps.get("scope_type"),
            source_filename=stored_pdf.get("filename") or pdf.filename or "document.pdf",
            source_size=stored_pdf["size"],
            source_sha256=stored_pdf["sha256"],
            s3_bucket=stored_pdf["bucket"],
            s3_key=stored_pdf["key"],
            s3_url=stored_pdf["url"],
            project_name=project_name,
            project_number=ps.get("project_number") or project.get("number"),
            architect=ps.get("architect") or project.get("architect"),
            pdf_type=None,
            model=None,
            analysis_json=analysis,
            project_json=project,
            summary_json={"project_summary": ps},
            metrics_json=metrics,
            completed_at=datetime.now(timezone.utc),
        )
        db.add(run)
        db.flush()

        for item in logs[:1000]:
            if not isinstance(item, dict):
                continue
            level = item.get("kind") or item.get("level") or "info"
            if level not in {"info", "ok", "warn", "error"}:
                level = "info"
            db.add(
                PdfRunLog(
                    run_id=run.id,
                    user_id=user.id,
                    level=level,
                    stage=item.get("stage"),
                    message=str(item.get("text") or item.get("message") or ""),
                    payload=item,
                )
            )

        for door in analysis.get("door_analysis") or []:
            if isinstance(door, dict):
                db.add(
                    ExtractedDoor(
                        run_id=run.id,
                        door_mark=door.get("mark"),
                        hardware_set=door.get("hardware_set"),
                        risk_level=door.get("risk_level"),
                        confidence=str(door.get("confidence")) if door.get("confidence") is not None else None,
                        payload=door,
                    )
                )

        for hw_set in analysis.get("hardware_set_review") or []:
            if not isinstance(hw_set, dict):
                continue
            items = hw_set.get("items") if isinstance(hw_set.get("items"), list) else []
            set_row = HardwareSet(
                run_id=run.id,
                hardware_set=hw_set.get("hardware_set"),
                status=hw_set.get("status"),
                item_count=len(items),
                payload=hw_set,
            )
            db.add(set_row)
            db.flush()
            for hw_item in items:
                if not isinstance(hw_item, dict):
                    continue
                db.add(
                    HardwareItem(
                        run_id=run.id,
                        hardware_set_id=set_row.id,
                        item_no=str(hw_item.get("item_no") or hw_item.get("item") or ""),
                        qty=str(hw_item.get("qty") or ""),
                        description=hw_item.get("desc") or hw_item.get("description"),
                        catalog_number=hw_item.get("part") or hw_item.get("catalog_number"),
                        manufacturer=hw_item.get("mfr") or hw_item.get("manufacturer"),
                        finish=hw_item.get("finish"),
                        payload=hw_item,
                    )
                )

        for rfi in analysis.get("rfi_log") or []:
            if isinstance(rfi, dict):
                db.add(
                    RfiItem(
                        run_id=run.id,
                        priority=rfi.get("priority") or rfi.get("severity"),
                        category=rfi.get("category"),
                        question=rfi.get("question") or rfi.get("issue"),
                        source=rfi.get("source") or rfi.get("where"),
                        payload=rfi,
                    )
                )

        add_audit(
            db,
            user,
            "runs.create",
            "pdf_run",
            str(run.id),
            {"source_filename": run.source_filename, "s3_url": run.s3_url},
        )
        return jsonify({"run": serialize_run(run, include_analysis=True)}), 201

    @app.get("/api/v1/runs/<run_id>")
    @require_user
    def get_run(db, user, run_id):
        run = db.query(PdfRun).filter(PdfRun.id == run_id, PdfRun.organization_id == user.organization_id).first()
        if not run:
            return api_error(404, "NotFound", "Run not found.")
        if user.role != "admin" and run.user_id != user.id:
            return api_error(403, "Forbidden", "You can only view your own runs.")
        return jsonify({"run": serialize_run(run, include_analysis=True)})

    @app.get("/api/v1/runs/<run_id>/logs")
    @require_user
    def get_run_logs(db, user, run_id):
        run = db.query(PdfRun).filter(PdfRun.id == run_id, PdfRun.organization_id == user.organization_id).first()
        if not run:
            return api_error(404, "NotFound", "Run not found.")
        if user.role != "admin" and run.user_id != user.id:
            return api_error(403, "Forbidden", "You can only view your own logs.")
        logs = db.query(PdfRunLog).filter(PdfRunLog.run_id == run.id).order_by(PdfRunLog.created_at.asc()).all()
        return jsonify({"items": [serialize_log(log) for log in logs]})

    @app.get("/api/v1/admin/users")
    @require_user
    @require_admin
    def admin_list_users(db, user):
        users = db.query(User).filter(User.organization_id == user.organization_id).order_by(User.created_at.desc()).all()
        return jsonify({"items": [serialize_user(item) for item in users]})

    @app.post("/api/v1/admin/users")
    @require_user
    @require_admin
    def admin_create_user(db, user):
        body = request.get_json(silent=True) or {}
        email = normalize_email(body.get("email", ""))
        password = body.get("password", "")
        name = (body.get("name") or email).strip()
        role = body.get("role") or "user"
        if role not in {"admin", "user"}:
            return api_error(422, "ValidationError", "Role must be admin or user.")
        if not email or "@" not in email:
            return api_error(422, "ValidationError", "A valid email is required.")
        if len(password) < 8:
            return api_error(422, "ValidationError", "Password must be at least 8 characters.")
        if db.query(User).filter(User.email == email).first():
            return api_error(409, "DuplicateUser", "A user with this email already exists.")
        analysis_key = (body.get("analysis_api_key") or "").strip()
        if analysis_key:
            if len(analysis_key) > 4096:
                return api_error(422, "ValidationError", "Analysis key is too long.")
            try:
                encrypt_secret(analysis_key)
            except SecretConfigurationError:
                return api_error(503, "AnalysisKeyNotConfigured", "Secure analysis keys are not configured on the server.")
        created = User(
            organization_id=user.organization_id,
            email=email,
            name=name,
            role=role,
            status="active",
            password_hash=hash_password(password),
        )
        db.add(created)
        db.flush()
        if analysis_key:
            upsert_account_analysis_key(db, created, user, analysis_key)
        add_audit(db, user, "admin.users.create", "user", str(created.id), {"email": email, "role": role, "analysis_key": "set" if analysis_key else "unset"})
        return jsonify({"user": serialize_user(created)}), 201

    @app.patch("/api/v1/admin/users/<user_id>")
    @require_user
    @require_admin
    def admin_update_user(db, user, user_id):
        target = db.query(User).filter(User.id == user_id, User.organization_id == user.organization_id).first()
        if not target:
            return api_error(404, "NotFound", "User not found.")
        body = request.get_json(silent=True) or {}
        analysis_key = (body.get("analysis_api_key") or "").strip() if "analysis_api_key" in body else None
        if analysis_key is not None:
            if not analysis_key:
                return api_error(422, "ValidationError", "Analysis key cannot be empty.")
            if len(analysis_key) > 4096:
                return api_error(422, "ValidationError", "Analysis key is too long.")
            try:
                encrypt_secret(analysis_key)
            except SecretConfigurationError:
                return api_error(503, "AnalysisKeyNotConfigured", "Secure analysis keys are not configured on the server.")
        if "role" in body:
            if body["role"] not in {"admin", "user"}:
                return api_error(422, "ValidationError", "Role must be admin or user.")
            target.role = body["role"]
        if "status" in body:
            if body["status"] not in {"active", "inactive"}:
                return api_error(422, "ValidationError", "Status must be active or inactive.")
            if str(target.id) == str(user.id) and body["status"] != "active":
                return api_error(422, "ValidationError", "You cannot deactivate your own admin account.")
            target.status = body["status"]
        if "name" in body:
            target.name = (body["name"] or target.name).strip()
        if "password" in body and body["password"]:
            if len(body["password"]) < 8:
                return api_error(422, "ValidationError", "Password must be at least 8 characters.")
            target.password_hash = hash_password(body["password"])
        if analysis_key is not None:
            upsert_account_analysis_key(db, target, user, analysis_key)
        elif body.get("clear_analysis_api_key"):
            clear_account_analysis_key(db, target)
        add_audit(db, user, "admin.users.update", "user", str(target.id), audit_safe_user_patch(body))
        return jsonify({"user": serialize_user(target)})

    @app.get("/api/v1/admin/runs")
    @require_user
    @require_admin
    def admin_list_runs(db, user):
        page = int(request.args.get("page", "1"))
        page_size = int(request.args.get("page_size", "50"))
        query = (
            db.query(PdfRun)
            .filter(PdfRun.organization_id == user.organization_id)
            .order_by(PdfRun.created_at.desc())
        )
        items, meta = paginate(query, page, page_size)
        return jsonify({"items": [serialize_run(item) for item in items], "pagination": meta})

    @app.get("/api/v1/admin/logs")
    @require_user
    @require_admin
    def admin_list_logs(db, user):
        run_id = request.args.get("run_id")
        page = int(request.args.get("page", "1"))
        page_size = int(request.args.get("page_size", "100"))
        query = db.query(PdfRunLog).join(PdfRun).filter(PdfRun.organization_id == user.organization_id)
        if run_id:
            query = query.filter(PdfRunLog.run_id == run_id)
        query = query.order_by(PdfRunLog.created_at.desc())
        items, meta = paginate(query, page, page_size)
        return jsonify({"items": [serialize_log(item) for item in items], "pagination": meta})
