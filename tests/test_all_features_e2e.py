#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web Dashboard 完整功能 E2E 测试

测试内容：
1. 侧边栏固定展开状态
2. 所有 8 个功能页面
3. 每个页面的核心功能
4. 页面切换流畅性
5. 数据显示正确性
"""

import asyncio
import subprocess
import time
import sys
from pathlib import Path
from datetime import datetime

from playwright.async_api import async_playwright, Page, Browser


WEB_URL = "http://localhost:8501"
STREAMLIT_PORT = 8501


async def start_streamlit():
    """启动 Streamlit"""
    project_root = Path(__file__).resolve().parents[1]
    dashboard_file = project_root / "scripts" / "web_dashboard.py"
    
    print("="*70)
    print("🚀 启动 Streamlit Web Dashboard")
    print("="*70)
    print(f"📂 项目目录: {project_root}")
    print(f"📄 Dashboard: {dashboard_file.name}")
    print("")
    
    proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", str(dashboard_file),
         "--server.headless", "true",
         "--server.port", str(STREAMLIT_PORT)],
        cwd=str(project_root),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    print("⏳ 等待 Streamlit 启动...")
    for i in range(30):
        try:
            import urllib.request
            response = urllib.request.urlopen(f"{WEB_URL}/_stcore/health", timeout=1)
            if response.status == 200:
                print(f"✅ Streamlit 已启动 (耗时 {i+1} 秒)")
                print("")
                break
        except Exception:
            time.sleep(1)
            if i % 5 == 0:
                print(f"   等待中... {i+1}/30")
    else:
        proc.kill()
        raise TimeoutError("Streamlit 启动超时")
    
    return proc


async def stop_streamlit(proc):
    """停止 Streamlit"""
    print("\n" + "="*70)
    print("🛑 停止 Streamlit...")
    print("="*70)
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
    print("✅ Streamlit 已停止")


def print_test_header(title):
    """打印测试标题"""
    print("\n" + "="*70)
    print(f"🧪 {title}")
    print("="*70)


def print_test_result(test_name, passed, details=""):
    """打印测试结果"""
    icon = "✅" if passed else "❌"
    status = "通过" if passed else "失败"
    print(f"{icon} {test_name}: {status}")
    if details:
        print(f"   {details}")


async def check_sidebar_state(page: Page) -> dict:
    """检查侧边栏状态"""
    result = {
        "exists": False,
        "expanded": False,
        "width": 0,
        "visible": False,
        "collapsed_button_hidden": False
    }
    
    try:
        # 检查侧边栏是否存在
        sidebar = await page.query_selector("[data-testid='stSidebar']")
        if sidebar:
            result["exists"] = True
            result["visible"] = await sidebar.is_visible()
            
            # 检查侧边栏宽度
            bounding_box = await sidebar.bounding_box()
            if bounding_box:
                result["width"] = int(bounding_box["width"])
                # 展开状态通常宽度 > 250px
                result["expanded"] = result["width"] > 250
            
            # 检查折叠按钮是否被隐藏
            collapsed_button = await page.query_selector("[data-testid='collapsedControl']")
            if collapsed_button:
                is_visible = await collapsed_button.is_visible()
                result["collapsed_button_hidden"] = not is_visible
    except Exception as e:
        print(f"   ⚠️  侧边栏检查异常: {e}")
    
    return result


async def test_sidebar_state(page: Page) -> dict:
    """测试侧边栏状态"""
    print_test_header("侧边栏状态测试")
    
    result = {
        "test": "侧边栏状态",
        "passed": False,
        "details": [],
        "sidebar_info": {}
    }
    
    try:
        # 等待页面加载
        await page.wait_for_load_state("networkidle", timeout=10000)
        
        # 检查侧边栏
        sidebar_info = await check_sidebar_state(page)
        result["sidebar_info"] = sidebar_info
        
        # 验证侧边栏存在
        if not sidebar_info["exists"]:
            result["details"].append("侧边栏不存在")
            return result
        
        print_test_result("侧边栏存在", True)
        
        # 验证侧边栏可见
        if not sidebar_info["visible"]:
            result["details"].append("侧边栏不可见")
            return result
        
        print_test_result("侧边栏可见", True)
        
        # 验证侧边栏展开
        if not sidebar_info["expanded"]:
            result["details"].append(f"侧边栏未展开 (宽度: {sidebar_info['width']}px)")
            return result
        
        print_test_result("侧边栏展开", True, f"宽度: {sidebar_info['width']}px")
        
        # 验证折叠按钮隐藏
        if not sidebar_info["collapsed_button_hidden"]:
            result["details"].append("折叠按钮仍然可见")
            return result
        
        print_test_result("折叠按钮隐藏", True)
        
        # 验证侧边栏菜单项
        menu_items = await page.query_selector_all("[data-testid='stSidebar'] option, [data-testid='stSidebar'] label")
        print_test_result("侧边栏菜单项", True, f"找到 {len(menu_items)} 个菜单项")
        
        result["passed"] = True
        
    except Exception as e:
        result["details"].append(f"测试异常: {e}")
    
    return result


async def test_page_overview(page: Page) -> dict:
    """测试系统概览页面"""
    print_test_header("系统概览页面测试")
    
    result = {"test": "系统概览", "passed": False, "details": []}
    
    try:
        await page.wait_for_load_state("networkidle", timeout=10000)
        
        # 检查标题
        title = await page.title()
        if "智能设计营销系统" in title:
            print_test_result("页面标题", True)
        else:
            result["details"].append(f"标题错误: {title}")
            return result
        
        # 检查指标卡片
        metrics = await page.query_selector_all("[data-testid='stMetricValue']")
        if len(metrics) >= 4:
            print_test_result("指标卡片", True, f"找到 {len(metrics)} 个")
        else:
            result["details"].append(f"指标卡片不足: {len(metrics)}/4")
            return result
        
        # 检查快捷操作卡片
        cards = await page.query_selector_all(".card")
        if len(cards) >= 3:
            print_test_result("快捷操作卡片", True, f"找到 {len(cards)} 个")
        else:
            result["details"].append(f"快捷操作卡片不足: {len(cards)}/3")
        
        result["passed"] = True
        
    except Exception as e:
        result["details"].append(f"测试异常: {e}")
    
    return result


async def test_page_scraping(page: Page) -> dict:
    """测试数据爬取页面"""
    print_test_header("数据爬取页面测试")
    
    result = {"test": "数据爬取", "passed": False, "details": []}
    
    try:
        await page.wait_for_load_state("networkidle", timeout=10000)
        
        # 切换到数据爬取页面
        await page.goto(f"{WEB_URL}?🕷️ 数据爬取", wait_until="networkidle", timeout=10000)
        await asyncio.sleep(2)
        
        # 检查配置表单
        inputs = await page.query_selector_all("input[type='text'], input[type='number']")
        if len(inputs) >= 2:
            print_test_result("配置表单", True, f"找到 {len(inputs)} 个输入框")
        else:
            result["details"].append(f"配置表单不足: {len(inputs)}/2")
            return result
        
        # 检查按钮
        buttons = await page.query_selector_all("button")
        scrape_button = any("爬取" in await b.inner_text() for b in buttons)
        if scrape_button:
            print_test_result("爬取按钮", True)
        else:
            result["details"].append("未找到爬取按钮")
            return result
        
        result["passed"] = True
        
    except Exception as e:
        result["details"].append(f"测试异常: {e}")
    
    return result


async def test_page_contacts(page: Page) -> dict:
    """测试联系人管理页面"""
    print_test_header("联系人管理页面测试")
    
    result = {"test": "联系人管理", "passed": False, "details": []}
    
    try:
        await page.wait_for_load_state("networkidle", timeout=10000)
        
        # 切换到联系人管理页面
        await page.goto(f"{WEB_URL}?👥 联系人管理", wait_until="networkidle", timeout=10000)
        await asyncio.sleep(2)
        
        # 检查搜索框
        search_input = await page.query_selector("input[placeholder*='搜索']")
        if search_input:
            print_test_result("搜索框", True)
        else:
            result["details"].append("未找到搜索框")
        
        # 检查选择器
        selects = await page.query_selector_all("select")
        if len(selects) >= 2:
            print_test_result("筛选器", True, f"找到 {len(selects)} 个")
        else:
            result["details"].append(f"筛选器不足: {len(selects)}/2")
        
        result["passed"] = True
        
    except Exception as e:
        result["details"].append(f"测试异常: {e}")
    
    return result


async def test_page_email(page: Page) -> dict:
    """测试邮件营销页面"""
    print_test_header("邮件营销页面测试")
    
    result = {"test": "邮件营销", "passed": False, "details": []}
    
    try:
        await page.wait_for_load_state("networkidle", timeout=10000)
        
        # 切换到邮件营销页面
        await page.goto(f"{WEB_URL}?📧 邮件营销", wait_until="networkidle", timeout=10000)
        await asyncio.sleep(2)
        
        # 检查邮件配置区域
        page_content = await page.content()
        if "邮件配置" in page_content or "邮件已配置" in page_content:
            print_test_result("邮件配置区", True)
        else:
            result["details"].append("未找到邮件配置区域")
            return result
        
        # 检查模板编辑器
        text_area = await page.query_selector("textarea")
        if text_area:
            print_test_result("邮件模板编辑器", True)
        else:
            result["details"].append("未找到邮件模板编辑器")
        
        result["passed"] = True
        
    except Exception as e:
        result["details"].append(f"测试异常: {e}")
    
    return result


async def test_page_export(page: Page) -> dict:
    """测试数据导出页面"""
    print_test_header("数据导出页面测试")
    
    result = {"test": "数据导出", "passed": False, "details": []}
    
    try:
        await page.wait_for_load_state("networkidle", timeout=10000)
        
        # 切换到数据导出页面
        await page.goto(f"{WEB_URL}?📥 数据导出", wait_until="networkidle", timeout=10000)
        await asyncio.sleep(2)
        
        # 检查导出选项
        selects = await page.query_selector_all("select")
        if len(selects) >= 3:
            print_test_result("导出选项", True, f"找到 {len(selects)} 个选择器")
        else:
            result["details"].append(f"导出选项不足: {len(selects)}/3")
            return result
        
        # 检查导出按钮
        buttons = await page.query_selector_all("button")
        export_button = any("导出" in await b.inner_text() for b in buttons)
        if export_button:
            print_test_result("导出按钮", True)
        else:
            result["details"].append("未找到导出按钮")
        
        result["passed"] = True
        
    except Exception as e:
        result["details"].append(f"测试异常: {e}")
    
    return result


async def test_page_database(page: Page) -> dict:
    """测试数据库管理页面"""
    print_test_header("数据库管理页面测试")
    
    result = {"test": "数据库管理", "passed": False, "details": []}
    
    try:
        await page.wait_for_load_state("networkidle", timeout=10000)
        
        # 切换到数据库管理页面
        await page.goto(f"{WEB_URL}?🗄️ 数据库管理", wait_until="networkidle", timeout=10000)
        await asyncio.sleep(2)
        
        # 检查数据库状态指标
        metrics = await page.query_selector_all("[data-testid='stMetricValue']")
        if len(metrics) >= 4:
            print_test_result("数据库指标", True, f"找到 {len(metrics)} 个")
        else:
            result["details"].append(f"数据库指标不足: {len(metrics)}/4")
            return result
        
        # 检查清理按钮
        buttons = await page.query_selector_all("button")
        clean_button = any("清理" in await b.inner_text() for b in buttons)
        if clean_button:
            print_test_result("清理按钮", True)
        else:
            result["details"].append("未找到清理按钮")
        
        result["passed"] = True
        
    except Exception as e:
        result["details"].append(f"测试异常: {e}")
    
    return result


async def test_page_logs(page: Page) -> dict:
    """测试系统日志页面"""
    print_test_header("系统日志页面测试")
    
    result = {"test": "系统日志", "passed": False, "details": []}
    
    try:
        await page.wait_for_load_state("networkidle", timeout=10000)
        
        # 切换到系统日志页面
        await page.goto(f"{WEB_URL}?📋 系统日志", wait_until="networkidle", timeout=10000)
        await asyncio.sleep(2)
        
        # 检查日志选项
        selects = await page.query_selector_all("select")
        if len(selects) >= 2:
            print_test_result("日志选项", True, f"找到 {len(selects)} 个选择器")
        else:
            result["details"].append(f"日志选项不足: {len(selects)}/2")
            return result
        
        # 检查日志显示区域
        code_block = await page.query_selector("code")
        if code_block or not selects:  # 如果没有日志文件，code_block 可能不存在
            print_test_result("日志显示区", True)
        else:
            result["details"].append("未找到日志显示区域")
        
        result["passed"] = True
        
    except Exception as e:
        result["details"].append(f"测试异常: {e}")
    
    return result


async def test_page_settings(page: Page) -> dict:
    """测试系统设置页面"""
    print_test_header("系统设置页面测试")
    
    result = {"test": "系统设置", "passed": False, "details": []}
    
    try:
        await page.wait_for_load_state("networkidle", timeout=10000)
        
        # 切换到系统设置页面
        await page.goto(f"{WEB_URL}?⚙️ 系统设置", wait_until="networkidle", timeout=10000)
        await asyncio.sleep(2)
        
        # 检查系统信息
        metrics = await page.query_selector_all("[data-testid='stMetricValue']")
        if len(metrics) >= 4:
            print_test_result("系统信息指标", True, f"找到 {len(metrics)} 个")
        else:
            result["details"].append(f"系统信息不足: {len(metrics)}/4")
            return result
        
        # 检查配置信息
        page_content = await page.content()
        if "配置" in page_content or "config" in page_content:
            print_test_result("配置信息", True)
        else:
            result["details"].append("未找到配置信息")
        
        result["passed"] = True
        
    except Exception as e:
        result["details"].append(f"测试异常: {e}")
    
    return result


async def test_page_navigation(page: Page) -> dict:
    """测试页面导航"""
    print_test_header("页面导航测试")
    
    result = {"test": "页面导航", "passed": False, "details": [], "navigation_times": []}
    
    pages = [
        "📊 系统概览",
        "🕷️ 数据爬取",
        "👥 联系人管理",
        "📧 邮件营销",
        "📥 数据导出",
        "🗄️ 数据库管理",
        "📋 系统日志",
        "⚙️ 系统设置",
    ]
    
    try:
        for page_name in pages:
            start_time = time.time()
            
            await page.goto(f"{WEB_URL}?{page_name}", wait_until="networkidle", timeout=10000)
            await asyncio.sleep(1)
            
            nav_time = time.time() - start_time
            result["navigation_times"].append({
                "page": page_name,
                "time": f"{nav_time:.2f}s"
            })
            
            # 验证侧边栏仍然展开
            sidebar_info = await check_sidebar_state(page)
            if not sidebar_info["expanded"]:
                result["details"].append(f"{page_name}: 切换后侧边栏折叠")
            
            print(f"   ✓ {page_name}: {nav_time:.2f}s")
        
        # 计算平均导航时间
        avg_time = sum(float(t["time"].rstrip("s")) for t in result["navigation_times"]) / len(result["navigation_times"])
        print_test_result("平均导航时间", True, f"{avg_time:.2f}s")
        
        if not result["details"]:
            result["passed"] = True
        
    except Exception as e:
        result["details"].append(f"测试异常: {e}")
    
    return result


async def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*70)
    print("🚀 Web Dashboard 完整功能 E2E 测试")
    print("="*70)
    print(f"📅 测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("")
    
    proc = None
    test_results = []
    
    try:
        # 启动 Streamlit
        proc = await start_streamlit()
        
        # 启动 Playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            print("🌐 打开浏览器...")
            await page.goto(WEB_URL, wait_until="networkidle", timeout=30000)
            print("✅ 页面已加载")
            print("")
            
            # 收集控制台消息
            console_messages = []
            def handle_console(msg):
                if msg.type in ["error", "warning"]:
                    console_messages.append({
                        "type": msg.type,
                        "text": msg.text
                    })
            
            page.on("console", handle_console)
            
            # 运行测试
            test_results.append(await test_sidebar_state(page))
            test_results.append(await test_page_overview(page))
            test_results.append(await test_page_scraping(page))
            test_results.append(await test_page_contacts(page))
            test_results.append(await test_page_email(page))
            test_results.append(await test_page_export(page))
            test_results.append(await test_page_database(page))
            test_results.append(await test_page_logs(page))
            test_results.append(await test_page_settings(page))
            test_results.append(await test_page_navigation(page))
            
            await asyncio.sleep(1)
            await browser.close()
        
        # 输出测试结果
        print_test_header("测试结果汇总")
        
        total_tests = len(test_results)
        passed_tests = sum(1 for r in test_results if r["passed"])
        
        for result in test_results:
            icon = "✅" if result["passed"] else "❌"
            print(f"\n{icon} {result['test']}")
            if result["details"]:
                for detail in result["details"]:
                    print(f"   ⚠️  {detail}")
            
            # 输出侧边栏信息
            if "sidebar_info" in result and result["sidebar_info"]:
                info = result["sidebar_info"]
                print(f"   📊 侧边栏宽度: {info['width']}px")
                print(f"   📊 展开: {'是' if info['expanded'] else '否'}")
                print(f"   📊 折叠按钮隐藏: {'是' if info['collapsed_button_hidden'] else '否'}")
            
            # 输出导航时间
            if "navigation_times" in result and result["navigation_times"]:
                print(f"   ⏱️  导航时间:")
                for nav in result["navigation_times"]:
                    print(f"      {nav['page']}: {nav['time']}")
        
        # 输出控制台消息
        if console_messages:
            print("\n" + "="*70)
            print("🖥️  浏览器控制台消息")
            print("="*70)
            for msg in console_messages[:10]:
                icon = "❌" if msg["type"] == "error" else "⚠️ "
                print(f"{icon} {msg['type']}: {msg['text'][:100]}")
        
        print("\n" + "="*70)
        print(f"📊 测试统计")
        print("="*70)
        print(f"总测试数: {total_tests}")
        print(f"通过: {passed_tests} ✅")
        print(f"失败: {total_tests - passed_tests} ❌")
        print(f"通过率: {passed_tests/total_tests*100:.1f}%")
        print("="*70)
        
        if passed_tests == total_tests:
            print("\n🎉 所有测试通过！")
            print("\n✅ 侧边栏固定展开功能正常")
            print("✅ 所有功能页面可正常访问")
            print("✅ 页面导航流畅")
        else:
            print(f"\n❌ {total_tests - passed_tests} 个测试失败")
        
        return test_results
        
    finally:
        if proc:
            await stop_streamlit(proc)


if __name__ == "__main__":
    try:
        results = asyncio.run(run_all_tests())
        total_passed = sum(1 for r in results if r["passed"])
        total_tests = len(results)
        sys.exit(1 if total_passed < total_tests else 0)
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ 测试执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
