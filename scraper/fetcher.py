"""
Playwright浏览器管理器
封装浏览器操作，提供简单的API
增加人类行为模拟以降低被封禁风险
"""
import logging
import random
import time
import os
import sys
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
    DETAIL_DELAY_MIN,
    DETAIL_DELAY_MAX,
    SIMULATE_HUMAN_BEHAVIOR,
)

logger = logging.getLogger(__name__)


class HumanBehaviorSimulator:
    """人类行为模拟器"""
    
    @staticmethod
    def random_delay(min_sec: float, max_sec: float, label: str = ""):
        """随机延迟"""
        delay = random.uniform(min_sec, max_sec)
        if label:
            logger.debug(f"[延迟] {label}: {delay:.1f}秒")
        time.sleep(delay)
        return delay
    
    @staticmethod
    def simulate_scroll(page: Page, scroll_times: int = None):
        """模拟随机滚动页面"""
        if scroll_times is None:
            scroll_times = random.randint(1, 3)
        
        for i in range(scroll_times):
            # 随机滚动距离
            scroll_distance = random.randint(200, 500)
            direction = random.choice([1, 1, 1, -1])  # 75%向下，25%向上
            
            try:
                page.evaluate(f"window.scrollBy(0, {scroll_distance * direction})")
                time.sleep(random.uniform(0.3, 0.8))
            except Exception:
                pass
    
    @staticmethod
    def simulate_mouse_move(page: Page):
        """模拟鼠标随机移动"""
        try:
            viewport = page.viewport_size
            if viewport:
                x = random.randint(100, viewport['width'] - 100)
                y = random.randint(100, min(600, viewport['height'] - 100))
                page.mouse.move(x, y)
                time.sleep(random.uniform(0.1, 0.3))
        except Exception:
            pass
    
    @staticmethod
    def simulate_reading(page: Page, min_sec: float = 2, max_sec: float = 5):
        """模拟阅读行为：滚动 + 停留"""
        # 随机滚动几次
        HumanBehaviorSimulator.simulate_scroll(page, random.randint(1, 2))
        # 模拟阅读停留
        HumanBehaviorSimulator.random_delay(min_sec, max_sec, "阅读页面")


class PlaywrightFetcher:
    """Playwright浏览器管理器"""

    def __init__(self):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self._initialized = False
        self.human_sim = HumanBehaviorSimulator()
        self._request_count = 0

    def start(self):
        """启动浏览器"""
        if self._initialized:
            return

        try:
            self.playwright_obj = sync_playwright().start()
            browser_launcher = getattr(self.playwright_obj, BROWSER_TYPE)

            # Determine browser executable path
            launch_kwargs = {
                'headless': BROWSER_HEADLESS,
                'args': [
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process',
                ]
            }

            # In frozen mode, explicitly set the browser executable path
            if getattr(sys, 'frozen', False):
                browsers_path = os.environ.get('PLAYWRIGHT_BROWSERS_PATH', '')
                logger.info(f"[DEBUG] Frozen mode detected. PLAYWRIGHT_BROWSERS_PATH={browsers_path}")
                
                # Check if path exists, if not, try root variants
                if not browsers_path or not os.path.exists(browsers_path):
                     logger.warning(f"[WARNING] Browsers path not found: {browsers_path}")
                     # Try to find next to executable
                     exe_path = os.path.dirname(os.path.abspath(sys.executable))
                     candidates = [
                         os.path.join(exe_path, "browsers"),
                         os.path.join(os.path.dirname(exe_path), "browsers"),
                     ]
                     for c in candidates:
                         if os.path.isdir(c):
                             browsers_path = c
                             logger.info(f"[FIX] Found browsers at: {browsers_path}")
                             break

                if browsers_path and os.path.isdir(browsers_path):
                    logger.info(f"[DEBUG] Browsers directory exists: {browsers_path}")

                    # Find the browser executable by walking the directory
                    import glob
                    exe_name = 'chrome.exe' if BROWSER_TYPE == 'chromium' else (
                        'firefox.exe' if BROWSER_TYPE == 'firefox' else 'webkit.exe'
                    )

                    # Try multiple patterns
                    patterns = [
                        os.path.join(browsers_path, 'chromium-*', 'chrome-win', exe_name),
                        os.path.join(browsers_path, 'firefox-*', 'firefox', exe_name),
                        os.path.join(browsers_path, 'webkit-*', 'playwright', exe_name),
                    ]

                    matches = []
                    for pattern in patterns:
                        matches = glob.glob(pattern)
                        if matches:
                            logger.info(f"[DEBUG] Found browser at: {matches[0]}")
                            break

                    if matches:
                        launch_kwargs['executable_path'] = matches[0]
                        logger.info(f"[INFO] Using browser at: {matches[0]}")
                    else:
                        logger.warning(f"[WARNING] Browser not found. Tried patterns: {patterns}")
                        # List what's in the browsers directory
                        try:
                            contents = os.listdir(browsers_path)
                            logger.warning(f"[DEBUG] Browsers directory contents: {contents}")
                        except Exception as e:
                            logger.warning(f"[DEBUG] Could not list browsers directory: {e}")
                else:
                    logger.warning(f"[WARNING] Browsers path not found or not a directory: {browsers_path}")

            self.browser = browser_launcher.launch(**launch_kwargs)

            # 创建上下文（模拟真实浏览器）
            self.context = self.browser.new_context(
                user_agent=USER_AGENT,
                viewport={'width': 1920, 'height': 1080},
                locale='zh-CN',
                timezone_id='Asia/Shanghai',
                # 添加更多真实浏览器特征
                java_script_enabled=True,
                has_touch=False,
                is_mobile=False,
                device_scale_factor=1,
            )
            
            # 注入反检测脚本
            self.context.add_init_script("""
                // 隐藏 webdriver 标志
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                // 模拟真实的 chrome 对象
                window.chrome = {
                    runtime: {}
                };
                
                // 修改 permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
            """)

            # 创建页面
            self.page = self.context.new_page()
            self.page.set_default_timeout(BROWSER_TIMEOUT)
            self.page.set_default_navigation_timeout(BROWSER_NAVIGATION_TIMEOUT)

            self._initialized = True
            self._request_count = 0
            logger.info(f"浏览器已启动 (类型={BROWSER_TYPE}, 无头={BROWSER_HEADLESS}, 人类模拟={SIMULATE_HUMAN_BEHAVIOR})")

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
            logger.info(f"浏览器已关闭 (本次共请求 {self._request_count} 个页面)")
        except Exception as e:
            logger.error(f"关闭浏览器失败: {e}")

    def get_page(self, url: str, wait_for: str = "networkidle", is_detail: bool = True) -> Optional[str]:
        """
        获取页面内容

        Args:
            url: 要访问的URL
            wait_for: 等待条件 (networkidle, load, domcontentloaded)
            is_detail: 是否是详情页（详情页使用更长延迟）

        Returns:
            页面HTML内容，失败返回None
        """
        if not self._initialized:
            self.start()

        try:
            self._request_count += 1
            
            # 请求前随机短暂延迟
            if self._request_count > 1:
                pre_delay = random.uniform(0.5, 1.5)
                time.sleep(pre_delay)
            
            # 访问页面
            if wait_for == "networkidle":
                self.page.goto(url, wait_until="networkidle", timeout=BROWSER_NAVIGATION_TIMEOUT)
            elif wait_for == "load":
                self.page.goto(url, wait_until="load", timeout=BROWSER_NAVIGATION_TIMEOUT)
            else:
                self.page.goto(url, wait_until="domcontentloaded", timeout=BROWSER_NAVIGATION_TIMEOUT)

            # 人类行为模拟
            if SIMULATE_HUMAN_BEHAVIOR:
                # 模拟鼠标移动
                self.human_sim.simulate_mouse_move(self.page)
                
                # 模拟阅读（滚动 + 延迟）
                if is_detail:
                    self.human_sim.simulate_reading(
                        self.page, 
                        DETAIL_DELAY_MIN, 
                        DETAIL_DELAY_MAX
                    )
                else:
                    self.human_sim.simulate_scroll(self.page, 1)
                    self.human_sim.random_delay(DELAY_MIN, DELAY_MAX, "页面加载后")
            else:
                # 即使不模拟人类行为，也要有基础延迟
                if is_detail:
                    delay = random.uniform(DETAIL_DELAY_MIN, DETAIL_DELAY_MAX)
                else:
                    delay = random.uniform(DELAY_MIN, DELAY_MAX)
                time.sleep(delay)

            # 获取页面内容
            html = self.page.content()
            logger.debug(f"成功获取页面 [{self._request_count}]: {url[:60]}... (长度: {len(html)})")
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

