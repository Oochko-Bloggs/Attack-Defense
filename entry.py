#!/usr/bin/env python3
import sys
import os
import json
import shlex
import time


def get_common_meta():
    """Metadata that is constant for this container."""
    return {
        "team_id": os.environ.get("TEAM_NUM", "00"),
        "secret_tag": os.environ.get("SECRET_TAG", "no-secret"),
        "log_file": os.environ.get("LOG_FILE", "/logs/can_log.jsonl"),
    }


def parse_cansend_line(raw_line: str):
    """
    Expect something like:
      CMD=cansend IF=can0 ARGS="can0 4B3#1122334455667788" USER=team01
    Returns a dict with parsed fields.
    """
    fields = {}

    # split on spaces BUT respect quotes in ARGS="..."
    for part in shlex.split(raw_line):
        if "=" in part:
            k, v = part.split("=", 1)
            fields[k] = v

    result = {
        "raw": raw_line,
        "if": fields.get("IF", ""),
        "user": fields.get("USER", ""),
    }

    if fields.get("CMD") != "cansend":
        # Not a cansend command – just return what we have
        return result

    args_str = fields.get("ARGS", "")
    args = shlex.split(args_str)

    # Expected args: ["can0", "4B3#1122334455667788"]
    if len(args) >= 2:
        frame = args[1]
        if "#" in frame:
            can_id_str, data_hex = frame.split("#", 1)
            can_id_str = can_id_str.strip()
            data_hex = data_hex.strip().upper()
            can_data = data_hex
            can_dlc = len(can_data) // 2  # each pair of hex is 1 byte
        else:
            # No data part, just an ID
            can_id_str = frame.strip()
            can_data = ""
            can_dlc = 0

        result.update(
            {
                "can_id": can_id_str.upper(),
                "can_dlc": str(can_dlc),
                "can_data": can_data,
            }
        )

    return result


def write_log(raw_line: str):
    meta = get_common_meta()

    parsed = parse_cansend_line(raw_line)

    now = time.time()
    can_time = f"{now:.2f}"  # fake "CAN time" from epoch seconds

    record = {
        "team_id": str(meta["team_id"]),
        "secret_tag": meta["secret_tag"],
        "can_time": can_time,
        # optional: also store original info
        "can_id": parsed.get("can_id", ""),
        "can_dlc": parsed.get("can_dlc", ""),
        "can_data": parsed.get("can_data", ""),
        "if": parsed.get("if", ""),
        "user": parsed.get("user", ""),
        "raw": parsed.get("raw", raw_line),
    }

    line = json.dumps(record, ensure_ascii=False)

    log_file = meta["log_file"]
    log_dir = os.path.dirname(log_file) or "/"
    os.makedirs(log_dir, exist_ok=True)

    existed_before = os.path.exists(log_file)

    try:
        with open(log_file, "a", buffering=1) as f:
            if not existed_before:
                try:
                    # writeable for owner/group; adjust if you want stricter perms
                    os.chmod(log_file, 0o664)
                except PermissionError:
                    pass
            f.write(line + "\n")
            f.flush()
            os.fsync(f.fileno())
    except Exception as e:
        print(f"[CANLOG] Failed to write log: {e}", file=sys.stderr, flush=True)


def main():
    if len(sys.argv) < 2 or sys.argv[1] != "log":
        print("Usage: entry.py log <message>", file=sys.stderr)
        sys.exit(1)

    msg = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
    write_log(msg)


if __name__ == "__main__":
    main()
