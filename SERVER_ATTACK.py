#!/usr/bin/env python3
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
import subprocess
import os
import time
import json
from collections import defaultdict, deque
import threading

app = FastAPI(title="CAN API")

# ====== RATE LIMIT CONFIG ======
RATE_LIMIT_MAX = 100        # max allowed requests per window
RATE_LIMIT_WINDOW = 60.0    # seconds (sliding window)
BAN_DURATION = 10.0         # seconds to ignore messages

_rate_lock = threading.Lock()
_request_log = defaultdict(deque)   # secret_tag -> deque[timestamps]
_banned_until = {}                  # secret_tag -> timestamp

# ====== LOG FILE CONFIG ======
LOG_PATH = "/opt/ctf_logs/logs/can_log.jsonl"


class CanSendRequest(BaseModel):
    interface: str = "can0"
    frame: str    # e.g. "123#DEADBEEF"


def check_rate_limit(secret_tag: str):
    """
    Returns (allowed: bool, seconds_remaining: int)
    """
    now = time.time()
    with _rate_lock:
        # Already banned?
        until = _banned_until.get(secret_tag)
        if until and now < until:
            return False, int(until - now)

        # Clean old timestamps
        q = _request_log[secret_tag]
        while q and now - q[0] > RATE_LIMIT_WINDOW:
            q.popleft()

        q.append(now)

        # Check if limit exceeded
        if len(q) > RATE_LIMIT_MAX:
            _banned_until[secret_tag] = now + BAN_DURATION
            _request_log[secret_tag].clear()
            return False, int(BAN_DURATION)

    return True, 0


def parse_frame(frame: str):
    """
    Parse frame like '123#DEADBEEF' into (can_id, can_dlc, can_data).
    You can adjust this if your format is slightly different.
    """
    # Split on the first '#'
    if "#" in frame:
        can_id, data = frame.split("#", 1)
    else:
        can_id, data = frame, ""

    can_id = can_id.upper()
    can_data = data.upper()

    # DLC = number of bytes (2 hex chars per byte) if hex; fallback to len
    if len(can_data) % 2 == 0 and len(can_data) > 0:
        can_dlc = str(len(can_data) // 2)
    else:
        # If format is something like '#1' you can tweak here
        can_dlc = str(len(can_data)) if can_data else "0"

    return can_id, can_dlc, can_data


def write_json_log(
    team_id: str,
    secret_tag: str,
    interface: str,
    frame: str,
    user: str,
    timestamp: float,
):
    """
    Append one JSON line into /opt/ctf_logs/logs/can_log.jsonl
    """
    can_id, can_dlc, can_data = parse_frame(frame)
    can_time = f"{timestamp:.2f}"  # same style as your example

    raw = f'CMD=cansend IF={interface} ARGS="{interface} {frame}" USER={user}'

    record = {
        "team_id": str(team_id),
        "secret_tag": str(secret_tag),
        "can_time": can_time,
        "can_id": can_id,
        "can_dlc": can_dlc,
        "can_data": can_data,
        "if": interface,
        "user": user,
        "raw": raw,
    }

    # Make sure directory exists
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            json.dump(record, f)
            f.write("\n")
    except Exception as e:
        # Don't crash the API if log file write fails
        print(f"[API] JSON log write failed: {e}", flush=True)


def log_and_cansend(
    interface: str,
    frame: str,
    user: str,
    secret_tag: str,
    team_id: str,
):
    # Timestamp for this event
    now = time.time()

    # 1) Write JSON log directly to /opt/ctf_logs/logs/can_log.jsonl
    write_json_log(
        team_id=team_id,
        secret_tag=secret_tag,
        interface=interface,
        frame=frame,
        user=user,
        timestamp=now,
    )

    try:
        subprocess.run(
            ["cansend", interface, frame],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"cansend failed: {e}")


@app.post("/api/cansend")
def cansend_endpoint(
    body: CanSendRequest,
    x_secret_tag: str = Header(default=None),
    x_team_id: str = Header(default=None),
):
    if not body.frame:
        raise HTTPException(status_code=400, detail="Missing frame")

    # Require secret tag
    if not x_secret_tag:
        raise HTTPException(
            status_code=401,
            detail="Missing X-Secret-Tag header"
        )

    secret_tag = x_secret_tag.strip()
    team_id = (x_team_id or TEAM_ID_DEFAULT).strip()
    # Rate limit by secret_tag
    allowed, wait_sec = check_rate_limit(secret_tag)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Try again in {wait_sec} seconds."
        )

    # Process CAN message (log + cansend)
    try:
        log_and_cansend(
            interface=body.interface,
            frame=body.frame,
            user="api",
            secret_tag=secret_tag,
            team_id=team_id,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "status": "ok",
        "interface": body.interface,
        "frame": body.frame,
    }


@app.get("/api/health")
def health():
    return {"status": "ok"}
