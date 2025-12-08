# 爬虫策略和反爬虫技术文档

## 目录
1. [通用爬虫策略](#通用爬虫策略)
2. [反爬虫技术分析](#反爬虫技术分析)
3. [爬虫优化技巧](#爬虫优化技巧)
4. [法律法规合规](#法律法规合规)
5. [常见问题解决](#常见问题解决)

## 通用爬虫策略

### 1. 基础爬虫架构

#### 单线程爬虫
```python
import requests
from bs4 import BeautifulSoup
import time
import random

class BasicCrawler:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def crawl_page(self, url):
        response = self.session.get(url, timeout=30)
        soup = BeautifulSoup(response.content, 'html.parser')
        return soup
```

#### 多线程爬虫
```python
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue

class MultiThreadCrawler:
    def __init__(self, max_workers=5):
        self.max_workers = max_workers
        self.session = requests.Session()

    def crawl_with_threads(self, urls):
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(self.crawl_page, url) for url in urls]
            results = [future.result() for future in as_completed(futures)]
        return results
```

#### 异步爬虫 (asyncio)
```python
import asyncio
import aiohttp
from bs4 import BeautifulSoup

class AsyncCrawler:
    async def crawl_page(self, session, url):
        async with session.get(url) as response:
            content = await response.text()
            return BeautifulSoup(content, 'html.parser')

    async def crawl_multiple(self, urls):
        async with aiohttp.ClientSession() as session:
            tasks = [self.crawl_page(session, url) for url in urls]
            return await asyncio.gather(*tasks)
```

### 2. 数据采集策略

#### 深度优先策略 (DFS)
- 适用于网站结构层次分明
- 优先爬取深层页面
- 内存占用相对较少

#### 广度优先策略 (BFS)
- 适用于网站层级扁平
- 优先爬取同级别页面
- 更快获取最新数据

#### 优先级队列策略
```python
import heapq
from urllib.parse import urlparse

class PriorityQueueCrawler:
    def __init__(self):
        self.priority_queue = []
        self.visited = set()

    def add_url(self, url, priority):
        if url not in self.visited:
            heapq.heappush(self.priority_queue, (priority, url))

    def get_next_url(self):
        if self.priority_queue:
            _, url = heapq.heappop(self.priority_queue)
            self.visited.add(url)
            return url
        return None
```

### 3. 数据存储策略

#### 文件存储
```python
import json
import csv
from pathlib import Path

class FileStorage:
    def __init__(self, base_dir="data"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)

    def save_json(self, data, filename):
        filepath = self.base_dir / f"{filename}.json"
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def save_csv(self, data, filename):
        filepath = self.base_dir / f"{filename}.csv"
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
```

#### 数据库存储
```python
import sqlite3
import json
from datetime import datetime

class DatabaseStorage:
    def __init__(self, db_path="data/crawler.db"):
        self.conn = sqlite3.connect(db_path)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE,
                title TEXT,
                content TEXT,
                crawl_time TIMESTAMP,
                metadata TEXT
            )
        ''')
        self.conn.commit()

    def save_page(self, url, title, content, metadata=None):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO pages
            (url, title, content, crawl_time, metadata)
            VALUES (?, ?, ?, ?, ?)
        ''', (url, title, content, datetime.now(), json.dumps(metadata or {})))
        self.conn.commit()
```

## 反爬虫技术分析

### 1. User-Agent检测

#### User-Agent池
```python
user_agents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15'
]

import random

def get_random_user_agent():
    return random.choice(user_agents)
```

#### 动态User-Agent生成
```python
from fake_useragent import UserAgent

ua = UserAgent()
def get_realistic_user_agent():
    return ua.random
```

### 2. IP地址检测和代理

#### 代理池管理
```python
import requests
from itertools import cycle

class ProxyPool:
    def __init__(self, proxy_list):
        self.proxy_list = proxy_list
        self.proxy_cycle = cycle(proxy_list)
        self.current_proxy = None

    def get_proxy(self):
        self.current_proxy = next(self.proxy_cycle)
        return {
            'http': self.current_proxy,
            'https': self.current_proxy
        }

    def test_proxy(self, proxy):
        try:
            response = requests.get(
                'https://httpbin.org/ip',
                proxies={'http': proxy, 'https': proxy},
                timeout=10
            )
            return response.status_code == 200
        except:
            return False
```

#### 免费代理API
```python
def get_free_proxies():
    """获取免费代理列表"""
    proxy_sources = [
        'https://www.proxy-list.download/api/v1/get?type=http',
        'https://api.proxyscrape.com/v2/?request=get&protocol=http&country=all&ssl=all&anonymity=all',
    ]

    proxies = []
    for source in proxy_sources:
        try:
            response = requests.get(source, timeout=10)
            # 解析响应获取代理列表
            # 实际解析逻辑取决于API返回格式
        except Exception as e:
            print(f"获取代理失败: {e}")

    return proxies
```

### 3. 请求频率控制

#### 固定延时
```python
import time
import random

class RateLimiter:
    def __init__(self, min_delay=1, max_delay=3):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.last_request_time = 0

    def wait(self):
        current_time = time.time()
        elapsed = current_time - self.last_request_time

        delay = random.uniform(self.min_delay, self.max_delay)
        if elapsed < delay:
            time.sleep(delay - elapsed)

        self.last_request_time = time.time()
```

#### 自适应延时
```python
class AdaptiveRateLimiter:
    def __init__(self, initial_delay=1):
        self.current_delay = initial_delay
        self.min_delay = 0.5
        self.max_delay = 10
        self.success_count = 0
        self.error_count = 0

    def record_success(self):
        self.success_count += 1
        if self.success_count > 5:
            self.current_delay = max(self.min_delay, self.current_delay * 0.9)
            self.success_count = 0

    def record_error(self):
        self.error_count += 1
        if self.error_count > 2:
            self.current_delay = min(self.max_delay, self.current_delay * 1.5)
            self.error_count = 0

    def wait(self):
        time.sleep(self.current_delay)
```

### 4. 验证码识别

#### OCR识别
```python
import pytesseract
from PIL import Image
import cv2
import numpy as np

class CaptchaOCR:
    def __init__(self):
        pass

    def preprocess_image(self, image_path):
        """图像预处理"""
        image = cv2.imread(image_path)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # 二值化
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)

        # 降噪
        denoised = cv2.medianBlur(binary, 3)

        return denoised

    def recognize_captcha(self, image_path):
        """识别验证码"""
        processed = self.preprocess_image(image_path)

        # 使用Tesseract OCR识别
        text = pytesseract.image_to_string(processed, config='--psm 7')

        return text.strip()
```

#### 第三方验证码服务
```python
class CaptchaService:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.captcha-service.com"

    def solve_captcha(self, image_data):
        """调用第三方验证码识别服务"""
        payload = {
            'apikey': self.api_key,
            'method': 'base64',
            'body': image_data
        }

        response = requests.post(f"{self.base_url}/solve", data=payload)
        result = response.json()

        return result.get('solution', '')
```

### 5. Cookie和Session管理

#### Session持久化
```python
import pickle
from pathlib import Path

class SessionManager:
    def __init__(self, session_file="session.pkl"):
        self.session_file = Path(session_file)
        self.session = requests.Session()

        if self.session_file.exists():
            self.load_session()

    def save_session(self):
        """保存Session状态"""
        with open(self.session_file, 'wb') as f:
            pickle.dump(self.session.cookies, f)

    def load_session(self):
        """加载Session状态"""
        with open(self.session_file, 'rb') as f:
            self.session.cookies.update(pickle.load(f))

    def login(self, login_url, credentials):
        """模拟登录"""
        response = self.session.post(login_url, data=credentials)
        if response.status_code == 200:
            self.save_session()
            return True
        return False
```

### 6. JavaScript渲染检测

#### Selenium + Chrome
```python
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class SeleniumCrawler:
    def __init__(self, headless=True):
        chrome_options = Options()
        if headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')

        self.driver = webdriver.Chrome(options=chrome_options)

    def get_page_source(self, url, wait_time=10):
        """获取动态渲染后的页面源码"""
        self.driver.get(url)

        # 等待页面加载完成
        WebDriverWait(self.driver, wait_time).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        return self.driver.page_source
```

#### Playwright
```python
from playwright.sync_api import sync_playwright

class PlaywrightCrawler:
    def __init__(self):
        self.browser = None
        self.page = None

    def start_browser(self, headless=True):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=headless)
        self.page = self.browser.new_page()

    def get_page_content(self, url):
        """获取页面内容"""
        if not self.page:
            self.start_browser()

        self.page.goto(url)
        return self.page.content()

    def close_browser(self):
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
```

## 爬虫优化技巧

### 1. 性能优化

#### 连接池
```python
import requests.adapters

# 配置连接池
session = requests.Session()
adapter = requests.adapters.HTTPAdapter(
    pool_connections=20,
    pool_maxsize=20,
    max_retries=3
)
session.mount('http://', adapter)
session.mount('https://', adapter)
```

#### 异步I/O优化
```python
import aiohttp
import asyncio
from asyncio import Semaphore

class AsyncCrawlerOptimized:
    def __init__(self, max_concurrent=10):
        self.semaphore = Semaphore(max_concurrent)
        self.session = None

    async def crawl_with_semaphore(self, url):
        async with self.semaphore:
            return await self.crawl_single(url)

    async def crawl_single(self, url):
        async with self.session.get(url) as response:
            return await response.text()

    async def crawl_batch(self, urls):
        connector = aiohttp.TCPConnector(limit=20)
        async with aiohttp.ClientSession(connector=connector) as session:
            self.session = session
            tasks = [self.crawl_with_semaphore(url) for url in urls]
            return await asyncio.gather(*tasks, return_exceptions=True)
```

### 2. 内存优化

#### 流式处理
```python
import ijson

class StreamProcessor:
    def process_large_json(self, file_path):
        """流式处理大JSON文件"""
        with open(file_path, 'rb') as file:
            # 逐个解析对象，避免内存溢出
            parser = ijson.items(file, 'item')
            for item in parser:
                yield item

    def save_streaming(self, items, file_path):
        """流式保存大文件"""
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write('[')
            first = True
            for item in items:
                if not first:
                    file.write(',')
                json.dump(item, file, ensure_ascii=False)
                first = False
            file.write(']')
```

#### 分页处理
```python
class PaginationHandler:
    def __init__(self, session, base_url):
        self.session = session
        self.base_url = base_url

    def crawl_all_pages(self, max_pages=None):
        """爬取所有分页数据"""
        page = 1
        all_data = []

        while True:
            if max_pages and page > max_pages:
                break

            url = f"{self.base_url}?page={page}"
            response = self.session.get(url)

            if response.status_code != 200:
                break

            data = self.parse_page(response.text)
            if not data:
                break

            all_data.extend(data)
            page += 1

            # 进度显示
            print(f"已爬取第 {page-1} 页，累计 {len(all_data)} 条数据")

        return all_data
```

### 3. 数据清洗优化

#### 数据去重
```python
class DataDeduplicator:
    def __init__(self):
        self.seen_urls = set()
        self.seen_hashes = set()

    def is_duplicate_by_url(self, item):
        """基于URL去重"""
        url = item.get('url', '')
        if url in self.seen_urls:
            return True
        self.seen_urls.add(url)
        return False

    def is_duplicate_by_content(self, item):
        """基于内容哈希去重"""
        import hashlib
        content = item.get('title', '') + item.get('content', '')
        content_hash = hashlib.md5(content.encode()).hexdigest()

        if content_hash in self.seen_hashes:
            return True
        self.seen_hashes.add(content_hash)
        return False

    def filter_duplicates(self, items):
        """过滤重复项"""
        filtered = []
        for item in items:
            if not (self.is_duplicate_by_url(item) or self.is_duplicate_by_content(item)):
                filtered.append(item)
        return filtered
```

## 法律法规合规

### 1. robots.txt遵守

```python
import urllib.robotparser

class RobotsChecker:
    def __init__(self):
        self.parsers = {}

    def can_fetch(self, user_agent, url):
        """检查是否允许爬取"""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"

        if base_url not in self.parsers:
            self.parsers[base_url] = urllib.robotparser.RobotFileParser()
            robots_url = f"{base_url}/robots.txt"
            self.parsers[base_url].set_url(robots_url)
            self.parsers[base_url].read()

        return self.parsers[base_url].can_fetch(user_agent, url)

    def crawl_delay(self, user_agent, url):
        """获取爬取延时要求"""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"

        if base_url in self.parsers:
            return self.parsers[base_url].crawl_delay(user_agent) or 1
        return 1
```

### 2. 隐私保护

#### 个人信息脱敏
```python
import re

class PrivacyProtector:
    def __init__(self):
        self.phone_pattern = re.compile(r'1[3-9]\d{9}')
        self.email_pattern = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
        self.id_pattern = re.compile(r'\d{17}[\dXx]')  # 身份证

    def mask_phone(self, text):
        """手机号脱敏"""
        return self.phone_pattern.sub(lambda m: f"{m.group()[:3]}****{m.group()[-4:]}", text)

    def mask_email(self, text):
        """邮箱脱敏"""
        return self.email_pattern.sub(lambda m: f"{m.group()[:2]}***@{m.group().split('@')[1]}", text)

    def mask_id(self, text):
        """身份证脱敏"""
        return self.id_pattern.sub(lambda m: f"{m.group()[:6]}********{m.group()[-4:]}", text)

    def protect_data(self, text):
        """数据脱敏处理"""
        text = self.mask_phone(text)
        text = self.mask_email(text)
        text = self.mask_id(text)
        return text
```

### 3. 使用条款检查

```python
class TermsChecker:
    def __init__(self):
        self.blocked_domains = set()
        self.allowed_domains = set()

    def is_allowed_domain(self, url):
        """检查域名是否在允许列表中"""
        from urllib.parse import urlparse
        domain = urlparse(url).netloc

        if self.allowed_domains:
            return domain in self.allowed_domains
        if self.blocked_domains:
            return domain not in self.blocked_domains
        return True

    def add_blocked_domain(self, domain):
        """添加禁止爬取的域名"""
        self.blocked_domains.add(domain)

    def add_allowed_domain(self, domain):
        """添加允许爬取的域名"""
        self.allowed_domains.add(domain)
```

## 常见问题解决

### 1. 网络问题处理

#### 连接超时
```python
import requests
from requests.exceptions import Timeout, ConnectionError

def robust_request(url, max_retries=3, timeout=30):
    """健壮的请求函数"""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            return response
        except Timeout:
            print(f"请求超时，重试 {attempt + 1}/{max_retries}")
        except ConnectionError:
            print(f"连接错误，重试 {attempt + 1}/{max_retries}")
        except Exception as e:
            print(f"未知错误: {e}")
            break

        if attempt < max_retries - 1:
            time.sleep(2 ** attempt)  # 指数退避

    return None
```

#### 网络错误恢复
```python
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def create_resilient_session():
    """创建具有自动恢复能力的Session"""
    session = requests.Session()

    # 配置重试策略
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    return session
```

### 2. 数据质量问题

#### 编码问题解决
```python
import chardet

def detect_encoding(content):
    """检测内容编码"""
    result = chardet.detect(content)
    return result['encoding']

def decode_content(content, encoding=None):
    """安全解码内容"""
    if not encoding:
        encoding = detect_encoding(content)

    try:
        return content.decode(encoding)
    except:
        # 备用解码方案
        for enc in ['utf-8', 'gbk', 'gb2312', 'latin-1']:
            try:
                return content.decode(enc)
            except:
                continue

        # 最后使用替换策略
        return content.decode('utf-8', errors='replace')
```

#### 数据完整性检查
```python
class DataValidator:
    def __init__(self):
        pass

    def validate_item(self, item):
        """验证单个数据项"""
        required_fields = ['url', 'title', 'content']

        for field in required_fields:
            if not item.get(field):
                return False, f"缺少字段: {field}"

        # 检查URL格式
        from urllib.parse import urlparse
        parsed = urlparse(item['url'])
        if not parsed.scheme or not parsed.netloc:
            return False, "URL格式无效"

        # 检查内容长度
        if len(item['content']) < 10:
            return False, "内容过短"

        return True, "验证通过"

    def validate_batch(self, items):
        """批量验证数据"""
        valid_items = []
        error_count = 0

        for item in items:
            is_valid, message = self.validate_item(item)
            if is_valid:
                valid_items.append(item)
            else:
                error_count += 1
                print(f"数据验证失败: {message}")

        return valid_items, error_count
```

### 3. 调试和监控

#### 日志记录
```python
import logging
from datetime import datetime

class CrawlerLogger:
    def __init__(self, log_file="crawler.log"):
        self.logger = logging.getLogger('crawler')
        self.logger.setLevel(logging.INFO)

        # 文件处理器
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)

        # 控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # 格式化器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def log_crawl_start(self, url):
        """记录开始爬取"""
        self.logger.info(f"开始爬取: {url}")

    def log_crawl_success(self, url, data_size):
        """记录成功爬取"""
        self.logger.info(f"爬取成功: {url}, 数据大小: {data_size}")

    def log_crawl_error(self, url, error):
        """记录爬取错误"""
        self.logger.error(f"爬取失败: {url}, 错误: {error}")
```

#### 进度监控
```python
import time
from tqdm import tqdm

class ProgressMonitor:
    def __init__(self, total_tasks):
        self.total_tasks = total_tasks
        self.completed_tasks = 0
        self.start_time = time.time()
        self.progress_bar = tqdm(total=total_tasks, desc="爬取进度")

    def update(self, success=True):
        """更新进度"""
        self.completed_tasks += 1
        self.progress_bar.update(1)

        # 计算预估剩余时间
        elapsed = time.time() - self.start_time
        if self.completed_tasks > 0:
            avg_time_per_task = elapsed / self.completed_tasks
            remaining_tasks = self.total_tasks - self.completed_tasks
            eta = remaining_tasks * avg_time_per_task
            self.progress_bar.set_postfix({
                '成功率': f'{self.success_count/self.completed_tasks*100:.1f}%',
                '剩余时间': f'{eta/60:.1f}分钟'
            })

    def close(self):
        """关闭进度条"""
        self.progress_bar.close()
        total_time = time.time() - self.start_time
        print(f"总共耗时: {total_time/60:.2f}分钟")
        print(f"完成任务: {self.completed_tasks}/{self.total_tasks}")
```

这份文档提供了全面的爬虫开发指南，涵盖了从基础架构到高级优化的各个方面，特别针对政府采购、高校、企业等目标网站的爬虫开发需求进行了优化。