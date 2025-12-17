#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能设计营销系统 - 系统编排

从仓库根目录的 main.py 抽离启动/编排逻辑，降低入口文件复杂度。
"""

import asyncio
import json
import logging
import os
import random
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Coroutine, Optional

from config.settings import settings
from core import playwright_fetcher
from core.emailer import emailer
from core.exceptions import PlaywrightFallback
from core.extractor import extractor
from core.filter import body_density, detail_keyword_hit, title_hit
from core.metrics import record_fallback, record_request
from core.queue import pop_url, push_start_urls, requeue_url
from core.retry import mark_failed, mark_irrelevant
from core.scraper import scraper


def _looks_like_procurement_title(title: str) -> bool:
    text = (title or "").strip()
    if not text:
        return False
    tokens = (
        "招标",
        "采购",
        "公告",
        "公示",
        "中标",
        "成交",
        "结果",
        "项目",
        "投标",
        "比选",
        "询价",
        "磋商",
        "谈判",
        "竞价",
        "入围",
        "遴选",
        "开标",
        "资格预审",
        "询比",
        "招采",
    )
    if any(token in text for token in tokens):
        return True
    lower = text.lower()
    return any(token in lower for token in ("tender", "bidding", "bid", "procurement", "purchase"))


class MarketingSystem:
    """智能设计营销系统主类"""

    def __init__(self):
        self.setup_logging()
        self.logger = logging.getLogger(__name__)
        # 暂时禁用metrics服务器以避免端口冲突
        # start_metrics_server()

    def setup_logging(self):
        """设置日志"""
        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(logs_dir / "marketing.log", encoding="utf-8"),
                logging.StreamHandler(),
            ],
        )

    def run_scraper(self):
        """运行爬虫"""
        global scraper
        print("🕷️  启动数据爬虫...")

        export_run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        batch_size = int(settings.get("scraper.performance.batch_size", 50) or 50)
        batch_size = max(5, min(batch_size, 200))
        flush_seconds = int(settings.get("scraper.performance.batch_flush_seconds", 30) or 30)
        flush_seconds = max(0, min(flush_seconds, 600))

        # 测试网络连接（可选）
        if not scraper.test_connection():
            print("⚠️  网络连接测试失败，但仍尝试爬取")
        else:
            print("✅ 网络连接正常")

        print("\n✅ 数据源: user_config.json + config/auto_sources.yaml（若存在）")
        flush_label = f", flush={flush_seconds}s" if flush_seconds else ""
        print(f"📦 批处理大小: {batch_size}{flush_label}（边爬边抓详情/抽取/导出）")

        total_items = 0
        total_extracted = 0
        batch: list[dict] = []
        last_flush = time.monotonic()

        # 详情抓取（队列）使用 asyncio；用 Runner 复用同一 event loop，避免多次 asyncio.run(...)
        # 在同一进程里创建多个 event loop 时，redis asyncio client 的内部 Lock 会触发
        # “is bound to a different event loop”。
        try:
            runner_cm = asyncio.Runner()  # py>=3.11
        except AttributeError:  # pragma: no cover
            runner_cm = None

        if runner_cm is None:  # pragma: no cover
            run_async = asyncio.run
            for item in scraper.scrape_all_sources():
                batch.append(item)
                total_items += 1
                now = time.monotonic()
                should_flush = len(batch) >= batch_size or (flush_seconds and now - last_flush >= flush_seconds)
                if should_flush:
                    total_extracted += self._process_scraped_batch(batch, export_run_id, run_async=run_async)
                    batch = []
                    last_flush = time.monotonic()

            if batch:
                total_extracted += self._process_scraped_batch(batch, export_run_id, run_async=run_async)

            total_extracted += self._backfill_pending_details(export_run_id, run_async=run_async)
        else:
            with runner_cm as runner:
                run_async = runner.run
                for item in scraper.scrape_all_sources():
                    batch.append(item)
                    total_items += 1
                    now = time.monotonic()
                    should_flush = len(batch) >= batch_size or (flush_seconds and now - last_flush >= flush_seconds)
                    if should_flush:
                        total_extracted += self._process_scraped_batch(batch, export_run_id, run_async=run_async)
                        batch = []
                        last_flush = time.monotonic()

                if batch:
                    total_extracted += self._process_scraped_batch(batch, export_run_id, run_async=run_async)

                total_extracted += self._backfill_pending_details(export_run_id, run_async=run_async)

        print(f"✅ 爬取完成，累计 {total_items} 条；已抽取 {total_extracted} 条（raw层）")

        stats = scraper.get_scraping_stats()
        print(
            f"📦 当前待提取详情: {stats.get('pending_detail_extraction', 0)} 条, 总计 {stats.get('scraped_data_total', 0)} 条"
        )
        last_cleanup = stats.get("retention", {}).get("last_cleanup", {})
        if last_cleanup.get("expired") or last_cleanup.get("overflow"):
            print(f"🧹 本轮清理: 过期 {last_cleanup.get('expired', 0)} 条, 超限 {last_cleanup.get('overflow', 0)} 条")

        return total_items

    def _load_pending_detail_items(self, limit: int) -> list[dict]:
        if limit <= 0:
            return []
        db_path = settings.get("storage.database_path", "data/marketing.db")
        if not Path(db_path).exists():
            return []
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, title, source, link
                FROM scraped_data
                WHERE processed = 0
                  AND (detail_content IS NULL OR detail_content = '')
                  AND link IS NOT NULL AND link != ''
                ORDER BY datetime(scraped_at) DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cursor.fetchall()
            conn.close()
        except Exception:
            return []

        items: list[dict] = []
        for row in rows:
            items.append(
                {
                    "id": row[0],
                    "title": row[1] or "",
                    "source": row[2] or "",
                    "link": row[3] or "",
                }
            )
        return items

    def _backfill_pending_details(
        self,
        export_run_id: str,
        *,
        run_async: Optional[Callable[[Coroutine[Any, Any, Any]], Any]] = None,
    ) -> int:
        try:
            limit = int(settings.get("scraper.performance.pending_detail_backfill_limit", 0) or 0)
        except (TypeError, ValueError):
            limit = 0
        if limit <= 0:
            return 0

        pending = self._load_pending_detail_items(limit)
        if not pending:
            return 0

        print(f"🔄 回填历史待抓详情: {len(pending)} 条（limit={limit}）")
        return self._process_scraped_batch(pending, export_run_id, run_async=run_async)

    def _process_scraped_batch(
        self,
        scraped_items: list[dict],
        export_run_id: str,
        run_async: Optional[Callable[[Coroutine[Any, Any, Any]], Any]] = None,
    ) -> int:
        """抓取详情 -> 抽取 -> 导出（增量批处理）。"""
        if not scraped_items:
            return 0

        try:
            if run_async is None:
                asyncio.run(self._process_queue(scraped_items))
            else:
                run_async(self._process_queue(scraped_items))
        except Exception as exc:
            self.logger.error("详情队列处理失败: %s", exc)
            return 0

        detailed_items = self._reload_details(scraped_items)
        if not detailed_items:
            return 0

        relevant_items = [
            item
            for item in detailed_items
            if item.get("detail_content")
            and (title_hit(item.get("title", "") or "") or detail_keyword_hit(item.get("detail_content", "") or ""))
        ]

        contacts = []
        if relevant_items:
            db_path = str(getattr(scraper, "db_path", "") or settings.get("storage.database_path", "data/marketing.db"))
            contacts = extractor.process_and_save(
                relevant_items,
                db_path=db_path,
                export_mode="append_jsonl",
                export_run_id=export_run_id,
            )

        try:
            processed_ids = [item["id"] for item in detailed_items if item.get("id")]
            if processed_ids:
                scraper.mark_items_processed(processed_ids)
        except Exception as exc:
            self.logger.error("更新 processed 状态失败: %s", exc)

        return len(contacts or [])

    async def _process_queue(self, scraped_items):
        """把待抓取详情推入队列并并发处理"""
        payloads = []
        for item in scraped_items:
            link = item.get("link")
            if not link:
                continue
            payload = {
                "link": link,
                # 详情抓取前的快速过滤依赖标题关键词；不带 title 会导致全部被判 irrelevant
                "title": item.get("title", ""),
                "render_mode": item.get("render_mode", ""),
                "wait_selector": item.get("wait_selector"),
                "source": item.get("source", ""),
            }
            actions = item.get("actions")
            if actions:
                payload["actions"] = actions
            payloads.append(json.dumps(payload, ensure_ascii=False))

        try:
            await push_start_urls(payloads)
            await self._run_workers(persistent=False)
        except Exception as exc:
            # Redis 不可用时（本地跑/容器外跑常见），直接在当前进程并发处理，避免“详情队列积压/全失败”
            self.logger.warning("Redis 队列不可用，改为本地并发处理: %s", exc)
            items = [json.loads(p) for p in payloads]
            await self._process_queue_locally(items)

    async def _process_queue_locally(self, items: list[dict]) -> None:
        if not items:
            return
        worker_count = int(os.getenv("WORKERS", "4"))
        semaphore = asyncio.Semaphore(max(worker_count, 1))

        async def _handle(item: dict) -> None:
            async with semaphore:
                try:
                    await self._process_single_item(item)
                except PlaywrightFallback:
                    record_fallback()
                    downgraded = dict(item)
                    downgraded["render_mode"] = "http"
                    downgraded.pop("wait_selector", None)
                    downgraded.pop("actions", None)
                    try:
                        await self._process_single_item(downgraded)
                    except Exception as exc:
                        try:
                            await mark_failed(item.get("link", ""), str(exc))
                        except Exception:
                            pass
                except Exception as exc:
                    try:
                        await mark_failed(item.get("link", ""), str(exc))
                    except Exception:
                        pass

        await asyncio.gather(*[_handle(item) for item in items])

    async def _run_workers(self, persistent: bool) -> None:
        worker_count = int(os.getenv("WORKERS", "4"))
        tasks = [asyncio.create_task(self._queue_worker(i, persistent=persistent)) for i in range(worker_count)]
        await asyncio.gather(*tasks)

    async def _queue_worker(self, worker_id: int, persistent: bool = False):
        """单个 Redis worker"""
        while True:
            payload = await pop_url(timeout=5)
            if payload is None:
                if persistent:
                    await asyncio.sleep(1)
                    continue
                break
            await asyncio.sleep(random.uniform(0.5, 1.5))
            item = json.loads(payload)
            try:
                await self._process_single_item(item)
            except PlaywrightFallback:
                record_fallback()
                downgraded = dict(item)
                downgraded["render_mode"] = "http"
                downgraded.pop("wait_selector", None)
                downgraded.pop("actions", None)
                await requeue_url(json.dumps(downgraded, ensure_ascii=False))
            except Exception as exc:
                await mark_failed(item.get("link", ""), str(exc))

    async def _process_single_item(self, item: dict):
        """根据 render_mode 处理单条记录"""
        link = item.get("link")
        if not link:
            raise ValueError("missing link")

        title = item.get("title", "") or ""

        if item.get("render_mode") == "playwright":
            wait_selector = item.get("wait_selector")
            actions = item.get("actions")
            try:
                html = await playwright_fetcher.fetch(link, wait_selector, actions)
            except PlaywrightFallback:
                record_request("playwright", "fail")
                raise
            record_request("playwright", "success")
            detail_text = scraper._parse_detail_html(html)
            if not detail_text:
                raise ValueError("empty detail content")
            item["detail_content"] = detail_text
            item["detail_scraped_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            scraper._update_detail_content(item)
            if not (title_hit(title) or detail_keyword_hit(detail_text)):
                await mark_irrelevant(link)
                return
        else:
            try:
                detail_item = scraper.scrape_detail({"link": link, "source": item.get("source", "detail")})
            except Exception:
                record_request("http", "fail")
                raise
            if detail_item.get("detail_content"):
                detail_html = detail_item["detail_content"]
                if title_hit(title) or detail_keyword_hit(detail_html):
                    record_request("http", "success")
                    return

                # HTTP 抽到的正文未命中行业词：尝试 Playwright 再抓一次（标题像“招采/公告”时）
                if item.get("render_mode") == "playwright" or _looks_like_procurement_title(title):
                    try:
                        html = await playwright_fetcher.fetch(link, item.get("wait_selector"), item.get("actions"))
                        record_request("playwright", "success")
                        detail_text = scraper._parse_detail_html(html)
                        if detail_text:
                            item["detail_content"] = detail_text
                            item["detail_scraped_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            scraper._update_detail_content(item)
                            if title_hit(title) or detail_keyword_hit(detail_text):
                                return
                    except PlaywrightFallback:
                        record_request("playwright", "fail")

                await mark_irrelevant(link)
                return
            else:
                record_request("http", "fail")
                # 为空时同样尝试 Playwright（标题像“招采/公告”时兜底）
                if item.get("render_mode") == "playwright" or _looks_like_procurement_title(title):
                    try:
                        html = await playwright_fetcher.fetch(link, item.get("wait_selector"), item.get("actions"))
                        record_request("playwright", "success")
                        detail_text = scraper._parse_detail_html(html)
                        if detail_text:
                            item["detail_content"] = detail_text
                            item["detail_scraped_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            scraper._update_detail_content(item)
                            if title_hit(title) or detail_keyword_hit(detail_text):
                                return
                            await mark_irrelevant(link)
                            return
                    except PlaywrightFallback:
                        record_request("playwright", "fail")
                raise ValueError("empty detail content")

    def _reload_details(self, items):
        """从数据库加载详情内容"""
        db_path = settings.get("storage.database_path", "data/marketing.db")
        if not Path(db_path).exists():
            return []
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        refreshed = []
        for item in items:
            link = item.get("link")
            if not link:
                continue
            cursor.execute("SELECT id, detail_content FROM scraped_data WHERE link = ?", (link,))
            row = cursor.fetchone()
            if row and row[1]:
                updated = dict(item)
                updated["id"] = row[0]
                updated["detail_content"] = row[1]
                refreshed.append(updated)
        conn.close()
        return refreshed

    def run_extractor(self):
        """运行联系人提取器"""
        print("👥 启动联系人提取...")

        try:
            # 从数据库加载爬取的数据
            import sqlite3

            db_path = settings.get("storage.database_path", "data/marketing.db")

            if not Path(db_path).exists():
                print("❌ 数据库不存在，请先运行爬虫")
                return 0

            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            export_run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            batch_size = int(os.getenv("EXTRACT_BATCH_SIZE", "200"))
            max_batches = int(os.getenv("EXTRACT_MAX_BATCHES", "0"))  # 0=不限
            batch_size = max(20, min(batch_size, 1000))
            max_batches = max(0, max_batches)

            processed_rows = 0
            extracted_contacts = 0
            batch_index = 0

            while True:
                if max_batches and batch_index >= max_batches:
                    break

                cursor.execute(
                    """
                    SELECT id, title, source, link, scraped_at, detail_content, raw_content
                    FROM scraped_data
                    WHERE processed = 0
                      AND link IS NOT NULL AND link != ''
                      AND (detail_content IS NOT NULL AND detail_content != ''
                           OR raw_content IS NOT NULL AND raw_content != '')
                    ORDER BY datetime(COALESCE(detail_scraped_at, scraped_at)) DESC
                    LIMIT ?
                    """,
                    (batch_size,),
                )
                rows = cursor.fetchall()
                if not rows:
                    break

                scraped_items = []
                ids = []
                for row in rows:
                    record_id = row[0]
                    detail = row[5] or ""
                    raw = row[6] or ""
                    content = detail or raw or ""
                    if not detail:
                        # 过滤掉导航菜单等无用内容（同时允许后续通过 backfill_detail_content 补抓详情自动重置 processed=0）
                        if len(content) <= 200 or ("采购" not in content and "招标" not in content and "中标" not in content):
                            ids.append(record_id)
                            continue
                    scraped_items.append(
                        {
                            "id": record_id,
                            "title": row[1] or "",
                            "source": row[2] or "",
                            "link": row[3] or "",
                            "scraped_at": row[4] or "",
                            "detail_content": detail,
                            "content": content,
                        }
                    )
                    ids.append(record_id)

                if scraped_items:
                    contacts = extractor.process_and_save(
                        scraped_items,
                        db_path=str(getattr(scraper, "db_path", "") or db_path),
                        export_mode="append_jsonl",
                        export_run_id=export_run_id,
                    )
                    extracted_contacts += len(contacts or [])

                # 无论是否抽到联系人，都标记本批已处理；后续若回填 detail_content 会自动重置 processed=0
                try:
                    scraper.mark_items_processed([int(i) for i in ids if i is not None])
                except Exception as mark_err:
                    print(f"⚠️  更新处理状态失败: {mark_err}")

                processed_rows += len(ids)
                batch_index += 1
                print(f"✅ 批次 {batch_index} 完成: 处理 {len(ids)} 条，累计处理 {processed_rows} 条，累计抽取 {extracted_contacts} 个联系人")

            conn.close()

            if processed_rows == 0:
                print("❌ 没有找到可提取的数据")
                return 0

            print(f"✅ 提取完成: 处理 {processed_rows} 条记录，抽取 {extracted_contacts} 个联系人")
            return extracted_contacts

        except Exception as e:
            print(f"❌ 提取联系人失败: {e}")
            return 0

    def run_emailer(self):
        """运行邮件发送"""
        print("📧 启动邮件发送...")

        # 检查邮件配置
        if not settings.email_configured:
            print("❌ 邮件未配置，请先配置邮件信息")
            print("💡 运行: python main.py --config")
            return

        # 测试邮件配置
        if not emailer.test_config():
            print("❌ 邮件配置测试失败，请检查配置信息")
            return

        # 加载联系人
        contacts = emailer.load_contacts_from_database()
        if not contacts:
            print("❌ 没有找到联系人数据")
            return

        print(f"📋 找到 {len(contacts)} 个联系人")

        # 准备邮件数据
        emails_to_send = []
        for contact in contacts[:10]:  # 限制发送数量
            if contact["emails"]:
                emails_to_send.append(
                    {
                        "email": contact["emails"][0],
                        "name": contact["names"][0] if contact["names"] else "项目负责人",
                        "company": contact["companies"][0] if contact["companies"] else "",
                        "title": contact["title"],
                    }
                )

        if not emails_to_send:
            print("❌ 没有找到有效的邮箱地址")
            return

        # 发送测试邮件
        print("🧪 发送测试邮件...")
        if emailer.send_test_email():
            print("✅ 测试邮件发送成功")
        else:
            print("❌ 测试邮件发送失败")
            return

        # 询问是否批量发送
        send_batch = input("\n📤 是否发送批量邮件? (y/N): ").lower()
        if send_batch == "y":
            print(f"📧 准备发送 {len(emails_to_send)} 封邮件...")
            results = emailer.send_batch_emails(emails_to_send, "marketing")
            print(f"✅ 发送完成: 成功 {results['success']}, 失败 {results['failed']}")

    def run_web(self):
        """启动Web界面"""
        print("🌐 启动Web界面...")

        try:
            project_root = Path(__file__).resolve().parent.parent
            dashboard_file = project_root / "scripts" / "web_dashboard.py"
            if not dashboard_file.exists():
                raise FileNotFoundError(f"missing dashboard script: {dashboard_file}")

            # 启动Streamlit
            import subprocess

            print("🌐 Web界面启动: http://localhost:8501")
            print("💡 按 Ctrl+C 停止服务")

            subprocess.run(
                [sys.executable, "-m", "streamlit", "run", str(dashboard_file)],
                cwd=str(project_root),
            )

        except Exception as e:
            print(f"❌ 启动Web界面失败: {e}")
            print("💡 请安装streamlit: pip install streamlit")

    def run_config(self):
        """运行配置向导"""
        print("⚙️ 系统配置向导")

        # 用户信息配置
        print("\n📋 配置用户信息:")
        name = input("姓名: ").strip() or "设计用户"
        email = input("邮箱: ").strip()
        company = input("公司/单位: ").strip()

        settings.set("user_info.name", name)
        settings.set("user_info.email", email)
        settings.set("user_info.company", company)

        # 邮件配置
        print("\n📧 配置邮件发送:")
        if not settings.email_configured:
            smtp_server = input("SMTP服务器 (默认: smtp.qq.com): ").strip() or "smtp.qq.com"
            smtp_port = int(input("SMTP端口 (默认: 587): ").strip() or "587")
            sender_email = input("发件邮箱: ").strip()
            sender_password = input("邮箱密码/应用专用密码: ").strip()
            sender_name = input("发件人姓名 (默认: 设计营销助手): ").strip() or "设计营销助手"

            settings.set("email.smtp_server", smtp_server)
            settings.set("email.smtp_port", smtp_port)
            settings.set("email.sender_email", sender_email)
            settings.set("email.sender_password", sender_password)
            settings.set("email.sender_name", sender_name)

            # 测试邮件配置
            print("\n🧪 测试邮件配置...")
            if emailer.test_config():
                print("✅ 邮件配置测试成功")
                settings.set("email.configured", True)
            else:
                print("❌ 邮件配置测试失败")
                settings.set("email.configured", False)

        # AI处理配置
        print("\n🤖 配置AI智能处理:")
        ai_enabled = input("启用AI智能联系人提取? (y/N): ").lower() == "y"
        settings.set("ai_processing.enabled", ai_enabled)

        if ai_enabled:
            print("\n   AI提供商选择:")
            print("   1. OpenAI (推荐)")
            print("   2. 自定义OpenAI兼容接口")

            provider_choice = input("   选择 (1-2): ").strip()
            if provider_choice == "2":
                provider = "openai"  # 使用openai兼容格式
                base_url = input("   API基础URL: ").strip()
                settings.set("ai_processing.provider", provider)
                settings.set("ai_processing.base_url", base_url)
            else:
                provider = "openai"
                settings.set("ai_processing.provider", provider)
                settings.set("ai_processing.base_url", "")

            api_key = input("   API密钥: ").strip()
            model = input("   模型 (默认: gpt-3.5-turbo): ").strip() or "gpt-3.5-turbo"

            settings.set("ai_processing.api_key", api_key)
            settings.set("ai_processing.model", model)

            print("\n   高级配置 (使用默认值):")
            batch_size = input("   批处理大小 (默认: 10): ").strip()
            if batch_size:
                settings.set("ai_processing.batch_size", int(batch_size))

            max_tokens = input("   最大令牌数 (默认: 1000): ").strip()
            if max_tokens:
                settings.set("ai_processing.max_tokens", int(max_tokens))

        # 数据源配置
        print("\n🕷️ 配置数据源:")
        sources = settings.get("scraper.sources", {})

        for source_id, source_config in sources.items():
            enabled = input(f"启用 {source_config['name']}? (y/N): ").lower() == "y"
            settings.set(f"scraper.sources.{source_id}.enabled", enabled)

        print("\n✅ 配置完成！")

    def show_status(self):
        """显示系统状态"""
        print("📊 系统状态")
        print("=" * 40)

        # 基本信息
        print("🏢 用户信息:")
        print(f"   姓名: {settings.get('user_info.name', '未配置')}")
        print(f"   邮箱: {settings.get('user_info.email', '未配置')}")
        print(f"   公司: {settings.get('user_info.company', '未配置')}")

        # 邮件配置
        print(f"\n📧 邮件配置: {'✅ 已配置' if settings.email_configured else '❌ 未配置'}")

        # AI配置
        ai_config = settings.get("ai_processing", {})
        ai_enabled = ai_config.get("enabled", False)
        ai_configured = bool(ai_enabled and ai_config.get("api_key"))

        print(f"\n🤖 AI智能处理: {'✅ 已配置' if ai_configured else '❌ 未配置'}")
        if ai_configured:
            print(f"   提供商: {ai_config.get('provider', 'N/A')}")
            print(f"   模型: {ai_config.get('model', 'N/A')}")

        # 数据源
        print("\n🕷️  数据源:")
        for source_id, source_config in settings.enabled_sources.items():
            print(f"   ✅ {source_config['name']}")

        stats = scraper.get_scraping_stats()
        print("\n📈 爬取统计:")
        print(f"   今日新增: {stats.get('today_count', 0)} 条")
        print(f"   总计入库: {stats.get('total_count', 0)} 条")
        print(f"   待提取详情: {stats.get('pending_detail_extraction', 0)} 条")
        print(f"   已处理详情: {stats.get('processed_detail_items', 0)} 条")
        if stats.get("oldest_pending_timestamp"):
            print(f"   最老待处理: {stats['oldest_pending_timestamp']}")
        retention_info = stats.get("retention", {})
        retention_cfg = retention_info.get("config", {}) or {}
        print(
            f"   保留策略: 最多 {retention_cfg.get('scraped_data_max_records', '∞')} 条, {retention_cfg.get('scraped_data_max_age_days', '∞')} 天"
        )
        last_cleanup = retention_info.get("last_cleanup", {}) or {}
        if last_cleanup.get("expired") or last_cleanup.get("overflow"):
            print(f"   最近清理: 过期 {last_cleanup.get('expired', 0)} 条, 超限 {last_cleanup.get('overflow', 0)} 条")

        # 数据库状态
        db_path = settings.get("storage.database_path", "data/marketing.db")
        db_file = Path(db_path)
        if db_file.exists():
            try:
                import sqlite3

                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()

                # 检查contacts表
                try:
                    cursor.execute("SELECT COUNT(*) FROM contacts")
                    contact_count = cursor.fetchone()[0]
                except Exception:
                    contact_count = 0

                # 检查去重表
                try:
                    cursor.execute("SELECT COUNT(*) FROM scraped_items_hash")
                    hash_count = cursor.fetchone()[0]
                except Exception:
                    hash_count = 0

                conn.close()
                print("\n📊 数据库状态:")
                print(f"   联系人: {contact_count} 条")
                print(f"   去重记录: {hash_count} 条")
                print(f"   文件大小: {db_file.stat().st_size / 1024:.1f} KB")
            except Exception as e:
                print(f"\n❌ 数据库读取失败: {e}")
        else:
            print("\n📊 数据库: 不存在")

    def clean_database(self):
        """清理数据库（保留策略 + contacts去重 + VACUUM）"""
        print("🧹 清理数据库...")
        db_path = Path(settings.get("storage.database_path", "data/marketing.db"))
        if not db_path.exists():
            print("❌ 数据库不存在")
            return

        def _format_bytes(size: int) -> str:
            if size < 1024:
                return f"{size} B"
            if size < 1024 * 1024:
                return f"{size / 1024:.1f} KB"
            return f"{size / (1024 * 1024):.2f} MB"

        before_size = db_path.stat().st_size
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT processed, COUNT(*) FROM scraped_data GROUP BY processed")
            processed_counts = {int(row[0] or 0): int(row[1] or 0) for row in cursor.fetchall()}
            cursor.execute("PRAGMA freelist_count")
            freelist_before = int(cursor.fetchone()[0] or 0)
            conn.close()
        except Exception:
            processed_counts = {}
            freelist_before = -1

        try:
            retention_stats = scraper._enforce_retention()
            print(
                "✅ 保留策略: 过期 %s 条, 超限 %s 条, hash 过期 %s 条, orphan contacts %s 条"
                % (
                    retention_stats.get("expired", 0),
                    retention_stats.get("overflow", 0),
                    retention_stats.get("hash_expired", 0),
                    retention_stats.get("contacts_orphaned", 0),
                )
            )
        except Exception as e:
            print(f"⚠️  执行保留策略失败: {e}")

        # contacts 按 link 去重：保留每个 link 最新一条
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='contacts'")
            if cursor.fetchone():
                cursor.execute(
                    """
                    DELETE FROM contacts
                    WHERE link IS NOT NULL AND link != ''
                      AND id NOT IN (SELECT MAX(id) FROM contacts GROUP BY link)
                    """
                )
                deduped = max(cursor.rowcount, 0)
                conn.commit()
                print(f"✅ contacts 去重: 删除 {deduped} 条重复记录")
            conn.close()
        except Exception as e:
            print(f"⚠️  contacts 去重失败: {e}")

        # VACUUM 收缩文件
        try:
            conn = sqlite3.connect(str(db_path))
            conn.execute("VACUUM")
            conn.close()
            print("✅ VACUUM 完成")
        except Exception as e:
            print(f"⚠️  VACUUM 失败: {e}")

        after_size = db_path.stat().st_size
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("SELECT processed, COUNT(*) FROM scraped_data GROUP BY processed")
            processed_counts_after = {int(row[0] or 0): int(row[1] or 0) for row in cursor.fetchall()}
            cursor.execute("PRAGMA freelist_count")
            freelist_after = int(cursor.fetchone()[0] or 0)
            conn.close()
        except Exception:
            processed_counts_after = {}
            freelist_after = -1

        if processed_counts or processed_counts_after:
            pending_before = processed_counts.get(0, 0)
            done_before = processed_counts.get(1, 0)
            pending_after = processed_counts_after.get(0, 0)
            done_after = processed_counts_after.get(1, 0)
            print(f"📊 scraped_data processed: 0={pending_before}->{pending_after}, 1={done_before}->{done_after}")

        if freelist_before >= 0 and freelist_after >= 0:
            print(f"📦 freelist_count: {freelist_before} -> {freelist_after}")

        print(f"📦 DB 文件大小: {_format_bytes(before_size)} -> {_format_bytes(after_size)} ({db_path})")

    def export_structured_contacts(self):
        """导出结构化联系人JSON"""
        print("📄 导出结构化联系人...")
        db_path = Path(settings.get("storage.database_path", "data/marketing.db"))
        if not db_path.exists():
            print("❌ 数据库不存在，请先运行爬虫/提取")
            return

        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(contacts)")
            existing_columns = {row[1] for row in cursor.fetchall()}

            select_cols = [
                "id",
                "title",
                "source",
                "link",
                "scraped_at",
                "created_at",
                "emails",
                "phones",
                "companies",
                "names",
                "addresses",
                "structured_contacts",
                "raw_text",
            ]
            if "procurement_title" in existing_columns:
                select_cols.append("procurement_title")
            if "organizations" in existing_columns:
                select_cols.append("organizations")

            cursor.execute(
                f"""
                SELECT {', '.join(select_cols)}
                FROM contacts
                ORDER BY datetime(created_at) DESC
                """
            )
            rows = cursor.fetchall()
            conn.close()
        except Exception as e:
            print(f"❌ 读取 contacts 表失败: {e}")
            return

        if not rows:
            print("📭 contacts 表为空")
            return

        contacts = []
        for row in rows:
            record = dict(zip(select_cols, row))
            contacts.append(
                {
                    "id": record.get("id"),
                    "title": record.get("title") or "",
                    "source": record.get("source") or "",
                    "link": record.get("link") or "",
                    "scraped_at": record.get("scraped_at") or "",
                    "emails": json.loads(record.get("emails")) if record.get("emails") else [],
                    "phones": json.loads(record.get("phones")) if record.get("phones") else [],
                    "companies": json.loads(record.get("companies")) if record.get("companies") else [],
                    "names": json.loads(record.get("names")) if record.get("names") else [],
                    "addresses": json.loads(record.get("addresses")) if record.get("addresses") else [],
                    "structured_contacts": json.loads(record.get("structured_contacts"))
                    if record.get("structured_contacts")
                    else [],
                    "raw_text": record.get("raw_text") or "",
                    "procurement_title": record.get("procurement_title") or "",
                    "organizations": json.loads(record.get("organizations")) if record.get("organizations") else {},
                }
            )

        export_results = extractor.export_contacts_tiered(contacts, mode="tiered_json")
        if not export_results:
            print("❌ 导出失败（请查看 logs/marketing.log）")
            return

        flat_results = extractor.export_contacts_flat(
            contacts,
            mode="append_jsonl",
            run_id=export_results.get("run_id"),
        )

        for tier in ("raw", "clean", "premium"):
            info = export_results.get(tier)
            if not info:
                continue
            path = info.get("path")
            count = info.get("count", 0)
            if path:
                print(f"✅ {tier} 导出: {count} 条 -> {path}")
        if flat_results.get("flat", {}).get("path"):
            print(f"✅ flat 导出: {flat_results['flat']['count']} 条 -> {flat_results['flat']['path']}")
