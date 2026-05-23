CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS organizations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id),
  email VARCHAR(320) NOT NULL,
  name VARCHAR(255) NOT NULL,
  role VARCHAR(32) NOT NULL DEFAULT 'user' CHECK (role IN ('admin', 'user')),
  status VARCHAR(32) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive')),
  password_hash TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_login_at TIMESTAMPTZ,
  CONSTRAINT uq_users_email UNIQUE (email)
);

CREATE TABLE IF NOT EXISTS user_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES users(id),
  token_hash VARCHAR(128) NOT NULL UNIQUE,
  expires_at TIMESTAMPTZ NOT NULL,
  revoked_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  last_seen_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS pdf_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id),
  user_id UUID NOT NULL REFERENCES users(id),
  proposal_id VARCHAR(64),
  status VARCHAR(32) NOT NULL DEFAULT 'completed' CHECK (status IN ('completed', 'failed', 'review_required')),
  scope VARCHAR(128),
  source_filename VARCHAR(512) NOT NULL,
  source_size BIGINT,
  source_sha256 VARCHAR(64),
  s3_bucket VARCHAR(255),
  s3_key VARCHAR(1024),
  s3_url TEXT,
  project_name VARCHAR(512),
  project_number VARCHAR(128),
  architect VARCHAR(512),
  pdf_type VARCHAR(128),
  model VARCHAR(128),
  analysis_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  project_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  summary_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  metrics_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS pdf_run_logs (
  id BIGSERIAL PRIMARY KEY,
  run_id UUID NOT NULL REFERENCES pdf_runs(id),
  user_id UUID NOT NULL REFERENCES users(id),
  level VARCHAR(32) NOT NULL DEFAULT 'info' CHECK (level IN ('info', 'ok', 'warn', 'error')),
  stage VARCHAR(128),
  message TEXT NOT NULL,
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS extracted_doors (
  id BIGSERIAL PRIMARY KEY,
  run_id UUID NOT NULL REFERENCES pdf_runs(id),
  door_mark VARCHAR(128),
  hardware_set VARCHAR(128),
  risk_level VARCHAR(64),
  confidence VARCHAR(64),
  payload JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS hardware_sets (
  id BIGSERIAL PRIMARY KEY,
  run_id UUID NOT NULL REFERENCES pdf_runs(id),
  hardware_set VARCHAR(128),
  status VARCHAR(128),
  item_count INTEGER NOT NULL DEFAULT 0,
  payload JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS hardware_items (
  id BIGSERIAL PRIMARY KEY,
  run_id UUID NOT NULL REFERENCES pdf_runs(id),
  hardware_set_id BIGINT REFERENCES hardware_sets(id),
  item_no VARCHAR(64),
  qty VARCHAR(64),
  description TEXT,
  catalog_number VARCHAR(255),
  manufacturer VARCHAR(255),
  finish VARCHAR(128),
  payload JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS rfi_items (
  id BIGSERIAL PRIMARY KEY,
  run_id UUID NOT NULL REFERENCES pdf_runs(id),
  priority VARCHAR(64),
  category VARCHAR(255),
  question TEXT,
  source VARCHAR(255),
  payload JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS audit_events (
  id BIGSERIAL PRIMARY KEY,
  organization_id UUID NOT NULL REFERENCES organizations(id),
  user_id UUID REFERENCES users(id),
  action VARCHAR(128) NOT NULL,
  entity_type VARCHAR(128) NOT NULL,
  entity_id VARCHAR(128),
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_users_organization_id ON users(organization_id);
CREATE INDEX IF NOT EXISTS ix_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS ix_user_sessions_expires_at ON user_sessions(expires_at);
CREATE INDEX IF NOT EXISTS ix_pdf_runs_org_created ON pdf_runs(organization_id, created_at);
CREATE INDEX IF NOT EXISTS ix_pdf_runs_user_created ON pdf_runs(user_id, created_at);
CREATE INDEX IF NOT EXISTS ix_pdf_runs_source_sha256 ON pdf_runs(source_sha256);
CREATE INDEX IF NOT EXISTS ix_pdf_run_logs_run_created ON pdf_run_logs(run_id, created_at);
CREATE INDEX IF NOT EXISTS ix_pdf_run_logs_user_created ON pdf_run_logs(user_id, created_at);
CREATE INDEX IF NOT EXISTS ix_extracted_doors_run_id ON extracted_doors(run_id);
CREATE INDEX IF NOT EXISTS ix_extracted_doors_hardware_set ON extracted_doors(hardware_set);
CREATE INDEX IF NOT EXISTS ix_hardware_sets_run_id ON hardware_sets(run_id);
CREATE INDEX IF NOT EXISTS ix_hardware_sets_hardware_set ON hardware_sets(hardware_set);
CREATE INDEX IF NOT EXISTS ix_hardware_items_run_id ON hardware_items(run_id);
CREATE INDEX IF NOT EXISTS ix_hardware_items_set_id ON hardware_items(hardware_set_id);
CREATE INDEX IF NOT EXISTS ix_rfi_items_run_id ON rfi_items(run_id);
CREATE INDEX IF NOT EXISTS ix_rfi_items_priority ON rfi_items(priority);
CREATE INDEX IF NOT EXISTS ix_audit_events_org_created ON audit_events(organization_id, created_at);
CREATE INDEX IF NOT EXISTS ix_audit_events_user_created ON audit_events(user_id, created_at);
