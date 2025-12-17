#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Keyword filtering utilities."""

from __future__ import annotations

from functools import lru_cache
import re
from pathlib import Path
from typing import Iterable

import jieba
import yaml
try:  # pragma: no cover
    from bs4 import BeautifulSoup
except Exception:  # pragma: no cover
    BeautifulSoup = None

KEYWORD_FILE = Path(__file__).resolve().parent.parent / "config" / "keywords.yaml"
CONTACT_PATTERNS = [
    r'联系人[：:：\s]*[A-Za-z\u4e00-\u9fa5]{2,10}',
    r'(?:联系电话|联系方式|电话)[：:：\s]*[+0-9\-（）() ]{7,20}',
    r'1[3-9]\d{9}',
    r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}',
]


def _load_keywords() -> list[str]:
    if not KEYWORD_FILE.exists():
        return []
    data = yaml.safe_load(KEYWORD_FILE.read_text(encoding="utf-8")) or {}
    return list(data.get("white_list", []))


@lru_cache(maxsize=1)
def keywords() -> tuple[str, ...]:
    return tuple(_load_keywords())


def title_hit(title: str) -> bool:
    if not title:
        return False
    title = title.strip()
    if not title:
        return False
    return any(word and word in title for word in keywords())

def _to_text(value: str) -> str:
    if not value:
        return ""
    text = value.strip()
    if not text:
        return ""
    if BeautifulSoup is None:
        return re.sub(r"<[^>]+>", " ", text)
    if "<" not in text or ">" not in text or not re.search(r"<[a-zA-Z][^>]*>", text):
        return text
    try:
        soup = BeautifulSoup(text, "lxml")
        for tag in soup(["script", "style", "noscript"]):
            try:
                tag.decompose()
            except Exception:
                continue
        return soup.get_text(separator=" ", strip=True)
    except Exception:
        return re.sub(r"<[^>]+>", " ", text)


def body_density(html: str, threshold: float = 0.015) -> bool:
    if not html:
        return False
    text = _to_text(html)
    if not text:
        return False
    tokens = jieba.lcut(text)
    if not tokens:
        return False
    hits = sum(1 for token in tokens if token in keywords())
    density = hits / len(tokens)
    return density >= threshold


def detail_keyword_hit(text: str) -> bool:
    if not text:
        return False
    scan = _to_text(text)
    if not scan:
        return False
    return any(word in scan for word in keywords())


def has_contact_info(text: str) -> bool:
    if not text:
        return False
    scan = _to_text(text)
    if not scan:
        return False
    for pattern in CONTACT_PATTERNS:
        if re.search(pattern, scan):
            return True
    return False
