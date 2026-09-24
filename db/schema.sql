PRAGMA foreign_keys = ON;

-- Stable editorial identities. Position can change without changing IDs.
CREATE TABLE IF NOT EXISTS steps (
    id TEXT PRIMARY KEY,
    position INTEGER NOT NULL UNIQUE CHECK (position > 0),
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'archived'))
);

CREATE TABLE IF NOT EXISTS step_locales (
    step_id TEXT NOT NULL REFERENCES steps(id),
    language TEXT NOT NULL CHECK (language IN ('fa', 'azb')),
    title TEXT NOT NULL CHECK (length(trim(title)) > 0),
    PRIMARY KEY (step_id, language)
);

CREATE TABLE IF NOT EXISTS pages (
    id TEXT PRIMARY KEY,
    step_id TEXT NOT NULL REFERENCES steps(id),
    kind TEXT NOT NULL CHECK (kind IN ('story', 'lesson', 'quiz')),
    position INTEGER NOT NULL CHECK (position > 0),
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'archived')),
    created_at TEXT NOT NULL,
    archived_at TEXT,
    UNIQUE (step_id, position)
);

-- Every edit inserts a revision; raw submissions keep the revision actually read.
-- JSON payload: story/lesson {text, art_key}; quiz {questions:[...]}.
CREATE TABLE IF NOT EXISTS page_revisions (
    id TEXT PRIMARY KEY,
    page_id TEXT NOT NULL REFERENCES pages(id),
    language TEXT NOT NULL CHECK (language IN ('fa', 'azb')),
    revision_no INTEGER NOT NULL CHECK (revision_no > 0),
    payload_json TEXT NOT NULL CHECK (json_valid(payload_json)),
    created_at TEXT NOT NULL,
    UNIQUE (page_id, language, revision_no),
    UNIQUE (page_id, language, id)
);

-- Absence of a row means that locale is still in draft.
CREATE TABLE IF NOT EXISTS page_publications (
    page_id TEXT NOT NULL REFERENCES pages(id),
    language TEXT NOT NULL CHECK (language IN ('fa', 'azb')),
    revision_id TEXT NOT NULL,
    published_at TEXT NOT NULL,
    PRIMARY KEY (page_id, language),
    FOREIGN KEY (page_id, language, revision_id)
        REFERENCES page_revisions(page_id, language, id)
);

CREATE TABLE IF NOT EXISTS readings (
    id TEXT PRIMARY KEY,
    language TEXT NOT NULL CHECK (language IN ('fa', 'azb')),
    ordinal INTEGER NOT NULL CHECK (ordinal BETWEEN 1 AND 4),
    UNIQUE (language, ordinal),
    UNIQUE (id, language)
);

-- Raw paths must be private. Never mount this directory as static web content.
CREATE TABLE IF NOT EXISTS submissions (
    id TEXT PRIMARY KEY,
    client_request_id TEXT NOT NULL UNIQUE,
    submitted_at TEXT NOT NULL,
    language TEXT NOT NULL CHECK (language IN ('fa', 'azb')),
    step_id TEXT NOT NULL REFERENCES steps(id),
    page_id TEXT NOT NULL REFERENCES pages(id),
    content_revision_id TEXT NOT NULL REFERENCES page_revisions(id),
    duration_ms INTEGER NOT NULL CHECK (duration_ms > 0),
    mime_type TEXT NOT NULL,
    file_size_bytes INTEGER NOT NULL CHECK (file_size_bytes > 0),
    raw_file_ref TEXT NOT NULL UNIQUE,
    original_filename TEXT NOT NULL,
    consent_version TEXT NOT NULL,
    consent_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (
        status IN ('pending', 'review', 'screened_out', 'shortlisted',
                   'selected', 'published', 'rejected')
    ),
    review_note TEXT NOT NULL DEFAULT '',
    target_reading_id TEXT,
    published_at TEXT,
    FOREIGN KEY (target_reading_id, language) REFERENCES readings(id, language)
);

CREATE INDEX IF NOT EXISTS submissions_page_status_idx
    ON submissions(language, step_id, page_id, status);

CREATE TABLE IF NOT EXISTS submission_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    submission_id TEXT NOT NULL REFERENCES submissions(id),
    occurred_at TEXT NOT NULL,
    actor TEXT NOT NULL,
    old_status TEXT,
    new_status TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT ''
);

-- Exactly one active published asset per page/language/Reading slot.
-- The reader API must JOIN against page_publications.revision_id; a changed
-- script therefore never plays audio recorded for an older text revision.
CREATE TABLE IF NOT EXISTS published_audio (
    page_id TEXT NOT NULL REFERENCES pages(id),
    language TEXT NOT NULL CHECK (language IN ('fa', 'azb')),
    reading_id TEXT NOT NULL,
    submission_id TEXT NOT NULL REFERENCES submissions(id),
    content_revision_id TEXT NOT NULL REFERENCES page_revisions(id),
    published_file_ref TEXT NOT NULL UNIQUE,
    published_at TEXT NOT NULL,
    PRIMARY KEY (page_id, language, reading_id),
    FOREIGN KEY (reading_id, language) REFERENCES readings(id, language)
);

CREATE TABLE IF NOT EXISTS story_ratings (
    client_id TEXT PRIMARY KEY,
    language TEXT NOT NULL CHECK (language IN ('fa', 'azb')),
    stars INTEGER NOT NULL CHECK (stars BETWEEN 1 AND 5),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Optional editorial banners: cover and one image per existing step.
-- Absence of a row keeps the original illustration as a fallback.
CREATE TABLE IF NOT EXISTS site_banners (
    slot TEXT PRIMARY KEY,
    art_key TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
