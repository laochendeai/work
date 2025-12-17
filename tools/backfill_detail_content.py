#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
回填 scraped_data.detail_content

用于“已有链接但没有详情正文”的历史数据补抓，从而显著提升后续结构化抽取准确率。
默认只抓取缺失详情的记录；抓取成功会写回 marketing.db（UPDATE scraped_data）。
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, List

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from config.settings import settings  # noqa: E402
from core.filter import title_hit  # noqa: E402
from core.scraper import UnifiedScraper  # noqa: E402


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="回填 scraped_data.detail_content（批量抓取详情页）")
    parser.add_argument("--db", default=settings.get("storage.database_path", "data/marketing.db"), help="数据库路径")
    parser.add_argument("--limit", type=int, default=200, help="最多处理多少条记录")
    parser.add_argument("--concurrency", type=int, default=20, help="详情抓取并发数（HTTP）")
    parser.add_argument("--include-processed", action="store_true", help="包含 processed=1 的历史记录")
    parser.add_argument("--skip-title-filter", action="store_true", help="不使用标题关键词过滤（可能更耗时）")
    parser.add_argument("--dry-run", action="store_true", help="只统计/列出，不实际抓取")
    return parser.parse_args()


def _load_pending(db_path: str, limit: int, include_processed: bool) -> List[Dict[str, Any]]:
    db_file = Path(db_path)
    if not db_file.exists():
        raise FileNotFoundError(f"数据库不存在: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    processed_clause = "" if include_processed else "AND processed = 0"
    cursor.execute(
        f"""
        SELECT id, title, source, link
        FROM scraped_data
        WHERE (detail_content IS NULL OR detail_content = '')
          AND link IS NOT NULL AND link != ''
          {processed_clause}
        ORDER BY datetime(scraped_at) DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = cursor.fetchall()
    conn.close()

    items: List[Dict[str, Any]] = []
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


def main() -> int:
    args = _parse_args()

    # tools 允许指定 --db：确保抓取器实例写回同一个数据库
    try:
        settings.load_user_config()
        settings._user_config.setdefault("storage", {})["database_path"] = str(args.db)  # type: ignore[attr-defined]
    except Exception:
        pass
    scraper = UnifiedScraper()

    pending = _load_pending(args.db, max(args.limit, 1), args.include_processed)
    if not pending:
        print("没有需要回填的记录（detail_content 已存在或无可用 link）")
        return 0

    if not args.skip_title_filter:
        before = len(pending)
        pending = [item for item in pending if title_hit(item.get("title", ""))]
        print(f"标题关键词过滤: {before} -> {len(pending)}")
        if not pending:
            print("过滤后无可处理记录（可加 --skip-title-filter 继续）")
            return 0

    if args.dry_run:
        print(f"待回填记录数: {len(pending)}")
        for item in pending[:10]:
            print(f"- {item.get('link')}  {item.get('title', '')[:60]}")
        return 0

    items = [{"link": item["link"], "source": item.get("source", "detail")} for item in pending if item.get("link")]
    print(f"开始抓取详情: {len(items)} 条, concurrency={args.concurrency}")
    stats = scraper.scrape_details_bulk(items, concurrency=max(args.concurrency, 1))
    print(f"完成: processed={stats.get('processed')} ok={stats.get('succeeded')} failed={stats.get('failed')}")
    print("提示：抓取成功的记录会被更新为 processed=0，随后可直接运行 `python main.py --extract`")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
