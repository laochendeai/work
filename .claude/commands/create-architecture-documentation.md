---
allowed-tools: Read, Write, Edit, Bash
argument-hint: [框架] | --c4-model --arc42 --adr --plantuml --full-suite
description: 生成综合架构文档，包含图表、ADR和交互式可视化
---

# 架构文档生成器

生成综合架构文档：$ARGUMENTS

## 当前架构上下文

- 项目结构：!`find . -type f -name "*.json" -o -name "*.yaml" -o -name "*.toml" | head -5`
- 现有文档：@docs/ 或 @README.md（如果存在）
- 架构文件：!`find . -name "*architecture*" -o -name "*design*" -o -name "*.puml" | head -3`
- Services/containers: @docker-compose.yml or @k8s/ (if exists)
- API definitions: !`find . -name "*api*" -o -name "*openapi*" -o -name "*swagger*" | head -3`

## 任务

使用现代工具和最佳实践生成全面的架构文档：

1. **架构分析和发现**
   - 分析当前系统架构和组件关系
   - 识别关键架构模式和设计决策
   - 记录系统边界、接口和依赖关系
   - 评估数据流和通信模式
   - 识别架构债务和改进机会

2. **架构文档框架**
   - 选择适当的文档框架和工具：
     - **C4模型**：上下文、容器、组件、代码图表
     - **Arc42**：全面的架构文档模板
     - **架构决策记录（ADRs）**：决策文档
     - **PlantUML/Mermaid**：代码图表文档
     - **Structurizr**：C4模型工具和可视化
     - **Draw.io/Lucidchart**：可视化图表工具

3. **系统上下文文档**
   - 创建高级别的系统上下文图表
   - 记录外部系统和集成
   - 定义系统边界和职责
   - 记录用户角色和利益相关者
   - 创建系统景观和生态系统概述

4. **容器和服务架构**
   - 记录容器/服务架构和部署视图
   - 创建服务依赖映射和通信模式
   - 记录部署架构和基础设施
   - 定义服务边界和API契约
   - 记录数据持久化和存储架构

5. **组件和模块文档**
   - 创建详细的组件架构图表
   - 记录内部模块结构和关系
   - 定义组件职责和接口
   - 记录设计模式和架构风格
   - 创建代码组织和包结构文档

6. **数据架构文档**
   - 记录数据模型和数据库模式
   - 创建数据流图和处理管道
   - 记录数据存储策略和技术
   - 定义数据治理和生命周期管理
   - 创建数据集成和同步文档

7. **安全和合规架构**
   - 记录安全架构和威胁模型
   - 创建身份验证和授权流程图
   - 记录合规要求和控制措施
   - 定义安全边界和信任区域
   - 创建事件响应和安全监控文档

8. **质量属性和横切关注点**
   - 记录性能特征和可扩展性模式
   - 创建可靠性和可用性架构文档
   - Document monitoring and observability architecture
   - Define maintainability and evolution strategies
   - Create disaster recovery and business continuity documentation

9. **Architecture Decision Records (ADRs)**
   - Create comprehensive ADR template and process
   - Document historical architectural decisions and rationale
   - Create decision tracking and review process
   - Document trade-offs and alternatives considered
   - Set up ADR maintenance and evolution procedures

10. **Documentation Automation and Maintenance**
    - Set up automated diagram generation from code annotations
    - Configure documentation pipeline and publishing automation
    - Set up documentation validation and consistency checking
    - Create documentation review and approval process
    - Train team on architecture documentation practices and tools
    - Set up documentation versioning and change management