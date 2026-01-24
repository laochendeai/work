"""
政府采购网智能搜索爬虫 - 增强版（兼容层）

历史上该模块包含一个与 Playwright sync API 不兼容的 async 实现（并且会在 pytest
环境触发事件循环冲突）。当前版本保留原有导出名称，内部复用纯同步实现：
`scraper.ccgp_searcher_v2.CCGPSearcherEnhanced`。
"""

from __future__ import annotations

from .ccgp_searcher_v2 import CCGPSearcherEnhanced as CCGPSearcherEnhanced


class CCGPSearcherSync(CCGPSearcherEnhanced):
    """同步版本（保持旧代码/测试的导入路径不变）"""

