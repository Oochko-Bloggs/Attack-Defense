#!/usr/bin/env python3
import os
import time
import subprocess

TEAM_NUM = os.environ.get("TEAM_NUM", "00")
TEAM_NAME = os.environ.get("TEAM_NAME", f"Team_{TEAM_NUM}")
ROLE = os.environ.get("ROLE", "defense")

CAN_INPUT_IF = os.environ.get("CAN_INPUT_IF", "can0")
# vcan index from TEAM_NUM ("01" -> "vcan1")
DEFAULT_VCAN_OUT = "vcan" + str(int(TEAM_NUM))
CAN_OUTPUT_IF = os.environ.get("CAN_OUTPUT_IF", DEFAULT_VCAN_OUT)


def is_suspicious(can_id: str, data_hex: str) -> bool:
    """
    TODO: teams implement their own logic here.

    :param can_id: string like '123'
    :param data_hex: hex string like 'DEADBEEF'
    :return: True if frame should be treated as attack / interesting.
    """
    # Example dummy rule: flag CAN ID 0x666
    try:
        if int(can_id, 16) == 0x666:
            return True
    except ValueError:
        pass
    return False


def forward_frame(can_id: str, data_hex: str):
    """
    Forward a frame to the team-specific vcan interface.
    """
    frame = f"{can_id}#{data_hex}"
    try:
        subprocess.run(
            ["cansend", CAN_OUTPUT_IF, frame],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"[IDS-{TEAM_NUM}] cansend failed on {CAN_OUTPUT_IF}: {e}", flush=True)


def run_ids():
    print(
        f"[IDS-{TEAM_NUM}] {TEAM_NAME} reading {CAN_INPUT_IF}, "
        f"writing filtered frames to {CAN_OUTPUT_IF}",
        flush=True,
    )

    # Use candump -L for a simple line-oriented stream
    proc = subprocess.Popen(
        ["candump", "-L", CAN_INPUT_IF],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    try:
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue

            # Example candump -L line:
            # (0000.000000) can0  123   [4]  DE AD BE EF
            parts = line.split()
            if len(parts) < 5:
                continue

            # Basic parsing
            try:
                can_if = parts[1]
                can_id = parts[2]
                data_bytes = "".join(parts[4:])  # 'DEADBEEF'
            except IndexError:
                continue

            # You can also ignore frames not from CAN_INPUT_IF if needed:
            if can_if != CAN_INPUT_IF:
                continue

            # Apply team logic
            if not is_suspicious(can_id, data_bytes):
                # Example: pass only non-suspicious frames, or invert this logic
                forward_frame(can_id, data_bytes)
    finally:
        proc.terminate()
        proc.wait()


if __name__ == "__main__":
    while True:
        try:
            run_ids()
        except Exception as e:
            print(f"[IDS-{TEAM_NUM}] crashed: {e}, restarting in 2s", flush=True)
            time.sleep(2)
