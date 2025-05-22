import os
from textwrap import dedent
from typing import Dict, Optional

import apsw
import apsw.bestpractice
import apsw.ext

from app.config import DB_PATH

apsw.bestpractice.apply(apsw.bestpractice.recommended)
apsw.ext.log_sqlite()


class DB:
    def __init__(self, path=DB_PATH, dc=True):
        self._path = path
        self._dc = dc

    def __enter__(self):
        self._conn = apsw.Connection(self._path)
        if self._dc:
            self._conn.row_trace = apsw.ext.DataClassRowFactory()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._conn:
            self._conn.close()
            self._conn = None

    def select(self, table, columns, where: Optional[Dict] = None, limit: Optional[int] = None):
        select_clause = ", ".join(columns)
        bindings = []
        statements = f"select {select_clause} from {table}"
        if where:
            where_clause = " and ".join([f"{key} = ?" for key in where.keys()])
            statements += f" where {where_clause}"
            bindings.extend(where.values())
        if limit:
            statements += " limit ?"
            bindings.append(limit)
        return self._conn.execute(statements, tuple(bindings))

    def insert(self, table, values):
        columns = ", ".join(values.keys())
        placeholders = ", ".join(["?"] * len(values))
        statements = f"insert into {table} ({columns}) values ({placeholders}) returning *;"
        bindings = tuple(values.values())
        return self._conn.execute(statements, bindings)

    def update(self, table: str, values: dict, where: dict):
        set_clause = ", ".join([f"{key} = ?" for key in values.keys()])
        where_clause = " and ".join([f"{key} = ?" for key in where.keys()])
        statements = f"update {table} set {set_clause} where {where_clause} returning *;"
        bindings = tuple(list(values.values()) + list(where.values()))
        return self._conn.execute(statements, bindings)

    def delete(self, table, where):
        where_clause = " and ".join([f"{key} = ?" for key in where.keys()])
        statements = f"delete from {table} where {where_clause} returning *;"
        bindings = tuple(where.values())
        return self._conn.execute(statements, bindings)


def init_db(db_path=DB_PATH, recreate=False):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = apsw.Connection(db_path)
    with conn:
        # Tiers table
        if recreate:
            conn.execute("DROP TABLE IF EXISTS users")
            conn.execute("DROP TABLE IF EXISTS podcasts")
            conn.execute("DROP TABLE IF EXISTS transactions")
            conn.execute("DROP TABLE IF EXISTS subscriptions")
            conn.execute("DROP TABLE IF EXISTS auth_accounts")
            conn.execute("DROP TABLE IF EXISTS tiers")
            conn.execute("DROP TRIGGER IF EXISTS update_podcasts_timestamp")

        conn.execute(
            dedent("""
            CREATE TABLE IF NOT EXISTS tiers (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                product_id TEXT UNIQUE,
                monthly_credits INTEGER NOT NULL,
                price INTEGER NOT NULL,
                duration TEXT DEFAULT 'monthly',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
        """)
        )

        # Users table
        conn.execute(
            dedent("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                email TEXT UNIQUE,
                first_name TEXT,
                last_name TEXT,
                balance INTEGER DEFAULT 3 NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
        """)
        )

        # Auths table
        conn.execute(
            dedent("""
            CREATE TABLE IF NOT EXISTS auth_accounts (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                provider TEXT NOT NULL,
                provider_user_id TEXT NOT NULL,
                refresh_token TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            );
        """)
        )

        # Auth sessions table
        conn.execute(
            dedent("""
            CREATE TABLE IF NOT EXISTS auth_sessions (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                refresh_token TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            );
        """)
        )

        # Transactions table
        conn.execute(
            dedent("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                type TEXT NOT NULL CHECK (type IN ('subscription', 'purchase', 'usage', 'refund')),
                amount INTEGER NOT NULL,
                reference_id INTEGER,
                transaction_id TEXT,
                receipt_data TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            );
        """)
        )

        # Podcasts table
        conn.execute(
            dedent("""
            CREATE TABLE IF NOT EXISTS podcasts (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                topic TEXT NOT NULL,
                length TEXT NOT NULL CHECK (length IN ('short', 'medium', 'long')),
                level TEXT NOT NULL CHECK (level IN ('beginner', 'intermediate', 'advanced')),
                format TEXT NOT NULL CHECK (format IN ('narrative', 'conversational')),
                voice TEXT NOT NULL CHECK (voice IN ('male', 'female')),
                instruction TEXT,

                status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'active', 'completed', 'cancelled')),
                step TEXT CHECK (step IN('research', 'compose', 'voice')),
                progress INTEGER NOT NULL DEFAULT 0,

                title TEXT,
                summary TEXT,
                transcript TEXT,
                audio_url TEXT,
                duration INTEGER,

                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            );
        """)
        )

        # Timestamp trigger
        conn.execute(
            dedent("""
            CREATE TRIGGER IF NOT EXISTS update_podcasts_timestamp
            AFTER UPDATE ON podcasts
            FOR EACH ROW
            BEGIN
                UPDATE podcasts SET updated_at = CURRENT_TIMESTAMP WHERE id = OLD.id;
            END;
        """)
        )

        # Insert default tiers
        tiers = [
            ("Free", "com.moonfish.free", 3, 0, "monthly"),
            ("Basic", "com.moonfish.basic", 12, 499, "monthly"),
            ("Premium", "com.moonfish.premium", 30, 999, "monthly"),
        ]

        conn.executemany(
            "INSERT OR IGNORE INTO tiers (name, product_id, monthly_credits, price, duration) VALUES (?, ?, ?, ?, ?)",
            tiers,
        )


def get_db():
    with DB() as db:
        yield db
