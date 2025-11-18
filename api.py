#!/usr/bin/env python3
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
import subprocess
import os

app = FastAPI(title="CAN API")

API_KEY = os.environ.get("API_KEY", "")


class CanSendRequest(BaseModel):
    interface: str = "can0"
    frame: str   # e.g. "123#DEADBEEF"


def log_and_cansend(interface: str, frame: str, user: str = $USER):
    msg = f'CMD=cansend IF={interface} ARGS="{interface} {frame}" USER={user}'

    # Log the message 
    try:
        subprocess.run(
            ["python3", "/app/entry.py", "log", msg],
            check=False,
        )
    except Exception as e:
        # Don't kill API if logging fails
        print(f"[API] logging failed: {e}", flush=True)

    # Send can frame
    try:
        subprocess.run(
            ["cansend", interface, frame],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"cansend failed: {e}")


@app.post("/api/cansend")
def cansend_endpoint(body: CanSendRequest, x_api_key: str = Header(default=None)):
    # If API_KEY is set, enforce header
    if API_KEY:
        if x_api_key is None or x_api_key != API_KEY:
            raise HTTPException(status_code=401, detail="Invalid or missing API key")

    if not body.frame:
        raise HTTPException(status_code=400, detail="Missing frame")

    try:
        log_and_cansend(body.interface, body.frame, user="api")
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
