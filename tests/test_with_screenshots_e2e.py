#!/usr/bin/env python3
"""E2E 测试 - 所有功能页面带截图验证"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright, Page

# 配置
WEB_URL = "http://localhost:8501"
SCREENSHOT_DIR = Path(__file__).parent.parent / "screenshots"
SCREENSHOT_DIR.mkdir(exist_ok=True)

# 页面配置
PAGES = [
    {"name": "系统概览", "icon": "📊", "url": ""},
    {"name": "数据爬取", "icon": "🕷️", "url": "数据爬取"},
    {"name": "联系人管理", "icon": "👥", "url": "联系人管理"},
    {"name": "邮件营销", "icon": "📧", "url": "邮件营销"},
    {"name": "数据导出", "icon": "📥", "url": "数据导出"},
    {"name": "数据库管理", "icon": "🗄️", "url": "数据库管理"},
    {"name": "系统日志", "icon": "📋", "url": "系统日志"},
    {"name": "系统设置", "icon": "⚙️", "url": "系统设置"},
]


async def check_sidebar(page: Page) -> dict:
    """检查侧边栏状态"""
    try:
        sidebar = await page.query_selector('[data-testid="stSidebar"]')
        if not sidebar:
            return {"width": 0, "visible": False, "expanded": False}

        box = await sidebar.bounding_box()
        width = int(box["width"]) if box else 0

        # 检查侧边栏是否展开（宽度 > 200px）
        expanded = width > 200

        return {"width": width, "visible": True, "expanded": expanded}
    except Exception as e:
        return {"width": 0, "visible": False, "expanded": False, "error": str(e)}


async def check_radio_menu(page: Page) -> dict:
    """检查 Radio 菜单状态"""
    try:
        # 查找 radio 组件
        radio = await page.query_selector('input[type="radio"]')
        radio_count = await page.locator('input[type="radio"]').count()

        # 检查所有 8 个选项是否可见
        all_options_visible = False
        if radio_count >= 8:
            all_options_visible = True

        return {
            "has_radio": radio is not None,
            "radio_count": radio_count,
            "all_options_visible": all_options_visible,
        }
    except Exception as e:
        return {"has_radio": False, "radio_count": 0, "error": str(e)}


async def capture_screenshot(page: Page, page_name: str, timestamp: str) -> str:
    """捕获页面截图"""
    filename = f"{timestamp}_{page_name.replace(' ', '_')}.png"
    filepath = SCREENSHOT_DIR / filename

    # 等待页面稳定
    await asyncio.sleep(0.5)

    # 截取整个页面
    await page.screenshot(path=str(filepath), full_page=False)

    return str(filepath)


async def test_page_with_screenshot(
    browser, page_info: dict, timestamp: str, index: int
) -> dict:
    """测试单个页面并截图"""
    page_name = page_info["name"]
    url_param = page_info["url"]

    result = {
        "page": page_name,
        "icon": page_info["icon"],
        "index": index,
        "success": False,
        "screenshot": "",
        "sidebar": {},
        "radio_menu": {},
        "error": None,
    }

    page = await browser.new_page()

    try:
        # 构建目标 URL
        target_url = f"{WEB_URL}"
        if url_param:
            # Streamlit 使用查询参数切换页面
            target_url = f"{WEB_URL}?{url_param}"

        print(f"  访问: {page_name} ({target_url})")

        # 导航到页面
        await page.goto(target_url, wait_until="networkidle", timeout=15000)
        await asyncio.sleep(1)  # 等待 Streamlit 渲染

        # 检查侧边栏
        result["sidebar"] = await check_sidebar(page)

        # 检查 Radio 菜单
        result["radio_menu"] = await check_radio_menu(page)

        # 截图
        screenshot_path = await capture_screenshot(page, page_name, timestamp)
        result["screenshot"] = screenshot_path

        # 检查页面内容
        content = await page.content()
        has_content = len(content) > 1000

        # 检查页面标题
        has_title = False
        title_selectors = [
            f"text={page_name}",
            f"h1:has-text('{page_name}')",
            f"h2:has-text('{page_name}')",
        ]
        for selector in title_selectors:
            try:
                if await page.locator(selector).count() > 0:
                    has_title = True
                    break
            except:
                pass

        # 判断测试是否通过
        result["success"] = (
            has_content
            and result["sidebar"].get("expanded", False)
            and result["radio_menu"].get("all_options_visible", False)
        )

        if not result["success"]:
            result["error"] = "验证失败"

    except Exception as e:
        result["error"] = str(e)
        result["success"] = False

    finally:
        await page.close()

    return result


async def run_all_tests():
    """运行所有页面的测试"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print("=" * 70)
    print("🧪 E2E 测试 - 所有功能页面（带截图）")
    print("=" * 70)
    print(f"📸 截图保存目录: {SCREENSHOT_DIR}")
    print(f"🕐 测试时间: {timestamp}")
    print("=" * 70)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        results = []

        for idx, page_info in enumerate(PAGES, 1):
            print(f"\n[{idx}/{len(PAGES)}] 测试: {page_info['icon']} {page_info['name']}")
            result = await test_page_with_screenshot(browser, page_info, timestamp, idx)
            results.append(result)

            # 显示结果
            status = "✅ 通过" if result["success"] else "❌ 失败"
            print(f"    状态: {status}")
            print(f"    侧边栏: {result['sidebar'].get('width', 0)}px ", end="")
            print(f"({'展开' if result['sidebar'].get('expanded') else '折叠'})")
            print(f"    Radio菜单: {result['radio_menu'].get('radio_count', 0)} 个选项 ", end="")
            print(f"({'全部可见' if result['radio_menu'].get('all_options_visible') else '不可见'})")
            print(f"    截图: {Path(result['screenshot']).name}")

        await browser.close()

    return results


def print_summary(results: list):
    """打印测试摘要"""
    print("\n" + "=" * 70)
    print("📊 测试结果汇总")
    print("=" * 70)

    # 统计
    total = len(results)
    passed = sum(1 for r in results if r["success"])
    failed = total - passed

    print(f"\n总计: {total} 个页面")
    print(f"通过: {passed} 个 ✅")
    print(f"失败: {failed} 个 ❌")
    print(f"通过率: {passed / total * 100:.1f}%")

    # 侧边栏状态
    sidebar_widths = [r["sidebar"].get("width", 0) for r in results if r["sidebar"]]
    avg_width = sum(sidebar_widths) / len(sidebar_widths) if sidebar_widths else 0
    all_expanded = all(r["sidebar"].get("expanded", False) for r in results)

    print(f"\n侧边栏状态:")
    print(f"  平均宽度: {avg_width:.0f}px")
    print(f"  全部展开: {'是 ✅' if all_expanded else '否 ❌'}")

    # Radio 菜单状态
    radio_counts = [r["radio_menu"].get("radio_count", 0) for r in results]
    all_visible = all(r["radio_menu"].get("all_options_visible", False) for r in results)

    print(f"\nRadio 菜单状态:")
    print(f"  平均选项数: {sum(radio_counts) / len(radio_counts):.0f}")
    print(f"  全部可见: {'是 ✅' if all_visible else '否 ❌'}")

    # 失败详情
    if failed > 0:
        print(f"\n❌ 失败的页面:")
        for r in results:
            if not r["success"]:
                print(f"  - {r['icon']} {r['page']}: {r.get('error', '未知错误')}")

    print("=" * 70)

    # 最终结果
    if passed == total:
        print("\n🎉 所有测试通过！")
        print("✅ 侧边栏在所有页面保持展开")
        print("✅ Radio 菜单所有选项可见")
        print("✅ 所有功能页面可访问")
        print(f"✅ 截图已保存到: {SCREENSHOT_DIR}")
        return True
    else:
        print(f"\n⚠️  有 {failed} 个测试失败")
        return False


def generate_markdown_report(results: list, timestamp: str):
    """生成 Markdown 格式的测试报告"""
    report_path = SCREENSHOT_DIR / f"test_report_{timestamp}.md"

    total = len(results)
    passed = sum(1 for r in results if r["success"])
    failed = total - passed

    sidebar_widths = [r["sidebar"].get("width", 0) for r in results if r["sidebar"]]
    avg_width = sum(sidebar_widths) / len(sidebar_widths) if sidebar_widths else 0

    md_content = f"""# Web Dashboard E2E 测试报告

**测试时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**工作区**: work-ui (feature/web-ui-v3)
**测试类型**: 完整功能测试 + 截图验证

---

## 测试结果概览

| 指标 | 结果 |
|------|------|
| 总页面数 | {total} |
| 通过 | {passed} ✅ |
| 失败 | {failed} {'❌' if failed > 0 else ''} |
| 通过率 | {passed / total * 100:.1f}% |
| 侧边栏平均宽度 | {avg_width:.0f}px |
| 侧边栏状态 | {'全部展开 ✅' if all(r['sidebar'].get('expanded') for r in results) else '部分折叠 ❌'} |
| Radio菜单状态 | {'全部可见 ✅' if all(r['radio_menu'].get('all_options_visible') for r in results) else '部分不可见 ❌'} |

---

## 功能页面详情

"""

    for r in results:
        status_icon = "✅" if r["success"] else "❌"
        sidebar_status = "展开" if r["sidebar"].get("expanded") else "折叠"
        radio_status = "可见" if r["radio_menu"].get("all_options_visible") else "不可见"

        screenshot_filename = Path(r["screenshot"]).name
        screenshot_relative = f"./{screenshot_filename}"

        md_content += f"""### {r['index']}. {status_icon} {r['icon']} {r['page']}

| 项目 | 结果 |
|------|------|
| 状态 | {'通过 ✅' if r['success'] else '失败 ❌'} |
| 侧边栏宽度 | {r['sidebar'].get('width', 0)}px |
| 侧边栏状态 | {sidebar_status} |
| Radio选项数 | {r['radio_menu'].get('radio_count', 0)} |
| 菜单可见性 | {radio_status} |
| 截图 | [{screenshot_filename}]({screenshot_relative}) |

![{r['page']}]({screenshot_relative})

---

"""

    md_content += f"""
## 截图说明

所有截图保存在: `{SCREENSHOT_DIR}`

截图命名规则: `{timestamp}_页面名称.png`

---

## 技术实现

### Radio 菜单

```python
page = st.radio(
    "📋 功能菜单",
    [
        "📊 系统概览",
        "🕷️ 数据爬取",
        "👥 联系人管理",
        "📧 邮件营销",
        "📥 数据导出",
        "🗄️ 数据库管理",
        "📋 系统日志",
        "⚙️ 系统设置",
    ],
    index=0,
    horizontal=False,
    label_visibility="visible"
)
```

**优势**:
- 所有 8 个选项默认可见
- 无需点击即可看到所有功能
- 更好的用户体验

---

**报告生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**测试脚本**: tests/test_with_screenshots_e2e.py
"""

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    print(f"\n📄 测试报告已生成: {report_path}")
    return report_path


async def main():
    """主函数"""
    # 运行测试
    results = await run_all_tests()

    # 打印摘要
    success = print_summary(results)

    # 生成报告
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = generate_markdown_report(results, timestamp)

    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
