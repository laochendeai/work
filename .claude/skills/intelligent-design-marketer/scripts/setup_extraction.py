#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
信息提取配置工具
设置和测试联系人信息提取规则和正则表达式
"""

import argparse
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Tuple


class ExtractionSetup:
    """信息提取配置类"""

    def __init__(self):
        self.extraction_patterns = {
            # 手机号正则
            'phone': [
                r'1[3-9]\d{9}',  # 常规手机号
                r'\+86\s*1[3-9]\d{9}',  # 带国际区号
                r'\d{3}-\d{4}-\d{4}',  # 带连字符
                r'\d{11}',  # 11位数字
            ],

            # 座机号正则
            'landline': [
                r'0\d{2,3}-?\d{7,8}',  # 区号-电话号码
                r'\d{3,4}-\d{7,8}',  # 3-4位区号
                r'\d{10,12}',  # 10-12位座机号
            ],

            # 邮箱正则
            'email': [
                r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
                r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.(com|cn|org|net|gov|edu)',
            ],

            # 姓名正则
            'name': [
                r'[王李张刘陈杨黄赵吴周徐孙马朱胡郭何高林罗郑梁谢宋唐许韩冯邓曹彭曾肖田董袁潘于蒋蔡余杜叶程苏魏吕丁任沈姚卢姜崔钟谭陆汪范金石廖贾夏韦付方白邹孟熊秦邱江尹薛闫段雷侯龙史陶黎贺顾毛郝龚邵万钱严覃武戴莫孔向汤][一-龥]{1,3}',
            ],

            # 职位/部门正则
            'department': [
                r'(院长|处长|科长|主任|经理|总监|主管|工程师|技术员|采购员|招标师|项目经理)',
                r'(技术部|采购部|信息中心|网络中心|设备科|后勤处|总务处)',
                r'(办公室|行政部|财务部|审计部|法务部|人事部)',
            ],

            # 公司正则
            'company': [
                r'([一-龥]+(公司|集团|企业|院|所|中心|局|委|部|署|厅))',
                r'([一-龥]+(技术|信息|网络|智能|科技|电子|自动化|建设|工程).{0,10}(公司|集团))',
            ],

            # 项目金额正则
            'budget': [
                r'(\d+(?:\.\d+)?)\s*(万|千|百)',
                r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*元',
                r'人民币\s*(\d+(?:\.\d+)?)\s*万',
                r'预算[：:]\s*(\d+(?:\.\d+)?)\s*(万|千|百)',
            ],

            # 项目时间正则
            'deadline': [
                r'(\d{4}年\d{1,2}月\d{1,2}日)',
                r'(\d{4}-\d{1,2}-\d{1,2})',
                r'(\d{1,2}月\d{1,2}日前)',
                r'(工期[：:]\s*\d+\s*(天|日|月))',
            ],

            # 联系方式关键词
            'contact_keywords': [
                '联系电话', '手机', '电话', '联系人', '联系人：', '联系人：',
                '邮箱', '邮件', 'email', 'E-mail', '联系地址',
                '地址', '邮编', '传真', 'qq', 'QQ', '微信', '微信',
            ]
        }

        self.extraction_config = {
            "enabled_fields": [
                "phone", "email", "name", "department", "company", "budget", "deadline"
            ],
            "extraction_rules": self.extraction_patterns,
            "validation_rules": {
                "phone_min_length": 11,
                "email_domains": ["qq.com", "163.com", "126.com", "sina.com", "gmail.com", "outlook.com"],
                "company_blacklist": ["测试公司", "示例公司"],
            },
            "confidence_threshold": 0.7,
            "deduplication": {
                "enabled": True,
                "similar_threshold": 0.8
            }
        }

    def create_extraction_config(self, config_path: str = "config/extraction_config.json"):
        """创建信息提取配置文件"""
        config_path = Path(config_path)
        config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(self.extraction_config, f, ensure_ascii=False, indent=2)

        print(f"✓ 创建信息提取配置: {config_path}")

    def create_contact_extractor(self, output_path: str = "src/extractors/contact_extractor.py"):
        """创建联系人信息提取器"""
        extractor_code = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
联系人信息提取器
从文本中智能提取联系人、公司、项目等信息
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from difflib import SequenceMatcher
import jieba
import jieba.posseg as pseg


class ContactExtractor:
    """联系人信息提取器"""

    def __init__(self, config_path: str = "config/extraction_config.json"):
        """
        初始化提取器

        Args:
            config_path: 配置文件路径
        """
        self.logger = logging.getLogger(__name__)
        self.config = self._load_config(config_path)
        self.patterns = self.config.get('extraction_rules', {})
        self.enabled_fields = self.config.get('enabled_fields', [])
        self.confidence_threshold = self.config.get('confidence_threshold', 0.7)

        # 初始化jieba分词
        jieba.initialize()

        # 加载自定义词典
        self._load_custom_dict()

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"配置文件加载失败: {e}")
            return self._get_default_config()

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "enabled_fields": ["phone", "email", "name", "department", "company"],
            "extraction_rules": {
                "phone": [r'1[3-9]\\d{9}'],
                "email": [r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}'],
                "name": [r'[王李张刘陈杨黄赵吴周徐孙马朱胡郭何高林罗郑梁谢宋唐许韩冯邓曹彭曾肖田董袁潘于蒋蔡余杜叶程苏魏吕丁任沈姚卢姜崔钟谭陆汪范金石廖贾夏韦付方白邹孟熊秦邱江尹薛闫段雷侯龙史陶黎贺顾毛郝龚邵万钱严覃武戴莫孔向汤][一-龥]{1,3}'],
                "department": [r'(院长|处长|科长|主任|经理|总监|主管)'],
                "company": [r'([一-龥]+(公司|集团|企业|院|所|中心))'],
            },
            "confidence_threshold": 0.7
        }

    def _load_custom_dict(self):
        """加载自定义词典"""
        # 添加行业专有词汇
        industry_terms = [
            "智能化", "弱电", "安防", "监控", "门禁", "楼宇自动化",
            "系统集成", "网络建设", "机房建设", "综合布线",
            "会议系统", "广播系统", "一卡通", "停车场管理"
        ]

        for term in industry_terms:
            jieba.add_word(term)

    def extract_phones(self, text: str) -> List[Dict[str, Any]]:
        """提取手机号"""
        phones = []
        phone_patterns = self.patterns.get('phone', [])
        landline_patterns = self.patterns.get('landline', [])

        all_patterns = phone_patterns + landline_patterns

        for pattern in all_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                phone = match.group().strip()
                # 清理和验证手机号
                clean_phone = re.sub(r'[^\d+]', '', phone)

                if len(clean_phone) >= 11:  # 确保是有效的号码
                    phones.append({
                        'type': 'phone' if len(clean_phone) == 11 else 'landline',
                        'value': clean_phone,
                        'original': phone,
                        'position': match.span(),
                        'confidence': 0.9
                    })

        return self._deduplicate_list(phones, 'value')

    def extract_emails(self, text: str) -> List[Dict[str, Any]]:
        """提取邮箱"""
        emails = []
        email_patterns = self.patterns.get('email', [])

        for pattern in email_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                email = match.group().strip().lower()

                # 验证邮箱格式
                if self._validate_email(email):
                    emails.append({
                        'type': 'email',
                        'value': email,
                        'original': match.group(),
                        'position': match.span(),
                        'confidence': 0.85
                    })

        return self._deduplicate_list(emails, 'value')

    def extract_names(self, text: str) -> List[Dict[str, Any]]:
        """提取姓名"""
        names = []
        name_patterns = self.patterns.get('name', [])

        for pattern in name_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                name = match.group().strip()

                # 过滤明显不是姓名的内容
                if self._validate_name(name):
                    names.append({
                        'type': 'name',
                        'value': name,
                        'original': name,
                        'position': match.span(),
                        'confidence': 0.75
                    })

        # 结合上下文分析提高准确性
        names = self._enhance_name_extraction(names, text)

        return self._deduplicate_list(names, 'value')

    def extract_departments(self, text: str) -> List[Dict[str, Any]]:
        """提取部门/职位信息"""
        departments = []
        dept_patterns = self.patterns.get('department', [])

        for pattern in dept_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                dept = match.group().strip()

                departments.append({
                    'type': 'department',
                    'value': dept,
                    'original': dept,
                    'position': match.span(),
                    'confidence': 0.8
                })

        return self._deduplicate_list(departments, 'value')

    def extract_companies(self, text: str) -> List[Dict[str, Any]]:
        """提取公司信息"""
        companies = []
        company_patterns = self.patterns.get('company', [])

        for pattern in company_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                company = match.group().strip()

                # 过滤测试公司
                blacklist = self.config.get('validation_rules', {}).get('company_blacklist', [])
                if not any(blackword in company for blackword in blacklist):
                    companies.append({
                        'type': 'company',
                        'value': company,
                        'original': company,
                        'position': match.span(),
                        'confidence': 0.7
                    })

        return self._deduplicate_list(companies, 'value')

    def extract_budget(self, text: str) -> List[Dict[str, Any]]:
        """提取项目预算"""
        budgets = []
        budget_patterns = self.patterns.get('budget', [])

        for pattern in budget_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                budget_info = match.group()

                budgets.append({
                    'type': 'budget',
                    'value': budget_info,
                    'original': budget_info,
                    'position': match.span(),
                    'confidence': 0.8
                })

        return budgets

    def extract_deadline(self, text: str) -> List[Dict[str, Any]]:
        """提取项目截止时间"""
        deadlines = []
        deadline_patterns = self.patterns.get('deadline', [])

        for pattern in deadline_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                deadline = match.group().strip()

                deadlines.append({
                    'type': 'deadline',
                    'value': deadline,
                    'original': deadline,
                    'position': match.span(),
                    'confidence': 0.85
                })

        return self._deduplicate_list(deadlines, 'value')

    def extract_contacts(self, text: str) -> Dict[str, Any]:
        """
        提取所有联系人信息

        Args:
            text: 待提取的文本

        Returns:
            提取结果字典
        """
        result = {
            'text_length': len(text),
            'extraction_time': '',
            'contacts': {
                'phones': [],
                'emails': [],
                'names': [],
                'departments': [],
                'companies': [],
                'budgets': [],
                'deadlines': []
            },
            'confidence_score': 0
        }

        try:
            # 根据配置提取各种类型的信息
            if 'phone' in self.enabled_fields:
                result['contacts']['phones'] = self.extract_phones(text)

            if 'email' in self.enabled_fields:
                result['contacts']['emails'] = self.extract_emails(text)

            if 'name' in self.enabled_fields:
                result['contacts']['names'] = self.extract_names(text)

            if 'department' in self.enabled_fields:
                result['contacts']['departments'] = self.extract_departments(text)

            if 'company' in self.enabled_fields:
                result['contacts']['companies'] = self.extract_companies(text)

            if 'budget' in self.enabled_fields:
                result['contacts']['budgets'] = self.extract_budget(text)

            if 'deadline' in self.enabled_fields:
                result['contacts']['deadlines'] = self.extract_deadline(text)

            # 计算整体置信度
            result['confidence_score'] = self._calculate_confidence(result['contacts'])

            # 记录提取时间
            from datetime import datetime
            result['extraction_time'] = datetime.now().isoformat()

        except Exception as e:
            self.logger.error(f"信息提取失败: {e}")
            result['error'] = str(e)

        return result

    def _validate_email(self, email: str) -> bool:
        """验证邮箱格式"""
        try:
            # 基本格式验证
            pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'
            if not re.match(pattern, email):
                return False

            # 检查常见域名
            valid_domains = self.config.get('validation_rules', {}).get('email_domains', [])
            domain = email.split('@')[-1]

            return len(email.split('@')) == 2 and len(domain) > 2

        except:
            return False

    def _validate_name(self, name: str) -> bool:
        """验证姓名有效性"""
        # 姓名长度检查
        if len(name) < 2 or len(name) > 6:
            return False

        # 排除明显不是姓名的内容
        exclude_words = ['公司', '集团', '有限', '股份', '技术', '工程', '建设']
        return not any(word in name for word in exclude_words)

    def _enhance_name_extraction(self, names: List[Dict[str, Any]], text: str) -> List[Dict[str, Any]]:
        """结合上下文增强姓名提取"""
        contact_keywords = self.patterns.get('contact_keywords', [])

        enhanced_names = []
        for name_info in names:
            name = name_info['value']
            position = name_info['position']

            # 检查姓名附近是否有联系人关键词
            start_pos = max(0, position[0] - 50)
            end_pos = min(len(text), position[1] + 50)
            context = text[start_pos:end_pos]

            if any(keyword in context for keyword in contact_keywords):
                name_info['confidence'] = min(0.95, name_info['confidence'] + 0.2)
                enhanced_names.append(name_info)

        return enhanced_names

    def _deduplicate_list(self, items: List[Dict[str, Any]], key: str) -> List[Dict[str, Any]]:
        """去重"""
        if not self.config.get('deduplication', {}).get('enabled', True):
            return items

        threshold = self.config.get('deduplication', {}).get('similar_threshold', 0.8)
        unique_items = []
        seen_values = set()

        for item in items:
            value = item[key]

            # 精确匹配
            if value not in seen_values:
                unique_items.append(item)
                seen_values.add(value)
                continue

            # 相似度匹配
            is_duplicate = False
            for seen_value in seen_values:
                similarity = SequenceMatcher(None, value, seen_value).ratio()
                if similarity > threshold:
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique_items.append(item)
                seen_values.add(value)

        return unique_items

    def _calculate_confidence(self, contacts: Dict[str, List]) -> float:
        """计算整体置信度"""
        total_items = sum(len(items) for items in contacts.values())
        if total_items == 0:
            return 0.0

        total_confidence = sum(
            sum(item.get('confidence', 0) for item in items)
            for items in contacts.values()
        )

        return min(1.0, total_confidence / total_items)

    def test_extraction(self, test_text: str) -> Dict[str, Any]:
        """测试提取功能"""
        self.logger.info("开始测试信息提取功能")

        result = self.extract_contacts(test_text)

        # 输出测试结果
        self.logger.info(f"测试完成，提取到 {sum(len(v) for v in result['contacts'].values())} 条信息")

        return result


def main():
    """主函数 - 用于测试"""
    # 测试文本
    test_text = """
    项目名称：XX大学智能化系统建设项目

    联系人：张三
    联系电话：13812345678
    邮箱：zhangsan@university.edu.cn

    技术负责人：李四工程师
    电话：13987654321
    邮件：lisi@tech-company.com

    预算：人民币150万元
    工期：2024年6月30日前完成

    采购单位：XX大学信息中心
    地址：XX市XX区XX路123号
    """

    # 创建提取器
    extractor = ContactExtractor()

    # 执行测试
    result = extractor.test_extraction(test_text)

    # 输出结果
    print("=== 信息提取测试结果 ===")
    print(f"置信度: {result['confidence_score']:.2f}")
    print()

    for field, items in result['contacts'].items():
        if items:
            print(f"{field.upper()}:")
            for item in items:
                print(f"  - {item['value']} (置信度: {item['confidence']:.2f})")
            print()


if __name__ == "__main__":
    main()
'''

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(extractor_code)

        print(f"✓ 创建联系人提取器: {output_path}")

    def create_test_data(self, output_dir: str = "assets/test_data"):
        """创建测试数据"""
        test_dir = Path(output_dir)
        test_dir.mkdir(parents=True, exist_ok=True)

        test_samples = [
            {
                "name": "政府采购公告",
                "content": """
                项目名称：XX市行政中心智能化改造项目

                联系人：王明 主任
                联系电话：010-12345678，手机：13912345678
                电子邮箱：wangming@gov.cn

                项目预算：人民币200万元
                招标截止时间：2024年3月15日17:00

                采购单位：XX市人民政府机关事务管理局
                地址：XX市XX区人民路1号
                邮编：100000

                技术负责人：张工
                电话：13987654321
                邮箱：zhanggong@tech-dept.com
                """
            },
            {
                "name": "高校采购公告",
                "content": """
                XX大学智慧校园建设项目招标公告

                项目负责人：李教授
                联系电话：021-65432109
                手机：13812345678
                邮箱：liprof@university.edu.cn

                技术咨询：赵工程师
                电话：13987654321
                email：zhao@it-center.edu.cn

                预算金额：150万元
                项目周期：2024年6月30日前完成

                单位：XX大学信息化建设办公室
                地址：XX市XX区学府路100号
                """
            },
            {
                "name": "企业供应商招募",
                "content": """
                华为公司供应商招募公告

                联系人：张经理（供应链管理部）
                电话：0755-12345678
                手机：18612345678
                邮箱：supplier@huawei.com

                供应商专员：李小姐
                联系方式：13987654321
                email：supplier-recruit@huawei.com

                注册地址：深圳市龙岗区坂田华为基地
                联系地址：深圳市南山区科技园南区

                截止日期：2024年4月30日
                """
            }
        ]

        for i, sample in enumerate(test_samples, 1):
            test_file = test_dir / f"test_sample_{i}.txt"
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write(f"# {sample['name']}\n\n")
                f.write(sample['content'])

            print(f"✓ 创建测试样本: {test_file}")

    def run_test(self, test_file: str = None) -> Dict[str, Any]:
        """运行提取测试"""
        try:
            # 创建临时提取器
            extractor = ContactExtractor()

            if test_file:
                # 测试指定文件
                with open(test_file, 'r', encoding='utf-8') as f:
                    test_text = f.read()
                result = extractor.test_extraction(test_text)
                return result
            else:
                # 测试所有测试数据
                test_dir = Path("assets/test_data")
                if not test_dir.exists():
                    print("❌ 测试数据目录不存在")
                    return {}

                all_results = {}
                for test_file in test_dir.glob("*.txt"):
                    with open(test_file, 'r', encoding='utf-8') as f:
                        test_text = f.read()

                    result = extractor.test_extraction(test_text)
                    all_results[test_file.name] = result

                return all_results

        except Exception as e:
            print(f"❌ 测试执行失败: {e}")
            return {}

    def setup_extraction_system(self, config_path: str = "config/extraction_config.json",
                                extractor_path: str = "src/extractors/contact_extractor.py",
                                test_data_dir: str = "assets/test_data"):
        """完整设置信息提取系统"""
        print("开始设置信息提取系统...")
        print("-" * 50)

        try:
            # 1. 创建配置文件
            self.create_extraction_config(config_path)

            # 2. 创建提取器
            self.create_contact_extractor(extractor_path)

            # 3. 创建测试数据
            self.create_test_data(test_data_dir)

            print("-" * 50)
            print("✅ 信息提取系统设置完成！")
            print()
            print("配置文件位置:")
            print(f"  - 配置: {config_path}")
            print(f"  - 提取器: {extractor_path}")
            print(f"  - 测试数据: {test_data_dir}")
            print()
            print("下一步:")
            print("1. 编辑配置文件调整提取规则")
            print("2. 运行测试验证提取效果")
            print("3. 集成到主系统中使用")

        except Exception as e:
            print(f"❌ 设置失败: {e}")
            raise


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="信息提取配置工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python setup_extraction.py --config
  python setup_extraction.py --test
  python setup_extraction.py --test-file assets/test_data/test_sample_1.txt
  python setup_extraction.py --setup
        """
    )

    parser.add_argument(
        "--config",
        action="store_true",
        help="创建信息提取配置文件"
    )

    parser.add_argument(
        "--test",
        action="store_true",
        help="运行提取测试"
    )

    parser.add_argument(
        "--test-file",
        help="测试指定文件"
    )

    parser.add_argument(
        "--setup",
        action="store_true",
        help="完整设置信息提取系统"
    )

    args = parser.parse_args()

    try:
        setup = ExtractionSetup()

        if args.setup:
            setup.setup_extraction_system()
        elif args.config:
            setup.create_extraction_config()
            print("✓ 配置文件创建完成")
        elif args.test_file:
            result = setup.run_test(args.test_file)
            print(f"✓ 测试完成，结果: {result}")
        elif args.test:
            results = setup.run_test()
            print(f"✓ 所有测试完成，共 {len(results)} 个文件")
            for filename, result in results.items():
                print(f"  {filename}: 置信度 {result.get('confidence_score', 0):.2f}")
        else:
            parser.print_help()

    except Exception as e:
        print(f"❌ 操作失败: {e}")
        import sys
        sys.exit(1)


if __name__ == "__main__":
    main()