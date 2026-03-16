-- Creation of the preferences table
CREATE TABLE IF NOT EXISTS preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    interested_in_gender TEXT NOT NULL DEFAULT 'everyone' CHECK(interested_in_gender IN ('male', 'female', 'everyone')),
    min_age INTEGER NOT NULL DEFAULT 18,
    max_age INTEGER NOT NULL DEFAULT 99,
    max_distance_km INTEGER NOT NULL DEFAULT 100,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
