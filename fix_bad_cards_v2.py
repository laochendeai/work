#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""修复名片库中的错误数据"""

import sqlite3
import os
import re
import json

def get_db_connection():
    db_path = os.path.join(os.path.dirname(__file__), 'data', 'gp.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def fix_cards():
    """修复有问题的名片"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("=" * 60)
    print("开始修复名片库中的错误数据...")
    print("=" * 60)
    
    deleted_count = 0
    
    # 1. 删除名字为特定的无效词
    bad_names = ['联系方式', '无', 'nan', 'null', 'None', '名称', '姓名', '联系人']
    placeholders = ','.join(['?'] * len(bad_names))
    cursor.execute(f"SELECT id, contact_name FROM business_cards WHERE contact_name IN ({placeholders})", bad_names)
    rows = cursor.fetchall()
    if rows:
        print(f"\n发现 {len(rows)} 个无效名字记录:")
        ids = [row['id'] for row in rows]
        for row in rows:
            print(f"  删除 ID: {row['id']}, 名字: {row['contact_name']}")
        
        cursor.execute(f"DELETE FROM business_cards WHERE id IN ({','.join(map(str, ids))})")
        deleted_count += len(rows)
    
    # 2. 删除名字包含 '/' 且看起来像数字/电话的
    # 例如: /3394/3307
    cursor.execute("SELECT id, contact_name FROM business_cards WHERE contact_name LIKE '%/%'")
    rows = cursor.fetchall()
    ids_to_delete = []
    
    for row in rows:
        name = row['contact_name']
        # 如果名字主要由数字和斜杠组成，或者是电话号码格式
        if re.search(r'^\d', name) or re.search(r'\d+/\d+', name) or name.startswith('/'):
            print(f"  删除疑似电话号码的名字 ID: {row['id']}, 名字: {name}")
            ids_to_delete.append(row['id'])
            
    if ids_to_delete:
        cursor.execute(f"DELETE FROM business_cards WHERE id IN ({','.join(map(str, ids_to_delete))})")
        deleted_count += len(ids_to_delete)

    # 3. 删除纯数字的名字
    cursor.execute("SELECT id, contact_name FROM business_cards WHERE contact_name GLOB '*[0-9]*' AND contact_name NOT GLOB '*[a-zA-Z\u4e00-\u9fa5]*'")
    rows = cursor.fetchall()
    if rows:
        print(f"\n发现 {len(rows)} 个纯数字/符号名字记录:")
        ids = [row['id'] for row in rows]
        for row in rows:
            print(f"  删除 ID: {row['id']}, 名字: {row['contact_name']}")
        cursor.execute(f"DELETE FROM business_cards WHERE id IN ({','.join(map(str, ids))})")
        deleted_count += len(rows)

    # 4. 删除包含 "电话" 字样的名字 (解析错误)
    cursor.execute("SELECT id, contact_name FROM business_cards WHERE contact_name LIKE '%电话%'")
    rows = cursor.fetchall()
    if rows:
        print(f"\n发现 {len(rows)} 个包含'电话'的名字记录:")
        ids = [row['id'] for row in rows]
        for row in rows:
            print(f"  删除 ID: {row['id']}, 名字: {row['contact_name']}")
        cursor.execute(f"DELETE FROM business_cards WHERE id IN ({','.join(map(str, ids))})")
        deleted_count += len(rows)
        
    conn.commit()
    print(f"\n总计删除 {deleted_count} 条错误记录")
    conn.close()

def deep_search_cui():
    """尝试深度搜索崔士杰"""
    conn = get_db_connection()
    cursor = conn.cursor()
    print("\n" + "=" * 60)
    print("尝试深度搜索 '崔' 姓相关信息...")
    
    cursor.execute("SELECT id, title, content FROM announcements WHERE content LIKE '%崔%'")
    rows = cursor.fetchall()
    
    found_cui = False
    for row in rows:
        content = row['content']
        # 查找 "崔" 后面跟着1-3个中文字符的模式
        matches = re.finditer(r'(崔[\u4e00-\u9fa5]{1,3})', content)
        for match in matches:
            name = match.group(1)
            # 简单的过滤，排除非人名的情况（这只是一个粗略的检查）
            if name not in ['崔先生', '崔女士', '崔工'] and len(name) >= 2:
                print(f"  公告 ID: {row['id']}, 发现可能的姓名: {name}")
                # 显示上下文
                start = max(0, match.start() - 20)
                end = min(len(content), match.end() + 50)
                print(f"    上下文: ...{content[start:end]}...")
                found_cui = True

    if not found_cui:
        print("未发现疑似 '崔' 姓的相关人名。")

    conn.close()

if __name__ == '__main__':
    fix_cards()
    deep_search_cui()
