import sqlite3
from pathlib import Path
import sys

DB_PATH = Path(__file__).resolve().parent.parent / "agent_data.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS pinned (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pinterest_pin_id TEXT UNIQUE,
            board_key TEXT,
            source_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS blog_pins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_url TEXT UNIQUE,
            pinterest_pin_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS searched_boards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_board_id TEXT UNIQUE,
            last_searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()


def clear_search_history():
    """Deletes all records from the searched_boards table."""
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("DELETE FROM searched_boards")

    deleted_count = cur.rowcount
    conn.commit()
    conn.close()

    return deleted_count


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "clear":
        print("🚨 Clearing search history database...")
        try:
            count = clear_search_history()
            print(f"✅ Successfully deleted {count} entries from searched_boards.")
        except Exception as e:
            print(f"❌ Failed to clear database: {e}")
    else:
        init_db()
        print("Database initialized.")
