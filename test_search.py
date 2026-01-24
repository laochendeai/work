#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试公共资源交易网智能搜索
完全模拟人工操作：搜索"智能"，工程类，今日
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from scraper.fetcher import PlaywrightFetcher
from scraper.ccgp_searcher import CCGPSearcher
from scraper.ccgp_parser import CCGPAnnouncementParser


def test_intelligent_search():
    """
    测试智能搜索功能

    模拟操作：
    1. 打开搜索平台
    2. 设置品目为"工程类"
    3. 设置时间为"今日"
    4. 输入关键词"智能"
    5. 点击"搜全文"
    6. 爬取搜索结果
    7. 访问详情页
    """

    print("=" * 70)
    print("公共资源交易网智能搜索测试")
    print("=" * 70)

    # 创建爬虫实例
    fetcher = PlaywrightFetcher()

    try:
        fetcher.start()

        # 创建搜索器
        searcher = CCGPSearcher(fetcher.page)

        # 执行搜索
        print("\n🔍 执行搜索:")
        print("  关键词: 智能")
        print("  品目: 工程类")
        print("  时间: 今日")
        print("  类别: 所有类别")
        print("  类型: 所有类型")

        results = searcher.search(
            keyword="智能",
            search_type="fulltext",  # 搜全文
            category="engineering",  # 工程类
            time_range="today",      # 今日
            announcement_type="all",
            region="all",
            max_pages=2,  # 测试只爬2页
        )

        print(f"\n✅ 搜索完成！获取到 {len(results)} 条结果")

        if not results:
            print("\n⚠️ 没有找到匹配的结果")
            return

        # 显示搜索结果摘要
        print("\n" + "=" * 70)
        print("搜索结果摘要:")
        print("=" * 70)

        for i, result in enumerate(results[:10], 1):
            print(f"\n{i}. {result.get('title', '未知标题')}")
            print(f"   URL: {result.get('url', '')}")

        if len(results) > 10:
            print(f"\n... 还有 {len(results) - 10} 条结果")

        # ========== 爬取详情页 ==========
        print("\n" + "=" * 70)
        print("开始爬取详情页...")
        print("=" * 70)

        parser = CCGPAnnouncementParser()
        detailed_results = []

        # 只爬前3个结果作为演示
        for i, result in enumerate(results[:3], 1):
            url = result.get('url', '')
            if not url:
                continue

            print(f"\n[{i}/{len(results[:3])}] 正在爬取: {result.get('title', '')[:40]}")
            print(f"     URL: {url}")

            try:
                # 获取详情页
                html = fetcher.get_page(url)
                if not html:
                    print("     ❌ 获取失败")
                    continue

                # 解析详情页
                parsed = parser.parse(html, url)
                formatted = parser.format_for_storage(parsed)

                detailed_results.append(formatted)

                # 显示关键信息
                print(f"     ✅ 项目名称: {formatted.get('project_name', '')[:40]}")
                print(f"     📍 采购人: {formatted.get('buyer_name', '')}")
                print(f"     🏆 中标人: {formatted.get('supplier', '')}")
                print(f"     💰 中标金额: {formatted.get('bid_amount', '')}")

            except Exception as e:
                print(f"     ❌ 失败: {e}")

        # ========== 保存结果 ==========
        print("\n" + "=" * 70)
        print("保存结果...")
        print("=" * 70)

        import json
        from datetime import datetime

        output_file = Path("data/search_results.json")
        output_file.parent.mkdir(exist_ok=True)

        save_data = {
            'search_params': {
                'keyword': '智能',
                'category': '工程类',
                'time_range': '今日',
                'search_time': datetime.now().isoformat(),
            },
            'summary': {
                'total_results': len(results),
                'detailed_crawled': len(detailed_results),
            },
            'results': results,
            'detailed_results': detailed_results,
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)

        print(f"✅ 结果已保存到: {output_file}")

        # ========== 统计信息 ==========
        print("\n" + "=" * 70)
        print("统计信息:")
        print("=" * 70)
        print(f"搜索结果总数: {len(results)}")
        print(f"成功爬取详情: {len(detailed_results)}")

        # 统计中标人
        suppliers = [r.get('supplier', '') for r in detailed_results if r.get('supplier')]
        if suppliers:
            print(f"\n中标企业:")
            for supplier in set(suppliers):
                count = suppliers.count(supplier)
                print(f"  - {supplier}: {count} 个项目")

    finally:
        fetcher.stop()

    print("\n" + "=" * 70)
    print("✅ 测试完成！")
    print("=" * 70)


if __name__ == '__main__':
    test_intelligent_search()
