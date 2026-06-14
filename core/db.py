import sqlite3
from core.config import DB_PATH


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    with conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS oauth_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service TEXT NOT NULL UNIQUE,
                access_token TEXT NOT NULL,
                refresh_token TEXT,
                expires_at INTEGER,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS purchase_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                store TEXT NOT NULL,
                item_name TEXT NOT NULL,
                normalized_name TEXT,
                purchased_at DATE,
                price REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS recurring_bills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                amount REAL,
                due_day INTEGER,
                frequency TEXT DEFAULT 'monthly',
                plaid_merchant TEXT,
                active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS sale_alerts_sent (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                store TEXT NOT NULL,
                item_name TEXT NOT NULL,
                sale_price REAL,
                regular_price REAL,
                week_of DATE,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
    conn.close()


if __name__ == "__main__":
    init_db()
    print("Database initialized.")
