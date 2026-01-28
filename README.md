# 中标信息整理

一个简洁、可靠的中标信息整理工具，帮助您从公共资源交易平台获取和整理中标公告信息。

## 功能特点

- 🕷️ **浏览器自动化** - 使用Playwright，支持JS渲染
- 🔍 **智能搜索** - 支持关键词全文搜索，自动筛选相关公告
- 📋 **公告列表获取** - 自动获取公共资源交易网站的公告列表
- 📄 **详情页抓取** - 获取每个公告的详细内容
- 👥 **联系人提取** - 从公告中提取采购人、代理机构、供应商信息
- 💾 **数据存储** - SQLite数据库存储
- 📊 **数据导出** - 支持导出为Excel、CSV格式
- 📇 **名片系统** - 按单位聚合联系人信息

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. 运行 bxsearch（推荐：唯一数据源）

bxsearch 支持关键词可替换、品目/类别/类型/时间可选，并会在多次搜索时按公告 `url` 去重，避免重复解析同一详情页。

**单个关键词：**

```bash
python main.py bxsearch --kw 机房 --search-type fulltext --pinmu engineering --time today --max-pages 3
```

**多个关键词依次搜索（同一 URL 会自动跳过二次详情解析）：**

```bash
python main.py bxsearch --kw 智能 机房 弱电 --search-type fulltext --pinmu engineering --time today --max-pages 3
```

**逗号分隔关键词：**

```bash
python main.py bxsearch --kw 智能,机房,弱电 --search-type fulltext --pinmu engineering --time today --max-pages 3
```

**从文件读取关键词（每行一个，支持逗号分隔；`#` 开头为注释）：**

```bash
python main.py bxsearch --kw-file data/keywords.txt --search-type fulltext --pinmu engineering --time today --max-pages 3
```

**自定义时间范围：**

```bash
python main.py bxsearch --kw 智能 --time custom --start-date 2026-01-01 --end-date 2026-01-24 --max-pages 3
```

### 3. 查询名片系统

按单位聚合联系人（同一联系人在不同公告出现过的手机号/邮箱会合并保留）：

```bash
python main.py cards --company "浙江警察学院"
python main.py cards --company "浙江警察" --like
```

---

### 4. 运行原有“多数据源采集”（可选）

如果你仍然需要按 `config/sources.yaml` 获取公告列表页（非 bxsearch），可以继续使用原有入口：

```bash
python main.py
```

## 项目结构

```
work/
├── config/        # 配置文件
├── scraper/       # 采集核心
├── extractor/     # 数据提取
├── storage/       # 数据存储
├── utils/         # 工具函数
├── data/          # 数据输出目录
└── main.py       # 主入口
```

## 配置说明

### 数据源配置 (config/sources.yaml)

```yaml
sources:
  - name: "网站名称"
    url: "https://example.com"      # 网站首页
    list_page: "/news/"             # 公告列表页路径
    enabled: true                   # 是否启用
```

### 全局设置 (config/settings.py)

```python
# 浏览器设置
BROWSER_HEADLESS = True      # 无头模式
BROWSER_TIMEOUT = 30000      # 页面超时(毫秒)

# 整理设置
MAX_PAGES = 10              # 每个源最多采集页数
DELAY_MIN = 1               # 最小延迟(秒)
DELAY_MAX = 3               # 最大延迟(秒)
```

## 数据存储

采集的数据保存在 `data/` 目录：
- `data/gp.db` - SQLite数据库
- `data/exports/` - 导出的Excel/CSV文件

## 常见问题

**Q: Playwright安装失败？**
```bash
pip install --upgrade pip
pip install playwright
playwright install chromium
```

**Q: 程序运行很慢？**
- 减少 `MAX_PAGES` 配置
- 减小 `DELAY_MIN` 和 `DELAY_MAX`

**Q: 某些网站采集失败？**
- 检查网站是否需要登录
- 检查网站是否有反采集机制
- 尝试增加超时时间

## License

MIT
