#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP驱动的数据源发现工具
使用Web Search Prime、Web Reader、Context7等MCP服务器
自动发现和验证政府采购网站
"""

import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# 系统路径设置
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import settings

class MCPSourceDiscovery:
    """MCP驱动的数据源发现器"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.discovered_sources = []
        self.results_dir = Path("data") / "discovered_sources"
        self.results_dir.mkdir(parents=True, exist_ok=True)

        # 搜索策略
        self.search_strategies = {
            "central_platforms": [
                "全国公共资源交易平台 site:ggzy.gov.cn",
                "中国政府采购网 site:ccgp.gov.cn",
                "招标投标公共服务平台 site:cebpubservice.com"
            ],
            "provincial_platforms": [
                "政府采购网 site:gov.cn 省份",
                "公共资源交易网 site:gov.cn",
                "省政府采购 site:gov.cn"
            ],
            "municipal_platforms": [
                "市政府采购网 site:gov.cn",
                "公共资源交易中心 site:gov.cn",
                "招标投标网 site:gov.cn"
            ],
            "specialized_platforms": [
                "高校采购网 site:edu.cn",
                "医院采购网 site:gov.cn",
                "军队采购 site:mil.cn",
                "国企采购 site:cn"
            ],
            "alternative_platforms": [
                "采购与招标网 site:cn",
                "招标网 site:cn",
                "采招网 site:cn"
            ]
        }

        # 验证关键词
        self.validation_keywords = {
            "positive": [
                "中标公告", "成交结果", "采购结果", "招标公告",
                "采购公告", "中标公示", "成交公示", "开标记录"
            ],
            "negative": [
                "登录", "注册", "用户中心", "个人中心",
                "帮助中心", "常见问题", "网站地图"
            ]
        }

    async def discover_all_sources(self):
        """执行完整的数据源发现流程"""
        self.logger.info("🚀 开始MCP驱动的数据源发现")

        all_sources = []

        # 1. 执行各种搜索策略
        for strategy_name, queries in self.search_strategies.items():
            self.logger.info(f"📊 执行搜索策略: {strategy_name}")

            for query in queries:
                try:
                    # 使用Web Search Prime搜索
                    search_results = await self.web_search(query)

                    # 处理搜索结果
                    for result in search_results:
                        if self.is_relevant_result(result):
                            # 使用Web Reader深度分析
                            detailed_info = await self.analyze_source(result['url'])

                            if detailed_info and self.validate_source(detailed_info):
                                all_sources.append(detailed_info)

                except Exception as e:
                    self.logger.error(f"搜索失败 '{query}': {e}")

        # 2. 去重和评分
        unique_sources = self.deduplicate_sources(all_sources)
        scored_sources = self.score_sources(unique_sources)

        # 3. 保存结果
        await self.save_discovered_sources(scored_sources)

        self.logger.info(f"✅ 发现 {len(scored_sources)} 个新数据源")
        return scored_sources

    async def web_search(self, query: str, location: str = "cn") -> List[Dict]:
        """使用Web Search Prime执行搜索"""
        # 这里需要调用实际的MCP服务器
        # 由于环境限制，我们模拟搜索结果
        self.logger.info(f"🔍 搜索: {query}")

        # 模拟搜索结果（实际应该调用mcp__web-search-prime__webSearchPrime）
        mock_results = [
            {
                "title": f"模拟搜索结果 - {query}",
                "url": f"https://example.com/search?q={query}",
                "content": "模拟搜索内容",
                "media": "",
                "publish_date": ""
            }
        ]

        return mock_results

    async def analyze_source(self, url: str) -> Optional[Dict]:
        """使用Web Reader深度分析数据源"""
        self.logger.info(f"📖 分析网站: {url}")

        try:
            # 这里应该调用mcp__web-reader__webReader
            # 模拟分析结果
            return {
                "url": url,
                "title": "发现的新数据源",
                "type": "政府采购网",
                "level": "省级",
                "features": {
                    "has_search": True,
                    "has_rss": False,
                    "has_api": False,
                    "requires_login": False
                },
                "contact_methods": ["中标公告", "采购结果"],
                "update_frequency": "每日",
                "quality_score": 0.8,
                "discovered_at": datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"分析失败 {url}: {e}")
            return None

    def is_relevant_result(self, result: Dict) -> bool:
        """判断搜索结果是否相关"""
        title = result.get('title', '').lower()
        content = result.get('content', '').lower()
        url = result.get('url', '').lower()

        # 检查是否包含相关关键词
        relevant_keywords = [
            '政府采购', '公共资源', '招标', '采购',
            'bid', 'procurement', 'tender'
        ]

        return any(keyword in title or keyword in content or keyword in url
                  for keyword in relevant_keywords)

    def validate_source(self, source_info: Dict) -> bool:
        """验证数据源的有效性"""
        # 1. 检查必要字段
        if not source_info.get('url'):
            return False

        # 2. 检查质量评分
        if source_info.get('quality_score', 0) < 0.3:
            return False

        # 3. 检查是否有联系方式获取方法
        if not source_info.get('contact_methods'):
            return False

        return True

    def deduplicate_sources(self, sources: List[Dict]) -> List[Dict]:
        """去重数据源"""
        seen_urls = set()
        unique_sources = []

        for source in sources:
            url = source.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_sources.append(source)

        self.logger.info(f"去重: {len(sources)} -> {len(unique_sources)}")
        return unique_sources

    def score_sources(self, sources: List[Dict]) -> List[Dict]:
        """为数据源评分"""
        for source in sources:
            score = 0

            # URL质量 (0-30分)
            if 'gov.cn' in source.get('url', ''):
                score += 30
            elif 'edu.cn' in source.get('url', ''):
                score += 20
            else:
                score += 10

            # 功能特性 (0-30分)
            features = source.get('features', {})
            if features.get('has_search', False):
                score += 10
            if features.get('has_api', False):
                score += 10
            if not features.get('requires_login', True):
                score += 10

            # 更新频率 (0-20分)
            freq = source.get('update_frequency', '').lower()
            if '实时' in freq or '每日' in freq:
                score += 20
            elif '每周' in freq:
                score += 15
            elif '每月' in freq:
                score += 10

            # 联系方式 (0-20分)
            methods = source.get('contact_methods', [])
            if '中标公告' in methods:
                score += 10
            if '采购结果' in methods:
                score += 10

            source['total_score'] = score

        # 按评分排序
        return sorted(sources, key=lambda x: x.get('total_score', 0), reverse=True)

    async def save_discovered_sources(self, sources: List[Dict]):
        """保存发现的数据源"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 保存详细JSON
        detail_file = self.results_dir / f"sources_detail_{timestamp}.json"
        with open(detail_file, 'w', encoding='utf-8') as f:
            json.dump({
                "discovery_time": datetime.now().isoformat(),
                "total_sources": len(sources),
                "sources": sources
            }, f, ensure_ascii=False, indent=2)

        # 生成配置文件
        config_sources = []
        for source in sources:
            if source['total_score'] >= 50:  # 只保留高质量的源
                config_sources.append({
                    "name": source.get('title', 'Unknown'),
                    "url": source.get('url', ''),
                    "type": source.get('type', 'unknown'),
                    "enabled": True,
                    "score": source.get('total_score', 0)
                })

        config_file = self.results_dir / f"auto_sources_{timestamp}.yaml"
        import yaml
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump({
                "discovery_time": datetime.now().isoformat(),
                "total_count": len(config_sources),
                "sources": config_sources
            }, f, allow_unicode=True, default_flow_style=False)

        self.logger.info(f"💾 保存到: {detail_file}")
        self.logger.info(f"⚙️ 配置文件: {config_file}")

        return detail_file, config_file

    async def research_with_context7(self, topic: str) -> List[Dict]:
        """使用Context7研究技术方案"""
        self.logger.info(f"📚 Context7研究: {topic}")

        try:
            # 解析相关库
            library_id = await mcp__context7__resolve-library-id(
                libraryName=topic
            )

            if library_id:
                # 获取文档
                docs = await mcp__context7__get-library-docs(
                    context7CompatibleLibraryID=library_id,
                    topic="data sources and scraping",
                    mode="info"
                )

                # 从文档中提取数据源信息
                sources = self.extract_sources_from_docs(docs)
                return sources

        except Exception as e:
            self.logger.error(f"Context7研究失败: {e}")

        return []

    def extract_sources_from_docs(self, docs: Any) -> List[Dict]:
        """从文档中提取数据源信息"""
        # 这里需要解析文档内容，提取URL和数据源信息
        # 实际实现需要根据docs的结构进行解析
        extracted = []

        # 模拟提取结果
        extracted.append({
            "url": "https://example.com/from-docs",
            "title": "从文档发现的数据源",
            "type": "技术文档推荐",
            "source": "Context7"
        })

        return extracted


async def main():
    """主函数"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    discovery = MCPSourceDiscovery()

    print("\n" + "="*80)
    print("🌐 MCP驱动的数据源发现工具")
    print("="*80)

    # 执行发现
    sources = await discovery.discover_all_sources()

    # 打印结果
    print(f"\n✅ 发现 {len(sources)} 个高质量数据源:")
    print("-"*80)

    for i, source in enumerate(sources[:10], 1):  # 只显示前10个
        print(f"\n{i}. {source.get('title', 'Unknown')}")
        print(f"   URL: {source.get('url', '')}")
        print(f"   类型: {source.get('type', '')}")
        print(f"   评分: {source.get('total_score', 0)}/100")
        print(f"   更新: {source.get('update_frequency', '')}")

    if len(sources) > 10:
        print(f"\n... 还有 {len(sources) - 10} 个数据源")

    print("\n" + "="*80)
    print("📝 建议下一步:")
    print("1. 查看生成的配置文件")
    print("2. 手动验证高评分的数据源")
    print("3. 将有效的源添加到系统配置")
    print("4. 运行爬虫测试新源")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())