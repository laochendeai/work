#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
联系人数据质量评分和分层导出系统
实现智能评分、去重和分层导出功能
"""

import json
import hashlib
import re
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from collections import defaultdict

from config.settings import settings


@dataclass
class QualityScore:
    """数据质量评分结果"""
    total_score: float
    email_score: float
    phone_score: float
    company_score: float
    name_score: float
    completeness_score: float
    confidence_level: str  # high, medium, low
    issues: List[str]


class QualityScorer:
    """数据质量评分器"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # 加载权重配置
        self.weights = {
            'email': settings.get('export.quality_scoring.email_weight', 0.4),
            'phone': settings.get('export.quality_scoring.phone_weight', 0.3),
            'company': settings.get('export.quality_scoring.company_weight', 0.2),
            'name': settings.get('export.quality_scoring.name_weight', 0.1)
        }

        # 验证权重总和
        total_weight = sum(self.weights.values())
        if abs(total_weight - 1.0) > 0.01:
            self.logger.warning(f"权重总和不为1.0: {total_weight}，将自动调整")
            # 自动归一化
            for key in self.weights:
                self.weights[key] /= total_weight

    def score_contact(self, contact: Dict[str, Any]) -> QualityScore:
        """
        对单个联系人进行质量评分

        Returns:
            QualityScore: 评分结果
        """
        scores = {
            'email': self._score_email(contact),
            'phone': self._score_phone(contact),
            'company': self._score_company(contact),
            'name': self._score_name(contact)
        }

        # 计算总分
        total_score = sum(scores[key] * self.weights[key] for key in scores)

        # 完整性评分
        completeness_score = self._calculate_completeness(contact)

        # 综合评分（80%字段评分 + 20%完整性）
        final_score = total_score * 0.8 + completeness_score * 0.2

        # 确定置信度等级
        if final_score >= 0.7:
            confidence = 'high'
        elif final_score >= 0.4:
            confidence = 'medium'
        else:
            confidence = 'low'

        # 收集问题
        issues = self._identify_issues(contact, scores)

        return QualityScore(
            total_score=round(final_score, 3),
            email_score=round(scores['email'], 3),
            phone_score=round(scores['phone'], 3),
            company_score=round(scores['company'], 3),
            name_score=round(scores['name'], 3),
            completeness_score=round(completeness_score, 3),
            confidence_level=confidence,
            issues=issues
        )

    def _score_email(self, contact: Dict[str, Any]) -> float:
        """评分邮箱字段"""
        emails = contact.get('emails', [])
        if not emails:
            return 0.0

        # 取第一个邮箱评分
        email = emails[0].lower().strip()

        # 基础分
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            return 0.0

        # 常见占位域名：视为无效邮箱（用于过滤测试/示例数据）
        domain = email.split('@', 1)[-1]
        if domain in {'example.com', 'test.com', 'localhost'}:
            return 0.0

        score = 0.5

        # 企业邮箱加分
        if any(domain in email for domain in [
            '.gov.cn', '.edu.cn', '.ac.cn',
            '.com.cn', '.org.cn', '.net.cn'
        ]):
            score += 0.2

        # 知名邮箱服务商
        if any(provider in email for provider in [
            '@qq.com', '@163.com', '@126.com', '@sina.com',
            '@gmail.com', '@outlook.com', '@163.net'
        ]):
            score += 0.1

        # 邮箱前缀质量
        local = email.split('@')[0]
        if len(local) >= 3 and not local.isdigit():
            score += 0.2

        return min(score, 1.0)

    def _score_phone(self, contact: Dict[str, Any]) -> float:
        """评分电话字段"""
        phones = contact.get('phones', [])
        if not phones:
            return 0.0

        # 取第一个电话评分
        phone = phones[0]

        # 手机号评分
        if re.match(r'^1[3-9]\d{9}$', phone):
            return 0.9

        # 固定电话评分
        if re.match(r'^0\d{2,3}-?\d{7,8}$', phone):
            return 0.8

        # 包含数字但格式不标准
        if re.search(r'\d{7,}', phone):
            return 0.3

        return 0.0

    def _score_company(self, contact: Dict[str, Any]) -> float:
        """评分公司字段"""
        companies = contact.get('companies', [])
        if not companies:
            return 0.0

        # 取第一个公司名称评分
        company = companies[0].strip()

        if len(company) < 2:
            return 0.0

        score = 0.3

        # 包含公司标识词
        if any(keyword in company for keyword in [
            '公司', '集团', '企业', '有限公司', '股份',
            '学校', '大学', '学院', '研究院',
            '医院', '中心', '政府', '委员会',
            'Co.', 'Ltd', 'Inc', 'Corp'
        ]):
            score += 0.4

        # 长度合理
        if 4 <= len(company) <= 30:
            score += 0.2

        # 不是纯数字或特殊字符
        if not re.match(r'^[0-9\-_]+$', company):
            score += 0.1

        return min(score, 1.0)

    def _score_name(self, contact: Dict[str, Any]) -> float:
        """评分姓名字段"""
        names = contact.get('names', [])
        if not names:
            return 0.0

        # 取第一个姓名评分
        name = names[0].strip()

        if len(name) < 2 or len(name) > 10:
            return 0.0

        score = 0.5

        # 中文姓名
        if re.match(r'^[\u4e00-\u9fa5]{2,4}$', name):
            score += 0.4

        # 包含称谓
        if any(title in name for title in ['先生', '女士', '老师', '经理', '主任']):
            score += 0.1

        # 避免明显错误
        if any(word in name for word in ['测试', 'test', '无名', '未知']):
            score -= 0.3

        return max(0.0, min(score, 1.0))

    def _calculate_completeness(self, contact: Dict[str, Any]) -> float:
        """计算信息完整度"""
        fields = ['emails', 'phones', 'companies', 'names']
        present_fields = 0

        for field in fields:
            if contact.get(field):
                present_fields += 1

        return present_fields / len(fields)

    def _identify_issues(self, contact: Dict[str, Any], scores: Dict[str, float]) -> List[str]:
        """识别数据问题"""
        issues = []

        if scores['email'] == 0:
            issues.append('缺少有效邮箱')
        elif scores['email'] < 0.5:
            issues.append('邮箱质量较低')

        if scores['phone'] == 0:
            issues.append('缺少有效电话')
        elif scores['phone'] < 0.5:
            issues.append('电话格式不标准')

        if scores['company'] == 0:
            issues.append('缺少公司信息')
        elif scores['company'] < 0.5:
            issues.append('公司信息不完整')

        if scores['name'] == 0:
            issues.append('缺少联系人姓名')

        # 检查重复信息
        all_text = ' '.join([
            ' '.join(contact.get('emails', [])),
            ' '.join(contact.get('phones', [])),
            ' '.join(contact.get('companies', [])),
            ' '.join(contact.get('names', []))
        ])

        if len(set(all_text)) / len(all_text) < 0.5 if all_text else True:
            issues.append('信息可能重复')

        return issues


class ContactDeduplicator:
    """联系人去重器"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.seen_hashes: Set[str] = set()
        self.email_index: Dict[str, List[Dict]] = defaultdict(list)
        self.phone_index: Dict[str, List[Dict]] = defaultdict(list)

    def deduplicate_contacts(self, contacts: List[Dict[str, Any]]) -> Tuple[List[Dict], Dict]:
        """
        去重联系人列表

        Returns:
            Tuple: (去重后的联系人列表, 去重统计信息)
        """
        deduped = []
        stats = {
            'original_count': len(contacts),
            'removed_count': 0,
            'email_duplicates': 0,
            'phone_duplicates': 0,
            'hash_duplicates': 0
        }

        # 按质量评分排序，保留高质量的
        scorer = QualityScorer()
        scored_contacts = []

        for contact in contacts:
            score = scorer.score_contact(contact)
            contact['_quality_score'] = asdict(score)
            scored_contacts.append(contact)

        # 按评分降序排序
        scored_contacts.sort(key=lambda x: x['_quality_score']['total_score'], reverse=True)

        # 去重处理
        for contact in scored_contacts:
            # 检查哈希重复
            contact_hash = self._calculate_hash(contact)
            if contact_hash in self.seen_hashes:
                stats['hash_duplicates'] += 1
                continue

            # 检查邮箱重复
            emails = contact.get('emails', [])
            if emails:
                email = emails[0].lower().strip()
                if email in self.email_index:
                    # 比较质量，保留更好的
                    existing = self.email_index[email][0]
                    if contact['_quality_score']['total_score'] <= existing['_quality_score']['total_score']:
                        stats['email_duplicates'] += 1
                        continue
                    else:
                        # 替换为更好的
                        deduped.remove(existing)
                        stats['removed_count'] += 1

            # 检查电话重复
            phones = contact.get('phones', [])
            if phones:
                phone = self._normalize_phone(phones[0])
                if phone in self.phone_index:
                    existing = self.phone_index[phone][0]
                    if contact['_quality_score']['total_score'] <= existing['_quality_score']['total_score']:
                        stats['phone_duplicates'] += 1
                        continue
                    else:
                        deduped.remove(existing)
                        stats['removed_count'] += 1

            # 添加到去重结果
            deduped.append(contact)
            self.seen_hashes.add(contact_hash)

            # 更新索引
            if emails:
                self.email_index[emails[0].lower().strip()] = [contact]
            if phones:
                self.phone_index[self._normalize_phone(phones[0])] = [contact]

        stats['removed_count'] = stats['original_count'] - len(deduped)

        self.logger.info(f"去重完成: 原始 {stats['original_count']} -> 去重后 {len(deduped)}")

        return deduped, stats

    def _calculate_hash(self, contact: Dict[str, Any]) -> str:
        """计算联系人哈希值"""
        # 使用邮箱+电话+公司创建唯一标识
        key_parts = []

        emails = contact.get('emails', [])
        if emails:
            key_parts.append(emails[0].lower().strip())

        phones = contact.get('phones', [])
        if phones:
            key_parts.append(self._normalize_phone(phones[0]))

        companies = contact.get('companies', [])
        if companies:
            key_parts.append(companies[0].strip())

        if not key_parts:
            # 如果都没有，使用标题和链接
            title = contact.get('title', '')[:50]
            link = contact.get('link', '')
            key_parts = [title, link]

        key_text = '|'.join(key_parts)
        return hashlib.md5(key_text.encode('utf-8')).hexdigest()[:16]

    def _normalize_phone(self, phone: str) -> str:
        """标准化电话号码"""
        # 移除所有非数字字符
        phone = re.sub(r'\D', '', phone)

        # 如果是手机号，保留11位
        if len(phone) == 11 and phone.startswith('1'):
            return phone

        # 如果是固话，保留区号和号码
        if len(phone) >= 7:
            return phone[-10:]  # 保留最后10位

        return phone


class TieredExporter:
    """分层导出器"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.export_dir = Path("data") / "exports" / "contacts"
        self.export_dir.mkdir(parents=True, exist_ok=True)

        self.scorer = QualityScorer()
        self.deduplicator = ContactDeduplicator()

    def export_contacts(self, contacts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分层导出联系人

        Returns:
            Dict: 导出结果统计
        """
        if not contacts:
            self.logger.warning("没有联系人数据可导出")
            return {'total': 0, 'tiers': {}}

        self.logger.info(f"开始分层导出，共 {len(contacts)} 条联系人")

        # 1. 质量评分
        scored_contacts = []
        for contact in contacts:
            score = self.scorer.score_contact(contact)
            contact['_quality_score'] = asdict(score)
            scored_contacts.append(contact)

        # 2. 去重
        deduped_contacts, dedup_stats = self.deduplicator.deduplicate_contacts(scored_contacts)

        # 3. 分层导出
        export_results = {}

        # 原始数据层
        if settings.get('export.tiers.raw.enabled', True):
            raw_path = self._export_raw_tier(scored_contacts)
            export_results['raw'] = {
                'path': raw_path,
                'count': len(scored_contacts)
            }

        # 清洁数据层
        if settings.get('export.tiers.clean.enabled', True):
            clean_path = self._export_clean_tier(deduped_contacts)
            export_results['clean'] = {
                'path': clean_path,
                'count': len(deduped_contacts)
            }

        # 高级数据层
        if settings.get('export.tiers.premium.enabled', True):
            premium_path = self._export_premium_tier(deduped_contacts)
            export_results['premium'] = {
                'path': premium_path,
                'count': self._count_premium_contacts(deduped_contacts)
            }

        # 4. 可选的Excel/CSV导出
        if settings.get('export.auto_excel', False):
            self._export_excel_fallback(deduped_contacts)

        if settings.get('export.auto_csv', False):
            self._export_csv_fallback(deduped_contacts)

        # 5. 生成质量报告
        report_path = self._generate_quality_report(scored_contacts, deduped_contacts, export_results)

        results = {
            'total': len(contacts),
            'deduped': len(deduped_contacts),
            'dedup_stats': dedup_stats,
            'tiers': export_results,
            'quality_report': report_path
        }

        self.logger.info(f"分层导出完成: {results}")
        return results

    def _export_raw_tier(self, contacts: List[Dict[str, Any]]) -> str:
        """导出原始数据层"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = settings.get('export.tiers.raw.filename', 'contacts_raw_{timestamp}.json')
        filename = filename.format(timestamp=timestamp)
        filepath = self.export_dir / filename

        raw_data = {
            'tier': 'raw',
            'description': settings.get('export.tiers.raw.description', '原始数据 - 所有提取的联系人信息'),
            'export_time': datetime.now().isoformat(),
            'total_count': len(contacts),
            'contacts': contacts
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(raw_data, f, ensure_ascii=False, indent=2)

        self.logger.info(f"原始数据层导出完成: {filepath}")
        return str(filepath)

    def _export_clean_tier(self, contacts: List[Dict[str, Any]]) -> str:
        """导出清洁数据层"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = settings.get('export.tiers.clean.filename', 'contacts_clean_{timestamp}.json')
        filename = filename.format(timestamp=timestamp)
        filepath = self.export_dir / filename

        # 应用清洁层过滤条件
        min_confidence = settings.get('export.tiers.clean.min_confidence', 0.3)
        require_email = settings.get('export.tiers.clean.require_email', True)

        clean_contacts = []
        for contact in contacts:
            score = contact.get('_quality_score', {})

            # 置信度过滤
            if score.get('total_score', 0) < min_confidence:
                continue

            # 邮箱要求
            if require_email and not contact.get('emails'):
                continue

            clean_contacts.append(contact)

        clean_data = {
            'tier': 'clean',
            'description': settings.get('export.tiers.clean.description', '清洁数据 - 去重并验证过的联系人'),
            'export_time': datetime.now().isoformat(),
            'filter_criteria': {
                'min_confidence': min_confidence,
                'require_email': require_email
            },
            'total_count': len(clean_contacts),
            'contacts': clean_contacts
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(clean_data, f, ensure_ascii=False, indent=2)

        self.logger.info(f"清洁数据层导出完成: {filepath} ({len(clean_contacts)} 条)")
        return str(filepath)

    def _export_premium_tier(self, contacts: List[Dict[str, Any]]) -> str:
        """导出高级数据层"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = settings.get('export.tiers.premium.filename', 'contacts_premium_{timestamp}.json')
        filename = filename.format(timestamp=timestamp)
        filepath = self.export_dir / filename

        # 应用高级层过滤条件
        min_confidence = settings.get('export.tiers.premium.min_confidence', 0.7)
        require_email = settings.get('export.tiers.premium.require_email', True)
        require_phone = settings.get('export.tiers.premium.require_phone', False)
        require_company = settings.get('export.tiers.premium.require_company', True)

        premium_contacts = []
        for contact in contacts:
            score = contact.get('_quality_score', {})

            # 置信度过滤
            if score.get('total_score', 0) < min_confidence:
                continue

            # 必需字段检查
            if require_email and not contact.get('emails'):
                continue
            if require_phone and not contact.get('phones'):
                continue
            if require_company and not contact.get('companies'):
                continue

            premium_contacts.append(contact)

        premium_data = {
            'tier': 'premium',
            'description': settings.get('export.tiers.premium.description', '高级数据 - 高质量完整联系人信息'),
            'export_time': datetime.now().isoformat(),
            'filter_criteria': {
                'min_confidence': min_confidence,
                'require_email': require_email,
                'require_phone': require_phone,
                'require_company': require_company
            },
            'total_count': len(premium_contacts),
            'contacts': premium_contacts
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(premium_data, f, ensure_ascii=False, indent=2)

        self.logger.info(f"高级数据层导出完成: {filepath} ({len(premium_contacts)} 条)")
        return str(filepath)

    def _count_premium_contacts(self, contacts: List[Dict[str, Any]]) -> int:
        """计算高级联系人数量（用于统计）"""
        min_confidence = settings.get('export.tiers.premium.min_confidence', 0.7)
        require_email = settings.get('export.tiers.premium.require_email', True)
        require_phone = settings.get('export.tiers.premium.require_phone', False)
        require_company = settings.get('export.tiers.premium.require_company', True)

        count = 0
        for contact in contacts:
            score = contact.get('_quality_score', {})

            if score.get('total_score', 0) >= min_confidence:
                if (not require_email or contact.get('emails')) and \
                   (not require_phone or contact.get('phones')) and \
                   (not require_company or contact.get('companies')):
                    count += 1

        return count

    def _export_excel_fallback(self, contacts: List[Dict[str, Any]]):
        """Excel导出降级方案"""
        try:
            import pandas as pd
            import openpyxl

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"contacts_fallback_{timestamp}.xlsx"
            filepath = self.export_dir / filename

            # 展开数据为表格
            rows = []
            for contact in contacts:
                base = {
                    'ID': contact.get('id', ''),
                    '标题': contact.get('title', ''),
                    '来源': contact.get('source', ''),
                    '质量评分': contact.get('_quality_score', {}).get('total_score', 0),
                    '置信度': contact.get('_quality_score', {}).get('confidence_level', ''),
                    '公司': ', '.join(contact.get('companies', [])),
                    '姓名': ', '.join(contact.get('names', [])),
                    '邮箱': ', '.join(contact.get('emails', [])),
                    '电话': ', '.join(contact.get('phones', [])),
                    '地址': ', '.join(contact.get('addresses', []))
                }
                rows.append(base)

            df = pd.DataFrame(rows)
            df.to_excel(filepath, index=False, engine='openpyxl')

            self.logger.info(f"Excel降级导出完成: {filepath}")

        except ImportError:
            self.logger.warning("pandas或openpyxl未安装，跳过Excel导出")
        except Exception as e:
            self.logger.error(f"Excel导出失败: {e}")

    def _export_csv_fallback(self, contacts: List[Dict[str, Any]]):
        """CSV导出降级方案"""
        try:
            import csv

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"contacts_fallback_{timestamp}.csv"
            filepath = self.export_dir / filename

            with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)

                # 写入表头
                writer.writerow([
                    'ID', '标题', '来源', '质量评分', '置信度',
                    '公司', '姓名', '邮箱', '电话', '地址'
                ])

                # 写入数据
                for contact in contacts:
                    score = contact.get('_quality_score', {})
                    writer.writerow([
                        contact.get('id', ''),
                        contact.get('title', ''),
                        contact.get('source', ''),
                        score.get('total_score', 0),
                        score.get('confidence_level', ''),
                        ', '.join(contact.get('companies', [])),
                        ', '.join(contact.get('names', [])),
                        ', '.join(contact.get('emails', [])),
                        ', '.join(contact.get('phones', [])),
                        ', '.join(contact.get('addresses', []))
                    ])

            self.logger.info(f"CSV降级导出完成: {filepath}")

        except Exception as e:
            self.logger.error(f"CSV导出失败: {e}")

    def _generate_quality_report(self, original: List[Dict], deduped: List[Dict],
                                export_results: Dict) -> str:
        """生成质量报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"quality_report_{timestamp}.json"
        filepath = self.export_dir / filename

        # 统计信息
        stats = {
            'original_count': len(original),
            'deduped_count': len(deduped),
            'dedup_rate': round((len(original) - len(deduped)) / len(original) * 100, 2) if original else 0
        }

        # 质量分布
        quality_dist = {'high': 0, 'medium': 0, 'low': 0}
        score_sum = 0
        for contact in deduped:
            score = contact.get('_quality_score', {})
            level = score.get('confidence_level', 'low')
            quality_dist[level] += 1
            score_sum += score.get('total_score', 0)

        # 字段完整性
        field_completeness = {}
        fields = ['emails', 'phones', 'companies', 'names']
        for field in fields:
            count = sum(1 for c in deduped if c.get(field))
            field_completeness[field] = round(count / len(deduped) * 100, 2) if deduped else 0

        report = {
            'report_time': datetime.now().isoformat(),
            'statistics': stats,
            'quality_distribution': quality_dist,
            'average_score': round(score_sum / len(deduped), 3) if deduped else 0,
            'field_completeness': field_completeness,
            'export_summary': export_results,
            'settings': {
                'weights': self.scorer.weights,
                'tier_configs': {
                    'clean': {
                        'enabled': settings.get('export.tiers.clean.enabled', True),
                        'min_confidence': settings.get('export.tiers.clean.min_confidence', 0.3),
                        'require_email': settings.get('export.tiers.clean.require_email', True)
                    },
                    'premium': {
                        'enabled': settings.get('export.tiers.premium.enabled', True),
                        'min_confidence': settings.get('export.tiers.premium.min_confidence', 0.7),
                        'requirements': {
                            'email': settings.get('export.tiers.premium.require_email', True),
                            'phone': settings.get('export.tiers.premium.require_phone', False),
                            'company': settings.get('export.tiers.premium.require_company', True)
                        }
                    }
                }
            }
        }

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        self.logger.info(f"质量报告生成完成: {filepath}")
        return str(filepath)
