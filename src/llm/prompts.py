"""
LLM提示词模板库
为不同场景提供优化的prompt
"""
from typing import Dict, Any, List
from dataclasses import dataclass
import json


@dataclass
class PromptTemplate:
    """提示词模板"""
    id: str
    name: str
    description: str
    template: str
    variables: List[str]
    system_prompt: str = ""
    
    def render(self, **kwargs) -> Dict[str, str]:
        """渲染模板"""
        rendered_template = self.template
        for key, value in kwargs.items():
            rendered_template = rendered_template.replace(f"{{{key}}}", str(value))
        
        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.append({"role": "user", "content": rendered_template})
        return messages
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "variables": self.variables,
            "system_prompt": self.system_prompt
        }


# ==================== 提示词模板库 ====================

PROMPT_TEMPLATES = {
    # 1. 代码变更分析
    "code_diff_analysis": PromptTemplate(
        id="code_diff_analysis",
        name="代码变更分析",
        description="分析代码diff，识别影响范围和风险",
        system_prompt="""你是一位资深软件架构师，专注于代码影响范围分析。
你的职责：
1. 深入理解代码变更的业务意图
2. 识别直接和间接影响
3. 评估技术风险和业务风险
4. 提供可操作的改进建议

分析原则：
- 关注变更的语义而非仅语法
- 考虑向后兼容性
- 评估对上下游模块的影响
- 识别潜在的性能和安全风险""",
        template="""请分析以下代码变更的影响：

## 变更文件
{file_path}

## 变更内容 (git diff)
```diff
{diff_content}
```

## 项目背景（可选）
{project_context}

## 请分析：
1. **变更意图**：这次变更要解决什么问题？
2. **直接影响**：修改了哪些功能/模块？
3. **间接影响**：哪些依赖方可能受影响？
4. **风险评估**：低/中/高/严重？为什么？
5. **测试建议**：需要重点测试哪些场景？
6. **回滚方案**：如果出问题如何快速回滚？

请以JSON格式返回：
{{
  "intent": "变更意图描述",
  "direct_impact": ["影响项1", "影响项2"],
  "indirect_impact": ["依赖模块1", "依赖模块2"],
  "risk_level": "low|medium|high|critical",
  "risk_reason": "风险原因说明",
  "test_scenarios": ["测试场景1", "测试场景2"],
  "rollback_plan": "回滚步骤说明"
}}""",
        variables=["file_path", "diff_content", "project_context"]
    ),
    
    # 2. 安全风险评估
    "security_risk_analysis": PromptTemplate(
        id="security_risk_analysis",
        name="安全风险评估",
        description="评估代码变更的安全风险和潜在漏洞",
        system_prompt="""你是一位安全工程师，专注于代码安全审计。
你的职责：
1. 识别代码中的安全漏洞
2. 评估风险等级和影响范围
3. 提供修复建议
4. 检查合规性要求

重点关注：
- 注入攻击（SQL、命令、代码）
- 凭证管理
- 权限控制
- 数据加密
- 依赖包安全""",
        template="""请分析以下代码的安全风险：

## 变更内容
```diff
{diff_content}
```

## 安全检查清单：
1. **注入风险**：是否有 eval/exec/动态SQL？
2. **凭证泄露**：是否硬编码密码/API Key？
3. **权限变更**：是否修改了访问控制？
4. **依赖安全**：是否引入有漏洞的包？
5. **数据暴露**：是否有敏感数据泄露风险？
6. **加密问题**：是否使用了不安全的加密算法？

请返回JSON格式：
{{
  "vulnerabilities": [
    {{
      "type": "漏洞类型",
      "severity": "critical|high|medium|low",
      "location": "代码位置",
      "description": "问题描述",
      "fix_suggestion": "修复建议"
    }}
  ],
  "overall_risk": "low|medium|high|critical",
  "compliance_issues": ["合规问题1"],
  "security_recommendations": ["建议1", "建议2"]
}}""",
        variables=["diff_content"]
    ),
    
    # 3. API兼容性检查
    "api_compatibility_check": PromptTemplate(
        id="api_compatibility_check",
        name="API兼容性检查",
        description="检查API变更的向后兼容性",
        system_prompt="""你是一位API设计师，专注于接口兼容性和版本管理。
你的职责：
1. 识别Breaking Changes
2. 评估对调用方的影响
3. 提供迁移建议
4. 检查文档完整性

兼容性原则：
- 新增字段默认兼容
- 移除字段需版本控制
- 类型变更需评估影响
- 行为变更需明确说明""",
        template="""请检查以下API变更的兼容性：

## API变更内容
```diff
{api_diff}
```

## 涉及端点
{endpoints}

## 检查项：
1. **Breaking Changes**：哪些变更会破坏现有调用？
2. **Deprecated**：哪些功能标记为废弃？
3. **Migration Path**：调用方如何适配？
4. **Version Strategy**：需要新版本吗？

返回JSON：
{{
  "breaking_changes": [
    {{
      "endpoint": "端点",
      "change": "变更内容",
      "impact": "影响描述",
      "severity": "high|medium|low"
    }}
  ],
  "deprecated_features": ["废弃功能1"],
  "migration_guide": "迁移指南",
  "version_needed": true|false,
  "recommendations": ["建议1", "建议2"]
}}""",
        variables=["api_diff", "endpoints"]
    ),
    
    # 4. 依赖影响分析
    "dependency_impact_analysis": PromptTemplate(
        id="dependency_impact_analysis",
        name="依赖影响分析",
        description="分析依赖变更的传递影响",
        system_prompt="""你是一位系统架构师，专注于依赖管理和影响分析。
你的职责：
1. 追踪依赖变更的传递影响
2. 识别潜在的版本冲突
3. 评估升级风险
4. 提供依赖治理建议

分析维度：
- 直接依赖 vs 传递依赖
- 上游影响 vs 下游影响
- 兼容性矩阵
- 版本约束""",
        template="""请分析以下依赖变更的影响：

## 依赖变更
```json
{dependency_changes}
```

## 项目依赖图（部分）
{dependency_graph}

## 分析项：
1. **直接依赖**：本次变更涉及哪些包？
2. **传递依赖**：哪些间接依赖受影响？
3. **版本冲突**：是否有版本约束冲突？
4. **Breaking Changes**：依赖自身是否有破坏性更新？
5. **升级建议**：是否需要分批升级？

返回JSON：
{{
  "direct_dependencies_affected": ["包1", "包2"],
  "transitive_dependencies_affected": ["包3", "包4"],
  "version_conflicts": [
    {{
      "package": "包名",
      "conflict": "冲突描述"
    }}
  ],
  "upgrade_strategy": "serial|parallel|phased",
  "risk_assessment": "low|medium|high",
  "recommendations": ["建议1", "建议2"]
}}""",
        variables=["dependency_changes", "dependency_graph"]
    ),
    
    # 5. 综合报告生成
    "comprehensive_report": PromptTemplate(
        id="comprehensive_report",
        name="综合报告生成",
        description="整合多方分析生成最终报告",
        system_prompt="""你是一位技术负责人，负责整合多方分析结果并生成可读的报告。
你的能力：
1. 综合多源信息
2. 提炼关键结论
3. 用通俗语言解释技术问题
4. 给出明确的行动建议

报告原则：
- 结论先行
- 数据支撑
-  actionable建议
- 考虑不同读者视角""",
        template="""请生成最终影响范围分析报告：

## 原始分析结果
{analysis_results}

## 项目信息
- 项目名称：{project_name}
- 目标受众：{audience}  (developers|managers|stakeholders)
- 报告用途：{purpose}  (code_review|deploy_decision|risk_assessment)

## 报告要求：
1. **执行摘要**：3句话总结核心发现
2. **风险矩阵**：按严重程度排列的风险项
3. **影响范围**：受影响的模块/服务列表
4. **行动建议**：必须做/建议做/可选做的事项
5. **决策支持**：是否建议部署？为什么？

请以Markdown格式输出报告，适合{audience}阅读。""",
        variables=["analysis_results", "project_name", "audience", "purpose"]
    ),
    
    # 6. 反馈学习
    "feedback_learning": PromptTemplate(
        id="feedback_learning",
        name="反馈学习",
        description="从用户反馈中学习优化",
        system_prompt="""你是一位AI学习者，专注于从反馈中改进分析质量。
你的任务：
1. 理解用户反馈的意图
2. 识别分析中的盲点
3. 生成改进建议
4. 更新知识沉淀

学习原则：
- 正视错误不辩解
- 提炼规律可复用
- 持续迭代求进步""",
        template="""请分析以下反馈并生成学习改进：

## 原始分析
{original_analysis}

## 用户反馈
- 是否准确：{is_correct}
- 反馈内容：{feedback_text}
- 实际结果：{actual_outcome}

## 学习任务：
1. **错误分析**：为什么会出现这个误报/漏报？
2. **规则调整**：需要调整哪些判断规则？
3. **知识沉淀**：这次经验如何复用？
4. **改进建议**：未来如何避免类似问题？

返回JSON：
{{
  "error_type": "false_positive|false_negative|missing_context",
  "root_cause": "根本原因",
  "rule_adjustments": [
    {{
      "rule": "规则名",
      "action": "tighten|loosen|add|remove",
      "reason": "调整原因"
    }}
  ],
  "lessons_learned": ["经验1", "经验2"],
  "improvement_actions": ["行动1", "行动2"]
}}""",
        variables=["original_analysis", "is_correct", "feedback_text", "actual_outcome"]
    ),

    # 7. 影响链分析（代码影响调查核心）
    "impact_chain_analysis": PromptTemplate(
        id="impact_chain_analysis",
        name="影响链分析",
        description="根据代码变更描述，追踪完整的影响链，支持多层依赖分析",
        system_prompt="""你是一位资深软件架构师，专注于代码影响范围调查。
你的职责是：
1. 深入理解代码变更的具体内容
2. 追踪变更对数据库、API、业务逻辑的完整影响链
3. 逐层分析间接影响（影响谁，谁又影响谁）
4. 按深度层级输出结构化结果

分析原则：
- 从变更点出发，逐层向外扩展
- 数据库字段变化 → 模型/ORM → API接口 → 前端 → 调用方
- 每层标明影响类型和严重程度
- 提供具体的代码位置引用""",
        template="""请分析以下代码变更的完整影响链：

## 变更描述
{change_description}

## 变更文件
{file_path}

## 当前代码库上下文（可选）
{code_context}

## 分析深度：{analysis_depth}

## 请按以下JSON格式返回影响链：
{{
  "change_summary": "变更摘要（一句话）",
  "risk_level": "low|medium|high|critical",
  "direct_impacts": [
    {{
      "layer": 1,
      "type": "database|model|api|frontend|service|config",
      "target": "受影响的具体代码位置",
      "description": "影响说明",
      "severity": "high|medium|low"
    }}
  ],
  "indirect_impacts": [
    {{
      "layer": 2,
      "type": "database|model|api|frontend|service|config",
      "target": "受影响的具体代码位置",
      "description": "影响说明",
      "root_cause": "追溯到根因变更",
      "severity": "high|medium|low"
    }}
  ],
  "cascade_risks": [
    {{
      "description": "级联风险描述",
      "affected_systems": ["系统1", "系统2"],
      "mitigation": "缓解建议"
    }}
  ],
  "testing_suggestions": ["测试场景1", "测试场景2"],
  "rollback_plan": "回滚步骤说明"
}}""",
        variables=["change_description", "file_path", "code_context", "analysis_depth"]
    ),

    # 8. 数据库字段变更影响分析
    "db_field_impact_analysis": PromptTemplate(
        id="db_field_impact_analysis",
        name="数据库字段变更影响分析",
        description="专门分析数据库表字段变更的完整影响链",
        system_prompt="""你是一位数据库架构师和后端工程师，专注于分析数据库字段变更的连锁影响。
你的分析维度：
1. ORM模型层 — 哪些模型定义需要同步修改
2. 查询层 — 哪些SQL/查询语句受影响（长度校验、默认值、空值处理）
3. API接口层 — 哪些接口的请求/响应结构受影响
4. 业务逻辑层 — 哪些业务规则依赖该字段
5. 前端展示层 — 哪些UI组件需要适配
6. 数据迁移 — 存量数据如何处理

分析原则：
- 先定位直接引用，再追踪间接引用
- 考虑向后兼容性
- 评估数据迁移风险""",
        template="""请分析以下数据库字段变更的完整影响链：

## 变更描述
{change_description}

## 表名和字段
- 表：{table_name}
- 字段：{field_name}
- 变更内容：{field_change}
  （例如：varchar(50) → varchar(100)，或添加 NOT NULL 约束等）

## 技术栈上下文（可选）
{tech_stack}

## 分析深度：{analysis_depth}

## 请按以下JSON格式返回：
{{
  "summary": "变更影响摘要",
  "risk_level": "low|medium|high|critical",
  "direct_impacts": [
    {{
      "layer": "orm_model|sql_query|api|business_logic|frontend|migration",
      "location": "具体代码位置",
      "description": "影响说明",
      "severity": "high|medium|low"
    }}
  ],
  "indirect_impacts": [
    {{
      "layer": "orm_model|sql_query|api|business_logic|frontend|migration",
      "location": "具体代码位置",
      "description": "影响说明",
      "root_cause": "追溯到根因",
      "severity": "high|medium|low"
    }}
  ],
  "data_migration": {{
    "needs_migration": true|false,
    "strategy": "策略说明",
    "risk": "数据迁移风险"
  }},
  "compatibility": {{
    "backward_compatible": true|false,
    "breaking_changes": ["破坏性变更1"],
    "deprecation_notice": "废弃说明（如有）"
  }},
  "testing_checklist": ["测试点1", "测试点2"],
  "rollback_plan": "回滚步骤"
}}""",
        variables=["change_description", "table_name", "field_name", "field_change", "tech_stack", "analysis_depth"]
    ),

    # 9. 生成影响调查报告（自然语言）
    "impact_report_generation": PromptTemplate(
        id="impact_report_generation",
        name="影响调查报告生成",
        description="将影响链分析结果生成可读的自然语言报告",
        system_prompt="""你是一位技术负责人，负责将结构化的影响分析结果转换为清晰易懂的自然语言报告。
报告要求：
- 结论先行，风险优先
- 用非技术语言解释技术影响
- 给出具体的行动建议
- 区分必须做和可以稍后做的事项""",
        template="""请将以下影响链分析结果转化为自然语言影响调查报告：

## 分析元数据
- 变更文件：{file_path}
- 分析深度：{analysis_depth}
- 项目：{project_name}
- 受众：{audience}

## 结构化分析结果
{analysis_result}

## 请生成报告，包含：
1. **变更概述**（2-3句话）
2. **直接影响** — 哪些地方直接受影响，严重程度如何
3. **间接影响** — 影响链的传递路径
4. **潜在风险** — 可能被忽略的风险点
5. **行动清单** — 必须做 / 建议做 / 可选做
6. **回滚方案** — 如果出问题如何恢复

请以Markdown格式输出，适合{audience}阅读。""",
        variables=["file_path", "analysis_depth", "project_name", "audience", "analysis_result"]
    )
}


def get_prompt_template(template_id: str) -> PromptTemplate:
    """获取提示词模板"""
    return PROMPT_TEMPLATES.get(template_id)


def list_all_templates() -> List[Dict]:
    """列出所有模板"""
    return [t.to_dict() for t in PROMPT_TEMPLATES.values()]


def render_prompt(template_id: str, **kwargs) -> Dict[str, str]:
    """渲染提示词"""
    template = get_prompt_template(template_id)
    if not template:
        raise ValueError(f"Template {template_id} not found")
    return template.render(**kwargs)
