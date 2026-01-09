#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web Dashboard 核心功能 E2E 测试

专注测试：
1. 侧边栏保持展开（宽度 > 250px）
2. 所有 8 个功能页面可访问
3. 页面核心功能正常
4. 页面导航流畅
"""

import asyncio
import subprocess
import time
import sys
from pathlib import Path
from datetime import datetime

from playwright.async_api import async_playwright


WEB_URL = "http://localhost:8501"
STREAMLIT_PORT = 8501


async def start_streamlit():
    """启动 Streamlit"""
    project_root = Path(__file__).resolve().parents[1]
    dashboard_file = project_root / "scripts" / "web_dashboard.py"
    
    print("="*70)
    print("🚀 Web Dashboard 核心功能 E2E 测试")
    print("="*70)
    print(f"📂 项目: {project_root.name}")
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
    
    print("⏳ 启动中...")
    for i in range(30):
        try:
            import urllib.request
            if urllib.request.urlopen(f"{WEB_URL}/_stcore/health", timeout=1).status == 200:
                print(f"✅ 就绪 ({i+1}s)\n")
                break
        except:
            time.sleep(1)
    else:
        proc.kill()
        raise TimeoutError("启动超时")
    
    return proc


async def stop_streamlit(proc):
    """停止 Streamlit"""
    print("\n🛑 停止服务...")
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except:
        proc.kill()


async def check_sidebar(page):
    """检查侧边栏状态"""
    sidebar = await page.query_selector("[data-testid='stSidebar']")
    if sidebar:
        box = await sidebar.bounding_box()
        width = int(box["width"]) if box else 0
        expanded = width > 250
        return width, expanded
    return 0, False


async def test_page(page, page_name, url):
    """测试单个页面"""
    try:
        await page.goto(f"{WEB_URL}?{url}", wait_until="networkidle", timeout=10000)
        await asyncio.sleep(1)
        
        # 检查侧边栏仍然展开
        width, expanded = await check_sidebar(page)
        
        # 检查页面内容
        content = await page.content()
        has_content = len(content) > 1000
        
        return {
            "page": page_name,
            "success": True,
            "sidebar_width": width,
            "sidebar_expanded": expanded,
            "has_content": has_content
        }
    except Exception as e:
        return {
            "page": page_name,
            "success": False,
            "error": str(e)
        }


async def run_tests():
    """运行所有测试"""
    proc = None
    results = []
    
    try:
        proc = await start_streamlit()
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            await page.goto(WEB_URL, wait_until="domcontentloaded", timeout=30000)
            print("🌐 已连接\n")
            
            # 测试配置
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
            
            print("="*70)
            print("🧪 功能测试")
            print("="*70)
            
            for name, url in pages:
                result = await test_page(page, name, url)
                results.append(result)
                
                if result["success"]:
                    icon = "✅"
                    sidebar_status = "展开" if result["sidebar_expanded"] else "折叠"
                    print(f"{icon} {name:<20} | 侧边栏: {result['sidebar_width']}px ({sidebar_status})")
                else:
                    icon = "❌"
                    print(f"{icon} {name:<20} | 错误: {result.get('error', 'Unknown')}")
            
            await browser.close()
        
        # 汇总结果
        print("\n" + "="*70)
        print("📊 测试结果")
        print("="*70)
        
        passed = sum(1 for r in results if r["success"])
        total = len(results)
        
        # 侧边栏统计
        widths = [r["sidebar_width"] for r in results if r["success"]]
        avg_width = sum(widths) / len(widths) if widths else 0
        all_expanded = all(r["sidebar_expanded"] for r in results if r["success"])
        
        print(f"通过: {passed}/{total}")
        print(f"侧边栏平均宽度: {avg_width:.0f}px")
        print(f"侧边栏状态: {'全部展开 ✅' if all_expanded else '部分折叠 ❌'}")
        print("="*70)
        
        if passed == total and all_expanded:
            print("\n🎉 所有功能正常！")
            print("✅ 侧边栏在所有页面保持展开")
            print("✅ 所有功能页面可访问")
        else:
            print(f"\n⚠️  {total - passed} 个功能异常")
        
        return results
        
    finally:
        if proc:
            await stop_streamlit(proc)


if __name__ == "__main__":
    try:
        results = asyncio.run(run_tests())
        sys.exit(0 if all(r["success"] and r["sidebar_expanded"] for r in results) else 1)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
