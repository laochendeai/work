#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一配置管理
所有配置项集中管理，避免分散配置
"""

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Dict, Any, Optional

class Settings:
    """统一配置管理器"""

    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.config_dir = self.base_dir / "config"
        self.data_dir = self.base_dir / "data"
        self.logs_dir = self.base_dir / "logs"

        # 确保目录存在
        self.config_dir.mkdir(exist_ok=True)
        self.data_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)

        self.user_config_file = self.config_dir / "user_config.json"
        self._user_config = None

    def load_user_config(self) -> Dict[str, Any]:
        """加载用户配置"""
        if self._user_config is None:
            defaults = self._create_default_config()
            needs_save = False

            if self.user_config_file.exists():
                with open(self.user_config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
            else:
                config_data = deepcopy(defaults)
                needs_save = True

            if self._merge_defaults(config_data, defaults):
                needs_save = True

            self._user_config = config_data
            if needs_save:
                self.save_user_config()

        return self._user_config

    def save_user_config(self):
        """保存用户配置"""
        with open(self.user_config_file, 'w', encoding='utf-8') as f:
            json.dump(self._user_config, f, ensure_ascii=False, indent=2)

    def _create_default_config(self) -> Dict[str, Any]:
        """创建默认配置"""
        return {
            "user_info": {
                "name": "设计营销用户",
                "email": "",
                "company": "",
                "setup_date": "2024-12-07"
            },
            "scraper": {
                "sources": {
                    "ccgp": {
                        "name": "政府采购网",
                        "enabled": True,
                        "base_url": "https://www.ccgp.gov.cn",
                        "delay_min": 3,
                        "delay_max": 8
                    },
                    "university": {
                        "name": "高校采购",
                        "enabled": True,
                        "base_url": "",
                        "delay_min": 5,
                        "delay_max": 10
                    },
                    "chinabidding": {
                        "name": "中国采购与招标网",
                        "enabled": True,
                        "base_url": "http://www.chinabidding.cn",
                        "delay_min": 3,
                        "delay_max": 8
                    },
                    "bidcenter": {
                        "name": "招标采购导航网",
                        "enabled": True,
                        "base_url": "http://www.bidcenter.com.cn",
                        "delay_min": 4,
                        "delay_max": 9
                    }
                },
                "schedule": {
                    "enabled": False,
                    "interval_hours": 8
                },
                "filters": {
                    "include_keywords": [
                        "设备采购", "工程招标", "项目招标", "服务采购", "系统采购",
                        "信息化", "智能化", "数字化", "自动化", "医疗设备", "教学设备",
                        "办公设备", "网络设备", "安防设备", "实验设备", "检测设备",
                        "建设", "工程", "设备", "系统", "软件", "服务", "采购"
                    ],
                    "exclude_keywords": [
                        "询价", "竞争性谈判", "更正", "澄清", "补充", "废标",
                        "终止", "暂停", "延期", "答疑", "预公告", "意向公告",
                        "办公用品", "文具", "耗材", "维修", "保养", "租赁"
                    ],
                    "min_title_length": 15,
                    "max_title_length": 200,
                    "skip_duplicates": True,
                    "max_age_days": 30,
                    "intelligent_filter": {
                        "enabled": True,
                        "min_value_score": 2.0,
                        "require_contact_info": True
                    }
                },
                "network": {
                    "http2": True,
                    "timeout": 25,
                    "concurrency": 10,
                    "detail_concurrency": 6,
                    "max_connections": 40,
                    "max_keepalive_connections": 20,
                    "retry_attempts": 3,
                    "retry_for_statuses": [408, 425, 429, 500, 502, 503, 504],
                    "retry_backoff": {
                        "min": 0.5,
                        "max": 6
                    },
                    "respect_retry_after": True,
                    "user_agents": [
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
                        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    ]
                }
            },
            "email": {
                "smtp_server": "smtp.qq.com",
                "smtp_port": 587,
                "use_ssl": False,
                "sender_email": "",
                "sender_password": "",
                "sender_name": "设计营销助手",
                "configured": False
            },
            "storage": {
                "database_path": str(self.data_dir / "marketing.db"),
                "backup_enabled": True,
                "backup_interval_days": 7,
                "export_formats": ["excel", "csv"],
                "retention": {
                    "scraped_data_max_age_days": 45,
                    "scraped_data_max_records": 5000
                }
            },
            "ui": {
                "theme": "light",
                "items_per_page": 50,
                "auto_refresh": False
            },
            "contact_processing": {
                "enabled": True,
                "method": "local",  # local, ai, hybrid
                "local_processing": {
                    "enabled": True,
                    "confidence_threshold": 0.3,
                    "max_contacts_per_item": 5,
                    "use_jieba": True
                },
                "ai_processing": {
                    "enabled": False,
                    "provider": "openai",  # openai, claude, local
                    "model": "gpt-3.5-turbo",
                    "api_key": "",
                    "base_url": "",
                    "max_tokens": 1000,
                    "temperature": 0.1,
                    "batch_size": 10,
                    "timeout": 30,
                    "retry_attempts": 2
                }
            }
        }

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
        config = self.load_user_config()
        keys = key.split('.')
        value = config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any):
        """设置配置项"""
        config = self.load_user_config()
        keys = key.split('.')
        current = config

        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]

        current[keys[-1]] = value
        self.save_user_config()

    def _merge_defaults(self, target: Dict[str, Any], defaults: Dict[str, Any]) -> bool:
        """将缺失的默认配置合并到用户配置中，返回是否有修改"""
        changed = False

        for key, default_value in defaults.items():
            if key not in target:
                target[key] = deepcopy(default_value)
                changed = True
            else:
                current_value = target[key]
                if isinstance(current_value, dict) and isinstance(default_value, dict):
                    if self._merge_defaults(current_value, default_value):
                        changed = True

        return changed

    @property
    def email_configured(self) -> bool:
        """检查邮件是否配置"""
        return bool(self.get('email.sender_email') and self.get('email.sender_password'))

    @property
    def enabled_sources(self) -> Dict[str, Any]:
        """获取启用的数据源"""
        sources = self.get('scraper.sources', {})
        return {k: v for k, v in sources.items() if v.get('enabled', False)}

# 全局配置实例
settings = Settings()
