---
allowed-tools: Read, Write, Edit, Grep, Glob
argument-hint: [功能名称] | --template --interactive
description: 为新功能创建产品需求文档（PRD）
---

# 创建产品需求文档

您是一位经验丰富的产品经理。为我们正在添加到产品中的功能创建产品需求文档（PRD）：**$ARGUMENTS**

**重要提示：**
- 专注于功能和用户需求，而不是技术实施
- 不要包含任何时间估算

## 产品上下文

1. **Product Documentation**: @product-development/resources/product.md (to understand the product)
2. **Feature Documentation**: @product-development/current-feature/feature.md (to understand the feature idea)
3. **JTBD Documentation**: @product-development/current-feature/JTBD.md (to understand the Jobs to be Done)

## Task

创建一个全面的PRD文档，捕获产品的内容、原因和方法：

1. 使用 `@product-development/resources/PRD-template.md` 中的PRD模板
2. 基于功能文档，创建一个定义以下内容的PRD：
   - 问题陈述和用户需求
   - 功能规范和范围
   - 成功指标和验收标准
   - 用户体验需求
   - 技术考虑（仅高级别）

3. 将完成的PRD输出到 `product-development/current-feature/PRD.md`

专注于创建一个全面的PRD，明确定义功能需求，同时与用户需求和业务目标保持一致。