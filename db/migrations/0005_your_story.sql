CREATE TABLE IF NOT EXISTS your_stories (
    id TEXT PRIMARY KEY,
    position INTEGER NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','published','archived'))
);
CREATE TABLE IF NOT EXISTS your_story_revisions (
    id TEXT PRIMARY KEY,
    story_id TEXT NOT NULL REFERENCES your_stories(id),
    language TEXT NOT NULL CHECK(language IN ('fa','azb')),
    revision_no INTEGER NOT NULL,
    payload_json TEXT NOT NULL CHECK(json_valid(payload_json)),
    created_at TEXT NOT NULL,
    UNIQUE(story_id, language, revision_no)
);
CREATE TABLE IF NOT EXISTS your_story_publications (
    story_id TEXT NOT NULL REFERENCES your_stories(id),
    language TEXT NOT NULL CHECK(language IN ('fa','azb')),
    revision_id TEXT NOT NULL REFERENCES your_story_revisions(id),
    PRIMARY KEY(story_id, language)
);
CREATE TABLE IF NOT EXISTS your_story_recordings (
    id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL UNIQUE,
    story_id TEXT NOT NULL REFERENCES your_stories(id),
    scene_id TEXT NOT NULL,
    language TEXT NOT NULL CHECK(language IN ('fa','azb')),
    revision_id TEXT NOT NULL REFERENCES your_story_revisions(id),
    duration_ms INTEGER NOT NULL,
    mime TEXT NOT NULL,
    raw_path TEXT NOT NULL,
    published_path TEXT,
    file_hash TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','published','rejected')),
    submitted_at TEXT NOT NULL,
    published_at TEXT
);
CREATE INDEX IF NOT EXISTS your_story_recordings_scene
    ON your_story_recordings(story_id,scene_id,language,status);
