#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量修正名片归属错误

此脚本会：
1. 遍历所有已存储的公告
2. 重新解析公告内容
3. 使用修正后的归属逻辑重新生成名片关联
4. 更新数据库中的名片归属

用法：
    python fix_card_attribution.py              # 预览模式（不修改数据）
    python fix_card_attribution.py --apply      # 应用修正
    python fix_card_attribution.py --url <URL>  # 只处理特定公告
"""
import argparse
import logging
import re
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional

from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def clean_phone(p: str) -> str:
    """清理电话号码，只保留数字"""
    return "".join(filter(str.isdigit, p)) if p else ""


def phones_match(phone1: str, phone2: str) -> bool:
    """检查两个电话号码是否匹配（支持部分匹配）"""
    if not phone1 or not phone2:
        return False
    p1 = clean_phone(phone1)
    p2 = clean_phone(phone2)
    if not p1 or not p2:
        return False
    # 完全匹配或后8位匹配
    return p1 == p2 or (len(p1) >= 8 and len(p2) >= 8 and p1[-8:] == p2[-8:])


def extract_phone(text: str) -> str:
    """从文本中提取电话号码"""
    if not text:
        return ''
    phone_patterns = [
        r'1[3-9]\d{9}',
        r'0\d{2,3}-?\d{7,8}',
    ]
    for pattern in phone_patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)
    return ''


def parse_contacts_from_content(content: str) -> Dict:
    """从公告内容中解析联系人信息"""
    contacts = {
        'buyer': {'name': '', 'phone': ''},
        'agent': {'name': '', 'phone': ''},
        'project': {'names': [], 'phone': ''},
    }
    
    if not content:
        return contacts
    
    lines = content.split('\n')
    current_type = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # 识别段落类型
        if '采购人信息' in line or '1.采购人' in line or '1、采购人' in line:
            current_type = 'buyer'
        elif '代理机构' in line or '2.采购代理机构' in line or '2、采购代理机构' in line:
            current_type = 'agent'
        elif '项目联系' in line or '3.项目' in line or '3、项目' in line:
            current_type = 'project'
        elif current_type:
            # 解析具体字段
            if '名称' in line or '名 称' in line:
                value = line.split('：')[-1].split(':')[-1].strip()
                if current_type in ['buyer', 'agent']:
                    contacts[current_type]['name'] = value
            elif '联系方式' in line:
                value = line.split('：')[-1].split(':')[-1].strip()
                phone = extract_phone(value)
                if phone and current_type in ['buyer', 'agent']:
                    contacts[current_type]['phone'] = phone
            elif '项目联系人' in line:
                value = line.split('：')[-1].split(':')[-1].strip()
                names = [n.strip() for n in re.split(r'[、,，]', value) if n.strip()]
                contacts['project']['names'] = names
            elif ('电话' in line or '电 话' in line) and current_type == 'project':
                value = line.split('：')[-1].split(':')[-1].strip()
                phone = extract_phone(value)
                if phone:
                    contacts['project']['phone'] = phone
    
    return contacts


def determine_correct_company(
    contact_name: str,
    project_phone: str,
    buyer_name: str,
    buyer_phone: str,
    agent_name: str,
    agent_phone: str
) -> str:
    """确定联系人的正确归属公司"""
    
    # 如果项目联系人电话与代理机构电话匹配
    if agent_name and phones_match(project_phone, agent_phone):
        return agent_name
    
    # 如果项目联系人电话与采购人电话匹配
    if buyer_name and phones_match(project_phone, buyer_phone):
        return buyer_name
    
    # 默认归属代理机构（项目联系人通常是代理机构员工）
    if agent_name:
        return agent_name
    
    # 如果没有代理机构，归属采购人
    return buyer_name


def analyze_announcement(conn: sqlite3.Connection, announcement_id: int) -> Dict:
    """分析一条公告的名片归属"""
    cur = conn.cursor()
    
    # 获取公告内容
    cur.execute('SELECT id, url, content FROM announcements WHERE id = ?', (announcement_id,))
    ann = cur.fetchone()
    if not ann:
        return None
    
    ann_id, url, content = ann
    
    # 解析联系人信息
    contacts = parse_contacts_from_content(content)
    
    buyer_name = contacts['buyer']['name']
    buyer_phone = contacts['buyer']['phone']
    agent_name = contacts['agent']['name']
    agent_phone = contacts['agent']['phone']
    project_names = contacts['project']['names']
    project_phone = contacts['project']['phone']
    
    # 获取现有的名片关联
    cur.execute('''
        SELECT bcm.id as mention_id, bcm.business_card_id, bcm.role,
               bc.company, bc.contact_name, bc.phones_json
        FROM business_card_mentions bcm
        JOIN business_cards bc ON bcm.business_card_id = bc.id
        WHERE bcm.announcement_id = ?
    ''', (announcement_id,))
    
    mentions = cur.fetchall()
    
    # 分析需要修正的名片
    fixes = []
    for m in mentions:
        mention_id, card_id, role, current_company, contact_name, phones_json = m
        
        # 只处理项目联系人角色
        if role != 'project':
            continue
        
        # 确定正确的公司
        correct_company = determine_correct_company(
            contact_name, project_phone,
            buyer_name, buyer_phone,
            agent_name, agent_phone
        )
        
        if current_company != correct_company and correct_company:
            fixes.append({
                'mention_id': mention_id,
                'card_id': card_id,
                'contact_name': contact_name,
                'current_company': current_company,
                'correct_company': correct_company,
                'project_phone': project_phone,
                'agent_phone': agent_phone,
                'buyer_phone': buyer_phone,
            })
    
    return {
        'announcement_id': ann_id,
        'url': url,
        'buyer_name': buyer_name,
        'buyer_phone': buyer_phone,
        'agent_name': agent_name,
        'agent_phone': agent_phone,
        'project_names': project_names,
        'project_phone': project_phone,
        'fixes': fixes,
    }


def apply_fix(conn: sqlite3.Connection, fix: Dict, announcement_id: int) -> bool:
    """应用一条修正"""
    cur = conn.cursor()
    
    contact_name = fix['contact_name']
    correct_company = fix['correct_company']
    old_card_id = fix['card_id']
    mention_id = fix['mention_id']
    
    # 查找或创建正确公司的名片
    cur.execute('''
        SELECT id, phones_json, emails_json FROM business_cards
        WHERE company = ? AND contact_name = ?
    ''', (correct_company, contact_name))
    
    existing = cur.fetchone()
    
    if existing:
        # 使用已存在的名片
        new_card_id = existing[0]
    else:
        # 创建新名片
        # 获取旧名片的电话和邮箱
        cur.execute('SELECT phones_json, emails_json FROM business_cards WHERE id = ?', (old_card_id,))
        old_card = cur.fetchone()
        phones_json = old_card[0] if old_card else '[]'
        emails_json = old_card[1] if old_card else '[]'
        
        cur.execute('''
            INSERT INTO business_cards (company, contact_name, phones_json, emails_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (correct_company, contact_name, phones_json, emails_json, 
              datetime.now().isoformat(), datetime.now().isoformat()))
        new_card_id = cur.lastrowid
    
    # 更新mention指向新名片
    cur.execute('''
        UPDATE business_card_mentions
        SET business_card_id = ?
        WHERE id = ?
    ''', (new_card_id, mention_id))
    
    return True


def main():
    parser = argparse.ArgumentParser(description='修正名片归属错误')
    parser.add_argument('--apply', action='store_true', help='应用修正（不加此参数只预览）')
    parser.add_argument('--url', type=str, help='只处理特定URL的公告')
    parser.add_argument('--limit', type=int, default=0, help='限制处理数量（0=不限制）')
    args = parser.parse_args()
    
    conn = sqlite3.connect('data/gp.db')
    cur = conn.cursor()
    
    # 获取所有公告
    if args.url:
        cur.execute('SELECT id FROM announcements WHERE url LIKE ?', (f'%{args.url}%',))
    else:
        cur.execute('SELECT id FROM announcements')
    
    announcement_ids = [row[0] for row in cur.fetchall()]
    
    if args.limit > 0:
        announcement_ids = announcement_ids[:args.limit]
    
    logger.info(f"开始分析 {len(announcement_ids)} 条公告...")
    
    total_fixes = 0
    processed = 0
    
    for ann_id in announcement_ids:
        result = analyze_announcement(conn, ann_id)
        if not result:
            continue
        
        processed += 1
        fixes = result['fixes']
        
        if fixes:
            logger.info(f"\n公告 #{ann_id}: {result['url'][:60]}...")
            logger.info(f"  采购人: {result['buyer_name']} (电话: {result['buyer_phone']})")
            logger.info(f"  代理机构: {result['agent_name']} (电话: {result['agent_phone']})")
            logger.info(f"  项目联系人电话: {result['project_phone']}")
            
            for fix in fixes:
                logger.info(f"  需修正: {fix['contact_name']}")
                logger.info(f"    当前归属: {fix['current_company']}")
                logger.info(f"    正确归属: {fix['correct_company']}")
                
                if args.apply:
                    apply_fix(conn, fix, ann_id)
                    logger.info(f"    ✓ 已修正")
                
                total_fixes += 1
    
    if args.apply:
        conn.commit()
        logger.info(f"\n完成！处理了 {processed} 条公告，修正了 {total_fixes} 条名片归属")
    else:
        logger.info(f"\n预览完成！共有 {total_fixes} 条名片需要修正")
        if total_fixes > 0:
            logger.info("使用 --apply 参数来应用修正")
    
    conn.close()


if __name__ == '__main__':
    main()
