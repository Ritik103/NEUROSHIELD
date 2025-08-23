import sqlite3
import time
import os

DB_PATH = "metrics.db"

def tail_db():
    if not os.path.exists(DB_PATH):
        print("No DB file found yet.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    last_seen_id = 0
    print("🔎 Watching router_logs... Press CTRL+C to stop.\n")

    try:
        while True:
            cursor.execute(
                "SELECT * FROM router_logs WHERE id > ? ORDER BY id ASC", (last_seen_id,)
            )
            rows = cursor.fetchall()
            if rows:
                for row in rows:
                    last_seen_id = row[0]  # id is first column
                    print(row)
            time.sleep(2)  # check every 2 seconds
    except KeyboardInterrupt:
        print("\n👋 Stopped watching.")
    finally:
        conn.close()

if __name__ == "__main__":
    tail_db()