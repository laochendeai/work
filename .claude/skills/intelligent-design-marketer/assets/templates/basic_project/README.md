# 智能设计营销自动化系统 - 基础项目模板

## 项目概述

这是一个基于智能设计营销自动化开发技能创建的基础项目模板，专为智能化设计工程师打造的自动化营销工具。

## 快速开始

### 1. 项目结构

```
basic-project/
├── src/                    # 源代码目录
│   ├── scrapers/          # 爬虫模块
│   │   └── government_scraper.py
│   ├── extractors/        # 信息提取模块
│   │   └── contact_extractor.py
│   ├── email_marketing/   # 邮件营销模块
│   │   └── email_sender.py
│   ├── utils/             # 工具模块
│   │   ├── database_manager.py
│   │   ├── logger.py
│   │   └── config_loader.py
│   └── main.py            # 主程序入口
├── config/                # 配置文件
│   ├── project_config.json
│   ├── extraction_config.json
│   └── email_config.json
├── data/                  # 数据存储
│   ├── raw/
│   ├── processed/
│   └── marketing_data.db
├── templates/             # 邮件模板
│   └── emails/
│       ├── default.html
│       ├── government.html
│       └── university.html
├── tests/                 # 测试文件
│   ├── test_scraper.py
│   ├── test_extractor.py
│   └── test_email.py
├── scripts/               # 脚本工具
│   ├── run_scraper.py
│   ├── test_extraction.py
│   └── send_test_email.py
├── logs/                  # 日志文件
├── docs/                  # 项目文档
├── requirements.txt       # 依赖包
└── README.md             # 项目说明
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置系统

编辑 `config/project_config.json` 文件，配置：
- 爬虫参数和目标网站
- 邮件SMTP设置
- 数据库配置
- 提取规则

### 4. 运行系统

```bash
# 运行完整系统
python src/main.py

# 执行特定任务
python src/main.py --task scraping
python src/main.py --task extraction
python src/main.py --task email
```

## 核心功能

### 1. 自动爬取

- **政府采购网站**：自动爬取政府采购、招标公告、中标信息
- **反爬虫策略**：随机延时、代理轮换、请求头伪装
- **数据清洗**：去重、格式化、数据验证

### 2. 智能提取

- **联系人信息**：姓名、电话、邮箱、职位、部门
- **项目信息**：项目名称、预算、截止时间、技术要求
- **机器学习增强**：上下文分析、置信度计算

### 3. 邮件营销

- **个性化邮件**：基于客户类型的邮件模板
- **批量发送**：控制发送频率，避免被封禁
- **发送跟踪**：送达率、打开率、点击率统计

## 配置说明

### 项目配置 (project_config.json)

```json
{
  "project_info": {
    "name": "your-marketing-system",
    "type": "basic",
    "version": "1.0.0"
  },
  "scraping": {
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "delay_range": [1, 3],
    "timeout": 30,
    "max_retries": 3,
    "concurrent_requests": 5
  },
  "data_sources": {
    "government": {
      "enabled": true,
      "base_url": "https://search.ccgp.gov.cn",
      "search_keywords": ["弱电", "智能化", "安防", "网络建设"]
    }
  },
  "email": {
    "smtp_server": "smtp.qq.com",
    "smtp_port": 587,
    "batch_size": 50,
    "delay_between_batches": 300
  }
}
```

### 邮件配置 (email_config.json)

```json
{
  "sender": {
    "name": "您的姓名",
    "email": "your_email@qq.com",
    "password": "your_password_or_app_password",
    "smtp_type": "qq"
  },
  "sending": {
    "batch_size": 50,
    "delay_between_emails": 5,
    "delay_between_batches": 300
  }
}
```

## 开发指南

### 添加新的数据源

1. 在 `src/scrapers/` 目录下创建新的爬虫文件
2. 继承基础爬虫类并实现特定逻辑
3. 在配置文件中添加数据源配置

```python
# src/scrapers/custom_scraper.py
class CustomScraper(BaseScraper):
    def scrape_data(self):
        # 实现自定义爬取逻辑
        pass
```

### 自定义提取规则

```python
# src/extractors/custom_extractor.py
class CustomExtractor(ContactExtractor):
    def extract_custom_field(self, text):
        # 实现自定义字段提取
        pass
```

### 扩展邮件功能

1. 在 `templates/emails/` 中添加新的邮件模板
2. 修改 `src/email_marketing/` 中的发送逻辑
3. 配置SMTP服务器设置

## 测试

### 运行单元测试

```bash
python -m pytest tests/
```

### 运行功能测试

```bash
# 测试爬虫功能
python scripts/test_scraper.py

# 测试信息提取
python scripts/test_extraction.py

# 测试邮件发送
python scripts/send_test_email.py
```

## 部署

### 1. 生成可执行文件

```bash
python scripts/build_executable.py
```

### 2. 设置定时任务

```bash
python scripts/setup_scheduler.py --hourly
```

### 3. 启动监控

```bash
python scripts/start_monitoring.py
```

## 注意事项

- **法律法规**：遵守网站robots.txt协议，尊重版权和隐私
- **技术限制**：合理控制爬取频率，避免对目标网站造成压力
- **数据安全**：妥善保管获取的联系人信息，避免泄露
- **邮件合规**：确保邮件发送符合相关法规要求

## 技术支持

- 查看日志文件 `logs/` 了解系统运行状态
- 参考文档 `docs/` 获取详细技术说明
- 使用测试脚本验证功能正常性

## 更新日志

### v1.0.0 (2024-01-01)
- 初始版本发布
- 支持政府采购网站爬取
- 实现基础信息提取功能
- 提供邮件营销模板