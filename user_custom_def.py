#!/usr/bin/env python3
"""

Participants can modify ONLY THIS FILE.

- Define handle_frame(msg, out_bus, build_record).
- When you run `python3 user_custom.py`, it will start the base_IDS
  forwarder using your handle_frame as the filter logic.
"""

import can
from base_IDS import run_forwarder


def handle_frame(msg: can.Message, out_bus: can.BusABC, build_record):
    """
    DEFAULT BEHAVIOR:

    - Forward every frame from input to output.
    - Log/report each frame using the core's build_record().

    You can modify this function to add IDS logic / filters.
    """

    # Example filter (commented out):
    # if msg.arbitration_id == 0x666:
    #     # Drop this suspicious ID: do not forward, do not log
    #     return None

    # Forward everything (same as original base_IDS handle_frame)
    try:
        out_bus.send(msg)
    except can.CanError as e:
        print(f"[USER] send error: {e}")
        return None

    record = build_record(msg)
    return record


if __name__ == "__main__":
    run_forwarder(handle_frame)
