import sys
import requests

def test_api():
    base_url = "http://localhost:8080/api/index.php"
    
    # 1. Login
    print("[1] Logging in...")
    login_url = f"{base_url}/login"
    login_data = {
        "login": "admin",
        "password": "admin"
    }
    response = requests.post(login_url, json=login_data)
    if response.status_code != 200:
        print(f"Login failed: HTTP {response.status_code}")
        print(response.text)
        return
        
    res_data = response.json()
    token = res_data.get("success", {}).get("token")
    if not token:
        print("No token received")
        return
    print(f"Login success! Token: {token[:8]}...")
    
    headers = {
        "DOLAPIKEY": token
    }
    
    # 2. Get User Info
    print("\n[2] Fetching user info...")
    info_url = f"{base_url}/users/info"
    response = requests.get(info_url, headers=headers)
    if response.status_code != 200:
        print(f"User info failed: HTTP {response.status_code}")
        return
    user_info = response.json()
    print(f"User info retrieved: ID={user_info.get('id')}, Username={user_info.get('username')}")

    # 3. Get Status (before clock-in)
    print("\n[3] Fetching current presence status...")
    status_url = f"{base_url}/presences/status"
    response = requests.get(status_url, headers=headers)
    if response.status_code != 200:
        print(f"Status check failed: HTTP {response.status_code}")
        print(response.text)
        return
    status_data = response.json()
    print(f"Current status: {status_data}")

    # 4. Get Tasks (this is where HTTP 500 happened!)
    print("\n[4] Fetching tasks and projects...")
    tasks_url = f"{base_url}/presences/tasks"
    response = requests.get(tasks_url, headers=headers)
    if response.status_code != 200:
        print(f"Tasks fetch failed: HTTP {response.status_code}")
        print(response.text)
        return
    tasks_data = response.json()
    print("Tasks fetch success!")
    print(f"Retrieved {len(tasks_data.get('tasks', {}))} projects/tasks.")

    # 5. Clock In
    if not status_data.get("logged_in"):
        print("\n[5] Clocking in...")
        clockin_url = f"{base_url}/presences/clockin"
        response = requests.post(clockin_url, headers=headers)
        if response.status_code != 200:
            print(f"Clock-in failed: HTTP {response.status_code}")
            print(response.text)
            return
        print(f"Clock-in success: {response.json()}")
        
        # Verify status after clock-in
        print("\n[6] Re-checking status after clock-in...")
        response = requests.get(status_url, headers=headers)
        print(f"New status: {response.json()}")
    else:
        print("\n[5] Already clocked in. Proceeding to clock out.")

    # 6. Clock Out
    print("\n[7] Clocking out...")
    clockout_url = f"{base_url}/presences/clockout"
    response = requests.post(clockout_url, headers=headers)
    if response.status_code != 200:
        print(f"Clock-out failed: HTTP {response.status_code}")
        print(response.text)
        return
    print(f"Clock-out success: {response.json()}")

    # Verify final status
    print("\n[8] Final status check...")
    response = requests.get(status_url, headers=headers)
    print(f"Final status: {response.json()}")

if __name__ == "__main__":
    test_api()
