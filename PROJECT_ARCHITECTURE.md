# 中标信息整理 - 项目架构设计

## 设计原则
- **简单优先** - 避免过度抽象和复杂配置
- **模块清晰** - 每个模块职责单一，易于理解
- **易于调试** - 代码可读性高，日志完善
- **稳定可靠** - 完善的超时和错误处理

## 目录结构
```
work/
├── config/                 # 配置文件
│   ├── sources.yaml       # 数据源配置（少量固定网站）
│   └── settings.py        # 全局设置
├── scraper/               # 核心爬虫模块
│   ├── base.py           # 基础爬虫类
│   ├── fetcher.py        # Playwright浏览器管理
│   ├── parser.py         # 页面解析器
│   └── ccgp_bxsearcher.py # 搜索平台爬虫
├── extractor/            # 数据提取模块
│   ├── contact.py        # 联系人提取
│   └── cleaner.py        # 数据清洗
├── storage/              # 数据存储模块
│   ├── database.py       # 数据库操作
│   └── export.py         # 数据导出
├── utils/                # 工具函数
│   ├── helpers.py        # 辅助函数
│   └── keyword_list.py   # 关键词列表管理
├── main.py              # 主入口
├── requirements.txt      # 依赖包
└── README.md            # 项目说明
```

## 核心模块说明

### 1. scraper/ - 爬虫核心
- **fetcher.py**: 封装Playwright，管理浏览器生命周期
- **parser.py**: 解析公告列表和详情页
- **base.py**: 统一的爬虫基类
- **ccgp_bxsearcher.py**: 政府采购搜索平台爬虫

### 2. extractor/ - 数据提取
- **contact.py**: 从公告中提取联系人（电话、邮箱、公司等）
- **cleaner.py**: 数据清洗和验证

### 3. storage/ - 数据存储
- **database.py**: SQLite数据库操作
- **export.py**: 导出为Excel/CSV格式

### 4. config/ - 配置管理
- **sources.yaml**: 简单的YAML配置，定义固定网站
- **settings.py**: 加载配置的辅助函数

## 数据流
```
配置文件 → 爬虫模块 → 页面解析 → 数据提取 → 数据存储 → 导出结果
    ↓         ↓          ↓          ↓          ↓         ↓
  sources   fetcher   parser   extractor   database  export
```

## 技术栈
- **浏览器**: Playwright (稳定、现代)
- **解析**: BeautifulSoup4 (简单、可靠)
- **存储**: SQLite (轻量、无需安装)
- **导出**: pandas + openpyxl (Excel支持)
