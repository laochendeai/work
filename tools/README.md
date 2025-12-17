# Tools 工具脚本

本目录存放**维护/运营**相关的命令行工具脚本（不属于 `main.py` 核心流程，但用于数据修复、评估与配置管理）。

## 联系人/数据质量

- 回填详情正文：`python tools/backfill_detail_content.py --limit 2000 --skip-title-filter`
- 重抽取并覆写 contacts：`python tools/reextract_contacts.py --mark-processed --no-require-email`
- 抽样评估抽取质量：`python tools/evaluate_extraction_quality.py --limit 200 --random --out data/exports/contacts/quality_eval.json`

## 数据源/配置管理

- 数据源管理（启用/禁用/删除/统计）：`python tools/manage_sources.py --help`
- 禁用自动发现（防止数据源无限增长）：`python tools/disable_auto_discovery.py`
- 清理明显无效的数据源：`python tools/clean_invalid_sources.py`
- 优化 `auto_sources.yaml`（去重/过滤详情页）：`python tools/optimize_auto_sources.py`
- 行业关键词全网发现（不限制域名，默认 dry-run）：`python tools/discover_industry_sources.py`（写入用 `--apply`，启用新源用 `--enable-new`）

## 归档脚本

- 不再在仓库内保留一次性/实验脚本；需要临时脚本请放到 `tools/scratch/`（建议加入 `.gitignore`）。
