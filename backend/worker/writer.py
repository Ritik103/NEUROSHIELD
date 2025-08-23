import os, json, time, asyncio, sqlite3
import redis.asyncio as redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
QUEUE_KEY = os.getenv("QUEUE_KEY", "telegraf:metrics")
DB_PATH   = os.getenv("DB_PATH", "metrics.db")

def ensure_schema(conn: sqlite3.Connection):
    # Very simple schema: store original payload and some useful breakouts
    conn.execute("""
    CREATE TABLE IF NOT EXISTS metrics(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts INTEGER,
        device TEXT,
        measurement TEXT,
        fields_json TEXT,
        tags_json TEXT,
        raw_json TEXT
    )
    """)
    # WAL mode improves concurrency
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.commit()

def extract_row(m: dict):
    # Try to normalize common Telegraf JSON fields
    ts = int(m.get("time") or m.get("timestamp") or time.time())
    measurement = m.get("name") or m.get("measurement") or "unknown"
    tags = m.get("tags") or {}
    fields = m.get("fields") or m.get("values") or {}
    device = tags.get("agent_host") or tags.get("host") or tags.get("device") or "unknown"
    return (ts, device, measurement, json.dumps(fields), json.dumps(tags), json.dumps(m))

async def main():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    ensure_schema(conn)
    r = redis.from_url(REDIS_URL, decode_responses=True)

    print("Writer started. Waiting for metrics...")
    while True:
        # Block-pop one item; tune timeout as needed
        item = await r.blpop(QUEUE_KEY, timeout=5)
        if not item:
            continue
        _, data = item
        payload = json.loads(data)

        rows = []
        if isinstance(payload, list):
            for m in payload:
                if isinstance(m, dict):
                    rows.append(extract_row(m))
        elif isinstance(payload, dict):
            rows.append(extract_row(payload))

        if rows:
            conn.executemany(
                "INSERT INTO metrics (ts, device, measurement, fields_json, tags_json, raw_json) VALUES (?,?,?,?,?,?)",
                rows
            )
            conn.commit()

if __name__ == "__main__":
    asyncio.run(main())
