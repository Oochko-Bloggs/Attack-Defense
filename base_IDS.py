#!/usr/bin/env python3
"""
Base IDS skeleton for the CTF defense docker.

You ONLY need to edit the function:

    def is_attack(can_id: str, data_hex: str) -> bool

Everything else (reading can0, sending results to server) is handled for you.
"""

import os
import subprocess
import sys
import requests


# ===================== CONFIG FROM ENV =====================

TEAM_NUM = os.environ.get("TEAM_NUM", "00")
TEAM_NAME = os.environ.get("TEAM_NAME", f"Team_{TEAM_NUM}")
CAN_INPUT_IF = os.environ.get("CAN_INPUT_IF", "can0")        # mixed dataset input
SCORE_API = os.environ.get("SCORE_API", "http://127.0.0.1:9000/api/ids/report")
SCORE_API_KEY = os.environ.get("SCORE_API_KEY", "")          # = team password
SECRET_TAG = os.environ.get("SECRET_TAG", "")                # per-container tag


# ===================== REPORT HELPER =====================

def report_ids(can_id: str, data_hex: str, verdict: str, reason: str = "", direction: str | None = None) -> None:
    """
    Send ONE IDS decision to the scoring server.

    Parameters:
        can_id   : hex string, e.g. "123"
        data_hex : payload hex, e.g. "DEADBEEF"
        verdict  : "attack" / "normal" / "unknown" (you decide)
        reason   : free text explaining why
        direction: optional ("in", "out", etc.)
    """
    headers = {"Content-Type": "application/json"}
    if SCORE_API_KEY:
        headers["X-API-Key"] = SCORE_API_KEY
    if SECRET_TAG:
        headers["X-Secret-Tag"] = SECRET_TAG

    payload = {
        "can_id": can_id,
        "data": data_hex,
        "verdict": verdict,
        "reason": reason or None,
        "direction": direction,
    }

    try:
        # timeout small so IDS never blocks on network problems
        requests.post(SCORE_API, json=payload, headers=headers, timeout=1.0)
    except Exception as e:
        print(f"[IDS] report_ids failed: {e}", file=sys.stderr, flush=True)


# ===================== TODO: YOUR LOGIC HERE =====================

def is_attack(can_id: str, data_hex: str) -> bool:
    """
    Decide if a frame is an attack.

    Arguments:
        can_id   : string like "123" (hex, no "0x")
        data_hex : string like "DEADBEEF" (bytes concatenated, uppercase or lowercase)

    Return:
        True  -> treat this as an ATTACK frame (will send verdict="attack")
        False -> treat as NORMAL (no report by default)

    NOTE:
        - You can convert to int: int(can_id, 16)
        - Length of data_hex is even (2 chars per byte).
        - You can inspect specific bytes: data_hex[0:2], data_hex[2:4], etc.
    """
    # ========================== EXAMPLES ==========================
    # Example 1: mark ID 0x666 as attack
    try:
        cid = int(can_id, 16)
    except ValueError:
        # malformed ID -> consider suspicious or ignore
        return False

    if cid == 0x666:
        return True

    # Example 2: if payload starts with "DEAD" mark as attack
    if data_hex.upper().startswith("DEAD"):
        return True

    # TODO: DELETE the examples above and add your own rules here.
    # For example:
    # - Check RPM > limit
    # - Detect impossible gear/RPM combination
    # - Detect abnormal speed jumps
    # - etc.

    return False


# ===================== CAN READER LOOP =====================

def parse_candump_line(line: str):
    """
    Parse a candump -L line.

    Example line:
        (0000.000000) can0  123   [4]  DE AD BE EF

    Returns:
        (can_if, can_id, data_hex)  -> ("can0", "123", "DEADBEEF")
        or (None, None, None) if parse fails.
    """
    line = line.strip()
    if not line:
        return None, None, None

    parts = line.split()
    # Expected: (timestamp) IF  ID  [len]  data...
    if len(parts) < 5:
        return None, None, None

    try:
        can_if = parts[1]
        can_id = parts[2]
        data_bytes = "".join(parts[4:])  # e.g. "DEADBEEF"
    except IndexError:
        return None, None, None

    if not can_if or not can_id or not data_bytes:
        return None, None, None

    return can_if, can_id, data_bytes


def main():
    print(f"[IDS] Starting IDS for {TEAM_NAME} (team{TEAM_NUM}) on {CAN_INPUT_IF}", flush=True)

    # Run candump -L on CAN_INPUT_IF and read from stdout line by line
    proc = subprocess.Popen(
        ["candump", "-L", CAN_INPUT_IF],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    try:
        for line in proc.stdout:
            can_if, can_id, data_hex = parse_candump_line(line)
            if not can_if:
                continue

            # Optional: only process frames from the expected interface
            if can_if != CAN_INPUT_IF:
                continue

            # ==== YOUR DECISION FUNCTION ====
            if is_attack(can_id, data_hex):
                # If attack -> send one report to server
                reason = "matched custom rule"  # TODO: customize per rule
                report_ids(can_id, data_hex, verdict="attack", reason=reason)
                # You could also print debug:
                print(f"[IDS] ATTACK {can_if} {can_id}#{data_hex}", flush=True)

            # If you also want to report normal frames (be careful with spam):
            # else:
            #     report_ids(can_id, data_hex, verdict="normal")
    finally:
        proc.terminate()
        proc.wait()


if __name__ == "__main__":
    main()
