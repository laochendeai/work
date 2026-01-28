
import sqlite3
import os

def get_db_connection():
    db_path = os.path.join("data", "gp.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def test_query():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT title, url, publish_date, source, content FROM announcements LIMIT 1")
        row = cursor.fetchone()
        if row:
            item = dict(row)
            print(f"Keys: {list(item.keys())}")
            print(f"Source value: '{item.get('source')}'")
        else:
            print("No rows found")
        conn.close()
    except Exception as e:
        print(e)

if __name__ == "__main__":
    test_query()
