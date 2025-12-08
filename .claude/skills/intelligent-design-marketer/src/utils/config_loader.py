#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置文件加载器
为个人用户提供简单的配置管理
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional

class ConfigLoader:
    """配置加载器"""

    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        self._configs = {}

    def load_config(self, config_name: str) -> Dict[str, Any]:
        """加载配置文件"""
        if config_name in self._configs:
            return self._configs[config_name]

        config_file = self.config_dir / f"{config_name}.json"
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                self._configs[config_name] = config
                return config
            except Exception as e:
                print(f"❌ 加载配置 {config_name} 失败: {e}")
                return {}
        else:
            print(f"⚠️  配置文件不存在: {config_file}")
            return {}

    def save_config(self, config_name: str, config: Dict[str, Any]):
        """保存配置文件"""
        config_file = self.config_dir / f"{config_name}.json"
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            self._configs[config_name] = config
            return True
        except Exception as e:
            print(f"❌ 保存配置 {config_name} 失败: {e}")
            return False

    def get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "email": {
                "smtp_server": "",
                "smtp_port": 587,
                "email": "",
                "password": "",
                "sender_name": "设计营销助手",
                "use_ssl": False
            },
            "scraper": {
                "data_sources": ["政府采购网"],
                "frequency": {"hours": 8, "description": "每天3次"},
                "delay_range": {"min": 3, "max": 8},
                "auto_start": False
            },
            "storage": {
                "data_path": "data",
                "retention_days": 90,
                "backup_enabled": False,
                "backup_frequency": "weekly"
            }
        }