# backend/app/routers/actions.py
from fastapi import APIRouter
from pydantic import BaseModel
import os, sqlite3, time

router = APIRouter()

DB_PATH = os.getenv("DB_PATH", "metrics.db")

class ActionCmd(BaseModel):
    device: str
    action: str
    params: dict = {}

def ensure_actions_table():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("""
      CREATE TABLE IF NOT EXISTS actions_log(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT,
        device TEXT,
        action TEXT,
        params TEXT,
        status TEXT
      )
    """)
    conn.commit(); conn.close()

@router.post("/api/actions")
def post_action(cmd: ActionCmd):
    ensure_actions_table()
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute(
      "INSERT INTO actions_log(ts,device,action,params,status) VALUES(?,?,?,?,?)",
      (time.strftime("%Y-%m-%d %H:%M:%S"), cmd.device, cmd.action, str(cmd.params), "queued")
    )
    conn.commit(); conn.close()
    # TODO: wire Nornir here later
    return {"ok": True, "queued": cmd.model_dump()}