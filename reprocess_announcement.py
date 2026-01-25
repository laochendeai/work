"""
重新处理指定公告的名片数据

用法：python reprocess_announcement.py <announcement_id 或 URL>
"""
import sys
import sqlite3
import json

def reprocess(identifier: str):
    """重新处理公告的名片数据"""
    conn = sqlite3.connect('data/gp.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # 查找公告
    if identifier.startswith('http'):
        cur.execute('SELECT id, url FROM announcements WHERE url LIKE ?', (f'%{identifier.split("/")[-1].split(".")[0]}%',))
    else:
        cur.execute('SELECT id, url FROM announcements WHERE id = ?', (int(identifier),))
    
    row = cur.fetchone()
    if not row:
        print(f"未找到公告: {identifier}")
        return
    
    announcement_id = row['id']
    url = row['url']
    print(f"找到公告 ID: {announcement_id}")
    print(f"URL: {url}")
    
    # 查找关联的名片
    cur.execute('''
        SELECT bcm.id as mention_id, bcm.business_card_id, bc.company, bc.contact_name
        FROM business_card_mentions bcm
        JOIN business_cards bc ON bcm.business_card_id = bc.id
        WHERE bcm.announcement_id = ?
    ''', (announcement_id,))
    
    mentions = cur.fetchall()
    print(f"\n关联了 {len(mentions)} 条名片记录:")
    for m in mentions:
        print(f"  - {m['company']} / {m['contact_name']} (mention_id: {m['mention_id']}, card_id: {m['business_card_id']})")
    
    confirm = input("\n是否删除这些关联并重新处理? (y/n): ")
    if confirm.lower() != 'y':
        print("取消操作")
        return
    
    # 删除mentions
    cur.execute('DELETE FROM business_card_mentions WHERE announcement_id = ?', (announcement_id,))
    
    # 删除公告记录（这样下次爬取会重新处理）
    cur.execute('DELETE FROM announcements WHERE id = ?', (announcement_id,))
    
    conn.commit()
    print(f"\n已删除公告 {announcement_id} 及其 {len(mentions)} 条名片关联")
    print("请重新运行搜索来重新爬取此公告")
    
    conn.close()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python reprocess_announcement.py <announcement_id 或 URL>")
        sys.exit(1)
    
    reprocess(sys.argv[1])
