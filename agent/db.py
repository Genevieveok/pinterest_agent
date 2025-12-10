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


def clear_all_history():
    """Deletes all records from the tracking tables."""
    conn = get_conn()
    cur = conn.cursor()

    # Clear the table that tracks saved pins
    cur.execute("DELETE FROM pinned")
    deleted_pins = cur.rowcount

    # Clear the table that tracks blog pins
    cur.execute("DELETE FROM blog_pins")
    deleted_blog_pins = cur.rowcount

    # Clear the table that tracks searched boards
    cur.execute("DELETE FROM searched_boards")
    deleted_boards = cur.rowcount

    conn.commit()
    conn.close()

    return {
        "pinned": deleted_pins,
        "blog_pins": deleted_blog_pins,
        "searched_boards": deleted_boards,
    }


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "clear":
        print(
            "🚨 Clearing ALL history database tables (pinned, blog_pins, searched_boards)..."
        )
        try:
            counts = clear_all_history()
            print(f"✅ Successfully deleted:")
            print(f"   - {counts['pinned']} entries from 'pinned'.")
            print(f"   - {counts['blog_pins']} entries from 'blog_pins'.")
            print(f"   - {counts['searched_boards']} entries from 'searched_boards'.")
        except Exception as e:
            print(f"❌ Failed to clear database: {e}")
    else:
        init_db()
        print("Database initialized.")
