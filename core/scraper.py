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
import yaml
import asyncio
import threading
from collections import Counter, defaultdict, deque
from typing import Dict, List, Any, Optional, Generator, Tuple
from urllib.parse import parse_qs, parse_qsl, quote, unquote, urlencode, urljoin, urlparse, urlunparse
from datetime import datetime, timedelta
from pathlib import Path
from bs4 import BeautifulSoup

from config.settings import settings
from core.filter import title_hit, detail_keyword_hit, has_contact_info, keywords
from .fetcher import AdvancedFetcher, FetchError

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
UNIVERSITY_SOURCES_FILE = CONFIG_DIR / "university_sources.yaml"
DEFAULT_UNIVERSITY_SOURCES = [
    {"name": "清华大学", "url": "https://www.tsinghua.edu.cn/"},
    {"name": "北京大学", "url": "https://www.pku.edu.cn/"},
    {"name": "复旦大学", "url": "https://www.fudan.edu.cn/"},
    {"name": "上海交通大学", "url": "https://www.sjtu.edu.cn/"},
    {"name": "浙江大学", "url": "https://www.zju.edu.cn/"},
    {"name": "南京大学", "url": "https://www.nju.edu.cn/"}
]
AWARD_TITLE_KEYWORDS = ['中标', '成交', '结果', '中选']

_AUTO_SOURCES_LOCK = threading.Lock()

def _ensure_university_sources_file() -> None:
    UNIVERSITY_SOURCES_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not UNIVERSITY_SOURCES_FILE.exists():
        try:
            import yaml

            UNIVERSITY_SOURCES_FILE.write_text(
                yaml.safe_dump({"universities": DEFAULT_UNIVERSITY_SOURCES}, allow_unicode=True, sort_keys=False),
                encoding='utf-8'
            )
        except Exception:
            # fallback to JSON if yaml not available
            UNIVERSITY_SOURCES_FILE.write_text(
                json.dumps({"universities": DEFAULT_UNIVERSITY_SOURCES}, ensure_ascii=False, indent=2),
                encoding='utf-8'
            )


GENERIC_KEYWORDS = [
    '招标', '采购', '公告', '中标', '更正', '公示', '项目', '成交', '投标', '比选'
]

GENERIC_SELECTORS = [
    '.list li a',
    '.news-list li a',
    '.article-list li a',
    '.notice-list li a',
    '.main-list-con li a',
    '.list_box li a',
    'td a',
    'tr a',
    'li a'
]

# 常见跟踪/分享参数：用于去重时的“安全忽略”，避免同一详情页因 utm/spm 等参数产生重复记录
_TRACKING_QUERY_KEYS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "utm_id",
    "spm",
    "spm_id_from",
    "from",
    "source",
    "src",
    "ref",
    "referer",
    "referrer",
    "share",
    "share_token",
    "scene",
    "timestamp",
}


def _normalize_url(url: str) -> str:
    parsed = urlparse(url)
    scheme = parsed.scheme or 'https'
    netloc = parsed.netloc
    if not netloc:
        return url
    normalized = parsed._replace(scheme=scheme, fragment='', query='')
    return urlunparse(normalized)


def _source_display_name(config: Dict[str, Any], domain: str) -> str:
    name = config.get('name')
    return name or f"自动发现: {domain}"

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
        self._db_lock = threading.Lock()
        self._init_database()
        self.discovery_config = settings.get('scraper.discovery', {}) or {}
        self.discovery_cache_file = Path("data") / "discovered_listings.json"
        self.discovery_cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.discovery_cache = self._load_discovery_cache()
        self.discovery_cache_ttl = int(self.discovery_config.get('cache_ttl_days', 7))
        self.policy = self._load_source_policy()
        self.deny_link_keywords = {str(item) for item in self.policy.get('deny_link_keywords', []) if item}
        self.deny_link_substrings = {str(item).lower() for item in self.policy.get('deny_link_substrings', []) if item}
        _ensure_university_sources_file()
        self._sources_cache: Optional[List[Dict[str, Any]]] = None

    def _looks_like_listing_url(self, url: str) -> bool:
        """基于URL形态判断是否更像“列表入口”而非“详情页”。

        入口固化时尽量只保留 index/list/分页 等列表页形态，避免把详情页写入 entry_urls。
        """
        if not url:
            return False
        parsed = urlparse(url)
        path = (parsed.path or "").lower()
        query = (parsed.query or "").lower()
        # 排除常见下载文件
        if path.endswith((".pdf", ".doc", ".docx", ".xls", ".xlsx", ".zip", ".rar")):
            return False
        # 排除详情页常见命名/路由
        if "-detail" in path or "/detail" in path or "/content" in path:
            return False
        # 排除包含长数字ID的路径（常见为详情页），但保留常见栏目编号目录（如 /jyxx/003001/）
        if re.search(r"/\d{8,}(?:/|$)", path):
            return False
        if re.search(r"/\d{6,7}(?:/|$)", path):
            # 栏目编号目录/分页入口通常以 / 结尾或包含 index/list；其余更可能是详情页
            if not (path.endswith("/") or "index" in path or "list" in path):
                return False
        # 排除“按年月归档的详情页”（但保留显式 index/list）
        if (
            re.search(r"/20\d{2}/\d{1,2}/", path)
            and path.endswith((".htm", ".html"))
            and "index" not in path
            and "list" not in path
        ):
            return False

        # 目录/首页（通常也可能作为入口兜底）
        if not path or path.endswith("/"):
            return True
        # 列表页常见命名
        if "index" in path or "list" in path:
            return True
        # 常见分页参数
        if any(key in query for key in ("page=", "p=", "curpage=")):
            return True
        # 部分站点使用 search 页作为公告入口
        if path.endswith(("search.html", "search.htm")):
            return True
        # 常见采购/公告栏目路径（部分站点为SPA路由，不含 index/list）
        listing_tokens = (
            "/notice",
            "/info-notice",
            "cggg",
            "zbgg",
            "cjgg",
            "jgg",
            "result-notice",
            "procument-notice",
        )
        if any(token in path for token in listing_tokens):
            return True
        return False

    def _unwrap_duckduckgo_redirect_url(self, href: str) -> str:
        if not href:
            return ""
        href = href.strip()
        if href.startswith("//"):
            href = f"https:{href}"
        parsed = urlparse(href)
        if parsed.netloc.endswith("duckduckgo.com") and parsed.path == "/l/":
            uddg = parse_qs(parsed.query or "").get("uddg", [None])[0]
            if uddg:
                return unquote(uddg)
        return href

    def _duckduckgo_site_search(self, domain: str, query: str, *, max_links: int = 30) -> List[str]:
        """使用 DuckDuckGo（通过 r.jina.ai 代理）做站内搜索，返回候选URL列表。"""
        if not domain or not query:
            return []
        search_query = f"site:{domain} {query}".strip()
        proxy_url = f"https://r.jina.ai/http://duckduckgo.com/html/?q={quote(search_query)}"
        try:
            resp = self.fetcher.fetch(proxy_url)
        except Exception:
            return []
        text = (resp.text or "").strip()
        if not text:
            return []
        links = re.findall(r"https?://duckduckgo\.com/l/\?uddg=[^\s)\"]+", text)
        results: List[str] = []
        seen: set[str] = set()
        for link in links:
            target = self._unwrap_duckduckgo_redirect_url(link)
            if not target:
                continue
            parsed = urlparse(target)
            if not parsed.scheme or not parsed.netloc:
                continue
            normalized = urlunparse(parsed._replace(fragment=""))
            if normalized in seen:
                continue
            seen.add(normalized)
            results.append(normalized)
            if len(results) >= max_links:
                break
        return results

    def _score_listing_candidate_url(self, url: str) -> int:
        """为“可能是中标/成交列表页”的URL打分，用于候选排序。"""
        if not url:
            return 0
        parsed = urlparse(url)
        path = (parsed.path or "").lower()
        query = (parsed.query or "").lower()
        score = 0

        # 结果/成交/中标优先
        if any(token in path for token in ("result", "hbgg", "cjgg")):
            score += 6
        if "zbgg" in path:
            score += 5
        if "jgg" in path:
            score += 2

        # 常见栏目形态
        if "notice" in path:
            score += 2
        if "info-notice" in path:
            score += 3
        if "index" in path or "list" in path:
            score += 2
        if any(key in query for key in ("page=", "p=", "curpage=")):
            score += 1

        # 明显非列表/详情特征降分
        if "-detail" in path or "/detail" in path:
            score -= 8
        if re.search(r"/\d{6,}", path):
            score -= 6
        if path.endswith((".pdf", ".doc", ".docx", ".xls", ".xlsx")):
            score -= 10

        return score

    def _create_fetcher(self) -> AdvancedFetcher:
        """构建具备HTTP/2和重试能力的抓取器"""
        # 优先使用性能配置，否则使用网络配置
        performance_config = settings.get('scraper.performance', {}) or {}
        retry_backoff = self.network_config.get('retry_backoff', {}) or {}

        return AdvancedFetcher(
            timeout=self.network_config.get('timeout', 30),
            concurrency=performance_config.get('http_concurrency', self.network_config.get('concurrency', 30)),
            max_connections=performance_config.get('http_max_connections', self.network_config.get('max_connections', 100)),
            max_keepalive_connections=performance_config.get('http_max_keepalive', self.network_config.get('max_keepalive_connections', 50)),
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
        db_path = Path(settings.get('storage.database_path', 'data/marketing.db'))
        db_path.parent.mkdir(exist_ok=True)

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        try:
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
        except Exception:  # pragma: no cover
            pass

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

        # 数据源运行状态：用于“和本地已有比对”并避免 auto_sources 每次全量重复爬
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS source_crawl_state (
                source_key TEXT PRIMARY KEY,
                source_id TEXT,
                base_url TEXT,
                config_type TEXT,
                last_crawled_at TEXT,
                last_emitted INTEGER DEFAULT 0,
                last_status TEXT,
                last_error TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_source_crawl_state_source_id ON source_crawl_state(source_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_source_crawl_state_updated_at ON source_crawl_state(updated_at)')

        conn.commit()
        conn.close()
        self.db_path = str(db_path)

    def _source_state_key(self, source_id: str, base_url: str) -> str:
        """生成数据源状态 key（尽量稳定，避免 http/https 等差异）。"""
        key = self._canonical_link_key(base_url)
        return key or (source_id or (base_url or "").strip())

    def _get_source_crawl_state(self, source_key: str) -> Optional[Dict[str, Any]]:
        if not source_key:
            return None
        try:
            with self._db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT last_crawled_at, last_emitted, last_status
                    FROM source_crawl_state
                    WHERE source_key = ?
                    """,
                    (source_key,),
                )
                row = cursor.fetchone()
                conn.close()
            if not row:
                return None
            return {
                "last_crawled_at": row[0] or "",
                "last_emitted": int(row[1] or 0),
                "last_status": row[2] or "",
            }
        except Exception:
            return None

    def _should_skip_source_run(self, source_id: str, base_url: str, config_type: str) -> tuple[bool, str]:
        """判断是否跳过某个数据源（仅对非 user 源、且上次无新增时按冷却窗口跳过）。"""
        schedule_cfg = settings.get("scraper.schedule", {}) or {}
        try:
            cooldown_hours = float(schedule_cfg.get("auto_source_cooldown_hours", 0) or 0)
        except (TypeError, ValueError):
            cooldown_hours = 0.0

        if cooldown_hours <= 0:
            return False, ""
        if not base_url:
            return False, ""
        if (config_type or "") in {"user", "recommended"}:
            return False, ""

        source_key = self._source_state_key(source_id, base_url)
        state = self._get_source_crawl_state(source_key)
        if not state:
            return False, ""

        if state.get("last_status") != "success":
            return False, ""
        if int(state.get("last_emitted") or 0) > 0:
            return False, ""

        last_crawled_at = (state.get("last_crawled_at") or "").strip()
        if not last_crawled_at:
            return False, ""
        try:
            last_dt = datetime.strptime(last_crawled_at, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return False, ""

        delta_hours = (datetime.now() - last_dt).total_seconds() / 3600.0
        if delta_hours < cooldown_hours:
            remaining = max(cooldown_hours - delta_hours, 0.0)
            return True, f"cooldown={cooldown_hours:.0f}h remaining={remaining:.1f}h"
        return False, ""

    def _record_source_run(
        self,
        source_id: str,
        base_url: str,
        config_type: str,
        *,
        emitted: int,
        status: str,
        error: str = "",
    ) -> None:
        source_key = self._source_state_key(source_id, base_url)
        if not source_key:
            return
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        safe_status = status if status in {"success", "error"} else "success"
        safe_error = (error or "")[:500]

        try:
            with self._db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO source_crawl_state (
                        source_key, source_id, base_url, config_type,
                        last_crawled_at, last_emitted, last_status, last_error, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(source_key) DO UPDATE SET
                        source_id=excluded.source_id,
                        base_url=excluded.base_url,
                        config_type=excluded.config_type,
                        last_crawled_at=excluded.last_crawled_at,
                        last_emitted=excluded.last_emitted,
                        last_status=excluded.last_status,
                        last_error=excluded.last_error,
                        updated_at=CURRENT_TIMESTAMP
                    """,
                    (
                        source_key,
                        source_id,
                        (base_url or "").strip(),
                        (config_type or "").strip(),
                        now_str,
                        int(emitted or 0),
                        safe_status,
                        safe_error,
                    ),
                )
                conn.commit()
                conn.close()
        except Exception:
            return

    def _load_source_policy(self) -> Dict[str, Any]:
        """读取本地 source_policy.yaml（若存在），用于过滤明显无效的链接/入口。"""
        defaults: Dict[str, Any] = {
            "deny_link_keywords": [
                "登录",
                "注册",
                "隐私",
                "政策",
                "新闻",
                "指南",
                "帮助",
                "下载",
                "附件",
            ],
            "deny_link_substrings": [
                "javascript:",
                "mailto:",
                "/login",
                "/register",
                "/help",
                "/about",
                "/privacy",
                "/policy",
            ],
        }

        policy_path = CONFIG_DIR / "source_policy.yaml"
        if not policy_path.exists():
            return defaults

        try:
            data = yaml.safe_load(policy_path.read_text(encoding="utf-8")) or {}
            if not isinstance(data, dict):
                return defaults
            merged = dict(defaults)
            merged.update(data)
            return merged
        except Exception:
            return defaults

    def _load_discovery_cache(self) -> Dict[str, Dict[str, Any]]:
        if not self.discovery_cache_file.exists():
            return {}
        try:
            data = json.loads(self.discovery_cache_file.read_text(encoding='utf-8'))
            if isinstance(data, dict):
                return data
        except Exception:
            pass
        return {}

    def _load_university_sources(self) -> List[Dict[str, str]]:
        try:
            data = yaml.safe_load(UNIVERSITY_SOURCES_FILE.read_text(encoding='utf-8')) or {}
        except Exception:
            try:
                data = json.loads(UNIVERSITY_SOURCES_FILE.read_text(encoding='utf-8'))
            except Exception:
                data = {}
        entries = data.get('universities', [])
        if not isinstance(entries, list):
            return []
        sanitized = []
        for item in entries:
            if not isinstance(item, dict):
                continue
            name = item.get('name')
            url = item.get('url')
            if name and url:
                sanitized.append({'name': str(name), 'url': str(url)})
        return sanitized

    def _save_discovery_cache(self) -> None:
        try:
            self.discovery_cache_file.write_text(
                json.dumps(self.discovery_cache, ensure_ascii=False, indent=2),
                encoding='utf-8'
            )
        except Exception as exc:
            self.logger.error("写入入口缓存失败: %s", exc)

    def _discovery_cache_key(self, url: str) -> str:
        """统一入口发现缓存的key，避免因 http/https 或尾部斜杠差异导致缓存失效。"""
        cleaned = self._clean_item_link(url)
        if not cleaned:
            return (url or "").strip()
        parsed = urlparse(cleaned)
        if not parsed.netloc:
            return cleaned

        scheme = parsed.scheme or "https"
        netloc = parsed.netloc.lower()
        path = parsed.path or "/"
        path = re.sub(r"/{2,}", "/", path)
        if path != "/" and path.endswith("/"):
            path = path.rstrip("/")
        return urlunparse(parsed._replace(scheme=scheme, netloc=netloc, path=path, params="", query="", fragment=""))

    def _get_cached_listings(self, base_url: str) -> List[str]:
        if not base_url:
            return []
        key = self._discovery_cache_key(base_url)
        entry = self.discovery_cache.get(key) or self.discovery_cache.get(base_url)
        if not entry:
            return []
        timestamp = entry.get('timestamp')
        listings = entry.get('listings') or []
        if not listings:
            return []
        if timestamp:
            try:
                ts = datetime.fromisoformat(timestamp)
                if (datetime.utcnow() - ts).days > max(self.discovery_cache_ttl, 1):
                    return []
            except ValueError:
                return []
        return [str(url) for url in listings if isinstance(url, str)]

    def _cache_listings(self, base_url: str, listings: List[str]) -> None:
        if not base_url or not listings:
            return
        key = self._discovery_cache_key(base_url)
        self.discovery_cache[key] = {
            'listings': listings,
            'timestamp': datetime.utcnow().isoformat()
        }
        self._save_discovery_cache()

    def _persist_entry_urls(self, source_id: str, entry_urls: List[str], source_config: Dict[str, Any]) -> None:
        """将发现到的入口列表页固化到 config/auto_sources.yaml，供下次直接使用。"""
        if not source_id or not entry_urls:
            return
        if source_config.get('config_type') != 'auto_discovered':
            return

        auto_sources_path = Path("config") / "auto_sources.yaml"
        if not auto_sources_path.exists():
            return

        # 去重并过滤非法URL
        cleaned: List[str] = []
        seen: set[str] = set()
        for url in entry_urls:
            if not isinstance(url, str):
                continue
            url = url.strip()
            if not url.startswith(('http://', 'https://')):
                continue
            if not self._looks_like_listing_url(url):
                continue
            if url in seen:
                continue
            seen.add(url)
            cleaned.append(url)

        if not cleaned:
            return

        with _AUTO_SOURCES_LOCK:
            try:
                data = yaml.safe_load(auto_sources_path.read_text(encoding='utf-8')) or {}
            except Exception as exc:
                self.logger.debug("读取 auto_sources.yaml 失败: %s", exc)
                return

            sources = data.get('sources', {})
            if not isinstance(sources, dict) or source_id not in sources:
                return
            current = sources.get(source_id)
            if not isinstance(current, dict):
                return

            existing = current.get('entry_urls', [])
            if isinstance(existing, list) and existing == cleaned:
                return

            current['entry_urls'] = cleaned
            current['entry_urls_updated_at'] = datetime.utcnow().isoformat()
            sources[source_id] = current
            data['sources'] = sources

            metadata = data.get('metadata', {}) or {}
            if isinstance(metadata, dict):
                metadata['last_updated'] = datetime.utcnow().isoformat()
                data['metadata'] = metadata

            try:
                auto_sources_path.write_text(
                    yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
                    encoding='utf-8'
                )
                self.logger.info("💾 已固化 %s 的列表入口: %s 条", source_id, len(cleaned))
            except Exception as exc:
                self.logger.debug("写入 auto_sources.yaml 失败: %s", exc)

    def _invalidate_cached_entry(self, base_url: str) -> None:
        if not base_url:
            return
        key = self._discovery_cache_key(base_url)
        if key in self.discovery_cache:
            self.discovery_cache.pop(key, None)
        if base_url in self.discovery_cache and base_url != key:
            self.discovery_cache.pop(base_url, None)
            self._save_discovery_cache()

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

    def _clean_item_link(self, link: Any) -> str:
        """清洗link用于存储/展示（不做激进改写，只去除 fragment / 空白）。"""
        if not link:
            return ''
        value = str(link).strip()
        if not value:
            return ''
        if value.startswith('//'):
            value = f"https:{value}"

        # 处理无 scheme 但看起来像域名的情况
        if '://' not in value and re.match(r'^[A-Za-z0-9.-]+\.[A-Za-z]{2,}(/|$)', value):
            value = f"http://{value}"

        parsed = urlparse(value)
        if not parsed.scheme or not parsed.netloc:
            return value
        return urlunparse(parsed._replace(fragment=''))

    def _strip_tracking_params(self, link: str) -> str:
        """移除常见跟踪参数（用于去重查询的补充变体），保留业务参数如 id/guid 等。"""
        if not link:
            return ''
        parsed = urlparse(link)
        if not parsed.query:
            return link
        kept = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=False) if k and k.lower() not in _TRACKING_QUERY_KEYS]
        if not kept:
            return urlunparse(parsed._replace(query=''))
        query = urlencode(sorted(kept), doseq=True)
        return urlunparse(parsed._replace(query=query))

    def _canonical_link_key(self, link: Any) -> str:
        """为去重生成稳定 key：忽略 scheme/fragment，过滤常见跟踪参数，统一 www/端口。"""
        cleaned = self._clean_item_link(link)
        if not cleaned:
            return ''
        parsed = urlparse(cleaned)
        if not parsed.netloc:
            return ''

        netloc = (parsed.netloc or '').lower()
        if '@' in netloc:
            netloc = netloc.rsplit('@', 1)[-1]
        if ':' in netloc:
            host, port = netloc.rsplit(':', 1)
            if port.isdigit():
                netloc = host
        if netloc.startswith('www.'):
            netloc = netloc[4:]

        path = parsed.path or '/'
        path = re.sub(r'/{2,}', '/', path)
        if path != '/' and path.endswith('/'):
            path = path.rstrip('/')

        params = [(k, v) for k, v in parse_qsl(parsed.query or '', keep_blank_values=False) if k and k.lower() not in _TRACKING_QUERY_KEYS]
        query = urlencode(sorted(params), doseq=True) if params else ''

        return f"{netloc}{path}" + (f"?{query}" if query else '')

    def _expand_link_variants(self, link: Any) -> List[str]:
        """生成少量等价URL变体，用于和本地已存link做比对（http/https, www, 去跟踪参数）。"""
        cleaned = self._clean_item_link(link)
        if not cleaned:
            return []
        parsed = urlparse(cleaned)
        if not parsed.scheme or not parsed.netloc:
            return [cleaned]

        bases = [cleaned]
        stripped = self._strip_tracking_params(cleaned)
        if stripped and stripped != cleaned:
            bases.append(stripped)

        schemes: List[str] = []
        for candidate in (parsed.scheme, 'http', 'https'):
            if candidate in {'http', 'https'} and candidate not in schemes:
                schemes.append(candidate)

        hosts: List[str] = []
        for candidate in (parsed.netloc, parsed.netloc.lower()):
            if candidate and candidate not in hosts:
                hosts.append(candidate)
        lower_host = parsed.netloc.lower()
        if lower_host.startswith('www.'):
            alt = lower_host[4:]
        else:
            alt = f"www.{lower_host}"
        if alt and alt not in hosts:
            hosts.append(alt)

        path = parsed.path or '/'
        path_variants = [path]
        if path != '/' and path.endswith('/'):
            path_variants.append(path.rstrip('/'))
        elif path != '/':
            path_variants.append(path + '/')

        variants: List[str] = []
        seen: set[str] = set()
        for base in bases:
            base_parsed = urlparse(base)
            for scheme in schemes:
                for host in hosts:
                    for p in path_variants:
                        variant = urlunparse(
                            base_parsed._replace(
                                scheme=scheme,
                                netloc=host,
                                path=p,
                                fragment='',
                            )
                        )
                        if variant in seen:
                            continue
                        seen.add(variant)
                        variants.append(variant)
                        if len(variants) >= 10:
                            return variants
        return variants

    def _generate_item_hash(self, item: Dict[str, Any]) -> str:
        """生成项目哈希值用于去重（基于稳定URL key，避免 http/https、utm 参数导致重复）。"""
        link_key = self._canonical_link_key(item.get('link', ''))
        if link_key:
            return hashlib.md5(link_key.encode('utf-8')).hexdigest()
        title = (item.get('title', '') or '').strip()
        source = (item.get('source', '') or '').strip()
        content = f"{title}|{source}"
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    def _is_duplicate_item(self, item: Dict[str, Any]) -> bool:
        """检查项目是否重复"""
        item_hash = self._generate_item_hash(item)
        link_variants = self._expand_link_variants(item.get('link', ''))

        try:
            with self._db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                cursor.execute('SELECT 1 FROM scraped_items_hash WHERE item_hash = ? LIMIT 1', (item_hash,))
                if cursor.fetchone() is not None:
                    conn.close()
                    return True

                # 额外比对本地已存link（兼容历史版本hash策略变化）
                if link_variants:
                    placeholders = ','.join(['?'] * len(link_variants))
                    cursor.execute(f'SELECT 1 FROM scraped_data WHERE link IN ({placeholders}) LIMIT 1', link_variants)
                    if cursor.fetchone() is not None:
                        conn.close()
                        return True

                conn.close()
                return False
        except Exception as e:
            self.logger.error(f"检查重复失败: {e}")
            return False

    # Crawl-session tracking hooks (disabled; kept for backward compatibility)
    def _start_crawl_session(self, url: str, session_id: Optional[str] = None) -> None:
        return None

    def _update_crawl_session(self, session_id: str, url: str, **kwargs) -> None:
        return None

    def _end_crawl_session(self, session_id: str, reason: str = "completed") -> None:
        return None

    def _save_item_hash(self, item: Dict[str, Any]):
        """保存项目哈希值"""
        item_hash = self._generate_item_hash(item)
        link = self._clean_item_link(item.get('link', ''))

        try:
            with self._db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO scraped_items_hash (item_hash, title, source, link)
                    VALUES (?, ?, ?, ?)
                ''', (item_hash, item.get('title', ''), item.get('source', ''), link))
                conn.commit()
                conn.close()
        except Exception as e:
            self.logger.error(f"保存哈希失败: {e}")

    def _save_raw_item(self, item: Dict[str, Any]):
        """将原始爬取结果写入数据库，供后续阶段使用"""
        link = self._clean_item_link(item.get('link', ''))
        if not link or not self._is_relevant_title(item.get('title', ''), link, item.get('source', '')):
            return

        try:
            with self._db_lock:
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
                    link,
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
        link = self._clean_item_link(item.get('link', ''))
        if not link or not item.get('detail_content'):
            return

        try:
            with self._db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                new_content = item.get('detail_content', '') or ''
                new_time = item.get('detail_scraped_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

                cursor.execute("SELECT detail_content, processed FROM scraped_data WHERE link = ? LIMIT 1", (link,))
                row = cursor.fetchone()
                existing_content = (row[0] or '') if row else ''

                if existing_content and existing_content == new_content:
                    # 内容未变化：不重置 processed，避免下次运行重复抽取/导出
                    cursor.execute(
                        "UPDATE scraped_data SET detail_scraped_at = ? WHERE link = ?",
                        (new_time, link),
                    )
                else:
                    # 内容有变化或原本为空：写入并标记为待处理
                    cursor.execute(
                        """
                        UPDATE scraped_data
                        SET detail_content = ?,
                            detail_scraped_at = ?,
                            processed = 0
                        WHERE link = ?
                        """,
                        (new_content, new_time, link),
                    )
                conn.commit()
                conn.close()
        except Exception as e:
            self.logger.error(f"保存详情内容失败: {e}")

    def mark_items_processed(self, item_ids: List[int]):
        """标记一批爬取的记录已完成联系人提取"""
        if not item_ids:
            return

        try:
            with self._db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                placeholders = ','.join(['?'] * len(item_ids))
                cursor.execute(f'''UPDATE scraped_data SET processed = 1 WHERE id IN ({placeholders})''', item_ids)
                conn.commit()
                conn.close()
        except Exception as e:
            self.logger.error(f"标记记录为已处理失败: {e}")

    def mark_links_processed(self, links: List[str]) -> None:
        """按 link 标记记录已处理（用于队列判定 irrelevant/失败后清理积压）。"""
        if not links:
            return
        cleaned: List[str] = []
        for link in links:
            value = self._clean_item_link(link)
            if value:
                cleaned.append(value)
        if not cleaned:
            return

        chunk_size = 800
        try:
            with self._db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                for start in range(0, len(cleaned), chunk_size):
                    chunk = cleaned[start : start + chunk_size]
                    placeholders = ",".join(["?"] * len(chunk))
                    cursor.execute(f"UPDATE scraped_data SET processed = 1 WHERE link IN ({placeholders})", chunk)
                conn.commit()
                conn.close()
        except Exception as e:
            self.logger.error(f"按 link 标记已处理失败: {e}")

    def _enforce_retention(self) -> Dict[str, int]:
        """按照配置清理过期或超限的数据。

        - `scraped_data`：仅清理 processed=1 的历史数据，避免误删待处理队列。
        - `scraped_items_hash`：默认跟随 `scraped_data_max_age_days`，可用 `scraped_items_hash_max_age_days` 单独控制。
        - `contacts`：若存在则清理已不在 scraped_data 中的联系人，避免数据库持续膨胀。
        """
        retention_config = settings.get("storage.retention", {}) or {}
        max_age_days = retention_config.get("scraped_data_max_age_days")
        max_records = retention_config.get("scraped_data_max_records")
        hash_max_age_days = retention_config.get("scraped_items_hash_max_age_days")

        deleted: Dict[str, int] = {
            "expired": 0,
            "overflow": 0,
            "hash_expired": 0,
            "contacts_orphaned": 0,
        }

        try:
            with self._db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                if max_age_days:
                    cutoff = (datetime.now() - timedelta(days=int(max_age_days))).strftime("%Y-%m-%d %H:%M:%S")
                    cursor.execute(
                        """
                        DELETE FROM scraped_data
                        WHERE processed = 1 AND datetime(COALESCE(detail_scraped_at, scraped_at)) < ?
                        """,
                        (cutoff,),
                    )
                    deleted["expired"] = max(cursor.rowcount, 0)

                if hash_max_age_days is None:
                    hash_max_age_days = max_age_days
                if hash_max_age_days:
                    cutoff = (datetime.now() - timedelta(days=int(hash_max_age_days))).strftime("%Y-%m-%d %H:%M:%S")
                    cursor.execute(
                        "DELETE FROM scraped_items_hash WHERE datetime(scraped_at) < ?",
                        (cutoff,),
                    )
                    deleted["hash_expired"] = max(cursor.rowcount, 0)

                if max_records:
                    cursor.execute("SELECT COUNT(*) FROM scraped_data")
                    total_records = cursor.fetchone()[0]
                    limit = int(max_records)
                    if total_records and total_records > limit:
                        excess = total_records - limit
                        cursor.execute(
                            """
                            SELECT id FROM scraped_data
                            WHERE processed = 1
                            ORDER BY datetime(COALESCE(detail_scraped_at, scraped_at)) ASC
                            LIMIT ?
                            """,
                            (excess,),
                        )
                        ids = [row[0] for row in cursor.fetchall()]

                        if len(ids) < excess:
                            remaining = excess - len(ids)
                            cursor.execute(
                                """
                                SELECT id FROM scraped_data
                                WHERE processed = 0
                                ORDER BY datetime(COALESCE(detail_scraped_at, scraped_at)) ASC
                                LIMIT ?
                                """,
                                (remaining,),
                            )
                            ids.extend([row[0] for row in cursor.fetchall()])

                        if ids:
                            cursor.execute(
                                f"DELETE FROM scraped_data WHERE id IN ({','.join('?' for _ in ids)})",
                                ids,
                            )
                            deleted["overflow"] = max(cursor.rowcount, 0)

                try:
                    cursor.execute(
                        """
                        DELETE FROM contacts
                        WHERE link IS NOT NULL AND link != ''
                          AND link NOT IN (SELECT link FROM scraped_data)
                        """
                    )
                    deleted["contacts_orphaned"] = max(cursor.rowcount, 0)
                except Exception:
                    deleted["contacts_orphaned"] = 0

                conn.commit()
                conn.close()
        except Exception as e:
            self.logger.error(f"执行保留策略失败: {e}")

        self.last_retention_stats = deleted
        return deleted

    def _is_relevant_title(self, title: str, url: str = "", source: str = "") -> bool:
        if not title:
            return False
        stripped = title.strip()
        if not stripped:
            return False

        filters = settings.get("scraper.filters", {}) or {}
        exclude_keywords = filters.get("exclude_keywords", []) or []
        if any(k and str(k) in stripped for k in exclude_keywords):
            return False

        # 白名单关键词（业务关键词来自 config/keywords.yaml）
        if title_hit(stripped):
            return True

        include_keywords = filters.get("include_keywords", []) or []
        if include_keywords and any(k and str(k) in stripped for k in include_keywords):
            return True

        # 兜底：公告/招标类标题（用于确保基础数据不被过度过滤）
        if any(k in stripped for k in AWARD_TITLE_KEYWORDS):
            return True
        if any(k in stripped for k in GENERIC_KEYWORDS):
            return True

        return False

    def _should_follow_link(self, url: str, patterns: List[str]) -> bool:
        """判断是否应该跟踪链接，结合URL模式和基础排除规则"""
        if not patterns:
            return True

        # 首先检查是否匹配基本模式
        pattern_match = any(pattern in url for pattern in patterns if pattern)
        if not pattern_match:
            return False

        # 排除明确的新闻、指南和服务页面
        exclude_patterns = [
            '/xwzx/',      # 新闻资讯
            '/bszn/',      # 办事指南
            '/fwzn/',      # 服务指南
            '/zcjd/',      # 政策解读
            '/tjsj/',      # 统计数据
            '/gxhz/',      # 合作互助
            '/hygl/',      # 会员管理
            '/huiyuan',    # 会员注册
            '/PSPBidder',  # 投标系统
            '/BigFileUp',  # 文件下载
            '/news/',      # 新闻
            '/guide/',     # 指南
            '/help/',      # 帮助
            '/service/',   # 服务
            '/info/',      # 信息（非采购）
            '/about/',     # 关于
            '/contact/',   # 联系（非采购）
        ]

        url_lower = url.lower()
        if any(pattern in url_lower for pattern in exclude_patterns):
            self.logger.debug(f"链接被排除模式拒绝: {url[:100]}...")
            return False

        return True

    def _should_skip_discovery_link(self, text: str, link: str, source_config: Dict[str, Any]) -> bool:
        if not link:
            return True
        discovery_cfg = source_config.get('discovery') if isinstance(source_config.get('discovery'), dict) else {}
        deny_keywords = set(self.deny_link_keywords)
        deny_keywords.update(str(item) for item in discovery_cfg.get('deny_keywords', []) if item)
        deny_substrings = set(self.deny_link_substrings)
        deny_substrings.update(str(item).lower() for item in discovery_cfg.get('deny_patterns', []) if item)
        lower_link = link.lower()
        if any(pattern and pattern in lower_link for pattern in deny_substrings):
            return True
        if text:
            stripped = text.strip()
            if any(keyword and keyword in stripped for keyword in deny_keywords):
                return True
        else:
            return True
        if len(text) <= 1:
            return True
        return False

    def _discover_source_entries(self, source_id: str, base_url: str, config: Dict[str, Any]) -> List[str]:
        if not base_url:
            return []
        entry_urls = config.get('entry_urls')
        if isinstance(entry_urls, list) and entry_urls:
            original_valid: List[str] = []
            sanitized: List[str] = []
            for url in entry_urls:
                if not isinstance(url, str):
                    continue
                if not url.startswith(('http://', 'https://')):
                    continue
                original_valid.append(url)
                if self._looks_like_listing_url(url):
                    sanitized.append(url)
            if sanitized:
                # 入口自愈：若历史 entry_urls 混入详情页/异常链接，则自动回写修正
                if original_valid != sanitized:
                    self._persist_entry_urls(source_id, sanitized, config)
                return sanitized
        cached = self._get_cached_listings(base_url)
        if cached:
            # 缓存命中时也尝试固化到 auto_sources.yaml（避免“只缓存不落盘”导致下次仍重复探测）
            if config.get('config_type') == 'auto_discovered':
                self._persist_entry_urls(source_id, cached, config)
            return cached
        discovery_overrides = config.get('discovery') if isinstance(config.get('discovery'), dict) else {}
        max_depth = int(discovery_overrides.get('max_depth', self.discovery_config.get('max_depth', 2)))
        max_entries = int(discovery_overrides.get('max_entries', self.discovery_config.get('max_entries', 3)))
        max_links_per_page = int(discovery_overrides.get('max_links_per_page', self.discovery_config.get('max_links_per_page', 80)))
        discovered = self._run_discovery(
            base_url,
            max_depth=max_depth,
            max_entries=max_entries,
            max_links_per_page=max_links_per_page,
            source_id=source_id,
            source_config=config
        )

        if not discovered:
            # HTML 入口探测失败时（如菜单由 JS 渲染/SPA），尝试站内搜索兜底，优先找“中标/成交/结果”列表页。
            domain = urlparse(base_url).netloc
            if domain:
                candidate_queries = [
                    "中标（成交）结果公告",
                    "中标 成交 结果 公告",
                    "成交 公告 列表",
                    "中标 公告 列表",
                    "结果 公告 列表",
                    "index_1.html 成交公告",
                    "index_1.html 中标公告",
                    "result-notice",
                ]
                candidates: List[str] = []
                for query in candidate_queries:
                    candidates.extend(self._duckduckgo_site_search(domain, query, max_links=30))

                scored: List[Tuple[str, int]] = []
                seen_candidate: set[str] = set()
                for url in candidates:
                    if not url or not isinstance(url, str):
                        continue
                    if url in seen_candidate:
                        continue
                    seen_candidate.add(url)
                    candidate_domain = urlparse(url).netloc.lower()
                    if candidate_domain:
                        # 站内搜索一般不会越域，但仍做一次防御（允许 www / 子域差异）
                        if (
                            candidate_domain != domain.lower()
                            and not candidate_domain.endswith("." + domain.lower())
                            and not domain.lower().endswith("." + candidate_domain)
                        ):
                            continue
                    if not self._looks_like_listing_url(url):
                        continue
                    score = self._score_listing_candidate_url(url)
                    if score <= 0:
                        continue
                    scored.append((url, score))

                scored.sort(key=lambda item: item[1], reverse=True)
                local_discovery = config.get('discovery') if isinstance(config.get('discovery'), dict) else {}
                max_site_candidates = int(local_discovery.get('max_site_search_candidates', 20))
                for url, _score in scored[:max_site_candidates]:
                    if url in discovered:
                        continue
                    if self._is_valid_listing_page(url, domain, config):
                        discovered.append(url)
                        if len(discovered) >= max_entries:
                            break

        if discovered:
            self.logger.info(f"✅ 发现 {len(discovered)} 个有效入口")
            self._cache_listings(base_url, discovered)
            self._persist_entry_urls(source_id, discovered, config)
        else:
            source_name = config.get('name', source_id)
            self.logger.warning(f"⚠️  {source_name} 未发现有效入口页面")
            self.logger.info(f"   follow_patterns: {config.get('follow_patterns', [])}")
            # 尝试使用base_url作为入口
            self.logger.info(f"   尝试使用base_url作为入口: {base_url}")
            discovered = [base_url]
            # 兜底入口也写入缓存/固化，避免下次运行重复触发站内搜索/入口探测
            self._cache_listings(base_url, discovered)
            self._persist_entry_urls(source_id, discovered, config)
        return discovered

    def _run_discovery(
        self,
        base_url: str,
        *,
        max_depth: int,
        max_entries: int,
        max_links_per_page: int,
        source_id: str,
        source_config: Dict[str, Any]
    ) -> List[str]:
        queue = deque([(base_url, 0)])
        visited: set[str] = set()
        entries: List[str] = []
        base_domain = urlparse(base_url).netloc
        keyword_set = set(keywords())

        # 保存source_config供后续使用
        self.current_source_config = source_config

        while queue and len(entries) < max_entries:
            current_url, depth = queue.popleft()
            normalized = _normalize_url(current_url)
            if normalized in visited or depth > max_depth:
                continue
            visited.add(normalized)
            try:
                response = self._fetch_with_metrics(normalized, source_id or 'discovery')
            except Exception as exc:
                self.logger.debug("入口探测失败 %s: %s", normalized, exc)
                continue
            soup = BeautifulSoup(response.text, 'lxml')
            anchors = soup.find_all('a', href=True)
            scored_links: List[Tuple[str, int]] = []
            follow_patterns = source_config.get('follow_patterns', []) if isinstance(source_config, dict) else []
            follow_patterns_lower = [str(p).lower() for p in follow_patterns if p]
            # 优先挑选命中 follow_patterns 的“列表页”链接（即使它们不在页面前N个链接里）
            prioritized_listing: List[Any] = []
            prioritized_follow: List[Any] = []
            if follow_patterns_lower:
                for anchor in anchors:
                    href = anchor.get('href')
                    if not href:
                        continue
                    href_lower = str(href).lower()
                    if not any(pattern in href_lower for pattern in follow_patterns_lower):
                        continue
                    anchor_text = anchor.get_text(strip=True)
                    looks_like_listing = (
                        'index_' in href_lower
                        or '/index' in href_lower
                        or href_lower.endswith('/')
                        or ('更多' in anchor_text)
                    )
                    if looks_like_listing:
                        prioritized_listing.append(anchor)
                    else:
                        prioritized_follow.append(anchor)
            prioritized_anchors: List[Any] = prioritized_listing + prioritized_follow

            selected_anchors: List[Any] = []
            seen_anchor_ids: set[int] = set()
            for anchor in prioritized_anchors + anchors:
                anchor_id = id(anchor)
                if anchor_id in seen_anchor_ids:
                    continue
                seen_anchor_ids.add(anchor_id)
                selected_anchors.append(anchor)
                if len(selected_anchors) >= max_links_per_page:
                    break

            for anchor in selected_anchors:
                href = anchor.get('href')
                if not href:
                    continue
                raw_link = urljoin(normalized, href)
                link = _normalize_url(raw_link)
                if not link:
                    continue
                if link == normalized:
                    continue
                if urlparse(link).netloc != base_domain:
                    continue
                anchor_text = anchor.get_text(strip=True)
                if self._should_skip_discovery_link(anchor_text, link, source_config):
                    continue
                score = self._score_anchor(anchor_text, link, keyword_set)
                if score > 0:
                    scored_links.append((link, score))
            scored_links.sort(key=lambda item: item[1], reverse=True)
            local_discovery = source_config.get('discovery') if isinstance(source_config.get('discovery'), dict) else {}
            max_child_links = int(local_discovery.get('max_child_links', self.discovery_config.get('max_child_links', 10)))
            for link, _score in scored_links[:max_child_links]:
                if link in visited or link in entries:
                    continue
                if self._is_valid_listing_page(link, base_domain, source_config):
                    if not self._looks_like_listing_url(link):
                        if depth + 1 <= max_depth:
                            queue.append((link, depth + 1))
                        continue
                    entries.append(link)
                    if len(entries) >= max_entries:
                        break
                elif depth + 1 <= max_depth:
                    queue.append((link, depth + 1))
        return entries

    def _score_anchor(self, text: str, link: str, keyword_set: set[str]) -> int:
        if not text:
            return 0
        score = 0
        lower_text = text.lower()

        # 检查URL是否在follow_patterns中
        follow_patterns = getattr(self, 'current_source_config', {}).get('follow_patterns', [])
        # 如果没有配置follow_patterns，则不进行此项过滤
        if follow_patterns and not any(pattern in link for pattern in follow_patterns):
            # 不直接返回0，而是降低分数而不是完全排除
            pass

        # 检查是否在排除列表中
        exclude_patterns = [
            '/xwzx/',      # 新闻资讯
            '/bszn/',      # 办事指南
            '/fwzn/',      # 服务指南
            '/zcjd/',      # 政策解读
            '/tjsj/',      # 统计数据
            '/gxhz/',      # 合作互助
            '/hygl/',      # 会员管理
            '/huiyuan',    # 会员注册
            '/PSPBidder',  # 投标系统
            '/BigFileUp',  # 文件下载
            '/news/',      # 新闻
            '/guide/',     # 指南
            '/help/',      # 帮助
            '/service/',   # 服务
            '/info/',      # 信息（非采购）
            '/about/',     # 关于
            '/contact/',   # 联系（非采购）
        ]

        link_lower = link.lower()
        if any(pattern in link_lower for pattern in exclude_patterns):
            return 0  # 排除的链接得分为0

        # 评分系统
        patterns = ['中标', '成交', '公告', '结果', '投标', 'award', 'result', 'bid', 'notice']
        for token in patterns:
            if token in text or token in lower_text:
                score += 2
                break
        if any(keyword in text for keyword in keyword_set):
            score += 1
        link_tokens = ['cjgg', 'zbgg', 'gonggao', 'result', 'award', 'win', 'bid', 'notice']
        if any(token in link_lower for token in link_tokens):
            score += 1

        # 省级政府采购站（ccgp-*）常见栏目：优先成交/中标等结果类列表
        preferred_tokens = {
            'hbgg': 3,   # 成交公告（如 pzhbgg/czhbgg）
            'cjgg': 2,   # 成交公告
            'zbgg': 2,   # 中标/招标公告（站点命名差异较大）
            'gkzb': 1,   # 公开招标
            'jzxtpgg': 1,  # 竞争性谈判
            'jzxcs': 1,  # 竞争性磋商
        }
        for token, weight in preferred_tokens.items():
            if token in link_lower:
                score += weight
                break

        # 列表页常见命名
        if 'index_' in link_lower or '/index' in link_lower:
            score += 2

        # 详情页常见命名（降低权重，避免把详情页当入口）
        detail_markers = ('/t202', '/202', '/detail', '/content', '/article')
        if link_lower.endswith(('.html', '.htm')) and any(marker in link_lower for marker in detail_markers) and 'index' not in link_lower:
            score -= 2
            if score <= 0:
                return 0

        # 优先匹配follow_patterns
        for pattern in follow_patterns:
            if pattern in link_lower:
                score += 3  # 给予更高分数
                break

        return score

    def _is_valid_listing_page(self, url: str, base_domain: str, source_config: Dict[str, Any]) -> bool:
        local_discovery = source_config.get('discovery') if isinstance(source_config.get('discovery'), dict) else {}
        enable_playwright = bool(local_discovery.get('enable_playwright_validation', True))

        try:
            response = self._fetch_with_metrics(url, 'discovery-list')
        except Exception:
            if enable_playwright and self._looks_like_listing_url(url):
                return self._is_valid_listing_page_playwright(url, base_domain)
            return False
        soup = BeautifulSoup(response.text, 'lxml')
        anchors = soup.find_all('a', href=True)
        candidates: List[Dict[str, str]] = []
        award_keywords = ['中标', '成交', '结果', '公告', '中标候选人', '中标公示', '成交公告']

        for anchor in anchors[:80]:
            title = anchor.get_text(strip=True)
            if not title or len(title) < 6:
                continue
            href = anchor.get('href')
            if not href:
                continue
            link = urljoin(url, href)
            if urlparse(link).netloc != base_domain:
                continue
            if self._should_skip_discovery_link(title, link, source_config):
                continue
            # 放宽标题检查，只要是相关公告即可
            if any(keyword in title for keyword in award_keywords):
                candidates.append({'title': title, 'link': link})

        # 降低门槛，只要有3个相关链接就认为是有效的列表页
        if len(candidates) < 3:
            if not enable_playwright:
                return False
            if not self._looks_like_listing_url(url):
                return False
            html = response.text or ""
            maybe_spa = (
                "<base " in html
                or "ng-app" in html
                or "ng-controller" in html
                or "webpack" in html
                or len(html) < 15000
            )
            if maybe_spa:
                return self._is_valid_listing_page_playwright(url, base_domain)
            return False

        # 检查页面标题是否包含相关关键词
        page_title = soup.title.get_text(strip=True) if soup.title else ''
        page_title_lower = page_title.lower()
        if any(keyword in page_title or keyword in page_title_lower
               for keyword in ['公告', '中标', '采购', '交易', '公示']):
            return True

        # 如果页面标题不相关，但有足够的候选链接，也认为是有效的
        return len(candidates) >= 5

    def _is_valid_listing_page_playwright(self, url: str, base_domain: str) -> bool:
        """对疑似 SPA/JS 渲染站点，用 Playwright 渲染后再判定是否为“公告列表页”。

        目标：只在 HTTP 解析无法确认时兜底，避免把详情页/门户页误固化到 entry_urls。
        """
        if not url:
            return False
        try:
            from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
            from playwright.sync_api import sync_playwright
        except Exception:
            return False

        user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )

        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent=user_agent,
                    locale="zh-CN",
                    timezone_id="Asia/Shanghai",
                    viewport={"width": 1280, "height": 720},
                )
                page = context.new_page()
                ok = False
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=30_000)

                    award_keywords = ['中标', '成交', '结果', '公告', '中标候选人', '中标公示', '成交公告']
                    # 等待页面渲染出足够的“公告类”链接（避免固定 sleep 造成偶发误判）
                    try:
                        page.wait_for_function(
                            """(keywords) => {
                                const anchors = Array.from(document.querySelectorAll('a'));
                                let count = 0;
                                for (const a of anchors) {
                                    const text = (a.innerText || a.textContent || '').trim();
                                    if (!text || text.length < 6) continue;
                                    if (!keywords.some(k => text.includes(k))) continue;
                                    const href = (a.getAttribute('href') || '').trim();
                                    const hrefOk = href && !href.startsWith('javascript');
                                    const clickOk = a.getAttribute('ng-click') || a.getAttribute('onclick') || a.getAttribute('data-href');
                                    if (!hrefOk && !clickOk) continue;
                                    count += 1;
                                    if (count >= 3) return true;
                                }
                                return false;
                            }""",
                            arg=award_keywords,
                            timeout=8_000,
                        )
                    except PlaywrightTimeoutError:
                        # 兜底：给少量渲染时间
                        page.wait_for_timeout(2500)

                    candidates = page.evaluate(
                        """({ keywords, domain }) => {
                            const anchors = Array.from(document.querySelectorAll('a'));
                            const results = [];
                            for (const a of anchors) {
                                const text = (a.innerText || a.textContent || '').trim();
                                if (!text || text.length < 6) continue;
                                if (!keywords.some(k => text.includes(k))) continue;
                                const href = (a.getAttribute('href') || '').trim();
                                const hrefOk = href && !href.startsWith('javascript');
                                const clickOk = a.getAttribute('ng-click') || a.getAttribute('onclick') || a.getAttribute('data-href');
                                if (!hrefOk && !clickOk) continue;
                                if (hrefOk) {
                                    try {
                                        const u = new URL(href, location.href);
                                        if (domain && u.host !== domain) continue;
                                    } catch (e) {
                                        continue;
                                    }
                                }
                                results.push(text);
                                if (results.length >= 10) break;
                            }
                            return results;
                        }""",
                        {"keywords": award_keywords, "domain": base_domain},
                    )

                    if not isinstance(candidates, list) or len(candidates) < 3:
                        ok = False
                    else:
                        title = page.title() or ""
                        try:
                            body_text = page.inner_text("body") or ""
                        except Exception:
                            body_text = ""
                        combined = f"{title} {body_text[:2000]}".strip()
                        ok = (
                            not combined
                            or any(token in combined for token in ("公告", "中标", "成交", "结果", "采购", "交易", "公示"))
                        )
                except PlaywrightTimeoutError:
                    ok = False
                finally:
                    try:
                        context.close()
                    except Exception:
                        pass
                    try:
                        browser.close()
                    except Exception:
                        pass

                return ok
        except Exception:
            return False

    def _extract_listing_items_playwright(
        self,
        entry_url: str,
        *,
        keywords_list: List[str],
        base_domain: str,
        source_name: str,
        source_config: Dict[str, Any],
        max_items: int,
    ) -> List[Dict[str, Any]]:
        """对 SPA/JS 渲染的列表页，用 Playwright 抽取条目与详情链接。"""
        if not entry_url or max_items <= 0:
            return []
        try:
            from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
            from playwright.sync_api import sync_playwright
        except Exception:
            return []

        # 以“中标/成交/结果”类公告为主，避免在动态门户页抓到无关导航链接
        keyword_candidates = [k for k in (keywords_list or []) if isinstance(k, str) and k]
        keyword_hints = [k for k in keyword_candidates if k in AWARD_TITLE_KEYWORDS]
        if not keyword_hints:
            keyword_hints = list(AWARD_TITLE_KEYWORDS)

        user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )

        items: List[Dict[str, Any]] = []

        def _build_item(title: str, link: str, raw: str) -> Dict[str, Any]:
            return {
                'title': self._normalize_encoding(title),
                'link': link,
                'source': source_name,
                'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'publish_date': None,
                'raw_content': raw,
                # 列表页已证明需要 JS 渲染，详情页大概率同样需要
                'render_mode': 'playwright',
            }

        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent=user_agent,
                    locale="zh-CN",
                    timezone_id="Asia/Shanghai",
                    viewport={"width": 1280, "height": 720},
                )
                page = context.new_page()

                try:
                    page.goto(entry_url, wait_until="domcontentloaded", timeout=30_000)
                except PlaywrightTimeoutError:
                    return []

                # 等待列表数据渲染出来
                try:
                    page.wait_for_function(
                        """(keywords) => {
                            const anchors = Array.from(document.querySelectorAll('a'));
                            let count = 0;
                            for (const a of anchors) {
                                const text = (a.innerText || a.textContent || '').trim();
                                if (!text || text.length < 6) continue;
                                if (!keywords.some(k => text.includes(k))) continue;
                                count += 1;
                                if (count >= 5) return true;
                            }
                            return false;
                        }""",
                        arg=keyword_hints,
                        timeout=10_000,
                    )
                except PlaywrightTimeoutError:
                    page.wait_for_timeout(2500)

                # 1) 先抽取带 href 的真实链接（无需点击）
                domain = (base_domain or "").lower()
                domain_alt = domain[4:] if domain.startswith("www.") else (f"www.{domain}" if domain else "")
                direct_links = page.evaluate(
                    """({ keywords, domain, domainAlt, limit }) => {
                        const anchors = Array.from(document.querySelectorAll('a'));
                        const results = [];
                        for (const a of anchors) {
                            const text = (a.innerText || a.textContent || '').trim();
                            if (!text || text.length < 6) continue;
                            if (keywords && keywords.length && !keywords.some(k => text.includes(k))) continue;
                            const href = (a.getAttribute('href') || '').trim();
                            if (!href || href.startsWith('javascript')) continue;
                            let u;
                            try { u = new URL(href, location.href); } catch (e) { continue; }
                            if (domain && u.host !== domain && u.host !== domainAlt) continue;
                            results.push({ title: text, link: u.toString() });
                            if (results.length >= limit) break;
                        }
                        return results;
                    }""",
                    {"keywords": keyword_hints, "domain": domain, "domainAlt": domain_alt, "limit": min(max_items, 60)},
                )
                if isinstance(direct_links, list):
                    for row in direct_links:
                        if len(items) >= max_items:
                            break
                        if not isinstance(row, dict):
                            continue
                        title = str(row.get("title", "")).strip()
                        link = self._clean_item_link(str(row.get("link", "")).strip())
                        if not title or not link:
                            continue
                        if not link.startswith(('http://', 'https://')):
                            continue
                        if self._should_skip_discovery_link(title, link, source_config):
                            continue
                        if not self._is_relevant_title(title, link, source_name):
                            continue
                        items.append(_build_item(title, link, raw=str(row)))

                if len(items) >= max_items:
                    return items

                # 2) 对无 href 的可点击条目（如 ng-click）通过弹窗/跳转捕获详情URL
                candidate_indexes = page.evaluate(
                    """({ keywords, limit }) => {
                        const anchors = Array.from(document.querySelectorAll('a'));
                        const results = [];
                        for (let i = 0; i < anchors.length; i++) {
                            const a = anchors[i];
                            const text = (a.innerText || a.textContent || '').trim();
                            if (!text || text.length < 6) continue;
                            if (keywords && keywords.length && !keywords.some(k => text.includes(k))) continue;
                            const href = (a.getAttribute('href') || '').trim();
                            const hrefOk = href && !href.startsWith('javascript');
                            const clickOk = a.getAttribute('ng-click') || a.getAttribute('onclick') || a.getAttribute('data-href');
                            if (!hrefOk && !clickOk) continue;
                            results.push(i);
                            if (results.length >= limit) break;
                        }
                        return results;
                    }""",
                    {"keywords": keyword_hints, "limit": min(max_items * 8, 80)},
                )

                if not isinstance(candidate_indexes, list):
                    candidate_indexes = []

                base_domain_norm = (base_domain or "").lower()
                if base_domain_norm.startswith("www."):
                    base_domain_norm = base_domain_norm[4:]

                seen_links: set[str] = {item.get("link") for item in items if item.get("link")}
                for i in candidate_indexes:
                    if len(items) >= max_items:
                        break
                    el = page.locator("a").nth(int(i))
                    try:
                        title = (el.inner_text() or "").strip()
                    except Exception:
                        continue
                    if not title or len(title) < 6:
                        continue
                    if keyword_hints and not any(k in title for k in keyword_hints):
                        continue

                    # 若本身带可用 href，则直接使用（避免点击）
                    try:
                        href = (el.get_attribute("href") or "").strip()
                    except Exception:
                        href = ""
                    link = ""
                    if href and not href.startswith("javascript"):
                        link = urljoin(entry_url, href)
                    else:
                        before = page.url
                        # 站点常用打开新 tab 的方式展示详情（优先捕获 popup）
                        try:
                            with page.expect_popup(timeout=8_000) as popup_info:
                                el.click()
                            popup = popup_info.value
                            try:
                                popup.wait_for_load_state("domcontentloaded", timeout=8_000)
                            except PlaywrightTimeoutError:
                                pass
                            link = popup.url
                            try:
                                popup.close()
                            except Exception:
                                pass
                        except PlaywrightTimeoutError:
                            try:
                                el.click()
                            except Exception:
                                link = ""
                            else:
                                page.wait_for_timeout(800)
                                if page.url != before:
                                    link = page.url
                                    try:
                                        page.go_back(timeout=10_000)
                                    except Exception:
                                        pass

                    link = self._clean_item_link(link)
                    if not link or link in seen_links:
                        continue
                    link_domain_norm = (urlparse(link).netloc or "").lower()
                    if link_domain_norm.startswith("www."):
                        link_domain_norm = link_domain_norm[4:]
                    if base_domain_norm and link_domain_norm:
                        if (
                            link_domain_norm != base_domain_norm
                            and not link_domain_norm.endswith("." + base_domain_norm)
                            and not base_domain_norm.endswith("." + link_domain_norm)
                        ):
                            continue
                    if self._should_skip_discovery_link(title, link, source_config):
                        continue
                    if not self._is_relevant_title(title, link, source_name):
                        continue
                    seen_links.add(link)
                    items.append(_build_item(title, link, raw=f"clickable:{int(i)}"))

                return items
        except Exception:
            return []

    def _crawl_listing(self, entry_url: str, config: Dict[str, Any], source_id: str, base_url: Optional[str] = None):
        max_pages = int(config.get('max_pages', 5))
        max_items = int(config.get('max_items', 100))
        keywords_list = config.get('keywords') or GENERIC_KEYWORDS
        source_name = config.get('name') or entry_url
        base_domain = urlparse(entry_url).netloc
        performance_config = settings.get('scraper.performance', {}) or {}
        stop_after_no_new_pages = config.get('stop_after_no_new_pages', performance_config.get('stop_after_no_new_pages', 2))
        try:
            stop_after_no_new_pages = int(stop_after_no_new_pages)
        except Exception:  # noqa: BLE001
            stop_after_no_new_pages = 2
        stop_after_no_new_pages = max(stop_after_no_new_pages, 0)
        visited_pages: set[str] = set()
        page_count = 0
        emitted = 0
        consecutive_no_new_pages = 0
        current_url = entry_url

        # 使用会话管理跟踪爬取行为
        session_id = f"{source_id}_{base_domain}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        session = self._start_crawl_session(entry_url, session_id)

        try:
            while current_url and page_count < max_pages and emitted < max_items:
                normalized = _normalize_url(current_url)
                if normalized in visited_pages:
                    break
                visited_pages.add(normalized)

                try:
                    response = self._fetch_with_metrics(normalized, source_id)
                    # 更新会话（成功）
                    self._update_crawl_session(
                        session_id, normalized,
                        success=True,
                        size=len(response.text) if response.text else 0
                    )
                except Exception as exc:
                    # 更新会话（失败）
                    self._update_crawl_session(
                        session_id, normalized,
                        success=False,
                        error=str(exc)
                    )
                    self.logger.error("爬取列表页 %s 失败: %s", normalized, exc)
                    break

                soup = BeautifulSoup(response.text, 'lxml')
                items = self._extract_generic_items(
                    soup,
                    normalized,
                    keywords_list,
                    base_domain,
                    source_name,
                    config
                )
                used_playwright_listing = False
                if not items:
                    # SPA/JS 渲染列表页：HTTP 抓取往往没有 href，尝试 Playwright 兜底抽取
                    items = self._extract_listing_items_playwright(
                        normalized,
                        keywords_list=keywords_list,
                        base_domain=base_domain,
                        source_name=source_name,
                        source_config=config,
                        max_items=max(0, max_items - emitted),
                    )
                    used_playwright_listing = bool(items)
                new_items_this_page = 0
                for item in items:
                    if emitted >= max_items:
                        break
                    if self._is_duplicate_item(item):
                        continue
                    self._save_item_hash(item)
                    self._save_raw_item(item)
                    emitted += 1
                    new_items_this_page += 1
                    yield item

                if items and new_items_this_page == 0 and stop_after_no_new_pages:
                    consecutive_no_new_pages += 1
                    if consecutive_no_new_pages >= stop_after_no_new_pages:
                        self.logger.info(
                            "列表页无新增（%s 连续 %s 页），提前结束翻页: %s",
                            source_name,
                            consecutive_no_new_pages,
                            entry_url,
                        )
                        break
                else:
                    consecutive_no_new_pages = 0

                current_url = None if used_playwright_listing else self._find_next_page(soup, normalized)
                page_count += 1

            # 结束会话
            reason = "completed" if emitted > 0 else "no_items"
            self._end_crawl_session(session_id, reason)

        except Exception as e:
            # 确保会话被正确结束
            self._end_crawl_session(session_id, "error")
            raise

        if emitted == 0 and base_url:
            self._invalidate_cached_entry(base_url)

    def scrape_all_sources(self) -> Generator[Dict[str, Any], None, None]:
        """爬取所有启用的数据源"""
        # 检查是否启用并发爬取
        performance_config = settings.get('scraper.performance', {}) or {}
        enable_concurrent = performance_config.get('enable_concurrent_sources', False)

        if enable_concurrent:
            # 使用并发爬取
            yield from self._scrape_sources_concurrent()
        else:
            # 使用原有的串行爬取（保持向后兼容）
            yield from self._scrape_sources_serial()

    def _order_sources(self, sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """对数据源做轻量排序/轮换，避免每次都从同一批源开始。"""
        if not sources:
            return []
        sources_copy = list(sources)
        # 优先保留推荐源在前，其余按“每日固定随机”洗牌
        recommended = [s for s in sources_copy if s.get('config_type') == 'recommended']
        others = [s for s in sources_copy if s.get('config_type') != 'recommended']
        seed = datetime.utcnow().strftime('%Y-%m-%d')
        rng = random.Random(seed)
        rng.shuffle(others)
        return recommended + others

    def _get_sources_for_scraper(self) -> List[Dict[str, Any]]:
        """汇总 user_config + auto_sources.yaml 的启用数据源，并做基础去重。"""
        if self._sources_cache is not None:
            return list(self._sources_cache)

        user_sources = settings.get("scraper.sources", {}) or {}
        if not isinstance(user_sources, dict):
            user_sources = {}

        auto_sources_path = CONFIG_DIR / "auto_sources.yaml"
        auto_sources: Dict[str, Any] = {}
        if auto_sources_path.exists():
            try:
                data = yaml.safe_load(auto_sources_path.read_text(encoding="utf-8")) or {}
                if isinstance(data, dict) and isinstance(data.get("sources"), dict):
                    auto_sources = data["sources"] or {}
            except Exception:
                auto_sources = {}

        merged: Dict[str, Dict[str, Any]] = {}
        for source_id, cfg in auto_sources.items():
            if isinstance(cfg, dict):
                merged[str(source_id)] = cfg
        for source_id, cfg in user_sources.items():
            if isinstance(cfg, dict):
                merged[str(source_id)] = cfg

        sources: List[Dict[str, Any]] = []
        for source_id, cfg in merged.items():
            enabled = bool(cfg.get("enabled", False))
            if not enabled:
                continue
            base_url = (cfg.get("base_url") or cfg.get("url") or "").strip()
            if not base_url:
                continue
            delay_min = cfg.get("delay_min", 3)
            delay_max = cfg.get("delay_max", 8)
            config_type = cfg.get("config_type")
            if not config_type:
                config_type = "user" if source_id in user_sources else "auto_discovered"

            follow_patterns = cfg.get("follow_patterns", [])
            if not isinstance(follow_patterns, list):
                follow_patterns = []

            entry_urls = cfg.get("entry_urls", [])
            if not isinstance(entry_urls, list):
                entry_urls = []

            sources.append(
                {
                    "source_id": source_id,
                    "name": (cfg.get("name") or source_id),
                    "url": base_url,
                    "delay_min": delay_min,
                    "delay_max": delay_max,
                    "config_type": config_type,
                    "follow_patterns": [str(p) for p in follow_patterns if p],
                    "entry_urls": [str(u) for u in entry_urls if u],
                }
            )

        def _dedupe_list(values: List[str]) -> List[str]:
            seen: set[str] = set()
            out: List[str] = []
            for value in values:
                value = (value or "").strip()
                if not value or value in seen:
                    continue
                seen.add(value)
                out.append(value)
            return out

        deduped_by_url: Dict[str, Dict[str, Any]] = {}
        for source in sources:
            key = self._canonical_link_key(source.get("url", "")) or source["source_id"]
            existing = deduped_by_url.get(key)
            if not existing:
                deduped_by_url[key] = source
                continue
            existing["entry_urls"] = _dedupe_list(existing.get("entry_urls", []) + source.get("entry_urls", []))
            existing["follow_patterns"] = _dedupe_list(existing.get("follow_patterns", []) + source.get("follow_patterns", []))
            # 优先保留 user 源作为主要展示
            if existing.get("config_type") != "user" and source.get("config_type") == "user":
                existing["config_type"] = "user"
                existing["name"] = source.get("name") or existing.get("name")
            deduped_by_url[key] = existing

        resolved = list(deduped_by_url.values())
        self._sources_cache = resolved
        return list(resolved)

    def _scrape_sources_serial(self) -> Generator[Dict[str, Any], None, None]:
        """串行爬取数据源（使用统一配置管理）"""
        all_sources = self._order_sources(self._get_sources_for_scraper())

        for source in all_sources:
            source_id = source['source_id']
            # 创建模拟的配置对象（兼容原有接口）
            source_config = {
                'name': source['name'],
                'base_url': source['url'],
                'delay_min': source['delay_min'],
                'delay_max': source['delay_max'],
                'content_type': 'award',
                'config_type': source['config_type'],
                'follow_patterns': source.get('follow_patterns', []),
                'entry_urls': source.get('entry_urls', [])
            }
            self.logger.info("开始爬取数据源: %s (来源: %s)", source['name'], source.get('config_type', 'user'))

            base_url = source_config.get('base_url', '')
            config_type = source_config.get('config_type', '') or ''

            skip, reason = self._should_skip_source_run(source_id, base_url, config_type)
            if skip:
                self.logger.info("⏭️ 跳过数据源: %s (%s)", source_config.get('name', source_id), reason)
                continue

            emitted = 0
            run_status = "success"
            run_error = ""

            try:
                adaptive_entries = self._discover_source_entries(source_id, base_url, source_config)
                if adaptive_entries:
                    for entry_url in adaptive_entries:
                        for item in self._crawl_listing(entry_url, source_config, source_id, base_url=base_url):
                            emitted += 1
                            yield item
                else:
                    if source_id == 'ccgp':
                        for item in self._scrape_ccgp(source_config):
                            emitted += 1
                            yield item
                    elif source_id == 'university':
                        for item in self._scrape_university(source_config):
                            emitted += 1
                            yield item
                    elif source_id == 'chinabidding':
                        for item in self._scrape_chinabidding(source_config):
                            emitted += 1
                            yield item
                    elif source_id == 'bidcenter':
                        for item in self._scrape_bidcenter(source_config):
                            emitted += 1
                            yield item
                    else:
                        for item in self._scrape_generic_source(source_id, source_config):
                            emitted += 1
                            yield item

                # 随机延迟，避免被反爬虫
                delay_min = source_config.get('delay_min', 3)
                delay_max = source_config.get('delay_max', 8)
                time.sleep(random.uniform(delay_min, delay_max))

            except Exception as e:
                run_status = "error"
                run_error = str(e)
                self.logger.error(f"爬取数据源 {source_config['name']} 失败: {e}")
            finally:
                try:
                    self._record_source_run(
                        source_id,
                        base_url,
                        config_type,
                        emitted=emitted,
                        status=run_status,
                        error=run_error,
                    )
                except Exception:
                    pass

        self._dump_source_health()
        cleanup_stats = self._enforce_retention()
        if cleanup_stats.get('expired') or cleanup_stats.get('overflow'):
                self.logger.info(
                    "保留策略清理完成: 过期 %s 条, 超限 %s 条",
                    cleanup_stats.get('expired', 0),
                    cleanup_stats.get('overflow', 0)
                )

    def _scrape_sources_concurrent(self) -> Generator[Dict[str, Any], None, None]:
        """并发爬取数据源（使用线程池）"""
        import concurrent.futures

        all_sources = self._order_sources(self._get_sources_for_scraper())

        performance_config = settings.get('scraper.performance', {}) or {}
        max_concurrency = performance_config.get('max_source_concurrency', 5)

        def _scrape_single_source_thread(source: Dict[str, Any]):
            """在线程中爬取单个数据源"""
            thread_items: List[Dict[str, Any]] = []
            source_id = source.get("source_id", "")
            config_type = source.get("config_type", "") or ""
            base_url = (source.get("url") or "").strip()
            run_status = "success"
            run_error = ""

            try:
                # 创建模拟的配置对象（兼容原有接口）
                source_config = {
                    'name': source['name'],
                    'base_url': source['url'],
                    'delay_min': source['delay_min'],
                    'delay_max': source['delay_max'],
                    'content_type': 'award',
                    'config_type': source['config_type'],
                    'follow_patterns': source.get('follow_patterns', []),
                    'entry_urls': source.get('entry_urls', [])
                }

                self.logger.info(f"开始并发爬取数据源: {source['name']} (来源: {source['config_type']})")

                base_url = source_config.get('base_url', '')
                adaptive_entries = self._discover_source_entries(source_id, base_url, source_config)

                if adaptive_entries:
                    for entry_url in adaptive_entries:
                        for item in self._crawl_listing(entry_url, source_config, source_id, base_url=base_url):
                            thread_items.append(item)
                else:
                    # 根据源类型选择爬取方法
                    scraper_method = getattr(self, f'_scrape_{source_id}', None)
                    if scraper_method:
                        for item in scraper_method(source_config):
                            thread_items.append(item)
                    else:
                        for item in self._scrape_generic_source(source_id, source_config):
                            thread_items.append(item)

                # 随机延迟
                delay_min = source.get('delay_min', 1)  # 并发时减少延迟
                delay_max = source.get('delay_max', 3)
                time.sleep(random.uniform(delay_min, delay_max))

            except Exception as e:
                run_status = "error"
                run_error = str(e)
                self.logger.error(f"并发爬取数据源 {source['name']} 失败: {e}")

            return {
                "source_id": source_id,
                "base_url": base_url,
                "config_type": config_type,
                "status": run_status,
                "error": run_error,
                "items": thread_items,
            }

        filtered_sources: List[Dict[str, Any]] = []
        for source in all_sources:
            source_id = source.get("source_id", "")
            base_url = (source.get("url") or "").strip()
            config_type = source.get("config_type", "") or ""
            skip, reason = self._should_skip_source_run(source_id, base_url, config_type)
            if skip:
                self.logger.info("⏭️ 跳过数据源: %s (%s)", source.get("name", source_id), reason)
                continue
            filtered_sources.append(source)
        all_sources = filtered_sources

        # 使用线程池执行并发爬取
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_concurrency) as executor:
            # 分批处理
            for i in range(0, len(all_sources), max_concurrency):
                batch = all_sources[i:i + max_concurrency]

                # 提交任务
                future_to_source = {
                    executor.submit(_scrape_single_source_thread, source): source
                    for source in batch
                }

                # 收集结果
                for future in concurrent.futures.as_completed(future_to_source):
                    source = future_to_source[future]
                    try:
                        result = future.result()
                        if isinstance(result, dict):
                            items = result.get("items", []) or []
                            for item in items:
                                yield item
                            try:
                                self._record_source_run(
                                    result.get("source_id", "") or source.get("source_id", ""),
                                    result.get("base_url", "") or (source.get("url") or ""),
                                    result.get("config_type", "") or source.get("config_type", ""),
                                    emitted=len(items),
                                    status=result.get("status", "success") or "success",
                                    error=result.get("error", "") or "",
                                )
                            except Exception:
                                pass
                        else:
                            items = result or []
                            for item in items:
                                yield item
                            try:
                                self._record_source_run(
                                    source.get("source_id", ""),
                                    (source.get("url") or ""),
                                    source.get("config_type", "") or "",
                                    emitted=len(items),
                                    status="success",
                                    error="",
                                )
                            except Exception:
                                pass
                    except Exception as e:
                        self.logger.error(f"获取数据源 {source['name']} 结果失败: {e}")

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
                    for item in self._extract_ccgp_api_items(response, url):
                        if self._is_duplicate_item(item):
                            self.logger.debug(f"跳过重复项目: {item.get('title', '')}")
                            continue
                        self._save_item_hash(item)
                        self._save_raw_item(item)
                        yield item
                else:
                    # HTML页面处理
                    soup = BeautifulSoup(response.text, 'lxml')
                    items = self._extract_ccgp_items(soup, url)
                    for item in items:
                        # 检查去重
                        if self._is_duplicate_item(item):
                            self.logger.debug(f"跳过重复项目: {item.get('title', '')}")
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
                link = self._clean_item_link(item.get('url', ''))
                if not link:
                    continue
                yield {
                    'title': item.get('title', ''),
                    'link': link,
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

        # 批量收集URL进行过滤
        raw_items = []

        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                self.logger.info(f"使用选择器 '{selector}' 找到 {len(elements)} 个链接")
                for element in elements:
                    try:
                        item = self._process_ccgp_item(element, source_url)
                        if item and item['title'] and item['link']:
                            raw_items.append((item, source_url))
                    except Exception as e:
                        self.logger.error(f"处理条目失败: {e}")

                if raw_items:  # 如果找到了数据，就不再尝试其他选择器
                    break

        if raw_items:
            for item, _source in raw_items:
                if self._is_relevant_title(item.get('title', ''), item.get('link', ''), item.get('source', '')):
                    items.append(item)

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
            full_link = self._clean_item_link(full_link)
            if not full_link.startswith(('http://', 'https://')):
                return None

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

    def _scrape_generic_source(self, source_id: str, config: Dict[str, Any]) -> Generator[Dict[str, Any], None, None]:
        """通用爬虫，用于自动发现的数据源"""
        base_url = config.get('base_url')
        if not base_url:
            self.logger.warning("数据源 %s 缺少 base_url，跳过", source_id)
            return

        max_pages = int(config.get('max_pages', 3))
        max_items = int(config.get('max_items', 50))
        keywords = config.get('keywords') or GENERIC_KEYWORDS
        follow_patterns = []
        raw_patterns = config.get('follow_patterns')
        if isinstance(raw_patterns, list):
            follow_patterns = [str(p) for p in raw_patterns if p]

        queue = [base_url]
        visited: set[str] = set()
        emitted = 0
        base_domain = urlparse(base_url).netloc
        source_name = _source_display_name(config, base_domain)

        while queue and len(visited) < max_pages and emitted < max_items:
            current = queue.pop(0)
            normalized = _normalize_url(current)
            if normalized in visited:
                continue
            visited.add(normalized)

            try:
                response = self._fetch_with_metrics(normalized, source_id)
            except Exception as exc:
                self.logger.error("抓取 %s 失败: %s", normalized, exc)
                continue

            soup = BeautifulSoup(response.text, 'lxml')
            items = self._extract_generic_items(
                soup,
                normalized,
                keywords,
                base_domain,
                source_name,
                config
            )
            for item in items:
                if emitted >= max_items:
                    break
                if self._is_duplicate_item(item):
                    continue
                self._save_item_hash(item)
                self._save_raw_item(item)
                emitted += 1
                yield item

            if emitted >= max_items:
                break

            next_page = self._find_next_page(soup, normalized)
            if next_page and self._should_follow_link(next_page, follow_patterns):
                next_normalized = _normalize_url(next_page)
                if next_normalized not in visited and next_normalized not in queue:
                    queue.append(next_normalized)

    def _extract_generic_items(
        self,
        soup: BeautifulSoup,
        source_url: str,
        keywords: List[str],
        base_domain: str,
        source_name: str,
        source_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        elements: List[Any] = []

        for selector in GENERIC_SELECTORS:
            nodes = soup.select(selector)
            if nodes:
                elements.extend(nodes)

        if not elements:
            elements = soup.find_all('a')

        base_domain_norm = (base_domain or "").lower()
        if base_domain_norm.startswith("www."):
            base_domain_norm = base_domain_norm[4:]

        seen_links: set[str] = set()
        for element in elements:
            title = element.get_text(strip=True)
            if not title or len(title) < 6:
                continue
            if keywords and not any(keyword in title for keyword in keywords):
                continue

            href = element.get('href')
            if not href:
                continue

            link = urljoin(source_url, href)
            link = self._clean_item_link(link)
            if not link.startswith(('http://', 'https://')):
                continue

            link_domain = urlparse(link).netloc
            link_domain_norm = (link_domain or "").lower()
            if link_domain_norm.startswith("www."):
                link_domain_norm = link_domain_norm[4:]
            if base_domain_norm:
                if (
                    link_domain_norm != base_domain_norm
                    and not link_domain_norm.endswith("." + base_domain_norm)
                    and not base_domain_norm.endswith("." + link_domain_norm)
                ):
                    continue

            if link in seen_links:
                continue
            seen_links.add(link)
            if self._should_skip_discovery_link(title, link, source_config):
                continue

            publish_date = self._extract_publish_date(element, title)
            item = {
                'title': self._normalize_encoding(title),
                'link': link,
                'source': source_name,
                'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'publish_date': publish_date,
                'raw_content': str(element)
            }
            if not self._is_relevant_title(item['title'], link, source_name):
                continue
            items.append(item)

        return items

    def _find_next_page(self, soup: BeautifulSoup, current_url: str) -> Optional[str]:
        # rel=next 优先
        rel_next = soup.find('a', attrs={'rel': 'next'})
        if rel_next and rel_next.get('href'):
            return urljoin(current_url, rel_next['href'])

        # 文本包含“下一页”
        anchor = soup.find('a', string=re.compile(r'(下一页|下一頁|下页|Next|›|»)', re.I))
        if anchor and anchor.get('href'):
            return urljoin(current_url, anchor['href'])

        parsed = urlparse(current_url)
        query = parsed.query
        if not query:
            return None
        try:
            params = dict(param.split('=') for param in query.split('&') if '=' in param)
        except ValueError:
            return None

        key = None
        for candidate in ('page', 'p', 'curpage'):
            if candidate in params:
                key = candidate
                break
        if not key:
            return None

        try:
            next_value = int(params[key]) + 1
        except ValueError:
            return None
        params[key] = str(next_value)
        new_query = '&'.join(f"{k}={v}" for k, v in params.items())
        return urlunparse(parsed._replace(query=new_query))

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
                        full_link = self._clean_item_link(full_link)
                        if not full_link.startswith(('http://', 'https://')):
                            continue

                        publish_date = self._extract_publish_date(element, title)

                        item = {
                            'title': title,
                            'link': full_link,
                            'source': '中国采购与招标网',
                            'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'publish_date': publish_date,
                            'raw_content': str(element)
                        }

                        if not self._is_relevant_title(item['title']):
                            continue
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
                        full_link = self._clean_item_link(full_link)
                        if not full_link.startswith(('http://', 'https://')):
                            continue

                        publish_date = self._extract_publish_date(element, title)

                        item = {
                            'title': title,
                            'link': full_link,
                            'source': '招标采购导航网',
                            'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'publish_date': publish_date,
                            'raw_content': str(element)
                        }

                        if not self._is_relevant_title(item['title']):
                            continue
                        items.append(item)

                    except Exception as e:
                        self.logger.error(f"处理条目失败: {e}")

                if items:
                    break

        return items

    def _scrape_university(self, config: Dict[str, Any]) -> Generator[Dict[str, Any], None, None]:
        """爬取高校采购信息（自适应入口）"""
        universities = self._load_university_sources()
        if not universities:
            self.logger.warning("高校采购源列表为空，跳过")
            return

        for entry in universities:
            name = entry.get('name')
            base_url = entry.get('url')
            if not base_url:
                continue
            source_label = f"高校采购:{name}" if name else "高校采购"
            local_config = dict(config)
            local_config['name'] = source_label
            local_config['base_url'] = base_url
            adaptive_entries = self._discover_source_entries(source_label, base_url, local_config)
            if not adaptive_entries:
                continue
            for entry_url in adaptive_entries:
                yield from self._crawl_listing(entry_url, local_config, source_label, base_url=base_url)

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
        if not html:
            return ''
        soup = BeautifulSoup(html, 'lxml')

        # 清理无关节点，减少脚本/样式干扰
        for tag in soup(['script', 'style', 'noscript']):
            try:
                tag.decompose()
            except Exception:  # noqa: BLE001
                continue

        content_selectors = [
            '.content',
            '.article-content',
            '.detail-content',
            '.main-content',
            '.text-con',
            'div[class*="content"]',
            '.article'
        ]

        # 在多个候选中选“更像正文/公告”的内容块：优先含联系方式关键词，其次长度
        keyword_hints = (
            '采购人', '采购单位', '采购代理', '代理机构', '联系方式', '联系人', '电话', '邮箱', '地址',
            '中标', '成交', '结果公告', '采购项目',
        )
        best_text = ''
        best_score = -1

        for selector in content_selectors:
            elements = soup.select(selector)[:3]
            for element in elements:
                text = element.get_text(separator='\n', strip=True)
                text = self._normalize_encoding(text)
                if not text:
                    continue
                # 规范化换行，避免后续抽取无法分段
                text = re.sub(r'\n{3,}', '\n\n', text)
                hint_hits = sum(text.count(hint) for hint in keyword_hints)
                score = hint_hits * 10_000 + min(len(text), 50_000)
                if score > best_score:
                    best_score = score
                    best_text = text

        if best_text:
            return best_text[:50_000]

        body = soup.find('body')
        if body:
            body_text = body.get_text(separator='\n', strip=True)
            body_text = self._normalize_encoding(body_text)
            body_text = re.sub(r'\n{3,}', '\n\n', body_text)
            return body_text[:50_000]

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
                detail_text = self._parse_detail_html(response.text)
                if not detail_text or not detail_text.strip():
                    stats['failed'] += 1
                    continue
                target_item['detail_content'] = detail_text
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
        retention_config = settings.get('storage.retention', {}) or {}

        try:
            with self._db_lock:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                # 今日爬取数量
                today = datetime.now().strftime('%Y-%m-%d')
                cursor.execute(
                    "SELECT COUNT(*) FROM scraped_items_hash WHERE DATE(scraped_at) = ?",
                    (today,),
                )
                today_count = cursor.fetchone()[0]

                # 总爬取数量
                cursor.execute("SELECT COUNT(*) FROM scraped_items_hash")
                total_count = cursor.fetchone()[0]

                # 各来源统计
                cursor.execute(
                    "SELECT source, COUNT(*) as count FROM scraped_items_hash GROUP BY source"
                )
                source_stats = dict(cursor.fetchall())

                # scraped_data 状态
                cursor.execute("SELECT processed, COUNT(*) FROM scraped_data GROUP BY processed")
                pending_details = 0
                processed_details = 0
                for processed_flag, count in cursor.fetchall():
                    if processed_flag:
                        processed_details = count
                    else:
                        pending_details = count

                cursor.execute("SELECT COUNT(*) FROM scraped_data")
                total_scraped_records = cursor.fetchone()[0]

                cursor.execute(
                    """
                    SELECT MIN(datetime(COALESCE(detail_scraped_at, scraped_at)))
                    FROM scraped_data
                    WHERE processed = 0
                    """
                )
                oldest_pending = cursor.fetchone()[0]

                conn.close()

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
                    'config': retention_config,
                    'last_cleanup': self.last_retention_stats
                }
            }

    def flush(self):
        """刷新缓冲区（当前实现为 no-op，保留接口兼容）。"""
        return None


# 全局爬虫实例
scraper = UnifiedScraper()
