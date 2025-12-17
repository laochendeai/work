#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于“行业关键词”的全网数据源发现（不限制域名）。

目标：
- 用行业词 + 招采/中标/公告等组合在 DuckDuckGo 做搜索（通过 r.jina.ai 代理）。
- 对候选站点做轻量校验：能否找到可用的“公告列表页”入口（entry_urls）。
- 将通过校验的候选写入 config/auto_sources.yaml，供主爬虫后续直接爬取。

说明：
- 为避免噪音/误伤，本脚本默认 dry-run（只输出不写文件）。
- 不建议默认把新源都 enabled=true；请先抽样验证后再启用。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import parse_qs, quote, unquote, urlparse, urlunparse

import yaml
from bs4 import BeautifulSoup

# 系统路径设置（与现有 tools 脚本保持一致）
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.fetcher import AdvancedFetcher  # noqa: E402
from core.scraper import UnifiedScraper  # noqa: E402


DEFAULT_PROCUREMENT_HINTS = [
    # 企业/园区/协会更常用的“平台词”优先，提升非 gov 源命中率
    "阳光采购",
    "电子采购平台",
    "采购平台",
    "招标采购平台",
    "电子招标",
    "供应商",
    "招标",
    "招标公告",
    "采购",
    "采购公告",
    "招采",
    "比选",
    "询价",
    "竞争性谈判",
    "竞争性磋商",
    "中标",
    "中标公告",
    "成交",
    "成交公告",
    "结果公告",
    "公示",
    "开标",
    "电子采购平台",
    "阳光采购",
    "采购平台",
    "招标采购平台",
    "bidding",
    "tender",
    "procurement",
    "purchase",
    "eproc",
]

# 更偏企业/园区/协会的入口路径线索（用于 discovery 的 follow_patterns 提权）
DEFAULT_FOLLOW_PATTERNS = [
    "/cggg",
    "/cgxx",
    "/zbcg",
    "/zbgg",
    "/cjgg",
    "/jyxx",
    "/ggzy",
    "/notice",
    "/gonggao",
    "/annc",
    "/bid",
    "/bidding",
    "/tender",
    "/procurement",
    "/purchase",
    "/sourcing",
    "/supplier",
    "/ecp",
    "/eproc",
    "/eps",
    "/zbxx",
    "/cggg",
]

DEFAULT_EXCLUDE_URL_SNIPPETS = [
    # 常见“招投标聚合/采招信息聚合”站点：易 403/429 或不便直接作为源
    "zbbid.com.cn",
    "yfbzb.com",
    "bidcenter.com.cn",
    "zhaobiao.cn",
    "ebnew.com",
    "dlzb.com.cn",
    "bidnews.cn",
    "anfangzb.com",
    "bdebid.com",
    "cntcitc.com.cn",
    "sohu.com",
    "sina.com.cn",
    "163.com",
    "qq.com",
    "people.com.cn",
    "cctv.com",
    "zhidao.baidu.com",
    "baike.baidu.com",
    "tieba.baidu.com",
    "weibo.com",
    "mp.weixin.qq.com",
    "facebook.com",
    "twitter.com",
    "x.com",
    "instagram.com",
    "youtube.com",
    "bilibili.com",
    "douyin.com",
    "tiktok.com",
    "zhihu.com",
    "csdn.net",
    "toutiao.com",
    "wenku.baidu.com",
    "/job",
    "/jobs",
    "/zhaopin",
    "/recruit",
    "/careers",
    "/hr",
]


def _unwrap_duckduckgo_redirect_url(href: str) -> str:
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


def _normalize_url_no_query(url: str) -> str:
    if not url:
        return ""
    try:
        parsed = urlparse(url)
    except Exception:
        return ""
    if not parsed.scheme or not parsed.netloc:
        return ""
    normalized = parsed._replace(fragment="", query="")
    return urlunparse(normalized)


def _root_url(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return ""
    return urlunparse(parsed._replace(path="/", query="", fragment=""))


def _stable_source_id(prefix: str, key: str) -> str:
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}{digest}"


_PROCUREMENT_STRONG_KEYWORDS = [
    "招标",
    "采购",
    "中标",
    "成交",
    "投标",
    "比选",
    "询价",
    "竞价",
    "磋商",
    "谈判",
    "入围",
    "候选",
    "开标",
    "遴选",
]


def _strong_procurement_hit(title: str) -> bool:
    if not title:
        return False
    text = title.strip()
    if not text:
        return False
    return any(k in text for k in _PROCUREMENT_STRONG_KEYWORDS)


def _dedupe_strs(items: Iterable[str]) -> List[str]:
    seen: set[str] = set()
    out: List[str] = []
    for item in items:
        value = (item or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if isinstance(data, dict):
            return data
    except Exception:
        return {}
    return {}


def _load_industry_keywords(config_dir: Path) -> List[str]:
    """优先读取 config/auto_keywords.yaml，否则退回 config/keywords.yaml."""
    keywords: List[str] = []

    auto_kw = config_dir / "auto_keywords.yaml"
    if auto_kw.exists():
        data = _load_yaml(auto_kw)
        values = data.get("keywords", [])
        if isinstance(values, list):
            keywords.extend([str(v).strip() for v in values if str(v).strip()])

    kw = config_dir / "keywords.yaml"
    if kw.exists():
        data = _load_yaml(kw)
        values = data.get("white_list", [])
        if isinstance(values, list):
            keywords.extend([str(v).strip() for v in values if str(v).strip()])

    # 过滤太泛的单字词（避免噪音爆炸）
    keywords = [k for k in keywords if len(k) >= 2]
    return _dedupe_strs(keywords)


def _build_queries(industry_keywords: List[str], *, max_queries: int) -> List[str]:
    queries: List[str] = []
    for kw in industry_keywords:
        for hint in DEFAULT_PROCUREMENT_HINTS:
            queries.append(f"{kw} {hint}".strip())
    # 去重 + 截断
    queries = _dedupe_strs(queries)
    if max_queries > 0:
        queries = queries[:max_queries]
    return queries


@dataclass
class CandidateSite:
    domain: str
    seed_urls: List[str]
    hit_queries: List[str]


@dataclass
class DiscoveredSource:
    source_id: str
    name: str
    base_url: str
    entry_urls: List[str]
    follow_patterns: List[str]
    quality_score: float
    matched_keywords: List[str]
    discovered_at: str
    discovered_by: str


class IndustrySourceDiscoverer:
    def __init__(
        self,
        *,
        config_dir: Path,
        max_results_per_query: int,
        max_domains: int,
        max_entries_per_site: int,
        max_depth: int,
        enable_playwright: bool,
        min_quality: float,
    ):
        self.config_dir = config_dir
        self.max_results_per_query = max(1, int(max_results_per_query))
        self.max_domains = max(1, int(max_domains))
        self.max_entries_per_site = max(1, int(max_entries_per_site))
        self.max_depth = max(0, int(max_depth))
        self.enable_playwright = bool(enable_playwright)
        self.min_quality = float(min_quality)

        self.scraper = UnifiedScraper()
        # Discovery 更偏“探测/筛选”，不要被重试/等待拖慢；不影响主爬虫的 fetcher 配置
        try:
            self.scraper.fetcher = AdvancedFetcher(
                timeout=8.0,
                concurrency=10,
                max_connections=20,
                max_keepalive_connections=10,
                retry_attempts=1,
                backoff_min=0.2,
                backoff_max=2.0,
                http2=False,
                respect_retry_after=False,
            )
        except Exception:
            pass
        self.blacklist_domains = set(str(d).lower() for d in self.scraper.policy.get("blacklist_domains", []) if d)

    def _duckduckgo_search(self, query: str, *, max_links: int) -> List[str]:
        """DuckDuckGo HTML 搜索（通过 r.jina.ai 代理），返回候选 URL 列表。"""
        if not query:
            return []
        proxy_url = f"https://r.jina.ai/http://duckduckgo.com/html/?q={quote(query)}"
        try:
            resp = self.scraper.fetcher.fetch(proxy_url)
        except Exception:
            return []
        text = (resp.text or "").strip()
        if not text:
            return []
        links = re.findall(r"https?://duckduckgo\.com/l/\?uddg=[^\s)\"]+", text)
        results: List[str] = []
        seen: set[str] = set()
        for link in links:
            target = _unwrap_duckduckgo_redirect_url(link)
            if not target:
                continue
            normalized = _normalize_url_no_query(target)
            if not normalized:
                continue
            if normalized in seen:
                continue
            seen.add(normalized)
            results.append(normalized)
            if len(results) >= max_links:
                break
        return results

    def _is_noise_url(self, url: str) -> bool:
        lower = (url or "").lower()
        if not lower:
            return True
        if any(snippet in lower for snippet in DEFAULT_EXCLUDE_URL_SNIPPETS):
            return True
        parsed = urlparse(lower)
        domain = parsed.netloc
        if not domain:
            return True
        # blacklist_domains 支持根域名：同时拒绝其子域名（例如 sohu.com / www.sohu.com）
        if any(domain == blocked or domain.endswith("." + blocked) for blocked in self.blacklist_domains):
            return True
        # 常见“媒体/门户/百科/问答”噪音（不做域名限制，只做轻量排除）
        noisy_domain_tokens = ("news.", "blog.", "wiki.", "bbs.", "forum.")
        if any(domain.startswith(tok) for tok in noisy_domain_tokens):
            return True
        # 排除静态文件
        if parsed.path.endswith((".pdf", ".doc", ".docx", ".xls", ".xlsx", ".zip", ".rar")):
            return True
        return False

    def collect_candidates(self, queries: List[str]) -> List[CandidateSite]:
        by_domain: Dict[str, CandidateSite] = {}
        for query in queries:
            urls = self._duckduckgo_search(query, max_links=self.max_results_per_query)
            for url in urls:
                if self._is_noise_url(url):
                    continue
                domain = urlparse(url).netloc.lower()
                if not domain:
                    continue
                existing = by_domain.get(domain)
                if not existing:
                    by_domain[domain] = CandidateSite(domain=domain, seed_urls=[url], hit_queries=[query])
                else:
                    existing.seed_urls = _dedupe_strs(existing.seed_urls + [url])
                    existing.hit_queries = _dedupe_strs(existing.hit_queries + [query])
                if len(by_domain) >= self.max_domains:
                    break
            if len(by_domain) >= self.max_domains:
                break
        return list(by_domain.values())

    def _discover_entries_for_site(
        self,
        *,
        start_urls: List[str],
        follow_patterns: List[str],
    ) -> Tuple[str, List[str]]:
        """返回 (base_url, entry_urls)。"""
        source_config: Dict[str, Any] = {
            "follow_patterns": follow_patterns,
            "discovery": {
                "enable_playwright_validation": bool(self.enable_playwright),
                "max_child_links": 8,
            },
        }
        for start in start_urls:
            start = _normalize_url_no_query(start)
            if not start:
                continue
            try:
                entries = self.scraper._run_discovery(
                    start,
                    max_depth=self.max_depth,
                    max_entries=self.max_entries_per_site,
                    max_links_per_page=50,
                    source_id="industry-discovery",
                    source_config=source_config,
                )
            except Exception:
                entries = []
            if entries:
                return start, _dedupe_strs(entries)
        return "", []

    def analyze_candidate(
        self,
        candidate: CandidateSite,
        *,
        industry_keywords: List[str],
        follow_patterns: List[str],
    ) -> Optional[DiscoveredSource]:
        seed_urls = candidate.seed_urls[:]
        roots = _dedupe_strs([_root_url(u) for u in seed_urls if u])
        start_urls = _dedupe_strs(seed_urls + roots)
        base_url, entry_urls = self._discover_entries_for_site(start_urls=start_urls, follow_patterns=follow_patterns)
        if not entry_urls:
            return None

        # 二次校验：entry_url 是否真的像“招采/中标列表页”（避免把普通公告/物流公告等误当成招采源）
        strong_hits = 0
        extracted_items = 0
        for probe_url in entry_urls[:2]:  # 只抽样前2个入口，控制请求量
            try:
                resp = self.scraper.fetcher.fetch(probe_url)
            except Exception:
                continue
            html = resp.text or ""
            if not html:
                continue
            soup = BeautifulSoup(html, "lxml")
            items = self.scraper._extract_generic_items(
                soup,
                probe_url,
                keywords=DEFAULT_PROCUREMENT_HINTS,  # 宽松提取，后续用 strong keyword 再筛
                base_domain=urlparse(probe_url).netloc,
                source_name=candidate.domain,
                source_config={"follow_patterns": follow_patterns},
            )
            titles = [str(it.get("title", "")).strip() for it in items if isinstance(it, dict)]
            extracted_items += len(titles)
            strong_hits += sum(1 for t in titles if _strong_procurement_hit(t))

        # 最少要抓到一些条目，且存在明显“招标/采购/中标/成交”等强关键词
        if extracted_items < 5 or strong_hits < 2:
            return None

        matched_keywords: List[str] = []
        try:
            sample_url = entry_urls[0]
            resp = self.scraper.fetcher.fetch(sample_url)
            page_text = (resp.text or "")[:200_000]
            matched_keywords = [k for k in industry_keywords if k and k in page_text]
        except Exception:
            matched_keywords = []

        # 质量评分：以“能找到多少入口 + 是否命中行业词”为主，保持可解释且简单
        score = 0.6 + min(len(entry_urls), 3) * 0.1
        # “招采强关键词”命中越多，说明更像真实招采列表页
        score += min(strong_hits, 10) * 0.01
        if matched_keywords:
            score += 0.1
        score = max(0.0, min(float(score), 1.0))
        if score < self.min_quality:
            return None

        discovered_at = datetime.now(timezone.utc).isoformat()
        # base_url 统一固化为“站点根”，避免把详情页/深链当作 base_url
        base_url_final = _root_url(entry_urls[0]) if entry_urls else ""
        base_url_final = _normalize_url_no_query(base_url_final) or base_url_final

        source_id = _stable_source_id("ind_auto_", candidate.domain)
        name = f"自动发现(行业): {candidate.domain}"
        return DiscoveredSource(
            source_id=source_id,
            name=name,
            base_url=base_url_final,
            entry_urls=entry_urls,
            follow_patterns=follow_patterns,
            quality_score=score,
            matched_keywords=_dedupe_strs(matched_keywords),
            discovered_at=discovered_at,
            discovered_by="Industry Discovery (DuckDuckGo)",
        )


def _load_or_init_auto_sources(path: Path) -> Dict[str, Any]:
    if path.exists():
        data = _load_yaml(path)
        if isinstance(data, dict) and "sources" in data and isinstance(data.get("sources"), dict):
            data.setdefault("metadata", {})
            return data
    return {
        "metadata": {
            "auto_discovery_enabled": False,
            "mcp_discovery_enabled": False,
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "total_sources": 0,
        },
        "sources": {},
    }


def _write_auto_sources(
    auto_sources_path: Path,
    discovered: List[DiscoveredSource],
    *,
    enable_new: bool,
    dry_run: bool,
) -> None:
    data = _load_or_init_auto_sources(auto_sources_path)
    sources: Dict[str, Any] = data.get("sources", {}) if isinstance(data.get("sources"), dict) else {}

    existing_domains: set[str] = set()
    for _sid, cfg in sources.items():
        if not isinstance(cfg, dict):
            continue
        url = (cfg.get("base_url") or cfg.get("url") or "").strip()
        if not url:
            continue
        netloc = urlparse(url).netloc.lower()
        if netloc:
            existing_domains.add(netloc)

    added = 0
    for item in discovered:
        item_domain = urlparse(item.base_url).netloc.lower()
        if item_domain and item_domain in existing_domains:
            continue
        if item.source_id in sources:
            continue
        sources[item.source_id] = {
            "source_id": item.source_id,
            "name": item.name,
            "base_url": item.base_url,
            "category": "industry_discovered",
            "content_type": "award",
            "enabled": bool(enable_new),
            "delay_min": 3,
            "delay_max": 8,
            "type": "企业/园区/协会招采",
            "categories": item.matched_keywords,
            "quality_score": float(item.quality_score),
            "discovered_by": item.discovered_by,
            "discovered_at": item.discovered_at,
            "follow_patterns": item.follow_patterns,
            "entry_urls": item.entry_urls,
            "entry_urls_updated_at": datetime.now(timezone.utc).isoformat(),
        }
        added += 1
        if item_domain:
            existing_domains.add(item_domain)

    if added == 0:
        print("ℹ️ 没有新增数据源")
        return

    data["sources"] = sources
    metadata = data.get("metadata", {}) if isinstance(data.get("metadata"), dict) else {}
    metadata["last_updated"] = datetime.now(timezone.utc).isoformat()
    metadata["total_sources"] = len(sources)
    data["metadata"] = metadata

    if dry_run:
        print(f"🧪 dry-run: 发现 {len(discovered)} 个候选，新增 {added} 个（未写入 {auto_sources_path}）")
        for item in discovered[: min(len(discovered), 20)]:
            print(f"  - {item.name} | {item.base_url} | entry_urls={len(item.entry_urls)} | score={item.quality_score:.2f}")
        if len(discovered) > 20:
            print(f"  ... 还有 {len(discovered) - 20} 个")
        return

    auto_sources_path.parent.mkdir(parents=True, exist_ok=True)
    auto_sources_path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"✅ 已写入 {auto_sources_path}，新增 {added} 个数据源（enable_new={enable_new}）")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="行业关键词驱动的全网数据源发现（不限制域名）")
    parser.add_argument("--max-queries", type=int, default=80, help="最多使用多少条搜索 query（默认80）")
    parser.add_argument("--max-results-per-query", type=int, default=20, help="每条 query 最多取多少条结果（默认20）")
    parser.add_argument("--max-domains", type=int, default=120, help="最多分析多少个域名候选（默认120）")
    parser.add_argument("--max-entries-per-site", type=int, default=3, help="每个站点最多固化多少个 entry_urls（默认3）")
    parser.add_argument("--max-depth", type=int, default=2, help="入口探测最大深度（默认2）")
    parser.add_argument("--min-quality", type=float, default=0.75, help="最低质量分（0-1，默认0.75）")
    parser.add_argument("--enable-playwright", action="store_true", help="启用 Playwright 校验（更慢，且需要安装浏览器）")
    parser.add_argument("--enable-new", action="store_true", help="写入时将新源 enabled=true（默认 false）")
    parser.add_argument("--apply", action="store_true", help="写入 config/auto_sources.yaml（默认 dry-run 不写）")
    args = parser.parse_args(argv)

    repo_dir = Path(__file__).parent.parent
    config_dir = repo_dir / "config"
    auto_sources_path = config_dir / "auto_sources.yaml"

    industry_keywords = _load_industry_keywords(config_dir)
    if not industry_keywords:
        print("❌ 未找到行业关键词（请检查 config/auto_keywords.yaml 或 config/keywords.yaml）")
        return 2

    queries = _build_queries(industry_keywords, max_queries=int(args.max_queries))
    print(f"🔍 行业关键词: {len(industry_keywords)} 个；搜索 query: {len(queries)} 条")

    discoverer = IndustrySourceDiscoverer(
        config_dir=config_dir,
        max_results_per_query=int(args.max_results_per_query),
        max_domains=int(args.max_domains),
        max_entries_per_site=int(args.max_entries_per_site),
        max_depth=int(args.max_depth),
        enable_playwright=bool(args.enable_playwright),
        min_quality=float(args.min_quality),
    )

    candidates = discoverer.collect_candidates(queries)
    print(f"🌐 候选域名: {len(candidates)} 个（将逐个探测入口列表页）")

    follow_patterns = _dedupe_strs(DEFAULT_FOLLOW_PATTERNS)
    discovered: List[DiscoveredSource] = []
    for idx, candidate in enumerate(candidates, start=1):
        found = discoverer.analyze_candidate(
            candidate,
            industry_keywords=industry_keywords,
            follow_patterns=follow_patterns,
        )
        if found:
            discovered.append(found)
            print(
                f"[{idx:03d}/{len(candidates):03d}] ✅ {found.name} | entry_urls={len(found.entry_urls)} | score={found.quality_score:.2f}"
            )
        else:
            print(f"[{idx:03d}/{len(candidates):03d}] ⏭️  {candidate.domain}（未通过入口校验/评分）")

    _write_auto_sources(
        auto_sources_path,
        discovered,
        enable_new=bool(args.enable_new),
        dry_run=not bool(args.apply),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
