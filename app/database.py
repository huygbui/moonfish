import apsw
import apsw.ext
import apsw.bestpractice

from textwrap import dedent
from config import DB_PATH

apsw.bestpractice.apply(apsw.bestpractice.recommended)
apsw.ext.log_sqlite()

conn = apsw.Connection(DB_PATH)
conn.execute("DROP TABLE IF EXISTS users")
with conn:
    conn.execute(dedent("""
        CREATE TABLE IF NOT EXISTS tiers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            monthly_credits INTEGER NOT NULL,
            price INTEGER NOT NULL
        )
    """))

    conn.execute(dedent("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            apple_id TEXT UNIQUE,
            email TEXT NOT NULL UNIQUE,
            name TEXT,
            balance INTEGER DEFAULT 3 NOT NULL,
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
            user_id INTEGER NOT NULL,
            topic TEXT NOT NULL,
            title TEXT,
            status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'processing', 'completed', 'error')),
            credits_used INTEGER DEFAULT 0 NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
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
            FOREIGN KEY (podcast_id) REFERENCES podcasts (id) ON DELETE CASCADE
        )
    """))

    conn.execute(dedent("""
        CREATE TABLE IF NOT EXISTS preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            podcast_id INTEGER UNIQUE,
            level TEXT CHECK(level IN ('beginner', 'intermediate', 'advanced')),
            length TEXT CHECK(length IN ('short', 'medium', 'long')),
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (podcast_id) REFERENCES podcasts (id) ON DELETE CASCADE
        )
    """))

    conn.execute(dedent("""
        CREATE TABLE IF NOT EXISTS transcripts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            podcast_id INTEGER NOT NULL UNIQUE,
            content TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (podcast_id) REFERENCES podcasts (id) ON DELETE CASCADE
        );
    """))

    conn.execute(dedent("""
        CREATE TABLE IF NOT EXISTS audio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            podcast_id INTEGER NOT NULL UNIQUE,
            path TEXT NOT NULL,
            duration INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (podcast_id) REFERENCES podcasts (id) ON DELETE CASCADE
        )
    """))


qry = "SELECT * FROM users"
print(apsw.ext.format_query_table(conn, qry))
