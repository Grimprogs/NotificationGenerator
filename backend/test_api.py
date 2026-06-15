import requests
import traceback

try:
    res = requests.get("http://127.0.0.1:8001/dashboard", timeout=10)
    data = res.json()
    if isinstance(data, list) and len(data) > 0:
        notifs = data[0].get("notifications", [])
        if notifs:
            print(f"First notification: id={notifs[0].get('id')}, user_id={notifs[0].get('user_id')}")
        else:
            print("No notifications in the first user group.")
    else:
        print(f"Dashboard returned unexpected type or empty. Type: {type(data)}. Content: {data}")
except Exception as e:
    traceback.print_exc()
