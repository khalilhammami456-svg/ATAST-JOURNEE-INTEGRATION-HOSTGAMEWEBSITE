-- Subscriptions (cotisations) and Excel imports.
-- A subscription row is the proof that someone paid for a season. It exists BEFORE the person has an account
-- (imported from the treasurer's Excel list => status AVAILABLE) and becomes CLAIMED once the person is a member.
-- Amounts are stored in minor units (millimes), like event prices.

CREATE TABLE import_batches (
  id               TEXT PRIMARY KEY,
  filename         TEXT NOT NULL,
  season           TEXT NOT NULL,          -- e.g. 2025-2026
  rows_total       INTEGER NOT NULL,
  rows_imported    INTEGER NOT NULL,
  rows_skipped     INTEGER NOT NULL,
  auto_accepted    INTEGER NOT NULL DEFAULT 0,   -- pending requests accepted automatically by this import
  renewals         INTEGER NOT NULL DEFAULT 0,   -- existing members whose subscription was recorded
  created_by       TEXT REFERENCES users (id),
  created_at       TEXT NOT NULL,
  reverted_at      TEXT,
  reverted_by      TEXT REFERENCES users (id)
);
CREATE INDEX ix_import_batches_created ON import_batches (created_at);

CREATE TABLE subscriptions (
  id         TEXT PRIMARY KEY,
  batch_id   TEXT REFERENCES import_batches (id),   -- NULL when entered by hand
  season     TEXT NOT NULL CHECK (season GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9]'),
  name       TEXT NOT NULL,
  email      TEXT NOT NULL,
  phone      TEXT NOT NULL,
  amount     INTEGER CHECK (amount IS NULL OR amount > 0),   -- minor units, optional
  paid_at    TEXT,                                           -- YYYY-MM-DD, optional
  reference  TEXT,                                           -- receipt number, optional
  status     TEXT NOT NULL DEFAULT 'AVAILABLE' CHECK (status IN ('AVAILABLE', 'CLAIMED', 'REVOKED')),
  user_id    TEXT REFERENCES users (id),                     -- set when CLAIMED
  claimed_at TEXT,
  created_by TEXT REFERENCES users (id),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  CHECK ((status = 'CLAIMED') = (user_id IS NOT NULL))
);
-- One live subscription per person and season.
CREATE UNIQUE INDEX ux_subscriptions_email_season ON subscriptions (lower(email), season)
  WHERE status IN ('AVAILABLE', 'CLAIMED');
CREATE INDEX ix_subscriptions_user ON subscriptions (user_id, season);
CREATE INDEX ix_subscriptions_status ON subscriptions (status, season);
CREATE INDEX ix_subscriptions_batch ON subscriptions (batch_id);
CREATE INDEX ix_subscriptions_email ON subscriptions (lower(email));

-- Requests accepted by the system (paid list match) instead of an administrator.
ALTER TABLE membership_requests ADD COLUMN auto_accepted INTEGER NOT NULL DEFAULT 0;
