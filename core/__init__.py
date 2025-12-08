#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能设计营销系统 - 核心模块
"""

from .scraper import UnifiedScraper, scraper
from .extractor import ContactExtractor, extractor
from .emailer import EmailSender, emailer
from .fetcher import AdvancedFetcher

__all__ = [
    'UnifiedScraper', 'scraper',
    'ContactExtractor', 'extractor',
    'EmailSender', 'emailer',
    'AdvancedFetcher'
]

__version__ = '2.0.0'
