#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中标信息整理 - 主入口

使用方法:
    python main.py                    # 爬取所有数据源
    python main.py --export           # 爬取并导出数据
    python main.py --stats            # 显示统计信息
    python main.py bxsearch --kw 智能  # bxsearch 搜索 + 名片系统
    python main.py cards --company "某单位"  # 查询名片
"""
import argparse
import logging
from datetime import datetime
from typing import Dict, List

from tqdm import tqdm

from utils.helpers import setup_logging, load_sources_config
from utils.keyword_list import load_keywords
from scraper import BaseScraper
from scraper.ccgp_bxsearcher import BxSearchParams, CCGPBxSearcher
from scraper.ccgp_parser import CCGPAnnouncementParser
from scraper.fetcher import PlaywrightFetcher
from extractor import ContactExtractor, DataCleaner
from storage import Database, DataExporter

logger = logging.getLogger(__name__)


def _iter_business_cards(formatted: Dict) -> List[Dict]:
    """从解析后的公告中提取（公司, 联系人, 电话, 邮箱, role）"""
    cards: List[Dict] = []

    buyer_name = (formatted.get("buyer_name") or "").strip()
    buyer_contact = (formatted.get("buyer_contact") or "").strip()
    buyer_phone = (formatted.get("buyer_phone") or "").strip()
    if buyer_name and buyer_contact:
        cards.append({
            "company": buyer_name,
            "contact_name": buyer_contact,
            "phones": [buyer_phone] if buyer_phone else [],
            "emails": [],
            "role": "buyer",
        })

    agent_name = (formatted.get("agent_name") or "").strip()
    agent_contact = (formatted.get("agent_contact") or "").strip()
    agent_phone = (formatted.get("agent_phone") or "").strip()
    if agent_name and agent_contact:
        cards.append({
            "company": agent_name,
            "contact_name": agent_contact,
            "phones": [agent_phone] if agent_phone else [],
            "emails": [],
            "role": "agent",
        })

    # 项目联系人：优先归属采购人，其次代理机构
    project_company = buyer_name or agent_name
    project_phone = (formatted.get("project_phone") or "").strip()
    project_contacts = formatted.get("project_contacts") or []
    if project_company and isinstance(project_contacts, list):
        for name in project_contacts:
            name = (name or "").strip()
            if not name:
                continue
            cards.append({
                "company": project_company,
                "contact_name": name,
                "phones": [project_phone] if project_phone else [],
                "emails": [],
                "role": "project",
            })

    return cards


def run_bxsearch(args):
    """bxsearch 搜索 + 详情解析 + 名片聚合"""
    keywords = load_keywords(args.kw, args.kw_file)
    if not keywords:
        print("参数错误: 需要提供 --kw 或 --kw-file")
        return

    print("=" * 70)
    print("bxsearch 搜索参数")
    print("=" * 70)
    print(f"关键词: {', '.join(keywords)}")
    print(f"搜类型: {args.search_type}")
    print(f"品目(pinMu): {args.pinmu}")
    print(f"类别(bidSort): {args.category}")
    print(f"类型(bidType): {args.bid_type}")
    print(f"时间(timeType): {args.time}")
    if args.time == "custom":
        print(f"  起止: {args.start_date} ~ {args.end_date}")
    print(f"最大页数: {args.max_pages}")
    print("=" * 70)

    db = Database()
    cleaner = DataCleaner()
    parser = CCGPAnnouncementParser()

    fetcher = PlaywrightFetcher()
    try:
        fetcher.start()
        searcher = CCGPBxSearcher(fetcher.page)

        total_results = 0
        new_announcements = 0
        card_writes = 0
        skipped = 0

        for kw in keywords:
            search_params = BxSearchParams(
                kw=kw,
                search_type=args.search_type,
                bid_sort=args.category,
                pin_mu=args.pinmu,
                bid_type=args.bid_type,
                time_type=args.time,
                start_date=args.start_date or "",
                end_date=args.end_date or "",
            )

            print("\n" + "=" * 70)
            print(f"开始搜索关键词: {kw}")
            print("=" * 70)

            try:
                results = searcher.search(search_params, max_pages=args.max_pages)
            except ValueError as e:
                print(f"参数错误: {e}")
                return

            total_results += len(results)
            print(f"\n搜索结果: {len(results)} 条")
            if not results:
                continue

            # 展示列表结果
            for i, r in enumerate(results, 1):
                print(f"\n[{i}] {r.get('title', '')}")
                print(f"  时间: {r.get('publish_date', '')}")
                print(f"  采购人: {r.get('buyer_name', '')}")
                print(f"  代理机构: {r.get('agent_name', '')}")
                print(f"  URL: {r.get('url', '')}")

            # 逐条抓取详情页（URL 去重：已入库的公告不再解析）
            print("\n" + "-" * 70)
            print("解析详情页并更新名片（已解析URL将跳过）")
            print("-" * 70)

            for r in results:
                url = (r.get("url") or "").strip()
                if not url:
                    continue

                existing_id = db.get_announcement_id_by_url(url)
                if existing_id:
                    skipped += 1
                    continue

                detail_html = fetcher.get_page(url, wait_for="networkidle")
                if not detail_html:
                    logger.warning(f"详情页获取失败，跳过: {url}")
                    continue

                parsed = parser.parse(detail_html, url)
                formatted = parser.format_for_storage(parsed)

                announcement = {
                    "title": (r.get("title") or formatted.get("title") or "").strip(),
                    "url": url,
                    "content": formatted.get("content", ""),
                    "publish_date": (r.get("publish_date") or formatted.get("publish_date") or "").strip(),
                    "source": "ccgp-bxsearch",
                    "scraped_at": datetime.now().isoformat(),
                }

                # 清洗
                announcement = cleaner.clean_announcement(announcement)

                announcement_id = db.insert_announcement(announcement)
                if not announcement_id:
                    announcement_id = db.get_announcement_id_by_url(url)
                if not announcement_id:
                    continue

                new_announcements += 1

                # 名片聚合写入
                for card in _iter_business_cards(formatted):
                    cleaned = cleaner.clean_contacts({
                        "phones": card.get("phones") or [],
                        "emails": card.get("emails") or [],
                        "company": card.get("company") or "",
                        "contacts": [card.get("contact_name") or ""],
                    })
                    company = cleaned.get("company") or ""
                    names = cleaned.get("contacts") or []
                    contact_name = names[0] if names else ""
                    phones = cleaned.get("phones") or []
                    emails = cleaned.get("emails") or []

                    card_id = db.upsert_business_card(company, contact_name, phones=phones, emails=emails)
                    if card_id:
                        db.add_business_card_mention(card_id, announcement_id, role=card.get("role") or "")
                        card_writes += 1

        print("\n" + "=" * 70)
        print("本次完成")
        print("=" * 70)
        print(f"总搜索结果(列表条目累计): {total_results}")
        print(f"新增公告: {new_announcements}")
        print(f"跳过已解析URL: {skipped}")
        print(f"名片写入次数(含更新): {card_writes}")
        print("\n查询名片示例：")
        print(f"  python main.py cards --company \"单位名称\"")

    finally:
        fetcher.stop()
        db.close()


def show_business_cards(args):
    """查询并展示名片"""
    db = Database()
    try:
        cards = db.get_business_cards(args.company, like=args.like, limit=args.limit)
        print("=" * 70)
        print("名片查询结果")
        print("=" * 70)
        print(f"公司: {args.company} ({'模糊匹配' if args.like else '精确匹配'})")
        print(f"数量: {len(cards)}")

        for i, c in enumerate(cards, 1):
            phones = ", ".join(c.get("phones") or [])
            emails = ", ".join(c.get("emails") or [])
            print(f"\n[{i}] {c.get('contact_name', '')}")
            if phones:
                print(f"  电话: {phones}")
            if emails:
                print(f"  邮箱: {emails}")
            print(f"  出现项目数: {c.get('projects_count', 0)}")
    finally:
        db.close()


def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='政府采购爬虫')
    subparsers = parser.add_subparsers(dest="command")

    # bxsearch 子命令
    bx = subparsers.add_parser("bxsearch", help="使用 search.ccgp.gov.cn/bxsearch 搜索并建立名片")
    bx.add_argument("--kw", nargs="+", help="一个或多个搜索关键词（也支持逗号分隔）")
    bx.add_argument("--kw-file", help="关键词文件路径（每行一个关键词，支持逗号分隔；# 开头为注释）")
    bx.add_argument("--search-type", choices=["title", "fulltext"], default="fulltext", help="搜标题/搜全文")
    bx.add_argument("--pinmu", choices=["all", "goods", "engineering", "services"], default="all", help="品目(pinMu)")
    bx.add_argument("--category", choices=["all", "central", "local"], default="all", help="类别(bidSort)")
    bx.add_argument(
        "--bid-type",
        default="all",
        help="类型(bidType)：可用 0-12 或中文名称（如 公开招标/中标公告/竞争性磋商 等）",
    )
    bx.add_argument(
        "--time",
        choices=["today", "3days", "1week", "1month", "3months", "halfyear", "custom"],
        default="1week",
        help="时间(timeType)：custom 需配合 --start-date/--end-date",
    )
    bx.add_argument("--start-date", help="自定义开始日期 YYYY-MM-DD（仅 time=custom）")
    bx.add_argument("--end-date", help="自定义结束日期 YYYY-MM-DD（仅 time=custom）")
    bx.add_argument("--max-pages", type=int, default=3, help="最多抓取页数")
    bx.set_defaults(func=run_bxsearch)

    # 名片查询子命令
    cards = subparsers.add_parser("cards", help="查询名片系统")
    cards.add_argument("--company", required=True, help="公司/单位名称")
    cards.add_argument("--like", action="store_true", help="模糊匹配（LIKE）")
    cards.add_argument("--limit", type=int, default=200, help="返回数量上限")
    cards.set_defaults(func=show_business_cards)

    # 兼容原有参数（无子命令时使用）
    parser.add_argument('--export', action='store_true', help='爬取后导出数据')
    parser.add_argument('--stats', action='store_true', help='显示统计信息')
    parser.add_argument('--sources', type=str, help='指定数据源配置文件路径')
    args = parser.parse_args()

    # 设置日志
    setup_logging()

    # 子命令
    if getattr(args, "command", None):
        args.func(args)
        return

    # 如果只是显示统计
    if args.stats:
        show_stats()
        return

    # 执行爬取
    run_scraping(export_data=args.export, sources_config=args.sources)


def run_scraping(export_data: bool = False, sources_config: str = None):
    """
    执行爬取流程

    Args:
        export_data: 是否导出数据
        sources_config: 数据源配置文件路径
    """
    # 加载数据源配置
    sources = load_sources_config(sources_config)

    if not sources:
        logger.warning("没有启用的数据源，请检查配置文件")
        return

    logger.info(f"开始爬取 {len(sources)} 个数据源")

    # 初始化组件
    db = Database()
    cleaner = DataCleaner()
    contact_extractor = ContactExtractor()

    # 统计信息
    total_announcements = 0
    total_contacts = 0

    # 逐个处理数据源
    for source in sources:
        logger.info(f"正在处理: {source['name']}")

        try:
            # 创建爬虫实例
            scraper = BaseScraper(source)

            # 爬取公告
            announcements = list(scraper.scrape())

            logger.info(f"获取到 {len(announcements)} 个公告")

            # 处理每个公告
            for announcement in tqdm(announcements, desc=f"处理 {source['name'][:10]}"):
                # 清洗数据
                cleaned = cleaner.clean_announcement(announcement)

                # 检查重复
                if cleaner.is_duplicate(cleaned):
                    logger.debug(f"跳过重复公告: {cleaned['title'][:30]}")
                    continue

                # 存储公告
                announcement_id = db.insert_announcement(cleaned)
                if announcement_id:
                    total_announcements += 1

                    # 提取并存储联系人
                    content = cleaned.get('content', '')
                    contacts = contact_extractor.extract(content)
                    cleaned_contacts = cleaner.clean_contacts(contacts)

                    contact_count = db.insert_contacts(announcement_id, cleaned_contacts)
                    total_contacts += contact_count

        except Exception as e:
            logger.error(f"处理数据源失败 {source['name']}: {e}")
            continue

    # 关闭数据库
    db.close()

    # 显示结果
    logger.info("=" * 50)
    logger.info("爬取完成!")
    logger.info(f"新增公告: {total_announcements} 条")
    logger.info(f"新增联系人: {total_contacts} 条")
    logger.info("=" * 50)

    # 导出数据
    if export_data:
        export_all_data(db)


def show_stats():
    """显示统计信息"""
    db = Database()
    stats = db.get_stats()

    print("\n" + "=" * 50)
    print("数据统计")
    print("=" * 50)
    print(f"公告总数: {stats.get('total_announcements', 0)}")
    print(f"联系人总数: {stats.get('total_contacts', 0)}")

    print("\n按数据源统计:")
    for source, count in stats.get('by_source', {}).items():
        print(f"  - {source}: {count}")

    print("\n热门公司 (前20):")
    for company, count in list(stats.get('top_companies', {}).items())[:20]:
        print(f"  - {company}: {count}")

    print("=" * 50 + "\n")

    db.close()


def export_all_data(db: Database):
    """
    导出所有数据

    Args:
        db: 数据库实例
    """
    exporter = DataExporter()

    logger.info("正在导出数据...")

    results = exporter.export_all(db, format='excel')

    logger.info("数据导出完成:")
    for name, path in results.items():
        if path:
            logger.info(f"  - {name}: {path}")


if __name__ == '__main__':
    main()
