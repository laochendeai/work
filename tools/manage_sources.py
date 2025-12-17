#!/usr/bin/env python3
"""
数据源管理工具
手动管理爬虫数据源
"""
import yaml
from datetime import datetime
from pathlib import Path
import argparse

def list_sources(show_disabled=True):
    """列出所有数据源"""
    auto_sources_file = Path("config/auto_sources.yaml")

    if not auto_sources_file.exists():
        print("❌ 配置文件不存在")
        return

    with open(auto_sources_file, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f) or {}

    sources = data.get('sources', {})

    # 按类型分组
    by_type = {}
    for key, source in sources.items():
        if not show_disabled and not source.get('enabled', True):
            continue

        stype = source.get('type', '未知')
        if stype not in by_type:
            by_type[stype] = []
        by_type[stype].append((key, source))

    # 统计
    total_enabled = sum(1 for s in sources.values() if s.get('enabled', True))
    total_disabled = len(sources) - total_enabled

    print("=" * 60)
    print("📊 数据源列表")
    print("=" * 60)
    print(f"总数: {len(sources)} (启用: {total_enabled}, 禁用: {total_disabled})")
    print()

    for stype, items in sorted(by_type.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"【{stype}】({len(items)}个)")
        for key, source in items[:10]:  # 每类最多显示10个
            status = "✅" if source.get('enabled', True) else "❌"
            name = source.get('name', 'N/A')
            url = source.get('base_url', 'N/A')
            if len(url) > 50:
                url = url[:50] + "..."
            print(f"  {status} {name}")
            print(f"      {url} ({key[:20]}...)")

        if len(items) > 10:
            print(f"  ... 还有 {len(items) - 10} 个")
        print()

def disable_source(pattern):
    """禁用匹配模式的数据源"""
    auto_sources_file = Path("config/auto_sources.yaml")

    with open(auto_sources_file, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f) or {}

    sources = data.get('sources', {})
    disabled_count = 0

    for key, source in sources.items():
        name = source.get('name', '').lower()
        base_url = source.get('base_url', '').lower()

        # 检查是否匹配
        if pattern.lower() in name or pattern.lower() in base_url:
            if source.get('enabled', True):
                source['enabled'] = False
                source['disabled_at'] = datetime.now().isoformat()
                source['disabled_reason'] = f"手动禁用 (匹配: {pattern})"
                disabled_count += 1
                print(f"✅ 已禁用: {source.get('name')}")

    # 保存
    data['sources'] = sources
    with open(auto_sources_file, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False)

    print(f"\n总共禁用了 {disabled_count} 个数据源")

def enable_source(pattern):
    """启用匹配模式的数据源"""
    auto_sources_file = Path("config/auto_sources.yaml")

    with open(auto_sources_file, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f) or {}

    sources = data.get('sources', {})
    enabled_count = 0

    for key, source in sources.items():
        name = source.get('name', '').lower()
        base_url = source.get('base_url', '').lower()

        # 检查是否匹配
        if pattern.lower() in name or pattern.lower() in base_url:
            if not source.get('enabled', True):
                source['enabled'] = True
                source.pop('disabled_at', None)
                source.pop('disabled_reason', None)
                enabled_count += 1
                print(f"✅ 已启用: {source.get('name')}")

    # 保存
    data['sources'] = sources
    with open(auto_sources_file, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False)

    print(f"\n总共启用了 {enabled_count} 个数据源")

def delete_source(pattern):
    """删除匹配模式的数据源"""
    auto_sources_file = Path("config/auto_sources.yaml")

    # 先备份
    backup_file = Path(f"backups/auto_sources_before_delete_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml")
    backup_file.parent.mkdir(exist_ok=True)
    with open(auto_sources_file, 'r', encoding='utf-8') as f:
        backup_content = f.read()
    with open(backup_file, 'w', encoding='utf-8') as f:
        f.write(backup_content)
    print(f"📦 已创建备份: {backup_file}")

    with open(auto_sources_file, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f) or {}

    sources = data.get('sources', {})
    to_delete = []

    for key, source in sources.items():
        name = source.get('name', '').lower()
        base_url = source.get('base_url', '').lower()

        # 检查是否匹配
        if pattern.lower() in name or pattern.lower() in base_url:
            to_delete.append((key, source))

    # 删除
    for key, source in to_delete:
        del sources[key]
        print(f"🗑️ 已删除: {source.get('name')}")

    # 保存
    data['sources'] = sources
    data['metadata']['total_sources'] = len(sources)
    data['metadata']['last_updated'] = datetime.now().isoformat()

    with open(auto_sources_file, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False)

    print(f"\n总共删除了 {len(to_delete)} 个数据源")

def show_stats():
    """显示统计信息"""
    auto_sources_file = Path("config/auto_sources.yaml")

    with open(auto_sources_file, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f) or {}

    sources = data.get('sources', {})
    metadata = data.get('metadata', {})

    # 基础统计
    total = len(sources)
    enabled = sum(1 for s in sources.values() if s.get('enabled', True))
    disabled = total - enabled

    print("=" * 60)
    print("📈 数据源统计")
    print("=" * 60)
    print(f"总数量: {total}")
    print(f"启用: {enabled} ({enabled/total*100:.1f}%)" if total > 0 else "启用: 0")
    print(f"禁用: {disabled} ({disabled/total*100:.1f}%)" if total > 0 else "禁用: 0")
    print()

    # 按类型统计
    type_stats = {}
    level_stats = {}

    for source in sources.values():
        # 类型统计
        stype = source.get('type', '未知')
        if stype not in type_stats:
            type_stats[stype] = {'enabled': 0, 'disabled': 0}
        if source.get('enabled', True):
            type_stats[stype]['enabled'] += 1
        else:
            type_stats[stype]['disabled'] += 1

        # 级别统计
        level = source.get('level', '未知')
        if level not in level_stats:
            level_stats[level] = {'enabled': 0, 'disabled': 0}
        if source.get('enabled', True):
            level_stats[level]['enabled'] += 1
        else:
            level_stats[level]['disabled'] += 1

    # 类型分布
    print("【按类型分布】")
    for stype, stats in sorted(type_stats.items(), key=lambda x: x[1]['enabled'], reverse=True):
        total_type = stats['enabled'] + stats['disabled']
        print(f"  {stype}: {stats['enabled']}/{total_type}")
    print()

    # 级别分布
    print("【按级别分布】")
    for level, stats in sorted(level_stats.items(), key=lambda x: x[1]['enabled'], reverse=True):
        total_level = stats['enabled'] + stats['disabled']
        print(f"  {level}: {stats['enabled']}/{total_level}")
    print()

    # 最近更新
    last_updated = metadata.get('last_updated', 'N/A')
    print(f"最后更新: {last_updated}")

def main():
    parser = argparse.ArgumentParser(description='数据源管理工具')
    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    # 列表命令
    list_parser = subparsers.add_parser('list', help='列出所有数据源')
    list_parser.add_argument('--enabled-only', action='store_true', help='只显示启用的数据源')

    # 禁用命令
    disable_parser = subparsers.add_parser('disable', help='禁用数据源')
    disable_parser.add_argument('pattern', help='匹配模式（名称或URL）')

    # 启用命令
    enable_parser = subparsers.add_parser('enable', help='启用数据源')
    enable_parser.add_argument('pattern', help='匹配模式（名称或URL）')

    # 删除命令
    delete_parser = subparsers.add_parser('delete', help='删除数据源')
    delete_parser.add_argument('pattern', help='匹配模式（名称或URL）')

    # 统计命令
    subparsers.add_parser('stats', help='显示统计信息')

    args = parser.parse_args()

    if args.command == 'list':
        list_sources(show_disabled=not args.enabled_only)
    elif args.command == 'disable':
        disable_source(args.pattern)
    elif args.command == 'enable':
        enable_source(args.pattern)
    elif args.command == 'delete':
        delete_source(args.pattern)
    elif args.command == 'stats':
        show_stats()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()