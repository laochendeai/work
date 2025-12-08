#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一爬虫引擎
整合所有爬虫功能，避免重复代码
支持多招标网站、自动索引、日期去重
"""

import time
import random
import logging
import hashlib
import sqlite3
import json
import re
from collections import Counter, defaultdict
from typing import Dict, List, Any, Optional, Generator
from urllib.parse import urljoin, urlparse
from datetime import datetime, timedelta
from pathlib import Path
from bs4 import BeautifulSoup

from config.settings import settings
from .fetcher import AdvancedFetcher, FetchError

class UnifiedScraper:
    """统一爬虫引擎"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.network_config = settings.get('scraper.network', {}) or {}
        self.fetcher = self._create_fetcher()
        self.source_health = defaultdict(lambda: {
            'status': Counter(),
            'failures': []
        })
        self.last_retention_stats = {'expired': 0, 'overflow': 0}
        self._init_database()

    def _create_fetcher(self) -> AdvancedFetcher:
        """构建具备HTTP/2和重试能力的抓取器"""
        retry_backoff = self.network_config.get('retry_backoff', {}) or {}
        return AdvancedFetcher(
            timeout=self.network_config.get('timeout', 30),
            concurrency=self.network_config.get('concurrency', 10),
            max_connections=self.network_config.get('max_connections', 30),
            max_keepalive_connections=self.network_config.get('max_keepalive_connections', 10),
            retry_attempts=self.network_config.get('retry_attempts', 3),
            backoff_min=retry_backoff.get('min', 0.5),
            backoff_max=retry_backoff.get('max', 8.0),
            http2=self.network_config.get('http2', True),
            user_agents=self.network_config.get('user_agents'),
            retry_for_statuses=self.network_config.get('retry_for_statuses'),
            respect_retry_after=self.network_config.get('respect_retry_after', True)
        )

    def _init_database(self):
        """初始化数据库，用于去重"""
        db_path = Path("data/marketing.db")
        db_path.parent.mkdir(exist_ok=True)

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # 创建去重表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scraped_items_hash (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_hash TEXT UNIQUE,
                title TEXT,
                source TEXT,
                link TEXT,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 存储原始爬取数据，供后续提取和去重
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scraped_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                source TEXT,
                link TEXT UNIQUE,
                publish_date TEXT,
                scraped_at TEXT,
                raw_content TEXT,
                detail_content TEXT,
                detail_scraped_at TEXT,
                processed INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_scraped_data_processed ON scraped_data(processed)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_scraped_data_scraped_at ON scraped_data(scraped_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_scraped_data_detail_time ON scraped_data(detail_scraped_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_scraped_data_source ON scraped_data(source)')

        conn.commit()
        conn.close()
        self.db_path = str(db_path)

    def _normalize_encoding(self, value: str) -> str:
        """尝试修复常见编码问题"""
        if not isinstance(value, str):
            return value
        if hasattr(value, 'encode'):
            for codec in ('latin1', 'cp1252'):
                try:
                    return value.encode(codec).decode('utf-8', errors='ignore')
                except Exception:  # noqa: BLE001
                    continue
        return value

    def _record_status(self, source_key: str, status_code: Optional[int]):
        if status_code is None:
            return
        bucket = self.source_health[source_key]['status']
        bucket[str(status_code)] += 1

    def _record_failure(self, source_key: str, url: str, error: str, status_code: Optional[int] = None):
        failure_log = self.source_health[source_key]['failures']
        failure_log.append({
            'url': url,
            'error': error,
            'status': status_code,
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        # 只保留最近的20条失败记录
        if len(failure_log) > 20:
            del failure_log[:-20]

    def _fetch_with_metrics(self, url: str, source_key: str, **kwargs):
        try:
            response = self.fetcher.fetch(url, **kwargs)
            self._record_status(source_key, response.status_code)
            for history_resp in getattr(response, 'history', []) or []:
                self._record_status(source_key, history_resp.status_code)
            return response
        except FetchError as exc:
            self._record_status(source_key, exc.status_code)
            self._record_failure(source_key, url, str(exc), exc.status_code)
            raise

    def _dump_source_health(self):
        report_path = Path('logs/source_health.json')
        payload = {}
        for source_key, data in self.source_health.items():
            payload[source_key] = {
                'status': dict(data['status']),
                'failures': data['failures']
            }
        report_path.parent.mkdir(exist_ok=True)
        with open(report_path, 'w', encoding='utf-8') as fp:
            json.dump(payload, fp, ensure_ascii=False, indent=2)

    def _generate_item_hash(self, item: Dict[str, Any]) -> str:
        """生成项目哈希值用于去重"""
        content = f"{item.get('title', '')}{item.get('source', '')}{item.get('link', '')}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    def _is_duplicate_item(self, item: Dict[str, Any]) -> bool:
        """检查项目是否重复"""
        item_hash = self._generate_item_hash(item)

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM scraped_items_hash WHERE item_hash = ?', (item_hash,))
            result = cursor.fetchone()
            conn.close()
            return result is not None
        except Exception as e:
            self.logger.error(f"检查重复失败: {e}")
            return False

    def _save_item_hash(self, item: Dict[str, Any]):
        """保存项目哈希值"""
        item_hash = self._generate_item_hash(item)

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO scraped_items_hash (item_hash, title, source, link)
                VALUES (?, ?, ?, ?)
            ''', (item_hash, item.get('title', ''), item.get('source', ''), item.get('link', '')))
            conn.commit()
            conn.close()
        except Exception as e:
            self.logger.error(f"保存哈希失败: {e}")

    def _save_raw_item(self, item: Dict[str, Any]):
        """将原始爬取结果写入数据库，供后续阶段使用"""
        if not item.get('link'):
            return

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO scraped_data (title, source, link, publish_date, scraped_at, raw_content)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(link) DO UPDATE SET
                    title=excluded.title,
                    source=excluded.source,
                    publish_date=excluded.publish_date,
                    scraped_at=excluded.scraped_at,
                    raw_content=CASE WHEN excluded.raw_content IS NOT NULL AND excluded.raw_content != ''
                        THEN excluded.raw_content ELSE scraped_data.raw_content END
            ''', (
                item.get('title', ''),
                item.get('source', ''),
                item.get('link'),
                item.get('publish_date', ''),
                item.get('scraped_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                item.get('raw_content', '')
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            self.logger.error(f"保存爬取数据失败: {e}")

    def _update_detail_content(self, item: Dict[str, Any]):
        """更新详情内容，用于后续联系人提取"""
        if not item.get('link') or not item.get('detail_content'):
            return

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE scraped_data
                SET detail_content = ?,
                    detail_scraped_at = ?,
                    processed = 0
                WHERE link = ?
            ''', (
                item.get('detail_content', ''),
                item.get('detail_scraped_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                item.get('link')
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            self.logger.error(f"保存详情内容失败: {e}")

    def mark_items_processed(self, item_ids: List[int]):
        """标记一批爬取的记录已完成联系人提取"""
        if not item_ids:
            return

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            placeholders = ','.join(['?'] * len(item_ids))
            cursor.execute(f'''UPDATE scraped_data SET processed = 1 WHERE id IN ({placeholders})''', item_ids)
            conn.commit()
            conn.close()
        except Exception as e:
            self.logger.error(f"标记记录为已处理失败: {e}")

    def _enforce_retention(self) -> Dict[str, int]:
        """按照配置清理过期或超限的数据"""
        retention_config = settings.get('storage.retention', {}) or {}
        max_age_days = retention_config.get('scraped_data_max_age_days')
        max_records = retention_config.get('scraped_data_max_records')
        deleted = {'expired': 0, 'overflow': 0}

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            if max_age_days:
                cutoff = (datetime.now() - timedelta(days=max_age_days)).strftime('%Y-%m-%d %H:%M:%S')
                cursor.execute('''
                    DELETE FROM scraped_data
                    WHERE processed = 1 AND datetime(COALESCE(detail_scraped_at, scraped_at)) < ?
                ''', (cutoff,))
                deleted['expired'] = max(cursor.rowcount, 0)

            if max_records:
                cursor.execute('SELECT COUNT(*) FROM scraped_data')
                total_records = cursor.fetchone()[0]
                if total_records and total_records > max_records:
                    excess = total_records - max_records
                    cursor.execute('''
                        SELECT id FROM scraped_data
                        WHERE processed = 1
                        ORDER BY datetime(COALESCE(detail_scraped_at, scraped_at)) ASC
                        LIMIT ?
                    ''', (excess,))
                    ids = [row[0] for row in cursor.fetchall()]

                    if len(ids) < excess:
                        remaining = excess - len(ids)
                        cursor.execute('''
                            SELECT id FROM scraped_data
                            WHERE processed = 0
                            ORDER BY datetime(COALESCE(detail_scraped_at, scraped_at)) ASC
                            LIMIT ?
                        ''', (remaining,))
                        ids.extend([row[0] for row in cursor.fetchall()])

                    if ids:
                        cursor.execute(
                            f'''DELETE FROM scraped_data WHERE id IN ({','.join('?' for _ in ids)})''', ids
                        )
                        deleted['overflow'] = max(cursor.rowcount, 0)

            conn.commit()
            conn.close()
        except Exception as e:
            self.logger.error(f"执行保留策略失败: {e}")

        self.last_retention_stats = deleted
        return deleted

    def scrape_all_sources(self) -> Generator[Dict[str, Any], None, None]:
        """爬取所有启用的数据源"""
        enabled_sources = settings.enabled_sources

        for source_id, source_config in enabled_sources.items():
            self.logger.info(f"开始爬取数据源: {source_config['name']}")

            try:
                if source_id == 'ccgp':
                    yield from self._scrape_ccgp(source_config)
                elif source_id == 'university':
                    yield from self._scrape_university(source_config)
                elif source_id == 'chinabidding':
                    yield from self._scrape_chinabidding(source_config)
                elif source_id == 'bidcenter':
                    yield from self._scrape_bidcenter(source_config)
                else:
                    self.logger.warning(f"未知数据源: {source_id}")

                # 随机延迟，避免被反爬虫
                delay_min = source_config.get('delay_min', 3)
                delay_max = source_config.get('delay_max', 8)
                time.sleep(random.uniform(delay_min, delay_max))

            except Exception as e:
                self.logger.error(f"爬取数据源 {source_config['name']} 失败: {e}")

        self._dump_source_health()
        cleanup_stats = self._enforce_retention()
        if cleanup_stats.get('expired') or cleanup_stats.get('overflow'):
            self.logger.info(
                "保留策略清理完成: 过期 %s 条, 超限 %s 条",
                cleanup_stats.get('expired', 0),
                cleanup_stats.get('overflow', 0)
            )

    def _scrape_ccgp(self, config: Dict[str, Any]) -> Generator[Dict[str, Any], None, None]:
        """爬取政府采购网"""
        base_url = config.get('base_url', 'http://www.ccgp.gov.cn')

        # 正确的URL结构
        urls_to_scrape = [
            # 采购公告 - 中央采购公告
            f"{base_url}/cggg/zygg/zbgg/",
            # 中标公告 - 中央中标公告
            f"{base_url}/cggg/zygg/cjgg/",
            # 更正公告 - 中央更正公告
            f"{base_url}/cggg/zygg/gzgg/",
            # 地方采购公告
            f"{base_url}/cggg/dfgg/",
            # 采购公告主页
            f"{base_url}/cggg/zygg/"
        ]

        for url in urls_to_scrape:
            try:
                self.logger.info(f"爬取页面: {url}")
                response = self._fetch_with_metrics(url, 'ccgp')

                if 'api' in url:
                    # API接口处理
                    yield from self._extract_ccgp_api_items(response, url)
                else:
                    # HTML页面处理
                    soup = BeautifulSoup(response.text, 'lxml')
                    items = self._extract_ccgp_items(soup, url)
                    for item in items:
                        # 检查去重
                        if self._is_duplicate_item(item):
                            self.logger.debug(f"跳过重复项目: {item['title']}")
                            continue
                        self._save_item_hash(item)
                        self._save_raw_item(item)
                        yield item

            except Exception as e:
                self.logger.error(f"爬取页面 {url} 失败: {e}")

    def _extract_ccgp_api_items(self, response, source_url: str) -> Generator[Dict[str, Any], None, None]:
        """从API提取CCGP数据"""
        try:
            data = response.json()
            if not data or 'data' not in data:
                return

            for item in data.get('data', []):
                yield {
                    'title': item.get('title', ''),
                    'link': item.get('url', ''),
                    'source': '政府采购网',
                    'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'publish_date': item.get('pubDate', ''),
                    'raw_content': json.dumps(item, ensure_ascii=False)
                }

        except Exception as e:
            self.logger.error(f"解析CCGP API失败: {e}")

    def _extract_ccgp_items(self, soup: BeautifulSoup, source_url: str) -> List[Dict[str, Any]]:
        """提取政府采购网页面条目"""
        items = []

        # 多种选择器策略
        selectors = [
            'vT-srch-result-list li a',  # 搜索结果列表
            '.vT-srch-result-list li a',  # 搜索结果列表（带点）
            'ul.vT-srch-list li a',       # 搜索列表
            '.c_list-bd li a',            # 常规列表
            '.main-list-con li a',        # 主列表
            'td[align="left"] a',         # 表格链接
            'a[href*="t"]',              # 通用链接
            'li a[href]'                 # 列表中的链接
        ]

        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                self.logger.info(f"使用选择器 '{selector}' 找到 {len(elements)} 个链接")
                for element in elements:
                    try:
                        item = self._process_ccgp_item(element, source_url)
                        if item and item['title'] and item['link']:
                            items.append(item)
                    except Exception as e:
                        self.logger.error(f"处理条目失败: {e}")

                if items:  # 如果找到了数据，就不再尝试其他选择器
                    break

        return items

    def _process_ccgp_item(self, element, source_url: str) -> Optional[Dict[str, Any]]:
        """处理单个CCGP条目"""
        try:
            title = element.get_text(strip=True)
            href = element.get('href', '')

            # 修复编码问题
            title = self._normalize_encoding(title)

            # 过滤无效链接
            if not title or not href:
                return None

            # 过滤非采购相关内容 - 放宽过滤条件
            keywords = ['采购', '招标', '中标', '公告', '采购结果', '更正', '公示', '投标', '项目', '中标候选人', '成交', '评标', '谈判']
            if not any(keyword in title for keyword in keywords):
                return None

            # 过滤标题过短的内容
            if len(title) < 8:
                return None

            # 处理相对链接
            if href.startswith('/'):
                full_link = f"http://www.ccgp.gov.cn{href}"
            elif not href.startswith('http'):
                full_link = urljoin(source_url, href)
            else:
                full_link = href

            # 尝试提取发布日期
            publish_date = self._extract_publish_date(element, title)

            return {
                'title': title,
                'link': full_link,
                'source': '政府采购网',
                'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'publish_date': publish_date,
                'raw_content': str(element)
            }

        except Exception as e:
            self.logger.error(f"处理CCGP条目失败: {e}")
            return None

    def _extract_publish_date(self, element, title: str) -> str:
        """提取发布日期"""
        # 尝试从元素中提取日期
        date_patterns = [
            r'(\d{4}年\d{1,2}月\d{1,2}日)',
            r'(\d{4}-\d{1,2}-\d{1,2})',
            r'(\d{4}/\d{1,2}/\d{1,2})',
            r'(\d{4}\.\d{1,2}\.\d{1,2})'
        ]

        # 从元素文本中提取
        text = element.get_text(strip=True)
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)

        # 从标题中提取
        for pattern in date_patterns:
            match = re.search(pattern, title)
            if match:
                return match.group(1)

        # 查找相邻的日期元素
        next_sibling = element.next_sibling
        if next_sibling:
            sibling_text = str(next_sibling)
            for pattern in date_patterns:
                match = re.search(pattern, sibling_text)
                if match:
                    return match.group(1)

        return ''

    def _scrape_chinabidding(self, config: Dict[str, Any]) -> Generator[Dict[str, Any], None, None]:
        """爬采中国采购与招标网"""
        base_url = "http://www.chinabidding.cn"

        urls_to_scrape = [
            f"{base_url}/zbxx/index.html",
            f"{base_url}/cggg/index.html"
        ]

        for url in urls_to_scrape:
            try:
                self.logger.info(f"爬取页面: {url}")
                response = self._fetch_with_metrics(url, 'chinabidding')
                soup = BeautifulSoup(response.text, 'lxml')

                items = self._extract_chinabidding_items(soup, url)
                for item in items:
                    if self._is_duplicate_item(item):
                        continue
                    self._save_item_hash(item)
                    self._save_raw_item(item)
                    yield item

            except Exception as e:
                self.logger.error(f"爬取页面 {url} 失败: {e}")

    def _extract_chinabidding_items(self, soup: BeautifulSoup, source_url: str) -> List[Dict[str, Any]]:
        """提取中国采购与招标网条目"""
        items = []

        selectors = [
            '.list-con li a',
            '.info-list a',
            'ul li a'
        ]

        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                for element in elements:
                    try:
                        title = element.get_text(strip=True)
                        href = element.get('href', '')

                        if not title or not href:
                            continue

                        if href.startswith('/'):
                            full_link = f"http://www.chinabidding.cn{href}"
                        elif not href.startswith('http'):
                            full_link = urljoin(source_url, href)
                        else:
                            full_link = href

                        publish_date = self._extract_publish_date(element, title)

                        item = {
                            'title': title,
                            'link': full_link,
                            'source': '中国采购与招标网',
                            'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'publish_date': publish_date,
                            'raw_content': str(element)
                        }

                        items.append(item)

                    except Exception as e:
                        self.logger.error(f"处理条目失败: {e}")

                if items:
                    break

        return items

    def _scrape_bidcenter(self, config: Dict[str, Any]) -> Generator[Dict[str, Any], None, None]:
        """爬采招标采购导航网"""
        base_url = "http://www.bidcenter.com.cn"

        try:
            self.logger.info(f"爬取页面: {base_url}")
            response = self._fetch_with_metrics(base_url, 'bidcenter')
            soup = BeautifulSoup(response.text, 'lxml')

            items = self._extract_bidcenter_items(soup, base_url)
            for item in items:
                if self._is_duplicate_item(item):
                    continue
                self._save_item_hash(item)
                self._save_raw_item(item)
                yield item

        except Exception as e:
            self.logger.error(f"爬取页面 {base_url} 失败: {e}")

    def _extract_bidcenter_items(self, soup: BeautifulSoup, source_url: str) -> List[Dict[str, Any]]:
        """提取招标采购导航网条目"""
        items = []

        # 这里可以根据实际网站结构调整选择器
        selectors = [
            '.news-list a',
            '.info-list a',
            'ul li a'
        ]

        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                for element in elements:
                    try:
                        title = element.get_text(strip=True)
                        href = element.get('href', '')

                        if not title or not href:
                            continue

                        if href.startswith('/'):
                            full_link = f"http://www.bidcenter.com.cn{href}"
                        elif not href.startswith('http'):
                            full_link = urljoin(source_url, href)
                        else:
                            full_link = href

                        publish_date = self._extract_publish_date(element, title)

                        item = {
                            'title': title,
                            'link': full_link,
                            'source': '招标采购导航网',
                            'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'publish_date': publish_date,
                            'raw_content': str(element)
                        }

                        items.append(item)

                    except Exception as e:
                        self.logger.error(f"处理条目失败: {e}")

                if items:
                    break

        return items

    def _scrape_university(self, config: Dict[str, Any]) -> Generator[Dict[str, Any], None, None]:
        """爬取高校采购信息"""
        # 扩展支持更多高校
        universities = [
            {"name": "清华大学", "url": "http://www.tsinghua.edu.cn"},
            {"name": "北京大学", "url": "http://www.pku.edu.cn"},
            {"name": "复旦大学", "url": "http://www.fudan.edu.cn"},
            {"name": "上海交通大学", "url": "http://www.sjtu.edu.cn"},
            {"name": "浙江大学", "url": "http://www.zju.edu.cn"},
            {"name": "南京大学", "url": "http://www.nju.edu.cn"}
        ]

        for university in universities:
            try:
                # 常见的高校采购页面路径
                procurement_paths = [
                    "/cggg",
                    "/cgxx",
                    "/zbcg",
                    "/cggg/index.htm",
                    "/info/1042",
                    "/xxgg"
                ]

                for path in procurement_paths:
                    procurement_url = f"{university['url']}{path}"

                    try:
                        response = self._fetch_with_metrics(procurement_url, 'university')
                        soup = BeautifulSoup(response.text, 'lxml')
                        items = self._extract_university_items(soup, university)

                        for item in items:
                            if self._is_duplicate_item(item):
                                continue
                            self._save_item_hash(item)
                            self._save_raw_item(item)
                            yield item

                        if items:  # 如果找到了数据，就不再尝试其他路径
                            break

                    except Exception:
                        continue

            except Exception as e:
                self.logger.error(f"爬取 {university['name']} 失败: {e}")

    def _extract_university_items(self, soup: BeautifulSoup, university: Dict[str, Any]) -> List[Dict[str, Any]]:
        """提取高校采购条目"""
        items = []

        selectors = [
            'a[href*="cg"]',
            'a[href*="procurement"]',
            'a[href*="tender"]',
            'a[href*="bid"]',
            '.news-list a',
            '.notice-list a',
            'ul li a'
        ]

        for selector in selectors:
            elements = soup.select(selector)
            for element in elements:
                try:
                    title = element.get_text(strip=True)
                    href = element.get('href', '')

                    # 过滤非采购相关内容
                    keywords = ['采购', '招标', '中标', '公告', 'procurement', 'tender', 'bid']
                    if not any(keyword in title.lower() for keyword in keywords):
                        continue

                    if not title or not href:
                        continue

                    if href.startswith('/'):
                        full_link = urljoin(university['url'], href)
                    elif not href.startswith('http'):
                        full_link = urljoin(university['url'], href)
                    else:
                        full_link = href

                    publish_date = self._extract_publish_date(element, title)

                    item = {
                        'title': title,
                        'link': full_link,
                        'source': university['name'],
                        'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'publish_date': publish_date,
                        'raw_content': str(element)
                    }

                    items.append(item)

                except Exception as e:
                    self.logger.error(f"提取条目失败: {e}")

            if items:
                break

        return items

    def scrape_detail(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """爬取详细信息"""
        if not item.get('link'):
            return item

        try:
            source_key = item.get('source', 'detail') or 'detail'
            response = self._fetch_with_metrics(item['link'], source_key)
            item['detail_content'] = self._parse_detail_html(response.text)
            item['detail_scraped_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self._update_detail_content(item)

        except Exception as e:
            self.logger.error(f"爬取详细信息失败 {item['link']}: {e}")

        return item

    def _parse_detail_html(self, html: str) -> str:
        """解析详情页HTML"""
        soup = BeautifulSoup(html, 'lxml')

        content_selectors = [
            '.content',
            '.article-content',
            '.detail-content',
            '.main-content',
            '.text-con',
            'div[class*="content"]',
            '.article'
        ]

        for selector in content_selectors:
            element = soup.select_one(selector)
            if element:
                content = self._normalize_encoding(element.get_text(strip=True))
                if content:
                    return content

        body = soup.find('body')
        if body:
            body_text = body.get_text(strip=True)[:2000]
            return self._normalize_encoding(body_text)

        return ''

    def scrape_details_bulk(
        self,
        items: List[Dict[str, Any]],
        *,
        concurrency: Optional[int] = None
    ) -> Dict[str, int]:
        """批量抓取详情页，优先使用HTTP/2并发"""
        url_to_item = {
            item['link']: item
            for item in items
            if item.get('link')
        }
        url_sources = {
            url: (item.get('source') or 'detail')
            for url, item in url_to_item.items()
        }

        stats = {
            'processed': len(url_to_item),
            'succeeded': 0,
            'failed': 0
        }

        if not url_to_item:
            return stats

        detail_concurrency = concurrency or \
            self.network_config.get('detail_concurrency', self.network_config.get('concurrency', 10))

        def failure_hook(url: str, status: Optional[int], error: str):
            source_key = url_sources.get(url, 'detail')
            self._record_status(source_key, status)
            self._record_failure(source_key, url, error, status)

        responses = self.fetcher.fetch_many(
            url_to_item.keys(),
            concurrency=detail_concurrency,
            failure_callback=failure_hook
        )

        for url, target_item in url_to_item.items():
            response = responses.get(url)
            if response is None:
                stats['failed'] += 1
                continue

            try:
                self._record_status(url_sources.get(url, 'detail'), response.status_code)
                target_item['detail_content'] = self._parse_detail_html(response.text)
                target_item['detail_scraped_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                self._update_detail_content(target_item)
                stats['succeeded'] += 1
            except Exception as exc:  # noqa: BLE001
                self.logger.error(f"批量爬取详情失败 {url}: {exc}")
                stats['failed'] += 1

        # 如果有未返回的URL，同样视为失败
        missing = stats['processed'] - stats['succeeded'] - stats['failed']
        if missing > 0:
            stats['failed'] += missing

        return stats

    def test_connection(self, url: str = None) -> bool:
        """测试网络连接"""
        test_url = url or "http://www.ccgp.gov.cn/"
        try:
            response = self._fetch_with_metrics(test_url, 'health-check', timeout=10)
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"连接测试失败: {e}")
            return False

    def get_scraping_stats(self) -> Dict[str, Any]:
        """获取爬取统计信息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 今日爬取数量
            today = datetime.now().strftime('%Y-%m-%d')
            cursor.execute('''
                SELECT COUNT(*) FROM scraped_items_hash
                WHERE DATE(scraped_at) = ?
            ''', (today,))
            today_count = cursor.fetchone()[0]

            # 总爬取数量
            cursor.execute('SELECT COUNT(*) FROM scraped_items_hash')
            total_count = cursor.fetchone()[0]

            # 各来源统计
            cursor.execute('''
                SELECT source, COUNT(*) as count
                FROM scraped_items_hash
                GROUP BY source
            ''')
            source_stats = dict(cursor.fetchall())

            # scraped_data 状态
            cursor.execute('''
                SELECT processed, COUNT(*) FROM scraped_data GROUP BY processed
            ''')
            pending_details = 0
            processed_details = 0
            for processed_flag, count in cursor.fetchall():
                if processed_flag:
                    processed_details = count
                else:
                    pending_details = count

            cursor.execute('SELECT COUNT(*) FROM scraped_data')
            total_scraped_records = cursor.fetchone()[0]

            cursor.execute('''
                SELECT MIN(datetime(COALESCE(detail_scraped_at, scraped_at)))
                FROM scraped_data
                WHERE processed = 0
            ''')
            oldest_pending = cursor.fetchone()[0]

            conn.close()

            retention_config = settings.get('storage.retention', {}) or {}

            return {
                'today_count': today_count,
                'total_count': total_count,
                'source_stats': source_stats,
                'pending_detail_extraction': pending_details,
                'processed_detail_items': processed_details,
                'scraped_data_total': total_scraped_records,
                'oldest_pending_timestamp': oldest_pending,
                'retention': {
                    'config': retention_config,
                    'last_cleanup': self.last_retention_stats
                }
            }

        except Exception as e:
            self.logger.error(f"获取统计信息失败: {e}")
            return {
                'today_count': 0,
                'total_count': 0,
                'source_stats': {},
                'pending_detail_extraction': 0,
                'processed_detail_items': 0,
                'scraped_data_total': 0,
                'oldest_pending_timestamp': None,
                'retention': {
                    'config': settings.get('storage.retention', {}),
                    'last_cleanup': self.last_retention_stats
                }
            }

# 全局爬虫实例
scraper = UnifiedScraper()
