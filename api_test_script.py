
import requests
import time
import json
import sys

BASE_URL = "http://localhost:8000/api"

def log(msg):
    print(f"[TEST] {msg}")

def test_status():
    log("Checking status...")
    try:
        r = requests.get(f"{BASE_URL}/status")
        r.raise_for_status()
        data = r.json()
        log(f"Status response: {data}")
        return data
    except Exception as e:
        log(f"Failed to get status: {e}")
        return None

def test_stats():
    log("Checking stats...")
    try:
        r = requests.get(f"{BASE_URL}/stats")
        r.raise_for_status()
        data = r.json()
        log(f"Stats response: {data}")
        return data
    except Exception as e:
        log(f"Failed to get stats: {e}")
        return None

def start_search():
    log("Starting search for '测试'...")
    payload = {
        "keywords": "测试",
        "search_type": "fulltext",
        "max_pages": 1,
        "time_type": "today" # Keep it small
    }
    try:
        r = requests.post(f"{BASE_URL}/search", json=payload)
        r.raise_for_status()
        log(f"Search start response: {r.json()}")
        return True
    except Exception as e:
        log(f"Failed to start search: {e}")
        return False

def stop_search():
    log("Stopping search...")
    try:
        r = requests.post(f"{BASE_URL}/stop")
        r.raise_for_status()
        log(f"Stop response: {r.json()}")
    except Exception as e:
        log(f"Failed to stop search: {e}")

def get_announcements():
    log("Getting announcements...")
    try:
        r = requests.get(f"{BASE_URL}/announcements?limit=5")
        r.raise_for_status()
        data = r.json()
        log(f"Got {len(data)} announcements")
        if data:
            log(f"Sample: {data[0]['title']}")
    except Exception as e:
        log(f"Failed to get announcements: {e}")

def get_cards():
    log("Getting cards...")
    try:
        r = requests.get(f"{BASE_URL}/cards?limit=5")
        r.raise_for_status()
        data = r.json()
        log(f"Got {len(data)} cards")
    except Exception as e:
        log(f"Failed to get cards: {e}")

def main():
    log("Starting API Test Sequence")
    
    # 1. Initial State
    test_status()
    test_stats()
    
    # 2. Start Search
    if start_search():
        time.sleep(2)
        
        # 3. Check running status
        status = test_status()
        if status and status.get("is_running"):
            log("Search is running correctly.")
            # Let it run for a bit more to ensure browser launches
            time.sleep(15)
        else:
            log("Search is NOT running (might have finished quickly or failed).")

        # 4. Stop Search (clean up)
        stop_search()
        
        # 5. Check final status
        time.sleep(1)
        test_status()
    
    # 6. Check Data
    get_announcements()
    get_cards()
    
    log("Test Sequence Complete")

if __name__ == "__main__":
    main()
