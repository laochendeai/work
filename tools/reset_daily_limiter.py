#!/usr/bin/env python3
"""
重置每日限制器
"""
import json
from pathlib import Path
from datetime import date

def reset_daily_limiter():
    """重置每日限制器数据"""
    print("🔄 重置每日限制器...")

    # 直接修改存储的文件
    data_file = Path("data/daily_limits.json")

    if data_file.exists():
        # 读取现有数据
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 重置今天的计数
        today = date.today().strftime("%Y-%m-%d")

        print(f"重置日期: {today}")

        # 重置所有源
        if today in data:
            for source_id in data[today]:
                data[today][source_id] = 0
            print(f"已重置 {len(data[today])} 个数据源的计数")
        else:
            print("今天没有数据，添加新记录")
            data[today] = {}

        # 保存
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    else:
        print("数据文件不存在，创建新文件")
        today = date.today().strftime("%Y-%m-%d")
        data = {today: {}}
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    print("\n✅ 每日限制器已重置！")

if __name__ == "__main__":
    reset_daily_limiter()