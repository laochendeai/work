import unittest
from unittest.mock import Mock

from main import _normalize_card_payload, _process_search_result


class MainProcessingTests(unittest.TestCase):
    def test_normalize_card_payload_uses_cleaner_output(self):
        cleaner = Mock()
        cleaner.clean_contacts.return_value = {
            "company": "测试公司",
            "contacts": ["张三"],
            "phones": ["123"],
            "emails": ["a@test.com"],
        }

        payload = _normalize_card_payload(
            {
                "company": "原公司",
                "contact_name": "原联系人",
                "phones": ["123"],
                "emails": ["a@test.com"],
            },
            cleaner,
        )

        self.assertEqual(payload, ("测试公司", "张三", ["123"], ["a@test.com"]))

    def test_process_search_result_returns_insert_stats(self):
        db = Mock()
        db.insert_announcement.return_value = 101
        db.upsert_business_card.return_value = 202
        db.add_business_card_mention.return_value = True

        detail_fetcher = Mock()
        detail_fetcher.fetch.return_value = "<html>content</html>"

        parser = Mock()
        parser.parse.return_value = {"parsed": True}
        parser.format_for_storage.return_value = {
            "title": "格式化标题",
            "content": "正文",
            "publish_date": "2026-03-13",
            "buyer_name": "采购单位",
            "buyer_contact": "李四",
            "buyer_phone": "123456",
            "buyer_email": "buyer@test.com",
            "agent_name": "",
            "agent_contacts_list": [],
            "agent_contact": "",
            "agent_phone": "",
            "agent_email": "",
            "project_phone": "",
            "project_contacts": [],
            "supplier": "",
        }

        cleaner = Mock()
        cleaner.clean_announcement.side_effect = lambda announcement: announcement
        cleaner.clean_contacts.side_effect = lambda payload: {
            "company": payload["company"],
            "contacts": payload["contacts"],
            "phones": payload["phones"],
            "emails": payload["emails"],
        }

        inserted, card_writes = _process_search_result(
            {
                "title": "搜索标题",
                "url": "https://example.com/item",
                "publish_date": "2026-03-13",
            },
            db=db,
            detail_fetcher=detail_fetcher,
            parser=parser,
            cleaner=cleaner,
        )

        self.assertTrue(inserted)
        self.assertEqual(card_writes, 1)
        db.insert_announcement.assert_called_once()
        db.add_business_card_mention.assert_called_once()

    def test_process_search_result_uses_prefetched_html_first(self):
        db = Mock()
        db.insert_announcement.return_value = 101
        db.upsert_business_card.return_value = 202
        db.add_business_card_mention.return_value = True

        detail_fetcher = Mock()

        parser = Mock()
        parser.parse.return_value = {"parsed": True}
        parser.format_for_storage.return_value = {
            "title": "格式化标题",
            "content": "正文",
            "publish_date": "2026-03-13",
            "buyer_name": "采购单位",
            "buyer_contact": "李四",
            "buyer_phone": "123456",
            "buyer_email": "buyer@test.com",
            "agent_name": "",
            "agent_contacts_list": [],
            "agent_contact": "",
            "agent_phone": "",
            "agent_email": "",
            "project_phone": "",
            "project_contacts": [],
            "supplier": "",
        }

        cleaner = Mock()
        cleaner.clean_announcement.side_effect = lambda announcement: announcement
        cleaner.clean_contacts.side_effect = lambda payload: {
            "company": payload["company"],
            "contacts": payload["contacts"],
            "phones": payload["phones"],
            "emails": payload["emails"],
        }

        inserted, card_writes = _process_search_result(
            {
                "title": "搜索标题",
                "url": "https://example.com/item",
                "publish_date": "2026-03-13",
            },
            db=db,
            detail_fetcher=detail_fetcher,
            parser=parser,
            cleaner=cleaner,
            prefetched_html="<html>prefetched</html>",
        )

        self.assertTrue(inserted)
        self.assertEqual(card_writes, 1)
        detail_fetcher.fetch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
