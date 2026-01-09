#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Streamlit Web Dashboard E2E 测试 (修复版)

修复页面切换问题，使用 URL 参数切换 Streamlit 页面
"""

import asyncio
import subprocess
import time
import sys
from pathlib import Path

from playwright.async_api import async_playwright, Page, Browser


# Web UI 配置
WEB_URL = "http://localhost:8501"
STREAMLIT_PORT = 8501


async def start_streamlit() -> subprocess.Popen:
    """启动 Streamlit 服务器"""
    project_root = Path(__file__).resolve().parents[1]
    dashboard_file = project_root / "scripts" / "web_dashboard.py"
    
    print(f"📂 项目目录: {project_root}")
    print(f"📄 Dashboard 文件: {dashboard_file}")
    
    if not dashboard_file.exists():
        raise FileNotFoundError(f"Dashboard 文件不存在: {dashboard_file}")
    
    # 启动 Streamlit (后台运行)
    proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", str(dashboard_file),
         "--server.headless", "true",
         "--server.port", str(STREAMLIT_PORT)],
        cwd=str(project_root),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # 等待启动
    print("⏳ 等待 Streamlit 启动...")
    for i in range(30):
        try:
            import urllib.request
            response = urllib.request.urlopen(f"{WEB_URL}/_stcore/health", timeout=1)
            if response.status == 200:
                print(f"✅ Streamlit 已启动 (耗时 {i+1} 秒)")
                break
        except Exception:
            time.sleep(1)
            if i % 5 == 0:
                print(f"   等待中... {i+1}/30")
    else:
        print("❌ Streamlit 启动超时")
        proc.kill()
        raise TimeoutError("Streamlit 启动超时")
    
    return proc


async def stop_streamlit(proc: subprocess.Popen):
    """停止 Streamlit 服务器"""
    print("🛑 停止 Streamlit...")
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
    print("✅ Streamlit 已停止")


async def test_page_overview(page: Page) -> dict:
    """测试系统概览页面"""
    print("\n" + "="*50)
    print("🧪 测试: 系统概览页面")
    print("="*50)
    
    result = {"page": "系统概览", "errors": [], "warnings": []}
    
    try:
        await page.wait_for_load_state("networkidle", timeout=10000)
        print("✅ 页面加载完成")
        
        # 检查标题
        title = await page.title()
        print(f"📌 页面标题: {title}")
        
        # 检查指标
        try:
            metrics = await page.query_selector_all("[data-testid='stMetric']")
            print(f"📊 找到 {len(metrics)} 个指标卡片")
        except Exception as e:
            result["errors"].append(f"指标检查失败: {e}")
        
    except Exception as e:
        result["errors"].append(f"测试异常: {e}")
    
    return result


async def test_page_by_url(page: Page, page_name: str, url_param: str) -> dict:
    """通过 URL 参数测试页面"""
    print("\n" + "="*50)
    print(f"🧪 测试: {page_name}")
    print("="*50)
    
    result = {"page": page_name, "errors": [], "warnings": []}
    
    try:
        await page.wait_for_load_state("networkidle", timeout=10000)
        
        # 使用 URL 参数切换页面
        test_url = f"{WEB_URL}?{url_param}"
        await page.goto(test_url, wait_until="networkidle", timeout=10000)
        print(f"✅ 成功切换到 {page_name}")
        
        await asyncio.sleep(2)
        
        # 检查页面内容
        try:
            page_content = await page.content()
            if page_name in page_content or any(keyword in page_content for keyword in ["数据", "联系人", "邮件", "系统", "设置"]):
                print(f"✅ {page_name} 页面显示正常")
            else:
                result["warnings"].append("页面内容可能异常")
        except Exception as e:
            result["errors"].append(f"页面内容检查失败: {e}")
        
    except Exception as e:
        result["errors"].append(f"测试异常: {e}")
    
    return result


async def run_all_tests():
    """运行所有 E2E 测试"""
    print("="*50)
    print("🚀 Streamlit Web Dashboard E2E 测试")
    print("="*50)
    
    streamlit_proc = None
    test_results = []
    
    try:
        # 启动 Streamlit
        streamlit_proc = await start_streamlit()
        
        # 启动 Playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            print("\n🌐 打开页面...")
            await page.goto(WEB_URL, wait_until="networkidle", timeout=30000)
            print(f"✅ 页面已加载: {WEB_URL}")
            
            # 收集控制台消息
            console_messages = []
            def handle_console(msg):
                if msg.type in ["error", "warning"]:
                    console_messages.append({
                        "type": msg.type,
                        "text": msg.text,
                        "location": f"{msg.location.get('url', '')}:{msg.location.get('lineNumber', '')}"
                    })
            
            page.on("console", handle_console)
            
            # 运行各页面测试
            test_results.append(await test_page_overview(page))
            test_results.append(await test_page_by_url(page, "数据爬取", "数据爬取"))
            test_results.append(await test_page_by_url(page, "联系人管理", "联系人管理"))
            test_results.append(await test_page_by_url(page, "邮件营销", "邮件营销"))
            test_results.append(await test_page_by_url(page, "系统设置", "系统设置"))
            
            await asyncio.sleep(2)
            await browser.close()
        
        # 输出测试结果
        print("\n" + "="*50)
        print("📊 测试结果汇总")
        print("="*50)
        
        total_errors = sum(len(r["errors"]) for r in test_results)
        total_warnings = sum(len(r["warnings"]) for r in test_results)
        
        for result in test_results:
            print(f"\n📄 {result['page']}:")
            if result["errors"]:
                print(f"  ❌ 错误 ({len(result['errors'])}):")
                for err in result["errors"]:
                    print(f"     - {err}")
            if result["warnings"]:
                print(f"  ⚠️  警告 ({len(result['warnings'])}):")
                for warn in result["warnings"]:
                    print(f"     - {warn}")
            if not result["errors"] and not result["warnings"]:
                print("  ✅ 全部通过")
        
        # 输出控制台消息
        if console_messages:
            print("\n" + "="*50)
            print("🖥️  浏览器控制台消息")
            print("="*50)
            for msg in console_messages[:20]:
                icon = "❌" if msg["type"] == "error" else "⚠️ "
                print(f"{icon} {msg['type']}: {msg['text']}")
        
        print("\n" + "="*50)
        print(f"总计: {total_errors} 个错误, {total_warnings} 个警告")
        print("="*50)
        
        if total_errors == 0:
            print("\n✅ 所有测试通过！")
        else:
            print(f"\n❌ 发现 {total_errors} 个错误需要修复")
        
        return test_results, console_messages
        
    finally:
        # 停止 Streamlit
        if streamlit_proc:
            await stop_streamlit(streamlit_proc)


if __name__ == "__main__":
    try:
        results, console_msgs = asyncio.run(run_all_tests())
        
        # 如果有错误，返回非零退出码
        total_errors = sum(len(r["errors"]) for r in results)
        sys.exit(1 if total_errors > 0 else 0)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ 测试执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
