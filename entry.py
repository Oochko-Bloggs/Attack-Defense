#!/usr/bin/env python3
import sys
import os
import json
from datetime import datetime

def get_common_meta():
    """Metadata that is constant for this container."""
    return {
        "team_num": os.environ.get("TEAM_NUM", "00"),
        "team_name": os.environ.get("TEAM_NAME", os.environ.get("HOSTNAME", "unknown_team")),
        "container_name": os.environ.get("CONTAINER_NAME", os.environ.get("HOSTNAME", "unknown_container")),
        "role": os.environ.get("ROLE", "attacker"),
        "secret_tag": os.environ.get("SECRET_TAG", "no-secret"),
        "log_file": os.environ.get("LOG_FILE", "/logs/can_log.jsonl"),
    }

def write_log(raw_line: str):
    meta = get_common_meta()
    now = datetime.utcnow().isoformat() + "Z"
    record = {
        "ts": now,
        "message": raw_line,
        "team_num": meta["team_num"],
        "team_name": meta["team_name"],
        "container_name": meta["container_name"],
        "role": meta["role"],
        "secret_tag": meta["secret_tag"],
    }

    line = json.dumps(record, ensure_ascii=False)     
    log_file = meta["log_file"]
    log_dir = os.path.dirname(log_file) or "/"
    os.makedirs(log_dir, exist_ok=True)

    # Print to stdout (for docker logs -f)
    # FOR DEBUG PURPOSE THIS SHOWS THE USER WHAT LOG SENDING
    # print(line, flush=True)

    # Append to shared log file, realtime
    import errno
    existed_before = os.path.exists(log_file)

    try:
        with open(log_file, "a", buffering=1) as f:
            if not existed_before:
                try:
                    os.chmod(log_file,0o200)
                except PermissionError:
                    #Ignore if we can't change mode
                    pass
            f.write(line + "\n")
            f.flush()
            os.fsync(f.fileno())
    except Exception as e:
        # Optional DEBUG
        # print(f"[CANLOG] Failed to write log: {e}", flush=True)
        pass

def main():
    if len(sys.argv) < 2 or sys.argv[1] != "log":
        print("Usage: entry.py log <message>", file=sys.stderr)
        sys.exit(1)

    msg = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
    write_log(msg)

if __name__ == "__main__":
    main()
