#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化auto_sources.yaml文件：
1. 删除无效的详情页
2. 合并同一域名的重复数据源
3. 保留最有价值的列表页
"""

import yaml
from pathlib import Path
from urllib.parse import urlparse
from collections import defaultdict

def is_valid_source_url(url: str) -> bool:
    """检查URL是否为有效的数据源URL"""
    # 排除详情页
    excluded_patterns = [
        '.htm', '.html',
        '/detail',
        '/showinfo',
        '/view',
        '/show',  # 显示页面
        '/article',
        '/content',
        '/news/',  # 新闻详情
        't202',    # 时间戳开头
        '/202',    # 年份开头
        '/id=',    # ID参数
        '?',       # 有查询参数（通常是详情页）
    ]

    url_lower = url.lower()
    return not any(pattern in url_lower for pattern in excluded_patterns)

def extract_domain(url: str) -> str:
    """提取URL的域名"""
    return urlparse(url).netloc.lower()

def get_path_depth(url: str) -> int:
    """获取URL路径深度"""
    parsed = urlparse(url)
    path = parsed.path.strip('/')
    return len(path.split('/')) if path else 0

def is_listing_page(url: str) -> bool:
    """判断是否为列表页"""
    # 列表页的关键词
    listing_keywords = [
        'cggg',    # 采购公告
        'zbgg',    # 中标公告
        'cjgg',    # 成交公告
        'gkzb',    # 公开招标
        'zbxx',    # 招标信息
        'tender',  # 招标
        'bid',     # 投标
        'notice',  # 通知
        'news',    # 新闻列表
        'announcement',  # 公告
        'bidding', # 招投标
        'procurement', # 采购
    ]

    # 详情页的关键词
    detail_keywords = [
        'detail',
        'show',
        'view',
        'info',
        'article',
        'content',
    ]

    url_lower = url.lower()

    # 排除详情页
    if any(kw in url_lower for kw in detail_keywords):
        return False

    # 包含列表页关键词
    if any(kw in url_lower for kw in listing_keywords):
        return True

    # 路径深度<=2的可能是列表页
    return get_path_depth(url) <= 2

def optimize_sources():
    """优化数据源"""
    print("=" * 60)
    print("🔧 优化 auto_sources.yaml")
    print("=" * 60)

    # 读取原始数据
    auto_file = Path("config/auto_sources.yaml")
    if not auto_file.exists():
        print("❌ auto_sources.yaml 不存在")
        return

    with open(auto_file, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    if not data or 'sources' not in data:
        print("❌ 没有找到数据源")
        return

    # 按域名分组
    domain_groups = defaultdict(list)
    valid_count = 0
    invalid_count = 0

    # 第一遍：过滤无效URL并分组
    for source_id, source_data in data['sources'].items():
        if not source_data.get('enabled', False):
            continue

        url = source_data.get('base_url', '')

        if not is_valid_source_url(url):
            invalid_count += 1
            continue

        if not is_listing_page(url):
            invalid_count += 1
            continue

        domain = extract_domain(url)
        domain_groups[domain].append({
            'id': source_id,
            'data': source_data,
            'url': url,
            'depth': get_path_depth(url),
            'path': urlparse(url).path
        })
        valid_count += 1

    print(f"\n📊 过滤统计:")
    print(f"   有效URL: {valid_count} 个")
    print(f"   无效URL: {invalid_count} 个")

    # 第二遍：每个域名只保留最好的数据源
    optimized_sources = {}
    domain_conflicts = 0

    for domain, sources in domain_groups.items():
        if len(sources) == 1:
            # 只有一个，直接保留
            source = sources[0]
            optimized_sources[source['id']] = source['data']
        else:
            # 多个数据源，选择最好的
            domain_conflicts += 1
            # 优先级：推荐源 > 路径浅的 > 主页
            best_source = None
            best_score = -1

            for source in sources:
                score = 0
                # 路径越浅越好
                score -= source['depth'] * 10
                # 路径为根路径的加分
                if source['path'] in ['', '/']:
                    score += 100
                # 包含列表页关键词的加分
                if any(kw in source['url'].lower() for kw in ['cggg', 'zbgg', 'cjgg']):
                    score += 50

                if score > best_score:
                    best_score = score
                    best_source = source

            if best_source:
                optimized_sources[best_source['id']] = best_source['data']

    print(f"\n🔄 域名去重:")
    print(f"   冲突域名: {domain_conflicts} 个")
    print(f"   最终保留: {len(optimized_sources)} 个")

    # 显示一些示例
    print(f"\n✅ 保留的数据源示例:")
    for i, (source_id, source_data) in enumerate(list(optimized_sources.items())[:5], 1):
        print(f"   {i}. {source_data.get('name', 'N/A')}")
        print(f"      URL: {source_data['base_url']}")

    # 备份原文件
    backup_file = auto_file.with_suffix('.yaml.backup')
    with open(backup_file, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
    print(f"\n💾 已备份到: {backup_file}")

    # 保存优化后的数据
    optimized_data = {
        'metadata': data.get('metadata', {}),
        'sources': optimized_sources
    }

    with open(auto_file, 'w', encoding='utf-8') as f:
        yaml.dump(optimized_data, f, allow_unicode=True, default_flow_style=False)

    print(f"\n✅ 优化完成！")
    print(f"   原始数据源: {len(data['sources'])} 个")
    print(f"   优化后: {len(optimized_sources)} 个")
    print(f"   压缩率: {((1 - len(optimized_sources) / len(data['sources'])) * 100):.1f}%")

if __name__ == "__main__":
    optimize_sources()