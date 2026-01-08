# Git Worktree 项目优化指南

## 项目工作区布局

本项目已使用 Git Worktree 进行优化：

```
/home/dministrator/work           # 主仓库 (master)
/home/dministrator/work-scraper   # 爬虫开发
/home/dministrator/work-tools     # 工具开发  
/home/dministrator/work-tests     # 测试开发
/home/dministrator/work-experiment # 实验功能
```

---

## 快速开始

### 查看所有工作区
```bash
./tools/setup_worktrees.sh list
```

### 切换工作区
```bash
cd ~/work-scraper   # 爬虫开发
cd ~/work-tools     # 工具开发
cd ~/work-tests     # 测试开发
cd ~/work-experiment # 实验功能
cd ~/work           # 主分支
```

---

## 各工作区职责

### work (主分支)
- 稳定的生产代码
- 运行和测试环境

### work-scraper (爬虫开发)
- 核心爬虫引擎
- HTTP 请求处理
- 数据提取逻辑

### work-tools (工具开发)
- 数据源验证工具
- 数据源发现工具
- 数据源管理工具

### work-tests (测试开发)
- 单元测试
- E2E 测试
- 测试数据

### work-experiment (实验功能)
- 新算法验证
- 重构实验
- 性能测试

---

## 工作流示例

### 开发新功能
```bash
cd ~/work-scraper
# 开发
# 测试
# 提交
git checkout master
git merge feature/scraper-v4
```

### 紧急修复
```bash
cd ~/work
./tools/setup_worktrees.sh hotfix bug-name
cd ../hotfix-bug-name
# 修复
git commit -am "fix: xxx"
git checkout master
git merge hotfix/bug-name
```

---

## 维护命令
```bash
./tools/setup_worktrees.sh clean    # 清理
./tools/setup_worktrees.sh list     # 查看
```

---

**更新**: 2025-12-30
