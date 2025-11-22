#!/usr/bin/env python3
"""
random_can_sender.py

Continuously sends random CAN frames on can0.
Use this to simulate traffic.
"""

import can
import random
import time


def main():
    # Open SocketCAN interface can0
    bus = can.interface.Bus(channel="can0", bustype="socketcan")

    print("[SENDER] Sending random CAN frames on can0. Press Ctrl+C to stop.")
    try:
        while True:
            # Random 11-bit ID
            arb_id = random.randint(0x000, 0x7FF)
            # Random data length 0–8 bytes
            dlc = random.randint(0, 8)
            data = bytes(random.getrandbits(8) for _ in range(dlc))

            msg = can.Message(
                arbitration_id=arb_id,
                data=data,
                is_extended_id=False,
            )

            try:
                bus.send(msg)
                print(f"[SENDER] Sent {arb_id:03X}#{data.hex().upper()}")
            except can.CanError as e:
                print(f"[SENDER] Failed to send: {e}")

            time.sleep(0.1)  # 10 Hz; adjust if you want faster/slower
    except KeyboardInterrupt:
        print("\n[SENDER] Stopped.")


if __name__ == "__main__":
    main()
