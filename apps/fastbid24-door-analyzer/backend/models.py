import uuid

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import declarative_base, relationship


Base = declarative_base()


def uuid_pk():
    return Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class Organization(Base):
    __tablename__ = "organizations"

    id = uuid_pk()
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    users = relationship("User", back_populates="organization")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        CheckConstraint("role IN ('admin', 'user')", name="ck_users_role"),
        CheckConstraint("status IN ('active', 'inactive')", name="ck_users_status"),
        Index("ix_users_organization_id", "organization_id"),
    )

    id = uuid_pk()
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    email = Column(String(320), nullable=False)
    name = Column(String(255), nullable=False)
    role = Column(String(32), nullable=False, default="user")
    status = Column(String(32), nullable=False, default="active")
    password_hash = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    organization = relationship("Organization", back_populates="users")
    sessions = relationship("UserSession", back_populates="user")
    runs = relationship("PdfRun", back_populates="user")
    ai_credential = relationship(
        "UserAiCredential",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        foreign_keys="UserAiCredential.user_id",
    )


class UserAiCredential(Base):
    __tablename__ = "user_ai_credentials"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_user_ai_credentials_user_id"),
        Index("ix_user_ai_credentials_org_user", "organization_id", "user_id"),
    )

    id = uuid_pk()
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    provider = Column(String(64), nullable=False, default="analysis")
    encrypted_api_key = Column(Text, nullable=False)
    key_fingerprint = Column(String(64), nullable=False)
    key_hint = Column(String(32), nullable=True)
    created_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="ai_credential", foreign_keys=[user_id])
    created_by = relationship("User", foreign_keys=[created_by_user_id])


class UserSession(Base):
    __tablename__ = "user_sessions"
    __table_args__ = (
        UniqueConstraint("token_hash", name="uq_user_sessions_token_hash"),
        Index("ix_user_sessions_user_id", "user_id"),
        Index("ix_user_sessions_expires_at", "expires_at"),
    )

    id = uuid_pk()
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    token_hash = Column(String(128), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_seen_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="sessions")


class PdfRun(Base):
    __tablename__ = "pdf_runs"
    __table_args__ = (
        CheckConstraint("status IN ('completed', 'failed', 'review_required')", name="ck_pdf_runs_status"),
        Index("ix_pdf_runs_org_created", "organization_id", "created_at"),
        Index("ix_pdf_runs_user_created", "user_id", "created_at"),
        Index("ix_pdf_runs_source_sha256", "source_sha256"),
    )

    id = uuid_pk()
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    proposal_id = Column(String(64), nullable=True)
    status = Column(String(32), nullable=False, default="completed")
    scope = Column(String(128), nullable=True)
    source_filename = Column(String(512), nullable=False)
    source_size = Column(BigInteger, nullable=True)
    source_sha256 = Column(String(64), nullable=True)
    s3_bucket = Column(String(255), nullable=True)
    s3_key = Column(String(1024), nullable=True)
    s3_url = Column(Text, nullable=True)
    project_name = Column(String(512), nullable=True)
    project_number = Column(String(128), nullable=True)
    architect = Column(String(512), nullable=True)
    pdf_type = Column(String(128), nullable=True)
    model = Column(String(128), nullable=True)
    analysis_json = Column(JSONB, nullable=False, default=dict)
    project_json = Column(JSONB, nullable=False, default=dict)
    summary_json = Column(JSONB, nullable=False, default=dict)
    metrics_json = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="runs")
    logs = relationship("PdfRunLog", back_populates="run", cascade="all, delete-orphan")


class PdfRunLog(Base):
    __tablename__ = "pdf_run_logs"
    __table_args__ = (
        CheckConstraint("level IN ('info', 'ok', 'warn', 'error')", name="ck_pdf_run_logs_level"),
        Index("ix_pdf_run_logs_run_created", "run_id", "created_at"),
        Index("ix_pdf_run_logs_user_created", "user_id", "created_at"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    run_id = Column(UUID(as_uuid=True), ForeignKey("pdf_runs.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    level = Column(String(32), nullable=False, default="info")
    stage = Column(String(128), nullable=True)
    message = Column(Text, nullable=False)
    payload = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    run = relationship("PdfRun", back_populates="logs")


class ExtractedDoor(Base):
    __tablename__ = "extracted_doors"
    __table_args__ = (
        Index("ix_extracted_doors_run_id", "run_id"),
        Index("ix_extracted_doors_hardware_set", "hardware_set"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    run_id = Column(UUID(as_uuid=True), ForeignKey("pdf_runs.id"), nullable=False)
    door_mark = Column(String(128), nullable=True)
    hardware_set = Column(String(128), nullable=True)
    risk_level = Column(String(64), nullable=True)
    confidence = Column(String(64), nullable=True)
    payload = Column(JSONB, nullable=False, default=dict)


class HardwareSet(Base):
    __tablename__ = "hardware_sets"
    __table_args__ = (
        Index("ix_hardware_sets_run_id", "run_id"),
        Index("ix_hardware_sets_hardware_set", "hardware_set"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    run_id = Column(UUID(as_uuid=True), ForeignKey("pdf_runs.id"), nullable=False)
    hardware_set = Column(String(128), nullable=True)
    status = Column(String(128), nullable=True)
    item_count = Column(Integer, nullable=False, default=0)
    payload = Column(JSONB, nullable=False, default=dict)


class HardwareItem(Base):
    __tablename__ = "hardware_items"
    __table_args__ = (
        Index("ix_hardware_items_run_id", "run_id"),
        Index("ix_hardware_items_set_id", "hardware_set_id"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    run_id = Column(UUID(as_uuid=True), ForeignKey("pdf_runs.id"), nullable=False)
    hardware_set_id = Column(BigInteger, ForeignKey("hardware_sets.id"), nullable=True)
    item_no = Column(String(64), nullable=True)
    qty = Column(String(64), nullable=True)
    description = Column(Text, nullable=True)
    catalog_number = Column(String(255), nullable=True)
    manufacturer = Column(String(255), nullable=True)
    finish = Column(String(128), nullable=True)
    payload = Column(JSONB, nullable=False, default=dict)


class RfiItem(Base):
    __tablename__ = "rfi_items"
    __table_args__ = (
        Index("ix_rfi_items_run_id", "run_id"),
        Index("ix_rfi_items_priority", "priority"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    run_id = Column(UUID(as_uuid=True), ForeignKey("pdf_runs.id"), nullable=False)
    priority = Column(String(64), nullable=True)
    category = Column(String(255), nullable=True)
    question = Column(Text, nullable=True)
    source = Column(String(255), nullable=True)
    payload = Column(JSONB, nullable=False, default=dict)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_events_org_created", "organization_id", "created_at"),
        Index("ix_audit_events_user_created", "user_id", "created_at"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    action = Column(String(128), nullable=False)
    entity_type = Column(String(128), nullable=False)
    entity_id = Column(String(128), nullable=True)
    payload = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
