# UI/Web 开发工作区

## 专注内容

本工作区专注于 Web UI 相关开发：

### 核心 UI 代码
- `scripts/web_dashboard.py` - Streamlit 主界面
- 页面组件和布局
- 用户交互逻辑

### UI 扩展方向
- 数据可视化组件
- 实时监控 Dashboard
- 数据源管理界面
- 爬虫任务监控界面
- 邮件发送历史界面

### 依赖库
- **Streamlit**: Web 框架
- **Pandas**: 数据处理
- **Plotly**: 图表可视化

## 启动 Web UI

```bash
# 方式1: 使用主程序
python main.py --web

# 方式2: 直接启动 Streamlit
streamlit run scripts/web_dashboard.py
```

## UI 相关文件结构

```
scripts/
├── web_dashboard.py          # 主 Dashboard (当前)
├── web_pages/                # 页面组件 (计划)
│   ├── overview.py          # 系统概览页
│   ├── scraping.py          # 数据爬取页
│   ├── contacts.py          # 联系人管理页
│   ├── email.py             # 邮件营销页
│   └── settings.py          # 系统设置页
└── web_components/          # 可复用组件 (计划)
    ├── charts.py            # 图表组件
    ├── tables.py            # 表格组件
    └── metrics.py           # 指标卡片
```

## 开发任务示例

### 添加新页面
```python
# 在 scripts/web_dashboard.py 中添加选项
page = st.sidebar.selectbox(
    "选择页面",
    [
        "系统概览",
        "数据爬取",
        "联系人管理",
        "邮件营销",
        "系统设置",
        "新功能页面",  # 新增
    ],
)
```

### 添加数据可视化
```python
import plotly.express as px

fig = px.scatter(df, x="date", y="count", title="数据趋势")
st.plotly_chart(fig)
```

## 与其他工作区的关系

| 工作区 | 依赖关系 | 说明 |
|--------|----------|------|
| work-scraper | → | UI 展示爬虫状态和结果 |
| work-tools | → | UI 提供工具的可视化界面 |
| work-tests | ← | 测试 UI 组件和交互 |

## 当前待办

- [ ] 添加实时爬虫进度监控
- [ ] 创建数据源管理界面
- [ ] 优化移动端显示
- [ ] 添加数据导出功能
- [ ] 创建任务调度界面
