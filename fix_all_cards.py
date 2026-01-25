#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全面修复名片数据

此脚本会：
1. 重新解析所有公告内容
2. 提取遗漏的代理机构联系人（多人情况）
3. 修正项目联系人的公司归属
4. 补充缺少公司名的名片

用法：
    python fix_all_cards.py              # 预览模式
    python fix_all_cards.py --apply      # 应用修正
"""
import argparse
import json
import logging
import re
import sqlite3
from datetime import datetime
from typing import Dict, List, Set

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def clean_phone(p: str) -> str:
    return "".join(filter(str.isdigit, p)) if p else ""


def phones_match(phone1: str, phone2: str) -> bool:
    if not phone1 or not phone2:
        return False
    p1 = clean_phone(phone1)
    p2 = clean_phone(phone2)
    if not p1 or not p2:
        return False
    return p1 == p2 or (len(p1) >= 8 and len(p2) >= 8 and p1[-8:] == p2[-8:])


def extract_phone(text: str) -> str:
    if not text:
        return ''
    patterns = [r'1[3-9]\d{9}', r'0\d{2,3}-?\d{7,8}']
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)
    return ''


def parse_contact_info(text: str) -> tuple:
    """解析联系人信息，返回 (姓名, 电话, 邮箱)"""
    phone = extract_phone(text)
    email = ''
    email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
    if email_match:
        email = email_match.group(0)
    
    name = text
    if phone:
        name = name.replace(phone, '')
    if email:
        name = name.replace(email, '')
    name = re.sub(r'[、，,：:()]', '', name).strip()
    
    return name, phone, email


def parse_contacts_from_content(content: str) -> Dict:
    """从公告内容重新解析联系人"""
    contacts = {
        'buyer': {'name': '', 'phone': '', 'contacts_list': []},
        'agent': {'name': '', 'phone': '', 'contacts_list': []},
        'project': {'names': [], 'phone': '', 'details': []},
    }
    
    if not content:
        return contacts
    
    lines = content.split('\n')
    current_type = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # 识别段落
        if '采购人信息' in line or '1.采购人' in line or '1、采购人' in line or '采购单位信息' in line:
            current_type = 'buyer'
        elif '代理机构' in line and ('信息' in line or '2.' in line or '2、' in line):
            current_type = 'agent'
        elif '项目联系' in line or '3.项目' in line or '3、项目' in line:
            current_type = 'project'
        elif current_type:
            # 解析字段
            if '名称' in line or '名 称' in line:
                value = line.split('：')[-1].split(':')[-1].strip()
                if current_type in ['buyer', 'agent']:
                    contacts[current_type]['name'] = value
            elif '联系方式' in line or '联系人' in line:
                value = line.split('：')[-1].split(':')[-1].strip()
                
                # 解析多人格式
                parts = [p.strip() for p in re.split(r'[、，,]', value) if p.strip()]
                contacts_list = []
                first_phone = ''
                
                for part in parts:
                    name, phone, email = parse_contact_info(part)
                    if name or phone:
                        contacts_list.append({'name': name, 'phone': phone, 'email': email})
                        if not first_phone and phone:
                            first_phone = phone
                
                if current_type in ['buyer', 'agent']:
                    contacts[current_type]['contacts_list'] = contacts_list
                    contacts[current_type]['phone'] = first_phone
                    
            elif '项目联系人' in line:
                value = line.split('：')[-1].split(':')[-1].strip()
                parts = [p.strip() for p in re.split(r'[、，,]', value) if p.strip()]
                details = []
                for part in parts:
                    name, phone, _ = parse_contact_info(part)
                    if name:
                        details.append({'name': name, 'phone': phone})
                contacts['project']['details'] = details
                contacts['project']['names'] = [d['name'] for d in details]
                
            elif ('电话' in line or '电 话' in line) and current_type == 'project':
                value = line.split('：')[-1].split(':')[-1].strip()
                phone = extract_phone(value)
                if phone:
                    contacts['project']['phone'] = phone
    
    return contacts


def get_or_create_card(conn: sqlite3.Connection, company: str, contact_name: str, 
                       phones: List[str], emails: List[str], dry_run: bool = True) -> int:
    """获取或创建名片，返回card_id"""
    cur = conn.cursor()
    
    cur.execute('''
        SELECT id, phones_json, emails_json FROM business_cards
        WHERE company = ? AND contact_name = ?
    ''', (company, contact_name))
    
    row = cur.fetchone()
    
    if row:
        card_id = row[0]
        # 合并电话和邮箱
        if not dry_run:
            existing_phones = set(json.loads(row[1] or '[]'))
            existing_emails = set(json.loads(row[2] or '[]'))
            new_phones = existing_phones | set(phones)
            new_emails = existing_emails | set(emails)
            
            if new_phones != existing_phones or new_emails != existing_emails:
                cur.execute('''
                    UPDATE business_cards SET phones_json = ?, emails_json = ?, updated_at = ?
                    WHERE id = ?
                ''', (json.dumps(list(new_phones)), json.dumps(list(new_emails)),
                      datetime.now().isoformat(), card_id))
        return card_id
    else:
        if not dry_run:
            cur.execute('''
                INSERT INTO business_cards (company, contact_name, phones_json, emails_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (company, contact_name, json.dumps(phones), json.dumps(emails),
                  datetime.now().isoformat(), datetime.now().isoformat()))
            return cur.lastrowid
        else:
            return -1  # 预览模式返回负数


def add_mention(conn: sqlite3.Connection, card_id: int, announcement_id: int, 
                role: str, dry_run: bool = True) -> bool:
    """添加名片与公告的关联"""
    if dry_run or card_id < 0:
        return True
        
    cur = conn.cursor()
    try:
        cur.execute('''
            INSERT OR IGNORE INTO business_card_mentions (business_card_id, announcement_id, role, created_at)
            VALUES (?, ?, ?, ?)
        ''', (card_id, announcement_id, role, datetime.now().isoformat()))
        return True
    except:
        return False


def process_announcement(conn: sqlite3.Connection, ann_id: int, content: str, 
                        dry_run: bool = True) -> Dict:
    """处理单条公告，返回修复统计"""
    stats = {
        'new_agent_contacts': 0,
        'fixed_project_attribution': 0,
        'new_cards': 0,
    }
    
    contacts = parse_contacts_from_content(content)
    
    buyer_name = contacts['buyer']['name']
    buyer_phone = contacts['buyer']['phone']
    agent_name = contacts['agent']['name']
    agent_phone = contacts['agent']['phone']
    agent_contacts = contacts['agent']['contacts_list']
    project_details = contacts['project']['details']
    project_phone = contacts['project']['phone']
    
    # 1. 处理代理机构联系人（多人情况）
    for contact in agent_contacts:
        name = contact.get('name', '').strip()
        phone = contact.get('phone', '').strip()
        email = contact.get('email', '').strip()
        
        if agent_name and name:
            card_id = get_or_create_card(
                conn, agent_name, name,
                [phone] if phone else [],
                [email] if email else [],
                dry_run
            )
            if card_id and card_id > 0:
                add_mention(conn, card_id, ann_id, 'agent', dry_run)
            stats['new_agent_contacts'] += 1
    
    # 2. 处理项目联系人归属
    default_company = agent_name if agent_name else buyer_name
    
    for detail in project_details:
        name = detail.get('name', '').strip()
        p_phone = detail.get('phone', '') or project_phone
        
        if not name:
            continue
        
        # 确定正确归属
        if agent_name and phones_match(p_phone, agent_phone):
            company = agent_name
        elif buyer_name and phones_match(p_phone, buyer_phone):
            company = buyer_name
        else:
            company = default_company
        
        if company and name:
            card_id = get_or_create_card(
                conn, company, name,
                [p_phone] if p_phone else [],
                [],
                dry_run
            )
            if card_id and card_id > 0:
                add_mention(conn, card_id, ann_id, 'project', dry_run)
            stats['fixed_project_attribution'] += 1
    
    return stats


def main():
    parser = argparse.ArgumentParser(description='全面修复名片数据')
    parser.add_argument('--apply', action='store_true', help='应用修正')
    parser.add_argument('--limit', type=int, default=0, help='限制处理数量')
    args = parser.parse_args()
    
    dry_run = not args.apply
    
    conn = sqlite3.connect('data/gp.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # 获取所有公告
    cur.execute('SELECT id, content FROM announcements WHERE content IS NOT NULL')
    rows = cur.fetchall()
    
    if args.limit > 0:
        rows = rows[:args.limit]
    
    logger.info(f"开始处理 {len(rows)} 条公告... (预览模式: {dry_run})")
    
    total_stats = {
        'new_agent_contacts': 0,
        'fixed_project_attribution': 0,
    }
    
    for row in rows:
        stats = process_announcement(conn, row['id'], row['content'], dry_run)
        total_stats['new_agent_contacts'] += stats['new_agent_contacts']
        total_stats['fixed_project_attribution'] += stats['fixed_project_attribution']
    
    if not dry_run:
        conn.commit()
    
    logger.info("=" * 60)
    logger.info("处理完成！统计：")
    logger.info(f"  新增代理机构联系人: {total_stats['new_agent_contacts']}")
    logger.info(f"  修正项目联系人归属: {total_stats['fixed_project_attribution']}")
    
    if dry_run:
        logger.info("\n这是预览模式，没有实际修改数据。")
        logger.info("使用 --apply 参数来应用修正。")
    
    conn.close()


if __name__ == '__main__':
    main()
