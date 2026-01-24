#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试增强版搜索爬虫 - 搜索"机房"
使用多种策略降低反爬风险
"""
import sys
from pathlib import Path
import json
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from scraper.fetcher import PlaywrightFetcher
from scraper.ccgp_searcher_v2 import CCGPSearcherEnhanced
from scraper.ccgp_parser import CCGPAnnouncementParser


def test_enhanced_search_jifang():
    """
    测试增强版搜索 - 搜全文"机房"

    使用策略：
    1. 随机User-Agent
    2. 模拟人工操作（逐字输入、随机延迟）
    3. 先访问首页建立会话
    4. 每步操作都有随机延迟
    """

    print("=" * 70)
    print("公共资源交易网搜索 - 增强版测试")
    print("搜索关键词：机房")
    print("=" * 70)

    # 搜索参数
    keyword = "机房"
    search_type = "fulltext"  # 搜全文
    category = "engineering"   # 工程类
    time_range = "1month"      # 近1月
    max_pages = 2             # 测试只爬2页

    print(f"\n🔍 搜索参数:")
    print(f"  关键词: {keyword}")
    print(f"  搜索类型: {search_type}")
    print(f"  品目: {category}")
    print(f"  时间: {time_range}")
    print(f"  最大页数: {max_pages}")

    print(f"\n🛡️ 反规避策略:")
    print(f"  ✅ 随机User-Agent")
    print(f"  ✅ 模拟人工操作（逐字输入）")
    print(f"  ✅ 随机延迟（3-6秒）")
    print(f"  ✅ 先访问首页建立会话")
    print(f"  ✅ 模拟人类浏览行为")

    # 创建爬虫
    fetcher = PlaywrightFetcher()

    try:
        fetcher.start()

        # 使用增强版搜索器
        searcher = CCGPSearcherEnhanced(fetcher.page)

        print(f"\n开始搜索（这可能需要1-2分钟）...")

        # 执行搜索
        results = searcher.search(
            keyword=keyword,
            search_type=search_type,
            category=category,
            time_range=time_range,
            max_pages=max_pages,
        )

        print(f"\n{'=' * 70}")
        print(f"搜索结果: {len(results)} 条")
        print(f"{'=' * 70}")

        if not results:
            print("\n⚠️ 未找到搜索结果")
            print("\n可能的原因:")
            print("  1. 反爬限制 - 建议稍后再试（等待10-30分钟）")
            print("  2. 搜索条件过严 - 可以尝试扩大时间范围")
            print("  3. 选择器失效 - 网站可能已更新结构")
            print("  4. 今日确实没有相关公告 - 可以尝试时间范围改为'1month'")
            print("\n💡 建议尝试:")
            print("  - 使用列表页爬取方式（更稳定）")
            print("  - 改用其他关键词（如'智能化'、'弱电'等）")
            print("  - 扩大时间范围到'1month'或'3months'")
            return

        # 显示搜索结果
        print(f"\n搜索结果:")
        print("-" * 70)

        for i, result in enumerate(results, 1):
            title = result.get('title', '未知标题')
            # 高亮显示"机房"关键词
            highlighted = title.replace('机房', '⭐机房⭐')
            print(f"{i}. {highlighted[:80]}")

        # ===== 爬取详情页（如果搜索成功）=====
        if results:
            print(f"\n{'=' * 70}")
            print("是否要爬取详情页？(演示前2条)")
            print(f"{'=' * 70}")

            # 只爬前2个结果作为演示
            crawler_results = []
            parser = CCGPAnnouncementParser()

            for i, result in enumerate(results[:2], 1):
                url = result.get('url', '')
                if not url:
                    continue

                print(f"\n[{i}/2] {result.get('title', '')[:50]}")
                print(f"     URL: {url}")

                try:
                    # 获取详情页 - 增加延迟
                    import time
                    time.sleep(3)

                    detail_html = fetcher.get_page(url)
                    if not detail_html:
                        print("     ❌ 获取详情页失败")
                        continue

                    # 解析详情页
                    parsed = parser.parse(detail_html, url)
                    formatted = parser.format_for_storage(parsed)

                    crawler_results.append(formatted)

                    # 显示关键信息
                    print(f"     ✅ 项目: {formatted.get('project_name', '')[:40]}")
                    print(f"     📍 采购人: {formatted.get('buyer_name', '')[:30]}")
                    print(f"     🏆 中标人: {formatted.get('supplier', '')[:30]}")
                    print(f"     💰 金额: {formatted.get('bid_amount', '')[:30]}")

                except Exception as e:
                    print(f"     ❌ 失败: {e}")

        # ===== 保存结果 =====
        print(f"\n保存结果...")

        output_file = Path("data/search_jifang_results.json")
        output_file.parent.mkdir(exist_ok=True)

        save_data = {
            'search_params': {
                'keyword': keyword,
                'search_type': search_type,
                'category': category,
                'time_range': time_range,
                'search_time': datetime.now().isoformat(),
            },
            'summary': {
                'total_results': len(results),
                'detailed_crawled': len(crawler_results) if results else 0,
            },
            'search_results': results,
            'detailed_results': crawler_results if results else [],
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)

        print(f"✅ 结果已保存到: {output_file}")

        # ===== 统计信息 =====
        print(f"\n{'=' * 70}")
        print("统计信息:")
        print(f"{'=' * 70}")
        print(f"搜索结果总数: {len(results)}")

        if results and 'crawler_results' in locals():
            print(f"成功解析详情: {len(crawler_results)}")

            # 统计包含"机房"的项目
            jifang_projects = [
                r for r in crawler_results
                if '机房' in r.get('project_name', '') or '机房' in r.get('title', '')
            ]

            if jifang_projects:
                print(f"\n包含'机房'的项目详情:")
                for r in jifang_projects:
                    print(f"  - {r.get('project_name', '')[:60]}")
                    print(f"    采购人: {r.get('buyer_name', '')}")
                    print(f"    中标人: {r.get('supplier', '')}")

    finally:
        fetcher.stop()

    print(f"\n{'=' * 70}")
    print("✅ 测试完成！")
    print(f"{'=' * 70}")

    # ===== 重要提醒 =====
    print(f"\n⚠️  重要提醒:")
    print(f"  1. 如果触发反爬限制，请等待10-30分钟后再试")
    print(f"  2. 建议每天搜索次数不超过3-5次")
    print(f"  3. 每次搜索间隔至少30分钟")
    print(f"  4. 避开工作时间高峰（9:00-17:00）")
    print(f"  5. 如需大量数据，优先使用列表页爬取方式")

    print(f"\n💡 替代方案:")
    print(f"  如果搜索平台受限，可以使用列表页爬取 + 本地过滤")
    print(f"  参考: test_list_search.py")


if __name__ == '__main__':
    test_enhanced_search_jifang()
