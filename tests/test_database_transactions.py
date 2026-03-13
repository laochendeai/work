import tempfile
import unittest
from pathlib import Path

from storage.database import Database


class DatabaseTransactionTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.db"
        self.db = Database(db_path=str(self.db_path))

    def tearDown(self):
        self.db.close()
        self.temp_dir.cleanup()

    def test_batch_transaction_commits_multiple_writes(self):
        self.db.begin()
        announcement_id = self.db.insert_announcement(
            {
                "title": "测试公告",
                "url": "https://example.com/a",
                "content": "content",
                "publish_date": "2026-03-13",
                "source": "test",
                "scraped_at": "2026-03-13T00:00:00",
            }
        )
        card_id = self.db.upsert_business_card(
            "测试公司", "张三", phones=["123456"], emails=["a@test.com"]
        )
        self.assertIsNotNone(announcement_id)
        self.assertIsNotNone(card_id)
        assert announcement_id is not None
        assert card_id is not None
        mention_ok = self.db.add_business_card_mention(
            card_id, announcement_id, role="buyer"
        )
        self.db.commit()

        self.assertTrue(announcement_id)
        self.assertTrue(card_id)
        self.assertTrue(mention_ok)
        self.assertEqual(
            self.db.get_announcement_id_by_url("https://example.com/a"), announcement_id
        )
        self.assertEqual(len(self.db.get_business_cards("测试公司")), 1)

    def test_rollback_discards_uncommitted_changes(self):
        self.db.begin()
        self.db.insert_announcement(
            {
                "title": "回滚公告",
                "url": "https://example.com/rollback",
                "content": "content",
                "publish_date": "2026-03-13",
                "source": "test",
                "scraped_at": "2026-03-13T00:00:00",
            }
        )
        self.db.rollback()

        self.assertIsNone(
            self.db.get_announcement_id_by_url("https://example.com/rollback")
        )

    def test_bulk_lookup_returns_existing_url_map(self):
        self.db.insert_announcement(
            {
                "title": "已存在公告",
                "url": "https://example.com/existing",
                "content": "content",
                "publish_date": "2026-03-13",
                "source": "test",
                "scraped_at": "2026-03-13T00:00:00",
            }
        )

        mapping = self.db.get_existing_announcement_ids(
            [
                "https://example.com/existing",
                "https://example.com/missing",
            ]
        )

        self.assertIn("https://example.com/existing", mapping)
        self.assertNotIn("https://example.com/missing", mapping)


if __name__ == "__main__":
    unittest.main()
