#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from storage.database import Database


def test_business_card_merges_phones_across_projects(tmp_path):
    db = Database(tmp_path / "t.db")
    try:
        ann_id = db.insert_announcement({
            "title": "t1",
            "url": "http://example.com/a",
            "content": "",
            "publish_date": "2026-01-24",
            "source": "test",
            "scraped_at": "2026-01-24T00:00:00",
        })
        assert ann_id is not None

        card_id_1 = db.upsert_business_card("A单位", "张三", phones=[], emails=[])
        assert card_id_1 is not None
        assert db.add_business_card_mention(card_id_1, ann_id, role="buyer") is True

        card_id_2 = db.upsert_business_card("A单位", "张三", phones=["13800138000"], emails=[])
        assert card_id_2 == card_id_1

        cards = db.get_business_cards("A单位", like=False, limit=10)
        assert len(cards) == 1
        assert cards[0]["company"] == "A单位"
        assert cards[0]["contact_name"] == "张三"
        assert "13800138000" in (cards[0].get("phones") or [])
        assert cards[0]["projects_count"] == 1

        # 再次写入同一个手机号不应重复
        _ = db.upsert_business_card("A单位", "张三", phones=["13800138000"], emails=[])
        cards2 = db.get_business_cards("A单位", like=False, limit=10)
        phones = cards2[0].get("phones") or []
        assert phones.count("13800138000") == 1

    finally:
        db.close()


def test_get_business_cards_like_query(tmp_path):
    db = Database(tmp_path / "t.db")
    try:
        _ = db.upsert_business_card("浙江警察学院", "李四", phones=["010-12345678"], emails=[])
        _ = db.upsert_business_card("浙江警察学院", "王五", phones=[], emails=["a@example.com"])
        _ = db.upsert_business_card("浙江大学", "赵六", phones=["13800138000"], emails=[])

        cards = db.get_business_cards("浙江", like=True, limit=10)
        companies = {c["company"] for c in cards}
        assert "浙江警察学院" in companies
        assert "浙江大学" in companies

    finally:
        db.close()
