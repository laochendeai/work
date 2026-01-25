import sqlite3
import json

conn = sqlite3.connect('data/gp.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Check cards for 毛自强
cur.execute('''
    SELECT bc.id, bc.company, bc.contact_name, bc.phones_json, bc.emails_json
    FROM business_cards bc 
    WHERE bc.contact_name LIKE ?
    LIMIT 10
''', ('%毛自强%',))

rows = cur.fetchall()
print(f"\n=== Found {len(rows)} cards for 毛自强 ===")
for r in rows:
    print(f"ID: {r['id']}")
    print(f"  Company: {r['company']}")
    print(f"  Contact: {r['contact_name']}")
    print(f"  Phones: {r['phones_json']}")
    print(f"  Emails: {r['emails_json']}")
    
    # Check mentions
    cur.execute('''
        SELECT bcm.role, a.title, a.url
        FROM business_card_mentions bcm
        JOIN announcements a ON bcm.announcement_id = a.id
        WHERE bcm.business_card_id = ?
    ''', (r['id'],))
    mentions = cur.fetchall()
    print(f"  Mentions: {len(mentions)}")
    for m in mentions:
        print(f"    - [{m['role']}] {m['title'][:50]}... | {m['url']}")
    print()

conn.close()
