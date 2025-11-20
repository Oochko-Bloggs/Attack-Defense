#!/usr/bin/env python3
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import os
import json
from datetime import datetime, timezone

app = FastAPI(title="CTF IDS Scoring API")

# Where the init script wrote api_keys.json
API_KEYS_FILE = os.environ.get("API_KEYS_FILE", "/opt/ctf_logs/passwords/api_keys.json")

# Where to log IDS reports (host-only, not mounted into team containers)
SCORE_LOG_DIR = os.environ.get("SCORE_LOG_DIR", "/opt/ctf_logs/ids")
SCORE_LOG_FILE = os.path.join(SCORE_LOG_DIR, "ids_reports.jsonl")

os.makedirs(SCORE_LOG_DIR, exist_ok=True)

# Load API_KEYS: { "password/6digits": { "team_num": "...", "team_name": "..." } }
try:
    with open(API_KEYS_FILE, "r") as f:
        API_KEYS: Dict[str, Dict[str, Any]] = json.load(f)
except FileNotFoundError:
    print(f"[SCORE_API] WARNING: {API_KEYS_FILE} not found, API_KEYS empty")
    API_KEYS = {}
except Exception as e:
    print(f"[SCORE_API] ERROR loading API_KEYS_FILE: {e}")
    API_KEYS = {}


class IDSReport(BaseModel):
    can_id: str          # e.g. "123"
    data: str            # e.g. "DEADBEEF"
    verdict: str         # "attack", "normal", etc.
    reason: Optional[str] = None
    direction: Optional[str] = None  # optional: "in", "out", ...


def append_log(entry: dict):
    with open(SCORE_LOG_FILE, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


@app.get("/api/health")
def health():
    return {"status": "ok", "keys_loaded": len(API_KEYS)}


@app.post("/api/ids/report")
def ids_report(
    body: IDSReport,
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    x_secret_tag: Optional[str] = Header(default=None, alias="X-Secret-Tag"),
):
    # 1) Check API key
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing API key")

    team_info = API_KEYS.get(x_api_key)
    if not team_info:
        raise HTTPException(status_code=401, detail="Invalid API key")

    team_num = team_info.get("team_num", "??")
    team_name = team_info.get("team_name", "unknown_team")

    # 2) Build log entry
    ts = datetime.now(timezone.utc).isoformat()

    entry = {
        "ts": ts,
        "team_num": team_num,
        "team_name": team_name,
        "api_key": x_api_key,      # for debugging; can be dropped later
        "secret_tag": x_secret_tag,
        "can_id": body.can_id,
        "data": body.data,
        "verdict": body.verdict,
        "reason": body.reason,
        "direction": body.direction,
    }

    # 3) Append to log
    try:
        append_log(entry)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write log: {e}")

    return {"status": "ok"}
