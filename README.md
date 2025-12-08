# 智能设计营销自动化系统

> 🎯 **专为智能化设计工程师打造的自动化营销工具**
>
> 7×24小时自动搜索政府采购、高校、国企中标公告，智能提取联系人信息，自动化邮件营销

## ✨ 最新特性 - v3.0 统一架构

### 🏗️ 架构优化
- ✨ **单一入口**: 所有功能通过 `python main.py` 启动
- 🧠 **核心模块**: 3个专门模块，消除重复代码
- ⚙️ **配置驱动**: 统一配置系统，自动生成默认配置
- 📊 **零重复**: 从73个Python文件整合为统一架构

### 🎯 核心功能
- ✅ **多源爬虫**: 政府采购网、高校、国企采购平台
- ✅ **智能提取**: 本地规则 + AI增强的联系人提取
- ✅ **个性营销**: 多模板邮件发送系统
- ✅ **数据管理**: SQLite数据库 + Excel导出
- ✅ **队列系统**: 异步处理详情页抓取
- ✅ **Web界面**: Streamlit驱动的数据可视化

## 🚀 快速开始

### 1. 环境准备
```bash
# 安装Python依赖
pip install -r requirements.txt

# 核心依赖
# requests, beautifulsoup4, pandas, openpyxl
# streamlit (Web界面)
# openai (AI处理，可选)
```

### 2. 系统配置
```bash
# 启动交互模式配置
python main.py --config

# 或直接运行
python main.py --interactive
```

### 3. 开始使用

#### 命令行模式
```bash
# 运行爬虫（抓取招标信息）
python main.py --scrape

# 提取联系人
python main.py --extract

# 发送邮件
python main.py --email

# 启动Web界面
python main.py --web

# 查看系统状态
python main.py --status

# 运行队列worker（处理详情页）
python main.py --queue

# 清理重复文件
python main.py --cleanup
```

#### 交互模式
```bash
python main.py
# 或
python main.py --interactive
```

## 📋 交互菜单

```
📋 智能设计营销系统 v3.0
=========================
1. 🕷️  运行爬虫        # --scrape
2. 👥 提取联系人        # --extract
3. 📧 发送邮件          # --email
4. 🌐 Web界面           # --web
5. ⚙️ 系统配置          # --config
6. 📊 系统状态          # --status
7. 🧹 清理重复文件      # --cleanup
8. 🚪 退出
```

## 📁 项目架构

```
work/
├── main.py                    # 🎯 唯一启动入口
├── core/                      # 🧠 核心功能模块
│   ├── __init__.py
│   ├── scraper.py            # 统一爬虫引擎（支持多数据源）
│   ├── extractor.py          # 联系人提取器（本地+AI）
│   ├── emailer.py            # 邮件发送器
│   ├── ai_processor.py       # AI智能处理
│   ├── local_processor.py    # 本地规则处理
│   ├── fetcher.py            # HTTP客户端
│   ├── queue.py              # 异步队列系统
│   └── retry.py              # 重试机制
├── config/                    # ⚙️ 配置管理
│   ├── __init__.py
│   ├── settings.py           # 统一配置系统
│   └── user_config.json      # 用户配置文件（自动生成）
├── data/                      # 📊 数据目录
│   └── marketing.db          # SQLite数据库
├── logs/                      # 📝 日志目录
│   └── marketing.log         # 运行日志
├── scripts/                   # 📜 辅助脚本（演示、测试）
│   └── README.md
├── tests/                     # 🧪 单元测试
├── models.py                  # 数据模型
├── http_client.py             # HTTP客户端
├── parser.py                  # HTML解析器
├── storage.py                 # 数据存储
├── analyze_ccgp.py            # 分析工具
├── requirements.txt           # 依赖列表
├── .gitignore                 # Git忽略规则
└── README.md                  # 项目说明
```

## 💡 配置说明

### 首次配置流程
运行 `python main.py --config` 后，系统会引导您配置：

1. **用户信息**
   - 姓名、邮箱、公司

2. **邮件配置**
   - SMTP服务器（默认QQ邮箱）
   - 发件人邮箱和密码
   - 自动测试配置

3. **AI处理配置**（可选）
   - OpenAI API密钥
   - 模型选择（默认gpt-3.5-turbo）
   - 批处理大小

4. **数据源配置**
   - 启用/禁用特定数据源
   - 设置爬取延迟

### 配置文件示例
```json
{
  "user_info": {
    "name": "您的姓名",
    "email": "your@email.com",
    "company": "您的公司"
  },
  "email": {
    "smtp_server": "smtp.qq.com",
    "smtp_port": 587,
    "sender_email": "your@qq.com",
    "sender_password": "your_password",
    "configured": true
  },
  "ai_processing": {
    "enabled": true,
    "provider": "openai",
    "api_key": "sk-...",
    "model": "gpt-3.5-turbo"
  },
  "scraper": {
    "sources": {
      "ccgp": {
        "enabled": true,
        "delay_min": 3,
        "delay_max": 8
      }
    }
  }
}
```

## 🎮 核心模块详解

### 1. 爬虫引擎 (`core/scraper.py`)
- **多数据源支持**: 政府采购网、高校采购等
- **智能反爬**: 动态延迟、User-Agent轮换
- **增量更新**: 基于日期的去重机制
- **队列系统**: 异步处理详情页抓取

### 2. 联系人提取器 (`core/extractor.py`)
- **双模式处理**:
  - 本地规则：正则表达式提取，快速准确
  - AI增强：使用GPT模型，提高复杂场景准确率
- **多格式支持**: 邮箱、电话、公司、联系人姓名
- **批量处理**: 支持大量数据并发处理

### 3. 邮件发送器 (`core/emailer.py`)
- **多模板支持**: 营销、跟进、通知等模板
- **发送验证**: 配置测试功能
- **批量发送**: 支持限制发送频率
- **状态跟踪**: 记录发送结果

## 📊 数据流程

```
1. 爬虫抓取
   └── 存储到 scraped_data 表

2. 队列处理
   └── 异步抓取详情页内容

3. 联系人提取
   └── 从详情页提取联系信息
   └── 存储到 contacts 表

4. 邮件发送
   └── 从 contacts 表读取
   └── 批量发送营销邮件
```

## 🛠️ 常见问题

### Q: 如何启用AI处理？
```bash
# 配置时选择启用AI
python main.py --config
# 输入OpenAI API密钥
```

### Q: 爬虫没有数据？
- 检查网络连接
- 查看日志：`tail -f logs/marketing.log`
- 确认数据源已启用

### Q: 邮件发送失败？
- 检查SMTP配置
- QQ邮箱需使用应用专用密码
- 运行 `python main.py --config` 重新配置

### Q: Web界面无法启动？
```bash
# 安装streamlit
pip install streamlit

# 启动Web界面
python main.py --web
```

## 🧪 测试功能

```bash
# 测试网络连接
python -c "from core.scraper import scraper; print(scraper.test_connection())"

# 测试邮件配置
python -c "from core.emailer import emailer; print(emailer.test_config())"

# 查看系统状态
python main.py --status
```

## 📈 性能优化

### 推荐配置
```json
{
  "scraper": {
    "network": {
      "concurrency": 10,
      "timeout": 30,
      "retry_attempts": 3
    }
  },
  "ai_processing": {
    "batch_size": 10,
    "max_tokens": 1000
  }
}
```

### 定时任务
```bash
# 添加到crontab
# 每天早上9点爬取数据
0 9 * * * cd /path/to/work && python main.py --scrape

# 每天下午3点提取联系人
0 15 * * * cd /path/to/work && python main.py --extract
```

## 📝 更新日志

### v3.0 (2025-12-08) - 统一架构
- 🏗️ **架构重构**: 73个Python文件 → 统一入口
- 🗑️ **代码清理**: 删除2864行重复代码
- 📦 **模块整合**: 8个爬虫 → 1个核心模块
- 🎯 **功能整合**: 所有功能通过main.py访问
- 📁 **目录优化**: scripts目录存放辅助脚本

### v2.0 (2025-12-04) - 模块化
- 🧩 模块化设计
- 🛡️ 类型安全
- ⚙️ 配置系统
- 🧪 测试覆盖

### v1.0 (2025-12-03) - 初始版本
- 基础爬虫功能
- 联系信息提取

## 🔒 安全与合规

- ✅ 仅采集公开招标公告
- ✅ 遵守网站robots.txt
- ✅ 本地数据存储
- ✅ 符合邮件营销法规

## 📄 许可证

本项目仅供学习和研究使用，请遵守相关法律法规。

---

**免责声明**: 本工具仅用于合法的业务推广目的，使用者需自行承担使用风险。

---

> 💡 **提示**: 首次使用建议运行 `python main.py --config` 完成配置，然后使用 `python main.py --scrape` 开始抓取数据。