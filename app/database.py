import apsw
import apsw.ext
import apsw.bestpractice

from pathlib import Path
from textwrap import dedent
from config import DB_PATH

apsw.bestpractice.apply(apsw.bestpractice.recommended)
apsw.ext.log_sqlite()

conn = apsw.Connection(DB_PATH)
conn.execute("DROP TABLE IF EXISTS users")
with conn:
    conn.execute(dedent("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            apple_id TEXT UNIQUE,
            email TEXT NOT NULL UNIQUE,
            name TEXT,
            balance INTEGER DEFAULT 3,
            tier_id INTEGER,
            reset_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (tier_id) REFERENCES tiers (id)
        );
    """))

    conn.execute(dedent("""
        CREATE TABLE IF NOT EXISTS podcasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            topic TEXT,
            transcript TEXT,
            title TEXT,
            status TEXT DEFAULT 'pending',
            credits_used INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """))

    conn.execute(dedent("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            podcast_id INTEGER,
            role TEXT,
            content TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(podcast_id, created_at),
            FOREIGN KEY (podcast_id) REFERENCES podcasts (id)
        )
    """))

    conn.execute(dedent("""
        CREATE TABLE IF NOT EXISTS preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            podcast_id INTEGER UNIQUE,
            level TEXT,
            length TEXT,
            style TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (podcast_id) REFERENCES PODCASTS (id)
        )
    """))

    conn.execute(dedent("""
        CREATE TABLE IF NOT EXISTS audio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            podcast_id INTEGER UNIQUE,
            path TEXT,
            duration INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (podcast_id) REFERENCES podcasts (id)
        )
    """))

    conn.execute(dedent("""
        CREATE TABLE IF NOT EXISTS tiers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            monthly_credits INTEGER,
            price INTEGER
        )
    """))

qry = "SELECT * FROM users"
print(apsw.ext.format_query_table(conn, qry))
