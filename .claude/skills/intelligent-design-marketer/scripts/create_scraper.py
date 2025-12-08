#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
爬虫生成器 - 基于模板快速创建各种类型的爬虫
支持政府采购、高校采购、企业采购等多种数据源
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List


class ScraperGenerator:
    """爬虫生成器类"""

    def __init__(self, template_type: str, config: Dict[str, Any] = None):
        self.template_type = template_type.lower()
        self.config = config or {}

        # 验证模板类型
        valid_templates = ["government", "university", "enterprise", "custom"]
        if self.template_type not in valid_templates:
            raise ValueError(f"无效的模板类型: {template_type}. 支持: {', '.join(valid_templates)}")

    def generate_government_scraper(self, output_path: str, targets: List[str] = None):
        """生成政府采购网站爬虫"""
        targets = targets or ["ccgp.gov.cn"]

        scraper_code = f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
政府采购网站爬虫
自动爬取政府采购、招标公告、中标信息等
"""

import re
import time
import random
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import sqlite3


class GovernmentScraper:
    """政府采购网站爬虫类"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化爬虫

        Args:
            config: 爬虫配置字典
        """
        self.config = config
        self.session = requests.Session()
        self.logger = logging.getLogger(__name__)

        # 设置请求头
        self.session.headers.update({{
            'User-Agent': config.get('user_agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }})

        # 搜索关键词
        self.keywords = config.get('keywords', ['弱电', '智能化', '安防', '网络建设', '系统集成'])

    def search_procurement(self, keyword: str, days: int = 7) -> List[Dict[str, Any]]:
        """
        搜索采购信息

        Args:
            keyword: 搜索关键词
            days: 搜索最近几天的数据

        Returns:
            采购信息列表
        """
        try:
            # 构建搜索URL
            base_url = "https://search.ccgp.gov.cn/bxsearch"
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            end_date = datetime.now().strftime('%Y-%m-%d')

            params = {{
                'searchtype': '1',
                'page_index': '1',
                'bidSort': '0',
                'buyerName': '',
                'projectId': '',
                'pinMu': '0',
                'bidType': '0',
                'dbselect': 'bid',
                'kw': keyword,
                'start_time': start_date,
                'end_time': end_date,
                'timeType': '6',
                'displayZone': '',
                'zoneName': '',
                'agentName': '',
            }}

            results = []
            page = 1

            while True:
                params['page_index'] = str(page)

                response = self.session.get(base_url, params=params, timeout=self.config.get('timeout', 30))
                response.raise_for_status()

                soup = BeautifulSoup(response.content, 'html.parser')

                # 提取搜索结果
                items = self._parse_search_results(soup)
                if not items:
                    break

                results.extend(items)

                # 随机延时
                delay = random.uniform(*self.config.get('delay_range', [1, 3]))
                time.sleep(delay)

                page += 1
                if page > 10:  # 限制页数
                    break

            self.logger.info(f"关键词 '{{keyword}}' 搜索完成，获取 {{len(results)}} 条结果")
            return results

        except Exception as e:
            self.logger.error(f"搜索失败: {{e}}")
            return []

    def _parse_search_results(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """解析搜索结果页面"""
        results = []

        try:
            # 查找结果列表
            result_items = soup.find_all('li', class_='vT-srch-result-bid')

            for item in result_items:
                try:
                    # 提取标题和链接
                    title_elem = item.find('a', class_='vT-srch-result-list-title')
                    if not title_elem:
                        continue

                    title = title_elem.get_text(strip=True)
                    url = title_elem.get('href')
                    if not url.startswith('http'):
                        url = urljoin('https://www.ccgp.gov.cn', url)

                    # 提取其他信息
                    info_parts = item.find_all('span')
                    publish_date = ''
                    region = ''
                    procurement_type = ''

                    for part in info_parts:
                        text = part.get_text(strip=True)
                        if '发布时间' in text:
                            publish_date = text.replace('发布时间：', '').strip()
                        elif '行政区划' in text:
                            region = text.replace('行政区划：', '').strip()
                        elif '采购类型' in text:
                            procurement_type = text.replace('采购类型：', '').strip()

                    result = {{
                        'title': title,
                        'url': url,
                        'publish_date': publish_date,
                        'region': region,
                        'procurement_type': procurement_type,
                        'keyword': self.keywords[0],  # 当前关键词
                        'scraped_at': datetime.now().isoformat(),
                        'content': ''  # 稍后填充详细内容
                    }}

                    results.append(result)

                except Exception as e:
                    self.logger.warning(f"解析单个结果失败: {{e}}")
                    continue

        except Exception as e:
            self.logger.error(f"解析搜索结果页面失败: {{e}}")

        return results

    def get_detail_content(self, url: str) -> str:
        """
        获取详细内容

        Args:
            url: 详情页面URL

        Returns:
            页面内容文本
        """
        try:
            response = self.session.get(url, timeout=self.config.get('timeout', 30))
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # 移除脚本和样式
            for script in soup(["script", "style"]):
                script.decompose()

            # 尝试找到主要内容区域
            content_areas = [
                soup.find('div', class_='vF_detail_content'),
                soup.find('div', class_='content'),
                soup.find('div', id='content'),
                soup.find('article'),
                soup.find('main')
            ]

            for area in content_areas:
                if area:
                    return area.get_text(strip=True, separator='\\n')

            # 如果没找到特定区域，返回整个body的文本
            return soup.get_text(strip=True, separator='\\n')

        except Exception as e:
            self.logger.error(f"获取详细内容失败 {{url}}: {{e}}")
            return ''

    def scrape_all_keywords(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        爬取所有关键词的采购信息

        Args:
            days: 搜索最近几天的数据

        Returns:
            完整的采购信息列表
        """
        all_results = []

        for keyword in self.keywords:
            self.logger.info(f"开始搜索关键词: {{keyword}}")

            results = self.search_procurement(keyword, days)

            # 获取详细内容
            for result in results:
                if result['url']:
                    content = self.get_detail_content(result['url'])
                    result['content'] = content

                    # 随机延时
                    delay = random.uniform(*self.config.get('delay_range', [1, 3]))
                    time.sleep(delay)

            all_results.extend(results)

            # 关键词间延时
            time.sleep(random.uniform(2, 5))

        self.logger.info(f"所有关键词搜索完成，总计获取 {{len(all_results)}} 条数据")
        return all_results

    def filter_relevant_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        过滤相关的结果

        Args:
            results: 原始结果列表

        Returns:
            过滤后的结果列表
        """
        relevant_keywords = [
            '弱电', '智能化', '安防', '监控', '门禁', '楼宇自动化',
            '网络建设', '系统集成', '智慧', '数字化', '信息化',
            '机房', '综合布线', '会议系统', '广播系统'
        ]

        filtered_results = []

        for result in results:
            title = result.get('title', '').lower()
            content = result.get('content', '').lower()

            # 检查是否包含相关关键词
            is_relevant = any(keyword in title or keyword in content for keyword in relevant_keywords)

            if is_relevant:
                result['is_relevant'] = True
                result['relevance_score'] = sum(1 for keyword in relevant_keywords
                                               if keyword in title or keyword in content)
                filtered_results.append(result)
            else:
                result['is_relevant'] = False
                result['relevance_score'] = 0

        self.logger.info(f"过滤后保留 {{len(filtered_results)}} 条相关结果")
        return filtered_results


def main():
    """主函数 - 用于测试"""
    # 测试配置
    config = {{
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'delay_range': [1, 3],
        'timeout': 30,
        'keywords': ['弱电', '智能化', '安防']
    }}

    # 创建爬虫实例
    scraper = GovernmentScraper(config)

    # 执行爬取
    results = scraper.scrape_all_keywords(days=3)

    # 过滤相关结果
    relevant_results = scraper.filter_relevant_results(results)

    # 输出结果
    print(f"获取到 {{len(relevant_results)}} 条相关采购信息")
    for i, result in enumerate(relevant_results[:5], 1):
        print(f"{{i}}. {{result['title']}}")
        print(f"   发布时间: {{result['publish_date']}}")
        print(f"   地区: {{result['region']}}")
        print(f"   URL: {{result['url']}}")
        print()


if __name__ == "__main__":
    main()
'''

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(scraper_code)

    def generate_university_scraper(self, output_path: str, targets: List[str] = None):
        """生成高校采购爬虫"""
        targets = targets or ["tsinghua.edu.cn", "pku.edu.cn", "fudan.edu.cn"]

        scraper_code = f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
高校采购网站爬虫
自动爬取各大高校的采购公告、招标信息等
"""

import re
import time
import random
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse


class UniversityScraper:
    """高校采购网站爬虫类"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化爬虫

        Args:
            config: 爬虫配置字典
        """
        self.config = config
        self.session = requests.Session()
        self.logger = logging.getLogger(__name__)

        # 设置请求头
        self.session.headers.update({{
            'User-Agent': config.get('user_agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }})

        # 目标高校配置
        self.targets = {targets}

        # 搜索关键词
        self.keywords = config.get('keywords', ['弱电', '智能化', '安防', '设备采购'])

    def scrape_tsinghua(self, days: int = 30) -> List[Dict[str, Any]]:
        """爬取清华大学采购信息"""
        results = []

        try:
            # 清华大学采购网
            base_url = "http://www.tsinghua.edu.cn/cgcg/zbgg.htm"

            response = self.session.get(base_url, timeout=self.config.get('timeout', 30))
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # 查找采购公告列表
            news_list = soup.find_all('li', class_='news')

            for item in news_list:
                try:
                    # 提取标题和链接
                    link_elem = item.find('a')
                    if not link_elem:
                        continue

                    title = link_elem.get_text(strip=True)
                    url = urljoin(base_url, link_elem.get('href'))

                    # 提取发布时间
                    date_elem = item.find('span', class_='date')
                    publish_date = date_elem.get_text(strip=True) if date_elem else ''

                    # 检查是否为相关内容
                    if any(keyword in title for keyword in self.keywords):
                        result = {{
                            'title': title,
                            'url': url,
                            'publish_date': publish_date,
                            'university': '清华大学',
                            'scraped_at': datetime.now().isoformat(),
                            'content': ''
                        }}

                        # 获取详细内容
                        detail_content = self.get_detail_content(url)
                        result['content'] = detail_content

                        results.append(result)

                except Exception as e:
                    self.logger.warning(f"解析清华大学采购信息失败: {{e}}")
                    continue

        except Exception as e:
            self.logger.error(f"爬取清华大学采购信息失败: {{e}}")

        return results

    def scrape_pku(self, days: int = 30) -> List[Dict[str, Any]]:
        """爬取北京大学采购信息"""
        results = []

        try:
            # 北京大学采购网
            base_url = "https://www.pku.edu.cn/cgzb/index.htm"

            response = self.session.get(base_url, timeout=self.config.get('timeout', 30))
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # 查找采购公告列表
            news_items = soup.find_all('div', class_='news-item')

            for item in news_items:
                try:
                    # 提取标题和链接
                    link_elem = item.find('a')
                    if not link_elem:
                        continue

                    title = link_elem.get_text(strip=True)
                    url = urljoin(base_url, link_elem.get('href'))

                    # 提取发布时间
                    date_elem = item.find('span', class_='date')
                    publish_date = date_elem.get_text(strip=True) if date_elem else ''

                    # 检查是否为相关内容
                    if any(keyword in title for keyword in self.keywords):
                        result = {{
                            'title': title,
                            'url': url,
                            'publish_date': publish_date,
                            'university': '北京大学',
                            'scraped_at': datetime.now().isoformat(),
                            'content': ''
                        }}

                        # 获取详细内容
                        detail_content = self.get_detail_content(url)
                        result['content'] = detail_content

                        results.append(result)

                except Exception as e:
                    self.logger.warning(f"解析北京大学采购信息失败: {{e}}")
                    continue

        except Exception as e:
            self.logger.error(f"爬取北京大学采购信息失败: {{e}}")

        return results

    def get_detail_content(self, url: str) -> str:
        """获取详细内容"""
        try:
            response = self.session.get(url, timeout=self.config.get('timeout', 30))
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # 移除脚本和样式
            for script in soup(["script", "style"]):
                script.decompose()

            # 尝试找到主要内容区域
            content_areas = [
                soup.find('div', class_='content'),
                soup.find('div', class_='article-content'),
                soup.find('div', id='content'),
                soup.find('article')
            ]

            for area in content_areas:
                if area:
                    return area.get_text(strip=True, separator='\\n')

            return soup.get_text(strip=True, separator='\\n')

        except Exception as e:
            self.logger.error(f"获取详细内容失败 {{url}}: {{e}}")
            return ''

    def scrape_all_universities(self, days: int = 30) -> List[Dict[str, Any]]:
        """爬取所有目标高校的采购信息"""
        all_results = []

        for target in self.targets:
            self.logger.info(f"开始爬取高校: {{target}}")

            if 'tsinghua' in target:
                results = self.scrape_tsinghua(days)
            elif 'pku' in target or 'beijing' in target:
                results = self.scrape_pku(days)
            else:
                self.logger.warning(f"不支持的高校: {{target}}")
                continue

            all_results.extend(results)

            # 高校间延时
            time.sleep(random.uniform(3, 6))

        self.logger.info(f"所有高校爬取完成，总计获取 {{len(all_results)}} 条数据")
        return all_results


def main():
    """主函数 - 用于测试"""
    config = {{
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'delay_range': [2, 4],
        'timeout': 30,
        'keywords': ['弱电', '智能化', '安防']
    }}

    targets = ['tsinghua.edu.cn', 'pku.edu.cn']
    scraper = UniversityScraper(config)
    scraper.targets = targets

    results = scraper.scrape_all_universities(days=30)

    print(f"获取到 {{len(results)}} 条高校采购信息")
    for i, result in enumerate(results[:5], 1):
        print(f"{{i}}. {{result['title']}}")
        print(f"   高校: {{result['university']}}")
        print(f"   发布时间: {{result['publish_date']}}")
        print(f"   URL: {{result['url']}}")
        print()


if __name__ == "__main__":
    main()
'''

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(scraper_code)

    def generate_enterprise_scraper(self, output_path: str, targets: List[str] = None):
        """生成企业采购爬虫"""
        targets = targets or ["huawei.com", "tencent.com", "alibaba.com"]

        scraper_code = f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
企业采购网站爬虫
自动爬取大型企业的供应商招募、采购需求等
"""

import re
import time
import random
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse


class EnterpriseScraper:
    """企业采购网站爬虫类"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化爬虫

        Args:
            config: 爬虫配置字典
        """
        self.config = config
        self.session = requests.Session()
        self.logger = logging.getLogger(__name__)

        # 设置请求头
        self.session.headers.update({{
            'User-Agent': config.get('user_agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        }})

        # 目标企业配置
        self.targets = {targets}

        # 搜索关键词
        self.keywords = config.get('keywords', ['供应商', '招募', '采购', '招标'])

    def scrape_huawei(self, days: int = 30) -> List[Dict[str, Any]]:
        """爬取华为供应商信息"""
        results = []

        try:
            # 华为供应商招募页面
            base_url = "https://supplier.huawei.com"

            response = self.session.get(base_url, timeout=self.config.get('timeout', 30))
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # 查找供应商招募信息
            recruit_items = soup.find_all('div', class_='recruit-item')

            for item in recruit_items:
                try:
                    # 提取标题和链接
                    link_elem = item.find('a')
                    if not link_elem:
                        continue

                    title = link_elem.get_text(strip=True)
                    url = urljoin(base_url, link_elem.get('href'))

                    # 提取发布时间
                    date_elem = item.find('span', class_='date')
                    publish_date = date_elem.get_text(strip=True) if date_elem else ''

                    result = {{
                        'title': title,
                        'url': url,
                        'publish_date': publish_date,
                        'company': '华为',
                        'scraped_at': datetime.now().isoformat(),
                        'content': ''
                    }}

                    # 获取详细内容
                    detail_content = self.get_detail_content(url)
                    result['content'] = detail_content

                    results.append(result)

                except Exception as e:
                    self.logger.warning(f"解析华为供应商信息失败: {{e}}")
                    continue

        except Exception as e:
            self.logger.error(f"爬取华为供应商信息失败: {{e}}")

        return results

    def get_detail_content(self, url: str) -> str:
        """获取详细内容"""
        try:
            response = self.session.get(url, timeout=self.config.get('timeout', 30))
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # 移除脚本和样式
            for script in soup(["script", "style"]):
                script.decompose()

            # 尝试找到主要内容区域
            content_areas = [
                soup.find('div', class_='content'),
                soup.find('div', class_='article-content'),
                soup.find('div', id='content'),
                soup.find('article')
            ]

            for area in content_areas:
                if area:
                    return area.get_text(strip=True, separator='\\n')

            return soup.get_text(strip=True, separator='\\n')

        except Exception as e:
            self.logger.error(f"获取详细内容失败 {{url}}: {{e}}")
            return ''

    def scrape_all_enterprises(self, days: int = 30) -> List[Dict[str, Any]]:
        """爬取所有目标企业的采购信息"""
        all_results = []

        for target in self.targets:
            self.logger.info(f"开始爬取企业: {{target}}")

            if 'huawei' in target:
                results = self.scrape_huawei(days)
            else:
                self.logger.warning(f"不支持的企业: {{target}}")
                continue

            all_results.extend(results)

            # 企业间延时
            time.sleep(random.uniform(3, 6))

        self.logger.info(f"所有企业爬取完成，总计获取 {{len(all_results)}} 条数据")
        return all_results


def main():
    """主函数 - 用于测试"""
    config = {{
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'delay_range': [2, 4],
        'timeout': 30,
        'keywords': ['供应商', '招募', '采购']
    }}

    targets = ['huawei.com']
    scraper = EnterpriseScraper(config)
    scraper.targets = targets

    results = scraper.scrape_all_enterprises(days=30)

    print(f"获取到 {{len(results)}} 条企业采购信息")
    for i, result in enumerate(results[:5], 1):
        print(f"{{i}}. {{result['title']}}")
        print(f"   企业: {{result['company']}}")
        print(f"   发布时间: {{result['publish_date']}}")
        print(f"   URL: {{result['url']}}")
        print()


if __name__ == "__main__":
    main()
'''

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(scraper_code)

    def generate_scraper(self, output_dir: str = "src/scrapers", targets: List[str] = None):
        """根据模板类型生成爬虫"""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        if self.template_type == "government":
            output_path = output_dir / "government_scraper.py"
            self.generate_government_scraper(str(output_path), targets)
            print(f"✓ 生成政府采购爬虫: {output_path}")

        elif self.template_type == "university":
            output_path = output_dir / "university_scraper.py"
            self.generate_university_scraper(str(output_path), targets)
            print(f"✓ 生成高校采购爬虫: {output_path}")

        elif self.template_type == "enterprise":
            output_path = output_dir / "enterprise_scraper.py"
            self.generate_enterprise_scraper(str(output_path), targets)
            print(f"✓ 生成企业采购爬虫: {output_path}")

        elif self.template_type == "custom":
            # 生成自定义爬虫模板
            output_path = output_dir / "custom_scraper.py"
            self.generate_custom_scraper_template(str(output_path))
            print(f"✓ 生成自定义爬虫模板: {output_path}")

    def generate_custom_scraper_template(self, output_path: str):
        """生成自定义爬虫模板"""
        template_code = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自定义网站爬虫模板
基于此模板快速开发特定网站的爬虫
"""

import re
import time
import random
import logging
from datetime import datetime
from typing import List, Dict, Any
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse


class CustomScraper:
    """自定义网站爬虫类"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化爬虫

        Args:
            config: 爬虫配置字典
        """
        self.config = config
        self.session = requests.Session()
        self.logger = logging.getLogger(__name__)

        # 设置请求头
        self.session.headers.update({
            'User-Agent': config.get('user_agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        })

        # 目标网站配置
        self.base_url = config.get('base_url', 'https://example.com')
        self.keywords = config.get('keywords', [])

    def scrape_listings(self) -> List[Dict[str, Any]]:
        """
        爬取列表页面

        Returns:
            列表信息
        """
        results = []

        try:
            # TODO: 实现列表页面爬取逻辑
            # 1. 构建请求URL
            # 2. 发送HTTP请求
            # 3. 解析HTML内容
            # 4. 提取标题、链接、时间等信息

            # 示例代码框架：
            url = f"{self.base_url}/list"
            response = self.session.get(url, timeout=self.config.get('timeout', 30))
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # 查找列表项 - 根据实际网站结构调整选择器
            list_items = soup.find_all('div', class_='list-item')

            for item in list_items:
                try:
                    # 提取标题和链接
                    title_elem = item.find('a', class_='title')
                    if not title_elem:
                        continue

                    title = title_elem.get_text(strip=True)
                    url = urljoin(self.base_url, title_elem.get('href'))

                    # 提取其他信息
                    date_elem = item.find('span', class_='date')
                    publish_date = date_elem.get_text(strip=True) if date_elem else ''

                    # 检查关键词匹配
                    if any(keyword in title for keyword in self.keywords):
                        result = {
                            'title': title,
                            'url': url,
                            'publish_date': publish_date,
                            'source': 'custom_site',
                            'scraped_at': datetime.now().isoformat(),
                            'content': ''
                        }

                        # 获取详细内容
                        detail_content = self.get_detail_content(url)
                        result['content'] = detail_content

                        results.append(result)

                except Exception as e:
                    self.logger.warning(f"解析单个项目失败: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"爬取列表页面失败: {e}")

        return results

    def get_detail_content(self, url: str) -> str:
        """
        获取详细内容

        Args:
            url: 详情页面URL

        Returns:
            页面内容文本
        """
        try:
            response = self.session.get(url, timeout=self.config.get('timeout', 30))
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # 移除脚本和样式
            for script in soup(["script", "style"]):
                script.decompose()

            # TODO: 根据实际网站结构调整内容提取逻辑
            # 尝试找到主要内容区域
            content_areas = [
                soup.find('div', class_='content'),
                soup.find('div', class_='article-content'),
                soup.find('div', id='content'),
                soup.find('article')
            ]

            for area in content_areas:
                if area:
                    return area.get_text(strip=True, separator='\\n')

            return soup.get_text(strip=True, separator='\\n')

        except Exception as e:
            self.logger.error(f"获取详细内容失败 {url}: {e}")
            return ''

    def run(self) -> List[Dict[str, Any]]:
        """运行爬虫"""
        self.logger.info("开始爬取自定义网站")

        results = self.scrape_listings()

        self.logger.info(f"爬取完成，获取 {len(results)} 条数据")
        return results


def main():
    """主函数 - 用于测试"""
    # TODO: 根据实际网站配置参数
    config = {
        'base_url': 'https://example.com',
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'delay_range': [1, 3],
        'timeout': 30,
        'keywords': ['关键词1', '关键词2']
    }

    scraper = CustomScraper(config)
    results = scraper.run()

    print(f"获取到 {len(results)} 条数据")
    for i, result in enumerate(results[:5], 1):
        print(f"{i}. {result['title']}")
        print(f"   发布时间: {result['publish_date']}")
        print(f"   URL: {result['url']}")
        print()


if __name__ == "__main__":
    main()
'''

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(template_code)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="爬虫生成器 - 基于模板快速创建各种类型的爬虫",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python create_scraper.py --template government
  python create_scraper.py --template university --targets "tsinghua,pku,fudan"
  python create_scraper.py --template enterprise --targets "huawei,tencent"
  python create_scraper.py --template custom --output "src/scrapers/my_scraper.py"
        """
    )

    parser.add_argument(
        "--template",
        choices=["government", "university", "enterprise", "custom"],
        required=True,
        help="爬虫模板类型"
    )

    parser.add_argument(
        "--targets",
        help="目标网站列表，用逗号分隔 (如: tsinghua,pku,fudan)"
    )

    parser.add_argument(
        "--output",
        default="src/scrapers",
        help="输出目录 (默认: src/scrapers)"
    )

    parser.add_argument(
        "--config",
        help="配置文件路径 (JSON格式)"
    )

    args = parser.parse_args()

    try:
        # 解析目标列表
        targets = None
        if args.targets:
            targets = [target.strip() for target in args.targets.split(",")]

        # 加载配置
        config = {}
        if args.config:
            with open(args.config, 'r', encoding='utf-8') as f:
                config = json.load(f)

        # 生成爬虫
        generator = ScraperGenerator(args.template, config)
        generator.generate_scraper(args.output, targets)

        print(f"\n✅ 爬虫生成完成！")
        print(f"模板类型: {args.template}")
        if targets:
            print(f"目标网站: {', '.join(targets)}")
        print(f"输出位置: {args.output}")
        print("\n下一步:")
        print("1. 根据实际网站调整爬虫代码")
        print("2. 配置目标网站URL和选择器")
        print("3. 测试爬虫功能")
        print("4. 集成到主系统中")

    except Exception as e:
        print(f"❌ 爬虫生成失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()