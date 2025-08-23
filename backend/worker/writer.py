
import os, json, sqlite3, asyncio
import redis.asyncio as redis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
QUEUE_KEY = os.getenv("QUEUE_KEY", "telegraf:metrics")
DB_PATH   = os.getenv("DB_PATH", "metrics.db")


def ensure_schema(conn: sqlite3.Connection):
    conn.execute("""
    CREATE TABLE IF NOT EXISTS router_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        Timestamp TEXT,
        Device_Name TEXT,
        Source_IP TEXT,
        Destination_IP TEXT,
        Traffic_Volume REAL,
        Latency REAL,
        Bandwidth_Allocated REAL,
        Bandwidth_Used REAL,
        Congestion_Flag TEXT,
        Log_Text TEXT
    )
    """)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.commit()


def extract_row(m: dict):
    return (
        m.get("Timestamp"),
        m.get("Device Name"),
        m.get("Source IP"),
        m.get("Destination IP"),
        float(m.get("Traffic Volume (MB/s)", 0)),
        float(m.get("Latency (ms)", 0)),
        float(m.get("Bandwidth Allocated (MB/s)", 0)),
        float(m.get("Bandwidth Used (MB/s)", 0)),
        m.get("Congestion Flag"),
        m.get("Log Text")
    )


async def main():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    ensure_schema(conn)
    r = redis.from_url(REDIS_URL, decode_responses=True)

    print("Writer started. Waiting for metrics...")
    while True:
        item = await r.blpop(QUEUE_KEY, timeout=5)
        if not item:
            continue
        _, data = item
        payload = json.loads(data)

        row = extract_row(payload)
        conn.execute("""
            INSERT INTO router_logs
            (Timestamp, Device_Name, Source_IP, Destination_IP,
             Traffic_Volume, Latency, Bandwidth_Allocated, Bandwidth_Used,
             Congestion_Flag, Log_Text)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, row)
        conn.commit()


if __name__ == "__main__":
    asyncio.run(main())