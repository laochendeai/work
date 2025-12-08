# 爬虫技术调研（2025Q1）

## 新技术概览
- **HTTP/2 + 现代连接池**: 通过 httpx/anyio 提供的多路复用、连接复用和可配置的限流策略，能够在一个 TCP 连接中同时请求多个页面，避免 requests 在高并发下频繁握手。
- **弹性重试与智能退避**: tenacity 提供指数级退避、抖动和同步/异步两套 API，可对瞬时 5xx、TLS 抖动、验证码页面等做快速重试，同时避免洪峰流量。
- **并发抓取协程化**: asyncio + httpx.AsyncClient 让我们为详情页、分页抓取提供轻量的批量任务，吞吐量提升 3~5 倍，且可通过信号量严格限制对目标站的并发数。
- **结构化指纹去重**: 结合数据库的 hash 表和网络层的 `ETag/Last-Modified` 缓存头，可以做到“见过内容不二次抓”；requests-cache/httpx-cache 也能做持久化缓存。
- **抗封锁的头部/代理治理**: 动态 UA 池（uasurfer/fake-useragent）+ 可选代理池，配合 referer、Sec-CH-UA 系列头部，让抓取请求更贴近真实浏览器轨迹。

## 与现有系统的差距
| 维度 | 当前实现 | 存在问题 | 可落地方案 |
| --- | --- | --- | --- |
| 网络栈 | requests + 同步串行 | 连接复用差、无法 HTTP/2、列表/详情完全串行 | 引入 httpx 客户端、异步批量抓取 |
| 重试策略 | try/except + 一次 sleep | 无指数退避，容易被当作重放攻击 | tenacity Retry + 退避策略 |
| 详情页抓取 | for 循环逐个请求 | 详情页总耗时长、失败不会回补 | asyncio.Semaphore 批量抓取 + 失败重试 |
| 头部治理 | 固定 UA/头部 | 一旦被封 UA 即全站失败 | 动态 UA 池、可注入自定义头部 |
| 监控 | logging + 摘要 | 缺少每个源的速率/错误统计 | 在抓取器中收集 metrics 供 UI 展示 |

## 落地计划
1. **实现 AdvancedFetcher**：封装 httpx.Client/AsyncClient、tenacity 重试、动态请求头、HTTP/2、连接数&并发限制。提供 `fetch`、`fetch_many` 两类接口。
2. **统一改造 UnifiedScraper**：把所有网络请求切换到 AdvancedFetcher，去掉零散的 requests.Session。
3. **批量详情抓取**：新增 `scrape_details_bulk`，主流程中一次性并发抓取详情页，失败自动回退到单个重试。
4. **配置化网络策略**：config/settings.json 新增 network 节点，控制最大并发/每源延迟/HTTP2 开关，后续可暴露到 UI。
5. **持续演进**（下一阶段）：挂载代理池、按站点自定义 cookie 注入、接入 requests-cache/httpx-cache 做 24h 缓存、把 HTML 解析升级为 selectolax。

## 社区案例洞察（2025-01调研）
- [yakhoruzhenko/auto-crawler](https://github.com/yakhoruzhenko/auto-crawler)（async + aiohttp + tenacity）：通过将页面分片分配给 worker 并记录“已抓 page id”，有效避免重复爬取，并利用 Tenacity 仅对 429/5xx 重试。
- [Kushagra1taneja/AmazonCrawler](https://github.com/Kushagra1taneja/AmazonCrawler)：在请求层轮换 UA 与代理，失败会进入多次 retry，强调 401/403 主要由 headers/proxy 不足导致。
- [0001001010/manga-scraper](https://github.com/0001001010/manga-scraper)：Scrapy 项目中通过缓存 + retry middleware + 状态报表准确监控 301/302/404 分布。

### 对本项目的启发
1. **状态可观测性**：如 manga-scraper，在日志/报表里统计各 HTTP 状态，可以快速定位 301/302 是否由于 http→https，或 401/403 触发。=> 为统一爬虫增加 `logs/source_health.json`。
2. **精准重试策略**：auto-crawler 只对少量可恢复状态重试，并尊重 `Retry-After`。=> AdvancedFetcher 改为自定义 `_should_retry`，避免对 401/404 的无效重试。
3. **抗封锁治理**：AmazonCrawler 的 UA/代理池思路用于我们 `network.user_agents` 配置，后续可扩展 `proxy` 字段。

该方案兼容现有数据库与业务逻辑，不影响 extractor/emailer。预计改造后同一批 20 条公告总抓取时长可从 ~90 秒缩短至 25~30 秒，并大幅降低短暂网络抖动造成的全局失败率。
