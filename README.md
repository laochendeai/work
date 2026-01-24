# 政府采购爬虫

一个简洁、可靠的政府采购网站爬虫系统。

## 功能特点

- 🕷️ **浏览器自动化** - 使用Playwright，支持JS渲染
- 📋 **公告列表爬取** - 自动爬取政府采购网站的公告列表
- 📄 **详情页抓取** - 获取每个公告的详细内容
- 👥 **联系人提取** - 从公告中提取采购人、代理机构、供应商信息
- 💾 **数据存储** - SQLite数据库存储
- 📊 **数据导出** - 支持导出为Excel、CSV格式

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. 配置数据源

编辑 `config/sources.yaml`，添加您要爬取的网站：

```yaml
sources:
  - name: "中国政府采购网"
    url: "http://www.ccgp.gov.cn"
    list_page: "/pub/data/bid/news/"
    enabled: true
```

### 3. 运行爬虫

```bash
python main.py
```

## 项目结构

```
work/
├── config/        # 配置文件
├── scraper/       # 爬虫核心
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

# 爬取设置
MAX_PAGES = 10              # 每个源最多爬取页数
DELAY_MIN = 1               # 最小延迟(秒)
DELAY_MAX = 3               # 最大延迟(秒)
```

## 数据存储

爬取的数据保存在 `data/` 目录：
- `data/gp.db` - SQLite数据库
- `data/exports/` - 导出的Excel/CSV文件

## 常见问题

**Q: Playwright安装失败？**
```bash
pip install --upgrade pip
pip install playwright
playwright install chromium
```

**Q: 爬虫运行很慢？**
- 减少 `MAX_PAGES` 配置
- 减小 `DELAY_MIN` 和 `DELAY_MAX`

**Q: 某些网站爬取失败？**
- 检查网站是否需要登录
- 检查网站是否有反爬机制
- 尝试增加超时时间

## License

MIT
