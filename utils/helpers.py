"""
工具函数模块
"""
import logging
import sys
from pathlib import Path

from config.settings import LOG_LEVEL, LOG_FILE


def setup_logging():
    """设置日志"""
    # 确保日志目录存在
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    # 配置日志格式
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'

    # 配置日志级别
    level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)

    # 配置处理器
    handlers = [
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, encoding='utf-8')
    ]

    logging.basicConfig(
        level=level,
        format=log_format,
        datefmt=date_format,
        handlers=handlers
    )

    logging.info("日志系统已启动")


def load_sources_config(config_path: str = None) -> list:
    """
    加载数据源配置

    Args:
        config_path: 配置文件路径

    Returns:
        数据源配置列表
    """
    import yaml

    from config.settings import BASE_DIR
    if config_path is None:
        config_path = BASE_DIR / "config" / "sources.yaml"

    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    sources = config.get('sources', [])

    # 只返回启用的数据源
    enabled_sources = [s for s in sources if s.get('enabled', False)]

    logging.info(f"加载了 {len(enabled_sources)}/{len(sources)} 个数据源")

    return enabled_sources
