import sqlite3

conn = sqlite3.connect('data/gp.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Check the announcement
cur.execute('''
    SELECT id, title, url, content
    FROM announcements 
    WHERE url LIKE '%26107129%'
    LIMIT 1
''')

row = cur.fetchone()
if row:
    print(f"ID: {row['id']}")
    print(f"Title: {row['title']}")
    print(f"URL: {row['url']}")
    print(f"\n=== Content (first 3000 chars) ===")
    content = row['content'] or ''
    print(content[:3000])
else:
    print("Announcement not found")

conn.close()
