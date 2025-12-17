#!/usr/bin/env python3
"""
禁用自动发现功能，防止重复添加数据源
"""
import yaml
from datetime import datetime
from pathlib import Path

def disable_auto_discovery():
    """禁用所有自动发现功能"""
    print("=" * 60)
    print("🛑 禁用自动发现功能")
    print("=" * 60)

    # 1. 更新auto_sources.yaml
    auto_sources_file = Path("config/auto_sources.yaml")

    if auto_sources_file.exists():
        with open(auto_sources_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}

        # 禁用自动发现
        metadata = data.get('metadata', {})
        metadata['auto_discovery_enabled'] = False
        metadata['mcp_discovery_enabled'] = False
        metadata['mcp_collaborative_enabled'] = False
        metadata['disabled_at'] = datetime.now().isoformat()
        metadata['disabled_reason'] = '防止重复添加数据源'

        data['metadata'] = metadata

        with open(auto_sources_file, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False)

        print("✅ 已更新 auto_sources.yaml")
        print("   - auto_discovery_enabled: false")
        print("   - mcp_discovery_enabled: false")
        print("   - mcp_collaborative_enabled: false")
    else:
        print("❌ auto_sources.yaml 不存在")

    # 2. 创建或更新mcp_scheduler.yaml
    scheduler_config = {
        "enabled": False,
        "schedule": "weekly",
        "auto_run_on_scrape": False,
        "max_sources_per_run": 0,
        "quality_threshold": 0.8,
        "email_notifications": False,
        "backup_discovered_sources": False,
        "disabled_at": datetime.now().isoformat(),
        "disabled_reason": "防止重复添加数据源"
    }

    scheduler_file = Path("config/mcp_scheduler.yaml")
    with open(scheduler_file, 'w', encoding='utf-8') as f:
        yaml.dump(scheduler_config, f, allow_unicode=True)

    print("\n✅ 已创建/更新 mcp_scheduler.yaml")
    print("   - enabled: false")
    print("   - auto_run_on_scrape: false")
    print("   - max_sources_per_run: 0")

    # 3. 创建一个专门的配置文件
    disable_config = {
        "auto_discovery": {
            "enabled": False,
            "reason": "防止数据源无限增长",
            "disabled_date": datetime.now().strftime('%Y-%m-%d')
        },
        "mcp_discovery": {
            "enabled": False,
            "reason": "MCP自动发现已禁用"
        },
        "mcp_scheduler": {
            "enabled": False,
            "reason": "调度器已禁用"
        }
    }

    config_file = Path("config/discovery_disabled.yaml")
    with open(config_file, 'w', encoding='utf-8') as f:
        yaml.dump(disable_config, f, allow_unicode=True)

    print(f"\n✅ 已创建 discovery_disabled.yaml")

    # 4. 显示当前数据源统计
    print("\n" + "=" * 60)
    print("📊 当前数据源统计")
    print("=" * 60)

    if auto_sources_file.exists():
        with open(auto_sources_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}

        sources = data.get('sources', {})
        total = len(sources)
        enabled = sum(1 for s in sources.values() if s.get('enabled', True))
        disabled = total - enabled

        print(f"总数据源: {total}")
        print(f"启用: {enabled}")
        print(f"禁用: {disabled}")

        # 显示最近添加的源
        print("\n最近添加的源:")
        recent_sources = []
        for key, source in sources.items():
            if source.get('discovered_at'):
                recent_sources.append((key, source))

        # 按时间排序
        recent_sources.sort(key=lambda x: x[1].get('discovered_at', ''), reverse=True)

        for key, source in recent_sources[:5]:
            name = source.get('name', 'N/A')
            discovered = source.get('discovered_at', 'N/A')
            print(f"  - {name} ({key[:20]}...) - {discovered[:10]}")

    # 5. 建议
    print("\n" + "=" * 60)
    print("💡 建议")
    print("=" * 60)
    print("1. 定期检查数据源质量")
    print("2. 手动禁用无效的数据源")
    print("3. 只保留高质量的数据源")
    print("4. 考虑设置数据源上限（如50个）")
    print("5. 实施定期清理机制")

    print("\n✅ 自动发现功能已全部禁用！")
    print("现在爬虫不会再自动添加新的数据源。")

if __name__ == "__main__":
    disable_auto_discovery()