-- YouTube Pulse: schema
-- SQLite (swap to Postgres later if you outgrow it — the shape is the same)

CREATE TABLE IF NOT EXISTS channels (
    channel_id      TEXT PRIMARY KEY,
    title           TEXT NOT NULL,
    category        TEXT,              -- e.g. 'gaming', 'music', 'indian_creators'
    subscriber_count INTEGER,
    country         TEXT,
    first_seen_at   TEXT DEFAULT (datetime('now')),
    last_updated_at TEXT
);

CREATE TABLE IF NOT EXISTS videos (
    video_id        TEXT PRIMARY KEY,
    channel_id      TEXT NOT NULL REFERENCES channels(channel_id),
    title           TEXT NOT NULL,
    category        TEXT,              -- inherited from channel or YouTube categoryId
    published_at    TEXT,
    tracked_since   TEXT DEFAULT (datetime('now')),
    is_active       INTEGER DEFAULT 1  -- stop polling old/dead videos to save quota
);

-- The core time-series table. One row per video per poll.
CREATE TABLE IF NOT EXISTS snapshots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id        TEXT NOT NULL REFERENCES videos(video_id),
    captured_at     TEXT NOT NULL DEFAULT (datetime('now')),
    view_count      INTEGER NOT NULL,
    like_count      INTEGER,
    comment_count   INTEGER
);

CREATE INDEX IF NOT EXISTS idx_snapshots_video_time
    ON snapshots(video_id, captured_at);

-- Precomputed leaderboard cache so the API never computes live on request.
-- Recomputed by momentum.py after every poll cycle.
CREATE TABLE IF NOT EXISTS leaderboard_cache (
    leaderboard     TEXT NOT NULL,     -- 'rising_now', 'most_viewed', 'hidden_gems', etc.
    rank            INTEGER NOT NULL,
    video_id        TEXT NOT NULL REFERENCES videos(video_id),
    score           REAL,
    view_growth_24h INTEGER,
    like_growth_24h INTEGER,
    total_views     INTEGER,
    computed_at     TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (leaderboard, rank)
);
