#!/usr/bin/env python3
"""
listener_api.py

Host-side:

- Listens on /api/report (port 9000)
- Receives JSON like:
    {
        "team_id": "11",
        "can_time": "1234123.10",
        "can_id": "4B3",
        "can_dlc": "8",
        "can_data": "3727E64337837055",
        "secret_tag": "b6999312-7dda-44c3-bf90-e96aa60d27fa"
    }
- Appends it as a JSON line to /opt/ctf_logs/ids_report.jsonl


RUN CODE : python3 -m uvicorn listener_api:app --host 0.0.0.0 --port 9000
"""

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from datetime import datetime, timezone
import os
import json
import sys

#LOG_FILE = "/opt/ctf_logs/ids_report.jsonl"
#os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

LOG_DIR = os.environ.get("CTF_LOG_DIR", "/opt/ctf_logs/logs")
LOG_FILE = os.path.join(LOG_DIR, "ids_report.jsonl")

try:
    os.makedirs(LOG_DIR, exist_ok=True)
except OSError as e:
    print(f"[WARN] Cannot create {LOG_DIR}: {e}. Falling back to /tmp/ctf_logs", file=sys.stderr)
    LOG_DIR = "/tmp/ctf_logs"
    LOG_FILE = os.path.join(LOG_DIR, "ids_report.jsonl")
    os.makedirs(LOG_DIR, exist_ok=True)

app = FastAPI(title="IDS Listener")


class CanReport(BaseModel):
    team_id: str
    can_time: str
    can_id: str
    can_dlc: str
    can_data: str
    secret_tag: str


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/report")
def report(body: CanReport):
    entry = body.dict()
    entry["server_ts"] = datetime.now(timezone.utc).isoformat()

    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        # return a controlled 500 with error detail
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Failed to write log file: {e}")
