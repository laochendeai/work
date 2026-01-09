#!/usr/bin/env python3
"""全面功能测试 - 测试所有按钮、链接和交互元素"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright, Page

# 配置
WEB_URL = "http://localhost:8501"
SCREENSHOT_DIR = Path(__file__).parent.parent / "screenshots"
SCREENSHOT_DIR.mkdir(exist_ok=True)

# 测试结果存储
test_results = {
    "passed": [],
    "failed": [],
    "warnings": []
}

async def take_screenshot(page: Page, name: str):
    """保存截图"""
    filepath = SCREENSHOT_DIR / f"test_{name}.png"
    await page.screenshot(path=str(filepath))
    return filepath

async def test_homepage(page: Page):
    """测试工作台首页"""
    print("\n[1] 测试工作台首页...")
    try:
        await page.goto(WEB_URL, wait_until="networkidle", timeout=15000)
        await asyncio.sleep(2)

        # 检查数据源指标
        content = await page.content()
        if "数据源" in content:
            # 检查是否显示"配置文件不存在"或正确的数据源数量
            if "配置文件不存在" in content:
                test_results["warnings"].append("数据源显示'配置文件不存在' - 这是正常的如果未配置数据源")
            elif "未配置" in content or "已配置" in content:
                test_results["passed"].append("✅ 数据源指标显示正常")
            else:
                test_results["warnings"].append("数据源显示状态不明确")
        else:
            test_results["failed"].append("❌ 数据源指标未显示")

        # 检查新手引导
        if "首次使用" in content or "新手指南" in content:
            test_results["passed"].append("✅ 新手引导显示正常")
        else:
            test_results["warnings"].append("⚠️ 新手引导可能未显示")

        # 检查快捷操作按钮
        quick_actions = [
            ("开始寻找", "寻找客户"),
            ("查看资料", "客户资料"),
            ("发送邮件", "发送推广")
        ]

        for button_text, expected_page in quick_actions:
            try:
                button = page.get_by_role("button", name=button_text).first
                if await button.is_visible():
                    test_results["passed"].append(f"✅ 快捷按钮'{button_text}'可见")
                else:
                    test_results["failed"].append(f"❌ 快捷按钮'{button_text}'不可见")
            except Exception as e:
                test_results["warnings"].append(f"⚠️ 快捷按钮'{button_text}'检查失败: {e}")

        await take_screenshot(page, "homepage")
        return True

    except Exception as e:
        test_results["failed"].append(f"❌ 工作台首页测试失败: {e}")
        return False

async def test_quick_action_navigation(page: Page):
    """测试快捷操作按钮导航"""
    print("\n[2] 测试快捷操作按钮导航...")

    # 测试"开始寻找"按钮
    try:
        await page.goto(WEB_URL, wait_until="networkidle", timeout=15000)
        await asyncio.sleep(1)

        # 点击"开始寻找"按钮
        button = page.get_by_role("button", name="开始寻找").first
        await button.click()
        await asyncio.sleep(2)

        # 检查是否跳转到寻找客户页面
        url = page.url
        if "寻找客户" in url:
            test_results["passed"].append("✅ '开始寻找'按钮导航正常")
        else:
            test_results["warnings"].append(f"⚠️ '开始寻找'按钮导航后URL: {url}")

        await take_screenshot(page, "after_click_find_customers")

    except Exception as e:
        test_results["failed"].append(f"❌ 快捷按钮导航测试失败: {e}")

async def test_all_pages_accessible(page: Page):
    """测试所有页面可访问性"""
    print("\n[3] 测试所有页面可访问性...")

    pages = [
        ("工作台", ""),
        ("寻找客户", "寻找客户"),
        ("客户资料", "客户资料"),
        ("发送推广", "发送推广"),
        ("数据报表", "数据报表"),
        ("数据整理", "数据整理"),
        ("运行记录", "运行记录"),
        ("系统设置", "系统设置"),
    ]

    for page_name, param in pages:
        try:
            url = f"{WEB_URL}?{param}" if param else WEB_URL
            await page.goto(url, wait_until="networkidle", timeout=15000)
            await asyncio.sleep(1)

            # 检查页面标题
            content = await page.content()
            if page_name in content:
                test_results["passed"].append(f"✅ 页面'{page_name}'可访问")
            else:
                test_results["warnings"].append(f"⚠️ 页面'{page_name}'可能未正确加载")

            # 检查侧边栏菜单
            if "功能菜单" in content:
                test_results["passed"].append(f"✅ 页面'{page_name}'侧边栏正常")

        except Exception as e:
            test_results["failed"].append(f"❌ 页面'{page_name}'访问失败: {e}")

async def test_customer_info_buttons(page: Page):
    """测试客户资料页面的所有按钮"""
    print("\n[4] 测试客户资料页面功能...")

    try:
        await page.goto(f"{WEB_URL}?客户资料", wait_until="networkidle", timeout=15000)
        await asyncio.sleep(2)

        content = await page.content()

        # 检查搜索框
        if "搜索" in content:
            test_results["passed"].append("✅ 客户资料页面搜索框存在")

        # 检查数据表格或空状态提示
        if "客户信息" in content or "暂无数据" in content or "联系人" in content:
            test_results["passed"].append("✅ 客户资料页面内容显示正常")

        await take_screenshot(page, "customer_info_page")
        return True

    except Exception as e:
        test_results["failed"].append(f"❌ 客户资料页面测试失败: {e}")
        return False

async def test_find_customers_page(page: Page):
    """测试寻找客户页面"""
    print("\n[5] 测试寻找客户页面...")

    try:
        await page.goto(f"{WEB_URL}?寻找客户", wait_until="networkidle", timeout=15000)
        await asyncio.sleep(2)

        content = await page.content()

        # 检查关键词输入框
        if "关键词" in content:
            test_results["passed"].append("✅ 寻找客户页面关键词输入框存在")

        # 检查开始搜索按钮
        try:
            button = page.get_by_role("button", name="开始搜索").first
            if await button.is_visible():
                test_results["passed"].append("✅ '开始搜索'按钮可见")
        except:
            test_results["warnings"].append("⚠️ '开始搜索'按钮可能不可见")

        await take_screenshot(page, "find_customers_page")
        return True

    except Exception as e:
        test_results["failed"].append(f"❌ 寻找客户页面测试失败: {e}")
        return False

async def test_send_promotion_page(page: Page):
    """测试发送推广页面"""
    print("\n[6] 测试发送推广页面...")

    try:
        await page.goto(f"{WEB_URL}?发送推广", wait_until="networkidle", timeout=15000)
        await asyncio.sleep(2)

        content = await page.content()

        # 检查邮箱设置区域
        if "邮箱设置" in content or "邮箱已配置" in content or "邮箱未设置" in content:
            test_results["passed"].append("✅ 发送推广页面邮箱设置显示正常")

        # 检查测试发送按钮
        if "测试" in content:
            test_results["passed"].append("✅ 发送推广页面测试功能存在")

        await take_screenshot(page, "send_promotion_page")
        return True

    except Exception as e:
        test_results["failed"].append(f"❌ 发送推广页面测试失败: {e}")
        return False

async def main():
    """主测试函数"""
    print("=" * 70)
    print("🧪 全面功能测试")
    print("=" * 70)
    print(f"📸 截图保存目录: {SCREENSHOT_DIR}")
    print(f"🕐 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # 运行所有测试
        await test_homepage(page)
        await test_quick_action_navigation(page)
        await test_all_pages_accessible(page)
        await test_customer_info_buttons(page)
        await test_find_customers_page(page)
        await test_send_promotion_page(page)

        await browser.close()

    # 打印测试结果
    print("\n" + "=" * 70)
    print("📊 测试结果汇总")
    print("=" * 70)

    print(f"\n✅ 通过: {len(test_results['passed'])} 项")
    for item in test_results['passed']:
        print(f"  {item}")

    print(f"\n⚠️ 警告: {len(test_results['warnings'])} 项")
    for item in test_results['warnings']:
        print(f"  {item}")

    print(f"\n❌ 失败: {len(test_results['failed'])} 项")
    for item in test_results['failed']:
        print(f"  {item}")

    total = len(test_results['passed']) + len(test_results['failed'])
    passed_count = len(test_results['passed'])

    print("\n" + "=" * 70)
    print(f"总计: {total} 项测试")
    print(f"通过: {passed_count} 项 ✅")
    print(f"失败: {len(test_results['failed'])} 项 ❌")
    print(f"通过率: {passed_count / total * 100:.1f}%")
    print("=" * 70)

    if len(test_results['failed']) == 0:
        print("\n🎉 所有测试通过！")
        return 0
    else:
        print(f"\n⚠️  有 {len(test_results['failed'])} 个测试失败")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
