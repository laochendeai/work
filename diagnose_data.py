#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据质量诊断脚本

系统性分析名片数据中可能存在的问题：
1. 名片缺少公司名
2. 代理机构联系人字段包含多个人但只解析了一个
3. 项目联系人归属错误
4. 电话号码格式问题
5. 重复名片
"""
import json
import re
import sqlite3
from collections import defaultdict

def diagnose():
    conn = sqlite3.connect('data/gp.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    issues = {
        'missing_company': [],        # 名片缺少公司名
        'missing_contact_name': [],   # 名片缺少联系人姓名
        'missing_phone': [],          # 名片缺少电话
        'agent_multi_contacts': [],   # 代理机构联系人字段包含多人
        'project_multi_contacts': [], # 项目联系人可能遗漏
        'duplicate_cards': [],        # 重复名片（同一公司+姓名有多条）
        'wrong_attribution': [],      # 可能的错误归属
    }
    
    # 1. 检查缺少公司名或联系人姓名的名片
    print("=" * 70)
    print("1. 检查名片基础信息完整性...")
    print("=" * 70)
    
    cur.execute("SELECT id, company, contact_name, phones_json FROM business_cards")
    for row in cur.fetchall():
        if not row['company'] or row['company'].strip() == '':
            issues['missing_company'].append({
                'id': row['id'],
                'contact_name': row['contact_name'],
                'phones': row['phones_json']
            })
        if not row['contact_name'] or row['contact_name'].strip() == '':
            issues['missing_contact_name'].append({
                'id': row['id'],
                'company': row['company'],
                'phones': row['phones_json']
            })
        try:
            phones = json.loads(row['phones_json'] or '[]')
            if not phones:
                issues['missing_phone'].append({
                    'id': row['id'],
                    'company': row['company'],
                    'contact_name': row['contact_name']
                })
        except:
            pass
    
    print(f"  缺少公司名的名片: {len(issues['missing_company'])} 条")
    for item in issues['missing_company'][:10]:
        print(f"    - ID {item['id']}: {item['contact_name']}, 电话: {item['phones']}")
    
    print(f"\n  缺少联系人姓名的名片: {len(issues['missing_contact_name'])} 条")
    for item in issues['missing_contact_name'][:10]:
        print(f"    - ID {item['id']}: {item['company']}")
    
    print(f"\n  缺少电话的名片: {len(issues['missing_phone'])} 条")
    
    # 2. 检查公告中可能遗漏的联系人
    print("\n" + "=" * 70)
    print("2. 检查代理机构联系人字段是否包含多人...")
    print("=" * 70)
    
    # 定义匹配多人的模式
    multi_person_pattern = re.compile(r'[，、,]\s*[\u4e00-\u9fa5]{2,4}\s*\d{11}')
    
    cur.execute("SELECT id, url, content FROM announcements WHERE content IS NOT NULL")
    for row in cur.fetchall():
        content = row['content'] or ''
        
        # 查找代理机构联系人行
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if '代理机构联系' in line or ('联系人' in line and '代理' in content[max(0,content.find(line)-200):content.find(line)]):
                # 检查这行是否包含多个联系人
                value = line.split('：')[-1].split(':')[-1] if '：' in line or ':' in line else line
                
                # 查找多个电话模式 (姓名+电话、姓名+电话)
                phones = re.findall(r'1[3-9]\d{9}', value)
                if len(phones) > 1:
                    issues['agent_multi_contacts'].append({
                        'announcement_id': row['id'],
                        'url': row['url'],
                        'line': line.strip()[:100],
                        'phone_count': len(phones)
                    })
                    break
    
    print(f"  代理机构联系人包含多人的公告: {len(issues['agent_multi_contacts'])} 条")
    for item in issues['agent_multi_contacts'][:10]:
        print(f"    - 公告 #{item['announcement_id']}: {item['line'][:80]}...")
        print(f"      发现 {item['phone_count']} 个电话号码")
    
    # 3. 检查是否有名片被错误归属（项目联系人归属到采购人而非代理机构）
    print("\n" + "=" * 70)
    print("3. 检查可能的错误归属...")
    print("=" * 70)
    
    cur.execute("""
        SELECT bcm.id, bcm.role, bc.company, bc.contact_name, bc.phones_json, a.id as ann_id, a.content
        FROM business_card_mentions bcm
        JOIN business_cards bc ON bcm.business_card_id = bc.id
        JOIN announcements a ON bcm.announcement_id = a.id
        WHERE bcm.role = 'project'
    """)
    
    for row in cur.fetchall():
        content = row['content'] or ''
        company = row['company'] or ''
        contact_name = row['contact_name'] or ''
        
        # 检查这个联系人在原文中是否出现在代理机构段落
        if contact_name and '代理机构联系' in content:
            # 查找代理机构段落
            agent_section = ''
            lines = content.split('\n')
            in_agent = False
            for line in lines:
                if '代理机构' in line:
                    in_agent = True
                elif in_agent and ('采购' in line or '项目联系' in line):
                    break
                if in_agent:
                    agent_section += line + '\n'
            
            # 如果联系人姓名出现在代理机构段落，但公司名不是代理机构名称
            if contact_name in agent_section:
                # 提取代理机构名称
                for line in lines:
                    if '代理机构' in line and '名称' in line:
                        agent_name = line.split('：')[-1].split(':')[-1].strip()
                        if agent_name and agent_name != company:
                            issues['wrong_attribution'].append({
                                'mention_id': row['id'],
                                'contact_name': contact_name,
                                'current_company': company,
                                'should_be': agent_name,
                                'announcement_id': row['ann_id']
                            })
                        break
    
    print(f"  可能的错误归属: {len(issues['wrong_attribution'])} 条")
    for item in issues['wrong_attribution'][:10]:
        print(f"    - {item['contact_name']}: 当前归属 '{item['current_company']}', 应该是 '{item['should_be']}'")
    
    # 4. 统计汇总
    print("\n" + "=" * 70)
    print("问题统计汇总")
    print("=" * 70)
    print(f"  缺少公司名:           {len(issues['missing_company']):5d} 条")
    print(f"  缺少联系人姓名:       {len(issues['missing_contact_name']):5d} 条")
    print(f"  缺少电话:             {len(issues['missing_phone']):5d} 条")
    print(f"  代理机构多人遗漏:     {len(issues['agent_multi_contacts']):5d} 条公告")
    print(f"  可能的错误归属:       {len(issues['wrong_attribution']):5d} 条")
    
    # 5. 分析根本原因
    print("\n" + "=" * 70)
    print("根本原因分析")
    print("=" * 70)
    
    causes = []
    
    if issues['missing_company']:
        causes.append("""
【问题1】名片缺少公司名
原因: 解析器在提取联系人时，未正确关联公司名称
位置: main.py _iter_business_cards() 函数中 default_project_company 逻辑
修复: 确保每个名片都有公司归属
""")
    
    if issues['agent_multi_contacts']:
        causes.append("""
【问题2】代理机构联系人字段包含多人但只解析了第一个
原因: 解析器假设联系人字段只有一个人
位置: ccgp_parser.py _extract_contacts_from_content() 第325-346行
       处理代理机构联系方式时，只提取第一个电话和姓名
修复: 类似项目联系人，支持解析多人格式如 "黄丹彤16620120513、崔世杰15800204406"
""")
    
    if issues['wrong_attribution']:
        causes.append("""
【问题3】项目联系人归属错误
原因: 电话号码匹配失败或没有电话可供匹配
位置: main.py _iter_business_cards() 中的 phones_match 逻辑
修复: 改进匹配算法，或根据内容上下文判断归属
""")
    
    for cause in causes:
        print(cause)
    
    conn.close()
    return issues


if __name__ == '__main__':
    diagnose()
