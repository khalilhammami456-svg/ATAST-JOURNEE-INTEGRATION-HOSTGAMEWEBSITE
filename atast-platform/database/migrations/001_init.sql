-- ATAST initial schema (see documentation.tex, chapter "Database Design")
-- Dates are ISO-8601 strings (UTC). Prices are stored in minor units
-- (millimes for TND, cents for EUR/USD) to avoid floating point errors.

CREATE TABLE users (
  id             TEXT PRIMARY KEY,
  name           TEXT NOT NULL,
  email          TEXT NOT NULL,
  password_hash  TEXT NOT NULL,
  phone          TEXT NOT NULL,
  profile_photo  TEXT,
  description    TEXT,
  birthday       TEXT,
  instagram      TEXT,
  facebook       TEXT,
  github         TEXT,
  linkedin       TEXT,
  role           TEXT NOT NULL CHECK (role IN ('ADMIN', 'MEMBER')),
  status         TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'SUSPENDED', 'DEACTIVATED')),
  created_at     TEXT NOT NULL,
  updated_at     TEXT NOT NULL
);
-- Business rule: one active email cannot belong to several active accounts.
CREATE UNIQUE INDEX ux_users_active_email ON users (lower(email)) WHERE status = 'ACTIVE';
CREATE INDEX ix_users_name ON users (name COLLATE NOCASE);
CREATE INDEX ix_users_role_status ON users (role, status);

CREATE TABLE membership_requests (
  id               TEXT PRIMARY KEY,
  name             TEXT NOT NULL,
  email            TEXT NOT NULL,
  phone            TEXT NOT NULL,
  password_hash    TEXT,            -- moved to the user account (and cleared) on acceptance;
                                    -- kept on rejection only so the applicant can read the reason
  status           TEXT NOT NULL DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'ACCEPTED', 'REJECTED')),
  rejection_reason TEXT,
  user_id          TEXT REFERENCES users (id),
  created_at       TEXT NOT NULL,
  reviewed_at      TEXT,
  reviewed_by      TEXT REFERENCES users (id)
);
CREATE UNIQUE INDEX ux_requests_pending_email ON membership_requests (lower(email)) WHERE status = 'PENDING';
CREATE INDEX ix_requests_status ON membership_requests (status, created_at);
CREATE INDEX ix_requests_email ON membership_requests (lower(email));

CREATE TABLE events (
  id              TEXT PRIMARY KEY,
  title           TEXT NOT NULL,
  description     TEXT NOT NULL DEFAULT '',
  type            TEXT NOT NULL CHECK (type IN ('SMALL', 'MEDIUM', 'BIG', 'MEETING')),
  date            TEXT NOT NULL,     -- YYYY-MM-DD
  time            TEXT NOT NULL,     -- HH:MM
  location        TEXT NOT NULL,
  is_free         INTEGER NOT NULL CHECK (is_free IN (0, 1)),
  price           INTEGER NOT NULL DEFAULT 0,  -- minor units
  currency        TEXT NOT NULL DEFAULT 'TND',
  image_url       TEXT,
  additional_info TEXT,
  status          TEXT NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT', 'PUBLISHED', 'COMPLETED', 'ARCHIVED')),
  created_by      TEXT REFERENCES users (id),
  created_at      TEXT NOT NULL,
  updated_at      TEXT NOT NULL,
  -- FR-09: free => price 0 ; paid => price > 0
  CHECK ((is_free = 1 AND price = 0) OR (is_free = 0 AND price > 0))
);
CREATE INDEX ix_events_status_date ON events (status, date, time);
CREATE INDEX ix_events_type ON events (type);
CREATE INDEX ix_events_title ON events (title COLLATE NOCASE);

CREATE TABLE event_participations (
  id             TEXT PRIMARY KEY,
  event_id       TEXT NOT NULL REFERENCES events (id),
  member_id      TEXT NOT NULL REFERENCES users (id),
  status         TEXT NOT NULL CHECK (status IN ('REGISTERED', 'VALIDATED', 'REMOVED')),
  points_awarded INTEGER NOT NULL DEFAULT 0,
  validated_at   TEXT,
  validated_by   TEXT REFERENCES users (id),
  created_at     TEXT NOT NULL,
  updated_at     TEXT NOT NULL
);
-- FR-13: no duplicate active/validated participation for the same (event, member)
CREATE UNIQUE INDEX ux_participation_active ON event_participations (event_id, member_id)
  WHERE status IN ('REGISTERED', 'VALIDATED');
CREATE INDEX ix_participation_member ON event_participations (member_id, status);
CREATE INDEX ix_participation_event ON event_participations (event_id, status);

CREATE TABLE messages (
  id         TEXT PRIMARY KEY,
  title      TEXT NOT NULL,
  content    TEXT NOT NULL,
  sender_id  TEXT NOT NULL REFERENCES users (id),
  created_at TEXT NOT NULL
);
CREATE INDEX ix_messages_created ON messages (created_at);

CREATE TABLE suggestions (
  id         TEXT PRIMARY KEY,
  member_id  TEXT NOT NULL REFERENCES users (id),
  title      TEXT,
  content    TEXT NOT NULL,
  status     TEXT NOT NULL DEFAULT 'NEW' CHECK (status IN ('NEW', 'READ', 'IN_REVIEW', 'RESOLVED')),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX ix_suggestions_status ON suggestions (status, created_at);
CREATE INDEX ix_suggestions_member ON suggestions (member_id);

CREATE TABLE audit_logs (
  id          TEXT PRIMARY KEY,
  actor_id    TEXT REFERENCES users (id),
  action      TEXT NOT NULL,
  entity_type TEXT NOT NULL,
  entity_id   TEXT,
  metadata    TEXT,   -- JSON, never contains passwords or secrets
  created_at  TEXT NOT NULL
);
CREATE INDEX ix_audit_created ON audit_logs (created_at);

CREATE TABLE sessions (
  id_hash    TEXT PRIMARY KEY,   -- SHA-256 of the cookie token, raw token never stored
  user_id    TEXT NOT NULL REFERENCES users (id),
  csrf_token TEXT NOT NULL,
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL
);
CREATE INDEX ix_sessions_user ON sessions (user_id);
CREATE INDEX ix_sessions_expires ON sessions (expires_at);
