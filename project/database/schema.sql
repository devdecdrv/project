-- Batches (courses/playlists)
CREATE TABLE IF NOT EXISTS batches (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    subject     TEXT,
    slug        TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Topics within a batch
CREATE TABLE IF NOT EXISTS topics (
    id          TEXT PRIMARY KEY,
    batch_id    TEXT REFERENCES batches(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    slug        TEXT,
    sort_order  INT DEFAULT 0
);

-- Videos
CREATE TABLE IF NOT EXISTS videos (
    id              TEXT PRIMARY KEY,
    batch_id        TEXT REFERENCES batches(id) ON DELETE CASCADE,
    topic_id        TEXT REFERENCES topics(id) ON DELETE SET NULL,
    title           TEXT NOT NULL,
    video_key       TEXT,                   -- PW's internal key
    duration_secs   INT,
    thumbnail_url   TEXT,
    video_type      TEXT DEFAULT 'pw',      -- pw | youtube | etc
    pw_url          TEXT,                   -- original PW stream URL (m3u8 or mp4)
    subject_id      TEXT,
    subject_slug    TEXT,
    topic_slug      TEXT,
    scraped_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_videos_batch ON videos(batch_id);
CREATE INDEX IF NOT EXISTS idx_videos_topic ON videos(topic_id);
