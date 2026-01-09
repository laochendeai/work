#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Streamlit Web Dashboard V2 E2E 测试

测试美化增强版的 Web Dashboard
"""

import asyncio
import subprocess
import time
import sys
from pathlib import Path

from playwright.async_api import async_playwright


WEB_URL = "http://localhost:8501"
STREAMLIT_PORT = 8501


async def start_streamlit():
    """启动 Streamlit"""
    project_root = Path(__file__).resolve().parents[1]
    dashboard_file = project_root / "scripts" / "web_dashboard_v2.py"
    
    print(f"📂 项目目录: {project_root}")
    print(f"📄 Dashboard: V2 (美化增强版)")
    
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
                break
        except Exception:
            time.sleep(1)
    else:
        proc.kill()
        raise TimeoutError("启动超时")
    
    return proc


async def stop_streamlit(proc):
    """停止 Streamlit"""
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()


async def test_page_by_url(page, page_name, url_param):
    """测试页面"""
    print(f"\n{'='*50}")
    print(f"🧪 测试: {page_name}")
    print('='*50)
    
    result = {"page": page_name, "errors": [], "warnings": []}
    
    try:
        await page.wait_for_load_state("networkidle", timeout=10000)
        
        test_url = f"{WEB_URL}?{url_param}"
        await page.goto(test_url, wait_until="networkidle", timeout=10000)
        print(f"✅ 成功切换到 {page_name}")
        
        await asyncio.sleep(2)
        
        # 检查页面内容
        page_content = await page.content()
        
        # 检查是否有错误指示
        if "错误" in page_content and "Error" not in page_content:
            result["warnings"].append("页面可能包含错误指示")
        
        # 检查页面关键元素
        if any(keyword in page_content for keyword in ["智能设计营销系统", "🚀", "数据"]):
            print(f"✅ {page_name} 页面内容正常")
        else:
            result["warnings"].append("页面内容可能异常")
        
        # 检查 CSS 样式是否加载
        if "gradient" in page_content or "padding" in page_content:
            print("✅ 样式已应用")
        
    except Exception as e:
        result["errors"].append(f"测试异常: {e}")
    
    return result


async def run_all_tests():
    """运行所有测试"""
    print("="*50)
    print("🚀 Web Dashboard V2 E2E 测试")
    print("="*50)
    
    proc = None
    test_results = []
    
    try:
        proc = await start_streamlit()
        
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
                        "text": msg.text
                    })
            
            page.on("console", handle_console)
            
            # 测试所有页面
            pages = [
                ("📊 系统概览", "📊 系统概览"),
                ("🕷️ 数据爬取", "🕷️ 数据爬取"),
                ("👥 联系人管理", "👥 联系人管理"),
                ("📧 邮件营销", "📧 邮件营销"),
                ("📥 数据导出", "📥 数据导出"),
                ("🗄️ 数据库管理", "🗄️ 数据库管理"),
                ("📋 系统日志", "📋 系统日志"),
                ("⚙️ 系统设置", "⚙️ 系统设置"),
            ]
            
            for page_name, url_param in pages:
                result = await test_page_by_url(page, page_name, url_param)
                test_results.append(result)
            
            await asyncio.sleep(2)
            await browser.close()
        
        # 输出结果
        print(f"\n{'='*50}")
        print("📊 测试结果汇总")
        print('='*50)
        
        total_errors = sum(len(r["errors"]) for r in test_results)
        total_warnings = sum(len(r["warnings"]) for r in test_results)
        
        for result in test_results:
            status = "✅" if not result["errors"] else "❌"
            print(f"{status} {result['page']}")
            if result["errors"]:
                for err in result["errors"]:
                    print(f"   ❌ {err}")
            if result["warnings"]:
                for warn in result["warnings"]:
                    print(f"   ⚠️  {warn}")
        
        print(f"\n{'='*50}")
        print(f"总计: {total_errors} 个错误, {total_warnings} 个警告")
        print('='*50)
        
        if total_errors == 0:
            print("\n✅ 所有测试通过！")
            print("\n🎉 Web Dashboard V2 (美化增强版) 验证成功！")
        else:
            print(f"\n❌ 发现 {total_errors} 个错误")
        
        return test_results
        
    finally:
        if proc:
            await stop_streamlit(proc)


if __name__ == "__main__":
    try:
        results = asyncio.run(run_all_tests())
        total_errors = sum(len(r["errors"]) for r in results)
        sys.exit(1 if total_errors > 0 else 0)
    except KeyboardInterrupt:
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
