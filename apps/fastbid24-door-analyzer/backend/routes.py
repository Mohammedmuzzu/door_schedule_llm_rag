import json
import uuid
from datetime import datetime, timezone
from functools import wraps

from flask import Flask, jsonify, request
from sqlalchemy import func
from werkzeug.exceptions import HTTPException

from config import allowed_origin, settings
from db import session_scope
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
    UserSession,
)
from security import hash_password, issue_token, normalize_email, token_digest, verify_password
from storage import StorageNotConfigured, upload_pdf


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
    return {
        "id": str(user.id),
        "organization_id": str(user.organization_id),
        "email": user.email,
        "name": user.name,
        "role": user.role,
        "status": user.status,
        "created_at": iso(user.created_at),
        "updated_at": iso(user.updated_at),
        "last_login_at": iso(user.last_login_at),
    }


def serialize_log(log: PdfRunLog) -> dict:
    return {
        "id": log.id,
        "run_id": str(log.run_id),
        "user_id": str(log.user_id),
        "level": log.level,
        "stage": log.stage,
        "message": log.message,
        "payload": log.payload or {},
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
        "pdf_type": run.pdf_type,
        "model": run.model,
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
                                                "model": {"type": "string"},
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
            project_name=ps.get("project_name") or project.get("name"),
            project_number=ps.get("project_number") or project.get("number"),
            architect=ps.get("architect") or project.get("architect"),
            pdf_type=qa.get("pdf_type"),
            model=request.form.get("model") or qa.get("chat_model"),
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
        add_audit(db, user, "admin.users.create", "user", str(created.id), {"email": email, "role": role})
        return jsonify({"user": serialize_user(created)}), 201

    @app.patch("/api/v1/admin/users/<user_id>")
    @require_user
    @require_admin
    def admin_update_user(db, user, user_id):
        target = db.query(User).filter(User.id == user_id, User.organization_id == user.organization_id).first()
        if not target:
            return api_error(404, "NotFound", "User not found.")
        body = request.get_json(silent=True) or {}
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
        add_audit(db, user, "admin.users.update", "user", str(target.id), body)
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
