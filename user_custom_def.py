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

#SEND MESSAGE BY
'''
msg = can.Message(
        arbitration_id=can_id,
        data=data_bytes,
        is_extended_id=False
        )
'''

    try:
        out_bus.send(msg)
    except can.CanError as e:
        print(f"[USER] send error: {e}")
        return None

    record = build_record(msg)
    return record


if __name__ == "__main__":
    run_forwarder(handle_frame)
