"""
全局配置设置
"""
import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).parent.parent

# 数据目录
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
EXPORT_DIR = DATA_DIR / "exports"
EXPORT_DIR.mkdir(exist_ok=True)

# 数据库路径
DB_PATH = DATA_DIR / "gp.db"

# ============ 浏览器设置 ============
BROWSER_TYPE = "chromium"          # 浏览器类型: chromium, firefox, webkit
BROWSER_HEADLESS = True            # 无头模式
BROWSER_TIMEOUT = 30000            # 页面加载超时(毫秒)
BROWSER_NAVIGATION_TIMEOUT = 60000 # 导航超时(毫秒)

# ============ 整理设置 ============
MAX_PAGES = 5                      # 每个源最多整理页数（保守设置）
MAX_ITEMS_PER_PAGE = 50            # 每页最多提取条目

DELAY_MIN = 1                      # 请求间最小延迟(秒)
DELAY_MAX = 3                      # 请求间最大延迟(秒)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# ============ 重试设置 ============
MAX_RETRIES = 2                    # 最大重试次数
RETRY_DELAY = 5                    # 重试延迟(秒)

# ============ 日志设置 ============
LOG_LEVEL = "INFO"                 # DEBUG, INFO, WARNING, ERROR
LOG_FILE = DATA_DIR / "scraper.log"

# ============ 过滤设置 ============
# 标题必须包含的关键词
REQUIRED_KEYWORDS = ["中标", "成交", "结果"]

# 标题不能包含的关键词
EXCLUDE_KEYWORDS = [
    "更正",
    "废标", "终止"
]

# 公告最大保留天数
MAX_AGE_DAYS = 30

# ============ 数据导出设置 ============
EXPORT_FORMATS = ["excel", "csv"]  # 支持的导出格式
EXPORT_BATCH_SIZE = 1000           # 批量导出大小
