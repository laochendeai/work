# 邮件营销模板库

## 目录
1. [模板分类体系](#模板分类体系)
2. [基础模板结构](#基础模板结构)
3. [行业专用模板](#行业专用模板)
4. [个性化策略](#个性化策略)
5. [设计最佳实践](#设计最佳实践)
6. [模板管理系统](#模板管理系统)
7. [A/B测试指南](#A/B测试指南)

## 模板分类体系

### 1. 按目标客户类型分类

```python
TEMPLATE_CATEGORIES = {
    "government": {
        "name": "政府机构",
        "templates": [
            "government_procurement.html",
            "government_system_integration.html",
            "government_maintenance.html"
        ],
        "characteristics": {
            "tone": "正式、专业",
            "focus": "合规性、专业性、安全性",
            "format": "结构化、标准化"
        }
    },

    "education": {
        "name": "教育机构",
        "templates": [
            "university_campus.html",
            "education_technology.html",
            "school_infrastructure.html"
        ],
        "characteristics": {
            "tone": "专业、学术",
            "focus": "教育价值、技术先进性",
            "format": "图文并茂、案例丰富"
        }
    },

    "enterprise": {
        "name": "企业客户",
        "templates": [
            "enterprise_solution.html",
            "corporate_integration.html",
            "business_efficiency.html"
        ],
        "characteristics": {
            "tone": "商业导向",
            "focus": "ROI、效率提升",
            "format": "数据驱动、结果导向"
        }
    }
}
```

### 2. 按项目阶段分类

```python
PROJECT_PHASE_TEMPLATES = {
    "initial_contact": {
        "purpose": "初次联系",
        "templates": ["introduction_basic.html", "company_profile.html"],
        "call_to_action": "了解详情、获取资料"
    },

    "follow_up": {
        "purpose": "跟进邮件",
        "templates": ["follow_up_general.html", "follow_up_proposal.html"],
        "call_to_action": "预约会议、技术交流"
    },

    "proposal": {
        "purpose": "方案提供",
        "templates": ["technical_proposal.html", "solution_design.html"],
        "call_to_action": "审阅方案、反馈意见"
    },

    "closing": {
        "purpose": "促成合作",
        "templates": ["final_negotiation.html", "contract_signing.html"],
        "call_to_action": "确定合作、签订合同"
    }
}
```

## 基础模板结构

### 1. HTML邮件基础结构

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <title>{{ subject }}</title>
    <style type="text/css">
        /* 基础样式重置 */
        body, table, td, a { -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%; }
        table, td { mso-table-lspace: 0pt; mso-table-rspace: 0pt; }
        img { -ms-interpolation-mode: bicubic; border: 0; height: auto; line-height: 100%; outline: none; text-decoration: none; }
        body { height: 100% !important; margin: 0 !important; padding: 0 !important; width: 100% !important; }

        /* 客户端兼容性 */
        @media screen and (max-width: 600px) {
            .mobile-container { width: 100% !important; max-width: 100% !important; }
            .mobile-padding { padding: 20px !important; }
            .mobile-font-size { font-size: 16px !important; }
        }
    </style>
</head>
<body style="margin: 0 !important; padding: 0 !important; background-color: #f4f4f4;">

    <!-- 预标题文本 -->
    <div style="display: none; font-size: 1px; color: #fefefe; line-height: 1px; font-family: Arial, sans-serif; max-height: 0px; max-width: 0px; opacity: 0; overflow: hidden;">
        {{ preview_text }}
    </div>

    <!-- 主容器 -->
    <table border="0" cellpadding="0" cellspacing="0" width="100%">
        <tr>
            <td align="center" style="background-color: #f4f4f4; padding: 20px 0;">
                <!-- 邮件内容容器 -->
                <table border="0" cellpadding="0" cellspacing="0" width="600" class="mobile-container" style="background-color: #ffffff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">

                    {% block header %}{% endblock %}
                    {% block content %}{% endblock %}
                    {% block footer %}{% endblock %}

                </table>
            </td>
        </tr>
    </table>

</body>
</html>
```

### 2. 响应式设计原则

```css
/* 基础响应式样式 */
.responsive-image {
    width: 100%;
    max-width: 100%;
    height: auto;
}

.mobile-hide {
    display: block;
}

.mobile-show {
    display: none;
}

/* 移动端适配 */
@media screen and (max-width: 600px) {
    .mobile-hide {
        display: none !important;
    }

    .mobile-show {
        display: block !important;
    }

    .responsive-text {
        font-size: 16px !important;
        line-height: 24px !important;
    }

    .responsive-button {
        width: 100% !important;
        max-width: 280px !important;
    }
}
```

### 3. 模板变量系统

```python
class TemplateVariables:
    """模板变量定义和验证"""

    REQUIRED_VARS = {
        # 个人信息
        'contact_name': str,
        'contact_email': str,
        'contact_company': str,

        # 公司信息
        'sender_name': str,
        'sender_company': str,
        'sender_phone': str,
        'sender_email': str,

        # 项目信息
        'project_title': str,
        'project_budget': str,
        'project_deadline': str,
    }

    OPTIONAL_VARS = {
        'contact_position': str,
        'contact_department': str,
        'project_requirements': str,
        'company_address': str,
        'previous_projects': list,
        'technical_specifications': dict,
    }

    @classmethod
    def validate_variables(cls, variables):
        """验证模板变量"""
        missing_vars = []
        for var_name, var_type in cls.REQUIRED_VARS.items():
            if var_name not in variables:
                missing_vars.append(var_name)
            elif not isinstance(variables[var_name], var_type):
                missing_vars.append(f"{var_name} (类型错误)")

        return missing_vars
```

## 行业专用模板

### 1. 政府机构模板

#### 政府采购专用模板
```html
{% extends "base.html" %}

{% block header %}
<tr>
    <td style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); padding: 40px 30px; text-align: center; border-radius: 8px 8px 0 0;">
        <h1 style="color: #ffffff; font-size: 28px; margin: 0; font-weight: bold;">
            政府采购智能化解决方案
        </h1>
        <p style="color: #e8f4f8; font-size: 16px; margin: 15px 0 0 0;">
            资质齐全 | 经验丰富 | 服务可靠
        </p>
        {% if qualification_badge %}
        <div style="background: #e74c3c; color: white; padding: 8px 16px; border-radius: 4px; display: inline-block; margin-top: 15px;">
            政府采购合格供应商
        </div>
        {% endif %}
    </td>
</tr>
{% endblock %}

{% block content %}
<tr>
    <td style="padding: 40px 30px;">
        <!-- 问候语 -->
        <p style="font-size: 18px; color: #2c3e50; margin: 0 0 25px 0;">
            尊敬的{{ contact_name }}：
        </p>

        <!-- 项目引用 -->
        {% if project_title %}
        <table style="background: #ecf0f1; border-left: 5px solid #3498db; margin: 25px 0; border-radius: 0 8px 8px 0;">
            <tr>
                <td style="padding: 25px;">
                    <h3 style="color: #2c3e50; margin: 0 0 15px 0; font-size: 20px;">
                        关于项目《{{ project_title }}》
                    </h3>
                    <p style="color: #34495e; margin: 0; line-height: 1.6;">
                        我公司注意到贵单位发布的智能化建设项目，我公司在该领域具有丰富的实施经验和完善的技术方案，特此致函表达合作意向。
                    </p>
                </td>
            </tr>
        </table>
        {% endif %}

        <!-- 资质展示 -->
        <h3 style="color: #2c3e50; margin: 30px 0 20px 0; font-size: 22px;">
            公司资质与优势
        </h3>
        <table style="width: 100%; background: #f8f9fa; border-radius: 8px; margin: 20px 0;">
            <tr>
                <td style="padding: 25px;">
                    <table style="width: 100%;">
                        <tr>
                            <td style="width: 50%; padding: 10px; vertical-align: top;">
                                <p style="margin: 0 0 15px 0; color: #2c3e50;">
                                    <span style="color: #27ae60; font-weight: bold;">✓</span>
                                    电子与智能化工程专业承包资质
                                </p>
                                <p style="margin: 0 0 15px 0; color: #2c3e50;">
                                    <span style="color: #27ae60; font-weight: bold;">✓</span>
                                    安防工程企业资质
                                </p>
                                <p style="margin: 0; color: #2c3e50;">
                                    <span style="color: #27ae60; font-weight: bold;">✓</span>
                                    ISO9001质量管理体系认证
                                </p>
                            </td>
                            <td style="width: 50%; padding: 10px; vertical-align: top;">
                                <p style="margin: 0 0 15px 0; color: #2c3e50;">
                                    <span style="color: #27ae60; font-weight: bold;">✓</span>
                                    政府采购项目实施经验50+
                                </p>
                                <p style="margin: 0 0 15px 0; color: #2c3e50;">
                                    <span style="color: #27ae60; font-weight: bold;">✓</span>
                                    专业工程师团队30+
                                </p>
                                <p style="margin: 0; color: #2c3e50;">
                                    <span style="color: #27ae60; font-weight: bold;">✓</span>
                                    完善的售后服务体系
                                </p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>

        <!-- 成功案例 -->
        <h3 style="color: #2c3e50; margin: 30px 0 20px 0; font-size: 22px;">
            政府项目经验
        </h3>
        <div style="background: #ffffff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 25px; margin: 20px 0;">
            <table style="width: 100%;">
                <tr>
                    <td style="width: 50%; padding: 15px; vertical-align: top; border-right: 1px solid #e0e0e0;">
                        <p style="margin: 0 0 10px 0; color: #2c3e50; font-weight: bold;">行政项目</p>
                        <ul style="margin: 0; padding-left: 20px; color: #34495e;">
                            <li>行政中心智能化系统建设</li>
                            <li>公安部门安防监控系统</li>
                            <li>政府机关会议系统改造</li>
                        </ul>
                    </td>
                    <td style="width: 50%; padding: 15px; vertical-align: top;">
                        <p style="margin: 0 0 10px 0; color: #2c3e50; font-weight: bold;">公共服务项目</p>
                        <ul style="margin: 0; padding-left: 20px; color: #34495e;">
                            <li>教育系统智慧校园建设</li>
                            <li>医疗机构智能化改造</li>
                            <li>交通枢纽智能化系统</li>
                        </ul>
                    </td>
                </tr>
            </table>
        </div>

        <!-- 联系方式 -->
        <table style="background: #2c3e50; color: white; padding: 25px; border-radius: 8px; margin: 30px 0; width: 100%;">
            <tr>
                <td>
                    <h3 style="color: white; margin: 0 0 20px 0; font-size: 20px;">项目联系方式</h3>
                    <table style="width: 100%;">
                        <tr>
                            <td style="width: 50%; padding: 10px; vertical-align: top;">
                                <p style="margin: 0 0 10px 0;"><strong>项目负责人：</strong>{{ sender_name }}</p>
                                <p style="margin: 0 0 10px 0;"><strong>联系电话：</strong>{{ sender_phone }}</p>
                            </td>
                            <td style="width: 50%; padding: 10px; vertical-align: top;">
                                <p style="margin: 0 0 10px 0;"><strong>邮箱：</strong>{{ sender_email }}</p>
                                <p style="margin: 0;"><strong>技术支持：</strong>7×24小时响应</p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>

        <!-- 行动按钮 -->
        <table align="center" style="margin: 30px 0;">
            <tr>
                <td align="center">
                    <a href="#" style="background: #3498db; color: white; padding: 15px 35px; text-decoration: none; border-radius: 8px; display: inline-block; font-weight: bold; font-size: 16px;" class="responsive-button">
                        获取详细技术方案
                    </a>
                </td>
            </tr>
        </table>
    </td>
</tr>
{% endblock %}
```

### 2. 教育机构模板

#### 智慧校园模板
```html
{% extends "base.html" %}

{% block header %}
<tr>
    <td style="background: linear-gradient(135deg, #27ae60 0%, #16a085 100%); padding: 40px 30px; text-align: center; border-radius: 8px 8px 0 0;">
        <h1 style="color: #ffffff; font-size: 28px; margin: 0; font-weight: bold;">
            智慧校园整体解决方案
        </h1>
        <p style="color: #e8f8f5; font-size: 16px; margin: 15px 0 0 0;">
            教育信息化专家 | 校园智能化领导者
        </p>
        {% if education_badge %}
        <div style="background: #e67e22; color: white; padding: 8px 16px; border-radius: 4px; display: inline-block; margin-top: 15px;">
            教育信息化优质服务商
        </div>
        {% endif %}
    </td>
</tr>
{% endblock %}

{% block content %}
<tr>
    <td style="padding: 40px 30px;">
        <!-- 个性化问候 -->
        <p style="font-size: 18px; color: #2c3e50; margin: 0 0 25px 0;">
            尊敬的{{ contact_name }}：
        </p>

        <!-- 针对性内容 -->
        {% if contact_company %}
        <table style="background: #f0f8ff; border-left: 5px solid #27ae60; margin: 25px 0; border-radius: 0 8px 8px 0;">
            <tr>
                <td style="padding: 25px;">
                    <h3 style="color: #2c3e50; margin: 0 0 15px 0; font-size: 20px;">
                        针对{{ contact_company }}智慧校园建设
                    </h3>
                    <p style="color: #34495e; margin: 0; line-height: 1.6;">
                        我们了解到贵校在智慧校园建设方面的规划，我公司在教育信息化领域深耕多年，已成功为众多高校提供了完整的智慧校园解决方案。
                    </p>
                </td>
            </tr>
        </table>
        {% endif %}

        <!-- 智慧校园核心系统 -->
        <h3 style="color: #2c3e50; margin: 30px 0 20px 0; font-size: 22px;">
            智慧校园核心系统
        </h3>

        {% for system in campus_systems %}
        <table style="width: 100%; background: #ffffff; border: 1px solid #e8f5e8; border-radius: 8px; margin: 15px 0;">
            <tr>
                <td style="padding: 20px;">
                    <h4 style="color: #27ae60; margin: 0 0 15px 0; font-size: 18px;">
                        <span style="display: inline-block; width: 6px; height: 6px; background: #27ae60; border-radius: 50%; margin-right: 10px;"></span>
                        {{ system.name }}
                    </h4>
                    <p style="color: #34495e; margin: 0; line-height: 1.6;">
                        {{ system.description }}
                    </p>
                    {% if system.features %}
                    <ul style="margin: 15px 0 0 0; padding-left: 20px; color: #34495e;">
                        {% for feature in system.features %}
                        <li>{{ feature }}</li>
                        {% endfor %}
                    </ul>
                    {% endif %}
                </td>
            </tr>
        </table>
        {% endfor %}

        <!-- 教育行业优势 -->
        <h3 style="color: #2c3e50; margin: 30px 0 20px 0; font-size: 22px;">
            教育行业优势
        </h3>
        <table style="width: 100%; background: #fff9e6; border-radius: 8px; padding: 25px;">
            <tr>
                <td>
                    <table style="width: 100%;">
                        {% for advantage in education_advantages %}
                        <tr>
                            <td style="padding: 10px 0;">
                                <table style="width: 100%;">
                                    <tr>
                                        <td style="width: 30px; vertical-align: top;">
                                            <span style="background: #27ae60; color: white; width: 24px; height: 24px; border-radius: 50%; display: inline-block; text-align: center; line-height: 24px; font-weight: bold;">
                                                {{ loop.index }}
                                            </span>
                                        </td>
                                        <td style="vertical-align: top; padding-left: 15px;">
                                            <p style="margin: 0; color: #2c3e50; font-weight: bold;">{{ advantage.title }}</p>
                                            <p style="margin: 5px 0 0 0; color: #34495e;">{{ advantage.description }}</p>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                        {% endfor %}
                    </table>
                </td>
            </tr>
        </table>

        <!-- 成功案例展示 -->
        {% if campus_cases %}
        <h3 style="color: #2c3e50; margin: 30px 0 20px 0; font-size: 22px;">
            成功案例
        </h3>
        <table style="width: 100%;">
            <tr>
                {% for case in campus_cases %}
                <td style="width: 50%; padding: 10px; vertical-align: top;">
                    <table style="background: #f8f9fa; border-radius: 8px; padding: 20px; width: 100%; height: 100%;">
                        <tr>
                            <td>
                                <p style="margin: 0 0 10px 0; color: #27ae60; font-weight: bold; font-size: 16px;">
                                    {{ case.name }}
                                </p>
                                <p style="margin: 0 0 10px 0; color: #34495e; font-size: 14px;">
                                    {{ case.description }}
                                </p>
                                {% if case.highlight %}
                                <p style="margin: 0; color: #7f8c8d; font-size: 12px; font-style: italic;">
                                    <em>{{ case.highlight }}</em>
                                </p>
                                {% endif %}
                            </td>
                        </tr>
                    </table>
                </td>
                {% if loop.index % 2 == 0 %}
            </tr>
            <tr>
                {% endif %}
                {% endfor %}
            </tr>
        </table>
        {% endif %}

        <!-- 行动号召 -->
        <table align="center" style="margin: 40px 0;">
            <tr>
                <td align="center">
                    <table>
                        <tr>
                            <td style="padding: 10px;">
                                <a href="#" style="background: #27ae60; color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; display: inline-block; font-weight: bold; font-size: 16px;" class="responsive-button">
                                    预约技术交流
                                </a>
                            </td>
                            {% if demo_available %}
                            <td style="padding: 10px;">
                                <a href="#" style="background: transparent; color: #27ae60; padding: 15px 30px; text-decoration: none; border: 2px solid #27ae60; border-radius: 8px; display: inline-block; font-weight: bold; font-size: 16px;" class="responsive-button">
                                    观看演示
                                </a>
                            </td>
                            {% endif %}
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </td>
</tr>
{% endblock %}
```

### 3. 企业客户模板

#### 企业解决方案模板
```html
{% extends "base.html" %}

{% block header %}
<tr>
    <td style="background: linear-gradient(135deg, #3498db 0%, #2980b9 100%); padding: 40px 30px; text-align: center; border-radius: 8px 8px 0 0;">
        <h1 style="color: #ffffff; font-size: 28px; margin: 0; font-weight: bold;">
            企业智能化解决方案
        </h1>
        <p style="color: #e3f2fd; font-size: 16px; margin: 15px 0 0 0;">
            提升效率 | 降低成本 | 数字化转型
        </p>
        {% if roi_focus %}
        <div style="background: #f39c12; color: white; padding: 8px 16px; border-radius: 4px; display: inline-block; margin-top: 15px;">
            ROI导向的技术方案
        </div>
        {% endif %}
    </td>
</tr>
{% endblock %}

{% block content %}
<tr>
    <td style="padding: 40px 30px;">
        <!-- 商业导向问候 -->
        <p style="font-size: 18px; color: #2c3e50; margin: 0 0 25px 0;">
            尊敬的{{ contact_name }}：
        </p>

        <!-- 商业价值主张 -->
        <table style="background: #e8f4f8; border-left: 5px solid #3498db; margin: 25px 0; border-radius: 0 8px 8px 0;">
            <tr>
                <td style="padding: 25px;">
                    <h3 style="color: #2c3e50; margin: 0 0 15px 0; font-size: 20px;">
                        为{{ contact_company }}创造商业价值
                    </h3>
                    <p style="color: #34495e; margin: 0; line-height: 1.6;">
                        基于对贵公司业务需求的深入理解，我们提供定制化的智能化解决方案，专注于提升运营效率、降低运营成本，助力企业数字化转型。
                    </p>
                </td>
            </tr>
        </table>

        <!-- 价值主张矩阵 -->
        <h3 style="color: #2c3e50; margin: 30px 0 20px 0; font-size: 22px;">
            核心价值主张
        </h3>
        <table style="width: 100%; margin: 20px 0;">
            <tr>
                {% for value in business_values %}
                <td style="width: 33.33%; padding: 10px; vertical-align: top;">
                    <table style="background: #ffffff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 25px; text-align: center; width: 100%; height: 100%;">
                        <tr>
                            <td>
                                {% if value.icon %}
                                <div style="font-size: 36px; margin-bottom: 15px; color: #3498db;">
                                    {{ value.icon }}
                                </div>
                                {% endif %}
                                <h4 style="color: #2c3e50; margin: 0 0 15px 0; font-size: 18px; font-weight: bold;">
                                    {{ value.title }}
                                </h4>
                                <p style="color: #34495e; margin: 0; line-height: 1.6; font-size: 14px;">
                                    {{ value.description }}
                                </p>
                                {% if value.metric %}
                                <div style="background: #f8f9fa; padding: 10px; border-radius: 4px; margin-top: 15px;">
                                    <span style="color: #27ae60; font-weight: bold; font-size: 16px;">{{ value.metric }}</span>
                                    <br>
                                    <span style="color: #7f8c8d; font-size: 12px;">{{ value.metric_desc }}</span>
                                </div>
                                {% endif %}
                            </td>
                        </tr>
                    </table>
                </td>
                {% if loop.index % 3 == 0 %}
            </tr>
            <tr>
                {% endif %}
                {% endfor %}
            </tr>
        </table>

        <!-- ROI计算展示 -->
        {% if roi_calculation %}
        <h3 style="color: #2c3e50; margin: 30px 0 20px 0; font-size: 22px;">
            投资回报分析
        </h3>
        <table style="background: #f8f9fa; border-radius: 8px; padding: 25px; margin: 20px 0; width: 100%;">
            <tr>
                <td>
                    <table style="width: 100%;">
                        <tr>
                            <td style="width: 50%; padding: 15px; vertical-align: top; border-right: 1px solid #e0e0e0;">
                                <h4 style="color: #2c3e50; margin: 0 0 15px 0;">投资成本</h4>
                                <table style="width: 100%;">
                                    {% for cost in roi_calculation.costs %}
                                    <tr>
                                        <td style="padding: 8px 0;">{{ cost.item }}</td>
                                        <td style="padding: 8px 0; text-align: right; font-weight: bold;">{{ cost.amount }}</td>
                                    </tr>
                                    {% endfor %}
                                    <tr>
                                        <td style="padding: 10px 0; border-top: 2px solid #2c3e50; font-weight: bold;">总投资</td>
                                        <td style="padding: 10px 0; text-align: right; font-weight: bold; color: #e74c3c; border-top: 2px solid #2c3e50;">
                                            {{ roi_calculation.total_investment }}
                                        </td>
                                    </tr>
                                </table>
                            </td>
                            <td style="width: 50%; padding: 15px; vertical-align: top;">
                                <h4 style="color: #2c3e50; margin: 0 0 15px 0;">年度收益</h4>
                                <table style="width: 100%;">
                                    {% for benefit in roi_calculation.benefits %}
                                    <tr>
                                        <td style="padding: 8px 0;">{{ benefit.item }}</td>
                                        <td style="padding: 8px 0; text-align: right; font-weight: bold; color: #27ae60;">{{ benefit.amount }}</td>
                                    </tr>
                                    {% endfor %}
                                    <tr>
                                        <td style="padding: 10px 0; border-top: 2px solid #2c3e50; font-weight: bold;">年总收益</td>
                                        <td style="padding: 10px 0; text-align: right; font-weight: bold; color: #27ae60; border-top: 2px solid #2c3e50;">
                                            {{ roi_calculation.total_benefit }}
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                        <tr>
                            <td colspan="2" style="padding: 15px 0 0 0; text-align: center;">
                                <div style="background: #3498db; color: white; padding: 15px; border-radius: 8px; display: inline-block;">
                                    <span style="font-size: 18px; font-weight: bold;">ROI: {{ roi_calculation.roi_percentage }}</span>
                                    <br>
                                    <span style="font-size: 14px;">回收期: {{ roi_calculation.payback_period }}</span>
                                </div>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
        {% endif %}

        <!-- 客户证言 -->
        {% if testimonials %}
        <h3 style="color: #2c3e50; margin: 30px 0 20px 0; font-size: 22px;">
            客户成功案例
        </h3>
        {% for testimonial in testimonials %}
        <table style="background: #ffffff; border: 1px solid #e0e0e0; border-radius: 8px; padding: 25px; margin: 20px 0; width: 100%;">
            <tr>
                <td style="width: 80px; vertical-align: top; text-align: center;">
                    {% if testimonial.avatar %}
                    <img src="{{ testimonial.avatar }}" alt="{{ testimonial.name }}" style="width: 60px; height: 60px; border-radius: 50%;">
                    {% else %}
                    <div style="width: 60px; height: 60px; background: #3498db; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-size: 24px; font-weight: bold;">
                        {{ testimonial.name[0] }}
                    </div>
                    {% endif %}
                </td>
                <td style="vertical-align: top; padding-left: 20px;">
                    <blockquote style="margin: 0 0 15px 0; padding: 0 0 0 15px; border-left: 3px solid #3498db; color: #34495e; font-style: italic; line-height: 1.6;">
                        "{{ testimonial.quote }}"
                    </blockquote>
                    <p style="margin: 0; color: #2c3e50; font-weight: bold;">{{ testimonial.name }}</p>
                    <p style="margin: 5px 0 0 0; color: #7f8c8d; font-size: 14px;">{{ testimonial.position }} - {{ testimonial.company }}</p>
                </td>
            </tr>
        </table>
        {% endfor %}
        {% endif %}

        <!-- 商务行动号召 -->
        <table align="center" style="margin: 40px 0;">
            <tr>
                <td align="center">
                    <table>
                        <tr>
                            <td style="padding: 10px;">
                                <a href="#" style="background: #3498db; color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; display: inline-block; font-weight: bold; font-size: 16px;" class="responsive-button">
                                    预约商务洽谈
                                </a>
                            </td>
                            <td style="padding: 10px;">
                                <a href="#" style="background: transparent; color: #3498db; padding: 15px 30px; text-decoration: none; border: 2px solid #3498db; border-radius: 8px; display: inline-block; font-weight: bold; font-size: 16px;" class="responsive-button">
                                    下载案例研究
                                </a>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </td>
</tr>
{% endblock %}
```

## 个性化策略

### 1. 动态内容生成

```python
class EmailPersonalizer:
    """邮件个性化引擎"""

    def __init__(self):
        self.industry_contexts = {
            'government': {
                'focus_areas': ['安全性', '合规性', '可靠性', '长期服务'],
                'case_types': ['政务中心', '公安系统', '教育机构', '医疗机构'],
                'value_props': ['资质齐全', '经验丰富', '服务可靠', '技术先进']
            },
            'education': {
                'focus_areas': ['教育价值', '技术先进性', '师生体验', '管理效率'],
                'case_types': ['智慧校园', '数字化教室', '在线教学', '校园安全'],
                'value_props': ['教育理解', '技术创新', '用户体验', '集成能力']
            },
            'enterprise': {
                'focus_areas': ['ROI', '效率提升', '成本降低', '数字化转型'],
                'case_types': ['办公智能化', '生产自动化', '数据中台', '数字化营销'],
                'value_props': ['商业价值', '技术方案', '实施能力', '售后服务']
            }
        }

    def personalize_template(self, template_vars, industry_type):
        """个性化模板变量"""
        context = self.industry_contexts.get(industry_type, {})

        # 增强基础变量
        personalized_vars = template_vars.copy()

        # 添加行业特定内容
        personalized_vars.update({
            'industry_focus_areas': context.get('focus_areas', []),
            'relevant_case_types': context.get('case_types', []),
            'key_value_props': context.get('value_props', []),
            'industry_badge': self._get_industry_badge(industry_type),
            'greeting_style': self._get_greeting_style(industry_type),
            'call_to_action': self._get_call_to_action(industry_type)
        })

        # 智能推荐相关案例
        if 'contact_company' in template_vars:
            personalized_vars['recommended_cases'] = self._recommend_cases(
                template_vars['contact_company'],
                industry_type
            )

        # 个性化ROI信息
        if industry_type == 'enterprise':
            personalized_vars['roi_calculation'] = self._calculate_roi(
                template_vars.get('project_budget', '100万'),
                template_vars.get('company_size', 'medium')
            )

        return personalized_vars

    def _get_industry_badge(self, industry_type):
        """获取行业徽章"""
        badges = {
            'government': '政府采购合格供应商',
            'education': '教育信息化优质服务商',
            'enterprise': '企业数字化转型专家'
        }
        return badges.get(industry_type, '智能化系统集成商')

    def _recommend_cases(self, company_name, industry_type):
        """基于公司类型推荐案例"""
        # 这里可以实现更复杂的推荐算法
        # 目前使用简单的关键词匹配
        company_keywords = company_name.lower()

        if '大学' in company_keywords or '学院' in company_keywords:
            return self._get_education_cases()
        elif '政府' in company_keywords or '局' in company_keywords:
            return self._get_government_cases()
        else:
            return self._get_enterprise_cases()
```

### 2. 智能内容匹配

```python
class ContentMatcher:
    """内容智能匹配器"""

    def __init__(self):
        self.content_rules = {
            'project_keywords': {
                '弱电工程': ['弱电', '电气', '电路'],
                '安防监控': ['安防', '监控', '摄像', '门禁'],
                '网络建设': ['网络', '布线', '交换机', '路由器'],
                '会议系统': ['会议', '音响', '投影', '视频会议'],
                '楼宇自动化': ['楼宇', '自控', '空调', '照明']
            },
            'budget_tiers': {
                'low': (0, 100),      # 100万以下
                'medium': (100, 500), # 100-500万
                'high': (500, 1000),  # 500-1000万
                'enterprise': (1000, float('inf')) # 1000万以上
            }
        }

    def match_content(self, project_info):
        """匹配最适合的内容"""
        matched_content = {
            'focus_areas': [],
            'recommended_solutions': [],
            'case_studies': [],
            'budget_tier': self._classify_budget(project_info.get('budget', 0))
        }

        # 基于项目标题和描述匹配关键词
        project_text = ' '.join([
            project_info.get('title', ''),
            project_info.get('requirements', ''),
            project_info.get('description', '')
        ]).lower()

        for category, keywords in self.content_rules['project_keywords'].items():
            if any(keyword in project_text for keyword in keywords):
                matched_content['focus_areas'].append(category)
                matched_content['recommended_solutions'].extend(
                    self._get_solutions_for_category(category)
                )

        # 推荐案例研究
        matched_content['case_studies'] = self._recommend_case_studies(
            matched_content['focus_areas'],
            matched_content['budget_tier']
        )

        return matched_content

    def _classify_budget(self, budget_amount):
        """预算分类"""
        for tier, (min_amount, max_amount) in self.content_rules['budget_tiers'].items():
            if min_amount <= budget_amount < max_amount:
                return tier
        return 'low'
```

## 设计最佳实践

### 1. 邮件客户端兼容性

```css
/* Outlook兼容性 */
.outlook-compatibility {
    /* 避免使用CSS3属性 */
    /* 使用table布局替代div */
    /* 内联所有CSS样式 */
}

/* 移动端优化 */
@media only screen and (max-width: 480px) {
    .mobile-stack {
        display: block !important;
        width: 100% !important;
    }

    .mobile-center {
        text-align: center !important;
    }

    .mobile-full-width {
        width: 100% !important;
        max-width: 100% !important;
    }
}
```

### 2. 送达率优化

```python
class DeliverabilityOptimizer:
    """送达率优化器"""

    def __init__(self):
        self.spam_keywords = [
            '免费', '赚钱', '点击', '紧急', '立即',
            '恭喜', '中奖', '优惠', '促销', '代购'
        ]

    def optimize_content(self, subject, html_content):
        """优化内容以提高送达率"""
        # 检查垃圾邮件关键词
        spam_score = self._calculate_spam_score(subject, html_content)

        if spam_score > 0.5:
            html_content = self._clean_content(html_content)

        # 优化HTML结构
        optimized_html = self._optimize_html_structure(html_content)

        # 添加送达示踪
        if self.enable_tracking:
            optimized_html = self._add_tracking(optimized_html)

        return {
            'subject': self._optimize_subject(subject),
            'html': optimized_html,
            'spam_score': spam_score
        }

    def _calculate_spam_score(self, subject, content):
        """计算垃圾邮件分数"""
        text = (subject + ' ' + content).lower()
        keyword_count = sum(1 for keyword in self.spam_keywords if keyword in text)
        return min(1.0, keyword_count / len(self.spam_keywords))
```

## 模板管理系统

### 1. 版本控制

```python
class TemplateVersionManager:
    """模板版本管理器"""

    def __init__(self, template_dir):
        self.template_dir = Path(template_dir)
        self.version_file = self.template_dir / 'versions.json'
        self.versions = self._load_versions()

    def create_version(self, template_name, content, description=""):
        """创建新版本"""
        version_id = self._generate_version_id()
        version_info = {
            'version_id': version_id,
            'template_name': template_name,
            'description': description,
            'created_at': datetime.now().isoformat(),
            'content_hash': self._calculate_hash(content)
        }

        # 保存版本文件
        version_file = self.template_dir / f'{template_name}_v{version_id}.html'
        with open(version_file, 'w', encoding='utf-8') as f:
            f.write(content)

        # 更新版本记录
        if template_name not in self.versions:
            self.versions[template_name] = []
        self.versions[template_name].append(version_info)

        self._save_versions()
        return version_id
```

### 2. A/B测试支持

```python
class ABTestManager:
    """A/B测试管理器"""

    def __init__(self):
        self.active_tests = {}
        self.test_results = {}

    def create_ab_test(self, template_name, variant_a, variant_b, traffic_split=0.5):
        """创建A/B测试"""
        test_id = self._generate_test_id()

        test_config = {
            'test_id': test_id,
            'template_name': template_name,
            'variant_a': variant_a,
            'variant_b': variant_b,
            'traffic_split': traffic_split,
            'created_at': datetime.now().isoformat(),
            'metrics': {
                'sent_a': 0,
                'sent_b': 0,
                'opens_a': 0,
                'opens_b': 0,
                'clicks_a': 0,
                'clicks_b': 0
            }
        }

        self.active_tests[test_id] = test_config
        return test_id

    def assign_variant(self, test_id, contact_id):
        """为联系人分配测试变体"""
        test = self.active_tests.get(test_id)
        if not test:
            return None

        # 简单的哈希分配算法
        import hashlib
        hash_input = f"{test_id}_{contact_id}".encode()
        hash_value = int(hashlib.md5(hash_input).hexdigest(), 16)

        if (hash_value % 100) < (test['traffic_split'] * 100):
            return 'variant_a'
        else:
            return 'variant_b'
```

这份邮件模板库文档提供了全面的邮件营销模板体系，包括不同行业的专用模板、个性化策略、设计最佳实践和管理系统，为智能化设计营销自动化系统提供了强大的邮件营销能力。