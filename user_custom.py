from can_api import cansend

# example usage in their own logic
def send_attack():
    # this is purely example, you decide IDs/data
    response = cansend("123#DEADBEEF")
    print("API response:", response)

if __name__ == '__main__':
    send_attack()