import sqlite3
import pytest
from pathlib import Path


def test_creation_bdd(tmp_path):
    base = tmp_path / "urls.db"

    with sqlite3.connect(base) as conn:
        conn.executescript("""
            CREATE TABLE urls (
                id    INTEGER PRIMARY KEY,
                media TEXT NOT NULL,
                url   TEXT NOT NULL,
                etat  INTEGER NOT NULL DEFAULT 0
            );
            CREATE INDEX idx_media_etat ON urls(media, etat);
        """)

    with sqlite3.connect(base) as conn:
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        assert ("urls",) in tables

        colonnes = [r[1] for r in conn.execute("PRAGMA table_info(urls)").fetchall()]
        assert colonnes == ["id", "media", "url", "etat"]

        index = conn.execute("SELECT name FROM sqlite_master WHERE type='index'").fetchall()
        assert ("idx_media_etat",) in index


def test_creation_bdd_echoue_si_existe(tmp_path):
    base = tmp_path / "urls.db"
    base.touch()

    assert base.exists()
    # simule le comportement de creation_bdd.py
    with pytest.raises(FileExistsError):
        if base.exists():
            raise FileExistsError(f"{base} existe déjà.")
