#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抽样评估：现有爬取数据的联系人结构化抽取质量

默认只读，不修改数据库。
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter
from dataclasses import asdict
from pathlib import Path
import sys
from typing import Any, Dict, List, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from config.settings import settings
from core.extractor import ContactExtractor
from core.quality_exporter import QualityScorer


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="评估联系人抽取质量（抽样）")
    parser.add_argument("--db", default=settings.get("storage.database_path", "data/marketing.db"), help="数据库路径")
    parser.add_argument("--limit", type=int, default=200, help="抽样数量")
    parser.add_argument("--random", action="store_true", help="随机抽样（ORDER BY RANDOM()）")
    parser.add_argument("--out", default="", help="输出JSON报告路径（可选）")
    parser.add_argument("--show", type=int, default=5, help="打印低质量样例条数")
    return parser.parse_args()


def _fetch_samples(db_path: str, limit: int, random_pick: bool) -> List[Dict[str, Any]]:
    db_file = Path(db_path)
    if not db_file.exists():
        raise FileNotFoundError(f"数据库不存在: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    order = "ORDER BY RANDOM()" if random_pick else "ORDER BY datetime(COALESCE(detail_scraped_at, scraped_at)) DESC"
    cursor.execute(
        f"""
        SELECT
            id,
            title,
            source,
            link,
            scraped_at,
            CASE
                WHEN detail_content IS NOT NULL AND detail_content != '' THEN detail_content
                ELSE raw_content
            END AS content,
            CASE
                WHEN detail_content IS NOT NULL AND detail_content != '' THEN 'detail_content'
                ELSE 'raw_content'
            END AS content_field
        FROM scraped_data
        WHERE (detail_content IS NOT NULL AND detail_content != '')
           OR (raw_content IS NOT NULL AND raw_content != '')
        {order}
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
                "scraped_at": row[4] or "",
                "content": row[5] or "",
                "content_field": row[6] or "",
            }
        )
    return items


def main() -> int:
    args = _parse_args()

    extractor = ContactExtractor()
    scorer = QualityScorer()

    items = _fetch_samples(args.db, max(args.limit, 1), args.random)
    if not items:
        print("没有可评估的样本（detail_content/raw_content 均为空）")
        return 0

    totals = Counter()
    confidence = Counter()
    low_examples: List[Tuple[float, Dict[str, Any]]] = []
    report_rows: List[Dict[str, Any]] = []

    for item in items:
        totals["total"] += 1
        result = extractor.extract_from_text(item["content"], title=item["title"], source=item["source"])

        has_email = bool(result.get("emails"))
        has_phone = bool(result.get("phones"))
        has_company = bool(result.get("companies"))
        has_name = bool(result.get("names"))

        totals["has_email"] += int(has_email)
        totals["has_phone"] += int(has_phone)
        totals["has_company"] += int(has_company)
        totals["has_name"] += int(has_name)

        score = scorer.score_contact(result)
        confidence[score.confidence_level] += 1

        row = {
            "id": item["id"],
            "title": item["title"],
            "source": item["source"],
            "link": item["link"],
            "scraped_at": item["scraped_at"],
            "content_field": item.get("content_field", ""),
            "has_email": has_email,
            "has_phone": has_phone,
            "has_company": has_company,
            "has_name": has_name,
            "quality_score": asdict(score),
            "extracted": {
                "emails": result.get("emails", []),
                "phones": result.get("phones", []),
                "companies": result.get("companies", []),
                "names": result.get("names", []),
            },
        }
        report_rows.append(row)

        if score.total_score < 0.4:
            low_examples.append((score.total_score, row))

    print("评估完成")
    print(f"- 样本数: {totals['total']}")
    print(f"- 有邮箱: {totals['has_email']} ({totals['has_email'] / totals['total']:.1%})")
    print(f"- 有电话: {totals['has_phone']} ({totals['has_phone'] / totals['total']:.1%})")
    print(f"- 有机构: {totals['has_company']} ({totals['has_company'] / totals['total']:.1%})")
    print(f"- 有姓名: {totals['has_name']} ({totals['has_name'] / totals['total']:.1%})")
    print(f"- 置信度分布: {dict(confidence)}")

    if args.show and low_examples:
        low_examples.sort(key=lambda x: x[0])
        print(f"\n低质量样例（score<0.4）前 {min(args.show, len(low_examples))} 条:")
        for score_value, row in low_examples[: args.show]:
            print(f"- score={score_value:.3f} link={row['link']} title={row['title'][:60]}")

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "meta": {
                "db": str(args.db),
                "limit": int(args.limit),
                "random": bool(args.random),
            },
            "summary": {
                "totals": dict(totals),
                "confidence": dict(confidence),
            },
            "rows": report_rows,
        }
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n已写入报告: {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
