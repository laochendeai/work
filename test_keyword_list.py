#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path


def test_load_keywords_splits_and_dedupes(tmp_path):
    from utils.keyword_list import load_keywords  # noqa: PLC0415

    kw_file = tmp_path / "keywords.txt"
    kw_file.write_text(
        "\n".join(
            [
                "智能",
                "机房",
                "",
                "# 注释行",
                "弱电, 数据中心",
                "智能",
            ]
        ),
        encoding="utf-8",
    )

    keywords = load_keywords(["智能,机房", "信息化"], str(kw_file))
    assert keywords == ["智能", "机房", "信息化", "弱电", "数据中心"]


def test_load_keywords_empty_inputs(tmp_path):
    from utils.keyword_list import load_keywords  # noqa: PLC0415

    assert load_keywords(None, None) == []

    kw_file = tmp_path / "empty.txt"
    kw_file.write_text("\n\n# only comments\n# x\n", encoding="utf-8")
    assert load_keywords([], str(kw_file)) == []

