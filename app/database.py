# type: ignore
from dataclasses import asdict
import os

import apsw
import apsw.ext
import apsw.bestpractice

from textwrap import dedent
from .config import DB_PATH

apsw.bestpractice.apply(apsw.bestpractice.recommended)
apsw.ext.log_sqlite()

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

def _conn(dc=False):
    conn = apsw.Connection(DB_PATH)
    if dc: conn.row_trace = apsw.ext.DataClassRowFactory()
    return conn

def query_one(query, params=()):
    with _conn(dc=True) as conn:
        row = conn.execute(query, params).fetchone()
        if row: return asdict(row)
        return None

def query_all(query, params=()):
    with _conn(dc=True) as conn:
        rows = conn.execute(query, params).fetchall()
        if rows: return [asdict(row) for row in rows]
        return []

# def insert(table, data):
#     """Insert data into a table and return the ID"""
#     with _conn() as conn:
#         columns = ", ".join(data.keys())
#         placeholders = ", ".join(["?"] * len(data))
#         query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
#         cursor = conn.cursor()
#         cursor.execute(query, list(data.values()))
#         return conn.last_insert_rowid()

# def update(table, id, data):
#     """Update data in a table by ID"""
#     with _conn() as conn:
#         set_clause = ", ".join([f"{key} = ?" for key in data.keys()])
#         query = f"UPDATE {table} SET {set_clause} WHERE id = ?"
#         cursor = conn.cursor()
#         cursor.execute(query, list(data.values()) + [id])
#         return id

def init_db(replace=False):
    """Initialize the database with tables"""
    with _conn() as conn:
        # Tiers table
        if replace:
            conn.execute(dedent("""
                DROP TABLE IF EXISTS tiers;
                DROP TABLE IF EXISTS users;
                DROP TABLE IF EXISTS subscriptions;
                DROP TABLE IF EXISTS transactions;
                DROP TABLE IF EXISTS podcasts;
                DROP TABLE IF EXISTS preferences;
                DROP TABLE IF EXISTS audio;
                DROP TABLE IF EXISTS transcripts;
            """))

        conn.execute(dedent("""
            CREATE TABLE IF NOT EXISTS tiers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                product_id TEXT UNIQUE,
                monthly_credits INTEGER NOT NULL,
                price INTEGER NOT NULL,
                duration TEXT DEFAULT 'monthly',
                is_consumable BOOLEAN DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
        """))

        # Users table
        conn.execute(dedent("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                apple_id TEXT NOT NULL UNIQUE,
                email TEXT UNIQUE,
                firstname TEXT,
                lastname TEXT,
                balance INTEGER DEFAULT 3 NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
        """))

        # Subscriptions table
        conn.execute(dedent("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                tier_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'expired', 'trial', 'canceled')),
                original_transaction_id TEXT,
                latest_receipt TEXT,
                expiration_date TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (tier_id) REFERENCES tiers (id) ON DELETE CASCADE
            );
        """))

        # Transactions table
        conn.execute(dedent("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                type TEXT NOT NULL CHECK (type IN ('subscription', 'purchase', 'usage', 'refund')),
                amount INTEGER NOT NULL,
                reference_id INTEGER,
                transaction_id TEXT,
                receipt_data TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            );
        """))

        # Podcasts table
        conn.execute(dedent("""
            CREATE TABLE IF NOT EXISTS podcasts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                topic TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
                credits_used INTEGER DEFAULT 1 NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            );
        """))

        # Preferences table
        conn.execute(dedent("""
            CREATE TABLE IF NOT EXISTS preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                podcast_id INTEGER NOT NULL UNIQUE,
                voice_id TEXT DEFAULT 'default',
                level TEXT CHECK (level IN ('beginner', 'intermediate', 'advanced')),
                length TEXT CHECK (length IN ('5', '10', '15')),
                custom_instruction TEXT,
                FOREIGN KEY (podcast_id) REFERENCES podcasts (id) ON DELETE CASCADE
            );
        """))

        # Audio table
        conn.execute(dedent("""
            CREATE TABLE IF NOT EXISTS audio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                podcast_id INTEGER NOT NULL UNIQUE,
                path TEXT NOT NULL,
                duration INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (podcast_id) REFERENCES podcasts (id) ON DELETE CASCADE
            );
        """))

        # Transcripts table
        conn.execute(dedent("""
            CREATE TABLE IF NOT EXISTS transcripts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                podcast_id INTEGER NOT NULL UNIQUE,
                content TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (podcast_id) REFERENCES podcasts (id) ON DELETE CASCADE
            );
        """))

        # Create trigger for user timestamps
        conn.execute(dedent("""
            CREATE TRIGGER IF NOT EXISTS update_user_timestamp
            AFTER UPDATE ON users
            BEGIN
                UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
            END;
        """))

        # Insert default tiers
        tiers = [
            ("Free", "com.moonfish.free", 3, 0, "monthly", 0),
            ("Basic", "com.moonfish.basic", 12, 499, "monthly", 0),
            ("Premium", "com.moonfish.premium", 30, 999, "monthly", 0),
        ]

        conn.executemany(
            "INSERT OR IGNORE INTO tiers (name, product_id, monthly_credits, price, duration, is_consumable) VALUES (?, ?, ?, ?, ?, ?)",
            tiers
        )
