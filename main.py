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
import random
import time
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
from config.settings import KEYWORD_SWITCH_DELAY_MIN, KEYWORD_SWITCH_DELAY_MAX


import sys
import os

# If frozen (PyInstaller), force Playwright to use bundled browsers
if getattr(sys, 'frozen', False):
    # Check if server.py already set the path (it should have)
    if "PLAYWRIGHT_BROWSERS_PATH" not in os.environ:
        # Fallback: set it ourselves
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        browsers_dir = os.path.join(exe_dir, "browsers")
        if os.path.isdir(browsers_dir):
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = browsers_dir

logger = logging.getLogger(__name__)


def _iter_business_cards(formatted: Dict) -> List[Dict]:
    """从解析后的公告中提取（公司, 联系人, 电话, 邮箱, role）"""
    cards: List[Dict] = []

    buyer_name = (formatted.get("buyer_name") or "").strip()
    buyer_contact = (formatted.get("buyer_contact") or "").strip()
    buyer_phone = (formatted.get("buyer_phone") or "").strip()
    buyer_email = (formatted.get("buyer_email") or "").strip()

    # 辅助函数：解析电话字符串为列表
    def parse_phones(p_str):
        if not p_str: return []
        return [p.strip() for p in str(p_str).split(',') if p.strip()]

    # 初始化电话列表
    buyer_phones = parse_phones(buyer_phone)
    if buyer_name and buyer_contact:
        cards.append({
            "company": buyer_name,
            "contact_name": buyer_contact,
            "phones": buyer_phones,
            "emails": [buyer_email] if buyer_email else [],
            "role": "buyer",
        })

    # ========== 代理机构联系人 ==========
    agent_name = (formatted.get("agent_name") or "").strip()
    agent_contacts_list = formatted.get("agent_contacts_list") or []
    agent_contact = (formatted.get("agent_contact") or "").strip()
    agent_phone = (formatted.get("agent_phone") or "").strip()
    agent_email = (formatted.get("agent_email") or "").strip()
    agent_phones = parse_phones(agent_phone)
    
    # 记录已添加的联系人（避免重复）
    added_agent_contacts = set()
    
    # 优先使用联系人列表（多人情况）
    if agent_name and agent_contacts_list:
        for contact in agent_contacts_list:
            name = (contact.get('name') or '').strip()
            phone = (contact.get('phone') or '').strip()
            email = (contact.get('email') or '').strip()
            p_list = parse_phones(phone)
            if name and name not in added_agent_contacts:
                cards.append({
                    "company": agent_name,
                    "contact_name": name,
                    "phones": p_list,
                    "emails": [email] if email else [],
                    "role": "agent",
                })
                added_agent_contacts.add(name)
    
    # 如果没有列表，使用单一联系人（向后兼容）
    if agent_name and agent_contact and agent_contact not in added_agent_contacts:
        cards.append({
            "company": agent_name,
            "contact_name": agent_contact,
            "phones": agent_phones,
            "emails": [agent_email] if agent_email else [],
            "role": "agent",
        })

    # ========== 项目联系人归属逻辑 ==========
    # 核心原则：项目联系人通常是代理机构的工作人员
    # 归属策略：
    # 1. 如果项目联系人电话与代理机构电话一致 -> 归属代理机构
    # 2. 如果项目联系人电话与采购人电话一致 -> 归属采购人
    # 3. 如果电话无法匹配但有代理机构名称 -> 默认归属代理机构
    # 4. 如果没有代理机构信息 -> 归属采购人
    
    project_phone = (formatted.get("project_phone") or "").strip()
    project_contacts = formatted.get("project_contacts") or []
    project_phones = parse_phones(project_phone)

    # 预处理电话号码（去除非数字字符用于比对）
    def clean_phone(p): 
        return "".join(filter(str.isdigit, p)) if p else ""
    
    def phones_match(p_list1, p_list2) -> bool:
        """检查两个电话列表是否有交集（支持模糊匹配）"""
        if not p_list1 or not p_list2:
            return False
        
        clean1 = [clean_phone(p) for p in p_list1 if p]
        clean2 = [clean_phone(p) for p in p_list2 if p]
        
        for p1 in clean1:
            if not p1: continue
            for p2 in clean2:
                if not p2: continue
                # 完全匹配或后8位匹配（座机可能有区号差异）
                if p1 == p2 or (len(p1) >= 8 and len(p2) >= 8 and p1[-8:] == p2[-8:]):
                    return True
        return False
    
    
    # 调试日志
    logger.debug(f"[名片归属] buyer_name={buyer_name}, buyer_phones={buyer_phones}")
    logger.debug(f"[名片归属] agent_name={agent_name}, agent_phones={agent_phones}")
    logger.debug(f"[名片归属] project_phones={project_phones}, project_contacts={project_contacts}")

    # 默认归属公司：优先代理机构
    default_project_company = agent_name if agent_name else buyer_name
    
    # 通过项目联系人电话预先判断归属
    global_attribution = None
    if project_phones:
        if agent_name and phones_match(project_phones, agent_phones):
            global_attribution = agent_name
            logger.debug(f"[名片归属] 项目电话与代理机构电话匹配 -> 归属 {agent_name}")
        elif buyer_name and phones_match(project_phones, buyer_phones):
            global_attribution = buyer_name
            logger.debug(f"[名片归属] 项目电话与采购人电话匹配 -> 归属 {buyer_name}")

    contacts_list = []
    
    # 处理结构化的项目联系人列表
    if isinstance(project_contacts, list) and project_contacts and isinstance(project_contacts[0], dict):
        for item in project_contacts:
            name = item.get('name', '').strip()
            if not name: 
                continue
            specific_phone = item.get('phone', '').strip()
            specific_phones = parse_phones(specific_phone)
            
            # 合并电话号码
            phones = list(set(specific_phones + project_phones))
            
            # 确定归属公司
            if global_attribution:
                # 如果已经通过项目电话确定了全局归属
                contact_company = global_attribution
            else:
                # 否则根据每个联系人的电话单独判断
                contact_company = default_project_company
                
                if agent_name and phones_match(phones, agent_phones):
                    contact_company = agent_name
                elif buyer_name and phones_match(phones, buyer_phones):
                    contact_company = buyer_name
            
            contacts_list.append({"name": name, "phones": phones, "company": contact_company})
            logger.debug(f"[名片归属] {name} -> {contact_company}")
            
    elif isinstance(project_contacts, list):
        # 字符串列表格式（旧格式兼容）
        contact_company = global_attribution if global_attribution else default_project_company
        
        # 再次尝试匹配（只要有一个项目电话匹配即可）
        if not global_attribution and project_phones:
            if agent_name and phones_match(project_phones, agent_phones):
                contact_company = agent_name
            elif buyer_name and phones_match(project_phones, buyer_phones):
                contact_company = buyer_name
                
        contacts_list = [
            {"name": n, "phones": project_phones, "company": contact_company} 
            for n in project_contacts if isinstance(n, str) and n.strip()
        ]

    for contact in contacts_list:
        if not contact['company']: 
            continue
        
        cards.append({
            "company": contact['company'],
            "contact_name": contact['name'],
            "phones": contact['phones'],
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
                # 即使没有结果，切换关键词前也要等待
                if kw != keywords[-1]:  # 不是最后一个关键词
                    delay = random.uniform(KEYWORD_SWITCH_DELAY_MIN / 2, KEYWORD_SWITCH_DELAY_MAX / 2)
                    print(f"[防封禁] 准备切换到下一个关键词，等待 {delay:.1f} 秒...")
                    time.sleep(delay)
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

            # 关键词切换延迟（不是最后一个关键词时）
            if kw != keywords[-1]:
                delay = random.uniform(KEYWORD_SWITCH_DELAY_MIN, KEYWORD_SWITCH_DELAY_MAX)
                print(f"\n[防封禁] 关键词 '{kw}' 处理完成，切换前等待 {delay:.1f} 秒...")
                time.sleep(delay)

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
    import sys
    print(f"[WORKER DEBUG] sys.argv: {sys.argv}")
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='中标信息整理工具')
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
        print(f"[WORKER DEBUG] Executing subcommand: {args.command}, args={args}")
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
    try:
        main()
    except Exception as e:
        logger.critical(f"程序发生严重错误: {e}", exc_info=True)
        print(f"\nCRITICAL ERROR: {e}")
        input("\n按回车键退出程序...")
    except KeyboardInterrupt:
        pass
