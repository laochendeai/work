# 联系人信息提取规则和正则表达式文档

## 目录
1. [提取规则概述](#提取规则概述)
2. [正则表达式库](#正则表达式库)
3. [智能提取算法](#智能提取算法)
4. [数据验证和清洗](#数据验证和清洗)
5. [机器学习增强](#机器学习增强)
6. [性能优化](#性能优化)
7. [错误处理和调试](#错误处理和调试)

## 提取规则概述

### 1. 信息分类体系

#### 核心信息类型
```python
INFORMATION_TYPES = {
    # 个人联系信息
    'personal_contact': {
        'name': '姓名',
        'phone': '电话号码',
        'email': '电子邮箱',
        'position': '职位',
        'department': '部门'
    },

    # 组织信息
    'organization': {
        'company_name': '公司名称',
        'organization_type': '机构类型',
        'address': '地址',
        'industry': '行业'
    },

    # 项目信息
    'project': {
        'project_name': '项目名称',
        'budget': '项目预算',
        'deadline': '截止时间',
        'requirements': '技术要求'
    }
}
```

#### 信息可信度等级
```python
CONFIDENCE_LEVELS = {
    'high': 0.9,      # 高置信度：明确匹配，上下文确认
    'medium': 0.7,    # 中等置信度：格式匹配，基本确认
    'low': 0.5,       # 低置信度：疑似匹配，需要验证
    'very_low': 0.3   # 极低置信度：可能误匹配，谨慎使用
}
```

### 2. 上下文分析框架

#### 关键词上下文
```python
CONTACT_CONTEXT_KEYWORDS = {
    'name': ['联系人', '负责人', '项目经理', '技术负责人', '姓名'],
    'phone': ['电话', '手机', '联系电话', '联系方式', 'Tel'],
    'email': ['邮箱', '邮件', 'Email', 'E-mail', '电子邮箱'],
    'position': ['职位', '岗位', '职务', '职称'],
    'department': ['部门', '处室', '科室', '单位'],
    'company': ['单位', '公司', '机构', '组织'],
    'budget': ['预算', '金额', '费用', '造价', '投资'],
    'deadline': ['截止时间', '完成时间', '工期', '交付时间']
}
```

#### 位置权重系统
```python
def calculate_position_weight(text, position, text_length):
    """计算位置权重"""
    relative_position = position / text_length

    if relative_position < 0.3:  # 前部区域
        return 1.2
    elif relative_position < 0.7:  # 中部区域
        return 1.0
    else:  # 后部区域
        return 0.8
```

## 正则表达式库

### 1. 联系人信息提取

#### 姓名提取正则
```python
import re

NAME_PATTERNS = {
    # 中国姓名（2-4个汉字）
    'chinese_name': [
        r'[王李张刘陈杨黄赵吴周徐孙马朱胡郭何高林罗郑梁谢宋唐许韩冯][一-龥]{1,3}',
        r'[王李张刘陈杨黄赵吴周徐孙马朱胡郭何高林罗郑梁谢宋唐许韩冯][一-龥]',
    ],

    # 外文姓名
    'foreign_name': [
        r'[A-Z][a-z]+\s+[A-Z][a-z]+',
        r'[A-Z]\.\s*[A-Z][a-z]+',
        r'Mr\.\s*[A-Z][a-z]+',
        r'Ms\.\s*[A-Z][a-z]+'
    ],

    # 职位+姓名组合
    'name_with_title': [
        r'(院长|处长|科长|主任|经理|总监|主管|教授|博士|硕士)[：:\s]*([王李张刘陈杨黄赵吴周徐孙马朱胡郭何高林罗郑梁谢宋唐许韩冯][一-龥]{2,4})',
        r'([王李张刘陈杨黄赵吴周徐孙马朱胡郭何高林罗郑梁谢宋唐许韩冯][一-龥]{2,4})\s*(院长|处长|科长|主任|经理|总监|主管|教授)',
    ]
}

def extract_names(text):
    """提取姓名信息"""
    names = []

    for pattern_type, patterns in NAME_PATTERNS.items():
        for pattern in patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                # 提取姓名部分
                name = match.group(2) if match.groups() else match.group()

                # 验证姓名有效性
                if validate_chinese_name(name):
                    names.append({
                        'name': name,
                        'pattern_type': pattern_type,
                        'position': match.span(),
                        'confidence': calculate_name_confidence(name, text, match.span())
                    })

    return names
```

#### 电话号码提取正则
```python
PHONE_PATTERNS = {
    # 中国手机号
    'mobile_phone': [
        r'1[3-9]\d{9}',
        r'\+86\s*1[3-9]\d{9}',
        r'86[-\s]*1[3-9]\d{9}'
    ],

    # 中国固定电话
    'landline': [
        r'0\d{2,3}[-\s]?\d{7,8}',
        r'\d{3,4}[-\s]?\d{7,8}',
        r'400[-\s]?\d{3}[-\s]?\d{4}',  # 400号码
        r'800[-\s]?\d{3}[-\s]?\d{4}'   # 800号码
    ],

    # 带分隔符的号码
    'formatted_phone': [
        r'(\d{3})[-\s]*(\d{4})[-\s]*(\d{4})',  # 3-4-4格式
        r'(\d{4})[-\s]*(\d{4})[-\s]*(\d{4})',  # 4-4-4格式
    ]
}

def extract_phones(text):
    """提取电话号码"""
    phones = []

    for phone_type, patterns in PHONE_PATTERNS.items():
        for pattern in patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                raw_phone = match.group()
                clean_phone = re.sub(r'[^\d+]', '', raw_phone)

                if validate_phone_number(clean_phone, phone_type):
                    phones.append({
                        'phone': clean_phone,
                        'original': raw_phone,
                        'type': phone_type,
                        'position': match.span(),
                        'confidence': calculate_phone_confidence(text, match.span())
                    })

    return phones
```

#### 邮箱地址提取正则
```python
EMAIL_PATTERNS = {
    # 标准邮箱格式
    'standard_email': [
        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.(com|cn|org|net|gov|edu|cn\.com)',
    ],

    # 特殊域名邮箱
    'special_domain': [
        r'[a-zA-Z0-9._%+-]+@(qq|163|126|sina|gmail|outlook|hotmail)\.com',
        r'[a-zA-Z0-9._%+-]+@(edu|gov|org)\.cn',
    ],

    # 企业邮箱格式
    'enterprise_email': [
        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.(com\.cn|net\.cn|org\.cn)',
    ]
}

def extract_emails(text):
    """提取邮箱地址"""
    emails = []

    for email_type, patterns in EMAIL_PATTERNS.items():
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                email = match.group().lower()

                if validate_email_format(email):
                    emails.append({
                        'email': email,
                        'type': email_type,
                        'position': match.span(),
                        'confidence': calculate_email_confidence(text, match.span())
                    })

    return emails
```

### 2. 组织信息提取

#### 公司/机构名称提取
```python
ORGANIZATION_PATTERNS = {
    # 政府机构
    'government': [
        r'[一-龥]+(人民政府|人民政府办公厅|人民政府办公室)',
        r'[一-龥]+(局|委|署|厅|处|科)',
        r'[一-龥]+(委员会|领导小组)',
    ],

    # 教育机构
    'education': [
        r'[一-龥]+(大学|学院|学校|校区)',
        r'[一-龥]+(研究院|研究所)',
        r'[一-龥]+(附属中学|附属小学)',
    ],

    # 企业公司
    'enterprise': [
        r'[一-龥]+(有限公司|有限责任公司|集团)',
        r'[一-龥]+(股份公司|股份有限公司)',
        r'[一-龥]+(科技|技术|工程|建设|咨询)[一-龥]*(公司|集团)',
    ],

    # 事业单位
    'public_institution': [
        r'[一-龥]+(中心|站|所|院)',
        r'[一-龥]+(协会|学会|联合会)',
        r'[一-龥]+(基金会|慈善机构)',
    ]
}

def extract_organizations(text):
    """提取组织机构信息"""
    organizations = []

    for org_type, patterns in ORGANIZATION_PATTERNS.items():
        for pattern in patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                org_name = match.group()

                if validate_organization_name(org_name):
                    organizations.append({
                        'name': org_name,
                        'type': org_type,
                        'position': match.span(),
                        'confidence': calculate_org_confidence(text, match.span())
                    })

    return organizations
```

#### 部门职位信息提取
```python
DEPARTMENT_PATTERNS = {
    # 技术部门
    'technical': [
        r'(信息技术中心|网络中心|计算机中心|技术部)',
        r'(研发部|工程部|技术支持部)',
        r'(运维部|系统部|数据部)',
    ],

    # 管理部门
    'administrative': [
        r'(办公室|行政部|人事部|财务部)',
        r'(采购部|招标办|审计部|法务部)',
        r'(后勤部|总务处|设备处)',
    ],

    # 学术部门
    'academic': [
        r'(教务处|科研处|研究生院)',
        r'(图书馆|信息中心|实验中心)',
        r'(院系|学院|研究所)',
    ]
}

POSITION_PATTERNS = {
    # 管理职位
    'management': [
        r'(院长|处长|科长|主任|经理|总监)',
        r'(主管|部长|司长|局长)',
    ],

    # 技术职位
    'technical': [
        r'(工程师|技术员|架构师|分析师)',
        r'(开发员|程序员|运维工程师)',
        r'(网络工程师|系统工程师)',
    ],

    # 学术职位
    'academic': [
        r'(教授|副教授|讲师|研究员)',
        r'(博士|硕士|导师)',
        r'(院士|专家|顾问)',
    ]
}
```

### 3. 项目信息提取

#### 预算金额提取
```python
BUDGET_PATTERNS = {
    # 数字+单位格式
    'amount_unit': [
        r'(\d+(?:\.\d+)?)\s*(万|千万|百万|千万|千|百)',
        r'(\d+(?:,\d{3})*(?:\.\d+)?)\s*元',
        r'人民币\s*(\d+(?:\.\d+)?)\s*万',
    ],

    # 预算关键词
    'budget_keywords': [
        r'预算[：:\s]*(\d+(?:\.\d+)?)\s*(万|千|百)',
        r'投资[：:\s]*(\d+(?:\.\d+)?)\s*(万|千|百)',
        r'金额[：:\s]*(\d+(?:\.\d+)?)\s*(万|千|百)',
        r'造价[：:\s]*(\d+(?:\.\d+)?)\s*(万|千|百)',
    ],

    # 区间预算
    'range_budget': [
        r'(\d+(?:\.\d+)?)\s*[-~至到]\s*(\d+(?:\.\d+)?)\s*(万|千|百)',
        r'(\d+(?:\.\d+)?)\s*(万|千|百)\s*[-~至到]\s*(\d+(?:\.\d+)?)\s*(万|千|百)',
    ]
}

def extract_budgets(text):
    """提取预算信息"""
    budgets = []

    for budget_type, patterns in BUDGET_PATTERNS.items():
        for pattern in patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                budget_info = match.group()

                # 解析金额数值
                amount = parse_budget_amount(budget_info)

                if amount and amount > 0:
                    budgets.append({
                        'amount': amount,
                        'original': budget_info,
                        'type': budget_type,
                        'position': match.span(),
                        'confidence': calculate_budget_confidence(text, match.span())
                    })

    return budgets

def parse_budget_amount(budget_text):
    """解析预算金额数值"""
    import re

    # 提取数字和单位
    number_match = re.search(r'(\d+(?:\.\d+)?)', budget_text)
    unit_match = re.search(r'(万|千|百|千万|百万)', budget_text)

    if not number_match:
        return None

    base_amount = float(number_match.group(1))

    if unit_match:
        unit = unit_match.group(1)
        multiplier = {
            '千': 1000,
            '万': 10000,
            '十万': 100000,
            '百万': 1000000,
            '千万': 10000000,
        }
        base_amount *= multiplier.get(unit, 1)

    return base_amount
```

#### 时间截止日期提取
```python
DEADLINE_PATTERNS = {
    # 完整日期格式
    'full_date': [
        r'(\d{4})[年-](\d{1,2})[月-](\d{1,2})[日]?',
        r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})',
    ],

    # 相对时间
    'relative_time': [
        r'(\d+)\s*(天|日|周|月|年)[后内]',
        r'(下|上)(周|月|年)',
        r'(本|当)(周|月|年)',
    ],

    # 截止时间关键词
    'deadline_keywords': [
        r'(截止|截至)[时间]*[：:\s]*(\d{4}[-年]\d{1,2}[-月]\d{1,2}[日]?)',
        r'(完成|交付|竣工)[时间]*[：:\s]*(\d{4}[-年]\d{1,2}[-月]\d{1,2}[日]?)',
        r'工期[：:\s]*(\d+)\s*(天|日|月)',
        r'(开标|投标)时间[：:\s]*(\d{4}[-年]\d{1,2}[-月]\d{1,2}[日]?)',
    ]
}

def extract_deadlines(text):
    """提取截止时间信息"""
    deadlines = []

    for deadline_type, patterns in DEADLINE_PATTERNS.items():
        for pattern in patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                deadline_text = match.group()

                # 解析具体日期
                date_obj = parse_deadline_date(deadline_text)

                if date_obj:
                    deadlines.append({
                        'date': date_obj,
                        'original': deadline_text,
                        'type': deadline_type,
                        'position': match.span(),
                        'confidence': calculate_deadline_confidence(text, match.span())
                    })

    return deadlines

def parse_deadline_date(date_text):
    """解析截止日期"""
    from datetime import datetime, timedelta

    try:
        # 尝试解析完整日期
        if re.search(r'\d{4}[-年]\d{1,2}[-月]\d{1,2}[日]?', date_text):
            # 标准化日期格式
            normalized = re.sub(r'[年月日]', '-', date_text).rstrip('-')
            date_obj = datetime.strptime(normalized, '%Y-%m-%d')
            return date_obj

        # 尝试解析相对时间
        relative_match = re.search(r'(\d+)\s*(天|日|周|月|年)[后内]', date_text)
        if relative_match:
            amount = int(relative_match.group(1))
            unit = relative_match.group(2)

            if unit in ['天', '日']:
                return datetime.now() + timedelta(days=amount)
            elif unit == '周':
                return datetime.now() + timedelta(weeks=amount)
            elif unit == '月':
                return datetime.now() + timedelta(days=amount * 30)
            elif unit == '年':
                return datetime.now() + timedelta(days=amount * 365)

    except:
        pass

    return None
```

## 智能提取算法

### 1. 上下文关联分析

#### 窗口上下文分析
```python
def analyze_context_window(text, position, window_size=100):
    """分析位置周围的上下文"""
    start = max(0, position - window_size)
    end = min(len(text), position + window_size)

    context = text[start:end]

    # 分析上下文关键词
    context_features = {}
    for field, keywords in CONTACT_CONTEXT_KEYWORDS.items():
        keyword_count = sum(1 for keyword in keywords if keyword in context)
        context_features[field] = keyword_count

    return context_features

def enhance_extraction_with_context(extracted_items, text):
    """使用上下文信息增强提取结果"""
    enhanced_items = []

    for item in extracted_items:
        context_features = analyze_context_window(text, item['position'][0])

        # 根据上下文调整置信度
        confidence_boost = 0
        if item['type'] in context_features and context_features[item['type']] > 0:
            confidence_boost = 0.2 * context_features[item['type']]

        item['confidence'] = min(1.0, item['confidence'] + confidence_boost)
        item['context_score'] = context_features

        enhanced_items.append(item)

    return enhanced_items
```

#### 关联性分析
```python
def find_related_items(items, max_distance=200):
    """查找相关的提取项"""
    related_groups = []

    for i, item1 in enumerate(items):
        group = [item1]

        for j, item2 in enumerate(items):
            if i != j and are_items_related(item1, item2, max_distance):
                group.append(item2)

        if len(group) > 1:
            related_groups.append(group)

    return related_groups

def are_items_related(item1, item2, max_distance):
    """判断两个提取项是否相关"""
    # 计算位置距离
    pos1_center = sum(item1['position']) / 2
    pos2_center = sum(item2['position']) / 2
    distance = abs(pos1_center - pos2_center)

    if distance > max_distance:
        return False

    # 检查类型相关性
    type_relations = {
        'name': ['phone', 'email', 'position', 'department'],
        'phone': ['name', 'email'],
        'email': ['name', 'phone'],
        'company': ['name', 'position', 'department'],
        'position': ['name', 'department', 'company'],
    }

    item1_type = item1.get('type', '')
    item2_type = item2.get('type', '')

    return item2_type in type_relations.get(item1_type, [])
```

### 2. 机器学习增强

#### 特征提取
```python
def extract_features(text, item):
    """提取特征用于机器学习模型"""
    features = {
        # 文本特征
        'item_length': len(str(item.get('value', ''))),
        'position_ratio': sum(item['position']) / (2 * len(text)),

        # 上下文特征
        'has_contact_keyword': has_contact_keywords(text, item['position']),
        'context_density': calculate_context_density(text, item['position']),

        # 格式特征
        'is_phone_number': is_valid_phone_format(str(item.get('value', ''))),
        'is_email_format': is_valid_email_format(str(item.get('value', ''))),
        'has_chinese_chars': has_chinese_characters(str(item.get('value', ''))),

        # 位置特征
        'is_in_first_quarter': is_in_text_region(text, item['position'], 0, 0.25),
        'is_in_header': is_near_text_start(text, item['position'], 500),
    }

    return features

def has_contact_keywords(text, position, window=150):
    """检查是否包含联系人关键词"""
    start = max(0, position[0] - window)
    end = min(len(text), position[1] + window)
    context = text[start:end]

    all_keywords = []
    for keywords in CONTACT_CONTEXT_KEYWORDS.values():
        all_keywords.extend(keywords)

    return any(keyword in context for keyword in all_keywords)
```

#### 置信度预测模型
```python
class ConfidencePredictor:
    def __init__(self):
        self.feature_weights = {
            'item_length': 0.1,
            'has_contact_keyword': 0.3,
            'context_density': 0.2,
            'is_valid_format': 0.25,
            'position_ratio': 0.15,
        }

    def predict_confidence(self, text, item):
        """预测提取项的置信度"""
        features = extract_features(text, item)

        confidence = 0.5  # 基础置信度

        # 线性加权
        for feature_name, weight in self.feature_weights.items():
            if feature_name in features:
                if features[feature_name]:
                    confidence += weight * features[feature_name]
                else:
                    confidence -= weight * 0.5

        # 应用非线性变换
        confidence = 1 / (1 + math.exp(-confidence * 2))

        return min(1.0, max(0.0, confidence))

# 使用示例
predictor = ConfidencePredictor()
enhanced_items = []
for item in extracted_items:
    item['ml_confidence'] = predictor.predict_confidence(text, item)
    enhanced_items.append(item)
```

## 数据验证和清洗

### 1. 数据质量检查

#### 姓名验证
```python
def validate_chinese_name(name):
    """验证中文名字有效性"""
    if not name or len(name) < 2 or len(name) > 4:
        return False

    # 检查是否全为汉字
    if not all('\u4e00' <= char <= '\u9fff' for char in name):
        return False

    # 检查是否包含常见姓氏
    common_surnames = ['王', '李', '张', '刘', '陈', '杨', '黄', '赵', '吴', '周']
    if name[0] not in common_surnames:
        # 不是常见姓氏，降低置信度但不完全排除
        return False

    # 排除明显不是姓名的词汇
    exclude_words = ['公司', '有限', '股份', '技术', '工程', '建设', '部门']
    if any(word in name for word in exclude_words):
        return False

    return True

def calculate_name_confidence(name, text, position):
    """计算姓名提取置信度"""
    base_confidence = 0.8 if validate_chinese_name(name) else 0.4

    # 检查上下文
    context_score = has_contact_keywords(text, position)

    # 检查位置权重
    position_weight = calculate_position_weight(text, position[0], len(text))

    confidence = base_confidence * (1 + context_score * 0.3) * position_weight
    return min(1.0, confidence)
```

#### 电话号码验证
```python
def validate_phone_number(phone, phone_type):
    """验证电话号码有效性"""
    phone = re.sub(r'[^\d+]', '', phone)

    if phone_type == 'mobile_phone':
        # 验证手机号
        return (
            len(phone) == 11 and
            phone.startswith('1') and
            phone[1] in '3456789'
        )

    elif phone_type == 'landline':
        # 验证固定电话
        if len(phone) == 11 and phone.startswith('0'):
            return True
        if len(phone) == 10 or len(phone) == 12:
            return True
        if phone.startswith('400') and len(phone) == 10:
            return True
        if phone.startswith('800') and len(phone) == 10:
            return True

    return False

def calculate_phone_confidence(text, position):
    """计算电话号码提取置信度"""
    # 检查格式正确性
    format_score = 0.9 if re.search(r'1[3-9]\d{9}', text[position[0]:position[1]]) else 0.6

    # 检查上下文
    context_score = has_contact_keywords(text, position)

    # 检查是否在联系人信息区域
    contact_area_score = is_in_contact_area(text, position)

    confidence = format_score * 0.6 + context_score * 0.3 + contact_area_score * 0.1
    return min(1.0, confidence)
```

#### 邮箱验证
```python
def validate_email_format(email):
    """验证邮箱格式"""
    import re

    # 基本格式检查
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False

    # 检查域名格式
    domain = email.split('@')[-1]
    if '.' not in domain:
        return False

    # 检查是否为常用邮箱域名
    common_domains = [
        'qq.com', '163.com', '126.com', 'sina.com', 'sohu.com',
        'gmail.com', 'outlook.com', 'hotmail.com', 'yahoo.com',
        'edu.cn', 'gov.cn', 'org.cn', 'net.cn'
    ]

    is_common_domain = any(domain.endswith(d) for d in common_domains)

    return is_common_domain or len(domain.split('.')) >= 2

def calculate_email_confidence(text, position):
    """计算邮箱提取置信度"""
    email_text = text[position[0]:position[1]]

    # 格式检查
    format_score = 0.9 if validate_email_format(email_text) else 0.5

    # 上下文检查
    context_score = has_contact_keywords(text, position)

    # 位置检查
    position_score = is_in_contact_area(text, position)

    confidence = format_score * 0.7 + context_score * 0.2 + position_score * 0.1
    return min(1.0, confidence)
```

### 2. 数据去重

#### 基于相似度的去重
```python
from difflib import SequenceMatcher

class DataDeduplicator:
    def __init__(self, similarity_threshold=0.8):
        self.similarity_threshold = similarity_threshold

    def deduplicate_items(self, items):
        """去重提取项"""
        unique_items = []

        for item in items:
            is_duplicate = False

            for unique_item in unique_items:
                if self.are_items_similar(item, unique_item):
                    # 保留置信度更高的项
                    if item.get('confidence', 0) > unique_item.get('confidence', 0):
                        unique_items.remove(unique_item)
                        unique_items.append(item)
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique_items.append(item)

        return unique_items

    def are_items_similar(self, item1, item2):
        """判断两个项是否相似"""
        if item1.get('type') != item2.get('type'):
            return False

        value1 = str(item1.get('value', ''))
        value2 = str(item2.get('value', ''))

        # 精确匹配
        if value1 == value2:
            return True

        # 相似度匹配
        similarity = SequenceMatcher(None, value1, value2).ratio()
        return similarity >= self.similarity_threshold
```

#### 联系人信息关联
```python
def group_related_contacts(items):
    """将相关的联系人信息分组"""
    contact_groups = []
    unassigned = items.copy()

    while unassigned:
        # 取第一个未分配的项作为组的核心
        core_item = unassigned.pop(0)
        current_group = [core_item]

        # 查找与核心项相关的其他项
        related_items = []
        for item in unassigned[:]:
            if is_contact_related(core_item, item):
                related_items.append(item)
                unassigned.remove(item)

        current_group.extend(related_items)
        contact_groups.append(current_group)

    return contact_groups

def is_contact_related(item1, item2):
    """判断两个联系人信息项是否相关"""
    # 检查类型相关性
    type_relations = {
        'name': ['phone', 'email', 'position', 'department'],
        'phone': ['name', 'email'],
        'email': ['name', 'phone'],
        'position': ['name', 'department', 'company'],
        'department': ['name', 'position', 'company'],
        'company': ['name', 'position', 'department'],
    }

    item1_type = item1.get('type', '')
    item2_type = item2.get('type', '')

    return item2_type in type_relations.get(item1_type, [])
```

## 性能优化

### 1. 正则表达式优化

#### 编译正则表达式
```python
import re

class CompiledPatterns:
    def __init__(self):
        # 预编译常用正则表达式
        self.phone_patterns = [re.compile(pattern) for pattern in PHONE_PATTERNS['mobile_phone']]
        self.email_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in EMAIL_PATTERNS['standard_email']]
        self.name_patterns = [re.compile(pattern) for pattern in NAME_PATTERNS['chinese_name']]

    def extract_phones(self, text):
        """使用预编译模式提取电话"""
        phones = []
        for pattern in self.phone_patterns:
            matches = pattern.finditer(text)
            for match in matches:
                phones.append({
                    'phone': match.group(),
                    'position': match.span(),
                    'pattern': pattern.pattern
                })
        return phones

# 全局编译模式实例
compiled_patterns = CompiledPatterns()
```

#### 缓存机制
```python
from functools import lru_cache
import hashlib

class ExtractionCache:
    def __init__(self, max_size=1000):
        self.cache = {}
        self.max_size = max_size

    def get_text_hash(self, text):
        """计算文本哈希"""
        return hashlib.md5(text.encode('utf-8')).hexdigest()

    def get_cached_result(self, text):
        """获取缓存结果"""
        text_hash = self.get_text_hash(text)
        return self.cache.get(text_hash)

    def cache_result(self, text, result):
        """缓存提取结果"""
        if len(self.cache) >= self.max_size:
            # 简单的LRU：删除最旧的一项
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]

        text_hash = self.get_text_hash(text)
        self.cache[text_hash] = result

# 使用缓存
extraction_cache = ExtractionCache()

def cached_extract_contacts(text):
    """带缓存的联系人提取"""
    # 检查缓存
    cached_result = extraction_cache.get_cached_result(text)
    if cached_result:
        return cached_result

    # 执行提取
    result = extract_all_contacts(text)

    # 缓存结果
    extraction_cache.cache_result(text, result)

    return result
```

### 2. 并行处理

#### 多线程提取
```python
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

class ParallelExtractor:
    def __init__(self, max_workers=4):
        self.max_workers = max_workers

    def extract_multiple_texts(self, texts):
        """并行提取多个文本"""
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self.extract_single_text, text): i
                for i, text in enumerate(texts)
            }

            results = [None] * len(texts)
            for future in as_completed(futures):
                index = futures[future]
                results[index] = future.result()

        return results

    def extract_single_text(self, text):
        """提取单个文本"""
        # 这里调用实际的提取逻辑
        return extract_all_contacts(text)
```

## 错误处理和调试

### 1. 错误恢复机制

#### 异常处理
```python
class RobustExtractor:
    def __init__(self):
        self.fallback_patterns = self._get_fallback_patterns()

    def safe_extract(self, text):
        """安全的提取函数，带有错误恢复"""
        try:
            # 主要提取逻辑
            result = self._main_extract(text)
            return result
        except Exception as e:
            print(f"主提取逻辑失败: {e}")

            try:
                # 备用提取逻辑
                result = self._fallback_extract(text)
                return result
            except Exception as e2:
                print(f"备用提取逻辑也失败: {e2}")

                # 最简单的提取
                return self._basic_extract(text)

    def _fallback_extract(self, text):
        """备用提取逻辑"""
        # 使用更简单、更宽松的模式
        result = {}

        for field, patterns in self.fallback_patterns.items():
            matches = []
            for pattern in patterns:
                try:
                    found = re.findall(pattern, text)
                    matches.extend(found)
                except:
                    continue
            result[field] = matches

        return result
```

### 2. 调试工具

#### 提取结果可视化
```python
class ExtractionDebugger:
    def __init__(self):
        pass

    def visualize_extraction(self, text, items):
        """可视化提取结果"""
        # 在文本中标记提取到的内容
        marked_text = list(text)

        # 按位置排序
        sorted_items = sorted(items, key=lambda x: x['position'][0])

        for item in sorted_items:
            start, end = item['position']
            item_type = item.get('type', 'unknown')

            # 在提取项前后添加标记
            marked_text.insert(start, f'[{item_type}:')
            marked_text.insert(end + 1, f']')

        return ''.join(marked_text)

    def debug_extraction(self, text, items):
        """调试提取过程"""
        print("=== 提取调试信息 ===")
        print(f"文本长度: {len(text)}")
        print(f"提取到 {len(items)} 项")

        for i, item in enumerate(items, 1):
            print(f"\n{i}. {item.get('type', 'unknown')}")
            print(f"   值: {item.get('value', '')}")
            print(f"   位置: {item.get('position')}")
            print(f"   置信度: {item.get('confidence', 0):.2f}")

            # 显示上下文
            start, end = item['position']
            context_start = max(0, start - 20)
            context_end = min(len(text), end + 20)
            context = text[context_start:context_end]
            print(f"   上下文: ...{context}...")

# 使用示例
debugger = ExtractionDebugger()
marked_text = debugger.visualize_extraction(text, extracted_items)
print(marked_text)
debugger.debug_extraction(text, extracted_items)
```

这份文档提供了全面的联系人信息提取规则和正则表达式库，包含了智能算法、机器学习增强、数据验证和性能优化等各个方面，为智能化设计营销自动化系统提供了强大的信息提取能力。