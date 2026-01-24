#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试：搜索机房相关公告
使用多个关键词和分类进行搜索
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from scraper.fetcher import PlaywrightFetcher
from scraper.ccgp_parser import CCGPAnnouncementParser
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json
from datetime import datetime


def search_with_keywords():
    """
    使用多个机房相关关键词搜索
    """

    # 机房相关关键词
    keywords = ["机房", "智能化", "弱电", "网络工程", "信息化", "数据中心"]

    # 多个分类（按优先级）
    categories = [
        {"name": "中央公告", "url": "https://www.ccgp.gov.cn/cggg/zygg/index.htm"},
        {"name": "中标公告", "url": "https://www.ccgp.gov.cn/cggg/zybg/index.htm"},
        {"name": "工程类", "url": "https://www.ccgp.gov.cn/cggg/gcgg/index.htm"},
    ]

    print("=" * 70)
    print("公共资源交易网 - 机房相关公告搜索")
    print("=" * 70)
    print(f"关键词: {', '.join(keywords)}")
    print(f"分类: {[c['name'] for c in categories]}")

    fetcher = PlaywrightFetcher()
    all_results = []

    try:
        fetcher.start()

        for cat in categories:
            print(f"\n{'=' * 70}")
            print(f"正在搜索: {cat['name']}")
            print(f"{'=' * 70}")

            # 爬取列表页
            html = fetcher.get_page(cat['url'])
            if not html:
                print(f"❌ 获取页面失败")
                continue

            soup = BeautifulSoup(html, 'lxml')

            # 查找所有公告链接
            found = []
            for link in soup.find_all('a'):
                href = link.get('href', '')
                title = link.get_text(strip=True)

                if href and 'htm' in href and len(title) > 10:
                    # 构建完整URL
                    if href.startswith('http'):
                        url = href
                    elif href.startswith('/'):
                        url = urljoin('https://www.ccgp.gov.cn/', href)
                    else:
                        continue

                    # 检查是否包含任何机房相关关键词
                    if any(kw in title for kw in keywords):
                        found.append({
                            'title': title,
                            'url': url,
                            'category': cat['name'],
                            'matched_keywords': [kw for kw in keywords if kw in title],
                        })

            print(f"✅ 找到 {len(found)} 条相关公告")

            all_results.extend(found)

            # 显示前几条
            for i, item in enumerate(found[:5], 1):
                matched = ', '.join(item['matched_keywords'])
                print(f"  {i}. {item['title'][:60]}")
                print(f"     匹配: {matched}")

    except Exception as e:
        print(f"❌ 搜索过程出错: {e}")
        import traceback
        traceback.print_exc()

    finally:
        fetcher.stop()

    # 统计
    print(f"\n{'=' * 70}")
    print(f"搜索完成！")
    print(f"{'=' * 70}")
    print(f"总共找到: {len(all_results)} 条相关公告")

    # 按关键词分类统计
    keyword_stats = {}
    for result in all_results:
        for kw in result.get('matched_keywords', []):
            keyword_stats[kw] = keyword_stats.get(kw, 0) + 1

    print(f"\n关键词分布:")
    for kw, count in sorted(keyword_stats.items(), key=lambda x: -x[1]):
        print(f"  {kw}: {count} 条")

    # 爬取详情页（前5条）
    if all_results:
        print(f"\n{'=' * 70}")
        print(f"爬取详情页 (前5条)...")
        print(f"{'=' * 70}")

        parser = CCGPAnnouncementParser()
        detailed = []

        for i, result in enumerate(all_results[:5], 1):
            url = result['url']
            print(f"\n[{i}/5] {result['title'][:50]}")
            print(f"     匹配: {', '.join(result['matched_keywords'])}")
            print(f"     URL: {url}")

            try:
                import time
                time.sleep(2)

                html = fetcher.get_page(url)
                if not html:
                    print("     ❌ 获取失败")
                    continue

                parsed = parser.parse(html, url)
                formatted = parser.format_for_storage(parsed)
                detailed.append(formatted)

                print(f"     ✅ 项目: {formatted.get('project_name', '')[:40]}")
                print(f"     🏆 中标人: {formatted.get('supplier', '')[:30]}")

            except Exception as e:
                print(f"     ❌ 失败: {e}")

        # 保存结果
        output_file = Path("data/jifang_related_results.json")
        output_file.parent.mkdir(exist_ok=True)

        save_data = {
            'search_time': datetime.now().isoformat(),
            'keywords': keywords,
            'total_found': len(all_results),
            'keyword_stats': keyword_stats,
            'results': all_results,
            'detailed_results': detailed,
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=2)

        print(f"\n✅ 结果已保存到: {output_file}")

        if detailed:
            print(f"\n成功解析 {len(detailed)} 条详情")

            # 找出真正包含"机房"的项目
            jifang_projects = [
                r for r in detailed
                if '机房' in r.get('project_name', '') or '机房' in r.get('title', '')
            ]

            if jifang_projects:
                print(f"\n⭐ 包含'机房'的项目 ({len(jifang_projects)}条):")
                for r in jifang_projects:
                    print(f"  - {r.get('project_name', '')[:60]}")
                    print(f"    中标人: {r.get('supplier', '')}")
    else:
        print("\n⚠️ 未找到任何相关公告")


if __name__ == '__main__':
    search_with_keywords()
