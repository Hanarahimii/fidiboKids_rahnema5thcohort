CREATE TABLE IF NOT EXISTS story_ratings (
    client_id TEXT PRIMARY KEY,
    language TEXT NOT NULL CHECK (language IN ('fa', 'azb')),
    stars INTEGER NOT NULL CHECK (stars BETWEEN 1 AND 5),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
