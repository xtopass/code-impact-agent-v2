# Code Impact Agent v2 技术文档

> 基于多Agent协作架构的代码变更影响范围分析系统

---

## 目录

1. [系统概述](#1-系统概述)
2. [架构设计](#2-架构设计)
3. [核心模块详解](#3-核心模块详解)
4. [API 参考](#4-api-参考)
5. [扩展开发指南](#5-扩展开发指南)
6. [部署与配置](#6-部署与配置)

---

## 1. 系统概述

### 1.1 项目简介

Code Impact Agent v2 是一个智能代码影响范围分析系统，通过多 Agent 协作架构实现对代码变更的全面评估。系统融合了静态分析、动态追踪、安全扫描和自学习引擎，能够从多个维度评估代码变更的潜在风险。

### 1.2 核心价值

| 维度 | 传统方案 | Code Impact Agent v2 |
|------|----------|---------------------|
| 分析范围 | 单一语言/工具 | 多语言支持（Python/JS/Java/Puppet） |
| 执行方式 | 串行执行 | 多Agent并行协作 |
| 智能化 | 静态规则 | 自学习优化 + LLM辅助 |
| 扩展性 | 固定功能 | MCP/Skill插件热插拔 |
| 准确率 | 人工校准 | 用户反馈驱动自动调优 |

### 1.3 技术栈

- **后端**: Python 3.10+ / FastAPI / Uvicorn
- **前端**: Vue 3 / Vite / Tailwind CSS
- **AI层**: LangChain / DeepSeek API
- **协议**: MCP (Model Context Protocol)
- **存储**: LowDB (JSON文件数据库)

---

## 2. 架构设计

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Web Interface (Vue 3)                       │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         API Gateway (FastAPI)                        │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌──────────────┐ │
│  │ /api/mcp    │ │ /api/skills │ │ /api/agents │ │ /api/cases   │ │
│  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬───────┘ │
└─────────┼───────────────┼───────────────┼──────────────┼───────────┘
          │               │               │               │
          ▼               ▼               ▼               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         AgentSystem (核心)                           │
│  ┌───────────┐ ┌───────────┐ ┌───────────┐ ┌───────────────────┐   │
│  │ MCP Client│ │ Skill Reg │ │ Agent Rtr │ │ Learning Engine   │   │
│  └─────┬─────┘ └─────┬─────┘ └─────┬─────┘ └────────┬──────────┘   │
│        │             │             │                │               │
│        ▼             ▼             ▼                ▼               │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    外部工具集成层                              │  │
│  │  Git │ Semgrep │ Puppet │ Dependency Graph │ LLM API          │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 模块分层

```
┌────────────────────────────────────────────┐
│           Presentation Layer               │  ← Web UI, API Routes
├────────────────────────────────────────────┤
│           Application Layer                │  ← AgentSystem, Crew Coordination
├────────────────────────────────────────────┤
│           Domain Layer                     │  ← AgentRouter, SkillRegistry
├────────────────────────────────────────────┤
│           Infrastructure Layer             │  ← MCPClient, LLMClient, Memory
├────────────────────────────────────────────┤
│           Data Layer                       │  ← LowDB, File Storage
└────────────────────────────────────────────┘
```

---

## 3. 核心模块详解

### 3.1 AgentSystem — 系统核心

**文件**: `src/system.py`

AgentSystem 是整个系统的协调中心，负责初始化所有模块并管理系统全局状态。

```python
class AgentSystem:
    def __init__(self):
        self.data_dir = Path(os.environ.get("DATA_DIR", "./data"))
        self._init_modules()
    
    def _init_modules(self):
        # 初始化顺序：MCP → Skills → Agents → Learning
        init_mcp(mcp_servers)          # MCP客户端
        init_skills(skill_dir)         # Skill注册表
        init_memory(memory_dir)        # 记忆系统
        init_context(...)              # 上下文管理
        init_llm(provider, api_key)   # LLM客户端
        init_repositories(...)         # 代码库管理
```

**关键职责**:
- 模块初始化与依赖注入
- 配置加载与持久化
- 全局状态管理

### 3.2 AgentRouter — 智能路由系统

**文件**: `src/agents/router.py`

AgentRouter 实现了基于能力的任务分发和负载均衡机制。

#### 3.2.1 Agent 角色模型

```python
class AgentRole(str, Enum):
    EXPERT      = "expert"      # 领域专家：执行具体分析任务
    COORDINATOR = "coordinator" # 协调者：任务分解与调度
    REVIEWER    = "reviewer"    # 审查者：结果审核与质量检查
    LEARNER     = "learner"     # 学习者：从历史中学习优化
```

#### 3.2.2 路由算法

```
任务到达
    │
    ▼
┌──────────────────┐
│ 匹配 capability  │ ← routing_table[task_type]
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 过滤可用 Agent   │ ← status in [IDLE, BUSY]
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ 选择负载最小者   │ ← min(tasks_completed)
└────────┬─────────┘
         │
         ▼
      执行任务
```

#### 3.2.3 AgentCrew 协作模型

```python
crew = get_or_create_crew("分析团队", "crew_001")
crew.add_member(code_agent, role="代码分析专家")
crew.add_member(security_agent, role="安全审查专家")
crew.set_workflow(["code_analysis", "security_review", "final_report"])
result = await crew.execute(task_data)
```

**工作流执行流程**:
1. 按 `workflow` 顺序遍历步骤
2. 为每个步骤匹配具有对应 capability 的 Agent
3. 依次执行各步骤，收集结果
4. 返回综合报告

### 3.3 MCPClient — 外部工具集成

**文件**: `src/mcp/client.py`

MCP (Model Context Protocol) 是系统扩展工具能力的标准协议。

#### 3.3.1 内置 MCP 服务器

| 服务器名 | 功能 | 工具列表 |
|----------|------|----------|
| `git` | Git版本控制 | `git_diff`, `git_log`, `git_changed_files` |
| `semgrep` | 静态安全扫描 | `semgrep_scan` |
| `puppet` | 基础设施配置 | `puppet_validate`, `puppet_dependencies` |
| `dependency` | 依赖图构建 | `dep_graph_build` |

#### 3.3.2 MCP 工具调用示例

```python
# 获取文件变更
client.call_tool("git", "git_diff", {"file": "src/app.py"})
# 返回: {"output": "...", "returncode": 0}

# 安全扫描
client.call_tool("semgrep", "semgrep_scan", {"target": "src/"})
# 返回: {"results": [...]}
```

#### 3.3.3 自定义 MCP 扩展

```bash
# 通过 API 添加自定义 MCP
curl -X POST http://localhost:3000/api/mcp/servers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-tool",
    "command": "npx",
    "args": ["my-mcp-server"]
  }'
```

### 3.4 SkillRegistry — 可插拔技能系统

**文件**: `src/skills/registry.py`

Skill 是封装了特定能力的独立模块，支持动态加载和热更新。

#### 3.4.1 Skill 元数据模型

```python
@dataclass
class SkillMetadata:
    id: str                  # 唯一标识符
    name: str                # 显示名称
    version: str             # 版本号
    description: str         # 功能描述
    author: str              # 作者
    tags: List[str]          # 标签分类
    dependencies: List[str]  # 依赖的其他 Skill
    entry_point: str         # Python模块入口点
    config_schema: Dict      # 配置Schema定义
```

#### 3.4.2 内置 Skill

| Skill ID | 名称 | 描述 | 依赖 |
|----------|------|------|------|
| `builtin.code-analyzer` | 代码分析器 | 分析代码结构和依赖关系 | 无 |
| `builtin.git-tracker` | Git变更追踪 | 追踪Git变更并生成报告 | 无 |
| `builtin.security-scanner` | 安全扫描器 | 扫描代码中的安全问题 | code-analyzer |

#### 3.4.3 创建自定义 Skill

```python
# skills/my_skill.py
class MySkill:
    async def execute(self, input_data: Dict) -> Dict:
        # 实现业务逻辑
        return {"result": "success", "data": {...}}

# 注册
metadata = SkillMetadata(
    id="my_custom_skill",
    name="我的自定义Skill",
    entry_point="skills.my_skill:MySkill.execute",
    tags=["custom", "analysis"]
)
registry.register_skill(metadata)
```

### 3.5 LearningEngine — 自学习引擎

**文件**: `src/learning/engine.py`

系统从历史分析案例中自动学习，持续优化分析准确率和性能。

#### 3.5.1 案例记录模型

```python
@dataclass
class CaseRecord:
    case_id: str              # 案例唯一ID
    timestamp: str            # 时间戳
    target_file: str          # 目标文件
    risk_level: str           # 风险等级
    findings_count: int       # 发现数量
    agents_used: List[str]    # 使用的Agent
    execution_time_ms: int    # 执行耗时
    quality_score: float      # 质量评分
    user_feedback: Optional[str]  # 用户反馈
    is_correct: Optional[bool]    # 是否正确
```

#### 3.5.2 学习流程

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  记录案例    │────▶│  分析模式    │────▶│  生成建议    │
│  record_case │     │ analyze_     │     │ generate_    │
│              │     │ patterns()   │     │ adjustments  │
└──────────────┘     └──────────────┘     └──────┬───────┘
                                                  │
                                          ┌───────▼───────┐
                                          │  应用调整     │
                                          │ apply_        │
                                          │ adjustments() │
                                          └───────────────┘
```

#### 3.5.3 模式分析维度

| 分析维度 | 计算方式 | 用途 |
|----------|----------|------|
| 风险分布 | `risk_level` 频次统计 | 识别高频风险类型 |
| 准确率 | 正确案例 / 总案例 | 评估系统整体质量 |
| 平均耗时 | `mean(execution_time_ms)` | 性能瓶颈识别 |
| 高频Agent | Agent使用频次排名 | 优化路由策略 |
| 时间趋势 | 最近7天案例数 | 趋势预测 |

#### 3.5.4 规则自动调优

```python
# 误报率过高时自动放宽阈值
if false_positive_rate > 0.3:
    adjustments.append(RuleAdjustment(
        rule_id="general_risk_threshold",
        adjustment_type="loosen",
        confidence=0.8
    ))

# 存在漏报时收紧检测规则
if high_risk_missed_count > 5:
    adjustments.append(RuleAdjustment(
        rule_id="deep_dependency_check",
        adjustment_type="tighten",
        confidence=0.7
    ))
```

---

## 4. API 参考

### 4.1 MCP 管理接口

```
GET    /api/mcp/servers                    # 列出所有MCP服务器
POST   /api/mcp/servers                    # 添加MCP服务器
DELETE /api/mcp/servers/{name}             # 删除MCP服务器
POST   /api/mcp/tools/{server}/{tool}      # 调用MCP工具
```

**请求示例 — 调用Git Diff**:
```bash
curl -X POST http://localhost:3000/api/mcp/tools/git/git_diff \
  -H "Content-Type: application/json" \
  -d '{"file": "src/app.py"}'
```

### 4.2 Skill 管理接口

```
GET    /api/skills                         # 列出所有Skills
POST   /api/skills                         # 注册新Skill
POST   /api/skills/{id}/execute            # 执行Skill
GET    /api/skills/marketplace             # 获取Skill市场
```

### 4.3 Agent 管理接口

```
GET    /api/agents                         # 列出所有Agent
GET    /api/agents/stats                   # 路由统计信息
POST   /api/agents/route                   # 路由任务
POST   /api/agents/crews                   # 创建Agent团队
```

**响应示例 — 路由统计**:
```json
{
  "total_agents": 5,
  "idle": 3,
  "busy": 2,
  "offline": 0,
  "routing_capacity": 0.6
}
```

### 4.4 学习引擎接口

```
POST   /api/cases                          # 记录新案例
POST   /api/cases/{id}/feedback            # 提交用户反馈
GET    /api/learning/insights              # 获取学习洞察
POST   /api/learning/rules/{id}/adjust     # 应用规则调整
```

**提交反馈示例**:
```bash
curl -X POST http://localhost:3000/api/cases/abc123/feedback \
  -H "Content-Type: application/json" \
  -d '{"is_correct": true, "feedback": "分析准确，覆盖全面"}'
```

### 4.5 分析接口

```
POST   /api/analyze                        # 运行完整影响分析
GET    /api/health                         # 健康检查
```

**分析请求示例**:
```json
{
  "target_file": "src/app.py",
  "depth": 2,
  "include_tests": false,
  "agents": ["code-analyzer", "security-scanner"]
}
```

**分析响应示例**:
```json
{
  "case_id": "a1b2c3d4",
  "risk_level": "high",
  "findings_count": 7,
  "execution_time_ms": 12500,
  "affected_files": ["src/app.py", "src/utils.py", "tests/test_app.py"],
  "dependencies": ["module_a", "module_b"],
  "recommendations": [...]
}
```

---

## 5. 扩展开发指南

### 5.1 添加新的 MCP 服务器

**步骤 1**: 创建 MCP 配置
```json
// data/mcp-servers.json
{
  "name": "custom-tool",
  "command": "npx",
  "args": ["my-custom-mcp"],
  "transport": "stdio",
  "enabled": true
}
```

**步骤 2**: 注册工具
```python
from src.mcp.client import get_mcp_client, MCPConfig, MCPTool

client = get_mcp_client()
config = MCPConfig(name="custom-tool", command="npx", args=["my-mcp"])
client.register_server(config)

# 定义工具
tools = [
    MCPTool(
        name="custom_action",
        description="执行自定义操作",
        input_schema={"type": "object", "properties": {"input": {"type": "string"}}}
    )
]
client.add_custom_mcp(config, tools)
```

### 5.2 开发自定义 Skill

**目录结构**:
```
skills/
├── my_skill.py          # Skill实现
└── registry.json        # 自动注册（或由API添加）
```

**Skill 实现模板**:
```python
# skills/my_skill.py
from typing import Dict, Any

class MySkill:
    """自定义Skill类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get("enabled", True)
    
    async def execute(self, input_data: Dict) -> Dict:
        """
        执行Skill的主要逻辑
        
        Args:
            input_data: 输入参数
            
        Returns:
            执行结果字典
        """
        if not self.enabled:
            return {"error": "Skill已禁用"}
        
        # 业务逻辑
        result = await self._process(input_data)
        
        return {
            "success": True,
            "result": result,
            "metadata": {
                "skill_id": "my_skill",
                "version": "1.0.0"
            }
        }
    
    async def _process(self, data: Dict) -> Any:
        """核心处理逻辑"""
        # 实现具体功能
        pass
```

**注册 Skill**:
```python
from src.skills.registry import get_skill_registry, SkillMetadata

registry = get_skill_registry()
metadata = SkillMetadata(
    id="my_custom_skill",
    name="我的自定义Skill",
    description="描述Skill功能",
    entry_point="skills.my_skill:MySkill",
    tags=["custom", "analysis"],
    dependencies=[],
    config_schema={
        "enabled": {"type": "boolean", "default": True}
    }
)
instance_id = registry.register_skill(metadata)
```

### 5.3 注册新 Agent

```python
from src.agents.router import get_agent_router, AgentConfig, AgentCapability, AgentRole

router = get_agent_router()

# 定义能力
capabilities = [
    AgentCapability(
        name="code_analysis",
        description="代码结构分析",
        input_types=["file_path", "code"],
        output_types=["analysis_result"],
        priority=1
    ),
    AgentCapability(
        name="dependency_trace",
        description="依赖关系追踪",
        input_types=["module"],
        output_types=["dependency_tree"],
        priority=2
    )
]

# 创建Agent配置
config = AgentConfig(
    id="code_analyst_01",
    name="代码分析师",
    role=AgentRole.EXPERT,
    capabilities=capabilities,
    description="专注于代码结构和依赖分析",
    max_concurrent=3,
    timeout=120
)

# 注册Agent
agent_id = router.register_agent(config)
```

---

## 6. 部署与配置

### 6.1 环境要求

| 组件 | 版本要求 | 说明 |
|------|----------|------|
| Python | ≥ 3.10 | 主开发语言 |
| Node.js | ≥ 18.0 | Web界面构建 |
| pip | 最新 | Python包管理 |
| npm | 最新 | Node包管理 |

### 6.2 安装步骤

```bash
# 1. 克隆项目
git clone <repository-url>
cd code-impact-agent-v2

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 API Key

# 3. 安装 Python 依赖
pip install -r requirements.txt

# 4. 安装 Node 依赖
npm install

# 5. 启动服务
python main.py
# 或开发模式
npm run dev
```

### 6.3 环境变量配置

```bash
# .env 文件
GITHUB_TOKEN=ghp_xxxxxxxxxxxx
PORT=3000
DATA_DIR=./data

# LLM配置
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx
LLM_MODEL=deepseek-chat

# 可选：其他配置
MAX_CONCURRENT_TASKS=10
ANALYSIS_TIMEOUT=300
```

### 6.4 数据存储结构

```
data/
├── mcp-servers.json      # MCP服务器配置
├── skills/
│   └── registry.json     # Skill注册表
├── cases.json            # 历史案例库
├── rules.json            # 分析规则库
├── memory/               # 记忆数据
└── repositories.json     # 代码库配置
```

### 6.5 生产部署

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 3000
CMD ["python", "main.py"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  api:
    build: .
    ports:
      - "3000:3000"
    environment:
      - LLM_PROVIDER=deepseek
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
    volumes:
      - ./data:/app/data
```

---

## 附录

### A. 系统启动流程

```
main.py
  └─ uvicorn.run("src.api:app")
       └─ from src.api import app
            └─ from src.system import get_system
                 └─ AgentSystem()
                      └─ _init_modules()
                           ├─ init_mcp()       → MCPClient单例
                           ├─ init_skills()      → SkillRegistry单例
                           ├─ init_memory()      → MemoryManager单例
                           ├─ init_context()     → ContextManager单例
                           ├─ init_repositories()→ RepositoryManager单例
                           └─ init_llm()         → LLMClient单例
```

### B. 关键设计模式

| 模式 | 应用位置 | 说明 |
|------|----------|------|
| 单例模式 | 所有 Manager/Client | 全局唯一实例，线程安全 |
| 工厂模式 | AgentRouter | 动态创建 Agent 实例 |
| 策略模式 | LearningEngine | 不同分析策略可插拔 |
| 观察者模式 | SkillRegistry | Skill状态变化通知 |
| 责任链模式 | AgentCrew | 多步骤工作流执行 |

### C. 常见问题

**Q: LLM API Key 未配置怎么办？**
```
A: 系统启动时会抛出 ValueError，请在 .env 文件中配置 LLM_API_KEY
```

**Q: 如何查看当前加载的 Skill？**
```bash
curl http://localhost:3000/api/skills
```

**Q: Agent 路由超时如何处理？**
```python
# 在 AgentConfig 中设置 timeout（秒）
config = AgentConfig(timeout=120, ...)
```

**Q: 如何重置学习引擎数据？**
```bash
rm data/cases.json data/rules.json
```

---

*文档版本: 2.0.0*  
*最后更新: 2024*
