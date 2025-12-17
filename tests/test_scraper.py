#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""面向统一架构的核心单元测试"""

import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from config.settings import settings

# 测试应使用隔离的配置/数据库，避免读取或污染本地 user_config.json 与 data/marketing.db。
_TEST_DIR = Path(tempfile.mkdtemp(prefix="marketing_test_"))
settings.user_config_file = _TEST_DIR / "user_config.json"
settings._user_config = None  # type: ignore[attr-defined]
settings.load_user_config()
settings.set("storage.database_path", str(_TEST_DIR / "marketing_test.db"))

from core.extractor import ContactExtractor
from core.scraper import UnifiedScraper


class TestSettings(unittest.TestCase):
    """配置和数据源相关测试"""

    def test_enabled_sources_not_empty(self):
        sources = settings.enabled_sources
        self.assertTrue(sources, "启用数据源列表不应为空")
        self.assertIn('ccgp', sources)
        self.assertTrue(sources['ccgp']['enabled'])

    def test_storage_path_exists(self):
        db_path = Path(settings.get('storage.database_path', 'data/marketing.db'))
        # 目录应当存在，文件可能初次运行尚未创建
        self.assertTrue(db_path.parent.exists())


class TestExtractor(unittest.TestCase):
    """联系人提取器测试"""

    def setUp(self):
        self.extractor = ContactExtractor()

    def test_extract_from_text_basic_fields(self):
        sample = """
        项目联系人：张三\n
        电话：13800138000\n
        邮箱：zhangsan@example.com\n
        采购单位：某某大学\n
        地址：北京市朝阳区测试路99号
        """
        result = self.extractor.extract_from_text(sample)
        self.assertIn('13800138000', result['phones'])
        self.assertIn('zhangsan@example.com', result['emails'])
        self.assertTrue(any(name.startswith('张') for name in result['names']))
        self.assertTrue(result['structured_contacts'])

    def test_merge_contacts_deduplicates(self):
        sample = """
        一、采购人信息\n
        名称：测试医院\n
        联系人：李四 电话：010-12345678\n
        二、采购代理机构信息\n
        名称：测试代理公司\n
        联系人：李四 电话：010-12345678
        """
        result = self.extractor.extract_from_text(sample)
        merged = result['merged_contacts']
        phones = {contact.get('phone') for contact in merged if contact.get('phone')}
        self.assertEqual(len(phones), 1, "重复联系人应去重")

    def test_phone_extraction_does_not_concat_multiple_numbers(self):
        sample = """
        九、凡对本次公告内容提出询问，请按以下方式联系。
        1.采购人信息
        名称：测试单位
        联系方式：张三 电话：010-12345678 传真：010-87654321
        """
        result = self.extractor.extract_from_text(sample)
        phones = result.get('phones', [])
        self.assertIn('010-12345678', phones)
        self.assertNotIn('010-12345678010-87654321', phones)
        self.assertNotIn('0101234567801087654321', phones)

    def test_email_obfuscation_variants(self):
        sample = """
        联系人：张三
        邮箱：zhangsan(at)example(dot)com
        备用邮箱：lisi at example dot com
        """
        result = self.extractor.extract_from_text(sample)
        self.assertIn('zhangsan@example.com', result.get('emails', []))
        self.assertIn('lisi@example.com', result.get('emails', []))

    def test_email_from_mailto_link(self):
        sample = '<a href="mailto:service%40example.com">发送邮件</a>'
        result = self.extractor.extract_from_text(sample)
        self.assertIn('service@example.com', result.get('emails', []))


class TestScraperStorage(unittest.TestCase):
    """验证爬虫的数据库写入能力"""

    def setUp(self):
        self.scraper = UnifiedScraper()
        self.test_link = 'https://example.com/__unittest__'
        self._cleanup_record()
        self.retention_backup = {
            'days': settings.get('storage.retention.scraped_data_max_age_days', None),
            'max_records': settings.get('storage.retention.scraped_data_max_records', None)
        }
        settings.set('storage.retention.scraped_data_max_age_days', 30)
        settings.set('storage.retention.scraped_data_max_records', 1000)

    def tearDown(self):
        self._cleanup_record()
        settings.set('storage.retention.scraped_data_max_age_days', self.retention_backup['days'])
        settings.set('storage.retention.scraped_data_max_records', self.retention_backup['max_records'])

    def _cleanup_record(self):
        conn = sqlite3.connect(self.scraper.db_path)
        cursor = conn.cursor()
        links = [self.test_link, f"{self.test_link}/old"]
        cursor.execute(f"DELETE FROM scraped_data WHERE link IN ({','.join('?' for _ in links)})", links)
        cursor.execute(f"DELETE FROM scraped_items_hash WHERE link IN ({','.join('?' for _ in links)})", links)
        conn.commit()
        conn.close()

    def test_save_raw_item_and_update_detail(self):
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        item = {
            'title': '这是一个用于单元测试的项目中标结果公告',
            'source': '单元测试',
            'link': self.test_link,
            'publish_date': now_str,
            'scraped_at': now_str,
            'raw_content': '<a>测试</a>'
        }
        self.scraper._save_item_hash(item)
        self.scraper._save_raw_item(item)

        conn = sqlite3.connect(self.scraper.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT title, detail_content FROM scraped_data WHERE link = ?', (self.test_link,))
        row = cursor.fetchone()
        self.assertIsNotNone(row, '原始记录应写入数据库')
        self.assertEqual(row[0], '这是一个用于单元测试的项目中标结果公告')
        conn.close()

        # 更新详情内容
        item['detail_content'] = '这是测试详情内容'
        item['detail_scraped_at'] = now_str
        self.scraper._update_detail_content(item)

        conn = sqlite3.connect(self.scraper.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT detail_content FROM scraped_data WHERE link = ?', (self.test_link,))
        detail_row = cursor.fetchone()
        conn.close()
        self.assertEqual(detail_row[0], '这是测试详情内容')

    def test_enforce_retention_removes_old_records(self):
        old_timestamp = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d %H:%M:%S')
        item = {
            'title': '这是一个用于单元测试的过期中标结果公告',
            'source': 'RetentionTest',
            'link': f"{self.test_link}/old",
            'publish_date': old_timestamp,
            'scraped_at': old_timestamp,
            'raw_content': 'old content'
        }
        self.scraper._save_item_hash(item)
        self.scraper._save_raw_item(item)

        conn = sqlite3.connect(self.scraper.db_path)
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE scraped_data SET processed = 1, detail_scraped_at = ? WHERE link = ?',
            (old_timestamp, item['link'])
        )
        conn.commit()
        conn.close()

        stats = self.scraper._enforce_retention()
        self.assertGreaterEqual(stats['expired'], 1)

        conn = sqlite3.connect(self.scraper.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM scraped_data WHERE link = ?', (item['link'],))
        remaining = cursor.fetchone()[0]
        conn.close()
        self.assertEqual(remaining, 0)


if __name__ == '__main__':
    unittest.main()
