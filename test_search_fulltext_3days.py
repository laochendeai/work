#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试：搜全文 3天内 - 搜索"机房"
专门测试政府采购网搜索平台的"搜全文"功能
"""
import sys
from pathlib import Path
import json
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from scraper.fetcher import PlaywrightFetcher
from scraper.ccgp_parser import CCGPAnnouncementParser


def test_search_fulltext_3days():
    """
    测试搜全文功能 - 3天内 - 关键词"机房"

    尝试多种方法来触发搜索：
    1. 直接点击"搜全文"按钮
    2. 构造搜索API请求
    3. 模拟完整表单填写流程
    """

    print("=" * 70)
    print("政府采购网搜索平台 - 搜全文测试")
    print("=" * 70)

    print("\n测试参数:")
    print("  关键词: 机房")
    print("  搜索方式: 搜全文")
    print("  时间范围: 3天内")
    print("  品目: 工程类")

    keyword = "机房"

    # 创建爬虫
    fetcher = PlaywrightFetcher()

    try:
        fetcher.start()
        page = fetcher.page

        # ========== 方法1: 访问搜索平台并操作 ==========
        print(f"\n{'=' * 70}")
        print("【方法1】搜索平台操作测试")
        print(f"{'=' * 70}")

        # 先访问主页
        print("\n步骤1: 访问政府采购网主页...")
        try:
            page.goto("https://www.ccgp.gov.cn/",
                          wait_until="domcontentloaded",
                          timeout=30000)
            print("✅ 主页访问成功")
            import time
            time.sleep(2)
        except Exception as e:
            print(f"❌ 主页访问失败: {e}")
            return

        # 访问搜索平台
        print("\n步骤2: 访问搜索平台...")
        search_url = "https://search.ccgp.gov.cn/bxsearch"
        try:
            page.goto(search_url,
                          wait_until="domcontentloaded",
                          timeout=30000)
            print("✅ 搜索平台加载成功")
            time.sleep(3)
        except Exception as e:
            print(f"❌ 搜索平台访问失败: {e}")
            return

        # 检查是否被封禁
        print("\n步骤3: 检查页面状态...")
        try:
            page_text = page.evaluate("() => document.body.innerText")
            if "访问过于频繁" in page_text or "稍后再试" in page_text:
                print("❌ ⚠️ 检测到反爬限制")
                print("\n建议:")
                print("  1. 等待10-30分钟后再试")
                print("  2. 使用列表页爬取方式")
                return
            else:
                print("✅ 页面正常")
        except:
            pass

        # 尝试查找和点击搜索相关元素
        print("\n步骤4: 查找搜索元素...")

        # 查找搜索输入框
        input_found = False
        input_selectors = [
            '#kw',
            'input[name="kw"]',
            'input[placeholder*="请输入"]',
            'input[type="text"]',
            '#keyword',
            'input[name="keyword"]',
            '.search-input',
        ]

        search_input = None
        for selector in input_selectors:
            try:
                elem = page.query_selector(selector)
                if elem:
                    search_input = elem
                    print(f"  ✅ 找到输入框: {selector}")
                    input_found = True
                    break
            except:
                continue

        if not search_input:
            print("  ❌ 未找到搜索输入框")

        # 查找"搜全文"按钮
        button_found = False
        button_selectors = [
            '#doSearch2',
            'text="搜全文"',
            'button:has-text("搜全文")',
            '[onclick*="fulltext"]',
            '.btn-fulltext',
        ]

        fulltext_button = None
        for selector in button_selectors:
            try:
                elem = page.query_selector(selector)
                if elem:
                    fulltext_button = elem
                    print(f"  ✅ 找到搜全文按钮: {selector}")
                    button_found = True
                    break
            except:
                continue

        if not button_found:
            print("  ❌ 未找到搜全文按钮")

        # 查找"3天内"选项
        time_3days_found = False
        time_selectors = [
            'text="近3日"',
            'text="3天内"',
            '[value="3d"]',
        ]

        time_button = None
        for selector in time_selectors:
            try:
                elem = page.query_selector(selector)
                if elem:
                    time_button = elem
                    print(f"  ✅ 找到时间选项: {selector}")
                    time_3days_found = True
                    break
            except:
                continue

        if not time_3days_found:
            print("  ⚠️ 未找到'近3日'选项")

        # 如果找到了必要元素，尝试操作
        if input_found and button_found:
            print("\n步骤5: 执行搜索操作...")

            # 重新获取输入框并输入关键词
            try:
                search_input = page.query_selector('#kw') or page.query_selector('input[name="kw"]')
                if search_input:
                    search_input.fill(keyword)
                    print(f"  ✅ 已输入关键词: {keyword}")
                    time.sleep(1)
            except Exception as e:
                print(f"  ❌ 输入关键词失败: {e}")

            # 重新获取并点击时间选项
            if time_3days_found:
                try:
                    time_button = page.query_selector('text="近3日"')
                    if time_button:
                        time_button.click()
                        print(f"  ✅ 已选择: 近3日")
                        time.sleep(1)
                except Exception as e:
                    print(f"  ⚠️ 选择时间失败: {e}")

            # 重新获取并点击搜全文按钮
            try:
                fulltext_button = page.query_selector('#doSearch2')
                if fulltext_button:
                    fulltext_button.click()
                    print(f"  ✅ 已点击: 搜全文")
                    time.sleep(5)  # 等待搜索结果
            except Exception as e:
                print(f"  ❌ 点击搜全文失败: {e}")

            # 尝试获取搜索结果
            print("\n步骤6: 获取搜索结果...")

            # 等待结果加载
            time.sleep(3)

            # 先打印页面内容用于调试
            print("\n[调试] 检查页面内容...")
            try:
                page_text = page.evaluate("() => document.body.innerText")
                print(f"页面文本长度: {len(page_text)} 字符")

                # 检查是否有特定关键词
                if "没有找到" in page_text or "共0条" in page_text or "暂无数据" in page_text:
                    print("  ⚠️ 搜索结果为空（页面显示无结果）")
                elif "条" in page_text and "找到" in page_text:
                    # 尝试提取结果数量
                    import re
                    match = re.search(r'共(\d+)条|找到.*?(\d+)条', page_text)
                    if match:
                        count = match.group(1) or match.group(2)
                        print(f"  📊 搜索结果数量: {count} 条")

                # 显示前500字符
                if len(page_text) > 0:
                    print(f"\n页面内容预览（前500字符）:")
                    print("-" * 70)
                    print(page_text[:500])
                    print("-" * 70)
            except Exception as e:
                print(f"  ❌ 获取页面内容失败: {e}")

            # 获取页面内容
            try:
                html = page.content()
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html, 'lxml')

                # 尝试多种结果选择器
                result_selectors = [
                    'li',  # 先尝试所有li元素
                    'a',   # 或者直接找所有链接
                ]

                # 直接用BeautifulSoup解析，更可靠
                results = []
                seen_urls = set()  # 去重

                # 查找所有链接
                for link in soup.find_all('a'):
                    try:
                        href = link.get('href', '')
                        title = link.get_text(strip=True)

                        # 过滤有效的公告链接
                        if (
                            href
                            and 'htm' in href
                            and len(title) > 10
                            and href not in seen_urls
                            # 排除导航链接
                            and not any(x in href for x in ['index.htm', 'javascript', '#'])
                            # 排除导航类标题
                            and not any(x in title for x in ['首页', '政采法规', '购买服务', '信息公告', '所有类型', '所有类别', '所有品目', '今日', '近3日', '近1周'])
                        ):
                            # 构建完整URL
                            if not href.startswith('http'):
                                from urllib.parse import urljoin
                                url = urljoin('http://www.ccgp.gov.cn/', href)
                            else:
                                url = href

                            results.append({
                                'title': title,
                                'url': url,
                                'source': '搜索平台',
                            })
                            seen_urls.add(href)

                    except Exception:
                        continue

                print(f"  ✅ 提取到 {len(results)} 个结果")

                if results:
                    print(f"\n搜索结果 (前5条):")
                    print("-" * 70)
                    for i, r in enumerate(results[:5], 1):
                        print(f"{i}. {r['title'][:70]}")

                    # 爬取详情页（前2条）
                    print(f"\n步骤7: 爬取详情页...")
                    parser = CCGPAnnouncementParser()
                    detailed = []

                    for r in results[:2]:
                        url = r['url']
                        if not url.startswith('http'):
                            from urllib.parse import urljoin
                            url = urljoin('http://www.ccgp.gov.cn/', url)

                        print(f"\n  爬取: {r['title'][:40]}")

                        try:
                            time.sleep(3)
                            detail_html = fetcher.get_page(url)
                            if detail_html:
                                parsed = parser.parse(detail_html, url)
                                formatted = parser.format_for_storage(parsed)
                                detailed.append(formatted)

                                print(f"    ✅ 项目: {formatted.get('project_name', '')[:40]}")

                                # 检查是否包含"机房"
                                has_jifang = (
                                    '机房' in formatted.get('project_name', '') or
                                    '机房' in formatted.get('title', '')
                                )

                                if has_jifang:
                                    print(f"    ⭐ 包含'机房'!")
                                else:
                                    print(f"    (未包含'机房'关键词)")
                        except Exception as e:
                            print(f"    ❌ 失败: {e}")

                    # 保存结果
                    output_file = Path("data/search_fulltext_3days_results.json")
                    output_file.parent.mkdir(exist_ok=True)

                    save_data = {
                        'search_params': {
                            'keyword': keyword,
                            'method': 'fulltext',
                            'time_range': '3days',
                            'search_time': datetime.now().isoformat(),
                        },
                        'results_count': len(results),
                        'results': results[:5],
                        'detailed_results': detailed,
                    }

                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(save_data, f, ensure_ascii=False, indent=2)

                    print(f"\n✅ 结果已保存到: {output_file}")

                    if detailed:
                        print(f"\n统计:")
                        print(f"  成功解析: {len(detailed)} 条")
                        jifang_count = sum(1 for r in detailed if '机房' in r.get('title', '') or '机房' in r.get('project_name', ''))
                        print(f"  包含'机房': {jifang_count} 条")

                else:
                    print("  ⚠️ 未找到搜索结果元素")

                    # 显示页面内容用于调试
                    try:
                        page_text = page.evaluate("() => document.body.innerText")
                        if len(page_text) < 5000:
                            print("\n  页面内容:")
                            print("  " + page_text[:500])
                    except:
                        pass

            except Exception as e:
                print(f"  ❌ 获取搜索结果失败: {e}")

        else:
            print("\n❌ 缺少必要的搜索元素，无法继续")
            print("\n💡 建议:")
            print("  1. 检查网站是否更新了结构")
            print("  2. 尝试使用列表页爬取方式")
            print("  3. 检查是否需要登录")

    finally:
        fetcher.stop()

    print("\n" + "=" * 70)
    print("✅ 测试完成")
    print("=" * 70)


if __name__ == '__main__':
    test_search_fulltext_3days()
