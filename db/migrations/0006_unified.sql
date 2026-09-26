CREATE TABLE IF NOT EXISTS craft_activities (
    id TEXT PRIMARY KEY,
    position INTEGER NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','published','archived')),
    payload_json TEXT NOT NULL CHECK(json_valid(payload_json)),
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS child_profiles (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    birth_date TEXT NOT NULL DEFAULT '',
    avatar TEXT NOT NULL DEFAULT '',
    daily_limit_min INTEGER NOT NULL DEFAULT 30,
    entry_code TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL
);
