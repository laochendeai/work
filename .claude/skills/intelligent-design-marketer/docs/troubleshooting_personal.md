# 个人用户故障排除指南

## 🚨 快速诊断

**遇到问题时，首先运行：**
```bash
python src/utils/health_checker.py
```

这个工具会自动检测90%的常见问题并提供解决方案。

---

## 🛠️ 常见问题解决

### 1. 启动问题

#### 问题：无法启动系统
**症状**：运行 `python quick_start.py` 时出错

**解决方案：**
```bash
# 1. 检查Python版本（需要3.7+）
python --version

# 2. 安装依赖
pip install -r requirements.txt

# 3. 检查是否在正确目录
pwd  # 应该显示 .../intelligent-design-marketer

# 4. 运行健康检查
python src/utils/health_checker.py
```

#### 问题：Web界面无法访问
**症状**：浏览器打不开 http://localhost:8501

**解决方案：**
```bash
# 1. 检查服务状态
python quick_start.py --status

# 2. 如果服务未运行，重新启动
python quick_start.py --services web

# 3. 检查端口是否被占用
netstat -an | grep 8501

# 4. 尝试不同端口
python -m streamlit run src/web/dashboard.py --server.port 8502
```

### 2. 配置问题

#### 问题：邮件发送失败
**症状**：邮件配置正确但发送失败

**解决方案：**
```bash
# 1. 检查邮箱设置
# - QQ邮箱：开启IMAP/SMTP服务，使用应用专用密码
# - 163邮箱：开启SMTP服务，使用授权码
# - Gmail：开启两步验证，使用应用专用密码

# 2. 重新配置邮件
python quick_start.py --config

# 3. 测试邮件配置
python -c "
import smtplib
# 在这里填入你的邮箱配置进行测试
"
```

#### 问题：爬虫无法工作
**症状**：没有数据被爬取

**解决方案：**
```bash
# 1. 检查网络连接
ping www.baidu.com

# 2. 检查目标网站是否可访问
curl -I http://www.ccgp.gov.cn

# 3. 重新配置爬虫
python quick_start.py --config

# 4. 查看爬虫日志
python quick_start.py  # 选择 logs 命令
```

### 3. 性能问题

#### 问题：系统运行缓慢
**症状**：操作响应慢，爬取速度慢

**解决方案：**
```bash
# 1. 检查系统资源
python src/utils/health_checker.py

# 2. 清理日志文件
find logs/ -name "*.log" -size +50M -delete

# 3. 优化数据库
sqlite3 data/marketing.db "VACUUM;"

# 4. 调整爬取频率
# 编辑 config/user_config.json，增大 delay_range
```

#### 问题：内存占用过高
**症状**：系统变得卡顿

**解决方案：**
```bash
# 1. 重启服务
python quick_start.py  # 选择 stop 然后 start

# 2. 清理缓存
rm -rf data/cache/*

# 3. 减少并发数
# 编辑配置文件，降低 max_workers
```

### 4. 数据问题

#### 问题：数据库损坏
**症状**：数据读取失败

**解决方案：**
```bash
# 1. 备份现有数据
cp data/marketing.db data/marketing_backup.db

# 2. 重建数据库
rm data/marketing.db
python quick_start.py  # 重新启动会自动创建

# 3. 恢复重要数据（如有）
sqlite3 data/marketing_backup.db ".dump" | sqlite3 data/marketing.db
```

#### 问题：联系人提取不准确
**症状**：提取的联系人信息错误或不完整

**解决方案：**
```bash
# 1. 更新提取规则
# 编辑 src/core/contact_extractor.py

# 2. 查看原始数据
sqlite3 data/marketing.db "SELECT raw_content FROM scraped_data LIMIT 5;"

# 3. 手动验证提取结果
python scripts/test_extraction.py --sample
```

---

## 🔧 高级故障排除

### 手动调试步骤

#### 1. 检查日志文件
```bash
# 查看最新错误
tail -f logs/app.log

# 查看所有错误
grep -i error logs/*.log

# 查看特定服务日志
tail -f logs/scraper.log
```

#### 2. 测试各个组件
```bash
# 测试网络连接
python -c "import requests; print(requests.get('https://www.baidu.com').status_code)"

# 测试数据库连接
python -c "import sqlite3; print(sqlite3.connect('data/marketing.db'))"

# 测试邮件服务
python scripts/test_email.py
```

#### 3. 重置系统状态
```bash
# 安全重置（保留数据）
python src/utils/reset_system.py --safe

# 完全重置（删除数据）
python src/utils/reset_system.py --full
```

---

## 📞 获取帮助

### 自助资源
1. **健康检查工具**：`python src/utils/health_checker.py`
2. **用户手册**：`docs/user_guide.md`
3. **配置向导**：`python quick_start.py --config`

### 常用命令速查
```bash
# 查看系统状态
python quick_start.py --status

# 重启所有服务
python quick_start.py  # 交互模式选择 restart

# 查看实时日志
python quick_start.py  # 交互模式选择 logs

# 重新配置
python quick_start.py --config

# 运行诊断
python src/utils/health_checker.py
```

### 问题报告模板
如果遇到无法解决的问题，请提供以下信息：

1. **系统信息**：
   ```bash
   python --version
   pip --version
   uname -a  # Linux/Mac
   # 或
   systeminfo  # Windows
   ```

2. **错误日志**：
   ```bash
   python src/utils/health_checker.py
   # 并保存报告
   ```

3. **配置信息**（敏感信息请删除）：
   ```bash
   cat config/user_config.json
   ```

---

## 💡 预防措施

### 定期维护
```bash
# 每周运行一次健康检查
python src/utils/health_checker.py

# 每月清理日志
find logs/ -name "*.log" -mtime +30 -delete

# 每月备份数据
cp data/marketing.db backups/marketing_$(date +%Y%m%d).db
```

### 最佳实践
1. **定期更新**：保持依赖包最新版本
2. **监控资源**：关注内存和磁盘使用情况
3. **备份数据**：定期备份重要数据
4. **合规使用**：遵守网站使用条款
5. **安全配置**：使用强密码和应用专用密码

### 性能优化建议
1. **合理设置爬取频率**：避免过于频繁的请求
2. **使用缓存**：减少重复爬取
3. **清理历史数据**：定期清理过期数据
4. **监控系统负载**：避免系统过载

---

## 🚨 紧急情况处理

### 系统完全无响应
```bash
# 1. 强制停止所有进程
pkill -f "python.*quick_start"
pkill -f streamlit

# 2. 重启系统
sudo reboot  # Linux/Mac
# 或重启计算机

# 3. 检查磁盘空间
df -h

# 4. 从备份恢复数据
```

### 数据丢失
```bash
# 1. 停止所有服务防止进一步损坏
python quick_start.py  # 选择 stop

# 2. 检查备份文件
ls -la backups/

# 3. 从最近备份恢复
cp backups/marketing_YYYYMMDD.db data/marketing.db
```

### 网络问题
```bash
# 1. 检查网络连接
ping 8.8.8.8

# 2. 检查DNS
nslookup www.baidu.com

# 3. 重启网络服务
sudo systemctl restart networking  # Linux
# 或重启网络适配器（Windows）
```

---

**记住：大多数问题都可以通过运行健康检查工具来解决！**

```bash
python src/utils/health_checker.py
```