CREATE TABLE IF NOT EXISTS child_activity (
  child_id TEXT NOT NULL REFERENCES child_profiles(id) ON DELETE CASCADE,
  lane TEXT NOT NULL CHECK(lane IN ('story','discovery','craft')),
  item_id TEXT NOT NULL,
  completed_at TEXT NOT NULL,
  PRIMARY KEY(child_id,lane,item_id)
);
