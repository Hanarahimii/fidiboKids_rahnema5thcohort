CREATE TABLE IF NOT EXISTS discovery_topics (
    id TEXT PRIMARY KEY,
    position INTEGER NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','published','archived'))
);
CREATE TABLE IF NOT EXISTS discovery_revisions (
    id TEXT PRIMARY KEY,
    topic_id TEXT NOT NULL REFERENCES discovery_topics(id),
    language TEXT NOT NULL CHECK(language IN ('fa','azb')),
    revision_no INTEGER NOT NULL,
    payload_json TEXT NOT NULL CHECK(json_valid(payload_json)),
    created_at TEXT NOT NULL,
    UNIQUE(topic_id,language,revision_no)
);
CREATE TABLE IF NOT EXISTS discovery_publications (
    topic_id TEXT NOT NULL REFERENCES discovery_topics(id),
    language TEXT NOT NULL CHECK(language IN ('fa','azb')),
    revision_id TEXT NOT NULL REFERENCES discovery_revisions(id),
    PRIMARY KEY(topic_id,language)
);
CREATE TABLE IF NOT EXISTS discovery_recordings (
    id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL UNIQUE,
    topic_id TEXT NOT NULL REFERENCES discovery_topics(id),
    scene_id TEXT NOT NULL,
    language TEXT NOT NULL CHECK(language IN ('fa','azb')),
    revision_id TEXT NOT NULL REFERENCES discovery_revisions(id),
    duration_ms INTEGER NOT NULL,
    mime TEXT NOT NULL,
    raw_path TEXT NOT NULL,
    published_path TEXT,
    file_hash TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','published','rejected')),
    submitted_at TEXT NOT NULL,
    published_at TEXT
);
CREATE INDEX IF NOT EXISTS discovery_recordings_scene ON discovery_recordings(topic_id,scene_id,language,status);
