#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
替代方案：通过列表页实现搜索功能
避免搜索平台的反爬限制，直接爬取分类列表并过滤
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent))

from scraper.fetcher import PlaywrightFetcher
from scraper.ccgp_parser import CCGPAnnouncementParser
from bs4 import BeautifulSoup


def search_via_list_pages(
    keyword: str = "智能",
    category: str = "engineering",  # engineering, goods, services
    days: int = 1,  # 最近几天
    max_results: int = 20,
):
    """
    通过列表页搜索公告

    Args:
        keyword: 搜索关键词（如"智能"）
        category: 品目类别
        days: 搜索最近几天的公告
        max_results: 最多返回结果数
    """
    print("=" * 70)
    print("政府采购网列表页搜索")
    print("=" * 70)

    # 分类URL映射
    category_urls = {
        'engineering': 'https://www.ccgp.gov.cn/cggg/gcgg/index.htm',  # 工程类
        'goods': 'https://www.ccgp.gov.cn/cggg/hwggg/index.htm',     # 货物类
        'services': 'https://www.ccgp.gov.cn/cggg/fwgpg/index.htm',   # 服务类
        'central': 'https://www.ccgp.gov.cn/cggg/zygg/index.htm',      # 中央公告
        'winning': 'https://www.ccgp.gov.cn/cggg/zybg/index.htm',      # 中标公告
        # 工程类中标公告（最可能有机房项目）
        'engineering_winning': 'https://www.ccgp.gov.cn/cggg/gcgg/zbgg/index.htm',
    }

    target_url = category_urls.get(category)
    if not target_url:
        print(f"❌ 不支持的类别: {category}")
        return

    print(f"\n🔍 搜索条件:")
    print(f"  关键词: {keyword}")
    print(f"  品目: {category}")
    print(f"  时间: 最近 {days} 天")
    print(f"  来源: {target_url}")

    # 创建爬虫
    fetcher = PlaywrightFetcher()

    try:
        fetcher.start()

        # 计算目标日期
        target_date = datetime.now() - timedelta(days=days)
        date_str = target_date.strftime('%Y年%m月%d日')

        print(f"\n正在爬取列表页...")

        # 获取列表页
        html = fetcher.get_page(target_url)
        if not html:
            print("❌ 获取列表页失败")
            return

        # 解析列表页
        soup = BeautifulSoup(html, 'lxml')

        # 查找所有公告链接
        all_links = []
        for link in soup.find_all('a'):
            href = link.get('href', '')
            title = link.get_text(strip=True)

            # 过滤有效的公告链接
            if (
                href
                and 'htm' in href
                and len(title) > 10
                and title not in [item.get('title') for item in all_links]
            ):
                all_links.append({
                    'title': title,
                    'href': href,
                })

        print(f"✅ 找到 {len(all_links)} 个公告链接")

        # ===== 关键词过滤 =====
        print(f"\n正在过滤包含关键词 '{keyword}' 的公告...")

        filtered = []
        for item in all_links:
            if keyword in item['title']:
                # 构建完整URL
                href = item['href']

                # 使用urllib.parse.urljoin正确处理相对路径
                from urllib.parse import urljoin
                url = urljoin('https://www.ccgp.gov.cn/cggg/zygg/', href)

                filtered.append({
                    'title': item['title'],
                    'url': url,
                    'source': category,
                })

        print(f"✅ 过滤后剩余 {len(filtered)} 条公告")

        if not filtered:
            print(f"\n⚠️ 没有找到包含'{keyword}'的公告")
            return

        # 显示搜索结果
        print(f"\n搜索结果 (前10条):")
        print("-" * 70)

        for i, item in enumerate(filtered[:10], 1):
            print(f"{i}. {item['title'][:60]}")
            print(f"   {item['url']}")

        if len(filtered) > 10:
            print(f"\n... 还有 {len(filtered) - 10} 条结果")

        # ===== 爬取详情页 =====
        print(f"\n正在爬取详情页 (前{min(max_results, len(filtered))}条)...")

        parser = CCGPAnnouncementParser()
        detailed_results = []

        for i, item in enumerate(filtered[:max_results], 1):
            print(f"\n[{i}/{len(filtered[:max_results])}] {item['title'][:40]}")

            try:
                # 获取详情页
                detail_html = fetcher.get_page(item['url'])
                if not detail_html:
                    print("   ❌ 获取详情页失败")
                    continue

                # 解析详情页
                parsed = parser.parse(detail_html, item['url'])
                formatted = parser.format_for_storage(parsed)

                detailed_results.append(formatted)

                # 显示关键信息
                print(f"   ✅ 采购人: {formatted.get('buyer_name', '')[:30]}")
                print(f"   🏆 中标人: {formatted.get('supplier', '')[:30]}")
                print(f"   💰 金额: {formatted.get('bid_amount', '')[:30]}")

            except Exception as e:
                print(f"   ❌ 失败: {e}")

        # ===== 保存结果 =====
        print(f"\n保存结果...")

        import json
        output_file = Path("data/list_search_results.json")
        output_file.parent.mkdir(exist_ok=True)

        save_data = {
            'search_params': {
                'keyword': keyword,
                'category': category,
                'days': days,
                'search_time': datetime.now().isoformat(),
            },
            'summary': {
                'total_found': len(filtered),
                'detailed_crawled': len(detailed_results),
            },
            'filtered_results': filtered,
            'detailed_results': detailed_results,
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)

        print(f"✅ 结果已保存到: {output_file}")

        # ===== 统计信息 =====
        print(f"\n" + "=" * 70)
        print("统计信息:")
        print("=" * 70)
        print(f"找到相关公告: {len(filtered)} 条")
        print(f"成功解析详情: {len(detailed_results)} 条")

        # 统计中标人
        suppliers = {}
        for r in detailed_results:
            supplier = r.get('supplier', '')
            if supplier:
                suppliers[supplier] = suppliers.get(supplier, 0) + 1

        if suppliers:
            print(f"\n中标企业 (按项目数排序):")
            for supplier, count in sorted(suppliers.items(), key=lambda x: -x[1])[:10]:
                print(f"  - {supplier}: {count} 个项目")

    finally:
        fetcher.stop()

    print("\n" + "=" * 70)
    print("✅ 搜索完成！")
    print("=" * 70)


if __name__ == '__main__':
    # 搜索"机房"相关的公告
    # 尝试工程类中标公告（最可能有机房项目）
    print("尝试多个分类搜索...\n")

    # 先尝试工程类中标公告
    print("=" * 70)
    print("【尝试1】工程类中标公告")
    print("=" * 70)
    search_via_list_pages(
        keyword="机房",
        category="engineering_winning",  # 工程类中标公告
        days=90,               # 最近90天
        max_results=10,
    )
