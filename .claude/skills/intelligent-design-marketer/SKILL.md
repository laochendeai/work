---
name: intelligent-design-marketer
description: 专为智能化设计工程师打造的个人自动化营销开发技能，快速爬取政府采购、高校、国企、上市公司中标公告，提取联系人信息并自动邮件营销，显著提升项目获取效率
---

# 智能设计营销自动化开发技能

这是一个专为个人智能化设计工程师打造的开发技能，能够快速搭建、测试和部署自动化营销系统，帮助您在2周内完成从概念到运行的完整系统。

## 🎯 技能特色（个人用户专用）

**专为个人用户设计，企业级功能，个人用户友好：**

- ✨ **零配置启动** - 一键配置向导，5分钟完成设置
- 🛡️ **智能错误处理** - 个人用户友好的错误提示和解决方案
- 📊 **可视化界面** - Streamlit Web界面，操作简单直观
- 🏥 **健康检查** - 自动诊断系统问题并提供建议
- 📱 **快速启动** - 单命令启动所有服务，支持交互模式

## 🚀 快速开始（个人用户）

### 方式一：一键配置和启动（推荐）

```bash
# 1. 克隆或下载项目到本地
# 2. 进入项目目录
cd intelligent-design-marketer

# 3. 一键启动（自动检查依赖并配置）
python quick_start.py --interactive
```

### 方式二：分步配置

```bash
# 1. 运行配置向导
python quick_start.py --config

# 2. 启动服务（Web界面 + 爬虫）
python quick_start.py

# 3. 查看服务状态
python quick_start.py --status
```

### 方式三：仅启动Web界面

```bash
# 仅启动Web管理界面
python quick_start.py --services web

# 访问 http://localhost:8501
```

## 🛠️ 系统健康检查

```bash
# 运行完整健康检查
python src/utils/health_checker.py

# 自动修复常见问题
python src/utils/health_checker.py  # 选择自动修复选项
```

## 💡 个人用户使用场景

### 场景1：首次使用（推荐流程）
```bash
# 1. 一键启动并进入交互模式
python quick_start.py --interactive

# 2. 根据提示完成配置
# 3. Web界面自动打开，开始使用
```

### 场景2：日常使用
```bash
# 启动所有服务
python quick_start.py

# 在另一个终端查看状态
python quick_start.py --status
```

### 场景3：问题排查
```bash
# 1. 运行健康检查
python src/utils/health_checker.py

# 2. 查看详细错误日志
python quick_start.py  # 选择 logs 命令

# 3. 重新配置
python quick_start.py --config
```

## ⚠️ 重要提醒（个人用户）

- **个人用户专用**：本技能专为个人用户优化，不适用于企业级部署
- **资源要求**：建议至少2GB内存，稳定网络连接
- **数据安全**：所有数据存储在本地，请定期备份
- **合规使用**：请遵守相关法律法规，合理使用爬虫功能
- **技术支持**：遇到问题请先运行健康检查工具

## 📚 核心开发流程（进阶用户）

### 2. 爬虫模块开发

**核心爬虫架构：**
- 使用 `references/crawler_patterns.md` 中的爬虫策略
- 执行 `scripts/create_scraper.py --source government` 生成基础爬虫
- 使用 `assets/templates/scraper_template.py` 作为起点

**开发流程：**
```python
# 生成政府网站爬虫
python scripts/generate_scraper.py --template government --config config.json

# 生成高校采购爬虫
python scripts/generate_scraper.py --template university --targets "tsinghua,pku,fudan"

# 生成企业采购爬虫
python scripts/generate_scraper.py --template enterprise --targets "huawei,tencent,alibaba"
```

### 3. 信息提取和处理

**智能信息提取：**
```python
# 配置信息提取规则
python scripts/setup_extraction.py --config extraction_rules.json

# 测试信息提取准确性
python scripts/test_extraction.py --test_data samples/
```

### 4. 邮件营销系统

**自动化邮件发送：**
```python
# 配置邮件模板
python scripts/setup_email.py --template personal --smtp qq

# 测试邮件发送
python scripts/test_email.py --send_test true
```

### 5. 部署和监控

**一键部署：**
```bash
# 生成可执行文件
python scripts/build_executable.py

# 设置定时任务
python scripts/setup_scheduler.py --hourly

# 启动监控
python scripts/start_monitoring.py
```

## 可重用资源

### Scripts/ 脚本文件

- **`init_project.py`** - 项目初始化脚本，自动生成项目结构
- **`create_scraper.py`** - 爬虫生成器，基于模板快速创建爬虫
- **`setup_extraction.py`** - 信息提取配置工具
- **`setup_email.py` - 邮件营销配置工具
- **`build_executable.py` - 打包可执行文件工具
- **`test_system.py`** - 系统集成测试脚本
- **`deploy_system.py`** - 自动化部署脚本

### References/ 参考资料

- **`crawler_patterns.md`** - 爬虫策略和反爬虫技术文档
- **`extraction_rules.md` - 联系人信息提取规则和正则表达式
- **`email_templates.md` - 邮件营销模板库
- **`project_templates.md` - 不同项目类型的配置模板
- **`deployment_guide.md` - 部署和运维指南
- **`optimization_tips.md` - 性能优化和最佳实践

### Assets/ 资源文件

- **`templates/`** - 项目模板目录
  - `basic_project/` - 基础项目模板
  - `comprehensive_project/` - 完整项目模板
  - `scraper_template.py` - 爬虫代码模板
  - `email_template.txt` - 邮件模板
- **`config_samples/` - 配置示例
  - `personal_config.json` - 个人信息配置
  - `scraper_config.json` - 爬虫配置
  - `email_config.json` - 邮件配置
- **`test_data/` - 测试数据样本

## 开发工具和命令

### 快速原型开发

**5分钟原型：**
```bash
# 创建基础原型
python scripts/quick_prototype.py --keywords "弱电,智能化" --test_data

# 验证爬虫功能
python scripts/validate_scraper.py --url "https://search.ccgp.gov.cn"

# 测试邮件发送
python scripts/validate_email.py --recipient "test@example.com"
```

### 代码质量保证

**自动化测试：**
```bash
# 运行所有测试
python scripts/run_all_tests.py

# 生成测试报告
python scripts/generate_test_report.py

# 代码质量检查
python scripts/code_quality_check.py
```

### 部署和运维

**一键部署：**
```bash
# 生成部署包
python scripts/create_deployment_package.py

# 自动部署到服务器
python scripts/auto_deploy.py --server "personal-server"

# 设置监控
python scripts/setup_monitoring.py --alerts "email,sms"
```

## 性能优化指南

### 爬虫性能优化
- 使用 `references/optimization_tips.md` 中的策略
- 执行 `python scripts/analyze_performance.py` 分析瓶颈
- 应用 `python scripts/optimize_scraper.py` 优化爬虫

### 系统稳定性
- 使用内置的重试机制和错误处理
- 执行 `python scripts/setup_monitoring.py` 设置监控
- 参考 `references/deployment_guide.md` 的运维指南

## 扩展和定制

### 添加新的数据源
```python
# 添加新的采购网站
python scripts/add_data_source.py --type "new_type" --config "config.json"

# 更新爬虫模板
python scripts/update_scraper_template.py --template "new_template"
```

### 自定义功能模块
```python
# 添加新的处理模块
python scripts/add_module.py --name "custom_processor" --path "modules/"

# 更新系统配置
python scripts/update_system_config.py --feature "new_feature"
```

## 最佳实践

### 开发效率提升
1. **使用模板优先** - 总是从 `assets/templates/` 开始
2. **测试驱动开发** - 使用 `scripts/test_*.py` 验证功能
3. **增量开发** - 使用 `scripts/iterative_development.py` 快速迭代
4. **代码复用** - 使用 `scripts/create_reusable_component.py` 创建可复用组件

### 系统可靠性
1. **错误处理** - 所有脚本都包含完善的错误处理
2. **日志记录** - 使用统一的日志格式和级别
3. **备份恢复** - 自动备份重要数据和配置
4. **监控告警** - 实时监控系统状态和性能

这个技能让您能够在最短时间内构建出完整的智能化设计营销自动化系统，大幅提升开发效率和项目成功率！