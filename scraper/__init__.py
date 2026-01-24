"""
爬虫模块
"""
from .base import BaseScraper
from .fetcher import PlaywrightFetcher
from .parser import ListPageParser, DetailPageParser
from .ccgp_parser import CCGPAnnouncementParser
from .smart_parser import SmartAnnouncementParser

__all__ = [
    'BaseScraper',
    'PlaywrightFetcher',
    'ListPageParser',
    'DetailPageParser',
    'CCGPAnnouncementParser',
    'SmartAnnouncementParser',
]
