#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能设计营销系统 - 统一启动入口

保持 `python main.py ...` 的使用习惯不变；
具体的命令行解析与业务编排拆分在：
- `core/cli.py`
- `core/system.py`
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from core.cli import main as cli_main


def main() -> int:
    return cli_main()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n👋 程序已退出")
    except Exception as e:
        print(f"❌ 程序运行失败: {e}")
        raise SystemExit(1)

