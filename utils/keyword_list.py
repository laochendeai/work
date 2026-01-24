#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional


def _split_keywords(raw: str) -> List[str]:
    # 支持中文/英文逗号分隔
    parts = []
    for part in (raw or "").replace("，", ",").split(","):
        s = part.strip()
        if s:
            parts.append(s)
    return parts


def load_keywords(keywords: Optional[Iterable[str]], kw_file: Optional[str]) -> List[str]:
    """
    从命令行参数 + 文件加载关键词列表

    - `keywords`: 可为 ["智能", "机房"] 或 ["智能,机房"]
    - `kw_file`: 文本文件路径，每行一个关键词；支持注释行（# 开头）与逗号分隔
    - 返回值：去重（保序）
    """
    result: List[str] = []
    seen: set[str] = set()

    for item in keywords or []:
        for kw in _split_keywords(item):
            if kw not in seen:
                seen.add(kw)
                result.append(kw)

    if kw_file:
        path = Path(kw_file)
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                for kw in _split_keywords(s):
                    if kw not in seen:
                        seen.add(kw)
                        result.append(kw)

    return result

