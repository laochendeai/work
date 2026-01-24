"""
Playwright浏览器管理器
封装浏览器操作，提供简单的API
"""
import logging
import random
import time
from typing import Optional
from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext

from config.settings import (
    BROWSER_TYPE,
    BROWSER_HEADLESS,
    BROWSER_TIMEOUT,
    BROWSER_NAVIGATION_TIMEOUT,
    USER_AGENT,
    DELAY_MIN,
    DELAY_MAX,
)

logger = logging.getLogger(__name__)


class PlaywrightFetcher:
    """Playwright浏览器管理器"""

    def __init__(self):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self._initialized = False

    def start(self):
        """启动浏览器"""
        if self._initialized:
            return

        try:
            self.playwright_obj = sync_playwright().start()
            browser_launcher = getattr(self.playwright_obj, BROWSER_TYPE)
            self.browser = browser_launcher.launch(
                headless=BROWSER_HEADLESS,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-setuid-sandbox'
                ]
            )

            # 创建上下文（模拟真实浏览器）
            self.context = self.browser.new_context(
                user_agent=USER_AGENT,
                viewport={'width': 1920, 'height': 1080},
                locale='zh-CN',
                timezone_id='Asia/Shanghai'
            )

            # 创建页面
            self.page = self.context.new_page()
            self.page.set_default_timeout(BROWSER_TIMEOUT)
            self.page.set_default_navigation_timeout(BROWSER_NAVIGATION_TIMEOUT)

            self._initialized = True
            logger.info(f"浏览器已启动 (类型={BROWSER_TYPE}, 无头={BROWSER_HEADLESS})")

        except Exception as e:
            logger.error(f"启动浏览器失败: {e}")
            self.stop()
            raise

    def stop(self):
        """停止浏览器"""
        try:
            if self.page:
                self.page.close()
                self.page = None
            if self.context:
                self.context.close()
                self.context = None
            if self.browser:
                self.browser.close()
                self.browser = None
            if hasattr(self, 'playwright_obj') and self.playwright_obj:
                self.playwright_obj.stop()
                self.playwright_obj = None
            self._initialized = False
            logger.info("浏览器已关闭")
        except Exception as e:
            logger.error(f"关闭浏览器失败: {e}")

    def get_page(self, url: str, wait_for: str = "networkidle") -> Optional[str]:
        """
        获取页面内容

        Args:
            url: 要访问的URL
            wait_for: 等待条件 (networkidle, load, domcontentloaded)

        Returns:
            页面HTML内容，失败返回None
        """
        if not self._initialized:
            self.start()

        try:
            # 访问页面
            if wait_for == "networkidle":
                self.page.goto(url, wait_until="networkidle", timeout=BROWSER_NAVIGATION_TIMEOUT)
            elif wait_for == "load":
                self.page.goto(url, wait_until="load", timeout=BROWSER_NAVIGATION_TIMEOUT)
            else:
                self.page.goto(url, wait_until="domcontentloaded", timeout=BROWSER_NAVIGATION_TIMEOUT)

            # 随机延迟，避免请求过快
            delay = random.uniform(DELAY_MIN, DELAY_MAX)
            time.sleep(delay)

            # 获取页面内容
            html = self.page.content()
            logger.debug(f"成功获取页面: {url} (长度: {len(html)})")
            return html

        except Exception as e:
            logger.error(f"获取页面失败 {url}: {e}")
            return None

    def __enter__(self):
        """上下文管理器入口"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.stop()
