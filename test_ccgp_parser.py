#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试政府采购网公告解析器
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from scraper.fetcher import PlaywrightFetcher
from scraper.ccgp_parser import CCGPAnnouncementParser
import json


def test_parse_ccgp_page():
    """测试解析政府采购网公告页面"""

    print("=" * 60)
    print("测试政府采购网公告解析器")
    print("=" * 60)

    # 目标URL
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

    # 解析页面
    print("\n正在解析页面...")
    parser = CCGPAnnouncementParser()
    parsed = parser.parse(html, url)

    # 显示解析结果
    print("\n" + "=" * 60)
    print("解析结果")
    print("=" * 60)

    # 元数据
    print("\n【元数据】")
    meta = parsed.get('meta', {})
    print(f"  标题: {meta.get('title', '')}")
    print(f"  发布日期: {meta.get('publish_date', '')}")

    # 概要表格
    print("\n【概要表格】")
    summary = parsed.get('summary_table', {})
    for key, value in summary.items():
        if key == 'total_amount' and isinstance(value, dict):
            print(f"  {key}: {value.get('original', '')}")
        else:
            print(f"  {key}: {value}")

    # 联系人信息
    print("\n【联系人信息】")
    contacts = parsed.get('contacts', {})

    if contacts.get('buyer'):
        print("  采购人:")
        buyer = contacts['buyer']
        print(f"    名称: {buyer.get('name', '')}")
        print(f"    地址: {buyer.get('address', '')}")
        print(f"    联系人: {buyer.get('contact_name', '')}")
        print(f"    电话: {buyer.get('phone', '')}")

    if contacts.get('agent'):
        print("  代理机构:")
        agent = contacts['agent']
        print(f"    名称: {agent.get('name', '')}")
        print(f"    地址: {agent.get('address', '')}")
        print(f"    联系人: {agent.get('contact_name', '')}")
        print(f"    电话: {agent.get('phone', '')}")

    if contacts.get('project'):
        print("  项目联系人:")
        project = contacts['project']
        print(f"    姓名: {project.get('names', [])}")
        print(f"    电话: {project.get('phone', '')}")

    if contacts.get('supplier'):
        print("  供应商:")
        supplier = contacts['supplier']
        print(f"    名称: {supplier.get('name', '')}")
        print(f"    地址: {supplier.get('address', '')}")

    # 格式化为存储格式
    print("\n" + "=" * 60)
    print("存储格式预览")
    print("=" * 60)

    formatted = parser.format_for_storage(parsed)
    for key, value in formatted.items():
        if isinstance(value, list):
            value = ', '.join(str(v) for v in value)
        if value and str(value).strip():
            print(f"  {key}: {str(value)[:50]}..." if len(str(value)) > 50 else f"  {key}: {value}")

    # 保存完整解析结果到JSON
    output_file = Path("data/parsed_result.json")
    output_file.parent.mkdir(exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(parsed, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 完整解析结果已保存到: {output_file}")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == '__main__':
    test_parse_ccgp_page()
