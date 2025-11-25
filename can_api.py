import os
import requests

########################################################
#                                                      #
#   DON'T CHANGE ANYTHING ON THIS CODE YOU CAN USE     #
#   CANSEND OF THIS FUNCTION AS SHOWN IN               #
#               user_custom.py                         #
#                                                      #
########################################################





API_BASE = os.environ.get("CAN_API_BASE", "http://192.168.41.104:8000")
SECRET_TAG = os.environ.get("SECRET_TAG")
TEAM_ID = os.environ.get("TEAM_ID") or os.environ.get("TEAM_NUM", "00")
if not SECRET_TAG:
    # Optional: fail early so it's obvious if env is not set correctly
    raise RuntimeError("SECRET_TAG environment variable is not set")

def cansend(frame: str, interface: str = "can0"):
    """
    Send one CAN frame via the central CAN API.
    frame example: '123#DEADBEEF'
    """
    url = f"{API_BASE}/api/cansend"
    headers = {
        "Content-Type": "application/json",
        "X-Secret-Tag": SECRET_TAG,
        "X-Team-Id": TEAM_ID,
    }

    data = {"interface": interface, "frame": frame}

    try:
        r = requests.post(url, json=data, headers=headers, timeout=2)
        r.raise_for_status()
    except Exception as e:
        # This will show up in docker logs
        print(f"[CAN_API] request failed: {e} (url={url})", flush=True)
        raise

    return r.json()
'''
def send_attack():
    # this is purely example, you decide IDs/data
    response = cansend("018#0000")
    print("API response:", response)

if __name__ == '__main__':
    send_attack()

'''
