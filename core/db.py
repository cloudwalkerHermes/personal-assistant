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
                upc TEXT,
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

            CREATE TABLE IF NOT EXISTS plaid_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id TEXT NOT NULL UNIQUE,
                access_token TEXT NOT NULL,
                institution_name TEXT,
                cursor TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id TEXT NOT NULL UNIQUE,
                item_id TEXT NOT NULL,
                account_id TEXT NOT NULL,
                date DATE NOT NULL,
                name TEXT,
                merchant_name TEXT,
                amount REAL,
                category TEXT,
                pending INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS garmin_daily (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                date             DATE NOT NULL UNIQUE,
                sleep_score      INTEGER,
                sleep_qualifier  TEXT,
                sleep_total_h    REAL,
                sleep_deep_h     REAL,
                sleep_rem_h      REAL,
                sleep_light_h    REAL,
                sleep_awake_h    REAL,
                battery_charged  INTEGER,
                battery_drained  INTEGER,
                battery_waking   INTEGER,
                steps            INTEGER,
                active_minutes   INTEGER,
                calories         INTEGER,
                resting_hr       INTEGER,
                avg_hr           INTEGER,
                avg_stress       INTEGER,
                max_stress       INTEGER,
                created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

    conn.execute("DROP TABLE IF EXISTS garmin_fitness")
    conn.commit()

    # Migrations for columns added after initial deploy
    try:
        conn.execute("ALTER TABLE purchase_history ADD COLUMN upc TEXT")
        conn.commit()
    except Exception:
        pass  # column already exists
    conn.close()


if __name__ == "__main__":
    init_db()
    print("Database initialized.")
