#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量重抽取联系人（用于“把现有数据也优化起来”）

特点：
- 从 scraped_data 批量读取（优先 detail_content，否则 raw_content）
- 使用最新 ContactExtractor 逻辑重新抽取
- 对每个 link 做“替换式写入”（先删后插），避免重复累积
- 抽取完成后可选标记 processed=1
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from config.settings import settings  # noqa: E402
from core.extractor import extractor  # noqa: E402
from core.quality_exporter import QualityScorer  # noqa: E402


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="批量重抽取联系人（覆写 contacts 表）")
    parser.add_argument("--db", default=settings.get("storage.database_path", "data/marketing.db"), help="数据库路径")
    parser.add_argument("--limit", type=int, default=0, help="最多处理多少条（0=全部）")
    parser.add_argument("--batch-size", type=int, default=200, help="每批处理多少条")
    parser.add_argument("--include-processed", action="store_true", help="包含 processed=1 的历史记录")
    parser.add_argument("--mark-processed", action="store_true", help="处理完成后标记 processed=1")
    parser.add_argument("--min-confidence", type=float, default=None, help="最低质量分（默认取配置 export.tiers.clean.min_confidence）")
    parser.add_argument("--require-email", action="store_true", default=None, help="仅保留包含邮箱的记录（默认取配置 export.tiers.clean.require_email）")
    parser.add_argument("--no-require-email", action="store_false", dest="require_email", help="不强制邮箱")
    parser.add_argument("--dry-run", action="store_true", help="只统计，不写入 contacts/processed")
    return parser.parse_args()


def _iter_scraped_rows(
    conn: sqlite3.Connection,
    *,
    limit: int,
    batch_size: int,
    include_processed: bool,
) -> List[List[Dict[str, Any]]]:
    cursor = conn.cursor()
    where_processed = "" if include_processed else "AND processed = 0"

    cursor.execute(
        f"""
        SELECT COUNT(*)
        FROM scraped_data
        WHERE link IS NOT NULL AND link != ''
        {where_processed}
        """,
    )
    total = int(cursor.fetchone()[0] or 0)
    if limit and limit > 0:
        total = min(total, limit)

    batches: List[List[Dict[str, Any]]] = []
    offset = 0
    while offset < total:
        current_limit = min(batch_size, total - offset)
        cursor.execute(
            f"""
            SELECT id, title, source, link, scraped_at, detail_content, raw_content
            FROM scraped_data
            WHERE link IS NOT NULL AND link != ''
            {where_processed}
            ORDER BY datetime(COALESCE(detail_scraped_at, scraped_at)) DESC
            LIMIT ? OFFSET ?
            """,
            (current_limit, offset),
        )
        rows = cursor.fetchall()
        if not rows:
            break

        batch: List[Dict[str, Any]] = []
        for row in rows:
            detail = row[5] or ""
            raw = row[6] or ""
            content = detail or raw or ""
            batch.append(
                {
                    "id": row[0],
                    "title": row[1] or "",
                    "source": row[2] or "",
                    "link": row[3] or "",
                    "scraped_at": row[4] or "",
                    "detail_content": detail,
                    "content": content,
                }
            )

        batches.append(batch)
        offset += len(batch)

    return batches


def _update_processed(conn: sqlite3.Connection, ids: List[int]) -> None:
    if not ids:
        return
    cursor = conn.cursor()
    chunk_size = 800
    for start in range(0, len(ids), chunk_size):
        chunk = ids[start:start + chunk_size]
        placeholders = ",".join(["?"] * len(chunk))
        cursor.execute(f"UPDATE scraped_data SET processed = 1 WHERE id IN ({placeholders})", chunk)
    conn.commit()


def main() -> int:
    args = _parse_args()

    db_file = Path(args.db)
    if not db_file.exists():
        raise FileNotFoundError(f"数据库不存在: {args.db}")

    batch_size = max(int(args.batch_size), 1)
    limit = max(int(args.limit), 0)

    min_confidence = args.min_confidence
    if min_confidence is None:
        min_confidence = float(settings.get("export.tiers.clean.min_confidence", 0.3))

    require_email: bool = args.require_email
    if args.require_email is None:
        require_email = bool(settings.get("export.tiers.clean.require_email", True))

    scorer = QualityScorer()

    conn = sqlite3.connect(args.db)
    try:
        batches = _iter_scraped_rows(
            conn,
            limit=limit,
            batch_size=batch_size,
            include_processed=bool(args.include_processed),
        )

        total_rows = sum(len(batch) for batch in batches)
        print(f"待处理 scraped_data: {total_rows} 条 (batch_size={batch_size})")
        print(f"保存策略: min_confidence={min_confidence} require_email={require_email} dry_run={bool(args.dry_run)}")

        processed_rows = 0
        extracted_contacts = 0
        saved_contacts = 0

        for idx, batch in enumerate(batches, start=1):
            links = [item.get("link", "") for item in batch if item.get("link")]
            ids = [int(item["id"]) for item in batch if item.get("id") is not None]

            # 重新抽取
            contacts = extractor.extract_from_scraped_data(batch)
            extracted_contacts += len(contacts)

            # 质量评分与过滤（保存到 contacts 的子集）
            kept: List[Dict[str, Any]] = []
            for contact in contacts:
                score = scorer.score_contact(contact)
                contact["_quality_score"] = asdict(score)
                if score.total_score < min_confidence:
                    continue
                if require_email and not contact.get("emails"):
                    continue
                kept.append(contact)

            if not args.dry_run:
                # 替换式写入：即使 kept 为空也先删掉旧的，避免留下历史脏数据
                extractor.save_to_database(kept, args.db, replace_links=links)
                if args.mark_processed:
                    _update_processed(conn, ids)

            processed_rows += len(batch)
            saved_contacts += len(kept)

            if idx == 1 or idx % 5 == 0:
                print(
                    f"[{idx}/{len(batches)}] rows={processed_rows}/{total_rows} "
                    f"extracted_contacts={extracted_contacts} saved_contacts={saved_contacts}"
                )

        print("完成")
        print(f"- processed_rows: {processed_rows}")
        print(f"- extracted_contacts: {extracted_contacts}")
        print(f"- saved_contacts: {saved_contacts}")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())

