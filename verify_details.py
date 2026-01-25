
import requests
import sqlite3
import os

BASE_URL = "http://localhost:8000/api"

def get_db_connection():
    db_path = os.path.join("data", "gp.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def test_detail_view():
    print("Testing Detail View...")
    # Get an ID from DB
    conn = get_db_connection()
    row = conn.execute("SELECT id FROM announcements LIMIT 1").fetchone()
    conn.close()
    
    if not row:
        print("No announcements in DB.")
        return

    item_id = row['id']
    print(f"Fetching details for ID: {item_id}")
    
    try:
        r = requests.get(f"{BASE_URL}/announcements/{item_id}")
        r.raise_for_status()
        data = r.json()
        print(f"Success! Title: {data.get('title')}")
        print(f"Content field present? {'Yes' if 'content' in data else 'NO'}")
        if 'content' in data:
            print(f"Content length: {len(data['content'])}")
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    test_detail_view()
