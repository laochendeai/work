#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能设计营销自动化技能测试脚本
全面测试技能的各个组件和功能
"""

import os
import sys
import json
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, Any, List
import time


class SkillTester:
    """技能测试器"""

    def __init__(self):
        self.skill_root = Path(__file__).parent.parent
        self.test_results = {
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'test_details': []
        }

    def run_all_tests(self):
        """运行所有测试"""
        print("🧪 智能设计营销自动化技能测试")
        print("=" * 60)
        print()

        # 测试脚本文件
        self.test_script_files()

        # 测试配置文件
        self.test_config_files()

        # 测试模板文件
        self.test_template_files()

        # 测试参考资料
        self.test_reference_files()

        # 测试项目初始化
        self.test_project_initialization()

        # 生成测试报告
        self.generate_test_report()

    def test_script_files(self):
        """测试脚本文件"""
        print("📄 测试脚本文件...")

        scripts_dir = self.skill_root / "scripts"
        required_scripts = [
            "init_project.py",
            "create_scraper.py",
            "setup_extraction.py",
            "setup_email.py"
        ]

        for script_name in required_scripts:
            script_path = scripts_dir / script_name
            if script_path.exists():
                result = self.test_python_syntax(script_path)
                self.record_test(f"脚本语法测试: {script_name}", result)
            else:
                self.record_test(f"脚本存在性: {script_name}", False, f"文件不存在: {script_path}")

    def test_python_syntax(self, file_path: Path) -> bool:
        """测试Python语法"""
        try:
            result = subprocess.run([
                sys.executable, '-m', 'py_compile', str(file_path)
            ], capture_output=True, text=True, timeout=10)

            return result.returncode == 0
        except Exception as e:
            return False

    def test_config_files(self):
        """测试配置文件"""
        print("⚙️ 测试配置文件...")

        config_dir = self.skill_root / "assets" / "config_samples"
        required_configs = [
            "personal_config.json"
        ]

        for config_name in required_configs:
            config_path = config_dir / config_name
            if config_path.exists():
                result = self.test_json_syntax(config_path)
                self.record_test(f"配置语法测试: {config_name}", result)
            else:
                self.record_test(f"配置存在性: {config_name}", False, f"文件不存在: {config_path}")

    def test_json_syntax(self, file_path: Path) -> bool:
        """测试JSON语法"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                json.load(f)
            return True
        except Exception as e:
            return False

    def test_template_files(self):
        """测试模板文件"""
        print("📧 测试模板文件...")

        templates_dir = self.skill_root / "assets" / "templates"

        # 测试邮件模板
        email_templates = templates_dir / "emails"
        if email_templates.exists():
            for template_file in email_templates.glob("*.html"):
                result = self.test_html_template(template_file)
                self.record_test(f"邮件模板: {template_file.name}", result)

        # 测试项目模板
        project_templates = templates_dir / "basic_project"
        if project_templates.exists():
            readme_file = project_templates / "README.md"
            if readme_file.exists():
                self.record_test(f"项目模板README", True)
            else:
                self.record_test(f"项目模板README", False, "README.md文件不存在")

    def test_html_template(self, file_path: Path) -> bool:
        """测试HTML模板"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 检查基本HTML结构
            if not content.strip().startswith('<!DOCTYPE html>'):
                return False

            # 检查模板变量
            template_vars = ['{{ subject }}', '{{ contact_name }}', '{{ sender_name }}']
            for var in template_vars:
                if var not in content:
                    return False

            return True
        except Exception as e:
            return False

    def test_reference_files(self):
        """测试参考资料"""
        print("📚 测试参考资料...")

        references_dir = self.skill_root / "references"
        required_docs = [
            "crawler_patterns.md",
            "extraction_rules.md",
            "email_templates.md"
        ]

        for doc_name in required_docs:
            doc_path = references_dir / doc_name
            if doc_path.exists():
                result = self.test_markdown_doc(doc_path)
                self.record_test(f"参考文档: {doc_name}", result)
            else:
                self.record_test(f"参考文档存在性: {doc_name}", False, f"文件不存在: {doc_path}")

    def test_markdown_doc(self, file_path: Path) -> bool:
        """测试Markdown文档"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 检查基本markdown结构
            if len(content) < 1000:  # 文档应该有足够内容
                return False

            # 检查是否有标题
            if '#' not in content:
                return False

            return True
        except Exception as e:
            return False

    def test_project_initialization(self):
        """测试项目初始化功能"""
        print("🚀 测试项目初始化...")

        # 创建临时测试目录
        with tempfile.TemporaryDirectory() as temp_dir:
            test_project_name = "test_marketing_system"

            try:
                # 运行初始化脚本
                init_script = self.skill_root / "scripts" / "init_project.py"
                if not init_script.exists():
                    self.record_test("项目初始化", False, "初始化脚本不存在")
                    return

                # 切换到临时目录并运行初始化
                os.chdir(temp_dir)
                result = subprocess.run([
                    sys.executable, str(init_script),
                    "--name", test_project_name,
                    "--type", "basic"
                ], capture_output=True, text=True, timeout=30)

                # 检查初始化结果
                if result.returncode == 0:
                    # 检查项目文件是否生成
                    project_path = Path(temp_dir) / test_project_name
                    required_files = [
                        "src/main.py",
                        "config/project_config.json",
                        "requirements.txt",
                        "README.md"
                    ]

                    all_files_exist = True
                    for file_path in required_files:
                        if not (project_path / file_path).exists():
                            all_files_exist = False
                            break

                    self.record_test("项目初始化", all_files_exist)

                    if all_files_exist:
                        # 测试主程序语法
                        main_file = project_path / "src" / "main.py"
                        syntax_ok = self.test_python_syntax(main_file)
                        self.record_test("生成的项目语法", syntax_ok)

                else:
                    self.record_test("项目初始化", False, f"初始化失败: {result.stderr}")

            except Exception as e:
                self.record_test("项目初始化", False, f"测试异常: {str(e)}")
            finally:
                # 切换回原目录
                os.chdir(self.skill_root)

    def record_test(self, test_name: str, passed: bool, details: str = ""):
        """记录测试结果"""
        self.test_results['total_tests'] += 1
        if passed:
            self.test_results['passed_tests'] += 1
        else:
            self.test_results['failed_tests'] += 1

        self.test_results['test_details'].append({
            'name': test_name,
            'passed': passed,
            'details': details
        })

        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {status} {test_name}")
        if details and not passed:
            print(f"    详情: {details}")

    def generate_test_report(self):
        """生成测试报告"""
        print()
        print("📊 测试报告")
        print("=" * 60)

        total = self.test_results['total_tests']
        passed = self.test_results['passed_tests']
        failed = self.test_results['failed_tests']

        if total > 0:
            success_rate = (passed / total) * 100
            print(f"总测试数: {total}")
            print(f"通过: {passed}")
            print(f"失败: {failed}")
            print(f"成功率: {success_rate:.1f}%")
        else:
            print("没有执行任何测试")

        print()
        print("详细结果:")
        print("-" * 60)

        for test in self.test_results['test_details']:
            status = "✅" if test['passed'] else "❌"
            print(f"{status} {test['name']}")
            if test['details'] and not test['passed']:
                print(f"   错误: {test['details']}")

        print()
        if self.test_results['failed_tests'] == 0:
            print("🎉 所有测试通过！技能配置正常。")
            print()
            print("下一步操作:")
            print("1. 创建新项目: python scripts/init_project.py --name your-project")
            print("2. 配置个人信息: 编辑生成的配置文件")
            print("3. 运行系统: python src/main.py")
        else:
            print("⚠️ 部分测试失败，请检查上述错误并修复。")

        return self.test_results

    def test_skill_functionality(self):
        """测试技能功能完整性"""
        print("🔧 测试技能功能完整性...")

        # 检查技能核心组件
        skill_components = {
            "技能定义文件": self.skill_root / "SKILL.md",
            "初始化脚本": self.skill_root / "scripts" / "init_project.py",
            "爬虫生成器": self.skill_root / "scripts" / "create_scraper.py",
            "信息提取配置": self.skill_root / "scripts" / "setup_extraction.py",
            "邮件营销配置": self.skill_root / "scripts" / "setup_email.py",
            "爬虫策略文档": self.skill_root / "references" / "crawler_patterns.md",
            "提取规则文档": self.skill_root / "references" / "extraction_rules.md",
            "邮件模板文档": self.skill_root / "references" / "email_templates.md"
        }

        for component_name, component_path in skill_components.items():
            exists = component_path.exists()
            self.record_test(f"组件完整性: {component_name}", exists)

            if exists:
                # 检查文件大小
                size = component_path.stat().st_size
                size_ok = size > 1000  # 至少1KB
                self.record_test(f"组件大小: {component_name}", size_ok,
                               f"文件大小: {size} bytes")

def main():
    """主函数"""
    tester = SkillTester()

    try:
        # 运行所有测试
        tester.run_all_tests()

        # 额外功能测试
        tester.test_skill_functionality()

        # 生成最终报告
        results = tester.generate_test_report()

        # 返回适当的退出码
        sys.exit(0 if results['failed_tests'] == 0 else 1)

    except KeyboardInterrupt:
        print("\n\n⏹️ 测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 测试过程中发生错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()