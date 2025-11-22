#!/usr/bin/env python3
"""
base_IDS.py  (core defense forwarder)

- Listens on CAN_INPUT_IF (default can0)
- Forwards to CAN_OUTPUT_IF (default vcan0)
- Logs every frame and sends report to REPORT_URL
- Uses a handle_frame() function provided by user_custom.py
"""

import os
import sys
import json
import requests
import can

# ===== ENVIRONMENT =====
TEAM_ID    = os.environ.get("TEAM_ID") or os.environ.get("TEAM_NUM", "00")
SECRET_TAG = os.environ.get("SECRET_TAG", "no-secret")

REPORT_URL = os.environ.get("REPORT_URL", "http://0.0.0.0:9000/api/report")
LOG_FILE   = os.environ.get("LOG_FILE", "/logs/forwarder_log.jsonl")


# -------- Build full log JSON (same format as original) --------
def build_record(msg: can.Message):
    return {
        "team_id": str(TEAM_ID),
        "secret_tag": SECRET_TAG,
        "can_time": f"{msg.timestamp:.2f}",
        "can_id": f"{msg.arbitration_id:03X}",
        "can_dlc": str(msg.dlc),
        "can_data": msg.data.hex().upper(),
    }


# -------- Logger --------
def write_log(record: dict):
    log_path = LOG_FILE
    log_dir = os.path.dirname(log_path) or "/"
    os.makedirs(log_dir, exist_ok=True)

    try:
        with open(log_path, "a", encoding="utf-8") as f:
            json.dump(record, f)
            f.write("\n")
    except Exception as e:
        print(f"[LOG] write failed: {e}", file=sys.stderr)


# -------- Default handle_frame (if user doesn't provide one) --------
def default_handle_frame(msg: can.Message, out_bus: can.BusABC, build_record_fn):
    """
    Default behavior: forward everything and log it.
    This matches your original handle_frame.
    """
    try:
        out_bus.send(msg)
    except can.CanError as e:
        print(f"[FWD] send error (default): {e}", file=sys.stderr)
        return None

    return build_record_fn(msg)


def run_forwarder(user_handle_frame=None):
    """
    Core loop. Call this from user_custom with their handle_frame.
    If user_handle_frame is None, uses default_handle_frame.
    """
    if user_handle_frame is None:
        handle_fn = default_handle_frame
        print("[FWD] Using default_handle_frame (no user filter).", flush=True)
    else:
        handle_fn = user_handle_frame
        print("[FWD] Using user_custom.handle_frame().", flush=True)

    # DEBUG
    print(f"[FWD] Team={TEAM_ID}, tag={SECRET_TAG}")
    print("[FWD] In=can0, Out=van0")
    print(f"[FWD] Reporting to {REPORT_URL}", flush=True)

    # CAN input
    try:
        in_bus = can.interface.Bus(channel="can0", bustype="socketcan")
    except Exception as e:
        print(f"[FWD] ERROR opening input can0: {e}", file=sys.stderr)
        sys.exit(1)

    # CAN output
    try:
        out_bus = can.interface.Bus(channel="vcan0", bustype="socketcan")
    except Exception as e:
        print(f"[FWD] ERROR opening output vcan0: {e}", file=sys.stderr)
        sys.exit(1)

    # Main loop
    while True:
        msg = in_bus.recv(timeout=1.0)
        if msg is None:
            continue

        try:
            record = handle_fn(msg, out_bus, build_record)
        except Exception as e:
            # User code crash should not kill whole forwarder
            print(f"[FWD] ERROR in handle_frame: {e}", file=sys.stderr)
            continue

        if record is None:
            # Dropped by user filter
            continue

        # Core logging + report (same as original)
        write_log(record)

        try:
            r = requests.post(REPORT_URL, json=record, timeout=1.0)
            if r.status_code != 200:
                print(f"[FWD] report error {r.status_code}: {r.text}", file=sys.stderr)
        except Exception as e:
            print(f"[FWD] HTTP error: {e}", file=sys.stderr)


if __name__ == "__main__":
    """
    Optional: allow running base_IDS.py directly.
    In that case we *try* to import user_custom.handle_frame.
    """
    try:
        from user_custom import handle_frame as user_handle_frame
        print("[FWD] Loaded handle_frame() from user_custom.py", flush=True)
    except Exception as e:
        print(f"[FWD] WARNING: could not import user_custom.handle_frame: {e}", file=sys.stderr)
        user_handle_frame = None

    run_forwarder(user_handle_frame)
