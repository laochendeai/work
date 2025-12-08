#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能公告过滤器
识别真正有价值的政府采购公告，过滤无用的询价、竞争性谈判等
"""

import re
import jieba
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

@dataclass
class AnnouncementValue:
    """公告价值评估"""
    is_valuable: bool = False
    value_score: float = 0.0
    announcement_type: str = ""
    contact_quality: str = ""
    procurement_stage: str = ""
    reasons: List[str] = None

    def __post_init__(self):
        if self.reasons is None:
            self.reasons = []

class IntelligentAnnouncementFilter:
    """智能公告过滤器"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._setup_filters()

    def _setup_filters(self):
        """设置过滤器规则"""

        # 高价值公告类型（我们要的）
        self.high_value_types = {
            '招标公告', '采购公告', '项目招标', '设备采购', '服务采购', '工程招标',
            '公开招标', '邀请招标', '单一来源采购', '竞争性磋商'
        }

        # 中等价值公告类型（可能有价值的）
        self.medium_value_types = {
            '中标公告', '成交公告', '结果公告', '合同公告'
        }

        # 低价值公告类型（要过滤掉的）
        self.low_value_types = {
            '询价公告', '询价通知', '询价结果', '竞争性谈判', '谈判公告',
            '更正公告', '澄清公告', '补充公告', '废标公告', '终止公告',
            '暂停公告', '延期公告', '答疑公告', '预公告', '意向公告'
        }

        # 高价值关键词
        self.high_value_keywords = {
            # 项目类型
            '建设', '工程', '设备', '系统', '软件', '服务', '采购', '招标',
            '信息化', '智能化', '数字化', '自动化', '医疗设备', '教学设备',
            '办公设备', '网络设备', '安防设备', '实验设备', '检测设备',

            # 规模指标
            '项目', '建设期', '合同', '预算', '资金', '投资',

            # 时间指标（表明是当前项目）
            '2025', '2026', '年度', '本期', '近期',
        }

        # 决策权关键词
        self.decision_keywords = {
            '采购人', '建设单位', '项目单位', '使用单位', '业主',
            '学校', '医院', '政府', '机关', '研究院', '大学',
            '公司', '企业', '机构', '部门'
        }

        # 联系方式关键词
        self.contact_keywords = {
            '联系人', '负责人', '项目经理', '采购人代表', '经办人',
            '电话', '手机', '邮箱', '邮箱地址', '联系方式',
            '地址', '办公地址'
        }

    def evaluate_announcement(self, title: str, content: str = "") -> AnnouncementValue:
        """评估公告价值"""

        evaluation = AnnouncementValue()
        title_lower = str(title).lower()
        content = str(content) if content else ""

        # 1. 判断公告类型
        evaluation.announcement_type = self._classify_announcement_type(title_lower)

        # 2. 计算基础价值分数
        evaluation.value_score = self._calculate_base_score(title_lower, content)

        # 3. 联系方式质量评估
        evaluation.contact_quality = self._assess_contact_quality(content)

        # 4. 采购阶段判断
        evaluation.procurement_stage = self._identify_procurement_stage(title_lower, content)

        # 5. 生成评估理由
        evaluation.reasons = self._generate_reasons(title, content, evaluation)

        # 6. 最终判断
        evaluation.is_valuable = self._make_final_decision(evaluation)

        return evaluation

    def _classify_announcement_type(self, title: str) -> str:
        """分类公告类型"""

        for gonggao_type in self.low_value_types:
            if gonggao_type in title:
                return f"低价值: {gonggao_type}"

        for gonggao_type in self.high_value_types:
            if gonggao_type in title:
                return f"高价值: {gonggao_type}"

        for gonggao_type in self.medium_value_types:
            if gonggao_type in title:
                return f"中等价值: {gonggao_type}"

        return "未分类"

    def _calculate_base_score(self, title: str, content: str) -> float:
        """计算基础价值分数"""
        score = 0.0

        # 公告类型分数
        for gonggao_type in self.high_value_types:
            if gonggao_type in title:
                score += 2.0
                break

        for gonggao_type in self.medium_value_types:
            if gonggao_type in title:
                score += 1.0
                break

        for gonggao_type in self.low_value_types:
            if gonggao_type in title:
                score -= 1.0
                break

        # 关键词分数
        keyword_count = sum(1 for keyword in self.high_value_keywords if keyword in title or keyword in content)
        score += keyword_count * 0.2

        # 决策机构分数
        decision_count = sum(1 for keyword in self.decision_keywords if keyword in title or keyword in content)
        score += decision_count * 0.3

        return max(0, score)

    def _assess_contact_quality(self, content: str) -> str:
        """评估联系方式质量"""
        if not content:
            return "无内容"

        # 提取电话
        phones = re.findall(r'1[3-9]\d{9}|\d{3,4}-\d{7,8}', content)

        # 提取邮箱
        emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', content)

        # 提取联系人
        contacts = re.findall(r'联系人[：:\s]*([^\s,，。]+)', content)

        if len(phones) >= 2 and len(emails) >= 1 and len(contacts) >= 1:
            return "优秀: 完整联系方式"
        elif len(phones) >= 1 and len(contacts) >= 1:
            return "良好: 有电话和联系人"
        elif len(phones) >= 1:
            return "一般: 仅有电话"
        elif len(contacts) >= 1:
            return "一般: 仅有联系人"
        else:
            return "差: 缺少联系方式"

    def _identify_procurement_stage(self, title: str, content: str) -> str:
        """识别采购阶段"""
        full_text = title + content

        if any(keyword in full_text for keyword in ['招标', '采购', '征集']):
            return "招标阶段"
        elif any(keyword in full_text for keyword in ['中标', '成交', '结果']):
            return "成交阶段"
        elif any(keyword in full_text for keyword in ['询价', '谈判']):
            return "询价阶段"
        elif any(keyword in full_text for keyword in ['更正', '澄清', '补充']):
            return "补充阶段"
        else:
            return "未知阶段"

    def _generate_reasons(self, title: str, content: str, evaluation: AnnouncementValue) -> List[str]:
        """生成评估理由"""
        reasons = []

        # 公告类型理由
        if "高价值" in evaluation.announcement_type:
            reasons.append(f"✅ 高价值公告类型: {evaluation.announcement_type}")
        elif "低价值" in evaluation.announcement_type:
            reasons.append(f"❌ 低价值公告类型: {evaluation.announcement_type}")

        # 联系方式理由
        if "优秀" in evaluation.contact_quality:
            reasons.append(f"✅ 联系方式完整: {evaluation.contact_quality}")
        elif "良好" in evaluation.contact_quality:
            reasons.append(f"✅ 联系方式可用: {evaluation.contact_quality}")
        elif "差" in evaluation.contact_quality:
            reasons.append(f"❌ 联系方式缺失: {evaluation.contact_quality}")

        # 采购阶段理由
        if evaluation.procurement_stage == "招标阶段":
            reasons.append("✅ 处于招标阶段，适合开发")
        elif evaluation.procurement_stage == "询价阶段":
            reasons.append("❌ 处于询价阶段，价值较低")

        # 分数理由
        if evaluation.value_score >= 3.0:
            reasons.append(f"✅ 综合评分高: {evaluation.value_score:.1f}")
        elif evaluation.value_score <= 0.5:
            reasons.append(f"❌ 综合评分低: {evaluation.value_score:.1f}")

        return reasons

    def _make_final_decision(self, evaluation: AnnouncementValue) -> bool:
        """做出最终决策"""

        # 一票否决的情况
        if "低价值" in evaluation.announcement_type:
            return False

        if "询价阶段" == evaluation.procurement_stage:
            return False

        if evaluation.value_score < 0.5:
            return False

        if "差: 缺少联系方式" == evaluation.contact_quality:
            return False

        # 推荐的情况
        if ("高价值" in evaluation.announcement_type and
            evaluation.value_score >= 2.0 and
            evaluation.contact_quality in ["优秀: 完整联系方式", "良好: 有电话和联系人"]):
            return True

        # 中等情况
        if evaluation.value_score >= 1.5 and evaluation.contact_quality != "差: 缺少联系方式":
            return True

        return False

    def filter_announcements(self, announcements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """批量过滤公告"""
        valuable_announcements = []

        for announcement in announcements:
            title = announcement.get('标题', announcement.get('title', ''))
            content = announcement.get('内容', announcement.get('content', ''))

            evaluation = self.evaluate_announcement(title, content)

            if evaluation.is_valuable:
                # 添加评估结果
                announcement['_evaluation'] = {
                    'value_score': evaluation.value_score,
                    'announcement_type': evaluation.announcement_type,
                    'contact_quality': evaluation.contact_quality,
                    'procurement_stage': evaluation.procurement_stage,
                    'reasons': evaluation.reasons
                }
                valuable_announcements.append(announcement)

        return valuable_announcements

    def get_statistics(self, announcements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """获取公告统计信息"""

        stats = {
            'total': len(announcements),
            'high_value': 0,
            'medium_value': 0,
            'low_value': 0,
            'valuable_count': 0,
            'with_contacts': 0,
            'distribution': {}
        }

        for announcement in announcements:
            title = announcement.get('标题', announcement.get('title', ''))
            content = announcement.get('内容', announcement.get('内容', ''))

            evaluation = self.evaluate_announcement(title, content)

            # 统计价值类型
            if "高价值" in evaluation.announcement_type:
                stats['high_value'] += 1
            elif "低价值" in evaluation.announcement_type:
                stats['low_value'] += 1
            else:
                stats['medium_value'] += 1

            # 统计有价值的
            if evaluation.is_valuable:
                stats['valuable_count'] += 1

            # 统计有联系方式的
            if evaluation.contact_quality not in ["无内容", "差: 缺少联系方式"]:
                stats['with_contacts'] += 1

        # 计算百分比
        if stats['total'] > 0:
            stats['valuable_percentage'] = stats['valuable_count'] / stats['total'] * 100
            stats['contact_percentage'] = stats['with_contacts'] / stats['total'] * 100
        else:
            stats['valuable_percentage'] = 0
            stats['contact_percentage'] = 0

        return stats