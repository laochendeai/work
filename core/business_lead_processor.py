#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
设计业务商机处理器
专门针对中标方的设计业务推广需求
识别刚刚获得项目的公司，提取联系方式，自动化推荐设计服务
"""

import re
import jieba
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class BusinessLead:
    """设计业务商机"""
    # 中标信息
    project_name: str = ""
    winning_company: str = ""
    procurement_amount: str = ""
    announcement_date: str = ""
    source_link: str = ""

    # 联系信息
    contact_name: str = ""
    contact_phone: str = ""
    contact_email: str = ""
    contact_position: str = ""

    # 项目评估
    design_relevance: float = 0.0  # 设计相关度 0-1
    project_scale: str = ""        # 项目规模
    urgency_level: str = ""        # 紧急程度
    follow_up_priority: float = 0.0  # 跟进优先级

    # 营销建议
    design_service_type: str = ""   # 推荐的设计服务类型
    marketing_angle: str = ""        # 营销切入点
    confidence_score: float = 0.0   # 信息可信度

class DesignBusinessLeadProcessor:
    """设计业务商机处理器"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._setup_patterns()

    def _setup_patterns(self):
        """设置提取模式"""

        # 高设计需求项目类型
        self.high_design_projects = {
            '建设', '工程', '建筑', '装修', '装饰', '改造', '翻新', '设计',
            '信息化', '智能化', '数字化', '自动化', '系统集成',
            '展馆', '展示', '博物馆', '文化馆', '科技馆', '图书馆',
            '医院', '学校', '办公楼', '商业体', '园区', '景区',
            '设备', '系统', '平台', '软件开发', '硬件设计'
        }

        # 设计相关关键词
        self.design_keywords = {
            '设计', '方案设计', '施工图设计', '概念设计', '规划设计',
            '建筑设计', '室内设计', '景观设计', '平面设计', '产品设计',
            'CAD', '效果图', '施工图', '设计方案', '设计院', '设计公司'
        }

        # 项目规模关键词
        self.scale_keywords = {
            '大型': '大型项目',
            '中型': '中型项目',
            '小型': '小型项目',
            '亿元': '大型项目',
            '万元': self._extract_amount_scale,
            '建设': '建设工程',
            '改造': '改造工程',
            '装修': '装修工程'
        }

        # 紧急程度关键词
        self.urgency_keywords = {
            '紧急': '紧急项目',
            '急需': '急需项目',
            '近期': '近期项目',
            '马上': '紧急项目',
            '立即': '紧急项目',
            '投标': '投标阶段',
            '招标': '招标阶段'
        }

    def extract_business_leads(self, announcements: List[Dict[str, Any]]) -> List[BusinessLead]:
        """从公告中提取设计业务商机"""
        leads = []

        for announcement in announcements:
            lead = self._extract_single_lead(announcement)
            if lead and self._is_valid_lead(lead):
                leads.append(lead)

        # 按优先级排序
        leads.sort(key=lambda x: x.follow_up_priority, reverse=True)
        return leads

    def _extract_single_lead(self, announcement: Dict[str, Any]) -> Optional[BusinessLead]:
        """从单个公告中提取商机"""
        title = announcement.get('标题', '')
        content = announcement.get('内容', announcement.get('联系人', ''))
        link = announcement.get('链接', '')

        # 只处理中标/成交公告
        if not any(keyword in title for keyword in ['中标', '成交', '结果']):
            return None

        lead = BusinessLead()

        # 提取项目信息
        lead.project_name = self._extract_project_name(title)
        lead.winning_company = self._extract_winning_company(content)
        lead.procurement_amount = self._extract_amount(content)
        lead.announcement_date = self._extract_date(announcement)
        lead.source_link = link

        # 提取联系信息
        lead.contact_name = self._extract_contact_name(content)
        lead.contact_phone = self._extract_contact_phone(content)
        lead.contact_email = self._extract_contact_email(content)
        lead.contact_position = self._extract_contact_position(content, lead.contact_name)

        # 项目评估
        lead.design_relevance = self._calculate_design_relevance(title, content)
        lead.project_scale = self._determine_project_scale(title, content, lead.procurement_amount)
        lead.urgency_level = self._determine_urgency_level(content)
        lead.follow_up_priority = self._calculate_follow_up_priority(lead)

        # 营销建议
        lead.design_service_type = self._recommend_design_service_type(title, content, lead.project_scale)
        lead.marketing_angle = self._generate_marketing_angle(lead)
        lead.confidence_score = self._calculate_confidence_score(lead)

        return lead

    def _extract_project_name(self, title: str) -> str:
        """提取项目名称"""
        # 移除公告类型标识
        project_name = re.sub(r'(.+?)(?:中标|成交|结果公告)', r'\1', title)
        # 移除项目编号等
        project_name = re.sub(r'[（(][^)）]+[)）]', '', project_name).strip()
        return project_name

    def _extract_winning_company(self, content: str) -> str:
        """提取中标公司名称"""
        patterns = [
            r'中标单位[：:\s]*([^\s,，。\n;；]+)',
            r'中标人[：:\s]*([^\s,，。\n;；]+)',
            r'成交供应商[：:\s]*([^\s,，。\n;；]+)',
            r'中标（成交）供应商[：:\s]*([^\s,，。\n;；]+)',
            r'成交单位[：:\s]*([^\s,，。\n;；]+)',
            r'供应商[：:\s]*([^\s,，。\n;；]+)'
        ]

        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                company = match.group(1).strip()
                # 清理公司名称
                company = re.sub(r'[,，。;；].*$', '', company)  # 移除后面的描述
                if len(company) > 3 and any(suffix in company for suffix in ['公司', '集团', '企业', '院', '所']):
                    return company

        # 尝试从内容中寻找包含"有限公司"的完整公司名
        company_pattern = r'([^，,。\n;；]*?(?:有限公司|有限责任公司|集团|企业|股份公司|院|所|大学)[^，,。\n;；]*)'
        companies = re.findall(company_pattern, content)

        # 过滤掉明显不是公司的内容
        for company in companies:
            company = company.strip()
            if len(company) > 5 and not any(word in company for word in ['代理机构', '采购单位', '招标单位', '地址', '联系方式', '项目']):
                return company

        return ""

    def _extract_amount(self, content: str) -> str:
        """提取采购金额"""
        patterns = [
            r'中标金额[：:\s]*([\d,，.]+万元)',
            r'成交金额[：:\s]*([\d,，.]+万元)',
            r'中标（成交）金额[：:\s]*([\d,，.]+万元)',
            r'合同金额[：:\s]*([\d,，.]+万元)',
            r'项目金额[：:\s]*([\d,，.]+万元)',
            r'预算[：:\s]*([\d,，.]+万元)'
        ]

        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                return match.group(1).strip()

        return ""

    def _extract_date(self, announcement: Dict[str, Any]) -> str:
        """提取公告日期"""
        # 尝试从爬取时间获取
        if '爬取时间' in announcement:
            return announcement['爬取时间']

        # 从标题中提取日期
        title = announcement.get('标题', '')
        date_match = re.search(r'(\d{4}年\d{1,2}月\d{1,2}日)', title)
        if date_match:
            return date_match.group(1)

        return datetime.now().strftime('%Y-%m-%d')

    def _extract_contact_name(self, content: str) -> str:
        """提取联系人姓名"""
        patterns = [
            r'联系人[：:\s]*([^\s,，。\n]{2,10})',
            r'负责人[：:\s]*([^\s,，。\n]{2,10})',
            r'项目经理[：:\s]*([^\s,，。\n]{2,10})',
            r'经办人[：:\s]*([^\s,，。\n]{2,10})'
        ]

        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                name = match.group(1).strip()
                # 清理姓名
                name = re.sub(r'[^\u4e00-\u9fa5]', '', name)
                if 2 <= len(name) <= 4:
                    return name

        return ""

    def _extract_contact_phone(self, content: str) -> str:
        """提取联系电话"""
        phones = re.findall(r'1[3-9]\d{9}|\d{3,4}-\d{7,8}', content)
        if phones:
            # 返回第一个有效的手机号（优先）
            for phone in phones:
                if phone.startswith('1'):
                    return phone
            return phones[0]  # 返回座机
        return ""

    def _extract_contact_email(self, content: str) -> str:
        """提取邮箱地址"""
        emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', content)
        if emails:
            return emails[0]
        return ""

    def _extract_contact_position(self, content: str, name: str) -> str:
        """推断联系人职位"""
        if not name:
            return ""

        # 在联系人附近寻找职位信息
        lines = content.split('\n')
        for line in lines:
            if name in line:
                if any(pos in line for pos in ['经理', '主管', '主任', '科长', '院长', '校长', '总经理']):
                    if '经理' in line:
                        return '经理'
                    elif '主管' in line:
                        return '主管'
                    elif '主任' in line:
                        return '主任'
                    elif '科长' in line:
                        return '科长'
                    elif '院长' in line:
                        return '院长'
                    elif '校长' in line:
                        return '校长'
                    elif '总经理' in line:
                        return '总经理'

        return ""

    def _calculate_design_relevance(self, title: str, content: str) -> float:
        """计算设计相关度"""
        full_text = title + content
        score = 0.0

        # 项目类型相关度
        for project_type in self.high_design_projects:
            if project_type in full_text:
                score += 0.3

        # 设计关键词相关度
        for keyword in self.design_keywords:
            if keyword in full_text:
                score += 0.2

        # 标题权重更高
        for keyword in self.design_keywords:
            if keyword in title:
                score += 0.1

        return min(score, 1.0)

    def _extract_amount_scale(self, amount_str: str) -> str:
        """从金额字符串判断项目规模"""
        if not amount_str:
            return "未知规模"

        try:
            # 提取数字
            numbers = re.findall(r'[\d.]+', amount_str)
            if numbers:
                amount = float(numbers[0])
                if amount >= 1000:  # 1000万以上
                    return "大型项目"
                elif amount >= 100:  # 100-1000万
                    return "中型项目"
                else:  # 100万以下
                    return "小型项目"
        except:
            pass

        return "未知规模"

    def _determine_project_scale(self, title: str, content: str, amount_str: str) -> str:
        """判断项目规模"""
        # 优先从金额判断
        if amount_str:
            return self._extract_amount_scale(amount_str)

        # 从关键词判断
        full_text = title + content
        if any(keyword in full_text for keyword in ['大型', '重点', '重大']):
            return "大型项目"
        elif any(keyword in full_text for keyword in ['中型', '一般']):
            return "中型项目"
        elif any(keyword in full_text for keyword in ['小型', '零星']):
            return "小型项目"

        return "中等项目"

    def _determine_urgency_level(self, content: str) -> str:
        """判断紧急程度"""
        for keyword in self.urgency_keywords:
            if keyword in content:
                return self.urgency_keywords[keyword]

        return "常规项目"

    def _calculate_follow_up_priority(self, lead: BusinessLead) -> float:
        """计算跟进优先级"""
        score = 0.0

        # 设计相关度 (40%)
        score += lead.design_relevance * 0.4

        # 项目规模 (25%)
        scale_scores = {"大型项目": 1.0, "中型项目": 0.7, "小型项目": 0.4, "未知规模": 0.2}
        score += scale_scores.get(lead.project_scale, 0.2) * 0.25

        # 紧急程度 (20%)
        urgency_scores = {"紧急项目": 1.0, "急需项目": 0.8, "近期项目": 0.6, "常规项目": 0.4}
        score += urgency_scores.get(lead.urgency_level, 0.4) * 0.2

        # 联系方式完整性 (15%)
        contact_score = 0.0
        if lead.contact_phone:
            contact_score += 0.6
        if lead.contact_email:
            contact_score += 0.4
        score += contact_score * 0.15

        return min(score, 1.0)

    def _recommend_design_service_type(self, title: str, content: str, project_scale: str) -> str:
        """推荐设计服务类型"""
        full_text = title + content

        if any(keyword in full_text for keyword in ['建筑', '建设', '工程']):
            return "建筑设计、工程制图"
        elif any(keyword in full_text for keyword in ['装修', '装饰', '室内']):
            return "室内设计、装修方案"
        elif any(keyword in full_text for keyword in ['信息化', '系统', '软件']):
            return "软件界面设计、系统设计"
        elif any(keyword in full_text for keyword in ['设备', '产品']):
            return "产品设计、工业设计"
        elif any(keyword in full_text for keyword in ['展览', '展示', '博物馆']):
            return "展馆设计、展示设计"
        elif project_scale == "大型项目":
            return "全套设计方案、规划设计"
        else:
            return "概念设计、方案设计"

    def _generate_marketing_angle(self, lead: BusinessLead) -> str:
        """生成营销切入点"""
        angles = []

        if lead.winning_company:
            angles.append(f"向{lead.winning_company}推荐专业设计服务")

        if lead.project_name:
            angles.append(f"针对{lead.project_name}项目提供设计支持")

        if lead.urgency_level == "紧急项目":
            angles.append("紧急设计需求，快速响应")
        elif lead.project_scale == "大型项目":
            angles.append("大型项目专业设计团队")

        service_type = lead.design_service_type
        if service_type:
            angles.append(f"专业{service_type}服务")

        return "; ".join(angles[:3])  # 最多3个切入点

    def _calculate_confidence_score(self, lead: BusinessLead) -> float:
        """计算信息可信度"""
        score = 0.0

        # 公司信息 (30%)
        if lead.winning_company:
            score += 0.3

        # 联系电话 (30%)
        if lead.contact_phone:
            score += 0.3

        # 项目信息 (20%)
        if lead.project_name and lead.project_name != "":
            score += 0.2

        # 联系人姓名 (10%)
        if lead.contact_name:
            score += 0.1

        # 邮箱 (10%)
        if lead.contact_email:
            score += 0.1

        return score

    def _is_valid_lead(self, lead: BusinessLead) -> bool:
        """验证是否为有效商机"""
        # 必须有中标公司
        if not lead.winning_company:
            return False

        # 必须有项目名称
        if not lead.project_name:
            return False

        # 必须有联系方式（电话或邮箱）
        if not lead.contact_phone and not lead.contact_email:
            return False

        # 设计相关度不能太低
        if lead.design_relevance < 0.1:
            return False

        return True

    def generate_follow_up_list(self, leads: List[BusinessLead]) -> List[Dict[str, Any]]:
        """生成跟进列表"""
        follow_up_list = []

        for lead in leads:
            item = {
                '优先级': f"{lead.follow_up_priority:.2f}",
                '项目名称': lead.project_name,
                '中标公司': lead.winning_company,
                '联系人': lead.contact_name,
                '职位': lead.contact_position,
                '电话': lead.contact_phone,
                '邮箱': lead.contact_email,
                '项目规模': lead.project_scale,
                '设计相关度': f"{lead.design_relevance:.2f}",
                '推荐服务': lead.design_service_type,
                '营销切入点': lead.marketing_angle,
                '公告日期': lead.announcement_date,
                '金额': lead.procurement_amount,
                '信息源': lead.source_link
            }
            follow_up_list.append(item)

        return follow_up_list