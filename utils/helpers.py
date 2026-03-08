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



