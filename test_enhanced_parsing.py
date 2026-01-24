#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强测试：验证中标人信息和表格解析能力
"""
import sys
from pathlib import Path
import json

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from scraper.fetcher import PlaywrightFetcher
from scraper.ccgp_parser import CCGPAnnouncementParser
from scraper.table_parser import SmartTableParser
from bs4 import BeautifulSoup


def test_enhanced_parsing():
    """增强测试：重点验证中标人信息和表格解析"""

    print("=" * 70)
    print("公共资源交易网公告解析增强测试")
    print("=" * 70)

    url = "https://www.ccgp.gov.cn/cggg/zygg/zbgg/202601/t20260120_26095606.htm"

    print(f"\n目标URL: {url}")
    print("\n正在获取页面...")

    # 获取页面内容
    fetcher = PlaywrightFetcher()
    try:
        fetcher.start()
        html = fetcher.get_page(url, wait_for="networkidle")

        if not html:
            print("❌ 获取页面失败")
            return

        print(f"✅ 页面获取成功 (长度: {len(html)} 字符)")

    finally:
        fetcher.stop()

    soup = BeautifulSoup(html, 'lxml')

    # ========== 测试1: 表格结构分析 ==========
    print("\n" + "=" * 70)
    print("【测试1】表格结构分析")
    print("=" * 70)

    table_div = soup.find('div', class_='table')
    if table_div:
        table = table_div.find('table')
        if table:
            table_parser = SmartTableParser()
            structure = table_parser.analyze_table_structure(table)

            print(f"\n表格结构:")
            print(f"  总行数: {structure['total_rows']}")
            print(f"  最大列数: {structure['max_cols']}")
            print(f"  包含跨列(colspan): {structure['has_colspan']}")
            print(f"  包含跨行(rowspan): {structure['has_rowspan']}")
            print(f"  复杂度: {structure['complexity']}")

            # 解析表格
            parsed = table_parser.parse_table(table)

            print(f"\n解析的结构化数据:")
            for category, data in parsed['structured'].items():
                if data and (not isinstance(data, dict) or data):
                    print(f"\n  {category}:")
                    if isinstance(data, dict):
                        for k, v in data.items():
                            if v:
                                print(f"    {k}: {v}")
                    elif isinstance(data, list):
                        for item in data:
                            print(f"    - {item}")
                    else:
                        print(f"    {data}")

    # ========== 测试2: 完整页面解析 ==========
    print("\n" + "=" * 70)
    print("【测试2】完整页面解析")
    print("=" * 70)

    parser = CCGPAnnouncementParser()
    parsed = parser.parse(html, url)

    # ========== 测试3: 中标人信息验证 ==========
    print("\n" + "=" * 70)
    print("【测试3】中标人信息验证 ⭐")
    print("=" * 70)

    formatted = parser.format_for_storage(parsed)

    print(f"\n✅ 中标人（供应商）信息:")
    print(f"  公司名称: {formatted.get('supplier', '❌ 未解析到')}")
    print(f"  公司地址: {formatted.get('supplier_address', '❌ 未解析到')}")
    print(f"  中标金额: {formatted.get('bid_amount', '❌ 未解析到')}")

    # 从原始数据中也查看
    bid_info = parsed.get('content_sections', {}).get('bid_info', {})
    print(f"\n原始中标信息:")
    print(f"  供应商名称: {bid_info.get('supplier', '❌')}")
    print(f"  供应商地址: {bid_info.get('supplier_address', '❌')}")

    # ========== 测试4: 所有联系人信息 ==========
    print("\n" + "=" * 70)
    print("【测试4】所有联系人信息")
    print("=" * 70)

    print(f"\n📋 采购人:")
    print(f"  名称: {formatted.get('buyer_name', '❌')}")
    print(f"  地址: {formatted.get('buyer_address', '❌')}")
    print(f"  联系人: {formatted.get('buyer_contact', '❌')}")
    print(f"  电话: {formatted.get('buyer_phone', '❌')}")

    print(f"\n🤝 代理机构:")
    print(f"  名称: {formatted.get('agent_name', '❌')}")
    print(f"  地址: {formatted.get('agent_address', '❌')}")
    print(f"  联系人: {formatted.get('agent_contact', '❌')}")
    print(f"  电话: {formatted.get('agent_phone', '❌')}")

    print(f"\n📞 项目联系人:")
    contacts = formatted.get('project_contacts', [])
    if isinstance(contacts, list):
        for i, name in enumerate(contacts, 1):
            print(f"    {i}. {name}")
    else:
        print(f"  {contacts}")
    print(f"  电话: {formatted.get('project_phone', '❌')}")

    # ========== 测试5: 存储格式预览 ==========
    print("\n" + "=" * 70)
    print("【测试5】存储格式预览")
    print("=" * 70)

    print(f"\n关键字段:")
    key_fields = [
        ('项目名称', 'project_name'),
        ('项目编号', 'project_no'),
        ('中标人', 'supplier'),
        ('中标金额', 'bid_amount'),
        ('采购人', 'buyer_name'),
        ('代理机构', 'agent_name'),
        ('专家', 'experts'),
    ]

    for label, field in key_fields:
        value = formatted.get(field, '')
        if value:
            if isinstance(value, list):
                value = ', '.join(str(v) for v in value)
            print(f"  {label}: {value[:60]}..." if len(str(value)) > 60 else f"  {label}: {value}")
        else:
            print(f"  {label}: ❌ 未解析到")

    # ========== 保存结果 ==========
    output_file = Path("data/parsed_result_enhanced.json")
    output_file.parent.mkdir(exist_ok=True)

    result = {
        'url': url,
        'formatted': formatted,
        'parsed_raw': parsed,
        'verification': {
            'supplier_parsed': bool(formatted.get('supplier')),
            'supplier_address_parsed': bool(formatted.get('supplier_address')),
            'bid_amount_parsed': bool(formatted.get('bid_amount')),
            'buyer_parsed': bool(formatted.get('buyer_name')),
            'agent_parsed': bool(formatted.get('agent_name')),
        }
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 完整解析结果已保存到: {output_file}")

    # ========== 验证总结 ==========
    print("\n" + "=" * 70)
    print("【验证总结】")
    print("=" * 70)

    verification = result['verification']
    total = len(verification)
    passed = sum(1 for v in verification.values() if v)

    for item, status in verification.items():
        icon = "✅" if status else "❌"
        print(f"  {icon} {item.replace('_', ' ').title()}")

    print(f"\n解析成功率: {passed}/{total} ({int(passed/total*100)}%)")

    if passed == total:
        print("\n🎉 所有关键字段解析成功！")
    else:
        print(f"\n⚠️ {total - passed} 个字段未解析到")

    print("\n" + "=" * 70)


if __name__ == '__main__':
    test_enhanced_parsing()
