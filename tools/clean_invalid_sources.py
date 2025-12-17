#!/usr/bin/env python3
"""
清理无效的数据源（如Python库等）
"""
import yaml
from pathlib import Path

def clean_invalid_sources():
    """清理无效的数据源"""
    print("=" * 60)
    print("🧹 清理无效数据源")
    print("=" * 60)

    # 需要删除的关键词
    invalid_keywords = [
        'python', 'playwright', 'selenium', 'scrapy', 'beautifulsoup',
        'requests', 'aiohttp', 'httpx', 'lxml', 'pandas', 'numpy',
        'pytorch', 'tensorflow', 'django', 'flask', 'fastapi',
        'asyncio', 'multiprocessing', 'threading', 'socket'
    ]

    # 读取配置文件
    auto_sources_file = Path("config/auto_sources.yaml")
    if not auto_sources_file.exists():
        print("❌ 配置文件不存在")
        return

    with open(auto_sources_file, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f) or {}

    sources = data.get('sources', {})
    metadata = data.get('metadata', {})

    # 找出并删除无效源
    to_delete = []
    for key, source in sources.items():
        name = source.get('name', '').lower()
        base_url = source.get('base_url', '').lower()
        description = source.get('description', '').lower() if source.get('description') else ''

        # 检查是否包含无效关键词
        is_invalid = False
        for keyword in invalid_keywords:
            if keyword in name or keyword in base_url or keyword in description:
                is_invalid = True
                break

        # 检查URL是否明显无效
        if base_url and ('pypi.org' in base_url or 'github.com' in base_url):
            is_invalid = True

        if is_invalid:
            to_delete.append((key, source))

    # 删除无效源
    deleted_count = 0
    for key, source in to_delete:
        print(f"\n删除: {source.get('name', 'N/A')}")
        print(f"  Key: {key}")
        print(f"  URL: {source.get('base_url', 'N/A')}")

        if key in sources:
            del sources[key]
            deleted_count += 1

    # 更新元数据
    metadata['last_cleanup'] = datetime.now().isoformat()
    metadata['last_cleanup_deleted'] = deleted_count
    metadata['total_sources'] = len(sources)

    data['metadata'] = metadata
    data['sources'] = sources

    # 保存更新后的配置
    with open(auto_sources_file, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False)

    print(f"\n✅ 已删除 {deleted_count} 个无效数据源")

    # 显示当前统计
    enabled_count = sum(1 for s in sources.values() if s.get('enabled', True))
    disabled_count = len(sources) - enabled_count

    print(f"\n当前统计:")
    print(f"  总数: {len(sources)}")
    print(f"  启用: {enabled_count}")
    print(f"  禁用: {disabled_count}")

    # 列出剩余的源类型
    print(f"\n数据源类型分布:")
    type_count = {}
    for source in sources.values():
        source_type = source.get('type', '未知')
        type_count[source_type] = type_count.get(source_type, 0) + 1

    for stype, count in sorted(type_count.items(), key=lambda x: x[1], reverse=True):
        print(f"  - {stype}: {count}")

    # 创建清理备份
    backup_file = Path(f"backups/auto_sources_before_cleanup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml")
    backup_file.parent.mkdir(exist_ok=True)

    # 读取原文件作为备份
    with open(auto_sources_file, 'r', encoding='utf-8') as f:
        backup_data = f.read()

    with open(backup_file, 'w', encoding='utf-8') as f:
        f.write(backup_data)

    print(f"\n📦 已创建备份: {backup_file}")

    print("\n" + "=" * 60)
    print("💡 后续建议")
    print("=" * 60)
    print("1. 只保留政府采购相关的数据源")
    print("2. 设置数据源上限（如20个）")
    print("3. 定期审查数据源质量")
    print("4. 手动管理新增数据源")
    print("5. 考虑按地区分类管理数据源")

if __name__ == "__main__":
    from datetime import datetime
    clean_invalid_sources()