-- RHOBEAR Rep Card — prototype schema (single tenant hardcoded; multi-tenancy is Phase 0, not this)
CREATE TABLE IF NOT EXISTS reps (
  id          SERIAL PRIMARY KEY,
  slug        TEXT UNIQUE NOT NULL,
  name        TEXT NOT NULL,
  title       TEXT,
  company     TEXT,
  phone       TEXT,
  email       TEXT,
  photo_url   TEXT,
  accent      TEXT DEFAULT '#4A9EFF',
  book_url    TEXT,
  blurb       TEXT,
  created_at  TIMESTAMPTZ DEFAULT now()
);

-- one row per card send (rep -> prospect number)
CREATE TABLE IF NOT EXISTS sends (
  id          SERIAL PRIMARY KEY,
  rep_id      INT REFERENCES reps(id) ON DELETE CASCADE,
  to_phone    TEXT NOT NULL,
  label       TEXT,
  token       TEXT UNIQUE NOT NULL,
  sent_at     TIMESTAMPTZ DEFAULT now()
);

-- every touch on a card
CREATE TABLE IF NOT EXISTS events (
  id          BIGSERIAL PRIMARY KEY,
  send_id     INT REFERENCES sends(id) ON DELETE CASCADE,
  rep_id      INT REFERENCES reps(id) ON DELETE CASCADE,
  kind        TEXT NOT NULL,      -- view | dwell | scroll | tap_call | tap_text | tap_book | tap_save
  meta        TEXT,
  ua          TEXT,
  at          TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS events_send_idx ON events(send_id);
CREATE INDEX IF NOT EXISTS events_at_idx   ON events(at DESC);
