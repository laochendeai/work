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
from scraper.ccgp_searcher_enhanced import CCGPSearcherSync
from scraper.ccgp_parser import CCGPAnnouncementParser


def test_enhanced_search_jifang():
    """
    测试增强版搜索 - 搜全文"机房"

    使用策略：
    1. 随机User-Agent
    2. 模拟人工操作
    3. 增加随机延迟
    4. 先访问首页建立会话
    """

    print("=" * 70)
    print("公共资源交易网搜索 - 增强版测试")
    print("=" * 70)

    # 搜索参数
    keyword = "机房"
    search_type = "fulltext"  # 搜全文
    category = "engineering"   # 工程类
    time_range = "1month"      # 近1月（扩大时间范围提高成功率）
    max_pages = 2             # 测试只爬2页

    print(f"\n🔍 搜索参数:")
    print(f"  关键词: {keyword}")
    print(f"  搜索类型: {search_type}")
    print(f"  品目: {category}")
    print(f"  时间: {time_range}")
    print(f"  最大页数: {max_pages}")

    # 创建爬虫
    fetcher = PlaywrightFetcher()

    try:
        fetcher.start()

        # 使用增强版搜索器
        searcher = CCGPSearcherSync(fetcher.page)

        print(f"\n开始搜索...")

        # 执行搜索（会使用多种反规避策略）
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
            print("  1. 反爬限制 - 建议稍后再试")
            print("  2. 搜索条件过严 - 尝试扩大时间范围")
            print("  3. 选择器失效 - 网站可能已更新")
            return

        # 显示搜索结果
        print(f"\n搜索结果 (前10条):")
        print("-" * 70)

        for i, result in enumerate(results[:10], 1):
            print(f"{i}. {result.get('title', '未知标题')[:70]}")
            print(f"   URL: {result.get('url', '')}")

        if len(results) > 10:
            print(f"\n... 还有 {len(results) - 10} 条结果")

        # ===== 爬取详情页 =====
        print(f"\n{'=' * 70}")
        print("开始爬取详情页...")
        print(f"{'=' * 70}")

        parser = CCGPAnnouncementParser()
        detailed_results = []

        # 只爬前3个结果作为演示
        crawl_count = min(3, len(results))

        for i, result in enumerate(results[:crawl_count], 1):
            url = result.get('url', '')
            if not url:
                continue

            print(f"\n[{i}/{crawl_count}] {result.get('title', '')[:50]}")
            print(f"     URL: {url}")

            try:
                # 获取详情页 - 增加延迟避免触发限制
                import time
                time.sleep(3)  # 每个详情页间隔3秒

                detail_html = fetcher.get_page(url)
                if not detail_html:
                    print("     ❌ 获取详情页失败")
                    continue

                # 解析详情页
                parsed = parser.parse(detail_html, url)
                formatted = parser.format_for_storage(parsed)

                detailed_results.append(formatted)

                # 显示关键信息
                print(f"     ✅ 项目名称: {formatted.get('project_name', '')[:50]}")
                print(f"     📍 采购人: {formatted.get('buyer_name', '')[:30]}")
                print(f"     🏆 中标人: {formatted.get('supplier', '')[:30]}")
                print(f"     💰 中标金额: {formatted.get('bid_amount', '')[:30]}")

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
                'detailed_crawled': len(detailed_results),
            },
            'search_results': results,
            'detailed_results': detailed_results,
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)

        print(f"✅ 结果已保存到: {output_file}")

        # ===== 统计信息 =====
        print(f"\n{'=' * 70}")
        print("统计信息:")
        print(f"{'=' * 70}")
        print(f"搜索结果总数: {len(results)}")
        print(f"成功解析详情: {len(detailed_results)}")

        # 统计包含"机房"的项目
        jifang_projects = [
            r for r in detailed_results
            if '机房' in r.get('project_name', '') or '机房' in r.get('title', '')
        ]

        print(f"包含'机房'的项目: {len(jifang_projects)}")

        if jifang_projects:
            print(f"\n相关项目详情:")
            for r in jifang_projects:
                print(f"  - {r.get('project_name', '')[:50]}")
                print(f"    中标人: {r.get('supplier', '')}")

    finally:
        fetcher.stop()

    print(f"\n{'=' * 70}")
    print("✅ 测试完成！")
    print(f"{'=' * 70}")

    # ===== 使用建议 =====
    print(f"\n💡 降低反爬风险的建议:")
    print(f"  1. 每次搜索间隔至少5-10分钟")
    print(f"  2. 每天搜索次数不超过3-5次")
    print(f"  3. 使用不同的关键词和条件组合")
    print(f"  4. 避开高峰时段（工作时间）")
    print(f"  5. 考虑使用代理IP池")
    print(f"  6. 优先使用列表页爬取方式")


if __name__ == '__main__':
    test_enhanced_search_jifang()
