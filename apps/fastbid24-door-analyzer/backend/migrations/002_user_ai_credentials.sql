CREATE TABLE IF NOT EXISTS user_ai_credentials (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id UUID NOT NULL REFERENCES organizations(id),
  user_id UUID NOT NULL REFERENCES users(id),
  provider VARCHAR(64) NOT NULL DEFAULT 'analysis',
  encrypted_api_key TEXT NOT NULL,
  key_fingerprint VARCHAR(64) NOT NULL,
  key_hint VARCHAR(32),
  created_by_user_id UUID REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_user_ai_credentials_user_id UNIQUE (user_id)
);

CREATE INDEX IF NOT EXISTS ix_user_ai_credentials_org_user ON user_ai_credentials(organization_id, user_id);
