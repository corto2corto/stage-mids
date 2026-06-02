import sqlite3

BASE = "/data/elias/stage-mids/data/urls.db"

with sqlite3.connect(BASE) as conn:
    conn.executescript("""
        CREATE TABLE urls (
            id    INTEGER PRIMARY KEY,
            media TEXT NOT NULL,
            url   TEXT NOT NULL,
            etat  INTEGER NOT NULL DEFAULT 0
        );
        CREATE INDEX idx_media_etat ON urls(media, etat);
    """)
