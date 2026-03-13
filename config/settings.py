"""
全局配置设置
"""

import os
from pathlib import Path

# 项目根目录
import sys

if getattr(sys, "frozen", False):
    # 如果是打包后的 exe，使用 exe 所在目录
    BASE_DIR = Path(sys.executable).parent
else:
    # 开发环境
    BASE_DIR = Path(__file__).parent.parent

# 数据目录
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
EXPORT_DIR = DATA_DIR / "exports"
EXPORT_DIR.mkdir(exist_ok=True)

# 数据库路径
DB_PATH = DATA_DIR / "gp.db"


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    return int(value)


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    return float(value)


# ============ 浏览器设置 ============
BROWSER_TYPE = os.getenv(
    "BROWSER_TYPE", "chromium"
)  # 浏览器类型: chromium, firefox, webkit
BROWSER_HEADLESS = _env_bool("BROWSER_HEADLESS", True)  # 无头模式
BROWSER_TIMEOUT = _env_int("BROWSER_TIMEOUT", 30000)  # 页面加载超时(毫秒)
BROWSER_NAVIGATION_TIMEOUT = _env_int(
    "BROWSER_NAVIGATION_TIMEOUT", 60000
)  # 导航超时(毫秒)
DETAIL_WAIT_UNTIL = os.getenv("DETAIL_WAIT_UNTIL", "domcontentloaded")
HTTP_FETCH_TIMEOUT = _env_int("HTTP_FETCH_TIMEOUT", 15)
HTTP_FETCH_ENABLED = _env_bool("HTTP_FETCH_ENABLED", True)
HTTP_PREFETCH_WORKERS = _env_int("HTTP_PREFETCH_WORKERS", 4)

# ============ 整理设置 ============
MAX_PAGES = 5  # 每个源最多整理页数（保守设置）
MAX_ITEMS_PER_PAGE = 50  # 每页最多提取条目

# ============ 延迟设置（防封禁） ============
# 基础请求延迟
DELAY_MIN = _env_float("DELAY_MIN", 0.5)  # 请求间最小延迟(秒)
DELAY_MAX = _env_float("DELAY_MAX", 1.5)  # 请求间最大延迟(秒)

# 详情页抓取延迟（较长，模拟阅读行为）
DETAIL_DELAY_MIN = _env_float("DETAIL_DELAY_MIN", 0.5)  # 详情页抓取最小延迟(秒)
DETAIL_DELAY_MAX = _env_float("DETAIL_DELAY_MAX", 2.0)  # 详情页抓取最大延迟(秒)

# 翻页延迟
PAGE_TURN_DELAY_MIN = _env_float("PAGE_TURN_DELAY_MIN", 1.5)  # 翻页最小延迟(秒)
PAGE_TURN_DELAY_MAX = _env_float("PAGE_TURN_DELAY_MAX", 3.0)  # 翻页最大延迟(秒)

# 关键词切换延迟（较长，模拟新搜索行为）
KEYWORD_SWITCH_DELAY_MIN = _env_float(
    "KEYWORD_SWITCH_DELAY_MIN", 2.0
)  # 关键词切换最小延迟(秒)
KEYWORD_SWITCH_DELAY_MAX = _env_float(
    "KEYWORD_SWITCH_DELAY_MAX", 5.0
)  # 关键词切换最大延迟(秒)

# 是否模拟人类行为（随机滚动、鼠标移动等）
SIMULATE_HUMAN_BEHAVIOR = _env_bool("SIMULATE_HUMAN_BEHAVIOR", False)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# ============ 重试设置 ============
MAX_RETRIES = _env_int("MAX_RETRIES", 2)  # 最大重试次数
RETRY_DELAY = _env_float("RETRY_DELAY", 2.0)  # 重试延迟(秒)

# ============ 日志设置 ============
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR
LOG_FILE = DATA_DIR / "scraper.log"

# ============ 过滤设置 ============
# 标题必须包含的关键词
REQUIRED_KEYWORDS = ["中标", "成交", "结果"]

# 标题不能包含的关键词
EXCLUDE_KEYWORDS = ["更正", "废标", "终止"]

# 公告最大保留天数
MAX_AGE_DAYS = 30

# ============ 数据导出设置 ============
EXPORT_FORMATS = ["excel", "csv"]  # 支持的导出格式
EXPORT_BATCH_SIZE = 1000  # 批量导出大小
