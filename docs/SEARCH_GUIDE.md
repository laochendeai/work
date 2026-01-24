# 公共资源交易网搜索功能说明

## ⚠️ 重要提示

中国公共资源交易网的搜索平台具有**反爬保护机制**，直接模拟页面操作可能会被限制访问。

### 反爬机制
- ✅ 访问频率限制（频繁访问会被封禁）
- ✅ IP地址追踪
- ✅ 可能触发验证码

---

## ✅ 推荐方案

### 方案1：直接爬取分类列表页 + 关键词过滤

这是**最简单、最稳定**的方法：

```python
from scraper.fetcher import PlaywrightFetcher
from bs4 import BeautifulSoup

# 1. 创建爬虫
fetcher = PlaywrightFetcher()
fetcher.start()

# 2. 爬取中央公告列表页
url = "https://www.ccgp.gov.cn/cggg/zygg/index.htm"
html = fetcher.get_page(url)

# 3. 解析列表页
soup = BeautifulSoup(html, 'lxml')
links = soup.find_all('a')

# 4. 过滤包含"智能"的公告
keyword = "智能"
results = []

for link in links:
    title = link.get_text(strip=True)
    href = link.get('href', '')

    # 只保留包含关键词的公告
    if keyword in title and 'htm' in href:
        results.append({
            'title': title,
            'url': f"https://www.ccgp.gov.cn{href}"
        })

print(f"找到 {len(results)} 条包含'{keyword}'的公告")

# 5. 逐个访问详情页
from scraper.ccgp_parser import CCGPAnnouncementParser
parser = CCGPAnnouncementParser()

for result in results[:10]:  # 测试前10条
    detail_html = fetcher.get_page(result['url'])
    parsed = parser.parse(detail_html, result['url'])
    formatted = parser.format_for_storage(parsed)

    print(f"项目: {formatted['project_name']}")
    print(f"中标人: {formatted['supplier']}")
    print(f"金额: {formatted['bid_amount']}")
    print("-" * 50)

fetcher.stop()
```

### 方案2：爬取多个分类页面

```python
categories = {
    '中央公告': 'https://www.ccgp.gov.cn/cggg/zygg/index.htm',
    '货物类': 'https://www.ccgp.gov.cn/cggg/hwggg/index.htm',
    '工程类': 'https://www.ccgp.gov.cn/cggg/gcgg/index.htm',
    '服务类': 'https://www.ccgp.gov.cn/cggg/fwgpg/index.htm',
}

keyword = "智能"
all_results = []

for category_name, url in categories.items():
    print(f"正在爬取: {category_name}")
    # 爬取并过滤...
```

---

## 📊 可用的分类列表页

| 分类 | URL | 说明 |
|------|-----|------|
| 中央公告 | /cggg/zygg/index.htm | 国务院部委公告 |
| 货物类 | /cggg/hwggg/index.htm | 货物采购公告 |
| 工程类 | /cggg/gcgg/index.htm | 工程采购公告 |
| 服务类 | /cggg/fwgpg/index.htm | 服务采购公告 |
| 中标公告 | /cggg/zybg/index.htm | 中标结果公告 |
| 成交公告 | /cggg/cjgg/index.htm | 成交结果公告 |

---

## 🎯 实际使用建议

### 策略1：按日期爬取 + 过滤

```python
# 爬取今日公告后，在代码中过滤
from datetime import datetime, timedelta

today = datetime.now().strftime('%Y年%m月%d日')

# 解析后过滤
filtered_results = [
    r for r in all_results
    if today in r.get('publish_date', '')
    and '智能' in r.get('title', '')
]
```

### 策略2：分时爬取

```python
import time

categories = ['zygg', 'gczb', 'zybg']
for cat in categories:
    # 爬取一个分类
    scrape_category(cat)

    # 等待5-10分钟再爬下一个
    time.sleep(300)
```

### 策略3：使用代理IP

如果需要大量爬取，可以使用代理IP池：
```python
# 在Playwright中配置代理
context = browser.new_context(
    proxy={
        "server": "http://proxy.example.com:8080",
        "username": "user",
        "password": "pass"
    }
)
```

---

## 💡 最佳实践

1. **降低请求频率** - 每次请求间隔3-5秒
2. **分时段爬取** - 避开高峰时段
3. **使用列表页** - 比搜索平台更稳定
4. **本地过滤** - 爬取后在代码中按条件筛选
5. **遵守规则** - 仅用于合法的数据采集需求

---

## 🔧 完整示例

项目中的 `test_search.py` 展示了完整的搜索流程，但由于反爬限制，建议：

1. 先爬取列表页
2. 在内存中过滤关键词
3. 逐个访问详情页
4. 存储到数据库

这样可以避免触发搜索平台的反爬机制，同时实现相同的功能。
