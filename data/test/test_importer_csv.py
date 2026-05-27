import sqlite3
import pandas as pd
import pytest
from pathlib import Path


@pytest.fixture
def base(tmp_path):
    chemin = tmp_path / "urls.db"
    with sqlite3.connect(chemin) as conn:
        conn.executescript("""
            CREATE TABLE urls (
                id    INTEGER PRIMARY KEY,
                media TEXT NOT NULL,
                url   TEXT NOT NULL,
                etat  INTEGER NOT NULL DEFAULT 0
            );
        """)
    return chemin


@pytest.fixture
def csv_simple(tmp_path):
    chemin = tmp_path / "le_monde_articles.csv"
    chemin.write_text("sitemap,url\nhttp://s1,http://url1\nhttp://s2,http://url2\n")
    return chemin


def test_import_lignes(base, csv_simple):
    with sqlite3.connect(base) as conn:
        df = pd.read_csv(csv_simple, usecols=["url"])
        df["media"] = csv_simple.stem.removesuffix("_articles")
        df.to_sql("urls", conn, if_exists="append", index=False)

    with sqlite3.connect(base) as conn:
        rows = conn.execute("SELECT media, url, etat FROM urls").fetchall()

    assert len(rows) == 2
    assert rows[0] == ("le_monde", "http://url1", 0)
    assert rows[1] == ("le_monde", "http://url2", 0)


def test_import_id_autoincrement(base, csv_simple):
    with sqlite3.connect(base) as conn:
        df = pd.read_csv(csv_simple, usecols=["url"])
        df["media"] = csv_simple.stem.removesuffix("_articles")
        df.to_sql("urls", conn, if_exists="append", index=False)

    with sqlite3.connect(base) as conn:
        ids = [r[0] for r in conn.execute("SELECT id FROM urls").fetchall()]

    assert ids == [1, 2]
